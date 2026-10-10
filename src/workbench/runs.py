"""Runs heals and generations in a background thread, one at a time.

The web app starts a run here and streams its events to the browser. Events
are kept, so a reloaded page or a second tab can replay them from the start.
"""

import logging
import secrets
import threading
import time
from collections.abc import Callable
from typing import Literal

from workbench.events import Emit
from workbench.models.events import RunEvent
from workbench.reports import Report

logger = logging.getLogger(__name__)

RunKind = Literal["heal", "generate"]
Job = Callable[[Emit, threading.Event], Report]


class Run:
    """One heal or generation: its events so far, and how it ended."""

    def __init__(
        self,
        kind: RunKind,
        label: str,
        model_label: str = "",
        steps: tuple[str, ...] = (),
    ) -> None:
        self.id = secrets.token_hex(6)
        self.kind: RunKind = kind
        self.label = label
        self.model_label = model_label
        self.steps = steps
        self.cancel = threading.Event()
        self.report_id: str | None = None
        self.error = ""
        self._events: list[RunEvent] = []
        self._lock = threading.Lock()
        self._finished = threading.Event()
        self._started = time.monotonic()

    def add(self, event: RunEvent) -> None:
        """Record an event (the pipeline's ``emit``)."""
        with self._lock:
            self._events.append(event)

    def events_after(self, count: int) -> list[RunEvent]:
        """Events after the first ``count``, in order."""
        with self._lock:
            return list(self._events[count:])

    @property
    def finished(self) -> bool:
        return self._finished.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        """Block until the run ends; False on timeout."""
        return self._finished.wait(timeout)

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self._started) * 1000)

    def finish(self, report_id: str | None, error: str = "") -> None:
        self.report_id, self.error = report_id, error
        self._finished.set()


class RunInProgress(RuntimeError):
    """Another run is still going."""

    def __init__(self, active: Run) -> None:
        super().__init__(f"A run is already in progress: {active.label}")
        self.active = active


class RunRegistry:
    """Starts runs and finds them again; keeps the latest ``keep`` runs."""

    def __init__(self, keep: int = 20) -> None:
        self._keep = keep
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()

    def start(
        self,
        kind: RunKind,
        label: str,
        job: Job,
        *,
        model_label: str = "",
        steps: tuple[str, ...] = (),
    ) -> Run:
        with self._lock:
            active = self._active()
            if active is not None:
                raise RunInProgress(active)
            run = Run(kind, label, model_label, steps)
            self._runs[run.id] = run
            for old in list(self._runs)[: -self._keep]:
                del self._runs[old]
        threading.Thread(target=self._execute, args=(run, job), daemon=True).start()
        return run

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

    def active(self) -> Run | None:
        with self._lock:
            return self._active()

    def latest_finished(self, kind: RunKind) -> Run | None:
        """The most recent finished run of that kind that saved a report."""
        with self._lock:
            return next(
                (
                    run
                    for run in reversed(self._runs.values())
                    if run.kind == kind and run.finished and run.report_id
                ),
                None,
            )

    def stop(self, timeout: float = 0.0) -> bool:
        """Cancel the active run and wait up to ``timeout`` seconds for it to end.

        True when no run is left going. The app calls this as it shuts down.
        """
        run = self.active()
        if run is None:
            return True
        run.cancel.set()
        return run.wait(timeout)

    def _active(self) -> Run | None:
        return next((r for r in self._runs.values() if not r.finished), None)

    @staticmethod
    def _execute(run: Run, job: Job) -> None:
        try:
            report = job(run.add, run.cancel)
        except Exception as exc:  # the UI shows it; the slot must be freed
            logger.exception("Run %s (%s) crashed", run.id, run.label)
            run.finish(None, f"{type(exc).__name__}: {exc}")
        else:
            run.finish(report.id)
