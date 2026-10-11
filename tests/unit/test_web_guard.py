"""The request guard: other sites cannot post to the app, other host names cannot read it."""

import asyncio
import threading
from pathlib import Path
from typing import Any

import pytest
from httpx import Response
from starlette.types import Message, Receive, Scope, Send

from tests.unit import report_fixtures as fx
from tests.unit.web_support import BASE_URL, heal_job, heal_report, make_client
from workbench.config import specs_dir
from workbench.models.generate import GenerateReport
from workbench.models.heal import HealReport
from workbench.models.settings import (
    DEFAULT_URLS,
    DEMO_MODEL,
    ConnectionStatus,
    ModelSettings,
)
from workbench.models.shared import RunResult
from workbench.reports import load_report, save_report
from workbench.settings import load_settings, save_settings
from workbench.web.guard import RequestGuard

pytestmark = pytest.mark.usefixtures("web_workspace")

DEMO = ModelSettings(provider="demo", model=DEMO_MODEL)
EVIL = {"Origin": "https://evil.example"}
OLLAMA_FORM = {"provider": "ollama", "base_url": DEFAULT_URLS["ollama"], "model": "m"}
OLLAMA = ModelSettings(provider="ollama", base_url=DEFAULT_URLS["ollama"], model="m")
SPEC_UPLOAD = {"spec": ("x.spec.ts", b"require('child_process');\n", "text/plain")}


@pytest.fixture(autouse=True)
def demo_model(web_workspace: Path) -> None:
    """A ready model, so every start route would run if the guard let it through."""
    save_settings(DEMO)


class Calls:
    """Fake services that record every call a route makes."""

    def __init__(self) -> None:
        self.made: list[str] = []

    def heal(
        self, request: Any, *, model: Any, emit: Any = None, cancel: Any = None
    ) -> HealReport:
        self.made.append("heal")
        return heal_job(heal_report())(emit, cancel)  # type: ignore[return-value]

    def generate(
        self, request: Any, *, model: Any, emit: Any = None, cancel: Any = None
    ) -> GenerateReport:
        self.made.append("generate")
        report = fx.generate_not_run()
        save_report(report)
        return report

    def run_test(self, spec: Path, *, cancel: Any = None) -> RunResult:
        self.made.append("run_test")
        return fx.run_result("passed")

    def check(self, provider: str, base_url: str = "") -> ConnectionStatus:
        self.made.append(f"check {provider} {base_url}".strip())
        return ConnectionStatus(
            provider=provider,  # type: ignore[arg-type]
            base_url=base_url,
            reachable=True,
            models=["m"],
        )


def _client(calls: Calls):  # type: ignore[no-untyped-def]
    return make_client(
        heal=calls.heal,
        generate=calls.generate,
        run_test=calls.run_test,
        check_connection=calls.check,
    )


def _assert_refused(response: Response, status: int = 403) -> None:
    assert response.status_code == status
    assert response.headers["content-type"].startswith("text/plain")
    assert "HX-Redirect" not in response.headers
    assert "HX-Refresh" not in response.headers


def _uploads() -> list[Path]:
    folder = specs_dir() / "uploads"
    return sorted(folder.iterdir()) if folder.is_dir() else []


def test_another_site_cannot_save_the_model() -> None:
    calls = Calls()
    form = {**OLLAMA_FORM, "base_url": "http://attacker.example/v1"}
    _assert_refused(_client(calls).post("/model", data=form, headers=EVIL))
    assert load_settings() == DEMO
    assert calls.made == []


def test_another_site_cannot_make_the_app_probe_a_server() -> None:
    calls = Calls()
    form = {"provider": "ollama", "base_url": "http://attacker.example/v1"}
    _assert_refused(_client(calls).post("/model/test", data=form, headers=EVIL))
    assert calls.made == []


def test_another_site_cannot_upload_and_run_a_spec() -> None:
    calls = Calls()
    client = _client(calls)
    response = client.post(
        "/heal",
        data={"action": "upload", "max_attempts": "1"},
        files=SPEC_UPLOAD,
        headers=EVIL,
    )
    _assert_refused(response)
    assert _uploads() == []
    assert client.app.state.runs.active() is None  # type: ignore[attr-defined]
    assert calls.made == []


