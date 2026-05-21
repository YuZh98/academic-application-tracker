# tests/test_ui.py
# Unit + static tests for the shared presentation module `ui.py`.
#
# ui.py exposes the design system (CSS tokens, dark-mode block) and a
# small set of pure-string helpers (status_pill, urgency_pill) plus
# imperative renderers (inject_global_styles, section_header,
# sidebar_about_block, accent_bar). The helpers are pure functions —
# tested directly without AppTest. The injection + page-presence checks
# use AST grep to pin the architectural rule that every Streamlit page
# must call inject_global_styles().

import ast
import re
from pathlib import Path
from unittest.mock import patch

import config
import ui

REPO_ROOT = Path(__file__).parent.parent
_PAGES_DIR = REPO_ROOT / "pages"
_APP_PY = REPO_ROOT / "app.py"


# ── status_pill ───────────────────────────────────────────────────────────────


class TestStatusPill:
    def test_returns_html_span(self) -> None:
        html = ui.status_pill(config.STATUS_SAVED)
        assert html.startswith("<span"), f"Pill must be a <span>, got: {html[:30]!r}"
        assert "</span>" in html

    def test_contains_status_label(self) -> None:
        for raw in config.STATUS_VALUES:
            html = ui.status_pill(raw)
            label = config.STATUS_LABELS[raw]
            assert label in html, (
                f"status_pill({raw!r}) must contain its UI label {label!r}; got {html!r}"
            )

    def test_carries_status_class(self) -> None:
        # Each pill must carry a class hook the stylesheet can target.
        # Class names must be stable per status — locked at "aat-pill aat-pill-<lowercase>".
        for raw in config.STATUS_VALUES:
            html = ui.status_pill(raw)
            assert "aat-pill" in html, f"Pill missing aat-pill class for {raw!r}: {html!r}"
            ui_label_slug = config.STATUS_LABELS[raw].lower()
            assert f"aat-pill-{ui_label_slug}" in html, (
                f"Pill must carry aat-pill-{ui_label_slug} for {raw!r}; got {html!r}"
            )

    def test_unknown_status_falls_back_to_neutral(self) -> None:
        # An unknown raw value (eg a renamed status the migration missed)
        # must render without raising and must NOT include a stale class.
        # The class slug must be exactly "neutral" — pinning this makes
        # the class-attribute injection guard machine-checkable, not
        # just a code comment.
        html = ui.status_pill("[NONEXISTENT]")
        assert "<span" in html
        assert "aat-pill aat-pill-neutral" in html

    def test_unknown_status_html_escapes_payload(self) -> None:
        # Defence in depth — the fallback path interpolates the raw
        # status into HTML; a value containing '<' must NOT punch
        # through the markup.
        html = ui.status_pill("[<script>alert(1)</script>]")
        assert "<script>" not in html
        # Browsers see the escaped entity, not a live tag.
        assert "&lt;script&gt;" in html or "&lt;" in html


# ── urgency_pill ──────────────────────────────────────────────────────────────


class TestUrgencyPill:
    def test_none_returns_em_dash_placeholder(self) -> None:
        # 'no deadline at all' renders as the em-dash glyph wrapped in
        # the neutral pill class — distinct from 'far-future deadline'
        # which renders as an empty/muted band.
        html = ui.urgency_pill(None)
        assert config.EM_DASH in html

    def test_urgent_band(self) -> None:
        # days_away <= DEADLINE_URGENT_DAYS → urgent class.
        for d in [config.DEADLINE_URGENT_DAYS, 0, -1, -100]:
            html = ui.urgency_pill(d)
            assert "aat-urgent" in html, (
                f"urgency_pill({d}) must carry aat-urgent (≤ {config.DEADLINE_URGENT_DAYS}d band)"
            )

    def test_warn_band(self) -> None:
        # past urgent, ≤ DEADLINE_ALERT_DAYS → warn class.
        d = config.DEADLINE_URGENT_DAYS + 1
        html = ui.urgency_pill(d)
        assert "aat-warn" in html
        assert "aat-urgent" not in html

    def test_calm_band(self) -> None:
        # beyond alert → muted class, no warn/urgent.
        d = config.DEADLINE_ALERT_DAYS + 5
        html = ui.urgency_pill(d)
        assert "aat-urgent" not in html
        assert "aat-warn" not in html
        assert "aat-pill" in html

    def test_negative_is_urgent_invariant(self) -> None:
        # Mirrors the urgency_glyph negative-day invariant in config.py:
        # past-due deadlines must remain in the urgent band, not silently
        # decay to warn/muted.
        assert "aat-urgent" in ui.urgency_pill(-1)
        assert "aat-urgent" in ui.urgency_pill(-365)


