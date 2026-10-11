"""Identifiers and file-name slugs for runs, reports and specs."""

import re
from datetime import datetime

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_length: int = 40) -> str:
    """Return a lower-case kebab-case slug of ``text`` ("spec" if nothing is left)."""
    slug = _NON_ALNUM.sub("-", text.lower()).strip("-")
    slug = slug[:max_length].rstrip("-")
    return slug or "spec"


def new_run_id(kind: str, name: str, *, now: datetime | None = None) -> str:
    """Return ``YYYYMMDD-HHMMSS-<kind>-<slug>``; ids sort by start time."""
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{kind}-{slugify(name)}"
