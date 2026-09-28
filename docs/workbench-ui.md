# Workbench UI

The Gradio app (`uv run python src/app.py`, then <http://127.0.0.1:7860>) has eight tabs. The UI only wires inputs to `src/services/`; every pipeline can also be called from Python.

## Overview

Shows the system status and one run history table, with a row per decision artifact across the generation, healing and vision pipelines. **Refresh Recent Runs** reloads it.

## Generation Pipeline

Enter a target URL and a plain-English scenario. **Generate Test** produces a TypeScript spec from the page's DOM, accessibility tree and console signals. **Run Test** executes it straight away.

## Healing Pipeline

Upload a broken `.spec.ts` file, set **Max Repair Attempts** (1 to 5) and click **Run Healing Pipeline**. The pipeline:

1. Runs the test and captures the failure
1. Gathers evidence: error log, DOM, accessibility tree, console errors, network errors, screenshot
1. Pre-classifies the failure type with a heuristic classifier (deterministic, no LLM)
1. Asks the LLM to plan the repair and propose a code fix
1. Applies the fix with AST-based strategies: selector replace, import add, timeout adjust, role argument, assertion swap
1. Re-runs the test to verify
1. Repeats up to the configured limit

The **Decision Report** tab shows `HealingDecision.to_markdown()`: failure type, hypothesis, confidence and its rationale, root cause evidence, the code change, and provenance (model, prompt version, execution time).

## Vision Pipeline

Enter a URL and an instruction. The pipeline captures a screenshot, sends it to a vision-capable model and writes a test from what is visible on screen. Useful when the DOM alone is not enough.

## Artifact Inspector

Browses the decision artifacts written to `tests/artifacts/` after every generation, healing and vision run. Selecting one renders the markdown report next to the raw JSON, including provenance: model, prompt version and hash, planning time, and the evidence snapshot used.

## Evaluation

- **Heuristic Classification** runs the classification benchmark against `benchmarks/healing/fixtures/repair_scenarios.json`. No LLM or browser needed; it finishes in milliseconds and shows expected against classified failure type and confidence per case.
- **Generation (LLM)** runs the generation benchmark against `benchmarks/generation/fixtures/web_scenarios.json`. Needs a running local model.

See [evaluation/benchmarks.md](evaluation/benchmarks.md) for running the same benchmarks from Python.

## Trace Inspector

Loads `logs/traces.jsonl` and shows session, LLM call and subprocess spans linked by `trace_id`: token usage, latency and retries without leaving the UI. The same data can be queried with `jq`; see [architecture/observability.md](architecture/observability.md).

## Models

Shows the active model configuration from `LM_STUDIO_TEXT_MODEL`, `LM_STUDIO_VISION_MODEL`, `OLLAMA_TEXT_MODEL` and `OLLAMA_VISION_MODEL`, with capability metadata from the `ModelRegistry`. **Refresh** reloads it.

## Running the healing pipeline from Python

```bash
uv run python -c "
from src.services.healing_service import heal_test_streaming
for step in heal_test_streaming('tests/generated/my_broken_test.spec.ts', 3):
    print(step[0])
"
```
