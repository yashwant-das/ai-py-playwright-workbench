# v2 Phase 4: Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the FastAPI + Jinja + HTMX web app that runs heals and generations with live progress and shows every screen and state in the Figma design, so the workbench is usable end to end from a browser.

**Architecture:**

- **App:** `workbench.app.create_app(services)` builds the FastAPI app. `services` carries every collaborator the app calls (pipelines, model client, connection checks), so route tests pass fakes.
- **Runs:** a run starts in a background thread through `workbench.runs.RunRegistry`, which allows one active run at a time. The pipelines' `RunEvent`s are rendered into HTML fragments and streamed over server-sent events, so the page keeps no state of its own.
- **Results:** a finished run redirects to `/reports/{id}`, which renders the saved report. A reload therefore always shows the same result.
- **Look:** the styles mirror the Figma variables one to one. Code and diffs are highlighted on the server with Pygments.

**Tech Stack:**

- Python 3.13
- FastAPI 0.142.2 and Starlette 1.7
- Jinja2 3.1.6
- uvicorn 0.54.0
- python-multipart 0.0.32
- Pygments 2.21.0
- htmx 2.0.11 with htmx-ext-sse 2.2.4 (vendored)
- Inter and JetBrains Mono (self-hosted woff2)
- pytest with FastAPI's `TestClient` (httpx2 2.13.1 in the dev group)

**Spec:** [docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md](../specs/2026-10-03-v2-showcase-simplification-design.md). The relevant sections are:

- §5.1 Features
- §5.2 Screens and states (the complete list)
- §5.3 Figma changes
- §6.1 Layout
- §6.2 Runtime data flow
- §6.3 HTTP routes
- §6.7 UI implementation
- D1, D2 and D15
- §11 Phase 4

**Design reference:** [Figma file](https://www.figma.com/design/eL5DUZmc85ESpusNSmxDkA). Screenshots taken on 2026-10-04 are in [phase-4-figma/](phase-4-figma/); use them when the Figma MCP is rate-limited:

- `heal-running.png`
- `heal-healed.png`
- `heal-healed-retry-model-io.png`
- `heal-model-unreachable-popover.png`
- `generate-passed.png`
- `states-board.png`

The "Heal — not healed" and "Generate — run failed" frames have no screenshot. Their parts are on the states board: attempt cards, banners, input errors and the popover.

## Global Constraints

- **Stack (spec D2):** FastAPI + Jinja + HTMX + SSE, with no front-end build. No client-side libraries apart from HTMX and its SSE extension, vendored with their versions in the file names. Small inline `onclick`/`onchange` attributes for clipboard, stepper and file-name display are allowed. No other JavaScript files.
- **Network:** the app binds to `127.0.0.1` only. The default port is `7860`. `WORKBENCH_PORT` and `WORKBENCH_WORKSPACE` are the only environment variables, and both are optional.
- **One run at a time:** starting another returns `409`, and the UI keeps its start buttons disabled while a run is active.
- **Routes (spec §6.3):** `GET /` redirects to `/heal`. The others are:
  - `GET /heal`, `GET /generate`
  - `POST /heal`, `POST /generate`
  - `POST /runs/{id}/cancel`, `GET /runs/{id}/events`
  - `GET /reports/{id}`, `GET /reports/{id}.json`, `GET /reports/{id}/spec`, `GET /reports/{id}/video`
  - `GET /model`, `POST /model`, `POST /model/test`
  - `GET /sample-site/...`, `GET /healthz`

  This plan adds three routes: `GET /runs/{id}/result`, which redirects a finished run to its report; `POST /generate/run`, for the "Generated, not run" state's "Run test" button; and `GET /static/...`, for assets.
- **Tokens:**
  - `tokens.css` mirrors the 30 Figma colour variables one to one (`bg/canvas` becomes `--bg-canvas`), plus the 8 type styles.
  - `app.css` holds layout and components, using simple class names with BEM-style modifiers (`.btn`, `.btn--primary`, `.pill`, `.pill--pass`).
- **Fonts:** Inter and JetBrains Mono, self-hosted as `woff2` (SIL Open Font License).
- **Code and diffs:** highlighted on the server with Pygments; diffs come from `difflib`.
- **Accessibility:**
  - semantic landmarks and visible focus
  - a keyboard-operable popover (native `popover` attribute) and keyboard-operable tabs (links)
  - status changes announced through `aria-live`
  - colour never the only signal: every status has text and an icon
- **Desktop only:** the minimum supported width is 1280px.
- **Templates:** the pages are `heal.html` and `generate.html`. Partials live in `partials/` and are named after their component: `step_row`, `attempt_card`, `banner`, `pill`, `code_pane`, `diff_pane`, `model_io`, `diagnosis_card`, and the others listed in the file map.
- **Upload:** heal a single `.spec.ts` file of at most 200 KB. It is copied into `workspace/specs/uploads/`, and the original is never modified.
- **Max attempts:** between 1 and 5, default 3.
- **Demo:** Demo runs are labelled everywhere: the header pill, the result header, and the provenance in the diagnosis card.
- **Sample site URL:** the sample spec's `{{BASE_URL}}` is built from the server's bind address (`http://127.0.0.1:<port>/sample-site/`), never from the request's `Host` header.
- **Code rules:**
  - Paths come from `workbench.config`.
  - New data shapes are Pydantic models in `workbench/models/`.
  - Subprocesses use argument lists.
  - Unit tests make no network or browser calls: routes are tested through `TestClient` with fake `Services`.
- **Commits:** Conventional Commits, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. The agent rule is to use your own model's attribution line.
- **Docs timing (plan decision):** `AGENTS.md`, `ROADMAP.md` and `CHANGELOG.md` are updated in Task 11.
- **Figma (spec §5.3):**
  - **Four changes:**
    - the popover footnote reads "Saved on this machine"
    - the sample card shows two samples
    - a new "Stopped: likely app bug" state
    - a "Re-run video" tab
  - **Templates first:** the templates implement all four.
  - **Figma file:** it is updated in Task 12 when the Figma MCP quota allows.
  - **After this phase:** the templates are the source of truth.

## Review Focus

1. **A reload or a second tab during a run.** Expected: the page shows the live run, rebuilt from the start of its events, and a second start is refused with a "A run is already in progress" notice, never a parallel run or a 500. Pinned by `test_heal_page_resumes_the_active_run` and `test_second_start_is_refused_with_409` (Task 7).
2. **An upload that is not a usable spec:** a wrong extension, more than 200 KB, an empty file, non-UTF-8 text, or a path-like name such as `../../evil.spec.ts`. Expected: an inline error, and nothing written outside `workspace/specs/uploads/`. Pinned by `test_bad_uploads_are_rejected_inline` and `test_upload_name_cannot_escape_the_uploads_folder` (Task 7).
3. **A forged report id, or a report whose `video_path` points outside `workspace/runs/`.** Expected: `404`, never an arbitrary file. Pinned by `test_downloads_reject_forged_ids` and `test_video_outside_the_runs_folder_is_not_served` (Task 9).
4. **The browser tab closing in the middle of a stream.** Expected: the run continues, its report is saved, and the next page load shows the result. Pinned by `test_run_finishes_after_the_stream_is_dropped` (Task 6).
5. **The model server going down between page load and the run.** Expected: the run ends with the model's error message shown on the result page (status `error`, "Model unreachable" heading), not a 500; the next page load shows the pill as not connected. Pinned by `test_model_failure_result_says_model_unreachable` (Task 8) and `test_pill_shows_not_connected_when_the_server_is_down` (Task 5).

## Plan decisions

- **Routes split by area (spec §6.1 deviation):** routes live in `src/workbench/web/routes/` (`model.py`, `runs.py`, `heal.py`, `reports.py`, `generate.py`), and `app.py` composes them. §6.1 puts the routes in `app.py`; splitting them keeps each file to one area.
- **A finished run triggers a full page load of `/reports/{id}`:** the stream's `done` fragment calls `GET /runs/{id}/result`, which answers with an `HX-Redirect`. The sidebar is then re-rendered enabled, the URL is shareable, and a reload shows the same result.
- **The live log is built from events:** it is made from the pipeline's step and attempt events (the runner does not stream Playwright's output). When the diagnose or model step has been active for more than 30 s, the run header adds "the model is still thinking". This is the visible answer to slow thinking models; the model-call timeout stays at 300 s.
- **The model menu saves on "Save":** picking a provider or pressing Retry only tests the connection (`POST /model/test`). "Save" writes `workspace/settings.json` (`POST /model`) and reloads the page. This adds a Save button to the Figma popover.
- **Model view lives with the settings models:** `ModelView`, the pill and menu's view of the model state, goes in `workbench/models/settings.py`, following the "data shapes live in models/" rule.

---

## File map

| Action | Path | Responsibility |
| --- | --- | --- |
| Modify | `pyproject.toml`, `uv.lock` | Web dependencies; `workbench` script |
| Modify | `src/workbench/config.py` | `WEB_DIR`, `TEMPLATES_DIR`, `STATIC_DIR`, `HOST`, `DEFAULT_PORT`, `port()`, `base_url()` |
| Create | `src/workbench/__main__.py` | Launcher: uvicorn on 127.0.0.1, opens the browser |
| Create | `src/workbench/app.py` | `create_app(services, *, port)` |
| Create | `src/workbench/runs.py` | `Run`, `RunRegistry`, `RunInProgress` |
| Create | `src/workbench/web/__init__.py` | Package marker |
| Create | `src/workbench/web/services.py` | `Services`: the collaborators the app calls |
| Create | `src/workbench/web/templating.py` | Jinja environment, filters and globals |
| Create | `src/workbench/web/icons.py` | SVG paths for the `icon()` macro |
| Create | `src/workbench/web/views.py` | Formatting, highlighting, diff rows, status badges, step names |
| Create | `src/workbench/web/model_state.py` | `ModelState`: saved or detected choice, plus its connection |
| Create | `src/workbench/web/sse.py` | `sse_message()`, `RunStream` (events → fragments) |
| Create | `src/workbench/web/uploads.py` | `store_upload()` |
| Create | `src/workbench/web/jobs.py` | `run_generated()` for "Run test" |
| Create | `src/workbench/web/routes/{__init__,model,runs,heal,reports,generate}.py` | Routes |
| Create | `src/workbench/web/templates/base.html`, `heal.html`, `generate.html` | Pages |
| Create | `src/workbench/web/templates/partials/*.html` | Components (see each task) |
| Create | `src/workbench/web/static/css/tokens.css`, `app.css` | Design tokens and components |
| Create | `src/workbench/web/static/fonts/*` | Inter 400/500/600 and JetBrains Mono 400, with licences |
| Create | `src/workbench/web/static/vendor/*` | htmx 2.0.11, htmx-ext-sse 2.2.4, licence |
| Create | `src/workbench/web/static/img/logo.svg` | Logo |
| Modify | `src/workbench/models/settings.py` | `ModelView` |
| Modify | `src/workbench/validation.py` | `MAX_SPEC_BYTES`, `validate_spec_upload()` |
| Create | `tests/unit/report_fixtures.py` | One saved report per result state (tests and the walkthrough) |
| Create | `tests/unit/test_app.py`, `test_web_assets.py`, `test_views.py`, `test_runs.py`, `test_web_model.py`, `test_web_runs.py`, `test_web_heal.py`, `test_web_reports.py`, `test_web_downloads.py`, `test_web_generate.py` | Tests |
| Modify | `AGENTS.md`, `ROADMAP.md`, `CHANGELOG.md` | Guides |

---

### Task 1: Web dependencies, app factory and launcher

**Files:**

- Modify: `pyproject.toml`, `uv.lock`, `src/workbench/config.py`
- Create: `src/workbench/app.py`, `src/workbench/__main__.py`, `src/workbench/web/__init__.py`, `src/workbench/web/services.py`, `src/workbench/web/static/img/logo.svg`, `tests/unit/test_app.py`

**Interfaces:**

- Consumes:
  - `heal()`, `generate()`, `run_test()`, `chromium_installed()` (Phase 2)
  - `build_model()`, `detect_provider()`, `check_connection(provider, base_url)` (Phase 3)
  - `config.SAMPLE_SITE_DIR` (Phase 3)
- Produces:
  - `workbench.config`:
    - `WEB_DIR`, `TEMPLATES_DIR`, `STATIC_DIR`
    - `HOST = "127.0.0.1"`, `PORT_ENV = "WORKBENCH_PORT"`, `DEFAULT_PORT = 7860`
    - `port() -> int`, which raises `ValueError` for a bad value
    - `base_url(port_number: int | None = None) -> str`
  - `workbench.web.services.Services`: a frozen dataclass with the fields `heal`, `generate`, `run_test`, `build_model`, `detect`, `check_connection` and `browsers_ready`
  - `workbench.app.create_app(services: Services | None = None, *, port: int | None = None) -> FastAPI`, with `app.state.services` and `app.state.base_url`
  - `python -m workbench` and `uv run workbench`

- [ ] **Step 1: Add the dependencies**

```bash
uv add "fastapi==0.142.2" "uvicorn==0.54.0" "jinja2==3.1.6" "python-multipart==0.0.32" "pygments==2.21.0"
uv add --group dev "httpx2==2.13.1"
```

Expected: `pyproject.toml` lists the five runtime pins and the dev pin. Starlette's `TestClient` warns about `httpx` unless `httpx2` is installed, so the dev pin keeps test output clean.

Then add to `pyproject.toml`, after the `dependencies` list:

```toml
[project.scripts]
workbench = "workbench.__main__:main"
```

and run `uv sync --group dev`.

- [ ] **Step 2: Write the failing tests**

Create `tests/unit/test_app.py`:

```python
"""The app factory, its static mounts, and the launcher's port setting."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from workbench import config
from workbench.app import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))
    return TestClient(create_app())


def test_health(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_redirects_to_heal(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/heal"


def test_sample_site_is_served_under_a_trailing_slash(client: TestClient) -> None:
    redirect = client.get("/sample-site", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"].endswith("/sample-site/")
    assert "Contact form" in client.get("/sample-site/").text
    assert "Place order" in client.get("/sample-site/checkout.html").text


def test_static_files_are_served(client: TestClient) -> None:
    response = client.get("/static/img/logo.svg")
    assert response.status_code == 200
    assert "svg" in response.headers["content-type"]


def test_base_url_uses_the_bind_address() -> None:
    assert config.base_url(7860) == "http://127.0.0.1:7860"
    assert create_app(port=8123).state.base_url == "http://127.0.0.1:8123"


def test_port_defaults_and_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.PORT_ENV, raising=False)
    assert config.port() == 7860
    monkeypatch.setenv(config.PORT_ENV, " 8123 ")
    assert config.port() == 8123
    for bad in ("abc", "0", "70000"):
        monkeypatch.setenv(config.PORT_ENV, bad)
        with pytest.raises(ValueError, match="WORKBENCH_PORT"):
            config.port()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_app.py -q -o addopts=`
Expected: collection error `No module named 'workbench.app'`.

- [ ] **Step 4: Add the config values**

In `src/workbench/config.py`, after `RECORDINGS_DIR`, add:

```python
WEB_DIR = PACKAGE_DIR / "web"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"

HOST = "127.0.0.1"  # local tool: never listen on other interfaces
PORT_ENV = "WORKBENCH_PORT"
DEFAULT_PORT = 7860


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
```

- [ ] **Step 5: Write the services, the app factory, the logo and the launcher**

Create `src/workbench/web/__init__.py`:

```python
"""The web UI: routes, templates and static assets."""
```

Create `src/workbench/web/services.py`:

```python
"""Everything the web app calls outside itself, in one place tests can replace."""

from collections.abc import Callable
from dataclasses import dataclass

from workbench.environment import chromium_installed
from workbench.generate import generate
from workbench.heal import heal
from workbench.llm import build_model, check_connection, detect_provider
from workbench.llm.chat import ChatModel
from workbench.models.generate import GenerateReport
from workbench.models.heal import HealReport
from workbench.models.settings import ConnectionStatus, ModelSettings
from workbench.models.shared import RunResult
from workbench.runner import run_test


@dataclass(frozen=True)
class Services:
    """The pipelines, model client and checks the routes use."""

    heal: Callable[..., HealReport] = heal
    generate: Callable[..., GenerateReport] = generate
    run_test: Callable[..., RunResult] = run_test
    build_model: Callable[[ModelSettings], ChatModel] = build_model
    detect: Callable[[], ModelSettings | None] = detect_provider
    check_connection: Callable[..., ConnectionStatus] = check_connection
    browsers_ready: Callable[[], bool] = chromium_installed
```

Create `src/workbench/web/static/img/logo.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 26 26"><rect width="26" height="26" rx="6" fill="#18181b"/><path d="M8 13.5l3.2 3.2L18 9.8" fill="none" stroke="#4ade80" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
```

Create `src/workbench/app.py`:

```python
"""The web app factory: tests build it with fake services, the launcher with real ones."""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from workbench import config
from workbench.web.services import Services


def create_app(services: Services | None = None, *, port: int | None = None) -> FastAPI:
    """Build the app; ``port`` only sets the sample-site address the app reports."""
    app = FastAPI(
        title="Playwright Workbench", docs_url=None, redoc_url=None, openapi_url=None
    )
    app.state.services = services or Services()
    app.state.base_url = config.base_url(port)
    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")
    app.mount(
        "/sample-site",
        StaticFiles(directory=config.SAMPLE_SITE_DIR, html=True),
        name="sample-site",
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/")
    def home() -> RedirectResponse:
        return RedirectResponse("/heal", status_code=303)

    return app
```

Create `src/workbench/__main__.py`:

```python
"""Starts the workbench on 127.0.0.1 and opens it in the default browser."""

import logging
import threading
import webbrowser

import uvicorn

from workbench import config
from workbench.app import create_app


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    try:
        port = config.port()
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    url = f"{config.base_url(port)}/"
    print(f"Playwright Workbench is running at {url} (press Ctrl+C to stop)")
    threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(port=port), host=config.HOST, port=port, log_level="warning")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the tests**

Run: `uv run python -m pytest tests/unit/test_app.py -q -o addopts=`
Expected: 6 passed, with no warnings.

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check . && npm run lint`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock src/workbench/config.py src/workbench/app.py src/workbench/__main__.py src/workbench/web tests/unit/test_app.py
git commit -m "feat: add the web app factory, static mounts and launcher" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Design tokens, fonts, htmx and the base layout

**Files:**

- Create:
  - `src/workbench/web/static/css/tokens.css`, `src/workbench/web/static/css/app.css`
  - `src/workbench/web/static/fonts/{inter-400,inter-500,inter-600,jetbrains-mono-400}.woff2`, `LICENSE-inter.txt`, `LICENSE-jetbrains-mono.txt`
  - `src/workbench/web/static/vendor/htmx-2.0.11.min.js`, `htmx-ext-sse-2.2.4.js`, `LICENSE-htmx.txt`
  - `src/workbench/web/icons.py`, `src/workbench/web/templating.py`
  - `src/workbench/web/templates/base.html`, `src/workbench/web/templates/partials/icons.html`
  - `tests/unit/test_web_assets.py`

**Interfaces:**

- Consumes: `config.TEMPLATES_DIR`, `config.STATIC_DIR` (Task 1).
- Produces:
  - `workbench.web.templating.templates`, a `Jinja2Templates` whose env has the global `ICON_PATHS`
  - `workbench.web.icons.ICON_PATHS: dict[str, str]`
  - `base.html` with the blocks `title`, `model`, `sidebar_label`, `sidebar` and `main`, and the context variable `page` (`"heal"` or `"generate"`)
  - the macro `icon(name, size=16, label=None)` in `partials/icons.html`, used as `{% from "partials/icons.html" import icon %}`

- [ ] **Step 1: Download the fonts and htmx**

```bash
S=src/workbench/web/static
mkdir -p $S/fonts $S/vendor $S/css
curl -sfL -o $S/fonts/inter-400.woff2 https://cdn.jsdelivr.net/npm/@fontsource/inter@5.3.0/files/inter-latin-400-normal.woff2
curl -sfL -o $S/fonts/inter-500.woff2 https://cdn.jsdelivr.net/npm/@fontsource/inter@5.3.0/files/inter-latin-500-normal.woff2
curl -sfL -o $S/fonts/inter-600.woff2 https://cdn.jsdelivr.net/npm/@fontsource/inter@5.3.0/files/inter-latin-600-normal.woff2
curl -sfL -o $S/fonts/jetbrains-mono-400.woff2 https://cdn.jsdelivr.net/npm/@fontsource/jetbrains-mono@5.3.0/files/jetbrains-mono-latin-400-normal.woff2
curl -sfL -o $S/fonts/LICENSE-inter.txt https://cdn.jsdelivr.net/npm/@fontsource/inter@5.3.0/LICENSE
curl -sfL -o $S/fonts/LICENSE-jetbrains-mono.txt https://cdn.jsdelivr.net/npm/@fontsource/jetbrains-mono@5.3.0/LICENSE
curl -sfL -o $S/vendor/htmx-2.0.11.min.js https://cdn.jsdelivr.net/npm/htmx.org@2.0.11/dist/htmx.min.js
curl -sfL -o $S/vendor/htmx-ext-sse-2.2.4.js https://cdn.jsdelivr.net/npm/htmx-ext-sse@2.2.4/dist/sse.js
curl -sfL -o $S/vendor/LICENSE-htmx.txt https://cdn.jsdelivr.net/npm/htmx.org@2.0.11/LICENSE
ls -la $S/fonts $S/vendor
```

Expected sizes:

- each font file is about 21–25 KB
- `htmx-2.0.11.min.js` is about 52 KB
- `htmx-ext-sse-2.2.4.js` is about 9 KB

Add `src/workbench/web/static/vendor/` to the `ignores` list in `eslint.config.cjs`, and to `.prettierignore`, so vendored code is not linted or reformatted.

- [ ] **Step 2: Write the failing tests**

Create `tests/unit/test_web_assets.py`:

```python
"""Design tokens match Figma, assets are present, and the base layout is accessible."""

import re

from workbench import config
from workbench.web.templating import templates

# The 30 colour variables in the Figma file (eL5DUZmc85ESpusNSmxDkA).
FIGMA_COLOURS = {
    "accent-primary": "#18181b",
    "text-primary": "#18181b",
    "text-secondary": "#52525b",
    "text-tertiary": "#8a8a93",
    "text-inverse": "#ffffff",
    "bg-canvas": "#f7f7f5",
    "bg-surface": "#ffffff",
    "bg-subtle": "#f1f1ee",
    "border-default": "#e4e4df",
    "border-strong": "#d1d1cb",
    "status-pass": "#15803d",
    "status-pass-bg": "#e7f4eb",
    "status-fail": "#b91c1c",
    "status-fail-bg": "#fbeaea",
    "status-run": "#1d4ed8",
    "status-run-bg": "#e8eefd",
    "status-warn": "#b45309",
    "status-warn-bg": "#fcf1e1",
    "code-bg": "#111113",
    "code-text": "#e4e4e7",
    "code-muted": "#71717a",
    "code-gutter": "#18181b",
    "code-border": "#27272a",
    "code-string": "#a5d6ff",
    "code-keyword": "#ff7b72",
    "code-fn": "#d2a8ff",
    "diff-add-text": "#7ee2a8",
    "diff-add-bg": "#11291d",
    "diff-del-text": "#ffa198",
    "diff-del-bg": "#2e1517",
}
TYPE_STYLES = [
    "title-page",
    "title-section",
    "body",
    "body-small",
    "label",
    "label-caps",
    "mono-code",
    "mono-small",
]


def _css(name: str) -> str:
    return (config.STATIC_DIR / "css" / name).read_text(encoding="utf-8")


def test_tokens_mirror_the_figma_colours_one_to_one() -> None:
    declared = dict(
        re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-f]{6});", _css("tokens.css"))
    )
    assert declared == FIGMA_COLOURS


def test_tokens_define_the_eight_type_styles() -> None:
    tokens = _css("tokens.css")
    for style in TYPE_STYLES:
        assert f"--type-{style}:" in tokens


def test_fonts_are_self_hosted_woff2() -> None:
    for name in ("inter-400", "inter-500", "inter-600", "jetbrains-mono-400"):
        assert (config.STATIC_DIR / "fonts" / f"{name}.woff2").read_bytes()[
            :4
        ] == b"wOF2"
    assert (config.STATIC_DIR / "fonts" / "LICENSE-inter.txt").is_file()
    assert (config.STATIC_DIR / "fonts" / "LICENSE-jetbrains-mono.txt").is_file()


def test_htmx_is_vendored_with_its_version_in_the_name() -> None:
    vendor = config.STATIC_DIR / "vendor"
    assert (vendor / "htmx-2.0.11.min.js").stat().st_size > 40_000
    assert "sse-connect" in (vendor / "htmx-ext-sse-2.2.4.js").read_text(
        encoding="utf-8"
    )


def test_base_layout_has_landmarks_and_marks_the_current_page() -> None:
    html = templates.get_template("base.html").render(page="generate")
    assert '<header class="header">' in html
    assert '<nav class="nav" aria-label="Pages">' in html
    assert '<main class="main" id="main"' in html
    assert "<aside" in html
    assert '<a href="/generate" aria-current="page">Generate</a>' in html
    assert 'aria-live="polite"' in html
    assert "/static/vendor/htmx-2.0.11.min.js" in html
    assert "/static/vendor/htmx-ext-sse-2.2.4.js" in html


def test_icon_macro_renders_decorative_and_labelled_icons() -> None:
    module = templates.env.get_template("partials/icons.html").module
    decorative = str(module.icon("check"))  # type: ignore[attr-defined]
    labelled = str(module.icon("x", 20, "Failed"))  # type: ignore[attr-defined]
    assert 'aria-hidden="true"' in decorative
    assert 'role="img" aria-label="Failed"' in labelled
    assert 'width="20"' in labelled
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_web_assets.py -q -o addopts=`
Expected: collection error `No module named 'workbench.web.templating'`.

- [ ] **Step 4: Write the tokens**

Create `src/workbench/web/static/css/tokens.css`:

