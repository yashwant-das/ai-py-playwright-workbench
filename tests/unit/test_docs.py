"""The documentation set in the v2 spec (section 9) exists, and what it points at is real."""

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
