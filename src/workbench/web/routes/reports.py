"""A finished run's page, rendered from its saved report."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse

from workbench.config import runs_dir
from workbench.models.generate import GenerateReport
from workbench.models.heal import HealReport
from workbench.reports import report_path
from workbench.web.pages import page_context
from workbench.web.results import generate_context, heal_context, load_or_none
from workbench.web.templating import templates

router = APIRouter()


def not_found(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "not_found.html", page_context(request, "heal"), status_code=404
    )


def _found(report_id: str) -> HealReport | GenerateReport:
    report = load_or_none(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No such report")
    return report


def _attachment(name: str) -> str:
    safe = Path(name).name.replace('"', "") or "spec.ts"
    return f'attachment; filename="{safe}"'


# The download routes sit above report_page: otherwise /reports/<id>.json matches it.
@router.get("/reports/{report_id}.json")
def report_json(report_id: str) -> FileResponse:
    _found(report_id)
    return FileResponse(
        report_path(report_id),
        media_type="application/json",
        filename=f"{report_id}.json",
    )


@router.get("/reports/{report_id}/spec")
def report_spec(report_id: str) -> Response:
    report = _found(report_id)
    if isinstance(report, HealReport):
        code = report.final_code or report.original_code
    else:
        code = report.code
    if not code:
        raise HTTPException(status_code=404, detail="This run has no spec")
    return Response(
        code,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": _attachment(report.spec_name)},
    )


@router.get("/reports/{report_id}/video")
def report_video(report_id: str, attempt: int = 1) -> FileResponse:
    report = _found(report_id)
    found = (
        next((a for a in report.attempts if a.number == attempt), None)
        if isinstance(report, HealReport)
        else None
    )
    recorded = found.rerun.video_path if found is not None and found.rerun else None
    if not recorded:
        raise HTTPException(status_code=404, detail="No video for this attempt")
    path = Path(recorded).resolve()
    if not path.is_relative_to(runs_dir().resolve()) or not path.is_file():
        raise HTTPException(status_code=404, detail="No video for this attempt")
    return FileResponse(
        path, media_type="video/webm", content_disposition_type="inline"
    )


@router.get("/reports/{report_id}", response_class=HTMLResponse)
def report_page(
    report_id: str, request: Request, attempt: int | None = None, tab: str = ""
) -> HTMLResponse:
    report = load_or_none(report_id)
    if isinstance(report, HealReport):
        context = page_context(request, "heal")
        context["result"] = heal_context(report, attempt=attempt, tab=tab)
        return templates.TemplateResponse(request, "heal.html", context)
    if isinstance(report, GenerateReport):
        context = page_context(request, "generate")
        context["examples"] = {}
        context["result"] = generate_context(report)
        context["form"] = {
            "url": report.url,
            "scenario": report.scenario,
            "run_after": True,
        }
        return templates.TemplateResponse(request, "generate.html", context)
    return not_found(request)
