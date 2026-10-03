"""Runtime output lives under one workspace folder; runs get readable ids."""

from datetime import datetime
from pathlib import Path

import pytest

from workbench import config
from workbench.ids import new_run_id, slugify


def test_workspace_defaults_to_the_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.WORKSPACE_ENV, raising=False)
    assert config.workspace_dir() == config.PROJECT_ROOT / "workspace"


def test_workspace_can_be_redirected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path))
    assert config.workspace_dir() == tmp_path.resolve()


def test_workspace_subfolders_are_created_on_demand(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))
    folders = [config.runs_dir(), config.reports_dir(), config.specs_dir()]
    assert [f.name for f in folders] == ["runs", "reports", "specs"]
    assert all(f.is_dir() and f.parent == (tmp_path / "ws").resolve() for f in folders)


def test_workspace_playwright_config_ships_with_the_repo() -> None:
    assert config.WORKSPACE_PLAYWRIGHT_CONFIG.is_file()


@pytest.mark.parametrize(
    ("text", "slug"),
    [
        ("A user logs in!", "a-user-logs-in"),
        ("contact.spec.ts", "contact-spec-ts"),
        ("   ", "spec"),
        ("x" * 60, "x" * 40),
        ("aaaa " * 20, "aaaa-aaaa-aaaa-aaaa-aaaa-aaaa-aaaa-aaaa"),
    ],
)
def test_slugify(text: str, slug: str) -> None:
    assert slugify(text) == slug


def test_run_ids_sort_by_time_and_name_the_run() -> None:
    stamp = datetime(2026, 10, 3, 14, 5, 9)
    assert new_run_id("heal", "Contact form", now=stamp) == (
        "20261003-140509-heal-contact-form"
    )
