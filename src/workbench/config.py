"""Filesystem locations used across the workbench.

Every module gets paths from here instead of counting parent directories,
so moving a module never breaks a path.
"""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]

PROMPTS_DIR = PACKAGE_DIR / "prompts"
AST_REPAIR_SCRIPT = PACKAGE_DIR / "heal" / "ast_repair.js"

# Runtime output. Phase 2 moves these into workspace/.
GENERATED_SPECS_DIR = PROJECT_ROOT / "tests" / "generated"
ARTIFACTS_DIR = PROJECT_ROOT / "tests" / "artifacts"
TEST_RESULTS_DIR = PROJECT_ROOT / "test-results"
