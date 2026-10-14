# v2 Phase 5: Quality Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task, inline in one session. Do not dispatch subagents without the user's approval (see Plan decisions, P9). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch on every quality gate in the v2 spec (§8) and prove the app against them: strict types, a coverage threshold, a UI suite that covers every screen state with accessibility checks, and a four-job CI.

**Architecture:**

- **Gates in config:** mypy runs with `strict = true`, coverage fails under 85% (lines and branches), and `npm run lint` checks formatting and skips runtime output.
- **UI suite:** Playwright Test (TypeScript) in `tests/ui/`. A worker fixture starts the real app on a free port with a temporary workspace through a small launcher, `tests/ui/serve.py`. Live flows use the Demo model. Result states that Demo cannot produce are shown from saved reports.
- **Accessibility:** every page state is scanned with axe; serious and critical violations fail the test.
- **CI:** four jobs (`lint`, `unit`, `integration`, `ui`) with actions pinned to commits.

**Tech Stack:**

- Python 3.13, pytest, pytest-cov, mypy (strict), ruff
- `@playwright/test` 1.63.0 (already installed), `@axe-core/playwright` 4.13.0 (new dev dependency)
- GitHub Actions, Codecov, Dependabot

**Spec:** [docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md](../specs/2026-10-03-v2-showcase-simplification-design.md). The relevant sections are:

- §2 Success criteria S1, S5 and S6
- §5.2 Screens and states (the complete list)
- §6.7 UI implementation (accessibility)
- §8 Quality gates and testing approach
- §11 Phase 5

## Global Constraints

