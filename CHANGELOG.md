# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

Work towards 2.0.0, tracked in [ROADMAP.md](ROADMAP.md).

### Added

- `ROADMAP.md` and this changelog.
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

- The runner uses Playwright's test outcomes (skipped tests, `test.fail()`,
  "No tests found") and stops at the first failure.
- The syntax-tree selector repair no longer rewrites a model's locator fix
  into a different call; fixes that change more than the selector are applied
  as written.

## [1.0.0] - 2026-09-28

The Gradio workbench: generation, healing and vision pipelines, benchmarks
and JSONL tracing.
