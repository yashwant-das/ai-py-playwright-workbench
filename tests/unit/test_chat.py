"""The ChatModel interface's shared helper."""

from workbench.llm.chat import response_format_for


def test_response_format_names_the_schema() -> None:
    schema = {"title": "HealingAnalysis", "type": "object"}
    assert response_format_for(schema) == {
        "type": "json_schema",
        "json_schema": {"name": "HealingAnalysis", "schema": schema},
    }
