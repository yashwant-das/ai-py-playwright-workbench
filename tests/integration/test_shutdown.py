"""Ctrl+C on the real server during a run: the run is cancelled and the server exits."""

import signal
import socket
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field

import pytest
import uvicorn

from workbench.__main__ import build_server
from workbench.app import create_app
from workbench.events import Emit
from workbench.models.heal import HealReport
from workbench.reports import load_report, save_report
from workbench.runs import Run

# Well under the server's own 10 s limit: the run must be what lets it exit.
EXIT_WITHIN_S = 5


@dataclass
class Running:
    """A real server on a free port with one run that ends only when cancelled."""

    server: uvicorn.Server
    thread: threading.Thread
    port: int
    run: Run
    saw_cancel: list[bool] = field(default_factory=list)

    def request(self, path: str) -> socket.socket:
        conn = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        conn.sendall(
            f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n\r\n".encode()
        )
        return conn

    def press_ctrl_c(self) -> None:
        self.server.handle_exit(signal.SIGINT, None)


def _read_until(conn: socket.socket, marker: bytes) -> bytes:
    """Read until ``marker`` arrives; the socket's timeout bounds the wait."""
    data = b""
    while marker not in data:
        chunk = conn.recv(4096)
        if not chunk:
            raise AssertionError(f"closed before {marker!r}: {data!r}")
        data += chunk
    return data


def _read_to_end(conn: socket.socket) -> bytes:
    data = b""
    while chunk := conn.recv(4096):
        data += chunk
    return data


@pytest.fixture
def running() -> Iterator[Running]:
    # Bound and listening before the server starts, so a request can queue at once.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen()
    port = sock.getsockname()[1]
    app = create_app(port=port)
    server = build_server(app, port)
    started = threading.Event()
    saw_cancel: list[bool] = []

    def job(emit: Emit, cancel: threading.Event) -> HealReport:
        started.set()
        saw_cancel.append(cancel.wait(20))
        report = HealReport(
            id="20261011-120000-heal-shutdown",
            spec_name="contact-form.spec.ts",
            status="cancelled",
        )
        save_report(report)
        return report

    run = app.state.runs.start("heal", "contact-form.spec.ts", job)
    assert started.wait(5)
    thread = threading.Thread(target=server.run, args=([sock],), daemon=True)
    thread.start()
    try:
        yield Running(server, thread, port, run, saw_cancel)
    finally:
        run.cancel.set()
        server.should_exit = True
        thread.join(timeout=15)


def test_ctrl_c_with_the_live_stream_open_cancels_the_run_and_exits(
    running: Running,
) -> None:
    with running.request(f"/runs/{running.run.id}/events") as stream:
        _read_until(stream, b"event: clock")  # the tab is watching the run
        running.press_ctrl_c()
        running.thread.join(timeout=EXIT_WITHIN_S)
        assert not running.thread.is_alive()
        assert b"event: done" in _read_to_end(stream)
    assert running.saw_cancel == [True]
    assert running.run.finished
    assert load_report(running.run.report_id or "").status == "cancelled"


def test_ctrl_c_with_no_tab_open_still_cancels_the_run_first(running: Running) -> None:
    with running.request("/healthz") as conn:
        _read_until(conn, b'{"status":"ok"}')  # the server is up
    running.press_ctrl_c()
    running.thread.join(timeout=EXIT_WITHIN_S)
    assert not running.thread.is_alive()
    assert running.saw_cancel == [True]
    assert load_report(running.run.report_id or "").status == "cancelled"