```css
/* Design tokens: one custom property per Figma variable (bg/canvas → --bg-canvas).
   Figma file eL5DUZmc85ESpusNSmxDkA. Change a value in Figma first, then here. */

@font-face {
  font-family: 'Inter';
  font-weight: 400;
  font-display: swap;
  src: url('../fonts/inter-400.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  font-weight: 500;
  font-display: swap;
  src: url('../fonts/inter-500.woff2') format('woff2');
}
@font-face {
  font-family: 'Inter';
  font-weight: 600;
  font-display: swap;
  src: url('../fonts/inter-600.woff2') format('woff2');
}
@font-face {
  font-family: 'JetBrains Mono';
  font-weight: 400;
  font-display: swap;
  src: url('../fonts/jetbrains-mono-400.woff2') format('woff2');
}

:root {
  /* Colours (30) */
  --accent-primary: #18181b;
  --text-primary: #18181b;
  --text-secondary: #52525b;
  --text-tertiary: #8a8a93;
  --text-inverse: #ffffff;
  --bg-canvas: #f7f7f5;
  --bg-surface: #ffffff;
  --bg-subtle: #f1f1ee;
  --border-default: #e4e4df;
  --border-strong: #d1d1cb;
  --status-pass: #15803d;
  --status-pass-bg: #e7f4eb;
  --status-fail: #b91c1c;
  --status-fail-bg: #fbeaea;
  --status-run: #1d4ed8;
  --status-run-bg: #e8eefd;
  --status-warn: #b45309;
  --status-warn-bg: #fcf1e1;
  --code-bg: #111113;
  --code-text: #e4e4e7;
  --code-muted: #71717a;
  --code-gutter: #18181b;
  --code-border: #27272a;
  --code-string: #a5d6ff;
  --code-keyword: #ff7b72;
  --code-fn: #d2a8ff;
  --diff-add-text: #7ee2a8;
  --diff-add-bg: #11291d;
  --diff-del-text: #ffa198;
  --diff-del-bg: #2e1517;

  /* Type styles (8). Figma letter spacing is in percent: -1% = -0.01em. */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
  --type-title-page: 600 20px/28px var(--font-sans);
  --tracking-title-page: -0.01em;
  --type-title-section: 600 15px/22px var(--font-sans);
  --tracking-title-section: -0.005em;
  --type-body: 400 14px/20px var(--font-sans);
  --type-body-small: 400 13px/18px var(--font-sans);
  --type-label: 500 13px/18px var(--font-sans);
  --type-label-caps: 600 11px/16px var(--font-sans);
  --tracking-label-caps: 0.06em;
  --type-mono-code: 400 13px/21px var(--font-mono);
  --type-mono-small: 400 12px/18px var(--font-mono);
}
```

- [ ] **Step 5: Write the component styles**

Create `src/workbench/web/static/css/app.css`:

```css
/* Layout and components. Class names are BEM-style: .block, .block__part, .block--variant. */

*,
*::before,
*::after {
  box-sizing: border-box;
}
body {
  margin: 0;
  min-width: 1280px;
  background: var(--bg-canvas);
  color: var(--text-primary);
  font: var(--type-body);
  -webkit-font-smoothing: antialiased;
}
a {
  color: inherit;
}
h1,
h2,
h3,
p {
  margin: 0;
}
:focus-visible {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}
[hidden] {
  display: none !important;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
.skip-link {
  position: absolute;
  left: 16px;
  top: -48px;
  z-index: 20;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--bg-surface);
}
.skip-link:focus {
  top: 8px;
}
.icon {
  flex: none;
}
.spin {
  animation: spin 0.9s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .spin {
    animation: none;
  }
}

/* Typography */
.t-page {
  font: var(--type-title-page);
  letter-spacing: var(--tracking-title-page);
}
.t-section {
  font: var(--type-title-section);
  letter-spacing: var(--tracking-title-section);
}
.t-caps {
  font: var(--type-label-caps);
  letter-spacing: var(--tracking-label-caps);
  text-transform: uppercase;
  color: var(--text-tertiary);
}
.t-small {
  font: var(--type-body-small);
}
.t-label {
  font: var(--type-label);
}
.t-mono {
  font: var(--type-mono-small);
}
.t-muted {
  color: var(--text-secondary);
}
.t-faint {
  color: var(--text-tertiary);
}

/* Header */
.header {
  display: flex;
  align-items: center;
  gap: 32px;
  height: 56px;
  padding: 0 24px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  font: var(--type-title-section);
  letter-spacing: var(--tracking-title-section);
}
.nav {
  display: flex;
  gap: 2px;
  padding: 3px;
  border-radius: 8px;
  background: var(--bg-subtle);
}
.nav a {
  padding: 5px 14px;
  border-radius: 6px;
  text-decoration: none;
  font: var(--type-label);
  color: var(--text-secondary);
}
.nav a[aria-current='page'] {
  background: var(--bg-surface);
  color: var(--text-primary);
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.06);
}
.header__model {
  margin-left: auto;
}

/* Layout */
.layout {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  min-height: calc(100vh - 56px);
}
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 32px 24px 24px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border-default);
}
.sidebar__foot {
  margin-top: auto;
}
.main {
  min-width: 0;
  padding: 28px 32px;
  outline: none;
}
.stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stack--tight {
  gap: 6px;
}
.stack--loose {
  gap: 20px;
}
.row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.result-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 20px;
  align-items: start;
}
.run-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 20px;
  align-items: start;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 34px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: 8px;
  font: var(--type-label);
  white-space: nowrap;
  text-decoration: none;
  cursor: pointer;
}
.btn--primary {
  background: var(--accent-primary);
  color: var(--text-inverse);
}
.btn--secondary {
  background: var(--bg-surface);
  color: var(--text-primary);
  border-color: var(--border-strong);
}
.btn--ghost {
  background: transparent;
  color: var(--text-secondary);
}
.btn--ghost:hover {
  background: var(--bg-subtle);
}
.btn--block {
  width: 100%;
}
.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn--primary:disabled {
  background: var(--text-tertiary);
  opacity: 1;
}

/* Status pills */
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font: var(--type-label);
  white-space: nowrap;
}
.pill::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.pill--pass {
  color: var(--status-pass);
  background: var(--status-pass-bg);
}
.pill--fail {
  color: var(--status-fail);
  background: var(--status-fail-bg);
}
.pill--run {
  color: var(--status-run);
  background: var(--status-run-bg);
}
.pill--warn {
  color: var(--status-warn);
  background: var(--status-warn-bg);
}
.pill--neutral {
  color: var(--text-secondary);
  background: var(--bg-subtle);
}

/* Header model pill and its popover */
.model-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 30px;
  padding: 0 14px;
  border: 1px solid var(--border-default);
  border-radius: 999px;
  background: var(--bg-surface);
  color: var(--text-primary);
  font: var(--type-mono-small);
  cursor: pointer;
}
.model-pill::before {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--status-pass);
}
.model-pill__provider {
  font: var(--type-body-small);
  color: var(--text-tertiary);
}
.model-pill--demo {
  border-color: var(--status-warn);
}
.model-pill--demo::before {
  background: var(--status-warn);
}
.model-pill--off {
  border-color: var(--status-fail);
}
.model-pill--off::before {
  background: var(--status-fail);
}
.popover {
  position: fixed;
  inset: 64px 24px auto auto;
  width: 360px;
  margin: 0;
  padding: 16px;
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: var(--bg-surface);
  box-shadow: 0 12px 32px rgb(0 0 0 / 0.12);
}
.seg {
  display: flex;
  padding: 3px;
  border-radius: 8px;
  background: var(--bg-subtle);
}
.seg label {
  flex: 1;
  padding: 6px;
  border-radius: 6px;
  text-align: center;
  font: var(--type-label);
  color: var(--text-secondary);
  cursor: pointer;
}
.seg input {
  position: absolute;
  opacity: 0;
}
.seg label:has(input:checked) {
  background: var(--bg-surface);
  color: var(--text-primary);
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.06);
}
.seg label:has(input:focus-visible) {
  outline: 2px solid var(--accent-primary);
}
.popover__foot {
  padding-top: 12px;
  border-top: 1px solid var(--border-default);
  font: var(--type-body-small);
  color: var(--text-tertiary);
}

/* Cards */
.card {
  padding: 20px;
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: var(--bg-surface);
}
.card--subtle {
  background: var(--bg-subtle);
}
.card--sample {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  background: var(--bg-canvas);
}
.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  font: var(--type-body-small);
  color: var(--text-tertiary);
}
.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border-default);
}

/* Result header */
.result-head {
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 36px;
  margin-bottom: 20px;
}
.result-head__name {
  font: var(--type-title-page);
  letter-spacing: var(--tracking-title-page);
}
.result-head__meta {
  color: var(--text-tertiary);
}
.result-head__actions {
  display: flex;
  gap: 10px;
  margin-left: auto;
}

/* Steps (live run) */
.steps {
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: var(--bg-surface);
  overflow: hidden;
}
.steps > li + li {
  border-top: 1px solid var(--border-default);
}
.step {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  gap: 14px;
  align-items: start;
  padding: 14px 16px;
}
.step__icon {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
}
.step__title {
  font: var(--type-label);
}
.step__detail {
  font: var(--type-body-small);
  color: var(--text-secondary);
  overflow-wrap: anywhere;
}
.step__time {
  font: var(--type-mono-small);
  color: var(--text-tertiary);
}
.step--done .step__icon {
  background: var(--status-pass-bg);
  color: var(--status-pass);
}
.step--active .step__icon {
  background: var(--status-run-bg);
  color: var(--status-run);
}
.step--failed .step__icon {
  background: var(--status-fail-bg);
  color: var(--status-fail);
}
.step--pending .step__icon,
.step--skipped .step__icon {
  color: var(--border-strong);
}
.step--pending :is(.step__title, .step__detail),
.step--skipped :is(.step__title, .step__detail) {
  color: var(--text-tertiary);
}

/* Step summary bar (results) */
.stepbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  margin-bottom: 20px;
  padding: 12px 16px;
  border: 1px solid var(--border-default);
  border-radius: 12px;
  background: var(--bg-surface);
}
.stepbar__item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font: var(--type-label);
}
.stepbar__item--done .icon {
  color: var(--status-pass);
}
.stepbar__item--failed .icon {
  color: var(--status-fail);
}
.stepbar__item--skipped {
  color: var(--text-tertiary);
}

/* Code, diff and log panes */
.code {
  overflow: hidden;
  border: 1px solid var(--code-border);
  border-radius: 12px;
  background: var(--code-bg);
  color: var(--code-text);
}
.code__head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--code-border);
  font: var(--type-mono-small);
}
.code__head-meta {
  margin-left: auto;
  color: var(--code-muted);
}
.code__body {
  max-height: 640px;
  margin: 0;
  padding: 12px 0;
  overflow: auto;
  font: var(--type-mono-code);
}
.code__line {
  display: grid;
  grid-template-columns: 44px 1fr;
  padding-right: 16px;
  white-space: pre;
}
.code__line--diff {
  grid-template-columns: 36px 36px 20px 1fr;
}
.code__num {
  padding-right: 12px;
  text-align: right;
  color: var(--code-muted);
  user-select: none;
}
.code__mark {
  color: var(--code-muted);
  user-select: none;
}
.code__line--add {
  background: var(--diff-add-bg);
}
.code__line--add .code__mark {
  color: var(--diff-add-text);
}
.code__line--del {
  background: var(--diff-del-bg);
}
.code__line--del .code__mark {
  color: var(--diff-del-text);
}
.tok-kw {
  color: var(--code-keyword);
}
.tok-str {
  color: var(--code-string);
}
.tok-fn {
  color: var(--code-fn);
}
.tok-mut {
  color: var(--code-muted);
}
.diffstat--add {
  color: var(--diff-add-text);
}
.diffstat--del {
  color: var(--diff-del-text);
}
.log__body {
  min-height: 420px;
  max-height: 640px;
  margin: 0;
  padding: 12px 16px;
  overflow: auto;
  font: var(--type-mono-small);
  line-height: 21px;
  white-space: pre-wrap;
}
.log__line--step {
  color: var(--code-fn);
}
.log__line--fail {
  color: var(--diff-del-text);
}
.log__line--muted {
  color: var(--code-muted);
}

/* Tabs */
.tabs {
  display: flex;
  gap: 20px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--border-default);
}
.tab {
  margin-bottom: -1px;
  padding: 8px 0;
  border-bottom: 2px solid transparent;
  font: var(--type-body);
  color: var(--text-secondary);
  text-decoration: none;
}
.tab[aria-selected='true'] {
  border-bottom-color: var(--accent-primary);
  color: var(--text-primary);
  font-weight: 500;
}

/* Attempt chips and cards */
.chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 32px;
  padding: 0 14px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-surface);
  font: var(--type-label);
  color: var(--text-primary);
  text-decoration: none;
}
.chip[aria-current='true'] {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 1px var(--accent-primary);
}
.chip__note {
  font: var(--type-body-small);
  color: var(--text-tertiary);
}
.chip--example {
  height: 28px;
  border-radius: 999px;
  font: var(--type-body-small);
  color: var(--text-secondary);
}
.attempt {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  border: 1px solid var(--border-default);
  border-radius: 10px;
  background: var(--bg-surface);
}
.attempt__head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.attempt__head .pill {
  margin-left: auto;
}
.tag {
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--bg-subtle);
  font: var(--type-body-small);
  color: var(--text-secondary);
}
.snippet {
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--bg-subtle);
  font: var(--type-mono-small);
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

/* Diagnosis and context cards */
.side-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 100%;
}
.kv {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin: 0;
  font: var(--type-body-small);
}
.kv dt {
  color: var(--text-tertiary);
}
.kv dd {
  margin: 0;
  font: var(--type-mono-small);
  text-align: right;
}
.kv--plain dt {
  color: var(--text-secondary);
}
.meter {
  display: flex;
  align-items: center;
  gap: 10px;
}
.meter__bar {
  width: 100px;
  height: 4px;
  overflow: hidden;
  border-radius: 2px;
  background: var(--bg-subtle);
}
.meter__fill {
  height: 100%;
  background: var(--status-pass);
}
.code-badge {
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--bg-subtle);
  font: var(--type-mono-small);
}
.evidence {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.evidence li {
  padding: 8px 10px;
  border-radius: 6px;
  background: var(--bg-subtle);
  font: var(--type-mono-small);
  overflow-wrap: anywhere;
}
.reasons {
  margin: 0;
  padding-left: 20px;
  font: var(--type-body-small);
}
.reasons li + li {
  margin-top: 6px;
}
.meta-foot {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid var(--border-default);
}
.ok-line,
.fail-line {
  display: flex;
  align-items: center;
  gap: 6px;
  font: var(--type-body-small);
}
.ok-line {
  color: var(--status-pass);
}
.fail-line {
  color: var(--status-fail);
}

/* Banners and notices */
.banner {
  display: grid;
  grid-template-columns: 20px 1fr;
  gap: 10px;
  margin-bottom: 16px;
  padding: 12px 14px;
  border-radius: 10px;
  font: var(--type-body-small);
}
.banner__title {
  font: var(--type-label);
}
.banner--fail {
  background: var(--status-fail-bg);
}
.banner--fail :is(.banner__title, .icon) {
  color: var(--status-fail);
}
.banner--warn {
  background: var(--status-warn-bg);
}
.banner--warn :is(.banner__title, .icon) {
  color: var(--status-warn);
}
.banner--info {
  background: var(--bg-subtle);
}
.cmd {
  display: inline-block;
  margin-top: 6px;
  padding: 4px 8px;
  border-radius: 6px;
  background: var(--code-bg);
  color: var(--code-text);
  font: var(--type-mono-small);
}
.notice {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
}
.notice:empty {
  display: none;
}

/* Forms */
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field__label {
  font: var(--type-label);
}
.field__hint {
  font: var(--type-body-small);
  color: var(--text-tertiary);
}
.field__error {
  font: var(--type-body-small);
  color: var(--status-fail);
}
.input,
.textarea,
.select {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  background: var(--bg-surface);
  color: var(--text-primary);
  font: var(--type-body);
}
.input--mono {
  font: var(--type-mono-small);
}
.textarea {
  min-height: 96px;
  resize: vertical;
}
[aria-invalid='true'] {
  border-color: var(--status-fail);
}
.check {
  display: flex;
  align-items: center;
  gap: 10px;
}
.check input {
  width: 16px;
  height: 16px;
  accent-color: var(--accent-primary);
}
.stepper {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
}
.stepper button {
  width: 28px;
  border: 0;
  background: var(--bg-surface);
  cursor: pointer;
}
.stepper input {
  width: 36px;
  border: 0;
  background: var(--bg-subtle);
  text-align: center;
  font: var(--type-mono-small);
  appearance: textfield;
}
.stepper input::-webkit-inner-spin-button {
  appearance: none;
}
.dropzone {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 24px;
  border: 1px dashed var(--border-strong);
  border-radius: 12px;
  text-align: center;
  font: var(--type-body-small);
  color: var(--text-tertiary);
}
.dropzone strong {
  font: var(--type-label);
  color: var(--text-primary);
}
.dropzone input[type='file'] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}
.dropzone:focus-within {
  outline: 2px solid var(--accent-primary);
  outline-offset: 2px;
}
.dropzone--error {
  border-color: var(--status-fail);
  background: var(--status-fail-bg);
  color: var(--status-fail);
}

/* Empty and centred states */
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 56px 24px;
  text-align: center;
  color: var(--text-secondary);
}
.empty__icon,
.icon-tile {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--bg-subtle);
}
.icon-tile--fail {
  background: var(--status-fail-bg);
  color: var(--status-fail);
}
.icon-tile--warn {
  background: var(--status-warn-bg);
  color: var(--status-warn);
}
.center-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 600px;
  margin: 96px auto 0;
}

/* Video */
.video {
  width: 100%;
  border-radius: 12px;
  background: #000;
}
```

- [ ] **Step 6: Write the icons, the templating module and the base layout**

Create `src/workbench/web/icons.py`:

```python
"""SVG paths for the icon() macro: 24×24 viewBox, stroked with currentColor."""

ICON_PATHS: dict[str, str] = {
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    "upload": '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M5 20h14"/>',
    "download": '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M5 20h14"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    "warn": '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    "plug": '<path d="M9 3v5M15 3v5M7 8h10v3a5 5 0 0 1-10 0zM12 16v5"/>',
    "play": '<path d="M8 5v14l11-7z"/>',
    "refresh": '<path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"/>',
    "chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "chevron-right": '<path d="M9 6l6 6-6 6"/>',
    "code": '<path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/>',
    "copy": '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
    "spinner": '<path class="spin" style="transform-origin:12px 12px" d="M21 12a9 9 0 1 1-9-9"/>',
    "circle-dashed": '<circle cx="12" cy="12" r="9" stroke-dasharray="3 3"/>',
    "video": '<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10l5-3v10l-5-3"/>',
}
```

Create `src/workbench/web/templating.py`:

```python
"""The Jinja environment every page and fragment is rendered with."""

from fastapi.templating import Jinja2Templates

from workbench.config import TEMPLATES_DIR
from workbench.web.icons import ICON_PATHS

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["ICON_PATHS"] = ICON_PATHS
```

Create `src/workbench/web/templates/partials/icons.html`:

```jinja
{% macro icon(name, size=16, label=None) -%}
<svg class="icon icon--{{ name }}" width="{{ size }}" height="{{ size }}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" {% if label %}role="img" aria-label="{{ label }}"{% else %}aria-hidden="true"{% endif %}>{{ ICON_PATHS[name] | safe }}</svg>
{%- endmacro %}
```

Create `src/workbench/web/templates/base.html`. The `htmx-config` meta lets 409 and 422 responses swap, so refusals and input errors render inline. Other 4xx/5xx responses do not swap.

```jinja
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=1280">
  <meta name="htmx-config" content='{"responseHandling":[{"code":"204","swap":false},{"code":"[23]..","swap":true},{"code":"409","swap":true},{"code":"422","swap":true},{"code":"[45]..","swap":false,"error":true}]}'>
  <title>{% block title %}Playwright Workbench{% endblock %}</title>
  <link rel="icon" href="/static/img/logo.svg">
  <link rel="stylesheet" href="/static/css/tokens.css">
  <link rel="stylesheet" href="/static/css/app.css">
  <script src="/static/vendor/htmx-2.0.11.min.js" defer></script>
  <script src="/static/vendor/htmx-ext-sse-2.2.4.js" defer></script>
</head>
<body hx-ext="sse">
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="header">
    <a class="brand" href="/heal"><img src="/static/img/logo.svg" alt="" width="26" height="26"><span>Playwright Workbench</span></a>
    <nav class="nav" aria-label="Pages">
      <a href="/heal"{% if page == "heal" %} aria-current="page"{% endif %}>Heal</a>
      <a href="/generate"{% if page == "generate" %} aria-current="page"{% endif %}>Generate</a>
    </nav>
    <div class="header__model">{% block model %}{% endblock %}</div>
  </header>
  <div class="layout">
    <aside class="sidebar" aria-label="{% block sidebar_label %}Controls{% endblock %}">{% block sidebar %}{% endblock %}</aside>
    <main class="main" id="main" tabindex="-1">{% block main %}{% endblock %}</main>
  </div>
  <div id="notice" class="notice" role="status" aria-live="polite"></div>
</body>
</html>
```

- [ ] **Step 7: Run the tests**

Run: `uv run python -m pytest tests/unit/test_web_assets.py -q -o addopts=`
Expected: 6 passed.

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check . && npm run lint && npm run type-check`
Expected: all pass. Prettier may reformat `app.css` and `tokens.css` through the Husky hook; that is fine.

- [ ] **Step 8: Commit**

```bash
git add src/workbench/web eslint.config.cjs .prettierignore tests/unit/test_web_assets.py
git commit -m "feat: add the design tokens, fonts, htmx and the base layout" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: View helpers: times, sizes, highlighted code, diffs and badges

**Files:**

- Create: `src/workbench/models/web.py`, `src/workbench/web/views.py`, `tests/unit/test_views.py`
- Modify: `src/workbench/web/templating.py`

**Interfaces:**

- Consumes:
  - `HealStatus`, `AttemptOutcome`, `REPAIR_STRATEGY_LABELS` (`workbench.models.heal`)
  - `GenerateStatus` (`workbench.models.generate`)
  - `StepName` (`workbench.models.events`)
- Produces:
  - `workbench.models.web`, all frozen Pydantic models:
    - `BadgeVariant = Literal["pass", "fail", "run", "warn", "neutral"]`
    - `Badge(variant, label)`
    - `OutcomeBadge(variant, label, title)`
    - `StepInfo(name: StepName, title, description)`
    - `DiffRow(kind: Literal["same", "add", "del"], old_no: int | None, new_no: int | None, html: str)`
  - `workbench.web.views`:
    - `format_duration(ms: int | None) -> str`
    - `format_size(chars: int) -> str`
    - `highlight_lines(code: str) -> list[str]`, each line HTML-escaped with `tok-kw`, `tok-str`, `tok-fn` and `tok-mut` spans
    - `diff_rows(old: str, new: str) -> list[DiffRow]`
    - `diff_counts(rows) -> tuple[int, int]`, giving (added, removed)
    - `locators_in(code: str) -> list[str]`
    - `HEAL_STEPS`, `GENERATE_STEPS: tuple[StepInfo, ...]`, `STEP_INFO: dict[str, StepInfo]`
    - `HEAL_BADGES`, `GENERATE_BADGES: dict[str, Badge]`, `OUTCOME_BADGES: dict[str, OutcomeBadge]`
  - Template filters `duration` and `size`, and the globals `views`, `HEAL_BADGES`, `GENERATE_BADGES`, `OUTCOME_BADGES`, `STRATEGY_LABELS`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_views.py`:

```python
"""Formatting, highlighting and status presentation for the templates."""

from typing import get_args

from workbench.models.events import StepName
from workbench.models.generate import GenerateStatus
from workbench.models.heal import AttemptOutcome, HealStatus
from workbench.web import views


def test_durations_read_like_the_design() -> None:
    assert views.format_duration(2400) == "2.4s"
    assert views.format_duration(300) == "0.3s"
    assert views.format_duration(65_000) == "1m 05s"
    assert views.format_duration(None) == "–"


def test_sizes_are_in_kilobytes() -> None:
    assert views.format_size(2150) == "2.1 KB"
    assert views.format_size(0) == "0.0 KB"


def test_typescript_is_highlighted_and_escaped() -> None:
    lines = views.highlight_lines(
        'import { test } from "@playwright/test";\n'
        "\n"
        'test("a <b>", async ({ page }) => {\n'
        "  await page.goto(`http://x/`); // go\n"
        "});\n"
    )
    assert len(lines) == 5
    assert lines[0].startswith('<span class="tok-kw">import</span>')
    assert '<span class="tok-str">"@playwright/test"</span>' in lines[0]
    assert lines[1] == ""
    assert '<span class="tok-fn">test</span>' in lines[2]
    assert "&lt;b&gt;" in lines[2] and "<b>" not in lines[2]
    assert '<span class="tok-fn">goto</span>' in lines[3]
    assert '<span class="tok-mut">// go</span>' in lines[3]


def test_leading_blank_lines_keep_their_numbers() -> None:
    assert views.highlight_lines("\na\n") == ["", "a"]
    assert views.highlight_lines("") == []


def test_diff_rows_number_both_sides() -> None:
    rows = views.diff_rows("a\nb\nc\n", "a\nB\nc\n")
    assert [(r.kind, r.old_no, r.new_no) for r in rows] == [
        ("same", 1, 1),
        ("del", 2, None),
        ("add", None, 2),
        ("same", 3, 3),
    ]
    assert views.diff_counts(rows) == (1, 1)


def test_locators_are_listed_once_in_order() -> None:
    code = (
        "await page.getByLabel('Name').fill('Ada');\n"
        "await page.getByRole('button', { name: 'Submit' }).click();\n"
        "await page.getByLabel('Name').clear();\n"
        "await page.locator('#x').click();\n"
    )
    assert views.locators_in(code) == [
        "getByLabel('Name')",
        "getByRole('button', { name: 'Submit' })",
        "locator('#x')",
    ]


