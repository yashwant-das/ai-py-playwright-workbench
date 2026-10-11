"""The quality gates in the v2 spec (section 8) are switched on in the config files."""

import tomllib

from workbench.config import PROJECT_ROOT

PYPROJECT = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_mypy_is_strict_for_the_package() -> None:
    mypy = PYPROJECT["tool"]["mypy"]
    assert mypy["strict"] is True
    assert mypy["files"] == ["src/workbench"]


def test_coverage_counts_branches_and_fails_under_85() -> None:
    coverage = PYPROJECT["tool"]["coverage"]
    assert coverage["run"]["branch"] is True
    assert coverage["run"]["source"] == ["src/workbench"]
    assert coverage["report"]["fail_under"] == 85


def test_linters_skip_runtime_output() -> None:
    eslint = (PROJECT_ROOT / "eslint.config.cjs").read_text(encoding="utf-8")
    markdownlint = (PROJECT_ROOT / ".markdownlint-cli2.jsonc").read_text(
        encoding="utf-8"
    )
    assert "'workspace/'" in eslint
    assert '"workspace"' in markdownlint
