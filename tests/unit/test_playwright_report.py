"""Playwright's JSON report becomes a RunResult."""

from typing import Any

from workbench.playwright_report import parse_json_report

# Fixtures follow the shape Playwright 1.64's JSON reporter writes: every test
# carries its outcome in a test-level "status" ("expected", "unexpected",
# "flaky", "skipped"); each result carries the raw status of one try.


def _outcome(result: dict[str, Any]) -> str:
    """The outcome Playwright gives a test without annotations."""
    raw = result.get("status")
    if raw == "passed":
        return "expected"
    if raw in ("skipped", "interrupted"):
        return "skipped"
    return "unexpected"


def _test(result: dict[str, Any], outcome: str | None = None) -> dict[str, Any]:
    return {"status": outcome or _outcome(result), "results": [result]}


def _report(result: dict[str, Any], nested: bool = False) -> dict[str, Any]:
    spec = {"title": "submit", "tests": [_test(result)]}
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
    return _specs(_test(first), _test(second))


def _specs(*tests: dict[str, Any]) -> dict[str, Any]:
    specs = [{"title": f"t{i}", "tests": [test]} for i, test in enumerate(tests)]
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


def test_a_skipped_test_does_not_hide_the_failing_one() -> None:
    skipped = {"status": "skipped", "duration": 0, "errors": [], "attachments": []}
    failing = {
        "status": "failed",
        "duration": 30,
        "errors": [
            {
                "message": "Error: expect(received).toBe(expected)",
                "location": {"file": "/w/skip.spec.ts", "line": 3, "column": 35},
            }
        ],
        "attachments": [
            {"name": "error-context", "path": "/w/out/b/error-context.md"},
        ],
    }
    run = parse_json_report(_specs(_test(skipped), _test(failing)))
    assert run.status == "failed"
    assert run.error_message == "Error: expect(received).toBe(expected)"
    assert run.error_location == "/w/skip.spec.ts:3:35"
    assert run.error_context_path == "/w/out/b/error-context.md"


def test_a_test_that_fails_as_marked_by_test_fail_passes() -> None:
    result = {
        "status": "failed",
        "duration": 20,
        "errors": [{"message": "Error: expect(received).toBe(expected)"}],
        "attachments": [{"name": "error-context", "path": "/w/out/error-context.md"}],
    }
    run = parse_json_report(_specs(_test(result, outcome="expected")))
    assert run.passed
    assert run.error_message == ""
    assert run.error_context_path is None


def test_a_flaky_test_counts_as_passed() -> None:
    test = {
        "status": "flaky",
        "results": [
            {"status": "failed", "errors": [{"message": "Error: first try"}]},
            {"status": "passed", "duration": 9},
        ],
    }
    assert parse_json_report(_specs(test)).passed


def test_a_timed_out_unexpected_test_is_timed_out() -> None:
    skipped = {"status": "skipped"}
    timed_out = {
        "status": "timedOut",
        "errors": [{"message": "Test timeout of 30000ms exceeded."}],
    }
    run = parse_json_report(_specs(_test(skipped), _test(timed_out)))
    assert run.status == "timed_out"
    assert run.error_message == "Test timeout of 30000ms exceeded."


def test_every_test_skipped_is_an_error() -> None:
    skipped = {"status": "skipped", "duration": 0, "errors": [], "attachments": []}
    run = parse_json_report(_specs(_test(skipped), _test(dict(skipped))))
    assert run.status == "error"
    assert "skipped" in run.error_message


def test_no_tests_found_is_an_error_not_a_failure() -> None:
    message = (
        "Error: No tests found.\nMake sure that arguments are regular expressions"
        " matching test files."
    )
    run = parse_json_report(
        {"suites": [], "errors": [{"message": message, "stack": message}]}
    )
    assert run.status == "error"
    assert run.error_message.startswith("Error: No tests found.")


def test_top_level_error_without_a_location_is_an_error() -> None:
    run = parse_json_report(
        {"suites": [], "errors": [{"message": "Error: config could not be loaded"}]}
    )
    assert run.status == "error"
    assert run.error_message == "Error: config could not be loaded"


def test_a_passing_run_keeps_only_its_video() -> None:
    skipped = {"status": "skipped"}
    expected_failure = {
        "status": "failed",
        "errors": [{"message": "Error: failed as marked"}],
        "attachments": [
            {"name": "error-context", "path": "/w/out/error-context.md"},
            {"name": "video", "path": "/w/out/video.webm"},
        ],
    }
    run = parse_json_report(
        _specs(_test(skipped), _test(expected_failure, outcome="expected"))
    )
    assert run.passed
    assert run.video_path == "/w/out/video.webm"
    assert run.error_context_path is None


def test_a_test_without_a_known_outcome_fails_closed() -> None:
    result = {"status": "failed", "errors": [{"message": "Error: boom"}]}
    run = parse_json_report(_specs({"results": [result]}))
    assert run.status == "failed"
    assert run.error_message == "Error: boom"