def test_every_status_and_outcome_has_a_badge() -> None:
    assert set(get_args(HealStatus)) == set(views.HEAL_BADGES)
    assert set(get_args(GenerateStatus)) == set(views.GENERATE_BADGES)
    assert set(get_args(AttemptOutcome)) == set(views.OUTCOME_BADGES)
    assert views.HEAL_BADGES["app_defect_suspected"].label == "Likely app bug"
    assert views.OUTCOME_BADGES["not_applied"].title == "Fix not applied"


def test_every_step_has_a_title() -> None:
    assert set(get_args(StepName)) == set(views.STEP_INFO)
    assert [s.name for s in views.HEAL_STEPS] == [
        "run",
        "evidence",
        "diagnose",
        "repair",
        "verify",
    ]
    assert [s.name for s in views.GENERATE_STEPS] == ["context", "model", "execute"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_views.py -q -o addopts=`
Expected: collection error `cannot import name 'views'`.

- [ ] **Step 3: Write the view models**

Create `src/workbench/models/web.py`:

```python
"""What the web templates show, derived from reports and events."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from workbench.models.events import StepName

BadgeVariant = Literal["pass", "fail", "run", "warn", "neutral"]


class Badge(BaseModel):
    """A status pill: its colour variant and its text."""

    model_config = ConfigDict(frozen=True)

    variant: BadgeVariant
    label: str


class OutcomeBadge(Badge):
    """An attempt's pill plus the title its card shows."""

    title: str


class StepInfo(BaseModel):
    """A pipeline step as the progress list names it."""

    model_config = ConfigDict(frozen=True)

    name: StepName
    title: str
    description: str


class DiffRow(BaseModel):
    """One line of a two-column diff, already highlighted."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["same", "add", "del"]
    old_no: int | None
    new_no: int | None
    html: str
```

- [ ] **Step 4: Write the helpers**

Create `src/workbench/web/views.py`:

```python
"""Turns report data into what the templates show: times, sizes, code and badges."""

import difflib
import re
from html import escape

from pygments.lexers import TypeScriptLexer
from pygments.token import Comment, Keyword, Name, String, _TokenType

from workbench.models.web import Badge, DiffRow, OutcomeBadge, StepInfo

HEAL_STEPS: tuple[StepInfo, ...] = (
    StepInfo(name="run", title="Run the test", description="npx playwright test"),
    StepInfo(
        name="evidence",
        title="Collect evidence",
        description="Error context, screenshot and page snapshot",
    ),
    StepInfo(name="diagnose", title="Diagnose", description="Ask the model what broke"),
    StepInfo(
        name="repair", title="Repair", description="Apply the fix to the syntax tree"
    ),
    StepInfo(name="verify", title="Verify", description="Re-run the test"),
)
GENERATE_STEPS: tuple[StepInfo, ...] = (
    StepInfo(
        name="context",
        title="Load page context",
        description="Accessibility snapshot and locator candidates",
    ),
    StepInfo(name="model", title="Ask the model", description="Write the spec"),
    StepInfo(name="execute", title="Run the test", description="Runs after generation"),
)
STEP_INFO: dict[str, StepInfo] = {
    step.name: step for step in (*HEAL_STEPS, *GENERATE_STEPS)
}

HEAL_BADGES: dict[str, Badge] = {
    "healed": Badge(variant="pass", label="Healed"),
    "not_healed": Badge(variant="fail", label="Not healed"),
    "app_defect_suspected": Badge(variant="warn", label="Likely app bug"),
    "nothing_to_heal": Badge(variant="pass", label="Nothing to heal"),
    "cancelled": Badge(variant="neutral", label="Cancelled"),
    "error": Badge(variant="fail", label="Error"),
}
GENERATE_BADGES: dict[str, Badge] = {
    "passed": Badge(variant="pass", label="Passed"),
    "failed": Badge(variant="fail", label="Run failed"),
    "not_run": Badge(variant="neutral", label="Not run"),
    "cancelled": Badge(variant="neutral", label="Cancelled"),
    "error": Badge(variant="fail", label="Error"),
}
OUTCOME_BADGES: dict[str, OutcomeBadge] = {
    "healed": OutcomeBadge(variant="pass", label="Passed", title="Healed"),
    "rerun_failed": OutcomeBadge(variant="fail", label="Failed", title="Re-run failed"),
    "not_applied": OutcomeBadge(
        variant="warn", label="Not applied", title="Fix not applied"
    ),
    "invalid_reply": OutcomeBadge(
        variant="warn", label="Invalid reply", title="Invalid model reply"
    ),
    "app_defect": OutcomeBadge(variant="warn", label="Stopped", title="Likely app bug"),
    "cancelled": OutcomeBadge(variant="neutral", label="Cancelled", title="Cancelled"),
}

_LOCATOR = re.compile(r"\b(?:getBy[A-Z]\w*|locator)\((?:[^()]|\([^()]*\))*\)")
Token = tuple[_TokenType, str]


def format_duration(ms: int | None) -> str:
    """``2.4s`` under a minute, ``1m 05s`` above; ``–`` when unknown."""
    if ms is None:
        return "–"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rest = divmod(round(seconds), 60)
    return f"{minutes}m {rest:02d}s"


def format_size(chars: int) -> str:
    """A prompt section's size in kilobytes."""
    return f"{chars / 1024:.1f} KB"


def _neighbour(tokens: list[Token], index: int, step: int) -> str:
    index += step
    while 0 <= index < len(tokens):
        value = tokens[index][1]
        if value.strip():
            return value
        index += step
    return ""


def _css_class(tokens: list[Token], index: int) -> str:
    ttype = tokens[index][0]
    if ttype in Comment:
        return "mut"
    if ttype in String:
        return "str"
    # Pygments tags some method names (goto) as reserved words: a call wins.
    if _neighbour(tokens, index, 1).startswith("(") and (
        ttype in Name or _neighbour(tokens, index, -1) == "."
    ):
        return "fn"
    if ttype in Keyword:
        return "kw"
    return ""


def highlight_lines(code: str) -> list[str]:
    """One escaped HTML string per source line, with ``tok-*`` spans."""
    if not code:
        return []
    tokens: list[Token] = list(TypeScriptLexer(stripnl=False).get_tokens(code))
    lines: list[list[str]] = [[]]
    for index, (_, value) in enumerate(tokens):
        css = _css_class(tokens, index)
        for position, part in enumerate(value.split("\n")):
            if position:
                lines.append([])
            if part:
                text = escape(part, quote=False)
                lines[-1].append(
                    f'<span class="tok-{css}">{text}</span>' if css else text
                )
    return ["".join(parts) for parts in lines[: len(code.splitlines())]]


def diff_rows(old: str, new: str) -> list[DiffRow]:
    """The whole file with removed and added lines in place, numbered on both sides."""
    old_html, new_html = highlight_lines(old), highlight_lines(new)
    matcher = difflib.SequenceMatcher(
        a=old.splitlines(), b=new.splitlines(), autojunk=False
    )
    rows: list[DiffRow] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            rows += [
                DiffRow(kind="same", old_no=i + 1, new_no=j + 1, html=old_html[i])
                for i, j in zip(range(i1, i2), range(j1, j2), strict=True)
            ]
            continue
        rows += [
            DiffRow(kind="del", old_no=i + 1, new_no=None, html=old_html[i])
            for i in range(i1, i2)
        ]
        rows += [
            DiffRow(kind="add", old_no=None, new_no=j + 1, html=new_html[j])
            for j in range(j1, j2)
        ]
    return rows


def diff_counts(rows: list[DiffRow]) -> tuple[int, int]:
    """(added, removed) line counts."""
    return (
        sum(row.kind == "add" for row in rows),
        sum(row.kind == "del" for row in rows),
    )


def locators_in(code: str) -> list[str]:
    """The locator calls a spec uses, each once, in order of appearance."""
    return list(dict.fromkeys(_LOCATOR.findall(code)))
```

- [ ] **Step 5: Register the helpers with Jinja**

Replace `src/workbench/web/templating.py` with:

```python
"""The Jinja environment every page and fragment is rendered with."""

from fastapi.templating import Jinja2Templates

from workbench.config import TEMPLATES_DIR
from workbench.models.heal import REPAIR_STRATEGY_LABELS
from workbench.web import views
from workbench.web.icons import ICON_PATHS

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.filters["duration"] = views.format_duration
templates.env.filters["size"] = views.format_size
templates.env.globals.update(
    ICON_PATHS=ICON_PATHS,
    views=views,
    HEAL_BADGES=views.HEAL_BADGES,
    GENERATE_BADGES=views.GENERATE_BADGES,
    OUTCOME_BADGES=views.OUTCOME_BADGES,
    STRATEGY_LABELS={k.value: v for k, v in REPAIR_STRATEGY_LABELS.items()},
)
```

- [ ] **Step 6: Run the tests**

Run: `uv run python -m pytest tests/unit/test_views.py tests/unit/test_web_assets.py -q -o addopts=`
Expected: 15 passed (9 view tests and 6 asset tests).

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check .`
Expected: all pass. `_TokenType` is a private Pygments name; if mypy cannot see it, define `Token = tuple[Any, str]` instead.

- [ ] **Step 7: Commit**

```bash
git add src/workbench/models/web.py src/workbench/web/views.py src/workbench/web/templating.py tests/unit/test_views.py
git commit -m "feat: add view helpers for times, sizes, highlighted code, diffs and badges" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: The run registry

**Files:**

- Create: `src/workbench/runs.py`, `tests/unit/test_runs.py`

**Interfaces:**

- Consumes: `RunEvent`, `EventSink`, `Emit` (Phase 2); `HealReport | GenerateReport` (`workbench.reports.Report`).
- Produces:
  - `workbench.runs`:
    - `RunKind = Literal["heal", "generate"]`
    - `Job = Callable[[Emit, threading.Event], Report]`
    - `RunInProgress(RuntimeError)`, with an `.active` attribute holding the running `Run`
  - `Run`:
    - attributes: `id`, `kind`, `label`, `model_label`, `steps: tuple[str, ...]` (the step names its progress list shows), `cancel: threading.Event`, `report_id: str | None`, `error: str`
    - methods and properties: `add(event)`, `events_after(count) -> list[RunEvent]`, `finished` (property), `wait(timeout) -> bool`, `elapsed_ms() -> int`
  - `RunRegistry`:
    - `start(kind, label, job, *, model_label="", steps=()) -> Run`, which raises `RunInProgress`
    - `get(run_id) -> Run | None`
    - `active() -> Run | None`

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_runs.py`:

```python
"""One run at a time, in a background thread, with its events kept for late listeners."""

import threading

import pytest

from workbench.events import EventSink
from workbench.models.generate import GenerateReport
from workbench.runs import Run, RunInProgress, RunRegistry


def _report(report_id: str = "20261004-120000-generate-x") -> GenerateReport:
    return GenerateReport(id=report_id, url="http://x/", scenario="s", status="passed")


def _quick_job(emit, cancel):  # type: ignore[no-untyped-def]
    sink = EventSink("r", emit)
    sink.step("context", "active")
    sink.step("context", "done", "3 locator candidates")
    return _report()


def test_a_run_records_its_events_and_report() -> None:
    registry = RunRegistry()
    run = registry.start(
        "generate",
        "contact",
        _quick_job,
        model_label="qwen · Ollama",
        steps=("context",),
    )
    assert run.wait(5)
    assert run.finished
    assert run.report_id == "20261004-120000-generate-x"
    assert [e.state for e in run.events_after(0)] == ["active", "done"]
    assert [e.state for e in run.events_after(1)] == ["done"]
    assert run.model_label == "qwen · Ollama"
    assert run.steps == ("context",)
    assert registry.get(run.id) is run
    assert registry.active() is None


def test_only_one_run_at_a_time() -> None:
    registry = RunRegistry()
    release = threading.Event()

    def slow(emit, cancel):  # type: ignore[no-untyped-def]
        release.wait(5)
        return _report()

    first = registry.start("heal", "a.spec.ts", slow)
    with pytest.raises(RunInProgress) as refused:
        registry.start("heal", "b.spec.ts", _quick_job)
    assert refused.value.active is first
    assert registry.active() is first
    release.set()
    assert first.wait(5)
    second = registry.start("heal", "b.spec.ts", _quick_job)
    assert second.wait(5)


def test_cancel_reaches_the_job() -> None:
    registry = RunRegistry()
    seen = threading.Event()

    def waits_for_cancel(emit, cancel):  # type: ignore[no-untyped-def]
        seen.set()
        cancel.wait(5)
        return _report()

    run = registry.start("heal", "a.spec.ts", waits_for_cancel)
    assert seen.wait(5)
    run.cancel.set()
    assert run.wait(5)


def test_a_crashing_job_finishes_with_an_error_and_frees_the_slot() -> None:
    registry = RunRegistry()

    def crashes(emit, cancel):  # type: ignore[no-untyped-def]
        raise OSError("disk full")

    run = registry.start("heal", "a.spec.ts", crashes)
    assert run.wait(5)
    assert run.report_id is None
    assert run.error == "OSError: disk full"
    assert registry.active() is None


def test_unknown_runs_are_none_and_old_runs_are_dropped() -> None:
    registry = RunRegistry(keep=2)
    runs: list[Run] = []
    for _ in range(3):
        run = registry.start("generate", "x", _quick_job)
        assert run.wait(5)
        runs.append(run)
    assert registry.get("nope") is None
    assert registry.get(runs[0].id) is None
    assert registry.get(runs[2].id) is runs[2]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_runs.py -q -o addopts=`
Expected: collection error `No module named 'workbench.runs'`.

- [ ] **Step 3: Write the registry**

Create `src/workbench/runs.py`:

```python
"""Runs heals and generations in a background thread, one at a time.

The web app starts a run here and streams its events to the browser. Events
are kept, so a reloaded page or a second tab can replay them from the start.
"""

import logging
import secrets
import threading
import time
from collections.abc import Callable
from typing import Literal

from workbench.events import Emit
from workbench.models.events import RunEvent
from workbench.reports import Report

logger = logging.getLogger(__name__)

RunKind = Literal["heal", "generate"]
Job = Callable[[Emit, threading.Event], Report]


class Run:
    """One heal or generation: its events so far, and how it ended."""

    def __init__(
        self,
        kind: RunKind,
        label: str,
        model_label: str = "",
        steps: tuple[str, ...] = (),
    ) -> None:
        self.id = secrets.token_hex(6)
        self.kind: RunKind = kind
        self.label = label
        self.model_label = model_label
        self.steps = steps
        self.cancel = threading.Event()
        self.report_id: str | None = None
        self.error = ""
        self._events: list[RunEvent] = []
        self._lock = threading.Lock()
        self._finished = threading.Event()
        self._started = time.monotonic()

    def add(self, event: RunEvent) -> None:
        """Record an event (the pipeline's ``emit``)."""
        with self._lock:
            self._events.append(event)

    def events_after(self, count: int) -> list[RunEvent]:
        """Events after the first ``count``, in order."""
        with self._lock:
            return list(self._events[count:])

    @property
    def finished(self) -> bool:
        return self._finished.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        """Block until the run ends; False on timeout."""
        return self._finished.wait(timeout)

    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self._started) * 1000)

    def finish(self, report_id: str | None, error: str = "") -> None:
        self.report_id, self.error = report_id, error
        self._finished.set()


class RunInProgress(RuntimeError):
    """Another run is still going."""

    def __init__(self, active: Run) -> None:
        super().__init__(f"A run is already in progress: {active.label}")
        self.active = active


class RunRegistry:
    """Starts runs and finds them again; keeps the latest ``keep`` runs."""

    def __init__(self, keep: int = 20) -> None:
        self._keep = keep
        self._runs: dict[str, Run] = {}
        self._lock = threading.Lock()

    def start(
        self,
        kind: RunKind,
        label: str,
        job: Job,
        *,
        model_label: str = "",
        steps: tuple[str, ...] = (),
    ) -> Run:
        with self._lock:
            active = self._active()
            if active is not None:
                raise RunInProgress(active)
            run = Run(kind, label, model_label, steps)
            self._runs[run.id] = run
            for old in list(self._runs)[: -self._keep]:
                del self._runs[old]
        threading.Thread(target=self._execute, args=(run, job), daemon=True).start()
        return run

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            return self._runs.get(run_id)

    def active(self) -> Run | None:
        with self._lock:
            return self._active()

    def _active(self) -> Run | None:
        return next((r for r in self._runs.values() if not r.finished), None)

    @staticmethod
    def _execute(run: Run, job: Job) -> None:
        try:
            report = job(run.add, run.cancel)
        except Exception as exc:  # the UI shows it; the slot must be freed
            logger.exception("Run %s (%s) crashed", run.id, run.label)
            run.finish(None, f"{type(exc).__name__}: {exc}")
        else:
            run.finish(report.id)
```

- [ ] **Step 4: Run the tests**

Run: `uv run python -m pytest tests/unit/test_runs.py -q -o addopts=`
Expected: 5 passed.

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check .`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/workbench/runs.py tests/unit/test_runs.py
git commit -m "feat: add the run registry: one background run at a time with replayable events" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: The model menu, header pill and "model unreachable" card

**Files:**

- Modify: `src/workbench/models/settings.py` (add `ModelView`), `src/workbench/app.py`, `src/workbench/web/static/css/app.css`
- Create:
  - `src/workbench/web/model_state.py`
  - `src/workbench/web/routes/__init__.py`, `src/workbench/web/routes/model.py`
  - `src/workbench/web/templates/partials/model_pill.html`, `model_popover.html`, `unreachable.html`
  - `tests/unit/test_web_model.py`

**Interfaces:**

- Consumes:
  - `load_settings()`, `save_settings()` (`workbench.settings`)
  - `ModelSettings`, `ConnectionStatus`, `PROVIDER_LABELS`, `DEFAULT_URLS`, `DEMO_MODEL`, `ProviderName` (`workbench.models.settings`)
  - `Services.detect` and `Services.check_connection(provider, base_url)` (Task 1)
- Produces:
  - `workbench.models.settings.ModelView(choice: ModelSettings | None = None, connection: ConnectionStatus | None = None)`, with the properties:
    - `state` (`"connected"`, `"demo"` or `"off"`)
    - `ready`, `provider`, `label`, `base_url`, `model_label`
  - `workbench.web.model_state.ModelState(services)`, with the methods:
    - `choice() -> ModelSettings | None`, which returns the saved choice or a server detected once per app
    - `view() -> ModelView`
    - `probe(provider, base_url) -> ConnectionStatus`
  - `app.state.model: ModelState`
  - routes `GET /model`, `POST /model/test`, `POST /model`
  - partials:
    - `model_pill.html` (context `model: ModelView`): the pill button plus the lazily loaded popover `#model-menu`
    - `unreachable.html` (context `model: ModelView`)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_web_model.py`:

```python
"""The model menu: test a server, pick a model, save the choice; and the header pill."""

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from workbench import config
from workbench.app import create_app
from workbench.models.settings import (
    DEFAULT_URLS,
    DEMO_MODEL,
    ConnectionStatus,
    ModelSettings,
    ModelView,
)
from workbench.settings import load_settings, save_settings
from workbench.web.services import Services
from workbench.web.templating import templates

OLLAMA = DEFAULT_URLS["ollama"]


class FakeServers:
    """check_connection and detect fakes that record their calls."""

    def __init__(self, models: dict[str, list[str]] | None = None) -> None:
        self.models = models or {}
        self.checked: list[tuple[str, str]] = []
        self.detections = 0

    def check(self, provider: str, base_url: str = "") -> ConnectionStatus:
        self.checked.append((provider, base_url))
        if provider == "demo":
            return ConnectionStatus(
                provider="demo", reachable=True, models=[DEMO_MODEL]
            )
        if base_url in self.models:
            return ConnectionStatus(
                provider=provider,
                base_url=base_url,
                reachable=True,
                models=self.models[base_url],
            )
        return ConnectionStatus(
            provider=provider,
            base_url=base_url,
            reachable=False,
            error=f"Could not reach the server at {base_url}. Is it running?",
        )

    def detect(self) -> ModelSettings | None:
        self.detections += 1
        return None


@pytest.fixture
def servers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeServers:
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))
    return FakeServers({OLLAMA: ["qwen3.6:35b-mlx", "gemma3:4b"]})


def _client(servers: FakeServers) -> TestClient:
    services = replace(
        Services(), check_connection=servers.check, detect=servers.detect
    )
    return TestClient(create_app(services))


def test_menu_lists_the_saved_servers_models(servers: FakeServers) -> None:
    save_settings(ModelSettings(provider="ollama", base_url=OLLAMA, model="gemma3:4b"))
    html = _client(servers).get("/model").text
    assert "Connected" in html
    assert '<option value="gemma3:4b" selected>' in html
    assert (
        '<option value="qwen3.6:35b-mlx" >' in html
        or '<option value="qwen3.6:35b-mlx">' in html
    )
    assert "Saved on this machine." in html


def test_switching_provider_uses_its_default_url(servers: FakeServers) -> None:
    html = (
        _client(servers)
        .post(
            "/model/test",
            data={"provider": "ollama", "base_url": DEFAULT_URLS["lm_studio"]},
        )
        .text
    )
    assert servers.checked[-1] == ("ollama", OLLAMA)
    assert f'value="{OLLAMA}"' in html


def test_a_custom_server_url_is_kept(servers: FakeServers) -> None:
    _client(servers).post(
        "/model/test",
        data={"provider": "ollama", "base_url": "http://gpu-box:11434/v1"},
    )
    assert servers.checked[-1] == ("ollama", "http://gpu-box:11434/v1")


def test_an_unreachable_server_shows_its_error_and_cannot_be_saved(
    servers: FakeServers,
) -> None:
    html = (
        _client(servers)
        .post(
            "/model/test",
            data={"provider": "lm_studio", "base_url": DEFAULT_URLS["lm_studio"]},
        )
        .text
    )
    assert "Unreachable" in html
    assert "Is it running?" in html
    assert "Available once connected" in html
    assert 'type="submit" disabled' in html


def test_saving_writes_the_settings_and_reloads_the_page(servers: FakeServers) -> None:
    response = _client(servers).post(
        "/model",
        data={"provider": "ollama", "base_url": OLLAMA, "model": "qwen3.6:35b-mlx"},
    )
    assert response.status_code == 200
    assert response.headers["HX-Refresh"] == "true"
    assert load_settings() == ModelSettings(
        provider="ollama", base_url=OLLAMA, model="qwen3.6:35b-mlx"
    )


def test_demo_is_saved_without_a_server(servers: FakeServers) -> None:
    response = _client(servers).post("/model", data={"provider": "demo"})
    assert response.headers["HX-Refresh"] == "true"
    assert load_settings() == ModelSettings(provider="demo", model=DEMO_MODEL)


@pytest.mark.parametrize(
    "form",
    [
        {"provider": "ollama", "base_url": "localhost:abc", "model": "m"},
        {"provider": "ollama", "base_url": OLLAMA, "model": ""},
        {"provider": "openai", "base_url": OLLAMA, "model": "m"},
    ],
)
def test_bad_choices_are_refused_inline(
    servers: FakeServers, form: dict[str, str]
) -> None:
    response = _client(servers).post("/model", data=form)
    assert response.status_code == 422
    assert 'role="alert"' in response.text
    assert load_settings() is None


def test_detection_runs_once_when_nothing_is_saved(servers: FakeServers) -> None:
    client = _client(servers)
    client.get("/model")
    client.get("/model")
    assert servers.detections == 1


def _pill(view: ModelView) -> str:
    return templates.get_template("partials/model_pill.html").render(model=view)


def test_pill_shows_not_connected_when_the_server_is_down() -> None:
    choice = ModelSettings(
        provider="lm_studio", base_url=DEFAULT_URLS["lm_studio"], model="m"
    )
    html = _pill(
        ModelView(
            choice=choice,
            connection=ConnectionStatus(
                provider="lm_studio", reachable=False, error="down"
            ),
        )
    )
    assert "model-pill--off" in html and "Not connected" in html and "LM Studio" in html


def test_pill_shows_the_model_or_demo() -> None:
    connected = ModelView(
        choice=ModelSettings(
            provider="ollama", base_url=OLLAMA, model="qwen3.6:35b-mlx"
        ),
        connection=ConnectionStatus(
            provider="ollama", reachable=True, models=["qwen3.6:35b-mlx"]
        ),
    )
    demo = ModelView(
        choice=ModelSettings(provider="demo", model=DEMO_MODEL),
        connection=ConnectionStatus(
            provider="demo", reachable=True, models=[DEMO_MODEL]
        ),
    )
    assert "qwen3.6:35b-mlx" in _pill(connected) and "Ollama" in _pill(connected)
    assert "model-pill--demo" in _pill(demo) and "scripted answers" in _pill(demo)
    assert 'popovertarget="model-menu"' in _pill(demo)


def test_unreachable_card_offers_demo() -> None:
    html = templates.get_template("partials/unreachable.html").render(
        model=ModelView(
            choice=ModelSettings(
                provider="lm_studio", base_url=DEFAULT_URLS["lm_studio"], model="m"
            ),
            connection=ConnectionStatus(provider="lm_studio", reachable=False),
        )
    )
    assert "Can't reach LM Studio at localhost:1234/v1" in html
    assert 'name="provider" value="demo"' in html
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_web_model.py -q -o addopts=`
Expected: collection error `cannot import name 'ModelView'`.

- [ ] **Step 3: Add `ModelView`**

Append to `src/workbench/models/settings.py`:

```python
ModelReadiness = Literal["connected", "demo", "off"]


