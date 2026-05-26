# ui.py
# Shared presentation layer — editorial-brutalist design system. Imported
# by app.py + every page in pages/.
#
# Layer contract (DESIGN §4, GUIDELINES §2):
#   - imports config + streamlit;
#   - does NOT import database or exports (display layer must not call
#     into the data tier).
#   - all CSS lives in this one module; pages never inject raw <style>.
#
# Aesthetic charter (editorial-brutalist, v0.14.0):
#   - Three typographic voices: serif italic (display), mono (labels),
#     sans (body). Magazine-confident hierarchy, not sans-only minimalism.
#   - Warm cream paper + ink ramp. Vermilion + cobalt + citron as
#     editorial accents (Bauhaus / Vignelli).
#   - No drop shadows. Surfaces sit on the paper; depth comes from
#     hairlines and typographic mass.
#   - Sharp geometry: 0px section radii, 2px input radii, 999px on pills
#     only. Hairlines (1px solid ink) replace boxed cards.
#   - Slow deliberate motion. The hero conic gradient rotates one full
#     turn every 120s — almost imperceptible newsprint-press feel.

from __future__ import annotations

import html
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

import config

# ── Pill palette ──────────────────────────────────────────────────────────────
# Python-side mirror of the editorial status palette. Used by helpers
# that emit inline-styled HTML (Streamlit re-parses our <span> blocks
# into the canvas, and inline `style=""` is the only colour anchor that
# survives dark-mode CSS-variable flips reliably).
#
# Keep aligned with the :root tokens further down in this file.
_PILL_PALETTE: dict[str, str] = {
    # status label slug → editorial-brutalist accent (light mode)
    "saved": "#2541B2",  # cobalt — pre-application stillness
    "applied": "#E63946",  # vermilion — action committed
    "interview": "#F4D35E",  # citron — signal moment
    "offer": "#588157",  # sage — success
    "closed": "#5A5752",  # ink-muted — quiet exit
    "rejected": "#7A0E1F",  # oxblood — finality
    "declined": "#5A5752",  # ink-muted — declined
    "neutral": "#5A5752",
}


# ── Public helpers ────────────────────────────────────────────────────────────


def status_pill(raw_status: str) -> str:
    """Return an HTML <span> rendering ``raw_status`` as a ticket-stub pill.

    The shape is editorial, not iOS-soft: a thin colour stripe on the
    left edge, uppercase mono label inside, 999px end caps. The class
    slug is restricted to known palette keys so an unknown raw value
    cannot inject markup via the class attribute.

    Output shape (locked by tests):
        <span class="aat-pill aat-pill-<slug>" style="...">{label}</span>
    """
    label = config.STATUS_LABELS.get(raw_status, raw_status.strip("[]").title())
    safe_label = html.escape(label)
    raw_slug = label.lower()
    slug = raw_slug if raw_slug in _PILL_PALETTE else "neutral"
    colour = _PILL_PALETTE[slug]
    klass = f"aat-pill aat-pill-{slug}"
    # Editorial ticket-stub: vertical stripe on the left (4px box-shadow
    # acts as the stripe so the pill itself stays a clean rectangle of
    # paper). Mono uppercase label inside.
    style = (
        f"color:{colour};"
        "background:transparent;"
        f"border:1px solid {colour};"
        f"box-shadow:inset 4px 0 0 {colour};"
        "padding-left:0.85rem;"
    )
    # Label stays title-case in the HTML for screen-reader friendliness;
    # the editorial uppercase look comes from `.aat-pill { text-transform:
    # uppercase }` in the stylesheet.
    return f'<span class="{klass}" style="{style}">{safe_label}</span>'


def urgency_pill(
    days_left: int | None,
    *,
    urgent_d: int = config.DEADLINE_URGENT_DAYS,
    alert_d: int = config.DEADLINE_ALERT_DAYS,
) -> str:
    """Editorial urgency tag — mono digits + colour-coded stripe.

    Bands mirror ``config.urgency_glyph``:
        days_left is None              → em-dash placeholder (no deadline)
        days_left <= urgent_d          → urgent (vermilion)
        days_left <= alert_d           → warn (citron)
        days_left >  alert_d           → calm (muted)
    Negative inputs (past-due) fall into the urgent band.
    """
    if days_left is None:
        return (
            '<span class="aat-pill aat-pill-neutral" '
            f'style="color:#5A5752;background:transparent;'
            f'border:1px solid #1a1a1a22;">{config.EM_DASH}</span>'
        )

    if days_left <= urgent_d:
        klass = "aat-pill aat-pill-urgent aat-urgent"
        colour = "#E63946"
        label = f"T-{days_left}D" if days_left >= 0 else f"+{abs(days_left)}D OVERDUE"
    elif days_left <= alert_d:
        klass = "aat-pill aat-pill-warn aat-warn"
        colour = "#B58A00"  # darker citron so it reads on paper
        label = f"T-{days_left}D"
    else:
        klass = "aat-pill aat-pill-calm"
        colour = "#5A5752"
        label = f"T-{days_left}D"

    style = (
        f"color:{colour};"
        "background:transparent;"
        f"border:1px solid {colour};"
        f"box-shadow:inset 4px 0 0 {colour};"
        "padding-left:0.85rem;"
    )
    return f'<span class="{klass}" style="{style}">{label}</span>'


def accent_bar() -> None:
    """Bauhaus-poster mark: vermilion + cobalt geometric blocks butted
    edge-to-edge. Replaces the Apple-tech indigo gradient with something
    that has a louder shape and a clearer point of view.
    """
    st.markdown(
        "<div class='aat-accent-bar'>"
        "<span class='aat-accent-block aat-accent-block-1'></span>"
        "<span class='aat-accent-block aat-accent-block-2'></span>"
        "<span class='aat-accent-block aat-accent-block-3'></span>"
        "</div>",
        unsafe_allow_html=True,
    )


