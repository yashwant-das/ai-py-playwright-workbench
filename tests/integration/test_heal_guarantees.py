"""S3 and S4 against a real Chromium, with a scripted in-process model."""

import json
from pathlib import Path
from typing import Any

from tests.integration.conftest import SITE_URL
from workbench.config import specs_dir
from workbench.heal import HealRequest, heal
from workbench.llm.chat import ChatReply

DRIFTED = f"""import {{ test, expect }} from "@playwright/test";

test("Submit the contact form", async ({{ page }}) => {{
  await page.goto("{SITE_URL}");
  await page.getByLabel("Name").fill("Ada");
  await page.locator("#submit-btn").click({{ timeout: 3000 }});
  await expect(page.getByRole("status")).toHaveText("Submitted");
}});
"""
WRONG_EXPECTATION = DRIFTED.replace(
    'page.locator("#submit-btn")', 'page.getByRole("button", { name: "Submit" })'
).replace('toHaveText("Submitted")', 'toHaveText("Order placed", { timeout: 2000 })')


def _analysis(failure_type: str, original: str = "", fixed: str = "") -> str:
    return json.dumps(
        {
            "failure_type": failure_type,
            "failure_summary": "s",
            "hypothesis": "h",
            "confidence_score": 0.9,
            "reasoning_steps": ["r"],
            "action_taken": {
                "original_code": original,
                "fixed_code": fixed,
                "description": "d",
                "repair_strategy": "selector_replace",
            },
        }
    )


class ScriptedModel:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def chat(self, messages: list[dict[str, str]], **_: Any) -> ChatReply:
        self.prompts.append(messages[1]["content"])
        return ChatReply(content=self.reply, model="scripted", provider="test")


def _spec(name: str, code: str) -> Path:
    path = specs_dir() / name
    path.write_text(code, encoding="utf-8")
    return path


def test_evidence_is_the_page_at_the_moment_of_failure(site: str) -> None:
    model = ScriptedModel(
        _analysis(
            "LOCATOR_DRIFT",
            'page.locator("#submit-btn")',
            'page.getByRole("button", { name: "Submit" })',
        )
    )
    report = heal(HealRequest(spec_path=_spec("drift.spec.ts", DRIFTED)), model=model)

    assert report.status == "healed", report.model_dump_json(indent=2)
    evidence = report.attempts[0].evidence
    assert evidence is not None and evidence.source == "error_context"
    snapshot_section = model.prompts[0].split("## Page snapshot at failure\n", 1)[1]
    # The name typed before the failure is in the snapshot: this is mid-test state,
    # not a fresh load of the start page.
    assert 'textbox "Name"' in snapshot_section and "Ada" in snapshot_section
    video = report.attempts[0].rerun.video_path  # type: ignore[union-attr]
    assert video and video.endswith(".webm") and Path(video).is_file()


def test_suspected_app_bug_leaves_the_test_alone(site: str) -> None:
    spec = _spec("order.spec.ts", WRONG_EXPECTATION)
    report = heal(
        HealRequest(spec_path=spec),
        model=ScriptedModel(_analysis("POTENTIAL_APP_DEFECT")),
    )

    assert report.status == "app_defect_suspected"
    assert [a.outcome for a in report.attempts] == ["app_defect"]
    assert report.attempts[0].rerun is None
    assert spec.read_text(encoding="utf-8") == WRONG_EXPECTATION