class ModelView(BaseModel):
    """The model choice and its connection, as the header pill and menu show them."""

    choice: ModelSettings | None = None
    connection: ConnectionStatus | None = None

    @property
    def state(self) -> ModelReadiness:
        if (
            self.choice is None
            or self.connection is None
            or not self.connection.reachable
        ):
            return "off"
        return "demo" if self.choice.provider == "demo" else "connected"

    @property
    def ready(self) -> bool:
        return self.state != "off"

    @property
    def provider(self) -> ProviderName:
        return self.choice.provider if self.choice else "lm_studio"

    @property
    def label(self) -> str:
        return PROVIDER_LABELS[self.provider]

    @property
    def base_url(self) -> str:
        if self.choice is not None:
            return self.choice.base_url
        return DEFAULT_URLS["lm_studio"]

    @property
    def model_label(self) -> str:
        return f"{self.choice.model} · {self.label}" if self.choice else self.label
```

- [ ] **Step 4: Write the model state and the routes**

Create `src/workbench/web/model_state.py`:

```python
"""The model the app uses: the saved choice, otherwise a server found once at startup."""

import threading

from workbench.models.settings import (
    ConnectionStatus,
    ModelSettings,
    ModelView,
    ProviderName,
)
from workbench.settings import load_settings
from workbench.web.services import Services


class ModelState:
    """Reads the saved choice each time; detects a server only once per app."""

    def __init__(self, services: Services) -> None:
        self._services = services
        self._detected: ModelSettings | None = None
        self._detection_done = False
        self._lock = threading.Lock()

    def choice(self) -> ModelSettings | None:
        saved = load_settings()
        if saved is not None:
            return saved
        with self._lock:
            if not self._detection_done:
                self._detected = self._services.detect()
                self._detection_done = True
            return self._detected

    def view(self) -> ModelView:
        choice = self.choice()
        if choice is None:
            return ModelView()
        return ModelView(
            choice=choice, connection=self.probe(choice.provider, choice.base_url)
        )

    def probe(self, provider: ProviderName, base_url: str) -> ConnectionStatus:
        return self._services.check_connection(provider, base_url)
```

Create `src/workbench/web/routes/__init__.py`:

```python
"""Routes, one module per area of the app."""
```

Create `src/workbench/web/routes/model.py`:

```python
"""The model menu: test a server, list its models, save the choice."""

from typing import Any, get_args

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from workbench.models.settings import (
    DEFAULT_URLS,
    DEMO_MODEL,
    PROVIDER_LABELS,
    ConnectionStatus,
    ModelSettings,
    ProviderName,
)
from workbench.settings import save_settings
from workbench.web.model_state import ModelState
from workbench.web.templating import templates

router = APIRouter()


def _state(request: Request) -> ModelState:
    state: ModelState = request.app.state.model
    return state


def _url_for(provider: str, base_url: str) -> str:
    """The typed URL, unless it is empty or another provider's default."""
    if provider == "demo":
        return ""
    typed = base_url.strip().rstrip("/")
    if not typed or typed in DEFAULT_URLS.values():
        return DEFAULT_URLS[provider]  # type: ignore[index]
    return typed


def _menu(
    request: Request,
    *,
    provider: str,
    base_url: str,
    status: ConnectionStatus,
    selected: str = "",
    error: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    menu: dict[str, Any] = {
        "provider": provider,
        "base_url": base_url,
        "status": status,
        "selected": selected or (status.models[0] if status.models else ""),
        "error": error,
        "providers": list(PROVIDER_LABELS.items()),
    }
    return templates.TemplateResponse(
        request, "partials/model_popover.html", {"menu": menu}, status_code=status_code
    )


def _provider(raw: str) -> ProviderName | None:
    return raw if raw in get_args(ProviderName) else None  # type: ignore[return-value]


@router.get("/model", response_class=HTMLResponse)
def model_menu(request: Request) -> HTMLResponse:
    view = _state(request).view()
    status = view.connection or _state(request).probe(view.provider, view.base_url)
    selected = view.choice.model if view.choice else ""
    return _menu(
        request,
        provider=view.provider,
        base_url=view.base_url,
        status=status,
        selected=selected,
    )


@router.post("/model/test", response_class=HTMLResponse)
def test_model(
    request: Request, provider: str = Form("lm_studio"), base_url: str = Form("")
) -> HTMLResponse:
    chosen = _provider(provider) or "lm_studio"
    url = _url_for(chosen, base_url)
    status = _state(request).probe(chosen, url)
    current = _state(request).choice()
    selected = current.model if current and current.provider == chosen else ""
    return _menu(
        request, provider=chosen, base_url=url, status=status, selected=selected
    )


@router.post("/model", response_model=None)
def save_model(
    request: Request,
    provider: str = Form("lm_studio"),
    base_url: str = Form(""),
    model: str = Form(""),
) -> Response:
    chosen = _provider(provider)
    url = _url_for(chosen or "lm_studio", base_url)
    try:
        if chosen is None:
            raise ValueError(f"Unknown provider {provider!r}.")
        settings = (
            ModelSettings(provider="demo", model=DEMO_MODEL)
            if chosen == "demo"
            else ModelSettings(provider=chosen, base_url=url, model=model.strip())
        )
    except (ValidationError, ValueError) as exc:
        message = (
            exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else str(exc)
        )
        status = ConnectionStatus(
            provider=chosen or "lm_studio", base_url=url, reachable=False
        )
        return _menu(
            request,
            provider=chosen or "lm_studio",
            base_url=url,
            status=status,
            error=message.removeprefix("Value error, "),
            status_code=422,
        )
    save_settings(settings)
    return Response(status_code=200, headers={"HX-Refresh": "true"})
```

Update `src/workbench/app.py` to keep the model state and include the router. Add these imports:

```python
from workbench.web.model_state import ModelState
from workbench.web.routes import model as model_routes
```

and after `app.state.base_url = ...`, add:

```python
    app.state.model = ModelState(app.state.services)
    app.include_router(model_routes.router)
```

- [ ] **Step 5: Write the templates**

Create `src/workbench/web/templates/partials/model_pill.html`. The popover body loads when it opens, so a page render never waits on the model server for the menu:

```jinja
{% set state = model.state %}
<button type="button" popovertarget="model-menu"
  class="model-pill{% if state == 'demo' %} model-pill--demo{% elif state == 'off' %} model-pill--off{% endif %}"
  aria-label="Model: {% if state == 'off' %}not connected{% elif state == 'demo' %}Demo{% else %}{{ model.choice.model }}{% endif %}, {{ model.label }}. Change the model">
  {%- if state == "off" %}Not connected{% elif state == "demo" %}Demo{% else %}{{ model.choice.model }}{% endif %}
  <span class="model-pill__provider">{% if state == "demo" %}scripted answers{% else %}{{ model.label }}{% endif %}</span>
</button>
<div id="model-menu" class="popover" popover aria-label="Model" hx-get="/model" hx-trigger="toggle" hx-swap="innerHTML">
  <p class="t-small t-faint">Checking the model server…</p>
</div>
```

Create `src/workbench/web/templates/partials/model_popover.html`:

```jinja
{% from "partials/icons.html" import icon %}
<form class="stack" hx-post="/model" hx-target="this" hx-swap="outerHTML">
  <div class="row">
    <h2 class="t-section">Model</h2>
    {% if menu.provider == "demo" %}<span class="pill pill--warn ml-auto">Demo</span>
    {% elif menu.status.reachable %}<span class="pill pill--pass ml-auto">Connected</span>
    {% else %}<span class="pill pill--fail ml-auto">Unreachable</span>{% endif %}
  </div>
  <fieldset class="fieldset stack stack--tight">
    <legend class="field__label">Provider</legend>
    <div class="seg" hx-post="/model/test" hx-trigger="change" hx-include="closest form" hx-target="closest form" hx-swap="outerHTML">
      {% for value, label in menu.providers %}
      <label><input type="radio" name="provider" value="{{ value }}"{% if value == menu.provider %} checked{% endif %}>{{ label }}</label>
      {% endfor %}
    </div>
  </fieldset>
  {% if menu.provider != "demo" %}
  <div class="field">
    <div class="row">
      <label class="field__label" for="model-server">Server</label>
      <button type="button" class="btn btn--ghost btn--small ml-auto" hx-post="/model/test" hx-include="closest form" hx-target="closest form" hx-swap="outerHTML">{{ icon("refresh", 14) }} Retry</button>
    </div>
    <input class="input input--mono" id="model-server" name="base_url" value="{{ menu.base_url }}"{% if not menu.status.reachable %} aria-invalid="true" aria-describedby="model-server-error"{% endif %}>
    {% if not menu.status.reachable and menu.status.error %}<p class="field__error" id="model-server-error">{{ menu.status.error }}</p>{% endif %}
  </div>
  <div class="field">
    <label class="field__label" for="model-name">Model</label>
    {% if menu.status.reachable and menu.status.models %}
    <select class="select input--mono" id="model-name" name="model">
      {% for name in menu.status.models %}<option value="{{ name }}"{% if name == menu.selected %} selected{% endif %}>{{ name }}</option>{% endfor %}
    </select>
    {% else %}
    <select class="select" id="model-name" disabled><option>Available once connected</option></select>
    {% endif %}
  </div>
  {% else %}
  <p class="t-small t-muted">Replays recorded model answers for the bundled samples, so you can see the whole flow without a model. Runs are labelled "Demo".</p>
  {% endif %}
  {% if menu.error %}<p class="field__error" role="alert">{{ menu.error }}</p>{% endif %}
  <button class="btn btn--primary btn--block" type="submit"{% if menu.provider != "demo" and not menu.status.reachable %} disabled{% endif %}>Save</button>
  <p class="popover__foot">Saved on this machine.</p>
</form>
```

Create `src/workbench/web/templates/partials/unreachable.html`:

```jinja
{% from "partials/icons.html" import icon %}
<section class="card center-card" aria-labelledby="unreachable-title">
  <span class="icon-tile icon-tile--fail">{{ icon("plug", 18) }}</span>
  <h1 class="t-page" id="unreachable-title">{% if model.choice %}Can't reach {{ model.label }} at {{ model.base_url | replace("http://", "") | replace("https://", "") }}{% else %}No model server found{% endif %}</h1>
  <p class="t-muted">Healing and generating need a model. Start one locally, or try the samples with the scripted demo model.</p>
  <div class="card card--subtle stack">
    <h2 class="t-label row">{{ icon("play", 14) }} Start a local model</h2>
    <p class="t-small t-muted">LM Studio: load a model and start the local server. Ollama: start the server, then pull a model.</p>
    <code class="cmd">ollama serve</code>
    <div><button class="btn btn--secondary" type="button" onclick="location.reload()">Test connection</button></div>
  </div>
  <div class="card card--subtle stack">
    <h2 class="t-label row">{{ icon("check", 14) }} Use the scripted demo model</h2>
    <p class="t-small t-muted">Replays recorded model answers for the sample tests, so you can see the whole flow without a model. Runs are labelled "Demo".</p>
    <form hx-post="/model"><input type="hidden" name="provider" value="demo"><button class="btn btn--primary" type="submit">Switch to demo model</button></form>
  </div>
</section>
```

Append to `src/workbench/web/static/css/app.css`:

```css

/* Small utilities */
.ml-auto {
  margin-left: auto;
}
.fieldset {
  margin: 0;
  padding: 0;
  border: 0;
}
.btn--small {
  height: 24px;
  padding: 0 8px;
}
```

- [ ] **Step 6: Run the tests**

Run: `uv run python -m pytest tests/unit/test_web_model.py -q -o addopts=`
Expected: 13 passed (the parametrized refusal test counts 3).

If the `<option>` assertion in `test_menu_lists_the_saved_servers_models` fails only on whitespace, change the template so the rendered tag is exactly `<option value="qwen3.6:35b-mlx">`, and simplify the assertion to that form. The test checks that the unselected option has no `selected`.

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check . && npm run lint`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/workbench/models/settings.py src/workbench/app.py src/workbench/web tests/unit/test_web_model.py
git commit -m "feat: add the model menu, header pill and model-unreachable card" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Live runs over server-sent events

**Files:**

- Create:
  - `src/workbench/web/sse.py`, `src/workbench/web/routes/runs.py`
  - `src/workbench/web/templates/partials/run_view.html`, `step_row.html`, `step_body.html`, `log_line.html`, `run_done.html`
  - `tests/unit/conftest.py`, `tests/unit/web_support.py`, `tests/unit/test_web_runs.py`
- Modify: `src/workbench/app.py`

**Interfaces:**

- Consumes:
  - `Run`, `RunRegistry` (Task 4)
  - `STEP_INFO`, `format_duration`, `HEAL_STEPS`, `GENERATE_STEPS` (Task 3)
  - `templates` (Task 2)
- Produces:
  - `workbench.web.sse`:
    - `sse_message(event: str, html: str) -> str`
    - `RunStream(run)`, with `.pending() -> list[str]`, `.clock() -> str`, `.done() -> str` and `.sent: int`
  - `app.state.runs: RunRegistry`
  - routes:
    - `GET /runs/{id}/events`: the SSE stream. Its events are `step-<step>` (a `step_body` fragment), `log` (a log line), `clock` (the header meta text) and `done` (`run_done`)
    - `POST /runs/{id}/cancel`, which returns a disabled "Cancelling…" button
    - `GET /runs/{id}/result`, which returns `HX-Redirect: /reports/{report_id}`, or the error banner if the run crashed
  - the partial `run_view.html` (context `run: Run`; its progress list shows `run.steps`), used by Tasks 7 and 10
  - `tests/unit/conftest.py`: a `web_workspace` fixture that points `WORKBENCH_WORKSPACE` at a temp folder
  - `tests/unit/web_support.py`:
    - `make_client(**service_overrides) -> TestClient`, with fakes: no detection, every server reachable, browsers ready
    - `heal_report(**fields) -> HealReport`
    - `heal_job(report, *, gate=None) -> Job`, which emits the five heal steps, saves the report and returns it

- [ ] **Step 1: Write the test support and the failing tests**

Create `tests/unit/conftest.py`:

```python
"""Shared fixtures for the unit suite."""

from pathlib import Path

import pytest

from workbench import config


@pytest.fixture
def web_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fresh workspace for tests that start the web app."""
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))
    return config.workspace_dir()
```

Create `tests/unit/web_support.py`:

```python
"""Helpers for the web route tests: a client with fake services, and canned runs."""

import threading
from dataclasses import replace
from typing import Any

from fastapi.testclient import TestClient

from workbench.app import create_app
from workbench.events import Emit, EventSink
from workbench.ids import new_run_id
from workbench.models.heal import HealReport
from workbench.models.settings import DEMO_MODEL, ConnectionStatus
from workbench.reports import save_report
from workbench.runs import Job
from workbench.web.services import Services


def _reachable(provider: str, base_url: str = "") -> ConnectionStatus:
    models = [DEMO_MODEL] if provider == "demo" else ["test-model"]
    return ConnectionStatus(
        provider=provider, base_url=base_url, reachable=True, models=models
    )  # type: ignore[arg-type]


def make_client(**overrides: Any) -> TestClient:
    """An app whose services are fakes unless overridden."""
    services = replace(
        Services(),
        detect=lambda: None,
        check_connection=_reachable,
        browsers_ready=lambda: True,
        **overrides,
    )
    return TestClient(create_app(services))


def heal_report(**fields: Any) -> HealReport:
    values: dict[str, Any] = {
        "id": new_run_id("heal", "contact-form"),
        "spec_name": "contact-form.spec.ts",
        "status": "healed",
    }
    values.update(fields)
    return HealReport(**values)


def heal_job(report: HealReport, *, gate: threading.Event | None = None) -> Job:
    """A job that walks the five heal steps, optionally waiting on ``gate`` first."""

    def job(emit: Emit, cancel: threading.Event) -> HealReport:
        if gate is not None:
            gate.wait(5)
        events = EventSink(report.id, emit)
        events.step("run", "active", "npx playwright test contact-form.spec.ts")
        events.step(
            "run", "done", "TimeoutError: locator.click: Timeout 3000ms exceeded."
        )
        events.step("evidence", "active")
        events.step("evidence", "done", "Page snapshot from error-context.md")
        events.step("diagnose", "active", "Classifier hint: TIMEOUT")
        events.step("diagnose", "done", "LOCATOR_DRIFT (0.90)")
        events.step("repair", "active")
        events.step("repair", "done", "Selector replaced (ast)")
        events.step("verify", "active")
        events.step("verify", "done", "Re-run passed")
        events.attempt(1, "healed")
        events.done(report.status)
        save_report(report)
        return report

    return job
```

Create `tests/unit/test_web_runs.py`:

```python
"""The SSE stream, cancel and the hand-over to the result page."""

import threading

import pytest

from tests.unit.web_support import heal_job, heal_report, make_client
from workbench.events import EventSink
from workbench.reports import load_report
from workbench.runs import Run
from workbench.web.sse import RunStream, sse_message

pytestmark = pytest.mark.usefixtures("web_workspace")


def _stream(client, run_id: str) -> str:  # type: ignore[no-untyped-def]
    with client.stream("GET", f"/runs/{run_id}/events") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        return response.read().decode()


def test_sse_message_puts_each_line_in_its_own_data_field() -> None:
    assert sse_message("log", "a\nb") == "event: log\ndata: a\ndata: b\n\n"
    assert sse_message("clock", "") == "event: clock\ndata: \n\n"


def test_stream_renders_steps_logs_and_the_hand_over() -> None:
    client = make_client()
    report = heal_report()
    run = client.app.state.runs.start("heal", "contact-form.spec.ts", heal_job(report))  # type: ignore[attr-defined]
    body = _stream(client, run.id)
    assert "event: step-run\n" in body
    assert "step--done" in body
    assert "event: log\n" in body and "[verify] Re-run passed" in body
    assert "Attempt 1: healed" in body
    assert f'hx-get="/runs/{run.id}/result"' in body.split("event: done", 1)[1]


def test_a_late_listener_gets_every_event_from_the_start() -> None:
    client = make_client()
    run = client.app.state.runs.start("heal", "x", heal_job(heal_report()))  # type: ignore[attr-defined]
    assert run.wait(5)
    assert _stream(client, run.id).count("event: step-") == 10


def test_result_redirects_to_the_report() -> None:
    client = make_client()
    report = heal_report()
    run = client.app.state.runs.start("heal", "x", heal_job(report))  # type: ignore[attr-defined]
    assert run.wait(5)
    response = client.get(f"/runs/{run.id}/result")
    assert response.status_code == 200
    assert response.headers["HX-Redirect"] == f"/reports/{report.id}"


def test_a_crashed_run_shows_its_error() -> None:
    client = make_client()

    def crashes(emit, cancel):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    run = client.app.state.runs.start("heal", "x", crashes)  # type: ignore[attr-defined]
    assert run.wait(5)
    assert "The run stopped unexpectedly" in _stream(client, run.id)
    result = client.get(f"/runs/{run.id}/result")
    assert "RuntimeError: boom" in result.text
    assert "HX-Redirect" not in result.headers


def test_cancel_sets_the_flag_the_job_sees() -> None:
    client = make_client()
    report = heal_report(status="cancelled")
    seen = threading.Event()

    def waits(emit, cancel):  # type: ignore[no-untyped-def]
        seen.set()
        cancel.wait(5)
        return heal_job(report)(emit, cancel)

    run = client.app.state.runs.start("heal", "x", waits)  # type: ignore[attr-defined]
    assert seen.wait(5)
    response = client.post(f"/runs/{run.id}/cancel")
    assert "Cancelling" in response.text and "disabled" in response.text
    assert run.wait(5)


def test_unknown_runs_are_404() -> None:
    client = make_client()
    assert client.get("/runs/nope/events").status_code == 404
    assert client.post("/runs/nope/cancel").status_code == 404
    assert client.get("/runs/nope/result").status_code == 404


def test_run_finishes_after_the_stream_is_dropped() -> None:
    client = make_client()
    gate = threading.Event()
    report = heal_report()
    run = client.app.state.runs.start("heal", "x", heal_job(report, gate=gate))  # type: ignore[attr-defined]
    with client.stream("GET", f"/runs/{run.id}/events") as response:
        next(response.iter_text())  # the first clock tick
    gate.set()
    assert run.wait(5)
    assert load_report(report.id).status == "healed"


def test_clock_says_the_model_is_still_thinking() -> None:
    run = Run("heal", "contact-form.spec.ts")
    EventSink("r", run.add).step("diagnose", "active", "Classifier hint: TIMEOUT")
    stream = RunStream(run)
    stream.pending()
    run.elapsed_ms = lambda: 45_000  # type: ignore[method-assign]
    assert "the model is still thinking" in stream.clock()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_web_runs.py -q -o addopts=`
Expected: collection error `No module named 'workbench.web.sse'`.

- [ ] **Step 3: Write the stream renderer**

Create `src/workbench/web/sse.py`:

```python
"""Renders a run's events as server-sent events carrying HTML fragments.

HTMX's SSE extension swaps each fragment into the element whose ``sse-swap``
names the event, so the browser keeps no state of its own.
"""

from typing import Any

from workbench.models.events import RunEvent
from workbench.runs import Run
from workbench.web.templating import templates
from workbench.web.views import STEP_INFO, format_duration

THINKING_AFTER_MS = 30_000
_TONES = {"active": "step", "failed": "fail", "skipped": "muted", "done": ""}


def sse_message(event: str, html: str) -> str:
    """One SSE message; every line of ``html`` goes in its own ``data:`` field."""
    lines = html.splitlines() or [""]
    return f"event: {event}\n" + "".join(f"data: {line}\n" for line in lines) + "\n"


def _render(name: str, **context: Any) -> str:
    return templates.get_template(name).render(**context)


class RunStream:
    """One browser tab's view of a run: which events it has sent, and step timings."""

    def __init__(self, run: Run) -> None:
        self.run = run
        self.sent = 0
        self._started: dict[str, int] = {}
        self._active: str | None = None
        self._attempts = 0

    def pending(self) -> list[str]:
        """Messages for the events this tab has not seen yet."""
        messages: list[str] = []
        for event in self.run.events_after(self.sent):
            self.sent += 1
            messages += self._messages(event)
        return messages

    def _messages(self, event: RunEvent) -> list[str]:
        if event.kind == "step" and event.step and event.state:
            info = STEP_INFO[event.step]
            took = ""
            if event.state == "active":
                self._started[event.step] = event.elapsed_ms
                self._active = event.step
            else:
                if self._active == event.step:
                    self._active = None
                started = self._started.get(event.step)
                if started is not None:
                    took = format_duration(event.elapsed_ms - started)
            body = _render(
                "partials/step_body.html",
                info=info,
                state=event.state,
                detail=event.detail or info.description,
                time=took,
            )
            line = _render(
                "partials/log_line.html",
                tone=_TONES[event.state],
                text=f"[{event.step}] {event.detail or info.title}",
            )
            return [sse_message(f"step-{event.step}", body), sse_message("log", line)]
        if event.kind == "attempt":
            self._attempts += 1
            return [
                sse_message(
                    "log",
                    _render("partials/log_line.html", tone="step", text=event.detail),
                )
            ]
        if event.kind == "log":
            return [
                sse_message(
                    "log",
                    _render("partials/log_line.html", tone="muted", text=event.detail),
                )
            ]
        return []  # the pipeline's own "done": the stream sends its own when the run ends

    def clock(self) -> str:
        """The run header's meta text: attempt, elapsed time, and a thinking hint."""
        parts = []
        if self.run.kind == "heal" and "evidence" in self._started:
            parts.append(f"Attempt {self._attempts + 1}")
        elapsed = self.run.elapsed_ms()
        parts.append(format_duration(elapsed))
        if self._active in ("diagnose", "model"):
            waited = elapsed - self._started.get(self._active, elapsed)
            if waited > THINKING_AFTER_MS:
                parts.append("the model is still thinking")
        if self.run.model_label:
            parts.append(self.run.model_label)
        return " · ".join(parts)

    def done(self) -> str:
        return sse_message("done", _render("partials/run_done.html", run=self.run))
```

- [ ] **Step 4: Write the routes and wire the registry**

Create `src/workbench/web/routes/runs.py`:

```python
"""A run's live event stream, its cancel button, and the hand-over to its report."""

import asyncio
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse

from workbench.runs import Run, RunRegistry
from workbench.web.sse import RunStream, sse_message
from workbench.web.templating import templates

router = APIRouter()
POLL_S = 0.1
CLOCK_S = 1.0


def _run(request: Request, run_id: str) -> Run:
    registry: RunRegistry = request.app.state.runs
    run = registry.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="No such run")
    return run


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, request: Request) -> StreamingResponse:
    run = _run(request, run_id)
    stream = RunStream(run)

    async def messages() -> AsyncIterator[str]:
        last_clock = 0.0
        while True:
            if await request.is_disconnected():
                return
            for message in stream.pending():
                yield message
            if run.finished and not run.events_after(stream.sent):
                yield stream.done()
                return
            now = time.monotonic()
            if now - last_clock >= CLOCK_S:
                yield sse_message("clock", stream.clock())
                last_clock = now
            await asyncio.sleep(POLL_S)

    return StreamingResponse(
        messages(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.post("/runs/{run_id}/cancel", response_class=HTMLResponse)
def cancel_run(run_id: str, request: Request) -> HTMLResponse:
    _run(request, run_id).cancel.set()
    return HTMLResponse(
        '<button class="btn btn--secondary" type="button" disabled>Cancelling…</button>'
    )


@router.get("/runs/{run_id}/result", response_model=None)
def run_result(run_id: str, request: Request) -> Response:
    run = _run(request, run_id)
    if run.report_id:
        return Response(
            status_code=200, headers={"HX-Redirect": f"/reports/{run.report_id}"}
        )
    return templates.TemplateResponse(request, "partials/run_done.html", {"run": run})
```

In `src/workbench/app.py`, add the imports `from workbench.runs import RunRegistry` and `from workbench.web.routes import runs as run_routes`, and after `app.state.model = ...`:

```python
    app.state.runs = RunRegistry()
    app.include_router(run_routes.router)
```

- [ ] **Step 5: Write the templates**

Create `src/workbench/web/templates/partials/run_view.html`:

```jinja
{% from "partials/icons.html" import icon %}
<section class="run" sse-connect="/runs/{{ run.id }}/events" sse-close="done" aria-labelledby="run-title">
  <div class="result-head">
    <span class="pill pill--run">{{ "Healing" if run.kind == "heal" else "Generating" }}</span>
    <h1 class="result-head__name" id="run-title">{{ run.label }}</h1>
    <span class="result-head__meta" sse-swap="clock">{{ run.model_label }}</span>
    <div class="result-head__actions">
      <button class="btn btn--secondary" type="button" hx-post="/runs/{{ run.id }}/cancel" hx-swap="outerHTML">Cancel</button>
    </div>
  </div>
  <div class="run-grid">
    <ol class="steps" aria-label="Progress">
      {% for name in run.steps %}{% set info = views.STEP_INFO[name] %}{% include "partials/step_row.html" %}{% endfor %}
    </ol>
    <section class="code" aria-label="Live log">
      <div class="code__head">{{ icon("file", 14) }} Live log <span class="code__head-meta">streaming</span></div>
      <div class="log__body" role="log" aria-live="polite" sse-swap="log" hx-swap="beforeend"></div>
    </section>
  </div>
  <div sse-swap="done" hx-swap="outerHTML"></div>
</section>
```

Create `src/workbench/web/templates/partials/step_row.html`. The `<li>` stays in place, and each event swaps its contents:

```jinja
<li id="step-{{ info.name }}" sse-swap="step-{{ info.name }}">{% with state="pending", detail=info.description, time="" %}{% include "partials/step_body.html" %}{% endwith %}</li>
```

Create `src/workbench/web/templates/partials/step_body.html`:

```jinja
{% from "partials/icons.html" import icon %}
{% set glyph = {"done": "check", "failed": "x", "active": "spinner"}.get(state, "circle-dashed") %}
{% set said = {"done": "Done", "failed": "Failed", "active": "In progress", "skipped": "Skipped"}.get(state, "Not started") %}
<div class="step step--{{ state }}">
  <span class="step__icon">{{ icon(glyph, 14, said) }}</span>
  <div><p class="step__title">{{ info.title }}</p><p class="step__detail">{{ detail }}</p></div>
  <span class="step__time">{{ time or "–" }}</span>
</div>
```

Create `src/workbench/web/templates/partials/log_line.html`:

```jinja
<div class="log__line{% if tone %} log__line--{{ tone }}{% endif %}">{{ text }}</div>
```

Create `src/workbench/web/templates/partials/run_done.html`:

```jinja
{% from "partials/icons.html" import icon %}
{% if run.report_id %}
<div hx-get="/runs/{{ run.id }}/result" hx-trigger="load"></div>
{% else %}
<div class="banner banner--fail" role="alert">{{ icon("x") }}<div><p class="banner__title">The run stopped unexpectedly</p><p>{{ run.error or "No report was written." }}</p><p><a href="/{{ run.kind }}">Start again</a></p></div></div>
{% endif %}
```

- [ ] **Step 6: Run the tests**

Run: `uv run python -m pytest tests/unit/test_web_runs.py -q -o addopts=`
Expected: 9 passed, in under 10 seconds.

If `test_run_finishes_after_the_stream_is_dropped` blocks on `next(response.iter_text())`, the first chunk is not flushed before the gate opens. In that case read with `response.iter_raw()` instead. The stream sends a clock message within `CLOCK_S` of connecting.

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check .`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/workbench/web src/workbench/app.py tests/unit/conftest.py tests/unit/web_support.py tests/unit/test_web_runs.py
git commit -m "feat: stream live run progress as server-sent HTML fragments" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: The Heal page and starting a heal

**Files:**

- Modify: `src/workbench/validation.py`, `src/workbench/app.py`
- Create:
  - `src/workbench/web/uploads.py`, `src/workbench/web/pages.py`, `src/workbench/web/routes/heal.py`
  - `src/workbench/web/templates/heal.html`
  - `src/workbench/web/templates/partials/heal_idle.html`, `banner.html`, `notice.html`
  - `tests/unit/test_web_heal.py`

**Interfaces:**

- Consumes:
  - `install_sample(name, base_url)`, `SAMPLES` (Phase 3)
  - `HealRequest` (Phase 2)
  - `load_report`, `GenerateReport`, `specs_dir()`, `slugify()`
  - `RunRegistry`, `RunInProgress` (Task 4)
  - `ModelState` (Task 5)
  - `run_view.html` (Task 6)
  - `HEAL_STEPS` (Task 3)
- Produces:
  - `workbench.validation`:
    - `MAX_SPEC_BYTES = 200 * 1024`
    - `validate_spec_upload(filename: str, data: bytes) -> str`, which raises `ValidationError`
  - `workbench.web.uploads.store_upload(filename: str, text: str) -> Path`, which writes `specs_dir() / "uploads" / <slug>.spec.ts`
  - `workbench.web.pages`:
    - `browsers_ready(request) -> bool`: it checks once and checks again while the browsers are missing
    - `page_context(request, page) -> dict`, with the keys `page`, `model`, `active`, `busy`, `browsers_ok`, `samples`, `base_url`, `result` (None) and `form` ({})
  - routes:
    - `GET /heal`
    - `POST /heal`, a multipart form with the fields:
      - `action`: `sample:<name>`, `upload` or `generated`
      - `max_attempts`
      - `spec`, the file
      - `generated`, a report id
  - templates:
    - `heal.html`, which renders `partials/heal_result.html` when `result` is set (Task 8)
    - `partials/banner.html`, with the macro `banner(variant, title, body, cmd=None)`
  - refusals:
    - `422` with `HX-Retarget` set to one of `#sample-error`, `#upload-error` or `#attempts-error`, and the message as the body
    - `409` with `HX-Retarget: #notice` and a notice banner

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_web_heal.py`:

```python
"""The Heal page, starting a heal from a sample, an upload or a generated test, and refusals."""

import threading
from typing import Any

import pytest

from tests.unit.web_support import heal_job, heal_report, make_client
from workbench.config import specs_dir, workspace_dir
from workbench.heal import HealRequest
from workbench.models.generate import GenerateReport
from workbench.models.settings import (
    DEFAULT_URLS,
    DEMO_MODEL,
    ConnectionStatus,
    ModelSettings,
)
from workbench.reports import save_report
from workbench.settings import save_settings

pytestmark = pytest.mark.usefixtures("web_workspace")


class FakeHeal:
    """Records heal() calls and runs the canned five-step job."""

    def __init__(self, gate: threading.Event | None = None) -> None:
        self.calls: list[HealRequest] = []
        self.gate = gate

    def __call__(
        self, request: HealRequest, *, model: Any, emit: Any = None, cancel: Any = None
    ):  # type: ignore[no-untyped-def]
        self.calls.append(request)
        return heal_job(heal_report(), gate=self.gate)(emit, cancel)


@pytest.fixture(autouse=True)
def demo_model() -> None:
    save_settings(ModelSettings(provider="demo", model=DEMO_MODEL))


def _start(client, fake: FakeHeal, **form: str):  # type: ignore[no-untyped-def]
    response = client.post("/heal", data={"max_attempts": "3", **form})
    run = client.app.state.runs.active()
    if run is not None:
        run.wait(5)
    return response


def test_heal_page_offers_both_samples_and_an_upload() -> None:
    html = make_client().get("/heal").text
    assert "Heal a failing test" in html
    assert 'value="sample:selector-drift"' in html and 'value="sample:app-bug"' in html
    assert "Selector drift" in html and "App bug" in html
    assert 'name="spec"' in html and 'name="max_attempts"' in html
    assert '<a href="/heal" aria-current="page">Heal</a>' in html
    assert (
        "disabled" not in html.split('value="sample:selector-drift"')[1].split(">")[0]
    )


def test_without_a_model_the_page_shows_the_unreachable_card_and_locks_buttons() -> (
    None
):
    def down(provider: str, base_url: str = "") -> ConnectionStatus:
        return ConnectionStatus(provider=provider, base_url=base_url, reachable=False)  # type: ignore[arg-type]

    save_settings(
        ModelSettings(
            provider="lm_studio", base_url=DEFAULT_URLS["lm_studio"], model="m"
        )
    )
    html = make_client(check_connection=down).get("/heal").text
    assert "Can't reach LM Studio" in html
    assert "Connect a model to run this." in html
    assert 'value="sample:selector-drift" disabled' in html


def test_missing_browsers_block_runs() -> None:
    html = make_client(browsers_ready=lambda: False).get("/heal").text
    assert "Playwright browsers aren't installed" in html
    assert "npx playwright install chromium" in html
    assert 'value="upload" disabled' in html


def test_a_sample_is_installed_and_healed() -> None:
    fake = FakeHeal()
    client = make_client(heal=fake)
    response = _start(client, fake, action="sample:selector-drift", max_attempts="2")
    assert response.status_code == 200
    assert "sse-connect=" in response.text
    request = fake.calls[0]
    assert request.spec_path == specs_dir() / "samples" / "contact-form.spec.ts"
    assert request.max_attempts == 2
    assert "http://127.0.0.1:7860/sample-site/" in request.spec_path.read_text(
        encoding="utf-8"
    )


def test_an_upload_is_copied_into_the_workspace() -> None:
    fake = FakeHeal()
    client = make_client(heal=fake)
    response = client.post(
        "/heal",
        data={"action": "upload", "max_attempts": "3"},
        files={
            "spec": ("My Test.spec.ts", b"test('x', async () => {});\n", "text/plain")
        },
    )
    assert response.status_code == 200
    client.app.state.runs.active() and client.app.state.runs.active().wait(5)  # type: ignore[attr-defined]
    path = specs_dir() / "uploads" / "my-test.spec.ts"
    assert fake.calls[0].spec_path == path
    assert path.read_text(encoding="utf-8") == "test('x', async () => {});\n"


@pytest.mark.parametrize(
    ("name", "content", "message"),
    [
        ("notes.txt", b"x", "isn't a test file"),
        ("big.spec.ts", b"a" * (200 * 1024 + 1), "larger than 200 KB"),
        ("empty.spec.ts", b"  \n", "is empty"),
        ("latin.spec.ts", b"\xff\xfe\xfa", "isn't UTF-8"),
    ],
)
def test_bad_uploads_are_rejected_inline(
    name: str, content: bytes, message: str
) -> None:
    fake = FakeHeal()
    response = make_client(heal=fake).post(
        "/heal",
        data={"action": "upload", "max_attempts": "3"},
        files={"spec": (name, content, "application/octet-stream")},
    )
    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#upload-error"
    assert message in response.text
    assert fake.calls == []


def test_upload_without_a_file_is_refused() -> None:
    response = make_client().post(
        "/heal", data={"action": "upload", "max_attempts": "3"}
    )
    assert response.status_code == 422
    assert "Choose a .spec.ts file first." in response.text


def test_upload_name_cannot_escape_the_uploads_folder() -> None:
    fake = FakeHeal()
    client = make_client(heal=fake)
    client.post(
        "/heal",
        data={"action": "upload", "max_attempts": "3"},
        files={"spec": ("../../evil.spec.ts", b"test('x', () => {});", "text/plain")},
    )
    client.app.state.runs.active() and client.app.state.runs.active().wait(5)  # type: ignore[attr-defined]
    assert fake.calls[0].spec_path == specs_dir() / "uploads" / "evil.spec.ts"
    assert not (workspace_dir().parent / "evil.spec.ts").exists()


@pytest.mark.parametrize("attempts", ["0", "6", "x"])
def test_attempts_out_of_range_are_refused(attempts: str) -> None:
    response = make_client().post(
        "/heal", data={"action": "sample:selector-drift", "max_attempts": attempts}
    )
    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#attempts-error"


def test_unknown_sample_is_refused() -> None:
    response = make_client().post(
        "/heal", data={"action": "sample:nope", "max_attempts": "3"}
    )
    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == "#sample-error"
    assert "Unknown sample" in response.text


def test_second_start_is_refused_with_409() -> None:
    gate = threading.Event()
    client = make_client(heal=FakeHeal(gate))
    client.post("/heal", data={"action": "sample:selector-drift", "max_attempts": "3"})
    second = client.post(
        "/heal", data={"action": "sample:app-bug", "max_attempts": "3"}
    )
    assert second.status_code == 409
    assert second.headers["HX-Retarget"] == "#notice"
    assert "already in progress" in second.text
    gate.set()
    client.app.state.runs.active().wait(5)  # type: ignore[attr-defined]


def test_heal_page_resumes_the_active_run() -> None:
    gate = threading.Event()
    client = make_client(heal=FakeHeal(gate))
    client.post("/heal", data={"action": "sample:selector-drift", "max_attempts": "3"})
    run = client.app.state.runs.active()  # type: ignore[attr-defined]
    html = client.get("/heal").text
    assert f'sse-connect="/runs/{run.id}/events"' in html
    assert 'value="sample:app-bug" disabled' in html
    gate.set()
    run.wait(5)


def test_a_failed_generated_test_can_be_healed() -> None:
    spec = specs_dir() / "a-user-can-send-the-contact-form.spec.ts"
    spec.write_text("test('x', () => {});", encoding="utf-8")
    report = GenerateReport(
        id="20261004-120000-generate-contact",
        url="http://127.0.0.1:7860/sample-site/",
        scenario="A user can send the contact form",
        status="failed",
        spec_name=spec.name,
    )
    save_report(report)
    fake = FakeHeal()
    client = make_client(heal=fake)
    _start(client, fake, action="generated", generated=report.id)
    assert fake.calls[0].spec_path == spec
    refused = client.post(
        "/heal", data={"action": "generated", "generated": "nope", "max_attempts": "3"}
    )
    assert refused.status_code == 422


def test_a_model_that_went_down_shows_the_unreachable_card_instead_of_running() -> None:
    def down(provider: str, base_url: str = "") -> ConnectionStatus:
        return ConnectionStatus(provider=provider, base_url=base_url, reachable=False)  # type: ignore[arg-type]

    fake = FakeHeal()
    save_settings(
        ModelSettings(provider="ollama", base_url=DEFAULT_URLS["ollama"], model="m")
    )
    response = make_client(heal=fake, check_connection=down).post(
        "/heal", data={"action": "sample:selector-drift", "max_attempts": "3"}
    )
    assert "Can't reach Ollama" in response.text
    assert fake.calls == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_web_heal.py -q -o addopts=`
Expected: most tests fail with `404 Not Found` on `/heal`.

- [ ] **Step 3: Add upload validation and storage**

Append to `src/workbench/validation.py`, and add `from pathlib import Path` to its imports:

```python
MAX_SPEC_BYTES = 200 * 1024


def validate_spec_upload(filename: str, data: bytes) -> str:
    """The text of an uploaded spec; raises ValidationError saying what is wrong."""
    name = Path(filename or "").name or "The file"
    if not name.endswith(".spec.ts"):
        raise ValidationError(
            f"{name} isn't a test file. Only .spec.ts files are supported."
        )
    if len(data) > MAX_SPEC_BYTES:
        raise ValidationError(f"{name} is larger than 200 KB.")
    if not data.strip():
        raise ValidationError(f"{name} is empty.")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError(f"{name} isn't UTF-8 text.") from None
```

Create `src/workbench/web/uploads.py`:

```python
"""Keeps a copy of an uploaded spec in the workspace; the original is never touched."""

from pathlib import Path

from workbench.config import specs_dir
from workbench.ids import slugify


def store_upload(filename: str, text: str) -> Path:
    """Write ``text`` to ``workspace/specs/uploads/<slug>.spec.ts`` and return the path."""
    stem = Path(filename).name.removesuffix(".spec.ts")
    target = specs_dir() / "uploads" / f"{slugify(stem)}.spec.ts"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target
```

- [ ] **Step 4: Write the page context and the routes**

Create `src/workbench/web/pages.py`:

```python
"""What every full page needs: the model, the active run, and the browser check."""

from typing import Any, Literal

from fastapi import Request

from workbench.samples import SAMPLES


def browsers_ready(request: Request) -> bool:
    """Chromium check: once at first use, and again on every call while it is missing."""
    state = request.app.state
    if getattr(state, "browsers_ok", False) is not True:
        state.browsers_ok = bool(state.services.browsers_ready())
    return bool(state.browsers_ok)


def page_context(request: Request, page: Literal["heal", "generate"]) -> dict[str, Any]:
    active = request.app.state.runs.active()
    return {
        "page": page,
        "model": request.app.state.model.view(),
        "active": active,
        "busy": active is not None,
        "browsers_ok": browsers_ready(request),
        "samples": list(SAMPLES.values()),
        "base_url": request.app.state.base_url,
        "result": None,
        "form": {},
    }
```

Create `src/workbench/web/routes/heal.py`:

```python
"""The Heal page, and starting a heal from a sample, an upload or a generated test."""

import threading
from html import escape
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from workbench.config import specs_dir
from workbench.events import Emit
from workbench.heal import HealRequest
from workbench.models.generate import GenerateReport
from workbench.models.heal import HealReport
from workbench.reports import load_report
from workbench.runs import Run, RunInProgress, RunRegistry
from workbench.samples import install_sample
from workbench.validation import MAX_SPEC_BYTES, ValidationError, validate_spec_upload
from workbench.web.pages import browsers_ready, page_context
from workbench.web.templating import templates
from workbench.web.uploads import store_upload
from workbench.web.views import HEAL_STEPS

router = APIRouter()


class _Refused(Exception):
    def __init__(self, target: str, message: str) -> None:
        super().__init__(message)
        self.target = target


def refuse(target: str, message: str) -> HTMLResponse:
    """A 422 whose message HTMX swaps into the element ``#target``."""
    return HTMLResponse(
        escape(message),
        status_code=422,
        headers={"HX-Retarget": f"#{target}", "HX-Reswap": "innerHTML"},
    )


def busy_notice(request: Request, active: Run) -> HTMLResponse:
    """A 409 shown in the page's notice area."""
    return templates.TemplateResponse(
        request,
        "partials/notice.html",
        {"active": active},
        status_code=409,
        headers={"HX-Retarget": "#notice", "HX-Reswap": "innerHTML"},
    )


@router.get("/heal", response_class=HTMLResponse)
def heal_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "heal.html", page_context(request, "heal")
    )


