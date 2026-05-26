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

    def test_also_installs_hotkey_shield(self) -> None:
        """``inject_global_styles`` is the single bootstrap call every
        page makes; folding the hotkey shield in here guarantees the
        Cmd+C protection lands on every page without a second AST
        contract for callers."""
        with (
            patch.object(ui.st, "markdown"),
            patch.object(ui.components, "html") as mock_components_html,
        ):
            ui.inject_global_styles()
            assert mock_components_html.called, (
                "inject_global_styles must install the hotkey shield via "
                "streamlit.components.v1.html so Cmd+C does not trigger "
                "Streamlit's clear-cache dialog."
            )


# ── Hotkey shield (Cmd+C copy regression) ─────────────────────────────────────


class TestHotkeyShield:
    """Pin the contract for the hotkey shield that stops Streamlit's
    bare-letter dev hotkeys from firing on Cmd/Ctrl chords. The actual
    behaviour lives in JS injected via a zero-height components iframe;
    these tests pin the payload shape so a regression in the JS or the
    iframe-hiding CSS would surface as a unit-test failure rather than
    as a user-visible "Clear function caches?" dialog on Cmd+C."""

    def test_payload_targets_meta_and_ctrl_chords(self) -> None:
        assert "metaKey" in ui._HOTKEY_SHIELD_JS, (
            "Shield must check event.metaKey so macOS Cmd chords are caught."
        )
        assert "ctrlKey" in ui._HOTKEY_SHIELD_JS, (
            "Shield must check event.ctrlKey so Windows / Linux Ctrl chords are caught."
        )

    def test_payload_calls_stop_propagation(self) -> None:
        assert "stopPropagation" in ui._HOTKEY_SHIELD_JS, (
            "Shield must call event.stopPropagation() so Streamlit's "
            "document-level keydown listener never sees the chord."
        )

    def test_payload_uses_capture_phase(self) -> None:
        """The shield must register the listener in the capture phase
        (third arg ``true`` to ``addEventListener``) so it runs before
        Streamlit's own handler."""
        assert "true" in ui._HOTKEY_SHIELD_JS and "addEventListener" in ui._HOTKEY_SHIELD_JS
        # Crude but specific: the literal addEventListener-keydown-true
        # ordering, ignoring whitespace, must be present.
        normalised = "".join(ui._HOTKEY_SHIELD_JS.split())
        assert "'keydown'" in normalised
        assert "true" in normalised.split("'keydown'", 1)[1], (
            "addEventListener must pass capture=true so the shield runs "
            "before Streamlit's bubble-phase listener."
        )

    def test_payload_is_idempotent(self) -> None:
        """Streamlit reruns the page on every interaction; the shield
        installer must not stack listeners. Idempotency is enforced by
        a sentinel flag on the parent document."""
        assert "__aatHotkeyShieldInstalled" in ui._HOTKEY_SHIELD_JS, (
            "Shield must guard against double-install across reruns."
        )

    def test_payload_carries_sentinel_for_css_hide(self) -> None:
        """The stylesheet hides the shield's host iframe by matching
        ``srcdoc*='aatHotkeyShield'``. The JS payload must carry that
        sentinel so the CSS selector resolves."""
        assert "aatHotkeyShield" in ui._HOTKEY_SHIELD_JS

    def test_stylesheet_hides_shield_iframe(self) -> None:
        assert "aatHotkeyShield" in ui._STYLE_BLOCK, (
            "Stylesheet must include the iframe-hiding rule keyed on the "
            "shield sentinel so the install leaves no layout artefact."
        )
        assert "display: none" in ui._STYLE_BLOCK

    def test_payload_only_targets_single_character_keys(self) -> None:
        """The capture-phase listener runs at the document level — a
        blanket ``stopPropagation()`` on every Meta/Ctrl chord would
        block widget keybindings on named keys (e.g. BaseWeb selectbox
        Cmd+ArrowLeft to jump to the first option, contenteditable
        Cmd+Enter to submit). Restrict the stop to single-character
        keys (length 1) so only the keys Streamlit's bare-letter dev
        hotkeys could possibly bind (letters, digits, ``/``) are
        intercepted; named keys (ArrowLeft/Right/Up/Down, Tab, Enter,
        Escape, F-keys, etc.) pass through to the descendant widget."""
        normalised = "".join(ui._HOTKEY_SHIELD_JS.split())
        assert "event.key.length" in normalised or ".key.length" in normalised, (
            "Shield must gate stopPropagation on event.key.length so "
            "named keys (Arrow*, Tab, Enter, Escape, F-keys, …) reach "
            "the descendant widget. Currently the chord-shield blocks "
            "EVERY Meta/Ctrl chord, breaking widget keybindings."
        )

    def test_install_uses_zero_height_iframe(self) -> None:
        """The shield install is a side effect, not a content slot — the
        iframe must be zero-height so it cannot push the page layout
        even if the CSS hide rule ever fails to match."""
        with patch.object(ui.components, "html") as mock_components_html:
            ui._install_hotkey_shield()
            assert mock_components_html.called
            kwargs = mock_components_html.call_args.kwargs
            assert kwargs.get("height") == 0, (
                f"Shield iframe must be height=0; got {kwargs.get('height')!r}"
            )


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


