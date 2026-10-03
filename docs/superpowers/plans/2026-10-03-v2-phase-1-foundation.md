# v2 Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the repository into a `workbench` package with a clean test layout, delete every subsystem v2 drops, and add the roadmap, changelog and agent guides, without changing what the generate and heal pipelines do.

**Architecture:** This phase only moves, renames and deletes code. Source modules move from `src/<area>` and `schemas/` into `src/workbench/`, their imports are rewritten by a one-off codemod, and paths are centralised in `workbench/config.py`. The Gradio UI, the services layer, the CLI, the vision pipeline, the JSONL tracer, the benchmarks and Docker are deleted. The pipelines keep their current behaviour; Phase 2 rewrites them.

**Tech Stack:** Python 3.11, uv, hatchling, pytest, ruff, mypy, Node 20, ts-morph, Playwright 1.57, ESLint, markdownlint-cli2.

**Spec:** [docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md](../specs/2026-10-03-v2-showcase-simplification-design.md)

## Plan series

The spec is delivered in six phases. Each phase gets its own plan, written once the previous phase has landed, because each phase builds on the code shapes the previous one produces. `ROADMAP.md` tracks all of them.

| Phase | Plan | Status |
| --- | --- | --- |
| 1. Foundation | this document | ready |
| 2. Engine | `<date>-v2-phase-2-engine.md` | written when Phase 1 lands |
| 3. Providers and samples | `<date>-v2-phase-3-providers.md` | written when Phase 2 lands |
| 4. Web UI | `<date>-v2-phase-4-web-ui.md` | written when Phase 3 lands |
| 5. Quality gates | `<date>-v2-phase-5-quality-gates.md` | written when Phase 4 lands |
| 6. Showcase | `<date>-v2-phase-6-showcase.md` | written when Phase 5 lands |

## Global Constraints

- Python `>=3.11`; Playwright pinned at `1.57.0` (Python) and `^1.57.0` (npm).
- Ruff line length 88, double quotes; the existing rule set in `pyproject.toml` stays.
- No behaviour change to generation or healing in this phase. The prompts' content and versions stay as they are, apart from deleting `vision`.
- Runtime output paths stay as they are in this phase (`tests/generated/`, `tests/artifacts/`, `test-results/`). Phase 2 moves them into `workspace/`.
- The LLM router, model registry, `.env` loading and `python-dotenv` stay until Phase 3 replaces the LLM layer. Only `gradio` is removed from the dependencies here.
- mypy settings stay as they are; strict mode arrives in Phase 5 with the rewritten code.
- Commits follow Conventional Commits and end with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- `ROADMAP.md` and `CHANGELOG.md` are updated in the same commit as the work they describe.
- All work is committed on branch `v2`. Nothing is pushed without asking the user.

## Review Focus

1. **Paths after the move.** Prompts, the ts-morph script and the project root used to be found with `Path(__file__).parent.parent.parent`, which is wrong one level deeper. Expected: every path comes from `workbench.config` and points at a real file. Pinned by `tests/unit/test_config.py` (Task 3).
2. **Node resolving `ts-morph` from the script's new location** under `src/workbench/heal/`. Expected: Node walks up to the root `node_modules` and the script still edits code. Pinned by `test_ast_repair_script_resolves_ts_morph_from_the_package` (Task 3).
3. **Stale imports hidden by `except Exception`.** The router and the runner imported the tracer inside `try/except Exception`, so a leftover legacy import would fail silently at runtime. Expected: no file imports `src.*`, `schemas.*`, `benchmarks`, `gradio` or the tracer. Pinned by `tests/unit/test_layout.py` (Task 3).
4. **The package imported from outside the repository root.** pytest and editors import `workbench` without `sys.path` tricks. Expected: `import workbench.config` works from any directory after `uv sync`. Pinned by Task 3 Step 12.
5. **The integration test still finds the sample site** after it moves to `samples/site/`. Expected: the generate-then-heal integration test passes against the moved site. Pinned by Task 4 Step 6.

---

## File map

| Action | Path | Responsibility after this phase |
| --- | --- | --- |
| Create | `ROADMAP.md` | Status of every v2 item |
| Create | `CHANGELOG.md` | Keep a Changelog history |
| Create | `src/workbench/__init__.py` | Package marker and version |
| Create | `src/workbench/config.py` | All filesystem locations |
| Create | `src/workbench/generate/__init__.py` | Package marker |
| Move | `src/healing/*.py` → `src/workbench/heal/*.py` (except `runner.py`) | Heal modules (unchanged logic) |
| Move | `src/healing/runner.py` → `src/workbench/runner.py` | Playwright subprocess |
| Move | `scripts/ast_repair.js` → `src/workbench/heal/ast_repair.js` | ts-morph script |
| Move | `src/agents/generator.py` → `src/workbench/generate/pipeline.py` | Generation (unchanged logic) |
| Move | `src/context/*` → `src/workbench/context/*` | Page context collection |
| Move | `src/llm/*` → `src/workbench/llm/*` | Router, client, registry, policies (until Phase 3) |
| Move | `src/utils/llm.py` → `src/workbench/llm/parsing.py` | Parsing LLM output |
| Move | `src/utils/prompt_loader.py` → `src/workbench/llm/prompts.py` | Loading prompts |
| Move | `src/utils/validation.py` → `src/workbench/validation.py` | Input checks |
| Move | `src/utils/formatting.py` → `src/workbench/text.py` | `clean_ansi_codes()` only |
| Move | `schemas/{healing,generation,shared,artifacts}.py` → `src/workbench/models/{heal,generate,shared,artifacts}.py` | Pydantic contracts |
| Move | `prompts/*` → `src/workbench/prompts/*` | Prompt files and manifest |
| Move | `tests/unit_test_*.py` → `tests/unit/test_*.py` | Unit tests |
| Move | `tests/e2e/{e2e_test_pipeline.py,fake_llm.py}` → `tests/integration/{test_pipeline.py,fake_llm.py}` | Integration test |
| Move | `tests/e2e/site/` → `samples/site/` | Sample web app |
| Create | `tests/unit/test_config.py`, `tests/unit/test_layout.py` | Guards for this restructure |
| Rewrite | `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md` | v2 guides |
| Create | `CLAUDE.md` | Points agents at `AGENTS.md` |
| Modify | `pyproject.toml`, `package.json`, `eslint.config.cjs`, `tsconfig.json`, `playwright.e2e.config.ts`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `.gitignore` | Tooling for the new layout |
| Delete | see Task 2 and Task 5 | Dropped subsystems and docs |

