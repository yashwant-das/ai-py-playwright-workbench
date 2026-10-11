"""Shared fixtures for the unit suite."""

from pathlib import Path

import pytest

from workbench import config


@pytest.fixture
def web_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh workspace for tests that start the web app."""
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))
    return config.workspace_dir()
