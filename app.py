# app.py
# Streamlit entry point — dashboard home page.
# Phase 3 stub: initialises the database and shows a placeholder.
# Full dashboard (KPI cards, funnel, timeline, alerts) is Phase 4.

import streamlit as st
import database

database.init_db()

st.title("Postdoc Tracker")
st.info("Dashboard coming in Phase 4.")