---

### Task 1: Roadmap and changelog

**Files:**

- Create: `ROADMAP.md`
- Create: `CHANGELOG.md`

**Interfaces:**

- Produces: `ROADMAP.md` with sections `Now`, `Next`, `Later`, `Done`, `Removed`; `CHANGELOG.md` with an `[Unreleased]` section that later tasks append to.

- [ ] **Step 1: Create `ROADMAP.md`**

```markdown
# Roadmap

Tracks the v2 redesign described in the
[v2 spec](docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md).
Status: ✅ Done · 🚧 In progress · 🔭 Planned · 🗑️ Removed. Update this file in
the same commit as the work it describes.

## Now

| Item | Status | Phase | Plan |
| --- | --- | --- | --- |
| `workbench` package and test layout | 🚧 In progress | 1 | [Phase 1](docs/superpowers/plans/2026-10-03-v2-phase-1-foundation.md) |
| Remove the Gradio UI, services, CLI, vision pipeline, tracer, benchmarks and Docker | 🚧 In progress | 1 | [Phase 1](docs/superpowers/plans/2026-10-03-v2-phase-1-foundation.md) |
| Roadmap, changelog and agent guides | 🚧 In progress | 1 | [Phase 1](docs/superpowers/plans/2026-10-03-v2-phase-1-foundation.md) |

## Next

| Item | Status | Phase |
| --- | --- | --- |
| Evidence from Playwright's `error-context.md` and a per-run output folder | 🔭 Planned | 2 |
| Accessibility snapshot through `aria_snapshot()` instead of CDP | 🔭 Planned | 2 |
| Model I/O capture and schema-constrained model output | 🔭 Planned | 2 |
| One heal loop with live events, cancellation and the app-defect guard | 🔭 Planned | 2 |
| One report per run, all runtime output in `workspace/` | 🔭 Planned | 2 |
| LM Studio, Ollama and Demo providers chosen in the UI; no `.env` | 🔭 Planned | 3 |
| Bundled samples: selector drift and app bug | 🔭 Planned | 3 |
| FastAPI + HTMX web UI matching the Figma design | 🔭 Planned | 4 |
| Integration and UI suites, axe, coverage gate, strict mypy, CI rework | 🔭 Planned | 5 |
| README, GIF, architecture and decision docs, 2.0.0 release | 🔭 Planned | 6 |

## Later

- CI integration: a GitHub Action that heals failing specs and opens a pull request, or flags a suspected app bug.
- The classifier treats "waiting for locator" timeouts as locator problems rather than slow pages.
- Cloud providers (Anthropic, OpenAI).
- A run history page.
- A benchmark built from a deliberately mutated sample app.
- Comparing heals with Playwright's own healer agent.
- Dark mode.
- Renaming the repository.

## Done

Nothing yet.

## Removed

| Item | Reason | Phase |
| --- | --- | --- |
```

- [ ] **Step 2: Create `CHANGELOG.md`**

```markdown
# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

Work towards 2.0.0, tracked in [ROADMAP.md](ROADMAP.md).

### Added

- `ROADMAP.md` and this changelog.

## [1.0.0] - 2026-09-28

The Gradio workbench: generation, healing and vision pipelines, benchmarks
and JSONL tracing.
```

- [ ] **Step 3: Lint the new files**

Run: `npx markdownlint-cli2 ROADMAP.md CHANGELOG.md`
Expected: `Summary: 0 issues in 0 files`. The `Removed` table has a header and no rows yet; if markdownlint reports MD055/MD056 for it, add the first row now from Task 2 Step 11 instead of leaving it empty.

- [ ] **Step 4: Commit**

```bash
git add ROADMAP.md CHANGELOG.md
git commit -m "docs: add the v2 roadmap and changelog" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Delete the subsystems v2 drops

**Files:**

- Delete: `src/app.py`, `src/services/`, `src/agents/healer.py`, `src/agents/__init__.py`, `src/observability/`, `src/utils/browser.py`, `src/utils/logger.py`, `prompts/vision.md`, `schemas/evaluation.py`, `benchmarks/`, `Dockerfile`, `.dockerignore`, `.github/workflows/docker.yml`, `docs/docker.md`
- Delete: `tests/unit_test_evaluation.py`, `tests/unit_test_information_architecture.py`, `tests/unit_test_workbench_eval.py`, `tests/unit_test_observability.py`
- Modify: `src/healing/__init__.py`, `src/healing/runner.py`, `src/llm/router.py`, `src/utils/formatting.py`, `schemas/__init__.py`, `schemas/artifacts.py`, `schemas/generation.py`, `prompts/manifest.json`
- Modify: `tests/unit_test_provenance.py`, `tests/unit_test_visibility.py`, `tests/unit_test_healing.py`, `tests/e2e/e2e_test_pipeline.py`
- Modify: `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `ROADMAP.md`, `CHANGELOG.md`

**Interfaces:**

- Consumes: nothing.
- Produces: the same public functions as before, minus the deleted ones. `src.agents.generator.generate_test_script(url, feature_description) -> GenerationDecision` and `src.healing.attempt_healing(test_file, max_retries=3) -> str` keep their signatures.

- [ ] **Step 1: Delete the files nothing will keep**

```bash
git rm -r -q src/app.py src/services src/agents/healer.py src/agents/__init__.py \
  src/observability src/utils/browser.py src/utils/logger.py prompts/vision.md \
  schemas/evaluation.py benchmarks Dockerfile .dockerignore \
  .github/workflows/docker.yml docs/docker.md \
  tests/unit_test_evaluation.py tests/unit_test_information_architecture.py \
  tests/unit_test_workbench_eval.py tests/unit_test_observability.py
```

