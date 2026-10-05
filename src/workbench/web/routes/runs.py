"""A run's live event stream, its cancel button, and the hand-over to its report."""

import asyncio
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse

from workbench.runs import Run, RunRegistry
from workbench.web.sse import RunStream, sse_message
from workbench.web.templating import templates

router = APIRouter()
POLL_S = 0.1
CLOCK_S = 1.0


def _run(request: Request, run_id: str) -> Run:
    registry: RunRegistry = request.app.state.runs
    run = registry.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No such run")
    return run


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, request: Request) -> StreamingResponse:
    run = _run(request, run_id)
    stream = RunStream(run)

    async def messages() -> AsyncIterator[str]:
        last_clock = 0.0
        while True:
            if await request.is_disconnected():
                return
            for message in stream.pending():
                yield message
            if run.finished and not run.events_after(stream.sent):
                yield stream.done()
                return
            now = time.monotonic()
            if now - last_clock >= CLOCK_S:
                yield sse_message("clock", stream.clock())
                last_clock = now
            await asyncio.sleep(POLL_S)

    return StreamingResponse(
        messages(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.post("/runs/{run_id}/cancel", response_class=HTMLResponse)
def cancel_run(run_id: str, request: Request) -> HTMLResponse:
    _run(request, run_id).cancel.set()
    return HTMLResponse(
        '<button class="btn btn--secondary" type="button" disabled>Cancelling…</button>'
    )


@router.get("/runs/{run_id}/result", response_model=None)
def run_result(run_id: str, request: Request) -> Response:
    run = _run(request, run_id)
    if run.report_id:
        return Response(
            status_code=200, headers={"HX-Redirect": f"/reports/{run.report_id}"}
        )
    return templates.TemplateResponse(request, "partials/run_done.html", {"run": run})
