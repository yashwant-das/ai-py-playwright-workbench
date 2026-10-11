"""The heal loop: run, gather evidence, diagnose, repair, verify.

``heal()`` never leaves a half-repaired spec behind: unless the result is
``healed``, the spec is restored to exactly what it was.
"""

import difflib
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from workbench.config import runs_dir
from workbench.context import collect_context
from workbench.environment import chromium_installed
from workbench.events import Emit, EventSink
from workbench.heal.classifier import classify_failure_heuristic
from workbench.heal.evidence import Collect, gather_evidence
from workbench.heal.planner import Hint, plan_fix
from workbench.heal.repair import apply_fix
from workbench.ids import new_run_id
from workbench.llm.cancellable import cancellable
from workbench.llm.chat import ChatModel, ModelError
from workbench.models.heal import (
    REPAIR_STRATEGY_LABELS,
    Attempt,
    AttemptOutcome,
    HealReport,
    HealStatus,
)
from workbench.models.shared import FailureType, RunResult, RunWarning
from workbench.reports import save_report
from workbench.runner import run_test

APP_DEFECT_CONFIDENCE = 0.7

Run = Callable[..., RunResult]

_EVIDENCE_LABEL = {
    "error_context": "Snapshot from the moment of failure",
    "page_load": "Snapshot from a fresh page load",
    "none": "No page snapshot available",
}


class HealRequest(BaseModel):
    """A spec to heal; the file is edited in place."""

    spec_path: Path
    max_attempts: int = Field(default=3, ge=1, le=5)


def heal(
    request: HealRequest,
    *,
    model: ChatModel,
    emit: Emit | None = None,
    cancel: threading.Event | None = None,
    run: Run = run_test,
    collect: Collect = collect_context,
    browsers_ready: Callable[[], bool] = chromium_installed,
) -> HealReport:
    """Heal ``request.spec_path`` and return the saved report."""
    return _HealRun(
        request, model, emit, cancel, run, collect, browsers_ready
    ).execute()


