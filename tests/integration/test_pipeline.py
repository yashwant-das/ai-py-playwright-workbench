"""
End-to-end suite: generation and healing against a real browser.

Only the LLM is faked (see tests/integration/fake_llm.py); everything else is real —
context collection opens Chromium on a sample site in samples/site/, specs are
executed with ``npx playwright test``, and the heal loop applies its repair
through src/workbench/heal/ast_repair.js. Generated and healed specs, and the
reports, live in the workspace folder.

Run from the repo root:

    uv run python -m pytest tests/integration
"""

import os

import pytest

from tests.integration.conftest import SITE_URL
from tests.integration.fake_llm import FakeLLM
from workbench.config import specs_dir
from workbench.generate import GenerateRequest, generate
from workbench.heal import HealRequest, heal
from workbench.llm import _reset_default_router_for_testing, get_default_router
from workbench.llm.chat import RouterChatModel
from workbench.reports import load_report

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


def test_generated_spec_passes_in_a_real_browser(site, fake_llm):
    report = generate(
        GenerateRequest(url=site, scenario="A user can submit the contact form"),
        model=RouterChatModel(get_default_router()),
    )

    prompts = fake_llm.prompts_containing("## Target URL")
    assert prompts, "generator never called the LLM"
    assert "## Page snapshot" in prompts[-1]
    assert 'button "Submit"' in prompts[-1]
    assert report.status == "passed", report.model_dump_json(indent=2)
    assert site in report.code
    assert (
        report.exchange is not None
        and report.exchange.provenance.provider == "lm_studio"
    )


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
