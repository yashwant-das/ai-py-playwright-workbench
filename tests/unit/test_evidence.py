"""Evidence comes from the failing run's error-context.md when it exists."""

from pathlib import Path

import pytest

from workbench.heal.evidence import (
    extract_url_from_code,
    gather_evidence,
    parse_error_context,
)
from workbench.models.artifacts import ContextSnapshot
from workbench.models.shared import RunResult

ERROR_CONTEXT = """# Instructions

- Following Playwright test failed.

# Error details

```
TimeoutError: locator.click: Timeout 2000ms exceeded.
```

# Page snapshot

```yaml
- generic [ref=e1]:
  - textbox "Name" [active] [ref=e2]: Ada
  - button "Submit" [ref=e3]
```

# Test source

```ts
  5 |   await page.locator("#submit-btn").click();
```
"""
CODE = 'test("x", async ({ page }) => {\n  await page.goto("http://127.0.0.1:4173/");\n});\n'


def _failed(error_context: Path | None = None) -> RunResult:
    return RunResult(
        status="failed",
        error_message="TimeoutError: locator.click",
        error_location="/w/a.spec.ts:5:37",
        screenshot_path="/w/shot.png",
        error_context_path=str(error_context) if error_context else None,
    )


def _never(url: str) -> ContextSnapshot:
    raise AssertionError(f"collect_context should not run for {url}")


@pytest.mark.parametrize(
    ("code", "url"),
    [
        ("await page.goto('https://example.com/foo');", "https://example.com/foo"),
        ('await page.goto("https://example.com/bar");', "https://example.com/bar"),
        ("await page.goto(`https://example.com/baz`);", "https://example.com/baz"),
        (
            'await page.goto("https://example.com/slow", { timeout: 5000 });',
            "https://example.com/slow",
        ),
        ("await page.click('#btn');", None),
        ("", None),
    ],
)
def test_extract_url_from_code(code: str, url: str | None) -> None:
    assert extract_url_from_code(code) == url


def test_parse_error_context_returns_the_page_snapshot() -> None:
    snapshot = parse_error_context(ERROR_CONTEXT)
    assert snapshot is not None
    assert snapshot.startswith("- generic [ref=e1]:")
    assert 'textbox "Name" [active] [ref=e2]: Ada' in snapshot
    assert "Test source" not in snapshot


def test_parse_error_context_without_a_snapshot() -> None:
    assert parse_error_context("# Error details\n\nboom\n") is None


def test_error_context_is_the_main_evidence(tmp_path: Path) -> None:
    path = tmp_path / "error-context.md"
    path.write_text(ERROR_CONTEXT, encoding="utf-8")

    evidence, warnings = gather_evidence(CODE, _failed(path), collect=_never)

    assert warnings == []
    assert evidence.source == "error_context"
    assert "Ada" in (evidence.page_snapshot or "")
    assert "getByRole('button', { name: 'Submit' })" in evidence.locator_candidates
    assert evidence.error_location == "/w/a.spec.ts:5:37"
    assert evidence.screenshot_path == "/w/shot.png"


def test_without_error_context_the_first_url_is_loaded() -> None:
    def collect(url: str) -> ContextSnapshot:
        assert url == "http://127.0.0.1:4173/"
        return ContextSnapshot(
            url=url,
            aria_snapshot='- button "Submit" [ref=e3]',
            locator_candidates=["getByRole('button', { name: 'Submit' })"],
            console_errors=["[ERROR] boom"],
            network_errors=["POST http://x/orders → 500"],
        )

    evidence, warnings = gather_evidence(CODE, _failed(), collect=collect)

    assert warnings == []
    assert evidence.source == "page_load"
    assert evidence.console_errors == ["[ERROR] boom"]
    assert evidence.network_errors == ["POST http://x/orders → 500"]


def test_no_context_at_all_is_flagged() -> None:
    evidence, warnings = gather_evidence(
        CODE, _failed(), collect=lambda url: ContextSnapshot(url=url)
    )
    assert evidence.source == "none"
    assert warnings == ["page_context_unavailable"]


def test_spec_without_a_url_is_flagged() -> None:
    evidence, warnings = gather_evidence(
        "test('x', () => {});", _failed(), collect=_never
    )
    assert evidence.source == "none"
    assert warnings == ["page_context_unavailable"]
