"""The bundled samples the app offers on the Heal page."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Sample(BaseModel):
    """A bundled spec that shows one heal outcome against the sample site."""

    model_config = ConfigDict(frozen=True)

    name: str
    title: str
    description: str
    spec_file: str
    expected_status: Literal["healed", "app_defect_suspected"]


class Recording(BaseModel):
    """One recorded model answer that the Demo provider replays."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["heal", "generate"]
    sample: str
    match: str = Field(min_length=1)
    reply: str | dict[str, Any]
