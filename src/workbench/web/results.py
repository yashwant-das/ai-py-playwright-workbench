"""What a finished run's page shows, derived from its saved report."""

from typing import Any, Literal

from workbench.models.generate import GenerateReport
from workbench.models.heal import Attempt, HealReport
from workbench.models.web import StepbarItem
from workbench.reports import Report, load_report
from workbench.web.views import (
    GENERATE_BADGES,
    HEAL_BADGES,
    diff_counts,
    diff_rows,
    format_duration,
    locators_in,
)

Tab = Literal["diff", "video", "log", "model"]
TAB_LABELS: dict[str, str] = {
    "diff": "Diff",
    "video": "Re-run video",
    "log": "Execution log",
    "model": "Model I/O",
}


def load_or_none(report_id: str) -> Report | None:
    """The saved report, or None for an unknown or malformed id."""
    try:
        return load_report(report_id)
    except (ValueError, FileNotFoundError):
        return None


def _model_failed(report: HealReport | GenerateReport) -> bool:
    return report.status == "error" and report.error_message.startswith(
        "The model call failed"
    )


def _model_failure_title(report: HealReport | GenerateReport) -> str:
    """A slow model is not an unreachable one: the server answered the connection."""
    if "did not answer within" in report.error_message:
        return "Model timed out"
    return "Model unreachable"


def _tabs(report: HealReport) -> list[str]:
    tabs = ["diff", "video"] if report.status == "healed" else []
    tabs.append("log")
    if report.attempts:
        tabs.append("model")
    return tabs


def _attempt(report: HealReport, number: int | None) -> Attempt | None:
    if not report.attempts:
        return None
    if number is not None:
        for attempt in report.attempts:
            if attempt.number == number:
                return attempt
    healed = [a for a in report.attempts if a.outcome == "healed"]
    return healed[-1] if healed else report.attempts[-1]


def _stepbar(report: HealReport, attempt: Attempt | None) -> list[StepbarItem]:
    run = report.initial_run
    items = [
        StepbarItem(
            title="Run",
            state="failed" if run is not None and run.status == "error" else "done",
            time=format_duration(run.duration_ms) if run else "",
        )
    ]
    if attempt is None:
        return items
    exchange = attempt.exchange
    items += [
        StepbarItem(title="Evidence", state="done" if attempt.evidence else "skipped"),
        StepbarItem(
            title="Diagnose",
            state="failed" if attempt.outcome == "invalid_reply" else "done",
            time=format_duration(exchange.provenance.latency_ms) if exchange else "",
        ),
        StepbarItem(
            title="Repair",
            state="done"
            if attempt.repair_method
            else ("failed" if attempt.outcome == "not_applied" else "skipped"),
        ),
        StepbarItem(
            title="Verify",
            state="done"
            if attempt.outcome == "healed"
            else ("failed" if attempt.rerun else "skipped"),
            time=format_duration(attempt.rerun.duration_ms) if attempt.rerun else "",
        ),
    ]
    return items


def heal_context(
    report: HealReport, *, attempt: int | None, tab: str
) -> dict[str, Any]:
    """Everything the heal result templates need."""
    tabs = _tabs(report)
    selected = _attempt(report, attempt)
    rows = (
        diff_rows(report.original_code, report.final_code)
        if report.status == "healed"
        else []
    )
    added, removed = diff_counts(rows)
    count = len(report.attempts)
    return {
        "report": report,
        "badge": HEAL_BADGES[report.status],
        "tabs": [(name, TAB_LABELS[name]) for name in tabs],
        "tab": tab if tab in tabs else tabs[0],
        "attempt": selected,
        "rows": rows,
        "added": added,
        "removed": removed,
        "demo": any(
            a.exchange is not None and a.exchange.provenance.provider == "demo"
            for a in report.attempts
        ),
        "meta": f"{count} attempt{'' if count == 1 else 's'} · {format_duration(report.duration_ms)}",
        "model_failed": _model_failed(report),
        "model_failure_title": _model_failure_title(report),
        "stepbar": _stepbar(report, selected),
    }


def generate_context(report: GenerateReport) -> dict[str, Any]:
    """Everything the generate result templates need."""
    exchange = report.exchange
    parts = []
    if exchange is not None:
        parts.append(f"Generated in {format_duration(exchange.provenance.latency_ms)}")
    if report.run is not None:
        parts.append(f"ran in {format_duration(report.run.duration_ms)}")
    return {
        "report": report,
        "badge": GENERATE_BADGES[report.status],
        "meta": " · ".join(parts),
        "locators": locators_in(report.code),
        "lines": len(report.code.splitlines()),
        "demo": exchange is not None and exchange.provenance.provider == "demo",
        "model_failed": _model_failed(report),
        "model_failure_title": _model_failure_title(report),
    }
