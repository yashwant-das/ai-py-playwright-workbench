# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

Work towards 2.0.0, tracked in [ROADMAP.md](ROADMAP.md).

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
- The 1.0 heal loop, decision artifacts, CDP accessibility code, custom
  console and network listeners, and the Playwright report re-run configs.
- The LLM router, model registry, retry policies, `python-dotenv` and
  `.env.example`. No environment variable configures the app.

### Changed

- The README now explains how to install, start and try the v2 app.
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

## [1.0.0] - 2026-09-28

The Gradio workbench: generation, healing and vision pipelines, benchmarks
and JSONL tracing.
