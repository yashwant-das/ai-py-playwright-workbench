"""
Shared types used across all schema modules.

This module provides the FailureType enum, the RunResult model, and the
Provenance and ModelExchange records consumed by the healing and generation reports.
"""

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


RunWarning = Literal[
    "page_context_unavailable",
    "ast_unavailable",
    "playwright_browsers_missing",
]


class Provenance(BaseModel):
    """Which model and prompt produced an answer, and what it cost."""

    provider: str = ""
    model: str = ""
    prompt_name: str = ""
    prompt_version: str = ""
    prompt_hash: str = ""
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)


class PromptSection(BaseModel):
    """One named block of context sent to the model."""

    name: str
    chars: int = Field(ge=0)
    original_chars: int | None = Field(
        default=None, ge=0, description="Set when the content was cut to fit."
    )

    @property
    def truncated(self) -> bool:
        """True when the section was cut to its limit."""
        return self.original_chars is not None


class ModelExchange(BaseModel):
    """What was sent to the model and what came back (the UI's Model I/O view)."""

    sections: list[PromptSection] = Field(default_factory=list)
    raw_response: str = ""
    valid: bool = False
    validation_error: str = ""
    provenance: Provenance = Field(default_factory=Provenance)
