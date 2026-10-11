"""Every heal result state renders from its saved report."""

import re

import pytest

from tests.unit import report_fixtures as fx
from tests.unit.web_support import make_client
from workbench.reports import save_report

pytestmark = pytest.mark.usefixtures("web_workspace")


def _page(build, query: str = "") -> str:  # type: ignore[no-untyped-def]
    report = build()
    save_report(report)
    response = make_client().get(f"/reports/{report.id}{query}")
    assert response.status_code == 200
    return response.text


def test_healed_shows_the_diff_diagnosis_and_downloads() -> None:
    html = _page(fx.healed)
    assert "pill--pass" in html and "Healed" in html and "contact-form.spec.ts" in html
    assert "code__line--del" in html and "code__line--add" in html
    assert 'class="diffstat--add">+1<' in html and 'class="diffstat--del">-1<' in html
    for label in ("Diff", "Re-run video", "Execution log", "Model I/O"):
        assert f">{label}</a>" in html
    assert 'aria-current="page">Diff</a>' in html
    assert 'role="tab"' not in html and 'role="tabpanel"' not in html
    assert "LOCATOR_DRIFT" in html and "0.90" in html
    assert "Selector replaced on the syntax tree" in html
    assert "Re-run passed in 2.1s" in html
    assert "qwen3.6:35b-mlx · Ollama" in html
    assert "/spec" in html and "Download fixed spec" in html


def test_retries_show_attempt_chips_and_select_the_healed_one() -> None:
    html = _page(fx.healed_after_retries)
    assert "Fix not applied" in html and "2 attempts" in html
    assert 'aria-current="true"' in html.split("Attempt 2")[0].rsplit("<a", 1)[1]
    first = _page(fx.healed_after_retries, "?attempt=1&tab=model")
    assert "Diagnosis · attempt 1" in first


def test_model_io_lists_sections_and_truncation() -> None:
    html = _page(fx.healed, "?tab=model")
    assert "Sent to the model" in html
    assert "Page snapshot at failure" in html and "cut from 17.6 KB" in html
    assert "valid HealingAnalysis" in html
    assert "4,812 in · 386 out" in html


def test_execution_log_and_video_tabs() -> None:
    assert "TimeoutError: locator.click" in _page(fx.healed, "?tab=log")
    video = _page(fx.healed, "?tab=video")
    assert '<video class="video" controls' in video and "/video?attempt=1" in video


def _between_lines(html: str) -> list[str]:
    """The text between consecutive line elements; any of it renders as a blank line."""
    return re.findall(r"</span></span>(\s*)<span class=\"code__line", html)


def test_code_and_diff_lines_have_no_whitespace_between_them() -> None:
    diff = _page(fx.healed)
    assert 'class="code__line code__line--diff' in diff
    assert diff.count('<span class="code__line') > 3
    assert _between_lines(diff) == [""] * (diff.count('<span class="code__line') - 1)
    model = _page(fx.healed, "?tab=model")
    assert 'class="code__line"' in model
    assert set(_between_lines(model)) <= {""}


def test_execution_log_has_no_template_whitespace() -> None:
    html = _page(fx.healed, "?tab=log")
    body = html.split('<div class="log__body" tabindex="0">')[1].split("</section>")[0]
    assert not body[0].isspace()
    assert not re.search(r">\s+<", body)
    assert "TimeoutError: locator.click" in body


def test_not_healed_lists_every_attempt() -> None:
    html = _page(fx.not_healed)
    assert "Not healed" in html
    for title in ("Re-run failed", "Fix not applied", "Invalid model reply"):
        assert title in html
    assert ">Diff</a>" not in html
    assert "action_taken: Field required" in _page(
        fx.not_healed, "?attempt=3&tab=model"
    )


def test_app_defect_stops_without_changing_the_test() -> None:
    html = _page(fx.app_defect)
    assert "pill--warn" in html and "Likely app bug" in html
    assert "The test was not changed." in html
    assert "POTENTIAL_APP_DEFECT" in html
    assert ">Diff</a>" not in html


def test_nothing_to_heal_and_cancelled() -> None:
    assert "The test passed on its first run" in _page(fx.nothing_to_heal)
    assert "The file was not changed" in _page(fx.cancelled)


def test_model_failure_result_says_model_unreachable() -> None:
    html = _page(fx.model_error)
    assert "Model unreachable" in html
    assert "Could not reach Ollama at http://localhost:11434/v1" in html


