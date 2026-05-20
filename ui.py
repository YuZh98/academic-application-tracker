# ui.py
# Shared presentation layer — design-system tokens, global stylesheet, and
# small pure-render helpers. Imported by app.py + every page in pages/.
#
# Layer contract (DESIGN §4, GUIDELINES §2):
#   - imports config + streamlit;
#   - does NOT import database or exports (display layer must not call
#     into the data tier).
#   - all CSS lives in this one module; pages never inject raw <style>.
#
# Why a single shared module:
#   Prior to v0.14.0, the entire stylesheet lived inline in app.py and
#   only the dashboard rendered with it. Every other page inherited
#   Streamlit's defaults, so the four pages looked visually unrelated.
#   Consolidating into `ui.inject_global_styles()` gives all four
#   pages the same shell without duplicating the CSS string.

from __future__ import annotations

import streamlit as st

import config

# ── Brand tokens ──────────────────────────────────────────────────────────────
# Python-side mirror of the brand accent. Used by helpers that need to
# emit colour-coded HTML inline (status pills can't read CSS variables
# inside Streamlit's inline-rendered <span> easily — the variables are
# present, but inline `style=""` defeats the dark-mode flip).
#
# Keep these in sync with the :root tokens in inject_global_styles().
_PILL_PALETTE: dict[str, str] = {
    # status label slug → background colour (light mode)
    "saved": "#4F6BEF",
    "applied": "#F59E3A",
    "interview": "#8B5CF6",
    "offer": "#10B981",
    "closed": "#94A3B8",
    "rejected": "#EF4444",
    "declined": "#94A3B8",
    "neutral": "#94A3B8",
}


# ── Public helpers ────────────────────────────────────────────────────────────


def status_pill(raw_status: str) -> str:
    """Return an HTML <span> rendering ``raw_status`` as a pill.

    Output shape (locked by tests):
        <span class="aat-pill aat-pill-<slug>" style="...">{label}</span>

    Unknown raw values fall back to the neutral class so a future status
    addition that forgets to update the palette renders gracefully
    instead of raising.
    """
    label = config.STATUS_LABELS.get(raw_status, raw_status.strip("[]").title())
    slug = label.lower()
    colour = _PILL_PALETTE.get(slug, _PILL_PALETTE["neutral"])
    klass = f"aat-pill aat-pill-{slug}"
    style = (
        f"background:{colour}1A;"  # 1A == 10% alpha hex suffix → soft tint
        f"color:{colour};"
        f"border:1px solid {colour}33;"  # 20% alpha border
    )
    return f'<span class="{klass}" style="{style}">{label}</span>'


def urgency_pill(
    days_left: int | None,
    *,
    urgent_d: int = config.DEADLINE_URGENT_DAYS,
    alert_d: int = config.DEADLINE_ALERT_DAYS,
) -> str:
    """Render a deadline-urgency pill.

    Bands mirror ``config.urgency_glyph``:
        days_left is None              → em-dash placeholder (no deadline)
        days_left <= urgent_d          → urgent (red)
        days_left <= alert_d           → warn (amber)
        days_left >  alert_d           → calm (muted)
    Negative inputs (past-due) fall into the urgent band.
    """
    if days_left is None:
        return (
            '<span class="aat-pill aat-pill-neutral" '
            f'style="color:#94A3B8;background:transparent;">{config.EM_DASH}</span>'
        )

    if days_left <= urgent_d:
        klass = "aat-pill aat-pill-urgent aat-urgent"
        colour = "#EF4444"
        label = f"{days_left}d" if days_left >= 0 else f"{abs(days_left)}d overdue"
    elif days_left <= alert_d:
        klass = "aat-pill aat-pill-warn aat-warn"
        colour = "#F59E3A"
        label = f"{days_left}d"
    else:
        klass = "aat-pill aat-pill-calm"
        colour = "#94A3B8"
        label = f"{days_left}d"

    style = f"background:{colour}1A;color:{colour};border:1px solid {colour}33;"
    return f'<span class="{klass}" style="{style}">{label}</span>'


def accent_bar() -> None:
    """Three-stop indigo→violet→green gradient hairline. Brand mark."""
    st.markdown(
        "<div class='aat-accent-bar'></div>",
        unsafe_allow_html=True,
    )


