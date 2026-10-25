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
| Tooling | `npm run test:tooling` | Node.js; no services |
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
| Text conventions | `npm run lint:text` | No trailing whitespace, missing final newlines or conflict markers |
| Tooling behavior | `npm run test:tooling` | All text-checker behavior tests pass |
| Markdown | `npm run lint:md` | markdownlint reports nothing |
| Unit tests and coverage | `uv run python -m pytest --cov` | All pass, with at least 85% line and branch coverage |
| Integration tests | `uv run python -m pytest tests/integration` | All pass |
| UI tests and accessibility | `npm run test:ui` | All pass; no serious or critical axe violation |

`npm run lint` runs lint, formatting, Python types, maintained Markdown and
text checks; `npm run type-check` checks TypeScript separately. `npm test` runs
the tooling and Python unit suites. CI independently checks all maintained files
with the same configurations; staged filters do not narrow CI scope.

### Hooks and exclusions

`npm ci` installs the existing Husky hook. Run `npm run lint:staged` to check the
Git index, or run the full commands above to check all maintained files. Hooks
run Ruff's full rule set and formatter, ESLint, Prettier, Markdown lint and the
text checker in check mode. Fix and restage changes yourself; a failed hook
blocks the commit and must not be bypassed without explicit owner authorization.
Builds, type checking, tests and browser runs stay outside the pre-commit hook.

Markdown lint selects root documents, maintained guides and community Markdown.
Historical design/plan directories are excluded; their maintained index is checked.
Prompt Markdown is executable application data, not setup documentation, and is
reviewed through prompt versioning and tests. The text checker also preserves
historical records and vendored libraries. Prettier's existing exclusions retain
intentional broken fixtures, sample specs, vendored assets and generated output.
Intentional Markdown hard breaks remain valid. The shared text checker strictly parses `.json` with `JSON.parse`; Prettier checks
JSONC and YAML syntax and configuration formatting, including `.prettierrc`.
Prompt templates are excluded in the shared Markdown configuration so staged
checks and CI use the same documentation boundary.

CodeQL scans Python, TypeScript and workflows on PRs and weekly. Dependabot
proposes grouped minor/patch updates weekly for uv and npm, and weekly action
updates. Major upgrades require explicit review; no automation merges them.

### Proposed required checks

The 2026-10-22 account audit found no protection on `main` and no rulesets.
Workflow presence does not enforce merging. After successful checks on the PR,
the owner can require these exact contexts on `main`:

- `Lint and types`
- `Unit tests and coverage`
- `Integration (real Chromium, Demo and fake models)`
- `UI (Playwright Test, axe, Demo model)`
- `Analyze (python)`, `Analyze (javascript-typescript)` and `Analyze (actions)`

Require a pull request and passing checks on the revision being merged. This
PR prepares the check list; applying protection is a separate account change
for owner approval. No check is bypassed or marked required by this document.

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

