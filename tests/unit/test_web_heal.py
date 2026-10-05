"""The Heal page, starting a heal from a sample, an upload or a generated test, and refusals."""

import threading
from pathlib import Path
from typing import Any

import pytest

from tests.unit.web_support import heal_job, heal_report, make_client, started_run
from workbench.config import specs_dir, workspace_dir
from workbench.heal import HealRequest
from workbench.models.generate import GenerateReport
from workbench.models.settings import (
    DEFAULT_URLS,
    DEMO_MODEL,
    ConnectionStatus,
    ModelSettings,
)
from workbench.reports import save_report
from workbench.settings import save_settings

pytestmark = pytest.mark.usefixtures("web_workspace")


class FakeHeal:
    """Records heal() calls and runs the canned five-step job."""

    def __init__(self, gate: threading.Event | None = None) -> None:
        self.calls: list[HealRequest] = []
        self.gate = gate

    def __call__(
        self, request: HealRequest, *, model: Any, emit: Any = None, cancel: Any = None
    ):  # type: ignore[no-untyped-def]
        self.calls.append(request)
        return heal_job(heal_report(), gate=self.gate)(emit, cancel)


@pytest.fixture(autouse=True)
def demo_model(web_workspace: Path) -> None:
    """Saved inside the test workspace: the fixture must run after it is set up."""
    save_settings(ModelSettings(provider="demo", model=DEMO_MODEL))


def _start(client, fake: FakeHeal, **form: str):  # type: ignore[no-untyped-def]
    response = client.post("/heal", data={"max_attempts": "3", **form})
    run = client.app.state.runs.active()
    if run is not None:
        run.wait(5)
    return response


def test_heal_page_offers_both_samples_and_an_upload() -> None:
    html = make_client().get("/heal").text
    assert "Heal a failing test" in html
    assert 'value="sample:selector-drift"' in html and 'value="sample:app-bug"' in html
    assert "Selector drift" in html and "App bug" in html
    assert 'name="spec"' in html and 'name="max_attempts"' in html
    assert '<a href="/heal" aria-current="page">Heal</a>' in html
    assert (
        "disabled" not in html.split('value="sample:selector-drift"')[1].split(">")[0]
    )


def test_without_a_model_the_page_shows_the_unreachable_card_and_locks_buttons() -> (
    None
):
    def down(provider: str, base_url: str = "") -> ConnectionStatus:
        return ConnectionStatus(provider=provider, base_url=base_url, reachable=False)  # type: ignore[arg-type]

    save_settings(
        ModelSettings(
            provider="lm_studio", base_url=DEFAULT_URLS["lm_studio"], model="m"
        )
    )
    html = make_client(check_connection=down).get("/heal").text
    assert "Can't reach LM Studio" in html
    assert "Connect a model to run this." in html
    assert 'value="sample:selector-drift" disabled' in html


def test_missing_browsers_block_runs() -> None:
    html = make_client(browsers_ready=lambda: False).get("/heal").text
    assert "Playwright browsers aren't installed" in html
    assert "npx playwright install chromium" in html
    assert 'value="upload" disabled' in html


def test_a_sample_is_installed_and_healed() -> None:
    fake = FakeHeal()
    client = make_client(heal=fake)
    response = _start(client, fake, action="sample:selector-drift", max_attempts="2")
    assert response.status_code == 200
    started_run(client, response, "heal")
    assert response.text == ""
    request = fake.calls[0]
    assert request.spec_path == specs_dir() / "samples" / "contact-form.spec.ts"
    assert request.max_attempts == 2
    assert "http://127.0.0.1:7860/sample-site/" in request.spec_path.read_text(
        encoding="utf-8"
    )


def test_an_upload_is_copied_into_the_workspace() -> None:
    fake = FakeHeal()
    client = make_client(heal=fake)
    response = client.post(
        "/heal",
        data={"action": "upload", "max_attempts": "3"},
        files={
            "spec": ("My Test.spec.ts", b"test('x', async () => {});\n", "text/plain")
        },
    )
    assert response.status_code == 200
    started_run(client, response, "heal")
    client.app.state.runs.active() and client.app.state.runs.active().wait(5)  # type: ignore[attr-defined]
    path = specs_dir() / "uploads" / "my-test.spec.ts"
    assert fake.calls[0].spec_path == path
    assert path.read_text(encoding="utf-8") == "test('x', async () => {});\n"


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("notes.txt", b"x", "isn't a test file"),
        ("big.spec.ts", b"a" * (200 * 1024 + 1), "larger than 200 KB"),
        ("empty.spec.ts", b"  \n", "is empty"),
        ("latin.spec.ts", b"\xff\xfe\xfa", "isn't UTF-8"),
    ],
)
def test_bad_uploads_are_rejected_inline(
    name: str, content: bytes, message: str
) -> None:
    fake = FakeHeal()
    response = make_client(heal=fake).post(
        "/heal",
        data={"action": "upload", "max_attempts": "3"},
        files={"spec": (name, content, "application/octet-stream")},
    )
    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#upload-error"
    assert message in response.text
    assert fake.calls == []


