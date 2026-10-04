"""Filesystem locations used across the workbench.

Every module gets paths from here instead of counting parent directories,
so moving a module never breaks a path. Runtime output lives under one
workspace folder, which ``WORKBENCH_WORKSPACE`` can redirect (tests and CI).
"""

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]

PROMPTS_DIR = PACKAGE_DIR / "prompts"
AST_REPAIR_SCRIPT = PACKAGE_DIR / "heal" / "ast_repair.js"
WORKSPACE_PLAYWRIGHT_CONFIG = PROJECT_ROOT / "playwright.workspace.config.ts"
WORKSPACE_ENV = "WORKBENCH_WORKSPACE"


def workspace_dir() -> Path:
    """Root of all runtime output (git-ignored)."""
    override = os.environ.get(WORKSPACE_ENV)
    return Path(override).resolve() if override else PROJECT_ROOT / "workspace"


def _subdir(name: str) -> Path:
    path = workspace_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def runs_dir() -> Path:
    """Per-run Playwright output: JSON report, screenshot, error context, video."""
    return _subdir("runs")


def reports_dir() -> Path:
    """One JSON report per heal or generate run."""
    return _subdir("reports")


def specs_dir() -> Path:
    """Generated specs, and copies of uploaded or sample specs."""
    return _subdir("specs")
