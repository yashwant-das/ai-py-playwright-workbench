"""The Generate page, starting a generation, the result states, Run test and Heal this test."""

import re
import threading
from typing import Any

import pytest

from tests.unit import report_fixtures as fx
from tests.unit.web_support import make_client, started_run
from workbench.config import specs_dir
from workbench.events import EventSink
from workbench.generate import GenerateRequest
from workbench.models.generate import GenerateReport
from workbench.models.settings import DEMO_MODEL, ModelSettings
from workbench.reports import load_report, save_report
from workbench.settings import save_settings
from workbench.web.jobs import run_generated

pytestmark = pytest.mark.usefixtures("web_workspace")


@pytest.fixture(autouse=True)
def demo_model(web_workspace: Any) -> None:
    """Saved inside the test workspace: the fixture must run after it is set up."""
    save_settings(ModelSettings(provider="demo", model=DEMO_MODEL))


class FakeGenerate:
    def __init__(self) -> None:
        self.calls: list[GenerateRequest] = []

    def __call__(
        self,
        request: GenerateRequest,
        *,
        model: Any,
        emit: Any = None,
        cancel: Any = None,
    ) -> GenerateReport:
        self.calls.append(request)
        events = EventSink("g", emit)
        events.step("context", "active", request.url)
        events.step("context", "done", "18 locator candidates")
        events.step("model", "active")
        events.step("model", "done", "8 lines → a-user.spec.ts")
        report = fx.generate_not_run()
        save_report(report)
        return report


def _wait(client) -> None:  # type: ignore[no-untyped-def]
    run = client.app.state.runs.active()
    if run is not None:
        run.wait(5)


def test_generate_page_has_the_form_and_examples() -> None:
    html = make_client().get("/generate").text
    assert "Generate a test" in html
    assert (
        'name="url"' in html
        and 'name="scenario"' in html
        and 'name="run_after"' in html
    )
    assert "Your test will appear here" in html
    assert 'href="/generate?example=contact-form"' in html
    assert '<a href="/generate" aria-current="page">Generate</a>' in html


def test_an_example_fills_the_form_with_the_sample_site() -> None:
    html = make_client().get("/generate?example=contact-form").text
    assert 'value="http://127.0.0.1:7860/sample-site/"' in html
    assert "A user can send the contact form</textarea>" in html


def test_generation_starts_with_the_form_values() -> None:
    fake = FakeGenerate()
    client = make_client(generate=fake)
    response = client.post(
        "/generate",
        data={
            "url": "http://127.0.0.1:7860/sample-site/",
            "scenario": "A user can send the contact form",
        },
    )
    # Reloading the page, not swapping #main, keeps the start button locked.
    assert response.status_code == 200
    started_run(client, response, "generate")
    _wait(client)
    assert fake.calls[0] == GenerateRequest(
        url="http://127.0.0.1:7860/sample-site/",
        scenario="A user can send the contact form",
        run_after=False,
    )


@pytest.mark.parametrize(
    ("form", "target", "message"),
    [
        (
            {"url": "example.com/login", "scenario": "x"},
            "#url-error",
            "Enter a full URL, starting with http:// or https://",
        ),
        (
            {"url": "http://x/", "scenario": "   "},
            "#scenario-error",
            "Description cannot be empty",
        ),
    ],
)
def test_bad_input_is_refused_inline(
    form: dict[str, str], target: str, message: str
) -> None:
    fake = FakeGenerate()
    response = make_client(generate=fake).post("/generate", data=form)
    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == target
    assert message in response.text
    assert fake.calls == []


def test_passed_result_shows_code_context_and_run() -> None:
    report = fx.generate_passed()
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    assert "pill--pass" in html and "Passed" in html
    assert "a-user-can-send-the-contact-form.spec.ts" in html
    assert '<span class="tok-fn">getByRole</span>' in html
    assert "Page context used" in html and ">42<" in html and ">18<" in html
    assert "getByLabel(&#39;Name&#39;)" in html
    assert "Passed in Chromium · 2.2s" in html
    assert f"/reports/{report.id}/spec" in html


def test_failed_result_offers_heal_this_test() -> None:
    report = fx.generate_failed()
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    assert "Run failed" in html
    assert 'name="action" value="generated"' in html
    assert f'name="generated" value="{report.id}"' in html
    assert "Heal this test" in html


def test_not_run_result_offers_run_test() -> None:
    report = fx.generate_not_run()
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    assert "Not run" in html and "Run test" in html
    assert 'hx-post="/generate/run"' in html


def test_timeout_result_says_model_timed_out() -> None:
    report = fx.generate_error()
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    assert "Model timed out" in html and "Model unreachable" not in html
    assert "did not answer within 300 seconds" in html


def test_error_result_says_model_unreachable() -> None:
    report = fx.generate_error().model_copy(
        update={
            "error_message": "The model call failed: Could not reach Ollama at http://localhost:11434/v1."
        }
    )
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    assert "Model unreachable" in html and "Model timed out" not in html


