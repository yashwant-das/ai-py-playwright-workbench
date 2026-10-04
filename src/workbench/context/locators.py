"""Locator candidates parsed from an aria snapshot.

Interactive elements in the snapshot (``- button "Submit" [ref=e3]``) become
``getByRole`` calls the model can use as stable, user-facing locators.
"""

import re

_INTERACTIVE_ROLES = frozenset(
    {
        "button",
        "checkbox",
        "combobox",
        "heading",
        "img",
        "link",
        "listbox",
        "menuitem",
        "radio",
        "searchbox",
        "slider",
        "spinbutton",
        "tab",
        "textbox",
    }
)
_LINE = re.compile(r'^\s*-\s+(?P<role>[a-z]+)\s+"(?P<name>(?:[^"\\]|\\.)*)"')


def extract_locator_candidates(snapshot: str | None, max_count: int = 20) -> list[str]:
    """Return unique ``getByRole(...)`` strings for named interactive elements."""
    candidates: list[str] = []
    for line in (snapshot or "").splitlines():
        match = _LINE.match(line)
        if not match or match["role"] not in _INTERACTIVE_ROLES:
            continue
        name = match["name"].replace('\\"', '"')
        if not name:
            continue
        escaped = name.replace("'", "\\'")
        candidate = f"getByRole('{match['role']}', {{ name: '{escaped}' }})"
        if candidate not in candidates:
            candidates.append(candidate)
        if len(candidates) >= max_count:
            break
    return candidates
