"""Runs one Playwright spec and reads its result from Playwright's JSON report.

Each run gets its own output folder, so the screenshot, error context and
video in the result always belong to that run. Playwright starts in its own
process group, so stopping a run also stops the browsers it launched.
"""

import logging
import os
import re
import signal
import subprocess
import threading
import time
from pathlib import Path

from workbench.config import PROJECT_ROOT, WORKSPACE_PLAYWRIGHT_CONFIG, runs_dir
from workbench.ids import new_run_id
from workbench.models.shared import RunResult
from workbench.playwright_report import parse_json_report, read_json_report
from workbench.text import clean_ansi_codes

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 120.0
_POLL_S = 0.25


def run_test(
    spec: Path | str,
    run_dir: Path | None = None,
    *,
    record_video: bool = False,
    cancel: threading.Event | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> RunResult:
    """Run ``spec`` with Playwright Test and return its result.

    Args:
        spec:         The ``.spec.ts`` file to run, in any folder.
        run_dir:      Where Playwright writes its output; a new folder under
                      ``workspace/runs`` when omitted.
        record_video: Record a video with captioned actions.
        cancel:       Set it to stop the run; the result is then ``cancelled``.
        timeout_s:    Hard limit for the whole run.
    """
    spec = Path(spec).resolve()
    run_dir = run_dir or runs_dir() / new_run_id("run", spec.stem)
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "report.json"
    command = [
        "npx",
        "playwright",
        "test",
        re.escape(str(spec)),  # Playwright treats file arguments as regexes
        "--config",
        str(WORKSPACE_PLAYWRIGHT_CONFIG),
        "--output",
        str(run_dir / "test-results"),
        "--reporter=json",
        # Heal only uses the first failure, and stopping there keeps a run of
        # many slow failures inside the time limit, so its report is written.
        "--max-failures=1",
    ]
    env = {
        **os.environ,
        "PLAYWRIGHT_JSON_OUTPUT_FILE": str(report_path),
        "WORKBENCH_SPECS_DIR": str(spec.parent),
        "WORKBENCH_RECORD_VIDEO": "1" if record_video else "0",
        "FORCE_COLOR": "0",
        # Specs may live outside the project (a custom WORKBENCH_WORKSPACE), where
        # Node cannot find @playwright/test on its own.
        "NODE_PATH": os.pathsep.join(
            [str(PROJECT_ROOT / "node_modules"), os.environ.get("NODE_PATH", "")]
        ).rstrip(os.pathsep),
    }
    started = time.monotonic()
    try:
        proc = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            command,
            cwd=PROJECT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError:
        return RunResult(
            status="error",
            error_message="npx was not found. Install Node.js 24 and run npm ci.",
        )

    while True:
        try:
            stdout, stderr = proc.communicate(timeout=_POLL_S)
            break
        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            if cancel is not None and cancel.is_set():
                _stop(proc)
                return RunResult(
                    status="cancelled",
                    duration_ms=elapsed_ms,
                    error_message="The run was cancelled.",
                )
            if elapsed_ms > timeout_s * 1000:
                _stop(proc)
                return RunResult(
                    status="timed_out",
                    duration_ms=elapsed_ms,
                    error_message=f"Playwright did not finish within {timeout_s:.0f} seconds.",
                )

    duration_ms = int((time.monotonic() - started) * 1000)
    report = read_json_report(report_path)
    if report is None:
        message = (
            clean_ansi_codes(stderr or "").strip()
            or "Playwright did not write a report."
        )
        return RunResult(
            status="error",
            duration_ms=duration_ms,
            error_message=message[:2000],
            stdout=stdout or "",
            stderr=stderr or "",
        )
    result = parse_json_report(report)
    logger.debug("%s finished: %s", spec.name, result.status)
    return result.model_copy(
        update={
            "stdout": stdout or "",
            "stderr": stderr or "",
            "duration_ms": result.duration_ms or duration_ms,
        }
    )


def _stop(proc: "subprocess.Popen[str]") -> None:
    """Stop Playwright and every browser it started."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
