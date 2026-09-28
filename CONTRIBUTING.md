# Contributing

Thanks for taking a look. This is a reference project, so changes should keep
the code small, typed and covered by tests.

## Set up

Follow [docs/development/setup.md](docs/development/setup.md). In short:

```bash
uv sync --group dev
npm ci
npx playwright install chromium
```

The unit tests need no LLM and no browser.

## Before you open a pull request

Run the same checks CI runs:

```bash
npm run lint          # ESLint, Ruff, mypy and markdownlint
uv run ruff format .  # format Python
npm run type-check    # TypeScript
npm test              # Python unit tests
```

The Husky pre-commit hook formats and lints staged files for you.

## Conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `chore(ci):` and so on).
- Data shapes live in `schemas/` as Pydantic models; LLM output is always
  parsed with `parse_llm_response()`.
- New healing strategies, models and benchmarks each have a guide in
  [docs/development/](docs/development/).
- Keep pull requests focused: one change, with tests for new behaviour.

## Security

Please report vulnerabilities privately; see [SECURITY.md](SECURITY.md).