def test_another_site_cannot_heal_a_sample() -> None:
    calls = Calls()
    client = _client(calls)
    form = {"action": "sample:selector-drift", "max_attempts": "3"}
    _assert_refused(client.post("/heal", data=form, headers=EVIL))
    assert not (specs_dir() / "samples").exists()
    assert client.app.state.runs.active() is None  # type: ignore[attr-defined]
    assert calls.made == []


def test_another_site_cannot_start_a_generation() -> None:
    calls = Calls()
    client = _client(calls)
    form = {"url": f"{BASE_URL}/sample-site/", "scenario": "A user sends the form"}
    _assert_refused(client.post("/generate", data=form, headers=EVIL))
    assert client.app.state.runs.active() is None  # type: ignore[attr-defined]
    assert calls.made == []


def test_another_site_cannot_run_a_generated_spec() -> None:
    report = fx.generate_not_run()
    save_report(report)
    (specs_dir() / report.spec_name).write_text(report.code, encoding="utf-8")
    calls = Calls()
    client = _client(calls)
    response = client.post("/generate/run", data={"report": report.id}, headers=EVIL)
    _assert_refused(response)
    assert client.app.state.runs.active() is None  # type: ignore[attr-defined]
    assert calls.made == []
    assert load_report(report.id).status == "not_run"


def test_another_site_cannot_cancel_a_run() -> None:
    client = _client(Calls())
    gate = threading.Event()
    run = client.app.state.runs.start("heal", "x", heal_job(heal_report(), gate=gate))  # type: ignore[attr-defined]
    try:
        _assert_refused(client.post(f"/runs/{run.id}/cancel", headers=EVIL))
        assert not run.cancel.is_set()
    finally:
        gate.set()
        assert run.wait(5)


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "null"},
        {"Origin": ""},
        {"Sec-Fetch-Site": "cross-site"},
        {"Sec-Fetch-Site": "same-site"},
        {"Origin": "http://127.0.0.1:9999"},
        {"Origin": "http://localhost:7860"},
        {"Origin": "https://127.0.0.1:7860"},
        {"Origin": "http://127.0.0.1"},
        {"Origin": "http://127.0.0.1:7860.evil.example"},
        {"Origin": "http://127.0.0.1:7860/"},
        {"Origin": "https://evil.example", "Sec-Fetch-Site": "same-origin"},
    ],
)
def test_posts_that_are_not_from_the_apps_own_origin_are_refused(
    headers: dict[str, str],
) -> None:
    calls = Calls()
    _assert_refused(_client(calls).post("/model", data=OLLAMA_FORM, headers=headers))
    assert load_settings() == DEMO
    assert calls.made == []


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE"])
def test_every_state_changing_method_is_checked(method: str) -> None:
    _assert_refused(make_client().request(method, "/model", headers=EVIL))


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": BASE_URL},
        {"Origin": BASE_URL, "Sec-Fetch-Site": "same-origin"},
        {"Sec-Fetch-Site": "same-origin"},
        {"Sec-Fetch-Site": "none"},
    ],
)
def test_the_apps_own_pages_and_local_tools_can_still_post(
    headers: dict[str, str],
) -> None:
    response = _client(Calls()).post("/model", data=OLLAMA_FORM, headers=headers)
    assert response.status_code == 200
    assert response.headers["HX-Refresh"] == "true"
    assert load_settings() == OLLAMA


def test_the_app_opened_as_localhost_can_post_to_itself_only() -> None:
    client = _client(Calls())
    local = {"Host": "localhost:7860"}
    crossed = {**local, "Origin": BASE_URL}
    _assert_refused(client.post("/model", data=OLLAMA_FORM, headers=crossed))
    assert load_settings() == DEMO
    own = {**local, "Origin": "http://localhost:7860"}
    assert client.post("/model", data=OLLAMA_FORM, headers=own).status_code == 200
    assert load_settings() == OLLAMA


@pytest.mark.parametrize(
    "host",
    [
        "evil.example",
        "evil.example:7860",
        "127.0.0.1.evil.example",
        "127.0.0.1:7860.evil.example",
        "evil.example@127.0.0.1:7860",
        "localhost.evil.example:7860",
        "localhost:abc",
        "0.0.0.0:7860",
        "[::1]:7860",
        "",
    ],
)
def test_requests_for_another_host_name_are_refused(host: str) -> None:
    client = make_client()
    _assert_refused(client.get("/heal", headers={"Host": host}), 400)
    _assert_refused(client.get("/static/css/app.css", headers={"Host": host}), 400)
    _assert_refused(client.get("/sample-site/", headers={"Host": host}), 400)


