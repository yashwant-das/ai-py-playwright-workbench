"""Small jobs the web app runs that are not a whole pipeline."""

import threading
from collections.abc import Callable

from workbench.config import specs_dir
from workbench.events import Emit, EventSink
from workbench.models.events import StepState
from workbench.models.generate import GenerateReport, GenerateStatus
from workbench.models.shared import RunResult
from workbench.reports import save_report


def run_generated(
    report: GenerateReport,
    *,
    run_test: Callable[..., RunResult],
    emit: Emit,
    cancel: threading.Event,
) -> GenerateReport:
    """Run a generated spec that was not run, and record the result on its report."""
    events = EventSink(report.id, emit)
    spec = specs_dir() / report.spec_name
    events.step("execute", "active", f"npx playwright test {spec.name}")
    result = run_test(spec, cancel=cancel)
    status: GenerateStatus
    state: StepState
    if result.passed:
        status, state, detail = "passed", "done", "Passed"
    elif result.status == "cancelled":
        status, state, detail = "cancelled", "skipped", "Cancelled"
    else:
        first = result.error_message.strip().splitlines()
        status, state, detail = "failed", "failed", first[0] if first else result.status
    events.step("execute", state, detail)
    updated = report.model_copy(update={"run": result, "status": status})
    save_report(updated)
    events.done(status)
    return updated
