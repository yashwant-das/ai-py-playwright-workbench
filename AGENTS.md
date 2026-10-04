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
├── heal/               pipeline (heal()), evidence, planner, repair (+ ast_repair.js), classifier
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
- Tests never need a live model, browser or network unless they live in `tests/integration/`. Pipelines (`heal()`) take their collaborators as arguments (`model`, `run`, `collect`, `browsers_ready`); pass fakes instead of patching module globals.
- `tests/unit/test_layout.py` fails if anything imports the pre-v2 layout (`src.*`, `schemas.*`, benchmarks, Gradio, the tracer).

## Commits

- Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Update `ROADMAP.md` and `CHANGELOG.md` in the same commit as the work.
- Run the unit tests, ruff, mypy and `npm run lint` before committing; the Husky hook formats staged files.
