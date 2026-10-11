"""collect_context() with a fake browser: snapshot, signals, failures."""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from workbench.context import collector


def _page(aria: str = '- button "Submit" [ref=e3]') -> MagicMock:
    page = MagicMock()
    page.content.return_value = (
        "<html><body><button>Submit</button><script>x()</script></body></html>"
    )
    page.aria_snapshot.return_value = aria
    page.console_messages.return_value = [
        SimpleNamespace(type="error", text="boom"),
        SimpleNamespace(type="log", text="hello"),
    ]
    page.page_errors.return_value = [SimpleNamespace(message="kaput")]
    page.requests.return_value = [
        SimpleNamespace(
            method="GET",
            url="http://x/a.js",
            failure="net::ERR_FAILED",
            existing_response=None,
        ),
        SimpleNamespace(
            method="POST",
            url="http://x/orders",
            failure=None,
            existing_response=SimpleNamespace(status=500),
        ),
        SimpleNamespace(
            method="GET",
            url="http://x/ok",
            failure=None,
            existing_response=SimpleNamespace(status=200),
        ),
    ]
    return page


def _browser(monkeypatch: pytest.MonkeyPatch, page: MagicMock) -> MagicMock:
    playwright = MagicMock()
    browser = playwright.__enter__.return_value.chromium.launch.return_value
    browser.new_page.return_value = page
    monkeypatch.setattr(collector, "sync_playwright", lambda: playwright)
    return browser


def test_snapshot_signals_and_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    page = _page()
    browser = _browser(monkeypatch, page)

    snap = collector.collect_context("http://x/", wait_ms=0)

    page.aria_snapshot.assert_called_once_with(mode="ai")
    assert snap.aria_snapshot == '- button "Submit" [ref=e3]'
    assert snap.locator_candidates == ["getByRole('button', { name: 'Submit' })"]
    assert "<script>" not in (snap.html or "")
    assert snap.console_errors == ["[ERROR] boom", "[PAGEERROR] kaput"]
    assert snap.network_errors == [
        "GET http://x/a.js [net::ERR_FAILED]",
        "POST http://x/orders → 500",
    ]
    assert not snap.is_empty
    browser.close.assert_called_once()


def test_long_snapshot_is_kept_whole(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only render_prompt cuts the snapshot, so the cut is recorded on the exchange.
    aria = "- text: " + "x" * 50_000
    _browser(monkeypatch, _page(aria=aria))
    snap = collector.collect_context("http://x/", wait_ms=0)
    assert snap.aria_snapshot == aria


def test_navigation_failure_returns_an_empty_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = _page()
    page.goto.side_effect = RuntimeError("net::ERR_CONNECTION_REFUSED")
    browser = _browser(monkeypatch, page)
    snap = collector.collect_context("http://x/", wait_ms=0)
    assert snap.is_empty
    assert snap.url == "http://x/"
    browser.close.assert_called_once()


def test_browser_launch_failure_returns_an_empty_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken() -> Any:
        raise RuntimeError("Executable doesn't exist")

    monkeypatch.setattr(collector, "sync_playwright", broken)
    assert collector.collect_context("http://x/", wait_ms=0).is_empty


def test_dom_collector_strips_noise_and_respects_the_limit() -> None:
    from workbench.context.dom import collect_dom

    page = MagicMock()
    page.content.return_value = (
        "<html><body><script>a()</script><style>b{}</style><svg><path d='M0 0'/></svg>"
        + "<p>word</p>" * 100
        + "</body></html>"
    )
    html = collect_dom(page, max_chars=100)
    assert "<script>" not in html
    assert "<style>" not in html
    assert "<svg>" not in html
    assert len(html) <= 100


def test_dom_collector_returns_empty_when_the_page_is_gone() -> None:
    from workbench.context.dom import collect_dom

    page = MagicMock()
    page.content.side_effect = RuntimeError("page closed")
    assert collect_dom(page) == ""
