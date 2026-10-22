"""The quality gates in the v2 spec (section 8) are switched on in the config files."""

import re
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
    assert '"workspace/**"' in markdownlint


WORKFLOWS = PROJECT_ROOT / ".github" / "workflows"


def test_ci_runs_the_four_jobs() -> None:
    text = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    jobs = text.split("\njobs:\n", 1)[1]
    assert re.findall(r"^  ([a-z][\w-]*):$", jobs, flags=re.MULTILINE) == [
        "lint",
        "unit",
        "integration",
        "ui",
    ]


def test_workflow_actions_are_pinned_to_commits() -> None:
    unpinned = [
        f"{workflow.name}: {line.strip()}"
        for workflow in sorted(WORKFLOWS.glob("*.yml"))
        for line in workflow.read_text(encoding="utf-8").splitlines()
        if "uses:" in line and not re.search(r"@[0-9a-f]{40} # v\d", line)
    ]
    assert unpinned == []


def test_dependabot_checks_three_ecosystems_weekly() -> None:
    text = (PROJECT_ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    ecosystems = re.findall(r"package-ecosystem: ([\w-]+)", text)
    assert ecosystems == ["uv", "npm", "github-actions"]
    assert re.findall(r"interval: (\w+)", text) == ["weekly"] * 3


def test_ci_reports_coverage_in_the_job_summary_only() -> None:
    text = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert "codecov" not in text.lower()
    assert "--cov-report=xml" not in text
    assert "--cov-report=markdown-append" in text
