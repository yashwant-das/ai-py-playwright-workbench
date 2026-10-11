"""Guards against the pre-v2 layout creeping back in."""

import re
import subprocess
from pathlib import Path

from workbench.config import PROJECT_ROOT

LEGACY_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+(?:src|schemas|benchmarks|gradio|dotenv)\b"
    r"|[\"'](?:src|schemas)\.[a-z_]"
    r"|observability\.(?:tracer|writer)|get_tracer\("
    r"|workbench\.llm\.(?:router|registry|policies)\b|get_default_router\(",
    re.MULTILINE,
)


def _python_files() -> list:
    roots = [PROJECT_ROOT / "src" / "workbench", PROJECT_ROOT / "tests"]
    return [
        p for root in roots for p in root.rglob("*.py") if p.name != "test_layout.py"
    ]


def tracked_paths(root: Path, names: list[str]) -> list[str]:
    """Return the names under which git still tracks files.

    Folders git left behind only because they hold ignored files (such as
    ``__pycache__/``) after a checkout do not count.
    """
    present = []
    for name in names:
        listed = subprocess.run(
            ["git", "ls-files", "--", name],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        if listed.strip():
            present.append(name)
    return present


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
        ".env.example",
        "src/workbench/llm/router.py",
        "src/workbench/llm/registry.py",
        "src/workbench/llm/policies.py",
    ]
    assert tracked_paths(PROJECT_ROOT, legacy) == []


def _git_repo(path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    return path


def test_ignored_leftovers_do_not_count_as_legacy(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    cache = repo / "schemas" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "healing.cpython-313.pyc").write_bytes(b"")

    assert tracked_paths(repo, ["schemas"]) == []


def test_tracked_files_count_as_legacy(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    (repo / "schemas").mkdir()
    (repo / "schemas" / "healing.py").write_text("", encoding="utf-8")
    subprocess.run(["git", "add", "schemas/healing.py"], cwd=repo, check=True)

    assert tracked_paths(repo, ["schemas"]) == ["schemas"]
