"""Guards against the pre-v2 layout creeping back in."""

import re

from workbench.config import PROJECT_ROOT

LEGACY_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+(?:src|schemas|benchmarks|gradio)\b"
    r"|[\"'](?:src|schemas)\.[a-z_]"
    r"|observability\.(?:tracer|writer)|get_tracer\(",
    re.MULTILINE,
)


def _python_files() -> list:
    roots = [PROJECT_ROOT / "src" / "workbench", PROJECT_ROOT / "tests"]
    return [
        p for root in roots for p in root.rglob("*.py") if p.name != "test_layout.py"
    ]


def test_no_module_uses_the_legacy_layout() -> None:
    offenders = [
        str(path.relative_to(PROJECT_ROOT))
        for path in _python_files()
        if LEGACY_IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_legacy_top_level_folders_are_gone() -> None:
    legacy = [
        "schemas",
        "benchmarks",
        "scripts",
        "prompts",
        "src/__init__.py",
        "src/agents",
        "src/services",
        "src/healing",
        "src/utils",
        "src/context",
        "src/llm",
        "src/observability",
    ]
    present = [name for name in legacy if (PROJECT_ROOT / name).exists()]
    assert present == []