Profile: `complete`. Target: [repo-standards 073f51ff68ec050f6b3372c46bc3bd4e721a5342](https://github.com/yashwant-das/repo-standards/tree/073f51ff68ec050f6b3372c46bc3bd4e721a5342),
audited 2026-10-22 against `main` at `6cb85ca`. This branch proposes adoption;
publication and required-check enforcement are separate from local verification.

| Area | Status | Evidence or next action |
| --- | --- | --- |
| Documentation | verified locally | README, four maintained guides and historical index pass content/link tests and Markdown lint |
| Structure/dependencies | verified locally | Retained layout/baselines, refreshed compatible locks; full unit, type and browser suites pass; security constraints below require review |
| Hooks/CI | verified locally | Check-only Husky gates, matching CI rules, locked installs, weekly updates, caching, timeouts and short retention; hosted CI pending |
| Publication | pending | Open an adoption PR after verification; owner reviews before merge |
| Required-check enforcement | pending | Audit settings and prepare exact check names for owner review |

### Compatibility review

Registry metadata was checked on 2026-10-22. Resolved versions live in
[uv.lock](../uv.lock) and [package-lock.json](../package-lock.json).

- Preserve Python 3.13 and Node 24. Rechecked the official [Python status](https://devguide.python.org/versions/)
  and [Node schedule](https://github.com/nodejs/Release/blob/main/schedule.json);
  neither baseline needs an upgrade for this adoption.
- Keep Playwright Python and all three Node runner packages at 1.64.0. npm
  offers 1.64.1 while the Python registry offers 1.64.0; this project deliberately
  tests one identical binding set. Review when both bindings support the next
  common stable release. This is stricter than the shared default.
- Use OpenAI 2.54.0, the newest stable 2.x release. Candidate 3.36.1 changed the
  injected HTTP client's type and URL exception class; the invalid-port test and
  strict mypy rejected it. A separate transport migration must preserve those
  contracts before adopting 3.x. Owner: Yashwant Das; review on that migration
  or an actionable security update affecting 2.x.
- TypeScript 6.0.3 fits typescript-eslint's declared `<6.1.0` peer bound;
  TypeScript 7 does not. Node16 module resolution replaces deprecated Node10
  resolution, with explicit Node types matching the Node 24 runtime. ESLint 10
  and the matching TypeScript parser/plugin are resolved through typescript-eslint.
- The updated axe check found label/name mismatches. Accessible names now include
  the visible model, sample and example labels; no rule or impact level is disabled.

### Pending security and owner decisions

`npm audit` reports eight affected development-tool packages from two upstream
advisories (five high, three low), through the required Markdown linter:

- [braces stack exhaustion](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm):
  latest stable braces 3.0.3 remains affected; no patched release is available.
- [KaTeX trust bypass](https://github.com/advisories/GHSA-238p-pmpm-9mq7):
  patched 0.18.2 exists, but micromark-extension-math requires `^0.16.0`.
  Overriding that range is an unverified compatibility change.

These are development tools, not app runtime dependencies. Lint uses repository
controlled patterns and does not render math. Review incoming tooling/config
changes; keep weekly update PRs enabled. This limits exposure but is not proof
of safety. The audit's suggested markdownlint-cli2 0.0.4 downgrade would discard
the current checker, so it is not applied. Owner: Yashwant Das. Review when the
upstream graph receives a compatible fix, the advisory changes, or tool usage
changes. Retention of this graph is proposed for owner review, not an authorized
exception or a clean audit claim.

Required-check enforcement also remains pending owner approval. Runtime-baseline
changes are not included. Full adoption is not claimed while these owner actions
remain pending.

### Verification evidence

Verified 2026-10-22 on macOS/Apple Silicon, Python 3.13.15, Node 24.21.0 and
npm 11.19.0:

- `npm run lint` and `npm run type-check`: pass. Ruff checks 144 Python files;
  strict mypy checks 62 package files; Markdown lint checks 12 maintained files.
- `uv run python -m pytest --cov`: 579 tests and two subtests pass, 95.55%
  combined line/branch coverage against the unchanged 85% threshold.
- `npm run test:tooling`: all eight behavior tests pass. The original five failed
  before implementation; strict-JSON and full-mode regressions failed against
  the original helper before the review fix pass.
- `uv run python -m pytest tests/integration`: all 17 tests pass with real Chromium
  and scripted models, including generation, healing, cancellation and shutdown.
- `npm run test:ui`: all 39 tests pass with axe 4.14.0. The accessible-name
  regression was observed failing before the template fixes.

Actual Husky commits in a disposable Git repository accepted valid Markdown
(including hard breaks) and JSONC, and rejected invalid Markdown, trailing
whitespace, malformed JSON/YAML, comments in strict JSON, malformed `.prettierrc`
and undefined JavaScript calls. Prompt data remained exempt from documentation
lint. A partially staged Markdown commit preserved its unstaged changes and
committed only the staged content. All eleven probes matched their expected
result; no real repository hook was bypassed.
A fresh clone at `4569fcd` passed `npm ci`, `uv sync --locked --group dev`,
`npm test`, `npm run lint` and `npm run type-check` without tracked changes.
The final review fix pass passed the complete `npm test`, `npm run lint` and
`npm run type-check` suites, plus direct prompt-CLI checks and the eleven hook
probes above. Independent review findings (prompt scope, strict JSON, staged
extensionless config and full-mode deletion handling) are addressed without
suppressing checks.
Hosted CI and CodeQL results belong to the PR; local checks do not replace them.
Scripted browser runs do not prove behavior with a live LM Studio or Ollama model;
no change to the live-provider contract is proposed here.

### Showcase standards rework (2026-10-25)

The current `complete` profile is pinned to merged standards revision
`073f51ff68ec050f6b3372c46bc3bd4e721a5342` in AGENTS.md and this guide. The root
README now includes concrete mechanisms, a Heal/Generate architecture diagram,
structure/stack summaries and report locations while preserving the Demo GIF,
its replay disclosure, runnable setup and starting-page generation limits. The
architecture guide adds a request/run/event/report lifecycle sequence. CLAUDE.md
is a one-line Markdown pointer to AGENTS.md, with no duplicated instructions.
The existing `.python-version` and `.nvmrc` already select Python 3.13 and Node.js 24.
No application, prompt, dependency, hook or workflow implementation is changed.

At prior head `4b47a7c`, hosted lint/types, unit/coverage, integration, UI and
all three CodeQL language jobs succeeded. These results do not establish the
new head’s status or compatibility with an actual LM Studio/Ollama model. The
previously recorded dependency advisory and merge-protection decisions remain
open for owner review; no exception has been silently authorized.

Metadata audit: the current description exceeds the new 110-character limit.
Proposed description for owner review:
`Generates and heals Playwright tests with FastAPI, LM Studio and Ollama (proof of concept)`.
Proposed topic set, grouped by category/language/tools/technique:
`ai-testing`, `python`, `playwright`, `fastapi`, `ollama`, `lm-studio`,
`self-healing-tests`, `test-generation`.
This replaces the second category `llm` with the app’s web framework and stays
within eight topics. Native GitHub topic display order is not evidence of policy
ordering. No repository description, topic or account-setting changes were made.

Validation for this rework: the full 579-test offline suite and two subtests
passed with 95.55% coverage (85% threshold retained); all eight tooling tests,
Ruff lint/format, strict mypy, ESLint/Prettier, TypeScript and Markdown checks
passed. Existing doc-link and npm-command tests continue to pass without a new
layout validator. All maintained local file links and anchors resolve. The
three diagrams (root architecture, component map and run lifecycle) rendered
with Mermaid12.2.0 in Chromium and were visually inspected. Existing Demo media
were retained; the healed-result PNG was inspected and remains labelled Demo.
No new test suite or repository rendering tool was added.