- [ ] **Step 2: Remove the tracer from the CLI heal loop in `src/healing/__init__.py`**

Inside `attempt_healing`, make these exact replacements.

Replace the docstring's first paragraphs:

```python
    """Orchestrate the full healing pipeline for a failing test file.

    Non-streaming version intended for CLI use (``python -m src.healing``).
    The streaming Gradio version lives in src.services.healing_service.

    Starts and ends a tracer session so CLI runs produce the same spans as
    UI runs.  If no tracer has been configured, NullTracer no-ops all calls.
```

with:

```python
    """Orchestrate the full healing pipeline for a failing test file.

    Used by the integration test. Phase 2 replaces it with the streaming
    heal pipeline.
```

Delete the line `from src.observability import get_tracer`.

Replace:

```python
    tracer = get_tracer()
    trace_id = tracer.start_session("healing")
    _success = False

    try:
```

with:

```python
    try:
```

Delete both lines whose content is `_success = True` (one is indented 12 spaces, the other 16).

Replace:

```python
    finally:
        tracer.end_session(trace_id, success=_success)
```

with:

```python
    finally:
        logger.debug("Healing session finished for %s", test_file)
```

- [ ] **Step 3: Remove the tracer from `src/healing/runner.py`**

Replace:

```python
    # Observability — record subprocess span; silently no-op when no session is active.
    try:
        from src.observability import get_tracer

        get_tracer().record_subprocess(
            command=command,
            exit_code=exit_code,
            latency_ms=latency_ms,
        )
    except Exception:
        # Observability must never break the main path.
        logger.debug("Could not record subprocess span", exc_info=True)

    return run_result
```

with:

```python
    logger.debug(
        "%s exited with %s after %d ms", command, exit_code, latency_ms
    )
    return run_result
```

- [ ] **Step 4: Remove the tracer from `src/llm/router.py`**

Replace:

```python
        # Observability — record span; silently no-op when no session is active.
        try:
            from src.observability import get_tracer

            get_tracer().record_llm_response(response)
        except Exception:
            # Observability must never break the main path.
            logger.debug("Could not record LLM response span", exc_info=True)

        return response
```

with:

```python
        return response
```

- [ ] **Step 5: Reduce `src/utils/formatting.py` to `clean_ansi_codes()`**

Replace the whole file with:

```python
"""Text helpers shared by the data contracts."""

import re

_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def clean_ansi_codes(text: str) -> str:
    """Remove ANSI escape sequences from text.

    Args:
        text: Input string containing potential ANSI codes.

    Returns:
        The string without escape sequences ("" for empty input).
    """
    if not text:
        return ""
    return _ANSI_ESCAPE.sub("", text)
```

- [ ] **Step 6: Remove dropped data contracts**

In `schemas/artifacts.py`, delete the `TraceMetadata` class and its line in the module docstring (`TraceMetadata   — per-LLM-call observability record ...`). Keep `ContextSnapshot`.

In `schemas/generation.py`, delete the `VisionDecision` class (from `class VisionDecision(ProvenanceRecord):` to the end of that class).

Replace `schemas/__init__.py` with:

```python
"""Pydantic data contracts for LLM inputs, outputs and artifacts."""

from .artifacts import ContextSnapshot
from .generation import GenerationDecision, GenerationResult
from .healing import (
    Evidence,
    ExecutionTimeline,
    HealingAction,
    HealingAnalysis,
    HealingDecision,
    RepairStrategy,
    TimelineStep,
)
from .shared import FailureType, LLMConfig, ProvenanceRecord, RunResult

__all__ = [
    "ContextSnapshot",
    "Evidence",
    "ExecutionTimeline",
    "FailureType",
    "GenerationDecision",
    "GenerationResult",
    "HealingAction",
    "HealingAnalysis",
    "HealingDecision",
    "LLMConfig",
    "ProvenanceRecord",
    "RepairStrategy",
    "RunResult",
    "TimelineStep",
]
```

In `prompts/manifest.json`, delete the `"vision": { ... }` entry and the comma before it, so `prompts` holds only `generator` and `healer`.

- [ ] **Step 7: Remove tests for deleted code**

In `tests/unit_test_provenance.py`:

- change `from schemas.generation import GenerationDecision, VisionDecision` to `from schemas.generation import GenerationDecision`;
- delete the function `_make_vision_decision`;
- delete the classes `TestVisionDecisionToMarkdown` and `TestListArtifacts`;
- in `TestEmitDecision`, delete the method `test_vision_decision_file_has_correct_prefix`;
- in the module docstring, delete the lines about `VisionDecision.to_markdown()` and `list_artifacts()`.

In `tests/unit_test_visibility.py`, delete the class `TestGetModelInfo` and the docstring line `get_model_info()  — model registry markdown table`.

In `tests/unit_test_healing.py`, delete the class `TestAttemptHealingTracerSession` and the comment line above it (`# ── attempt_healing tracer session ──...`).

In `tests/e2e/e2e_test_pipeline.py`, delete the line `from src.observability import configure_tracer` and the line `configure_tracer(PROJECT_ROOT / "logs")`. In the module docstring, change `re-run them for the HTML report, JUnit XML and traces.` to `re-run them for the HTML report and JUnit XML.`

- [ ] **Step 8: Check nothing still imports a deleted module**

Run:

```bash
grep -rnE "src\.observability|src\.services|from benchmarks|import gradio|schemas\.evaluation|from \.evaluation|VisionDecision|TraceMetadata|utils\.(browser|logger)|configure_tracer|get_tracer" src schemas tests --include=*.py
```

Expected: no output. Any hit is a leftover import or reference to remove.

- [ ] **Step 9: Drop `gradio` and update CI**

In `pyproject.toml`, delete the line `"gradio==6.28.0",` from `dependencies`, and change `source` in `[tool.coverage.run]` and `files` in `[tool.mypy]` from `["src", "schemas", "benchmarks"]` to `["src", "schemas"]`.

Run: `uv lock && uv sync --group dev`
Expected: gradio and its dependencies are uninstalled; no errors.

