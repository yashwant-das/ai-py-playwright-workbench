"""LM Studio, Ollama and Demo: detection, connection checks and model creation."""

from collections.abc import Callable, Iterable, Mapping

import httpx

from workbench.llm.chat import ChatModel, ModelError
from workbench.llm.client import OpenAICompatibleModel, list_models
from workbench.llm.demo import DemoModel
from workbench.models.settings import (
    DEFAULT_URLS,
    DEMO_MODEL,
    PROVIDER_LABELS,
    ConnectionStatus,
    ModelSettings,
    ProviderName,
    normalise_base_url,
)

ListModels = Callable[[str], list[str]]
DETECTION_ORDER: tuple[ProviderName, ...] = ("lm_studio", "ollama")


def _usable(models: list[str]) -> list[str]:
    """Drop blank ids; a model choice needs a non-empty name."""
    return [model for model in models if model.strip()]


def detect_provider(
    *,
    order: Iterable[ProviderName] = DETECTION_ORDER,
    urls: Mapping[ProviderName, str] = DEFAULT_URLS,
    list_models: ListModels = list_models,
) -> ModelSettings | None:
    """The first local server that answers and offers a model, with its first model.

    None when neither LM Studio nor Ollama is usable; the UI then offers Demo.
    """
    for provider in order:
        base_url = urls[provider]
        try:
            models = _usable(list_models(base_url))
        except ModelError:
            continue
        if models:
            return ModelSettings(provider=provider, base_url=base_url, model=models[0])
    return None


def check_connection(
    provider: ProviderName, base_url: str = "", *, list_models: ListModels = list_models
) -> ConnectionStatus:
    """Ask the server at ``base_url`` for its models; Demo is always available.

    Needs no model, so the model menu can probe a typed URL before one is picked.
    Never raises: a bad URL or a server that does not answer is in ``error``.
    """
    if provider == "demo":
        return ConnectionStatus(provider="demo", reachable=True, models=[DEMO_MODEL])
    try:
        url = normalise_base_url(base_url)
    except ValueError as exc:
        return ConnectionStatus(
            provider=provider, base_url=base_url, reachable=False, error=str(exc)
        )
    try:
        models = _usable(list_models(url))
    except ModelError as exc:
        return ConnectionStatus(
            provider=provider,
            base_url=url,
            reachable=False,
            error=_connection_error(provider, url, exc),
        )
    return ConnectionStatus(
        provider=provider, base_url=url, reachable=True, models=models
    )


def _connection_error(provider: ProviderName, base_url: str, exc: ModelError) -> str:
    """Name the provider; say "not running" rather than show an errno."""
    label = PROVIDER_LABELS[provider]
    if isinstance(exc.__cause__, httpx.TransportError):  # refused, timed out, no DNS
        return f"Could not reach {label} at {base_url}. Is it running?"
    return f"{label}: {exc}"


def build_model(settings: ModelSettings) -> ChatModel:
    """The ``ChatModel`` for a model choice."""
    if settings.provider == "demo":
        return DemoModel()
    return OpenAICompatibleModel(
        provider=settings.provider, base_url=settings.base_url, model=settings.model
    )