def section_header(text: str, *, eyebrow: str | None = None) -> None:
    """Render a section header with an optional uppercase eyebrow.

    Uses raw markdown rather than ``st.subheader`` so the eyebrow can sit
    immediately above the title with tighter spacing than Streamlit's
    default heading margin allows.
    """
    if eyebrow:
        st.markdown(
            f"<div class='aat-eyebrow'>{eyebrow}</div>",
            unsafe_allow_html=True,
        )
    st.markdown(
        f"<h2 class='aat-section-title'>{text}</h2>",
        unsafe_allow_html=True,
    )


def sidebar_about_block(version: str) -> None:
    """Render an 'About' expander in the sidebar carrying the app version
    + a one-line tagline + a link to the repo.

    This is the only sidebar customisation in the design system: the
    sidebar otherwise hosts Streamlit's auto-generated page nav.
    """
    with st.sidebar.expander(f"About · v{version}", expanded=False):
        st.markdown(
            "**Academic Application Tracker**  \n"
            f"Version `{version}` — local-first, single-user.  \n"
            "[GitHub →](https://github.com/YuZh98/academic-application-tracker)"
        )


# ── Global stylesheet ─────────────────────────────────────────────────────────
# Single source of truth for visual tokens. Light and dark variants share
# the same custom-property names so the rest of the sheet stays
# appearance-agnostic.
#
# Surface elevation: one step only — `--aat-shadow-sm` for resting
# cards, no nested elevation, no glass effects. Apple-tech restraint.

