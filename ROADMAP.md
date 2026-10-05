# Roadmap

Tracks the v2 redesign described in the
[v2 spec](docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md).
Status: ✅ Done · 🚧 In progress · 🔭 Planned · 🗑️ Removed. Update this file in
the same commit as the work it describes.

## Now

| Item | Status | Phase | Plan |
| --- | --- | --- | --- |
| Integration and UI suites, axe, coverage gate, strict mypy, CI rework | 🔭 Planned | 5 | Phase 5 plan (to be written) |
| Figma file: the four §5.3 changes (the templates already implement them) | 🚧 Blocked: Figma MCP call limit | 4 | Phase 4 Task 12 |

## Next

| Item | Status | Phase |
| --- | --- | --- |
| README, GIF, architecture and decision docs, 2.0.0 release | 🔭 Planned | 6 |

## Later

- Stream Playwright's own output into the live log; today the log is built from pipeline events, because the runner reads the JSON report after the run.
- A run history page listing past reports (reports are already saved and linkable).
- CI integration: a GitHub Action that heals failing specs and opens a pull request, or flags a suspected app bug.
- The classifier treats "waiting for locator" timeouts as locator problems rather than slow pages.
- Cloud providers (Anthropic, OpenAI).
- A benchmark built from a deliberately mutated sample app.
- Comparing heals with Playwright's own healer agent.
- Dark mode.
- Renaming the repository.
- Heal: send Playwright's marked "Test source" block from `error-context.md` to the planner as its own prompt section (spec E2; currently the whole file plus file:line:col is sent).
- Heal: record a failed model call as an attempt with its `ModelExchange` (an outcome such as `model_error`, sections built before the call) so the Model I/O view shows it.
- Generate: guard unexpected exceptions after the spec is written (end the active step, save an error report) and reject a reply with no `test(` block as an invalid reply.
- Generate: make spec names and report ids collision-safe under concurrent runs (Phase 4).
- Cancel an in-flight model call; today a cancel takes effect when the model answers (calls time out after 5 minutes).
- Warn when a prompt may not fit the model's context window; Ollama silently drops the start of a prompt that is too long.
- Heal: review the `role_argument` and `timeout_adjust` AST strategies, which extract values from `fixed_code` as loosely as `selector_replace` did.

## Done

| Item | Phase | Plan |
| --- | --- | --- |
| FastAPI + HTMX web UI matching the Figma design | 4 | [Phase 4](docs/superpowers/plans/2026-10-04-v2-phase-4-web-ui.md) |
| LM Studio, Ollama and Demo providers; the choice is saved in the workspace (the UI arrives in Phase 4); no `.env` | 3 | [Phase 3](docs/superpowers/plans/2026-10-04-v2-phase-3-providers-and-samples.md) |
| Bundled samples: selector drift and app bug | 3 | [Phase 3](docs/superpowers/plans/2026-10-04-v2-phase-3-providers-and-samples.md) |
| `workbench` package and test layout | 1 | [Phase 1](docs/superpowers/plans/2026-10-03-v2-phase-1-foundation.md) |
| Remove the Gradio UI, services, CLI, vision pipeline, tracer, benchmarks and Docker | 1 | [Phase 1](docs/superpowers/plans/2026-10-03-v2-phase-1-foundation.md) |
| Roadmap, changelog and agent guides | 1 | [Phase 1](docs/superpowers/plans/2026-10-03-v2-phase-1-foundation.md) |
| Python 3.13, Playwright 1.63.0, Node 24 | 1 | [Phase 1](docs/superpowers/plans/2026-10-03-v2-phase-1-foundation.md) |
| Evidence from Playwright's `error-context.md` and a per-run output folder | 2 | [Phase 2](docs/superpowers/plans/2026-10-03-v2-phase-2-engine.md) |
| Accessibility snapshot through `aria_snapshot()` instead of CDP | 2 | [Phase 2](docs/superpowers/plans/2026-10-03-v2-phase-2-engine.md) |
| Model I/O capture and schema-constrained model output | 2 | [Phase 2](docs/superpowers/plans/2026-10-03-v2-phase-2-engine.md) |
| One heal loop with live events, cancellation and the app-defect guard | 2 | [Phase 2](docs/superpowers/plans/2026-10-03-v2-phase-2-engine.md) |
| One report per run, all runtime output in `workspace/` | 2 | [Phase 2](docs/superpowers/plans/2026-10-03-v2-phase-2-engine.md) |
| Runner reads Playwright's JSON report instead of terminal output | 2 | [Phase 2](docs/superpowers/plans/2026-10-03-v2-phase-2-engine.md) |
| Playwright's built-in console, page-error and request collections replace custom listeners | 2 | [Phase 2](docs/superpowers/plans/2026-10-03-v2-phase-2-engine.md) |
| Captioned video of each verification re-run | 2 | [Phase 2](docs/superpowers/plans/2026-10-03-v2-phase-2-engine.md) |

## Removed

| Item | Reason | Phase |
| --- | --- | --- |
| Gradio UI (8 tabs) | Replaced by a two-page FastAPI + HTMX app in Phase 4 | 1 |
| Services layer and CLI healer | Pipelines are called from the web app only | 1 |
| Vision pipeline | Out of scope for v2 | 1 |
| JSONL tracer and Trace Inspector | Duplicated the per-run reports | 1 |
| Benchmarks, mutation engine, intent validation | The only published score was circular; the rest was unused | 1 |
| Docker image and workflow | Needs a model and a browser on the host anyway | 1 |
| Most of `docs/` (30 files) | Replaced in Phase 6 by README, architecture, decisions and development guides | 1 |
| LLM router with retries and a fallback provider, model registry, `.env` | One client talks to the provider chosen in the UI; the choice is saved in the workspace | 3 |
