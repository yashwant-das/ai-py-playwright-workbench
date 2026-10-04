"""Page context collected from one browser session."""

from datetime import datetime

from pydantic import BaseModel, Field


class ContextSnapshot(BaseModel):
    """What a page looked like when the workbench opened it."""

    url: str
    html: str | None = None
    aria_snapshot: str | None = None
    locator_candidates: list[str] = Field(default_factory=list)
    console_errors: list[str] = Field(default_factory=list)
    network_errors: list[str] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_empty(self) -> bool:
        """True when neither HTML nor an aria snapshot was collected."""
        return not self.html and not self.aria_snapshot
