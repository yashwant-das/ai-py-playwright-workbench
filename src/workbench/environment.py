"""Checks for the external tools the workbench depends on."""

import logging
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


def node_available() -> bool:
    """True when Node.js is on the PATH (needed for the ts-morph AST repair)."""
    return shutil.which("node") is not None


def chromium_installed() -> bool:
    """True when Playwright's Chromium build is on disk."""
    try:
        with sync_playwright() as playwright:
            return Path(playwright.chromium.executable_path).exists()
    except Exception as exc:
        logger.debug("Could not locate Chromium: %s", exc)
        return False