_PAGE_MARK_GLYPHS = {"№", "§", "※", "⁂", "¶"}


def _page_mark_glyphs(py_path: Path) -> list[str]:
    """Return every literal-string arg passed to ``ui.page_mark(...)`` in
    ``py_path``. AST-walks so a glyph mentioned in a comment doesn't lie."""
    tree = ast.parse(py_path.read_text())
    glyphs: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "page_mark"):
            continue
        if node.args and isinstance(node.args[0], ast.Constant):
            val = node.args[0].value
            if isinstance(val, str):
                glyphs.append(val)
    return glyphs


def _call_lineno(py_path: Path, attr_name: str) -> int | None:
    """First-encountered line number of ``<something>.attr_name(...)`` in
    ``py_path``. Returns None if no such call exists. Used to pin call
    ORDER without coupling to surrounding line counts."""
    tree = ast.parse(py_path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == attr_name:
            return node.lineno
    return None


class TestPerPageMarkContract:
    """Pin the Margiela-blank-label design contract introduced in
    v0.14.0 (v6–v10): every non-Applications page renders one singular
    per-page typographic mark in the title gutter via ``ui.page_mark``;
    the Applications page deliberately omits its mark so the empty slot
    reads as withheld rather than missing. Without these pins, a
    future refactor could re-add a glyph to Applications (defanging the
    central design gesture) or drop a glyph from one of the other
    pages (breaking the system the absence relies on)."""

    def test_app_py_has_a_page_mark(self) -> None:
        glyphs = _page_mark_glyphs(_APP_PY)
        assert len(glyphs) == 1, (
            f"app.py must call ui.page_mark exactly once, got {len(glyphs)} call(s)"
        )
        assert glyphs[0] in _PAGE_MARK_GLYPHS, (
            f"app.py page_mark glyph {glyphs[0]!r} must be one of {_PAGE_MARK_GLYPHS}"
        )

    def test_non_applications_pages_each_have_one_mark(self) -> None:
        for page in sorted(_PAGES_DIR.glob("*.py")):
            if page.name == "2_Applications.py":
                continue
            glyphs = _page_mark_glyphs(page)
            assert len(glyphs) == 1, (
                f"{page.name} must call ui.page_mark exactly once, got {len(glyphs)} call(s)"
            )
            assert glyphs[0] in _PAGE_MARK_GLYPHS, (
                f"{page.name} page_mark glyph {glyphs[0]!r} must be one of {_PAGE_MARK_GLYPHS}"
            )

    def test_applications_page_omits_page_mark(self) -> None:
        # The Margiela lacuna: Applications carries NO ui.page_mark
        # call so the slot the other four pages fill stays empty. A
        # future re-introduction of a glyph here would defang the
        # central design gesture — block it at the test layer.
        applications = _PAGES_DIR / "2_Applications.py"
        glyphs = _page_mark_glyphs(applications)
        assert glyphs == [], (
            f"pages/2_Applications.py must NOT call ui.page_mark — the "
            f"empty gutter slot is the design gesture. Found {glyphs!r}."
        )

    def test_dashboard_page_mark_renders_before_hero(self) -> None:
        # The mark must land at the same flow position across pages
        # (top-right of main column, just under the colophon) so the
        # Applications absence reads as withheld rather than missing.
        # On Dashboard that means ui.page_mark MUST run BEFORE
        # ui.hero_greeting; otherwise the hero pushes the glyph below
        # the fold and the grid pin breaks (regression caught in v10).
        mark_line = _call_lineno(_APP_PY, "page_mark")
        hero_line = _call_lineno(_APP_PY, "hero_greeting")
        assert mark_line is not None, "app.py must call ui.page_mark"
        assert hero_line is not None, "app.py must call ui.hero_greeting"
        assert mark_line < hero_line, (
            f"app.py: ui.page_mark (line {mark_line}) must run BEFORE "
            f"ui.hero_greeting (line {hero_line}) so the glyph lands at "
            "the same coord as on every other page"
        )

    def test_glyph_uniqueness_across_pages(self) -> None:
        # Each page picks its OWN glyph (No  for Dashboard, sect for
        # Opportunities, etc.) — repeating one would flatten the system
        # into wallpaper. Pin uniqueness across the four marked pages.
        glyphs: list[str] = list(_page_mark_glyphs(_APP_PY))
        for page in sorted(_PAGES_DIR.glob("*.py")):
            if page.name == "2_Applications.py":
                continue
            glyphs.extend(_page_mark_glyphs(page))
        assert len(glyphs) == len(set(glyphs)), (
            f"Per-page mark glyphs must be unique across pages; got {glyphs!r}"
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

    def test_hero_has_no_gradient_orb(self) -> None:
        # v8: the conic-gradient orb behind the hero greeting imported a
        # softer lifestyle-app vocabulary at odds with the editorial
        # frame. Pinned removed so a future refactor cannot reintroduce
        # the orb under the same class name.
        with patch.object(ui.st, "markdown") as mock_md:
            ui.inject_global_styles()
            css = mock_md.call_args.args[0]
            assert "aat-hero-orb" not in css
            assert "@keyframes aat-orb-spin" not in css
        from datetime import datetime

        with patch.object(ui.st, "markdown") as mock_md:
            ui.hero_greeting(now=datetime(2026, 1, 1, 10, 0))
            payload = " ".join(c.args[0] for c in mock_md.call_args_list)
            assert "aat-hero-orb" not in payload

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


# ── Cross-platform strftime portability ────────────────────────────────────────


class TestUiStrftimePortability:
    """The ``%-d`` / ``%-m`` / ``%-H`` family of strftime directives strip
    the leading zero on glibc/macOS but raise ``ValueError`` on Windows
    (Windows wants ``%#d``). Since hero_greeting + colophon run on
    EVERY page, a single POSIX-only token blocks the whole app on
    Windows. Pin the rule at module level so neither side of the divide
    can regress."""

    _POSIX_ONLY = re.compile(r"%-[dmHIMSj]")

    def _scan(self, py_path: Path) -> list[tuple[int, str]]:
        hits: list[tuple[int, str]] = []
        for i, line in enumerate(py_path.read_text().splitlines(), start=1):
            for m in self._POSIX_ONLY.finditer(line):
                hits.append((i, m.group(0)))
        return hits

    def test_ui_py_avoids_posix_only_strftime_tokens(self) -> None:
        hits = self._scan(REPO_ROOT / "ui.py")
        assert hits == [], (
            "ui.py contains POSIX-only strftime directives that raise "
            "ValueError on Windows (Windows uses '%#d', '%#H' …). "
            f"Found: {hits}. Build the day-of-month with `str(n.day)` "
            "or `n.day` instead of `n.strftime('%-d')`."
        )


# ── Demo banner + sidebar reset block ─────────────────────────────────────────


class TestDemoBanner:
    """The banner + sidebar reset block render only when IS_DEMO=True.
    Layer rule preserved: ui.py imports neither database nor db_session;
    the reset block takes a callback for the actual wipe."""

    def test_demo_banner_noop_when_not_demo(self, monkeypatch):
        monkeypatch.setattr(config, "IS_DEMO", False)
        with patch("ui.st.markdown") as mock_md:
            ui.demo_banner()
            assert not mock_md.called, "demo_banner must not render when IS_DEMO=False"

    def test_demo_banner_renders_when_demo(self, monkeypatch):
        monkeypatch.setattr(config, "IS_DEMO", True)
        with patch("ui.st.markdown") as mock_md:
            ui.demo_banner()
            assert mock_md.called, "demo_banner must call st.markdown when IS_DEMO=True"
            # Inspect the markdown payload: headline + body + URL must be present.
            html = mock_md.call_args[0][0]
            assert config.DEMO_BANNER_HEADLINE in html
            assert config.DEMO_BANNER_BODY.split(".")[0] in html
            assert config.DEMO_SELF_HOST_URL in html

    def test_sidebar_reset_block_noop_when_not_demo(self, monkeypatch):
        monkeypatch.setattr(config, "IS_DEMO", False)
        called = []
        ui.sidebar_demo_reset_block(lambda: called.append("yes"))
        assert called == []

    def test_ui_does_not_import_database_or_db_session(self):
        # AST-level check — preserves the layer rule.
        source = (REPO_ROOT / "ui.py").read_text()
        tree = ast.parse(source)
        forbidden = {"database", "db_session"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in forbidden, (
                        f"ui.py imports forbidden module: {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom):
                assert node.module not in forbidden, (
                    f"ui.py imports forbidden module: {node.module}"
                )
