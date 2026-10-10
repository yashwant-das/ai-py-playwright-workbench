"""Helpers for the web route tests: a client with fake services, and canned runs."""

import threading
from dataclasses import replace
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response

from workbench.app import create_app
from workbench.events import Emit, EventSink
from workbench.ids import new_run_id
from workbench.models.heal import HealReport
from workbench.models.settings import DEMO_MODEL, ConnectionStatus
from workbench.reports import save_report
from workbench.runs import Job, Run
from workbench.web.services import Services

# The app only answers requests addressed to itself; TestClient's default is "testserver".
BASE_URL = "http://127.0.0.1:7860"


def _reachable(provider: str, base_url: str = "") -> ConnectionStatus:
    models = [DEMO_MODEL] if provider == "demo" else ["test-model"]
    return ConnectionStatus(
        provider=provider, base_url=base_url, reachable=True, models=models
    )  # type: ignore[arg-type]


def make_client(**overrides: Any) -> TestClient:
    """An app whose services are fakes unless overridden."""
    fakes: dict[str, Any] = {
        "detect": lambda: None,
        "check_connection": _reachable,
        "browsers_ready": lambda: True,
    }
    services = replace(Services(), **{**fakes, **overrides})
    return TestClient(create_app(services), base_url=BASE_URL)


def heal_report(**fields: Any) -> HealReport:
    values: dict[str, Any] = {
        "id": new_run_id("heal", "contact-form"),
        "spec_name": "contact-form.spec.ts",
        "status": "healed",
    }
    values.update(fields)
    return HealReport(**values)


def heal_job(report: HealReport, *, gate: threading.Event | None = None) -> Job:
    """A job that walks the five heal steps, optionally waiting on ``gate`` first."""

    def job(emit: Emit, cancel: threading.Event) -> HealReport:
        if gate is not None:
            gate.wait(5)
        events = EventSink(report.id, emit)
        events.step("run", "active", "npx playwright test contact-form.spec.ts")
        events.step(
            "run", "done", "TimeoutError: locator.click: Timeout 3000ms exceeded."
        )
        events.step("evidence", "active")
        events.step("evidence", "done", "Page snapshot from error-context.md")
        events.step("diagnose", "active", "Classifier hint: TIMEOUT")
        events.step("diagnose", "done", "LOCATOR_DRIFT (0.90)")
        events.step("repair", "active")
        events.step("repair", "done", "Selector replaced (ast)")
        events.step("verify", "active")
        events.step("verify", "done", "Re-run passed")
        events.attempt(1, "healed")
        events.done(report.status)
        save_report(report)
        return report

    return job


def started_run(client: TestClient, response: Response, page: str) -> Run:
    """The run a successful start redirects to: ``/<page>?run=<id>``."""
    location = response.headers["HX-Redirect"]
    prefix = f"/{page}?run="
    assert location.startswith(prefix), location
    run = client.app.state.runs.get(location.removeprefix(prefix))
    assert run is not None
    return run  # type: ignore[no-any-return]
