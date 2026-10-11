"""Locator candidates come from the aria snapshot Playwright produces."""

from workbench.context.locators import extract_locator_candidates

SNAPSHOT = """- generic [active] [ref=e1]:
  - text: Name
  - textbox "Name" [ref=e2]
  - button "Submit" [ref=e3]
  - button "Submit" [ref=e4]
  - link "Say \\"hi\\"" [ref=e5]
  - heading "Don't panic" [level=1] [ref=e6]
  - generic "Not interactive" [ref=e7]"""


def test_interactive_roles_become_get_by_role_calls() -> None:
    assert extract_locator_candidates(SNAPSHOT) == [
        "getByRole('textbox', { name: 'Name' })",
        "getByRole('button', { name: 'Submit' })",
        "getByRole('link', { name: 'Say \"hi\"' })",
        "getByRole('heading', { name: 'Don\\'t panic' })",
    ]


def test_max_count_is_respected() -> None:
    assert len(extract_locator_candidates(SNAPSHOT, max_count=2)) == 2


def test_empty_snapshot_has_no_candidates() -> None:
    assert extract_locator_candidates("") == []
    assert extract_locator_candidates(None) == []
