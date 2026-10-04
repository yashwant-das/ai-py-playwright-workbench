"""The bundled samples the app offers on the Heal page."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Sample(BaseModel):
    """A bundled spec that shows one heal outcome against the sample site."""

    model_config = ConfigDict(frozen=True)

    name: str
    title: str
    description: str
    spec_file: str
    expected_status: Literal["healed", "app_defect_suspected"]
