"""cancellable(): a model call that gives way as soon as the run is cancelled."""

import threading
import time
from typing import Any

import pytest

from workbench.llm import ModelCancelled, ModelError, cancellable
from workbench.llm.chat import ChatReply

MESSAGES = [{"role": "user", "content": "hi"}]


class BlockedModel:
    """Its call does not return until the test opens the gate."""

    provider = "fake-provider"

    def __init__(self) -> None:
        self.gate = threading.Event()
        self.entered = threading.Event()

    def chat(self, messages: Any, *, json_schema: Any = None, temperature: float = 0.1):
        self.entered.set()
        self.gate.wait(10)
        return ChatReply(content="late", model="m", provider="fake")


class QuickModel:
    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.seen: dict[str, Any] = {}

    def chat(self, messages: Any, *, json_schema: Any = None, temperature: float = 0.1):
        self.seen = {"messages": messages, "schema": json_schema, "t": temperature}
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def test_cancelling_during_a_call_raises_at_once_while_the_call_is_still_running() -> (
    None
):
    model, cancel = BlockedModel(), threading.Event()
    wrapped = cancellable(model, cancel, poll_s=0.02)
    threading.Timer(0.05, cancel.set).start()
    started = time.monotonic()
    try:
        with pytest.raises(ModelCancelled, match="Cancelled"):
            wrapped.chat(MESSAGES)
        assert time.monotonic() - started < 1
        assert model.entered.is_set() and not model.gate.is_set()
    finally:
        model.gate.set()


def test_a_cancelled_run_never_starts_the_call() -> None:
    model, cancel = BlockedModel(), threading.Event()
    cancel.set()
    with pytest.raises(ModelCancelled):
        cancellable(model, cancel, poll_s=0.02).chat(MESSAGES)
    assert not model.entered.wait(0.1)


def test_a_reply_that_arrives_first_is_returned_unchanged() -> None:
    reply = ChatReply(content="ok", model="m", provider="p")
    model = QuickModel(reply)
    got = cancellable(model, threading.Event()).chat(
        MESSAGES, json_schema={"a": 1}, temperature=0.5
    )
    assert got is reply
    assert model.seen == {"messages": MESSAGES, "schema": {"a": 1}, "t": 0.5}


def test_the_inner_error_is_re_raised_unchanged() -> None:
    error = ModelError("Could not reach it")
    with pytest.raises(ModelError) as caught:
        cancellable(QuickModel(error), threading.Event()).chat(MESSAGES)
    assert caught.value is error and not isinstance(error, ModelCancelled)


def test_other_exceptions_pass_through_too() -> None:
    error = ValueError("odd")
    with pytest.raises(ValueError) as caught:
        cancellable(QuickModel(error), threading.Event()).chat(MESSAGES)
    assert caught.value is error


def test_the_wrapper_forwards_the_models_attributes() -> None:
    wrapped = cancellable(BlockedModel(), threading.Event())
    assert wrapped.provider == "fake-provider"  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        wrapped.missing  # type: ignore[attr-defined]  # noqa: B018
