"""The Python library and the npm test runner must stay on one Playwright."""

import json
import sys
from importlib.metadata import version
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_python_is_3_13_or_newer() -> None:
    assert sys.version_info >= (3, 13)


def test_playwright_python_and_npm_versions_match() -> None:
    pkg = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
    npm_versions = {
        pkg["devDependencies"]["@playwright/test"],
        pkg["dependencies"]["playwright"],
        pkg["dependencies"]["playwright-core"],
    }
    assert npm_versions == {version("playwright")} == {"1.63.0"}
