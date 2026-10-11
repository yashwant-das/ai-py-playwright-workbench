# ai-py-playwright-workbench

A local web app that generates Playwright tests from a URL and a scenario, and
heals failing ones: it works out why the test failed with a local LLM, repairs
the code with a TypeScript syntax-tree edit, and re-runs the test to prove the
fix.

> **This is the v2 branch, still in progress.** The app works end to end and is
> ready to try. Test suites, CI and the full documentation are still to come;
> see [ROADMAP.md](ROADMAP.md) and the
> [v2 spec](docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md).
> The released 1.0 version is tagged
> [`v1.0.0`](https://github.com/yashwant-das/ai-py-playwright-workbench/tree/v1.0.0).

## What you need

- Python 3.13 or newer, with [uv](https://docs.astral.sh/uv/)
- Node.js 24 or newer
- A desktop browser window at least 1280px wide
- Optional: [LM Studio](https://lmstudio.ai/) or [Ollama](https://ollama.com/)
  with a model loaded. Without one, the built-in Demo model replays recorded
  answers for the bundled samples.

## Install and start

```bash
uv sync --group dev
npm ci
npx playwright install chromium
uv run workbench
```

The app starts on <http://127.0.0.1:7860> and opens in your browser. Port 7860
must be free. Press Ctrl+C in the terminal to stop it; a run in progress is
cancelled first.

## Choose a model

The pill at the top right shows the model in use. Click it to change it.

- **LM Studio** (`http://localhost:1234/v1`) or **Ollama**
  (`http://localhost:11434/v1`): start the server, pick the provider, choose a
  model from the list and press Save. If a server is already running when the
  app starts, the app finds it and uses the first model it lists, so check the
  menu if you want a different one.
- **Demo**: no model needed. It only knows the two bundled samples and the
  "Contact form" example, and every Demo result is labelled.

The choice is saved in `workspace/settings.json`. No environment variables or
`.env` file are involved.

## Try it

### Heal

1. Open **Heal**.
2. Press "Heal sample test" on one of the two samples:
   - **Selector drift**: the submit button lost its id. The healer fixes the
     locator and the test passes again.
   - **App bug**: checkout fails on the server. The healer reports a likely app
     bug and leaves the test alone.
3. Watch the steps and the live log. When the run ends, the result page shows
   the diff, a video of the verification re-run, the execution log and exactly
   what was sent to and received from the model.

To heal your own test, drop a single `.spec.ts` file (200 KB at most) on the
upload area and press "Heal uploaded file". The file is copied into the
workspace; your original is never changed.

### Generate

1. Open **Generate**.
2. Enter a URL and describe the scenario, or click the "Contact form" example.
3. Press "Generate test". With "Run the test after generating" ticked, the new
   test is run straight away. If it fails, "Heal this test" sends it to Heal.

## Where things go

Everything the app writes is under `workspace/` in this folder, which git
ignores:

| Folder | Contents |
| --- | --- |
| `workspace/specs/` | Sample, uploaded and generated tests |
| `workspace/runs/` | Playwright output for each run, including videos |
| `workspace/reports/` | One JSON report per run; each has a page at `/reports/<id>` |
| `workspace/settings.json` | The saved model choice |

Delete `workspace/` to start fresh.

## Good to know

- **One run at a time.** Start buttons are disabled while a run is active.
- **Slow models.** A model call is given 300 seconds. After 30 seconds the run
  header says the model is still thinking. Cancel stops the run at once.
- **Local only.** The app listens on 127.0.0.1 and refuses requests from other
  sites and hosts. Tests you upload or generate are code that the app runs on
  your machine, so only heal files you trust.
- **Past runs.** There is no history page yet. Until the app is restarted, the
  idle page links the last finished run. Any saved report can be opened again
  at `/reports/<id>`, where the id is its file name in `workspace/reports/`
  without `.json`.

## Develop

```bash
uv run python -m pytest                    # unit tests: no model, no browser
uv run python -m pytest tests/integration  # real Chromium, fake model
npm run lint                               # ESLint, Prettier, Ruff, mypy (strict), markdownlint
npm run type-check                         # TypeScript
```

Project layout and rules are in [AGENTS.md](AGENTS.md).

## License

MIT. See [LICENSE](LICENSE).
