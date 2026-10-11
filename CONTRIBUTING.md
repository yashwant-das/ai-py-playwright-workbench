# Contributing

Thanks for taking a look. Changes should keep the code small, typed and
covered by tests.

## Set up

```bash
uv sync
npm ci
npx playwright install chromium
```

The unit tests need no model, no browser and no network.
[docs/development.md](docs/development.md) explains the test levels and the
quality gates.

## Before you open a pull request

Run the checks CI runs:

```bash
uv run python -m pytest --cov              # unit tests; fails under 85% coverage
uv run python -m pytest tests/integration  # integration tests
npm run test:ui                            # UI tests
npm run lint                               # ESLint, Prettier, Ruff, mypy (strict), markdownlint
npm run type-check                         # TypeScript
```

The Husky pre-commit hook formats and lints staged files for you.

## Conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/).
- Data shapes are Pydantic models in `src/workbench/models/`; LLM output is
  always parsed with `parse_llm_response()`.
- Update [ROADMAP.md](ROADMAP.md) and [CHANGELOG.md](CHANGELOG.md) with the change.
- Keep pull requests focused: one change, with tests for new behaviour.
- [AGENTS.md](AGENTS.md) has the layout and the rules in more detail.

## Security

Please report vulnerabilities privately; see [SECURITY.md](SECURITY.md).
