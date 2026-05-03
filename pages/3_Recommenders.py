# pages/3_Recommenders.py
# Streamlit page — Recommenders tracker.
#
# Phase 5 T4: page shell + Pending Alerts panel (DESIGN §8.4).
#   - set_page_config, st.title, database.init_db()
#   - get_pending_recommenders() grouped by recommender_name;
#     one st.container(border=True) per person.
# Phase 5 T5: All Recommenders table + add form + inline edit. (next tier)
# Phase 5 T6: Reminder helpers (mailto + LLM prompts). (later tier)

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

import database

# DESIGN §8.0 + D14: every page's FIRST Streamlit call is set_page_config
# with wide layout. Must precede any other st.* call.
st.set_page_config(
    page_title="Postdoc Tracker",
    page_icon="📋",
    layout="wide",
)

database.init_db()

st.title("Recommenders")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _format_label(institute: str | None, position_name: str) -> str:
    """'{institute}: {position_name}' when institute is non-empty; bare
    position_name otherwise. Mirrors app.py T5 Label precedent — 'or'
    treats None and '' both as falsy, so no explicit pd.isna guard needed
    here: get_pending_recommenders surfaces missing TEXT cells as None."""
    if institute:
        return f"{institute}: {position_name}"
    return position_name


def _format_due(deadline_iso: str | None) -> str:
    """Due-date in 'Mon D' form (no year — near-future deadlines).
    Em-dash for NULL/empty, mirroring NEXT_INTERVIEW_EMPTY.
    pd.isna() catches both None and NaN-from-pandas (dev-notes gotcha #13)."""
    if deadline_iso is None or pd.isna(deadline_iso) or deadline_iso == "":
        return "—"
    d = date.fromisoformat(str(deadline_iso))
    return f"{d.strftime('%b')} {d.day}"


# ── Pending Alerts ────────────────────────────────────────────────────────────
#
# Driven by database.get_pending_recommenders() (default RECOMMENDER_ALERT_DAYS).
# One st.container(border=True) per distinct recommender_name; each card lists
# every position that recommender still owes a letter for.
#
# Locked card format (DESIGN §8.4):
#   **⚠ {name}** ({relationship})          ← relationship omitted when NULL
#   - {institute}: {position_name} (asked {N}d ago, due {Mon D})
#   - ...
#
# Reminder helpers (Compose button + LLM prompts expander) are Phase 5 T6 —
# NOT rendered here.

st.subheader("Pending Alerts")
_pending_recs = database.get_pending_recommenders()

if _pending_recs.empty:
    st.info("No pending recommenders.")
else:
    _today = date.today()

    # Stable iteration order: get_pending_recommenders() already sorts by
    # recommender_name ASC, deadline_date ASC NULLS LAST, so a plain groupby
    # preserves both within-group deadline order and across-group alphabetical
    # order without any extra sort.
    for _name, _group in _pending_recs.groupby("recommender_name", sort=False):
        with st.container(border=True):
            # Relationship: first row's value (same recommender → same person).
            # Guard against NaN surfaced by pandas for NULL TEXT columns.
            _rel: Any = _group.iloc[0]["relationship"]
            _rel_str = f" ({_rel})" if _rel and not pd.isna(_rel) else ""

            _bullets: list[str] = []
            for _, _row in _group.iterrows():
                _inst: Any = _row["institute"]
                _pos_name: Any = _row["position_name"]
                _label = _format_label(_inst, str(_pos_name))
                _asked_iso: str = str(_row["asked_date"])
                _days_ago = (_today - date.fromisoformat(_asked_iso)).days
                _due_raw: Any = _row["deadline_date"]
                _due = _format_due(_due_raw)
                _bullets.append(f"- {_label} (asked {_days_ago}d ago, due {_due})")

            _body = f"**⚠ {_name}**{_rel_str}\n" + "\n".join(_bullets)
            st.markdown(_body)