In `.github/workflows/ci.yml`, in the `Upload E2E artifacts` step, delete the line `logs/traces.jsonl`.

In `.github/dependabot.yml`, delete the final block (`- package-ecosystem: docker` and its `directory` and `schedule` lines).

- [ ] **Step 10: Run the gates**

Run:

```bash
uv run python -m pytest tests/unit_test_*.py -q
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

Expected: all tests pass (the count drops from 556 because whole suites were deleted); ruff and mypy report no errors. If ruff reports unused imports left by the edits, run `uv run ruff check --fix .` and re-run.

- [ ] **Step 11: Update the roadmap and changelog**

Add these rows to the `Removed` table in `ROADMAP.md`:

```markdown
| Gradio UI (8 tabs) | Replaced by a two-page FastAPI + HTMX app in Phase 4 | 1 |
| Services layer and CLI healer | Pipelines are called from the web app only | 1 |
| Vision pipeline | Out of scope for v2 | 1 |
| JSONL tracer and Trace Inspector | Duplicated the per-run reports | 1 |
| Benchmarks, mutation engine, intent validation | The only published score was circular; the rest was unused | 1 |
| Docker image and workflow | Needs a model and a browser on the host anyway | 1 |
```

Add to `CHANGELOG.md` under `## [Unreleased]`, after the `### Added` list:

```markdown
### Removed

- The Gradio UI, the services layer and the CLI healer.
- The vision pipeline and its prompt.
- The JSONL tracer, benchmarks, mutation engine and intent validation.
- The Docker image and its workflow.
```

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "refactor!: remove the Gradio UI, vision, tracer, benchmarks and Docker" -m "v2 keeps generation and healing only; the web UI is rebuilt in Phase 4." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Move the source into the `workbench` package

**Files:**

- Create: `src/workbench/__init__.py`, `src/workbench/config.py`, `src/workbench/generate/__init__.py`, `tests/unit/__init__.py`, `tests/unit/test_config.py`, `tests/unit/test_layout.py`
- Move: every source file listed in the file map
- Modify: `pyproject.toml`, `eslint.config.cjs`, every moved module that computed `PROJECT_ROOT`, `.gitignore`
- Delete: `src/__init__.py`, `src/utils/__init__.py`, `schemas/`, `scripts/`, `prompts/`

**Interfaces:**

- Consumes: Task 2's trimmed modules.
- Produces, for Phase 2 onwards:
  - `workbench.config`: `PACKAGE_DIR: Path`, `PROJECT_ROOT: Path`, `PROMPTS_DIR: Path`, `AST_REPAIR_SCRIPT: Path`, `GENERATED_SPECS_DIR: Path`, `ARTIFACTS_DIR: Path`, `TEST_RESULTS_DIR: Path`
  - `workbench.heal.attempt_healing(test_file, max_retries: int = 3) -> str`
  - `workbench.generate.pipeline.generate_test_script(url: str, feature_description: str) -> GenerationDecision`
  - `workbench.runner.run_test(test_file) -> RunResult`
  - `workbench.models.{heal,generate,shared,artifacts}`, the renamed `schemas` modules
  - `workbench.llm.parsing`, `workbench.llm.prompts`, `workbench.validation`, `workbench.text`

- [ ] **Step 1: Write the failing guard tests**

Create `tests/unit/__init__.py` as an empty file.

Create `tests/unit/test_config.py`:

```python
"""Paths in workbench.config must point at real files after the move."""

import json
import shutil
import subprocess

import pytest

from workbench import config


def test_project_root_is_the_repository() -> None:
    assert (config.PROJECT_ROOT / "pyproject.toml").is_file()
    assert (config.PROJECT_ROOT / "package.json").is_file()


def test_prompts_ship_inside_the_package() -> None:
    assert (config.PROMPTS_DIR / "manifest.json").is_file()
    assert (config.PROMPTS_DIR / "healer.md").is_file()
    assert (config.PROMPTS_DIR / "generator.md").is_file()
    assert not (config.PROMPTS_DIR / "vision.md").exists()


def test_ast_repair_script_ships_inside_the_package() -> None:
    assert config.AST_REPAIR_SCRIPT.is_file()
    assert config.AST_REPAIR_SCRIPT.parent == config.PACKAGE_DIR / "heal"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_ast_repair_script_resolves_ts_morph_from_the_package() -> None:
    payload = {
        "strategy": "selector_replace",
        "source": 'await page.locator("#old").click();\n',
        "original_code": 'page.locator("#old")',
        "fixed_code": 'page.locator("#new")',
    }
    proc = subprocess.run(
        ["node", str(config.AST_REPAIR_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
        cwd=config.PROJECT_ROOT,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["success"] is True
    assert "#new" in result["source"]
    assert "#old" not in result["source"]
```

Create `tests/unit/test_layout.py`:

```python
"""Guards against the pre-v2 layout creeping back in."""

import re

from workbench.config import PROJECT_ROOT

LEGACY_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+(?:src|schemas|benchmarks|gradio)\b"
    r"|[\"'](?:src|schemas)\.[a-z_]"
    r"|observability\.(?:tracer|writer)|get_tracer\(",
    re.MULTILINE,
)


def _python_files() -> list:
    roots = [PROJECT_ROOT / "src" / "workbench", PROJECT_ROOT / "tests"]
    return [p for root in roots for p in root.rglob("*.py") if p.name != "test_layout.py"]


def test_no_module_uses_the_legacy_layout() -> None:
    offenders = [
        str(path.relative_to(PROJECT_ROOT))
        for path in _python_files()
        if LEGACY_IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_legacy_top_level_folders_are_gone() -> None:
    legacy = [
        "schemas",
        "benchmarks",
        "scripts",
        "prompts",
        "src/__init__.py",
        "src/agents",
        "src/services",
        "src/healing",
        "src/utils",
        "src/context",
        "src/llm",
        "src/observability",
    ]
    present = [name for name in legacy if (PROJECT_ROOT / name).exists()]
    assert present == []
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run python -m pytest tests/unit/test_config.py tests/unit/test_layout.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'workbench'`.

