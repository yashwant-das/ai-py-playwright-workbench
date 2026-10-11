"""
Pydantic schemas for the test generation pipeline.

GenerationResult — validates raw LLM code output before writing to disk.
ContextSummary   — the page context a generation used, in counts the UI can show.
GenerateReport   — everything about one generate run.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .shared import ModelExchange, RunResult, RunWarning


class GenerationResult(BaseModel):
    """
    Validated result of a Playwright test generation call.

    The LLM may return the code in a markdown block, as raw text, or prefixed
    with explanatory prose. This model normalises the extracted code and
    validates it is non-empty before returning it to the caller.
    """

    code: str = Field(description="Generated TypeScript Playwright test code.")

    @field_validator("code")
    @classmethod
    def code_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Generated code is empty.")
        return stripped

    @property
    def has_playwright_import(self) -> bool:
        """True if the code imports from @playwright/test."""
        return "@playwright/test" in self.code

    @property
    def has_test_block(self) -> bool:
        """True if the code contains at least one test() or it() block."""
        return "test(" in self.code or "it(" in self.code

    @property
    def line_count(self) -> int:
        """Number of lines in the generated code."""
        return len(self.code.splitlines())


GenerateStatus = Literal["passed", "failed", "not_run", "cancelled", "error"]


class ContextSummary(BaseModel):
    """The page context a generation used, in counts the UI can show."""

    url: str
    snapshot_lines: int = Field(default=0, ge=0)
    locator_candidates: list[str] = Field(default_factory=list)
    console_errors: int = Field(default=0, ge=0)
    failed_requests: int = Field(default=0, ge=0)


class GenerateReport(BaseModel):
    """Everything about one generate run."""

    kind: Literal["generate"] = "generate"
    id: str
    url: str
    scenario: str
    status: GenerateStatus
    spec_name: str = ""
    code: str = ""
    context: ContextSummary | None = None
    exchange: ModelExchange | None = None
    run: RunResult | None = None
    warnings: list[RunWarning] = Field(default_factory=list)
    error_message: str = ""
    started_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    duration_ms: int = Field(default=0, ge=0)
