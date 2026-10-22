# ai-py-playwright-workbench

A local web app that generates Playwright tests and heals failing ones with a local LLM. It reads the page as it was when the test failed, repairs the code with a syntax-tree edit, re-runs the test to prove the fix, and refuses to patch a test when the app itself looks broken.

**Scope:** a small, auditable healing showcase with a focused test generator.
Generate inspects the starting page once; it does not explore your scenario
before writing the test. Checks on visible form controls and page content are
the best fit. Multi-page journeys and controls revealed after interaction may
use guessed locators, even with a capable model.

[![CI](https://github.com/yashwant-das/ai-py-playwright-workbench/actions/workflows/ci.yml/badge.svg)](https://github.com/yashwant-das/ai-py-playwright-workbench/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.64-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/)

![A heal from start to finish: the sample test is started, the steps run live, the diff and the diagnosis appear, then the Model I/O view](docs/assets/demo.gif)

The recording uses the built-in Demo model, which replays recorded answers, so it looks the same on any machine.

## Quickstart

You need Python 3.13 with [uv](https://docs.astral.sh/uv/), Node.js 24, and a desktop browser window at least 1280px wide. A model is optional.

1. **Install.**

   ```bash
   git clone https://github.com/yashwant-das/ai-py-playwright-workbench.git
   cd ai-py-playwright-workbench
   uv sync --locked --group dev
   npm ci
   npx playwright install chromium
   ```

2. **Start.**

   ```bash
   uv run workbench
   ```

   The app opens at <http://127.0.0.1:7860>. Press Ctrl+C to stop it.

3. **Heal the sample.** If no model server is running, press "Switch to demo model". Then press "Heal sample test" under **Selector drift** and watch the steps.

## Usage

- **Models.** The pill at the top right shows the model in use; click it to change it. Start [LM Studio](https://lmstudio.ai/) (`http://localhost:1234/v1`) or [Ollama](https://ollama.com/) (`http://localhost:11434/v1`), pick the provider, choose a model and save. A server that is already running is found on start, and its first listed model is used. Demo needs no server and covers the two samples and the "Contact form" example.
- **Heal.** Try the two samples: **Selector drift** heals, and **App bug** stops with "likely app bug" and leaves the test alone. To heal your own test, drop one `.spec.ts` file (200 KB at most) on the upload area. A copy is healed; your file is never changed.
- **Generate.** Enter a URL and a focused scenario, or choose an example to fill both fields. Public practice examples require LM Studio or Ollama and internet access; Demo supports the bundled Contact form. If the generated test fails, "Heal this test" sends it to Heal. Generation does not automatically revise a failed test.
- **Output.** Everything is written under `workspace/`, which git ignores: specs, Playwright's output and videos, one JSON report per run, and the saved model choice. Delete the folder to start fresh.
- **Limits.** One run at a time. A model call is given 300 seconds; Cancel stops a run at once. There is no history page yet: a saved report can be reopened at `/reports/<id>`.
- **Security.** The app listens on 127.0.0.1 only and refuses requests from other sites. Tests you upload or generate are code that runs on your machine, so heal only files you trust. See [SECURITY.md](SECURITY.md).

For runnable public scenarios and screenshots, see [generation examples](docs/generation.md).

## Verification

Run from the repository root after setup:

```bash
npm run lint                             # code, formatting, Python types and Markdown
npm run type-check                       # TypeScript
uv run python -m pytest --cov             # offline unit tests; 85% coverage minimum
uv run python -m pytest tests/integration # Chromium, local sample site and scripted models
npm run test:ui                          # whole app in Chromium, Demo model and axe
```

The unit suite needs no model, browser or network. Integration and UI runs use
Chromium from the locked Playwright package; they do not need a live LLM.
These scripted runs do not establish compatibility with a particular real model.
[Development](docs/development.md) documents prerequisites, hooks and check scope.

## Documentation

Profile: `complete`, adopting [repo-standards at c00f280](https://github.com/yashwant-das/repo-standards/tree/c00f280a94c5289aba795d240aaa963e7c886ed2).
[Adoption status and evidence](docs/development.md#standards-adoption) distinguish
local checks from published adoption and merge enforcement.

- [Development](docs/development.md): setup, checks, conventions and adoption evidence.
- [Architecture](docs/architecture.md): components, execution flow, boundaries and reports.
- [Decisions](docs/decisions.md): rationale and the comparison with Playwright Test Agents.
- [Generation examples](docs/generation.md): tested practice scenarios, limits and screenshots; kept separately because model-dependent examples need their own evidence.
- [Roadmap](ROADMAP.md): completed and deferred work.
- [Changelog](CHANGELOG.md): release history.
- [Historical design records](docs/superpowers/README.md): implementation plans and the v2 design, retained as context rather than current setup instructions.
- [Contributing](CONTRIBUTING.md) and [security](SECURITY.md): contribution and reporting policies.

## License

MIT. See [LICENSE](LICENSE).
