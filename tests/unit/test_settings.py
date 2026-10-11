"""The saved model choice in workspace/settings.json."""

from pathlib import Path

import pytest

from workbench import config
from workbench.models.settings import DEFAULT_URLS, DEMO_MODEL, ModelSettings
from workbench.settings import (
    load_settings,
    resolve_settings,
    save_settings,
    settings_path,
)


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))


def test_nothing_saved_means_no_choice() -> None:
    assert load_settings() is None


def test_saved_choice_round_trips() -> None:
    choice = ModelSettings(
        provider="ollama", base_url=DEFAULT_URLS["ollama"], model="qwen3:8b"
    )
    path = save_settings(choice)
    assert path == settings_path() == config.workspace_dir() / "settings.json"
    assert load_settings() == choice
    assert not path.with_suffix(".tmp").exists()


@pytest.mark.parametrize(
    "content",
    [
        "{not json",
        '{"provider": "openai", "model": "gpt"}',
        '{"provider": "ollama", "model": "qwen3:8b"}',
        '{"provider": "lm_studio", "base_url": "localhost:1234", "model": "m"}',
    ],
)
def test_unusable_file_is_ignored(content: str) -> None:
    settings_path().parent.mkdir(parents=True, exist_ok=True)
    settings_path().write_text(content, encoding="utf-8")
    assert load_settings() is None


def test_undecodable_file_is_ignored() -> None:
    settings_path().parent.mkdir(parents=True, exist_ok=True)
    settings_path().write_bytes(b"\xff\xfe\x00garbage")
    assert load_settings() is None


def test_resolve_prefers_the_saved_choice() -> None:
    save_settings(ModelSettings(provider="demo", model=DEMO_MODEL))

    def detect() -> ModelSettings | None:
        raise AssertionError("detected despite a saved choice")

    choice = resolve_settings(detect=detect)
    assert choice is not None and choice.provider == "demo"


def test_resolve_detects_when_nothing_is_saved_and_does_not_save() -> None:
    found = ModelSettings(
        provider="lm_studio", base_url=DEFAULT_URLS["lm_studio"], model="m"
    )
    assert resolve_settings(detect=lambda: found) == found
    assert not settings_path().exists()


def test_resolve_with_no_server_and_nothing_saved_is_none() -> None:
    assert resolve_settings(detect=lambda: None) is None
