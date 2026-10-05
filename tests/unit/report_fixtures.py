"""One realistic saved report per result state: for the template tests and the walkthrough.

    WORKBENCH_WORKSPACE=/tmp/ws uv run python -c \
        "from tests.unit.report_fixtures import write_all; print(write_all())"
"""

from collections.abc import Callable
from typing import Any

from workbench.ids import new_run_id
from workbench.models.heal import (
    Attempt,
    FailureEvidence,
    HealingAction,
    HealingAnalysis,
    HealReport,
    RepairStrategy,
)
from workbench.models.shared import (
    FailureType,
    ModelExchange,
    PromptSection,
    Provenance,
    RunResult,
)
from workbench.reports import save_report

ORIGINAL = """import { test, expect } from '@playwright/test';

test('Contact form sends a message', async ({ page }) => {
  await page.goto('http://127.0.0.1:7860/sample-site/');
  await page.getByLabel('Name').fill('Ada Lovelace');
  await page.locator('#submit-btn').click({ timeout: 3000 });
  await expect(page.getByRole('status')).toHaveText('Submitted');
});
"""
FIXED = ORIGINAL.replace(
    "page.locator('#submit-btn')", "page.locator('[data-testid=\"submit\"]')"
)
DIFF = """--- a/contact-form.spec.ts
+++ b/contact-form.spec.ts
@@ -6 +6 @@
-  await page.locator('#submit-btn').click({ timeout: 3000 });
+  await page.locator('[data-testid="submit"]').click({ timeout: 3000 });
"""
TIMEOUT = "TimeoutError: locator.click: Timeout 3000ms exceeded.\n  - waiting for locator('#submit-btn')"


def run_result(status: str = "failed", **fields: Any) -> RunResult:
    values: dict[str, Any] = {
        "status": status,
        "duration_ms": 2400,
        "error_message": TIMEOUT if status == "failed" else "",
        "stdout": "Running 1 test using 1 worker\n",
    }
    values.update(fields)
    return RunResult(**values)


def analysis(
    failure_type: FailureType = FailureType.LOCATOR_DRIFT,
    confidence: float = 0.9,
    original: str = "page.locator('#submit-btn')",
    fixed: str = "page.locator('[data-testid=\"submit\"]')",
    strategy: RepairStrategy = RepairStrategy.SELECTOR_REPLACE,
) -> HealingAnalysis:
    return HealingAnalysis(
        failure_type=failure_type,
        failure_summary="The click on #submit-btn timed out.",
        hypothesis='The button lost its id but keeps data-testid="submit".',
        confidence_score=confidence,
        confidence_rationale="One button named Submit in the snapshot.",
        reasoning_steps=[
            "The click waits for #submit-btn, which is not on the page.",
            'The page snapshot at the failure has a button named "Submit".',
            'The button still carries data-testid="submit".',
        ],
        root_cause_evidence=[
            'button "Submit" in the page snapshot',
            "Timeout 3000ms exceeded",
        ],
        action_taken=HealingAction(
            original_code=original,
            fixed_code=fixed,
            description="Target the button by its test id.",
            repair_strategy=strategy,
        ),
    )


def exchange(
    provider: str = "ollama",
    model: str = "qwen3.6:35b-mlx",
    valid: bool = True,
    error: str = "",
) -> ModelExchange:
    return ModelExchange(
        sections=[
            PromptSection(name="Test file", chars=310),
            PromptSection(name="Error", chars=420),
            PromptSection(
                name="Page snapshot at failure", chars=12_000, original_chars=18_000
            ),
            PromptSection(name="Locator candidates", chars=180),
        ],
        raw_response='{"failure_type": "LOCATOR_DRIFT", "confidence_score": 0.9}'
        if valid
        else "Sure! Here is the fix:",
        valid=valid,
        validation_error=error,
        provenance=Provenance(
            provider=provider,
            model=model,
            prompt_name="healer",
            prompt_version="3",
            prompt_hash="3f9a1c2b7d4e5f60",
            input_tokens=4812,
            output_tokens=386,
            latency_ms=6800,
        ),
    )


