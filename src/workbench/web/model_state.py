"""The model the app uses: the saved choice, otherwise a server detected on demand."""

import threading

from workbench.models.settings import (
    ConnectionStatus,
    ModelSettings,
    ModelView,
    ProviderName,
)
from workbench.settings import load_settings
from workbench.web.services import Services


class ModelState:
    """Reads the saved choice each time; keeps a detected server, and looks again while none is found."""

    def __init__(self, services: Services) -> None:
        self._services = services
        self._detected: ModelSettings | None = None
        self._lock = threading.Lock()

    def choice(self) -> ModelSettings | None:
        saved = load_settings()
        if saved is not None:
            return saved
        with self._lock:
            if self._detected is None:
                self._detected = self._services.detect()
            return self._detected

    def view(self) -> ModelView:
        choice = self.choice()
        if choice is None:
            return ModelView()
        return ModelView(
            choice=choice, connection=self.probe(choice.provider, choice.base_url)
        )

    def probe(self, provider: ProviderName, base_url: str) -> ConnectionStatus:
        return self._services.check_connection(provider, base_url)
