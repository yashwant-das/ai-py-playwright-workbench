"""Playwright's JSON report becomes a RunResult."""

from typing import Any

from workbench.playwright_report import parse_json_report


def _report(result: dict[str, Any], nested: bool = False) -> dict[str, Any]:
    spec = {"title": "submit", "tests": [{"results": [result]}]}
    suite: dict[str, Any] = {"title": "contact.spec.ts", "specs": [spec]}
    if nested:
        suite = {"title": "contact.spec.ts", "specs": [], "suites": [suite]}
    return {"suites": [suite], "errors": []}


def test_passed_run() -> None:
    run = parse_json_report(_report({"status": "passed", "duration": 812}))
    assert run.passed
    assert run.duration_ms == 812
    assert run.error_message == ""


def test_failed_run_keeps_error_location_and_attachments() -> None:
    result = {
        "status": "failed",
        "duration": 2300,
        "errors": [
            {
                "message": "\x1b[31mTimeoutError: locator.click: Timeout 2000ms exceeded.\x1b[39m",
                "location": {"file": "/w/contact.spec.ts", "line": 5, "column": 37},
            }
        ],
        "attachments": [
            {"name": "screenshot", "path": "/w/out/test-failed-1.png"},
            {"name": "error-context", "path": "/w/out/error-context.md"},
            {"name": "video", "path": "/w/out/video.webm"},
        ],
    }
    run = parse_json_report(_report(result))
    assert run.status == "failed"
    assert run.error_message == "TimeoutError: locator.click: Timeout 2000ms exceeded."
    assert run.error_location == "/w/contact.spec.ts:5:37"
    assert run.screenshot_path == "/w/out/test-failed-1.png"
    assert run.error_context_path == "/w/out/error-context.md"
    assert run.video_path == "/w/out/video.webm"


def test_results_inside_describe_blocks_are_found() -> None:
    run = parse_json_report(
        _report({"status": "timedOut", "duration": 30000}, nested=True)
    )
    assert run.status == "timed_out"


def test_top_level_error_is_a_failure() -> None:
    report = {
        "suites": [],
        "errors": [
            {
                "message": "SyntaxError: Unexpected token (3:20)",
                "location": {"file": "/w/broken.spec.ts", "line": 3, "column": 20},
            }
        ],
    }
    run = parse_json_report(report)
    assert run.status == "failed"
    assert "SyntaxError" in run.error_message
    assert run.error_location == "/w/broken.spec.ts:3:20"


def test_report_without_tests_or_errors_is_an_error() -> None:
    run = parse_json_report({"suites": [], "errors": []})
    assert run.status == "error"
    assert run.error_message == "Playwright ran no tests."


def test_interrupted_run_is_cancelled() -> None:
    assert parse_json_report(_report({"status": "interrupted"})).status == "cancelled"


def _two_tests(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    specs = [
        {"title": "one", "tests": [{"results": [first]}]},
        {"title": "two", "tests": [{"results": [second]}]},
    ]
    return {"suites": [{"title": "contact.spec.ts", "specs": specs}], "errors": []}


def test_a_later_failing_test_fails_the_run() -> None:
    failing = {
        "status": "failed",
        "duration": 40,
        "errors": [{"message": "Error: second broke"}],
        "attachments": [{"name": "screenshot", "path": "/w/out/second.png"}],
    }
    run = parse_json_report(_two_tests({"status": "passed", "duration": 10}, failing))
    assert run.status == "failed"
    assert run.error_message == "Error: second broke"
    assert run.screenshot_path == "/w/out/second.png"
    assert run.duration_ms == 50


def test_first_failing_test_supplies_the_error() -> None:
    first = {"status": "timedOut", "errors": [{"message": "Error: first"}]}
    second = {"status": "failed", "errors": [{"message": "Error: second"}]}
    run = parse_json_report(_two_tests(first, second))
    assert run.status == "timed_out"
    assert run.error_message == "Error: first"


def test_all_tests_passing_is_a_pass() -> None:
    run = parse_json_report(
        _two_tests(
            {"status": "passed", "duration": 5}, {"status": "passed", "duration": 7}
        )
    )
    assert run.passed
    assert run.duration_ms == 12