class _HealRun:
    def __init__(
        self,
        request: HealRequest,
        model: ChatModel,
        emit: Emit | None,
        cancel: threading.Event | None,
        run: Run,
        collect: Collect,
        browsers_ready: Callable[[], bool],
    ) -> None:
        self.spec = request.spec_path
        self.max_attempts = request.max_attempts
        self.run, self.collect = run, collect
        self.browsers_ready = browsers_ready
        self.cancel = cancel or threading.Event()
        # A model call blocks for minutes; this lets Cancel interrupt it.
        self.model = cancellable(model, self.cancel)
        # Restoring uses the raw bytes (line endings included); the pipeline
        # itself works on the decoded text.
        self.original_bytes = self.spec.read_bytes()
        self.original = self.spec.read_text(encoding="utf-8")
        self.code = self.original
        self.report = HealReport(
            id=new_run_id("heal", self.spec.stem),
            spec_name=self.spec.name,
            status="error",
            max_attempts=self.max_attempts,
            original_code=self.original,
            final_code=self.original,
        )
        self.run_root = runs_dir() / self.report.id
        self.events = EventSink(self.report.id, emit)
        self.warnings: set[RunWarning] = set()
        self.started = time.monotonic()

    def execute(self) -> HealReport:
        """Run the heal; the spec is restored unless it ends ``healed``, even on an exception."""
        try:
            return self._execute()
        except BaseException:
            self._restore_spec()
            raise

    def _restore_spec(self) -> None:
        """Put the original bytes back, writing only if the file differs."""
        try:
            current: bytes | None = self.spec.read_bytes()
        except FileNotFoundError:
            current = None
        if current != self.original_bytes:
            self.spec.write_bytes(self.original_bytes)
        self.code = self.original

    def _execute(self) -> HealReport:
        if not self.browsers_ready():
            self.warnings.add("playwright_browsers_missing")
            return self.finish(
                "error",
                "Playwright's Chromium is not installed. Run: npx playwright install chromium",
            )
        self.events.step("run", "active", f"npx playwright test {self.spec.name}")
        result = self.run(self.spec, self.run_root / "initial", cancel=self.cancel)
        self.report.initial_run = result
        if result.status == "cancelled":
            self.events.step("run", "skipped", "Cancelled")
            return self.finish("cancelled")
        if result.status == "error":
            self.events.step("run", "failed", _first_line(result.error_message))
            return self.finish("error", result.error_message)
        if result.passed:
            self.events.step("run", "done", "Passed on the first run")
            return self.finish("nothing_to_heal")
        self.events.step("run", "done", _first_line(result.error_message))

        hint = classify_failure_heuristic(result.output)
        self.report.classifier_hint = hint[0].value
        for number in range(1, self.max_attempts + 1):
            status, result = self.attempt(number, result, hint)
            if status is not None:
                return self.finish(status)
        return self.finish("not_healed")

    def attempt(
        self, number: int, result: RunResult, hint: Hint
    ) -> tuple[HealStatus | None, RunResult]:
        """One diagnose → repair → verify cycle; a status ends the heal."""
        started = time.monotonic()

        def record(outcome: AttemptOutcome, **fields: Any) -> None:
            elapsed = int((time.monotonic() - started) * 1000)
            self.report.attempts.append(
                Attempt(number=number, outcome=outcome, duration_ms=elapsed, **fields)
            )
            self.events.attempt(number, outcome)

        if self.cancel.is_set():
            record("cancelled")
            return "cancelled", result

        self.events.step("evidence", "active")
        evidence, warnings = gather_evidence(self.code, result, collect=self.collect)
        self.warnings.update(warnings)
        self.events.step("evidence", "done", _EVIDENCE_LABEL[evidence.source])

        self.events.step("diagnose", "active", f"Classifier hint: {hint[0].value}")
        try:
            analysis, exchange = plan_fix(
                code=self.code, evidence=evidence, hint=hint, model=self.model
            )
        except ModelError as exc:
            if self.cancel.is_set():  # ModelCancelled, or a call that failed meanwhile
                self.events.step("diagnose", "skipped", "Cancelled")
                record("cancelled", evidence=evidence)
                return "cancelled", result
            self.events.step("diagnose", "failed", str(exc))
            self.report.error_message = f"The model call failed: {exc}"
            return "error", result
        if self.cancel.is_set():
            self.events.step("diagnose", "skipped", "Cancelled")
            record("cancelled", evidence=evidence, analysis=analysis, exchange=exchange)
            return "cancelled", result
        if analysis is None:
            self.events.step("diagnose", "failed", "The reply did not match the schema")
            record("invalid_reply", evidence=evidence, exchange=exchange)
            return None, result
        self.events.step(
            "diagnose",
            "done",
            f"{analysis.failure_type.value} · confidence {analysis.confidence_score:.2f}",
        )
        if (
            analysis.failure_type == FailureType.POTENTIAL_APP_DEFECT
            and analysis.confidence_score >= APP_DEFECT_CONFIDENCE
        ):
            record(
                "app_defect", evidence=evidence, analysis=analysis, exchange=exchange
            )
            return "app_defect_suspected", result

        self.events.step("repair", "active")
        repaired = apply_fix(self.code, analysis.action_taken)
        if repaired.ast_unavailable:
            self.warnings.add("ast_unavailable")
        if repaired.method is None:
            self.events.step(
                "repair", "failed", "The code to replace is not in the file"
            )
            record(
                "not_applied", evidence=evidence, analysis=analysis, exchange=exchange
            )
            return None, result
        label = REPAIR_STRATEGY_LABELS[analysis.action_taken.repair_strategy]
        self.events.step("repair", "done", f"{label} ({repaired.method})")
        self.code = repaired.code
        self.spec.write_text(self.code, encoding="utf-8")

        self.events.step("verify", "active")
        rerun = self.run(
            self.spec,
            self.run_root / f"attempt-{number}",
            record_video=True,
            cancel=self.cancel,
        )
        fields: dict[str, Any] = {
            "evidence": evidence,
            "analysis": analysis,
            "exchange": exchange,
            "repair_method": repaired.method,
            "rerun": rerun,
        }
        if rerun.status == "cancelled":
            self.events.step("verify", "skipped", "Cancelled")
            record("cancelled", **fields)
            return "cancelled", rerun
        if rerun.passed:
            self.events.step("verify", "done", "Re-run passed")
            record("healed", **fields)
            return "healed", rerun
        self.events.step("verify", "failed", _first_line(rerun.error_message))
        record("rerun_failed", **fields)
        return None, rerun

    def finish(self, status: HealStatus, error_message: str = "") -> HealReport:
        if status != "healed":
            self._restore_spec()
        report = self.report
        report.status = status
        if error_message:
            report.error_message = error_message
        report.final_code = self.code
        report.diff = _unified_diff(self.original, self.code, self.spec.name)
        report.warnings = sorted(self.warnings)
        report.duration_ms = int((time.monotonic() - self.started) * 1000)
        save_report(report)
        self.events.done(status)
        return report


def _first_line(text: str) -> str:
    lines = text.strip().splitlines()
    return lines[0][:200] if lines else ""


def _unified_diff(before: str, after: str, name: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
        )
    )
