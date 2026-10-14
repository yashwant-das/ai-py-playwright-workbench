# v2 Phase 2: Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the generate and heal engine so evidence comes from the failing run itself, every model call is recorded, a suspected app bug stops the heal, runs can be cancelled, verification re-runs are recorded as captioned video, and each run produces one JSON report in `workspace/`.

**Architecture:** The runner reads Playwright's JSON report from a per-run output folder. Healing evidence comes from the `error-context.md` file that report points to; page context comes from Playwright's own `aria_snapshot(mode="ai")`, console, page-error and request collections. Pipelines talk to models only through a `ChatModel` protocol (an adapter wraps the 1.0 router until Phase 3), emit `RunEvent`s through a callback, honour a cancel flag, and save a `HealReport` or `GenerateReport`. The 1.0 orchestrators, decision artifacts and custom browser listeners are deleted as their replacements land.

**Tech Stack:** Python 3.13, Pydantic 2, Playwright 1.63 (Python and Playwright Test), ts-morph, OpenAI SDK (behind the router until Phase 3), pytest.

**Spec:** [docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md](../specs/2026-10-03-v2-showcase-simplification-design.md) — sections 4 (D3, D5–D8, D11, D13–D15), 6.4 (data contracts), 6.5 (E1–E12) and 11 (Phase 2 row).

## Global Constraints

- Python `>=3.13`, Playwright exactly `1.63.0` (Python and npm), Node 24.
- Runtime output lives only under `workbench.config.workspace_dir()` (`<repo>/workspace`, overridable with `WORKBENCH_WORKSPACE`).
- Every path comes from `workbench.config`.
- All model output is parsed into a Pydantic model with `parse_llm_response()`; never `json.loads` alone.
- Pipelines (`heal()`, `generate()`) return a report with a status for every expected failure (unreachable model, missing browsers, cancelled, unreachable page); they raise only on programmer error.
- `heal()` leaves the spec byte-for-byte unchanged unless the final status is `healed`.
- App-defect guard: diagnosis `POTENTIAL_APP_DEFECT` with confidence `>= 0.7` stops the heal without editing the spec.
- Subprocesses use argument lists; Playwright starts with `start_new_session=True` so cancel can kill its whole process group (macOS and Linux).
- Prompt content changes bump `src/workbench/prompts/manifest.json`: healer `3`, generator `3`.
- Unit tests need no model, browser or network. Pipelines take their collaborators as arguments (`model`, `run`, `collect`, `browsers_ready`); tests pass fakes instead of patching module globals.
- The router, model registry and `.env` loading stay until Phase 3. `RouterChatModel` is the only code that touches the router.
- Uploaded and generated specs are single files; specs importing local helpers are out of scope.
- Commits follow Conventional Commits and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; `ROADMAP.md` and `CHANGELOG.md` change in the same commit as the work.

## Review Focus

1. **A spec that does not compile** (a TypeScript syntax error) produces Playwright top-level errors and no test results. Expected: a `failed` run the healer can work on, not a runner `error`. Pinned by `test_top_level_error_is_a_failure` (Task 2) and `test_syntax_error_spec_is_reported_as_a_failure` (Task 2, integration).
2. **Cancelling a run** must not leave Playwright or its browsers running. Expected: the process group is killed and the run returns `cancelled` within seconds. Pinned by `test_cancel_stops_a_long_run` (Task 2, integration).
3. **Every non-healed outcome restores the spec**, including a model failure after an earlier attempt already changed it. Expected: file content equals the original. Pinned by `test_model_error_after_a_failed_attempt_restores_the_spec` and the per-status assertions in `test_heal_pipeline.py` (Task 7).
4. **A report id coming from a URL** (Phase 4) is used to build a file path. Expected: anything that is not a generated id is rejected. Pinned by `test_load_report_rejects_path_traversal` (Task 6).
5. **Very large pages** inflate the prompt. Expected: each section is cut to its limit and the cut is recorded. Pinned by `test_long_snapshot_is_truncated_and_recorded` (Task 7).

---

## File map

| Action | Path | Responsibility |
| --- | --- | --- |
| Modify | `src/workbench/config.py` | Workspace folders (`workspace_dir`, `runs_dir`, `reports_dir`, `specs_dir`) |
| Create | `src/workbench/ids.py` | `slugify()`, `new_run_id()` |
| Create | `playwright.workspace.config.ts` | Config the runner uses for every spec; enables captioned video on request |
| Create | `src/workbench/playwright_report.py` | Playwright JSON report → `RunResult` |
| Rewrite | `src/workbench/runner.py` | Cancellable run with a per-run output folder |
| Rewrite | `src/workbench/context/collector.py` | One Chromium session: DOM, `aria_snapshot(mode="ai")`, console, page errors, failed requests |
| Create | `src/workbench/context/locators.py` | Locator candidates from an aria snapshot |
| Delete | `src/workbench/context/{accessibility,console,network,screenshot,locator_candidates}.py` | Replaced by Playwright built-ins |
| Create | `src/workbench/environment.py` | `node_available()`, `chromium_installed()` |
| Modify | `src/workbench/heal/repair.py` | `apply_fix(code, action) -> RepairResult` |
| Create | `src/workbench/llm/chat.py` | `ChatModel` protocol, `ChatReply`, `ModelError`, `RouterChatModel` |
| Modify | `src/workbench/llm/router.py` | `response_format` pass-through; bad requests are not retried |
| Modify | `src/workbench/llm/prompts.py` | `render_prompt()` for named, size-limited sections |
| Create | `src/workbench/models/events.py`, `src/workbench/events.py` | `RunEvent`, `EventSink` |
| Create | `src/workbench/reports.py` | Save, load and list reports |
| Rewrite | `src/workbench/heal/evidence.py`, `heal/planner.py` | Failure evidence; diagnosis with `ModelExchange` |
| Create | `src/workbench/heal/pipeline.py` | `heal()` |
| Rewrite | `src/workbench/generate/pipeline.py` | `generate()` |
| Delete | `src/workbench/heal/{verifier,artifact_store}.py` | Replaced by the pipeline and reports |
| Rewrite | `src/workbench/prompts/{healer,generator}.md` | v3 prompts |
| Modify | `src/workbench/models/{shared,heal,generate,artifacts,__init__}.py` | v2 data contracts; 1.0 decision types deleted |
| Rewrite | `tests/unit/*`, `tests/integration/*` | One test file per module |
| Delete | `playwright.config.ts`, `playwright.e2e.config.ts` | The runner's workspace config replaces both; Phase 5 adds a config for UI tests |

---

### Task 1: Workspace layout and run ids

**Files:**

- Modify: `src/workbench/config.py`, `tsconfig.json`
- Create: `src/workbench/ids.py`, `playwright.workspace.config.ts`, `tests/unit/test_workspace.py`

**Interfaces:**

- Produces:
  - `workbench.config.workspace_dir() -> Path`, `runs_dir() -> Path`, `reports_dir() -> Path`, `specs_dir() -> Path` (the last three create the folder), `WORKSPACE_PLAYWRIGHT_CONFIG: Path`, `WORKSPACE_ENV = "WORKBENCH_WORKSPACE"`
  - `workbench.ids.slugify(text: str, max_length: int = 40) -> str`, `new_run_id(kind: str, name: str, *, now: datetime | None = None) -> str`
  - `playwright.workspace.config.ts` reading `WORKBENCH_SPECS_DIR` and `WORKBENCH_RECORD_VIDEO`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_workspace.py`:

```python
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run python -m pytest tests/unit/test_workspace.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'workbench.ids'`.

- [ ] **Step 3: Write `src/workbench/ids.py`**

```python
"""Identifiers and file-name slugs for runs, reports and specs."""

import re
from datetime import datetime

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_length: int = 40) -> str:
    """Return a lower-case kebab-case slug of ``text`` ("spec" if nothing is left)."""
    slug = _NON_ALNUM.sub("-", text.lower()).strip("-")
    slug = slug[:max_length].rstrip("-")
    return slug or "spec"


def new_run_id(kind: str, name: str, *, now: datetime | None = None) -> str:
    """Return ``YYYYMMDD-HHMMSS-<kind>-<slug>``; ids sort by start time."""
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{kind}-{slugify(name)}"
```

- [ ] **Step 4: Rewrite `src/workbench/config.py`**

First confirm the two Phase 1 constants being dropped are unused: `grep -rn "GENERATED_SPECS_DIR\|TEST_RESULTS_DIR" src tests` must print nothing. Then replace the whole file:

```python
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

# Where the 1.0 artifact store writes; removed with it in Task 7.
ARTIFACTS_DIR = PROJECT_ROOT / "tests" / "artifacts"


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
```

- [ ] **Step 5: Create `playwright.workspace.config.ts`**

```ts
import { defineConfig, devices } from '@playwright/test';

/**
 * The config the workbench runner (src/workbench/runner.py) uses for every
 * generated, uploaded or healed spec. The runner sets:
 *
 *   WORKBENCH_SPECS_DIR     folder that holds the spec under test
 *   WORKBENCH_RECORD_VIDEO  "1" to record a video with captioned actions
 *
 * and passes --output and --reporter=json on the command line.
 */
const recordVideo = process.env.WORKBENCH_RECORD_VIDEO === '1';

