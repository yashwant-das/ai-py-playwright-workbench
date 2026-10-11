"""The Python library and the npm test runner must stay on one Playwright."""

import json
import re
import sys
import tomllib
from importlib.metadata import version
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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


def test_the_release_version_is_the_same_everywhere() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text("utf-8"))
    pkg = json.loads((PROJECT_ROOT / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((PROJECT_ROOT / "package-lock.json").read_text(encoding="utf-8"))
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    versions = {
        pyproject["project"]["version"],
        pkg["version"],
        lock["version"],
        lock["packages"][""]["version"],
        version("ai-py-playwright-workbench"),
    }
    assert versions == {"2.0.0"}
    assert re.search(r"^## \[2\.0\.0\] - \d{4}-\d{2}-\d{2}$", changelog, re.MULTILINE)