- **Types (§8):** mypy `strict = true` for `src/workbench`; no errors. Any relaxation is per module, with a comment.
- **Coverage (§8):** unit tests reach at least 85% line and branch coverage on `src/workbench`.
- **UI tests (§8):** Playwright Test in TypeScript against the running app with Demo. Every state in §5.2 is covered. The HTML report is uploaded in CI.
- **Accessibility (§8):** no serious or critical axe violations on Heal, Generate and the model popover.
- **CI (§8):** exactly four jobs: `lint`, `unit`, `integration`, `ui`. Codecov keeps receiving coverage.
- **Dependabot (§8):** uv, npm and Actions; monthly; grouped.
- **Environment variables:** `WORKBENCH_WORKSPACE` and `WORKBENCH_PORT` stay the only two. The UI launcher takes flags, not new variables.
- **Colours:** only from `static/css/tokens.css`, one variable per Figma variable.
- **JavaScript in the app:** none beyond the vendored htmx files. UI tests are TypeScript under `tests/ui/` and are not part of the app.
- **AGENTS.md rules apply:** pipelines take collaborators as arguments, no patching of module globals, `ROADMAP.md` and `CHANGELOG.md` change in the same commit as the work.
- **Never push `v2` without asking the user.** Commits stay local.
- **Commits:** Conventional Commits, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **A model server already running on the developer's machine (LM Studio or Ollama).** The UI suite must see "no model" on a fresh workspace anyway. Pinned in Task 2: `first-launch.spec.ts` asserts "No model server found" (the launcher turns detection off).
2. **A used `workspace/` folder** (reports, generated specs, Playwright's `error-context.md`). `npm run lint` must not lint it. Pinned in Task 1: `test_linters_skip_runtime_output`, and Step 8 runs the lint with those files present.
3. **The app already running on port 7860 while the suite runs.** The suite must not collide with it or write into `workspace/`. Pinned in Task 2: `first-launch.spec.ts` asserts the suite's port and workspace.
4. **A slow machine or CI runner.** A live heal can take far longer than a default 5-second assertion. Pinned in Task 2: `expectResult` waits up to 60 seconds; Task 8 Step 3 runs the suite twice in a row to catch timing flakes.
5. **A test that fails or is interrupted mid-run.** The app process and its Chromium must not be left running. Pinned in Task 2 Step 8: after the suite, `pgrep -f tests.ui.serve` finds nothing.

## Plan decisions

These were settled while planning. Each is a ruling the executor follows.

- **P1. The UI suite starts the app through `tests/ui/serve.py`, not `uv run workbench`.** The real launcher opens a browser tab and looks for a model server on the machine, which would make the suite behave differently on each computer. The test launcher calls the same `create_app` and `build_server`.
- **P2. States Demo cannot produce are shown from saved reports.** Healed after retries, not healed, the attempt outcomes, the warning banners and the model-failure pages are rendered from the reports in `tests/unit/report_fixtures.py`, saved into the suite's workspace. The pages are rendered by the real app from real report files.
- **P3. Two states need a flag on the test launcher.** "Model connected" uses the fake OpenAI-compatible server from the integration suite (`--model fake`). "Playwright browsers missing" uses `--no-browsers`, because the only real way to produce it is to uninstall Chromium.
- **P4. Four colour values change before the Figma file does.** An axe scan during planning found one rule failing, colour contrast, on four tokens (values in Task 3). The Figma file is still blocked by the MCP call limit, so the values change in `tokens.css` first and the roadmap's Figma row lists them.
- **P5. The result views become plain links, not ARIA tabs.** Each view is a page load, so `role="tab"` promised arrow-key behaviour that does not exist. A `nav` of links with `aria-current="page"` is correct and works from the keyboard as it is.
- **P6. CI actions move to current major versions, pinned to commits.** Every input the workflow uses is checked against the action's own `action.yml` at the pinned commit (Task 7 Step 3).
- **P7. Some of the phase is already in place.** The integration suite needs no new tests: S1 and S4 are in `tests/integration/test_samples.py`, S3 in `test_heal_guarantees.py`, generation in `test_samples.py` and `test_pipeline.py`. Only its CI job is renamed. The CodeQL workflow already covers Python, JS/TS and Actions weekly, and the Docker workflow was removed in Phase 1.
- **P8. Out of scope.** The deferred minors from Phases 2 to 4, except the three this phase touches anyway (lint scope, contrast, result-view semantics). README badges and the GIF (Phase 6). The 300-second model timeout (an open decision for the user).
- **P9. Inline execution, no subagents.** The user asked for this on 2026-10-11. The final whole-branch review needs the user's approval before a reviewer subagent is dispatched; without it, do a self-review and say so.

## Coverage of §5.2 (S5 checklist)

| Area | State | Test |
| --- | --- | --- |
| Global | Model connected | `model-connected.spec.ts` |
| Global | Demo | `first-launch.spec.ts` (choosing Demo), `heal.spec.ts` (idle) |
| Global | Not connected (pill and popover) | `first-launch.spec.ts`, `model-unreachable.spec.ts` |
| Heal | Idle | `heal.spec.ts` |
| Heal | Running (live steps and log) | `heal.spec.ts` (selector drift) |
| Heal | Healed | `heal.spec.ts` (selector drift), `results.spec.ts` |
| Heal | Healed after retries | `results.spec.ts` |
| Heal | Not healed | `results.spec.ts` |
| Heal | Stopped: likely app bug | `heal.spec.ts` (app bug), `results.spec.ts` |
| Heal | Nothing to heal | `heal.spec.ts` (upload), `results.spec.ts` |
| Heal | Cancelled | `heal.spec.ts` (cancel), `results.spec.ts` |
| Heal | Model unreachable | `results.spec.ts`, `model-unreachable.spec.ts` |
| Attempt outcomes | Healed, Re-run failed, Fix not applied, Invalid model reply | `results.spec.ts` |
| Result tabs | Diff, Re-run video, Execution log, Model I/O | `heal.spec.ts` (selector drift), `results.spec.ts` (keyboard) |
| Generate | Empty | `generate.spec.ts` |
| Generate | Generating | `generate.spec.ts` (example) |
| Generate | Passed | `generate.spec.ts` (example), `results.spec.ts` |
| Generate | Generated, not run | `generate.spec.ts`, `results.spec.ts` |
| Generate | Run failed → Heal | `generate.spec.ts`, `results.spec.ts` |
| Banners | Playwright browsers missing | `browsers-missing.spec.ts` |
| Banners | Page context unavailable, Repair used text replacement | `results.spec.ts` |
| Input errors | Invalid URL | `generate.spec.ts` |
| Input errors | Not a spec file, File too large | `heal.spec.ts` |

## File map

| File | Task | Purpose |
| --- | --- | --- |
| `pyproject.toml` | 1 | `strict = true`, `fail_under = 85` |
| `src/workbench/context/dom.py`, `src/workbench/llm/prompts.py` | 1 | The three strict-typing fixes |
| `tests/unit/test_quality_gates.py` | 1, 7 | Pins the gates in the config files |
| `eslint.config.cjs`, `.markdownlint-cli2.jsonc`, `.prettierignore`, `package.json` | 1, 2 | Lint scope and scripts |
| `playwright.ui.config.ts` | 2 | The UI suite's config |
| `tests/ui/__init__.py`, `tests/ui/serve.py` | 2 | The launcher the suite uses |
| `tests/ui/support/app.ts` | 2 | Worker fixture: starts and stops the app |
| `tests/ui/support/page.ts` | 2 | Shared locators and waits |
| `tests/ui/support/axe.ts` | 3 | The accessibility assertion |
| `tests/ui/first-launch.spec.ts` | 2, 3 | S1 and the "no model" states |
| `src/workbench/web/static/css/tokens.css`, `app.css`, `templates/partials/heal_result.html` | 3 | Contrast values; result views as links |
| `tests/ui/heal.spec.ts` | 4 | Heal page and live heals |
| `tests/ui/generate.spec.ts`, `tests/ui/results.spec.ts` | 5 | Generate page; every saved result state |
| `tests/ui/model-unreachable.spec.ts`, `model-connected.spec.ts`, `browsers-missing.spec.ts` | 6 | Model and browser states |
| `.github/workflows/ci.yml`, `.github/dependabot.yml` | 7 | Four jobs; monthly updates |
| `AGENTS.md`, `README.md`, `ROADMAP.md`, `CHANGELOG.md` | 1–8 | Updated with the work |

---

### Task 1: Gates in config: strict types, coverage threshold, lint scope

**Files:**

- Create: `tests/unit/test_quality_gates.py`
- Modify: `pyproject.toml`, `src/workbench/context/dom.py:20`, `src/workbench/llm/prompts.py:13-23`
- Modify: `eslint.config.cjs`, `.markdownlint-cli2.jsonc`, `.prettierignore`, `package.json`
- Modify: `ROADMAP.md`, `CHANGELOG.md`, `README.md`, `AGENTS.md`

**Interfaces:**

- Consumes: nothing.
- Produces: npm scripts `lint:format`, `test:integration` (renamed from `test:e2e`); `tests/unit/test_quality_gates.py` (Task 7 adds two tests to it).

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_quality_gates.py`:

```python
"""The quality gates in the v2 spec (section 8) are switched on in the config files."""

import tomllib

from workbench.config import PROJECT_ROOT

PYPROJECT = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_mypy_is_strict_for_the_package() -> None:
    mypy = PYPROJECT["tool"]["mypy"]
    assert mypy["strict"] is True
    assert mypy["files"] == ["src/workbench"]


def test_coverage_counts_branches_and_fails_under_85() -> None:
    coverage = PYPROJECT["tool"]["coverage"]
    assert coverage["run"]["branch"] is True
    assert coverage["run"]["source"] == ["src/workbench"]
    assert coverage["report"]["fail_under"] == 85


def test_linters_skip_runtime_output() -> None:
    eslint = (PROJECT_ROOT / "eslint.config.cjs").read_text(encoding="utf-8")
    markdownlint = (PROJECT_ROOT / ".markdownlint-cli2.jsonc").read_text(
        encoding="utf-8"
    )
    assert "'workspace/'" in eslint
    assert '"workspace"' in markdownlint
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run python -m pytest tests/unit/test_quality_gates.py`
Expected: 3 failed (`KeyError: 'strict'`, `KeyError: 'fail_under'`, `assert "'workspace/'" in eslint`).

- [ ] **Step 3: Turn on strict mypy and fix the three errors**

In `pyproject.toml`, replace the `[tool.mypy]` table (keep the `[[tool.mypy.overrides]]` block below it):

```toml
[tool.mypy]
python_version = "3.13"
files = ["src/workbench"]
plugins = ["pydantic.mypy"]
strict = true
```

In `src/workbench/context/dom.py`, add the import and the annotation:

```python
from bs4 import BeautifulSoup
from playwright.sync_api import Page
```

```python
def collect_dom(page: Page, max_chars: int = 30000) -> str:
```

In `src/workbench/llm/prompts.py`:

```python
import hashlib
import json
from typing import Any
```

```python
_manifest_cache: dict[str, Any] | None = None


def _load_manifest() -> dict[str, Any]:
```

Run: `uv run mypy`
Expected: `Success: no issues found in 62 source files`. If strict mode reports anything else, fix it at the source; a `# type: ignore` needs a comment saying why.

- [ ] **Step 4: Add the coverage threshold**

In `pyproject.toml`:

```toml
[tool.coverage.report]
show_missing = true
skip_empty = true
fail_under = 85
```

Prove the gate bites, then that the suite clears it:

Run: `uv run python -m pytest --cov --cov-fail-under=99`
Expected: tests pass, then `FAIL Required test coverage of 99% not reached` and a non-zero exit.

Run: `uv run python -m pytest --cov`
Expected: all pass, `Required test coverage of 85% reached. Total coverage: 96.…%`.

- [ ] **Step 5: Keep the linters out of runtime output**

`eslint.config.cjs`, in the `ignores` list, after `'reports/',`:

```js
      'workspace/',
```

`.markdownlint-cli2.jsonc`, in `ignores`, after `"playwright-report",`:

```jsonc
    "workspace",
```

Replace `.prettierignore` with (UI specs are now formatted; sample and fixture specs are data and stay as written):

```text
node_modules
dist
build
.venv
tests/artifacts
tests/fixtures
test-results
samples/specs
workspace
src/workbench/web/static/vendor/
```

- [ ] **Step 6: Make `npm run lint` check formatting, and rename the integration script**

In `package.json` `scripts`, replace `test:e2e`, `lint` and `lint:py`, and add `lint:format`:

```json
    "test:integration": "uv run python -m pytest tests/integration --junitxml=reports/integration-pytest.xml",
    "lint": "npm run lint:js && npm run lint:format && npm run lint:py && npm run lint:types && npm run lint:md",
    "lint:format": "prettier --check \"**/*.{js,cjs,ts}\"",
    "lint:py": "uv run ruff check . && uv run ruff format --check .",
```

Find other mentions of the old script name and update each hit to `test:integration`:

Run: `grep -rn "test:e2e" . --include="*.md" --include="*.yml" --include="*.json" --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=docs`
Expected after the edits: no output.

- [ ] **Step 7: Run the tests**

Run: `uv run python -m pytest tests/unit/test_quality_gates.py`
Expected: 3 passed.

- [ ] **Step 8: Run the lint with a used workspace present (Review Focus 2)**

Run: `find workspace -name "*.md" | head -1`
Expected: at least one path if the app has been used. If there is none, create a stand-in and remove it after this step: `mkdir -p workspace/runs/lint-check && printf '# x\n#y\n' > workspace/runs/lint-check/error-context.md`.

Run: `npm run lint`
Expected: every part passes; no file under `workspace/` is reported.

- [ ] **Step 9: Update the guides**

- `ROADMAP.md`, "Now": change the Phase 5 row's status to `🚧 In progress`.
- `CHANGELOG.md`, under `## [Unreleased]` → `### Changed`:
  - `Type checking is strict for the whole package, and the unit suite fails under 85% line and branch coverage.`
  - `` `npm run lint` now checks formatting and no longer checks files the app writes to `workspace/`. ``
- `AGENTS.md`, Commands block: change the lint comment to `# ESLint, Prettier, Ruff, mypy (strict), markdownlint`.
- `README.md`, Develop block: the same comment change.

- [ ] **Step 10: Verify and commit**

Run: `uv run python -m pytest --cov && npm run lint && npm run type-check`
Expected: all pass.

```bash
git add tests/unit/test_quality_gates.py pyproject.toml src/workbench/context/dom.py src/workbench/llm/prompts.py eslint.config.cjs .markdownlint-cli2.jsonc .prettierignore package.json ROADMAP.md CHANGELOG.md README.md AGENTS.md
git commit -m "chore: turn on strict types, the coverage threshold and the formatting check"
```

---

### Task 2: UI suite harness and the first-launch spec (S1)

**Files:**

- Create: `playwright.ui.config.ts`, `tests/ui/__init__.py` (empty), `tests/ui/serve.py`
- Create: `tests/ui/support/app.ts`, `tests/ui/support/page.ts`, `tests/ui/first-launch.spec.ts`
- Modify: `package.json`, `tsconfig.json`, `eslint.config.cjs`, `AGENTS.md`, `README.md`, `CHANGELOG.md`

**Interfaces:**

- Consumes: `workbench.__main__.build_server`, `workbench.app.create_app`, `workbench.web.services.Services`, `tests.unit.report_fixtures.write_all`, `tests.integration.fake_llm.FakeLLM`.
- Produces, for Tasks 3 to 6:
  - `tests/ui/support/app.ts`: `test`, `expect`, `type AppOptions = { model?: 'none' | 'demo' | 'unreachable' | 'fake'; browsers?: boolean; seed?: boolean }`, `type App = { url: string; workspace: string; reports: Record<string, string> }`. A spec file picks its app with `test.use({ appOptions: {...} })` at the top level. `baseURL` is the app's address.
  - `tests/ui/support/page.ts`: `RUN_TIMEOUT_MS`, `statusPill(page)`, `expectResult(page, status)`, `openModelMenu(page)`, `resultViews(page)`.
  - `app.reports` keys (with `seed: true`): `healed`, `healed_after_retries`, `not_healed`, `app_defect`, `nothing_to_heal`, `cancelled`, `model_error`, `demo_healed`, `with_warnings`, `generate_passed`, `generate_failed`, `generate_not_run`, `generate_error`.
  - npm script `test:ui`.

- [ ] **Step 1: Add the config and the failing spec**

Create `playwright.ui.config.ts`:

```ts
import { defineConfig, devices } from '@playwright/test';

/**
 * The UI suite: Playwright Test drives the real app in Chromium.
 *
 * Spec files start their own app on a free port with a temporary workspace
 * (tests/ui/support/app.ts), so the suite never touches workspace/ or port 7860.
 * Files that ask for the same app options share one app.
 */
export default defineConfig({
  testDir: 'tests/ui',
  outputDir: 'test-results/ui',
  // An app runs one heal or generation at a time.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: { trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
  ],
});
```

Create `tests/ui/first-launch.spec.ts`:

```ts
import { expect, test } from './support/app';
import { expectResult, openModelMenu } from './support/page';

// S1: a first-time visitor with no model installed heals the sample.
test.use({ appOptions: { model: 'none' } });

test('a fresh workspace has no model and says how to get one', async ({ page, app }) => {
  // The suite's app never uses the developer's port or workspace.
  expect(app.url).not.toContain(':7860');
  expect(app.workspace).not.toContain(process.cwd());

  await page.goto('/');

  await expect(page).toHaveURL(/\/heal$/);
  await expect(page.getByRole('heading', { name: 'No model server found' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Change the model/ })).toContainText(
    'Not connected'
  );
  await expect(page.getByRole('button', { name: 'Heal the Selector drift sample' })).toBeDisabled();
  await expect(page.getByText('Connect a model to run this.')).toBeVisible();
});

test('the model menu works from the keyboard and will not save a server that is down', async ({
  page,
}) => {
  await page.goto('/heal');
  const pill = page.getByRole('button', { name: /Change the model/ });
  const menu = page.locator('#model-menu');

  await pill.focus();
  await page.keyboard.press('Enter');
  await expect(menu.getByRole('heading', { name: 'Model' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(menu).toBeHidden();
  await expect(pill).toBeFocused();

  await openModelMenu(page);
  await menu.getByLabel('Server').fill('http://127.0.0.1:9/v1');
  await menu.getByRole('button', { name: 'Retry' }).click();

  await expect(menu.getByText('Unreachable', { exact: true })).toBeVisible();
  await expect(menu.getByLabel('Server')).toHaveAttribute('aria-invalid', 'true');
  await expect(menu.getByRole('button', { name: 'Save' })).toBeDisabled();
});

test('choosing Demo heals the selector-drift sample', async ({ page }) => {
  await page.goto('/heal');
  const menu = await openModelMenu(page);
  await menu.locator('label', { hasText: 'Demo' }).click();
  await expect(menu.getByText('Replays recorded model answers')).toBeVisible();
  await menu.getByRole('button', { name: 'Save' }).click();

  await expect(page.getByRole('button', { name: /Change the model/ })).toContainText(
    'scripted answers'
  );
  await page.getByRole('button', { name: 'Heal the Selector drift sample' }).click();

  await expectResult(page, 'Healed');
  await expect(page.getByRole('heading', { name: 'contact-form.spec.ts' })).toBeVisible();
  await expect(page.locator('#main .result-head').getByText('Demo', { exact: true })).toBeVisible();
});
```

In `package.json` `scripts`, after `test:integration`:

```json
    "test:ui": "playwright test --config playwright.ui.config.ts",
```

- [ ] **Step 2: Run it to see it fail**

Run: `npm run test:ui`
Expected: FAIL with `Cannot find module './support/app'`.

- [ ] **Step 3: Write the launcher**

Create the empty file `tests/ui/__init__.py`, and `tests/ui/serve.py`:

```python
"""Starts the app for the UI suite (tests/ui/*.spec.ts).

Unlike ``uv run workbench`` it opens no browser tab and never looks for a model
server on this machine, so the suite behaves the same on every computer. It can
also prepare the workspace before the app starts:

    WORKBENCH_WORKSPACE=/tmp/ui uv run python -m tests.ui.serve --port 7901 --seed
"""

import argparse
import json
from contextlib import ExitStack
from dataclasses import replace

from tests.integration.fake_llm import FakeLLM
from tests.unit.report_fixtures import write_all
from workbench import config
from workbench.__main__ import build_server
from workbench.app import create_app
from workbench.models.generate import GenerateReport
from workbench.models.settings import DEMO_MODEL, ModelSettings
from workbench.reports import load_report, save_report
from workbench.samples import BASE_URL_PLACEHOLDER
from workbench.settings import save_settings
from workbench.web.services import Services

# Nothing listens on the discard port, so this server is always down.
DOWN_URL = "http://127.0.0.1:9/v1"
SEEDED_FILE = "seeded.json"


def seed_reports(port: int) -> None:
    """Save one report per result state and list their ids in ``seeded.json``."""
    ids = write_all()
    # "Heal this test" needs the failed spec on disk, broken the way Demo can heal.
    failed = load_report(ids["generate_failed"])
    assert isinstance(failed, GenerateReport)
    source = (config.SAMPLE_SPECS_DIR / "contact-form.spec.ts").read_text(
        encoding="utf-8"
    )
    code = source.replace(BASE_URL_PLACEHOLDER, f"{config.base_url(port)}/sample-site/")
    (config.specs_dir() / failed.spec_name).write_text(code, encoding="utf-8")
    save_report(failed.model_copy(update={"code": code}))
    (config.workspace_dir() / SEEDED_FILE).write_text(json.dumps(ids), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the app for the UI suite.")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument(
        "--model", choices=["none", "demo", "unreachable", "fake"], default="demo"
    )
    parser.add_argument("--no-browsers", action="store_true")
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args()

    services = replace(Services(), detect=lambda: None)
    if args.no_browsers:
        services = replace(services, browsers_ready=lambda: False)
    with ExitStack() as stack:
        if args.model == "demo":
            save_settings(ModelSettings(provider="demo", model=DEMO_MODEL))
        elif args.model == "unreachable":
            save_settings(
                ModelSettings(
                    provider="ollama", base_url=DOWN_URL, model="missing-model"
                )
            )
        elif args.model == "fake":
            llm = stack.enter_context(FakeLLM())
            save_settings(
                ModelSettings(
                    provider="lm_studio", base_url=llm.base_url, model="fake-model"
                )
            )
        if args.seed:
            seed_reports(args.port)
        build_server(create_app(services, port=args.port), args.port).run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Write the fixture and the page helpers**

Create `tests/ui/support/app.ts`:

```ts
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { type AddressInfo, createServer } from 'node:net';
import { tmpdir } from 'node:os';
import path from 'node:path';

import { test as base } from '@playwright/test';

/** How the app under test is started; see tests/ui/serve.py. */
export type AppOptions = {
  /** The saved model: none (first launch), Demo, a server that is down, or a fake server that answers. */
  model?: 'none' | 'demo' | 'unreachable' | 'fake';
  /** false: the app believes Chromium is not installed. */
  browsers?: boolean;
  /** Save one report per result state before the app starts; their ids arrive in `app.reports`. */
  seed?: boolean;
};

export type App = {
  url: string;
  workspace: string;
  /** Result state → report id, when started with `seed`. */
  reports: Record<string, string>;
};

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const START_TIMEOUT_MS = 30_000;
const STOP_TIMEOUT_MS = 12_000;

function freePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address() as AddressInfo;
      server.close(() => resolve(port));
    });
  });
}

