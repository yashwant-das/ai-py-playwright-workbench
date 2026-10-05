"""The Heal page, and starting a heal from a sample, an upload or a generated test."""

import threading
from html import escape
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from workbench.config import specs_dir
from workbench.events import Emit
from workbench.heal import HealRequest
from workbench.models.generate import GenerateReport
from workbench.models.heal import HealReport
from workbench.reports import load_report
from workbench.runs import Run, RunInProgress, RunRegistry
from workbench.samples import install_sample
from workbench.validation import MAX_SPEC_BYTES, ValidationError, validate_spec_upload
from workbench.web.pages import browsers_ready, page_context
from workbench.web.services import Services
from workbench.web.templating import templates
from workbench.web.uploads import store_upload
from workbench.web.views import HEAL_STEPS

router = APIRouter()


class _Refused(Exception):
    def __init__(self, target: str, message: str) -> None:
        super().__init__(message)
        self.target = target


def refuse(target: str, message: str) -> HTMLResponse:
    """A 422 whose message HTMX swaps into the element ``#target``."""
    return HTMLResponse(
        escape(message, quote=False),
        status_code=422,
        headers={"HX-Retarget": f"#{target}", "HX-Reswap": "innerHTML"},
    )


def busy_notice(request: Request, active: Run) -> HTMLResponse:
    """A 409 shown in the page's notice area."""
    return templates.TemplateResponse(
        request,
        "partials/notice.html",
        {"active": active},
        status_code=409,
        headers={"HX-Retarget": "#notice", "HX-Reswap": "innerHTML"},
    )


@router.get("/heal", response_class=HTMLResponse)
def heal_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "heal.html", page_context(request, "heal")
    )


def _spec_for(
    request: Request, action: str, spec: UploadFile | None, generated: str
) -> Path:
    if action.startswith("sample:"):
        base = f"{request.app.state.base_url}/sample-site/"
        try:
            return install_sample(action.removeprefix("sample:"), base)
        except (ValueError, ValidationError) as exc:
            raise _Refused("sample-error", str(exc)) from exc
    if action == "upload":
        if spec is None or not spec.filename:
            raise _Refused("upload-error", "Choose a .spec.ts file first.")
        data = spec.file.read(MAX_SPEC_BYTES + 1)
        try:
            return store_upload(
                spec.filename, validate_spec_upload(spec.filename, data)
            )
        except ValidationError as exc:
            raise _Refused("upload-error", str(exc)) from exc
    if action == "generated":
        try:
            report = load_report(generated)
        except (ValueError, FileNotFoundError) as exc:
            raise _Refused(
                "sample-error", "That generated test no longer exists."
            ) from exc
        path = (
            specs_dir() / report.spec_name
            if isinstance(report, GenerateReport)
            else None
        )
        if path is None or not report.spec_name or not path.is_file():
            raise _Refused("sample-error", "That generated test no longer exists.")
        return path
    raise _Refused("sample-error", "Choose a sample or a file to heal.")


@router.post("/heal", response_class=HTMLResponse)
def start_heal(
    request: Request,
    action: str = Form(""),
    max_attempts: str = Form("3"),
    spec: Annotated[UploadFile | None, File()] = None,
    generated: str = Form(""),
) -> HTMLResponse:
    runs: RunRegistry = request.app.state.runs
    if (active := runs.active()) is not None:
        return busy_notice(request, active)
    try:
        attempts = int(max_attempts)
    except ValueError:
        attempts = 0
    if not 1 <= attempts <= 5:
        return refuse("attempts-error", "Choose between 1 and 5 attempts.")
    if not browsers_ready(request):
        return templates.TemplateResponse(request, "partials/browsers_missing.html", {})
    view = request.app.state.model.view()
    if not view.ready or view.choice is None:
        return templates.TemplateResponse(
            request, "partials/unreachable.html", {"model": view}
        )
    try:
        path = _spec_for(request, action, spec, generated)
    except _Refused as exc:
        return refuse(exc.target, str(exc))

    services: Services = request.app.state.services
    model = services.build_model(view.choice)

    def job(emit: Emit, cancel: threading.Event) -> HealReport:
        return services.heal(
            HealRequest(spec_path=path, max_attempts=attempts),
            model=model,
            emit=emit,
            cancel=cancel,
        )

    try:
        run = runs.start(
            "heal",
            path.name,
            job,
            model_label=view.model_label,
            steps=tuple(step.name for step in HEAL_STEPS),
        )
    except RunInProgress as exc:
        return busy_notice(request, exc.active)
    return templates.TemplateResponse(request, "partials/run_view.html", {"run": run})
