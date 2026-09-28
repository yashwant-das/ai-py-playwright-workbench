"""Tests for validate_file_path: files must stay inside the allowed directories."""

import os
import unittest

from src.utils.validation import ValidationError, validate_file_path


class TestValidateFilePath(unittest.TestCase):
    def test_accepts_file_inside_default_dir(self):
        result = validate_file_path(os.path.join("tests", "generated", "a.spec.ts"))
        self.assertTrue(
            result.endswith(os.path.join("tests", "generated", "a.spec.ts"))
        )
        self.assertTrue(os.path.isabs(result))

    def test_rejects_parent_traversal(self):
        with self.assertRaises(ValidationError):
            validate_file_path(os.path.join("tests", "generated", "..", "..", "x.ts"))

    def test_rejects_sibling_dir_sharing_the_prefix(self):
        with self.assertRaises(ValidationError):
            validate_file_path(os.path.join("tests", "generated_evil", "x.ts"))

    def test_rejects_the_allowed_dir_itself(self):
        with self.assertRaises(ValidationError):
            validate_file_path(os.path.join("tests", "generated"))

    def test_rejects_empty_path(self):
        with self.assertRaises(ValidationError):
            validate_file_path("")

    def test_custom_allowed_dirs(self):
        result = validate_file_path(
            os.path.join("benchmarks", "reports", "r.json"),
            allowed_dirs=["tests/generated", "benchmarks/reports"],
        )
        self.assertTrue(
            result.endswith(os.path.join("benchmarks", "reports", "r.json"))
        )


if __name__ == "__main__":
    unittest.main()
