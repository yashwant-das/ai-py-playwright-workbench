"""The Demo provider replays recorded answers for the bundled samples only."""

from pathlib import Path

import pytest

from workbench import config
from workbench.environment import node_available
from workbench.heal import HealRequest, heal
from workbench.heal.repair import apply_fix
from workbench.llm.chat import ModelError
from workbench.llm.demo import DemoModel, load_recordings, prompt_sections
from workbench.llm.parsing import extract_code_block, parse_llm_response
from workbench.llm.prompts import render_prompt
from workbench.models.artifacts import ContextSnapshot
from workbench.models.heal import HealingAnalysis
from workbench.models.settings import DEMO_MODEL
from workbench.models.shared import FailureType, RunResult
from workbench.samples import GENERATE_SCENARIO, SAMPLES

LIMITS = {
    "Test file": 20_000,
    "Error": 4_000,
    "Target URL": 500,
    "Scenario": 1_000,
    "Page snapshot": 12_000,
}


def _messages(user: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": user},
    ]


def _heal_prompt(test_file: str) -> str:
    return render_prompt([("Test file", test_file), ("Error", "TimeoutError")], LIMITS)[
        0
    ]


def _generate_prompt(url: str, scenario: str) -> str:
    sections = [
        ("Target URL", url),
        ("Scenario", scenario),
        ("Page snapshot", "- button"),
    ]
    return render_prompt(sections, LIMITS)[0]


def _sample_spec(name: str) -> str:
    return (config.SAMPLE_SPECS_DIR / SAMPLES[name].spec_file).read_text(
        encoding="utf-8"
    )


def test_prompt_sections_round_trip() -> None:
    prompt, _ = render_prompt([("A", "one\ntwo"), ("B", "three")], {"A": 100, "B": 100})
    assert prompt_sections(prompt) == {"A": "one\ntwo", "B": "three"}


def test_drift_sample_gets_a_fix_that_matches_its_source() -> None:
    spec = _sample_spec("selector-drift")
    reply = DemoModel().chat(_messages(_heal_prompt(spec)))
    analysis = parse_llm_response(reply.content, HealingAnalysis)
    assert analysis.failure_type == FailureType.LOCATOR_DRIFT
    assert analysis.action_taken.original_code in spec
    assert (reply.provider, reply.model) == ("demo", DEMO_MODEL)


@pytest.mark.skipif(not node_available(), reason="Node.js is needed for the AST repair")
def test_drift_fix_is_a_real_selector_edit_of_the_sample_spec() -> None:
    spec = _sample_spec("selector-drift")
    reply = DemoModel().chat(_messages(_heal_prompt(spec)))
    analysis = parse_llm_response(reply.content, HealingAnalysis)

    result = apply_fix(spec, analysis.action_taken)

    assert result.method == "ast"
    assert "page.locator('[data-testid=\"submit\"]')" in result.code
    assert "#submit-btn" not in result.code


def test_app_bug_sample_gets_a_confident_app_defect_diagnosis() -> None:
    reply = DemoModel().chat(_messages(_heal_prompt(_sample_spec("app-bug"))))
    analysis = parse_llm_response(reply.content, HealingAnalysis)
    assert analysis.failure_type == FailureType.POTENTIAL_APP_DEFECT
    assert analysis.confidence_score >= 0.7


def test_sample_scenario_is_generated_for_the_given_url() -> None:
    prompt = _generate_prompt(
        "http://127.0.0.1:4173/", "  a user can SEND the contact form "
    )
    code = extract_code_block(DemoModel().chat(_messages(prompt)).content)
    assert "page.goto('http://127.0.0.1:4173/')" in code
    assert "{{URL}}" not in code


def test_unknown_spec_is_not_covered() -> None:
    with pytest.raises(ModelError, match="Demo only covers the bundled samples"):
        DemoModel().chat(_messages(_heal_prompt("test('mine', async () => {});")))


@pytest.mark.parametrize(
    "spec",
    [
        "test('Checkout places an order twice', async () => {});",
        "// Contact form sends a message\ntest('mine', async () => {});",
    ],
)
def test_a_spec_that_only_resembles_a_sample_is_not_covered(spec: str) -> None:
    with pytest.raises(ModelError, match="Demo only covers the bundled samples"):
        DemoModel().chat(_messages(_heal_prompt(spec)))


def test_unknown_scenario_is_not_covered() -> None:
    with pytest.raises(ModelError, match="Demo only covers the bundled samples"):
        DemoModel().chat(_messages(_generate_prompt("http://x.test/", "Buy a hat")))


def test_unrecognised_prompt_is_not_covered() -> None:
    with pytest.raises(ModelError, match="Demo only covers the bundled samples"):
        DemoModel().chat(_messages("hello"))


def test_every_sample_has_a_heal_recording() -> None:
    assert {r.sample for r in load_recordings() if r.kind == "heal"} == set(SAMPLES)


def test_the_generate_recording_is_the_sample_scenario() -> None:
    assert [r.match for r in load_recordings() if r.kind == "generate"] == [
        GENERATE_SCENARIO
    ]


def test_heal_with_demo_on_an_unknown_spec_is_a_clear_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(config.WORKSPACE_ENV, str(tmp_path / "ws"))
    code = (
        "import { test } from '@playwright/test';\n"
        "test('mine', async ({ page }) => {\n"
        "  await page.goto('http://example.test/');\n"
        "});\n"
    )
    spec = tmp_path / "mine.spec.ts"
    spec.write_text(code, encoding="utf-8")

    report = heal(
        HealRequest(spec_path=spec, max_attempts=1),
        model=DemoModel(),
        run=lambda *_, **__: RunResult(status="failed", error_message="Error: boom"),
        collect=lambda url: ContextSnapshot(url=url),
        browsers_ready=lambda: True,
    )

    assert report.status == "error"
    assert "Demo only covers the bundled samples" in report.error_message
    assert spec.read_text(encoding="utf-8") == code