_STYLE_BLOCK = """
<style>
/* ── Design tokens ─────────────────────────────────────────────── */
:root {
    /* Brand */
    --aat-accent: #4F6BEF;
    --aat-accent-2: #8B5CF6;
    --aat-success: #10B981;
    --aat-warn:    #F59E3A;
    --aat-danger:  #EF4444;

    /* Neutrals — slate ramp */
    --aat-bg:          #ffffff;
    --aat-bg-elevated: #ffffff;
    --aat-bg-soft:     #f8fafc;
    --aat-border:      #eef2f7;
    --aat-text:        #0f172a;
    --aat-text-muted:  #475569;
    --aat-text-faint:  #94a3b8;

    /* Geometry */
    --aat-radius-sm: 8px;
    --aat-radius:    12px;
    --aat-radius-lg: 16px;

    /* Shadow — one step */
    --aat-shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.04),
                     0 6px 20px rgba(15, 23, 42, 0.04);
    --aat-shadow-md: 0 2px 6px rgba(15, 23, 42, 0.06),
                     0 12px 30px rgba(15, 23, 42, 0.06);

    /* Motion */
    --aat-ease:   cubic-bezier(0.2, 0, 0, 1);
    --aat-dur:    170ms;

    /* Typography */
    --aat-font: -apple-system, BlinkMacSystemFont, 'SF Pro Text',
                'Segoe UI Variable', 'Segoe UI', Helvetica, Arial, sans-serif;
}

@media (prefers-color-scheme: dark) {
    :root {
        --aat-bg:          #0b1020;
        --aat-bg-elevated: #111733;
        --aat-bg-soft:     #0f152a;
        --aat-border:      #1f2747;
        --aat-text:        #f1f5f9;
        --aat-text-muted:  #cbd5e1;
        --aat-text-faint:  #64748b;
        --aat-shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.4),
                         0 6px 20px rgba(0, 0, 0, 0.35);
    }
}

/* ── Typography ─────────────────────────────────────────────────── */
html, body {
    font-family: var(--aat-font) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

h1, [data-testid="stHeading"] h1 {
    letter-spacing: -0.02em !important;
    font-weight: 700 !important;
}

[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3 {
    color: var(--aat-text) !important;
    letter-spacing: -0.01em !important;
    font-weight: 700 !important;
}

/* ── Eyebrow + section title (used by ui.section_header) ───────── */
.aat-eyebrow {
    font-size: 0.70rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--aat-text-faint);
    margin: 0.5rem 0 0.15rem;
}

h2.aat-section-title {
    font-size: 1.4rem !important;
    font-weight: 700 !important;
    color: var(--aat-text) !important;
    margin: 0 0 0.6rem !important;
    letter-spacing: -0.01em !important;
}

/* ── Accent gradient line (used by ui.accent_bar) ──────────────── */
.aat-accent-bar {
    height: 3px;
    border-radius: 2px;
    margin-bottom: 0.5rem;
    background: linear-gradient(90deg,
        var(--aat-accent) 0%,
        var(--aat-accent-2) 50%,
        var(--aat-success) 100%);
}

/* ── Page tagline under the accent bar ─────────────────────────── */
.aat-tagline {
    color: var(--aat-text-muted);
    font-size: 0.95rem;
    margin: 0.1rem 0 1rem;
    line-height: 1.4;
}

/* ── KPI metric cards ──────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--aat-bg-elevated);
    border: 1px solid var(--aat-border);
    border-radius: var(--aat-radius);
    padding: 1.1rem 1.4rem 0.9rem;
    box-shadow: var(--aat-shadow-sm);
    transition: transform var(--aat-dur) var(--aat-ease),
                box-shadow var(--aat-dur) var(--aat-ease);
}
[data-testid="stMetric"]:hover {
    transform: translateY(-1px);
    box-shadow: var(--aat-shadow-md);
}
[data-testid="stMetricLabel"] p {
    font-size: 0.70rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    color: var(--aat-text-faint) !important;
    font-weight: 700 !important;
}
[data-testid="stMetricValue"] > div {
    font-size: 2rem !important;
    font-weight: 800 !important;
    color: var(--aat-text) !important;
    line-height: 1.2 !important;
    overflow-wrap: break-word !important;
    word-break: break-word !important;
}

/* ── Bordered containers (hero, recommender alert cards) ───────── */
[data-testid="stVerticalBlockBorderWrapper"] > div > div {
    border-radius: var(--aat-radius) !important;
    background: linear-gradient(135deg,
        var(--aat-bg-soft) 0%,
        color-mix(in srgb, var(--aat-accent) 5%, var(--aat-bg-soft)) 100%) !important;
    border-color: var(--aat-border) !important;
}

/* ── Info / alert blocks ───────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: var(--aat-radius-sm);
    border-left-width: 3px;
}

/* ── Dataframes ────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: var(--aat-radius);
    border: 1px solid var(--aat-border) !important;
    overflow: hidden;
    box-shadow: var(--aat-shadow-sm);
}

/* ── Buttons ───────────────────────────────────────────────────── */
[data-testid="stBaseButton-primary"] {
    border-radius: var(--aat-radius-sm) !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    transition: transform var(--aat-dur) var(--aat-ease),
                box-shadow var(--aat-dur) var(--aat-ease);
}
[data-testid="stBaseButton-primary"]:hover {
    transform: translateY(-1px);
    box-shadow: var(--aat-shadow-sm);
}

/* ── Sidebar nav pills ─────────────────────────────────────────── */
section[data-testid="stSidebarNav"] a {
    border-radius: var(--aat-radius-sm);
    padding: 0.35rem 0.7rem;
    margin-bottom: 2px;
    transition: background var(--aat-dur) var(--aat-ease),
                color var(--aat-dur) var(--aat-ease);
    font-weight: 500;
}
section[data-testid="stSidebarNav"] a:hover {
    background: rgba(79, 107, 239, 0.08);
    color: var(--aat-accent);
}
section[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(79, 107, 239, 0.10);
    color: var(--aat-accent);
    font-weight: 600;
}

/* ── Dividers ──────────────────────────────────────────────────── */
hr {
    border-color: var(--aat-border) !important;
    margin: 0.5rem 0 !important;
}

/* ── Pill helpers (rendered by ui.status_pill / ui.urgency_pill) ─ */
.aat-pill {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    line-height: 1.4;
    white-space: nowrap;
}

/* ── Focus rings — visible-only on keyboard nav ────────────────── */
button:focus-visible,
a:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
[data-testid="stBaseButton-primary"]:focus-visible {
    outline: 2px solid var(--aat-accent) !important;
    outline-offset: 2px !important;
    border-radius: var(--aat-radius-sm) !important;
}

/* ── Print: hide chrome so the dashboard prints cleanly ────────── */
@media print {
    section[data-testid="stSidebar"],
    [data-testid="stToolbar"],
    [data-testid="stStatusWidget"] { display: none !important; }
    [data-testid="stAppViewContainer"] { padding: 0 !important; }
}
</style>
"""


def inject_global_styles() -> None:
    """Inject the design-system stylesheet.

    Must be called once per Streamlit page, right after
    ``st.set_page_config(...)`` (Streamlit re-renders the whole page on
    every rerun, so re-injecting is free).

    Tests pin the existence of ``:root`` design tokens and the
    ``prefers-color-scheme: dark`` block so a stylesheet edit that
    accidentally drops either fails CI rather than silently flattening
    the UI.
    """
    st.markdown(_STYLE_BLOCK, unsafe_allow_html=True)
