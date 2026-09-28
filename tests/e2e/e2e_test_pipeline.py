"""
End-to-end suite: generation and healing against a real browser.

Only the LLM is faked (see tests/e2e/fake_llm.py); everything else is real —
context collection opens Chromium on a local fixture site, specs are written to
tests/generated/ and executed with ``npx playwright test``, and the heal loop
applies its repair through scripts/ast_repair.js.

Run from the repo root (validate_file_path resolves tests/generated from cwd):

    uv run python -m pytest tests/e2e/e2e_test_pipeline.py

The specs are left in tests/generated/ so ``npm run test:e2e:report`` can
re-run them for the HTML report, JUnit XML and traces.
"""

import json
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from src.agents.generator import generate_test_script
from src.healing import attempt_healing, run_test
from src.llm import _reset_default_router_for_testing
from src.observability import configure_tracer
from tests.e2e.fake_llm import FakeLLM

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SITE_DIR = Path(__file__).resolve().parent / "site"
GENERATED_DIR = PROJECT_ROOT / "tests" / "generated"
ARTIFACTS_DIR = PROJECT_ROOT / "tests" / "artifacts"

# Fixed so playwright.e2e.config.ts can serve the same URL the specs contain.
SITE_PORT = int(os.getenv("E2E_SITE_PORT", "4173"))
SITE_URL = f"http://127.0.0.1:{SITE_PORT}/"

GENERATED_SPEC = GENERATED_DIR / "e2e_generated_contact.spec.ts"
HEALED_SPEC = GENERATED_DIR / "e2e_healed_contact.spec.ts"

BROKEN_SPEC = f"""import {{ test, expect }} from "@playwright/test";

// The submit button used to be #submit-btn; the site now uses data-testid="submit".
test("Submit the contact form after a selector drift", async ({{ page }}) => {{
  await page.goto("{SITE_URL}");
  await page.getByLabel("Name").fill("Ada");
  await page.locator("#submit-btn").click({{ timeout: 3000 }});
  await expect(page.locator("#result")).toHaveText("Submitted");
}});
"""


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass


@pytest.fixture(scope="module")
def site():
    handler = partial(_QuietHandler, directory=str(SITE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", SITE_PORT), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield SITE_URL
    server.shutdown()
    server.server_close()


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
        configure_tracer(PROJECT_ROOT / "logs")
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
    for spec in (GENERATED_SPEC, HEALED_SPEC):
        spec.unlink(missing_ok=True)


def test_generated_spec_passes_in_a_real_browser(site, fake_llm):
    decision = generate_test_script(site, "A user can submit the contact form")

    # The generator collected live page context from Chromium and sent it on.
    prompts = fake_llm.prompts_containing("USER STORY:")
    assert prompts, "generator never called the LLM"
    assert "ACCESSIBILITY TREE" in prompts[-1]
    assert "Submit" in prompts[-1]

    assert site in decision.code
    assert decision.provider == "lm_studio"
    GENERATED_SPEC.write_text(decision.code, encoding="utf-8")

    result = run_test(GENERATED_SPEC.relative_to(PROJECT_ROOT))
    assert result.passed, result.output


def test_heal_loop_repairs_a_drifted_selector(site, fake_llm):
    HEALED_SPEC.write_text(BROKEN_SPEC, encoding="utf-8")
    spec_path = str(HEALED_SPEC.relative_to(PROJECT_ROOT))
    started = {p.name for p in ARTIFACTS_DIR.glob("healing_decision_*.json")}

    assert not run_test(spec_path).passed, "broken spec should fail before healing"

    outcome = attempt_healing(spec_path, max_retries=2)
    assert "SUCCESS" in outcome, outcome

    # The healer saw live DOM evidence, and the repair landed in the file.
    prompts = fake_llm.prompts_containing("BROKEN CODE:")
    assert prompts, "healer never called the LLM"
    assert "PAGE DOM CONTEXT" in prompts[-1]
    healed = HEALED_SPEC.read_text(encoding="utf-8")
    assert 'locator("#submit-btn")' not in healed
    assert '[data-testid="submit"]' in healed

    new_artifacts = [
        p
        for p in ARTIFACTS_DIR.glob("healing_decision_*.json")
        if p.name not in started
    ]
    assert new_artifacts, "no healing decision artifact was written"
    decision = json.loads(
        max(new_artifacts, key=lambda p: p.stat().st_mtime).read_text()
    )
    assert decision["verification_passed"] is True
    assert decision["action_taken"]["repair_strategy"] == "selector_replace"