# ── inject_global_styles ──────────────────────────────────────────────────────


class TestInjectGlobalStyles:
    def test_emits_style_block(self) -> None:
        # The function must call st.markdown with a stylesheet payload.
        # We capture the call by patching the imported reference inside
        # the module so we don't depend on AppTest's element tree.
        with patch.object(ui.st, "markdown") as mock_md:
            ui.inject_global_styles()
            assert mock_md.called, "inject_global_styles must call st.markdown"
            # First positional arg is the CSS string.
            css = mock_md.call_args.args[0]
            assert "<style>" in css and "</style>" in css

    def test_defines_design_tokens(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.inject_global_styles()
            css = mock_md.call_args.args[0]
            # Token plumbing (:root vars) must be present — they are the
            # contract the rest of the stylesheet hangs off.
            assert ":root" in css
            assert "--aat-" in css

    def test_includes_dark_mode_block(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.inject_global_styles()
            css = mock_md.call_args.args[0]
            assert "prefers-color-scheme: dark" in css, (
                "Dark mode block must be present so OS-level appearance is honoured"
            )

    def test_unsafe_allow_html_kwarg(self) -> None:
        # Streamlit requires unsafe_allow_html=True for raw CSS injection.
        with patch.object(ui.st, "markdown") as mock_md:
            ui.inject_global_styles()
            kwargs = mock_md.call_args.kwargs
            assert kwargs.get("unsafe_allow_html") is True


# ── Page injection presence (static AST check) ────────────────────────────────


def _module_calls_inject(py_path: Path) -> bool:
    """True if the given .py file contains a call to ui.inject_global_styles().

    AST walk so a string match inside a comment doesn't lie."""
    tree = ast.parse(py_path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "inject_global_styles":
            return True
    return False


class TestPagesInjectStyles:
    """Pin GUIDELINES §UI-1: every Streamlit entrypoint calls
    ui.inject_global_styles() so the design system is consistent."""

    def test_app_py_injects(self) -> None:
        assert _module_calls_inject(_APP_PY), (
            "app.py must call ui.inject_global_styles() at module top"
        )

    def test_every_page_injects(self) -> None:
        for page in sorted(_PAGES_DIR.glob("*.py")):
            assert _module_calls_inject(page), f"{page.name} must call ui.inject_global_styles()"


def _module_calls(py_path: Path, attr_name: str) -> bool:
    """True if ``py_path`` contains a call to ``<something>.attr_name(...)``.

    AST walk so a string match inside a comment doesn't lie. Used by the
    sidebar-block pin tests below."""
    tree = ast.parse(py_path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == attr_name:
            return True
    return False


class TestPagesCallSidebarAbout:
    """Pin the sidebar-cohesion rule: every page (dashboard + 4 pages)
    must call ``ui.sidebar_about_block`` so the About expander appears
    in the sidebar regardless of which page the user lands on.

    Streamlit re-renders the entire sidebar on every page rerun, so a
    page that forgets the call shows an empty About slot — breaking
    the design-system promise that the shell is the same everywhere."""

    def test_app_py_calls(self) -> None:
        assert _module_calls(_APP_PY, "sidebar_about_block"), (
            "app.py must call ui.sidebar_about_block()"
        )

    def test_every_page_calls(self) -> None:
        for page in sorted(_PAGES_DIR.glob("*.py")):
            assert _module_calls(page, "sidebar_about_block"), (
                f"{page.name} must call ui.sidebar_about_block() — "
                "otherwise the About expander vanishes on this page"
            )


class TestPagesCallShortcuts:
    """Pin per-page shortcuts-block consistency for the same reason as
    the About expander above."""

    def test_app_py_calls(self) -> None:
        assert _module_calls(_APP_PY, "sidebar_shortcuts_block"), (
            "app.py must call ui.sidebar_shortcuts_block()"
        )

    def test_every_page_calls(self) -> None:
        for page in sorted(_PAGES_DIR.glob("*.py")):
            assert _module_calls(page, "sidebar_shortcuts_block"), (
                f"{page.name} must call ui.sidebar_shortcuts_block()"
            )


class TestSidebarShortcutsBlock:
    def test_renders_keyboard_hints(self) -> None:
        from unittest.mock import patch

        with (
            patch.object(ui.st, "sidebar") as mock_sidebar,
            patch.object(ui.st, "markdown") as mock_md,
        ):
            mock_sidebar.expander.return_value.__enter__ = lambda s: s
            mock_sidebar.expander.return_value.__exit__ = lambda s, *a: False
            ui.sidebar_shortcuts_block()
            payload = " ".join(c.args[0] for c in mock_md.call_args_list if c.args)
            assert "Rerun" in payload or "rerun" in payload, (
                "Shortcuts block must mention the rerun keybinding"
            )


# ── Editorial-brutalist additions (v0.14.0) ──────────────────────────────────


class TestHeroGreeting:
    """Editorial hero: time-of-day serif italic greeting + mono date
    stamp. Bands chosen so a 7am check-in reads "morning", a 2pm
    check-in reads "afternoon", an 8pm check-in reads "evening", and a
    2am check-in (insomniac PhD students happen) still reads "evening"
    rather than the technically-correct-but-unfriendly "morning"."""

    def test_morning_greeting(self) -> None:
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.hero_greeting(now=datetime(2026, 5, 20, 8, 0))
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "Good morning" in payload

    def test_afternoon_greeting(self) -> None:
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.hero_greeting(now=datetime(2026, 5, 20, 14, 0))
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "Good afternoon" in payload

    def test_evening_greeting(self) -> None:
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.hero_greeting(now=datetime(2026, 5, 20, 20, 0))
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "Good evening" in payload

    def test_pre_dawn_reads_as_evening(self) -> None:
        # 2am should still read "evening" — the band-edge is at 5am.
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.hero_greeting(now=datetime(2026, 5, 20, 2, 0))
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "Good evening" in payload

    def test_stamp_carries_weekday_and_date(self) -> None:
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.hero_greeting(now=datetime(2026, 5, 20, 9, 0))
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "WEDNESDAY" in payload  # 2026-05-20 is a Wednesday
            assert "MAY" in payload
            assert "2026" in payload

    def test_name_prefix_when_supplied(self) -> None:
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.hero_greeting(name="Yu", now=datetime(2026, 5, 20, 9, 0))
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "YU" in payload

    def test_hero_html_escapes_payload(self) -> None:
        # Defence in depth — `name` is interpolated into HTML.
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.hero_greeting(
                name="<script>alert(1)</script>",
                now=datetime(2026, 5, 20, 9, 0),
            )
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "<script>" not in payload
            assert "&lt;" in payload


class TestNumberedSection:
    def test_emits_two_digit_number(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.numbered_section(1, "Deadlines")
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "01" in payload, "Number must be zero-padded to 2 digits"
            assert "Deadlines" in payload

    def test_double_digit_number(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.numbered_section(12, "Far Section")
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "12" in payload

    def test_html_escapes_payload(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.numbered_section(1, "<script>x</script>")
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "<script>" not in payload
            assert "&lt;" in payload


class TestAccentBarShape:
    """The editorial-brutalist accent bar replaces the prior gradient
    with three solid colour blocks (vermilion, cobalt, citron). Pin
    the shape so a future re-styling doesn't quietly drop the Bauhaus
    look without an explicit decision."""

    def test_emits_three_colour_blocks(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.accent_bar()
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "aat-accent-block-1" in payload
            assert "aat-accent-block-2" in payload
            assert "aat-accent-block-3" in payload


class TestColophon:
    """Editorial masthead strip at the very top of every page."""

    def test_carries_section_name(self) -> None:
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.colophon("Dashboard", now=datetime(2026, 5, 20))
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "DASHBOARD" in payload

    def test_carries_app_name(self) -> None:
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.colophon("Opportunities", now=datetime(2026, 5, 20))
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "Academic Application Tracker" in payload

    def test_issue_stamp_includes_month_year(self) -> None:
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.colophon("Dashboard", now=datetime(2026, 5, 20))
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "MAY" in payload
            assert "2026" in payload

    def test_html_escapes_section(self) -> None:
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.colophon("<script>x</script>", now=datetime(2026, 5, 20))
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "<script>" not in payload
            assert "&lt;" in payload


class TestPagesCallColophon:
    """Every entrypoint must call ui.colophon() so the editorial
    masthead is present on every screen — this is the move that
    carries the design system below the fold (no more "header
    editorial, interior Streamlit-default")."""

    def test_app_py_calls(self) -> None:
        assert _module_calls(_APP_PY, "colophon"), "app.py must call ui.colophon()"

    def test_every_page_calls(self) -> None:
        for page in sorted(_PAGES_DIR.glob("*.py")):
            assert _module_calls(page, "colophon"), (
                f"{page.name} must call ui.colophon() at the top of the page"
            )


class TestWarnMarkStyle:
    """The .aat-warn-mark class is the single hook that replaces the
    pre-v0.14.0 emoji ⚠️. Its CSS sets the vermilion colour + serif
    voice so the typographic register doesn't break."""

    def test_class_styled_in_stylesheet(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.inject_global_styles()
            css = mock_md.call_args.args[0]
            assert ".aat-warn-mark" in css
            assert "var(--aat-vermilion)" in css


class TestEditorialTokens:
    """Pin the editorial palette tokens in the global stylesheet. A
    regression that quietly dropped the vermilion / cobalt / citron
    accents would silently fall back to default browser styling."""

    def test_palette_tokens_present(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.inject_global_styles()
            css = mock_md.call_args.args[0]
            for token in (
                "--aat-vermilion",
                "--aat-cobalt",
                "--aat-citron",
                "--aat-paper",
                "--aat-ink",
            ):
                assert token in css, f"Missing editorial token: {token}"

    def test_hero_orb_keyframes_present(self) -> None:
        # The slow-rotating conic-gradient orb is the signature motion
        # of the editorial hero. Pin its keyframes so a CSS refactor
        # that strips animations breaks loudly.
        with patch.object(ui.st, "markdown") as mock_md:
            ui.inject_global_styles()
            css = mock_md.call_args.args[0]
            assert "@keyframes aat-orb-spin" in css
            assert "conic-gradient" in css

    def test_serif_stack_present(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.inject_global_styles()
            css = mock_md.call_args.args[0]
            assert "--aat-font-serif" in css
            assert "--aat-font-mono" in css


# ── accent_bar / section_header (smoke) ───────────────────────────────────────


class TestRenderers:
    def test_accent_bar_renders(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.accent_bar()
            assert mock_md.called

    def test_section_header_renders(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.section_header("Upcoming", eyebrow="THIS WEEK")
            assert mock_md.called
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "Upcoming" in payload
            assert "THIS WEEK" in payload

    def test_section_header_no_eyebrow(self) -> None:
        with patch.object(ui.st, "markdown") as mock_md:
            ui.section_header("Recommender Alerts")
            assert mock_md.called
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "Recommender Alerts" in payload

    def test_section_header_html_escapes_payload(self) -> None:
        # The helper interpolates `text` + `eyebrow` into raw HTML; a
        # future caller passing user-supplied content must not be able
        # to inject markup.
        with patch.object(ui.st, "markdown") as mock_md:
            ui.section_header("<script>alert(1)</script>", eyebrow="<b>x</b>")
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "<script>" not in payload
            assert "<b>" not in payload
            assert "&lt;" in payload  # entity-encoded angle bracket

    def test_sidebar_about_block_emits_version(self) -> None:
        # sidebar_about_block must surface the version it's handed.
        # We don't care about Streamlit's actual sidebar tree — just that
        # the version string appears in *some* markdown call.
        with (
            patch.object(ui.st, "sidebar") as mock_sidebar,
            patch.object(ui.st, "markdown") as mock_md,
        ):
            # st.sidebar.expander → context manager; we mock loosely.
            mock_sidebar.expander.return_value.__enter__ = lambda s: s
            mock_sidebar.expander.return_value.__exit__ = lambda s, *a: False
            ui.sidebar_about_block("0.14.0")
            all_md_payload = " ".join(c.args[0] for c in mock_md.call_args_list if c.args)
            # Either st.markdown or st.sidebar.expander received the version.
            sidebar_calls_repr = repr(mock_sidebar.method_calls)
            assert "0.14.0" in all_md_payload + sidebar_calls_repr, (
                f"sidebar_about_block must surface the version string somewhere; "
                f"markdown payload: {all_md_payload!r}, sidebar calls: {sidebar_calls_repr!r}"
            )


# ── ui.py module-import contract (static) ─────────────────────────────────────


class TestUIImports:
    """ui.py is the display layer. It must import config (for status
    colour data) + streamlit, and must NOT import database, exports, or
    any page module (would create a layer-cycle)."""

    def test_ui_does_not_import_database_or_exports(self) -> None:
        src = (REPO_ROOT / "ui.py").read_text()
        # Module-level imports only (regex over the top of the file is
        # sufficient — lazy imports are an anti-pattern in display code).
        # We scan all `import X` / `from X import` lines.
        for m in re.finditer(r"^(?:import|from)\s+([\w.]+)", src, re.MULTILINE):
            mod = m.group(1).split(".")[0]
            assert mod not in {"database", "exports"}, (
                f"ui.py must not import {mod!r} — layer violation. "
                f"Display code receives data from pages, not directly from the data layer."
            )
