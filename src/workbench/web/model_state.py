"""The model the app uses: the saved choice, otherwise a server found once at startup."""

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
    """Reads the saved choice each time; detects a server only once per app."""

    def __init__(self, services: Services) -> None:
        self._services = services
        self._detected: ModelSettings | None = None
        self._detection_done = False
        self._lock = threading.Lock()

    def choice(self) -> ModelSettings | None:
        saved = load_settings()
        if saved is not None:
            return saved
        with self._lock:
            if not self._detection_done:
                self._detected = self._services.detect()
                self._detection_done = True
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
