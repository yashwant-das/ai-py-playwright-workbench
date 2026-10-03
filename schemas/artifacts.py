"""
Pydantic schemas for context snapshots and artifact records.

ContextSnapshot — unified context collected from a browser session before generation or healing.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ContextSnapshot(BaseModel):
    """
    Unified context snapshot collected before generation or healing.

    Captures DOM HTML, accessibility tree, console errors, network failures,
    locator candidates, and an optional screenshot path — all collected in a
    single Playwright session via ``src.context.collect_context()``.
    """

    url: str
    html: str | None = None
    accessibility_tree: str | None = None
    console_errors: list[str] = Field(default_factory=list)
    network_errors: list[str] = Field(default_factory=list)
    locator_candidates: list[str] = Field(default_factory=list)
    screenshot_path: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    @property
    def has_html(self) -> bool:
        return bool(self.html)

    @property
    def has_a11y_tree(self) -> bool:
        return bool(self.accessibility_tree)

    @property
    def is_empty(self) -> bool:
        """True when neither HTML nor accessibility tree was collected."""
        return not self.html and not self.accessibility_tree
