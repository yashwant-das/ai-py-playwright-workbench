"""OpenAICompatibleModel and list_models against a mocked HTTP server."""

import json
import time
from collections.abc import Callable

import httpx
import pytest

from workbench.llm.chat import ModelError
from workbench.llm.client import OpenAICompatibleModel, list_models
from workbench.models.settings import ProviderName

BASE = "http://127.0.0.1:1234/v1"
SCHEMA = {"title": "HealingAnalysis", "type": "object"}
MESSAGES = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]

Handler = Callable[[httpx.Request], httpx.Response]


def _completion(content: str | None = "ok", model: str = "m-1") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "c1",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        },
    )


def _model(
    handler: Handler, provider: ProviderName = "lm_studio"
) -> OpenAICompatibleModel:
    return OpenAICompatibleModel(
        provider=provider,
        base_url=BASE,
        model="m-1",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _recorder(answer: Handler) -> tuple[list[dict], Handler]:
    bodies: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return answer(request)

    return bodies, handler


def test_reply_carries_provenance() -> None:
    reply = _model(lambda _: _completion("hello")).chat(MESSAGES)
    assert reply.content == "hello"
    assert (reply.provider, reply.model) == ("lm_studio", "m-1")
    assert (reply.input_tokens, reply.output_tokens) == (3, 4)
    assert reply.latency_ms >= 0


def test_schema_is_sent_as_response_format() -> None:
    bodies, handler = _recorder(lambda _: _completion())
    _model(handler).chat(MESSAGES, json_schema=SCHEMA)
    assert bodies[0]["model"] == "m-1"
    assert bodies[0]["messages"] == MESSAGES
    assert bodies[0]["response_format"]["type"] == "json_schema"
    assert bodies[0]["response_format"]["json_schema"]["schema"] == SCHEMA


def test_no_schema_sends_no_response_format() -> None:
    bodies, handler = _recorder(lambda _: _completion())
    _model(handler).chat(MESSAGES)
    assert "response_format" not in bodies[0]


def test_rejected_schema_is_retried_once_without_it() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        if "response_format" in json.loads(request.content):
            return httpx.Response(
                400, json={"error": {"message": "response_format unsupported"}}
            )
        return _completion("plain")

    bodies, handler = _recorder(answer)
    reply = _model(handler).chat(MESSAGES, json_schema=SCHEMA)
    assert reply.content == "plain"
    assert ["response_format" in body for body in bodies] == [True, False]


def test_a_bad_request_without_a_schema_is_not_retried() -> None:
    bodies, handler = _recorder(
        lambda _: httpx.Response(
            400, json={"error": {"message": "context length exceeded"}}
        )
    )
    with pytest.raises(ModelError, match="HTTP 400: context length exceeded"):
        _model(handler).chat(MESSAGES)
    assert len(bodies) == 1


def test_failure_after_the_retry_is_a_model_error() -> None:
    bodies, handler = _recorder(
        lambda _: httpx.Response(400, json={"error": {"message": "still bad"}})
    )
    with pytest.raises(ModelError, match="still bad"):
        _model(handler).chat(MESSAGES, json_schema=SCHEMA)
    assert len(bodies) == 2


def test_unreachable_server_names_the_provider() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(
        ModelError, match=r"Could not reach Ollama at http://127\.0\.0\.1:1234/v1"
    ):
        _model(refuse, provider="ollama").chat(MESSAGES)


def test_timeout_is_reported_as_such() -> None:
    def stall(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ModelError, match="did not answer within 300 seconds"):
        _model(stall).chat(MESSAGES)


def test_unknown_model_says_so() -> None:
    with pytest.raises(ModelError, match="has no model named 'm-1'"):
        _model(
            lambda _: httpx.Response(404, json={"error": {"message": "not found"}})
        ).chat(MESSAGES)


def test_empty_content_becomes_an_empty_reply() -> None:
    assert _model(lambda _: _completion(None)).chat(MESSAGES).content == ""


def _listing(handler: Handler) -> list[str]:
    return list_models(
        BASE, http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_list_models_skips_embedding_models() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == f"{BASE}/models"
        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {"id": "text-embedding-nomic-embed-text-v1.5"},
                    {"id": "qwen3-8b"},
                    {"id": "gemma-3-4b"},
                ],
            },
        )

    assert _listing(answer) == ["qwen3-8b", "gemma-3-4b"]


def test_list_models_skips_blank_ids() -> None:
    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"data": [{"id": ""}, {"id": "  "}, {"id": "qwen3-8b"}]}
        )

    assert _listing(answer) == ["qwen3-8b"]


def test_list_models_reports_an_unreachable_server() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ModelError, match="No answer from"):
        _listing(refuse)


def test_list_models_reports_http_errors() -> None:
    with pytest.raises(ModelError, match="No answer from"):
        _listing(lambda _: httpx.Response(500, text="boom"))


def test_list_models_rejects_an_answer_that_is_not_a_model_list() -> None:
    with pytest.raises(ModelError, match="did not return a model list"):
        _listing(lambda _: httpx.Response(200, json={"hello": "world"}))


def test_an_html_answer_is_a_model_error() -> None:
    page = httpx.Response(200, html="<html>Not an API</html>")
    with pytest.raises(ModelError, match="did not return a chat completion"):
        _model(lambda _: page).chat(MESSAGES)


def test_json_content_type_with_a_non_json_body_is_a_model_error() -> None:
    broken = httpx.Response(
        200, content=b"not json", headers={"content-type": "application/json"}
    )
    with pytest.raises(ModelError, match="did not return a chat completion"):
        _model(lambda _: broken).chat(MESSAGES)


def test_a_choice_without_a_message_is_a_model_error() -> None:
    reply = httpx.Response(
        200,
        json={
            "id": "c1",
            "object": "chat.completion",
            "created": 0,
            "model": "m-1",
            "choices": [{"index": 0, "message": None, "finish_reason": "stop"}],
        },
    )
    with pytest.raises(ModelError, match="did not return a chat completion"):
        _model(lambda _: reply).chat(MESSAGES)
