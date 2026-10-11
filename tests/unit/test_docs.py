"""The documentation set in the v2 spec (section 9) exists, and what it points at is real."""

import json
import re

import pytest

from workbench.config import PROJECT_ROOT

ASSETS = PROJECT_ROOT / "docs" / "assets"
SCREENSHOTS = [
    "heal-healed.png",
    "heal-model-io.png",
    "heal-app-bug.png",
    "generate-passed.png",
]
MB = 1024 * 1024


def _read(name: str) -> str:
    return (PROJECT_ROOT / name).read_text(encoding="utf-8")


def test_the_demo_gif_is_a_real_recording_small_enough_for_a_readme() -> None:
    data = (ASSETS / "demo.gif").read_bytes()
    assert data[:6] == b"GIF89a"
    # Each frame starts with a graphic control extension; the 1.0 GIF had five.
    assert data.count(b"\x21\xf9\x04") > 20
    assert len(data) < 5 * MB


@pytest.mark.parametrize("name", SCREENSHOTS)
def test_screenshots_exist_and_are_not_huge(name: str) -> None:
    data = (ASSETS / name).read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(data) < 1.5 * MB


DOCS = [
    "README.md",
    "ROADMAP.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "AGENTS.md",
    "docs/architecture.md",
    "docs/decisions.md",
    "docs/development.md",
]
_FENCE = re.compile(r"^(`{3,})[^\n]*\n.*?^\1[ \t]*$", re.MULTILINE | re.DOTALL)
_LINK = re.compile(r"!?\[[^\]]*\]\(<?([^)\s>]+)>?[^)]*\)")
_NPM_SCRIPT = re.compile(r"npm run ([a-z][\w:-]*)")
_ELSEWHERE = ("http://", "https://", "mailto:", "#")


def _prose(name: str) -> str:
    """The document without its fenced code blocks."""
    return _FENCE.sub("", _read(name))


@pytest.mark.parametrize("name", DOCS)
def test_relative_links_resolve(name: str) -> None:
    folder = (PROJECT_ROOT / name).parent
    targets = [t for t in _LINK.findall(_prose(name)) if not t.startswith(_ELSEWHERE)]
    missing = [t for t in targets if not (folder / t.split("#")[0]).exists()]
    assert missing == []


@pytest.mark.parametrize("name", DOCS)
def test_npm_commands_in_the_docs_exist(name: str) -> None:
    scripts = json.loads(_read("package.json"))["scripts"]
    unknown = sorted(set(_NPM_SCRIPT.findall(_read(name))) - set(scripts))
    assert unknown == []


README_SECTIONS = [
    "## Why it exists",
    "## How it works",
    "## Quickstart",
    "## Using the app",
    "## Screenshots",
    "## How this compares to Playwright Test Agents",
    "## Tests and quality gates",
    "## Tech stack",
    "## Project structure",
    "## Documentation",
    "## License",
]


def test_readme_has_the_showcase_sections_in_order() -> None:
    readme = _read("README.md")
    positions = [readme.find(f"\n{heading}\n") for heading in README_SECTIONS]
    assert -1 not in positions
    assert positions == sorted(positions)


def test_readme_shows_the_gif_before_the_first_section_and_every_screenshot() -> None:
    readme = _read("README.md")
    assert "docs/assets/demo.gif" in readme.split("\n## ")[0]
    for name in SCREENSHOTS:
        assert f"docs/assets/{name}" in readme


def test_readme_says_the_recording_uses_the_demo_model() -> None:
    assert "Demo model" in _read("README.md").split("\n## ")[0]