def test_generated_code_lines_have_no_whitespace_between_them() -> None:
    report = fx.generate_passed()
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    count = html.count('<span class="code__line')
    assert count > 3
    assert len(re.findall(r'</span></span><span class="code__line', html)) == count - 1


def test_run_test_runs_the_saved_spec_and_updates_the_report() -> None:
    report = fx.generate_not_run()
    save_report(report)
    spec = specs_dir() / report.spec_name
    spec.write_text(report.code, encoding="utf-8")
    seen: list[Any] = []

    def fake_run(path: Any, **kwargs: Any) -> Any:
        seen.append(path)
        return fx.run_result("passed", duration_ms=2000)

    client = make_client(run_test=fake_run)
    response = client.post("/generate/run", data={"report": report.id})
    assert response.status_code == 200
    started_run(client, response, "generate")
    _wait(client)
    assert seen == [spec]
    updated = load_report(report.id)
    assert isinstance(updated, GenerateReport)
    assert updated.status == "passed" and updated.run is not None


def test_run_test_refuses_an_unknown_report_in_the_notice() -> None:
    response = make_client().post("/generate/run", data={"report": "nope"})
    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#notice"
    assert "No such generated test" in response.text


def test_run_test_refuses_when_the_spec_file_is_gone() -> None:
    report = fx.generate_not_run()
    save_report(report)
    response = make_client().post("/generate/run", data={"report": report.id})
    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#notice"
    assert "The generated spec file is gone" in response.text


def test_generate_page_resumes_an_active_generation() -> None:
    gate = threading.Event()

    def slow(request: GenerateRequest, **kwargs: Any) -> GenerateReport:
        gate.wait(5)
        return FakeGenerate()(request, **kwargs)

    client = make_client(generate=slow)
    started = client.post(
        "/generate", data={"url": "http://x/", "scenario": "s", "run_after": "1"}
    )
    run = started_run(client, started, "generate")
    html = client.get("/generate").text
    assert f'sse-connect="/runs/{run.id}/events"' in html
    assert 'class="log__body" tabindex="0" role="log"' in html
    button = html.split("Generate test</button>")[0].rsplit("<button", 1)[1]
    assert "disabled" in button
    gate.set()
    run.wait(5)


def _run_job(result: Any) -> GenerateReport:
    return run_generated(
        fx.generate_not_run(),
        run_test=lambda path, **kwargs: result,
        emit=lambda event: None,
        cancel=threading.Event(),
    )


def test_run_generated_records_a_failure_but_not_a_cancellation() -> None:
    failed = _run_job(fx.run_result("failed"))
    assert failed.status == "failed" and failed.run is not None
    assert load_report(failed.id) == failed
    cancelled = _run_job(fx.run_result("cancelled", error_message=""))
    assert cancelled.status == "not_run" and cancelled.run is None


def test_a_run_that_finished_before_the_reload_is_still_shown() -> None:
    fake = FakeGenerate()
    client = make_client(generate=fake)
    started = client.post(
        "/generate", data={"url": "http://x/", "scenario": "s", "run_after": "1"}
    )
    run = started_run(client, started, "generate")
    run.wait(5)
    html = client.get(f"/generate?run={run.id}").text
    assert f'sse-connect="/runs/{run.id}/events"' in html
    button = html.split("Generate test</button>")[0].rsplit("<button", 1)[1]
    assert "disabled" not in button


def test_a_run_of_the_other_page_or_an_unknown_run_is_ignored() -> None:
    fake = FakeGenerate()
    client = make_client(generate=fake)
    started = client.post("/generate", data={"url": "http://x/", "scenario": "s"})
    run = started_run(client, started, "generate")
    run.wait(5)
    assert "sse-connect=" not in client.get("/generate?run=nope").text
    assert "sse-connect=" not in client.get(f"/heal?run={run.id}").text
    assert "Your test will appear here" in client.get("/generate?run=nope").text


def test_cancelling_run_test_leaves_the_report_runnable() -> None:
    report = fx.generate_not_run()
    save_report(report)
    (specs_dir() / report.spec_name).write_text(report.code, encoding="utf-8")
    started = threading.Event()

    def slow_run(path: Any, *, cancel: threading.Event, **kwargs: Any) -> Any:
        started.set()
        cancel.wait(5)
        return fx.run_result("cancelled", error_message="")

    client = make_client(run_test=slow_run)
    response = client.post("/generate/run", data={"report": report.id})
    run = started_run(client, response, "generate")
    assert started.wait(5)
    assert client.post(f"/runs/{run.id}/cancel").status_code == 200
    assert run.wait(5)
    saved = load_report(report.id)
    assert isinstance(saved, GenerateReport)
    assert saved == report
    html = client.get(f"/reports/{report.id}").text
    assert "Not run" in html and 'hx-post="/generate/run"' in html
    assert "stopped before it finished" not in html


