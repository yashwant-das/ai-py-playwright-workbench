"""The app factory, its static mounts, and the launcher's port setting."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from workbench import config
from workbench.app import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))
    return TestClient(create_app(), base_url="http://127.0.0.1:7860")


def test_health(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_redirects_to_heal(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/heal"


def test_sample_site_is_served_under_a_trailing_slash(client: TestClient) -> None:
    redirect = client.get("/sample-site", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"].endswith("/sample-site/")
    assert "Contact form" in client.get("/sample-site/").text
    assert "Place order" in client.get("/sample-site/checkout.html").text


def test_static_files_are_served(client: TestClient) -> None:
    response = client.get("/static/img/logo.svg")
    assert response.status_code == 200
    assert "svg" in response.headers["content-type"]


def test_base_url_uses_the_bind_address() -> None:
    assert config.base_url(7860) == "http://127.0.0.1:7860"
    assert create_app(port=8123).state.base_url == "http://127.0.0.1:8123"


def test_port_defaults_and_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.PORT_ENV, raising=False)
    assert config.port() == 7860
    monkeypatch.setenv(config.PORT_ENV, " 8123 ")
    assert config.port() == 8123
    for bad in ("abc", "0", "70000"):
        monkeypatch.setenv(config.PORT_ENV, bad)
        with pytest.raises(ValueError, match="WORKBENCH_PORT"):
            config.port()
