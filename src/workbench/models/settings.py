"""Which model the workbench talks to, and how to reach it."""

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ProviderName = Literal["lm_studio", "ollama", "demo"]

PROVIDER_LABELS: dict[ProviderName, str] = {
    "lm_studio": "LM Studio",
    "ollama": "Ollama",
    "demo": "Demo",
}
DEFAULT_URLS: dict[ProviderName, str] = {
    "lm_studio": "http://localhost:1234/v1",
    "ollama": "http://localhost:11434/v1",
}
DEMO_MODEL = "recorded-answers"


def normalise_base_url(url: str) -> str:
    """Clean a typed server URL: no trailing slash, and ``/v1`` when no path is given.

    Raises ``ValueError`` unless the URL is http(s), names a host and, when it
    has a port, the port is a number up to 65535.
    """
    cleaned = url.strip().rstrip("/")
    parsed = urlparse(cleaned)
    try:
        parsed.port  # noqa: B018 - urlparse checks the port only when it is read
    except ValueError as exc:
        raise ValueError(
            f"Server URL has an invalid port: {url!r}. Use http:// or https://, "
            "a host and a port number up to 65535."
        ) from exc
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(
            f"Server URL must start with http:// or https:// and name a host: {url!r}"
        )
    return cleaned if parsed.path else f"{cleaned}/v1"


class ModelSettings(BaseModel):
    """The model choice saved in ``workspace/settings.json``."""

    model_config = ConfigDict(frozen=True)

    provider: ProviderName
    base_url: str = ""
    model: str = Field(min_length=1)

    @field_validator("base_url")
    @classmethod
    def _normalise(cls, value: str) -> str:
        return normalise_base_url(value) if value.strip() else ""

    @model_validator(mode="after")
    def _servers_need_a_url(self) -> "ModelSettings":
        if self.provider != "demo" and not self.base_url:
            raise ValueError(f"{PROVIDER_LABELS[self.provider]} needs a server URL.")
        return self

    @property
    def label(self) -> str:
        return PROVIDER_LABELS[self.provider]


class ConnectionStatus(BaseModel):
    """What the model menu shows about the chosen server."""

    provider: ProviderName
    base_url: str = ""
    reachable: bool
    models: list[str] = Field(default_factory=list)
    error: str = ""
