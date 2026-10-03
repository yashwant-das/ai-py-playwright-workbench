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
| Gradio UI (8 tabs) | Replaced by a two-page FastAPI + HTMX app in Phase 4 | 1 |
| Services layer and CLI healer | Pipelines are called from the web app only | 1 |
| Vision pipeline | Out of scope for v2 | 1 |
| JSONL tracer and Trace Inspector | Duplicated the per-run reports | 1 |
| Benchmarks, mutation engine, intent validation | The only published score was circular; the rest was unused | 1 |
| Docker image and workflow | Needs a model and a browser on the host anyway | 1 |