def test_the_idle_page_links_the_last_finished_generation() -> None:
    fake = FakeGenerate()
    client = make_client(generate=fake)
    assert "Last run" not in client.get("/generate").text
    started = client.post(
        "/generate",
        data={
            "url": "http://127.0.0.1:7860/sample-site/",
            "scenario": "A user can send the contact form",
        },
    )
    run = started_run(client, started, "generate")
    assert run.wait(5) and run.report_id
    html = client.get("/generate").text
    assert "Your test will appear here" in html
    assert "Last run: A user can send the contact form" in html
    assert f'<a href="/reports/{run.report_id}">View result</a>' in html
    assert "Last run" not in client.get("/heal").text


MODEL_FAILURES = [
    (
        "Could not reach Ollama at http://localhost:11434/v1. Is it running?",
        "Model unreachable",
    ),
    (
        "Ollama at http://localhost:11434/v1 did not answer within 300 seconds.",
        "Model timed out",
    ),
    (
        "Demo only covers the bundled samples. Choose LM Studio or Ollama in the model menu to generate other tests.",
        "The model call failed",
    ),
    (
        "Ollama at http://localhost:11434/v1 has no model named 'x'. Load it or pick another model.",
        "The model call failed",
    ),
    (
        "LM Studio at http://localhost:1234/v1 answered HTTP 400: context length exceeded",
        "The model call failed",
    ),
    (
        "LM Studio at http://localhost:1234/v1 did not return a chat completion.",
        "The model call failed",
    ),
]


@pytest.mark.parametrize(("message", "title"), MODEL_FAILURES)
def test_a_model_failure_is_named_for_what_happened(message: str, title: str) -> None:
    report = fx.generate_error().model_copy(
        update={"error_message": f"The model call failed: {message}"}
    )
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    titles = re.findall(r'<p class="banner__title">([^<]*)</p>', html)
    assert titles == [title]
    assert message.split(".")[0].replace("'", "&#39;") in html


def test_demo_is_only_offered_the_example_it_can_answer() -> None:
    html = make_client().get("/generate").text
    assert 'href="/generate?example=contact-form"' in html
    assert "example=checkout" not in html and "Checkout" not in html
    prefilled = make_client().get("/generate?example=checkout").text
    assert "checkout.html" not in prefilled


def test_a_real_model_is_offered_both_examples() -> None:
    save_settings(
        ModelSettings(
            provider="ollama", base_url="http://localhost:11434/v1", model="m"
        )
    )
    html = make_client().get("/generate").text
    assert 'href="/generate?example=contact-form"' in html
    assert 'href="/generate?example=checkout"' in html
    prefilled = make_client().get("/generate?example=checkout").text
    assert 'value="http://127.0.0.1:7860/sample-site/checkout.html"' in prefilled


def test_every_generate_result_offers_the_report_download() -> None:
    for build in (
        fx.generate_passed,
        fx.generate_failed,
        fx.generate_not_run,
        fx.generate_error,
    ):
        report = build()
        save_report(report)
        html = make_client().get(f"/reports/{report.id}").text
        assert f'href="/reports/{report.id}.json" download>Download report</a>' in html
    passed = fx.generate_passed()
    save_report(passed)
    assert "Download spec" in make_client().get(f"/reports/{passed.id}").text


def test_generate_explains_snapshot_scope_and_public_example_requirements() -> None:
    html = make_client().get("/generate").text
    assert "starting page once" in html
    assert "Later pages and controls revealed after interaction" in html
    assert "Locked-out account" in html
    assert "Customer invoice data" in html
    assert "Checkbox preferences" in html
    assert "Local model required" in html
    assert 'href="/generate?example=locked-account"' not in html


@pytest.mark.parametrize(
    ("key", "url", "scenario"),
    [
        (
            "locked-account",
            "https://www.saucedemo.com/",
            "Attempt to sign in with username locked_out_user and password secret_sauce.",
        ),
        (
            "customer-data",
            "https://the-internet.herokuapp.com/tables",
            "In the first data table, find the row for Jason Doe.",
        ),
        (
            "checkboxes",
            "https://the-internet.herokuapp.com/checkboxes",
            "Check both checkboxes and verify both are checked.",
        ),
    ],
)
def test_public_examples_prefill_without_starting_a_run(
    key: str, url: str, scenario: str
) -> None:
    save_settings(
        ModelSettings(
            provider="ollama", base_url="http://localhost:11434/v1", model="m"
        )
    )
    client = make_client()
    html = client.get(f"/generate?example={key}").text
    assert f'value="{url}"' in html
    assert scenario in html
    assert client.app.state.runs.active() is None


def test_demo_cannot_prefill_a_public_example() -> None:
    html = make_client().get("/generate?example=locked-account").text
    assert 'value="https://www.saucedemo.com/"' not in html
