"""generate(): every outcome, with a fake browser, model and runner."""

import threading
from pathlib import Path
from typing import Any

import pytest

from workbench.generate import GenerateRequest, generate
from workbench.llm.chat import ChatReply, ModelError
from workbench.models.artifacts import ContextSnapshot
from workbench.models.events import RunEvent
from workbench.models.shared import RunResult
from workbench.reports import load_report

URL = "http://127.0.0.1:4173/"
SPEC = (
    '```typescript\nimport { test, expect } from "@playwright/test";\n\n'
    'test("submit", async ({ page }) => {\n  await page.goto("http://127.0.0.1:4173/");\n});\n```'
)


class FakeModel:
    def __init__(self, outcome: Any = SPEC) -> None:
        self.outcome = outcome
        self.messages: list[Any] = []

    def chat(self, messages, *, json_schema=None, temperature=0.1) -> ChatReply:
        self.messages = messages
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return ChatReply(content=self.outcome, model="m", provider="fake")


def page(url: str) -> ContextSnapshot:
    return ContextSnapshot(
        url=url,
        aria_snapshot='- textbox "Name" [ref=e2]\n- button "Submit" [ref=e3]',
        locator_candidates=["getByRole('button', { name: 'Submit' })"],
    )


def runner(status: str = "passed", message: str = "boom"):
    calls: list[Path] = []

    def run(spec: Path, run_dir: Path | None = None, **_: Any) -> RunResult:
        calls.append(spec)
        return RunResult(
            status=status, error_message="" if status == "passed" else message
        )

    return run, calls


@pytest.fixture(autouse=True)
def _workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WORKBENCH_WORKSPACE", str(tmp_path))


def go(
    model: FakeModel, run: Any, request: GenerateRequest | None = None, **kwargs: Any
):
    kwargs.setdefault("browsers_ready", lambda: True)
    kwargs.setdefault("collect", page)
    request = request or GenerateRequest(
        url=URL, scenario="A visitor submits the contact form"
    )
    return generate(request, model=model, run=run, **kwargs)


def test_generates_writes_and_runs(tmp_path: Path) -> None:
    run, calls = runner("passed")
    model = FakeModel()
    report = go(model, run)

    assert report.status == "passed"
    spec = tmp_path / "specs" / "a-visitor-submits-the-contact-form.spec.ts"
    assert report.spec_name == spec.name
    assert calls == [spec]
    assert spec.read_text().startswith(
        'import { test, expect } from "@playwright/test";'
    )
    assert "```" not in report.code
    assert [s.name for s in report.exchange.sections] == [
        "Target URL",
        "Scenario",
        "Page snapshot",
        "Locator candidates",
    ]  # type: ignore[union-attr]
    assert report.exchange.provenance.prompt_version == "3"  # type: ignore[union-attr]
    assert report.context.locator_candidates == [
        "getByRole('button', { name: 'Submit' })"
    ]  # type: ignore[union-attr]
    assert "## Page snapshot\n- textbox" in model.messages[1]["content"]
    assert load_report(report.id).status == "passed"


def test_failed_run_is_reported() -> None:
    run, _ = runner("failed")
    assert go(FakeModel(), run).status == "failed"


def test_not_run_when_asked() -> None:
    run, calls = runner()
    report = go(
        FakeModel(), run, GenerateRequest(url=URL, scenario="login", run_after=False)
    )
    assert report.status == "not_run"
    assert calls == []


def test_same_scenario_twice_gets_a_new_file(tmp_path: Path) -> None:
    run, _ = runner()
    first, second = go(FakeModel(), run), go(FakeModel(), run)
    assert first.spec_name != second.spec_name
    assert second.spec_name == "a-visitor-submits-the-contact-form-2.spec.ts"


def test_invalid_url_is_rejected_before_any_work() -> None:
    run, calls = runner()

    def no_page(url: str) -> ContextSnapshot:
        raise AssertionError("should not load")

    report = go(
        FakeModel(),
        run,
        GenerateRequest(url="example.com", scenario="x"),
        collect=no_page,
    )
    assert report.status == "error"
    assert "Invalid URL" in report.error_message
    assert calls == []


