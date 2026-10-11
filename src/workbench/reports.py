"""Saves and loads the one JSON report each heal or generate run produces."""

import os
import re
from pathlib import Path
from typing import Annotated

from pydantic import Field, TypeAdapter

from workbench.config import reports_dir
from workbench.models.generate import GenerateReport
from workbench.models.heal import HealReport

Report = HealReport | GenerateReport
_ADAPTER: TypeAdapter[Report] = TypeAdapter(
    Annotated[Report, Field(discriminator="kind")]
)
_REPORT_ID = re.compile(r"\d{8}-\d{6}-(heal|generate)-[a-z0-9-]+")


def inside(folder: Path, name: str) -> Path:
    """``folder/name``; refuses a name that would lead out of ``folder``."""
    base = os.path.normpath(folder)
    path = os.path.normpath(os.path.join(base, name))
    if not path.startswith(base + os.sep):
        raise ValueError(f"{name!r} is outside {folder}")
    return Path(path)


def report_path(report_id: str) -> Path:
    """Path of a report; rejects anything that is not a generated id."""
    if not _REPORT_ID.fullmatch(report_id):
        raise ValueError(f"Not a report id: {report_id!r}")
    # The id pattern already keeps the path in the folder; the second check
    # does not depend on that pattern staying strict.
    return inside(reports_dir(), f"{report_id}.json")


def save_report(report: Report) -> Path:
    """Write ``report`` to the workspace and return its path."""
    path = report_path(report.id)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_report(report_id: str) -> Report:
    """Read a saved report; raises ``FileNotFoundError`` if it does not exist."""
    return _ADAPTER.validate_json(report_path(report_id).read_text(encoding="utf-8"))


def list_report_ids(limit: int = 20) -> list[str]:
    """Report ids, newest first (ids start with their timestamp)."""
    ids = [p.stem for p in reports_dir().glob("*.json") if _REPORT_ID.fullmatch(p.stem)]
    return sorted(ids, reverse=True)[:limit]
