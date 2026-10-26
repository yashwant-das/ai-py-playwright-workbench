# Repository Guidelines

Instructions for AI assistants (Claude, Codex and others) working in this
repository. Keep this file accurate: update it in the same commit as any change
to the layout, commands or conventions.

## Shared standards

Use the `complete` documentation profile and read the affected guides in
[repo-standards at 073f51ff68ec050f6b3372c46bc3bd4e721a5342](https://github.com/yashwant-das/repo-standards/tree/073f51ff68ec050f6b3372c46bc3bd4e721a5342)
before changing documentation, structure, dependencies or CI. Follow explicit
user instructions first and retain deliberate runtime baselines. Record pending
work and any owner-authorized exceptions in
[development](docs/development.md#standards-adoption).

Keep the root README’s badges, concrete capabilities, Mermaid diagram and
structure/stack summary accurate. Keep detailed setup and rollout evidence in
the guides; the Demo media must remain clearly labelled as recorded answers.

## What this project is

A local web app that generates Playwright tests and heals failing ones with
local LLMs (LM Studio or Ollama), plus a recorded Demo provider.

Use [architecture](docs/architecture.md), [decisions](docs/decisions.md) and
[development](docs/development.md) for current behavior and commands.
[ROADMAP.md](ROADMAP.md) tracks deferred work. The
[v2 design and implementation plans](docs/superpowers/README.md) are historical
context; they do not override current code, maintained guides or owner requests.
Keep unrequested features on the roadmap rather than expanding the scope.

## Layout

The [README tree](README.md#project-structure) summarizes directories.
Key modules for implementation work:

| Module under `src/workbench/` | Responsibility |
| --- | --- |
| `config.py`, `__main__.py`, `app.py` | Paths, local launcher and FastAPI app factory |
| `runs.py`, `events.py` | Single background run and numbered progress events |
| `runner.py`, `playwright_report.py`, `environment.py` | Playwright execution, JSON results and prerequisites |
| `heal/`, `generate/`, `context/` | Pipelines, repair strategies and browser evidence |
| `llm/`, `models/`, `prompts/` | Model clients, validated contracts and versioned prompts |
| `web/` | Routes, services, templates, static assets and Host/Origin guard |
| `reports.py`, `settings.py`, `samples.py` | Report storage, saved model choice and bundled samples |
| `ids.py`, `validation.py`, `text.py` | Identifiers, input validation and text utilities |

`playwright.workspace.config.ts` configures specs run by the app;
`playwright.ui.config.ts` configures UI tests and
`playwright.capture.config.ts` configures Demo-media capture.

## Commands

```bash
uv sync --locked --group dev && npm ci && npx playwright install chromium
uv run workbench                           # start the app on http://127.0.0.1:7860
uv run python -m pytest                    # unit tests
uv run python -m pytest tests/integration  # integration tests
npm run test:ui                            # UI tests: real app, Chromium, Demo model
npm run docs:capture                       # rebuild the README's GIF and screenshots
uv run ruff check . && uv run ruff format .
uv run mypy
npm run lint                               # code, format, Python types, Markdown and text checks
npm run type-check                         # TypeScript
```

## Rules

- Heal analysis is parsed with `workbench.llm.parsing.parse_llm_response` into a Pydantic model. Generate extracts code and validates it with `GenerationResult`; this checks non-empty text, not TypeScript syntax or test semantics.
- New data shapes are Pydantic models in `workbench/models/`.
- Paths come from `workbench.config`.
- Talk to models only through `workbench.llm.chat.ChatModel`.
- `heal()` must leave the spec unchanged unless the status is `healed`.
- Prompt changes go in `src/workbench/prompts/` and bump the version in `src/workbench/prompts/manifest.json`.
- Subprocesses use argument lists, never `shell=True`.
- Unit tests and tooling checks need no live model, browser or network. Browser work belongs in `tests/integration/` or `tests/ui/`; both use controlled models.
- Pipelines take their collaborators as arguments (`model`, `run`, `collect`, `browsers_ready`). Unit tests pass fakes; do not patch module globals.
- `tests/unit/test_layout.py` fails if anything imports the pre-v2 layout (`src.*`, `schemas.*`, benchmarks, Gradio, the tracer), the 1.0 router or `dotenv`.
- No environment variables configure the app. The model choice lives in `workspace/settings.json`; `WORKBENCH_WORKSPACE` and `WORKBENCH_PORT` exist for tests and CI only.
- UI: the templates in `src/workbench/web/templates/` are the source of truth; colours and type come only from `static/css/tokens.css` (one variable per Figma variable). No JavaScript files beyond the vendored htmx and its SSE extension.
- Routes call pipelines and the model client only through `workbench.web.services.Services`; route tests build the app with `tests/unit/web_support.make_client()` and fakes.
- UI tests get their app from the fixture in `tests/ui/support/app.ts` (free port, temporary workspace). Never point them at port 7860 or `workspace/`.
- The app answers only requests addressed to 127.0.0.1 or localhost, and refuses state-changing requests from other origins (`workbench.web.guard`); new POST routes need no extra code, but must not be exempted.

## Commits

- Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
- Update `ROADMAP.md` and `CHANGELOG.md` in the same commit as the work.
- Run the unit tests, ruff, mypy and `npm run lint` before committing; the Husky hook checks staged files without modifying them.
