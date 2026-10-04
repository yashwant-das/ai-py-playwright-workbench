"""
Code repair — AST-first with indentation-tolerant string replacement fallback.

Single responsibility: given the current file content and a HealingAction,
return the updated source and how it was changed.  No filesystem I/O — the
caller is responsible for writing the returned string.

Repair routing
--------------
1. If ``action.repair_strategy`` is anything other than
   ``STRING_REPLACE``, the ts-morph Node.js script (``src/workbench/heal/ast_repair.js``)
   is called via subprocess.  The script applies a structural TypeScript AST
   transformation and returns the modified source.

2. If the AST path is skipped, unavailable (Node.js not found), times out,
   or makes no changes, execution falls back to the two-strategy string path:

   a. **Exact string replacement** (fast path).
   b. **Normalized sliding-window** — strips leading whitespace before comparing,
      then re-indents the replacement to match the matched block's indentation.

Any fallback is logged as a WARNING so the engineering team can detect cases
where the LLM chose an AST strategy but the script couldn't apply it.
"""

import json
import logging
import subprocess

from workbench.config import AST_REPAIR_SCRIPT, PROJECT_ROOT
from workbench.environment import node_available
from workbench.models.heal import HealingAction, RepairResult, RepairStrategy

logger = logging.getLogger(__name__)

_AST_SCRIPT = AST_REPAIR_SCRIPT


# ── public entry point ────────────────────────────────────────────────────────


def apply_fix(code: str, action: HealingAction) -> RepairResult:
    """Apply the proposed change: AST first, text replacement as the fallback.

    Returns the new code and how it was changed; ``method`` is None when no
    strategy found the code to replace.
    """
    ast_unavailable = False
    if action.repair_strategy != RepairStrategy.STRING_REPLACE:
        if node_available():
            new_code = _apply_ast_fix(code, action)
            if new_code != code:
                return RepairResult(code=new_code, method="ast")
            logger.warning(
                "AST repair (%s) made no change; trying text replacement",
                action.repair_strategy.value,
            )
        else:
            ast_unavailable = True
            logger.warning("Node.js not found; using text replacement")
    new_code = _apply_string_fix(code, action)
    return RepairResult(
        code=new_code,
        method="text" if new_code != code else None,
        ast_unavailable=ast_unavailable,
    )


# ── AST path (ts-morph via Node.js subprocess) ────────────────────────────────


def _apply_ast_fix(current_code: str, action: HealingAction) -> str:
    """Call src/workbench/heal/ast_repair.js and return the modified source.

    Returns ``current_code`` unchanged on any subprocess or parsing failure.
    """
    payload = {
        "strategy": action.repair_strategy.value,
        "source": current_code,
        "original_code": action.original_code,
        "fixed_code": action.fixed_code,
    }

    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["node", str(_AST_SCRIPT)],  # noqa: S607 - node/npx resolved from PATH
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )

        if result.returncode != 0:
            logger.warning(
                "ast_repair.js exited with code %d: %s",
                result.returncode,
                result.stderr[:500],
            )
            return current_code

        output = json.loads(result.stdout)

        if not output.get("success"):
            logger.warning("AST repair failed: %s", output.get("error"))
            return current_code

        if output.get("changes", 0) == 0:
            logger.debug("AST repair made no changes (0 nodes matched)")
            return current_code

        logger.info(
            "AST repair (%s) applied %d change(s)",
            action.repair_strategy.value,
            output["changes"],
        )
        return str(output["source"])

    except subprocess.TimeoutExpired:
        logger.warning("ast_repair.js timed out after 30s")
        return current_code
    except FileNotFoundError:
        logger.warning(
            "Node.js not found; AST repair unavailable — falling back to string replacement"
        )
        return current_code
    except json.JSONDecodeError as exc:
        logger.warning("ast_repair.js returned invalid JSON: %s", exc)
        return current_code
    except Exception as exc:
        logger.warning("Unexpected AST repair error: %s", exc)
        return current_code


# ── string path — exact and normalized fallback when all AST strategies miss ──


def _apply_string_fix(current_code: str, action: HealingAction) -> str:
    """Apply the proposed fix using exact match with normalized fallback.

    Strategy 1 — exact string replacement.
    Strategy 2 — normalized sliding-window (indentation-tolerant).

    Returns ``current_code`` unchanged if neither strategy finds a match.
    """
    target = action.original_code
    replacement = action.fixed_code

    if not target or not replacement:
        return current_code

    # Strategy 1: exact string replacement
    if target in current_code and (
        len(replacement.splitlines()) == 1
        or (
            len(target.splitlines()) > 1
            and (len(target) - len(target.lstrip()))
            == (len(replacement) - len(replacement.lstrip()))
        )
    ):
        return current_code.replace(target, replacement)

    # Strategy 2: normalized line match (tolerates indentation drift in LLM output)
    def normalize_lines(text: str) -> list[str]:
        return [line.strip() for line in text.splitlines() if line.strip()]

    target_lines = normalize_lines(target)
    code_lines = current_code.splitlines()

    for i in range(len(code_lines) - len(target_lines) + 1):
        window = [line.strip() for line in code_lines[i : i + len(target_lines)]]
        if window == target_lines:
            # Infer base indentation from the first matched line
            base_indent = code_lines[i][
                : len(code_lines[i]) - len(code_lines[i].lstrip())
            ]

            # Determine the base indentation of the replacement block
            replacement_lines = replacement.splitlines()
            non_empty = [line for line in replacement_lines if line.strip()]
            rep_base = (
                len(non_empty[0]) - len(non_empty[0].lstrip()) if non_empty else 0
            )

            # Re-indent replacement to match the matched block's indentation
            indented: list[str] = []
            for r_line in replacement_lines:
                if not r_line.strip():
                    indented.append("")
                else:
                    rel = max(0, (len(r_line) - len(r_line.lstrip())) - rep_base)
                    indented.append(base_indent + (" " * rel) + r_line.lstrip())

            new_lines = code_lines[:i] + indented + code_lines[i + len(target_lines) :]
            return "\n".join(new_lines)

    logger.warning(
        "Target code not found in file (exact or normalized).\nTarget:\n%s", target
    )
    return current_code
