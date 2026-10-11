"""Reports round-trip through JSON files in the workspace."""

from pathlib import Path

import pytest

from workbench.models.generate import ContextSummary, GenerateReport
from workbench.models.heal import Attempt, FailureEvidence, HealReport
from workbench.models.shared import ModelExchange, PromptSection, RunResult
from workbench.reports import (
    inside,
    list_report_ids,
    load_report,
    report_path,
    save_report,
)


@pytest.fixture(autouse=True)
def _workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WORKBENCH_WORKSPACE", str(tmp_path))


def _heal(report_id: str = "20261003-140509-heal-contact") -> HealReport:
    return HealReport(
        id=report_id,
        spec_name="contact.spec.ts",
        status="healed",
        attempts=[
            Attempt(
                number=1,
                outcome="healed",
                evidence=FailureEvidence(error_message="boom", source="error_context"),
                exchange=ModelExchange(
                    sections=[
                        PromptSection(name="Test file", chars=10, original_chars=20)
                    ],
                    valid=True,
                ),
                repair_method="ast",
                rerun=RunResult(status="passed", video_path="/v.webm"),
            )
        ],
        warnings=["ast_unavailable"],
    )


def test_heal_report_round_trip() -> None:
    report = _heal()
    save_report(report)
    loaded = load_report("20261003-140509-heal-contact")
    assert isinstance(loaded, HealReport)
    assert loaded == report
    assert loaded.attempts[0].exchange.sections[0].truncated  # type: ignore[union-attr]


def test_generate_report_round_trip() -> None:
    report = GenerateReport(
        id="20261003-140600-generate-login",
        url="http://x/",
        scenario="login",
        status="not_run",
        context=ContextSummary(url="http://x/", snapshot_lines=3),
    )
    save_report(report)
    assert load_report(report.id) == report


def test_list_is_newest_first() -> None:
    save_report(_heal("20261003-140509-heal-a"))
    save_report(_heal("20261003-150000-heal-b"))
    assert list_report_ids() == ["20261003-150000-heal-b", "20261003-140509-heal-a"]


@pytest.mark.parametrize(
    "bad_id", ["../../etc/passwd", "x.json", "", "20261003-140509-heal-A"]
)
def test_load_report_rejects_path_traversal(bad_id: str) -> None:
    with pytest.raises(ValueError):
        report_path(bad_id)


def test_unknown_report_is_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        load_report("20261003-140509-heal-missing")


@pytest.mark.parametrize("name", ["../x.json", "a/../../x.json", "/etc/passwd", ".."])
def test_inside_refuses_a_name_that_leaves_the_folder(
    tmp_path: Path, name: str
) -> None:
    with pytest.raises(ValueError, match="outside"):
        inside(tmp_path, name)


def test_inside_returns_the_path_of_a_plain_name(tmp_path: Path) -> None:
    assert inside(tmp_path, "report.json") == tmp_path / "report.json"
