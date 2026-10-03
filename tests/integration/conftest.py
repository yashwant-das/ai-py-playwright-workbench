"""Shared fixtures for the integration suite (real Chromium, no real model)."""

import os
from pathlib import Path

import pytest

from workbench import config


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate runtime output; CI sets WORKBENCH_WORKSPACE to keep it as an artifact."""
    if not os.environ.get(config.WORKSPACE_ENV):
        monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "workspace"))
    return config.workspace_dir()
