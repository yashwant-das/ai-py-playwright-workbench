"""
Utility for loading LLM prompts from external markdown files.

Public API:
  load_prompt(agent_name)       — read a prompt file from prompts/
  get_prompt_version(agent_name) — read the version label from prompts/manifest.json
  get_prompt_hash(agent_name)    — compute SHA-256 fingerprint of the prompt content

The manifest stores human-set version labels; hashes are always computed fresh
from file content by get_prompt_hash().
"""

import hashlib
import json

from workbench.config import PROMPTS_DIR
from workbench.models.shared import PromptSection

_MANIFEST_PATH = PROMPTS_DIR / "manifest.json"
_manifest_cache: dict | None = None


def _load_manifest() -> dict:
    """Load (and cache) the prompts/manifest.json registry."""
    global _manifest_cache
    if _manifest_cache is None:
        if _MANIFEST_PATH.exists():
            _manifest_cache = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        else:
            _manifest_cache = {"prompts": {}}
    return _manifest_cache


def get_prompt_version(agent_name: str) -> str:
    """Return the human-set version string for a prompt from prompts/manifest.json.

    Falls back to ``"1"`` if the manifest does not exist or the agent is not
    listed.  Version strings are set manually when a prompt is intentionally
    changed; they are NOT computed from content (use :func:`get_prompt_hash`
    for content-based fingerprinting).

    Args:
        agent_name: Name of the agent (e.g., 'healer', 'generator').

    Returns:
        Version string (e.g. ``"1"``, ``"2"``).
    """
    manifest = _load_manifest()
    prompts = manifest.get("prompts", {})
    return str(prompts.get(agent_name, {}).get("version", "1"))


def load_prompt(agent_name: str) -> str:
    """Load a prompt from the prompts/ directory.

    Args:
        agent_name: Name of the agent (e.g., 'generator', 'healer')

    Returns:
        str: Content of the prompt file
    """
    prompt_path = PROMPTS_DIR / f"{agent_name}.md"

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with open(prompt_path, encoding="utf-8") as f:
        return f.read().strip()


def get_prompt_hash(agent_name: str) -> str:
    """Return the SHA-256 hex digest (first 16 chars) of a prompt file's content.

    Recorded in every model exchange so results can be reproduced or compared
    across prompt iterations.

    Args:
        agent_name: Name of the agent (e.g., 'generator', 'healer').

    Returns:
        16-character hex string derived from the prompt content.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    content = load_prompt(agent_name)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def render_prompt(
    sections: list[tuple[str, str]], limits: dict[str, int]
) -> tuple[str, list[PromptSection]]:
    """Join ``(name, content)`` pairs as ``## name`` blocks, each cut to its limit.

    Returns the prompt text and a record of every section's size, with the
    original size when it was cut.
    """
    parts: list[str] = []
    records: list[PromptSection] = []
    for name, content in sections:
        limit = limits[name]
        kept = content[:limit]
        records.append(
            PromptSection(
                name=name,
                chars=len(kept),
                original_chars=len(content) if len(content) > limit else None,
            )
        )
        parts.append(f"## {name}\n{kept}")
    return "\n\n".join(parts), records
