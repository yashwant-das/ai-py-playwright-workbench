"""A finished run's page, rendered from its saved report."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from workbench.models.heal import HealReport
from workbench.web.pages import page_context
from workbench.web.results import heal_context, load_or_none
from workbench.web.templating import templates

router = APIRouter()


def not_found(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "not_found.html", page_context(request, "heal"), status_code=404
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
    return not_found(request)
