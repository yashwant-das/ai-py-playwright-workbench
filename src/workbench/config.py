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

SAMPLES_DIR = PROJECT_ROOT / "samples"
SAMPLE_SITE_DIR = SAMPLES_DIR / "site"
SAMPLE_SPECS_DIR = SAMPLES_DIR / "specs"
RECORDINGS_DIR = SAMPLES_DIR / "recordings"

WEB_DIR = PACKAGE_DIR / "web"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

HOST = "127.0.0.1"  # local tool: never listen on other interfaces
PORT_ENV = "WORKBENCH_PORT"
DEFAULT_PORT = 7860


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


def port() -> int:
    """The port the app listens on: ``WORKBENCH_PORT`` or 7860."""
    raw = os.environ.get(PORT_ENV, "").strip()
    if not raw:
        return DEFAULT_PORT
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{PORT_ENV} must be a port number, got {raw!r}") from None
    if not 1 <= value <= 65535:
        raise ValueError(f"{PORT_ENV} must be between 1 and 65535, got {value}")
    return value


def base_url(port_number: int | None = None) -> str:
    """The app's own address, built from the bind address (never a Host header)."""
    return f"http://{HOST}:{port_number or port()}"