def _spec_for(
    request: Request, action: str, spec: UploadFile | None, generated: str
) -> Path:
    if action.startswith("sample:"):
        base = f"{request.app.state.base_url}/sample-site/"
        try:
            return install_sample(action.removeprefix("sample:"), base)
        except (ValueError, ValidationError) as exc:
            raise _Refused("sample-error", str(exc)) from exc
    if action == "upload":
        if spec is None or not spec.filename:
            raise _Refused("upload-error", "Choose a .spec.ts file first.")
        data = spec.file.read(MAX_SPEC_BYTES + 1)
        try:
            return store_upload(
                spec.filename, validate_spec_upload(spec.filename, data)
            )
        except ValidationError as exc:
            raise _Refused("upload-error", str(exc)) from exc
    if action == "generated":
        try:
            report = load_report(generated)
        except (ValueError, FileNotFoundError) as exc:
            raise _Refused(
                "sample-error", "That generated test no longer exists."
            ) from exc
        path = (
            specs_dir() / report.spec_name
            if isinstance(report, GenerateReport)
            else None
        )
        if path is None or not report.spec_name or not path.is_file():
            raise _Refused("sample-error", "That generated test no longer exists.")
        return path
    raise _Refused("sample-error", "Choose a sample or a file to heal.")


@router.post("/heal", response_class=HTMLResponse)
def start_heal(
    request: Request,
    action: str = Form(""),
    max_attempts: str = Form("3"),
    spec: UploadFile | None = File(None),
    generated: str = Form(""),
) -> HTMLResponse:
    runs: RunRegistry = request.app.state.runs
    if (active := runs.active()) is not None:
        return busy_notice(request, active)
    try:
        attempts = int(max_attempts)
    except ValueError:
        attempts = 0
    if not 1 <= attempts <= 5:
        return refuse("attempts-error", "Choose between 1 and 5 attempts.")
    if not browsers_ready(request):
        return templates.TemplateResponse(request, "partials/browsers_missing.html", {})
    view = request.app.state.model.view()
    if not view.ready or view.choice is None:
        return templates.TemplateResponse(
            request, "partials/unreachable.html", {"model": view}
        )
    try:
        path = _spec_for(request, action, spec, generated)
    except _Refused as exc:
        return refuse(exc.target, str(exc))

    services = request.app.state.services
    model = services.build_model(view.choice)

    def job(emit: Emit, cancel: threading.Event) -> HealReport:
        return services.heal(
            HealRequest(spec_path=path, max_attempts=attempts),
            model=model,
            emit=emit,
            cancel=cancel,
        )

    try:
        run = runs.start(
            "heal",
            path.name,
            job,
            model_label=view.model_label,
            steps=tuple(step.name for step in HEAL_STEPS),
        )
    except RunInProgress as exc:
        return busy_notice(request, exc.active)
    return templates.TemplateResponse(request, "partials/run_view.html", {"run": run})
```

In `src/workbench/app.py`, add the import `from workbench.web.routes import heal as heal_routes` and include `app.include_router(heal_routes.router)` after the runs router.

- [ ] **Step 5: Write the templates**

Create `src/workbench/web/templates/partials/banner.html`:

```jinja
{% from "partials/icons.html" import icon %}
{% macro banner(variant, title, body, cmd=None) -%}
<div class="banner banner--{{ variant }}" role="{{ 'alert' if variant == 'fail' else 'status' }}">
  {{ icon({"fail": "x", "warn": "warn"}.get(variant, "info")) }}
  <div><p class="banner__title">{{ title }}</p><p>{{ body }}</p>{% if cmd %}<code class="cmd">{{ cmd }}</code>{% endif %}</div>
</div>
{%- endmacro %}
```

Create `src/workbench/web/templates/partials/browsers_missing.html`:

```jinja
{% from "partials/banner.html" import banner %}
{{ banner("fail", "Playwright browsers aren't installed", "The test can't run until Chromium is installed.", "npx playwright install chromium") }}
```

Create `src/workbench/web/templates/partials/notice.html`:

```jinja
{% from "partials/banner.html" import banner %}
{{ banner("warn", "A run is already in progress", active.label ~ " is still running. Cancel it or wait for it to finish.") }}
```

Create `src/workbench/web/templates/partials/heal_idle.html`:

```jinja
{% from "partials/icons.html" import icon %}
<section class="card empty" aria-labelledby="idle-title">
  <span class="empty__icon">{{ icon("code", 18) }}</span>
  <h1 class="t-section" id="idle-title">Pick a sample or upload a spec</h1>
  <p class="t-small">The workbench runs the test, reads the page as it was when it failed, asks {{ model.model_label }} for a fix, applies it and re-runs the test to prove it.</p>
</section>
```

Create `src/workbench/web/templates/heal.html`:

```jinja
{% extends "base.html" %}
{% from "partials/icons.html" import icon %}
{% from "partials/banner.html" import banner %}
{% block title %}Heal · Playwright Workbench{% endblock %}
{% block model %}{% include "partials/model_pill.html" %}{% endblock %}
{% block sidebar_label %}Heal a test{% endblock %}
{% block sidebar %}
{% set locked = busy or not model.ready or not browsers_ok %}
<div class="stack stack--tight">
  <h1 class="t-page">Heal a failing test</h1>
  <p class="t-muted">Runs the spec, works out why it failed, repairs the code with a syntax-tree edit, then re-runs it to prove the fix.</p>
</div>
<form id="heal-form" class="stack stack--loose" hx-post="/heal" hx-target="#main" hx-encoding="multipart/form-data" hx-disabled-elt="find button[type=submit]">
  <section class="card card--sample" aria-labelledby="samples-title">
    <h2 class="t-caps" id="samples-title">Try a sample</h2>
    {% for sample in samples %}
    <div class="stack stack--tight">
      <p class="row t-label">{{ icon("file", 14) }} {{ sample.title }} <span class="t-mono t-faint">{{ sample.spec_file }}</span></p>
      <p class="t-small t-muted">{{ sample.description }}</p>
      <button class="btn btn--primary btn--block" type="submit" name="action" value="sample:{{ sample.name }}"{% if locked %} disabled{% endif %} aria-label="Heal the {{ sample.title }} sample">Heal sample test</button>
    </div>
    {% endfor %}
    {% if not model.ready %}<p class="t-small t-faint">Connect a model to run this.</p>{% endif %}
    <p class="field__error" id="sample-error" role="alert"></p>
  </section>
  <p class="divider">or upload your own</p>
  <div class="stack stack--tight">
    <label class="dropzone">
      {{ icon("upload", 18) }}
      <strong id="upload-name">Drop a .spec.ts file</strong>
      <span>or click to browse</span>
      <input type="file" name="spec" accept=".ts" aria-describedby="upload-error" onchange="document.getElementById('upload-name').textContent = this.files[0] ? this.files[0].name : 'Drop a .spec.ts file'">
    </label>
    <p class="field__error" id="upload-error" role="alert"></p>
  </div>
  <div class="row">
    <div class="stack stack--tight">
      <label class="field__label" for="max-attempts">Max repair attempts</label>
      <span class="field__hint">Gives up after this many failed fixes</span>
    </div>
    <div class="stepper ml-auto">
      <button type="button" aria-label="Fewer attempts" onclick="this.nextElementSibling.stepDown()">−</button>
      <input id="max-attempts" name="max_attempts" type="number" min="1" max="5" value="{{ form.max_attempts or 3 }}" aria-describedby="attempts-error">
      <button type="button" aria-label="More attempts" onclick="this.previousElementSibling.stepUp()">+</button>
    </div>
  </div>
  <p class="field__error" id="attempts-error" role="alert"></p>
  <button class="btn btn--secondary btn--block" type="submit" name="action" value="upload"{% if locked %} disabled{% endif %}>Heal uploaded file</button>
