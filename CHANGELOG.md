# Changelog

<!-- markdownlint-disable MD024 -->
<!-- Release entries deliberately repeat Added/Changed headings. -->

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Document session-based, multi-page generation as future scope, retaining the
  current architecture and leaving exploration budgets for a future design.

- Generate offers three public practice scenarios with form presets and clear
  local-model requirements. Demo keeps its bundled Contact form example.
- The Generate form and README explain starting-page snapshot limits, and the
  README includes verified example scenarios and labels Checkout's expected failure.

### Changed

- Restore the README showcase with a root architecture diagram, concrete
  capabilities, structure/stack summaries and explicit Demo/verification scope;
  add a run-lifecycle sequence and pin the revised shared standards.
- Clarify that text repair can use exact or indentation-tolerant matching,
  and retain explicit limits on badge and live-model verification.

- Keep standards profiles and rollout status in contributor documentation rather
  than the README introduction to project guides.

- Align staged prompt exclusions and extensionless config checks with CI;
  strictly validate JSON while accepting JSONC, and handle unstaged deletions
  during full text checks.

- Use weekly dependency updates, locked and cached Python CI installs, short CI
  artifact retention and a bounded CodeQL job.
- Keep Husky, run staged linters in check mode with the full Ruff rule set, and
  add shared text/config checks with behavior tests.
- Lint maintained Markdown with the shared baseline; exclude historical records
  and treat prompt templates as application assets.
- Refresh compatible dependencies, retain the shared Playwright 1.64.0 binding
  set, and use Node-aware TypeScript resolution with explicit Node types.
- Match model, sample and example accessible names to their visible labels,
  satisfying the updated axe check without changing visible button text.

- Adopt the complete documentation profile with a pinned shared-standards reference,
  a shorter entry point, focused generation examples and a historical-plan index.

- Playwright is 1.64.0 in both the Python package and npm.
- `AGENTS.md` no longer describes v2 as work in progress on a branch.
- The Figma file matches the app again: two samples, the likely-app-bug state,
  the Re-run video tab, the popover footnote and the four contrast colours.
- A full pass over the Figma file brought its wording, buttons and example
  data in line with the app; two Figma ideas the app lacks are on the roadmap.

## [2.0.0] - 2026-10-11

The workbench was rebuilt as a small local web app: two features (Heal and
Generate), one heal loop and one report per run. The 1.0 Gradio UI, vision
pipeline, benchmarks, tracer, CLI and Docker image are gone. The reasoning is
in the [v2 spec](docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md)
and [docs/decisions.md](docs/decisions.md).

### Added

- A local web app (FastAPI, Jinja and HTMX, no front-end build): `uv run workbench`
  opens Heal and Generate on <http://127.0.0.1:7860>.
- Live progress over server-sent events, with cancel; every finished run has a
  page at `/reports/<id>` with the diff, a captioned re-run video, the execution
  log and the Model I/O.
- A model menu that tests a server, lists its models and saves the choice.
- Downloads for the report JSON, the fixed or generated spec, and the video.
- `ROADMAP.md` and this changelog.
- A UI test suite (`npm run test:ui`) that drives the real app in Chromium with
  the Demo model.
- Accessibility checks with axe on every page state in the UI suite.
- A README with a recording of a heal, screenshots and a comparison with
  Playwright Test Agents; architecture, decisions and development documents.
- The engine records every model exchange (sections sent, raw reply, validity,
  provenance) and writes one JSON report per run to `workspace/reports/`.
- Healing evidence comes from Playwright's `error-context.md`: the page as it
  was at the moment of failure.
- Verification re-runs are recorded as video with each action captioned.
- A confident `POTENTIAL_APP_DEFECT` diagnosis stops the heal without editing
  the test.
- Runs can be cancelled; Playwright and its browsers are stopped.
- LM Studio and Ollama through one OpenAI-compatible client. The first server
  that answers is detected on start, and the model choice is saved in
  `workspace/settings.json`.
- A Demo provider that replays recorded answers, so the bundled samples work
  without a model server.
- Two bundled samples against the sample site: *Selector drift* heals, and
  *App bug* stops without editing the test.

### Removed

- The Gradio UI, the services layer and the CLI healer.
- The vision pipeline and its prompt.
- The JSONL tracer, benchmarks, mutation engine and intent validation.
- The Docker image and its workflow.
- The Codecov upload. Coverage is printed in the CI job summary, and the build
  fails under 85%.
- The 1.0 heal loop, decision artifacts, CDP accessibility code, custom
  console and network listeners, and the Playwright report re-run configs.
- The LLM router, model registry, retry policies, `python-dotenv` and
  `.env.example`. No environment variable configures the app.

### Changed

- Type checking is strict for the whole package, and the unit suite fails under
  85% line and branch coverage.
- `npm run lint` now checks formatting and no longer checks files the app
  writes to `workspace/`.
- Muted text and the pass and warning colours are darker, so all text meets
  WCAG AA contrast.
- The result views (Diff, Re-run video, Execution log, Model I/O) are plain
  links, so they work as expected with a keyboard and a screen reader.
- CI runs four jobs (lint, unit, integration, UI) with actions pinned to
  commits, and Dependabot checks monthly.
- Python 3.13, Playwright 1.63.0 (the Python and npm packages pinned to the
  same version) and Node 24.
- The code is now the installable `workbench` package under `src/`, with all
  paths in `workbench.config`.
- Tests are split into `tests/unit` (the default pytest run) and
  `tests/integration`; the sample web app lives in `samples/site/`.
- `AGENTS.md`, `CONTRIBUTING.md` and `SECURITY.md` describe v2; `CLAUDE.md`
  points agents at `AGENTS.md`. The old documentation set was removed.
- The runner reads Playwright's JSON report; page context uses
  `aria_snapshot(mode="ai")` and Playwright's own console, page-error and
  request collections.
- Healer and generator prompts are version 3; the model is asked for
  schema-constrained output where the provider supports it.
- A failed model call names the provider and server and says what went wrong
  (not running, timed out, unknown model, or the server's own error).

### Fixed

- The code, diff and log panes can be focused, so they scroll from the keyboard.
- The runner uses Playwright's test outcomes (skipped tests, `test.fail()`,
  "No tests found") and stops at the first failure.
- The syntax-tree selector repair no longer rewrites a model's locator fix
  into a different call; fixes that change more than the selector are applied
  as written.
- Cancelling a run now stops it at once, even while the model is answering.
- Ctrl+C now stops the app during a run and cancels the run first.
- Model errors are named for what happened (unreachable, timed out, or failed).

### Security

- The app refuses requests from other sites and hosts, so a web page cannot
  start runs or change the model.
- A report's file path is checked a second time to stay inside
  `workspace/reports/`, independent of the report id pattern.

## [1.0.0] - 2026-09-28

The Gradio workbench: generation, healing and vision pipelines, benchmarks
and JSONL tracing.
