"""What every full page needs: the model, the active run, and the browser check."""

from typing import Any, Literal

from fastapi import Request

from workbench.samples import SAMPLES


def browsers_ready(request: Request) -> bool:
    """Chromium check: once at first use, and again on every call while it is missing."""
    state = request.app.state
    if getattr(state, "browsers_ok", False) is not True:
        state.browsers_ok = bool(state.services.browsers_ready())
    return bool(state.browsers_ok)


def page_context(request: Request, page: Literal["heal", "generate"]) -> dict[str, Any]:
    runs = request.app.state.runs
    running = runs.active()
    # ``?run=<id>`` keeps a run on screen after it finishes, until its stream
    # hands over to the report; ``busy`` still only counts a run in progress.
    shown = runs.get(request.query_params.get("run", ""))
    if shown is None or shown.kind != page:
        shown = running
    return {
        "page": page,
        "model": request.app.state.model.view(),
        "active": shown,
        "busy": running is not None,
        "browsers_ok": browsers_ready(request),
        "samples": list(SAMPLES.values()),
        "base_url": request.app.state.base_url,
        "result": None,
        "form": {},
    }
