"""apply_fix() edits the code and says how: AST, text, or not at all."""

import pytest

from workbench.config import SAMPLE_SPECS_DIR
from workbench.environment import node_available
from workbench.heal import repair
from workbench.heal.repair import apply_fix
from workbench.models.heal import REPAIR_STRATEGY_LABELS, HealingAction, RepairStrategy


def _action(
    original: str, fixed: str, strategy: RepairStrategy = RepairStrategy.STRING_REPLACE
) -> HealingAction:
    return HealingAction(
        original_code=original,
        fixed_code=fixed,
        description="",
        repair_strategy=strategy,
    )


def test_whitespace_tolerant_text_fix() -> None:
    code = "\n        // comment\n        await page.click('#wrong');\n        // next line\n        "
    result = apply_fix(
        code, _action("await page.click('#wrong');", "await page.click('#right');")
    )
    assert result.method == "text"
    assert (
        result.code.strip()
        == "// comment\n        await page.click('#right');\n        // next line"
    )


def test_multiline_fix_keeps_indentation() -> None:
    code = "\n    test('foo', async ({ page }) => {\n        await page.goto('url');\n        await page.click('#wrong');\n    });\n"
    result = apply_fix(
        code,
        _action(
            "await page.goto('url');\nawait page.click('#wrong');",
            "await page.goto('url');\nawait page.click('#right');",
        ),
    )
    assert result.code.strip() == (
        "test('foo', async ({ page }) => {\n        await page.goto('url');\n"
        "        await page.click('#right');\n    });"
    )


def test_nested_replacement_is_reindented() -> None:
    code = "\n    test('nested', async ({ page }) => {\n        await page.click('#wrong');\n        // extra comments\n    });\n"
    result = apply_fix(
        code,
        _action(
            "await page.click('#wrong');",
            "await page.click('#right');\nif (success) {\n    await page.click('#done');\n}",
        ),
    )
    assert result.code.strip() == (
        "test('nested', async ({ page }) => {\n        await page.click('#right');\n"
        "        if (success) {\n            await page.click('#done');\n        }\n"
        "        // extra comments\n    });"
    )


def test_missing_target_changes_nothing() -> None:
    result = apply_fix(
        "await page.click('#a');", _action("await page.click('#zzz');", "x")
    )
    assert result.method is None
    assert result.code == "await page.click('#a');"


def test_ast_result_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(repair, "node_available", lambda: True)
    monkeypatch.setattr(
        repair, "_apply_ast_fix", lambda code, action: code.replace("#old", "#new")
    )
    action = _action(
        'page.locator("#old")', 'page.locator("#new")', RepairStrategy.SELECTOR_REPLACE
    )
    result = apply_fix('await page.locator("#old").click();', action)
    assert result.method == "ast"
    assert result.code == 'await page.locator("#new").click();'
    assert not result.ast_unavailable


def test_missing_node_falls_back_to_text_and_says_so(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(repair, "node_available", lambda: False)
    action = _action(
        'page.locator("#old")', 'page.locator("#new")', RepairStrategy.SELECTOR_REPLACE
    )
    result = apply_fix('await page.locator("#old").click();', action)
    assert result.method == "text"
    assert result.ast_unavailable
    assert result.code == 'await page.locator("#new").click();'


@pytest.mark.skipif(not node_available(), reason="Node.js is needed for the AST repair")
def test_a_locator_fix_that_changes_the_call_is_applied_as_written() -> None:
    spec = (SAMPLE_SPECS_DIR / "contact-form.spec.ts").read_text()
    action = _action(
        "page.locator('#submit-btn').click({ timeout: 3000 })",
        "page.getByRole('button', { name: 'Submit' }).click()",
        RepairStrategy.SELECTOR_REPLACE,
    )
    result = apply_fix(spec, action)
    assert result.method == "text"
    assert "page.getByRole('button', { name: 'Submit' }).click();" in result.code
    assert "locator('button')" not in result.code


def test_every_strategy_has_a_label() -> None:
    assert set(REPAIR_STRATEGY_LABELS) == set(RepairStrategy)