</form>
<p class="sidebar__foot t-small t-faint">Each run saves a report (diagnosis, evidence, diff, model) to workspace/reports/.</p>
{% endblock %}
{% block main %}
{% if not browsers_ok %}{% include "partials/browsers_missing.html" %}{% endif %}
{% if active and active.kind == "heal" %}{% set run = active %}{% include "partials/run_view.html" %}
{% elif result %}{% include "partials/heal_result.html" %}
{% elif not model.ready %}{% include "partials/unreachable.html" %}
{% else %}{% include "partials/heal_idle.html" %}{% endif %}
{% endblock %}
```

- [ ] **Step 6: Run the tests**

Run: `uv run python -m pytest tests/unit/test_web_heal.py -q -o addopts=`
Expected: 18 passed (the parametrized tests count 4 and 3).

If `test_heal_page_offers_both_samples_and_an_upload`'s check that the drift button is enabled is fragile, assert instead that `'value="sample:selector-drift" disabled'` is not in the HTML.

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check . && npm run lint`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/workbench/validation.py src/workbench/app.py src/workbench/web tests/unit/test_web_heal.py
git commit -m "feat: add the Heal page and start heals from samples, uploads and generated tests" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Heal results: every outcome, tabs and the diagnosis card

**Files:**

- Create:
  - `src/workbench/web/results.py`, `src/workbench/web/routes/reports.py`
  - `src/workbench/web/templates/not_found.html`
  - `src/workbench/web/templates/partials/heal_result.html`, `stepbar.html`, `diff_pane.html`, `code_pane.html`, `model_io.html`, `diagnosis_card.html`, `attempt_card.html`, `video_pane.html`, `exec_log.html`, `warnings.html`
  - `tests/unit/report_fixtures.py`, `tests/unit/test_web_reports.py`
- Modify:
  - `src/workbench/models/web.py` (add `StepbarItem`)
  - `src/workbench/web/templating.py` (add the `ansi` and `first_line` filters, and `PROVIDER_LABELS`)
  - `src/workbench/web/templates/heal.html` (show `result` before the active run)
  - `src/workbench/app.py`

**Interfaces:**

- Consumes:
  - `HealReport`, `Attempt` and the related models (Phase 2)
  - `diff_rows`, `diff_counts`, `highlight_lines`, `format_duration`, the badges (Task 3)
  - `page_context` (Task 7)
  - `clean_ansi_codes` (`workbench.text`)
- Produces:
  - `workbench.models.web.StepbarItem(title, state: Literal["done", "failed", "skipped"], time: str)`
  - `workbench.web.results`:
    - `Tab = Literal["diff", "video", "log", "model"]`, `TAB_LABELS`
    - `heal_context(report, *, attempt: int | None, tab: str) -> dict`
    - `load_or_none(report_id) -> Report | None`
  - route `GET /reports/{id}` (heal reports; Task 10 adds generate reports). Query parameters:
    - `attempt=N`
    - `tab=diff|video|log|model`
  - `tests/unit/report_fixtures.py`:
    - one builder per heal state: `healed`, `healed_after_retries`, `not_healed`, `app_defect`, `nothing_to_heal`, `cancelled`, `model_error`, `demo_healed`, `with_warnings`
    - `HEAL_STATES: dict[str, Callable[[], HealReport]]`
    - `write_all() -> dict[str, str]`, which maps each state name to a saved report id

- [ ] **Step 1: Write the report fixtures**

Create `tests/unit/report_fixtures.py`:

```python
"""One realistic saved report per result state: for the template tests and the walkthrough.

    WORKBENCH_WORKSPACE=/tmp/ws uv run python -c \
        "from tests.unit.report_fixtures import write_all; print(write_all())"
"""

from collections.abc import Callable
from typing import Any

from workbench.ids import new_run_id
from workbench.models.heal import (
    Attempt,
    FailureEvidence,
    HealingAction,
    HealingAnalysis,
    HealReport,
    RepairStrategy,
)
from workbench.models.shared import (
    FailureType,
    ModelExchange,
    PromptSection,
    Provenance,
    RunResult,
)
from workbench.reports import save_report

ORIGINAL = """import { test, expect } from '@playwright/test';

test('Contact form sends a message', async ({ page }) => {
  await page.goto('http://127.0.0.1:7860/sample-site/');
  await page.getByLabel('Name').fill('Ada Lovelace');
  await page.locator('#submit-btn').click({ timeout: 3000 });
  await expect(page.getByRole('status')).toHaveText('Submitted');
});
"""
FIXED = ORIGINAL.replace(
    "page.locator('#submit-btn')", "page.locator('[data-testid=\"submit\"]')"
)
DIFF = """--- a/contact-form.spec.ts
+++ b/contact-form.spec.ts
@@ -6 +6 @@
-  await page.locator('#submit-btn').click({ timeout: 3000 });
+  await page.locator('[data-testid="submit"]').click({ timeout: 3000 });
"""
TIMEOUT = "TimeoutError: locator.click: Timeout 3000ms exceeded.\n  - waiting for locator('#submit-btn')"


def run_result(status: str = "failed", **fields: Any) -> RunResult:
    values: dict[str, Any] = {
        "status": status,
        "duration_ms": 2400,
        "error_message": TIMEOUT if status == "failed" else "",
        "stdout": "Running 1 test using 1 worker\n",
    }
    values.update(fields)
    return RunResult(**values)


def analysis(
    failure_type: FailureType = FailureType.LOCATOR_DRIFT,
    confidence: float = 0.9,
    original: str = "page.locator('#submit-btn')",
    fixed: str = "page.locator('[data-testid=\"submit\"]')",
    strategy: RepairStrategy = RepairStrategy.SELECTOR_REPLACE,
) -> HealingAnalysis:
    return HealingAnalysis(
        failure_type=failure_type,
        failure_summary="The click on #submit-btn timed out.",
        hypothesis='The button lost its id but keeps data-testid="submit".',
        confidence_score=confidence,
        confidence_rationale="One button named Submit in the snapshot.",
        reasoning_steps=[
            "The click waits for #submit-btn, which is not on the page.",
            'The page snapshot at the failure has a button named "Submit".',
            'The button still carries data-testid="submit".',
        ],
        root_cause_evidence=[
            'button "Submit" in the page snapshot',
            "Timeout 3000ms exceeded",
        ],
        action_taken=HealingAction(
            original_code=original,
            fixed_code=fixed,
            description="Target the button by its test id.",
            repair_strategy=strategy,
        ),
    )


def exchange(
    provider: str = "ollama",
    model: str = "qwen3.6:35b-mlx",
    valid: bool = True,
    error: str = "",
) -> ModelExchange:
    return ModelExchange(
        sections=[
            PromptSection(name="Test file", chars=310),
            PromptSection(name="Error", chars=420),
            PromptSection(
                name="Page snapshot at failure", chars=12_000, original_chars=18_000
            ),
            PromptSection(name="Locator candidates", chars=180),
        ],
        raw_response='{"failure_type": "LOCATOR_DRIFT", "confidence_score": 0.9}'
        if valid
        else "Sure! Here is the fix:",
        valid=valid,
        validation_error=error,
        provenance=Provenance(
            provider=provider,
            model=model,
            prompt_name="healer",
            prompt_version="3",
            prompt_hash="3f9a1c2b7d4e5f60",
            input_tokens=4812,
            output_tokens=386,
            latency_ms=6800,
        ),
    )


def attempt(number: int, outcome: str, **fields: Any) -> Attempt:
    values: dict[str, Any] = {
        "number": number,
        "outcome": outcome,
        "evidence": FailureEvidence(error_message=TIMEOUT, source="error_context"),
        "analysis": analysis(),
        "exchange": exchange(),
        "duration_ms": 9800,
    }
    if outcome == "healed":
        values.update(
            repair_method="ast",
            rerun=run_result(
                "passed", duration_ms=2100, video_path="/nonexistent/video.webm"
            ),
        )
    if outcome == "rerun_failed":
        values.update(repair_method="ast", rerun=run_result("failed", duration_ms=3100))
    values.update(fields)
    return Attempt(**values)


def _report(name: str, status: str, **fields: Any) -> HealReport:
    values: dict[str, Any] = {
        "id": new_run_id("heal", name),
        "spec_name": "contact-form.spec.ts",
        "status": status,
        "initial_run": run_result("failed"),
        "original_code": ORIGINAL,
        "final_code": ORIGINAL,
        "classifier_hint": "TIMEOUT",
        "duration_ms": 12_700,
    }
    values.update(fields)
    return HealReport(**values)


def healed() -> HealReport:
    return _report(
        "healed", "healed", attempts=[attempt(1, "healed")], final_code=FIXED, diff=DIFF
    )


def healed_after_retries() -> HealReport:
    return _report(
        "healed-after-retries",
        "healed",
        attempts=[attempt(1, "not_applied", repair_method=None), attempt(2, "healed")],
        final_code=FIXED,
        diff=DIFF,
        duration_ms=24_900,
    )


def not_healed() -> HealReport:
    return _report(
        "not-healed",
        "not_healed",
        attempts=[
            attempt(1, "rerun_failed"),
            attempt(2, "not_applied", repair_method=None),
            attempt(
                3,
                "invalid_reply",
                analysis=None,
                exchange=exchange(valid=False, error="action_taken: Field required"),
            ),
        ],
    )


def app_defect() -> HealReport:
    bug = analysis(
        FailureType.POTENTIAL_APP_DEFECT, 0.95, "", "", RepairStrategy.STRING_REPLACE
    )
    return _report(
        "app-defect",
        "app_defect_suspected",
        spec_name="checkout.spec.ts",
        attempts=[attempt(1, "app_defect", analysis=bug)],
    )


def nothing_to_heal() -> HealReport:
    return _report(
        "nothing", "nothing_to_heal", initial_run=run_result("passed"), duration_ms=2300
    )


def cancelled() -> HealReport:
    return _report(
        "cancelled",
        "cancelled",
        attempts=[attempt(1, "rerun_failed")],
        duration_ms=14_000,
    )


def model_error() -> HealReport:
    return _report(
        "model-error",
        "error",
        error_message="The model call failed: Could not reach Ollama at http://localhost:11434/v1. Is it running?",
    )


def demo_healed() -> HealReport:
    demo = attempt(
        1, "healed", exchange=exchange(provider="demo", model="recorded-answers")
    )
    return _report("demo", "healed", attempts=[demo], final_code=FIXED, diff=DIFF)


def with_warnings() -> HealReport:
    text_fix = attempt(1, "healed", repair_method="text")
    return _report(
        "warnings",
        "healed",
        attempts=[text_fix],
        final_code=FIXED,
        diff=DIFF,
        warnings=["page_context_unavailable", "ast_unavailable"],
    )


HEAL_STATES: dict[str, Callable[[], HealReport]] = {
    "healed": healed,
    "healed_after_retries": healed_after_retries,
    "not_healed": not_healed,
    "app_defect": app_defect,
    "nothing_to_heal": nothing_to_heal,
    "cancelled": cancelled,
    "model_error": model_error,
    "demo_healed": demo_healed,
    "with_warnings": with_warnings,
}


def write_all() -> dict[str, str]:
    """Save one report per state; returns state name → report id."""
    ids = {}
    for name, build in HEAL_STATES.items():
        report = build()
        save_report(report)
        ids[name] = report.id
    return ids
```

- [ ] **Step 2: Write the failing tests**

Create `tests/unit/test_web_reports.py`:

```python
"""Every heal result state renders from its saved report."""

import pytest

from tests.unit import report_fixtures as fx
from tests.unit.web_support import make_client
from workbench.reports import save_report

pytestmark = pytest.mark.usefixtures("web_workspace")


def _page(build, query: str = "") -> str:  # type: ignore[no-untyped-def]
    report = build()
    save_report(report)
    response = make_client().get(f"/reports/{report.id}{query}")
    assert response.status_code == 200
    return response.text


def test_healed_shows_the_diff_diagnosis_and_downloads() -> None:
    html = _page(fx.healed)
    assert "pill--pass" in html and "Healed" in html and "contact-form.spec.ts" in html
    assert "code__line--del" in html and "code__line--add" in html
    assert 'class="diffstat--add">+1<' in html and 'class="diffstat--del">-1<' in html
    for label in ("Diff", "Re-run video", "Execution log", "Model I/O"):
        assert f">{label}</a>" in html
    assert 'aria-selected="true">Diff</a>' in html
    assert "LOCATOR_DRIFT" in html and "0.90" in html
    assert "Selector replaced on the syntax tree" in html
    assert "Re-run passed in 2.1s" in html
    assert "qwen3.6:35b-mlx · Ollama" in html
    assert "/spec" in html and "Download fixed spec" in html


def test_retries_show_attempt_chips_and_select_the_healed_one() -> None:
    html = _page(fx.healed_after_retries)
    assert "Fix not applied" in html and "2 attempts" in html
    assert 'aria-current="true"' in html.split("Attempt 2")[0].rsplit("<a", 1)[1]
    first = _page(fx.healed_after_retries, "?attempt=1&tab=model")
    assert "Diagnosis · attempt 1" in first


def test_model_io_lists_sections_and_truncation() -> None:
    html = _page(fx.healed, "?tab=model")
    assert "Sent to the model" in html
    assert "Page snapshot at failure" in html and "cut from 17.6 KB" in html
    assert "valid HealingAnalysis" in html
    assert "4,812 in · 386 out" in html


def test_execution_log_and_video_tabs() -> None:
    assert "TimeoutError: locator.click" in _page(fx.healed, "?tab=log")
    video = _page(fx.healed, "?tab=video")
    assert '<video class="video" controls' in video and "/video?attempt=1" in video


def test_not_healed_lists_every_attempt() -> None:
    html = _page(fx.not_healed)
    assert "Not healed" in html
    for title in ("Re-run failed", "Fix not applied", "Invalid model reply"):
        assert title in html
    assert ">Diff</a>" not in html
    assert "action_taken: Field required" in _page(
        fx.not_healed, "?attempt=3&tab=model"
    )


def test_app_defect_stops_without_changing_the_test() -> None:
    html = _page(fx.app_defect)
    assert "pill--warn" in html and "Likely app bug" in html
    assert "The test was not changed." in html
    assert "POTENTIAL_APP_DEFECT" in html
    assert ">Diff</a>" not in html


def test_nothing_to_heal_and_cancelled() -> None:
    assert "The test passed on its first run" in _page(fx.nothing_to_heal)
    assert "The file was not changed" in _page(fx.cancelled)


def test_model_failure_result_says_model_unreachable() -> None:
    html = _page(fx.model_error)
    assert "Model unreachable" in html
    assert "Could not reach Ollama at http://localhost:11434/v1" in html


def test_demo_runs_are_labelled() -> None:
    html = _page(fx.demo_healed)
    assert "Answers replayed from samples/recordings" in html
    assert '<span class="pill pill--warn">Demo</span>' in html


def test_warnings_become_banners() -> None:
    html = _page(fx.with_warnings)
    assert "Page context unavailable" in html
    assert "Repair used text replacement" in html


def test_an_unavailable_tab_falls_back_to_the_first() -> None:
    html = _page(fx.not_healed, "?tab=diff")
    assert 'aria-selected="true">Execution log</a>' in html


@pytest.mark.parametrize("report_id", ["nope", "20261004-120000-heal-missing"])
def test_unknown_reports_are_404(report_id: str) -> None:
    response = make_client().get(f"/reports/{report_id}")
    assert response.status_code == 404
    assert "No such report" in response.text
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_web_reports.py -q -o addopts=`
Expected: failures with `404` for every report.

- [ ] **Step 4: Write the result context**

Append to `src/workbench/models/web.py`:

```python
class StepbarItem(BaseModel):
    """One step in a finished run's summary bar."""

    model_config = ConfigDict(frozen=True)

    title: str
    state: Literal["done", "failed", "skipped"]
    time: str = ""
```

Create `src/workbench/web/results.py`:

```python
"""What a finished run's page shows, derived from its saved report."""

from typing import Any, Literal

from workbench.models.heal import Attempt, HealReport
from workbench.models.web import StepbarItem
from workbench.reports import Report, load_report
from workbench.web.views import HEAL_BADGES, diff_counts, diff_rows, format_duration

Tab = Literal["diff", "video", "log", "model"]
TAB_LABELS: dict[str, str] = {
    "diff": "Diff",
    "video": "Re-run video",
    "log": "Execution log",
    "model": "Model I/O",
}


def load_or_none(report_id: str) -> Report | None:
    """The saved report, or None for an unknown or malformed id."""
    try:
        return load_report(report_id)
    except (ValueError, FileNotFoundError):
        return None


def _tabs(report: HealReport) -> list[str]:
    tabs = ["diff", "video"] if report.status == "healed" else []
    tabs.append("log")
    if report.attempts:
        tabs.append("model")
    return tabs


def _attempt(report: HealReport, number: int | None) -> Attempt | None:
    if not report.attempts:
        return None
    if number is not None:
        for attempt in report.attempts:
            if attempt.number == number:
                return attempt
    healed = [a for a in report.attempts if a.outcome == "healed"]
    return healed[-1] if healed else report.attempts[-1]


def _stepbar(report: HealReport, attempt: Attempt | None) -> list[StepbarItem]:
    run = report.initial_run
    items = [
        StepbarItem(
            title="Run",
            state="failed" if run is not None and run.status == "error" else "done",
            time=format_duration(run.duration_ms) if run else "",
        )
    ]
    if attempt is None:
        return items
    exchange = attempt.exchange
    items += [
        StepbarItem(title="Evidence", state="done" if attempt.evidence else "skipped"),
        StepbarItem(
            title="Diagnose",
            state="failed" if attempt.outcome == "invalid_reply" else "done",
            time=format_duration(exchange.provenance.latency_ms) if exchange else "",
        ),
        StepbarItem(
            title="Repair",
            state="done"
            if attempt.repair_method
            else ("failed" if attempt.outcome == "not_applied" else "skipped"),
        ),
        StepbarItem(
            title="Verify",
            state="done"
            if attempt.outcome == "healed"
            else ("failed" if attempt.rerun else "skipped"),
            time=format_duration(attempt.rerun.duration_ms) if attempt.rerun else "",
        ),
    ]
    return items


def heal_context(
    report: HealReport, *, attempt: int | None, tab: str
) -> dict[str, Any]:
    """Everything the heal result templates need."""
    tabs = _tabs(report)
    selected = _attempt(report, attempt)
    rows = (
        diff_rows(report.original_code, report.final_code)
        if report.status == "healed"
        else []
    )
    added, removed = diff_counts(rows)
    count = len(report.attempts)
    return {
        "report": report,
        "badge": HEAL_BADGES[report.status],
        "tabs": [(name, TAB_LABELS[name]) for name in tabs],
        "tab": tab if tab in tabs else tabs[0],
        "attempt": selected,
        "rows": rows,
        "added": added,
        "removed": removed,
        "demo": any(
            a.exchange is not None and a.exchange.provenance.provider == "demo"
            for a in report.attempts
        ),
        "meta": f"{count} attempt{'' if count == 1 else 's'} · {format_duration(report.duration_ms)}",
        "model_failed": report.status == "error"
        and report.error_message.startswith("The model call failed"),
        "stepbar": _stepbar(report, selected),
    }
```

Add to `src/workbench/web/templating.py`, with the matching imports (`from workbench.models.settings import PROVIDER_LABELS`, `from workbench.text import clean_ansi_codes`):

```python
templates.env.filters["ansi"] = clean_ansi_codes
templates.env.filters["first_line"] = lambda text: (
    (text or "").strip().splitlines()[0] if (text or "").strip() else ""
)
templates.env.globals["PROVIDER_LABELS"] = PROVIDER_LABELS
```

- [ ] **Step 5: Write the route**

Create `src/workbench/web/routes/reports.py`:

```python
"""A finished run's page, rendered from its saved report."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from workbench.models.heal import HealReport
from workbench.web.pages import page_context
from workbench.web.results import heal_context, load_or_none
from workbench.web.templating import templates

router = APIRouter()


def not_found(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "not_found.html", page_context(request, "heal"), status_code=404
    )


@router.get("/reports/{report_id}", response_class=HTMLResponse)
def report_page(
    report_id: str, request: Request, attempt: int | None = None, tab: str = ""
) -> HTMLResponse:
    report = load_or_none(report_id)
    if isinstance(report, HealReport):
        context = page_context(request, "heal")
        context["result"] = heal_context(report, attempt=attempt, tab=tab)
        return templates.TemplateResponse(request, "heal.html", context)
    return not_found(request)
```

In `src/workbench/app.py`, include `reports_routes.router` (`from workbench.web.routes import reports as reports_routes`).

In `heal.html`'s `main` block, show `result` before the active run. Change the chain to start with `{% if result %}{% include "partials/heal_result.html" %}{% elif active and active.kind == "heal" %}…`.

- [ ] **Step 6: Write the templates**

Create `src/workbench/web/templates/not_found.html`:

```jinja
{% extends "base.html" %}
{% block title %}Not found · Playwright Workbench{% endblock %}
{% block model %}{% include "partials/model_pill.html" %}{% endblock %}
{% block main %}
<section class="card empty" aria-labelledby="missing-title">
  <h1 class="t-section" id="missing-title">No such report</h1>
  <p class="t-small">It may have been deleted from workspace/reports/. <a href="/heal">Back to Heal</a></p>
</section>
{% endblock %}
```

Create `src/workbench/web/templates/partials/heal_result.html`. It reads `result`:

```jinja
{% from "partials/icons.html" import icon %}
{% from "partials/banner.html" import banner %}
{% set report = result.report %}
<section aria-labelledby="result-title">
  <div class="result-head">
    <span class="pill pill--{{ result.badge.variant }}">{{ result.badge.label }}</span>
    {% if result.demo %}<span class="pill pill--warn">Demo</span>{% endif %}
    <h1 class="result-head__name" id="result-title">{{ report.spec_name }}</h1>
    <span class="result-head__meta">{{ result.meta }}</span>
    <div class="result-head__actions">
      {% if report.status == "healed" %}
      <button class="btn btn--secondary" type="button" data-diff="{{ report.diff }}" onclick="navigator.clipboard.writeText(this.dataset.diff); this.textContent = 'Copied'">{{ icon("copy", 14) }} Copy diff</button>
      <a class="btn btn--primary" href="/reports/{{ report.id }}/spec" download>{{ icon("download", 14) }} Download fixed spec</a>
      {% else %}
      <a class="btn btn--secondary" href="/heal">Heal again</a>
      <a class="btn btn--secondary" href="/reports/{{ report.id }}.json" download>Download report</a>
      {% endif %}
    </div>
  </div>
  {% include "partials/warnings.html" %}
  {% if report.status == "error" %}
    {% if result.model_failed %}{{ banner("fail", "Model unreachable", report.error_message) }}
    {% else %}{{ banner("fail", "The heal stopped with an error", report.error_message) }}{% endif %}
  {% elif report.status == "nothing_to_heal" %}
    {{ banner("info", "The test passed on its first run", "No changes were made. A report is still saved, marked \"nothing to heal\".") }}
  {% elif report.status == "cancelled" %}
    {{ banner("info", "The file was not changed", (report.attempts | length) ~ " attempt(s) kept in the report. The run stopped before a fix was applied.") }}
  {% elif report.status == "app_defect_suspected" %}
    {{ banner("warn", "Stopped: likely app bug", "The model thinks the app is broken, not the test. The test was not changed.") }}
  {% endif %}
  {% if report.attempts | length > 1 or report.status in ("not_healed", "cancelled") %}
  <nav class="chips" aria-label="Attempts">
    {% for a in report.attempts %}
    {% set outcome = OUTCOME_BADGES[a.outcome] %}
    <a class="chip" href="/reports/{{ report.id }}?attempt={{ a.number }}&tab={{ result.tab }}"{% if result.attempt and a.number == result.attempt.number %} aria-current="true"{% endif %}>
      {{ icon("check" if a.outcome == "healed" else "x", 14) }} Attempt {{ a.number }} <span class="chip__note">{{ outcome.title }}</span>
    </a>
    {% endfor %}
    {% if result.attempt %}<span class="t-small t-faint ml-auto">Showing attempt {{ result.attempt.number }}</span>{% endif %}
  </nav>
  {% endif %}
  {% include "partials/stepbar.html" %}
  <div class="result-grid">
    <div>
      {% if report.status == "not_healed" %}
      <div class="stack" style="margin-bottom: 20px">{% for a in report.attempts %}{% include "partials/attempt_card.html" %}{% endfor %}</div>
      {% endif %}
      <nav class="tabs" role="tablist" aria-label="Result views">
        {% for name, label in result.tabs %}
        <a class="tab" role="tab" href="/reports/{{ report.id }}?{% if result.attempt %}attempt={{ result.attempt.number }}&{% endif %}tab={{ name }}" aria-selected="{{ 'true' if name == result.tab else 'false' }}">{{ label }}</a>
        {% endfor %}
      </nav>
      <div role="tabpanel">
        {% if result.tab == "diff" %}{% include "partials/diff_pane.html" %}
        {% elif result.tab == "video" %}{% include "partials/video_pane.html" %}
        {% elif result.tab == "log" %}{% include "partials/exec_log.html" %}
        {% else %}{% include "partials/model_io.html" %}{% endif %}
      </div>
    </div>
    {% if result.attempt %}{% include "partials/diagnosis_card.html" %}{% endif %}
  </div>
</section>
```

Create `src/workbench/web/templates/partials/warnings.html`:

```jinja
{% from "partials/banner.html" import banner %}
{% if "playwright_browsers_missing" in report.warnings %}{{ banner("fail", "Playwright browsers aren't installed", "The test can't run until Chromium is installed.", "npx playwright install chromium") }}{% endif %}
{% if "page_context_unavailable" in report.warnings %}{{ banner("warn", "Page context unavailable", "The page in page.goto() didn't load, so the diagnosis used the error log only. Expect lower confidence.") }}{% endif %}
{% if "ast_unavailable" in report.warnings %}{{ banner("info", "Repair used text replacement", "Node.js wasn't found, so the syntax-tree (ts-morph) step was skipped and the fix was applied as a text edit.") }}{% endif %}
```

Create `src/workbench/web/templates/partials/stepbar.html`:

