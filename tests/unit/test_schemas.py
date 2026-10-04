"""
Unit tests for all Pydantic schemas.

Covers: field validation, coercion, Pydantic parsing, serialization,
and the parse_llm_response() integration point.
"""

import json
import unittest

from pydantic import ValidationError

from workbench.llm.parsing import parse_llm_response
from workbench.models.generate import GenerationResult
from workbench.models.heal import HealingAction, HealingAnalysis
from workbench.models.shared import FailureType, RunResult

# ---------------------------------------------------------------------------
# RunResult
# ---------------------------------------------------------------------------


class TestRunResult(unittest.TestCase):
    def test_passed_only_for_status_passed(self):
        self.assertTrue(RunResult(status="passed").passed)
        for status in ("failed", "timed_out", "cancelled", "error"):
            self.assertFalse(RunResult(status=status).passed, status)

    def test_output_joins_error_and_streams(self):
        r = RunResult(status="failed", error_message="E", stdout="O", stderr="S")
        self.assertEqual(r.output, "E\nO\nS")

    def test_output_skips_empty_parts(self):
        self.assertEqual(RunResult(status="failed", stderr="S").output, "S")


# ---------------------------------------------------------------------------
# HealingAction — list coercion validator
# ---------------------------------------------------------------------------


class TestHealingAction(unittest.TestCase):
    def test_string_fields_accepted(self):
        a = HealingAction(original_code="old", fixed_code="new", description="desc")
        self.assertEqual(a.original_code, "old")

    def test_list_original_code_coerced_to_string(self):
        """LLMs sometimes return code as a list of lines."""
        a = HealingAction(
            original_code=["line1", "line2"],
            fixed_code="new",
            description="desc",
        )
        self.assertEqual(a.original_code, "line1\nline2")

    def test_list_fixed_code_coerced_to_string(self):
        a = HealingAction(
            original_code="old",
            fixed_code=["line1", "line2"],
            description="desc",
        )
        self.assertEqual(a.fixed_code, "line1\nline2")


# ---------------------------------------------------------------------------
# HealingAnalysis — structured LLM response schema
# ---------------------------------------------------------------------------


class TestHealingAnalysis(unittest.TestCase):
    def _valid_payload(self) -> dict:
        return {
            "failure_type": "TIMEOUT",
            "failure_summary": "Selector timed out",
            "hypothesis": "The selector changed",
            "confidence_score": 0.95,
            "reasoning_steps": ["step 1", "step 2"],
            "action_taken": {
                "original_code": "old",
                "fixed_code": "new",
                "description": "changed selector",
            },
        }

    def test_valid_payload_parses(self):
        a = HealingAnalysis(**self._valid_payload())
        self.assertEqual(a.failure_type, FailureType.TIMEOUT)
        self.assertAlmostEqual(a.confidence_score, 0.95)

    def test_confidence_clamped_above_1(self):
        payload = self._valid_payload()
        payload["confidence_score"] = 1.05
        a = HealingAnalysis(**payload)
        self.assertAlmostEqual(a.confidence_score, 1.0)

    def test_confidence_clamped_below_0(self):
        payload = self._valid_payload()
        payload["confidence_score"] = -0.1
        a = HealingAnalysis(**payload)
        self.assertAlmostEqual(a.confidence_score, 0.0)

    def test_single_string_step_coerced_to_list(self):
        payload = self._valid_payload()
        payload["reasoning_steps"] = "just one step"
        a = HealingAnalysis(**payload)
        self.assertEqual(a.reasoning_steps, ["just one step"])

    def test_failure_type_string_coercion(self):
        payload = self._valid_payload()
        payload["failure_type"] = "LOCATOR_DRIFT"
        a = HealingAnalysis(**payload)
        self.assertEqual(a.failure_type, FailureType.LOCATOR_DRIFT)

    def test_invalid_failure_type_raises(self):
        payload = self._valid_payload()
        payload["failure_type"] = "INVALID_TYPE_XYZ"
        with self.assertRaises(ValidationError):
            HealingAnalysis(**payload)

    def test_missing_required_field_raises(self):
        payload = self._valid_payload()
        del payload["hypothesis"]
        with self.assertRaises(ValidationError):
            HealingAnalysis(**payload)

    def test_unknown_failure_type_is_rejected(self):
        # An invalid failure_type in model output is an invalid reply; it is
        # never silently coerced to UNKNOWN.
        payload = self._valid_payload()
        payload["failure_type"] = "INVALID_TYPE_BLAH"
        with self.assertRaises(ValueError):
            parse_llm_response(json.dumps(payload), HealingAnalysis)


