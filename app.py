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

import streamlit as st

import config
import database

database.init_db()

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
# Next Interview stays "—" until T1-D wires get_upcoming_interviews()
# (locked decision U3). All status literals via config.STATUS_* aliases.
NEXT_INTERVIEW_PLACEHOLDER = "—"

_status_counts = database.count_by_status()
tracked = (
    _status_counts.get(config.STATUS_OPEN, 0)
    + _status_counts.get(config.STATUS_APPLIED, 0)
)
applied = _status_counts.get(config.STATUS_APPLIED, 0)
interview = _status_counts.get(config.STATUS_INTERVIEW, 0)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric(label="Tracked", value=str(tracked))
with c2:
    st.metric(label="Applied", value=str(applied))
with c3:
    st.metric(label="Interview", value=str(interview))
with c4:
    st.metric(label="Next Interview", value=NEXT_INTERVIEW_PLACEHOLDER)
