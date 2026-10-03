"""
Shared types used across all schema modules.

This module provides the FailureType enum, RunResult model, and
ProvenanceRecord base model consumed by healing, generation, and evaluation schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class FailureType(str, Enum):
    """Classification of Playwright test failure types."""

    LOCATOR_NOT_FOUND = "LOCATOR_NOT_FOUND"
    LOCATOR_DRIFT = "LOCATOR_DRIFT"
    TIMEOUT = "TIMEOUT"
    ASSERTION_FAILED = "ASSERTION_FAILED"
    ENVIRONMENT_ISSUE = "ENVIRONMENT_ISSUE"
    POTENTIAL_APP_DEFECT = "POTENTIAL_APP_DEFECT"
    JAVASCRIPT_ERROR = "JAVASCRIPT_ERROR"
    UNKNOWN = "UNKNOWN"


RunStatus = Literal["passed", "failed", "timed_out", "cancelled", "error"]


class RunResult(BaseModel):
    """Outcome of one ``npx playwright test`` run, read from its JSON report."""

    status: RunStatus
    duration_ms: int = Field(default=0, ge=0)
    error_message: str = ""
    error_location: str = ""
    screenshot_path: str | None = None
    error_context_path: str | None = None
    video_path: str | None = None
    stdout: str = ""
    stderr: str = ""

    @property
    def passed(self) -> bool:
        """True if the test passed."""
        return self.status == "passed"

    @property
    def output(self) -> str:
        """Error message and process output, for logs and the failure classifier."""
        parts = (self.error_message, self.stdout, self.stderr)
        return "\n".join(part for part in parts if part)

    @property
    def returncode(self) -> int:
        """Exit-code view for the 1.0 heal loop; removed with it in Task 7."""
        return 0 if self.passed else 1


class LLMConfig(BaseModel):
    """Configuration for a single LLM provider connection.

    Defined here (rather than in src/llm/) to avoid circular imports.
    """

    provider: str  # "lm_studio" | "ollama" | "openai"
    base_url: str | None = None
    api_key: str | None = None
    model: str
    vision_model: str | None = None
    temperature: float = 0.1
    seed: int | None = None


class ProvenanceRecord(BaseModel):
    """Common provenance fields shared by all pipeline decision artifacts.

    Every decision — healing, generation, vision — embeds these fields so the
    Artifact Inspector can display uniform provenance across all pipeline types
    and each artifact can deep-link to its trace span.
    """

    model_used: str = Field(
        default="",
        description="Model identifier that produced this decision (e.g. 'qwen3-30b').",
    )
    provider: str = Field(
        default="",
        description="LLM provider name (e.g. 'lm_studio', 'ollama').",
    )
    prompt_version: str = Field(
        default="",
        description="Human-set version label from prompts/manifest.json.",
    )
    prompt_hash: str = Field(
        default="",
        description="SHA-256 hex prefix of the prompt content at run time.",
    )
    input_tokens: int = Field(default=0, ge=0, description="Prompt token count.")
    output_tokens: int = Field(default=0, ge=0, description="Completion token count.")
    latency_ms: int = Field(
        default=0, ge=0, description="Wall-clock LLM call latency in milliseconds."
    )
    retry_count: int = Field(
        default=0, ge=0, description="Retry attempts before success."
    )
    trace_id: str = Field(
        default="",
        description="Tracer session ID — links this artifact to logs/traces.jsonl.",
    )
    context_snapshot_id: str = Field(
        default="",
        description="Short hash identifying the context snapshot for this decision.",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO-8601 timestamp of when the decision was produced.",
    )
