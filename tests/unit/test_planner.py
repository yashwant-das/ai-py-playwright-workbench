"""plan_fix() sends named, size-limited sections and records the exchange."""

import json
from typing import Any

import pytest

from workbench.heal.planner import LIMITS, plan_fix
from workbench.llm.chat import ChatReply
from workbench.models.heal import FailureEvidence, HealingAnalysis
from workbench.models.shared import FailureType

CODE = 'await page.locator("#submit-btn").click();\n'
HINT = (FailureType.TIMEOUT, 1.0, "Detected 'TimeoutError'")


def analysis(failure_type: str = "LOCATOR_DRIFT") -> str:
    return json.dumps(
        {
            "failure_type": failure_type,
            "failure_summary": "The selector drifted",
            "hypothesis": "Use the role-based locator",
            "confidence_score": 0.92,
            "confidence_rationale": "The snapshot shows the button",
            "reasoning_steps": ["#submit-btn is gone", "button 'Submit' exists"],
            "root_cause_evidence": ['button "Submit" [ref=e3]'],
            "action_taken": {
                "original_code": 'page.locator("#submit-btn")',
                "fixed_code": 'page.getByRole("button", { name: "Submit" })',
                "description": "Role-based locator",
                "repair_strategy": "selector_replace",
            },
        }
    )


class FakeModel:
    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, Any]] = []

    def chat(self, messages, *, json_schema=None, temperature=0.1) -> ChatReply:
        self.calls.append({"messages": messages, "json_schema": json_schema})
        return ChatReply(
            content=self.replies.pop(0),
            model="m-1",
            provider="fake",
            input_tokens=9,
            output_tokens=3,
            latency_ms=5,
        )


def _evidence(**changes: Any) -> FailureEvidence:
    base = FailureEvidence(
        error_message="TimeoutError: locator.click",
        error_location="/w/a.spec.ts:5:37",
        page_snapshot='- button "Submit" [ref=e3]',
        locator_candidates=["getByRole('button', { name: 'Submit' })"],
        source="error_context",
    )
    return base.model_copy(update=changes)


def test_sections_and_schema_are_sent() -> None:
    model = FakeModel(analysis())
    result, exchange = plan_fix(code=CODE, evidence=_evidence(), hint=HINT, model=model)

    assert result is not None and result.failure_type == FailureType.LOCATOR_DRIFT
    assert [s.name for s in exchange.sections] == [
        "Test file",
        "Error",
        "Page snapshot at failure",
        "Locator candidates",
    ]
    user = model.calls[0]["messages"][1]["content"]
    assert user.startswith("## Test file\n" + CODE)
    assert "## Error\nTimeoutError: locator.click\nat /w/a.spec.ts:5:37" in user
    assert model.calls[0]["json_schema"] == HealingAnalysis.model_json_schema()
    system = model.calls[0]["messages"][0]["content"]
    assert "TIMEOUT" in system and "1.00" in system


def test_exchange_records_provenance_and_validity() -> None:
    _, exchange = plan_fix(
        code=CODE, evidence=_evidence(), hint=HINT, model=FakeModel(analysis())
    )
    assert exchange.valid
    assert exchange.raw_response == analysis()
    p = exchange.provenance
    assert (p.provider, p.model, p.prompt_name, p.prompt_version) == (
        "fake",
        "m-1",
        "healer",
        "3",
    )
    assert (p.input_tokens, p.output_tokens, p.latency_ms) == (9, 3, 5)
    assert len(p.prompt_hash) == 16


def test_fresh_page_load_is_labelled_as_such() -> None:
    _, exchange = plan_fix(
        code=CODE,
        evidence=_evidence(source="page_load"),
        hint=HINT,
        model=FakeModel(analysis()),
    )
    assert "Page snapshot (fresh page load)" in [s.name for s in exchange.sections]


def test_long_snapshot_is_truncated_and_recorded() -> None:
    huge = "- text: " + "x" * 50_000
    model = FakeModel(analysis())
    _, exchange = plan_fix(
        code=CODE, evidence=_evidence(page_snapshot=huge), hint=HINT, model=model
    )
    section = next(s for s in exchange.sections if s.name == "Page snapshot at failure")
    assert section.chars == LIMITS["Page snapshot at failure"]
    assert section.original_chars == len(huge)
    assert len(model.calls[0]["messages"][1]["content"]) < 40_000


def test_invalid_reply_is_recorded_not_raised() -> None:
    result, exchange = plan_fix(
        code=CODE, evidence=_evidence(), hint=HINT, model=FakeModel("not json")
    )
    assert result is None
    assert not exchange.valid
    assert exchange.validation_error
    assert exchange.raw_response == "not json"


@pytest.mark.parametrize(
    ("hint_conf", "expected"), [(0.9, FailureType.TIMEOUT), (0.5, FailureType.UNKNOWN)]
)
def test_confident_heuristic_replaces_an_unknown_diagnosis(
    hint_conf: float, expected: FailureType
) -> None:
    hint = (FailureType.TIMEOUT, hint_conf, "reason")
    result, _ = plan_fix(
        code=CODE, evidence=_evidence(), hint=hint, model=FakeModel(analysis("UNKNOWN"))
    )
    assert result is not None and result.failure_type == expected