async function startApp(options: AppOptions): Promise<{ app: App; stop: () => Promise<void> }> {
  const port = await freePort();
  const url = `http://127.0.0.1:${port}`;
  const workspace = mkdtempSync(path.join(tmpdir(), 'workbench-ui-'));
  const args = ['run', 'python', '-m', 'tests.ui.serve', '--port', String(port)];
  args.push('--model', options.model ?? 'demo');
  if (options.browsers === false) args.push('--no-browsers');
  if (options.seed) args.push('--seed');

  // Its own process group, so stopping it also stops any Playwright run it started.
  const child = spawn('uv', args, {
    cwd: REPO_ROOT,
    detached: true,
    env: { ...process.env, WORKBENCH_WORKSPACE: workspace },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let log = '';
  let gone = false;
  child.stdout?.on('data', (chunk: Buffer) => (log += chunk.toString()));
  child.stderr?.on('data', (chunk: Buffer) => (log += chunk.toString()));
  const exited = new Promise<void>((resolve) => {
    const finish = (note = ''): void => {
      gone = true;
      log += note;
      resolve();
    };
    child.once('exit', () => finish());
    child.once('error', (error) => finish(String(error)));
  });

  const signal = (name: NodeJS.Signals): void => {
    try {
      if (child.pid) process.kill(-child.pid, name);
    } catch {
      // already gone
    }
  };
  const stop = async (): Promise<void> => {
    signal('SIGTERM');
    const force = setTimeout(() => signal('SIGKILL'), STOP_TIMEOUT_MS);
    await exited;
    clearTimeout(force);
    rmSync(workspace, { recursive: true, force: true });
  };

  const deadline = Date.now() + START_TIMEOUT_MS;
  let up = false;
  while (!up && !gone && Date.now() < deadline) {
    try {
      up = (await fetch(`${url}/healthz`)).ok;
    } catch {
      // not listening yet
    }
    if (!up) await new Promise((resolve) => setTimeout(resolve, 150));
  }
  if (!up) {
    await stop();
    throw new Error(`The app did not start at ${url}.\n${log}`);
  }

  const reports: Record<string, string> = options.seed
    ? JSON.parse(readFileSync(path.join(workspace, 'seeded.json'), 'utf8'))
    : {};
  return { app: { url, workspace, reports }, stop };
}

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export const test = base.extend<{}, { appOptions: AppOptions; app: App }>({
  appOptions: [{}, { option: true, scope: 'worker' }],
  app: [
    async ({ appOptions }, use) => {
      const { app, stop } = await startApp(appOptions);
      await use(app);
      await stop();
    },
    { scope: 'worker', timeout: 60_000 },
  ],
  baseURL: async ({ app }, use) => {
    await use(app.url);
  },
});

export { expect } from '@playwright/test';
```

Create `tests/ui/support/page.ts`:

```ts
import { expect, type Locator, type Page } from '@playwright/test';

/** A live heal or generation is real work in Chromium; allow for slow machines. */
export const RUN_TIMEOUT_MS = 60_000;

/** The status pill at the top of a live run or a result. */
export function statusPill(page: Page): Locator {
  return page.locator('#main .result-head .pill').first();
}

/** Waits for a run to finish and its report page to show `status`. */
export async function expectResult(page: Page, status: string): Promise<void> {
  await expect(statusPill(page)).toHaveText(status, { timeout: RUN_TIMEOUT_MS });
  await expect(page).toHaveURL(/\/reports\//);
}

/** Opens the model menu and waits until the server has filled it in. */
export async function openModelMenu(page: Page): Promise<Locator> {
  await page.getByRole('button', { name: /Change the model/ }).click();
  const menu = page.locator('#model-menu');
  await expect(menu.getByRole('heading', { name: 'Model' })).toBeVisible();
  return menu;
}

/** The links that switch a heal result between Diff, video, log and Model I/O. */
export function resultViews(page: Page): Locator {
  return page.getByRole('navigation', { name: 'Result views' });
}
```

- [ ] **Step 5: Let the tools see the new files**

`tsconfig.json`, `include`:

```json
  "include": ["tests/**/*", "playwright.workspace.config.ts", "playwright.ui.config.ts", "src/**/*"],
```

`eslint.config.cjs`: add this block before the final rules block, so the helpers that assert count as assertions:

```js
  {
    files: ['tests/ui/**/*.spec.ts'],
    rules: {
      'playwright/expect-expect': [
        'warn',
        { assertFunctionNames: ['expectResult', 'expectNoSeriousViolations'] },
      ],
    },
  },
```

- [ ] **Step 6: Run the spec**

Run: `npm run test:ui`
Expected: 3 passed. The first test passes on a machine where Ollama or LM Studio is running (Review Focus 1).

If a test fails because the page differs from what this plan says (text, role, timing), read the trace (`npx playwright show-trace test-results/ui/<test>/trace.zip`), then decide: a wrong expectation is fixed in the test with a `Ruling:` in the ledger; a real defect in the app is fixed in the app, test first.

- [ ] **Step 7: Format, lint and type-check**

Run: `npx prettier --write tests/ui playwright.ui.config.ts && npm run lint && npm run type-check`
Expected: all pass.

- [ ] **Step 8: Check nothing is left running (Review Focus 5)**

Run: `pgrep -fl "tests.ui.serve" ; echo "exit: $?"`
Expected: no process listed, `exit: 1`.

- [ ] **Step 9: Update the guides**

- `AGENTS.md` layout: after the `tests/integration/` line add `tests/ui/                Playwright Test (TypeScript) against the real app with Demo; serve.py starts it`, and after `playwright.workspace.config.ts` add `playwright.ui.config.ts  the UI suite's config`.
- `AGENTS.md` commands: add `npm run test:ui                            # UI tests: real app, Chromium, Demo model`.
- `AGENTS.md` rules: add `- UI tests get their app from the fixture in tests/ui/support/app.ts (free port, temporary workspace). Never point them at port 7860 or workspace/.`
- `README.md` Develop block: add the same `npm run test:ui` line.
- `CHANGELOG.md` → `### Added`: `` A UI test suite (`npm run test:ui`) that drives the real app in Chromium with the Demo model. ``

- [ ] **Step 10: Commit**

```bash
git add playwright.ui.config.ts tests/ui package.json tsconfig.json eslint.config.cjs AGENTS.md README.md CHANGELOG.md
git commit -m "test: add the UI suite harness and the first-launch spec"
```

---

### Task 3: Accessibility: the axe gate, contrast, and result views as links

**Files:**

- Create: `tests/ui/support/axe.ts`
- Modify: `tests/ui/first-launch.spec.ts`, `package.json`, `package-lock.json`
- Modify: `src/workbench/web/static/css/tokens.css`, `src/workbench/web/static/css/app.css:609`
- Modify: `src/workbench/web/templates/partials/heal_result.html` (the `tabs` nav and the `tabpanel` div)
- Modify: `tests/unit/test_web_assets.py`, `tests/unit/test_web_reports.py:29,138`
- Modify: `ROADMAP.md`, `CHANGELOG.md`, `AGENTS.md`

**Interfaces:**

- Consumes: `test`, `expect` from `tests/ui/support/app.ts`.
- Produces: `expectNoSeriousViolations(page: Page): Promise<void>` in `tests/ui/support/axe.ts`; the result views are `<nav aria-label="Result views">` with links, the current one marked `aria-current="page"` (Tasks 4 and 5 rely on this through `resultViews`).

- [ ] **Step 1: Add axe and the failing accessibility checks**

Run: `npm install --save-dev @axe-core/playwright@4.13.0`

Create `tests/ui/support/axe.ts`:

```ts
import { AxeBuilder } from '@axe-core/playwright';
import { expect, type Page } from '@playwright/test';

/** Fails on any axe violation rated serious or critical: the gate in the v2 spec, section 8. */
export async function expectNoSeriousViolations(page: Page): Promise<void> {
  const { violations } = await new AxeBuilder({ page }).analyze();
  const blocking = violations
    .filter((violation) => violation.impact === 'serious' || violation.impact === 'critical')
    .map((violation) => {
      const where = violation.nodes.map((node) => node.target.join(' ')).join(' | ');
      return `${violation.id}: ${where}`;
    });
  expect(blocking).toEqual([]);
}
```

In `tests/ui/first-launch.spec.ts`, import it and add one call at the end of each of the first two tests (the page with no model, and the open menu):

```ts
import { expectNoSeriousViolations } from './support/axe';
```

```ts
  await expectNoSeriousViolations(page);
```

- [ ] **Step 2: Run to see the contrast failures**

Run: `npm run test:ui`
Expected: the first two tests FAIL with `color-contrast: .model-pill__provider | …` (muted text `#8a8a93` is 3.42:1 on white and 3.18:1 on the canvas).

- [ ] **Step 3: Write the failing unit test for contrast**

Add at the end of `tests/unit/test_web_assets.py`:

```python
def _luminance(colour: str) -> float:
    channels = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(text: str, background: str) -> float:
    lighter, darker = sorted(
        (_luminance(FIGMA_COLOURS[text]), _luminance(FIGMA_COLOURS[background])),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


# Every text colour on every background it is used on.
TEXT_ON_BACKGROUND = [
    ("text-primary", "bg-canvas"),
    ("text-secondary", "bg-subtle"),
    ("text-tertiary", "bg-surface"),
    ("text-tertiary", "bg-canvas"),
    ("text-tertiary", "bg-subtle"),
    ("status-pass", "status-pass-bg"),
    ("status-fail", "status-fail-bg"),
    ("status-run", "status-run-bg"),
    ("status-warn", "status-warn-bg"),
    ("code-text", "code-bg"),
    ("code-muted", "code-bg"),
    ("code-muted", "code-gutter"),
    ("code-muted", "diff-add-bg"),
    ("code-muted", "diff-del-bg"),
    ("diff-add-text", "diff-add-bg"),
    ("diff-del-text", "diff-del-bg"),
]


def test_text_colours_meet_wcag_aa_contrast() -> None:
    low = {
        f"{text} on {background}": round(_contrast(text, background), 2)
        for text, background in TEXT_ON_BACKGROUND
        if _contrast(text, background) < 4.5
    }
    assert low == {}
```

Run: `uv run python -m pytest tests/unit/test_web_assets.py`
Expected: the new test FAILS, listing nine pairs: `text-tertiary` on all three backgrounds, `status-pass`, `status-warn`, and `code-muted` on its four backgrounds.

Now change four values in `FIGMA_COLOURS` in the same file:

```python
    "text-tertiary": "#6c6c73",
    "status-pass": "#147d3b",
    "status-warn": "#b15209",
    "code-muted": "#8c8c93",
```

Run: `uv run python -m pytest tests/unit/test_web_assets.py`
Expected: the contrast test passes; the token-values test FAILS, because `tokens.css` still has the old values.

- [ ] **Step 4: Change the four tokens**

In `src/workbench/web/static/css/tokens.css`:

```css
  --text-tertiary: #6c6c73;
```

```css
  --status-pass: #147d3b;
```

```css
  --status-warn: #b15209;
```

```css
  --code-muted: #8c8c93;
```

And change the header comment's second line to:

```css
   Figma file eL5DUZmc85ESpusNSmxDkA. Four values are darker (or, on code, lighter) than the file
   for WCAG AA contrast; ROADMAP.md tracks bringing the file in line. */
```

Run: `uv run python -m pytest tests/unit/test_web_assets.py && npm run test:ui`
Expected: all pass.

- [ ] **Step 5: Write the failing test for the result views**

In `tests/unit/test_web_reports.py`, change the two assertions and add one line after the first:

```python
    assert 'aria-current="page">Diff</a>' in html
    assert 'role="tab"' not in html and 'role="tabpanel"' not in html
```

```python
    assert 'aria-current="page">Execution log</a>' in html
```

Run: `uv run python -m pytest tests/unit/test_web_reports.py`
Expected: 2 failed.

- [ ] **Step 6: Make the result views links**

In `src/workbench/web/templates/partials/heal_result.html`, replace the `tabs` nav and the opening tag of the panel:

```html
      <nav class="tabs" aria-label="Result views">
        {% for name, label in result.tabs %}
        <a class="tab" href="/reports/{{ report.id }}?{% if result.attempt %}attempt={{ result.attempt.number }}&{% endif %}tab={{ name }}"{% if name == result.tab %} aria-current="page"{% endif %}>{{ label }}</a>
        {% endfor %}
      </nav>
      <div>
```

In `src/workbench/web/static/css/app.css`:

```css
.tab[aria-current='page'] {
```

Run: `uv run python -m pytest tests/unit/test_web_reports.py tests/unit/test_web_assets.py`
Expected: all pass.

- [ ] **Step 7: Update the guides**

- `ROADMAP.md`, the Figma row: change the item to `Figma file: the four §5.3 changes, and four contrast values (text/tertiary #6c6c73, status/pass #147d3b, status/warn #b15209, code/muted #8c8c93); the app already has them`.
- `CHANGELOG.md` → `### Added`: `Accessibility checks with axe on every page state in the UI suite.`
- `CHANGELOG.md` → `### Changed`:
  - `Muted text and the pass and warning colours are darker, so all text meets WCAG AA contrast.`
  - `The result views (Diff, Re-run video, Execution log, Model I/O) are plain links, so they work as expected with a keyboard and a screen reader.`
- `AGENTS.md`, the UI rule: append the sentence `Four values differ from the Figma file for contrast; ROADMAP.md lists them.`

- [ ] **Step 8: Verify and commit**

Run: `uv run python -m pytest && npx prettier --write tests/ui && npm run lint && npm run type-check && npm run test:ui`
Expected: all pass.

```bash
git add tests/ui package.json package-lock.json src/workbench/web tests/unit/test_web_assets.py tests/unit/test_web_reports.py ROADMAP.md CHANGELOG.md AGENTS.md
git commit -m "fix: meet WCAG AA contrast and make the result views links; check pages with axe"
```

---

### Task 4: The Heal page and live heals

**Files:**

- Create: `tests/ui/heal.spec.ts`

**Interfaces:**

- Consumes: `test`, `expect` (`support/app.ts`); `expectResult`, `resultViews`, `statusPill` (`support/page.ts`); `expectNoSeriousViolations` (`support/axe.ts`).
- Produces: nothing.

- [ ] **Step 1: Write the spec**

Create `tests/ui/heal.spec.ts`:

```ts
import { readFileSync } from 'node:fs';

import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';
import { expectResult, resultViews, statusPill } from './support/page';

test.use({ appOptions: { model: 'demo' } });

const SPEC_INPUT = 'input[name="spec"]';

test('idle: the samples and the upload are offered', async ({ page }) => {
  await page.goto('/heal');

  await expect(page.getByRole('heading', { name: 'Pick a sample or upload a spec' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Change the model/ })).toContainText(
    'scripted answers'
  );
  await expect(page.getByRole('button', { name: 'Heal the Selector drift sample' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Heal the App bug sample' })).toBeEnabled();
  await expect(page.getByRole('button', { name: 'Heal uploaded file' })).toBeEnabled();
  await expectNoSeriousViolations(page);
});

test('selector drift: live steps, then a healed test with its evidence', async ({ page }) => {
  await page.goto('/heal');
  await page.getByRole('button', { name: 'Heal the Selector drift sample' }).click();

  // Running
  await expect(statusPill(page)).toHaveText('Healing');
  await expect(page.getByRole('list', { name: 'Progress' }).getByRole('listitem')).toContainText([
    'Run the test',
    'Collect evidence',
    'Diagnose',
    'Repair',
    'Verify',
  ]);
  await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Heal the App bug sample' })).toBeDisabled();
  await expect(page.getByRole('log')).not.toBeEmpty();
  await expectNoSeriousViolations(page);

  // Healed
  await expectResult(page, 'Healed');
  await expect(page.getByRole('heading', { name: 'contact-form.spec.ts' })).toBeVisible();
  await expect(page.locator('#main .result-head').getByText('Demo', { exact: true })).toBeVisible();
  const diff = page.getByRole('region', { name: 'Diff' });
  await expect(diff.locator('.code__line--del')).toContainText("page.locator('#submit-btn')");
  await expect(diff.locator('.code__line--add')).toContainText('data-testid="submit"');
  const diagnosis = page.getByRole('complementary', { name: /Diagnosis/ });
  await expect(diagnosis).toContainText('LOCATOR_DRIFT');
  await expect(diagnosis).toContainText('Re-run passed in');
  await expect(diagnosis).toContainText('not a live model');
  await expectNoSeriousViolations(page);

  // Re-run video
  const views = resultViews(page);
  await views.getByRole('link', { name: 'Re-run video' }).click();
  await expect(page.getByText('Verification re-run of attempt 1')).toBeVisible();
  const source = await page.locator('video').getAttribute('src');
  const clip = await page.request.get(source ?? '');
  expect(clip.ok()).toBe(true);
  expect(clip.headers()['content-type']).toContain('video/webm');

  // Execution log
  await views.getByRole('link', { name: 'Execution log' }).click();
  const log = page.getByRole('region', { name: 'Execution log' });
  await expect(log).toContainText('$ npx playwright test contact-form.spec.ts');
  await expect(log).toContainText('[attempt 1] Healed');

  // Model I/O
  await views.getByRole('link', { name: 'Model I/O' }).click();
  await expect(page.getByRole('columnheader', { name: 'Sent to the model' })).toBeVisible();
  await expect(page.getByRole('region', { name: 'Model reply' })).toContainText(
    'valid HealingAnalysis'
  );
  await expectNoSeriousViolations(page);

  // Downloads
  const report = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download report' }).click();
  expect((await report).suggestedFilename()).toMatch(/\.json$/);
  const fixed = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Download fixed spec' }).click();
  expect(readFileSync(await (await fixed).path(), 'utf8')).toContain('data-testid="submit"');
});

test('app bug: the heal stops and leaves the test alone', async ({ page }) => {
  await page.goto('/heal');
  await page.getByRole('button', { name: 'Heal the App bug sample' }).click();

  await expectResult(page, 'Likely app bug');
  await expect(page.getByRole('heading', { name: 'checkout.spec.ts' })).toBeVisible();
  await expect(page.getByText('Stopped: likely app bug')).toBeVisible();
  await expect(page.getByRole('complementary', { name: /Diagnosis/ })).toContainText(
    'POTENTIAL_APP_DEFECT'
  );
  await expect(page.getByRole('link', { name: 'Download fixed spec' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Heal again' })).toBeVisible();
  await expectNoSeriousViolations(page);
});

test('an uploaded test that already passes has nothing to heal', async ({ page, baseURL }) => {
  const passing = [
    "import { test, expect } from '@playwright/test';",
    '',
    "test('The sample site loads', async ({ page }) => {",
    `  await page.goto('${baseURL}/sample-site/');`,
    "  await expect(page.getByLabel('Name')).toBeVisible();",
    '});',
    '',
  ].join('\n');

  await page.goto('/heal');
  await page.locator(SPEC_INPUT).setInputFiles({
    name: 'site-loads.spec.ts',
    mimeType: 'text/plain',
    buffer: Buffer.from(passing),
  });
  await expect(page.locator('#upload-name')).toHaveText('site-loads.spec.ts');
  await page.getByRole('button', { name: 'Heal uploaded file' }).click();

  await expectResult(page, 'Nothing to heal');
  await expect(page.getByText('The test passed on its first run')).toBeVisible();
});

test('cancel stops a run and keeps the test unchanged', async ({ page }) => {
  await page.goto('/heal');
  await page.getByRole('button', { name: 'Heal the Selector drift sample' }).click();
  await page.getByRole('button', { name: 'Cancel' }).click();

  await expectResult(page, 'Cancelled');
  await expect(page.getByText('The file was not changed')).toBeVisible();
});

test('upload errors are shown next to the upload', async ({ page }) => {
  await page.goto('/heal');
  const error = page.locator('#upload-error');
  const start = page.getByRole('button', { name: 'Heal uploaded file' });

  await start.click();
  await expect(error).toHaveText('Choose a .spec.ts file first.');

  await page.locator(SPEC_INPUT).setInputFiles({
    name: 'notes.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('not a test'),
  });
  await start.click();
  await expect(error).toHaveText("notes.txt isn't a test file. Only .spec.ts files are supported.");

  await page.locator(SPEC_INPUT).setInputFiles({
    name: 'huge.spec.ts',
    mimeType: 'text/plain',
    buffer: Buffer.alloc(200 * 1024 + 1, 'a'),
  });
  await start.click();
  await expect(error).toHaveText('huge.spec.ts is larger than 200 KB.');
  await expect(page.getByRole('heading', { name: 'Pick a sample or upload a spec' })).toBeVisible();
});
```

- [ ] **Step 2: Run it**

Run: `npm run test:ui -- tests/ui/heal.spec.ts`
Expected: 6 passed.

These tests describe behaviour the app already has, so they should pass on the first run. Prove that two of them can fail before trusting them:

- In `src/workbench/web/templates/partials/heal_result.html`, change `Stopped: likely app bug` to `Stopped`, re-run `npm run test:ui -- tests/ui/heal.spec.ts -g "app bug"`, expect FAIL, then restore the file with `git checkout src/workbench/web/templates/partials/heal_result.html`.
- In `src/workbench/validation.py`, change `larger than 200 KB` to `too big`, re-run with `-g "upload errors"`, expect FAIL, then restore with `git checkout src/workbench/validation.py`.

A failure for any other reason is handled as in Task 2 Step 6.

- [ ] **Step 3: Format, lint, commit**

Run: `npx prettier --write tests/ui && npm run lint && npm run type-check`
Expected: all pass.

```bash
git add tests/ui/heal.spec.ts
git commit -m "test: cover the Heal page and live heals in the UI suite"
```

---

### Task 5: The Generate page and every saved result state

**Files:**

- Create: `tests/ui/generate.spec.ts`, `tests/ui/results.spec.ts`

**Interfaces:**

- Consumes: `test`, `expect`, `app.reports` (`support/app.ts`); `expectResult`, `resultViews`, `statusPill` (`support/page.ts`); `expectNoSeriousViolations` (`support/axe.ts`).
- Produces: nothing.

- [ ] **Step 1: Write the Generate spec**

Create `tests/ui/generate.spec.ts`:

```ts
import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';
import { expectResult, statusPill } from './support/page';

test.use({ appOptions: { model: 'demo', seed: true } });

const SCENARIO = 'A user can send the contact form';

test('empty: the form, the one example Demo can answer, and an empty result area', async ({
  page,
}) => {
  await page.goto('/generate');

  await expect(page.getByRole('heading', { name: 'Your test will appear here' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Contact form' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Checkout' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Generate test' })).toBeEnabled();
  await expectNoSeriousViolations(page);
});

test('an invalid URL is refused next to the field', async ({ page }) => {
  await page.goto('/generate');
  await page.getByLabel('Target URL').fill('not a url');
  await page.getByLabel('Scenario').fill(SCENARIO);
  await page.getByRole('button', { name: 'Generate test' }).click();

  await expect(page.locator('#url-error')).toHaveText(
    'Enter a full URL, starting with http:// or https://'
  );
  await expect(page.getByRole('heading', { name: 'Your test will appear here' })).toBeVisible();
});

test('the example generates a passing test, with live steps', async ({ page, baseURL }) => {
  await page.goto('/generate');
  await page.getByRole('link', { name: 'Contact form' }).click();
  await expect(page.getByLabel('Target URL')).toHaveValue(`${baseURL}/sample-site/`);
  await expect(page.getByLabel('Scenario')).toHaveValue(SCENARIO);
  await page.getByRole('button', { name: 'Generate test' }).click();

  // Generating
  await expect(statusPill(page)).toHaveText('Generating');
  await expect(page.getByRole('list', { name: 'Progress' }).getByRole('listitem')).toContainText([
    'Load page context',
    'Ask the model',
    'Run the test',
  ]);

  // Passed
  await expectResult(page, 'Passed');
  await expect(page.getByRole('region', { name: /workspace\/specs\// })).toContainText(
    "getByRole('button', { name: 'Submit' })"
  );
  const context = page.getByRole('complementary', { name: 'Page context used' });
  await expect(context).toContainText('Passed in Chromium');
  await expect(context).toContainText('not a live model');
  await expect(page.getByRole('link', { name: 'Download spec' })).toBeVisible();
  await expectNoSeriousViolations(page);
});

test('a test generated without running can be run afterwards', async ({ page }) => {
  await page.goto('/generate?example=contact-form');
  await page.getByLabel('Run the test after generating').uncheck();
  await page.getByRole('button', { name: 'Generate test' }).click();

  await expectResult(page, 'Not run');
  await expect(page.getByRole('complementary', { name: 'Page context used' })).toContainText(
    'Not run'
  );

  await page.getByRole('button', { name: 'Run test' }).click();
  await expectResult(page, 'Passed');
});

test('a generated test that fails can be sent to Heal', async ({ page, app }) => {
  await page.goto(`/reports/${app.reports.generate_failed}`);
  await expect(statusPill(page)).toHaveText('Run failed');

  await page.getByRole('button', { name: 'Heal this test' }).click();

  await expect(page).toHaveURL(/\/heal\?run=/);
  await expectResult(page, 'Healed');
  await expect(
    page.getByRole('heading', { name: 'a-user-can-send-the-contact-form.spec.ts' })
  ).toBeVisible();
});
```

- [ ] **Step 2: Write the results spec**

Create `tests/ui/results.spec.ts`:

```ts
import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';
import { resultViews, statusPill } from './support/page';

// Every result state, rendered by the app from a saved report (tests/unit/report_fixtures.py).
test.use({ appOptions: { model: 'demo', seed: true } });

type Expected = { state: string; pill: string; shows: string[] };

const RESULTS: Expected[] = [
  { state: 'healed', pill: 'Healed', shows: ['Download fixed spec', 'Re-run passed in 2.1s'] },
  {
    state: 'healed_after_retries',
    pill: 'Healed',
    shows: ['Attempt 1', 'Fix not applied', 'Attempt 2', 'Showing attempt 2'],
  },
  {
    state: 'not_healed',
    pill: 'Not healed',
    shows: [
      'Re-run failed',
      'Fix not applied',
      'Invalid model reply',
      "The response didn't match the HealingAnalysis schema",
    ],
  },
  {
    state: 'app_defect',
    pill: 'Likely app bug',
    shows: ['Stopped: likely app bug', 'The test was not changed'],
  },
  { state: 'nothing_to_heal', pill: 'Nothing to heal', shows: ['The test passed on its first run'] },
  { state: 'cancelled', pill: 'Cancelled', shows: ['The file was not changed'] },
  { state: 'model_error', pill: 'Error', shows: ['Model unreachable', 'Could not reach Ollama'] },
  {
    state: 'with_warnings',
    pill: 'Healed',
    shows: ['Page context unavailable', 'Repair used text replacement', 'Applied as a text edit'],
  },
  {
    state: 'demo_healed',
    pill: 'Healed',
    shows: ['Demo', 'Answers replayed from samples/recordings'],
  },
  { state: 'generate_passed', pill: 'Passed', shows: ['Download spec', 'Passed in Chromium'] },
  { state: 'generate_not_run', pill: 'Not run', shows: ['Run test'] },
  { state: 'generate_failed', pill: 'Run failed', shows: ['Heal this test'] },
  {
    state: 'generate_error',
    pill: 'Error',
    shows: ['Model timed out', 'did not answer within 300 seconds', 'No test written'],
  },
];

for (const { state, pill, shows } of RESULTS) {
  test(`saved result: ${state}`, async ({ page, app }) => {
    await page.goto(`/reports/${app.reports[state]}`);

    await expect(statusPill(page)).toHaveText(pill);
    for (const text of shows) {
      await expect(page.locator('#main').getByText(text).first()).toBeVisible();
    }
    await expectNoSeriousViolations(page);
  });
}

test('result views and attempts are links that work from the keyboard', async ({ page, app }) => {
  await page.goto(`/reports/${app.reports.healed_after_retries}`);
  const views = resultViews(page);
  await expect(views.getByRole('link')).toHaveText([
    'Diff',
    'Re-run video',
    'Execution log',
    'Model I/O',
  ]);
  await expect(views.getByRole('link', { name: 'Diff' })).toHaveAttribute('aria-current', 'page');

  await views.getByRole('link', { name: 'Model I/O' }).focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/tab=model/);
  await expect(views.getByRole('link', { name: 'Model I/O' })).toHaveAttribute(
    'aria-current',
    'page'
  );
  await expect(page.getByRole('columnheader', { name: 'Sent to the model' })).toBeVisible();

  await page.getByRole('navigation', { name: 'Attempts' }).getByRole('link', { name: /Attempt 1/ }).focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/attempt=1/);
  await expect(page).toHaveURL(/tab=model/);
  await expect(page.getByRole('complementary', { name: 'Diagnosis · attempt 1' })).toBeVisible();
});

test('a view that a result does not have falls back to the first one', async ({ page, app }) => {
  await page.goto(`/reports/${app.reports.not_healed}?tab=diff`);

  await expect(resultViews(page).getByRole('link')).toHaveText(['Execution log', 'Model I/O']);
  await expect(page.getByRole('region', { name: 'Execution log' })).toBeVisible();
});

test('an unknown report says so', async ({ page }) => {
  await page.goto('/reports/20260101-000000-heal-missing');

  await expect(page.getByRole('heading', { name: 'No such report' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Back to Heal' })).toBeVisible();
});
```

- [ ] **Step 3: Run them**

Run: `npm run test:ui -- tests/ui/generate.spec.ts tests/ui/results.spec.ts`
Expected: 21 passed (5 + 16).

Prove two can fail, restoring each file with `git checkout <file>` afterwards:

- In `src/workbench/web/views.py`, change the label `"Not healed"` to `"Failed"`; re-run with `-g "saved result: not_healed"`; expect FAIL.
- In `src/workbench/web/routes/generate.py`, change `"Enter a full URL, starting with http:// or https://"` to `"Bad URL"`; re-run with `-g "invalid URL"`; expect FAIL.

A failure for any other reason is handled as in Task 2 Step 6.

- [ ] **Step 4: Format, lint, commit**

Run: `npx prettier --write tests/ui && npm run lint && npm run type-check`
Expected: all pass.

```bash
git add tests/ui/generate.spec.ts tests/ui/results.spec.ts
git commit -m "test: cover the Generate page and every saved result state in the UI suite"
```

---

### Task 6: Model and browser states

**Files:**

- Create: `tests/ui/model-unreachable.spec.ts`, `tests/ui/model-connected.spec.ts`, `tests/ui/browsers-missing.spec.ts`

**Interfaces:**

- Consumes: `test`, `expect` (`support/app.ts`); `openModelMenu` (`support/page.ts`); `expectNoSeriousViolations` (`support/axe.ts`).
- Produces: nothing.

- [ ] **Step 1: Write the three specs**

Create `tests/ui/model-unreachable.spec.ts`:

```ts
import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';

test.use({ appOptions: { model: 'unreachable' } });

test('a saved model that is down blocks runs and offers the demo', async ({ page }) => {
  await page.goto('/heal');
  await expect(
    page.getByRole('heading', { name: "Can't reach Ollama at 127.0.0.1:9/v1" })
  ).toBeVisible();
  await expect(page.getByRole('button', { name: /Change the model/ })).toContainText(
    'Not connected'
  );
  await expect(page.getByRole('button', { name: 'Heal the Selector drift sample' })).toBeDisabled();
  await expectNoSeriousViolations(page);

  await page.goto('/generate');
  await expect(page.getByRole('heading', { name: /Can't reach Ollama/ })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Generate test' })).toBeDisabled();

  await page.getByRole('button', { name: 'Switch to demo model' }).click();
  await expect(page.getByRole('button', { name: /Change the model/ })).toContainText(
    'scripted answers'
  );
  await expect(page.getByRole('button', { name: 'Generate test' })).toBeEnabled();
});
```

Create `tests/ui/model-connected.spec.ts`:

```ts
import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';
import { openModelMenu } from './support/page';

// A fake OpenAI-compatible server stands in for LM Studio.
test.use({ appOptions: { model: 'fake' } });

test("a connected model shows its name and lists the server's chat models", async ({ page }) => {
  await page.goto('/heal');
  const pill = page.getByRole('button', { name: /Change the model/ });
  await expect(pill).toContainText('fake-model');
  await expect(pill).toContainText('LM Studio');
  await expect(page.getByText('asks fake-model · LM Studio for a fix')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Heal the Selector drift sample' })).toBeEnabled();

  const menu = await openModelMenu(page);
  await expect(menu.getByText('Connected', { exact: true })).toBeVisible();
  await expect(menu.getByLabel('Server')).toHaveValue(/^http:\/\/127\.0\.0\.1:\d+\/v1$/);
  const models = menu.getByLabel('Model', { exact: true });
  await expect(models).toHaveValue('fake-model');
  // The server also lists an embedding model, which cannot chat.
  await expect(models.locator('option')).toHaveText(['fake-model']);
  await expect(menu.getByRole('button', { name: 'Save' })).toBeEnabled();
  await expectNoSeriousViolations(page);
});

test('with a real model both Generate examples are offered', async ({ page }) => {
  await page.goto('/generate');

  await expect(page.getByRole('link', { name: 'Contact form' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Checkout' })).toBeVisible();
});
```

Create `tests/ui/browsers-missing.spec.ts`:

```ts
import { expect, test } from './support/app';
import { expectNoSeriousViolations } from './support/axe';

test.use({ appOptions: { model: 'demo', browsers: false } });

const PAGES = [
  { path: '/heal', start: 'Heal the Selector drift sample' },
  { path: '/generate', start: 'Generate test' },
];

for (const { path, start } of PAGES) {
  test(`${path}: missing browsers block the page and say how to install them`, async ({
    page,
  }) => {
    await page.goto(path);

    const banner = page
      .getByRole('alert')
      .filter({ hasText: "Playwright browsers aren't installed" });
    await expect(banner).toContainText('npx playwright install chromium');
    await expect(page.getByRole('button', { name: start })).toBeDisabled();
    await expectNoSeriousViolations(page);
  });
}
```

- [ ] **Step 2: Run the whole suite**

Run: `npm run test:ui`
Expected: 35 passed (first-launch 3, heal 6, generate 5, results 16, model-unreachable 1, model-connected 2, browsers-missing 2).

Prove one can fail: in `tests/ui/serve.py`, change `browsers_ready=lambda: False` to `browsers_ready=lambda: True`; re-run `npm run test:ui -- tests/ui/browsers-missing.spec.ts`; expect 2 failed; restore with `git checkout tests/ui/serve.py`.

- [ ] **Step 3: Format, lint, commit**

Run: `npx prettier --write tests/ui && npm run lint && npm run type-check`
Expected: all pass.

```bash
git add tests/ui
git commit -m "test: cover the model and browser states in the UI suite"
```

---

### Task 7: CI: four jobs, pinned actions, monthly updates

**Files:**

- Modify: `.github/workflows/ci.yml` (replace), `.github/dependabot.yml`
- Modify: `tests/unit/test_quality_gates.py`, `package-lock.json` (if `npm audit fix` changes it), `CHANGELOG.md`

**Interfaces:**

- Consumes: npm scripts `lint:py`, `lint:types`, `type-check`, `lint:js`, `lint:format`, `lint:md`, `test:ui` (Tasks 1 and 2).
- Produces: nothing.

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_quality_gates.py` (and add `import re` at the top):

```python
WORKFLOWS = PROJECT_ROOT / ".github" / "workflows"


def test_ci_runs_the_four_jobs() -> None:
    text = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    jobs = text.split("\njobs:\n", 1)[1]
    assert re.findall(r"^  ([a-z][\w-]*):$", jobs, flags=re.MULTILINE) == [
        "lint",
        "unit",
        "integration",
        "ui",
    ]


def test_workflow_actions_are_pinned_to_commits() -> None:
    unpinned = [
        f"{workflow.name}: {line.strip()}"
        for workflow in sorted(WORKFLOWS.glob("*.yml"))
        for line in workflow.read_text(encoding="utf-8").splitlines()
        if "uses:" in line and not re.search(r"@[0-9a-f]{40} # v\d", line)
    ]
    assert unpinned == []


def test_dependabot_checks_three_ecosystems_monthly() -> None:
    text = (PROJECT_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    ecosystems = re.findall(r"package-ecosystem: ([\w-]+)", text)
    assert ecosystems == ["uv", "npm", "github-actions"]
    assert re.findall(r"interval: (\w+)", text) == ["monthly"] * 3
```

Run: `uv run python -m pytest tests/unit/test_quality_gates.py`
Expected: 3 failed (jobs are `lint`, `e2e`; `ci.yml` uses tags; Dependabot is weekly), 3 passed.

- [ ] **Step 2: Replace the workflow**

Replace `.github/workflows/ci.yml` with:

```yaml
name: CI

on:
  push:
    branches: [main, v2]
  pull_request:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint and types
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up Node.js
        uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'

      - name: Install Node dependencies
        run: npm ci

      - name: Set up uv
        uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0

      - name: Install Python dependencies
        run: uv sync --group dev

      - name: Python lint and format (ruff)
        run: npm run lint:py

      - name: Python types (mypy, strict)
        run: npm run lint:types

      - name: TypeScript types (tsc)
        run: npm run type-check

      - name: JavaScript and TypeScript lint (eslint)
        run: npm run lint:js

      - name: Formatting (prettier)
        run: npm run lint:format

      - name: Markdown lint
        run: npm run lint:md

  unit:
    name: Unit tests and coverage
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up Node.js
        uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'

      # The syntax-tree repair runs through Node (ts-morph).
      - name: Install Node dependencies
        run: npm ci

      - name: Set up uv
        uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0

      - name: Install Python dependencies
        run: uv sync --group dev

      # Fails under 85% line and branch coverage (pyproject.toml).
      - name: Unit tests with coverage
        run: |
          uv run python -m pytest -q --cov --cov-report=term --cov-report=xml --cov-report=markdown-append:"$GITHUB_STEP_SUMMARY"

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@303a32d7a59b442fa8d48b6a1cc6825c09c847a5 # v7.1.1
        with:
          files: coverage.xml
          token: ${{ secrets.CODECOV_TOKEN }}
          fail_ci_if_error: false

  integration:
    name: Integration (real Chromium, Demo and fake models)
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up Node.js
        uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'

      - name: Install Node dependencies
        run: npm ci

      - name: Set up uv
        uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0

      - name: Install Python dependencies
        run: uv sync --group dev

      - name: Install Chromium
        run: npx playwright install --with-deps chromium

      - name: Generate and heal specs against a real browser
        env:
          WORKBENCH_WORKSPACE: ${{ github.workspace }}/workspace
        run: uv run python -m pytest tests/integration -v --junitxml=reports/integration-pytest.xml

      - name: Upload integration artifacts
        if: always()
        uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: integration-report
          path: |
            reports/
            workspace/
          if-no-files-found: warn
          retention-days: 14

  ui:
    name: UI (Playwright Test, axe, Demo model)
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      - name: Set up Node.js
        uses: actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0
        with:
          node-version-file: '.nvmrc'
          cache: 'npm'

      - name: Install Node dependencies
        run: npm ci

      - name: Set up uv
        uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0

      - name: Install Python dependencies
        run: uv sync --group dev

      - name: Install Chromium
        run: npx playwright install --with-deps chromium

      - name: Drive the app in Chromium
        run: npm run test:ui

      - name: Upload the UI report
        if: always()
        uses: actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2
        with:
          name: ui-report
          path: |
            playwright-report/
            test-results/ui/
          if-no-files-found: warn
          retention-days: 14
```

- [ ] **Step 3: Check every input against the pinned actions (P6)**

Run:

```bash
check() { echo "== $1"; curl -fsSL "https://raw.githubusercontent.com/$1/$2/action.yml" | grep -nE "^  ($3):" ; }
check actions/checkout 3d3c42e5aac5ba805825da76410c181273ba90b1 "persist-credentials"
check actions/setup-node 949feb2413d6458794dcd2491c4babbbce0c15c1 "node-version-file|cache"
check codecov/codecov-action 303a32d7a59b442fa8d48b6a1cc6825c09c847a5 "files|token|fail_ci_if_error"
check actions/upload-artifact cf430e030ddbb5b0abf93d22962f4752f3646cd9 "name|path|if-no-files-found|retention-days"
```

Expected: every input name is listed (1, 2, 3 and 4 lines). If one is missing, read that action's `action.yml` and use the input it now offers; record a `Ruling:`.

- [ ] **Step 4: Make Dependabot monthly**

In `.github/dependabot.yml`, change the first comment line to `# Monthly dependency updates, grouped so minor and patch bumps land as one PR` and all three `interval: weekly` to `interval: monthly`.

- [ ] **Step 5: Clear what `npm audit` can clear without a breaking change**

Run: `npm audit fix`
Expected: the `lint-staged` advisory is fixed. The others come through `markdownlint-cli2`, which is already at its latest version; leave them for Dependabot. Never use `--force`.

Run: `npm audit --omit=dev`
Expected: `found 0 vulnerabilities`.

- [ ] **Step 6: Run the tests**

Run: `uv run python -m pytest tests/unit/test_quality_gates.py`
Expected: 6 passed.

- [ ] **Step 7: Update the changelog, verify and commit**

`CHANGELOG.md` → `### Changed`: `CI runs four jobs (lint, unit, integration, UI) with actions pinned to commits, and Dependabot checks monthly.`

Run: `uv run python -m pytest && npm run lint`
Expected: all pass.

```bash
git add .github tests/unit/test_quality_gates.py package-lock.json CHANGELOG.md
git commit -m "ci: run lint, unit, integration and UI jobs with pinned actions"
```

---

### Task 8: Verify the phase and finish

**Files:**

- Modify: `ROADMAP.md`

- [ ] **Step 1: Run every gate on the final tree**

Run each and read the output:

```bash
uv run python -m pytest --cov
uv run python -m pytest tests/integration -q -o addopts=
npm run lint
npm run type-check
```

Expected: unit all pass with coverage at or above 85%; integration 17 passed; lint and type-check clean.

- [ ] **Step 2: Check the S5 table**

For every row of "Coverage of §5.2" above, confirm the named test exists and passed in the last run: `npx playwright test --config playwright.ui.config.ts --list`. Expected: 35 tests in 7 files; every row has at least one.

- [ ] **Step 3: Run the UI suite twice in a row (Review Focus 4)**

Run: `npm run test:ui -- --repeat-each 2`
Expected: 70 passed. A test that fails once in the two runs is flaky: find the cause (a wait on the wrong thing, a too-short timeout) and fix it; do not add a retry.

Run: `pgrep -fl "tests.ui.serve" ; echo "exit: $?"`
Expected: `exit: 1`.

- [ ] **Step 4: Move the roadmap row**

`ROADMAP.md`:

- Remove the Phase 5 row from "Now" and add to "Done": `| Quality gates: strict types, 85% coverage, UI suite with axe, four-job CI | 5 | [Phase 5](docs/superpowers/plans/2026-10-11-v2-phase-5-quality-gates.md) |`.
- Move the Phase 6 row from "Next" into "Now" as `| README, GIF, architecture and decision docs, 2.0.0 release | 🔭 Planned | 6 | Phase 6 plan (to be written) |`, and replace the "Next" table with the line `Nothing is queued after Phase 6.`

```bash
git add ROADMAP.md
git commit -m "docs: mark Phase 5 done in the roadmap"
```

- [ ] **Step 5: Final review**

Ask the user whether one reviewer subagent may be dispatched for the whole-branch review (P9). With approval, follow superpowers:executing-plans "Final Review". Without it, do the self-review that skill describes, write `Final review: self-review (user asked for no subagents)` in the ledger, and say so in the final message. Fix Critical and Important findings test-first in one pass; ledger the Minor ones.

- [ ] **Step 6: S6 needs a push**

S6 is "CI is green on `v2`". Report the result of Steps 1 to 5, list the rulings and deferred minors, and ask the user whether to push `v2`. After a yes, push and read the four jobs' results with `gh run watch`. A red job is fixed test-first and pushed again only after asking.
