"""Turns Playwright's JSON report into a RunResult."""

import json
from pathlib import Path
from typing import Any

from workbench.models.shared import RunResult, RunStatus
from workbench.text import clean_ansi_codes

_STATUS: dict[str, RunStatus] = {
    "passed": "passed",
    "failed": "failed",
    "timedOut": "timed_out",
    "interrupted": "cancelled",
    "skipped": "failed",
}


def read_json_report(path: Path) -> dict[str, Any] | None:
    """Load the report Playwright wrote, or None if it is missing or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def parse_json_report(report: dict[str, Any]) -> RunResult:
    """Build a RunResult from every test result in a JSON report.

    The run fails if any test did not pass; the first such test supplies the
    status, error and attachments. A spec that does not compile has no test
    results, only top-level errors; that is a failure the healer can work on,
    not a runner error.
    """
    results = _final_results(report.get("suites") or [])
    if not results:
        errors = report.get("errors") or []
        if errors:
            message, location = _error_text(errors[0])
            return RunResult(
                status="failed", error_message=message, error_location=location
            )
        return RunResult(status="error", error_message="Playwright ran no tests.")

    chosen = next((r for r in results if r.get("status") != "passed"), results[0])
    errors = chosen.get("errors") or []
    message, location = _error_text(errors[0]) if errors else ("", "")
    attachments: dict[str, str] = {}
    for attachment in chosen.get("attachments") or []:
        name, path = attachment.get("name"), attachment.get("path")
        if name and path and name not in attachments:
            attachments[name] = path
    return RunResult(
        status=_STATUS.get(str(chosen.get("status")), "failed"),
        duration_ms=sum(int(r.get("duration") or 0) for r in results),
        error_message=message,
        error_location=location,
        screenshot_path=attachments.get("screenshot"),
        error_context_path=attachments.get("error-context"),
        video_path=attachments.get("video"),
    )


def _final_results(suites: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The deciding (last retry) result of every test, in report order."""
    found: list[dict[str, Any]] = []
    for suite in suites:
        for spec in suite.get("specs") or []:
            for test in spec.get("tests") or []:
                results: list[dict[str, Any]] = test.get("results") or []
                if results:
                    found.append(results[-1])  # the final retry decides the outcome
        found.extend(_final_results(suite.get("suites") or []))
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