export default defineConfig({
  testDir: process.env.WORKBENCH_SPECS_DIR ?? 'workspace/specs',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  use: {
    screenshot: 'only-on-failure',
    trace: 'off',
    video: recordVideo
      ? {
          mode: 'on',
          show: {
            actions: { position: 'top-right' },
            test: { level: 'title', position: 'top-left' },
          },
        }
      : 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
```

In `tsconfig.json`, add `"playwright.workspace.config.ts"` to the `include` array (after `"playwright.e2e.config.ts"`).

- [ ] **Step 6: Run the tests and the type checks**

Run: `uv run python -m pytest tests/unit/test_workspace.py -q -o addopts=`
Expected: 10 passed.

Run: `npm run type-check && npm run lint:js && uv run mypy`
Expected: no errors (tsc checks the `video.show` option types against Playwright 1.63).

- [ ] **Step 7: Commit**

```bash
git add src/workbench/config.py src/workbench/ids.py playwright.workspace.config.ts tsconfig.json tests/unit/test_workspace.py
git commit -m "feat: add the workspace folder layout and run ids" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The runner reads Playwright's JSON report

**Files:**

- Create: `src/workbench/playwright_report.py`, `tests/unit/test_playwright_report.py`, `tests/unit/test_runner.py`, `tests/integration/conftest.py`, `tests/integration/test_runner.py`
- Rewrite: `src/workbench/runner.py`
- Modify: `src/workbench/models/shared.py` (`RunResult`), `src/workbench/heal/evidence.py` (two lines), `tests/unit/test_schemas.py`, `tests/unit/test_healing.py`

**Interfaces:**

- Consumes: Task 1 `runs_dir()`, `new_run_id()`, `WORKSPACE_PLAYWRIGHT_CONFIG`.
- Produces:
  - `workbench.models.shared.RunStatus = Literal["passed", "failed", "timed_out", "cancelled", "error"]`
  - `RunResult(status, duration_ms=0, error_message="", error_location="", screenshot_path=None, error_context_path=None, video_path=None, stdout="", stderr="")` with properties `passed`, `output`, and a temporary `returncode` (removed in Task 7)
  - `workbench.playwright_report.read_json_report(path: Path) -> dict | None`, `parse_json_report(report: dict) -> RunResult`
  - `workbench.runner.run_test(spec, run_dir=None, *, record_video=False, cancel=None, timeout_s=DEFAULT_TIMEOUT_S) -> RunResult`

- [ ] **Step 1: Write the failing report-parser tests**

Create `tests/unit/test_playwright_report.py`:

```python
"""Playwright's JSON report becomes a RunResult."""

from typing import Any

from workbench.playwright_report import parse_json_report


def _report(result: dict[str, Any], nested: bool = False) -> dict[str, Any]:
    spec = {"title": "submit", "tests": [{"results": [result]}]}
    suite: dict[str, Any] = {"title": "contact.spec.ts", "specs": [spec]}
    if nested:
        suite = {"title": "contact.spec.ts", "specs": [], "suites": [suite]}
    return {"suites": [suite], "errors": []}


def test_passed_run() -> None:
    run = parse_json_report(_report({"status": "passed", "duration": 812}))
    assert run.passed
    assert run.duration_ms == 812
    assert run.error_message == ""


def test_failed_run_keeps_error_location_and_attachments() -> None:
    result = {
        "status": "failed",
        "duration": 2300,
        "errors": [
            {
                "message": "\x1b[31mTimeoutError: locator.click: Timeout 2000ms exceeded.\x1b[39m",
                "location": {"file": "/w/contact.spec.ts", "line": 5, "column": 37},
            }
        ],
        "attachments": [
            {"name": "screenshot", "path": "/w/out/test-failed-1.png"},
            {"name": "error-context", "path": "/w/out/error-context.md"},
            {"name": "video", "path": "/w/out/video.webm"},
        ],
    }
    run = parse_json_report(_report(result))
    assert run.status == "failed"
    assert run.error_message == "TimeoutError: locator.click: Timeout 2000ms exceeded."
    assert run.error_location == "/w/contact.spec.ts:5:37"
    assert run.screenshot_path == "/w/out/test-failed-1.png"
    assert run.error_context_path == "/w/out/error-context.md"
    assert run.video_path == "/w/out/video.webm"


def test_results_inside_describe_blocks_are_found() -> None:
    run = parse_json_report(
        _report({"status": "timedOut", "duration": 30000}, nested=True)
    )
    assert run.status == "timed_out"


def test_top_level_error_is_a_failure() -> None:
    report = {
        "suites": [],
        "errors": [
            {
                "message": "SyntaxError: Unexpected token (3:20)",
                "location": {"file": "/w/broken.spec.ts", "line": 3, "column": 20},
            }
        ],
    }
    run = parse_json_report(report)
    assert run.status == "failed"
    assert "SyntaxError" in run.error_message
    assert run.error_location == "/w/broken.spec.ts:3:20"


def test_report_without_tests_or_errors_is_an_error() -> None:
    run = parse_json_report({"suites": [], "errors": []})
    assert run.status == "error"
    assert run.error_message == "Playwright ran no tests."


def test_interrupted_run_is_cancelled() -> None:
    assert parse_json_report(_report({"status": "interrupted"})).status == "cancelled"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run python -m pytest tests/unit/test_playwright_report.py -q -o addopts=`
Expected: collection error `No module named 'workbench.playwright_report'`.

- [ ] **Step 3: Replace `RunResult` in `src/workbench/models/shared.py`**

Add `Literal` to the `typing` imports (`from typing import Literal`) and replace the whole `RunResult` class with:

```python
RunStatus = Literal["passed", "failed", "timed_out", "cancelled", "error"]


class RunResult(BaseModel):
    """Outcome of one ``npx playwright test`` run, read from its JSON report."""

    status: RunStatus
    duration_ms: int = Field(default=0, ge=0)
    error_message: str = ""
    error_location: str = ""
    screenshot_path: str | None = None
    error_context_path: str | None = None
    video_path: str | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def passed(self) -> bool:
        """True if the test passed."""
        return self.status == "passed"

    @property
    def output(self) -> str:
        """Error message and process output, for logs and the failure classifier."""
        parts = (self.error_message, self.stdout, self.stderr)
        return "\n".join(part for part in parts if part)

    @property
    def returncode(self) -> int:
        """Exit-code view for the 1.0 heal loop; removed with it in Task 7."""
        return 0 if self.passed else 1
```

- [ ] **Step 4: Write `src/workbench/playwright_report.py`**

```python
"""Turns Playwright's JSON report into a RunResult."""

import json
from pathlib import Path
from typing import Any

from workbench.models.shared import RunResult, RunStatus
from workbench.text import clean_ansi_codes

_STATUS: dict[str, RunStatus] = {
    "passed": "passed",
    "failed": "failed",
    "timedOut": "timed_out",
    "interrupted": "cancelled",
    "skipped": "failed",
}


def read_json_report(path: Path) -> dict[str, Any] | None:
    """Load the report Playwright wrote, or None if it is missing or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def parse_json_report(report: dict[str, Any]) -> RunResult:
    """Build a RunResult from the first test result in a JSON report.

    A spec that does not compile has no test results, only top-level errors;
    that is a failure the healer can work on, not a runner error.
    """
    result = _first_result(report.get("suites") or [])
    if result is None:
        errors = report.get("errors") or []
        if errors:
            message, location = _error_text(errors[0])
            return RunResult(
                status="failed", error_message=message, error_location=location
            )
        return RunResult(status="error", error_message="Playwright ran no tests.")

    errors = result.get("errors") or []
    message, location = _error_text(errors[0]) if errors else ("", "")
    attachments: dict[str, str] = {}
    for attachment in result.get("attachments") or []:
        name, path = attachment.get("name"), attachment.get("path")
        if name and path and name not in attachments:
            attachments[name] = path
    return RunResult(
        status=_STATUS.get(str(result.get("status")), "failed"),
        duration_ms=int(result.get("duration") or 0),
        error_message=message,
        error_location=location,
        screenshot_path=attachments.get("screenshot"),
        error_context_path=attachments.get("error-context"),
        video_path=attachments.get("video"),
    )


def _first_result(suites: list[dict[str, Any]]) -> dict[str, Any] | None:
    for suite in suites:
        for spec in suite.get("specs") or []:
            for test in spec.get("tests") or []:
                results = test.get("results") or []
                if results:
                    return results[-1]  # the final retry decides the outcome
        nested = _first_result(suite.get("suites") or [])
        if nested is not None:
            return nested
    return None


def _error_text(error: dict[str, Any]) -> tuple[str, str]:
    message = clean_ansi_codes(
        str(error.get("message") or error.get("value") or "")
    ).strip()
    location = error.get("location") or {}
    where = (
        f"{location['file']}:{location.get('line', 0)}:{location.get('column', 0)}"
        if location.get("file")
        else ""
    )
    return message, where
```

- [ ] **Step 5: Run the parser tests**

Run: `uv run python -m pytest tests/unit/test_playwright_report.py -q -o addopts=`
Expected: 6 passed.

- [ ] **Step 6: Write the failing runner tests**

Create `tests/unit/test_runner.py`:

```python
"""The runner builds the right command and reads the report it asked for."""

import json
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest

from workbench import runner
from workbench.config import WORKSPACE_PLAYWRIGHT_CONFIG

FAILED_REPORT = {
    "suites": [
        {
            "specs": [
                {
                    "tests": [
                        {
                            "results": [
                                {
                                    "status": "failed",
                                    "duration": 50,
                                    "errors": [{"message": "Error: boom"}],
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}


def _fake_popen(report: dict[str, Any] | None, stderr: str = "", hang: bool = False):
    calls: list[Any] = []

    class FakeProcess:
        pid = 4242

        def __init__(self, command: list[str], **kwargs: Any) -> None:
            self.command, self.kwargs = command, kwargs
            calls.append(self)

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            if hang:
                raise subprocess.TimeoutExpired(self.command, timeout or 0)
            if report is not None:
                out = Path(self.kwargs["env"]["PLAYWRIGHT_JSON_OUTPUT_FILE"])
                out.write_text(json.dumps(report), encoding="utf-8")
            return "", stderr

    return FakeProcess, calls


@pytest.fixture(autouse=True)
def _workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WORKBENCH_WORKSPACE", str(tmp_path / "ws"))


def test_command_uses_the_workspace_config_and_the_json_reporter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake, calls = _fake_popen(FAILED_REPORT)
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    spec = tmp_path / "specs" / "contact.spec.ts"

    runner.run_test(spec, tmp_path / "run", record_video=True)

    (call,) = calls
    assert call.command[:4] == ["npx", "playwright", "test", str(spec.resolve())]
    assert call.command[call.command.index("--config") + 1] == str(
        WORKSPACE_PLAYWRIGHT_CONFIG
    )
    assert call.command[call.command.index("--output") + 1] == str(
        tmp_path / "run" / "test-results"
    )
    assert "--reporter=json" in call.command
    env = call.kwargs["env"]
    assert env["PLAYWRIGHT_JSON_OUTPUT_FILE"] == str(tmp_path / "run" / "report.json")
    assert env["WORKBENCH_SPECS_DIR"] == str(spec.resolve().parent)
    assert env["WORKBENCH_RECORD_VIDEO"] == "1"
    assert call.kwargs["start_new_session"] is True


def test_report_is_parsed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake, _ = _fake_popen(FAILED_REPORT)
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    result = runner.run_test(tmp_path / "a.spec.ts", tmp_path / "run")
    assert result.status == "failed"
    assert result.error_message == "Error: boom"


def test_default_run_folder_is_inside_the_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake, calls = _fake_popen(FAILED_REPORT)
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    runner.run_test(tmp_path / "a.spec.ts")
    output = Path(calls[0].command[calls[0].command.index("--output") + 1])
    assert output.parent.parent == (tmp_path / "ws" / "runs").resolve()


def test_missing_report_is_an_error_that_keeps_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake, _ = _fake_popen(None, stderr="Error: No tests found")
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    result = runner.run_test(tmp_path / "a.spec.ts", tmp_path / "run")
    assert result.status == "error"
    assert "No tests found" in result.error_message


def test_missing_npx_is_an_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def no_npx(*_args: Any, **_kwargs: Any) -> None:
        raise FileNotFoundError("npx")

    monkeypatch.setattr(runner.subprocess, "Popen", no_npx)
    result = runner.run_test(tmp_path / "a.spec.ts", tmp_path / "run")
    assert result.status == "error"
    assert "npx" in result.error_message


def test_cancel_stops_the_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake, _ = _fake_popen(None, hang=True)
    stopped: list[Any] = []
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    monkeypatch.setattr(runner, "_stop", stopped.append)
    cancel = threading.Event()
    cancel.set()

    result = runner.run_test(tmp_path / "a.spec.ts", tmp_path / "run", cancel=cancel)

    assert result.status == "cancelled"
    assert len(stopped) == 1


def test_timeout_stops_the_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake, _ = _fake_popen(None, hang=True)
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    monkeypatch.setattr(runner, "_stop", lambda _proc: None)
    result = runner.run_test(tmp_path / "a.spec.ts", tmp_path / "run", timeout_s=0)
    assert result.status == "timed_out"
```

- [ ] **Step 7: Run them to verify they fail**

Run: `uv run python -m pytest tests/unit/test_runner.py -q -o addopts=`
Expected: failures; the current `run_test` uses `subprocess.run` and takes no `run_dir`.

- [ ] **Step 8: Rewrite `src/workbench/runner.py`**

```python
"""Runs one Playwright spec and reads its result from Playwright's JSON report.

Each run gets its own output folder, so the screenshot, error context and
video in the result always belong to that run. Playwright starts in its own
process group, so stopping a run also stops the browsers it launched.
"""

import logging
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

from workbench.config import PROJECT_ROOT, WORKSPACE_PLAYWRIGHT_CONFIG, runs_dir
from workbench.ids import new_run_id
from workbench.models.shared import RunResult
from workbench.playwright_report import parse_json_report, read_json_report
from workbench.text import clean_ansi_codes

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 120.0
_POLL_S = 0.25


def run_test(
    spec: Path | str,
    run_dir: Path | None = None,
    *,
    record_video: bool = False,
    cancel: threading.Event | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> RunResult:
    """Run ``spec`` with Playwright Test and return its result.

    Args:
        spec:         The ``.spec.ts`` file to run, in any folder.
        run_dir:      Where Playwright writes its output; a new folder under
                      ``workspace/runs`` when omitted.
        record_video: Record a video with captioned actions.
        cancel:       Set it to stop the run; the result is then ``cancelled``.
        timeout_s:    Hard limit for the whole run.
    """
    spec = Path(spec).resolve()
    run_dir = run_dir or runs_dir() / new_run_id("run", spec.stem)
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "report.json"
    command = [
        "npx",
        "playwright",
        "test",
        str(spec),
        "--config",
        str(WORKSPACE_PLAYWRIGHT_CONFIG),
        "--output",
        str(run_dir / "test-results"),
        "--reporter=json",
    ]
    env = {
        **os.environ,
        "PLAYWRIGHT_JSON_OUTPUT_FILE": str(report_path),
        "WORKBENCH_SPECS_DIR": str(spec.parent),
        "WORKBENCH_RECORD_VIDEO": "1" if record_video else "0",
        "FORCE_COLOR": "0",
    }
    started = time.monotonic()
    try:
        proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            command,
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError:
        return RunResult(
            status="error",
            error_message="npx was not found. Install Node.js 24 and run npm ci.",
        )

    while True:
        try:
            stdout, stderr = proc.communicate(timeout=_POLL_S)
            break
        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if cancel is not None and cancel.is_set():
                _stop(proc)
                return RunResult(
                    status="cancelled",
                    duration_ms=elapsed_ms,
                    error_message="The run was cancelled.",
                )
            if elapsed_ms > timeout_s * 1000:
                _stop(proc)
                return RunResult(
                    status="timed_out",
                    duration_ms=elapsed_ms,
                    error_message=f"Playwright did not finish within {timeout_s:.0f} seconds.",
                )

    duration_ms = int((time.monotonic() - started) * 1000)
    report = read_json_report(report_path)
    if report is None:
        message = (
            clean_ansi_codes(stderr or "").strip()
            or "Playwright did not write a report."
        )
        return RunResult(
            status="error",
            duration_ms=duration_ms,
            error_message=message[:2000],
            stdout=stdout or "",
            stderr=stderr or "",
        )
    result = parse_json_report(report)
    logger.debug("%s finished: %s", spec.name, result.status)
    return result.model_copy(
        update={
            "stdout": stdout or "",
            "stderr": stderr or "",
            "duration_ms": result.duration_ms or duration_ms,
        }
    )


def _stop(proc: "subprocess.Popen[str]") -> None:
    """Stop Playwright and every browser it started."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
```

- [ ] **Step 9: Run the runner tests**

Run: `uv run python -m pytest tests/unit/test_runner.py -q -o addopts=`
Expected: 7 passed.

- [ ] **Step 10: Keep the 1.0 heal loop working on the new RunResult**

In `src/workbench/heal/evidence.py`, inside `gather_evidence`:

- replace `logs = result.stderr if result.stderr else result.stdout` with `logs = result.output`;
- replace the whole "Most recent screenshot written to test-results/" block (from `screenshot_path: str | None = None` through the `screenshot_path = str(max(...))` line) with `screenshot_path = result.screenshot_path`.

Then remove the now-unused `PROJECT_ROOT` import if ruff reports it.

In `tests/unit/test_healing.py`:

- delete the classes `TestRunTest` and `TestGatherEvidence` (their replacements are `tests/unit/test_runner.py` and Task 7's `test_evidence.py`);
- rewrite the remaining `RunResult` constructions:

```bash
uv run python - <<'EOF'
from pathlib import Path
p = Path("tests/unit/test_healing.py")
s = p.read_text(encoding="utf-8")
s = s.replace("returncode=0", 'status="passed"').replace("returncode=1", 'status="failed"')
p.write_text(s, encoding="utf-8")
EOF
```

In `tests/unit/test_schemas.py`, replace the class `TestRunResult` with:

```python
class TestRunResult(unittest.TestCase):
    def test_passed_only_for_status_passed(self):
        self.assertTrue(RunResult(status="passed").passed)
        for status in ("failed", "timed_out", "cancelled", "error"):
            self.assertFalse(RunResult(status=status).passed, status)

    def test_output_joins_error_and_streams(self):
        r = RunResult(status="failed", error_message="E", stdout="O", stderr="S")
        self.assertEqual(r.output, "E\nO\nS")

    def test_output_skips_empty_parts(self):
        self.assertEqual(RunResult(status="failed", stderr="S").output, "S")
```

- [ ] **Step 11: Add the integration fixtures**

Create `tests/integration/conftest.py`:

```python
"""Shared fixtures for the integration suite (real Chromium, no real model)."""

import os
from pathlib import Path

import pytest

from workbench import config


@pytest.fixture(autouse=True)
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate runtime output; CI sets WORKBENCH_WORKSPACE to keep it as an artifact."""
    if not os.environ.get(config.WORKSPACE_ENV):
        monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "workspace"))
    return config.workspace_dir()
```

- [ ] **Step 12: Write the real-browser runner tests**

Create `tests/integration/test_runner.py`:

```python
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
```

- [ ] **Step 13: Run every suite**

Run:

```bash
uv run python -m pytest -q -o addopts=
uv run python -m pytest tests/integration -q -o addopts=
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Expected: all pass. The 1.0 heal and generate integration tests still pass, because `run_test()` now writes into `workspace/` but takes the same spec argument.

- [ ] **Step 14: Commit**

```bash
git add -A
git commit -m "feat: read run results from Playwright's JSON report, with cancel and video" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Page context from Playwright's own snapshot and collections

**Files:**

- Rewrite: `src/workbench/context/collector.py`, `src/workbench/context/__init__.py`, `src/workbench/models/artifacts.py`, `tests/unit/test_context.py`
- Create: `src/workbench/context/locators.py`, `tests/unit/test_locators.py`, `tests/integration/test_context.py`
- Delete: `src/workbench/context/accessibility.py`, `console.py`, `network.py`, `screenshot.py`, `locator_candidates.py`, `tests/unit/test_visibility.py`
- Modify: `src/workbench/models/heal.py` (`Evidence.from_context_snapshot`), `src/workbench/models/generate.py` (`to_markdown`), `src/workbench/heal/evidence.py`, `src/workbench/generate/pipeline.py`, `tests/integration/conftest.py`, `tests/integration/test_pipeline.py`

**Interfaces:**

- Produces:
  - `ContextSnapshot(url, html=None, aria_snapshot=None, locator_candidates=[], console_errors=[], network_errors=[], timestamp)` with property `is_empty`
  - `workbench.context.collect_context(url, *, capture_html=True, max_html_chars=30000, max_snapshot_chars=12000, max_locator_candidates=20, wait_ms=1000) -> ContextSnapshot`
  - `workbench.context.collector.console_errors(page) -> list[str]`, `network_errors(page) -> list[str]`
  - `workbench.context.locators.extract_locator_candidates(snapshot: str | None, max_count: int = 20) -> list[str]`
  - integration fixture `site` (URL of `samples/site/` on port 4173) in `tests/integration/conftest.py`

- [ ] **Step 1: Write the failing locator tests**

Create `tests/unit/test_locators.py`:

```python
"""Locator candidates come from the aria snapshot Playwright produces."""

from workbench.context.locators import extract_locator_candidates

SNAPSHOT = """- generic [active] [ref=e1]:
  - text: Name
  - textbox "Name" [ref=e2]
  - button "Submit" [ref=e3]
  - button "Submit" [ref=e4]
  - link "Say \\"hi\\"" [ref=e5]
  - heading "Don't panic" [level=1] [ref=e6]
  - generic "Not interactive" [ref=e7]"""


def test_interactive_roles_become_get_by_role_calls() -> None:
    assert extract_locator_candidates(SNAPSHOT) == [
        "getByRole('textbox', { name: 'Name' })",
        "getByRole('button', { name: 'Submit' })",
        "getByRole('link', { name: 'Say \"hi\"' })",
        "getByRole('heading', { name: 'Don\\'t panic' })",
    ]


def test_max_count_is_respected() -> None:
    assert len(extract_locator_candidates(SNAPSHOT, max_count=2)) == 2


def test_empty_snapshot_has_no_candidates() -> None:
    assert extract_locator_candidates("") == []
    assert extract_locator_candidates(None) == []
```

- [ ] **Step 2: Write the failing collector tests**

Replace `tests/unit/test_context.py` with:

```python
"""collect_context() with a fake browser: snapshot, signals, failures."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from workbench.context import collector


def _page(aria: str = '- button "Submit" [ref=e3]') -> MagicMock:
    page = MagicMock()
    page.content.return_value = (
        "<html><body><button>Submit</button><script>x()</script></body></html>"
    )
    page.aria_snapshot.return_value = aria
    page.console_messages.return_value = [
        SimpleNamespace(type="error", text="boom"),
        SimpleNamespace(type="log", text="hello"),
    ]
    page.page_errors.return_value = [SimpleNamespace(message="kaput")]
    page.requests.return_value = [
        SimpleNamespace(
            method="GET",
            url="http://x/a.js",
            failure="net::ERR_FAILED",
            existing_response=None,
        ),
        SimpleNamespace(
            method="POST",
            url="http://x/orders",
            failure=None,
            existing_response=SimpleNamespace(status=500),
        ),
        SimpleNamespace(
            method="GET",
            url="http://x/ok",
            failure=None,
            existing_response=SimpleNamespace(status=200),
        ),
    ]
    return page


def _browser(monkeypatch: pytest.MonkeyPatch, page: MagicMock) -> MagicMock:
    playwright = MagicMock()
    browser = playwright.__enter__.return_value.chromium.launch.return_value
    browser.new_page.return_value = page
    monkeypatch.setattr(collector, "sync_playwright", lambda: playwright)
    return browser


def test_snapshot_signals_and_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _page()
    browser = _browser(monkeypatch, page)

    snap = collector.collect_context("http://x/", wait_ms=0)

    page.aria_snapshot.assert_called_once_with(mode="ai")
    assert snap.aria_snapshot == '- button "Submit" [ref=e3]'
    assert snap.locator_candidates == ["getByRole('button', { name: 'Submit' })"]
    assert "<script>" not in (snap.html or "")
    assert snap.console_errors == ["[ERROR] boom", "[PAGEERROR] kaput"]
    assert snap.network_errors == [
        "GET http://x/a.js [net::ERR_FAILED]",
        "POST http://x/orders → 500",
    ]
    assert not snap.is_empty
    browser.close.assert_called_once()


def test_long_snapshot_is_cut(monkeypatch: pytest.MonkeyPatch) -> None:
    _browser(monkeypatch, _page(aria="- text: " + "x" * 500))
    snap = collector.collect_context("http://x/", wait_ms=0, max_snapshot_chars=100)
    assert len(snap.aria_snapshot or "") == 100


def test_navigation_failure_returns_an_empty_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _page()
    page.goto.side_effect = RuntimeError("net::ERR_CONNECTION_REFUSED")
    browser = _browser(monkeypatch, page)
    snap = collector.collect_context("http://x/", wait_ms=0)
    assert snap.is_empty
    assert snap.url == "http://x/"
    browser.close.assert_called_once()


def test_browser_launch_failure_returns_an_empty_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> Any:
        raise RuntimeError("Executable doesn't exist")

    monkeypatch.setattr(collector, "sync_playwright", broken)
    assert collector.collect_context("http://x/", wait_ms=0).is_empty
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run python -m pytest tests/unit/test_locators.py tests/unit/test_context.py -q -o addopts=`
Expected: collection error `No module named 'workbench.context.locators'`.

- [ ] **Step 4: Write `src/workbench/context/locators.py`**

```python
"""Locator candidates parsed from an aria snapshot.

Interactive elements in the snapshot (``- button "Submit" [ref=e3]``) become
``getByRole`` calls the model can use as stable, user-facing locators.
"""

import re

_INTERACTIVE_ROLES = frozenset(
    {
        "button",
        "checkbox",
        "combobox",
        "heading",
        "img",
        "link",
        "listbox",
        "menuitem",
        "radio",
        "searchbox",
        "slider",
        "spinbutton",
        "tab",
        "textbox",
    }
)
_LINE = re.compile(r'^\s*-\s+(?P<role>[a-z]+)\s+"(?P<name>(?:[^"\\]|\\.)*)"')


def extract_locator_candidates(snapshot: str | None, max_count: int = 20) -> list[str]:
    """Return unique ``getByRole(...)`` strings for named interactive elements."""
    candidates: list[str] = []
    for line in (snapshot or "").splitlines():
        match = _LINE.match(line)
        if not match or match["role"] not in _INTERACTIVE_ROLES:
            continue
        name = match["name"].replace('\\"', '"')
        if not name:
            continue
        escaped = name.replace("'", "\\'")
        candidate = f"getByRole('{match['role']}', {{ name: '{escaped}' }})"
        if candidate not in candidates:
            candidates.append(candidate)
        if len(candidates) >= max_count:
            break
    return candidates
```

- [ ] **Step 5: Replace `ContextSnapshot` in `src/workbench/models/artifacts.py`**

Replace the whole file with:

```python
"""Page context collected from one browser session."""

from datetime import datetime

from pydantic import BaseModel, Field


class ContextSnapshot(BaseModel):
    """What a page looked like when the workbench opened it."""

    url: str
    html: str | None = None
    aria_snapshot: str | None = None
    locator_candidates: list[str] = Field(default_factory=list)
    console_errors: list[str] = Field(default_factory=list)
    network_errors: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_empty(self) -> bool:
        """True when neither HTML nor an aria snapshot was collected."""
        return not self.html and not self.aria_snapshot
```

- [ ] **Step 6: Rewrite `src/workbench/context/collector.py`**

```python
"""Page context from one Chromium session, using Playwright's own collections.

The aria snapshot uses ``mode="ai"``, the format Playwright itself writes into
``error-context.md``, so generation and healing show the model one format.
"""

import logging

from playwright.sync_api import Page, sync_playwright

from workbench.context.dom import collect_dom
from workbench.context.locators import extract_locator_candidates
from workbench.models.artifacts import ContextSnapshot

logger = logging.getLogger(__name__)

_CONSOLE_TYPES = frozenset({"error", "warning"})


def collect_context(
    url: str,
    *,
    capture_html: bool = True,
    max_html_chars: int = 30_000,
    max_snapshot_chars: int = 12_000,
    max_locator_candidates: int = 20,
    wait_ms: int = 1_000,
) -> ContextSnapshot:
    """Open ``url`` and collect what the model needs; never raises.

    On any navigation or browser failure, returns a snapshot with only the
    URL set (``is_empty`` is then True).
    """
    snapshot = ContextSnapshot(url=url)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                try:
                    page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                except Exception as exc:
                    logger.warning("Navigation failed for %s: %s", url, exc)
                    return snapshot
                if wait_ms > 0:
                    page.wait_for_timeout(wait_ms)
                if capture_html:
                    snapshot.html = collect_dom(page, max_chars=max_html_chars) or None
                aria = page.aria_snapshot(mode="ai")
                snapshot.aria_snapshot = aria[:max_snapshot_chars] or None
                snapshot.locator_candidates = extract_locator_candidates(
                    aria, max_count=max_locator_candidates
                )
                snapshot.console_errors = console_errors(page)
                snapshot.network_errors = network_errors(page)
            finally:
                browser.close()
    except Exception as exc:
        logger.warning("Context collection failed for %s: %s", url, exc)
    return snapshot


def console_errors(page: Page) -> list[str]:
    """Console errors and warnings, then uncaught page errors."""
    lines = [
        f"[{message.type.upper()}] {message.text}"
        for message in page.console_messages()
        if message.type in _CONSOLE_TYPES
    ]
    lines += [f"[PAGEERROR] {error.message}" for error in page.page_errors()]
    return lines


def network_errors(page: Page) -> list[str]:
    """Requests that failed outright or came back with HTTP 400 or higher."""
    lines: list[str] = []
    for request in page.requests():
        if request.failure:
            lines.append(f"{request.method} {request.url} [{request.failure}]")
            continue
        response = request.existing_response
        if response is not None and response.status >= 400:
            lines.append(f"{request.method} {request.url} → {response.status}")
    return lines
```

Replace `src/workbench/context/__init__.py` with:

```python
"""Page context for generation and for healing when no failure snapshot exists."""

from workbench.context.collector import collect_context

__all__ = ["collect_context"]
```

Delete the replaced modules and the decision-rendering tests that read the old snapshot fields (those decision types are deleted in Tasks 7 and 8):

```bash
git rm -q src/workbench/context/accessibility.py src/workbench/context/console.py \
  src/workbench/context/network.py src/workbench/context/screenshot.py \
  src/workbench/context/locator_candidates.py tests/unit/test_visibility.py
```

- [ ] **Step 7: Point the 1.0 callers at the new snapshot**

- `src/workbench/heal/evidence.py`: replace the multi-line `collect_context(url, capture_html=True, ... capture_network=True,)` call with `collect_context(url)`.
- `src/workbench/models/heal.py`, in `Evidence.from_context_snapshot`: replace `screenshot_path=screenshot_path or snapshot.screenshot_path,` with `screenshot_path=screenshot_path,` and `accessibility_tree=snapshot.accessibility_tree,` with `accessibility_tree=snapshot.aria_snapshot,`.
- `src/workbench/models/generate.py`, in `GenerationDecision.to_markdown`: replace both `snap.accessibility_tree` with `snap.aria_snapshot`.
- `src/workbench/generate/pipeline.py`:
  - `collect_context(url, capture_html=True, capture_a11y=True)` becomes `collect_context(url)`;
  - `if not snapshot.html and not snapshot.accessibility_tree:` becomes `if snapshot.is_empty:`;
  - `if snapshot.accessibility_tree:` becomes `if snapshot.aria_snapshot:`;
  - `f"ACCESSIBILITY TREE:\n{snapshot.accessibility_tree[:5000]}"` becomes `f"PAGE SNAPSHOT:\n{snapshot.aria_snapshot[:5000]}"`.
- `tests/integration/test_pipeline.py`: `assert "ACCESSIBILITY TREE" in prompts[-1]` becomes `assert "PAGE SNAPSHOT" in prompts[-1]`.

Then run `grep -rn "accessibility_tree\|capture_a11y\|screenshot_path or snapshot" src` — the only remaining hits must be the 1.0 `Evidence` model and planner in `src/workbench/models/heal.py` and `src/workbench/heal/planner.py` (both replaced in Task 7).

- [ ] **Step 8: Share the sample-site fixture**

Move the `site` fixture (and its `_QuietHandler`, `SITE_DIR`, `SITE_PORT`, `SITE_URL` definitions) from `tests/integration/test_pipeline.py` into `tests/integration/conftest.py`, appending:

```python
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

SITE_DIR = config.PROJECT_ROOT / "samples" / "site"
# Fixed so specs written by tests can hard-code the URL.
SITE_PORT = int(os.environ.get("E2E_SITE_PORT", "4173"))
SITE_URL = f"http://127.0.0.1:{SITE_PORT}/"


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture(scope="session")
def site() -> str:
    handler = partial(_QuietHandler, directory=str(SITE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", SITE_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield SITE_URL
    server.shutdown()
    server.server_close()
```

(Move the new imports to the top of the file.) In `tests/integration/test_pipeline.py`, delete the moved definitions and import `SITE_URL` with `from tests.integration.conftest import SITE_URL` where `BROKEN_SPEC` uses it.

- [ ] **Step 9: Add the real-browser context test**

Create `tests/integration/test_context.py`:

```python
"""collect_context() against the sample site in a real Chromium."""

from workbench.context import collect_context


def test_sample_site_context(site: str) -> None:
    snap = collect_context(site)
    assert 'button "Submit"' in (snap.aria_snapshot or "")
    assert "getByRole('button', { name: 'Submit' })" in snap.locator_candidates
    assert "getByRole('textbox', { name: 'Name' })" in snap.locator_candidates
    assert snap.console_errors == []
    assert snap.network_errors == []
```

- [ ] **Step 10: Run every suite**

Run:

```bash
uv run python -m pytest -q -o addopts=
uv run python -m pytest tests/integration -q -o addopts=
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Expected: all pass.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "feat: collect page context with aria snapshots and Playwright's own signals" -m "Replaces the CDP accessibility tree and the custom console and network listeners." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Repair reports what it did

**Files:**

- Modify: `src/workbench/heal/repair.py`, `src/workbench/models/heal.py`, `src/workbench/heal/__init__.py`, `tests/unit/test_ast_repair.py`, `tests/unit/test_healing.py`
- Create: `src/workbench/environment.py`, `tests/unit/test_repair.py`, `tests/unit/test_environment.py`
- Delete: `tests/unit/test_fixer.py`

**Interfaces:**

- Consumes: `HealingAction`, `RepairStrategy` (unchanged).
- Produces:
  - `workbench.models.heal.RepairMethod = Literal["ast", "text"]`, `RepairResult(code: str, method: RepairMethod | None, ast_unavailable: bool = False)`
  - `workbench.heal.repair.apply_fix(code: str, action: HealingAction) -> RepairResult`; `_apply_ast_fix(code, action) -> str`; `_apply_string_fix(code, action) -> str`
  - `workbench.environment.node_available() -> bool`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_environment.py`:

```python
"""Checks for the external tools the workbench needs."""

import pytest

from workbench import environment


def test_node_available_follows_the_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(environment.shutil, "which", lambda name: "/usr/bin/node")
    assert environment.node_available()
    monkeypatch.setattr(environment.shutil, "which", lambda name: None)
    assert not environment.node_available()
```

Create `tests/unit/test_repair.py`:

```python
"""apply_fix() edits the code and says how: AST, text, or not at all."""

import pytest

from workbench.heal import repair
from workbench.heal.repair import apply_fix
from workbench.models.heal import REPAIR_STRATEGY_LABELS, HealingAction, RepairStrategy


def _action(
    original: str, fixed: str, strategy: RepairStrategy = RepairStrategy.STRING_REPLACE
) -> HealingAction:
    return HealingAction(
        original_code=original,
        fixed_code=fixed,
        description="",
        repair_strategy=strategy,
    )


def test_whitespace_tolerant_text_fix() -> None:
    code = "\n        // comment\n        await page.click('#wrong');\n        // next line\n        "
    result = apply_fix(
        code, _action("await page.click('#wrong');", "await page.click('#right');")
    )
    assert result.method == "text"
    assert (
        result.code.strip()
        == "// comment\n        await page.click('#right');\n        // next line"
    )


def test_multiline_fix_keeps_indentation() -> None:
    code = "\n    test('foo', async ({ page }) => {\n        await page.goto('url');\n        await page.click('#wrong');\n    });\n"
    result = apply_fix(
        code,
        _action(
            "await page.goto('url');\nawait page.click('#wrong');",
            "await page.goto('url');\nawait page.click('#right');",
        ),
    )
    assert result.code.strip() == (
        "test('foo', async ({ page }) => {\n        await page.goto('url');\n"
        "        await page.click('#right');\n    });"
    )


def test_nested_replacement_is_reindented() -> None:
    code = "\n    test('nested', async ({ page }) => {\n        await page.click('#wrong');\n        // extra comments\n    });\n"
    result = apply_fix(
        code,
        _action(
            "await page.click('#wrong');",
            "await page.click('#right');\nif (success) {\n    await page.click('#done');\n}",
        ),
    )
    assert result.code.strip() == (
        "test('nested', async ({ page }) => {\n        await page.click('#right');\n"
        "        if (success) {\n            await page.click('#done');\n        }\n"
        "        // extra comments\n    });"
    )


def test_missing_target_changes_nothing() -> None:
    result = apply_fix(
        "await page.click('#a');", _action("await page.click('#zzz');", "x")
    )
    assert result.method is None
    assert result.code == "await page.click('#a');"


def test_ast_result_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repair, "node_available", lambda: True)
    monkeypatch.setattr(
        repair, "_apply_ast_fix", lambda code, action: code.replace("#old", "#new")
    )
    action = _action(
        'page.locator("#old")', 'page.locator("#new")', RepairStrategy.SELECTOR_REPLACE
    )
    result = apply_fix('await page.locator("#old").click();', action)
    assert result.method == "ast"
    assert result.code == 'await page.locator("#new").click();'
    assert not result.ast_unavailable


def test_missing_node_falls_back_to_text_and_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repair, "node_available", lambda: False)
    action = _action(
        'page.locator("#old")', 'page.locator("#new")', RepairStrategy.SELECTOR_REPLACE
    )
    result = apply_fix('await page.locator("#old").click();', action)
    assert result.method == "text"
    assert result.ast_unavailable
    assert result.code == 'await page.locator("#new").click();'


def test_every_strategy_has_a_label() -> None:
    assert set(REPAIR_STRATEGY_LABELS) == set(RepairStrategy)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run python -m pytest tests/unit/test_repair.py tests/unit/test_environment.py -q -o addopts=`
Expected: collection errors (`No module named 'workbench.environment'`, `apply_fix` signature).

- [ ] **Step 3: Add `RepairResult` and `environment.py`**

Append to `src/workbench/models/heal.py` (add `Literal` to its `typing` import):

```python
RepairMethod = Literal["ast", "text"]


class RepairResult(BaseModel):
    """The code after a repair attempt, and how the change was made."""

    code: str
    method: RepairMethod | None = Field(
        default=None, description="None when nothing in the code changed."
    )
    ast_unavailable: bool = Field(
        default=False,
        description="An AST strategy was requested but Node.js was not found.",
    )
```

Create `src/workbench/environment.py`:

```python
"""Checks for the external tools the workbench depends on."""

import shutil


def node_available() -> bool:
    """True when Node.js is on the PATH (needed for the ts-morph AST repair)."""
    return shutil.which("node") is not None
```

- [ ] **Step 4: Change `src/workbench/heal/repair.py` to the new signature**

- Move `from workbench.config import AST_REPAIR_SCRIPT, PROJECT_ROOT` up into the import block (it currently sits after `logger = ...`), keep `_AST_SCRIPT = AST_REPAIR_SCRIPT` below the imports, and add `from workbench.environment import node_available` and `from workbench.models.heal import HealingAction, RepairResult, RepairStrategy` (dropping `HealingDecision`).
- Replace `apply_fix` with:

```python
def apply_fix(code: str, action: HealingAction) -> RepairResult:
    """Apply the proposed change: AST first, text replacement as the fallback.

    Returns the new code and how it was changed; ``method`` is None when no
    strategy found the code to replace.
    """
    ast_unavailable = False
    if action.repair_strategy != RepairStrategy.STRING_REPLACE:
        if node_available():
            new_code = _apply_ast_fix(code, action)
            if new_code != code:
                return RepairResult(code=new_code, method="ast")
            logger.warning(
                "AST repair (%s) made no change; trying text replacement",
                action.repair_strategy.value,
            )
        else:
            ast_unavailable = True
            logger.warning("Node.js not found; using text replacement")
    new_code = _apply_string_fix(code, action)
    return RepairResult(
        code=new_code,
        method="text" if new_code != code else None,
        ast_unavailable=ast_unavailable,
    )
```

- Change `_apply_ast_fix(current_code: str, decision: HealingDecision)` to `_apply_ast_fix(current_code: str, action: HealingAction)` and `_apply_string_fix(current_code: str, decision: HealingDecision)` to `_apply_string_fix(current_code: str, action: HealingAction)`, replacing every `decision.action_taken.` inside them with `action.`.
- Update the module docstring: the AST script is `src/workbench/heal/ast_repair.js` (not `scripts/ast_repair.js`); fix the same stale path in the `_apply_ast_fix` docstring.

In `src/workbench/heal/__init__.py`, replace `new_code = apply_fix(validated_path, current_code, decision)` with `new_code = apply_fix(current_code, decision.action_taken).code`. In `src/workbench/heal/ast_repair.js`, change the comment `The Python caller in src/healing/repair.py` to `The Python caller in src/workbench/heal/repair.py`.

- [ ] **Step 5: Update the AST tests and delete the old fixer tests**

```bash
git rm -q tests/unit/test_fixer.py
uv run python - <<'EOF'
import re
from pathlib import Path
p = Path("tests/unit/test_ast_repair.py")
s = p.read_text(encoding="utf-8")
start = s.index("def _make_decision(")
end = s.index("def _ast_available")
s = s[:start] + '''def _make_action(
    *,
    original_code: str = "",
    fixed_code: str = "",
    description: str = "",
    strategy: RepairStrategy = RepairStrategy.STRING_REPLACE,
) -> HealingAction:
    return HealingAction(
        original_code=original_code,
        fixed_code=fixed_code,
        description=description,
        repair_strategy=strategy,
    )


''' + s[end:]
s = s.replace("_make_decision(", "_make_action(")
s = re.sub(r"\bdecision\b", "action", s)
s = re.sub(r'apply_fix\("[^"]*", ([^,()]+(?:\([^()]*\))?), action\)', r"apply_fix(\1, action).code", s)
s = s.replace('AST_SCRIPT = PROJECT_ROOT / "scripts" / "ast_repair.js"\n', "")
p.write_text(s, encoding="utf-8")
EOF
grep -n "apply_fix(\"\|_make_decision\|failure_type=\|HealingDecision\|AST_SCRIPT" tests/unit/test_ast_repair.py
```

Expected: the `grep` prints only import lines that still name `HealingDecision`, `Evidence` or `FailureType`; remove those names from the imports. Any `failure_type=` argument left in a `_make_action(...)` call must be deleted, and any `action.action_taken.` left by the rename becomes `action.` (check with `grep -n "action_taken" tests/unit/test_ast_repair.py`, which must print nothing).

In the class `TestApplyFixRouting`, add as its first method so routing tests do not depend on the machine:

```python
    def setUp(self):
        patcher = patch("workbench.heal.repair.node_available", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
```

In `tests/unit/test_healing.py`, delete the class `TestRepairSmoke` (covered by `test_repair.py`).

- [ ] **Step 6: Run every suite**

Run:

```bash
uv run python -m pytest -q -o addopts=
uv run python -m pytest tests/integration -q -o addopts=
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Expected: all pass; `test_repair.py` 7 passed, `test_environment.py` 1 passed.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: apply_fix returns the new code and how it changed" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: One model interface, with schema-constrained output

**Files:**

- Create: `src/workbench/llm/chat.py`, `tests/unit/test_chat.py`
- Modify: `src/workbench/llm/router.py`, `tests/unit/test_llm.py`

**Interfaces:**

- Consumes: `LLMRouter`, `LLMRequest`, `LLMResponse` from `workbench.llm.router`.
- Produces:
  - `workbench.llm.chat.Message = dict[str, str]`
  - `ChatReply(content, model="", provider="", input_tokens=0, output_tokens=0, latency_ms=0)`
  - `ChatModel` protocol: `chat(messages: list[Message], *, json_schema: dict[str, Any] | None = None, temperature: float = 0.1) -> ChatReply`
  - `ModelError(RuntimeError)`
  - `response_format_for(json_schema: dict[str, Any]) -> dict[str, Any]`
  - `RouterChatModel(router)` implementing `ChatModel`
  - `LLMRequest.response_format: dict[str, Any] | None`

- [ ] **Step 1: Write the failing router tests**

Append to `tests/unit/test_llm.py` (it already imports `MagicMock`, `_make_router` and `_make_completion`; add `import httpx` and `import openai` at the top):

```python
def _bad_request() -> openai.BadRequestError:
    request = httpx.Request("POST", "http://localhost:9999/v1/chat/completions")
    return openai.BadRequestError(
        "response_format is not supported",
        response=httpx.Response(400, request=request),
        body=None,
    )


class TestRequestOptions(unittest.TestCase):
    def _router_with_client(self, **kwargs):
        router = _make_router(**kwargs)
        router._LLMRouter__primary_client = MagicMock()
        return router, router._LLMRouter__primary_client.chat.completions.create

    def test_response_format_is_sent(self):
        router, create = self._router_with_client()
        create.return_value = _make_completion()
        fmt = {"type": "json_schema", "json_schema": {"name": "X", "schema": {}}}
        router.complete(LLMRequest(messages=[], model="m", response_format=fmt))
        self.assertEqual(create.call_args.kwargs["response_format"], fmt)

    def test_response_format_is_omitted_when_unset(self):
        router, create = self._router_with_client()
        create.return_value = _make_completion()
        router.complete(LLMRequest(messages=[], model="m"))
        self.assertNotIn("response_format", create.call_args.kwargs)

    def test_bad_request_is_not_retried(self):
        router, create = self._router_with_client(
            retry_policy=RetryPolicy(max_retries=2)
        )
        create.side_effect = _bad_request()
        with self.assertRaises(RuntimeError) as caught:
            router.complete(LLMRequest(messages=[], model="m"))
        self.assertEqual(create.call_count, 1)
        self.assertIsInstance(caught.exception.__cause__, openai.BadRequestError)
```

(`LLMRequest` and `RetryPolicy` are already imported in that file; if not, import them from `workbench.llm`.)

- [ ] **Step 2: Write the failing adapter tests**

Create `tests/unit/test_chat.py`:

```python
"""RouterChatModel turns router responses into ChatReply and handles schemas."""

from typing import Any

import httpx
import openai
import pytest

from workbench.llm.chat import ModelError, RouterChatModel, response_format_for
from workbench.llm.router import LLMRequest, LLMResponse

SCHEMA = {"title": "HealingAnalysis", "type": "object"}
MESSAGES = [{"role": "user", "content": "hi"}]


def _response(content: str = "{}") -> LLMResponse:
    return LLMResponse(
        content=content,
        model_used="m-1",
        provider="lm_studio",
        latency_ms=12,
        input_tokens=3,
        output_tokens=4,
    )


def _rejected() -> RuntimeError:
    request = httpx.Request("POST", "http://x/v1/chat/completions")
    error = RuntimeError("rejected")
    error.__cause__ = openai.BadRequestError(
        "unsupported", response=httpx.Response(400, request=request), body=None
    )
    return error


class FakeRouter:
    primary_model = "fake-model"

    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def test_reply_carries_provenance() -> None:
    reply = RouterChatModel(FakeRouter([_response("ok")])).chat(MESSAGES)  # type: ignore[arg-type]
    assert (reply.content, reply.model, reply.provider) == ("ok", "m-1", "lm_studio")
    assert (reply.input_tokens, reply.output_tokens, reply.latency_ms) == (3, 4, 12)


def test_schema_becomes_a_response_format() -> None:
    router = FakeRouter([_response()])
    RouterChatModel(router).chat(MESSAGES, json_schema=SCHEMA)  # type: ignore[arg-type]
    assert router.requests[0].response_format == response_format_for(SCHEMA)
    assert response_format_for(SCHEMA)["json_schema"]["name"] == "HealingAnalysis"


def test_no_schema_sends_no_response_format() -> None:
    router = FakeRouter([_response()])
    RouterChatModel(router).chat(MESSAGES)  # type: ignore[arg-type]
    assert router.requests[0].response_format is None


def test_rejected_schema_is_retried_without_it() -> None:
    router = FakeRouter([_rejected(), _response("{}")])
    reply = RouterChatModel(router).chat(MESSAGES, json_schema=SCHEMA)  # type: ignore[arg-type]
    assert reply.content == "{}"
    assert [r.response_format is None for r in router.requests] == [False, True]


def test_other_failures_become_model_errors() -> None:
    router = FakeRouter([RuntimeError("connection refused")])
    with pytest.raises(ModelError, match="connection refused"):
        RouterChatModel(router).chat(MESSAGES, json_schema=SCHEMA)  # type: ignore[arg-type]


def test_failure_after_the_retry_is_a_model_error() -> None:
    router = FakeRouter([_rejected(), RuntimeError("still down")])
    with pytest.raises(ModelError, match="still down"):
        RouterChatModel(router).chat(MESSAGES, json_schema=SCHEMA)  # type: ignore[arg-type]
```

- [ ] **Step 3: Run them to verify they fail**

Run: `uv run python -m pytest tests/unit/test_chat.py tests/unit/test_llm.py -q -o addopts=`
Expected: `test_chat.py` fails to import `workbench.llm.chat`; `TestRequestOptions` fails on the unknown `response_format` field.

- [ ] **Step 4: Teach the router `response_format` and stop retrying bad requests**

In `src/workbench/llm/router.py`:

- add `import openai` to the imports;
- add to `LLMRequest`, after `max_tokens`:

```python
    response_format: dict[str, Any] | None = Field(
        default=None,
        description="OpenAI response_format, e.g. a JSON schema the reply must match.",
    )
```

- replace the helper `_max_tokens_kwargs` with:

```python
def _request_kwargs(request: LLMRequest) -> dict[str, Any]:
    """Optional arguments, sent only when set so providers keep their defaults."""
    kwargs: dict[str, Any] = {}
    if request.max_tokens:
        kwargs["max_tokens"] = request.max_tokens
    if request.response_format:
        kwargs["response_format"] = request.response_format
    return kwargs
```

  and change both `**_max_tokens_kwargs(request),` call sites to `**_request_kwargs(request),`;

- in `complete()`, add before `except Exception as exc:` in the primary loop:

```python
            except openai.BadRequestError as exc:
                # The provider rejected the request itself; retrying cannot help.
                raise RuntimeError(
                    f"The provider rejected the request (model={request.model}): {exc}"
                ) from exc
```

- replace both occurrences of `See docs/env-variables.md for the full reference.` with `See .env.example for the variables.`

- [ ] **Step 5: Write `src/workbench/llm/chat.py`**

```python
"""The one interface pipelines use to talk to a model.

Pipelines depend on ``ChatModel``, never on a provider. Phase 3 adds the
LM Studio, Ollama and Demo implementations; until then ``RouterChatModel``
adapts the 1.0 router.
"""

import logging
from typing import Any, Protocol

import openai
from pydantic import BaseModel

from workbench.llm.router import LLMRequest, LLMResponse, LLMRouter

logger = logging.getLogger(__name__)

Message = dict[str, str]


class ChatReply(BaseModel):
    """A model's answer and what produced it."""

    content: str
    model: str = ""
    provider: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


class ModelError(RuntimeError):
    """The model could not be reached or did not answer."""


class ChatModel(Protocol):
    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> ChatReply:
        """Send ``messages``; with ``json_schema``, ask for output matching it."""
        ...


def response_format_for(json_schema: dict[str, Any]) -> dict[str, Any]:
    """OpenAI-style ``response_format`` asking for output matching ``json_schema``."""
    return {
        "type": "json_schema",
        "json_schema": {
            "name": str(json_schema.get("title", "response")),
            "schema": json_schema,
        },
    }


def _rejected_by_provider(exc: BaseException) -> bool:
    cause: BaseException | None = exc
    while cause is not None:
        if isinstance(cause, openai.BadRequestError):
            return True
        cause = cause.__cause__
    return False


class RouterChatModel:
    """Adapts the 1.0 ``LLMRouter`` to ``ChatModel`` (replaced in Phase 3)."""

    def __init__(self, router: LLMRouter) -> None:
        self._router = router

    def chat(
        self,
        messages: list[Message],
        *,
        json_schema: dict[str, Any] | None = None,
        temperature: float = 0.1,
    ) -> ChatReply:
        response_format = response_format_for(json_schema) if json_schema else None
        try:
            response = self._complete(messages, temperature, response_format)
        except RuntimeError as exc:
            if response_format is None or not _rejected_by_provider(exc):
                raise ModelError(str(exc)) from exc
            logger.info("The provider rejected the JSON schema; asking without it.")
            try:
                response = self._complete(messages, temperature, None)
            except RuntimeError as retry_exc:
                raise ModelError(str(retry_exc)) from retry_exc
        return ChatReply(
            content=response.content,
            model=response.model_used,
            provider=response.provider,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=response.latency_ms,
        )

    def _complete(
        self,
        messages: list[Message],
        temperature: float,
        response_format: dict[str, Any] | None,
    ) -> LLMResponse:
        return self._router.complete(
            LLMRequest(
                messages=list(messages),
                model=self._router.primary_model,
                temperature=temperature,
                response_format=response_format,
            )
        )
```

- [ ] **Step 6: Run the tests**

Run: `uv run python -m pytest -q -o addopts= && uv run ruff check . && uv run ruff format --check . && uv run mypy`
Expected: all pass (`test_chat.py` 6 passed; `TestRequestOptions` 3 passed).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add the ChatModel interface with schema-constrained output" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Run reports and progress events

**Files:**

- Modify: `src/workbench/models/shared.py`, `src/workbench/models/heal.py`, `src/workbench/models/generate.py`
- Create: `src/workbench/models/events.py`, `src/workbench/events.py`, `src/workbench/reports.py`, `tests/unit/test_reports.py`, `tests/unit/test_events.py`

**Interfaces:**

- Consumes: `RunResult` (Task 2), `HealingAnalysis`, `RepairMethod` (Task 4), `new_run_id` and `reports_dir()` (Task 1).
- Produces:
  - `workbench.models.shared`: `RunWarning = Literal["page_context_unavailable", "ast_unavailable", "playwright_browsers_missing"]`, `Provenance`, `PromptSection` (property `truncated`), `ModelExchange`
  - `workbench.models.heal`: `EvidenceSource`, `FailureEvidence`, `AttemptOutcome`, `Attempt`, `HealStatus`, `HealReport`
  - `workbench.models.generate`: `GenerateStatus`, `ContextSummary`, `GenerateReport`
  - `workbench.models.events`: `EventKind`, `StepName`, `StepState`, `RunEvent`
  - `workbench.events`: `Emit = Callable[[RunEvent], None]`, `EventSink(run_id, emit=None)` with `step(step, state, detail="")`, `log(text)`, `attempt(number, outcome)`, `done(status)`
  - `workbench.reports`: `report_path(report_id) -> Path`, `save_report(report) -> Path`, `load_report(report_id) -> HealReport | GenerateReport`, `list_report_ids(limit=20) -> list[str]`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_events.py`:

```python
"""EventSink numbers events and stamps their elapsed time."""

from workbench.events import EventSink
from workbench.models.events import RunEvent


def test_events_are_numbered_and_typed() -> None:
    seen: list[RunEvent] = []
    sink = EventSink("run-1", seen.append)
    sink.step("run", "active", "npx playwright test a.spec.ts")
    sink.log("hello")
    sink.attempt(1, "healed")
    sink.done("healed")

    assert [e.seq for e in seen] == [1, 2, 3, 4]
    assert [e.kind for e in seen] == ["step", "log", "attempt", "done"]
    assert (seen[0].step, seen[0].state) == ("run", "active")
    assert seen[2].detail == "Attempt 1: healed"
    assert seen[3].detail == "healed"
    assert all(e.run_id == "run-1" and e.elapsed_ms >= 0 for e in seen)


def test_sink_without_a_listener_discards_events() -> None:
    assert EventSink("run-2").done("error").seq == 1
```

Create `tests/unit/test_reports.py`:

```python
"""Reports round-trip through JSON files in the workspace."""

from pathlib import Path

import pytest

from workbench.models.generate import ContextSummary, GenerateReport
from workbench.models.heal import Attempt, FailureEvidence, HealReport
from workbench.models.shared import ModelExchange, PromptSection, RunResult
from workbench.reports import list_report_ids, load_report, report_path, save_report


@pytest.fixture(autouse=True)
def _workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WORKBENCH_WORKSPACE", str(tmp_path))


def _heal(report_id: str = "20261003-140509-heal-contact") -> HealReport:
    return HealReport(
        id=report_id,
        spec_name="contact.spec.ts",
        status="healed",
        attempts=[
            Attempt(
                number=1,
                outcome="healed",
                evidence=FailureEvidence(error_message="boom", source="error_context"),
                exchange=ModelExchange(
                    sections=[
                        PromptSection(name="Test file", chars=10, original_chars=20)
                    ],
                    valid=True,
                ),
                repair_method="ast",
                rerun=RunResult(status="passed", video_path="/v.webm"),
            )
        ],
        warnings=["ast_unavailable"],
    )


def test_heal_report_round_trip() -> None:
    report = _heal()
    save_report(report)
    loaded = load_report("20261003-140509-heal-contact")
    assert isinstance(loaded, HealReport)
    assert loaded == report
    assert loaded.attempts[0].exchange.sections[0].truncated  # type: ignore[union-attr]


def test_generate_report_round_trip() -> None:
    report = GenerateReport(
        id="20261003-140600-generate-login",
        url="http://x/",
        scenario="login",
        status="not_run",
        context=ContextSummary(url="http://x/", snapshot_lines=3),
    )
    save_report(report)
    assert load_report(report.id) == report


def test_list_is_newest_first() -> None:
    save_report(_heal("20261003-140509-heal-a"))
    save_report(_heal("20261003-150000-heal-b"))
    assert list_report_ids() == ["20261003-150000-heal-b", "20261003-140509-heal-a"]


@pytest.mark.parametrize(
    "bad_id", ["../../etc/passwd", "x.json", "", "20261003-140509-heal-A"]
)
def test_load_report_rejects_path_traversal(bad_id: str) -> None:
    with pytest.raises(ValueError):
        report_path(bad_id)


def test_unknown_report_is_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_report("20261003-140509-heal-missing")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run python -m pytest tests/unit/test_events.py tests/unit/test_reports.py -q -o addopts=`
Expected: collection errors (`No module named 'workbench.events'`).

- [ ] **Step 3: Add the shared contracts**

Append to `src/workbench/models/shared.py`:

```python
RunWarning = Literal[
    "page_context_unavailable",
    "ast_unavailable",
    "playwright_browsers_missing",
]


class Provenance(BaseModel):
    """Which model and prompt produced an answer, and what it cost."""

    provider: str = ""
    model: str = ""
    prompt_name: str = ""
    prompt_version: str = ""
    prompt_hash: str = ""
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)


class PromptSection(BaseModel):
    """One named block of context sent to the model."""

    name: str
    chars: int = Field(ge=0)
    original_chars: int | None = Field(
        default=None, ge=0, description="Set when the content was cut to fit."
    )

    @property
    def truncated(self) -> bool:
        """True when the section was cut to its limit."""
        return self.original_chars is not None


class ModelExchange(BaseModel):
    """What was sent to the model and what came back (the UI's Model I/O view)."""

    sections: list[PromptSection] = Field(default_factory=list)
    raw_response: str = ""
    valid: bool = False
    validation_error: str = ""
    provenance: Provenance = Field(default_factory=Provenance)
```

- [ ] **Step 4: Add the heal and generate reports**

Append to `src/workbench/models/heal.py` (import `ModelExchange`, `RunResult`, `RunWarning` from `.shared`; `datetime` is already imported):

```python
EvidenceSource = Literal["error_context", "page_load", "none"]
AttemptOutcome = Literal[
    "healed", "rerun_failed", "not_applied", "invalid_reply", "app_defect", "cancelled"
]
HealStatus = Literal[
    "healed",
    "not_healed",
    "app_defect_suspected",
    "nothing_to_heal",
    "cancelled",
    "error",
]


class FailureEvidence(BaseModel):
    """What the model is shown about a failure."""

    error_message: str = ""
    error_location: str = ""
    page_snapshot: str | None = None
    screenshot_path: str | None = None
    console_errors: list[str] = Field(default_factory=list)
    network_errors: list[str] = Field(default_factory=list)
    locator_candidates: list[str] = Field(default_factory=list)
    source: EvidenceSource = "none"


class Attempt(BaseModel):
    """One diagnose → repair → verify cycle."""

    number: int = Field(ge=1)
    outcome: AttemptOutcome
    evidence: FailureEvidence | None = None
    analysis: HealingAnalysis | None = None
    exchange: ModelExchange | None = None
    repair_method: RepairMethod | None = None
    rerun: RunResult | None = None
    duration_ms: int = Field(default=0, ge=0)


class HealReport(BaseModel):
    """Everything about one heal run; the UI and downloads read this."""

    kind: Literal["heal"] = "heal"
    id: str
    spec_name: str
    status: HealStatus
    max_attempts: int = Field(default=3, ge=1, le=5)
    attempts: list[Attempt] = Field(default_factory=list)
    initial_run: RunResult | None = None
    original_code: str = ""
    final_code: str = ""
    diff: str = ""
    classifier_hint: str = ""
    warnings: list[RunWarning] = Field(default_factory=list)
    error_message: str = ""
    started_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    duration_ms: int = Field(default=0, ge=0)
```

Append to `src/workbench/models/generate.py` (add `from datetime import datetime`, `from typing import Literal`, and import `ModelExchange`, `RunResult`, `RunWarning` from `.shared`):

```python
GenerateStatus = Literal["passed", "failed", "not_run", "cancelled", "error"]


class ContextSummary(BaseModel):
    """The page context a generation used, in counts the UI can show."""

    url: str
    snapshot_lines: int = Field(default=0, ge=0)
    locator_candidates: list[str] = Field(default_factory=list)
    console_errors: int = Field(default=0, ge=0)
    failed_requests: int = Field(default=0, ge=0)


class GenerateReport(BaseModel):
    """Everything about one generate run."""

    kind: Literal["generate"] = "generate"
    id: str
    url: str
    scenario: str
    status: GenerateStatus
    spec_name: str = ""
    code: str = ""
    context: ContextSummary | None = None
    exchange: ModelExchange | None = None
    run: RunResult | None = None
    warnings: list[RunWarning] = Field(default_factory=list)
    error_message: str = ""
    started_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    duration_ms: int = Field(default=0, ge=0)
```

`GenerateStatus` adds `cancelled` to the spec's list (section 6.4): a generation can be cancelled from the UI like a heal.

- [ ] **Step 5: Add events and the report store**

Create `src/workbench/models/events.py`:

```python
"""Progress events a pipeline emits; the web UI streams them over SSE."""

from typing import Literal

from pydantic import BaseModel, Field

EventKind = Literal["step", "log", "attempt", "done"]
StepName = Literal[
    "run", "evidence", "diagnose", "repair", "verify", "context", "model", "execute"
]
StepState = Literal["pending", "active", "done", "failed", "skipped"]


class RunEvent(BaseModel):
    """One progress update from a running pipeline."""

    run_id: str
    seq: int = Field(ge=1)
    kind: EventKind
    step: StepName | None = None
    state: StepState | None = None
    detail: str = ""
    elapsed_ms: int = Field(default=0, ge=0)
```

Create `src/workbench/events.py`:

```python
"""Numbers and timestamps the progress events a pipeline emits."""

import time
from collections.abc import Callable

from workbench.models.events import EventKind, RunEvent, StepName, StepState

Emit = Callable[[RunEvent], None]


def _discard(_event: RunEvent) -> None:
    return None


class EventSink:
    """Sends ``RunEvent``s to a listener, numbered from 1 with elapsed time."""

    def __init__(self, run_id: str, emit: Emit | None = None) -> None:
        self.run_id = run_id
        self._emit = emit or _discard
        self._seq = 0
        self._started = time.monotonic()

    def step(self, step: StepName, state: StepState, detail: str = "") -> RunEvent:
        return self._send("step", step=step, state=state, detail=detail)

    def log(self, text: str) -> RunEvent:
        return self._send("log", detail=text)

    def attempt(self, number: int, outcome: str) -> RunEvent:
        return self._send("attempt", detail=f"Attempt {number}: {outcome}")

    def done(self, status: str) -> RunEvent:
        return self._send("done", detail=status)

    def _send(
        self,
        kind: EventKind,
        *,
        step: StepName | None = None,
        state: StepState | None = None,
        detail: str = "",
    ) -> RunEvent:
        self._seq += 1
        event = RunEvent(
            run_id=self.run_id,
            seq=self._seq,
            kind=kind,
            step=step,
            state=state,
            detail=detail,
            elapsed_ms=int((time.monotonic() - self._started) * 1000),
        )
        self._emit(event)
        return event
```

Create `src/workbench/reports.py`:

```python
"""Saves and loads the one JSON report each heal or generate run produces."""

import re
from pathlib import Path
from typing import Annotated

from pydantic import Field, TypeAdapter

from workbench.config import reports_dir
from workbench.models.generate import GenerateReport
from workbench.models.heal import HealReport

Report = HealReport | GenerateReport
_ADAPTER: TypeAdapter[Report] = TypeAdapter(
    Annotated[Report, Field(discriminator="kind")]
)
_REPORT_ID = re.compile(r"\d{8}-\d{6}-(heal|generate)-[a-z0-9-]+")


def report_path(report_id: str) -> Path:
    """Path of a report; rejects anything that is not a generated id."""
    if not _REPORT_ID.fullmatch(report_id):
        raise ValueError(f"Not a report id: {report_id!r}")
    return reports_dir() / f"{report_id}.json"


def save_report(report: Report) -> Path:
    path = report_path(report.id)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_report(report_id: str) -> Report:
    return _ADAPTER.validate_json(report_path(report_id).read_text(encoding="utf-8"))


def list_report_ids(limit: int = 20) -> list[str]:
    """Report ids, newest first (ids start with their timestamp)."""
    ids = [p.stem for p in reports_dir().glob("*.json") if _REPORT_ID.fullmatch(p.stem)]
    return sorted(ids, reverse=True)[:limit]
```

- [ ] **Step 6: Run the tests**

Run: `uv run python -m pytest -q -o addopts= && uv run ruff check . && uv run ruff format --check . && uv run mypy`
Expected: all pass (`test_events.py` 2, `test_reports.py` 8).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: add run reports, model exchange records and progress events" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: The heal pipeline

**Files:**

- Rewrite: `src/workbench/heal/evidence.py`, `src/workbench/heal/planner.py`, `src/workbench/heal/__init__.py`, `src/workbench/prompts/healer.md`, `tests/unit/test_schemas.py` (two classes removed)
- Create: `src/workbench/heal/pipeline.py`, `tests/unit/test_evidence.py`, `tests/unit/test_planner.py`, `tests/unit/test_heal_pipeline.py`, `tests/unit/test_prompts.py`
- Modify: `src/workbench/llm/prompts.py`, `src/workbench/environment.py`, `src/workbench/prompts/manifest.json`, `src/workbench/models/heal.py`, `src/workbench/models/shared.py`, `src/workbench/models/__init__.py`, `src/workbench/config.py`, `src/workbench/validation.py`, `tests/unit/test_environment.py`, `tests/integration/fake_llm.py`, `tests/integration/test_pipeline.py`
- Delete: `src/workbench/heal/verifier.py`, `src/workbench/heal/artifact_store.py`, `tests/unit/test_healing.py`, `tests/unit/test_explainability.py`, `tests/unit/test_provenance.py`, `tests/unit/test_path_validation.py`

**Interfaces:**

- Consumes: `run_test` (Task 2), `collect_context`, `extract_locator_candidates` (Task 3), `apply_fix`, `node_available` (Task 4), `ChatModel`, `ModelError` (Task 5), reports, events and report models (Task 6), `classify_failure_heuristic` (unchanged).
- Produces:
  - `workbench.llm.prompts.render_prompt(sections: list[tuple[str, str]], limits: dict[str, int]) -> tuple[str, list[PromptSection]]`
  - `workbench.environment.chromium_installed() -> bool`
  - `workbench.heal.evidence`: `Collect = Callable[[str], ContextSnapshot]`, `extract_url_from_code(code)`, `parse_error_context(text) -> str | None`, `gather_evidence(code, result, *, collect=collect_context) -> tuple[FailureEvidence, list[RunWarning]]`
  - `workbench.heal.planner`: `Hint = tuple[FailureType, float, str]`, `LIMITS`, `build_sections(code, evidence)`, `plan_fix(*, code, evidence, hint, model) -> tuple[HealingAnalysis | None, ModelExchange]`
  - `workbench.heal.pipeline`: `APP_DEFECT_CONFIDENCE = 0.7`, `HealRequest(spec_path: Path, max_attempts: int = 3)`, `heal(request, *, model, emit=None, cancel=None, run=run_test, collect=collect_context, browsers_ready=chromium_installed) -> HealReport`
  - `workbench.heal` re-exports `heal`, `HealRequest`, `APP_DEFECT_CONFIDENCE`

- [ ] **Step 1: Write the failing evidence and planner tests**

Create `tests/unit/test_evidence.py`:

````python
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
````

Create `tests/unit/test_planner.py`:

```python
"""plan_fix() sends named, size-limited sections and records the exchange."""

import json
from typing import Any

import pytest

from workbench.heal.planner import LIMITS, plan_fix
from workbench.llm.chat import ChatReply
from workbench.models.heal import FailureEvidence, HealingAnalysis
from workbench.models.shared import FailureType

CODE = 'await page.locator("#submit-btn").click();\n'
HINT = (FailureType.TIMEOUT, 1.0, "Detected 'TimeoutError'")


def analysis(failure_type: str = "LOCATOR_DRIFT") -> str:
    return json.dumps(
        {
            "failure_type": failure_type,
            "failure_summary": "The selector drifted",
            "hypothesis": "Use the role-based locator",
            "confidence_score": 0.92,
            "confidence_rationale": "The snapshot shows the button",
            "reasoning_steps": ["#submit-btn is gone", "button 'Submit' exists"],
            "root_cause_evidence": ['button "Submit" [ref=e3]'],
            "action_taken": {
                "original_code": 'page.locator("#submit-btn")',
                "fixed_code": 'page.getByRole("button", { name: "Submit" })',
                "description": "Role-based locator",
                "repair_strategy": "selector_replace",
            },
        }
    )


class FakeModel:
    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, Any]] = []

    def chat(self, messages, *, json_schema=None, temperature=0.1) -> ChatReply:
        self.calls.append({"messages": messages, "json_schema": json_schema})
        return ChatReply(
            content=self.replies.pop(0),
            model="m-1",
            provider="fake",
            input_tokens=9,
            output_tokens=3,
            latency_ms=5,
        )


def _evidence(**changes: Any) -> FailureEvidence:
    base = FailureEvidence(
        error_message="TimeoutError: locator.click",
        error_location="/w/a.spec.ts:5:37",
        page_snapshot='- button "Submit" [ref=e3]',
        locator_candidates=["getByRole('button', { name: 'Submit' })"],
        source="error_context",
    )
    return base.model_copy(update=changes)


def test_sections_and_schema_are_sent() -> None:
    model = FakeModel(analysis())
    result, exchange = plan_fix(code=CODE, evidence=_evidence(), hint=HINT, model=model)

    assert result is not None and result.failure_type == FailureType.LOCATOR_DRIFT
    assert [s.name for s in exchange.sections] == [
        "Test file",
        "Error",
        "Page snapshot at failure",
        "Locator candidates",
    ]
    user = model.calls[0]["messages"][1]["content"]
    assert user.startswith("## Test file\n" + CODE)
    assert "## Error\nTimeoutError: locator.click\nat /w/a.spec.ts:5:37" in user
    assert model.calls[0]["json_schema"] == HealingAnalysis.model_json_schema()
    system = model.calls[0]["messages"][0]["content"]
    assert "TIMEOUT" in system and "1.00" in system


def test_exchange_records_provenance_and_validity() -> None:
    _, exchange = plan_fix(
        code=CODE, evidence=_evidence(), hint=HINT, model=FakeModel(analysis())
    )
    assert exchange.valid
    assert exchange.raw_response == analysis()
    p = exchange.provenance
    assert (p.provider, p.model, p.prompt_name, p.prompt_version) == (
        "fake",
        "m-1",
        "healer",
        "3",
    )
    assert (p.input_tokens, p.output_tokens, p.latency_ms) == (9, 3, 5)
    assert len(p.prompt_hash) == 16


def test_fresh_page_load_is_labelled_as_such() -> None:
    _, exchange = plan_fix(
        code=CODE,
        evidence=_evidence(source="page_load"),
        hint=HINT,
        model=FakeModel(analysis()),
    )
    assert "Page snapshot (fresh page load)" in [s.name for s in exchange.sections]


def test_long_snapshot_is_truncated_and_recorded() -> None:
    huge = "- text: " + "x" * 50_000
    model = FakeModel(analysis())
    _, exchange = plan_fix(
        code=CODE, evidence=_evidence(page_snapshot=huge), hint=HINT, model=model
    )
    section = next(s for s in exchange.sections if s.name == "Page snapshot at failure")
    assert section.chars == LIMITS["Page snapshot at failure"]
    assert section.original_chars == len(huge)
    assert len(model.calls[0]["messages"][1]["content"]) < 40_000


def test_invalid_reply_is_recorded_not_raised() -> None:
    result, exchange = plan_fix(
        code=CODE, evidence=_evidence(), hint=HINT, model=FakeModel("not json")
    )
    assert result is None
    assert not exchange.valid
    assert exchange.validation_error
    assert exchange.raw_response == "not json"


@pytest.mark.parametrize(
    ("hint_conf", "expected"), [(0.9, FailureType.TIMEOUT), (0.5, FailureType.UNKNOWN)]
)
def test_confident_heuristic_replaces_an_unknown_diagnosis(
    hint_conf: float, expected: FailureType
) -> None:
    hint = (FailureType.TIMEOUT, hint_conf, "reason")
    result, _ = plan_fix(
        code=CODE, evidence=_evidence(), hint=hint, model=FakeModel(analysis("UNKNOWN"))
    )
    assert result is not None and result.failure_type == expected
```

Create `tests/unit/test_prompts.py`:

```python
"""Prompt files, versions and rendered sections."""

from workbench.llm.prompts import (
    get_prompt_hash,
    get_prompt_version,
    load_prompt,
    render_prompt,
)


def test_healer_prompt_is_version_3_and_formats() -> None:
    assert get_prompt_version("healer") == "3"
    text = load_prompt("healer").format(
        failure_type="TIMEOUT", confidence="1.00", reason="r"
    )
    assert "POTENTIAL_APP_DEFECT" in text
    assert '"failure_type"' in text  # JSON braces survived str.format


def test_prompt_hash_is_stable() -> None:
    assert get_prompt_hash("healer") == get_prompt_hash("healer")


def test_render_prompt_cuts_and_records() -> None:
    text, sections = render_prompt([("A", "abc"), ("B", "x" * 10)], {"A": 100, "B": 4})
    assert text == "## A\nabc\n\n## B\nxxxx"
    assert [(s.name, s.chars, s.original_chars) for s in sections] == [
        ("A", 3, None),
        ("B", 4, 10),
    ]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run python -m pytest tests/unit/test_evidence.py tests/unit/test_planner.py tests/unit/test_prompts.py -q -o addopts=`
Expected: failures and import errors (`parse_error_context`, `plan_fix`, `render_prompt` do not exist; healer prompt is version 2).

- [ ] **Step 3: Add `render_prompt()` and the v3 healer prompt**

Append to `src/workbench/llm/prompts.py` (import `PromptSection` from `workbench.models.shared`):

```python
def render_prompt(
    sections: list[tuple[str, str]], limits: dict[str, int]
) -> tuple[str, list[PromptSection]]:
    """Join ``(name, content)`` pairs as ``## name`` blocks, each cut to its limit.

    Returns the prompt text and a record of every section's size, with the
    original size when it was cut.
    """
    parts: list[str] = []
    records: list[PromptSection] = []
    for name, content in sections:
        limit = limits[name]
        kept = content[:limit]
        records.append(
            PromptSection(
                name=name,
                chars=len(kept),
                original_chars=len(content) if len(content) > limit else None,
            )
        )
        parts.append(f"## {name}\n{kept}")
    return "\n\n".join(parts), records
```

Also remove `'vision'` from the `agent_name` examples in that module's docstrings and replace "Used by benchmark runners" with "Recorded in every model exchange".

Replace `src/workbench/prompts/healer.md` with:

````markdown
You are a senior QA automation engineer who repairs failing Playwright tests (TypeScript).

The user message has these sections, in this order; some may be missing:

- **Test file**: the whole spec, exactly as it is on disk.
- **Error**: the failure message and where it happened.
- **Page snapshot at failure**: the page's accessibility snapshot at the moment the test failed. If the section is called **Page snapshot (fresh page load)** instead, it shows the start page, not the failing state.
- **Locator candidates**: role-based locators that exist on that page.
- **Console errors** and **Failed requests**: what the page reported.

A rule-based classifier suggests:

- Type: {failure_type}
- Confidence: {confidence}
- Reason: {reason}

Treat that as a hint; correct it when the evidence disagrees.

## Decide first: test problem or app problem

If the evidence shows the application itself is broken (a server error, wrong data, a missing feature, an uncaught page error) rather than the test being out of date, set `failure_type` to `POTENTIAL_APP_DEFECT`, explain why in `hypothesis` and `root_cause_evidence`, and leave `action_taken.original_code` and `action_taken.fixed_code` empty. Never weaken an assertion to hide an app problem.

## Otherwise, propose one fix

- Prefer locators from **Locator candidates**: `getByRole`, `getByLabel`, `getByPlaceholder`, `getByText`, then `data-testid`.
- `original_code` must be one contiguous block copied exactly from **Test file**, including whitespace.
- If several separate lines need changing, include the unchanged lines between them so the block stays contiguous.
- Keep the file's indentation style. Fix the first failure first.

## Repair strategy

- `selector_replace`: a locator selector changed. `original_code` is the old locator call, `fixed_code` the new one; every occurrence in the file is updated.
- `import_add`: an import is missing. `original_code` is empty, `fixed_code` the import statement.
- `timeout_adjust`: a timeout value must change. Give the old and new object or value.
- `role_argument`: a `getByRole` name is wrong. Give the old and new call.
- `assertion_swap`: an assertion method must change (for example `toBe` to `toHaveText`).
- `string_replace`: anything else; exact or indentation-tolerant text replacement.

## Output

Return only a JSON object matching this shape:

```json
{{
  "failure_type": "LOCATOR_DRIFT | LOCATOR_NOT_FOUND | TIMEOUT | ASSERTION_FAILED | JAVASCRIPT_ERROR | ENVIRONMENT_ISSUE | POTENTIAL_APP_DEFECT",
  "failure_summary": "short description of the failure",
  "hypothesis": "why the fix will work, or why the app is at fault",
  "confidence_score": 0.9,
  "confidence_rationale": "one sentence on why this confidence",
  "reasoning_steps": ["step 1", "step 2"],
  "root_cause_evidence": ["the log line or snapshot line that proves it"],
  "action_taken": {{
    "original_code": "exact contiguous block from Test file",
    "fixed_code": "replacement block",
    "description": "what changed",
    "repair_strategy": "selector_replace"
  }}
}}
```
````

In `src/workbench/prompts/manifest.json`, set `"healer"`'s `"version"` to `"3"`.

- [ ] **Step 4: Write `src/workbench/heal/evidence.py`**

Replace the whole file:

```python
"""Evidence for a diagnosis, taken from the failing run itself.

When a test fails, Playwright writes ``error-context.md``: the error, the test
source and a snapshot of the page at the moment of failure. That snapshot is
the main evidence. Only when it is missing is the spec's first URL loaded in
a fresh browser, which shows the start page rather than the failing state.
"""

import logging
import re
from collections.abc import Callable
from pathlib import Path

from workbench.context import collect_context
from workbench.context.locators import extract_locator_candidates
from workbench.models.artifacts import ContextSnapshot
from workbench.models.heal import FailureEvidence
from workbench.models.shared import RunResult, RunWarning

logger = logging.getLogger(__name__)

Collect = Callable[[str], ContextSnapshot]

_GOTO = re.compile(r"page\.goto\(\s*['\"`](https?://[^\s'\"`]+)['\"`]")
_PAGE_SNAPSHOT = re.compile(
    r"^# Page snapshot\s*\n+```[a-z]*\n(?P<body>.*?)\n```", re.MULTILINE | re.DOTALL
)


def extract_url_from_code(code: str | None) -> str | None:
    """The first URL passed to ``page.goto()``, with or without options."""
    match = _GOTO.search(code or "")
    return match.group(1) if match else None


def parse_error_context(text: str) -> str | None:
    """The page snapshot from Playwright's ``error-context.md``, if present."""
    match = _PAGE_SNAPSHOT.search(text)
    return match["body"].strip() or None if match else None


def gather_evidence(
    code: str, result: RunResult, *, collect: Collect = collect_context
) -> tuple[FailureEvidence, list[RunWarning]]:
    """Build the evidence for one failed run, preferring the failure snapshot."""
    evidence = FailureEvidence(
        error_message=result.error_message,
        error_location=result.error_location,
        screenshot_path=result.screenshot_path,
    )
    if result.error_context_path:
        try:
            snapshot = parse_error_context(
                Path(result.error_context_path).read_text(encoding="utf-8")
            )
        except OSError as exc:
            logger.warning("Could not read %s: %s", result.error_context_path, exc)
            snapshot = None
        if snapshot:
            evidence.page_snapshot = snapshot
            evidence.locator_candidates = extract_locator_candidates(snapshot)
            evidence.source = "error_context"
            return evidence, []

    url = extract_url_from_code(code)
    if url:
        page = collect(url)
        if not page.is_empty:
            evidence.page_snapshot = page.aria_snapshot
            evidence.locator_candidates = list(page.locator_candidates)
            evidence.console_errors = list(page.console_errors)
            evidence.network_errors = list(page.network_errors)
            evidence.source = "page_load"
            return evidence, []
    return evidence, ["page_context_unavailable"]
```

- [ ] **Step 5: Write `src/workbench/heal/planner.py`**

Replace the whole file:

```python
"""Asks the model for a diagnosis and a fix, and records the exchange."""

import logging

from workbench.llm.chat import ChatModel
from workbench.llm.parsing import parse_llm_response
from workbench.llm.prompts import (
    get_prompt_hash,
    get_prompt_version,
    load_prompt,
    render_prompt,
)
from workbench.models.heal import FailureEvidence, HealingAnalysis
from workbench.models.shared import FailureType, ModelExchange, Provenance

logger = logging.getLogger(__name__)

Hint = tuple[FailureType, float, str]

LIMITS = {
    "Test file": 12_000,
    "Error": 2_000,
    "Page snapshot at failure": 12_000,
    "Page snapshot (fresh page load)": 12_000,
    "Locator candidates": 2_000,
    "Console errors": 2_000,
    "Failed requests": 2_000,
}
# A heuristic this sure replaces an UNKNOWN diagnosis from the model.
HEURISTIC_OVERRIDE = 0.8


def build_sections(code: str, evidence: FailureEvidence) -> list[tuple[str, str]]:
    """Named context blocks in prompt order; empty ones are left out."""
    error = evidence.error_message
    if evidence.error_location:
        error += f"\nat {evidence.error_location}"
    snapshot_name = (
        "Page snapshot at failure"
        if evidence.source == "error_context"
        else "Page snapshot (fresh page load)"
    )
    sections = [
        ("Test file", code),
        ("Error", error),
        (snapshot_name, evidence.page_snapshot or ""),
        (
            "Locator candidates",
            "\n".join(f"- {c}" for c in evidence.locator_candidates),
        ),
        ("Console errors", "\n".join(evidence.console_errors)),
        ("Failed requests", "\n".join(evidence.network_errors)),
    ]
    return [(name, content) for name, content in sections if content.strip()]


def plan_fix(
    *, code: str, evidence: FailureEvidence, hint: Hint, model: ChatModel
) -> tuple[HealingAnalysis | None, ModelExchange]:
    """Return the model's validated analysis (None if invalid) and the exchange.

    Raises ``ModelError`` when the model cannot be reached.
    """
    hint_type, hint_confidence, hint_reason = hint
    system = load_prompt("healer").format(
        failure_type=hint_type.value,
        confidence=f"{hint_confidence:.2f}",
        reason=hint_reason,
    )
    user, sections = render_prompt(build_sections(code, evidence), LIMITS)
    reply = model.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        json_schema=HealingAnalysis.model_json_schema(),
        temperature=0.1,
    )
    exchange = ModelExchange(
        sections=sections,
        raw_response=reply.content,
        provenance=Provenance(
            provider=reply.provider,
            model=reply.model,
            prompt_name="healer",
            prompt_version=get_prompt_version("healer"),
            prompt_hash=get_prompt_hash("healer"),
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            latency_ms=reply.latency_ms,
        ),
    )
    try:
        analysis = parse_llm_response(reply.content, HealingAnalysis)
    except ValueError as exc:
        logger.warning("Healer reply did not match the schema: %s", exc)
        exchange.validation_error = str(exc)[:500]
        return None, exchange
    if (
        analysis.failure_type == FailureType.UNKNOWN
        and hint_confidence > HEURISTIC_OVERRIDE
    ):
        analysis = analysis.model_copy(update={"failure_type": hint_type})
    exchange.valid = True
    return analysis, exchange
```

- [ ] **Step 6: Run the evidence, planner and prompt tests**

Run: `uv run python -m pytest tests/unit/test_evidence.py tests/unit/test_planner.py tests/unit/test_prompts.py -q -o addopts=`
Expected: all pass. (The 1.0 heal loop in `heal/__init__.py` no longer imports cleanly; Step 9 replaces it.)

- [ ] **Step 7: Write the failing pipeline tests**

Add to `tests/unit/test_environment.py`:

```python
from pathlib import Path
from unittest.mock import MagicMock


def test_chromium_installed_checks_the_executable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    exe = tmp_path / "chrome"
    playwright = MagicMock()
    playwright.__enter__.return_value.chromium.executable_path = str(exe)
    monkeypatch.setattr(environment, "sync_playwright", lambda: playwright)
    assert not environment.chromium_installed()
    exe.write_text("", encoding="utf-8")
    assert environment.chromium_installed()


def test_chromium_check_survives_a_broken_install(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> None:
        raise RuntimeError("driver missing")

    monkeypatch.setattr(environment, "sync_playwright", broken)
    assert not environment.chromium_installed()
```

Create `tests/unit/test_heal_pipeline.py`:

```python
"""heal(): every outcome, with a fake runner, fake model and fake browser."""

import json
import threading
from pathlib import Path
from typing import Any

import pytest

from workbench.heal import HealRequest, heal, repair
from workbench.llm.chat import ChatReply, ModelError
from workbench.models.artifacts import ContextSnapshot
from workbench.models.events import RunEvent
from workbench.models.shared import RunResult
from workbench.reports import load_report

BROKEN = (
    'import { test } from "@playwright/test";\n\n'
    'test("submit", async ({ page }) => {\n'
    '  await page.goto("http://127.0.0.1:4173/");\n'
    '  await page.locator("#submit-btn").click();\n'
    "});\n"
)
SNAPSHOT_FILE = '# Page snapshot\n\n```yaml\n- button "Submit" [ref=e3]\n```\n'


def reply(
    failure_type: str = "LOCATOR_DRIFT",
    confidence: float = 0.9,
    original: str = 'page.locator("#submit-btn")',
    fixed: str = 'page.getByRole("button", { name: "Submit" })',
    strategy: str = "string_replace",
) -> str:
    return json.dumps(
        {
            "failure_type": failure_type,
            "failure_summary": "s",
            "hypothesis": "h",
            "confidence_score": confidence,
            "reasoning_steps": ["r"],
            "action_taken": {
                "original_code": original,
                "fixed_code": fixed,
                "description": "d",
                "repair_strategy": strategy,
            },
        }
    )


class FakeModel:
    def __init__(self, *outcomes: Any) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def chat(self, messages, *, json_schema=None, temperature=0.1) -> ChatReply:
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return ChatReply(content=outcome, model="m", provider="fake")


class FakeRunner:
    def __init__(self, tmp_path: Path, *statuses: str, on_call: Any = None) -> None:
        self.statuses = list(statuses)
        self.calls: list[dict[str, Any]] = []
        self.context = tmp_path / "error-context.md"
        self.context.write_text(SNAPSHOT_FILE, encoding="utf-8")
        self.on_call = on_call

    def __call__(
        self,
        spec: Path,
        run_dir: Path | None = None,
        *,
        record_video: bool = False,
        cancel: Any = None,
    ) -> RunResult:
        self.calls.append(
            {
                "spec": spec,
                "run_dir": run_dir,
                "record_video": record_video,
                "code": spec.read_text(),
            }
        )
        if self.on_call:
            self.on_call(len(self.calls))
        status = self.statuses.pop(0)
        if status == "passed":
            return RunResult(
                status="passed", video_path="/v.webm" if record_video else None
            )
        if status in ("cancelled", "error"):
            return RunResult(status=status, error_message=f"{status}!")
        return RunResult(
            status="failed",
            error_message="TimeoutError: waiting for locator('#submit-btn')",
            error_context_path=str(self.context),
        )


def no_page(url: str) -> ContextSnapshot:
    raise AssertionError("evidence should come from error-context.md")


@pytest.fixture
def spec(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("WORKBENCH_WORKSPACE", str(tmp_path / "ws"))
    path = tmp_path / "contact.spec.ts"
    path.write_text(BROKEN, encoding="utf-8")
    return path


def run_heal(spec: Path, model: FakeModel, runner: FakeRunner, **kwargs: Any):
    kwargs.setdefault("browsers_ready", lambda: True)
    return heal(
        HealRequest(spec_path=spec, max_attempts=kwargs.pop("max_attempts", 3)),
        model=model,
        run=runner,
        collect=no_page,
        **kwargs,
    )


def test_passing_spec_needs_no_healing(spec: Path, tmp_path: Path) -> None:
    model = FakeModel()
    report = run_heal(spec, model, FakeRunner(tmp_path, "passed"))
    assert report.status == "nothing_to_heal"
    assert model.calls == 0
    assert spec.read_text() == BROKEN
    assert load_report(report.id).status == "nothing_to_heal"


def test_heals_on_the_first_attempt(spec: Path, tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path, "failed", "passed")
    report = run_heal(spec, FakeModel(reply()), runner)

    assert report.status == "healed"
    assert [a.outcome for a in report.attempts] == ["healed"]
    assert 'getByRole("button", { name: "Submit" })' in spec.read_text()
    assert report.final_code == spec.read_text()
    assert '-  await page.locator("#submit-btn").click();' in report.diff
    assert runner.calls[1]["record_video"] is True
    assert report.attempts[0].rerun.video_path == "/v.webm"  # type: ignore[union-attr]
    assert report.attempts[0].evidence.source == "error_context"  # type: ignore[union-attr]
    assert report.attempts[0].repair_method == "text"
    assert report.classifier_hint == "TIMEOUT"


def test_fix_that_cannot_be_applied_is_retried(spec: Path, tmp_path: Path) -> None:
    model = FakeModel(reply(original="page.locator('#nope')"), reply())
    report = run_heal(spec, model, FakeRunner(tmp_path, "failed", "passed"))
    assert [a.outcome for a in report.attempts] == ["not_applied", "healed"]


def test_invalid_reply_is_retried(spec: Path, tmp_path: Path) -> None:
    report = run_heal(
        spec, FakeModel("not json", reply()), FakeRunner(tmp_path, "failed", "passed")
    )
    assert [a.outcome for a in report.attempts] == ["invalid_reply", "healed"]
    assert report.attempts[0].exchange.valid is False  # type: ignore[union-attr]


def test_confident_app_defect_stops_without_editing(spec: Path, tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path, "failed")
    report = run_heal(
        spec, FakeModel(reply("POTENTIAL_APP_DEFECT", 0.9, "", "")), runner
    )
    assert report.status == "app_defect_suspected"
    assert [a.outcome for a in report.attempts] == ["app_defect"]
    assert len(runner.calls) == 1
    assert spec.read_text() == BROKEN


def test_unsure_app_defect_still_tries_the_fix(spec: Path, tmp_path: Path) -> None:
    report = run_heal(
        spec,
        FakeModel(reply("POTENTIAL_APP_DEFECT", 0.5)),
        FakeRunner(tmp_path, "failed", "passed"),
    )
    assert report.status == "healed"


def test_exhausted_attempts_restore_the_spec(spec: Path, tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path, "failed", "failed", "failed")
    report = run_heal(
        spec,
        FakeModel(
            reply(),
            reply(
                original='page.getByRole("button", { name: "Submit" })',
                fixed="page.getByText('Submit')",
            ),
        ),
        runner,
        max_attempts=2,
    )
    assert report.status == "not_healed"
    assert [a.outcome for a in report.attempts] == ["rerun_failed", "rerun_failed"]
    assert spec.read_text() == BROKEN
    assert report.final_code == BROKEN and report.diff == ""


def test_model_error_after_a_failed_attempt_restores_the_spec(
    spec: Path, tmp_path: Path
) -> None:
    runner = FakeRunner(tmp_path, "failed", "failed")
    report = run_heal(
        spec, FakeModel(reply(), ModelError("connection refused")), runner
    )
    assert report.status == "error"
    assert "connection refused" in report.error_message
    assert spec.read_text() == BROKEN


def test_cancel_during_verification_restores_the_spec(
    spec: Path, tmp_path: Path
) -> None:
    report = run_heal(
        spec, FakeModel(reply()), FakeRunner(tmp_path, "failed", "cancelled")
    )
    assert report.status == "cancelled"
    assert [a.outcome for a in report.attempts] == ["cancelled"]
    assert spec.read_text() == BROKEN


def test_cancel_before_an_attempt(spec: Path, tmp_path: Path) -> None:
    cancel = threading.Event()
    runner = FakeRunner(tmp_path, "failed", on_call=lambda n: cancel.set())
    report = run_heal(spec, FakeModel(), runner, cancel=cancel)
    assert report.status == "cancelled"
    assert spec.read_text() == BROKEN


def test_missing_browsers_stop_before_running(spec: Path, tmp_path: Path) -> None:
    runner = FakeRunner(tmp_path)
    report = run_heal(spec, FakeModel(), runner, browsers_ready=lambda: False)
    assert report.status == "error"
    assert report.warnings == ["playwright_browsers_missing"]
    assert runner.calls == []


def test_runner_error_is_reported(spec: Path, tmp_path: Path) -> None:
    report = run_heal(spec, FakeModel(), FakeRunner(tmp_path, "error"))
    assert report.status == "error"
    assert report.error_message == "error!"


def test_missing_node_is_a_warning(
    spec: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repair, "node_available", lambda: False)
    report = run_heal(
        spec,
        FakeModel(reply(strategy="selector_replace")),
        FakeRunner(tmp_path, "failed", "passed"),
    )
    assert report.status == "healed"
    assert report.warnings == ["ast_unavailable"]


def test_events_describe_the_run(spec: Path, tmp_path: Path) -> None:
    events: list[RunEvent] = []
    run_heal(
        spec,
        FakeModel(reply()),
        FakeRunner(tmp_path, "failed", "passed"),
        emit=events.append,
    )
    steps = [(e.step, e.state) for e in events if e.kind == "step"]
    assert steps == [
        ("run", "active"),
        ("run", "done"),
        ("evidence", "active"),
        ("evidence", "done"),
        ("diagnose", "active"),
        ("diagnose", "done"),
        ("repair", "active"),
        ("repair", "done"),
        ("verify", "active"),
        ("verify", "done"),
    ]
    assert events[-1].kind == "done" and events[-1].detail == "healed"
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
```

- [ ] **Step 8: Run them to verify they fail**

Run: `uv run python -m pytest tests/unit/test_heal_pipeline.py tests/unit/test_environment.py -q -o addopts=`
Expected: import errors (`heal`, `HealRequest`, `chromium_installed` do not exist).

- [ ] **Step 9: Write the pipeline, then delete the 1.0 heal loop**

Append to `src/workbench/environment.py` (add `import logging`, `from pathlib import Path`, `from playwright.sync_api import sync_playwright`, and `logger = logging.getLogger(__name__)`):

```python
def chromium_installed() -> bool:
    """True when Playwright's Chromium build is on disk."""
    try:
        with sync_playwright() as playwright:
            return Path(playwright.chromium.executable_path).exists()
    except Exception as exc:
        logger.debug("Could not locate Chromium: %s", exc)
        return False
```

Create `src/workbench/heal/pipeline.py`:

```python
"""The heal loop: run, gather evidence, diagnose, repair, verify.

``heal()`` never leaves a half-repaired spec behind: unless the result is
``healed``, the spec is restored to exactly what it was.
"""

import difflib
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from workbench.config import runs_dir
from workbench.context import collect_context
from workbench.environment import chromium_installed
from workbench.events import Emit, EventSink
from workbench.heal.classifier import classify_failure_heuristic
from workbench.heal.evidence import Collect, gather_evidence
from workbench.heal.planner import Hint, plan_fix
from workbench.heal.repair import apply_fix
from workbench.ids import new_run_id
from workbench.llm.chat import ChatModel, ModelError
from workbench.models.heal import (
    REPAIR_STRATEGY_LABELS,
    Attempt,
    AttemptOutcome,
    HealReport,
    HealStatus,
)
from workbench.models.shared import FailureType, RunResult, RunWarning
from workbench.reports import save_report
from workbench.runner import run_test

APP_DEFECT_CONFIDENCE = 0.7

Run = Callable[..., RunResult]

_EVIDENCE_LABEL = {
    "error_context": "Snapshot from the moment of failure",
    "page_load": "Snapshot from a fresh page load",
    "none": "No page snapshot available",
}


class HealRequest(BaseModel):
    """A spec to heal; the file is edited in place."""

    spec_path: Path
    max_attempts: int = Field(default=3, ge=1, le=5)


def heal(
    request: HealRequest,
    *,
    model: ChatModel,
    emit: Emit | None = None,
    cancel: threading.Event | None = None,
    run: Run = run_test,
    collect: Collect = collect_context,
    browsers_ready: Callable[[], bool] = chromium_installed,
) -> HealReport:
    """Heal ``request.spec_path`` and return the saved report."""
    return _HealRun(
        request, model, emit, cancel, run, collect, browsers_ready
    ).execute()


class _HealRun:
    def __init__(
        self,
        request: HealRequest,
        model: ChatModel,
        emit: Emit | None,
        cancel: threading.Event | None,
        run: Run,
        collect: Collect,
        browsers_ready: Callable[[], bool],
    ) -> None:
        self.spec = request.spec_path
        self.max_attempts = request.max_attempts
        self.model, self.run, self.collect = model, run, collect
        self.browsers_ready = browsers_ready
        self.cancel = cancel or threading.Event()
        self.original = self.spec.read_text(encoding="utf-8")
        self.code = self.original
        self.report = HealReport(
            id=new_run_id("heal", self.spec.stem),
            spec_name=self.spec.name,
            status="error",
            max_attempts=self.max_attempts,
            original_code=self.original,
            final_code=self.original,
        )
        self.run_root = runs_dir() / self.report.id
        self.events = EventSink(self.report.id, emit)
        self.warnings: set[RunWarning] = set()
        self.started = time.monotonic()

    def execute(self) -> HealReport:
        if not self.browsers_ready():
            self.warnings.add("playwright_browsers_missing")
            return self.finish(
                "error",
                "Playwright's Chromium is not installed. Run: npx playwright install chromium",
            )
        self.events.step("run", "active", f"npx playwright test {self.spec.name}")
        result = self.run(self.spec, self.run_root / "initial", cancel=self.cancel)
        self.report.initial_run = result
        if result.status == "cancelled":
            return self.finish("cancelled")
        if result.status == "error":
            self.events.step("run", "failed", result.error_message)
            return self.finish("error", result.error_message)
        if result.passed:
            self.events.step("run", "done", "Passed on the first run")
            return self.finish("nothing_to_heal")
        self.events.step("run", "done", _first_line(result.error_message))

        hint = classify_failure_heuristic(result.output)
        self.report.classifier_hint = hint[0].value
        for number in range(1, self.max_attempts + 1):
            status, result = self.attempt(number, result, hint)
            if status is not None:
                return self.finish(status)
        return self.finish("not_healed")

    def attempt(
        self, number: int, result: RunResult, hint: Hint
    ) -> tuple[HealStatus | None, RunResult]:
        """One diagnose → repair → verify cycle; a status ends the heal."""
        started = time.monotonic()

        def record(outcome: AttemptOutcome, **fields: Any) -> None:
            elapsed = int((time.monotonic() - started) * 1000)
            self.report.attempts.append(
                Attempt(number=number, outcome=outcome, duration_ms=elapsed, **fields)
            )
            self.events.attempt(number, outcome)

        if self.cancel.is_set():
            record("cancelled")
            return "cancelled", result

        self.events.step("evidence", "active")
        evidence, warnings = gather_evidence(self.code, result, collect=self.collect)
        self.warnings.update(warnings)
        self.events.step("evidence", "done", _EVIDENCE_LABEL[evidence.source])

        self.events.step("diagnose", "active", f"Classifier hint: {hint[0].value}")
        try:
            analysis, exchange = plan_fix(
                code=self.code, evidence=evidence, hint=hint, model=self.model
            )
        except ModelError as exc:
            self.events.step("diagnose", "failed", str(exc))
            self.report.error_message = f"The model could not be reached: {exc}"
            return "error", result
        if analysis is None:
            self.events.step("diagnose", "failed", "The reply did not match the schema")
            record("invalid_reply", evidence=evidence, exchange=exchange)
            return None, result
        self.events.step(
            "diagnose",
            "done",
            f"{analysis.failure_type.value} · confidence {analysis.confidence_score:.2f}",
        )
        if (
            analysis.failure_type == FailureType.POTENTIAL_APP_DEFECT
            and analysis.confidence_score >= APP_DEFECT_CONFIDENCE
        ):
            record(
                "app_defect", evidence=evidence, analysis=analysis, exchange=exchange
            )
            return "app_defect_suspected", result

        self.events.step("repair", "active")
        repaired = apply_fix(self.code, analysis.action_taken)
        if repaired.ast_unavailable:
            self.warnings.add("ast_unavailable")
        if repaired.method is None:
            self.events.step(
                "repair", "failed", "The code to replace is not in the file"
            )
            record(
                "not_applied", evidence=evidence, analysis=analysis, exchange=exchange
            )
            return None, result
        label = REPAIR_STRATEGY_LABELS[analysis.action_taken.repair_strategy]
        self.events.step("repair", "done", f"{label} ({repaired.method})")
        self.code = repaired.code
        self.spec.write_text(self.code, encoding="utf-8")

        self.events.step("verify", "active")
        rerun = self.run(
            self.spec,
            self.run_root / f"attempt-{number}",
            record_video=True,
            cancel=self.cancel,
        )
        fields: dict[str, Any] = {
            "evidence": evidence,
            "analysis": analysis,
            "exchange": exchange,
            "repair_method": repaired.method,
            "rerun": rerun,
        }
        if rerun.status == "cancelled":
            record("cancelled", **fields)
            return "cancelled", rerun
        if rerun.passed:
            self.events.step("verify", "done", "Re-run passed")
            record("healed", **fields)
            return "healed", rerun
        self.events.step("verify", "failed", _first_line(rerun.error_message))
        record("rerun_failed", **fields)
        return None, rerun

    def finish(self, status: HealStatus, error_message: str = "") -> HealReport:
        if status != "healed":
            self.spec.write_text(self.original, encoding="utf-8")
            self.code = self.original
        report = self.report
        report.status = status
        if error_message:
            report.error_message = error_message
        report.final_code = self.code
        report.diff = _unified_diff(self.original, self.code, self.spec.name)
        report.warnings = sorted(self.warnings)
        report.duration_ms = int((time.monotonic() - self.started) * 1000)
        save_report(report)
        self.events.done(status)
        return report


def _first_line(text: str) -> str:
    lines = text.strip().splitlines()
    return lines[0][:200] if lines else ""


def _unified_diff(before: str, after: str, name: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{name}",
            tofile=f"b/{name}",
        )
    )
```

Replace `src/workbench/heal/__init__.py` with:

```python
"""Healing: diagnose a failing Playwright spec, repair it and prove the fix."""

from workbench.heal.pipeline import APP_DEFECT_CONFIDENCE, HealRequest, heal

__all__ = ["APP_DEFECT_CONFIDENCE", "HealRequest", "heal"]
```

Delete the 1.0 heal loop, its artifacts and their tests:

```bash
git rm -q src/workbench/heal/verifier.py src/workbench/heal/artifact_store.py \
  tests/unit/test_healing.py tests/unit/test_explainability.py \
  tests/unit/test_provenance.py tests/unit/test_path_validation.py
```

Then remove what only they used:

- `src/workbench/models/heal.py`: delete the classes `Evidence`, `HealingDecision`, `TimelineStep` and `ExecutionTimeline`, and any import left unused (ruff will list them).
- `src/workbench/models/__init__.py`: replace with

```python
"""Pydantic data contracts: model output, run results and reports."""

from .artifacts import ContextSnapshot
from .events import RunEvent
from .generate import (
    ContextSummary,
    GenerateReport,
    GenerationDecision,
    GenerationResult,
)
from .heal import (
    Attempt,
    FailureEvidence,
    HealingAction,
    HealingAnalysis,
    HealReport,
    RepairResult,
    RepairStrategy,
)
from .shared import FailureType, ModelExchange, PromptSection, Provenance, RunResult

__all__ = [
    "Attempt",
    "ContextSnapshot",
    "ContextSummary",
    "FailureEvidence",
    "FailureType",
    "GenerateReport",
    "GenerationDecision",
    "GenerationResult",
    "HealReport",
    "HealingAction",
    "HealingAnalysis",
    "ModelExchange",
    "PromptSection",
    "Provenance",
    "RepairResult",
    "RepairStrategy",
    "RunEvent",
    "RunResult",
]
```

- `src/workbench/models/shared.py`: delete the `returncode` property from `RunResult`.
- `src/workbench/config.py`: delete the `ARTIFACTS_DIR` constant and its comment.
- `src/workbench/validation.py`: delete `validate_file_path` (uploads get their own checks in Phase 4).
- `tests/unit/test_schemas.py`: delete the classes `TestHealingDecision` and `TestExecutionTimeline` and the imports they used.

- [ ] **Step 10: Move the heal integration test to the new pipeline**

In `tests/integration/fake_llm.py`, in `_answer`, replace `if "BROKEN CODE:" in user:` with `if "## Test file" in user:`, and update the module docstring's mention of `BROKEN CODE:` to `## Test file`.

In `tests/integration/test_pipeline.py`, replace the imports `from workbench.heal import attempt_healing, run_test` with:

```python
from workbench.config import specs_dir
from workbench.heal import HealRequest, heal
from workbench.llm import get_default_router
from workbench.llm.chat import RouterChatModel
from workbench.reports import load_report
from workbench.runner import run_test
```

delete the `ARTIFACTS_DIR` and `HEALED_SPEC` constants, and replace `test_heal_loop_repairs_a_drifted_selector` with:

```python
def test_heal_loop_repairs_a_drifted_selector(site, fake_llm):
    spec = specs_dir() / "healed-contact.spec.ts"
    spec.write_text(BROKEN_SPEC, encoding="utf-8")

    report = heal(
        HealRequest(spec_path=spec, max_attempts=2),
        model=RouterChatModel(get_default_router()),
    )

    assert report.status == "healed", report.model_dump_json(indent=2)
    prompts = fake_llm.prompts_containing("## Test file")
    assert prompts, "healer never called the LLM"
    assert "## Page snapshot at failure" in prompts[-1]
    healed = spec.read_text(encoding="utf-8")
    assert 'locator("#submit-btn")' not in healed
    assert '[data-testid="submit"]' in healed
    assert report.attempts[-1].repair_method == "ast"
    assert load_report(report.id).status == "healed"
```

Also remove `HEALED_SPEC` from the `clean_generated` fixture's loop.

- [ ] **Step 11: Run every suite**

Run:

```bash
uv run python -m pytest -q -o addopts=
uv run python -m pytest tests/integration -q -o addopts=
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Expected: all pass. `grep -rn "attempt_healing\|HealingDecision\|artifact_store\|verify_repair\|returncode" src tests` prints nothing.

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "feat!: rebuild the heal loop around failure-time evidence and reports" -m "Evidence comes from Playwright's error-context.md; each attempt records the model exchange; a confident app-defect diagnosis stops without editing; every non-healed outcome restores the spec." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: The generate pipeline

**Files:**

- Rewrite: `src/workbench/generate/pipeline.py`, `src/workbench/generate/__init__.py`, `src/workbench/prompts/generator.md`
- Create: `tests/unit/test_generate_pipeline.py`
- Modify: `src/workbench/prompts/manifest.json`, `src/workbench/models/generate.py`, `src/workbench/models/shared.py`, `src/workbench/models/__init__.py`, `tests/unit/test_prompts.py`, `tests/integration/fake_llm.py`, `tests/integration/test_pipeline.py`

**Interfaces:**

- Consumes: everything Task 7 consumes, plus `specs_dir()`, `slugify()`, `validate_and_sanitize_url()`, `validate_description()`, `extract_code_block()`, `GenerationResult`.
- Produces:
  - `workbench.generate.pipeline`: `LIMITS`, `GenerateRequest(url: str, scenario: str, run_after: bool = True)`, `generate(request, *, model, emit=None, cancel=None, run=run_test, collect=collect_context, browsers_ready=chromium_installed) -> GenerateReport`
  - `workbench.generate` re-exports `generate`, `GenerateRequest`

- [ ] **Step 1: Write the failing tests**

Add to `tests/unit/test_prompts.py`:

```python
def test_generator_prompt_is_version_3() -> None:
    assert get_prompt_version("generator") == "3"
    assert "Page snapshot" in load_prompt("generator")
```

Create `tests/unit/test_generate_pipeline.py`:

```python
"""generate(): every outcome, with a fake browser, model and runner."""

import threading
from pathlib import Path
from typing import Any

import pytest

from workbench.generate import GenerateRequest, generate
from workbench.llm.chat import ChatReply, ModelError
from workbench.models.artifacts import ContextSnapshot
from workbench.models.events import RunEvent
from workbench.models.shared import RunResult
from workbench.reports import load_report

URL = "http://127.0.0.1:4173/"
SPEC = (
    '```typescript\nimport { test, expect } from "@playwright/test";\n\n'
    'test("submit", async ({ page }) => {\n  await page.goto("http://127.0.0.1:4173/");\n});\n```'
)


class FakeModel:
    def __init__(self, outcome: Any = SPEC) -> None:
        self.outcome = outcome
        self.messages: list[Any] = []

    def chat(self, messages, *, json_schema=None, temperature=0.1) -> ChatReply:
        self.messages = messages
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return ChatReply(content=self.outcome, model="m", provider="fake")


def page(url: str) -> ContextSnapshot:
    return ContextSnapshot(
        url=url,
        aria_snapshot='- textbox "Name" [ref=e2]\n- button "Submit" [ref=e3]',
        locator_candidates=["getByRole('button', { name: 'Submit' })"],
    )


def runner(status: str = "passed"):
    calls: list[Path] = []

    def run(spec: Path, run_dir: Path | None = None, **_: Any) -> RunResult:
        calls.append(spec)
        return RunResult(
            status=status, error_message="" if status == "passed" else "boom"
        )

    return run, calls


@pytest.fixture(autouse=True)
def _workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WORKBENCH_WORKSPACE", str(tmp_path))


def go(
    model: FakeModel, run: Any, request: GenerateRequest | None = None, **kwargs: Any
):
    kwargs.setdefault("browsers_ready", lambda: True)
    kwargs.setdefault("collect", page)
    request = request or GenerateRequest(
        url=URL, scenario="A visitor submits the contact form"
    )
    return generate(request, model=model, run=run, **kwargs)


def test_generates_writes_and_runs(tmp_path: Path) -> None:
    run, calls = runner("passed")
    model = FakeModel()
    report = go(model, run)

    assert report.status == "passed"
    spec = tmp_path / "specs" / "a-visitor-submits-the-contact-form.spec.ts"
    assert report.spec_name == spec.name
    assert calls == [spec]
    assert spec.read_text().startswith(
        'import { test, expect } from "@playwright/test";'
    )
    assert "```" not in report.code
    assert [s.name for s in report.exchange.sections] == [
        "Target URL",
        "Scenario",
        "Page snapshot",
        "Locator candidates",
    ]  # type: ignore[union-attr]
    assert report.exchange.provenance.prompt_version == "3"  # type: ignore[union-attr]
    assert report.context.locator_candidates == [
        "getByRole('button', { name: 'Submit' })"
    ]  # type: ignore[union-attr]
    assert "## Page snapshot\n- textbox" in model.messages[1]["content"]
    assert load_report(report.id).status == "passed"


def test_failed_run_is_reported() -> None:
    run, _ = runner("failed")
    assert go(FakeModel(), run).status == "failed"


def test_not_run_when_asked() -> None:
    run, calls = runner()
    report = go(
        FakeModel(), run, GenerateRequest(url=URL, scenario="login", run_after=False)
    )
    assert report.status == "not_run"
    assert calls == []


def test_same_scenario_twice_gets_a_new_file(tmp_path: Path) -> None:
    run, _ = runner()
    first, second = go(FakeModel(), run), go(FakeModel(), run)
    assert first.spec_name != second.spec_name
    assert second.spec_name == "a-visitor-submits-the-contact-form-2.spec.ts"


def test_invalid_url_is_rejected_before_any_work() -> None:
    run, calls = runner()

    def no_page(url: str) -> ContextSnapshot:
        raise AssertionError("should not load")

    report = go(
        FakeModel(),
        run,
        GenerateRequest(url="example.com", scenario="x"),
        collect=no_page,
    )
    assert report.status == "error"
    assert "Invalid URL" in report.error_message
    assert calls == []


def test_unreachable_page_is_reported() -> None:
    run, _ = runner()
    report = go(FakeModel(), run, collect=lambda url: ContextSnapshot(url=url))
    assert report.status == "error"
    assert "Could not load" in report.error_message


def test_reply_without_code_writes_nothing(tmp_path: Path) -> None:
    run, calls = runner()
    report = go(FakeModel("   "), run)
    assert report.status == "error"
    assert report.exchange is not None and not report.exchange.valid
    assert not any((tmp_path / "specs").glob("*.spec.ts"))
    assert calls == []


def test_model_error_is_reported() -> None:
    run, _ = runner()
    report = go(FakeModel(ModelError("refused")), run)
    assert report.status == "error"
    assert "refused" in report.error_message


def test_missing_browsers_stop_early() -> None:
    run, calls = runner()
    report = go(FakeModel(), run, browsers_ready=lambda: False)
    assert report.status == "error"
    assert report.warnings == ["playwright_browsers_missing"]
    assert calls == []


def test_cancel_after_generation_skips_the_run() -> None:
    run, calls = runner()
    cancel = threading.Event()

    class CancellingModel(FakeModel):
        def chat(self, messages, **kwargs: Any) -> ChatReply:
            cancel.set()
            return super().chat(messages, **kwargs)

    report = go(CancellingModel(), run, cancel=cancel)
    assert report.status == "cancelled"
    assert calls == []


def test_events_describe_the_run() -> None:
    events: list[RunEvent] = []
    run, _ = runner()
    go(FakeModel(), run, emit=events.append)
    steps = [(e.step, e.state) for e in events if e.kind == "step"]
    assert steps == [
        ("context", "active"),
        ("context", "done"),
        ("model", "active"),
        ("model", "done"),
        ("execute", "active"),
        ("execute", "done"),
    ]
    assert events[-1].detail == "passed"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run python -m pytest tests/unit/test_generate_pipeline.py tests/unit/test_prompts.py -q -o addopts=`
Expected: import errors (`GenerateRequest`, `generate`), and the generator prompt is version 2.

- [ ] **Step 3: Write the v3 generator prompt**

Replace `src/workbench/prompts/generator.md` with:

````markdown
You are a senior QA automation engineer who writes Playwright tests in TypeScript.

The user message has these sections; some may be missing:

- **Target URL**: the page the test starts on.
- **Scenario**: the user flow to test, in plain language.
- **Page snapshot**: the page's accessibility snapshot (roles, names, states).
- **Locator candidates**: role-based locators that exist on the page.
- **Console errors**: what the page reported while loading.

Write one complete, runnable test for the scenario.

## Structure

- Start with `import { test, expect } from "@playwright/test";`
- One `test()` block, named after the scenario. No `describe()`.
- Begin with `await page.goto(...)` using the exact Target URL.

## Locators, in order of preference

1. A locator from **Locator candidates** or `page.getByRole(role, { name })` built from the **Page snapshot**.
2. `page.getByLabel(...)` for labelled form fields.
3. `page.getByPlaceholder(...)`, then `page.getByText(...)`.
4. `page.locator('[data-testid="..."]')` or a stable `#id`.

Never use XPath, CSS classes that look generated, or positional selectors.

## Assertions

- Assert the outcome of the flow, not just that the page loaded.
- Use web-first assertions: `toBeVisible()`, `toHaveText()`, `toContainText()`, `toHaveValue()`, `toHaveURL()`.
- No `waitForTimeout()`, `waitForSelector()` or fixed delays.

## Output

Only the TypeScript code, in one ```typescript block. No explanation.
````

In `src/workbench/prompts/manifest.json`, set `"generator"`'s `"version"` to `"3"`.

- [ ] **Step 4: Write `src/workbench/generate/pipeline.py`**

Replace the whole file:

```python
"""Generation: page context in, a runnable Playwright spec out."""

import threading
import time
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from workbench.config import runs_dir, specs_dir
from workbench.context import collect_context
from workbench.environment import chromium_installed
from workbench.events import Emit, EventSink
from workbench.heal.evidence import Collect
from workbench.ids import new_run_id, slugify
from workbench.llm.chat import ChatModel, ModelError
from workbench.llm.parsing import extract_code_block
from workbench.llm.prompts import (
    get_prompt_hash,
    get_prompt_version,
    load_prompt,
    render_prompt,
)
from workbench.models.generate import (
    ContextSummary,
    GenerateReport,
    GenerateStatus,
    GenerationResult,
)
from workbench.models.shared import ModelExchange, Provenance, RunResult
from workbench.reports import save_report
from workbench.runner import run_test
from workbench.validation import (
    ValidationError,
    validate_and_sanitize_url,
    validate_description,
)

Run = Callable[..., RunResult]

LIMITS = {
    "Target URL": 500,
    "Scenario": 1_000,
    "Page snapshot": 12_000,
    "Locator candidates": 2_000,
    "Console errors": 2_000,
}


class GenerateRequest(BaseModel):
    """What to generate a test for."""

    url: str
    scenario: str
    run_after: bool = True


def generate(
    request: GenerateRequest,
    *,
    model: ChatModel,
    emit: Emit | None = None,
    cancel: threading.Event | None = None,
    run: Run = run_test,
    collect: Collect = collect_context,
    browsers_ready: Callable[[], bool] = chromium_installed,
) -> GenerateReport:
    """Generate a spec for ``request``, optionally run it, and return the saved report."""
    report = GenerateReport(
        id=new_run_id("generate", request.scenario),
        url=request.url,
        scenario=request.scenario,
        status="error",
    )
    events = EventSink(report.id, emit)
    cancel = cancel or threading.Event()
    started = time.monotonic()

    def finish(status: GenerateStatus, error_message: str = "") -> GenerateReport:
        report.status = status
        if error_message:
            report.error_message = error_message
        report.duration_ms = int((time.monotonic() - started) * 1000)
        save_report(report)
        events.done(status)
        return report

    try:
        url = validate_and_sanitize_url(request.url)
        scenario = validate_description(request.scenario)
    except ValidationError as exc:
        return finish("error", str(exc))
    if not browsers_ready():
        report.warnings = ["playwright_browsers_missing"]
        return finish(
            "error",
            "Playwright's Chromium is not installed. Run: npx playwright install chromium",
        )

    events.step("context", "active", url)
    page = collect(url)
    if page.is_empty:
        events.step("context", "failed", f"Could not load {url}")
        return finish("error", f"Could not load {url}.")
    report.context = ContextSummary(
        url=url,
        snapshot_lines=len((page.aria_snapshot or "").splitlines()),
        locator_candidates=list(page.locator_candidates),
        console_errors=len(page.console_errors),
        failed_requests=len(page.network_errors),
    )
    events.step("context", "done", f"{len(page.locator_candidates)} locator candidates")

    events.step("model", "active")
    sections = [
        ("Target URL", url),
        ("Scenario", scenario),
        ("Page snapshot", page.aria_snapshot or ""),
        ("Locator candidates", "\n".join(f"- {c}" for c in page.locator_candidates)),
        ("Console errors", "\n".join(page.console_errors)),
    ]
    user, records = render_prompt([(n, c) for n, c in sections if c.strip()], LIMITS)
    try:
        reply = model.chat(
            [
                {"role": "system", "content": load_prompt("generator")},
                {"role": "user", "content": user},
            ],
            temperature=0.1,
        )
    except ModelError as exc:
        events.step("model", "failed", str(exc))
        return finish("error", f"The model could not be reached: {exc}")
    exchange = ModelExchange(
        sections=records,
        raw_response=reply.content,
        provenance=Provenance(
            provider=reply.provider,
            model=reply.model,
            prompt_name="generator",
            prompt_version=get_prompt_version("generator"),
            prompt_hash=get_prompt_hash("generator"),
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            latency_ms=reply.latency_ms,
        ),
    )
    report.exchange = exchange
    try:
        code = GenerationResult(code=extract_code_block(reply.content)).code
    except ValueError as exc:
        exchange.validation_error = str(exc)[:500]
        events.step("model", "failed", "The reply contained no code")
        return finish("error", "The model returned no code.")
    exchange.valid = True

    spec = _free_path(specs_dir(), slugify(scenario))
    spec.write_text(code + "\n", encoding="utf-8")
    report.spec_name, report.code = spec.name, code
    events.step("model", "done", f"{len(code.splitlines())} lines → {spec.name}")

    if not request.run_after:
        return finish("not_run")
    if cancel.is_set():
        return finish("cancelled")
    events.step("execute", "active", f"npx playwright test {spec.name}")
    result = run(spec, runs_dir() / report.id, cancel=cancel)
    report.run = result
    if result.status == "cancelled":
        return finish("cancelled")
    if result.status == "error":
        events.step("execute", "failed", result.error_message)
        return finish("error", result.error_message)
    events.step("execute", "done" if result.passed else "failed", result.status)
    return finish("passed" if result.passed else "failed")


def _free_path(folder: Path, slug: str) -> Path:
    path = folder / f"{slug}.spec.ts"
    number = 2
    while path.exists():
        path = folder / f"{slug}-{number}.spec.ts"
        number += 1
    return path
```

Replace `src/workbench/generate/__init__.py` with:

```python
"""Generation: page context in, a runnable Playwright spec out."""

from workbench.generate.pipeline import GenerateRequest, generate

__all__ = ["GenerateRequest", "generate"]
```

- [ ] **Step 5: Delete the 1.0 generation types**

- `src/workbench/models/generate.py`: delete the class `GenerationDecision` and the imports only it used (`ContextSnapshot`, `ProvenanceRecord`); keep `GenerationResult`. Update the module docstring to list `GenerationResult`, `ContextSummary` and `GenerateReport`.
- `src/workbench/models/shared.py`: delete the classes `ProvenanceRecord` and `LLMConfig`.
- `src/workbench/models/__init__.py`: remove `GenerationDecision` from the import and from `__all__`.

- [ ] **Step 6: Move the generate integration test to the new pipeline**

In `tests/integration/fake_llm.py`, replace `match = re.search(r"TARGET URL:\s*(\S+)", user)` with `match = re.search(r"## Target URL\n(\S+)", user)` and update the docstring's `TARGET URL` mention.

In `tests/integration/test_pipeline.py`, replace the import `from workbench.generate.pipeline import generate_test_script` with `from workbench.generate import GenerateRequest, generate`; delete `GENERATED_DIR`, `GENERATED_SPEC`, the `clean_generated` fixture and any now-unused imports; and replace `test_generated_spec_passes_in_a_real_browser` with:

```python
def test_generated_spec_passes_in_a_real_browser(site, fake_llm):
    report = generate(
        GenerateRequest(url=site, scenario="A user can submit the contact form"),
        model=RouterChatModel(get_default_router()),
    )

    prompts = fake_llm.prompts_containing("## Target URL")
    assert prompts, "generator never called the LLM"
    assert "## Page snapshot" in prompts[-1]
    assert 'button "Submit"' in prompts[-1]
    assert report.status == "passed", report.model_dump_json(indent=2)
    assert site in report.code
    assert (
        report.exchange is not None
        and report.exchange.provenance.provider == "lm_studio"
    )
```

- [ ] **Step 7: Run every suite**

Run:

```bash
uv run python -m pytest -q -o addopts=
uv run python -m pytest tests/integration -q -o addopts=
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Expected: all pass. `grep -rn "GenerationDecision\|ProvenanceRecord\|LLMConfig\|generate_test_script\|tests/generated" src tests` prints nothing.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat!: rebuild generation with page snapshots, events and reports" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Prove the guarantees in a real browser

**Files:**

- Create: `tests/integration/test_heal_guarantees.py`
- Modify: `.github/workflows/ci.yml`, `package.json`, `tsconfig.json`
- Delete: `playwright.config.ts`, `playwright.e2e.config.ts`

**Interfaces:**

- Consumes: `heal()`, `HealRequest`, `specs_dir()`, the `site` fixture.
- Produces: integration evidence for spec success criteria S3 (evidence from the failure) and S4 (app-defect guard), plus a recorded re-run video.

- [ ] **Step 1: Write the integration tests**

Create `tests/integration/test_heal_guarantees.py`:

```python
"""S3 and S4 against a real Chromium, with a scripted in-process model."""

import json
from pathlib import Path
from typing import Any

from tests.integration.conftest import SITE_URL
from workbench.config import specs_dir
from workbench.heal import HealRequest, heal
from workbench.llm.chat import ChatReply

DRIFTED = f"""import {{ test, expect }} from "@playwright/test";

test("Submit the contact form", async ({{ page }}) => {{
  await page.goto("{SITE_URL}");
  await page.getByLabel("Name").fill("Ada");
  await page.locator("#submit-btn").click({{ timeout: 3000 }});
  await expect(page.getByRole("status")).toHaveText("Submitted");
}});
"""
WRONG_EXPECTATION = DRIFTED.replace(
    'page.locator("#submit-btn")', 'page.getByRole("button", { name: "Submit" })'
).replace('toHaveText("Submitted")', 'toHaveText("Order placed", { timeout: 2000 })')


def _analysis(failure_type: str, original: str = "", fixed: str = "") -> str:
    return json.dumps(
        {
            "failure_type": failure_type,
            "failure_summary": "s",
            "hypothesis": "h",
            "confidence_score": 0.9,
            "reasoning_steps": ["r"],
            "action_taken": {
                "original_code": original,
                "fixed_code": fixed,
                "description": "d",
                "repair_strategy": "selector_replace",
            },
        }
    )


class ScriptedModel:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def chat(self, messages: list[dict[str, str]], **_: Any) -> ChatReply:
        self.prompts.append(messages[1]["content"])
        return ChatReply(content=self.reply, model="scripted", provider="test")


def _spec(name: str, code: str) -> Path:
    path = specs_dir() / name
    path.write_text(code, encoding="utf-8")
    return path


def test_evidence_is_the_page_at_the_moment_of_failure(site: str) -> None:
    model = ScriptedModel(
        _analysis(
            "LOCATOR_DRIFT",
            'page.locator("#submit-btn")',
            'page.getByRole("button", { name: "Submit" })',
        )
    )
    report = heal(HealRequest(spec_path=_spec("drift.spec.ts", DRIFTED)), model=model)

    assert report.status == "healed", report.model_dump_json(indent=2)
    evidence = report.attempts[0].evidence
    assert evidence is not None and evidence.source == "error_context"
    snapshot_section = model.prompts[0].split("## Page snapshot at failure\n", 1)[1]
    # The name typed before the failure is in the snapshot: this is mid-test state,
    # not a fresh load of the start page.
    assert 'textbox "Name"' in snapshot_section and "Ada" in snapshot_section
    video = report.attempts[0].rerun.video_path  # type: ignore[union-attr]
    assert video and video.endswith(".webm") and Path(video).is_file()


def test_suspected_app_bug_leaves_the_test_alone(site: str) -> None:
    spec = _spec("order.spec.ts", WRONG_EXPECTATION)
    report = heal(
        HealRequest(spec_path=spec),
        model=ScriptedModel(_analysis("POTENTIAL_APP_DEFECT")),
    )

    assert report.status == "app_defect_suspected"
    assert [a.outcome for a in report.attempts] == ["app_defect"]
    assert report.attempts[0].rerun is None
    assert spec.read_text(encoding="utf-8") == WRONG_EXPECTATION
```

- [ ] **Step 2: Run them**

Run: `uv run python -m pytest tests/integration -v -o addopts=`
Expected: every integration test passes, including the two new ones.

- [ ] **Step 3: Simplify the Playwright configs and CI**

The runner's `playwright.workspace.config.ts` now runs every spec and records the evidence, so the separate report re-run is redundant.

```bash
git rm -q playwright.config.ts playwright.e2e.config.ts
```

- `tsconfig.json`: remove `"playwright.config.ts"` and `"playwright.e2e.config.ts"` from `include`.
- `package.json` `scripts`: delete `"test:generated"` and `"test:e2e:report"`, and set `"test:e2e": "uv run python -m pytest tests/integration --junitxml=reports/integration-pytest.xml"`.
- `.github/workflows/ci.yml`, integration job:
  - add `env: WORKBENCH_WORKSPACE: ${{ github.workspace }}/workspace` to the step that runs `pytest tests/integration` and change its `--junitxml` to `reports/integration-pytest.xml`;
  - delete the step `Re-run generated and healed specs for the report`;
  - in `Upload E2E artifacts`, rename the step to `Upload integration artifacts`, the artifact `name` to `integration-report`, and replace the `path` list with `reports/` and `workspace/`.

Run: `npm run type-check && npm run lint`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "test: prove failure-time evidence, the app-defect guard and re-run video" -m "CI now keeps the workspace (reports, videos, error context) as its artifact." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Tidy up and update the guides

**Files:**

- Modify: `pyproject.toml`, `.gitignore`, `.env.example`, `package.json`, `AGENTS.md`, `ROADMAP.md`, `CHANGELOG.md`, `tests/integration/test_pipeline.py`, any file the sweep below finds
- Delete: `logs/.gitkeep`

**Interfaces:**

- Consumes: the finished Phase 2 layout.
- Produces: guides that match the code; no stale references to the 1.0 layout.

- [ ] **Step 1: Sweep stale references**

Run:

```bash
grep -rnE "scripts/ast_repair|src/healing|logs/traces|traces\.jsonl|unit_test_|tests/generated|tests/artifacts|vision|benchmark|Gradio" src tests AGENTS.md CONTRIBUTING.md README.md
```

Fix every hit in `src/` and `tests/` so it describes the current code (for example, a docstring mentioning `logs/traces.jsonl` drops that clause; one naming `src/healing/` names `src/workbench/heal/`). Hits in the router and model registry about vision stay: Phase 3 deletes those modules. Fix doc hits in Step 4.

In `tests/integration/test_pipeline.py`, replace `PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent` with `from workbench.config import PROJECT_ROOT` (or delete it if nothing uses it).

- [ ] **Step 2: Drop the stale lint exemption**

In `pyproject.toml`, delete the line `"E402",   # some modules set up sys.path before importing` from `[tool.ruff.lint] ignore`, then run `uv run ruff check .` and move any import ruff now flags into its module's import block. In test files, the cause is a leftover `sys.path.insert(...)` before the imports: delete that line (the package is installed, so it is not needed).

- [ ] **Step 3: Remove leftovers from 1.0**

- `git rm -q logs/.gitkeep`
- `.gitignore`: delete the entries for `tests/screenshots/*.png`, `tests/artifacts/`, `tests/generated/*.spec.ts` (and its comment), `benchmarks/reports/*.json`, the `# Gradio` block, and the `# Logs` block (`*.log`, `logs/`, `!logs/.gitkeep`).
- `.env.example`: delete the `LOG_LEVEL` line and its comment.
- `package.json`: set `"version": "2.0.0-dev.0"` and `"description": "Generates Playwright tests and heals failing ones with local LLMs"`.

- [ ] **Step 4: Update `AGENTS.md`, the roadmap and the changelog**

In `AGENTS.md`, replace the `## Layout` block with:

````markdown
## Layout

```text
src/workbench/          the Python package
├── config.py           every path; workspace_dir() / runs_dir() / reports_dir() / specs_dir()
├── ids.py              run ids and slugs
├── runner.py           runs one spec; result from Playwright's JSON report
├── playwright_report.py  JSON report → RunResult
├── environment.py      Node.js and Chromium checks
├── events.py           EventSink: numbered progress events
├── reports.py          save / load / list run reports
├── heal/               pipeline.py (heal), evidence, planner, repair (+ ast_repair.js), classifier
├── generate/           pipeline.py (generate)
├── context/            page context: aria snapshot, console, page errors, requests
├── llm/                chat.py (ChatModel), router (until Phase 3), parsing, prompts
├── models/             Pydantic contracts: reports, events, model output
└── prompts/            prompt files and manifest.json
samples/site/           sample web app used by tests
tests/unit/             default pytest run: no model, no browser, no network
tests/integration/      real Chromium + scripted or fake OpenAI-compatible model
workspace/              runtime output (git-ignored): specs/, runs/, reports/
playwright.workspace.config.ts  the config the runner uses for every spec
```
````

and replace the bullets under `## Rules` that mention mocking the router and `prompts/manifest.json` with:

```markdown
- Pipelines take their collaborators as arguments (`model`, `run`, `collect`, `browsers_ready`). Unit tests pass fakes; do not patch module globals.
- Talk to models only through `workbench.llm.chat.ChatModel`.
- `heal()` must leave the spec unchanged unless the status is `healed`.
- Prompt changes go in `src/workbench/prompts/` and bump the version in `src/workbench/prompts/manifest.json`.
```

Also change the opening sentence "A local web app that generates…" to "A tool that generates…, rebuilt as a local web app in v2." In `README.md`, nothing changes in this phase.

In `ROADMAP.md`, move the eight Phase 2 rows from `Now` to `Done` (Phase `2`, Plan `[Phase 2](docs/superpowers/plans/2026-10-03-v2-phase-2-engine.md)`), and move the two Phase 3 rows from `Next` to `Now` with `Phase 3 plan (to be written)`. Fix the Phase 1 `Removed` row "Most of `docs/` (31 files)" to "(30 files)".

In `CHANGELOG.md`, add under `## [Unreleased]`:

```markdown
### Added

- The engine records every model exchange (sections sent, raw reply, validity,
  provenance) and writes one JSON report per run to `workspace/reports/`.
- Healing evidence comes from Playwright's `error-context.md`: the page as it
  was at the moment of failure.
- Verification re-runs are recorded as video with each action captioned.
- A confident `POTENTIAL_APP_DEFECT` diagnosis stops the heal without editing
  the test.
- Runs can be cancelled; Playwright and its browsers are stopped.
```

and under `### Changed`:

```markdown
- The runner reads Playwright's JSON report; page context uses
  `aria_snapshot(mode="ai")` and Playwright's own console, page-error and
  request collections.
- Healer and generator prompts are version 3; the model is asked for
  schema-constrained output where the provider supports it.
```

and under `### Removed`:

```markdown
- The 1.0 heal loop, decision artifacts, CDP accessibility code, custom
  console and network listeners, and the Playwright report re-run configs.
```

- [ ] **Step 5: Lint and commit**

Run: `npm run lint && npm run type-check && uv run python -m pytest -q -o addopts=`
Expected: all pass.

```bash
git add -A
git commit -m "chore: remove 1.0 leftovers and update the guides for the new engine" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Verify the phase and hand over

**Files:** none changed unless a check fails.

- [ ] **Step 1: Run every gate from a clean environment**

```bash
rm -rf .venv node_modules workspace
uv sync --group dev && npm ci && npx playwright install chromium
uv run python -m pytest -q -o addopts= --cov
uv run python -m pytest tests/integration -v -o addopts=
npm run lint && npm run type-check
```

Expected: everything passes; coverage is reported (the gate arrives in Phase 5).

- [ ] **Step 2: Confirm the phase's definition of done**

Run: `uv run python -m pytest tests/unit/test_heal_pipeline.py -v -o addopts= | grep -c PASSED`
Expected: at least 14 (every heal outcome: healed, nothing to heal, not applied, invalid reply, app defect, unsure app defect, not healed, model error, cancelled twice, browsers missing, runner error, AST unavailable, events).

Run: `ls workspace 2>/dev/null; git status --short`
Expected: no `workspace/` at the repo root after the unit and integration runs (both redirect it), and a clean tree.

- [ ] **Step 3: Ask before pushing**

Show the user `git log --oneline` for the Phase 2 commits and ask whether to push `v2`. Do not push without a yes.
