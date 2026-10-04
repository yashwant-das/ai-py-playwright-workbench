"""The saved model choice and how server URLs are cleaned up."""

import pytest
from pydantic import ValidationError

from workbench.models.settings import DEMO_MODEL, ModelSettings, normalise_base_url


def test_bare_host_gets_the_openai_path() -> None:
    assert normalise_base_url("http://localhost:11434") == "http://localhost:11434/v1"
    assert (
        normalise_base_url(" http://localhost:1234/v1/ ") == "http://localhost:1234/v1"
    )
    assert (
        normalise_base_url("http://gpu-box:8080/openai/v1")
        == "http://gpu-box:8080/openai/v1"
    )


@pytest.mark.parametrize("url", ["localhost:1234", "ftp://host/v1", "http://", ""])
def test_bad_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="http:// or https://"):
        normalise_base_url(url)


def test_server_providers_need_a_url() -> None:
    with pytest.raises(ValidationError, match="Ollama needs a server URL"):
        ModelSettings(provider="ollama", model="qwen3:8b")


def test_saved_url_is_normalised() -> None:
    choice = ModelSettings(
        provider="ollama", base_url="http://localhost:11434/", model="m"
    )
    assert choice.base_url == "http://localhost:11434/v1"
    assert choice.label == "Ollama"


def test_demo_needs_no_url() -> None:
    choice = ModelSettings(provider="demo", model=DEMO_MODEL)
    assert choice.base_url == ""
    assert choice.label == "Demo"


def test_unknown_provider_and_empty_model_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelSettings(provider="openai", base_url="http://x/v1", model="m")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        ModelSettings(provider="demo", model="")
