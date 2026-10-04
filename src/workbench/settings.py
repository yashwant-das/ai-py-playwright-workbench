"""The model choice saved in ``workspace/settings.json``.

The app has no ``.env``: the user picks a provider and model in the UI and
the choice is saved here. Until something is saved, the app detects a local
server on every start.
"""

import logging
import os
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from workbench.config import workspace_dir
from workbench.llm.providers import detect_provider
from workbench.models.settings import ModelSettings

logger = logging.getLogger(__name__)

SETTINGS_FILE = "settings.json"


def settings_path() -> Path:
    return workspace_dir() / SETTINGS_FILE


def load_settings() -> ModelSettings | None:
    """The saved choice, or None when nothing usable is saved.

    A missing, unreadable or invalid file counts as no choice, so a bad hand
    edit never stops the app from starting.
    """
    path = settings_path()
    try:
        return ModelSettings.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError, ValidationError) as exc:
        logger.warning("Ignoring %s: %s", path, exc)
        return None


def save_settings(settings: ModelSettings) -> Path:
    """Write the choice atomically, so a crash never leaves half a file."""
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
    os.replace(temporary, path)
    return path


def resolve_settings(
    *, detect: Callable[[], ModelSettings | None] = detect_provider
) -> ModelSettings | None:
    """The saved choice; otherwise the first local server that answers.

    A detected server is used but not saved. A saved server that is down is
    still returned: the UI shows it as not connected instead of switching.
    """
    return load_settings() or detect()
