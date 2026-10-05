"""Report, spec and video downloads, and that forged ids and paths get nothing."""

import json

import pytest

from tests.unit import report_fixtures as fx
from tests.unit.web_support import make_client
from workbench.config import runs_dir
from workbench.models.generate import GenerateReport
from workbench.reports import save_report

pytestmark = pytest.mark.usefixtures("web_workspace")

WEBM = b"\x1aE\xdf\xa3" + b"\x00" * 2048


def test_report_json_downloads() -> None:
    report = fx.healed()
    save_report(report)
    response = make_client().get(f"/reports/{report.id}.json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    assert json.loads(response.text)["id"] == report.id


def test_spec_download_is_the_fixed_or_original_code() -> None:
    healed, failed = fx.healed(), fx.not_healed()
    save_report(healed)
    save_report(failed)
    client = make_client()
    fixed = client.get(f"/reports/{healed.id}/spec")
    assert fixed.text == fx.FIXED
    assert 'filename="contact-form.spec.ts"' in fixed.headers["content-disposition"]
    assert client.get(f"/reports/{failed.id}/spec").text == fx.ORIGINAL


def test_generated_spec_downloads() -> None:
    report = GenerateReport(
        id="20261004-120000-generate-contact",
        url="http://x/",
        scenario="s",
        status="not_run",
        spec_name="a-user.spec.ts",
        code="test('x', () => {});\n",
    )
    save_report(report)
    response = make_client().get(f"/reports/{report.id}/spec")
    assert response.text == report.code
    assert 'filename="a-user.spec.ts"' in response.headers["content-disposition"]


def test_rerun_video_streams_from_the_runs_folder() -> None:
    video = runs_dir() / "r1" / "test-results" / "video.webm"
    video.parent.mkdir(parents=True)
    video.write_bytes(WEBM)
    healed = fx.attempt(1, "healed")
    assert healed.rerun is not None
    healed.rerun.video_path = str(video)
    report = fx.healed().model_copy(update={"attempts": [healed]})
    save_report(report)
    client = make_client()
    whole = client.get(f"/reports/{report.id}/video?attempt=1")
    assert whole.status_code == 200
    assert whole.headers["content-type"] == "video/webm"
    assert whole.content == WEBM
    part = client.get(
        f"/reports/{report.id}/video?attempt=1", headers={"Range": "bytes=0-3"}
    )
    assert part.status_code == 206
    assert part.content == WEBM[:4]


@pytest.mark.parametrize("video_path", ["/etc/hosts", "RUNS/../outside.webm"])
def test_video_outside_the_runs_folder_is_not_served(video_path: str) -> None:
    outside = runs_dir().parent / "outside.webm"
    outside.write_bytes(WEBM)
    healed = fx.attempt(1, "healed")
    assert healed.rerun is not None
    healed.rerun.video_path = video_path.replace("RUNS", str(runs_dir()))
    report = fx.healed().model_copy(update={"attempts": [healed]})
    save_report(report)
    assert make_client().get(f"/reports/{report.id}/video?attempt=1").status_code == 404


def test_video_symlinked_out_of_the_runs_folder_is_not_served() -> None:
    outside = runs_dir().parent / "outside.webm"
    outside.write_bytes(WEBM)
    link = runs_dir() / "r1" / "video.webm"
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    healed = fx.attempt(1, "healed")
    assert healed.rerun is not None
    healed.rerun.video_path = str(link)
    report = fx.healed().model_copy(update={"attempts": [healed]})
    save_report(report)
    assert make_client().get(f"/reports/{report.id}/video?attempt=1").status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/reports/nope.json",
        "/reports/nope/spec",
        "/reports/nope/video",
        "/reports/20261004-120000-heal-missing.json",
        "/reports/20261004-120000-heal-missing/video?attempt=1",
    ],
)
def test_downloads_reject_forged_ids(path: str) -> None:
    assert make_client().get(path).status_code == 404


def test_missing_attempt_or_video_is_404() -> None:
    report = fx.not_healed()
    save_report(report)
    client = make_client()
    assert client.get(f"/reports/{report.id}/video?attempt=9").status_code == 404
    assert client.get(f"/reports/{report.id}/video?attempt=2").status_code == 404