- [ ] **Step 3: Make the project an installable `workbench` package**

In `pyproject.toml`:

Replace the `[project]` header lines `version` and `description` with:

```toml
version = "2.0.0.dev0"
description = "Generates Playwright tests and heals failing ones with local LLMs"
```

Add after the `[dependency-groups]` table:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/workbench"]
```

In `[tool.ruff]`, add `src = ["src", "tests"]` below `line-length = 88`.

Replace the `[tool.pytest.ini_options]` table with:

```toml
[tool.pytest.ini_options]
testpaths = ["tests/unit"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-q --tb=short"
```

Change `source` in `[tool.coverage.run]` to `["src/workbench"]` and `files` in `[tool.mypy]` to `["src/workbench"]`.

- [ ] **Step 4: Move the files**

```bash
mkdir -p src/workbench/heal src/workbench/generate src/workbench/models
git mv src/healing/runner.py src/workbench/runner.py
git mv src/healing/__init__.py src/workbench/heal/__init__.py
for f in classifier planner repair evidence verifier artifact_store; do
  git mv "src/healing/$f.py" "src/workbench/heal/$f.py"
done
git mv scripts/ast_repair.js src/workbench/heal/ast_repair.js
git mv src/agents/generator.py src/workbench/generate/pipeline.py
git mv src/context src/workbench/context
git mv src/llm src/workbench/llm
git mv src/utils/llm.py src/workbench/llm/parsing.py
git mv src/utils/prompt_loader.py src/workbench/llm/prompts.py
git mv src/utils/validation.py src/workbench/validation.py
git mv src/utils/formatting.py src/workbench/text.py
git mv schemas/healing.py src/workbench/models/heal.py
git mv schemas/generation.py src/workbench/models/generate.py
git mv schemas/shared.py src/workbench/models/shared.py
git mv schemas/artifacts.py src/workbench/models/artifacts.py
git mv schemas/__init__.py src/workbench/models/__init__.py
git mv prompts src/workbench/prompts
git rm -q src/__init__.py src/utils/__init__.py
rm -rf src/healing src/agents src/utils schemas scripts
find src -name __pycache__ -type d -prune -exec rm -rf {} +
```

Create `src/workbench/generate/__init__.py`:

```python
"""Test generation: page context in, Playwright spec out."""
```

Create `src/workbench/__init__.py`:

```python
"""Playwright Workbench: generates Playwright tests and heals failing ones."""

__version__ = "2.0.0.dev0"
```

In `src/workbench/models/__init__.py`, fix the two relative imports that point at renamed files: `from .generation import` becomes `from .generate import`, and `from .healing import (` becomes `from .heal import (`.

- [ ] **Step 5: Create `src/workbench/config.py`**

```python
"""Filesystem locations used across the workbench.

Every module gets paths from here instead of counting parent directories,
so moving a module never breaks a path.
"""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]

PROMPTS_DIR = PACKAGE_DIR / "prompts"
AST_REPAIR_SCRIPT = PACKAGE_DIR / "heal" / "ast_repair.js"

# Runtime output. Phase 2 moves these into workspace/.
GENERATED_SPECS_DIR = PROJECT_ROOT / "tests" / "generated"
ARTIFACTS_DIR = PROJECT_ROOT / "tests" / "artifacts"
TEST_RESULTS_DIR = PROJECT_ROOT / "test-results"
```

- [ ] **Step 6: Point moved modules at `workbench.config`**

Make these replacements (each `PROJECT_ROOT = Path(__file__)...` line is removed; leave the rest of each file alone):

`src/workbench/runner.py`: replace `PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent` with `from workbench.config import PROJECT_ROOT` (move it up into the import block).

`src/workbench/heal/repair.py`: replace

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_AST_SCRIPT = PROJECT_ROOT / "scripts" / "ast_repair.js"
```

with

```python
from workbench.config import AST_REPAIR_SCRIPT, PROJECT_ROOT

_AST_SCRIPT = AST_REPAIR_SCRIPT
```

`src/workbench/heal/evidence.py`: replace `PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent` with `from workbench.config import PROJECT_ROOT`.

`src/workbench/heal/artifact_store.py`: replace

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "tests" / "artifacts"
```

with `from workbench.config import ARTIFACTS_DIR, PROJECT_ROOT`.

`src/workbench/context/screenshot.py`: replace `_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent` with `from workbench.config import PROJECT_ROOT as _PROJECT_ROOT`.

`src/workbench/llm/prompts.py`: replace

```python
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_MANIFEST_PATH = _PROJECT_ROOT / "prompts" / "manifest.json"
```

with

```python
from workbench.config import PROMPTS_DIR

_MANIFEST_PATH = PROMPTS_DIR / "manifest.json"
```

and in `load_prompt`, replace

```python
    # Resolve the project root dynamically
    project_root = Path(__file__).resolve().parent.parent.parent
    prompt_path = project_root / "prompts" / f"{agent_name}.md"
```

with

```python
    prompt_path = PROMPTS_DIR / f"{agent_name}.md"
```

`src/workbench/llm/router.py`: replace `load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")` with `load_dotenv(PROJECT_ROOT / ".env")` and add `from workbench.config import PROJECT_ROOT` to the import block.

`src/workbench/generate/pipeline.py`: delete the unused constant `TEST_DIR = "tests/generated"` if nothing in the file reads it (`grep -n TEST_DIR src/workbench/generate/pipeline.py` shows only the definition).

- [ ] **Step 7: Rewrite imports and patch targets with a one-off codemod**

Create `codemod_v2.py` at the repository root (it is deleted in Step 9 and never committed):

```python
"""One-off: rewrite pre-v2 module paths to the workbench package."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Most specific first, so "src.healing.runner" is not caught by "src.healing".
DOTTED = [
    ("src.healing.runner", "workbench.runner"),
    ("src.healing.classifier", "workbench.heal.classifier"),
    ("src.healing.planner", "workbench.heal.planner"),
    ("src.healing.repair", "workbench.heal.repair"),
    ("src.healing.evidence", "workbench.heal.evidence"),
    ("src.healing.verifier", "workbench.heal.verifier"),
    ("src.healing.artifact_store", "workbench.heal.artifact_store"),
    ("src.healing", "workbench.heal"),
    ("src.agents.generator", "workbench.generate.pipeline"),
    ("src.context", "workbench.context"),
    ("src.utils.llm", "workbench.llm.parsing"),
    ("src.utils.prompt_loader", "workbench.llm.prompts"),
    ("src.utils.validation", "workbench.validation"),
    ("src.utils.formatting", "workbench.text"),
    ("src.llm", "workbench.llm"),
    ("schemas.healing", "workbench.models.heal"),
    ("schemas.generation", "workbench.models.generate"),
    ("schemas.shared", "workbench.models.shared"),
    ("schemas.artifacts", "workbench.models.artifacts"),
]
BARE_SCHEMAS = re.compile(r"^(\s*)from schemas import", re.MULTILINE)


def rewrite(text: str) -> str:
    for old, new in DOTTED:
        text = re.sub(r"(?<![\w.])" + re.escape(old) + r"(?!\w)", new, text)
    return BARE_SCHEMAS.sub(r"\1from workbench.models import", text)


changed = []
for path in [*ROOT.joinpath("src", "workbench").rglob("*.py"), *ROOT.joinpath("tests").rglob("*.py")]:
    before = path.read_text(encoding="utf-8")
    after = rewrite(before)
    if after != before:
        path.write_text(after, encoding="utf-8")
        changed.append(path.relative_to(ROOT))
print(f"rewrote {len(changed)} files")
for p in changed:
    print(" ", p)
```

Run: `uv run python codemod_v2.py`
Expected: a list of rewritten files under `src/workbench/` and `tests/`.

- [ ] **Step 8: Fix tooling paths**

In `eslint.config.cjs`, change `files: ['scripts/**/*.js'],` to `files: ['src/workbench/**/*.js'],` and its comment to `// Node.js scripts shipped in the package — allow require(), process, __dirname, etc.`

In `.gitignore`, add under `# Project Specific`:

```gitignore
# v2 runtime output (Phase 2 onwards)
workspace/
```

- [ ] **Step 9: Install, delete the codemod, and tidy imports**

Run:

```bash
rm codemod_v2.py
uv sync --group dev
uv run ruff check --fix . && uv run ruff format .
```

Expected: `uv sync` builds and installs `ai-py-playwright-workbench` in editable mode; ruff sorts the rewritten imports and reports no remaining errors.

- [ ] **Step 10: Run the guard tests**

Run: `uv run python -m pytest tests/unit/test_config.py tests/unit/test_layout.py -v`
Expected: 6 passed (the Node test is skipped only if `node` is missing).

- [ ] **Step 11: Run the existing unit tests from their old location**

The old test files still live in `tests/` (Task 4 moves them), and the codemod has already rewritten their imports.

Run: `uv run python -m pytest tests/unit_test_*.py -q`
Expected: the same number of tests pass as in Task 2 Step 10. (Files passed explicitly are collected even though `python_files` is now `test_*.py`.)

If a test fails because a file is missing, a source module still points at the old layout. Find it with `grep -rn "scripts/ast_repair\|parent.parent.parent" src/workbench` and switch it to `workbench.config`.

- [ ] **Step 12: Check the package imports from anywhere**

Run: `cd /tmp && uv run --project "$OLDPWD" python -c "import workbench.config as c; print(c.PROJECT_ROOT)"; cd "$OLDPWD"`
Expected: prints the repository path.

Run: `uv run mypy && npm run lint:js && npm run type-check`
Expected: no errors.

- [ ] **Step 13: Commit**

```bash
git add -A
git commit -m "refactor: move the source into the workbench package" -m "Paths now come from workbench.config; imports and test patch targets were rewritten by a one-off codemod." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Reorganise the tests into unit and integration suites

**Files:**

- Move: `tests/unit_test_*.py` → `tests/unit/test_*.py`; `tests/e2e/` → `tests/integration/`; `tests/e2e/site/` → `samples/site/`
- Modify: `tests/unit/test_ast_repair.py`, `tests/integration/test_pipeline.py`, `playwright.e2e.config.ts`, `tsconfig.json`, `package.json`, `.github/workflows/ci.yml`

**Interfaces:**

- Consumes: Task 3's package.
- Produces: `uv run python -m pytest` runs the unit suite; `uv run python -m pytest tests/integration` runs the integration suite; `samples/site/index.html` is the sample web app Phase 3 builds on.

- [ ] **Step 1: Move the unit tests**

```bash
for f in tests/unit_test_*.py; do
  name="$(basename "$f")"
  git mv "$f" "tests/unit/${name#unit_}"
done
ls tests/unit
```

Expected: `__init__.py`, `test_ast_repair.py`, `test_classification.py`, `test_config.py`, `test_context.py`, `test_explainability.py`, `test_fixer.py`, `test_healing.py`, `test_json.py`, `test_layout.py`, `test_llm.py`, `test_path_validation.py`, `test_provenance.py`, `test_schemas.py`, `test_validation.py`, `test_visibility.py`.

- [ ] **Step 2: Fix paths in the moved unit tests**

The files are now one folder deeper. Run:

```bash
grep -rln "Path(__file__).resolve().parent.parent" tests/unit | xargs sed -i '' 's/Path(__file__).resolve().parent.parent)/Path(__file__).resolve().parents[2])/; s/Path(__file__).resolve().parent.parent$/Path(__file__).resolve().parents[2]/'
grep -rn "parent.parent" tests/unit
```

Expected: no output from the second command. (On Linux use `sed -i` without `''`.)

- [ ] **Step 3: Run the unit suite from its new home**

Run: `uv run python -m pytest`
Expected: all tests pass, including `test_config.py` and `test_layout.py`; the total equals Task 3 Step 11's count plus the 6 guard tests.

- [ ] **Step 4: Move the integration test and the sample site**

```bash
mkdir -p samples
git mv tests/e2e tests/integration
git mv tests/integration/e2e_test_pipeline.py tests/integration/test_pipeline.py
git mv tests/integration/site samples/site
```

In `tests/integration/test_pipeline.py`:

- replace `SITE_DIR = Path(__file__).resolve().parent / "site"` with `SITE_DIR = PROJECT_ROOT / "samples" / "site"` (keep it below the `PROJECT_ROOT` line);
- replace `from tests.e2e.fake_llm import FakeLLM` with `from tests.integration.fake_llm import FakeLLM`;
- in the module docstring, replace `uv run python -m pytest tests/e2e/e2e_test_pipeline.py` with `uv run python -m pytest tests/integration` and `local fixture site` with `sample site in samples/site/`.

In `playwright.e2e.config.ts`, replace `--directory tests/e2e/site` with `--directory samples/site` and `(tests/e2e/e2e_test_pipeline.py)` with `(tests/integration/test_pipeline.py)`.

- [ ] **Step 5: Update scripts, TypeScript config and CI**

In `package.json` `scripts`:

```json
    "test:unit": "uv run python -m pytest",
    "test:e2e": "uv run python -m pytest tests/integration --junitxml=reports/e2e-pytest.xml && npm run test:e2e:report",
```

In `tsconfig.json`, set `"exclude": ["node_modules", "dist", "tests/fixtures", ".venv", "samples"]`.

In `.github/workflows/ci.yml`:

- in `Python unit tests (with coverage)`, replace `uv run python -m pytest tests/unit_test_*.py -q --cov` with `uv run python -m pytest -q --cov`;
- in the e2e job, replace `uv run python -m pytest tests/e2e/e2e_test_pipeline.py -v --junitxml=reports/e2e-pytest.xml` with `uv run python -m pytest tests/integration -v --junitxml=reports/e2e-pytest.xml`;
- rename the job's `name:` to `Integration (generate + heal, fake LLM)`.

- [ ] **Step 6: Run the integration suite**

Run: `npx playwright install chromium && uv run python -m pytest tests/integration -v`
Expected: every test passes. The generate-then-heal flow runs against `samples/site/` in a real Chromium with the fake model.

Run: `npm run test:e2e:report`
Expected: Playwright re-runs the generated and healed specs against `samples/site/` and they pass.

- [ ] **Step 7: Run every gate**

Run:

```bash
uv run python -m pytest -q --cov
uv run ruff check . && uv run ruff format --check .
uv run mypy
npm run lint
npm run type-check
```

Expected: everything passes.

- [ ] **Step 8: Update the changelog and commit**

Add under `## [Unreleased]` in `CHANGELOG.md`:

```markdown
### Changed

- The code is now the installable `workbench` package under `src/`, with all
  paths in `workbench.config`.
- Tests are split into `tests/unit` (the default pytest run) and
  `tests/integration`; the sample web app lives in `samples/site/`.
```

```bash
git add -A
git commit -m "test: split the suites into unit and integration and move the sample site" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Replace the documentation and agent guides

**Files:**

- Delete: `docs/README.md`, `docs/ai-systems-engineering.md`, `docs/architecture/`, `docs/development/`, `docs/evaluation/`, `docs/prompts/`, `docs/governance.md`, `docs/workbench-ui.md`, `docs/decisions.md`, `docs/env-variables.md`, `docs/assets/evaluation.png`
- Rewrite: `README.md`, `AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`
- Create: `CLAUDE.md`
- Modify: `ROADMAP.md`, `CHANGELOG.md`

**Interfaces:**

- Consumes: the layout from Tasks 3 and 4.
- Produces: `AGENTS.md` as the single guide for agents; Phases 2–6 update it as the layout grows.

- [ ] **Step 1: Delete the old documentation**

`docs/decisions.md` goes too: Phase 6 rewrites it with the still-valid ADRs and D1–D12 from the spec. Until then the spec is the decision record.

```bash
git rm -r -q docs/README.md docs/ai-systems-engineering.md docs/architecture \
  docs/development docs/evaluation docs/prompts docs/governance.md \
  docs/workbench-ui.md docs/decisions.md docs/env-variables.md docs/assets/evaluation.png
ls docs
```

Expected: `assets` and `superpowers`.

- [ ] **Step 2: Write the interim `README.md`**

Replace the whole file with:

````markdown
# ai-py-playwright-workbench

Generates Playwright tests from a URL and a scenario, and heals failing ones:
it diagnoses the failure with a local LLM, repairs the code with a TypeScript
syntax-tree edit and re-runs the test to prove the fix.

> **v2 is under construction on this branch.** The redesign is described in
> the [v2 spec](docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md)
> and its progress is tracked in [ROADMAP.md](ROADMAP.md). The released 1.0
> version is on `main`.

## State of this branch

The web UI is being rebuilt (Phase 4), so there is nothing to launch yet. The
generate and heal pipelines are covered by tests:

```bash
uv sync --group dev
npm ci
npx playwright install chromium
uv run python -m pytest                    # unit tests: no model, no browser
uv run python -m pytest tests/integration  # real Chromium, fake model
```

## License

MIT. See [LICENSE](LICENSE).
````

- [ ] **Step 3: Rewrite `AGENTS.md`**

Replace the whole file with:

````markdown
# Repository Guidelines

Instructions for AI assistants (Claude, Codex and others) working in this
repository. Keep this file accurate: update it in the same commit as any change
to the layout, commands or conventions.

## What this project is

A local web app that generates Playwright tests and heals failing ones with
local LLMs (LM Studio or Ollama). It is being redesigned as v2 on the `v2`
branch:

- Design: [v2 spec](docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md)
- Progress: [ROADMAP.md](ROADMAP.md)
- Plans: [docs/superpowers/plans/](docs/superpowers/plans/)

Read the spec before changing behaviour. If a change is not in the spec or the
current phase's plan, add it to `ROADMAP.md` under "Later" instead of building it.

## Layout

```text
src/workbench/          the Python package
├── config.py           every filesystem path; never count parent folders
├── runner.py           runs `npx playwright test`
├── heal/               classifier, planner, repair (+ ast_repair.js), evidence, verifier
├── generate/           generation pipeline
├── context/            page context from one Chromium session
├── llm/                router (replaced in Phase 3), parsing, prompt loading
├── models/             Pydantic data contracts
├── prompts/            prompt files and manifest.json
├── validation.py       input checks
└── text.py             clean_ansi_codes()
samples/site/           sample web app used by tests (and by the app from Phase 3)
tests/unit/             default pytest run: no model, no browser, no network
tests/integration/      real Chromium + fake OpenAI-compatible server
docs/superpowers/       specs and plans
```

## Commands

```bash
uv sync --group dev && npm ci && npx playwright install chromium
uv run python -m pytest                    # unit tests
uv run python -m pytest tests/integration  # integration tests
uv run ruff check . && uv run ruff format .
uv run mypy
npm run lint                               # ESLint, Ruff, mypy, markdownlint
npm run type-check                         # TypeScript
```

## Rules

- All LLM output is parsed into a Pydantic model (`workbench.llm.parsing.parse_llm_response`), never `json.loads` alone.
- New data shapes are Pydantic models in `workbench/models/`.
- Paths come from `workbench.config`.
- Prompt changes go in `src/workbench/prompts/` and bump the version in `prompts/manifest.json`.
- Subprocesses use argument lists, never `shell=True`.
- Tests never need a live model, browser or network unless they live in `tests/integration/`. Mock the model with `@patch("workbench.heal.planner.get_default_router")`; a mocked `LLMResponse.model_used` must be a string.
- `tests/unit/test_layout.py` fails if anything imports the pre-v2 layout (`src.*`, `schemas.*`, benchmarks, Gradio, the tracer).

## Commits

- Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Update `ROADMAP.md` and `CHANGELOG.md` in the same commit as the work.
- Run the unit tests, ruff, mypy and `npm run lint` before committing; the Husky hook formats staged files.
````

- [ ] **Step 4: Create `CLAUDE.md`**

```markdown
@AGENTS.md
```

- [ ] **Step 5: Rewrite `CONTRIBUTING.md`**

Replace the whole file with:

````markdown
# Contributing

Thanks for taking a look. Changes should keep the code small, typed and
covered by tests.

## Set up

```bash
uv sync --group dev
npm ci
npx playwright install chromium
```

The unit tests need no model, no browser and no network.

## Before you open a pull request

Run the checks CI runs:

```bash
uv run python -m pytest                    # unit tests
uv run python -m pytest tests/integration  # integration tests
npm run lint                               # ESLint, Ruff, mypy, markdownlint
npm run type-check                         # TypeScript
uv run ruff format .                       # format Python
```

The Husky pre-commit hook formats and lints staged files for you.

## Conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).
- Data shapes are Pydantic models in `src/workbench/models/`; LLM output is
  always parsed with `parse_llm_response()`.
- Update [ROADMAP.md](ROADMAP.md) and [CHANGELOG.md](CHANGELOG.md) with the change.
- Keep pull requests focused: one change, with tests for new behaviour.
- [AGENTS.md](AGENTS.md) has the layout and the rules in more detail.

## Security

Please report vulnerabilities privately; see [SECURITY.md](SECURITY.md).
````

- [ ] **Step 6: Update `SECURITY.md`**

Replace the bullet that starts `- The Gradio UI binds to` (two lines) with:

```markdown
- The web app (from v2 Phase 4) binds to `127.0.0.1` only.
```

In the paragraph that starts "Reports in scope include", replace the words "path traversal out of" followed by the inline code `tests/generated/` with "path traversal out of the folders the workbench writes to".

Replace the last bullet (two lines, starting `- Dependabot opens weekly`) with:

```markdown
- Dependabot opens weekly update PRs for uv, npm and GitHub Actions.
```

- [ ] **Step 7: Mark Phase 1 done in the roadmap**

In `ROADMAP.md`:

- move the three Phase 1 rows from `Now` into `Done`, replacing `Nothing yet.` with:

```markdown
| Item | Phase | Plan |
| --- | --- | --- |
| `workbench` package and test layout | 1 | [Phase 1](docs/superpowers/plans/2026-10-03-v2-phase-1-foundation.md) |
| Remove the Gradio UI, services, CLI, vision pipeline, tracer, benchmarks and Docker | 1 | [Phase 1](docs/superpowers/plans/2026-10-03-v2-phase-1-foundation.md) |
| Roadmap, changelog and agent guides | 1 | [Phase 1](docs/superpowers/plans/2026-10-03-v2-phase-1-foundation.md) |
```

- move the five Phase 2 rows from `Next` into `Now` with status `🔭 Planned` and a `Plan` column of `Phase 2 plan (to be written)`;
- add this row to `Removed`:

```markdown
| Most of `docs/` (31 files) | Replaced in Phase 6 by README, architecture, decisions and development guides | 1 |
```

Add under `### Changed` in `CHANGELOG.md`:

```markdown
- `AGENTS.md`, `CONTRIBUTING.md` and `SECURITY.md` describe v2; `CLAUDE.md`
  points agents at `AGENTS.md`. The old documentation set was removed.
```

- [ ] **Step 8: Lint and commit**

Run: `npm run lint:md`
Expected: `0 issues`.

```bash
git add -A
git commit -m "docs: replace the documentation set with v2 guides" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Verify the phase and hand over

**Files:** none changed unless a check fails.

- [ ] **Step 1: Run every gate from a clean environment**

```bash
rm -rf .venv node_modules
uv sync --group dev && npm ci && npx playwright install chromium
uv run python -m pytest -q --cov
uv run python -m pytest tests/integration -v
npm run test:e2e:report
npm run lint
npm run type-check
```

Expected: everything passes. Coverage is reported (the 85% gate arrives in Phase 5).

- [ ] **Step 2: Confirm the removals**

Run: `git ls-files | grep -E "^(schemas|benchmarks|scripts|prompts)/|^src/(app|agents|services|healing|utils|observability)|Dockerfile|docker"`
Expected: no output.

- [ ] **Step 3: Ask before pushing**

Show the user `git log --oneline main..v2` and ask whether to push `v2` and open the Phase 1 pull request. Do not push without a yes.
