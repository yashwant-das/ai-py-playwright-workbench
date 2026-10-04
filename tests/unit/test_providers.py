"""Detection order, connection checks and which ChatModel a choice builds."""

from collections.abc import Callable

import httpx

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
            refused = httpx.ConnectError("[Errno 61] Connection refused")
            raise ModelError(f"No answer from {base_url}: {refused}") from refused
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


def test_blank_model_ids_are_ignored() -> None:
    choice = detect_provider(list_models=_servers({LM: ["", "gemma3:4b"]}))
    assert choice == ModelSettings(provider="lm_studio", base_url=LM, model="gemma3:4b")


def test_a_server_listing_only_blank_ids_is_skipped() -> None:
    choice = detect_provider(
        list_models=_servers({LM: [""], OLLAMA: ["  ", "gemma3:4b"]})
    )
    assert choice is not None and choice.provider == "ollama"
    assert detect_provider(list_models=_servers({LM: [""]})) is None


def test_no_server_means_no_choice() -> None:
    assert detect_provider(list_models=_servers({})) is None


def test_connection_lists_the_models() -> None:
    status = check_connection(
        "ollama", OLLAMA, list_models=_servers({OLLAMA: ["gemma3:4b", "qwen3:8b"]})
    )
    assert status == ConnectionStatus(
        provider="ollama",
        base_url=OLLAMA,
        reachable=True,
        models=["gemma3:4b", "qwen3:8b"],
    )


def test_connection_normalises_a_typed_url() -> None:
    status = check_connection(
        "ollama", "http://localhost:11434/", list_models=_servers({OLLAMA: ["m"]})
    )
    assert status.base_url == OLLAMA and status.models == ["m"]


def test_connection_reports_an_unreachable_server_by_name() -> None:
    status = check_connection("ollama", OLLAMA, list_models=_servers({}))
    assert not status.reachable
    assert status.models == []
    assert status.error == f"Could not reach Ollama at {OLLAMA}. Is it running?"
    assert "[Errno" not in status.error


def test_connection_reports_an_invalid_url_without_raising() -> None:
    status = check_connection("lm_studio", "http://localhost:1234a", list_models=_never)
    assert not status.reachable
    assert status.base_url == "http://localhost:1234a"
    assert "Server URL has an invalid port" in status.error


def test_connection_needs_a_url_for_a_server() -> None:
    status = check_connection("ollama", list_models=_never)
    assert not status.reachable
    assert "http:// or https://" in status.error


def test_demo_is_connected_without_a_url() -> None:
    status = check_connection("demo", list_models=_never)
    assert status == ConnectionStatus(
        provider="demo", reachable=True, models=[DEMO_MODEL]
    )


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


def test_connection_lists_only_non_blank_models() -> None:
    status = check_connection(
        "ollama", OLLAMA, list_models=_servers({OLLAMA: ["", "gemma3:4b", " "]})
    )
    assert status.models == ["gemma3:4b"]
