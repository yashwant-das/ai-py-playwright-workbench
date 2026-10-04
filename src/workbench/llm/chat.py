"""The one interface pipelines use to talk to a model.

Pipelines depend on ``ChatModel``, never on a provider. Phase 3 adds the
LM Studio, Ollama and Demo implementations; until then ``RouterChatModel``
adapts the 1.0 router.
"""

import logging
from typing import Any, Protocol

import openai
from pydantic import BaseModel

from workbench.llm.router import LLMRequest, LLMResponse, LLMRouter

logger = logging.getLogger(__name__)

Message = dict[str, str]


class ChatReply(BaseModel):
    """A model's answer and what produced it."""

    content: str
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


class ModelError(RuntimeError):
    """The model could not be reached or did not answer."""


class ChatModel(Protocol):
    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> ChatReply:
        """Send ``messages``; with ``json_schema``, ask for output matching it."""
        ...


def response_format_for(json_schema: dict[str, Any]) -> dict[str, Any]:
    """OpenAI-style ``response_format`` asking for output matching ``json_schema``."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": str(json_schema.get("title", "response")),
            "schema": json_schema,
        },
    }


def _rejected_by_provider(exc: BaseException) -> bool:
    cause: BaseException | None = exc
    while cause is not None:
        if isinstance(cause, openai.BadRequestError):
            return True
        cause = cause.__cause__
    return False


class RouterChatModel:
    """Adapts the 1.0 ``LLMRouter`` to ``ChatModel`` (replaced in Phase 3)."""

    def __init__(self, router: LLMRouter) -> None:
        self._router = router

    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> ChatReply:
        response_format = response_format_for(json_schema) if json_schema else None
        try:
            response = self._complete(messages, temperature, response_format)
        except RuntimeError as exc:
            if response_format is None or not _rejected_by_provider(exc):
                raise ModelError(str(exc)) from exc
            logger.info("The provider rejected the JSON schema; asking without it.")
            try:
                response = self._complete(messages, temperature, None)
            except RuntimeError as retry_exc:
                raise ModelError(str(retry_exc)) from retry_exc
        return ChatReply(
            content=response.content,
            model=response.model_used,
            provider=response.provider,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
        )

    def _complete(
        self,
        messages: list[Message],
        temperature: float,
        response_format: dict[str, Any] | None,
    ) -> LLMResponse:
        return self._router.complete(
            LLMRequest(
                messages=list(messages),
                model=self._router.primary_model,
                temperature=temperature,
                response_format=response_format,
            )
        )