# ---------------------------------------------------------------------------
# GenerationResult
# ---------------------------------------------------------------------------


class TestGenerationResult(unittest.TestCase):
    def test_valid_code_accepted(self):
        code = "import { test } from '@playwright/test';\ntest('foo', async () => {});"
        r = GenerationResult(code=code)
        self.assertEqual(r.code, code.strip())

    def test_empty_code_raises(self):
        with self.assertRaises(ValidationError):
            GenerationResult(code="")

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValidationError):
            GenerationResult(code="   \n  ")

    def test_code_is_stripped(self):
        r = GenerationResult(code="  const x = 1;  ")
        self.assertEqual(r.code, "const x = 1;")

    def test_has_playwright_import_true(self):
        r = GenerationResult(code="import { test } from '@playwright/test';")
        self.assertTrue(r.has_playwright_import)

    def test_has_playwright_import_false(self):
        r = GenerationResult(code="const x = 1;")
        self.assertFalse(r.has_playwright_import)

    def test_has_test_block(self):
        r = GenerationResult(code="test('foo', async ({ page }) => {});")
        self.assertTrue(r.has_test_block)

    def test_line_count(self):
        r = GenerationResult(code="line1\nline2\nline3")
        self.assertEqual(r.line_count, 3)


# ---------------------------------------------------------------------------
# parse_llm_response — integration
# ---------------------------------------------------------------------------


class TestParseLlmResponse(unittest.TestCase):
    def _valid_json(self) -> str:
        return json.dumps(
            {
                "failure_type": "TIMEOUT",
                "failure_summary": "timed out",
                "hypothesis": "selector missing",
                "confidence_score": 0.9,
                "reasoning_steps": ["checked logs"],
                "action_taken": {
                    "original_code": "old",
                    "fixed_code": "new",
                    "description": "fix",
                },
            }
        )

    def test_clean_json_parses(self):
        result = parse_llm_response(self._valid_json(), HealingAnalysis)
        self.assertEqual(result.failure_type, FailureType.TIMEOUT)

    def test_markdown_fenced_json_parses(self):
        fenced = f"Here is the analysis:\n\n```json\n{self._valid_json()}\n```"
        result = parse_llm_response(fenced, HealingAnalysis)
        self.assertEqual(result.failure_type, FailureType.TIMEOUT)

    def test_json_with_surrounding_text_parses(self):
        surrounded = (
            f"Sure! Here you go:\n{self._valid_json()}\nLet me know if you need more."
        )
        result = parse_llm_response(surrounded, HealingAnalysis)
        self.assertEqual(result.failure_type, FailureType.TIMEOUT)

    def test_empty_response_raises(self):
        with self.assertRaises(ValueError):
            parse_llm_response("", HealingAnalysis)

    def test_invalid_json_raises(self):
        with self.assertRaises(ValueError):
            parse_llm_response("this is not json at all", HealingAnalysis)

    def test_wrong_schema_raises(self):
        """Valid JSON but wrong shape should raise ValueError."""
        wrong = json.dumps({"foo": "bar"})
        with self.assertRaises(ValueError):
            parse_llm_response(wrong, HealingAnalysis)

    def test_confidence_clamping_via_parser(self):
        """Over-confident LLM (1.05) should be clamped to 1.0."""
        payload = json.loads(self._valid_json())
        payload["confidence_score"] = 1.05
        result = parse_llm_response(json.dumps(payload), HealingAnalysis)
        self.assertAlmostEqual(result.confidence_score, 1.0)

    def test_null_or_non_numeric_confidence_is_a_validation_error(self):
        """A null or list confidence is a ValueError, never a TypeError."""
        for bad in (None, [1]):
            with self.subTest(confidence=bad):
                payload = json.loads(self._valid_json())
                payload["confidence_score"] = bad
                with self.assertRaises(ValueError):
                    parse_llm_response(json.dumps(payload), HealingAnalysis)

    def test_list_code_coercion_via_parser(self):
        """LLM returns original_code as list — should be coerced to string."""
        payload = json.loads(self._valid_json())
        payload["action_taken"]["original_code"] = ["line1", "line2"]
        result = parse_llm_response(json.dumps(payload), HealingAnalysis)
        self.assertEqual(result.action_taken.original_code, "line1\nline2")


if __name__ == "__main__":
    unittest.main()
