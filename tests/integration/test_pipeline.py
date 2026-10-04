"""
End-to-end suite: generation and healing against a real browser.

Only the LLM is faked (see tests/integration/fake_llm.py); everything else is real —
context collection opens Chromium on a sample site in samples/site/, specs are
executed with ``npx playwright test``, and the heal loop applies its repair
through src/workbench/heal/ast_repair.js. Healed specs and reports live in the
workspace folder.

Run from the repo root:

    uv run python -m pytest tests/integration

The specs are left in tests/generated/ so ``npm run test:e2e:report`` can
re-run them for the HTML report and JUnit XML.
"""

import os
from pathlib import Path

import pytest

from tests.integration.conftest import SITE_URL
from tests.integration.fake_llm import FakeLLM
from workbench.config import specs_dir
from workbench.generate.pipeline import generate_test_script
from workbench.heal import HealRequest, heal
from workbench.llm import _reset_default_router_for_testing, get_default_router
from workbench.llm.chat import RouterChatModel
from workbench.reports import load_report
from workbench.runner import run_test

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATED_DIR = PROJECT_ROOT / "tests" / "generated"

GENERATED_SPEC = GENERATED_DIR / "e2e_generated_contact.spec.ts"

BROKEN_SPEC = f"""import {{ test, expect }} from "@playwright/test";

// The submit button used to be #submit-btn; the site now uses data-testid="submit".
test("Submit the contact form after a selector drift", async ({{ page }}) => {{
  await page.goto("{SITE_URL}");
  await page.getByLabel("Name").fill("Ada");
  await page.locator("#submit-btn").click({{ timeout: 3000 }});
  await expect(page.locator("#result")).toHaveText("Submitted");
}});
"""


@pytest.fixture(scope="module")
def fake_llm():
    overrides = {
        "LLM_PROVIDER": "lm_studio",
        "LM_STUDIO_TEXT_MODEL": "fake-model",
        "LM_STUDIO_API_KEY": "fake-key",
    }
    with FakeLLM() as llm:
        overrides["LM_STUDIO_URL"] = llm.base_url
        saved = {key: os.environ.get(key) for key in overrides}
        os.environ.update(overrides)
        _reset_default_router_for_testing()
        try:
            yield llm
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            _reset_default_router_for_testing()


@pytest.fixture(scope="module", autouse=True)
def clean_generated():
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    GENERATED_SPEC.unlink(missing_ok=True)


def test_generated_spec_passes_in_a_real_browser(site, fake_llm):
    decision = generate_test_script(site, "A user can submit the contact form")

    # The generator collected live page context from Chromium and sent it on.
    prompts = fake_llm.prompts_containing("USER STORY:")
    assert prompts, "generator never called the LLM"
    assert "PAGE SNAPSHOT" in prompts[-1]
    assert "Submit" in prompts[-1]

    assert site in decision.code
    assert decision.provider == "lm_studio"
    GENERATED_SPEC.write_text(decision.code, encoding="utf-8")

    result = run_test(GENERATED_SPEC.relative_to(PROJECT_ROOT))
    assert result.passed, result.output


def test_heal_loop_repairs_a_drifted_selector(site, fake_llm):
    spec = specs_dir() / "healed-contact.spec.ts"
    spec.write_text(BROKEN_SPEC, encoding="utf-8")

    report = heal(
        HealRequest(spec_path=spec, max_attempts=2),
        model=RouterChatModel(get_default_router()),
    )

    assert report.status == "healed", report.model_dump_json(indent=2)
    prompts = fake_llm.prompts_containing("## Test file")
    assert prompts, "healer never called the LLM"
    assert "## Page snapshot at failure" in prompts[-1]
    healed = spec.read_text(encoding="utf-8")
    assert 'locator("#submit-btn")' not in healed
    assert '[data-testid="submit"]' in healed
    assert report.attempts[-1].repair_method == "ast"
    assert load_report(report.id).status == "healed"
