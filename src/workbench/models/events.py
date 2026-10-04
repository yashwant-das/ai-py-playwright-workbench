"""Progress events a pipeline emits; the web UI streams them over SSE."""

from typing import Literal

from pydantic import BaseModel, Field

EventKind = Literal["step", "log", "attempt", "done"]
StepName = Literal[
    "run", "evidence", "diagnose", "repair", "verify", "context", "model", "execute"
]
StepState = Literal["pending", "active", "done", "failed", "skipped"]


class RunEvent(BaseModel):
    """One progress update from a running pipeline."""

    run_id: str
    seq: int = Field(ge=1)
    kind: EventKind
    step: StepName | None = None
    state: StepState | None = None
    detail: str = ""
    elapsed_ms: int = Field(default=0, ge=0)
