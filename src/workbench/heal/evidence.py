"""Evidence for a diagnosis, taken from the failing run itself.

When a test fails, Playwright writes ``error-context.md``: the error, the test
source and a snapshot of the page at the moment of failure. That snapshot is
the main evidence. Only when it is missing is the spec's first URL loaded in
a fresh browser, which shows the start page rather than the failing state.
"""

import logging
import re
from collections.abc import Callable
from pathlib import Path

from workbench.context import collect_context
from workbench.context.locators import extract_locator_candidates
from workbench.models.artifacts import ContextSnapshot
from workbench.models.heal import FailureEvidence
from workbench.models.shared import RunResult, RunWarning

logger = logging.getLogger(__name__)

Collect = Callable[[str], ContextSnapshot]

_GOTO = re.compile(r"page\.goto\(\s*['\"`](https?://[^\s'\"`]+)['\"`]")
_PAGE_SNAPSHOT = re.compile(
    r"^# Page snapshot\s*\n+```[a-z]*\n(?P<body>.*?)\n```", re.MULTILINE | re.DOTALL
)


def extract_url_from_code(code: str | None) -> str | None:
    """The first URL passed to ``page.goto()``, with or without options."""
    match = _GOTO.search(code or "")
    return match.group(1) if match else None


def parse_error_context(text: str) -> str | None:
    """The page snapshot from Playwright's ``error-context.md``, if present."""
    match = _PAGE_SNAPSHOT.search(text)
    return match["body"].strip() or None if match else None


def gather_evidence(
    code: str, result: RunResult, *, collect: Collect = collect_context
) -> tuple[FailureEvidence, list[RunWarning]]:
    """Build the evidence for one failed run, preferring the failure snapshot."""
    evidence = FailureEvidence(
        error_message=result.error_message,
        error_location=result.error_location,
        screenshot_path=result.screenshot_path,
    )
    if result.error_context_path:
        try:
            snapshot = parse_error_context(
                Path(result.error_context_path).read_text(encoding="utf-8")
            )
        except OSError as exc:
            logger.warning("Could not read %s: %s", result.error_context_path, exc)
            snapshot = None
        if snapshot:
            evidence.page_snapshot = snapshot
            evidence.locator_candidates = extract_locator_candidates(snapshot)
            evidence.source = "error_context"
            return evidence, []

    url = extract_url_from_code(code)
    if url:
        page = collect(url)
        if not page.is_empty:
            evidence.page_snapshot = page.aria_snapshot
            evidence.locator_candidates = list(page.locator_candidates)
            evidence.console_errors = list(page.console_errors)
            evidence.network_errors = list(page.network_errors)
            evidence.source = "page_load"
            return evidence, []
    return evidence, ["page_context_unavailable"]