```jinja
{% from "partials/icons.html" import icon %}
<ol class="stepbar" aria-label="Steps">
  {% for item in result.stepbar %}
  <li class="stepbar__item stepbar__item--{{ item.state }}">{{ icon({"done": "check", "failed": "x"}.get(item.state, "circle-dashed"), 14, item.state) }} {{ item.title }} {% if item.time %}<span class="t-mono t-faint">{{ item.time }}</span>{% endif %}</li>
  {% endfor %}
</ol>
```

Create `src/workbench/web/templates/partials/diff_pane.html`:

```jinja
{% from "partials/icons.html" import icon %}
<section class="code" aria-label="Diff">
  <div class="code__head">{{ icon("file", 14) }} {{ result.report.spec_name }}
    <span class="code__head-meta"><span class="diffstat--add">+{{ result.added }}</span> <span class="diffstat--del">-{{ result.removed }}</span></span>
  </div>
  <pre class="code__body">{% for row in result.rows %}<span class="code__line code__line--diff{% if row.kind != 'same' %} code__line--{{ row.kind }}{% endif %}"><span class="code__num">{{ row.old_no or "" }}</span><span class="code__num">{{ row.new_no or "" }}</span><span class="code__mark">{{ {"add": "+", "del": "-"}.get(row.kind, "") }}</span><span>{{ row.html | safe }}</span></span>
{% endfor %}</pre>
</section>
```

Create `src/workbench/web/templates/partials/code_pane.html`. It is used with `{% with title=..., code=..., meta=... %}`:

```jinja
{% from "partials/icons.html" import icon %}
<section class="code" aria-label="{{ title }}">
  <div class="code__head">{{ icon("file", 14) }} {{ title }}<span class="code__head-meta">{{ meta }}</span></div>
  <pre class="code__body">{% for line in views.highlight_lines(code) %}<span class="code__line"><span class="code__num">{{ loop.index }}</span><span>{{ line | safe }}</span></span>
{% endfor %}</pre>
</section>
```

Create `src/workbench/web/templates/partials/video_pane.html`:

```jinja
{% set rerun = result.attempt.rerun if result.attempt else None %}
{% if rerun and rerun.video_path %}
<figure class="stack">
  <video class="video" controls preload="metadata" src="/reports/{{ result.report.id }}/video?attempt={{ result.attempt.number }}"></video>
  <figcaption class="row t-small t-muted">Verification re-run of attempt {{ result.attempt.number }}, with each action captioned · {{ rerun.duration_ms | duration }}
    <a class="ml-auto" href="/reports/{{ result.report.id }}/video?attempt={{ result.attempt.number }}" download>Download video</a></figcaption>
</figure>
{% else %}
<p class="card t-small t-muted">No video was recorded for this run.</p>
{% endif %}
```

Create `src/workbench/web/templates/partials/exec_log.html`:

```jinja
{% from "partials/icons.html" import icon %}
{% set report = result.report %}
<section class="code" aria-label="Execution log">
  <div class="code__head">{{ icon("file", 14) }} Execution log</div>
  <div class="log__body">
    <div class="log__line--muted">$ npx playwright test {{ report.spec_name }}</div>
    {% if report.initial_run %}<div>{{ report.initial_run.output | ansi }}</div>{% endif %}
    {% for a in report.attempts %}
    <div class="log__line--step">[attempt {{ a.number }}] {{ OUTCOME_BADGES[a.outcome].title }}</div>
    {% if a.rerun %}<div>{{ a.rerun.output | ansi }}</div>{% endif %}
    {% endfor %}
  </div>
</section>
```

Create `src/workbench/web/templates/partials/model_io.html`:

```jinja
{% from "partials/icons.html" import icon %}
{% set exchange = result.attempt.exchange if result.attempt else None %}
{% if exchange %}
<div class="stack">
  <div class="card" style="padding: 0">
    <table class="io-table">
      <thead><tr><th scope="col">Sent to the model</th><th scope="col">Size</th><th scope="col">Note</th></tr></thead>
      <tbody>
        {% for section in exchange.sections %}
        <tr><td>{{ section.name }}</td><td class="t-mono">{{ section.chars | size }}</td><td class="t-faint">{% if section.truncated %}cut from {{ section.original_chars | size }}{% else %}whole{% endif %}</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <section class="code" aria-label="Model reply">
    <div class="code__head">{{ icon("code", 14) }} Received · response.json
      <span class="code__head-meta">{{ exchange.provenance.output_tokens }} tokens · {{ exchange.provenance.latency_ms | duration }} ·
        {% if exchange.valid %}<span class="diffstat--add">valid HealingAnalysis</span>{% else %}<span class="diffstat--del">invalid: {{ exchange.validation_error or "did not match the schema" }}</span>{% endif %}</span>
    </div>
    <pre class="code__body">{% for line in exchange.raw_response.splitlines() %}<span class="code__line"><span class="code__num">{{ loop.index }}</span><span>{{ line }}</span></span>
{% endfor %}</pre>
  </section>
</div>
{% else %}
<p class="card t-small t-muted">No model call was made.</p>
{% endif %}
```

Create `src/workbench/web/templates/partials/attempt_card.html`. It reads `a`:

```jinja
{% set outcome = OUTCOME_BADGES[a.outcome] %}
{% set action = a.analysis.action_taken if a.analysis else None %}
<article class="attempt" aria-label="Attempt {{ a.number }}">
  <div class="attempt__head">
    <span class="t-label">{{ outcome.title }}</span>
    {% if action %}<span class="tag">{{ STRATEGY_LABELS[action.repair_strategy.value] }}</span>{% endif %}
    <span class="pill pill--{{ outcome.variant }}">{{ outcome.label }}</span>
  </div>
  {% if action and (action.original_code or action.fixed_code) %}<p class="snippet">{{ action.original_code }} → {{ action.fixed_code }}</p>{% endif %}
  <p class="t-small t-muted">
    {% if a.outcome == "healed" %}Re-run passed in {{ a.rerun.duration_ms | duration }}.
    {% elif a.outcome == "rerun_failed" %}The fix was applied but the test still failed: {{ a.rerun.error_message | first_line }}
    {% elif a.outcome == "not_applied" %}The code the model wanted to replace isn't in the file, so nothing was changed. The next attempt starts from the same code.
    {% elif a.outcome == "invalid_reply" %}The response didn't match the HealingAnalysis schema. See Model I/O for the raw text.
    {% elif a.outcome == "app_defect" %}The model thinks the app is broken, so the test was left as it is.
    {% else %}Stopped before the fix was applied.{% endif %}
  </p>
</article>
```

Create `src/workbench/web/templates/partials/diagnosis_card.html`:

```jinja
{% from "partials/icons.html" import icon %}
{% set a = result.attempt %}
{% set analysis = a.analysis %}
{% set p = a.exchange.provenance if a.exchange else None %}
<aside class="card side-card" aria-labelledby="diagnosis-title">
  <h2 class="t-caps" id="diagnosis-title">Diagnosis · attempt {{ a.number }}</h2>
  {% if analysis %}
  <dl class="kv kv--plain"><dt>Failure type</dt><dd><span class="code-badge">{{ analysis.failure_type.value }}</span></dd></dl>
  <dl class="kv kv--plain"><dt>Confidence</dt><dd class="meter"><span class="meter__bar"><span class="meter__fill" style="width: {{ (analysis.confidence_score * 100) | round }}%"></span></span>{{ "%.2f" | format(analysis.confidence_score) }}</dd></dl>
  <p class="t-small">{{ analysis.hypothesis }}</p>
  {% if analysis.reasoning_steps %}<h3 class="t-caps">Why</h3><ol class="reasons">{% for step in analysis.reasoning_steps %}<li>{{ step }}</li>{% endfor %}</ol>{% endif %}
  {% if analysis.root_cause_evidence %}<h3 class="t-caps">Evidence</h3><ul class="evidence">{% for item in analysis.root_cause_evidence %}<li>{{ item }}</li>{% endfor %}</ul>{% endif %}
  {% else %}
  <p class="t-small t-muted">The reply could not be read as a diagnosis. See Model I/O.</p>
  {% endif %}
  <h3 class="t-caps">Repair</h3>
  <p class="t-small">
    {% if a.repair_method == "ast" %}{{ STRATEGY_LABELS[analysis.action_taken.repair_strategy.value] }} on the syntax tree (ts-morph)
    {% elif a.repair_method == "text" %}Applied as a text edit
    {% elif a.outcome == "app_defect" %}No change: the test was left as it is
    {% elif a.outcome == "not_applied" %}The code to replace wasn't in the file
    {% else %}No fix was applied{% endif %}
  </p>
  <h3 class="t-caps">Verification</h3>
  {% if a.rerun and a.outcome == "healed" %}<p class="ok-line">{{ icon("check", 14) }} Re-run passed in {{ a.rerun.duration_ms | duration }}</p>
  {% elif a.rerun %}<p class="fail-line">{{ icon("x", 14) }} Re-run failed: {{ a.rerun.error_message | first_line }}</p>
  {% else %}<p class="t-small t-faint">Not re-run</p>{% endif %}
  {% if p %}
  <div class="meta-foot">
    <dl class="kv"><dt>Model</dt><dd>{{ p.model }} · {{ PROVIDER_LABELS.get(p.provider, p.provider) }}</dd></dl>
    <dl class="kv"><dt>Prompt</dt><dd>{{ p.prompt_name }} v{{ p.prompt_version }} · {{ p.prompt_hash[:7] }}</dd></dl>
    <dl class="kv"><dt>Tokens</dt><dd>{{ "{:,}".format(p.input_tokens) }} in · {{ "{:,}".format(p.output_tokens) }} out</dd></dl>
    <dl class="kv"><dt>LLM latency</dt><dd>{{ p.latency_ms | duration }}</dd></dl>
    {% if p.provider == "demo" %}<p class="t-small t-faint">Answers replayed from samples/recordings — not a live model.</p>{% endif %}
  </div>
  {% endif %}
</aside>
```

Append the Model I/O table style to `src/workbench/web/static/css/app.css`:

```css

.io-table {
  width: 100%;
  border-collapse: collapse;
  font: var(--type-body-small);
}
.io-table th {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-default);
  text-align: left;
  font: var(--type-label-caps);
  letter-spacing: var(--tracking-label-caps);
  text-transform: uppercase;
  color: var(--text-tertiary);
}
.io-table td {
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-default);
}
.io-table tr:last-child td {
  border-bottom: 0;
}
```

- [ ] **Step 7: Run the tests**

Run: `uv run python -m pytest tests/unit/test_web_reports.py -q -o addopts=`
Expected: 13 passed (the 404 test counts 2).

`test_demo_runs_are_labelled` expects "Answers replayed from samples/recordings". The diagnosis footer says it with an em dash; keep the asserted phrase exactly.

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check . && npm run lint`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/workbench/models/web.py src/workbench/web src/workbench/app.py tests/unit/report_fixtures.py tests/unit/test_web_reports.py
git commit -m "feat: render every heal result: diff, re-run video, log, model I/O and diagnosis" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Downloads: report JSON, fixed spec and the re-run video

**Files:**

- Modify: `src/workbench/web/routes/reports.py`
- Create: `tests/unit/test_web_downloads.py`

**Interfaces:**

- Consumes:
  - `report_path()`, `load_or_none()` (Task 8)
  - `runs_dir()`
  - `HealReport`, `GenerateReport`
- Produces:
  - `GET /reports/{id}.json`: the saved report, as a download
  - `GET /reports/{id}/spec`: the fixed spec (heal) or the generated spec, as a download
  - `GET /reports/{id}/video?attempt=N`: the verification re-run's video, served inline (Range requests work through `FileResponse`), only from inside `workspace/runs/`

These three routes must be declared **above** `GET /reports/{report_id}` in `reports.py`. Otherwise `/reports/<id>.json` matches the page route, whose id check rejects it with a 404.

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_web_downloads.py`:

```python
"""Report, spec and video downloads, and that forged ids and paths get nothing."""

import json

import pytest

from tests.unit import report_fixtures as fx
from tests.unit.web_support import make_client
from workbench.config import runs_dir
from workbench.models.generate import GenerateReport
from workbench.reports import save_report

pytestmark = pytest.mark.usefixtures("web_workspace")

WEBM = b"\x1aE\xdf\xa3" + b"\x00" * 2048


def test_report_json_downloads() -> None:
    report = fx.healed()
    save_report(report)
    response = make_client().get(f"/reports/{report.id}.json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    assert json.loads(response.text)["id"] == report.id


def test_spec_download_is_the_fixed_or_original_code() -> None:
    healed, failed = fx.healed(), fx.not_healed()
    save_report(healed)
    save_report(failed)
    client = make_client()
    fixed = client.get(f"/reports/{healed.id}/spec")
    assert fixed.text == fx.FIXED
    assert 'filename="contact-form.spec.ts"' in fixed.headers["content-disposition"]
    assert client.get(f"/reports/{failed.id}/spec").text == fx.ORIGINAL


def test_generated_spec_downloads() -> None:
    report = GenerateReport(
        id="20261004-120000-generate-contact",
        url="http://x/",
        scenario="s",
        status="not_run",
        spec_name="a-user.spec.ts",
        code="test('x', () => {});\n",
    )
    save_report(report)
    response = make_client().get(f"/reports/{report.id}/spec")
    assert response.text == report.code
    assert 'filename="a-user.spec.ts"' in response.headers["content-disposition"]


def test_rerun_video_streams_from_the_runs_folder() -> None:
    video = runs_dir() / "r1" / "test-results" / "video.webm"
    video.parent.mkdir(parents=True)
    video.write_bytes(WEBM)
    healed = fx.attempt(1, "healed")
    assert healed.rerun is not None
    healed.rerun.video_path = str(video)
    report = fx.healed().model_copy(update={"attempts": [healed]})
    save_report(report)
    client = make_client()
    whole = client.get(f"/reports/{report.id}/video?attempt=1")
    assert whole.status_code == 200
    assert whole.headers["content-type"] == "video/webm"
    assert whole.content == WEBM
    part = client.get(
        f"/reports/{report.id}/video?attempt=1", headers={"Range": "bytes=0-3"}
    )
    assert part.status_code == 206
    assert part.content == WEBM[:4]


@pytest.mark.parametrize("video_path", ["/etc/hosts", "RUNS/../outside.webm"])
def test_video_outside_the_runs_folder_is_not_served(video_path: str) -> None:
    outside = runs_dir().parent / "outside.webm"
    outside.write_bytes(WEBM)
    healed = fx.attempt(1, "healed")
    assert healed.rerun is not None
    healed.rerun.video_path = video_path.replace("RUNS", str(runs_dir()))
    report = fx.healed().model_copy(update={"attempts": [healed]})
    save_report(report)
    assert make_client().get(f"/reports/{report.id}/video?attempt=1").status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/reports/nope.json",
        "/reports/nope/spec",
        "/reports/nope/video",
        "/reports/20261004-120000-heal-missing.json",
        "/reports/20261004-120000-heal-missing/video?attempt=1",
    ],
)
def test_downloads_reject_forged_ids(path: str) -> None:
    assert make_client().get(path).status_code == 404


def test_missing_attempt_or_video_is_404() -> None:
    report = fx.not_healed()
    save_report(report)
    client = make_client()
    assert client.get(f"/reports/{report.id}/video?attempt=9").status_code == 404
    assert client.get(f"/reports/{report.id}/video?attempt=2").status_code == 404
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_web_downloads.py -q -o addopts=`
Expected: failures with `404` where `200` is expected.

- [ ] **Step 3: Write the routes**

In `src/workbench/web/routes/reports.py`, add these imports:

```python
from pathlib import Path

from fastapi import HTTPException, Response
from fastapi.responses import FileResponse

from workbench.config import runs_dir
from workbench.models.generate import GenerateReport
from workbench.reports import report_path
```

and these routes **above** `report_page`:

```python
def _found(report_id: str) -> HealReport | GenerateReport:
    report = load_or_none(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="No such report")
    return report


def _attachment(name: str) -> str:
    safe = Path(name).name.replace('"', "") or "spec.ts"
    return f'attachment; filename="{safe}"'


@router.get("/reports/{report_id}.json")
def report_json(report_id: str) -> FileResponse:
    _found(report_id)
    return FileResponse(
        report_path(report_id),
        media_type="application/json",
        filename=f"{report_id}.json",
    )


@router.get("/reports/{report_id}/spec")
def report_spec(report_id: str) -> Response:
    report = _found(report_id)
    if isinstance(report, HealReport):
        code = report.final_code or report.original_code
    else:
        code = report.code
    if not code:
        raise HTTPException(status_code=404, detail="This run has no spec")
    return Response(
        code,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": _attachment(report.spec_name)},
    )


@router.get("/reports/{report_id}/video")
def report_video(report_id: str, attempt: int = 1) -> FileResponse:
    report = _found(report_id)
    found = (
        next((a for a in report.attempts if a.number == attempt), None)
        if isinstance(report, HealReport)
        else None
    )
    recorded = found.rerun.video_path if found is not None and found.rerun else None
    if not recorded:
        raise HTTPException(status_code=404, detail="No video for this attempt")
    path = Path(recorded).resolve()
    if not path.is_relative_to(runs_dir().resolve()) or not path.is_file():
        raise HTTPException(status_code=404, detail="No video for this attempt")
    return FileResponse(
        path, media_type="video/webm", content_disposition_type="inline"
    )
```

- [ ] **Step 4: Run the tests**

Run: `uv run python -m pytest tests/unit/test_web_downloads.py tests/unit/test_web_reports.py -q -o addopts=`
Expected: all pass (11 download tests and 13 report tests).

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check .`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/workbench/web/routes/reports.py tests/unit/test_web_downloads.py
git commit -m "feat: download reports, fixed specs and re-run videos, only from the workspace" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: The Generate page, its results, "Run test" and "Heal this test"

**Files:**

- Create:
  - `src/workbench/web/jobs.py`, `src/workbench/web/routes/generate.py`
  - `src/workbench/web/templates/generate.html`
  - `src/workbench/web/templates/partials/generate_idle.html`, `generate_result.html`, `context_card.html`
  - `tests/unit/test_web_generate.py`
- Modify:
  - `src/workbench/web/results.py` (add `generate_context`)
  - `src/workbench/web/routes/reports.py` (render generate reports)
  - `src/workbench/app.py`
  - `tests/unit/report_fixtures.py` (add the generate states)

**Interfaces:**

- Consumes:
  - `generate()`, `GenerateRequest`, `GenerateReport` (Phase 2)
  - `validate_and_sanitize_url`, `validate_description`, `ValidationError`
  - `GENERATE_SCENARIO` (Phase 3)
  - `run_test` via `Services.run_test`
  - `refuse`, `busy_notice` (Task 7)
  - `page_context`, `browsers_ready` (Task 7)
  - `locators_in`, `GENERATE_BADGES` (Task 3)
- Produces:
  - `workbench.web.jobs.run_generated(report, *, run_test, emit, cancel) -> GenerateReport`: runs the saved spec, updates `run` and `status`, and saves the report under the same id
  - `workbench.web.results.generate_context(report) -> dict`
  - routes:
    - `GET /generate`, with `?example=contact-form|checkout`
    - `POST /generate`, with the fields `url`, `scenario` and `run_after` (a checkbox)
    - `POST /generate/run`, with the field `report`
  - `GET /reports/{id}` renders generate reports in `generate.html`
  - `report_fixtures`: `generate_passed`, `generate_failed`, `generate_not_run`, `generate_error`, and `GENERATE_STATES`, which `write_all()` also saves

- [ ] **Step 1: Add the generate fixtures**

Append to `tests/unit/report_fixtures.py` (add `from workbench.models.generate import ContextSummary, GenerateReport` to its imports):

```python
GENERATED = """import { test, expect } from '@playwright/test';

test('A user can send the contact form', async ({ page }) => {
  await page.goto('http://127.0.0.1:7860/sample-site/');
  await page.getByLabel('Name').fill('Ada Lovelace');
  await page.getByRole('button', { name: 'Submit' }).click();
  await expect(page.getByRole('status')).toHaveText('Submitted');
});
"""


def _generated(name: str, status: str, **fields: Any) -> GenerateReport:
    values: dict[str, Any] = {
        "id": new_run_id("generate", name),
        "url": "http://127.0.0.1:7860/sample-site/",
        "scenario": "A user can send the contact form",
        "status": status,
        "spec_name": "a-user-can-send-the-contact-form.spec.ts",
        "code": GENERATED,
        "context": ContextSummary(
            url="http://127.0.0.1:7860/sample-site/",
            snapshot_lines=42,
            locator_candidates=["getByRole('button', { name: 'Submit' })"] * 18,
        ),
        "exchange": exchange(),
        "duration_ms": 8400,
    }
    values.update(fields)
    return GenerateReport(**values)


def generate_passed() -> GenerateReport:
    return _generated("passed", "passed", run=run_result("passed", duration_ms=2200))


def generate_failed() -> GenerateReport:
    return _generated("failed", "failed", run=run_result("failed"))


def generate_not_run() -> GenerateReport:
    return _generated("not-run", "not_run")


def generate_error() -> GenerateReport:
    return _generated(
        "error",
        "error",
        spec_name="",
        code="",
        exchange=None,
        error_message="The model call failed: Ollama at http://localhost:11434/v1 did not answer within 300 seconds.",
    )


GENERATE_STATES: dict[str, Callable[[], GenerateReport]] = {
    "generate_passed": generate_passed,
    "generate_failed": generate_failed,
    "generate_not_run": generate_not_run,
    "generate_error": generate_error,
}
```

and change `write_all()` to loop over `{**HEAL_STATES, **GENERATE_STATES}`, with the type `dict[str, Callable[[], HealReport | GenerateReport]]`.

- [ ] **Step 2: Write the failing tests**

Create `tests/unit/test_web_generate.py`:

```python
"""The Generate page, starting a generation, the result states, Run test and Heal this test."""

import threading
from typing import Any

import pytest

from tests.unit import report_fixtures as fx
from tests.unit.web_support import make_client
from workbench.config import specs_dir
from workbench.events import EventSink
from workbench.generate import GenerateRequest
from workbench.models.generate import GenerateReport
from workbench.models.settings import DEMO_MODEL, ModelSettings
from workbench.reports import load_report, save_report
from workbench.settings import save_settings

pytestmark = pytest.mark.usefixtures("web_workspace")


@pytest.fixture(autouse=True)
def demo_model() -> None:
    save_settings(ModelSettings(provider="demo", model=DEMO_MODEL))


class FakeGenerate:
    def __init__(self) -> None:
        self.calls: list[GenerateRequest] = []

    def __call__(
        self,
        request: GenerateRequest,
        *,
        model: Any,
        emit: Any = None,
        cancel: Any = None,
    ) -> GenerateReport:
        self.calls.append(request)
        events = EventSink("g", emit)
        events.step("context", "active", request.url)
        events.step("context", "done", "18 locator candidates")
        events.step("model", "active")
        events.step("model", "done", "8 lines → a-user.spec.ts")
        report = fx.generate_not_run()
        save_report(report)
        return report


def _wait(client) -> None:  # type: ignore[no-untyped-def]
    run = client.app.state.runs.active()
    if run is not None:
        run.wait(5)


def test_generate_page_has_the_form_and_examples() -> None:
    html = make_client().get("/generate").text
    assert "Generate a test" in html
    assert (
        'name="url"' in html
        and 'name="scenario"' in html
        and 'name="run_after"' in html
    )
    assert "Your test will appear here" in html
    assert 'href="/generate?example=contact-form"' in html
    assert '<a href="/generate" aria-current="page">Generate</a>' in html


def test_an_example_fills_the_form_with_the_sample_site() -> None:
    html = make_client().get("/generate?example=contact-form").text
    assert 'value="http://127.0.0.1:7860/sample-site/"' in html
    assert "A user can send the contact form</textarea>" in html


def test_generation_starts_with_the_form_values() -> None:
    fake = FakeGenerate()
    client = make_client(generate=fake)
    response = client.post(
        "/generate",
        data={
            "url": "http://127.0.0.1:7860/sample-site/",
            "scenario": "A user can send the contact form",
        },
    )
    assert response.status_code == 200 and "sse-connect=" in response.text
    _wait(client)
    assert fake.calls[0] == GenerateRequest(
        url="http://127.0.0.1:7860/sample-site/",
        scenario="A user can send the contact form",
        run_after=False,
    )


@pytest.mark.parametrize(
    ("form", "target", "message"),
    [
        (
            {"url": "example.com/login", "scenario": "x"},
            "#url-error",
            "Enter a full URL, starting with http:// or https://",
        ),
        (
            {"url": "http://x/", "scenario": "   "},
            "#scenario-error",
            "Description cannot be empty",
        ),
    ],
)
def test_bad_input_is_refused_inline(
    form: dict[str, str], target: str, message: str
) -> None:
    fake = FakeGenerate()
    response = make_client(generate=fake).post("/generate", data=form)
    assert response.status_code == 422
    assert response.headers["HX-Retarget"] == target
    assert message in response.text
    assert fake.calls == []


def test_passed_result_shows_code_context_and_run() -> None:
    report = fx.generate_passed()
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    assert "pill--pass" in html and "Passed" in html
    assert "a-user-can-send-the-contact-form.spec.ts" in html
    assert '<span class="tok-fn">getByRole</span>' in html
    assert "Page context used" in html and ">42<" in html and ">18<" in html
    assert "getByLabel(&#39;Name&#39;)" in html
    assert "Passed in Chromium · 2.2s" in html
    assert f"/reports/{report.id}/spec" in html


def test_failed_result_offers_heal_this_test() -> None:
    report = fx.generate_failed()
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    assert "Run failed" in html
    assert 'name="action" value="generated"' in html
    assert f'name="generated" value="{report.id}"' in html
    assert "Heal this test" in html


def test_not_run_result_offers_run_test() -> None:
    report = fx.generate_not_run()
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    assert "Not run" in html and "Run test" in html
    assert 'hx-post="/generate/run"' in html


def test_error_result_says_model_unreachable() -> None:
    report = fx.generate_error()
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    assert "Model unreachable" in html and "did not answer within 300 seconds" in html


