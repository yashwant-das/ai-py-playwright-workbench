"""Lets a run stop waiting for a model that is still answering.

A local model can take minutes to answer, and a blocking HTTP call cannot be
interrupted from outside. ``cancellable()`` runs the call on a background
thread and gives up waiting the moment the run is cancelled; the abandoned
call finishes (or times out) in the background and its answer is dropped.
"""

import threading
from typing import Any

from workbench.llm.chat import ChatModel, ChatReply, Message, ModelError


class ModelCancelled(ModelError):
    """The run was cancelled while a model call was in flight."""


class _CancellableModel:
    def __init__(self, model: ChatModel, cancel: threading.Event, poll_s: float):
        self._model, self._cancel, self._poll_s = model, cancel, poll_s

    def __getattr__(self, name: str) -> Any:
        # Only reached for names not found on the wrapper: forward to the model.
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._model, name)

    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> ChatReply:
        if self._cancel.is_set():
            raise ModelCancelled("Cancelled")
        done = threading.Event()
        reply: list[ChatReply] = []
        error: list[Exception] = []

        def call() -> None:
            try:
                reply.append(
                    self._model.chat(
                        messages, json_schema=json_schema, temperature=temperature
                    )
                )
            except Exception as exc:
                error.append(exc)
            finally:
                done.set()

        threading.Thread(target=call, name="model-call", daemon=True).start()
        while not done.wait(self._poll_s):
            if self._cancel.is_set():
                raise ModelCancelled("Cancelled")
        if error:
            raise error[0]
        return reply[0]


def cancellable(
    model: ChatModel, cancel: threading.Event, *, poll_s: float = 0.2
) -> ChatModel:
    """``model`` whose ``chat()`` raises ``ModelCancelled`` as soon as ``cancel`` is set."""
    return _CancellableModel(model, cancel, poll_s)
