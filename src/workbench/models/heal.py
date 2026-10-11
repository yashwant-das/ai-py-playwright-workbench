"""
Pydantic schemas for the healing pipeline.

  HealingAnalysis  - what the LLM must return (the structured output contract).
  HealReport       - everything about one heal run, saved as a JSON report.

Keeping them separate lets the LLM schema stay minimal while the report
carries the evidence, model exchanges and verification results.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .shared import (
    FailureType,
    ModelExchange,
    RunResult,
    RunWarning,
)


class RepairStrategy(str, Enum):
    """Repair strategy selected by the LLM for each HealingAction.

    The planner chooses the strategy most appropriate for the failure type.
    ``string_replace`` is the legacy fallback; all other values trigger the
    ts-morph AST repair path in ``src/workbench/heal/repair.py``.

    | Value              | What the AST script does |
    |--------------------|--------------------------|
    | string_replace     | Existing sliding-window string replacement (fallback) |
    | selector_replace   | Find all matching locator/getByX calls and replace the selector argument |
    | import_add         | Insert a missing import declaration (skips if already present) |
    | timeout_adjust     | Find ``{ timeout: N }`` properties and update the value |
    | role_argument      | Update the ``name`` option in a ``getByRole()`` call |
    | assertion_swap     | Rename an assertion method in an ``expect()`` chain |
    """

    STRING_REPLACE = "string_replace"
    SELECTOR_REPLACE = "selector_replace"
    IMPORT_ADD = "import_add"
    TIMEOUT_ADJUST = "timeout_adjust"
    ROLE_ARGUMENT = "role_argument"
    ASSERTION_SWAP = "assertion_swap"


# Single source of truth for strategy → human-readable label.
# Used by the UI timeline and by artifact reports so both surfaces agree.
REPAIR_STRATEGY_LABELS: dict[RepairStrategy, str] = {
    RepairStrategy.STRING_REPLACE: "String replaced",
    RepairStrategy.SELECTOR_REPLACE: "Selector replaced",
    RepairStrategy.IMPORT_ADD: "Import added",
    RepairStrategy.TIMEOUT_ADJUST: "Timeout adjusted",
    RepairStrategy.ROLE_ARGUMENT: "Role argument updated",
    RepairStrategy.ASSERTION_SWAP: "Assertion swapped",
}


class HealingAction(BaseModel):
    """The specific code change proposed or applied during healing."""

    original_code: str
    fixed_code: str
    description: str
    repair_strategy: RepairStrategy = Field(default=RepairStrategy.STRING_REPLACE)

    @field_validator("original_code", "fixed_code", mode="before")
    @classmethod
    def coerce_list_to_str(cls, v: object) -> str:
        """Accept list-of-lines from LLM (common failure mode) and join them."""
        if isinstance(v, list):
            return "\n".join(str(line) for line in v)
        return str(v) if v is not None else ""

    @field_validator("repair_strategy", mode="before")
    @classmethod
    def coerce_repair_strategy(cls, v: object) -> RepairStrategy:
        """Accept None or missing field from older LLM responses."""
        if v is None:
            return RepairStrategy.STRING_REPLACE
        return RepairStrategy(v)


class HealingAnalysis(BaseModel):
    """
    LLM response schema for healer analysis.

    This is the structured output contract: every field the LLM must produce.
    Pydantic validates the response before any field is accessed. If validation
    fails, the caller retries or falls back — no silent data corruption.

    JSON schema for the healer prompt:
    {
        "failure_type": "LOCATOR_DRIFT | TIMEOUT | ASSERTION_FAILED | ...",
        "failure_summary": "Short description of failure",
        "hypothesis": "Why the fix will work",
        "confidence_score": 0.95,
        "confidence_rationale": "Why this confidence level was chosen",
        "reasoning_steps": ["step 1", "step 2"],
        "root_cause_evidence": ["evidence item 1", "evidence item 2"],
        "action_taken": {
            "original_code": "exact contiguous block to replace",
            "fixed_code": "replacement block",
            "description": "what changed",
            "repair_strategy": "string_replace | selector_replace | import_add | timeout_adjust | role_argument | assertion_swap"
        }
    }
    """

    failure_type: FailureType
    failure_summary: str
    hypothesis: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_rationale: str = Field(
        default="",
        description="The LLM's explanation of why this confidence level was assigned.",
    )
    reasoning_steps: list[str]
    root_cause_evidence: list[str] = Field(
        default_factory=list,
        description="Specific evidence items from logs / DOM that support the diagnosis.",
    )
    action_taken: HealingAction

    model_config = ConfigDict(use_enum_values=False)

    @field_validator("confidence_score", mode="before")
    @classmethod
    def clamp_confidence(cls, v: object) -> float:
        """Clamp to [0, 1] — LLMs occasionally return 1.05 etc.

        A null or non-numeric value raises ValueError, which Pydantic reports as
        a validation error; a TypeError would escape validation and crash heal().
        """
        try:
            score = float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ValueError(f"confidence_score must be a number, got {v!r}") from exc
        return max(0.0, min(1.0, score))

    @field_validator("reasoning_steps", mode="before")
    @classmethod
    def coerce_single_step(cls, v: object) -> list[str]:
        """Accept a bare string when LLM returns one step instead of a list."""
        if isinstance(v, str):
            return [v]
        return list(v) if isinstance(v, (list, tuple)) else []


RepairMethod = Literal["ast", "text"]


class RepairResult(BaseModel):
    """The code after a repair attempt, and how the change was made."""

    code: str
    method: RepairMethod | None = Field(
        default=None, description="None when nothing in the code changed."
    )
    ast_unavailable: bool = Field(
        default=False,
        description="An AST strategy was requested but Node.js was not found.",
    )


EvidenceSource = Literal["error_context", "page_load", "none"]
AttemptOutcome = Literal[
    "healed", "rerun_failed", "not_applied", "invalid_reply", "app_defect", "cancelled"
]
HealStatus = Literal[
    "healed",
    "not_healed",
    "app_defect_suspected",
    "nothing_to_heal",
    "cancelled",
    "error",
]


class FailureEvidence(BaseModel):
    """What the model is shown about a failure."""

    error_message: str = ""
    error_location: str = ""
    page_snapshot: str | None = None
    screenshot_path: str | None = None
    console_errors: list[str] = Field(default_factory=list)
    network_errors: list[str] = Field(default_factory=list)
    locator_candidates: list[str] = Field(default_factory=list)
    source: EvidenceSource = "none"


class Attempt(BaseModel):
    """One diagnose → repair → verify cycle."""

    number: int = Field(ge=1)
    outcome: AttemptOutcome
    evidence: FailureEvidence | None = None
    analysis: HealingAnalysis | None = None
    exchange: ModelExchange | None = None
    repair_method: RepairMethod | None = None
    rerun: RunResult | None = None
    duration_ms: int = Field(default=0, ge=0)


class HealReport(BaseModel):
    """Everything about one heal run; the UI and downloads read this."""

    kind: Literal["heal"] = "heal"
    id: str
    spec_name: str
    status: HealStatus
    max_attempts: int = Field(default=3, ge=1, le=5)
    attempts: list[Attempt] = Field(default_factory=list)
    initial_run: RunResult | None = None
    original_code: str = ""
    final_code: str = ""
    diff: str = ""
    classifier_hint: str = ""
    warnings: list[RunWarning] = Field(default_factory=list)
    error_message: str = ""
    started_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    duration_ms: int = Field(default=0, ge=0)
