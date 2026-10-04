"""heal(): every outcome, with a fake runner, fake model and fake browser."""

import json
import threading
from pathlib import Path
from typing import Any

import pytest

from workbench.heal import HealRequest, heal, repair
from workbench.llm.chat import ChatReply, ModelError
from workbench.models.artifacts import ContextSnapshot
from workbench.models.events import RunEvent
from workbench.models.shared import RunResult
from workbench.reports import load_report

BROKEN = (
    'import { test } from "@playwright/test";\n\n'
    'test("submit", async ({ page }) => {\n'
    '  await page.goto("http://127.0.0.1:4173/");\n'
    '  await page.locator("#submit-btn").click();\n'
    "});\n"
)
SNAPSHOT_FILE = '# Page snapshot\n\n```yaml\n- button "Submit" [ref=e3]\n```\n'


def reply(
    failure_type: str = "LOCATOR_DRIFT",
    confidence: float = 0.9,
    original: str = 'page.locator("#submit-btn")',
    fixed: str = 'page.getByRole("button", { name: "Submit" })',
    strategy: str = "string_replace",
) -> str:
    return json.dumps(
        {
            "failure_type": failure_type,
            "failure_summary": "s",
            "hypothesis": "h",
            "confidence_score": confidence,
            "reasoning_steps": ["r"],
            "action_taken": {
                "original_code": original,
                "fixed_code": fixed,
                "description": "d",
                "repair_strategy": strategy,
            },
        }
    )


class FakeModel:
    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def chat(self, messages, *, json_schema=None, temperature=0.1) -> ChatReply:
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return ChatReply(content=outcome, model="m", provider="fake")


class FakeRunner:
    def __init__(self, tmp_path: Path, *statuses: str, on_call: Any = None) -> None:
        self.statuses = list(statuses)
        self.calls: list[dict[str, Any]] = []
        self.context = tmp_path / "error-context.md"
        self.context.write_text(SNAPSHOT_FILE, encoding="utf-8")
        self.on_call = on_call

    def __call__(
        self,
        spec: Path,
        run_dir: Path | None = None,
        *,
        record_video: bool = False,
        cancel: Any = None,
    ) -> RunResult:
        self.calls.append(
            {
                "spec": spec,
                "run_dir": run_dir,
                "record_video": record_video,
                "code": spec.read_text(),
            }
        )
        if self.on_call:
            self.on_call(len(self.calls))
        status = self.statuses.pop(0)
        if status == "passed":
            return RunResult(
                status="passed", video_path="/v.webm" if record_video else None
            )
        if status in ("cancelled", "error"):
            return RunResult(status=status, error_message=f"{status}!")
        return RunResult(
            status="failed",
            error_message="TimeoutError: waiting for locator('#submit-btn')",
            error_context_path=str(self.context),
        )


def no_page(url: str) -> ContextSnapshot:
    raise AssertionError("evidence should come from error-context.md")


