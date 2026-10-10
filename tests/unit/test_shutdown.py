"""Stopping the app: the active run is cancelled first, and the server cannot hang."""

import threading
import time
from pathlib import Path

import pytest

from tests.unit.web_support import heal_report, make_client
from workbench import config
from workbench.__main__ import SHUTDOWN_TIMEOUT_S, build_server
from workbench.app import create_app
from workbench.models.heal import HealReport
from workbench.reports import load_report, save_report

pytestmark = pytest.mark.usefixtures("web_workspace")


def test_shutdown_cancels_the_active_run_and_waits_for_its_report() -> None:
    client = make_client()
    started = threading.Event()
    saw_cancel: list[bool] = []

    def job(emit, cancel) -> HealReport:  # type: ignore[no-untyped-def]
        started.set()
        saw_cancel.append(cancel.wait(5))
        report = heal_report(status="cancelled")
        save_report(report)
        return report

    with client:  # startup on enter, shutdown on exit
        run = client.app.state.runs.start("heal", "contact-form.spec.ts", job)  # type: ignore[attr-defined]
        assert started.wait(5)
        assert not run.cancel.is_set()
    # No waiting here: shutdown itself must have seen the run through.
    assert saw_cancel == [True]
    assert run.finished
    assert load_report(run.report_id).status == "cancelled"


def test_shutdown_returns_at_once_when_nothing_is_running() -> None:
    client = make_client()
    began = time.monotonic()
    with client:
        assert client.get("/healthz").status_code == 200
    assert time.monotonic() - began < 2


def test_shutdown_leaves_a_finished_run_alone() -> None:
    client = make_client()
    report = heal_report()

    def job(emit, cancel) -> HealReport:  # type: ignore[no-untyped-def]
        save_report(report)
        return report

    with client:
        run = client.app.state.runs.start("heal", "x", job)  # type: ignore[attr-defined]
        assert run.wait(5)
    assert not run.cancel.is_set()
    assert run.report_id == report.id


def test_the_server_cannot_be_held_open_by_a_stuck_connection(
    web_workspace: Path,
) -> None:
    server = build_server(create_app(port=8123), 8123)
    assert server.config.timeout_graceful_shutdown == SHUTDOWN_TIMEOUT_S == 10
    assert server.config.host == config.HOST == "127.0.0.1"
    assert server.config.port == 8123
