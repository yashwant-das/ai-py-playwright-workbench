"""Generation: page context in, a runnable Playwright spec out."""

import threading
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from workbench.config import runs_dir, specs_dir
from workbench.context import collect_context
from workbench.environment import chromium_installed
from workbench.events import Emit, EventSink
from workbench.heal.evidence import Collect
from workbench.ids import new_run_id, slugify
from workbench.llm.chat import ChatModel, ModelError
from workbench.llm.parsing import extract_code_block
from workbench.llm.prompts import (
    get_prompt_hash,
    get_prompt_version,
    load_prompt,
    render_prompt,
)
from workbench.models.generate import (
    ContextSummary,
    GenerateReport,
    GenerateStatus,
    GenerationResult,
)
from workbench.models.shared import ModelExchange, Provenance, RunResult
from workbench.reports import save_report
from workbench.runner import run_test
from workbench.validation import (
    ValidationError,
    validate_and_sanitize_url,
    validate_description,
)

Run = Callable[..., RunResult]

LIMITS = {
    "Target URL": 500,
    "Scenario": 1_000,
    "Page snapshot": 12_000,
    "Locator candidates": 2_000,
    "Console errors": 2_000,
}


class GenerateRequest(BaseModel):
    """What to generate a test for."""

    url: str
    scenario: str
    run_after: bool = True


def generate(
    request: GenerateRequest,
    *,
    model: ChatModel,
    emit: Emit | None = None,
    cancel: threading.Event | None = None,
    run: Run = run_test,
    collect: Collect = collect_context,
    browsers_ready: Callable[[], bool] = chromium_installed,
) -> GenerateReport:
    """Generate a spec for ``request``, optionally run it, and return the saved report."""
    report = GenerateReport(
        id=new_run_id("generate", request.scenario),
        url=request.url,
        scenario=request.scenario,
        status="error",
    )
    events = EventSink(report.id, emit)
    cancel = cancel or threading.Event()
    started = time.monotonic()

    def finish(status: GenerateStatus, error_message: str = "") -> GenerateReport:
        report.status = status
        if error_message:
            report.error_message = error_message
        report.duration_ms = int((time.monotonic() - started) * 1000)
        save_report(report)
        events.done(status)
        return report

    try:
        url = validate_and_sanitize_url(request.url)
        scenario = validate_description(request.scenario)
    except ValidationError as exc:
        return finish("error", str(exc))
    if not browsers_ready():
        report.warnings = ["playwright_browsers_missing"]
        return finish(
            "error",
            "Playwright's Chromium is not installed. Run: npx playwright install chromium",
        )

    events.step("context", "active", url)
    page = collect(url)
    if page.is_empty:
        events.step("context", "failed", f"Could not load {url}")
        return finish("error", f"Could not load {url}.")
    report.context = ContextSummary(
        url=url,
        snapshot_lines=len((page.aria_snapshot or "").splitlines()),
        locator_candidates=list(page.locator_candidates),
        console_errors=len(page.console_errors),
        failed_requests=len(page.network_errors),
    )
    events.step("context", "done", f"{len(page.locator_candidates)} locator candidates")

    if cancel.is_set():
        return finish("cancelled")

    events.step("model", "active")
    sections = [
        ("Target URL", url),
        ("Scenario", scenario),
        ("Page snapshot", page.aria_snapshot or ""),
        ("Locator candidates", "\n".join(f"- {c}" for c in page.locator_candidates)),
        ("Console errors", "\n".join(page.console_errors)),
    ]
    user, records = render_prompt([(n, c) for n, c in sections if c.strip()], LIMITS)
    try:
        reply = model.chat(
            [
                {"role": "system", "content": load_prompt("generator")},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
        )
    except ModelError as exc:
        events.step("model", "failed", _first_line(str(exc)))
        return finish("error", f"The model call failed: {exc}")
    exchange = ModelExchange(
        sections=records,
        raw_response=reply.content,
        provenance=Provenance(
            provider=reply.provider,
            model=reply.model,
            prompt_name="generator",
            prompt_version=get_prompt_version("generator"),
            prompt_hash=get_prompt_hash("generator"),
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            latency_ms=reply.latency_ms,
        ),
    )
    report.exchange = exchange
    if cancel.is_set():
        # A slow local model may answer after the user gave up: write and run nothing.
        events.step("model", "skipped", "Cancelled")
        return finish("cancelled")
    try:
        code = GenerationResult(code=extract_code_block(reply.content)).code
    except ValueError as exc:
        exchange.validation_error = str(exc)[:500]
        events.step("model", "failed", "The reply contained no code")
        return finish("error", "The model returned no code.")
    exchange.valid = True

    spec = _free_path(specs_dir(), slugify(scenario))
    spec.write_text(code + "\n", encoding="utf-8")
    report.spec_name, report.code = spec.name, code
    events.step("model", "done", f"{len(code.splitlines())} lines → {spec.name}")

    if not request.run_after:
        return finish("not_run")
    if cancel.is_set():
        return finish("cancelled")
    events.step("execute", "active", f"npx playwright test {spec.name}")
    result = run(spec, runs_dir() / report.id, cancel=cancel)
    report.run = result
    if result.status == "cancelled":
        events.step("execute", "skipped", "Cancelled")
        return finish("cancelled")
    if result.status == "error":
        events.step("execute", "failed", _first_line(result.error_message))
        return finish("error", result.error_message)
    if result.passed:
        events.step("execute", "done", result.status)
        return finish("passed")
    events.step("execute", "failed", _first_line(result.error_message) or result.status)
    return finish("failed")


def _first_line(text: str) -> str:
    lines = text.strip().splitlines()
    return lines[0][:200] if lines else ""


def _free_path(folder: Path, slug: str) -> Path:
    path = folder / f"{slug}.spec.ts"
    number = 2
    while path.exists():
        path = folder / f"{slug}-{number}.spec.ts"
        number += 1
    return path
