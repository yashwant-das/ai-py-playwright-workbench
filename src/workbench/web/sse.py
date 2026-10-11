"""Renders a run's events as server-sent events carrying HTML fragments.

HTMX's SSE extension swaps each fragment into the element whose ``sse-swap``
names the event, so the browser keeps no state of its own.
"""

from html import escape
from typing import Any

from workbench.models.events import RunEvent
from workbench.runs import Run
from workbench.web.templating import templates
from workbench.web.views import STEP_INFO, format_duration

THINKING_AFTER_MS = 30_000
_TONES = {"active": "step", "failed": "fail", "skipped": "muted", "done": ""}


def sse_message(event: str, html: str) -> str:
    """One SSE message; every line of ``html`` goes in its own ``data:`` field."""
    lines = html.splitlines() or [""]
    return f"event: {event}\n" + "".join(f"data: {line}\n" for line in lines) + "\n"


def _render(name: str, **context: Any) -> str:
    return templates.get_template(name).render(**context)


class RunStream:
    """One browser tab's view of a run: which events it has sent, and step timings."""

    def __init__(self, run: Run) -> None:
        self.run = run
        self.sent = 0
        self._started: dict[str, int] = {}
        self._active: str | None = None
        self._attempts = 0

    def pending(self) -> list[str]:
        """Messages for the events this tab has not seen yet."""
        messages: list[str] = []
        for event in self.run.events_after(self.sent):
            self.sent += 1
            messages += self._messages(event)
        return messages

    def _messages(self, event: RunEvent) -> list[str]:
        if event.kind == "step" and event.step and event.state:
            info = STEP_INFO[event.step]
            took = ""
            if event.state == "active":
                self._started[event.step] = event.elapsed_ms
                self._active = event.step
            else:
                if self._active == event.step:
                    self._active = None
                started = self._started.get(event.step)
                if started is not None:
                    took = format_duration(event.elapsed_ms - started)
            body = _render(
                "partials/step_body.html",
                info=info,
                state=event.state,
                detail=event.detail or info.description,
                time=took,
            )
            line = _render(
                "partials/log_line.html",
                tone=_TONES.get(event.state, ""),
                text=f"[{event.step}] {event.detail or info.title}",
            )
            return [sse_message(f"step-{event.step}", body), sse_message("log", line)]
        if event.kind == "attempt":
            self._attempts += 1
            return [
                sse_message(
                    "log",
                    _render("partials/log_line.html", tone="step", text=event.detail),
                )
            ]
        if event.kind == "log":
            return [
                sse_message(
                    "log",
                    _render("partials/log_line.html", tone="muted", text=event.detail),
                )
            ]
        return []  # the pipeline's own "done": the stream sends its own when the run ends

    def clock(self) -> str:
        """The run header's meta, as escaped HTML: attempt, elapsed time, hint, model.

        The model's name comes from the model server, and the browser swaps
        this in as markup.
        """
        parts = []
        if self.run.kind == "heal" and "evidence" in self._started:
            parts.append(f"Attempt {self._attempts + 1}")
        elapsed = self.run.elapsed_ms()
        parts.append(format_duration(elapsed))
        if self._active in ("diagnose", "model"):
            waited = elapsed - self._started.get(self._active, elapsed)
            if waited > THINKING_AFTER_MS:
                parts.append("the model is still thinking")
        if self.run.model_label:
            parts.append(self.run.model_label)
        return escape(" · ".join(parts), quote=False)

    def done(self) -> str:
        return sse_message("done", _render("partials/run_done.html", run=self.run))
