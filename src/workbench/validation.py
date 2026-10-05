"""
Input validation utilities for the QA Agent.
"""

import re
from pathlib import Path
from urllib.parse import urlparse


class ValidationError(Exception):
    """Custom exception for validation errors."""


def validate_url(url: str) -> bool:
    """Validate that a URL is properly formatted and uses http/https.

    Args:
        url: The URL string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    try:
        result = urlparse(url.strip())
        return all(
            [
                result.scheme in ["http", "https"],
                result.netloc,
                len(url) <= 2048,  # Reasonable URL length limit
            ]
        )
    except Exception:
        return False


def validate_and_sanitize_url(url: str) -> str:
    """Validate and sanitize a URL.

    Args:
        url: The URL string to validate and sanitize

    Returns:
        str: Sanitized URL string

    Raises:
        ValidationError: If URL is invalid
    """
    if not url:
        raise ValidationError("URL cannot be empty")

    url = url.strip()

    if not validate_url(url):
        raise ValidationError(f"Invalid URL format: {url}. Must be http:// or https://")

    return url


def validate_description(description: str, max_length: int = 500) -> str:
    """Validate and sanitize a test description/scenario.

    Args:
        description: The description string to validate
        max_length: Maximum allowed length (default: 500)

    Returns:
        str: Sanitized description string

    Raises:
        ValidationError: If description is invalid
    """
    if not description:
        raise ValidationError("Description cannot be empty")

    if not isinstance(description, str):
        raise ValidationError("Description must be a string")

    description = description.strip()

    if len(description) > max_length:
        raise ValidationError(f"Description too long (max {max_length} characters)")

    # Check for potentially dangerous patterns
    dangerous_patterns = [
        r"[<>]",  # HTML tags
        r"\.\./",  # Path traversal attempts
        r"[;&|$]",  # Command injection attempts (backtick removed for technical descriptions)
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, description):
            raise ValidationError(
                f"Description contains invalid characters: {description[:50]}..."
            )

    return description


MAX_SPEC_BYTES = 200 * 1024


def validate_spec_upload(filename: str, data: bytes) -> str:
    """The text of an uploaded spec; raises ValidationError saying what is wrong."""
    name = Path(filename or "").name or "The file"
    if not name.endswith(".spec.ts"):
        raise ValidationError(
            f"{name} isn't a test file. Only .spec.ts files are supported."
        )
    if len(data) > MAX_SPEC_BYTES:
        raise ValidationError(f"{name} is larger than 200 KB.")
    if not data.strip():
        raise ValidationError(f"{name} is empty.")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError(f"{name} isn't UTF-8 text.") from None
