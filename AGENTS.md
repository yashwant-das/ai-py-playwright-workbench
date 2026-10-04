# Repository Guidelines

Instructions for AI assistants (Claude, Codex and others) working in this
repository. Keep this file accurate: update it in the same commit as any change
to the layout, commands or conventions.

## What this project is

A tool that generates Playwright tests and heals failing ones with local LLMs
(LM Studio or Ollama), rebuilt as a local web app in v2. It is being redesigned
on the `v2` branch:

- Design: [v2 spec](docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md)
- Progress: [ROADMAP.md](ROADMAP.md)
- Plans: [docs/superpowers/plans/](docs/superpowers/plans/)

Read the spec before changing behaviour. If a change is not in the spec or the
current phase's plan, add it to `ROADMAP.md` under "Later" instead of building it.

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
├── prompts/            prompt files and manifest.json
├── validation.py       input checks
└── text.py             clean_ansi_codes()
samples/site/           sample web app used by tests
tests/unit/             default pytest run: no model, no browser, no network
tests/integration/      real Chromium + scripted or fake OpenAI-compatible model
workspace/              runtime output (git-ignored): specs/, runs/, reports/
playwright.workspace.config.ts  the config the runner uses for every spec
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
- Talk to models only through `workbench.llm.chat.ChatModel`.
- `heal()` must leave the spec unchanged unless the status is `healed`.
- Prompt changes go in `src/workbench/prompts/` and bump the version in `src/workbench/prompts/manifest.json`.
- Subprocesses use argument lists, never `shell=True`.
- Tests never need a live model, browser or network unless they live in `tests/integration/`.
- Pipelines take their collaborators as arguments (`model`, `run`, `collect`, `browsers_ready`). Unit tests pass fakes; do not patch module globals.
- `tests/unit/test_layout.py` fails if anything imports the pre-v2 layout (`src.*`, `schemas.*`, benchmarks, Gradio, the tracer).

## Commits

- Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Update `ROADMAP.md` and `CHANGELOG.md` in the same commit as the work.
- Run the unit tests, ruff, mypy and `npm run lint` before committing; the Husky hook formats staged files.