def section_header(text: str, *, eyebrow: str | None = None) -> None:
    """Render a section header with an optional uppercase mono eyebrow
    and a serif italic title underneath. Editorial table-of-contents
    feel."""
    if eyebrow:
        st.markdown(
            f"<div class='aat-eyebrow'>{html.escape(eyebrow)}</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        f"<h2 class='aat-section-title'>{html.escape(text)}</h2>",
        unsafe_allow_html=True,
    )


def numbered_section(n: int, title: str) -> None:
    """Section header in the editorial '01 — TITLE' pattern. The
    numeral lives in a thin display-serif span; the title is uppercase
    mono with generous letter-spacing — the kind of section mark used
    on Wallpaper* contents pages."""
    eyebrow_html = (
        f"<span class='aat-num'>{n:02d}</span>"
        "<span class='aat-num-sep'>—</span>"
        f"<span class='aat-num-title'>{html.escape(title)}</span>"
    )
    st.markdown(
        f"<div class='aat-numbered-section'>{eyebrow_html}</div>",
        unsafe_allow_html=True,
    )


def hero_greeting(*, name: str | None = None, now: datetime | None = None) -> None:
    """Dashboard hero: italic serif time-of-day greeting + mono date stamp.

    `name` defaults to None (the greeting reads "Good morning." flat,
    no name). Callers may pass a salutation; we accept it for future
    use, no production caller passes one in v0.14.0.

    `now` is exposed for tests; production reads ``datetime.now()`` so
    the greeting tracks local wall time across reruns.

    Bands:
        hour < 5  or  hour >= 22  → "Good evening."
        5  <= hour < 12          → "Good morning."
        12 <= hour < 18          → "Good afternoon."
        18 <= hour < 22          → "Good evening."
    """
    n = now or datetime.now()
    hour = n.hour
    if 5 <= hour < 12:
        greeting = "Good morning."
    elif 12 <= hour < 18:
        greeting = "Good afternoon."
    else:
        greeting = "Good evening."

    # Mono uppercase stamp: optionally "NAME · " prefix, then weekday + date.
    stamp_parts: list[str] = []
    if name:
        stamp_parts.append(html.escape(name.upper()))
    stamp_parts.append(n.strftime("%A").upper())
    # POSIX-only strftime "minus-d" directive raises ValueError on
    # Windows; build the day-of-month from ``n.day`` so the stamp
    # renders on every OS.
    stamp_parts.append(f"{n.strftime('%B')} {n.day}, {n.year}".upper())
    stamp = " · ".join(stamp_parts)

    st.markdown(
        "<div class='aat-hero'>"
        f"  <h1 class='aat-hero-greeting'>{html.escape(greeting)}</h1>"
        f"  <div class='aat-hero-stamp'>{stamp}</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def folio_footer(*, now: datetime | None = None) -> None:
    """Editorial folio footer at the bottom of every page.

    Magazine masthead-foot with an optional author-mark slot:
        VOL. XIV   ·   <italic-serif issue stamp>   [·  <mark> · MMXXVI]   — fin —

    The author-mark slot is driven by ``config.FOOTER_AUTHOR_MARK``; it
    is omitted entirely when that string is empty so a fresh clone ships
    with no personal stamp baked in (privacy-by-default). The flex
    layout still balances with the three remaining slots.
    """
    n = now or datetime.now()

    def _roman(n_int: int) -> str:
        """Tiny inline Roman numeral converter; only used here so we
        don't pull a dependency. Handles year-fragment range (e.g.
        the 0.14.0 string → 14 → 'XIV')."""
        vals = [
            (1000, "M"),
            (900, "CM"),
            (500, "D"),
            (400, "CD"),
            (100, "C"),
            (90, "XC"),
            (50, "L"),
            (40, "XL"),
            (10, "X"),
            (9, "IX"),
            (5, "V"),
            (4, "IV"),
            (1, "I"),
        ]
        out = ""
        for v, sym in vals:
            while n_int >= v:
                out += sym
                n_int -= v
        return out or "0"

    # Volume number tracks the app's minor version (0.14.0 → 14 → XIV).
    try:
        minor = int(config.APP_VERSION.removesuffix("-dev").split(".")[1])
    except (ValueError, IndexError):  # pragma: no cover — config drift
        minor = 0
    vol_roman = _roman(minor)
    year_roman = _roman(n.year)
    issue_label = n.strftime("№ %m / %Y")

    author_mark = config.FOOTER_AUTHOR_MARK.strip()
    author_span = (
        f"  <span>{author_mark} · {year_roman}</span>" if author_mark else ""
    )
    st.markdown(
        "<div class='aat-folio-footer'>"
        f"  <span>Vol. <span class='aat-folio-roman'>{vol_roman}</span></span>"
        f"  <span class='aat-folio-roman'>{issue_label}</span>"
        f"{author_span}"
        "  <span class='aat-folio-end'>— fin —</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def page_mark(glyph: str) -> None:
    """Render a singular oversized editorial mark in the page-title
    gutter. Each page picks its own glyph (§, ※, ¶, ⁂, № …) so the
    watermark stays "an intrusion" rather than a repeated decoration
    — addresses the v5 critique that a universal № flattens into
    wallpaper.

    The mark is absolutely positioned in a 0-height wrapper so it
    paints behind the next element (the page title) without
    consuming vertical space.
    """
    st.markdown(
        f"<div class='aat-page-mark-wrap'>"
        f"<span class='aat-page-mark'>{html.escape(glyph)}</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def colophon(section: str, *, now: datetime | None = None) -> None:
    """Magazine-style masthead strip at the very top of every page.

    Three-part editorial colophon:
        ACAD. APPLICATION TRACKER   ·   <section> (vermilion)   ·   ISSUE <year-month>   ·   <weekday date>

    Renders on the dashboard ("DASHBOARD") and on every page (the page
    name). The visual presence at the top of the canvas gives every page
    the same editorial signature without competing with the hero
    greeting underneath.

    `now` is exposed for tests; production reads ``datetime.now()`` so
    the issue stamp tracks local wall time across reruns.
    """
    n = now or datetime.now()
    safe_section = html.escape(section.upper())
    issue = n.strftime("ISSUE %Y · %B").upper()
    # POSIX-only "minus-d" directive — build day portably (see hero_greeting).
    stamp = f"{n.strftime('%A · %B')} {n.day}".upper()
    st.markdown(
        "<div class='aat-colophon'>"
        "  <strong>Academic Application Tracker</strong>"
        f"  <span class='aat-col-section'>{safe_section}</span>"
        f"  <span class='aat-col-issue'>{issue}</span>"
        f"  <span class='aat-col-stamp'>{stamp}</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def sidebar_about_block(version: str | None = None) -> None:
    """Sidebar 'About' expander. Mono uppercase header reads
    ``ABOUT · V<version>``. Default version is ``config.APP_VERSION``;
    callers may pass an explicit string (eg in tests).

    Must be called from every page entrypoint — Streamlit re-renders
    the sidebar on every page switch, so skipping the call on any page
    leaves the About expander invisible there.
    """
    v = version if version is not None else config.APP_VERSION
    with st.sidebar.expander(f"ABOUT · V{v}", expanded=False):
        st.markdown(
            "**Academic Application Tracker**  \n"
            f"Version `{v}` — local-first, single-user.  \n"
            "[GitHub →](https://github.com/YuZh98/academic-application-tracker)"
        )


def sidebar_shortcuts_block() -> None:
    """Sidebar 'Shortcuts' expander listing the page-level keyboard
    affordances. Mono uppercase header."""
    with st.sidebar.expander("SHORTCUTS", expanded=False):
        st.markdown(
            "- **R** — rerun the script  \n"
            "- **Esc** — close any open modal dialog  \n"
            "- Click a sidebar entry — switch page  \n"
            "- Click a row in any table — select (edit form appears below)  \n"
            "- ⚙ menu (top-right) — settings, clear cache, print"
        )


# ── Global stylesheet ─────────────────────────────────────────────────────────
# Editorial-brutalist token set. The :root variables are appearance-
# agnostic names; the @media (prefers-color-scheme: dark) block flips
# the warm-cream / ink-black pair without touching accent colours.

_STYLE_BLOCK = """
<style>
/* ── Hotkey-shield iframe ──────────────────────────────────────── */
/* The shield runs inside a zero-height components.v1.html iframe
   whose <script> tag carries the id `aatHotkeyShield`. Streamlit
   still wraps that iframe in an `stIFrame` slot that takes a row
   of layout space; collapse the slot so the install leaves no
   visible artefact on any page. */
div[data-testid="stIFrame"]:has(iframe[srcdoc*="aatHotkeyShield"]),
[data-testid="stCustomComponentV1"]:has(iframe[srcdoc*="aatHotkeyShield"]) {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ── Design tokens ─────────────────────────────────────────────── */
:root {
    /* Editorial palette — Bauhaus + newsroom */
    --aat-paper:       #F4EDE0;
    --aat-paper-soft:  #EDE5D4;
    --aat-ink:         #0A0A0A;
    --aat-ink-muted:   #5A5752;
    --aat-ink-faint:   #8C8879;
    --aat-rule:        #0A0A0A;
    --aat-rule-soft:   rgba(10, 10, 10, 0.15);

    /* Accents */
    --aat-vermilion: #E63946;
    --aat-cobalt:    #2541B2;
    --aat-citron:    #F4D35E;
    --aat-sage:      #588157;
    --aat-oxblood:   #7A0E1F;
    --aat-sand:      #E0CFA9;

    /* Geometry */
    --aat-radius-sm: 2px;
    --aat-radius:    0px;

    /* Motion */
    --aat-ease: cubic-bezier(0.65, 0.05, 0.36, 1);
    --aat-dur:  260ms;

    /* Typography stacks */
    --aat-font-serif: 'New York', 'Times New Roman', ui-serif, Georgia,
                      Cambria, serif;
    --aat-font-mono:  ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo,
                      Consolas, monospace;
    --aat-font-sans:  -apple-system, BlinkMacSystemFont, 'SF Pro Text',
                      'Segoe UI Variable', 'Segoe UI', Helvetica, Arial,
                      sans-serif;
}

@media (prefers-color-scheme: dark) {
    :root {
        --aat-paper:       #0A0A0A;
        --aat-paper-soft:  #1A1A1A;
        --aat-ink:         #F4EDE0;
        --aat-ink-muted:   #A8A599;
        --aat-ink-faint:   #6B6A60;
        --aat-rule:        #F4EDE0;
        --aat-rule-soft:   rgba(244, 237, 224, 0.18);
        --aat-cobalt:      #7A9BFF;
        --aat-oxblood:     #C3504A;
        --aat-sage:        #83A87F;
    }
}

/* ── Paper background ──────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--aat-paper) !important;
    color: var(--aat-ink) !important;
    font-family: var(--aat-font-sans) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Subtle SVG noise grain — adds newsprint flavour without distracting. */
body::before {
    content: "";
    position: fixed;
    inset: 0;
    pointer-events: none;
    opacity: 0.045;
    z-index: 0;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/></filter><rect width='200' height='200' filter='url(%23n)' opacity='0.7'/></svg>");
    mix-blend-mode: multiply;
}

/* ── Page title (st.title → h1) — italic serif monumental ─────── */
/* (Per-page editorial mark is now rendered as an explicit
   ui.page_mark(glyph) element so each page gets a unique typographic
   intrusion — §, ※, ¶, ⁂ — rather than the same № repeated as
   wallpaper across the system.) */
h1, [data-testid="stHeading"] h1 {
    font-family: var(--aat-font-serif) !important;
    font-style: italic !important;
    font-weight: 400 !important;
    font-size: 3.5rem !important;
    letter-spacing: -0.025em !important;
    color: var(--aat-ink) !important;
    margin: 1.2rem 0 0.4rem !important;
    line-height: 1.02 !important;
    position: relative;
    z-index: 1;
}

/* ── Subheaders (st.subheader → h3) — uppercase mono w/ rule ───── */
[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3 {
    font-family: var(--aat-font-mono) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.16em !important;
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    color: var(--aat-ink) !important;
    border-top: 1px solid var(--aat-rule);
    padding-top: 1.1rem !important;
    margin-top: 2.2rem !important;
}

/* ── Eyebrow + section title (used by ui.section_header) ───────── */
.aat-eyebrow {
    font-family: var(--aat-font-mono);
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--aat-ink-muted);
    margin: 0.6rem 0 0.1rem;
}

h2.aat-section-title {
    font-family: var(--aat-font-serif) !important;
    font-style: italic !important;
    font-weight: 400 !important;
    font-size: 2rem !important;
    color: var(--aat-ink) !important;
    margin: 0 0 1rem !important;
    letter-spacing: -0.015em !important;
    border: none !important;
    padding: 0 !important;
}

/* ── Numbered editorial section bar ────────────────────────────── */
.aat-numbered-section {
    border-top: 1px solid var(--aat-rule);
    padding-top: 0.9rem;
    margin-top: 2.4rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: baseline;
    gap: 0.85rem;
}
.aat-num {
    font-family: var(--aat-font-serif);
    font-style: italic;
    font-size: 1.7rem;
    color: var(--aat-vermilion);
    line-height: 1;
    letter-spacing: -0.02em;
}
.aat-num-sep {
    color: var(--aat-ink-muted);
    font-family: var(--aat-font-mono);
    font-weight: 400;
    margin: 0 0.15rem;
}
.aat-num-title {
    font-family: var(--aat-font-mono);
    text-transform: uppercase;
    letter-spacing: 0.22em;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--aat-ink);
}

/* ── Bauhaus accent bar (used by ui.accent_bar) ────────────────── */
.aat-accent-bar {
    display: flex;
    height: 8px;
    margin: 0.4rem 0 1.2rem;
    overflow: hidden;
}
.aat-accent-block { display: block; height: 100%; }
.aat-accent-block-1 { background: var(--aat-vermilion); flex: 5; }
.aat-accent-block-2 { background: var(--aat-cobalt);    flex: 2; }
.aat-accent-block-3 { background: var(--aat-citron);    flex: 1; }

/* ── Tagline (page subtitle under accent bar) ──────────────────── */
.aat-tagline {
    font-family: var(--aat-font-mono);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: var(--aat-ink-muted);
    font-size: 0.78rem;
    margin: 0.2rem 0 2rem;
    line-height: 1.5;
}

/* ── Hero (dashboard time-of-day greeting) ─────────────────────── */
.aat-hero {
    position: relative;
    padding: 3.5rem 0 2.5rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--aat-rule);
    overflow: hidden;
}
.aat-hero-greeting {
    position: relative;
    z-index: 1;
    font-family: var(--aat-font-serif) !important;
    font-style: italic !important;
    font-weight: 400 !important;
    font-size: clamp(3rem, 8vw, 5.8rem) !important;
    letter-spacing: -0.03em !important;
    line-height: 0.95 !important;
    color: var(--aat-ink) !important;
    margin: 0 !important;
    animation: aat-fade-up 1.2s var(--aat-ease) both;
}
.aat-hero-stamp {
    position: relative;
    z-index: 1;
    font-family: var(--aat-font-mono);
    text-transform: uppercase;
    letter-spacing: 0.22em;
    font-size: 0.72rem;
    color: var(--aat-ink-muted);
    margin-top: 1.2rem;
    animation: aat-fade-up 1.2s 0.15s var(--aat-ease) both;
}
@keyframes aat-fade-up {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── KPI metric cards — monumental display numerals + roman folio ─ */
[data-testid="stMetric"] {
    background: transparent;
    border: none;
    border-top: 2px solid var(--aat-ink);
    border-bottom: 1px solid var(--aat-rule-soft);
    border-radius: 0;
    padding: 1.2rem 0.4rem 1.4rem;
    box-shadow: none;
    transition: none;
    position: relative;
    counter-increment: aat-exhibit;
}
/* CSS-counter exhibit mark (i. ii. iii. iv.) above each metric —
   gallery-piece treatment turning each KPI into a numbered specimen.
   The counter resets at the .stHorizontalBlock that contains the row,
   so multiple metric rows on the same page each start at "i." */
[data-testid="stHorizontalBlock"] {
    counter-reset: aat-exhibit;
}
[data-testid="stMetric"]::before {
    content: counter(aat-exhibit, lower-roman) ".";
    position: absolute;
    top: 0.45rem;
    right: 0.4rem;
    font-family: var(--aat-font-serif);
    font-style: italic;
    font-size: 0.85rem;
    color: var(--aat-vermilion);
    letter-spacing: -0.01em;
    line-height: 1;
}
[data-testid="stMetric"]:hover { transform: none; box-shadow: none; }
[data-testid="stMetricLabel"] p {
    font-family: var(--aat-font-mono) !important;
    font-size: 0.70rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.18em !important;
    color: var(--aat-ink-muted) !important;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] > div {
    font-family: var(--aat-font-serif) !important;
    font-style: italic !important;
    font-size: 4rem !important;
    font-weight: 400 !important;
    color: var(--aat-ink) !important;
    line-height: 1 !important;
    letter-spacing: -0.04em !important;
    overflow-wrap: break-word !important;
    word-break: break-word !important;
    margin-top: 0.3rem !important;
    animation: aat-fade-up 0.9s var(--aat-ease) both;
}

/* ── Bordered containers ───────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] > div > div {
    border-radius: 0 !important;
    background: var(--aat-paper-soft) !important;
    border: none !important;
    border-top: 2px solid var(--aat-ink) !important;
    border-bottom: 1px solid var(--aat-rule-soft) !important;
    padding: 1rem 1.2rem !important;
}

/* ── Info / alert blocks ───────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 0;
    border: 1px solid var(--aat-rule);
    background: var(--aat-paper-soft) !important;
    border-left-width: 4px !important;
    border-left-color: var(--aat-cobalt) !important;
    font-family: var(--aat-font-mono);
    font-size: 0.85rem;
}

/* ── Dataframes — editorial exhibit frame ──────────────────────── */
/* Glide-data-grid is canvas-rendered so the cell internals cannot be
   restyled via CSS; the editorial gesture is therefore entirely in
   the frame around the canvas:
     - 2 px ink rule top and bottom (the masthead/footer of the table)
     - paper background so the canvas blends with the page paper
     - Streamlit's hover toolbar (download / search / fullscreen) hidden
       — it is the loudest piece of default-Streamlit chrome and the
       v7 critics caught it. */
[data-testid="stDataFrame"] {
    border-radius: 0 !important;
    border: none !important;
    border-top: 2px solid var(--aat-ink) !important;
    border-bottom: 2px solid var(--aat-ink) !important;
    background: var(--aat-paper) !important;
    overflow: hidden;
    box-shadow: none !important;
}
[data-testid="stDataFrame"] [data-testid="stElementToolbar"],
[data-testid="stDataFrame"] [data-testid="stToolbar"] {
    display: none !important;
}
[data-testid="stDataFrame"] canvas {
    background: var(--aat-paper) !important;
}

/* ── Buttons ───────────────────────────────────────────────────── */
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"] {
    border-radius: var(--aat-radius-sm) !important;
    font-family: var(--aat-font-mono) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    transition: transform var(--aat-dur) var(--aat-ease),
                background var(--aat-dur) var(--aat-ease);
}
[data-testid="stBaseButton-primary"] {
    background: var(--aat-ink) !important;
    color: var(--aat-paper) !important;
    border: 1px solid var(--aat-ink) !important;
}
[data-testid="stBaseButton-primary"]:hover {
    background: var(--aat-vermilion) !important;
    border-color: var(--aat-vermilion) !important;
    transform: translateX(2px);
}

/* ── Sidebar — editorial table of contents ─────────────────────── */
section[data-testid="stSidebar"],
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"] {
    background: var(--aat-paper-soft) !important;
    border-right: 1px solid var(--aat-rule);
}
[data-testid="stSidebarContent"] {
    padding-top: 2rem !important;
}
/* Sidebar masthead — typeset like a contents-page heading. */
[data-testid="stSidebarNav"]::before {
    content: "Contents";
    display: block;
    font-family: var(--aat-font-serif);
    font-style: italic;
    font-size: 1.4rem;
    color: var(--aat-ink);
    margin: 0 0 0.6rem 0.6rem;
    line-height: 1;
    letter-spacing: -0.01em;
}
[data-testid="stSidebarNav"]::after {
    content: "";
    display: block;
    height: 2px;
    background: var(--aat-vermilion);
    width: 32px;
    margin: 0.2rem 0 0.6rem 0.6rem;
}
[data-testid="stSidebarNav"] a {
    border-radius: 0;
    padding: 0.5rem 0.6rem 0.5rem 0.9rem;
    margin-bottom: 0;
    border-left: 2px solid transparent;
    transition: border-color var(--aat-dur) var(--aat-ease),
                color var(--aat-dur) var(--aat-ease),
                padding-left var(--aat-dur) var(--aat-ease);
    font-family: var(--aat-font-mono);
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.74rem;
    font-weight: 500;
    color: var(--aat-ink) !important;
}
[data-testid="stSidebarNav"] a:hover {
    border-left-color: var(--aat-cobalt);
    padding-left: 1.1rem;
    color: var(--aat-cobalt) !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"] {
    border-left-color: var(--aat-vermilion);
    color: var(--aat-vermilion) !important;
    font-weight: 700;
}

/* Sidebar expander labels — uppercase mono */
section[data-testid="stSidebar"] details summary {
    font-family: var(--aat-font-mono) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
    font-size: 0.74rem !important;
    color: var(--aat-ink) !important;
}

/* ── Dividers ──────────────────────────────────────────────────── */
hr {
    border-color: var(--aat-rule) !important;
    margin: 1.4rem 0 !important;
    opacity: 0.85;
}

/* ── Pill helpers (rendered by ui.status_pill / ui.urgency_pill) ─ */
.aat-pill {
    display: inline-block;
    padding: 0.18rem 0.7rem;
    border-radius: 999px;
    font-family: var(--aat-font-mono);
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    line-height: 1.5;
    white-space: nowrap;
    text-transform: uppercase;
}

/* ── Focus ring ────────────────────────────────────────────────── */
button:focus-visible,
a:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
[data-testid="stBaseButton-primary"]:focus-visible {
    outline: 2px solid var(--aat-vermilion) !important;
    outline-offset: 3px !important;
    border-radius: 0 !important;
}

/* ── BaseWeb selectbox / multiselect — deep editorial attack ───── */
/* Streamlit wraps native <select> in BaseWeb's component; the chrome
   we want is owned by [data-baseweb="select"] *inside* stSelectbox. */
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
    background: var(--aat-paper-soft) !important;
    border: 1px solid var(--aat-rule) !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    min-height: 36px !important;
    font-family: var(--aat-font-mono) !important;
    font-size: 0.78rem !important;
    color: var(--aat-ink) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
}
/* Selected-value text inside the BaseWeb select — caps + tracked. */
[data-testid="stSelectbox"] div[data-baseweb="select"] [data-baseweb="select-value"],
[data-testid="stSelectbox"] div[data-baseweb="select"] [role="combobox"] {
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
    font-family: var(--aat-font-mono) !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div:hover {
    border-color: var(--aat-vermilion) !important;
}
/* Hide BaseWeb's default chevron, paint our editorial one. */
[data-testid="stSelectbox"] div[data-baseweb="select"] svg,
[data-testid="stMultiSelect"] div[data-baseweb="select"] svg {
    display: none !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div::after,
[data-testid="stMultiSelect"] div[data-baseweb="select"] > div::after {
    content: "▼";
    font-family: var(--aat-font-mono);
    font-size: 0.6rem;
    color: var(--aat-vermilion);
    margin-left: auto;
    padding-right: 0.7rem;
    align-self: center;
    letter-spacing: 0;
}
/* Dropdown popover — paper bg, ink type, no radius. */
div[data-baseweb="popover"] [role="listbox"],
div[data-baseweb="popover"] ul[role="listbox"] {
    background: var(--aat-paper) !important;
    border: 1px solid var(--aat-rule) !important;
    border-radius: 0 !important;
    box-shadow: 4px 4px 0 var(--aat-ink) !important;
    font-family: var(--aat-font-mono) !important;
    font-size: 0.82rem !important;
}
div[data-baseweb="popover"] [role="option"] {
    color: var(--aat-ink) !important;
    border-radius: 0 !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
div[data-baseweb="popover"] [role="option"]:hover,
div[data-baseweb="popover"] [role="option"][aria-selected="true"] {
    background: var(--aat-vermilion) !important;
    color: var(--aat-paper) !important;
}

/* ── Link buttons (st.link_button) — match primary button language ─ */
[data-testid="stLinkButton"] a {
    background: var(--aat-paper-soft) !important;
    color: var(--aat-ink) !important;
    border: 1px solid var(--aat-ink) !important;
    border-radius: var(--aat-radius-sm) !important;
    font-family: var(--aat-font-mono) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    padding: 0.55rem 1rem !important;
    box-shadow: none !important;
    transition: transform var(--aat-dur) var(--aat-ease),
                background var(--aat-dur) var(--aat-ease),
                color var(--aat-dur) var(--aat-ease);
}
[data-testid="stLinkButton"] a:hover {
    background: var(--aat-ink) !important;
    color: var(--aat-paper) !important;
    transform: translateX(2px);
}

/* ── st.info / st.warning / st.error — pull-quote treatment ────── */
[data-testid="stAlert"] {
    background: var(--aat-paper-soft) !important;
    border: 1px solid var(--aat-rule) !important;
    border-left: 4px solid var(--aat-vermilion) !important;
    border-radius: 0 !important;
    font-family: var(--aat-font-serif) !important;
    font-style: italic !important;
    font-size: 1rem !important;
    color: var(--aat-ink) !important;
    padding: 1rem 1.2rem !important;
    line-height: 1.5 !important;
}
[data-testid="stAlert"] svg {
    color: var(--aat-vermilion) !important;
    fill: var(--aat-vermilion) !important;
}

/* ── Folio footer (editorial issue mark at every page bottom) ──── */
.aat-folio-footer {
    margin-top: 3rem;
    padding: 1.2rem 0 0.5rem;
    border-top: 1px solid var(--aat-rule);
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1.5rem;
    flex-wrap: wrap;
    font-family: var(--aat-font-mono);
    text-transform: uppercase;
    letter-spacing: 0.22em;
    font-size: 0.6rem;
    color: var(--aat-ink-faint);
}
.aat-folio-footer .aat-folio-roman {
    font-family: var(--aat-font-serif);
    font-style: italic;
    font-size: 0.95rem;
    color: var(--aat-vermilion);
    letter-spacing: 0.04em;
    text-transform: none;
    font-weight: 400;
}
.aat-folio-footer .aat-folio-end {
    color: var(--aat-ink-muted);
    font-family: var(--aat-font-serif);
    font-style: italic;
    text-transform: none;
    font-size: 0.95rem;
    letter-spacing: 0;
}

/* ── Hero scale-up + editorial dropped-letter on heroes ───────── */
.aat-hero-greeting {
    font-size: clamp(3.5rem, 11vw, 8rem) !important;
}
.aat-hero-greeting::first-letter {
    color: var(--aat-vermilion);
}

/* ── Per-page editorial watermark glyph (§ ※ ¶ ⁂ …) ────────── */
/* Each page picks a singular typographic mark; the Applications page
   deliberately omits its glyph (silent Margiela lacuna). The mark is
   anchored to a 0-height wrapper inserted immediately after the
   colophon strip on every page (including Dashboard, where the
   wrapper precedes the hero greeting) so the mark lands at the same
   flow position across pages. v9 tried pinning to stMain coords and
   broke visibility on pages with a hero block — reverted in v10. */
.aat-page-mark-wrap {
    position: relative;
    pointer-events: none;
    height: 0;
}
.aat-page-mark {
    position: absolute;
    top: -1rem;
    right: -1vw;
    font-family: var(--aat-font-serif);
    font-style: italic;
    font-weight: 400;
    font-size: clamp(7rem, 14vw, 11rem);
    color: var(--aat-vermilion);
    opacity: 0.08;
    line-height: 0.85;
    z-index: 0;
    letter-spacing: -0.05em;
    user-select: none;
}

/* Hero watermark removed in v6 — the per-page ui.page_mark() helper
   handles the editorial mark singly per page (different glyph each
   page) so the gesture stays an intrusion rather than wallpaper. */

/* ── Main-canvas markdown bullets — italic serif pull-quote ─────── */
/* Streamlit 1.57 dropped the stVerticalBlockBorderWrapper testid the
   prior CSS targeted. The Recommender Alert card's bullets live
   inside `section[data-testid="stMain"] [data-testid="stMarkdown"]`;
   scope the italic-serif treatment to main-canvas markdown lists so
   the sidebar Shortcuts expander keeps its sans-serif voice. */
section[data-testid="stMain"] [data-testid="stMarkdown"] ul {
    border-left: 1px solid var(--aat-rule);
    padding-left: 1.25rem !important;
    margin-left: 0.2rem;
}
section[data-testid="stMain"] [data-testid="stMarkdown"] ul li {
    font-family: var(--aat-font-serif) !important;
    font-style: italic !important;
    font-size: 1.02rem !important;
    line-height: 1.65 !important;
    color: var(--aat-ink) !important;
}
section[data-testid="stMain"] [data-testid="stMarkdown"] ul li::marker {
    color: var(--aat-vermilion) !important;
}
section[data-testid="stMain"] [data-testid="stMarkdown"] ul li strong,
section[data-testid="stMain"] [data-testid="stMarkdown"] p strong {
    font-family: var(--aat-font-sans) !important;
    font-style: normal !important;
    font-weight: 700 !important;
    letter-spacing: -0.005em !important;
}

/* ── Dataframe deeper editorial styling ───────────────────────── */
/* Glide DataGrid's table internals are React-canvas, but the outer
   chrome is HTML — push the wrapper to match the editorial system
   and lean on tabular-nums for any numeric columns. */
[data-testid="stDataFrame"] {
    border-radius: 0 !important;
}
[data-testid="stDataFrame"] thead tr th,
[data-testid="stDataFrame"] tbody tr td {
    font-feature-settings: "tnum" 1, "lnum" 1 !important;
    border-right: 1px solid var(--aat-rule-soft) !important;
}
[data-testid="stDataFrame"] tbody tr td:first-child {
    border-left: none;
}

/* ── Caption — editorial credit line ──────────────────────────── */
[data-testid="stCaptionContainer"] p,
[data-testid="stCaption"] {
    font-family: var(--aat-font-mono) !important;
    font-size: 0.7rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.18em !important;
    color: var(--aat-ink-muted) !important;
}

/* ── KPI numerals — tabular figures, vermilion accent on lead ─── */
[data-testid="stMetricValue"] > div {
    font-feature-settings: "tnum" 1, "lnum" 1, "zero" 1;
}

/* ── Editorial warn mark (replaces emoji ⚠️) ───────────────────── */
.aat-warn-mark {
    display: inline-block;
    color: var(--aat-vermilion);
    font-family: var(--aat-font-serif);
    font-weight: 700;
    margin-right: 0.35rem;
    line-height: 1;
    transform: translateY(-1px);
}

/* ── Body typography tuning ─────────────────────────────────────── */
[data-testid="stAppViewContainer"] p,
[data-testid="stAppViewContainer"] li {
    line-height: 1.55 !important;
    color: var(--aat-ink) !important;
}
[data-testid="stAppViewContainer"] li::marker {
    color: var(--aat-vermilion);
}

/* ── Inputs — newspaper editorial form fields ──────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
    background: var(--aat-paper-soft) !important;
    color: var(--aat-ink) !important;
    border: 1px solid var(--aat-rule) !important;
    border-radius: 0 !important;
    font-family: var(--aat-font-mono) !important;
    font-size: 0.85rem !important;
    box-shadow: none !important;
    padding: 0.5rem 0.7rem !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stDateInput"] input:focus {
    border-color: var(--aat-vermilion) !important;
    outline: 1px solid var(--aat-vermilion) !important;
    outline-offset: 0 !important;
}

/* Field labels — uppercase mono, generous letter-spacing */
[data-testid="stTextInput"] label p,
[data-testid="stTextArea"] label p,
[data-testid="stNumberInput"] label p,
[data-testid="stDateInput"] label p,
[data-testid="stSelectbox"] label p,
[data-testid="stMultiSelect"] label p,
[data-testid="stRadio"] label p,
[data-testid="stCheckbox"] label p {
    font-family: var(--aat-font-mono) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.16em !important;
    font-size: 0.66rem !important;
    color: var(--aat-ink-muted) !important;
    font-weight: 600 !important;
}

/* ── Selectbox — same editorial chrome as text inputs ───────────── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {
    background: var(--aat-paper-soft) !important;
    border: 1px solid var(--aat-rule) !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    font-family: var(--aat-font-mono) !important;
    font-size: 0.85rem !important;
}

/* ── Expanders — magazine-section divider style ────────────────── */
[data-testid="stExpander"] details {
    background: transparent !important;
    border: none !important;
    border-top: 1px solid var(--aat-rule) !important;
    border-bottom: 1px solid var(--aat-rule-soft) !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}
[data-testid="stExpander"] details summary {
    font-family: var(--aat-font-mono) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.16em !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    color: var(--aat-ink) !important;
    padding: 0.8rem 0.2rem !important;
}
[data-testid="stExpander"] details[open] summary {
    border-bottom: 1px solid var(--aat-rule-soft);
    margin-bottom: 0.5rem;
}

/* ── Dataframe — editorial gazetteer ───────────────────────────── */
[data-testid="stDataFrame"] thead tr th {
    background: var(--aat-ink) !important;
    color: var(--aat-paper) !important;
    font-family: var(--aat-font-mono) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.14em !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    border-right: 1px solid var(--aat-paper-soft) !important;
}
[data-testid="stDataFrame"] tbody tr td {
    background: var(--aat-paper) !important;
    color: var(--aat-ink) !important;
    font-family: var(--aat-font-sans) !important;
    font-size: 0.86rem !important;
    border-bottom: 1px solid var(--aat-rule-soft) !important;
}
[data-testid="stDataFrame"] tbody tr:hover td {
    background: var(--aat-paper-soft) !important;
}

/* ── Colophon (issue masthead) ─────────────────────────────────── */
.aat-colophon {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    border-bottom: 1px solid var(--aat-rule);
    padding: 0.5rem 0 0.65rem;
    margin-bottom: 0.4rem;
    font-family: var(--aat-font-mono);
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-size: 0.66rem;
    color: var(--aat-ink-muted);
    gap: 1rem;
    flex-wrap: wrap;
}
.aat-colophon strong {
    font-family: var(--aat-font-serif);
    font-style: italic;
    font-weight: 400;
    color: var(--aat-ink);
    font-size: 0.92rem;
    letter-spacing: -0.005em;
    text-transform: none;
}
.aat-colophon .aat-col-section {
    color: var(--aat-vermilion);
    font-weight: 700;
}

/* ── Print ─────────────────────────────────────────────────────── */
@media print {
    section[data-testid="stSidebar"],
    [data-testid="stToolbar"],
    [data-testid="stStatusWidget"],
    body::before { display: none !important; }
    [data-testid="stAppViewContainer"] { padding: 0 !important; }
}
</style>
"""


# Streamlit binds bare-letter developer hotkeys ('c' clears the function
# caches, 'r' reruns the script, '/' opens the menu, etc.) at the document
# level. On macOS the ``Cmd`` modifier still delivers the bare-letter
# ``keydown``, so ``Cmd+C`` to copy a selection lands on Streamlit's
# listener first and pops the "Clear function caches?" dialog instead of
# copying. Install a capture-phase listener on the parent document that
# halts propagation for the chord events Streamlit's bare-letter
# handlers could possibly bind — Streamlit's own listener never fires,
# the browser's default chord behaviour (copy, paste, reload, …) runs
# normally.
#
# The ``event.key.length === 1`` gate restricts the stop to
# single-character keys (letters, digits, ``/``, etc.); named keys
# (``ArrowLeft``/``ArrowRight``/``Tab``/``Enter``/``Escape``/``F1``…)
# pass through, so descendant widget keybindings (e.g. BaseWeb
# selectbox Cmd+Arrow navigation) survive.
#
# The sentinel string ``aatHotkeyShield`` is matched by a CSS rule in
# ``_STYLE_BLOCK`` that hides the host iframe so the install leaves no
# visible artefact.
_HOTKEY_SHIELD_JS: str = """
<script id="aatHotkeyShield">
(function () {
    try {
        var doc = window.parent && window.parent.document;
        if (!doc || doc.__aatHotkeyShieldInstalled) { return; }
        doc.__aatHotkeyShieldInstalled = true;
        doc.addEventListener(
            'keydown',
            function (event) {
                if ((event.metaKey || event.ctrlKey) && event.key && event.key.length === 1) {
                    event.stopPropagation();
                }
            },
            true
        );
    } catch (_) {
        /* cross-origin or otherwise unreachable — fail silently */
    }
})();
</script>
"""


def _install_hotkey_shield() -> None:
    """Suppress Streamlit's bare-letter dev hotkeys whenever the user
    holds ``Cmd`` / ``Ctrl`` so ``Cmd+C`` copies the current selection
    instead of clearing the function caches. See ``_HOTKEY_SHIELD_JS``
    for the rationale and DESIGN §8.7 for the contract."""
    components.html(_HOTKEY_SHIELD_JS, height=0, width=0)


def inject_global_styles() -> None:
    """Inject the editorial-brutalist stylesheet and the hotkey shield.

    Must be called once per Streamlit page, right after
    ``st.set_page_config(...)``. Streamlit re-renders the whole page on
    every rerun, so re-injecting is free; the shield install is
    idempotent (see the JS sentinel guard).
    """
    st.markdown(_STYLE_BLOCK, unsafe_allow_html=True)
    _install_hotkey_shield()


# ── Demo deploy affordances ───────────────────────────────────────────────────


def demo_banner() -> None:
    """Render the Demo Mode banner. No-op when ``config.IS_DEMO`` is False.

    Editorial register: vermilion accent bar + mono uppercase headline +
    italic-serif body + self-host CTA. Renders below
    ``inject_global_styles()`` so ``var(--aat-vermilion)`` resolves to
    the existing token (``#E63946``); we still pass the literal as a
    fallback for the rare case where the banner is rendered before
    the global style block.
    """
    if not config.IS_DEMO:
        return

    st.markdown(
        f"""
        <div style="
            border-left: 4px solid var(--aat-vermilion, #E63946);
            padding: 0.75rem 1rem;
            margin: 0 0 1.5rem 0;
            background: rgba(230, 57, 70, 0.06);
            font-family: 'IBM Plex Mono', monospace;
        ">
          <div style="
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 700;
            color: var(--aat-vermilion, #E63946);
            margin-bottom: 0.25rem;
          ">{config.DEMO_BANNER_HEADLINE}</div>
          <div style="font-style: italic; line-height: 1.5;">
            {config.DEMO_BANNER_BODY}
            <a href="{config.DEMO_SELF_HOST_URL}" target="_blank">Self-host instructions ↗</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_demo_reset_block(on_reset) -> None:
    """Render the 'Reset demo data' sidebar button. No-op when not in demo.

    Click → confirm dialog → ``on_reset()`` → ``st.rerun()``. The
    callback indirection preserves the layer rule (``ui.py`` never
    imports ``database`` or ``db_session`` directly — the page wires
    in ``db_session.reset`` at render time).
    """
    if not config.IS_DEMO:
        return

    with st.sidebar:
        st.markdown("---")
        if st.button("Reset demo data", key="_demo_reset_btn"):
            _confirm_reset(on_reset)


@st.dialog("Reset demo data?")
def _confirm_reset(on_reset) -> None:
    """Confirmation dialog. Order matters: ``on_reset()`` MUST run
    BEFORE ``st.rerun()`` so the next render sees the cleared cache."""
    st.write(
        "This will wipe your demo session and re-seed the fictional data. "
        "Continue?"
    )
    col1, col2 = st.columns(2)
    if col1.button("Yes, reset", key="_demo_reset_confirm"):
        on_reset()
        st.rerun()
    if col2.button("Cancel", key="_demo_reset_cancel"):
        st.rerun()
