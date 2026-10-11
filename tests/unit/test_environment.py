"""Checks for the external tools the workbench needs."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from workbench import environment


def test_node_available_follows_the_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(environment.shutil, "which", lambda name: "/usr/bin/node")
    assert environment.node_available()
    monkeypatch.setattr(environment.shutil, "which", lambda name: None)
    assert not environment.node_available()


def test_chromium_installed_checks_the_executable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    exe = tmp_path / "chrome"
    playwright = MagicMock()
    playwright.__enter__.return_value.chromium.executable_path = str(exe)
    monkeypatch.setattr(environment, "sync_playwright", lambda: playwright)
    assert not environment.chromium_installed()
    exe.write_text("", encoding="utf-8")
    assert environment.chromium_installed()


def test_chromium_check_survives_a_broken_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> None:
        raise RuntimeError("driver missing")

    monkeypatch.setattr(environment, "sync_playwright", broken)
    assert not environment.chromium_installed()