@pytest.fixture
def spec(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("WORKBENCH_WORKSPACE", str(tmp_path / "ws"))
    path = tmp_path / "contact.spec.ts"
    path.write_text(BROKEN, encoding="utf-8")
    return path


def run_heal(spec: Path, model: FakeModel, runner: FakeRunner, **kwargs: Any):
    kwargs.setdefault("browsers_ready", lambda: True)
    return heal(
        HealRequest(spec_path=spec, max_attempts=kwargs.pop("max_attempts", 3)),
        model=model,
        run=runner,
        collect=no_page,
        **kwargs,
    )


def test_passing_spec_needs_no_healing(spec: Path, tmp_path: Path) -> None:
    model = FakeModel()
    report = run_heal(spec, model, FakeRunner(tmp_path, "passed"))
    assert report.status == "nothing_to_heal"
    assert model.calls == 0
    assert spec.read_text() == BROKEN
    assert load_report(report.id).status == "nothing_to_heal"


def test_heals_on_the_first_attempt(spec: Path, tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path, "failed", "passed")
    report = run_heal(spec, FakeModel(reply()), runner)

    assert report.status == "healed"
    assert [a.outcome for a in report.attempts] == ["healed"]
    assert 'getByRole("button", { name: "Submit" })' in spec.read_text()
    assert report.final_code == spec.read_text()
    assert '-  await page.locator("#submit-btn").click();' in report.diff
    assert runner.calls[1]["record_video"] is True
    assert report.attempts[0].rerun.video_path == "/v.webm"  # type: ignore[union-attr]
    assert report.attempts[0].evidence.source == "error_context"  # type: ignore[union-attr]
    assert report.attempts[0].repair_method == "text"
    assert report.classifier_hint == "TIMEOUT"


def test_fix_that_cannot_be_applied_is_retried(spec: Path, tmp_path: Path) -> None:
    model = FakeModel(reply(original="page.locator('#nope')"), reply())
    report = run_heal(spec, model, FakeRunner(tmp_path, "failed", "passed"))
    assert [a.outcome for a in report.attempts] == ["not_applied", "healed"]


def test_invalid_reply_is_retried(spec: Path, tmp_path: Path) -> None:
    report = run_heal(
        spec, FakeModel("not json", reply()), FakeRunner(tmp_path, "failed", "passed")
    )
    assert [a.outcome for a in report.attempts] == ["invalid_reply", "healed"]
    assert report.attempts[0].exchange.valid is False  # type: ignore[union-attr]


def test_confident_app_defect_stops_without_editing(spec: Path, tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path, "failed")
    report = run_heal(
        spec, FakeModel(reply("POTENTIAL_APP_DEFECT", 0.9, "", "")), runner
    )
    assert report.status == "app_defect_suspected"
    assert [a.outcome for a in report.attempts] == ["app_defect"]
    assert len(runner.calls) == 1
    assert spec.read_text() == BROKEN


def test_unsure_app_defect_still_tries_the_fix(spec: Path, tmp_path: Path) -> None:
    report = run_heal(
        spec,
        FakeModel(reply("POTENTIAL_APP_DEFECT", 0.5)),
        FakeRunner(tmp_path, "failed", "passed"),
    )
    assert report.status == "healed"


def test_exhausted_attempts_restore_the_spec(spec: Path, tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path, "failed", "failed", "failed")
    report = run_heal(
        spec,
        FakeModel(
            reply(),
            reply(
                original='page.getByRole("button", { name: "Submit" })',
                fixed="page.getByText('Submit')",
            ),
        ),
        runner,
        max_attempts=2,
    )
    assert report.status == "not_healed"
    assert [a.outcome for a in report.attempts] == ["rerun_failed", "rerun_failed"]
    assert spec.read_text() == BROKEN
    assert report.final_code == BROKEN and report.diff == ""


def test_model_error_after_a_failed_attempt_restores_the_spec(
    spec: Path, tmp_path: Path
) -> None:
    runner = FakeRunner(tmp_path, "failed", "failed")
    report = run_heal(
        spec, FakeModel(reply(), ModelError("connection refused")), runner
    )
    assert report.status == "error"
    assert "connection refused" in report.error_message
    assert spec.read_text() == BROKEN


def test_cancel_during_verification_restores_the_spec(
    spec: Path, tmp_path: Path
) -> None:
    report = run_heal(
        spec, FakeModel(reply()), FakeRunner(tmp_path, "failed", "cancelled")
    )
    assert report.status == "cancelled"
    assert [a.outcome for a in report.attempts] == ["cancelled"]
    assert spec.read_text() == BROKEN


def test_cancel_before_an_attempt(spec: Path, tmp_path: Path) -> None:
    cancel = threading.Event()
    runner = FakeRunner(tmp_path, "failed", on_call=lambda n: cancel.set())
    report = run_heal(spec, FakeModel(), runner, cancel=cancel)
    assert report.status == "cancelled"
    assert spec.read_text() == BROKEN


def test_missing_browsers_stop_before_running(spec: Path, tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path)
    report = run_heal(spec, FakeModel(), runner, browsers_ready=lambda: False)
    assert report.status == "error"
    assert report.warnings == ["playwright_browsers_missing"]
    assert runner.calls == []


def test_runner_error_is_reported(spec: Path, tmp_path: Path) -> None:
    report = run_heal(spec, FakeModel(), FakeRunner(tmp_path, "error"))
    assert report.status == "error"
    assert report.error_message == "error!"


def test_missing_node_is_a_warning(
    spec: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repair, "node_available", lambda: False)
    report = run_heal(
        spec,
        FakeModel(reply(strategy="selector_replace")),
        FakeRunner(tmp_path, "failed", "passed"),
    )
    assert report.status == "healed"
    assert report.warnings == ["ast_unavailable"]


def test_events_describe_the_run(spec: Path, tmp_path: Path) -> None:
    events: list[RunEvent] = []
    run_heal(
        spec,
        FakeModel(reply()),
        FakeRunner(tmp_path, "failed", "passed"),
        emit=events.append,
    )
    steps = [(e.step, e.state) for e in events if e.kind == "step"]
    assert steps == [
        ("run", "active"),
        ("run", "done"),
        ("evidence", "active"),
        ("evidence", "done"),
        ("diagnose", "active"),
        ("diagnose", "done"),
        ("repair", "active"),
        ("repair", "done"),
        ("verify", "active"),
        ("verify", "done"),
    ]
    assert events[-1].kind == "done" and events[-1].detail == "healed"
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
