"""collect_context() against the sample site in a real Chromium."""

from workbench.context import collect_context


def test_sample_site_context(site: str) -> None:
    snap = collect_context(site)
    assert 'button "Submit"' in (snap.aria_snapshot or "")
    assert "getByRole('button', { name: 'Submit' })" in snap.locator_candidates
    assert "getByRole('textbox', { name: 'Name' })" in snap.locator_candidates
    assert snap.console_errors == []
    assert snap.network_errors == []
