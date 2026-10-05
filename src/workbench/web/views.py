"""Turns report data into what the templates show: times, sizes, code and badges."""

import difflib
import re
from html import escape

from pygments.lexers import TypeScriptLexer
from pygments.token import Comment, Keyword, Name, String, _TokenType

from workbench.models.web import Badge, DiffRow, OutcomeBadge, StepInfo

HEAL_STEPS: tuple[StepInfo, ...] = (
    StepInfo(name="run", title="Run the test", description="npx playwright test"),
    StepInfo(
        name="evidence",
        title="Collect evidence",
        description="Error context, screenshot and page snapshot",
    ),
    StepInfo(name="diagnose", title="Diagnose", description="Ask the model what broke"),
    StepInfo(
        name="repair", title="Repair", description="Apply the fix to the syntax tree"
    ),
    StepInfo(name="verify", title="Verify", description="Re-run the test"),
)
GENERATE_STEPS: tuple[StepInfo, ...] = (
    StepInfo(
        name="context",
        title="Load page context",
        description="Accessibility snapshot and locator candidates",
    ),
    StepInfo(name="model", title="Ask the model", description="Write the spec"),
    StepInfo(name="execute", title="Run the test", description="Runs after generation"),
)
STEP_INFO: dict[str, StepInfo] = {
    step.name: step for step in (*HEAL_STEPS, *GENERATE_STEPS)
}

HEAL_BADGES: dict[str, Badge] = {
    "healed": Badge(variant="pass", label="Healed"),
    "not_healed": Badge(variant="fail", label="Not healed"),
    "app_defect_suspected": Badge(variant="warn", label="Likely app bug"),
    "nothing_to_heal": Badge(variant="pass", label="Nothing to heal"),
    "cancelled": Badge(variant="neutral", label="Cancelled"),
    "error": Badge(variant="fail", label="Error"),
}
GENERATE_BADGES: dict[str, Badge] = {
    "passed": Badge(variant="pass", label="Passed"),
    "failed": Badge(variant="fail", label="Run failed"),
    "not_run": Badge(variant="neutral", label="Not run"),
    "cancelled": Badge(variant="neutral", label="Cancelled"),
    "error": Badge(variant="fail", label="Error"),
}
OUTCOME_BADGES: dict[str, OutcomeBadge] = {
    "healed": OutcomeBadge(variant="pass", label="Passed", title="Healed"),
    "rerun_failed": OutcomeBadge(variant="fail", label="Failed", title="Re-run failed"),
    "not_applied": OutcomeBadge(
        variant="warn", label="Not applied", title="Fix not applied"
    ),
    "invalid_reply": OutcomeBadge(
        variant="warn", label="Invalid reply", title="Invalid model reply"
    ),
    "app_defect": OutcomeBadge(variant="warn", label="Stopped", title="Likely app bug"),
    "cancelled": OutcomeBadge(variant="neutral", label="Cancelled", title="Cancelled"),
}

_LOCATOR = re.compile(r"\b(?:getBy[A-Z]\w*|locator)\((?:[^()]|\([^()]*\))*\)")
Token = tuple[_TokenType, str]


def format_duration(ms: int | None) -> str:
    """``2.4s`` under a minute, ``1m 05s`` above; ``–`` when unknown."""
    if ms is None:
        return "–"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rest = divmod(round(seconds), 60)
    return f"{minutes}m {rest:02d}s"


def format_size(chars: int) -> str:
    """A prompt section's size in kilobytes."""
    return f"{chars / 1024:.1f} KB"


def _neighbour(tokens: list[Token], index: int, step: int) -> str:
    index += step
    while 0 <= index < len(tokens):
        value = tokens[index][1]
        if value.strip():
            return value
        index += step
    return ""


def _css_class(tokens: list[Token], index: int) -> str:
    ttype = tokens[index][0]
    if ttype in Comment:
        return "mut"
    if ttype in String:
        return "str"
    # Pygments tags some method names (goto) as reserved words: a call wins.
    if _neighbour(tokens, index, 1).startswith("(") and (
        ttype in Name or _neighbour(tokens, index, -1) == "."
    ):
        return "fn"
    if ttype in Keyword:
        return "kw"
    return ""


def highlight_lines(code: str) -> list[str]:
    """One escaped HTML string per source line, with ``tok-*`` spans."""
    if not code:
        return []
    tokens: list[Token] = list(TypeScriptLexer(stripnl=False).get_tokens(code))
    lines: list[list[str]] = [[]]
    for index, (_, value) in enumerate(tokens):
        css = _css_class(tokens, index)
        for position, part in enumerate(value.split("\n")):
            if position:
                lines.append([])
            if part:
                text = escape(part, quote=False)
                lines[-1].append(
                    f'<span class="tok-{css}">{text}</span>' if css else text
                )
    return ["".join(parts) for parts in lines[: len(code.splitlines())]]


def diff_rows(old: str, new: str) -> list[DiffRow]:
    """The whole file with removed and added lines in place, numbered on both sides."""
    old_html, new_html = highlight_lines(old), highlight_lines(new)
    matcher = difflib.SequenceMatcher(
        a=old.splitlines(), b=new.splitlines(), autojunk=False
    )
    rows: list[DiffRow] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            rows += [
                DiffRow(kind="same", old_no=i + 1, new_no=j + 1, html=old_html[i])
                for i, j in zip(range(i1, i2), range(j1, j2), strict=True)
            ]
            continue
        rows += [
            DiffRow(kind="del", old_no=i + 1, new_no=None, html=old_html[i])
            for i in range(i1, i2)
        ]
        rows += [
            DiffRow(kind="add", old_no=None, new_no=j + 1, html=new_html[j])
            for j in range(j1, j2)
        ]
    return rows


def diff_counts(rows: list[DiffRow]) -> tuple[int, int]:
    """(added, removed) line counts."""
    return (
        sum(row.kind == "add" for row in rows),
        sum(row.kind == "del" for row in rows),
    )


def locators_in(code: str) -> list[str]:
    """The locator calls a spec uses, each once, in order of appearance."""
    return list(dict.fromkeys(_LOCATOR.findall(code)))
