# app.py
# Streamlit entry point — dashboard home page.
#
# Phase 4 build-out: answers "What do I do today?" at a glance. This file
# is layered in over several tiers (see PHASE_4_GUIDELINES.md):
#   T1 — app shell + 4 KPI cards + 🔄 refresh + empty-DB hero   ✅ done
#   T2 — application funnel (Plotly bar + empty-state + columns wrap)  ✅ done
#   T3 — materials readiness panel                              ✅ done
#   T4 — upcoming timeline
#   T5 — recommender alerts

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
import database

database.init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

NEXT_INTERVIEW_EMPTY = "—"  # Locked decision U3: grid-consistent empty-state glyph.


def _next_interview_display(upcoming: pd.DataFrame) -> str:
    """Format the Next-Interview KPI value from get_upcoming_interviews().

    User-locked behaviour (2026-04-21):
      - Pick the EARLIEST future date across interview1_date AND
        interview2_date across all rows.
      - The paired institute belongs to whichever position owns that date.
      - Render as '{Mon D} · {institute}' (short month + day, no year).
      - Empty / no upcoming date → NEXT_INTERVIEW_EMPTY ('—').

    The underlying query includes a row when EITHER date is future, so
    the other column on the same row may be in the past — scanning both
    columns for the minimum FUTURE date is required.
    """
    if upcoming.empty:
        return NEXT_INTERVIEW_EMPTY

    today_iso = date.today().isoformat()
    best_iso: str | None = None
    best_institute: str | None = None
    for _, row in upcoming.iterrows():
        for col in ("interview1_date", "interview2_date"):
            v = row[col]
            if pd.isna(v) or v == "" or v < today_iso:
                continue
            if best_iso is None or v < best_iso:
                best_iso = v
                best_institute = row["institute"]

    if best_iso is None:
        return NEXT_INTERVIEW_EMPTY

    d = date.fromisoformat(best_iso)
    label = f"{d.strftime('%b')} {d.day}"
    if best_institute and not pd.isna(best_institute):
        label += f" · {best_institute}"
    return label

# ── Top bar ───────────────────────────────────────────────────────────────────
# Title on the left, 🔄 Refresh on the right (DESIGN.md §app.py). Streamlit
# already reruns on widget interaction; the manual refresh covers the case
# where data changed in another tab (e.g. Opportunities) — user decision C3.
title_col, refresh_col = st.columns([6, 1])
with title_col:
    st.title("Postdoc Tracker")
with refresh_col:
    if st.button("🔄 Refresh", key="dashboard_refresh"):
        st.rerun()

# ── KPI row ───────────────────────────────────────────────────────────────────
# Four equal columns per DESIGN.md §app.py. Labels are the UI contract.
# Tracked = open + applied — "opportunities that might get moved forward".
# Applied and Interview are single-bucket counts of their namesake status.
# Next Interview = earliest future date across interview1_date +
# interview2_date, rendered '{Mon D} · {institute}'; '—' when none
# (locked decision U3). All status literals via config.STATUS_* aliases.
_status_counts = database.count_by_status()
tracked = (
    _status_counts.get(config.STATUS_OPEN, 0)
    + _status_counts.get(config.STATUS_APPLIED, 0)
)
applied = _status_counts.get(config.STATUS_APPLIED, 0)
interview = _status_counts.get(config.STATUS_INTERVIEW, 0)
next_interview = _next_interview_display(database.get_upcoming_interviews())

# ── Empty-DB hero (T1-E) ──────────────────────────────────────────────────────
# Locked decision U5: when the counted KPI buckets are all zero, show a hero
# panel above the KPI grid with a CTA that routes to the Opportunities page.
# The grid still renders below — tests pin this so the hero is purely additive.
# Trigger = tracked + applied + interview == 0. A DB with only terminal-status
# rows (CLOSED/REJECTED/DECLINED) also satisfies this; if product call later
# narrows the trigger to 'total positions == 0', a single test (currently
# `test_terminal_only_db_still_shows_hero`) needs updating.
if tracked == 0 and applied == 0 and interview == 0:
    with st.container(border=True):
        st.subheader("Welcome to your Postdoc Tracker")
        st.write(
            "You haven't added any positions yet. "
            "Start by logging one — even rough notes — "
            "and come back here to see your pipeline take shape."
        )
        if st.button(
            "+ Add your first position",
            key="dashboard_empty_cta",
            type="primary",
        ):
            st.switch_page("pages/1_Opportunities.py")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric(label="Tracked", value=str(tracked))
