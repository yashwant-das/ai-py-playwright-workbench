"""RouterChatModel turns router responses into ChatReply and handles schemas."""

from typing import Any

import httpx
import openai
import pytest

from workbench.llm.chat import ModelError, RouterChatModel, response_format_for
from workbench.llm.router import LLMRequest, LLMResponse

SCHEMA = {"title": "HealingAnalysis", "type": "object"}
MESSAGES = [{"role": "user", "content": "hi"}]


def _response(content: str = "{}") -> LLMResponse:
    return LLMResponse(
        content=content,
        model_used="m-1",
        provider="lm_studio",
        latency_ms=12,
        input_tokens=3,
        output_tokens=4,
    )


def _rejected() -> RuntimeError:
    request = httpx.Request("POST", "http://x/v1/chat/completions")
    error = RuntimeError("rejected")
    error.__cause__ = openai.BadRequestError(
        "unsupported", response=httpx.Response(400, request=request), body=None
    )
    return error


class FakeRouter:
    primary_model = "fake-model"

    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def test_reply_carries_provenance() -> None:
    reply = RouterChatModel(FakeRouter([_response("ok")])).chat(MESSAGES)  # type: ignore[arg-type]
    assert (reply.content, reply.model, reply.provider) == ("ok", "m-1", "lm_studio")
    assert (reply.input_tokens, reply.output_tokens, reply.latency_ms) == (3, 4, 12)


def test_schema_becomes_a_response_format() -> None:
    router = FakeRouter([_response()])
    RouterChatModel(router).chat(MESSAGES, json_schema=SCHEMA)  # type: ignore[arg-type]
    assert router.requests[0].response_format == response_format_for(SCHEMA)
    assert response_format_for(SCHEMA)["json_schema"]["name"] == "HealingAnalysis"


def test_no_schema_sends_no_response_format() -> None:
    router = FakeRouter([_response()])
    RouterChatModel(router).chat(MESSAGES)  # type: ignore[arg-type]
    assert router.requests[0].response_format is None


def test_rejected_schema_is_retried_without_it() -> None:
    router = FakeRouter([_rejected(), _response("{}")])
    reply = RouterChatModel(router).chat(MESSAGES, json_schema=SCHEMA)  # type: ignore[arg-type]
    assert reply.content == "{}"
    assert [r.response_format is None for r in router.requests] == [False, True]


def test_other_failures_become_model_errors() -> None:
    router = FakeRouter([RuntimeError("connection refused")])
    with pytest.raises(ModelError, match="connection refused"):
        RouterChatModel(router).chat(MESSAGES, json_schema=SCHEMA)  # type: ignore[arg-type]


def test_failure_after_the_retry_is_a_model_error() -> None:
    router = FakeRouter([_rejected(), RuntimeError("still down")])
    with pytest.raises(ModelError, match="still down"):
        RouterChatModel(router).chat(MESSAGES, json_schema=SCHEMA)  # type: ignore[arg-type]
