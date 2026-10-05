"""The model menu: test a server, pick a model, save the choice; and the header pill."""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from workbench import config
from workbench.app import create_app
from workbench.models.settings import (
    DEFAULT_URLS,
    DEMO_MODEL,
    ConnectionStatus,
    ModelSettings,
    ModelView,
)
from workbench.settings import load_settings, save_settings
from workbench.web.services import Services
from workbench.web.templating import templates

OLLAMA = DEFAULT_URLS["ollama"]


class FakeServers:
    """check_connection and detect fakes that record their calls."""

    def __init__(
        self,
        models: dict[str, list[str]] | None = None,
        found: list[ModelSettings | None] | None = None,
    ) -> None:
        self.models = models or {}
        self.found = found or []
        self.checked: list[tuple[str, str]] = []
        self.detections = 0

    def check(self, provider: str, base_url: str = "") -> ConnectionStatus:
        self.checked.append((provider, base_url))
        if provider == "demo":
            return ConnectionStatus(
                provider="demo", reachable=True, models=[DEMO_MODEL]
            )
        if base_url in self.models:
            return ConnectionStatus(
                provider=provider,
                base_url=base_url,
                reachable=True,
                models=self.models[base_url],
            )
        return ConnectionStatus(
            provider=provider,
            base_url=base_url,
            reachable=False,
            error=f"Could not reach the server at {base_url}. Is it running?",
        )

    def detect(self) -> ModelSettings | None:
        self.detections += 1
        return self.found.pop(0) if self.found else None


@pytest.fixture
def servers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeServers:
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))
    return FakeServers({OLLAMA: ["qwen3.6:35b-mlx", "gemma3:4b"]})


def _client(servers: FakeServers) -> TestClient:
    services = replace(
        Services(), check_connection=servers.check, detect=servers.detect
    )
    return TestClient(create_app(services))


def test_menu_lists_the_saved_servers_models(servers: FakeServers) -> None:
    save_settings(ModelSettings(provider="ollama", base_url=OLLAMA, model="gemma3:4b"))
    html = _client(servers).get("/model").text
    assert "Connected" in html
    assert '<option value="gemma3:4b" selected>' in html
    assert (
        '<option value="qwen3.6:35b-mlx" >' in html
        or '<option value="qwen3.6:35b-mlx">' in html
    )
    assert "Saved on this machine." in html


def test_switching_provider_uses_its_default_url(servers: FakeServers) -> None:
    html = (
        _client(servers)
        .post(
            "/model/test",
            data={"provider": "ollama", "base_url": DEFAULT_URLS["lm_studio"]},
        )
        .text
    )
    assert servers.checked[-1] == ("ollama", OLLAMA)
    assert f'value="{OLLAMA}"' in html


def test_a_custom_server_url_is_kept(servers: FakeServers) -> None:
    _client(servers).post(
        "/model/test",
        data={"provider": "ollama", "base_url": "http://gpu-box:11434/v1"},
    )
    assert servers.checked[-1] == ("ollama", "http://gpu-box:11434/v1")


def test_an_unreachable_server_shows_its_error_and_cannot_be_saved(
    servers: FakeServers,
) -> None:
    html = (
        _client(servers)
        .post(
            "/model/test",
            data={"provider": "lm_studio", "base_url": DEFAULT_URLS["lm_studio"]},
        )
        .text
    )
    assert "Unreachable" in html
    assert "Is it running?" in html
    assert "Available once connected" in html
    assert 'type="submit" disabled' in html


def test_saving_writes_the_settings_and_reloads_the_page(servers: FakeServers) -> None:
    response = _client(servers).post(
        "/model",
        data={"provider": "ollama", "base_url": OLLAMA, "model": "qwen3.6:35b-mlx"},
    )
    assert response.status_code == 200
    assert response.headers["HX-Refresh"] == "true"
    assert load_settings() == ModelSettings(
        provider="ollama", base_url=OLLAMA, model="qwen3.6:35b-mlx"
    )


def test_demo_is_saved_without_a_server(servers: FakeServers) -> None:
    response = _client(servers).post("/model", data={"provider": "demo"})
    assert response.headers["HX-Refresh"] == "true"
    assert load_settings() == ModelSettings(provider="demo", model=DEMO_MODEL)


@pytest.mark.parametrize(
    "form",
    [
        {"provider": "ollama", "base_url": "localhost:abc", "model": "m"},
        {"provider": "ollama", "base_url": OLLAMA, "model": ""},
        {"provider": "openai", "base_url": OLLAMA, "model": "m"},
    ],
)
def test_bad_choices_are_refused_inline(
    servers: FakeServers, form: dict[str, str]
) -> None:
    response = _client(servers).post("/model", data=form)
    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert load_settings() is None


def test_a_detected_server_is_found_once_per_app(servers: FakeServers) -> None:
    servers.found = [
        ModelSettings(provider="ollama", base_url=OLLAMA, model="gemma3:4b")
    ]
    client = _client(servers)
    client.get("/model")
    client.get("/model")
    assert servers.detections == 1


def test_detection_runs_again_until_a_server_is_found(servers: FakeServers) -> None:
    detected = ModelSettings(provider="ollama", base_url=OLLAMA, model="gemma3:4b")
    servers.found = [None, detected]
    state = _client(servers).app.state.model
    assert state.choice() is None
    assert state.choice() == detected
    assert state.choice() == detected
    assert servers.detections == 2


def _pill(view: ModelView) -> str:
    return templates.get_template("partials/model_pill.html").render(model=view)


def test_pill_shows_not_connected_when_the_server_is_down() -> None:
    choice = ModelSettings(
        provider="lm_studio", base_url=DEFAULT_URLS["lm_studio"], model="m"
    )
    html = _pill(
        ModelView(
            choice=choice,
            connection=ConnectionStatus(
                provider="lm_studio", reachable=False, error="down"
            ),
        )
    )
    assert "model-pill--off" in html and "Not connected" in html and "LM Studio" in html


def test_pill_shows_the_model_or_demo() -> None:
    connected = ModelView(
        choice=ModelSettings(
            provider="ollama", base_url=OLLAMA, model="qwen3.6:35b-mlx"
        ),
        connection=ConnectionStatus(
            provider="ollama", reachable=True, models=["qwen3.6:35b-mlx"]
        ),
    )
    demo = ModelView(
        choice=ModelSettings(provider="demo", model=DEMO_MODEL),
        connection=ConnectionStatus(
            provider="demo", reachable=True, models=[DEMO_MODEL]
        ),
    )
    assert "qwen3.6:35b-mlx" in _pill(connected) and "Ollama" in _pill(connected)
    assert "model-pill--demo" in _pill(demo) and "scripted answers" in _pill(demo)
    assert 'popovertarget="model-menu"' in _pill(demo)


def test_unreachable_card_offers_demo() -> None:
    html = templates.get_template("partials/unreachable.html").render(
        model=ModelView(
            choice=ModelSettings(
                provider="lm_studio", base_url=DEFAULT_URLS["lm_studio"], model="m"
            ),
            connection=ConnectionStatus(provider="lm_studio", reachable=False),
        )
    )
    assert "Can't reach LM Studio at localhost:1234/v1" in html
    assert 'name="provider" value="demo"' in html