with c2:
    st.metric(label="Applied", value=str(applied))
with c3:
    st.metric(label="Interview", value=str(interview))
with c4:
    st.metric(label="Next Interview", value=next_interview)

# ── Funnel + Readiness row (T2-C) ─────────────────────────────────────────────
# Two equal-width columns per locked decision U2: Application Funnel on the
# left, Materials Readiness (T3) on the right. T3-B will place its content
# inside `_right_col` below — the split is created once here and reused so
# the dashboard stays a single 2-column row (no second `st.columns(2)` call).
_left_col, _right_col = st.columns(2)

with _left_col:
    # ── Application Funnel (T2-A + T2-B) ──────────────────────────────────────
    # Plotly horizontal bar — one bar per config.STATUS_VALUES entry in
    # canonical order so the pipeline reads top-to-bottom OPEN → DECLINED.
    # count_by_status() returns a sparse dict (zero-count statuses omitted);
    # we fill missing buckets with 0 so the chart shape stays stable as the
    # pipeline fills up. Marker colors come from config.STATUS_COLORS — same
    # anti-typo guardrail as the status literals, keeps the pre-merge grep
    # rule enforcing a single source.
    #
    # T2-B empty-state (Option C, locked 2026-04-21): when the positions table
    # is literally empty (no rows at all), skip the Plotly chart and show a
    # descriptive info instead. A terminal-only DB still renders the figure —
    # terminal rows are valid visual state, and the T1-E hero separately
    # covers 'no active pipeline'. Subheader renders in both branches so page
    # height doesn't flicker when the first position lands.
    st.subheader("Application Funnel")
    if sum(_status_counts.values()) == 0:
        st.info("Application funnel will appear once you've added positions.")
    else:
        _funnel_x = [_status_counts.get(s, 0) for s in config.STATUS_VALUES]
        _funnel_colors = [config.STATUS_COLORS[s] for s in config.STATUS_VALUES]
        _funnel_fig = go.Figure(
            data=[
                go.Bar(
                    x=_funnel_x,
                    y=list(config.STATUS_VALUES),
                    orientation="h",
                    marker_color=_funnel_colors,
                )
            ]
        )
        # Plotly renders horizontal bars bottom-to-top by default (first
        # y-category at the bottom). Reverse the axis so the pipeline reads
        # top-down — first STATUS_VALUES entry at the top, last at the bottom.
        _funnel_fig.update_yaxes(autorange="reversed")
        st.plotly_chart(_funnel_fig, key="funnel_chart")

with _right_col:
    # ── Materials Readiness (T3) ──────────────────────────────────────────────
    # Two stacked st.progress bars — one for positions whose required docs
    # are all done, one for positions still missing at least one. Readiness
    # is active-pipeline-only by definition (see compute_materials_readiness),
    # so a DB with only terminal-status rows returns 0/0 and we show the
    # empty state. Denominator guarded via max(..., 1) per locked decision D5;
    # strictly speaking unnecessary inside the else-branch (both counts are
    # zero → we take the if-branch), but the explicit guard keeps the
    # contract close to the code for a future reader.
    #
    # Subheader renders in BOTH branches so page height doesn't flicker when
    # the first qualifying position lands (same stability pattern as the
    # T2-B funnel subheader).
    st.subheader("Materials Readiness")
    _readiness = database.compute_materials_readiness()
    _ready = _readiness["ready"]
    _pending = _readiness["pending"]
    if _ready + _pending == 0:
        st.info(
            "Materials readiness will appear once you've added positions "
            "with required documents."
        )
    else:
        _total = max(_ready + _pending, 1)
        st.progress(_ready / _total, text=f"Ready to submit: {_ready}")
        st.progress(_pending / _total, text=f"Still missing: {_pending}")
        if st.button("→ Opportunities page", key="materials_readiness_cta"):
            st.switch_page("pages/1_Opportunities.py")
