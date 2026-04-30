# pages/2_Applications.py
# Applications page — submission/response/interview/result tracking per
# position. DESIGN §8.3.
#
# Phase 5 T1 ships the page shell — set_page_config, title, status filter
# bar, and the read-only Applications table sorted by deadline. T2 adds
# the editable detail card; T3 adds the inline interview list (per
# DESIGN §8.3 D-A + D-B).

import datetime
import math
from typing import Any

import pandas as pd
import streamlit as st

import config
import database


EM_DASH = "—"


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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_str(v: Any) -> str:
    """Coerce a DataFrame cell to a widget-safe ``str``.

    Mirror of the helper in `pages/1_Opportunities.py` (see
    docs/dev-notes/streamlit-state-gotchas.md §1) — pandas returns
    ``float('nan')`` for NULL TEXT cells once any other row in the same
    column has a value, and the obvious ``r[col] or ""`` idiom misfires
    because ``bool(float('nan')) is True``. Treat ``None`` and any
    NaN-truthy value as ``""``."""
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v)


def _format_label(institute: Any, position_name: Any) -> str:
    """Position cell — ``f'{institute}: {position_name}'`` when
    institute is non-empty, bare ``position_name`` otherwise.
    Same shape as T4 Upcoming's Label column (DESIGN §8.1)."""
    inst = _safe_str(institute)
    name = _safe_str(position_name)
    if inst:
        return f"{inst}: {name}"
    return name


def _format_date_or_em(iso_str: Any) -> str:
    """Render an ISO ``YYYY-MM-DD`` string as ``'Mon D'`` (e.g.
    ``'Apr 19'``); return EM_DASH for None / NaN / empty / unparseable.

    Matches the T4 Upcoming Date-column format (``MMM D``, no year).
    Done by hand rather than via ``st.column_config.DateColumn`` because
    this page renders the table as text cells (a per-cell-formatted
    table — see `_format_confirmation` for the why)."""
    s = _safe_str(iso_str)
    if not s:
        return EM_DASH
    try:
        d = datetime.date.fromisoformat(s)
    except ValueError:
        return EM_DASH
    return f"{d.strftime('%b')} {d.day}"


def _format_confirmation(received: Any, iso_str: Any) -> str:
    """Confirmation cell — DESIGN §8.3 D-A amendment (Phase 5 T1-C).

    The original D-A spec carried ``confirmation_date`` as a per-cell
    tooltip, but Streamlit 1.56's ``st.dataframe`` does not expose a
    per-cell tooltip API (``st.column_config.Column(help=...)`` is
    column-header only; pandas Styler tooltips don't transfer through
    the Arrow protobuf). The amendment folds the tooltip text into
    inline cell content so every piece of D-A's information stays
    visible at-a-glance:

      - ``received == 0``        → ``'—'``
      - ``received == 1`` + date → ``'✓ {Mon D}'`` (e.g. ``'✓ Apr 19'``)
      - ``received == 1`` + None → ``'✓ (no date)'``

    Resolution recorded in `reviews/phase-5-tier1-review.md`."""
    if pd.isna(received) or not bool(received):
        return EM_DASH
    formatted = _format_date_or_em(iso_str)
    if formatted == EM_DASH:
        return "✓ (no date)"
    return f"✓ {formatted}"


def _safe_str_or_em(v: Any) -> str:
    """Render a TEXT cell as its string value or EM_DASH for empty."""
    s = _safe_str(v)
    return s if s else EM_DASH


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

selected_filter = st.selectbox(
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


# ── Table render ──────────────────────────────────────────────────────────────
#
# Read the joined positions × applications view via the T1-A reader
# (already sorted `deadline_date ASC NULLS LAST, position_id ASC` — the
# page must NOT re-sort). Apply the filter, then project into the six
# wireframe columns; render via st.dataframe. Empty post-filter → info.

df = database.get_applications_table()

if selected_filter == config.STATUS_FILTER_ACTIVE:
    df_filtered = df[~df["status"].isin(config.STATUS_FILTER_ACTIVE_EXCLUDED)]
elif selected_filter == _FILTER_ALL:
    df_filtered = df
else:
    df_filtered = df[df["status"] == selected_filter]

if df_filtered.empty:
    st.info("No applications match the current filter.")
else:
    # Build the six display columns by applying per-row formatters to
    # the raw reader columns. Index resets so the display DataFrame
    # has its own positional order — `st.dataframe(hide_index=True)`
    # then suppresses the integer index column entirely.
    display_df = pd.DataFrame({
        "Position": df_filtered.apply(
            lambda r: _format_label(r["institute"], r["position_name"]),
            axis=1,
        ),
        "Applied": df_filtered["applied_date"].apply(_format_date_or_em),
        "Recs": df_filtered["position_id"].apply(
            lambda pid: "✓" if database.is_all_recs_submitted(pid) else EM_DASH
        ),
        "Confirmation": df_filtered.apply(
            lambda r: _format_confirmation(
                r["confirmation_received"], r["confirmation_date"],
            ),
            axis=1,
        ),
        "Response": df_filtered["response_type"].apply(_safe_str_or_em),
        "Result": df_filtered["result"].apply(_safe_str_or_em),
    }).reset_index(drop=True)

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        key="apps_table",
    )
