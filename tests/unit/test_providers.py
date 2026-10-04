"""Detection order, connection checks and which ChatModel a choice builds."""

from collections.abc import Callable

from workbench.llm.chat import ModelError
from workbench.llm.client import OpenAICompatibleModel
from workbench.llm.demo import DemoModel
from workbench.llm.providers import build_model, check_connection, detect_provider
from workbench.models.settings import (
    DEFAULT_URLS,
    DEMO_MODEL,
    ConnectionStatus,
    ModelSettings,
)

LM = DEFAULT_URLS["lm_studio"]
OLLAMA = DEFAULT_URLS["ollama"]


def _servers(answers: dict[str, list[str]]) -> Callable[[str], list[str]]:
    """A fake ``list_models``: URLs in ``answers`` respond, the rest are down."""

    def fake(base_url: str) -> list[str]:
        if base_url not in answers:
            raise ModelError(f"No answer from {base_url}: refused")
        return answers[base_url]

    return fake


def _never(base_url: str) -> list[str]:
    raise AssertionError(f"Demo must not contact {base_url}")


def test_lm_studio_wins_when_both_answer() -> None:
    choice = detect_provider(
        list_models=_servers({LM: ["qwen3-8b"], OLLAMA: ["gemma3:4b"]})
    )
    assert choice == ModelSettings(provider="lm_studio", base_url=LM, model="qwen3-8b")


def test_ollama_is_used_when_lm_studio_is_down() -> None:
    choice = detect_provider(list_models=_servers({OLLAMA: ["gemma3:4b", "qwen3:8b"]}))
    assert choice == ModelSettings(
        provider="ollama", base_url=OLLAMA, model="gemma3:4b"
    )


def test_a_server_with_no_models_is_skipped() -> None:
    choice = detect_provider(list_models=_servers({LM: [], OLLAMA: ["gemma3:4b"]}))
    assert choice is not None and choice.provider == "ollama"


def test_no_server_means_no_choice() -> None:
    assert detect_provider(list_models=_servers({})) is None


def test_connection_lists_the_models() -> None:
    choice = ModelSettings(provider="ollama", base_url=OLLAMA, model="gemma3:4b")
    status = check_connection(
        choice, list_models=_servers({OLLAMA: ["gemma3:4b", "qwen3:8b"]})
    )
    assert status == ConnectionStatus(
        provider="ollama",
        base_url=OLLAMA,
        reachable=True,
        models=["gemma3:4b", "qwen3:8b"],
    )


def test_connection_reports_an_unreachable_server() -> None:
    choice = ModelSettings(provider="lm_studio", base_url=LM, model="qwen3-8b")
    status = check_connection(choice, list_models=_servers({}))
    assert not status.reachable
    assert status.models == []
    assert "No answer from" in status.error


def test_demo_is_always_connected() -> None:
    status = check_connection(
        ModelSettings(provider="demo", model=DEMO_MODEL), list_models=_never
    )
    assert status.reachable and status.models == [DEMO_MODEL]


def test_build_model_picks_the_implementation() -> None:
    assert isinstance(
        build_model(ModelSettings(provider="demo", model=DEMO_MODEL)), DemoModel
    )
    model = build_model(
        ModelSettings(provider="ollama", base_url=OLLAMA, model="gemma3:4b")
    )
    assert isinstance(model, OpenAICompatibleModel)
    assert (model.provider, model.base_url, model.model) == (
        "ollama",
        OLLAMA,
        "gemma3:4b",
    )
