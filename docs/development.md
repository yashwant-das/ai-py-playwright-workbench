# Development

Setting up, running the checks, and the conventions the code follows.
[AGENTS.md](../AGENTS.md) has the module map and the rules in short form;
[architecture.md](architecture.md) explains how the parts fit.

## Set up

You need Python 3.13 with [uv](https://docs.astral.sh/uv/), and Node.js 24.

```bash
uv sync --locked --group dev
npm ci
npx playwright install chromium
```

`uv sync --locked --group dev` installs the development tools. `npm ci` installs Playwright
Test, which the app itself uses to run specs, and sets up the pre-commit hook.

## Run the app

```bash
uv run workbench
```

It serves <http://127.0.0.1:7860> and opens it in your browser. Runtime output
goes to `workspace/`. Two environment variables exist for tests and CI only:
`WORKBENCH_WORKSPACE` moves that folder and `WORKBENCH_PORT` changes the port.

## Tests

| Suite | Command | Needs |
| --- | --- | --- |
| Unit | `uv run python -m pytest` | Nothing: no model, no browser, no network |
| Integration | `uv run python -m pytest tests/integration` | Chromium |
| UI | `npm run test:ui` | Chromium |

- **Unit tests** call the pipelines with fake collaborators and the routes
  through FastAPI's `TestClient` (`tests/unit/web_support.make_client()`).
  Nothing is patched at module level.
- **Integration tests** run real specs in Chromium against the sample site,
  with the Demo model or a fake OpenAI-compatible server.
- **UI tests** are Playwright Test specs in `tests/ui/`. A fixture
  (`tests/ui/support/app.ts`) starts the app on a free port with a temporary
  workspace, so the suite never touches port 7860 or `workspace/`, and behaves
  the same whether or not a model server is running on your machine. Each page
  state is also checked with axe. After a failure,
  `npx playwright show-report` opens the HTML report.

## Quality gates

CI runs these as four jobs: lint, unit, integration and UI.

| Gate | Command | Passes when |
| --- | --- | --- |
| Python lint and format | `npm run lint:py` | Ruff reports nothing |
| Python types | `npm run lint:types` | mypy, strict, reports nothing |
| TypeScript types | `npm run type-check` | `tsc` reports nothing |
| JavaScript and TypeScript lint | `npm run lint:js` | ESLint reports no errors |
| Formatting | `npm run lint:format` | Prettier would change nothing |
| Markdown | `npm run lint:md` | markdownlint reports nothing |
| Unit tests and coverage | `uv run python -m pytest --cov` | All pass, with at least 85% line and branch coverage |
| Integration tests | `uv run python -m pytest tests/integration` | All pass |
| UI tests and accessibility | `npm run test:ui` | All pass; no serious or critical axe violation |

`npm run lint` runs the first six except the TypeScript types. The pre-commit
hook formats and lints the files you staged. CodeQL scans Python, TypeScript
and the workflows on pull requests to `main` and weekly; Dependabot opens
grouped update pull requests monthly.

## Conventions

- **Data shapes** are Pydantic models in `src/workbench/models/`. Model output
  is always parsed with `parse_llm_response()`, never `json.loads` alone.
- **Paths** come from `workbench.config`.
- **Models** are reached only through `ChatModel`.
- **Pipelines** take their collaborators as arguments; tests pass fakes.
- **Subprocesses** use argument lists, never `shell=True`.
- **UI:** the templates are the source of truth. Colours and type come only
  from `static/css/tokens.css`. There is no JavaScript beyond the vendored
  htmx files.
- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/).
  `ROADMAP.md` and `CHANGELOG.md` change in the same commit as the work.

## Changing a prompt

1. Edit the file in `src/workbench/prompts/` (`healer.md` or `generator.md`).
2. Raise that prompt's `version` in `src/workbench/prompts/manifest.json`.
3. Run the unit and integration tests.

The content hash is computed at run time. Each report records the prompt's
name, version and hash, so a result can always be traced to the prompt that
produced it. If the change alters what the Demo model should answer, update
the recording in `samples/recordings/` too.

## Refreshing the README's GIF and screenshots

```bash
npm run docs:capture
```

This drives the real app with the Demo model (`tests/ui/capture/`), rewrites
the screenshots in `docs/assets/`, and builds `demo.gif` from filmed frames.
Run it after a visible change to the UI and look at the results before
committing them.

## Releasing

1. Set the version in `pyproject.toml` and `package.json`, then run `uv lock`
   and `npm install --package-lock-only`.
2. Move the entries under `## [Unreleased]` in `CHANGELOG.md` into a section
   for the new version, with the date.
3. Run every gate above.
4. Merge to `main`, tag the commit `v<version>`, and publish a GitHub release
   with that section of the changelog.

## Standards adoption

Profile: `complete`. Target: [repo-standards c00f280a94c5289aba795d240aaa963e7c886ed2](https://github.com/yashwant-das/repo-standards/tree/c00f280a94c5289aba795d240aaa963e7c886ed2),
audited 2026-10-22 against `main` at `6cb85ca`. This branch proposes adoption;
publication and required-check enforcement are separate from local verification.

| Area | Status | Evidence or next action |
| --- | --- | --- |
| Documentation | in progress | README and four maintained guides organized; content, links and lint to verify |
| Structure/dependencies | in progress | Existing src layout, two root manifests, locks, Python 3.13 and Node 24 retained; registry and compatibility review underway |
| Hooks/CI | in progress | Retain Husky; align staged/full checks, locked installs and workflow safety |
| Publication | pending | Open an adoption PR after verification; owner reviews before merge |
| Required-check enforcement | pending | Audit settings and prepare exact check names for owner review |

Pending work is not an approved exception. Runtime-baseline changes and any
exception require owner review; no such change is included in documentation
adoption. Verification results and dependency decisions are recorded here as
technical adoption proceeds.
