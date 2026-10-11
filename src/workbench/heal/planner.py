"""Asks the model for a diagnosis and a fix, and records the exchange."""

import logging

from workbench.llm.chat import ChatModel
from workbench.llm.parsing import parse_llm_response
from workbench.llm.prompts import (
    get_prompt_hash,
    get_prompt_version,
    load_prompt,
    render_prompt,
)
from workbench.models.heal import FailureEvidence, HealingAnalysis
from workbench.models.shared import FailureType, ModelExchange, Provenance

logger = logging.getLogger(__name__)

Hint = tuple[FailureType, float, str]

LIMITS = {
    "Test file": 12_000,
    "Error": 2_000,
    "Page snapshot at failure": 12_000,
    "Page snapshot (fresh page load)": 12_000,
    "Locator candidates": 2_000,
    "Console errors": 2_000,
    "Failed requests": 2_000,
}
# A heuristic this sure replaces an UNKNOWN diagnosis from the model.
HEURISTIC_OVERRIDE = 0.8


def build_sections(code: str, evidence: FailureEvidence) -> list[tuple[str, str]]:
    """Named context blocks in prompt order; empty ones are left out."""
    error = evidence.error_message
    if evidence.error_location:
        error += f"\nat {evidence.error_location}"
    snapshot_name = (
        "Page snapshot at failure"
        if evidence.source == "error_context"
        else "Page snapshot (fresh page load)"
    )
    sections = [
        ("Test file", code),
        ("Error", error),
        (snapshot_name, evidence.page_snapshot or ""),
        (
            "Locator candidates",
            "\n".join(f"- {c}" for c in evidence.locator_candidates),
        ),
        ("Console errors", "\n".join(evidence.console_errors)),
        ("Failed requests", "\n".join(evidence.network_errors)),
    ]
    return [(name, content) for name, content in sections if content.strip()]


def plan_fix(
    *, code: str, evidence: FailureEvidence, hint: Hint, model: ChatModel
) -> tuple[HealingAnalysis | None, ModelExchange]:
    """Return the model's validated analysis (None if invalid) and the exchange.

    Raises ``ModelError`` when the model cannot be reached.
    """
    hint_type, hint_confidence, hint_reason = hint
    system = load_prompt("healer").format(
        failure_type=hint_type.value,
        confidence=f"{hint_confidence:.2f}",
        reason=hint_reason,
    )
    user, sections = render_prompt(build_sections(code, evidence), LIMITS)
    reply = model.chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        json_schema=HealingAnalysis.model_json_schema(),
        temperature=0.1,
    )
    exchange = ModelExchange(
        sections=sections,
        raw_response=reply.content,
        provenance=Provenance(
            provider=reply.provider,
            model=reply.model,
            prompt_name="healer",
            prompt_version=get_prompt_version("healer"),
            prompt_hash=get_prompt_hash("healer"),
            input_tokens=reply.input_tokens,
            output_tokens=reply.output_tokens,
            latency_ms=reply.latency_ms,
        ),
    )
    try:
        analysis = parse_llm_response(reply.content, HealingAnalysis)
    except ValueError as exc:
        logger.warning("Healer reply did not match the schema: %s", exc)
        exchange.validation_error = str(exc)[:500]
        return None, exchange
    if (
        analysis.failure_type == FailureType.UNKNOWN
        and hint_confidence > HEURISTIC_OVERRIDE
    ):
        analysis = analysis.model_copy(update={"failure_type": hint_type})
    exchange.valid = True
    return analysis, exchange
