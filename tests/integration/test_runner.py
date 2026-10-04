"""The runner against a real Playwright: reports, evidence files, video, cancel."""

import threading
import time
from pathlib import Path

from workbench.config import specs_dir
from workbench.runner import run_test

FORM = (
    "<label for=n>Name</label><input id=n>"
    "<button data-testid=submit>Submit</button><p role=status></p>"
)
HEADER = 'import { test, expect } from "@playwright/test";\n\n'


def _spec(name: str, body: str) -> Path:
    path = specs_dir() / name
    path.write_text(
        HEADER + f'test("{name}", async ({{ page }}) => {{\n'
        f"  await page.setContent(`{FORM}`);\n{body}\n}});\n",
        encoding="utf-8",
    )
    return path


def test_passing_spec() -> None:
    spec = _spec(
        "pass.spec.ts",
        '  await expect(page.getByRole("button", { name: "Submit" })).toBeVisible();',
    )
    result = run_test(spec)
    assert result.passed, result.output
    assert result.error_context_path is None


def test_failing_spec_points_at_its_own_evidence() -> None:
    spec = _spec(
        "drift.spec.ts",
        '  await page.getByLabel("Name").fill("Ada");\n'
        '  await page.locator("#submit-btn").click({ timeout: 2000 });',
    )
    result = run_test(spec)
    assert result.status == "failed"
    assert "#submit-btn" in result.error_message
    assert result.screenshot_path and Path(result.screenshot_path).is_file()
    context = Path(result.error_context_path or "").read_text(encoding="utf-8")
    assert "# Page snapshot" in context
    assert 'textbox "Name"' in context and "Ada" in context  # the state at failure


def test_record_video_attaches_a_video() -> None:
    spec = _spec("video.spec.ts", '  await page.getByLabel("Name").fill("Ada");')
    result = run_test(spec, record_video=True)
    assert result.passed, result.output
    assert result.video_path and result.video_path.endswith(".webm")
    assert Path(result.video_path).is_file()


def test_syntax_error_spec_is_reported_as_a_failure() -> None:
    path = specs_dir() / "syntax.spec.ts"
    path.write_text(
        HEADER + 'test("x", async ({ page }) => { await page.goto( });\n',
        encoding="utf-8",
    )
    result = run_test(path)
    assert result.status == "failed", result.output
    assert result.error_message


def test_cancel_stops_a_long_run() -> None:
    spec = _spec("slow.spec.ts", "  await page.waitForTimeout(25000);")
    cancel = threading.Event()
    threading.Timer(2.0, cancel.set).start()
    started = time.monotonic()
    result = run_test(spec, cancel=cancel)
    assert result.status == "cancelled"
    assert time.monotonic() - started < 15


def test_spec_in_a_folder_with_regex_characters_runs() -> None:
    folder = specs_dir() / "specs (v2)"
    folder.mkdir()
    path = folder / "c++.spec.ts"
    path.write_text(
        HEADER + 'test("odd path", async ({ page }) => {\n'
        f"  await page.setContent(`{FORM}`);\n"
        '  await expect(page.getByLabel("Name")).toBeVisible();\n});\n',
        encoding="utf-8",
    )
    result = run_test(path)
    assert result.passed, result.output