@pytest.mark.parametrize("host", ["127.0.0.1:7860", "localhost:7860", "127.0.0.1"])
def test_requests_for_this_machine_are_answered(host: str) -> None:
    response = make_client().get("/heal", headers={"Host": host})
    assert response.status_code == 200
    assert "Heal a failing test" in response.text


def test_a_rebound_host_name_cannot_post_even_with_a_matching_origin() -> None:
    calls = Calls()
    rebound = {"Host": "evil.example:7860", "Origin": "http://evil.example:7860"}
    response = _client(calls).post("/model", data=OLLAMA_FORM, headers=rebound)
    _assert_refused(response, 400)
    assert load_settings() == DEMO
    assert calls.made == []


def test_links_from_other_sites_can_still_open_pages() -> None:
    headers = {**EVIL, "Sec-Fetch-Site": "cross-site"}
    assert make_client().get("/heal", headers=headers).status_code == 200


def test_the_live_stream_is_only_host_checked() -> None:
    client = make_client()
    run = client.app.state.runs.start("heal", "x", heal_job(heal_report()))  # type: ignore[attr-defined]
    assert run.wait(5)
    path = f"/runs/{run.id}/events"
    own = client.get(path, headers={"Sec-Fetch-Site": "same-origin"})
    assert own.status_code == 200 and "event: done" in own.text
    _assert_refused(client.get(path, headers={"Host": "evil.example"}), 400)


def _ask(scope: dict[str, Any]) -> tuple[list[Message], list[str]]:
    """Send one raw request through the guard: what it sent, and what got past it."""
    sent: list[Message] = []
    reached: list[str] = []

    async def inner(scope: Scope, receive: Receive, send: Send) -> None:
        reached.append(scope["type"])

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    full = {"type": "http", "method": "POST", "path": "/model", **scope}
    asyncio.run(asyncio.wait_for(RequestGuard(inner)(full, receive, send), timeout=2))
    return sent, reached


OWN_HOST = (b"host", b"127.0.0.1:7860")
OWN_ORIGIN = (b"origin", b"http://127.0.0.1:7860")


def test_a_request_without_a_host_header_is_refused() -> None:
    sent, reached = _ask({"method": "GET", "headers": []})
    assert sent[0]["status"] == 400 and reached == []


def test_a_request_with_two_host_headers_is_refused() -> None:
    headers = [OWN_HOST, (b"host", b"evil.example")]
    sent, reached = _ask({"method": "GET", "headers": headers})
    assert sent[0]["status"] == 400 and reached == []


def test_a_post_with_two_origin_headers_is_refused() -> None:
    headers = [OWN_HOST, OWN_ORIGIN, (b"origin", b"https://evil.example")]
    sent, reached = _ask({"headers": headers})
    assert sent[0]["status"] == 403 and reached == []


def test_a_post_with_a_cross_site_fetch_header_among_several_is_refused() -> None:
    headers = [
        OWN_HOST,
        (b"sec-fetch-site", b"same-origin"),
        (b"sec-fetch-site", b"cross-site"),
    ]
    sent, reached = _ask({"headers": headers})
    assert sent[0]["status"] == 403 and reached == []


def test_the_guard_passes_its_own_origin_through_untouched() -> None:
    sent, reached = _ask({"headers": [OWN_HOST, OWN_ORIGIN]})
    assert sent == [] and reached == ["http"]


def test_a_websocket_from_another_site_is_refused() -> None:
    headers = [OWN_HOST, (b"origin", b"https://evil.example")]
    sent, reached = _ask({"type": "websocket", "method": None, "headers": headers})
    assert sent[0]["type"] == "websocket.http.response.start"
    assert sent[0]["status"] == 403 and reached == []
    _, reached = _ask(
        {"type": "websocket", "method": None, "headers": [OWN_HOST, OWN_ORIGIN]}
    )
    assert reached == ["websocket"]


def test_startup_and_shutdown_messages_are_not_guarded() -> None:
    sent, reached = _ask({"type": "lifespan"})
    assert sent == [] and reached == ["lifespan"]
