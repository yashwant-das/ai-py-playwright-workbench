"""EventSink numbers events and stamps their elapsed time."""

from workbench.events import EventSink
from workbench.models.events import RunEvent


def test_events_are_numbered_and_typed() -> None:
    seen: list[RunEvent] = []
    sink = EventSink("run-1", seen.append)
    sink.step("run", "active", "npx playwright test a.spec.ts")
    sink.log("hello")
    sink.attempt(1, "healed")
    sink.done("healed")

    assert [e.seq for e in seen] == [1, 2, 3, 4]
    assert [e.kind for e in seen] == ["step", "log", "attempt", "done"]
    assert (seen[0].step, seen[0].state) == ("run", "active")
    assert seen[2].detail == "Attempt 1: healed"
    assert seen[3].detail == "healed"
    assert all(e.run_id == "run-1" and e.elapsed_ms >= 0 for e in seen)


def test_sink_without_a_listener_discards_events() -> None:
    assert EventSink("run-2").done("error").seq == 1
