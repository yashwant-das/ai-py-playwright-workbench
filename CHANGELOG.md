# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

Work towards 2.0.0, tracked in [ROADMAP.md](ROADMAP.md).

### Added

- `ROADMAP.md` and this changelog.

### Removed

- The Gradio UI, the services layer and the CLI healer.
- The vision pipeline and its prompt.
- The JSONL tracer, benchmarks, mutation engine and intent validation.
- The Docker image and its workflow.

### Changed

- Python 3.13, Playwright 1.63.0 (the Python and npm packages pinned to the
  same version) and Node 24.
- The code is now the installable `workbench` package under `src/`, with all
  paths in `workbench.config`.
- Tests are split into `tests/unit` (the default pytest run) and
  `tests/integration`; the sample web app lives in `samples/site/`.
- `AGENTS.md`, `CONTRIBUTING.md` and `SECURITY.md` describe v2; `CLAUDE.md`
  points agents at `AGENTS.md`. The old documentation set was removed.

## [1.0.0] - 2026-09-28

The Gradio workbench: generation, healing and vision pipelines, benchmarks
and JSONL tracing.
