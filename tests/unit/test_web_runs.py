"""The SSE stream, cancel and the hand-over to the result page."""

import threading

import pytest

from tests.unit.web_support import heal_job, heal_report, make_client
from workbench.events import EventSink
from workbench.reports import load_report
from workbench.runs import Run
from workbench.web.sse import RunStream, sse_message

pytestmark = pytest.mark.usefixtures("web_workspace")


def _stream(client, run_id: str) -> str:  # type: ignore[no-untyped-def]
    with client.stream("GET", f"/runs/{run_id}/events") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        return response.read().decode()


def test_sse_message_puts_each_line_in_its_own_data_field() -> None:
    assert sse_message("log", "a\nb") == "event: log\ndata: a\ndata: b\n\n"
    assert sse_message("clock", "") == "event: clock\ndata: \n\n"


def test_stream_renders_steps_logs_and_the_hand_over() -> None:
    client = make_client()
    report = heal_report()
    run = client.app.state.runs.start("heal", "contact-form.spec.ts", heal_job(report))  # type: ignore[attr-defined]
    body = _stream(client, run.id)
    assert "event: step-run\n" in body
    assert "step--done" in body
    assert "event: log\n" in body and "[verify] Re-run passed" in body
    assert "Attempt 1: healed" in body
    assert f'hx-get="/runs/{run.id}/result"' in body.split("event: done", 1)[1]


def test_a_late_listener_gets_every_event_from_the_start() -> None:
    client = make_client()
    run = client.app.state.runs.start("heal", "x", heal_job(heal_report()))  # type: ignore[attr-defined]
    assert run.wait(5)
    assert _stream(client, run.id).count("event: step-") == 10


def test_result_redirects_to_the_report() -> None:
    client = make_client()
    report = heal_report()
    run = client.app.state.runs.start("heal", "x", heal_job(report))  # type: ignore[attr-defined]
    assert run.wait(5)
    response = client.get(f"/runs/{run.id}/result")
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == f"/reports/{report.id}"


def test_a_crashed_run_shows_its_error() -> None:
    client = make_client()

    def crashes(emit, cancel):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    run = client.app.state.runs.start("heal", "x", crashes)  # type: ignore[attr-defined]
    assert run.wait(5)
    assert "The run stopped unexpectedly" in _stream(client, run.id)
    result = client.get(f"/runs/{run.id}/result")
    assert "RuntimeError: boom" in result.text
    assert "HX-Redirect" not in result.headers


def test_cancel_sets_the_flag_the_job_sees() -> None:
    client = make_client()
    report = heal_report(status="cancelled")
    seen = threading.Event()

    def waits(emit, cancel):  # type: ignore[no-untyped-def]
        seen.set()
        cancel.wait(5)
        return heal_job(report)(emit, cancel)

    run = client.app.state.runs.start("heal", "x", waits)  # type: ignore[attr-defined]
    assert seen.wait(5)
    response = client.post(f"/runs/{run.id}/cancel")
    assert "Cancelling" in response.text and "disabled" in response.text
    assert run.wait(5)


def test_unknown_runs_are_404() -> None:
    client = make_client()
    assert client.get("/runs/nope/events").status_code == 404
    assert client.post("/runs/nope/cancel").status_code == 404
    assert client.get("/runs/nope/result").status_code == 404


def test_run_finishes_after_the_stream_is_dropped() -> None:
    client = make_client()
    gate = threading.Event()
    report = heal_report()
    run = client.app.state.runs.start("heal", "x", heal_job(report, gate=gate))  # type: ignore[attr-defined]
    with client.stream("GET", f"/runs/{run.id}/events") as response:
        next(response.iter_text())  # the first clock tick
    gate.set()
    assert run.wait(5)
    assert load_report(report.id).status == "healed"


def test_clock_says_the_model_is_still_thinking() -> None:
    run = Run("heal", "contact-form.spec.ts")
    EventSink("r", run.add).step("diagnose", "active", "Classifier hint: TIMEOUT")
    stream = RunStream(run)
    stream.pending()
    run.elapsed_ms = lambda: 45_000  # type: ignore[method-assign]
    assert "the model is still thinking" in stream.clock()
