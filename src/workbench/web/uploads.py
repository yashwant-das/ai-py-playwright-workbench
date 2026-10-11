"""Keeps a copy of an uploaded spec in the workspace; the original is never touched."""

from pathlib import Path

from workbench.config import specs_dir
from workbench.ids import slugify


def store_upload(filename: str, text: str) -> Path:
    """Write ``text`` to ``workspace/specs/uploads/<slug>.spec.ts`` and return the path."""
    stem = Path(filename).name.removesuffix(".spec.ts")
    target = specs_dir() / "uploads" / f"{slugify(stem)}.spec.ts"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target
