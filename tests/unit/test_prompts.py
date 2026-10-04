"""Prompt files, versions and rendered sections."""

from workbench.llm.prompts import (
    get_prompt_hash,
    get_prompt_version,
    load_prompt,
    render_prompt,
)


def test_healer_prompt_is_version_3_and_formats() -> None:
    assert get_prompt_version("healer") == "3"
    text = load_prompt("healer").format(
        failure_type="TIMEOUT", confidence="1.00", reason="r"
    )
    assert "POTENTIAL_APP_DEFECT" in text
    assert '"failure_type"' in text  # JSON braces survived str.format


def test_prompt_hash_is_stable() -> None:
    assert get_prompt_hash("healer") == get_prompt_hash("healer")


def test_render_prompt_cuts_and_records() -> None:
    text, sections = render_prompt([("A", "abc"), ("B", "x" * 10)], {"A": 100, "B": 4})
    assert text == "## A\nabc\n\n## B\nxxxx"
    assert [(s.name, s.chars, s.original_chars) for s in sections] == [
        ("A", 3, None),
        ("B", 4, 10),
    ]
