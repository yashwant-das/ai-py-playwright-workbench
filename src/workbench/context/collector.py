"""Page context from one Chromium session, using Playwright's own collections.

The aria snapshot uses ``mode="ai"``, the format Playwright itself writes into
``error-context.md``, so generation and healing show the model one format.
"""

import logging

from playwright.sync_api import Page, sync_playwright

from workbench.context.dom import collect_dom
from workbench.context.locators import extract_locator_candidates
from workbench.models.artifacts import ContextSnapshot

logger = logging.getLogger(__name__)

_CONSOLE_TYPES = frozenset({"error", "warning"})


def collect_context(
    url: str,
    *,
    capture_html: bool = True,
    max_html_chars: int = 30_000,
    max_snapshot_chars: int = 12_000,
    max_locator_candidates: int = 20,
    wait_ms: int = 1_000,
) -> ContextSnapshot:
    """Open ``url`` and collect what the model needs; never raises.

    On any navigation or browser failure, returns a snapshot with only the
    URL set (``is_empty`` is then True).
    """
    snapshot = ContextSnapshot(url=url)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(viewport={"width": 1280, "height": 720})
                try:
                    page.goto(url, timeout=30_000, wait_until="domcontentloaded")
                except Exception as exc:
                    logger.warning("Navigation failed for %s: %s", url, exc)
                    return snapshot
                if wait_ms > 0:
                    page.wait_for_timeout(wait_ms)
                if capture_html:
                    snapshot.html = collect_dom(page, max_chars=max_html_chars) or None
                aria = page.aria_snapshot(mode="ai")
                snapshot.aria_snapshot = aria[:max_snapshot_chars] or None
                snapshot.locator_candidates = extract_locator_candidates(
                    aria, max_count=max_locator_candidates
                )
                snapshot.console_errors = console_errors(page)
                snapshot.network_errors = network_errors(page)
            finally:
                browser.close()
    except Exception as exc:
        logger.warning("Context collection failed for %s: %s", url, exc)
    return snapshot


def console_errors(page: Page) -> list[str]:
    """Console errors and warnings, then uncaught page errors."""
    lines = [
        f"[{message.type.upper()}] {message.text}"
        for message in page.console_messages()
        if message.type in _CONSOLE_TYPES
    ]
    lines += [f"[PAGEERROR] {error.message}" for error in page.page_errors()]
    return lines


def network_errors(page: Page) -> list[str]:
    """Requests that failed outright or came back with HTTP 400 or higher."""
    lines: list[str] = []
    for request in page.requests():
        if request.failure:
            lines.append(f"{request.method} {request.url} [{request.failure}]")
            continue
        response = request.existing_response
        if response is not None and response.status >= 400:
            lines.append(f"{request.method} {request.url} → {response.status}")
    return lines
