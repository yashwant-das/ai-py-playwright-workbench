"""Shared fixtures for the integration suite (real Chromium, no real model)."""

import os
import threading
from collections.abc import Iterator
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from workbench import config

SITE_DIR = config.SAMPLE_SITE_DIR
# Fixed so specs written by tests can hard-code the URL.
SITE_PORT = int(os.environ.get("E2E_SITE_PORT", "4173"))
SITE_URL = f"http://127.0.0.1:{SITE_PORT}/"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate runtime output; CI sets WORKBENCH_WORKSPACE to keep it as an artifact."""
    if not os.environ.get(config.WORKSPACE_ENV):
        monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "workspace"))
    return config.workspace_dir()


@pytest.fixture(scope="session")
def site() -> Iterator[str]:
    handler = partial(_QuietHandler, directory=str(SITE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", SITE_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield SITE_URL
    server.shutdown()
    server.server_close()