def test_unreachable_page_is_reported() -> None:
    run, _ = runner()
    report = go(FakeModel(), run, collect=lambda url: ContextSnapshot(url=url))
    assert report.status == "error"
    assert "Could not load" in report.error_message


def test_reply_without_code_writes_nothing(tmp_path: Path) -> None:
    run, calls = runner()
    report = go(FakeModel("   "), run)
    assert report.status == "error"
    assert report.exchange is not None and not report.exchange.valid
    assert not any((tmp_path / "specs").glob("*.spec.ts"))
    assert calls == []


def test_model_error_is_reported() -> None:
    run, _ = runner()
    report = go(FakeModel(ModelError("refused")), run)
    assert report.status == "error"
    assert "refused" in report.error_message


def test_missing_browsers_stop_early() -> None:
    run, calls = runner()
    report = go(FakeModel(), run, browsers_ready=lambda: False)
    assert report.status == "error"
    assert report.warnings == ["playwright_browsers_missing"]
    assert calls == []


class CancellingModel(FakeModel):
    """Cancels while the (slow) model call is still in flight."""

    def __init__(self, cancel: threading.Event) -> None:
        super().__init__()
        self.cancel = cancel

    def chat(self, messages, **kwargs: Any) -> ChatReply:
        self.cancel.set()
        return super().chat(messages, **kwargs)


def test_cancel_during_the_model_call_writes_and_runs_nothing(tmp_path: Path) -> None:
    run, calls = runner()
    cancel = threading.Event()
    events: list[RunEvent] = []
    report = go(CancellingModel(cancel), run, cancel=cancel, emit=events.append)
    assert report.status == "cancelled"
    assert calls == []
    assert not any((tmp_path / "specs").glob("*.spec.ts"))
    assert report.spec_name == "" and report.code == ""
    model_steps = [(e.state, e.detail) for e in events if e.step == "model"]
    assert model_steps == [("active", ""), ("skipped", "Cancelled")]


def test_cancel_before_the_model_call_never_calls_the_model() -> None:
    run, calls = runner()
    cancel = threading.Event()
    cancel.set()
    model = FakeModel()
    report = go(model, run, cancel=cancel)
    assert report.status == "cancelled"
    assert model.messages == []
    assert calls == []


def test_cancelled_run_ends_its_step_as_skipped() -> None:
    events: list[RunEvent] = []
    run, _ = runner("cancelled")
    report = go(FakeModel(), run, emit=events.append)
    assert report.status == "cancelled"
    execute = [(e.state, e.detail) for e in events if e.step == "execute"]
    assert execute[-1] == ("skipped", "Cancelled")
    assert events[-1].kind == "done" and events[-1].detail == "cancelled"


def test_step_failure_details_use_the_first_line_of_the_error() -> None:
    events: list[RunEvent] = []
    run, _ = runner("error", "spawn failed\nlong stderr\nmore stderr")
    report = go(FakeModel(), run, emit=events.append)
    assert report.status == "error"
    assert report.error_message == "spawn failed\nlong stderr\nmore stderr"
    execute = [(e.state, e.detail) for e in events if e.step == "execute"]
    assert execute[-1] == ("failed", "spawn failed")

    events.clear()
    run, _ = runner("failed", "Error: expected visible\nCall log: ...")
    go(FakeModel(), run, emit=events.append)
    execute = [(e.state, e.detail) for e in events if e.step == "execute"]
    assert execute[-1] == ("failed", "Error: expected visible")


def test_model_error_headline_says_the_call_failed() -> None:
    events: list[RunEvent] = []
    run, _ = runner()
    report = go(FakeModel(ModelError("refused\ndetails")), run, emit=events.append)
    assert report.error_message == "The model call failed: refused\ndetails"
    failed = [e for e in events if e.step == "model" and e.state == "failed"]
    assert [e.detail for e in failed] == ["refused"]


def test_events_describe_the_run() -> None:
    events: list[RunEvent] = []
    run, _ = runner()
    go(FakeModel(), run, emit=events.append)
    steps = [(e.step, e.state) for e in events if e.kind == "step"]
    assert steps == [
        ("context", "active"),
        ("context", "done"),
        ("model", "active"),
        ("model", "done"),
        ("execute", "active"),
        ("execute", "done"),
    ]
    assert events[-1].detail == "passed"
