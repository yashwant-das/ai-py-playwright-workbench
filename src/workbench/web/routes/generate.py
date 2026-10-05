"""The Generate page, starting a generation, and running a generated spec."""

import threading

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from workbench.config import specs_dir
from workbench.events import Emit
from workbench.generate import GenerateRequest
from workbench.models.generate import GenerateReport
from workbench.runs import RunInProgress, RunRegistry
from workbench.samples import GENERATE_SCENARIO
from workbench.validation import (
    ValidationError,
    validate_and_sanitize_url,
    validate_description,
)
from workbench.web.jobs import run_generated
from workbench.web.pages import browsers_ready, page_context
from workbench.web.results import load_or_none
from workbench.web.routes.heal import busy_notice, refuse, refuse_in_notice
from workbench.web.services import Services
from workbench.web.templating import templates

router = APIRouter()

# label, page under /sample-site/, scenario. Demo can only answer the first.
EXAMPLES: dict[str, tuple[str, str, str]] = {
    "contact-form": ("Contact form", "", GENERATE_SCENARIO),
    "checkout": (
        "Checkout",
        "checkout.html",
        "A shopper enters their email and places an order",
    ),
}
GENERATE_STEP_NAMES = ("context", "model", "execute")
RUN_NOTICE_TITLE = "Can't run that test"


@router.get("/generate", response_class=HTMLResponse)
def generate_page(request: Request, example: str = "") -> HTMLResponse:
    context = page_context(request, "generate")
    context["examples"] = EXAMPLES
    if example in EXAMPLES:
        _, page, scenario = EXAMPLES[example]
        url = f"{request.app.state.base_url}/sample-site/{page}"
        context["form"] = {"url": url, "scenario": scenario, "run_after": True}
    return templates.TemplateResponse(request, "generate.html", context)


@router.post("/generate", response_class=HTMLResponse)
def start_generate(
    request: Request,
    url: str = Form(""),
    scenario: str = Form(""),
    run_after: str = Form(""),
) -> HTMLResponse:
    runs: RunRegistry = request.app.state.runs
    if (active := runs.active()) is not None:
        return busy_notice(request, active)
    try:
        clean_url = validate_and_sanitize_url(url)
    except ValidationError:
        return refuse(
            "url-error", "Enter a full URL, starting with http:// or https://"
        )
    try:
        clean_scenario = validate_description(scenario.strip())
    except ValidationError as exc:
        return refuse("scenario-error", str(exc))
    if not browsers_ready(request):
        return templates.TemplateResponse(request, "partials/browsers_missing.html", {})
    view = request.app.state.model.view()
    if not view.ready or view.choice is None:
        return templates.TemplateResponse(
            request, "partials/unreachable.html", {"model": view}
        )
    services: Services = request.app.state.services
    model = services.build_model(view.choice)
    generate_request = GenerateRequest(
        url=clean_url, scenario=clean_scenario, run_after=bool(run_after)
    )

    def job(emit: Emit, cancel: threading.Event) -> GenerateReport:
        return services.generate(
            generate_request, model=model, emit=emit, cancel=cancel
        )

    steps = (
        GENERATE_STEP_NAMES if generate_request.run_after else GENERATE_STEP_NAMES[:2]
    )
    try:
        runs.start(
            "generate", clean_scenario, job, model_label=view.model_label, steps=steps
        )
    except RunInProgress as exc:
        return busy_notice(request, exc.active)
    # Reload so the page renders the run and its locked start button.
    return HTMLResponse("", headers={"HX-Redirect": "/generate"})


@router.post("/generate/run", response_class=HTMLResponse)
def run_generated_spec(request: Request, report: str = Form("")) -> HTMLResponse:
    saved = load_or_none(report)
    if not isinstance(saved, GenerateReport) or not saved.spec_name:
        return refuse_in_notice(request, "No such generated test", RUN_NOTICE_TITLE)
    if not (specs_dir() / saved.spec_name).is_file():
        return refuse_in_notice(
            request, "The generated spec file is gone", RUN_NOTICE_TITLE
        )
    runs: RunRegistry = request.app.state.runs
    if (active := runs.active()) is not None:
        return busy_notice(request, active)
    if not browsers_ready(request):
        return templates.TemplateResponse(request, "partials/browsers_missing.html", {})
    run_test = request.app.state.services.run_test

    def job(emit: Emit, cancel: threading.Event) -> GenerateReport:
        return run_generated(saved, run_test=run_test, emit=emit, cancel=cancel)

    try:
        runs.start("generate", saved.spec_name, job, steps=("execute",))
    except RunInProgress as exc:
        return busy_notice(request, exc.active)
    return HTMLResponse("", headers={"HX-Redirect": "/generate"})
