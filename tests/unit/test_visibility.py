"""
Stage 3 — Visibility unit tests.

Covers:
  HealingDecision.to_markdown()   — Evidence Context section rendered
  GenerationDecision.to_markdown() — Context Snapshot section expanded
  emit_artifacts()                 — one file written, no execution_timeline
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from workbench.models.artifacts import ContextSnapshot
from workbench.models.generate import GenerationDecision
from workbench.models.heal import (
    Evidence,
    HealingAction,
    HealingAnalysis,
    HealingDecision,
)
from workbench.models.shared import FailureType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_action() -> HealingAction:
    return HealingAction(original_code="old", fixed_code="new", description="fix")


def _evidence_with_context() -> Evidence:
    return Evidence(
        error_log="Error: locator #btn not found",
        dom_snippet="<div><button id='btn'>Click</button></div>",
        accessibility_tree="button[name=Click]",
        locator_candidates=["#btn", "button >> text=Click", "[data-testid=submit]"],
        console_errors=["TypeError: cannot read property 'x' of undefined"],
    )


def _evidence_no_context() -> Evidence:
    return Evidence(error_log="Timeout 30000ms exceeded")


def _make_healing_decision(evidence: Evidence) -> HealingDecision:
    analysis = HealingAnalysis(
        failure_type=FailureType.LOCATOR_DRIFT,
        failure_summary="Locator drifted",
        hypothesis="Update selector",
        confidence_score=0.9,
        reasoning_steps=["step 1"],
        action_taken=_minimal_action(),
    )
    return HealingDecision.from_analysis(
        test_file="tests/e2e/click.spec.ts",
        analysis=analysis,
        evidence=evidence,
    )


def _make_generation_decision(snapshot: ContextSnapshot | None) -> GenerationDecision:
    return GenerationDecision(
        url="https://example.com",
        story="Login and verify",
        code="test('login', async ({page}) => {});",
        line_count=1,
        context_snapshot=snapshot,
    )


# ---------------------------------------------------------------------------
# HealingDecision — Evidence Context section (H3)
# ---------------------------------------------------------------------------


class TestHealingDecisionEvidenceContext(unittest.TestCase):
    """to_markdown() renders the Evidence Context section from Evidence fields."""

    def test_section_header_present(self):
        md = _make_healing_decision(_evidence_with_context()).to_markdown()
        self.assertIn("## Evidence Context", md)

    def test_dom_snippet_rendered(self):
        md = _make_healing_decision(_evidence_with_context()).to_markdown()
        self.assertIn("<button id='btn'>", md)

    def test_accessibility_tree_rendered(self):
        md = _make_healing_decision(_evidence_with_context()).to_markdown()
        self.assertIn("button[name=Click]", md)

    def test_locator_candidates_rendered(self):
        md = _make_healing_decision(_evidence_with_context()).to_markdown()
        self.assertIn("#btn", md)
        self.assertIn("button >> text=Click", md)
        self.assertIn("[data-testid=submit]", md)

    def test_console_errors_rendered(self):
        md = _make_healing_decision(_evidence_with_context()).to_markdown()
        self.assertIn("TypeError: cannot read property", md)

    def test_no_page_context_shows_placeholder(self):
        md = _make_healing_decision(_evidence_no_context()).to_markdown()
        self.assertIn("*(no page context collected)*", md)

    def test_dom_excerpt_capped_at_500_chars(self):
        long_dom = "<div>" + "x" * 1000 + "</div>"
        ev = Evidence(error_log="err", dom_snippet=long_dom)
        md = _make_healing_decision(ev).to_markdown()
        # The excerpt in the report should not contain more than 500 chars of dom
        # (plus the surrounding fenced block markers)
        dom_block_start = md.find("```html\n") + len("```html\n")
        dom_block_end = md.find("\n```", dom_block_start)
        dom_in_md = md[dom_block_start:dom_block_end]
        self.assertLessEqual(len(dom_in_md), 600)  # some slack for replaced backticks

    def test_locator_candidates_capped_at_10(self):
        ev = Evidence(
            error_log="err",
            locator_candidates=[f"#cand{i}" for i in range(20)],
        )
        md = _make_healing_decision(ev).to_markdown()
        # Only first 10 should appear
        self.assertIn("#cand9", md)
        self.assertNotIn("#cand10", md)


# ---------------------------------------------------------------------------
# GenerationDecision — Context Snapshot section (H3)
# ---------------------------------------------------------------------------


class TestGenerationDecisionContextSnapshot(unittest.TestCase):
    """to_markdown() renders the Context Snapshot section from ContextSnapshot."""

    def _snap(self) -> ContextSnapshot:
        return ContextSnapshot(
            url="https://example.com",
            html="<html><body><button>Go</button></body></html>",
            accessibility_tree="button[name=Go]",
            locator_candidates=["button >> text=Go", "#go-btn"],
            console_errors=["ReferenceError: x is not defined"],
        )

    def test_section_header_present(self):
        md = _make_generation_decision(self._snap()).to_markdown()
        self.assertIn("## Context Snapshot", md)

    def test_dom_rendered(self):
        md = _make_generation_decision(self._snap()).to_markdown()
        self.assertIn("<button>Go</button>", md)

    def test_accessibility_tree_rendered(self):
        md = _make_generation_decision(self._snap()).to_markdown()
        self.assertIn("button[name=Go]", md)

    def test_locator_candidates_rendered(self):
        md = _make_generation_decision(self._snap()).to_markdown()
        self.assertIn("button >> text=Go", md)
        self.assertIn("#go-btn", md)

    def test_console_errors_rendered(self):
        md = _make_generation_decision(self._snap()).to_markdown()
        self.assertIn("ReferenceError: x is not defined", md)

    def test_no_snapshot_shows_placeholder(self):
        md = _make_generation_decision(None).to_markdown()
        self.assertIn("*(no page context captured)*", md)

    def test_snapshot_id_rendered(self):
        d = GenerationDecision(
            url="https://example.com",
            story="test",
            code="test('t', () => {});",
            line_count=1,
            context_snapshot_id="abc123def456",
        )
        md = d.to_markdown()
        self.assertIn("abc123def456", md)


# ---------------------------------------------------------------------------
# emit_artifacts() — one file, no execution_timeline (M2)
# ---------------------------------------------------------------------------


class TestEmitArtifactsSingleFile(unittest.TestCase):
    """emit_artifacts() writes exactly one healing_decision_*.json file."""

    def _emit(self, tmpdir: Path):
        from workbench.heal.artifact_store import emit_artifacts
        from workbench.models.heal import ExecutionTimeline

        decision = _make_healing_decision(_evidence_no_context())
        timeline = ExecutionTimeline()
        timeline.add_step("Start", "Session started")
        with patch("workbench.heal.artifact_store.ARTIFACTS_DIR", tmpdir):
            emit_artifacts(decision, timeline)

    def test_exactly_one_file_written(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._emit(Path(tmpdir))
            files = list(Path(tmpdir).glob("*.json"))
            self.assertEqual(len(files), 1)

    def test_file_is_healing_decision(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._emit(Path(tmpdir))
            files = list(Path(tmpdir).glob("healing_decision_*.json"))
            self.assertEqual(len(files), 1)

    def test_no_execution_timeline_written(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._emit(Path(tmpdir))
            files = list(Path(tmpdir).glob("execution_timeline_*.json"))
            self.assertEqual(len(files), 0)


if __name__ == "__main__":
    unittest.main()
