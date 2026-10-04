"""The one interface pipelines use to talk to a model.

Pipelines depend on ``ChatModel``, never on a provider. The implementations
are ``OpenAICompatibleModel`` (LM Studio, Ollama) in ``client.py`` and
``DemoModel`` in ``demo.py``; ``providers.build_model()`` picks one.
"""

from typing import Any, Protocol

from pydantic import BaseModel

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
    """The model could not be reached, refused the request or failed to answer."""


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
