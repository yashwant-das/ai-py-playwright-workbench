"""Talks to LM Studio and Ollama through their OpenAI-compatible API.

``OpenAICompatibleModel`` implements ``ChatModel``. ``list_models`` asks a
server which models it can run; provider detection and the model menu use it.
"""

import logging
import time
from typing import Any, cast

import httpx
import openai
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from pydantic import BaseModel, ValidationError

from workbench.llm.chat import ChatReply, Message, ModelError, response_format_for
from workbench.models.settings import PROVIDER_LABELS, ProviderName

logger = logging.getLogger(__name__)

MODEL_TIMEOUT_S = 300.0  # a local model on modest hardware can take minutes
LIST_TIMEOUT_S = 2.0
# Local servers ignore the key, but the OpenAI client requires one.
_API_KEYS: dict[ProviderName, str] = {"lm_studio": "lm-studio", "ollama": "ollama"}


class _ModelEntry(BaseModel):
    id: str


class _ModelList(BaseModel):
    data: list[_ModelEntry]


def list_models(
    base_url: str,
    *,
    timeout_s: float = LIST_TIMEOUT_S,
    http_client: httpx.Client | None = None,
) -> list[str]:
    """Ids of the chat models the server at ``base_url`` offers, in its order.

    Embedding models and blank ids are left out: neither can answer a chat request.
    Raises ``ModelError`` when the server does not answer or answers nonsense.
    """
    client = http_client or httpx.Client(timeout=timeout_s)
    try:
        response = client.get(f"{base_url}/models", timeout=timeout_s)
        response.raise_for_status()
        listing = _ModelList.model_validate_json(response.content)
    except (httpx.InvalidURL, UnicodeError) as exc:  # bad port, or a host IDNA rejects
        raise ModelError(f"{base_url} is not a valid server URL: {exc}") from exc
    except httpx.HTTPError as exc:
        raise ModelError(f"No answer from {base_url}: {exc}") from exc
    except ValidationError as exc:
        raise ModelError(f"{base_url}/models did not return a model list.") from exc
    finally:
        if http_client is None:
            client.close()
    return [e.id for e in listing.data if e.id.strip() and "embed" not in e.id.lower()]


def _provider_message(exc: openai.APIStatusError) -> str:
    """The server's own error text, whichever shape its error body has."""
    body: Any = exc.body
    if isinstance(body, str):
        return body
    if isinstance(body, dict):
        error = body.get("error", body)
        if isinstance(error, str):
            return error
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return str(error["message"])
    return exc.message


class OpenAICompatibleModel:
    """A model served by LM Studio or Ollama."""

    def __init__(
        self,
        *,
        provider: ProviderName,
        base_url: str,
        model: str,
        timeout_s: float = MODEL_TIMEOUT_S,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.provider = provider
        self.base_url = base_url
        self.model = model
        self._label = PROVIDER_LABELS[provider]
        self._timeout_s = timeout_s
        self._http_client = http_client
        self._client: openai.OpenAI | None = None

    def _openai(self) -> openai.OpenAI:
        """The OpenAI client, built on first use so a bad URL is reported by chat()."""
        if self._client is None:
            self._client = openai.OpenAI(
                base_url=self.base_url,
                api_key=_API_KEYS.get(self.provider, "local"),
                timeout=self._timeout_s,
                # A local server that failed once will fail again; say so at once.
                max_retries=0,
                http_client=self._http_client,
            )
        return self._client

    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> ChatReply:
        response_format = response_format_for(json_schema) if json_schema else None
        started = time.monotonic()
        try:
            completion = self._complete(messages, temperature, response_format)
        except openai.BadRequestError as exc:
            if response_format is None:
                raise self._error(exc) from exc
            logger.info(
                "%s rejected the JSON schema (%s); asking without it.",
                self._label,
                _provider_message(exc),
            )
            try:
                completion = self._complete(messages, temperature, None)
            except openai.OpenAIError as retry_exc:
                raise self._error(retry_exc) from retry_exc
            except ValueError as bad_exc:
                raise self._not_a_completion(bad_exc) from bad_exc
        except openai.OpenAIError as exc:
            raise self._error(exc) from exc
        except httpx.InvalidURL as exc:  # e.g. a port that is not a number
            raise ModelError(
                f"{self._label} at {self.base_url} is not a valid server URL: {exc}"
            ) from exc
        except ValueError as exc:  # the body was declared JSON but is not
            raise self._not_a_completion(exc) from exc
        try:
            if not isinstance(completion, ChatCompletion):
                raise TypeError(
                    f"expected a chat completion, got {type(completion).__name__}"
                )
            usage = completion.usage
            content = (
                completion.choices[0].message.content if completion.choices else None
            )
            return ChatReply(
                content=content or "",
                model=completion.model or self.model,
                provider=self.provider,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise self._not_a_completion(exc) from exc

    def _not_a_completion(self, exc: Exception) -> ModelError:
        logger.info("%s sent an unusable answer: %r", self._label, exc)
        return ModelError(
            f"{self._label} at {self.base_url} did not return a chat completion."
        )

    def _complete(
        self,
        messages: list[Message],
        temperature: float,
        response_format: dict[str, Any] | None,
    ) -> ChatCompletion:
        extra: dict[str, Any] = (
            {"response_format": response_format} if response_format else {}
        )
        completion = self._openai().chat.completions.create(
            model=self.model,
            messages=cast(list[ChatCompletionMessageParam], messages),
            temperature=temperature,
            **extra,
        )
        return cast(ChatCompletion, completion)

    def _error(self, exc: openai.OpenAIError) -> ModelError:
        where = f"{self._label} at {self.base_url}"
        if isinstance(exc, openai.APITimeoutError):
            return ModelError(
                f"{where} did not answer within {self._timeout_s:.0f} seconds."
            )
        if isinstance(exc, openai.APIConnectionError):
            return ModelError(f"Could not reach {where}. Is it running?")
        if isinstance(exc, openai.NotFoundError):
            return ModelError(
                f"{where} has no model named {self.model!r}. Load it or pick another model."
            )
        if isinstance(exc, openai.APIStatusError):
            return ModelError(
                f"{where} answered HTTP {exc.status_code}: {_provider_message(exc)}"
            )
        return ModelError(f"{where} failed: {exc}")
