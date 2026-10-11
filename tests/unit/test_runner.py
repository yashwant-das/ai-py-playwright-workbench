"""The runner builds the right command and reads the report it asked for."""

import json
import os
import re
import subprocess
import threading
from pathlib import Path
from typing import Any

import pytest

from workbench import runner
from workbench.config import PROJECT_ROOT, WORKSPACE_PLAYWRIGHT_CONFIG

FAILED_REPORT = {
    "suites": [
        {
            "specs": [
                {
                    "tests": [
                        {
                            "status": "unexpected",
                            "results": [
                                {
                                    "status": "failed",
                                    "duration": 50,
                                    "errors": [{"message": "Error: boom"}],
                                }
                            ],
                        }
                    ]
                }
            ]
        }
    ]
}


def _fake_popen(report: dict[str, Any] | None, stderr: str = "", hang: bool = False):
    calls: list[Any] = []

    class FakeProcess:
        pid = 4242

        def __init__(self, command: list[str], **kwargs: Any) -> None:
            self.command, self.kwargs = command, kwargs
            calls.append(self)

        def communicate(self, timeout: float | None = None) -> tuple[str, str]:
            if hang:
                raise subprocess.TimeoutExpired(self.command, timeout or 0)
            if report is not None:
                out = Path(self.kwargs["env"]["PLAYWRIGHT_JSON_OUTPUT_FILE"])
                out.write_text(json.dumps(report), encoding="utf-8")
            return "", stderr

    return FakeProcess, calls


@pytest.fixture(autouse=True)
def _workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WORKBENCH_WORKSPACE", str(tmp_path / "ws"))


def test_command_uses_the_workspace_config_and_the_json_reporter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake, calls = _fake_popen(FAILED_REPORT)
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    spec = tmp_path / "specs" / "contact.spec.ts"

    runner.run_test(spec, tmp_path / "run", record_video=True)

    (call,) = calls
    assert call.command[:4] == [
        "npx",
        "playwright",
        "test",
        re.escape(str(spec.resolve())),
    ]
    assert call.command[call.command.index("--config") + 1] == str(
        WORKSPACE_PLAYWRIGHT_CONFIG
    )
    assert call.command[call.command.index("--output") + 1] == str(
        tmp_path / "run" / "test-results"
    )
    assert "--reporter=json" in call.command
    assert "--max-failures=1" in call.command  # heal only uses the first failure
    env = call.kwargs["env"]
    assert env["PLAYWRIGHT_JSON_OUTPUT_FILE"] == str(tmp_path / "run" / "report.json")
    assert env["WORKBENCH_SPECS_DIR"] == str(spec.resolve().parent)
    assert env["WORKBENCH_RECORD_VIDEO"] == "1"
    assert str(PROJECT_ROOT / "node_modules") in env["NODE_PATH"].split(os.pathsep)
    assert call.kwargs["start_new_session"] is True


def test_report_is_parsed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake, _ = _fake_popen(FAILED_REPORT)
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    result = runner.run_test(tmp_path / "a.spec.ts", tmp_path / "run")
    assert result.status == "failed"
    assert result.error_message == "Error: boom"


def test_default_run_folder_is_inside_the_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake, calls = _fake_popen(FAILED_REPORT)
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    runner.run_test(tmp_path / "a.spec.ts")
    output = Path(calls[0].command[calls[0].command.index("--output") + 1])
    assert output.parent.parent == (tmp_path / "ws" / "runs").resolve()


def test_missing_report_is_an_error_that_keeps_stderr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake, _ = _fake_popen(None, stderr="Error: No tests found")
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    result = runner.run_test(tmp_path / "a.spec.ts", tmp_path / "run")
    assert result.status == "error"
    assert "No tests found" in result.error_message


def test_missing_npx_is_an_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def no_npx(*_args: Any, **_kwargs: Any) -> None:
        raise FileNotFoundError("npx")

    monkeypatch.setattr(runner.subprocess, "Popen", no_npx)
    result = runner.run_test(tmp_path / "a.spec.ts", tmp_path / "run")
    assert result.status == "error"
    assert "npx" in result.error_message


def test_cancel_stops_the_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake, _ = _fake_popen(None, hang=True)
    stopped: list[Any] = []
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    monkeypatch.setattr(runner, "_stop", stopped.append)
    cancel = threading.Event()
    cancel.set()

    result = runner.run_test(tmp_path / "a.spec.ts", tmp_path / "run", cancel=cancel)

    assert result.status == "cancelled"
    assert len(stopped) == 1


def test_timeout_stops_the_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake, _ = _fake_popen(None, hang=True)
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    monkeypatch.setattr(runner, "_stop", lambda _proc: None)
    result = runner.run_test(tmp_path / "a.spec.ts", tmp_path / "run", timeout_s=0)
    assert result.status == "timed_out"


def test_spec_path_is_escaped_for_playwrights_regex_filter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake, calls = _fake_popen(FAILED_REPORT)
    monkeypatch.setattr(runner.subprocess, "Popen", fake)
    spec = tmp_path / "specs (v2)" / "c++.spec.ts"

    runner.run_test(spec, tmp_path / "run")

    argument = calls[0].command[3]
    assert argument == re.escape(str(spec.resolve()))
    assert re.fullmatch(argument, str(spec.resolve()))
    assert "\\(v2\\)" in argument and "c\\+\\+" in argument
