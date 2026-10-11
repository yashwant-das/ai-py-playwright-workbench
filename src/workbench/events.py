"""Numbers and timestamps the progress events a pipeline emits."""

import time
from collections.abc import Callable

from workbench.models.events import EventKind, RunEvent, StepName, StepState

Emit = Callable[[RunEvent], None]


def _discard(_event: RunEvent) -> None:
    return None


class EventSink:
    """Sends ``RunEvent``s to a listener, numbered from 1 with elapsed time."""

    def __init__(self, run_id: str, emit: Emit | None = None) -> None:
        self.run_id = run_id
        self._emit = emit or _discard
        self._seq = 0
        self._started = time.monotonic()

    def step(self, step: StepName, state: StepState, detail: str = "") -> RunEvent:
        """Report a pipeline step changing state."""
        return self._send("step", step=step, state=state, detail=detail)

    def log(self, text: str) -> RunEvent:
        """Report a free-text log line."""
        return self._send("log", detail=text)

    def attempt(self, number: int, outcome: str) -> RunEvent:
        """Report how a heal attempt ended."""
        return self._send("attempt", detail=f"Attempt {number}: {outcome}")

    def done(self, status: str) -> RunEvent:
        """Report the final status; the last event of a run."""
        return self._send("done", detail=status)

    def _send(
        self,
        kind: EventKind,
        *,
        step: StepName | None = None,
        state: StepState | None = None,
        detail: str = "",
    ) -> RunEvent:
        self._seq += 1
        event = RunEvent(
            run_id=self.run_id,
            seq=self._seq,
            kind=kind,
            step=step,
            state=state,
            detail=detail,
            elapsed_ms=int((time.monotonic() - self._started) * 1000),
        )
        self._emit(event)
        return event
