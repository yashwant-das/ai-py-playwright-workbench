"""One run at a time, in a background thread, with its events kept for late listeners."""

import threading

import pytest

from workbench.events import EventSink
from workbench.models.generate import GenerateReport
from workbench.runs import Run, RunInProgress, RunRegistry


def _report(report_id: str = "20261004-120000-generate-x") -> GenerateReport:
    return GenerateReport(id=report_id, url="http://x/", scenario="s", status="passed")


def _quick_job(emit, cancel):  # type: ignore[no-untyped-def]
    sink = EventSink("r", emit)
    sink.step("context", "active")
    sink.step("context", "done", "3 locator candidates")
    return _report()


def test_a_run_records_its_events_and_report() -> None:
    registry = RunRegistry()
    run = registry.start(
        "generate",
        "contact",
        _quick_job,
        model_label="qwen · Ollama",
        steps=("context",),
    )
    assert run.wait(5)
    assert run.finished
    assert run.report_id == "20261004-120000-generate-x"
    assert [e.state for e in run.events_after(0)] == ["active", "done"]
    assert [e.state for e in run.events_after(1)] == ["done"]
    assert run.model_label == "qwen · Ollama"
    assert run.steps == ("context",)
    assert registry.get(run.id) is run
    assert registry.active() is None


def test_only_one_run_at_a_time() -> None:
    registry = RunRegistry()
    release = threading.Event()

    def slow(emit, cancel):  # type: ignore[no-untyped-def]
        release.wait(5)
        return _report()

    first = registry.start("heal", "a.spec.ts", slow)
    with pytest.raises(RunInProgress) as refused:
        registry.start("heal", "b.spec.ts", _quick_job)
    assert refused.value.active is first
    assert registry.active() is first
    release.set()
    assert first.wait(5)
    second = registry.start("heal", "b.spec.ts", _quick_job)
    assert second.wait(5)


def test_cancel_reaches_the_job() -> None:
    registry = RunRegistry()
    seen = threading.Event()

    def waits_for_cancel(emit, cancel):  # type: ignore[no-untyped-def]
        seen.set()
        cancel.wait(5)
        return _report()

    run = registry.start("heal", "a.spec.ts", waits_for_cancel)
    assert seen.wait(5)
    run.cancel.set()
    assert run.wait(5)


def test_a_crashing_job_finishes_with_an_error_and_frees_the_slot() -> None:
    registry = RunRegistry()

    def crashes(emit, cancel):  # type: ignore[no-untyped-def]
        raise OSError("disk full")

    run = registry.start("heal", "a.spec.ts", crashes)
    assert run.wait(5)
    assert run.report_id is None
    assert run.error == "OSError: disk full"
    assert registry.active() is None


def test_unknown_runs_are_none_and_old_runs_are_dropped() -> None:
    registry = RunRegistry(keep=2)
    runs: list[Run] = []
    for _ in range(3):
        run = registry.start("generate", "x", _quick_job)
        assert run.wait(5)
        runs.append(run)
    assert registry.get("nope") is None
    assert registry.get(runs[0].id) is None
    assert registry.get(runs[2].id) is runs[2]
