"""Turns Playwright's JSON report into a RunResult."""

import json
from pathlib import Path
from typing import Any

from workbench.models.shared import RunResult, RunStatus
from workbench.text import clean_ansi_codes

# The raw status of the deciding result of an unexpected test.
_FAILED_STATUS: dict[str, RunStatus] = {"timedOut": "timed_out"}
# Outcomes that do not fail a run. Any other, "unexpected" or a missing one, does.
_NOT_FAILED = ("expected", "flaky", "skipped")


def read_json_report(path: Path) -> dict[str, Any] | None:
    """Load the report Playwright wrote, or None if it is missing or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def parse_json_report(report: dict[str, Any]) -> RunResult:
    """Build a RunResult from Playwright's test outcomes.

    Each test carries an outcome (``expected``, ``unexpected``, ``flaky`` or
    ``skipped``) that already accounts for ``test.fail()`` and skips. The run
    fails if any test is unexpected; the first such test supplies the error and
    attachments. ``flaky`` counts as passed; a missing outcome counts as a
    failure, so a malformed report never passes a re-run. A run in which every
    test was skipped is an error, as there is nothing to heal.

    Without tests, only top-level errors remain. One located in a file (a spec
    that does not compile) is a failure the healer can work on; one without a
    location, such as "No tests found", is a runner error.
    """
    tests = _tests(report.get("suites") or [])
    if not tests:
        return _without_tests(report.get("errors") or [])

    finals = [results[-1] for _, results in tests if results]
    duration_ms = sum(int(r.get("duration") or 0) for r in finals)
    unexpected = next(
        (
            results[-1] if results else {}
            for outcome, results in tests
            if outcome not in _NOT_FAILED
        ),
        None,
    )
    if unexpected is not None:
        errors = unexpected.get("errors") or []
        message, location = _error_text(errors[0]) if errors else ("", "")
        attachments = _attachments(unexpected)
        return RunResult(
            status=_FAILED_STATUS.get(str(unexpected.get("status")), "failed"),
            duration_ms=duration_ms,
            error_message=message,
            error_location=location,
            screenshot_path=attachments.get("screenshot"),
            error_context_path=attachments.get("error-context"),
            video_path=attachments.get("video"),
        )
    if any(r.get("status") == "interrupted" for r in finals):
        return RunResult(status="cancelled", duration_ms=duration_ms)
    ran = [
        results[-1] for outcome, results in tests if outcome != "skipped" and results
    ]
    if not ran:
        return RunResult(
            status="error",
            duration_ms=duration_ms,
            error_message="All tests were skipped.",
        )
    # A passing run reports only its video: the verification re-run's recording.
    return RunResult(
        status="passed",
        duration_ms=duration_ms,
        video_path=_attachments(ran[0]).get("video"),
    )


def _attachments(result: dict[str, Any]) -> dict[str, str]:
    """The first path of each named attachment of one result."""
    found: dict[str, str] = {}
    for attachment in result.get("attachments") or []:
        name, path = attachment.get("name"), attachment.get("path")
        if name and path and name not in found:
            found[name] = path
    return found


def _without_tests(errors: list[dict[str, Any]]) -> RunResult:
    if not errors:
        return RunResult(status="error", error_message="Playwright ran no tests.")
    message, location = _error_text(errors[0])
    if not location or "No tests found" in message:
        return RunResult(status="error", error_message=message)
    return RunResult(status="failed", error_message=message, error_location=location)


def _tests(suites: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    """Every test's outcome and its results, in report order.

    The last result is the final retry, which decides the outcome.
    """
    found: list[tuple[str, list[dict[str, Any]]]] = []
    for suite in suites:
        for spec in suite.get("specs") or []:
            for test in spec.get("tests") or []:
                found.append((str(test.get("status")), test.get("results") or []))
        found.extend(_tests(suite.get("suites") or []))
    return found


def _error_text(error: dict[str, Any]) -> tuple[str, str]:
    message = clean_ansi_codes(
        str(error.get("message") or error.get("value") or "")
    ).strip()
    location = error.get("location") or {}
    where = (
        f"{location['file']}:{location.get('line', 0)}:{location.get('column', 0)}"
        if location.get("file")
        else ""
    )
    return message, where
