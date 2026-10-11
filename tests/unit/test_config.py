"""Paths in workbench.config must point at real files after the move."""

import json
import shutil
import subprocess

import pytest

from workbench import config


def test_project_root_is_the_repository() -> None:
    assert (config.PROJECT_ROOT / "pyproject.toml").is_file()
    assert (config.PROJECT_ROOT / "package.json").is_file()


def test_prompts_ship_inside_the_package() -> None:
    assert (config.PROMPTS_DIR / "manifest.json").is_file()
    assert (config.PROMPTS_DIR / "healer.md").is_file()
    assert (config.PROMPTS_DIR / "generator.md").is_file()
    assert not (config.PROMPTS_DIR / "vision.md").exists()


def test_ast_repair_script_ships_inside_the_package() -> None:
    assert config.AST_REPAIR_SCRIPT.is_file()
    assert config.AST_REPAIR_SCRIPT.parent == config.PACKAGE_DIR / "heal"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_ast_repair_script_resolves_ts_morph_from_the_package() -> None:
    payload = {
        "strategy": "selector_replace",
        "source": 'await page.locator("#old").click();\n',
        "original_code": 'page.locator("#old")',
        "fixed_code": 'page.locator("#new")',
    }
    proc = subprocess.run(
        ["node", str(config.AST_REPAIR_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
        cwd=config.PROJECT_ROOT,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["success"] is True
    assert "#new" in result["source"]
    assert "#old" not in result["source"]
