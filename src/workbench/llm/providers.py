"""LM Studio, Ollama and Demo: detection, connection checks and model creation."""

from collections.abc import Callable, Iterable, Mapping

from workbench.llm.chat import ChatModel, ModelError
from workbench.llm.client import OpenAICompatibleModel, list_models
from workbench.llm.demo import DemoModel
from workbench.models.settings import (
    DEFAULT_URLS,
    DEMO_MODEL,
    ConnectionStatus,
    ModelSettings,
    ProviderName,
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
    settings: ModelSettings, *, list_models: ListModels = list_models
) -> ConnectionStatus:
    """Ask the chosen server for its models; Demo is always available."""
    if settings.provider == "demo":
        return ConnectionStatus(provider="demo", reachable=True, models=[DEMO_MODEL])
    try:
        models = _usable(list_models(settings.base_url))
    except ModelError as exc:
        return ConnectionStatus(
            provider=settings.provider,
            base_url=settings.base_url,
            reachable=False,
            error=str(exc),
        )
    return ConnectionStatus(
        provider=settings.provider,
        base_url=settings.base_url,
        reachable=True,
        models=models,
    )


def build_model(settings: ModelSettings) -> ChatModel:
    """The ``ChatModel`` for a model choice."""
    if settings.provider == "demo":
        return DemoModel()
    return OpenAICompatibleModel(
        provider=settings.provider, base_url=settings.base_url, model=settings.model
    )
