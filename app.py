# app.py
# Streamlit entry point — dashboard home page.
#
# Phase 4 build-out: answers "What do I do today?" at a glance. This file
# is layered in over several tiers (see PHASE_4_GUIDELINES.md):
#   T1 — app shell + 4 KPI cards   (in progress)
#   T2 — application funnel
#   T3 — materials readiness panel
#   T4 — upcoming timeline
#   T5 — recommender alerts

from datetime import date

import pandas as pd
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

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric(label="Tracked", value=str(tracked))
with c2:
    st.metric(label="Applied", value=str(applied))
with c3:
    st.metric(label="Interview", value=str(interview))
with c4:
    st.metric(label="Next Interview", value=next_interview)
