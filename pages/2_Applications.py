# pages/2_Applications.py
# Applications page — submission/response/interview/result tracking per
# position. DESIGN §8.3.
#
# Phase 5 T1 ships the page shell — set_page_config, title, status filter
# bar, and the read-only Applications table sorted by deadline. T2 adds
# the editable detail card; T3 adds the inline interview list (per
# DESIGN §8.3 D-A + D-B).

import streamlit as st

import config
import database


# DESIGN §8.0 — first executable Streamlit call on every page. Streamlit
# raises if anything else runs before this. Re-executed on every page
# switch; layout="wide" is required because the app is data-heavy
# (filter bar + multi-column applications table + future detail card).
st.set_page_config(
    page_title="Postdoc Tracker",
    page_icon="📋",
    layout="wide",
)

# Idempotent — picks up any pending REQUIREMENT_DOCS / vocabulary
# migrations when this page is opened first in a session, and is the
# pattern matched by app.py + pages/1_Opportunities.py.
database.init_db()

st.title("Applications")


# ── Filter bar ────────────────────────────────────────────────────────────────
#
# Default selection = config.STATUS_FILTER_ACTIVE — a sentinel that
# encodes "every actionable status" (excludes pre-application
# STATUS_SAVED and withdrawn STATUS_CLOSED per
# config.STATUS_FILTER_ACTIVE_EXCLUDED). The 'All' sentinel is the
# explicit "show every row" option; specific statuses appear after both
# sentinels and render via config.STATUS_LABELS.
#
# format_func uses STATUS_LABELS.get(v, v) — sentinel keys ("Active",
# "All") fall through to identity because they aren't STATUS_LABELS
# entries, so they render as themselves; STATUS_VALUES entries
# (bracketed sentinels in storage) render as their human labels.
#
# "All" stays a magic literal here for parity with the existing
# pages/1_Opportunities.py filter bar; promoting it to config is a
# project-wide refactor outside T1-B's scope.
_FILTER_ALL = "All"

st.selectbox(
    "Status",
    options=[
        config.STATUS_FILTER_ACTIVE,
        _FILTER_ALL,
        *config.STATUS_VALUES,
    ],
    index=0,
    format_func=lambda v: config.STATUS_LABELS.get(v, v),
    key="apps_filter_status",
)
