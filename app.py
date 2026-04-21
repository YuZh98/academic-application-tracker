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

import database

database.init_db()

st.title("Postdoc Tracker")

# ── KPI row ───────────────────────────────────────────────────────────────────
# Four equal columns per DESIGN.md §app.py. Labels are the UI contract.
# Values are placeholders here — T1-C wires count_by_status() into the first
# three cards, and T1-D wires get_upcoming_interviews() into the fourth
# (with "—" shown when no interview is scheduled, per locked decision U3).
KPI_PLACEHOLDER = "—"

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric(label="Tracked", value=KPI_PLACEHOLDER)
with c2:
    st.metric(label="Applied", value=KPI_PLACEHOLDER)
with c3:
    st.metric(label="Interview", value=KPI_PLACEHOLDER)
with c4:
    st.metric(label="Next Interview", value=KPI_PLACEHOLDER)