def test_model_timeout_result_says_model_timed_out() -> None:
    report = fx.model_error().model_copy(
        update={
            "error_message": "The model call failed: Ollama at http://localhost:11434/v1 did not answer within 300 seconds."
        }
    )
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    assert "Model timed out" in html and "Model unreachable" not in html
    assert "did not answer within 300 seconds" in html


def test_demo_runs_are_labelled() -> None:
    html = _page(fx.demo_healed)
    assert "Answers replayed from samples/recordings" in html
    assert '<span class="pill pill--warn">Demo</span>' in html


def test_warnings_become_banners() -> None:
    html = _page(fx.with_warnings)
    assert "Page context unavailable" in html
    assert "Repair used text replacement" in html


def test_an_unavailable_tab_falls_back_to_the_first() -> None:
    html = _page(fx.not_healed, "?tab=diff")
    assert 'aria-current="page">Execution log</a>' in html


@pytest.mark.parametrize("report_id", ["nope", "20261004-120000-heal-missing"])
def test_unknown_reports_are_404(report_id: str) -> None:
    response = make_client().get(f"/reports/{report_id}")
    assert response.status_code == 404
    assert "No such report" in response.text


@pytest.mark.parametrize(
    ("message", "title"),
    [
        (
            "Could not reach Ollama at http://localhost:11434/v1. Is it running?",
            "Model unreachable",
        ),
        (
            "Ollama at http://localhost:11434/v1 did not answer within 300 seconds.",
            "Model timed out",
        ),
        (
            "Demo only covers the bundled samples. Choose LM Studio or Ollama in the model menu to heal other tests.",
            "The model call failed",
        ),
        (
            "Ollama at http://localhost:11434/v1 has no model named 'x'. Load it or pick another model.",
            "The model call failed",
        ),
        (
            "LM Studio at http://localhost:1234/v1 answered HTTP 400: context length exceeded",
            "The model call failed",
        ),
        (
            "LM Studio at http://localhost:1234/v1 did not return a chat completion.",
            "The model call failed",
        ),
    ],
)
def test_a_model_failure_is_named_for_what_happened(message: str, title: str) -> None:
    report = fx.model_error().model_copy(
        update={"error_message": f"The model call failed: {message}"}
    )
    save_report(report)
    html = make_client().get(f"/reports/{report.id}").text
    assert re.findall(r'<p class="banner__title">([^<]*)</p>', html) == [title]


def test_every_heal_result_offers_the_report_download() -> None:
    for build in fx.HEAL_STATES.values():
        report = build()
        save_report(report)
        html = make_client().get(f"/reports/{report.id}").text
        assert f'href="/reports/{report.id}.json" download>Download report</a>' in html
    healed = _page(fx.healed)
    assert "Download fixed spec" in healed and "Copy diff" in healed


ODD_LINE_BREAKS = " ", " ", "\f", "\v", "\x1c", "\x1d", "\x1e", "\x85"


def test_a_spec_with_unusual_line_break_characters_still_renders() -> None:
    # str.splitlines() breaks on all of these; a source line only ends at a newline.
    odd = "".join(ODD_LINE_BREAKS)
    original = fx.ORIGINAL.replace("Ada Lovelace", f"Ada{odd}Lovelace")
    assert original != fx.ORIGINAL
    fixed = original.replace("#submit-btn", "#send-btn")
    report = fx.healed().model_copy(
        update={"original_code": original, "final_code": fixed}
    )
    save_report(report)
    client = make_client()
    diff = client.get(f"/reports/{report.id}?tab=diff")
    assert diff.status_code == 200
    lines = len(fx.ORIGINAL.splitlines())
    assert diff.text.count('<span class="code__line') == lines + 1
    assert 'class="diffstat--add">+1<' in diff.text
    assert 'class="diffstat--del">-1<' in diff.text
    numbers = re.findall(
        r'<span class="code__num">(\d*)</span><span class="code__num">(\d*)</span>',
        diff.text,
    )
    assert numbers[-1] == (str(lines), str(lines))


def test_scrolling_panes_can_be_reached_from_the_keyboard() -> None:
    # A pane that scrolls needs focus, or keyboard users cannot read all of it.
    assert '<pre class="code__body" tabindex="0">' in _page(fx.healed)
    assert '<div class="log__body" tabindex="0">' in _page(fx.healed, "?tab=log")
    assert '<pre class="code__body" tabindex="0">' in _page(fx.healed, "?tab=model")
    assert '<pre class="code__body" tabindex="0">' in _page(fx.generate_passed)
