# ai-py-playwright-workbench

Generates Playwright tests from a URL and a scenario, and heals failing ones:
it diagnoses the failure with a local LLM, repairs the code with a TypeScript
syntax-tree edit and re-runs the test to prove the fix.

> **v2 is under construction on this branch.** The redesign is described in
> the [v2 spec](docs/superpowers/specs/2026-10-03-v2-showcase-simplification-design.md)
> and its progress is tracked in [ROADMAP.md](ROADMAP.md). The released 1.0
> version is tagged [`v1.0.0`](https://github.com/yashwant-das/ai-py-playwright-workbench/tree/v1.0.0).

## State of this branch

The web UI is being rebuilt (Phase 4), so there is nothing to launch yet. The
generate and heal pipelines are covered by tests:

```bash
uv sync --group dev
npm ci
npx playwright install chromium
uv run python -m pytest                    # unit tests: no model, no browser
uv run python -m pytest tests/integration  # real Chromium, fake model
```

## License

MIT. See [LICENSE](LICENSE).