def test_upload_without_a_file_is_refused() -> None:
    response = make_client().post(
        "/heal", data={"action": "upload", "max_attempts": "3"}
    )
    assert response.status_code == 422
    assert "Choose a .spec.ts file first." in response.text


def test_upload_name_cannot_escape_the_uploads_folder() -> None:
    fake = FakeHeal()
    client = make_client(heal=fake)
    client.post(
        "/heal",
        data={"action": "upload", "max_attempts": "3"},
        files={"spec": ("../../evil.spec.ts", b"test('x', () => {});", "text/plain")},
    )
    client.app.state.runs.active() and client.app.state.runs.active().wait(5)  # type: ignore[attr-defined]
    assert fake.calls[0].spec_path == specs_dir() / "uploads" / "evil.spec.ts"
    assert not (workspace_dir().parent / "evil.spec.ts").exists()


@pytest.mark.parametrize("attempts", ["0", "6", "x"])
def test_attempts_out_of_range_are_refused(attempts: str) -> None:
    response = make_client().post(
        "/heal", data={"action": "sample:selector-drift", "max_attempts": attempts}
    )
    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#attempts-error"


def test_unknown_sample_is_refused() -> None:
    response = make_client().post(
        "/heal", data={"action": "sample:nope", "max_attempts": "3"}
    )
    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#sample-error"
    assert "Unknown sample" in response.text


def test_second_start_is_refused_with_409() -> None:
    gate = threading.Event()
    client = make_client(heal=FakeHeal(gate))
    client.post("/heal", data={"action": "sample:selector-drift", "max_attempts": "3"})
    second = client.post(
        "/heal", data={"action": "sample:app-bug", "max_attempts": "3"}
    )
    assert second.status_code == 409
    assert second.headers["HX-Retarget"] == "#notice"
    assert "already in progress" in second.text
    gate.set()
    client.app.state.runs.active().wait(5)  # type: ignore[attr-defined]


def test_heal_page_resumes_the_active_run() -> None:
    gate = threading.Event()
    client = make_client(heal=FakeHeal(gate))
    started = client.post(
        "/heal", data={"action": "sample:selector-drift", "max_attempts": "3"}
    )
    run = started_run(client, started, "heal")
    html = client.get("/heal").text
    assert f'sse-connect="/runs/{run.id}/events"' in html
    assert 'value="sample:app-bug" disabled' in html
    assert 'value="sample:selector-drift" disabled' in html
    assert 'value="upload" disabled' in html
    gate.set()
    run.wait(5)


def test_a_failed_generated_test_can_be_healed() -> None:
    spec = specs_dir() / "a-user-can-send-the-contact-form.spec.ts"
    spec.write_text("test('x', () => {});", encoding="utf-8")
    report = GenerateReport(
        id="20261004-120000-generate-contact",
        url="http://127.0.0.1:7860/sample-site/",
        scenario="A user can send the contact form",
        status="failed",
        spec_name=spec.name,
    )
    save_report(report)
    fake = FakeHeal()
    client = make_client(heal=fake)
    started = _start(client, fake, action="generated", generated=report.id)
    started_run(client, started, "heal")
    assert fake.calls[0].spec_path == spec
    refused = client.post(
        "/heal", data={"action": "generated", "generated": "nope", "max_attempts": "3"}
    )
    assert refused.status_code == 422
    assert refused.headers["HX-Retarget"] == "#notice"
    assert "no longer exists" in refused.text
    spec.unlink()
    gone = client.post(
        "/heal",
        data={"action": "generated", "generated": report.id, "max_attempts": "3"},
    )
    assert gone.status_code == 422
    assert gone.headers["HX-Retarget"] == "#notice"


def test_a_model_that_went_down_shows_the_unreachable_card_instead_of_running() -> None:
    def down(provider: str, base_url: str = "") -> ConnectionStatus:
        return ConnectionStatus(provider=provider, base_url=base_url, reachable=False)  # type: ignore[arg-type]

    fake = FakeHeal()
    save_settings(
        ModelSettings(provider="ollama", base_url=DEFAULT_URLS["ollama"], model="m")
    )
    response = make_client(heal=fake, check_connection=down).post(
        "/heal", data={"action": "sample:selector-drift", "max_attempts": "3"}
    )
    assert "Can't reach Ollama" in response.text
    assert fake.calls == []


def test_a_run_that_finished_before_the_reload_is_still_shown() -> None:
    fake = FakeHeal()
    client = make_client(heal=fake)
    started = _start(client, fake, action="sample:selector-drift", max_attempts="3")
    run = started_run(client, started, "heal")
    assert run.finished
    html = client.get(f"/heal?run={run.id}").text
    assert f'sse-connect="/runs/{run.id}/events"' in html
    assert 'value="upload" disabled' not in html
    assert 'value="sample:app-bug" disabled' not in html


def test_an_unknown_run_id_shows_the_idle_page() -> None:
    html = make_client().get("/heal?run=nope").text
    assert "sse-connect=" not in html
