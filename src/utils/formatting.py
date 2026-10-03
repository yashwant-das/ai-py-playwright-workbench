"""Text helpers shared by the data contracts."""

import re

_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def clean_ansi_codes(text: str) -> str:
    """Remove ANSI escape sequences from text.

    Args:
        text: Input string containing potential ANSI codes.

    Returns:
        The string without escape sequences ("" for empty input).
    """
    if not text:
        return ""
    return _ANSI_ESCAPE.sub("", text)
