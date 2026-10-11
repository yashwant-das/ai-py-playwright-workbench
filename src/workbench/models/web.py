"""What the web templates show, derived from reports and events."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from workbench.models.events import StepName

BadgeVariant = Literal["pass", "fail", "run", "warn", "neutral"]


class Badge(BaseModel):
    """A status pill: its colour variant and its text."""

    model_config = ConfigDict(frozen=True)

    variant: BadgeVariant
    label: str


class OutcomeBadge(Badge):
    """An attempt's pill plus the title its card shows."""

    title: str


class StepInfo(BaseModel):
    """A pipeline step as the progress list names it."""

    model_config = ConfigDict(frozen=True)

    name: StepName
    title: str
    description: str


class DiffRow(BaseModel):
    """One line of a two-column diff, already highlighted."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["same", "add", "del"]
    old_no: int | None
    new_no: int | None
    html: str


class StepbarItem(BaseModel):
    """One step in a finished run's summary bar."""

    model_config = ConfigDict(frozen=True)

    title: str
    state: Literal["done", "failed", "skipped"]
    time: str = ""