def attempt(number: int, outcome: str, **fields: Any) -> Attempt:
    values: dict[str, Any] = {
        "number": number,
        "outcome": outcome,
        "evidence": FailureEvidence(error_message=TIMEOUT, source="error_context"),
        "analysis": analysis(),
        "exchange": exchange(),
        "duration_ms": 9800,
    }
    if outcome == "healed":
        values.update(
            repair_method="ast",
            rerun=run_result(
                "passed", duration_ms=2100, video_path="/nonexistent/video.webm"
            ),
        )
    if outcome == "rerun_failed":
        values.update(repair_method="ast", rerun=run_result("failed", duration_ms=3100))
    values.update(fields)
    return Attempt(**values)


def _report(name: str, status: str, **fields: Any) -> HealReport:
    values: dict[str, Any] = {
        "id": new_run_id("heal", name),
        "spec_name": "contact-form.spec.ts",
        "status": status,
        "initial_run": run_result("failed"),
        "original_code": ORIGINAL,
        "final_code": ORIGINAL,
        "classifier_hint": "TIMEOUT",
        "duration_ms": 12_700,
    }
    values.update(fields)
    return HealReport(**values)


def healed() -> HealReport:
    return _report(
        "healed", "healed", attempts=[attempt(1, "healed")], final_code=FIXED, diff=DIFF
    )


def healed_after_retries() -> HealReport:
    return _report(
        "healed-after-retries",
        "healed",
        attempts=[attempt(1, "not_applied", repair_method=None), attempt(2, "healed")],
        final_code=FIXED,
        diff=DIFF,
        duration_ms=24_900,
    )


def not_healed() -> HealReport:
    return _report(
        "not-healed",
        "not_healed",
        attempts=[
            attempt(1, "rerun_failed"),
            attempt(2, "not_applied", repair_method=None),
            attempt(
                3,
                "invalid_reply",
                analysis=None,
                exchange=exchange(valid=False, error="action_taken: Field required"),
            ),
        ],
    )


def app_defect() -> HealReport:
    bug = analysis(
        FailureType.POTENTIAL_APP_DEFECT, 0.95, "", "", RepairStrategy.STRING_REPLACE
    )
    return _report(
        "app-defect",
        "app_defect_suspected",
        spec_name="checkout.spec.ts",
        attempts=[attempt(1, "app_defect", analysis=bug)],
    )


def nothing_to_heal() -> HealReport:
    return _report(
        "nothing", "nothing_to_heal", initial_run=run_result("passed"), duration_ms=2300
    )


def cancelled() -> HealReport:
    return _report(
        "cancelled",
        "cancelled",
        attempts=[attempt(1, "rerun_failed")],
        duration_ms=14_000,
    )


def model_error() -> HealReport:
    return _report(
        "model-error",
        "error",
        error_message="The model call failed: Could not reach Ollama at http://localhost:11434/v1. Is it running?",
    )


def demo_healed() -> HealReport:
    demo = attempt(
        1, "healed", exchange=exchange(provider="demo", model="recorded-answers")
    )
    return _report("demo", "healed", attempts=[demo], final_code=FIXED, diff=DIFF)


def with_warnings() -> HealReport:
    text_fix = attempt(1, "healed", repair_method="text")
    return _report(
        "warnings",
        "healed",
        attempts=[text_fix],
        final_code=FIXED,
        diff=DIFF,
        warnings=["page_context_unavailable", "ast_unavailable"],
    )


HEAL_STATES: dict[str, Callable[[], HealReport]] = {
    "healed": healed,
    "healed_after_retries": healed_after_retries,
    "not_healed": not_healed,
    "app_defect": app_defect,
    "nothing_to_heal": nothing_to_heal,
    "cancelled": cancelled,
    "model_error": model_error,
    "demo_healed": demo_healed,
    "with_warnings": with_warnings,
}


def write_all() -> dict[str, str]:
    """Save one report per state; returns state name → report id."""
    ids = {}
    for name, build in HEAL_STATES.items():
        report = build()
        save_report(report)
        ids[name] = report.id
    return ids
