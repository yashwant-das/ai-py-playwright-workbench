"""Design tokens match Figma, assets are present, and the base layout is accessible."""

import re

from workbench import config
from workbench.web.templating import templates

# The 30 colour variables in the Figma file (eL5DUZmc85ESpusNSmxDkA).
FIGMA_COLOURS = {
    "accent-primary": "#18181b",
    "text-primary": "#18181b",
    "text-secondary": "#52525b",
    "text-tertiary": "#8a8a93",
    "text-inverse": "#ffffff",
    "bg-canvas": "#f7f7f5",
    "bg-surface": "#ffffff",
    "bg-subtle": "#f1f1ee",
    "border-default": "#e4e4df",
    "border-strong": "#d1d1cb",
    "status-pass": "#15803d",
    "status-pass-bg": "#e7f4eb",
    "status-fail": "#b91c1c",
    "status-fail-bg": "#fbeaea",
    "status-run": "#1d4ed8",
    "status-run-bg": "#e8eefd",
    "status-warn": "#b45309",
    "status-warn-bg": "#fcf1e1",
    "code-bg": "#111113",
    "code-text": "#e4e4e7",
    "code-muted": "#71717a",
    "code-gutter": "#18181b",
    "code-border": "#27272a",
    "code-string": "#a5d6ff",
    "code-keyword": "#ff7b72",
    "code-fn": "#d2a8ff",
    "diff-add-text": "#7ee2a8",
    "diff-add-bg": "#11291d",
    "diff-del-text": "#ffa198",
    "diff-del-bg": "#2e1517",
}
TYPE_STYLES = [
    "title-page",
    "title-section",
    "body",
    "body-small",
    "label",
    "label-caps",
    "mono-code",
    "mono-small",
]


def _css(name: str) -> str:
    return (config.STATIC_DIR / "css" / name).read_text(encoding="utf-8")


def test_tokens_mirror_the_figma_colours_one_to_one() -> None:
    declared = dict(
        re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-f]{6});", _css("tokens.css"))
    )
    assert declared == FIGMA_COLOURS


def test_tokens_define_the_eight_type_styles() -> None:
    tokens = _css("tokens.css")
    for style in TYPE_STYLES:
        assert f"--type-{style}:" in tokens


def test_fonts_are_self_hosted_woff2() -> None:
    for name in ("inter-400", "inter-500", "inter-600", "jetbrains-mono-400"):
        assert (config.STATIC_DIR / "fonts" / f"{name}.woff2").read_bytes()[
            :4
        ] == b"wOF2"
    assert (config.STATIC_DIR / "fonts" / "LICENSE-inter.txt").is_file()
    assert (config.STATIC_DIR / "fonts" / "LICENSE-jetbrains-mono.txt").is_file()


def test_htmx_is_vendored_with_its_version_in_the_name() -> None:
    vendor = config.STATIC_DIR / "vendor"
    assert (vendor / "htmx-2.0.11.min.js").stat().st_size > 40_000
    assert "sse-connect" in (vendor / "htmx-ext-sse-2.2.4.js").read_text(
        encoding="utf-8"
    )


def test_base_layout_has_landmarks_and_marks_the_current_page() -> None:
    html = templates.get_template("base.html").render(page="generate")
    assert '<header class="header">' in html
    assert '<nav class="nav" aria-label="Pages">' in html
    assert '<main class="main" id="main"' in html
    assert "<aside" in html
    assert '<a href="/generate" aria-current="page">Generate</a>' in html
    assert 'aria-live="polite"' in html
    assert "/static/vendor/htmx-2.0.11.min.js" in html
    assert "/static/vendor/htmx-ext-sse-2.2.4.js" in html


def test_icon_macro_renders_decorative_and_labelled_icons() -> None:
    module = templates.env.get_template("partials/icons.html").module
    decorative = str(module.icon("check"))  # type: ignore[attr-defined]
    labelled = str(module.icon("x", 20, "Failed"))  # type: ignore[attr-defined]
    assert 'aria-hidden="true"' in decorative
    assert 'role="img" aria-label="Failed"' in labelled
    assert 'width="20"' in labelled


def test_meter_fill_is_a_block_so_its_width_applies() -> None:
    rule = re.search(r"\.meter__fill\s*\{([^}]*)\}", _css("app.css"))
    assert rule is not None
    assert re.search(r"display:\s*block", rule.group(1))