def test_run_test_runs_the_saved_spec_and_updates_the_report() -> None:
    report = fx.generate_not_run()
    save_report(report)
    spec = specs_dir() / report.spec_name
    spec.write_text(report.code, encoding="utf-8")
    seen: list[Any] = []

    def fake_run(path: Any, **kwargs: Any) -> Any:
        seen.append(path)
        return fx.run_result("passed", duration_ms=2000)

    client = make_client(run_test=fake_run)
    response = client.post("/generate/run", data={"report": report.id})
    assert response.status_code == 200 and "sse-connect=" in response.text
    _wait(client)
    assert seen == [spec]
    updated = load_report(report.id)
    assert isinstance(updated, GenerateReport)
    assert updated.status == "passed" and updated.run is not None


def test_run_test_refuses_an_unknown_report() -> None:
    response = make_client().post("/generate/run", data={"report": "nope"})
    assert response.status_code == 404


def test_generate_page_resumes_an_active_generation() -> None:
    gate = threading.Event()

    def slow(request: GenerateRequest, **kwargs: Any) -> GenerateReport:
        gate.wait(5)
        return FakeGenerate()(request, **kwargs)

    client = make_client(generate=slow)
    client.post(
        "/generate", data={"url": "http://x/", "scenario": "s", "run_after": "1"}
    )
    run = client.app.state.runs.active()  # type: ignore[attr-defined]
    html = client.get("/generate").text
    assert f'sse-connect="/runs/{run.id}/events"' in html
    assert (
        "Generate test</button>" in html
        and "disabled"
        in html.split("Generate test</button>")[0].rsplit("<button", 1)[1]
    )
    gate.set()
    run.wait(5)
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/unit/test_web_generate.py -q -o addopts=`
Expected: failures with `404` on `/generate`.

- [ ] **Step 4: Write the job, the result context and the routes**

Create `src/workbench/web/jobs.py`:

```python
"""Small jobs the web app runs that are not a whole pipeline."""

import threading
from collections.abc import Callable

from workbench.config import specs_dir
from workbench.events import Emit, EventSink
from workbench.models.generate import GenerateReport
from workbench.models.shared import RunResult
from workbench.reports import save_report


def run_generated(
    report: GenerateReport,
    *,
    run_test: Callable[..., RunResult],
    emit: Emit,
    cancel: threading.Event,
) -> GenerateReport:
    """Run a generated spec that was not run, and record the result on its report."""
    events = EventSink(report.id, emit)
    spec = specs_dir() / report.spec_name
    events.step("execute", "active", f"npx playwright test {spec.name}")
    result = run_test(spec, cancel=cancel)
    if result.passed:
        status, state, detail = "passed", "done", "Passed"
    elif result.status == "cancelled":
        status, state, detail = "cancelled", "skipped", "Cancelled"
    else:
        first = result.error_message.strip().splitlines()
        status, state, detail = "failed", "failed", first[0] if first else result.status
    events.step("execute", state, detail)  # type: ignore[arg-type]
    updated = report.model_copy(update={"run": result, "status": status})
    save_report(updated)
    events.done(status)
    return updated
```

Append to `src/workbench/web/results.py`. Add the imports `from workbench.models.generate import GenerateReport` and `from workbench.web.views import GENERATE_BADGES, locators_in`:

```python
def generate_context(report: GenerateReport) -> dict[str, Any]:
    """Everything the generate result templates need."""
    exchange = report.exchange
    parts = []
    if exchange is not None:
        parts.append(f"Generated in {format_duration(exchange.provenance.latency_ms)}")
    if report.run is not None:
        parts.append(f"ran in {format_duration(report.run.duration_ms)}")
    return {
        "report": report,
        "badge": GENERATE_BADGES[report.status],
        "meta": " · ".join(parts),
        "locators": locators_in(report.code),
        "lines": len(report.code.splitlines()),
        "demo": exchange is not None and exchange.provenance.provider == "demo",
        "model_failed": report.status == "error"
        and report.error_message.startswith("The model call failed"),
    }
```

Create `src/workbench/web/routes/generate.py`:

```python
"""The Generate page, starting a generation, and running a generated spec."""

import threading

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from workbench.config import specs_dir
from workbench.events import Emit
from workbench.generate import GenerateRequest
from workbench.models.generate import GenerateReport
from workbench.runs import RunInProgress, RunRegistry
from workbench.samples import GENERATE_SCENARIO
from workbench.validation import (
    ValidationError,
    validate_and_sanitize_url,
    validate_description,
)
from workbench.web.jobs import run_generated
from workbench.web.pages import browsers_ready, page_context
from workbench.web.results import load_or_none
from workbench.web.routes.heal import busy_notice, refuse
from workbench.web.templating import templates

router = APIRouter()

# label, page under /sample-site/, scenario. Demo can only answer the first.
EXAMPLES: dict[str, tuple[str, str, str]] = {
    "contact-form": ("Contact form", "", GENERATE_SCENARIO),
    "checkout": (
        "Checkout",
        "checkout.html",
        "A shopper enters their email and places an order",
    ),
}
GENERATE_STEP_NAMES = ("context", "model", "execute")


@router.get("/generate", response_class=HTMLResponse)
def generate_page(request: Request, example: str = "") -> HTMLResponse:
    context = page_context(request, "generate")
    context["examples"] = EXAMPLES
    if example in EXAMPLES:
        _, page, scenario = EXAMPLES[example]
        url = f"{request.app.state.base_url}/sample-site/{page}"
        context["form"] = {"url": url, "scenario": scenario, "run_after": True}
    return templates.TemplateResponse(request, "generate.html", context)


@router.post("/generate", response_class=HTMLResponse)
def start_generate(
    request: Request,
    url: str = Form(""),
    scenario: str = Form(""),
    run_after: str = Form(""),
) -> HTMLResponse:
    runs: RunRegistry = request.app.state.runs
    if (active := runs.active()) is not None:
        return busy_notice(request, active)
    try:
        clean_url = validate_and_sanitize_url(url)
    except ValidationError:
        return refuse(
            "url-error", "Enter a full URL, starting with http:// or https://"
        )
    try:
        clean_scenario = validate_description(scenario)
    except ValidationError as exc:
        return refuse("scenario-error", str(exc))
    if not browsers_ready(request):
        return templates.TemplateResponse(request, "partials/browsers_missing.html", {})
    view = request.app.state.model.view()
    if not view.ready or view.choice is None:
        return templates.TemplateResponse(
            request, "partials/unreachable.html", {"model": view}
        )
    services = request.app.state.services
    model = services.build_model(view.choice)
    generate_request = GenerateRequest(
        url=clean_url, scenario=clean_scenario, run_after=bool(run_after)
    )

    def job(emit: Emit, cancel: threading.Event) -> GenerateReport:
        return services.generate(
            generate_request, model=model, emit=emit, cancel=cancel
        )

    steps = (
        GENERATE_STEP_NAMES if generate_request.run_after else GENERATE_STEP_NAMES[:2]
    )
    try:
        run = runs.start(
            "generate", clean_scenario, job, model_label=view.model_label, steps=steps
        )
    except RunInProgress as exc:
        return busy_notice(request, exc.active)
    return templates.TemplateResponse(request, "partials/run_view.html", {"run": run})


@router.post("/generate/run", response_class=HTMLResponse)
def run_generated_spec(request: Request, report: str = Form("")) -> HTMLResponse:
    saved = load_or_none(report)
    if not isinstance(saved, GenerateReport) or not saved.spec_name:
        raise HTTPException(status_code=404, detail="No such generated test")
    if not (specs_dir() / saved.spec_name).is_file():
        raise HTTPException(status_code=404, detail="The generated spec file is gone")
    runs: RunRegistry = request.app.state.runs
    run_test = request.app.state.services.run_test

    def job(emit: Emit, cancel: threading.Event) -> GenerateReport:
        return run_generated(saved, run_test=run_test, emit=emit, cancel=cancel)

    try:
        run = runs.start("generate", saved.spec_name, job, steps=("execute",))
    except RunInProgress as exc:
        return busy_notice(request, exc.active)
    return templates.TemplateResponse(request, "partials/run_view.html", {"run": run})
```

In `src/workbench/web/routes/reports.py`, import `generate_context` and render generate reports in `report_page`, before the final `return not_found(request)`:

```python
if isinstance(report, GenerateReport):
    context = page_context(request, "generate")
    context["examples"] = {}
    context["result"] = generate_context(report)
    context["form"] = {
        "url": report.url,
        "scenario": report.scenario,
        "run_after": True,
    }
    return templates.TemplateResponse(request, "generate.html", context)
```

In `src/workbench/app.py`, include `generate_routes.router` (`from workbench.web.routes import generate as generate_routes`).

- [ ] **Step 5: Write the templates**

Create `src/workbench/web/templates/generate.html`:

```jinja
{% extends "base.html" %}
{% block title %}Generate · Playwright Workbench{% endblock %}
{% block model %}{% include "partials/model_pill.html" %}{% endblock %}
{% block sidebar_label %}Generate a test{% endblock %}
{% block sidebar %}
{% set locked = busy or not model.ready or not browsers_ok %}
<div class="stack stack--tight">
  <h1 class="t-page">Generate a test</h1>
  <p class="t-muted">Describe a user flow. The page opens in Chromium and its accessibility tree steers the model toward role-based locators.</p>
</div>
<form class="stack stack--loose" hx-post="/generate" hx-target="#main" hx-disabled-elt="find button[type=submit]">
  <div class="field">
    <label class="field__label" for="target-url">Target URL</label>
    <input class="input input--mono" id="target-url" name="url" value="{{ form.url or '' }}" placeholder="{{ base_url }}/sample-site/" aria-describedby="url-error">
    <p class="field__error" id="url-error" role="alert"></p>
  </div>
  <div class="field">
    <label class="field__label" for="scenario">Scenario</label>
    <textarea class="textarea" id="scenario" name="scenario" aria-describedby="scenario-error">{{ form.scenario or '' }}</textarea>
    <p class="field__error" id="scenario-error" role="alert"></p>
  </div>
  <label class="check"><input type="checkbox" name="run_after" value="1"{% if form.get("run_after", True) %} checked{% endif %}> Run the test after generating</label>
  <button class="btn btn--primary btn--block" type="submit"{% if locked %} disabled{% endif %}>Generate test</button>
  {% if not model.ready %}<p class="t-small t-faint">Connect a model to run this.</p>{% endif %}
</form>
{% if examples %}
<div class="stack stack--tight">
  <h2 class="t-caps">Examples</h2>
  <div class="row">{% for key, example in examples.items() %}<a class="chip chip--example" href="/generate?example={{ key }}">{{ example[0] }}</a>{% endfor %}</div>
</div>
{% endif %}
<p class="sidebar__foot t-small t-faint">If a generated test fails, open it in Heal with one click.</p>
{% endblock %}
{% block main %}
{% if not browsers_ok %}{% include "partials/browsers_missing.html" %}{% endif %}
{% if result %}{% include "partials/generate_result.html" %}
{% elif active and active.kind == "generate" %}{% set run = active %}{% include "partials/run_view.html" %}
{% elif not model.ready %}{% include "partials/unreachable.html" %}
{% else %}{% include "partials/generate_idle.html" %}{% endif %}
{% endblock %}
```

Create `src/workbench/web/templates/partials/generate_idle.html`:

```jinja
{% from "partials/icons.html" import icon %}
<section class="card empty" aria-labelledby="idle-title">
  <span class="empty__icon">{{ icon("code", 18) }}</span>
  <h1 class="t-section" id="idle-title">Your test will appear here</h1>
  <p class="t-small">Enter a URL and describe the flow. The page's accessibility tree and locator candidates are collected first, then the model writes the spec.</p>
</section>
```

Create `src/workbench/web/templates/partials/generate_result.html`:

```jinja
{% from "partials/icons.html" import icon %}
{% from "partials/banner.html" import banner %}
{% set report = result.report %}
<section aria-labelledby="result-title">
  <div class="result-head">
    <span class="pill pill--{{ result.badge.variant }}">{{ result.badge.label }}</span>
    {% if result.demo %}<span class="pill pill--warn">Demo</span>{% endif %}
    <h1 class="result-head__name" id="result-title">{{ report.spec_name or "No test written" }}</h1>
    <span class="result-head__meta">{{ result.meta }}</span>
    <div class="result-head__actions">
      {% if report.code %}
      <button class="btn btn--secondary" type="button" data-code="{{ report.code }}" onclick="navigator.clipboard.writeText(this.dataset.code); this.textContent = 'Copied'">{{ icon("copy", 14) }} Copy</button>
      {% endif %}
      {% if report.status == "not_run" %}
      <form hx-post="/generate/run" hx-target="#main"><input type="hidden" name="report" value="{{ report.id }}"><button class="btn btn--primary" type="submit">{{ icon("play", 14) }} Run test</button></form>
      {% elif report.status == "failed" %}
      <form hx-post="/heal" hx-target="#main"><input type="hidden" name="action" value="generated"><input type="hidden" name="generated" value="{{ report.id }}"><input type="hidden" name="max_attempts" value="3"><button class="btn btn--primary" type="submit">Heal this test</button></form>
      {% elif report.code %}
      <a class="btn btn--primary" href="/reports/{{ report.id }}/spec" download>{{ icon("download", 14) }} Download spec</a>
      {% endif %}
    </div>
  </div>
  {% include "partials/warnings.html" %}
  {% if report.status == "error" %}
    {% if result.model_failed %}{{ banner("fail", "Model unreachable", report.error_message) }}
    {% else %}{{ banner("fail", "The generation stopped with an error", report.error_message) }}{% endif %}
  {% elif report.status == "cancelled" %}{{ banner("info", "Cancelled", "The generation stopped before it finished.") }}
  {% endif %}
  {% if report.code %}
  <div class="result-grid">
    {% with title="workspace/specs/" ~ report.spec_name, code=report.code, meta=result.lines ~ " lines" %}{% include "partials/code_pane.html" %}{% endwith %}
    {% include "partials/context_card.html" %}
  </div>
  {% endif %}
</section>
```

Create `src/workbench/web/templates/partials/context_card.html`:

```jinja
{% from "partials/icons.html" import icon %}
{% set report = result.report %}
{% set p = report.exchange.provenance if report.exchange else None %}
<aside class="card side-card" aria-labelledby="context-title">
  <h2 class="t-caps" id="context-title">Page context used</h2>
  {% if report.context %}
  <dl class="kv kv--plain"><dt>Snapshot lines</dt><dd>{{ report.context.snapshot_lines }}</dd></dl>
  <dl class="kv kv--plain"><dt>Locator candidates</dt><dd>{{ report.context.locator_candidates | length }}</dd></dl>
  <dl class="kv kv--plain"><dt>Console errors</dt><dd>{{ report.context.console_errors }}</dd></dl>
  <dl class="kv kv--plain"><dt>Failed requests</dt><dd>{{ report.context.failed_requests }}</dd></dl>
  {% endif %}
  {% if result.locators %}
  <h3 class="t-caps">Locators in the test</h3>
  <ul class="evidence">{% for locator in result.locators %}<li>{{ locator }}</li>{% endfor %}</ul>
  {% endif %}
  <h3 class="t-caps">Run</h3>
  {% if report.run and report.run.passed %}<p class="ok-line">{{ icon("check", 14) }} Passed in Chromium · {{ report.run.duration_ms | duration }}</p>
  {% elif report.run %}<p class="fail-line">{{ icon("x", 14) }} {{ report.run.error_message | first_line or report.run.status }}</p>
  {% else %}<p class="t-small t-faint">Not run</p>{% endif %}
  {% if p %}
  <div class="meta-foot">
    <dl class="kv"><dt>Model</dt><dd>{{ p.model }} · {{ PROVIDER_LABELS.get(p.provider, p.provider) }}</dd></dl>
    <dl class="kv"><dt>Prompt</dt><dd>{{ p.prompt_name }} v{{ p.prompt_version }} · {{ p.prompt_hash[:7] }}</dd></dl>
    <dl class="kv"><dt>Tokens</dt><dd>{{ "{:,}".format(p.input_tokens) }} in · {{ "{:,}".format(p.output_tokens) }} out</dd></dl>
    {% if p.provider == "demo" %}<p class="t-small t-faint">Answers replayed from samples/recordings — not a live model.</p>{% endif %}
  </div>
  {% endif %}
</aside>
```

`warnings.html` reads `report.warnings`, which works for generate reports as well, because the template sets `report`.

- [ ] **Step 6: Run the tests**

Run: `uv run python -m pytest tests/unit/test_web_generate.py -q -o addopts=`
Expected: 13 passed (the parametrized refusal test counts 2).

Run: `uv run python -m pytest -q -o addopts= && uv run mypy && uv run ruff check . && npm run lint`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/workbench/web src/workbench/app.py tests/unit/report_fixtures.py tests/unit/test_web_generate.py
git commit -m "feat: add the Generate page, its result states, Run test and Heal this test" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Guides: AGENTS, roadmap and changelog

**Files:**

- Modify: `AGENTS.md`, `ROADMAP.md`, `CHANGELOG.md`

- [ ] **Step 1: Update `AGENTS.md`**

In the Layout block, add these lines under `src/workbench/`, after `config.py`:

```text
├── __main__.py         launcher: `uv run workbench` serves http://127.0.0.1:7860 and opens it
├── app.py              create_app(services): the FastAPI app factory
├── runs.py             RunRegistry: one background run at a time, with replayable events
├── web/                routes/, templates/, static/ (tokens.css, app.css, fonts, vendored htmx), views, SSE
```

In the Commands block, add, after the `uv sync` line:

```bash
uv run workbench                           # start the app on http://127.0.0.1:7860
```

Add to the Rules:

```markdown
- UI: the templates in `src/workbench/web/templates/` are the source of truth; colours and type come only from `static/css/tokens.css` (one variable per Figma variable). No JavaScript files beyond the vendored htmx and its SSE extension.
- Routes call pipelines and the model client only through `workbench.web.services.Services`; route tests build the app with `tests/unit/web_support.make_client()` and fakes.
```

- [ ] **Step 2: Update `ROADMAP.md`**

- Move "FastAPI + HTMX web UI matching the Figma design" from `Now` to `Done`, with Phase `4` and Plan `[Phase 4](docs/superpowers/plans/2026-10-04-v2-phase-4-web-ui.md)`.
- Move "Integration and UI suites, axe, coverage gate, strict mypy, CI rework" from `Next` to `Now`, with status `🔭 Planned`, Phase `5` and Plan `Phase 5 plan (to be written)`.
- Add to `Later`:

  ```markdown
  - Stream Playwright's own output into the live log; today the log is built from pipeline events, because the runner reads the JSON report after the run.
  - A run history page listing past reports (reports are already saved and linkable).
  ```

- [ ] **Step 3: Update `CHANGELOG.md`**

Under `## [Unreleased]`, add to `### Added`:

```markdown
- A local web app (FastAPI, Jinja and HTMX, no front-end build): `uv run workbench`
  opens Heal and Generate on http://127.0.0.1:7860.
- Live progress over server-sent events, with cancel; every finished run has a
  page at `/reports/<id>` with the diff, a captioned re-run video, the execution
  log and the Model I/O.
- A model menu that tests a server, lists its models and saves the choice.
- Downloads for the report JSON, the fixed or generated spec, and the video.
```

- [ ] **Step 4: Lint and commit**

Run: `npm run lint`
Expected: clean.

```bash
git add AGENTS.md ROADMAP.md CHANGELOG.md
git commit -m "docs: record the web UI in the guides, roadmap and changelog" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Figma updates (spec §5.3), run by the controller

This task edits the Figma file, not the repository. The controller runs it with the Figma MCP and the `/figma-use` skill. Subagents don't. The templates already implement all four changes, so this task only brings the design file in line.

- [ ] **Step 1: Apply the four changes** in file `eL5DUZmc85ESpusNSmxDkA`:
  1. In every "Model popover" frame (for example `5:223`, and the one on the states board), change the footnote "Defaults come from .env. Changes here last for this session." to "Saved on this machine." and add a full-width primary "Save" button above it.
  2. On every Heal screen, the sidebar's "Try a sample" card shows two samples: *Selector drift* (`contact-form.spec.ts`, "The submit button lost its id. The healer finds it by its test id and the test passes again.") and *App bug* (`checkout.spec.ts`, "Checkout fails on the server. The healer reports a likely app bug and leaves the test alone."), each with a "Heal sample test" button.
  3. Add a frame "Heal — stopped: likely app bug", duplicated from "Heal — not healed" (`4:181`). Give it:
     - a warn pill "Likely app bug" in the result header
     - a warn banner "Stopped: likely app bug" with the text "The model thinks the app is broken, not the test. The test was not changed."
     - the diagnosis card showing `POTENTIAL_APP_DEFECT` and its evidence
     - tabs: Execution log and Model I/O only
  4. On "Heal — healed" (`2:100`) and "Heal — healed on retry · Model I/O" (`6:157`), add a "Re-run video" tab after "Diff". Add one frame showing that tab selected: a video area with the caption "Verification re-run of attempt 1, with each action captioned · 2.1s" and a "Download video" link.

- [ ] **Step 2: If the Figma MCP refuses (plan call limit), record it and continue**

If `use_figma` is rate-limited, add a row to `ROADMAP.md` `Now`:

```markdown
| Figma file: the four §5.3 changes (the templates already implement them) | 🚧 Blocked: Figma MCP call limit | 4 | Phase 4 Task 12 |
```

Commit it (`docs: note the pending Figma updates`). Note the block in the ledger as a ruling, and go on to Task 13. The spec says the templates are the source of truth after this phase.

---

### Task 13: Verify the phase and walk through every state

**Files:** none change unless a check fails.

- [ ] **Step 1: Run every gate from a clean environment**

```bash
rm -rf .venv node_modules workspace
uv sync --group dev && npm ci && npx playwright install chromium
uv run python -m pytest -q -o addopts= --cov
uv run python -m pytest tests/integration -v -o addopts=
npm run lint && npm run type-check
```

Expected: everything passes. Coverage is reported, and `src/workbench/web/` is covered by the route tests.

- [ ] **Step 2: Start the app on a scratch workspace with every result state saved**

```bash
export WORKBENCH_WORKSPACE="$(mktemp -d)/ws" WORKBENCH_PORT=7861
uv run python -c "from tests.unit.report_fixtures import write_all; import json; print(json.dumps(write_all(), indent=2))"
uv run uvicorn --factory workbench.app:create_app --host 127.0.0.1 --port 7861
```

Run uvicorn in the background (not `python -m workbench`, which opens the user's browser). Open `http://127.0.0.1:7861/` in the in-app browser at a 1440×900 viewport.

- [ ] **Step 3: Walk through the spec §5.2 states and compare each with the Figma screenshots**

Tick each state below after seeing it. Save a screenshot of each to the scratchpad, and record any difference from `docs/superpowers/plans/phase-4-figma/*.png` in the ledger. Fix real defects through a fix round; note intentional differences.

| Area | State | How to reach it |
| --- | --- | --- |
| Global | Model connected | Model menu → Ollama → `qwen3.6:35b-mlx` → Save (the user's preferred model) |
| Global | Demo | Model menu → Demo → Save |
| Global | Not connected | Model menu → LM Studio with nothing running (or a bad port) → the pill is red after Save is refused, or remove `settings.json` with no server running |
| Heal | Idle | `/heal` with a connected model |
| Heal | Running (live steps + log) | Demo → "Heal sample test" on *Selector drift* |
| Heal | Healed | the finished Demo drift run, and the `healed` fixture |
| Heal | Healed after retries | the `healed_after_retries` fixture: attempt chips |
| Heal | Not healed | the `not_healed` fixture: three attempt cards |
| Heal | Stopped: likely app bug | Demo → "Heal sample test" on *App bug*, and the `app_defect` fixture |
| Heal | Nothing to heal | the `nothing_to_heal` fixture |
| Heal | Cancelled | start the drift sample with Ollama and press Cancel during Diagnose, and the `cancelled` fixture |
| Heal | Model unreachable | the `model_error` fixture, and `/heal` with no server and no saved choice |
| Attempt outcomes | Healed · Re-run failed · Fix not applied · Invalid model reply | the `not_healed` and `healed_after_retries` fixtures |
| Result tabs | Diff · Re-run video · Execution log · Model I/O | a real Demo heal (its video plays) |
| Generate | Empty | `/generate` |
| Generate | Generating | Demo → example "Contact form" → Generate |
| Generate | Passed | the finished Demo generation, and the `generate_passed` fixture |
| Generate | Generated, not run | untick "Run the test after generating", then "Run test" |
| Generate | Run failed → Heal | the `generate_failed` fixture → "Heal this test" |
| Banners | Browsers missing · Page context unavailable · Repair used text replacement | the `with_warnings` fixture; browsers missing by starting with `PLAYWRIGHT_BROWSERS_PATH=/nonexistent` |
| Input errors | Invalid URL · Not a spec file · File too large | Generate with `example.com/login`; upload a `.txt`; upload a 300 KB `.spec.ts` |

Also check:

- **Keyboard:** Tab reaches the model pill; Enter opens the menu; Esc closes it; the result tabs are reachable and announce their selected state. A focus ring is always visible.
- **Width:** the layout holds at 1280px with no horizontal scroll.
- **Reload:** a page reload during a run shows the live run.
- **Second tab:** a second tab shows the same run, and its start buttons are disabled.

- [ ] **Step 4: Real-model smoke test through the UI (Ollama, Qwen3.6)**

With Ollama running, choose Ollama with `qwen3.6:35b-mlx` in the model menu and save. Then check:

- **Heal:** heal the *Selector drift* sample. Expected result: "Healed", with the model's own fix in the diff.
- **App bug:** heal the *App bug* sample. Expected result: "Likely app bug".
- **Generate:** run the Contact form example. Expected result: "Passed".

Record each outcome and its time. If a call reaches the 300 s limit, the run header should have said "the model is still thinking" before the error. Record that too.

- [ ] **Step 5: Ask before pushing**

Show the user `git log --oneline` for the Phase 4 commits, the walkthrough results and the screenshots. Ask whether to push `v2`, and do not push without a yes.
