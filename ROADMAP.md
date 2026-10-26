# Roadmap

Current work and deferred ideas. The completed redesign is recorded in the
[changelog](CHANGELOG.md) and [historical design records](docs/superpowers/README.md).

## Now

Review [PR #26](https://github.com/yashwant-das/ai-py-playwright-workbench/pull/26):
repository standards adoption, documentation cleanup and the Playwright
Workbench display title. Check results and
outstanding owner decisions are in the
[development guide](docs/development.md#standards-adoption).

## Next

No feature work is scheduled. The ideas below are deferred, not commitments.

## Later

- Generate: replace starting-page-only collection with session-based exploration that gathers evidence from pages and controls reached during a scenario. Reuse the existing pipeline and ChatModel interface, and extend GenerateReport with the observed journey rather than introducing a separate agent subsystem. Action limits, retry budgets and cancellation behavior require a future design; this is deferred scope, not a current capability.

- Stream Playwright's own output into the live log; today the log is built from pipeline events, because the runner reads the JSON report after the run.
- A run history page listing past reports (reports are already saved and linkable).
- CI integration: a GitHub Action that heals failing specs and opens a pull request, or flags a suspected app bug.
- Review the classifier’s treatment of "waiting for locator" timeouts: it currently favors locator problems over slow pages.
- Cloud providers (Anthropic, OpenAI).
- A benchmark built from a deliberately mutated sample app.
- Comparing heals with Playwright's own healer agent.
- Dark mode.
- Heal, idle screen: show the "How healing works" card from the Figma file (five steps and three chips) instead of the plain empty card.
- Generate, run failed: show the banner from the Figma file that names the failing line and points to "Heal this test".
- Renaming the repository.
- Heal: send Playwright's marked "Test source" block from `error-context.md` to the planner as its own prompt section (spec E2; currently the whole file plus file:line:col is sent).
- Heal: record a failed model call as an attempt with its `ModelExchange` (an outcome such as `model_error`, sections built before the call) so the Model I/O view shows it.
- Generate: guard unexpected exceptions after the spec is written (end the active step, save an error report) and reject a reply with no `test(` block as an invalid reply.
- Review timestamp-based report-id collisions for repeated runs within the same second. The web registry serializes active runs, and generated spec names already avoid existing files.
- Warn when a prompt may not fit the selected model’s context window; per-section character limits do not measure the server’s token budget.
- Heal: review the `role_argument` and `timeout_adjust` AST strategies, which extract values from `fixed_code` as loosely as `selector_replace` did.
- Give reports a typed model-failure kind instead of matching message text.

## Completed work

Version 2.0 replaced the Gradio/CLI/vision stack with the local FastAPI/HTMX app,
Heal and Generate pipelines, saved reports, Demo samples and browser quality
gates. Later updates added public generation presets and documented their
starting-page limits. See the [changelog](CHANGELOG.md) for release details and
the [historical index](docs/superpowers/README.md) for the six implementation phases.
