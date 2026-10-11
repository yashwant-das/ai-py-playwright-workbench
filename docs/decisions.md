# Decisions

Why the workbench is built the way it is. The first table is the v2 redesign
([spec](superpowers/specs/2026-10-03-v2-showcase-simplification-design.md)).
The second lists decisions made while building it. The last section keeps the
1.0 decisions that still hold.

## The v2 redesign

| ID | Decision | Why |
| --- | --- | --- |
| D1 | Web UI only; no CLI and no `.env` | The user picks the provider and model in the UI. Fewer entry points and no setup file make the project easier to run and to explain. |
| D2 | FastAPI, Jinja, HTMX and server-sent events; no front-end build | Full control of the look without a second app or toolchain. Live progress maps directly onto server-sent events. |
| D3 | One report per run (`HealReport`, `GenerateReport`) | It replaces decision artifacts, timelines, traces and provenance records that overlapped. The UI, the downloads and the tests read the same object. |
| D4 | Providers: LM Studio, Ollama and Demo | Both local servers speak the OpenAI API, so one client covers both. Demo replays recorded answers, so the app works without a model. |
| D5 | Evidence comes from Playwright's `error-context.md` and the failing run's own output folder | Playwright already snapshots the page at the moment of failure. Re-opening the start page described the wrong state for any multi-step test. |
| D6 | `page.aria_snapshot(mode="ai")` and Playwright's own console, page-error and request collections | Public, maintained APIs replace custom CDP code and listeners. `mode="ai"` is the format Playwright itself writes into `error-context.md`, so Generate and Heal show the model the same thing. |
| D7 | Ask the model for JSON-schema output, then validate with Pydantic | It makes "structured output" true. If a server rejects the schema, the call is retried once without it and validation still applies. |
| D8 | The app-defect guard | A `POTENTIAL_APP_DEFECT` diagnosis with confidence 0.7 or more stops the heal without editing the test. One rule, and it answers the main criticism of self-healing: hiding real bugs. |
| D9 | Keep this project's own engine; compare it with Playwright Test Agents in the README | Test Agents are instructions and MCP tools run inside a coding assistant. This project is a standalone pipeline for local models with constrained, auditable fixes. Replacing the engine would leave nothing to show. |
| D10 | The package is `workbench` under `src/` | `from src.healing import …` used `src` as a package name. A proper src layout fixes imports and packaging. |
| D11 | All runtime output goes to one git-ignored `workspace/` folder | It replaces five scattered output folders. |
| D12 | pytest-style tests in `tests/unit`, `tests/integration` and `tests/ui` | Clear levels: nothing external, real browser, whole app. |
| D13 | Python 3.13, Playwright 1.63.0 (Python and npm pinned to the same version), Node 24 | Current, supported versions. Matching pins keep the Python library and the test runner on the same browser builds. |
| D14 | The runner reads Playwright's JSON report, not terminal output | The report gives each test's status, error and location, and the exact paths of its screenshot and `error-context.md`. It replaces parsing stdout and searching for files. |
| D15 | Verification re-runs are recorded as video with each action captioned | Visible proof that the fix works. Only verification runs are recorded, to keep the workspace small. |

## Decisions made while building v2

| Decision | Why |
| --- | --- |
| The app checks `Host` and `Origin` on every request | A local app still receives requests from pages open in the same browser. Without the check, another site could have posted a spec and had it run. |
| A model call can be abandoned | A local model can take minutes. Cancel returns at once by leaving the call to finish on its own thread; the run ends as cancelled. |
| Starting a run redirects to the same page with the run's id | The page then renders the run from the server's state: start buttons are locked, and a run that finishes before the reload is still shown. |
| A finished run redirects to its report page | The live view and a later visit render the same saved report, so there is one way to show a result. |
| The result views are links, not ARIA tabs | Each view is a page load. Links with `aria-current` are correct and work from the keyboard without script. |
| Four colours were changed for contrast | Muted text, pass green, warning amber and muted code text did not meet WCAG AA contrast. The app and the Figma file both have the corrected values. |
| States the Demo model cannot produce are tested from saved reports | "Healed after retries" or "invalid model reply" need a model that misbehaves. The UI suite renders them from report files instead of scripting a fake conversation. |
| Coverage is not uploaded to a third party | It is printed in the CI job summary, and the build fails under 85%. |

## Decisions kept from 1.0

### Pydantic models for every data shape

Model output, reports, events and settings are Pydantic models in
`src/workbench/models/`. Validation happens when the data is parsed, the same
classes produce the JSON schema sent to the model, and a report on disk is just
a model dumped as JSON. Dataclasses with hand-written validation, `attrs` and
`msgspec` were considered; none gives validation, schema export and wide
support together.

### ts-morph for syntax-tree repair, in a Node subprocess

A fix such as "replace this locator" is applied to the TypeScript syntax tree,
so formatting and everything around the change are untouched. ts-morph is
built on the TypeScript compiler, and Node is already required by Playwright.
Python sends the source and the change on stdin and reads the result on
stdout; a crash or timeout in the script cannot take the pipeline down, and
the fix then falls back to an exact text replacement. Regular expressions
(too fragile) and tree-sitter (reads trees well, awkward for edits) were
rejected.

### Prompts are files with a version manifest

The prompts live in `src/workbench/prompts/*.md`, not in Python strings, so a
prompt change is a readable diff. `manifest.json` holds a version for each
prompt, bumped by hand when its content changes; a content hash is computed at
run time. Every report records the prompt's name, version and hash.

### One browser session per context collection

The page context (accessibility snapshot, locator candidates, console and
network errors) is collected in a single visit to the page. Separate visits
per collector were slower and could each see a different page.

### The OpenAI SDK instead of a routing library

Both supported servers expose the OpenAI API, so `openai.OpenAI(base_url=…)`
is all the abstraction needed. A general routing library would add a large
dependency for providers this project does not use.
