"""Formatting, highlighting and status presentation for the templates."""

from typing import get_args

from workbench.models.events import StepName
from workbench.models.generate import GenerateStatus
from workbench.models.heal import AttemptOutcome, HealStatus
from workbench.web import views


def test_durations_read_like_the_design() -> None:
    assert views.format_duration(2400) == "2.4s"
    assert views.format_duration(300) == "0.3s"
    assert views.format_duration(65_000) == "1m 05s"
    assert views.format_duration(None) == "–"


def test_sizes_are_in_kilobytes() -> None:
    assert views.format_size(2150) == "2.1 KB"
    assert views.format_size(0) == "0.0 KB"


def test_typescript_is_highlighted_and_escaped() -> None:
    lines = views.highlight_lines(
        'import { test } from "@playwright/test";\n'
        "\n"
        'test("a <b>", async ({ page }) => {\n'
        "  await page.goto(`http://x/`); // go\n"
        "});\n"
    )
    assert len(lines) == 5
    assert lines[0].startswith('<span class="tok-kw">import</span>')
    assert '<span class="tok-str">"@playwright/test"</span>' in lines[0]
    assert lines[1] == ""
    assert '<span class="tok-fn">test</span>' in lines[2]
    assert "&lt;b&gt;" in lines[2] and "<b>" not in lines[2]
    assert '<span class="tok-fn">goto</span>' in lines[3]
    assert '<span class="tok-mut">// go</span>' in lines[3]


def test_leading_blank_lines_keep_their_numbers() -> None:
    assert views.highlight_lines("\na\n") == ["", "a"]
    assert views.highlight_lines("") == []


def test_diff_rows_number_both_sides() -> None:
    rows = views.diff_rows("a\nb\nc\n", "a\nB\nc\n")
    assert [(r.kind, r.old_no, r.new_no) for r in rows] == [
        ("same", 1, 1),
        ("del", 2, None),
        ("add", None, 2),
        ("same", 3, 3),
    ]
    assert views.diff_counts(rows) == (1, 1)


def test_locators_are_listed_once_in_order() -> None:
    code = (
        "await page.getByLabel('Name').fill('Ada');\n"
        "await page.getByRole('button', { name: 'Submit' }).click();\n"
        "await page.getByLabel('Name').clear();\n"
        "await page.locator('#x').click();\n"
    )
    assert views.locators_in(code) == [
        "getByLabel('Name')",
        "getByRole('button', { name: 'Submit' })",
        "locator('#x')",
    ]


def test_every_status_and_outcome_has_a_badge() -> None:
    assert set(get_args(HealStatus)) == set(views.HEAL_BADGES)
    assert set(get_args(GenerateStatus)) == set(views.GENERATE_BADGES)
    assert set(get_args(AttemptOutcome)) == set(views.OUTCOME_BADGES)
    assert views.HEAL_BADGES["app_defect_suspected"].label == "Likely app bug"
    assert views.OUTCOME_BADGES["not_applied"].title == "Fix not applied"


def test_every_step_has_a_title() -> None:
    assert set(get_args(StepName)) == set(views.STEP_INFO)
    assert [s.name for s in views.HEAL_STEPS] == [
        "run",
        "evidence",
        "diagnose",
        "repair",
        "verify",
    ]
    assert [s.name for s in views.GENERATE_STEPS] == ["context", "model", "execute"]
