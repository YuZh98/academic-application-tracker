# app.py
# Streamlit entry point — dashboard home page.
#
# Phase 4 build-out: answers "What do I do today?" at a glance. This file
# is layered in over several tiers (see PHASE_4_GUIDELINES.md):
#   T1 — app shell + 4 KPI cards + empty-DB hero                ✅ done
#   T2 — application funnel (Plotly bar, FUNNEL_BUCKETS aggregation,
#        bidirectional disclosure toggle, 3-branch empty-state)   ✅ done
#   T3 — materials readiness panel                              ✅ done
#   T4 — upcoming timeline (full-width, dynamic window selector) ✅ done
#   T5 — recommender alerts (cards grouped by recommender_name)  ✅ done
#   T6 — disclosure-toggle polish (bidirectional, tertiary, subheader-
#        row inline placement) — DESIGN §8.1 T6 amendment        ✅ done

from datetime import date
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
import database

# DESIGN §8.0 + D14: every page's FIRST Streamlit call is set_page_config
# with wide layout. Data-heavy views (KPI grid + funnel + timeline) need
# horizontal room; the default centered layout cramps them at ~750px.
# Must precede any other `st.*` call — Streamlit raises otherwise.
st.set_page_config(
    page_title="Academic Application Tracker",
    page_icon="📋",
    layout="wide",
)

database.init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _next_interview_display(upcoming: pd.DataFrame) -> str:
    """Format the Next-Interview KPI value from get_upcoming_interviews().

    User-locked behaviour (2026-04-21):
      - Pick the EARLIEST future scheduled_date across all upcoming
        interviews.
      - The paired institute belongs to whichever position owns that date.
      - Render as '{Mon D} · {institute}' (short month + day, no year).
      - Empty / no upcoming date → ``config.EM_DASH`` ('—').

    Sub-task 8 rewrote get_upcoming_interviews() to return row-per-
    interview from the normalized interviews sub-table (DESIGN §6.2 +
    D18) with a single scheduled_date column — rows are guaranteed to
    carry future dates (the SQL filters on `scheduled_date >= today`)
    and are ordered ASC by scheduled_date. So iloc[0] would also be
    correct today; the explicit min-scan is kept for robustness against
    a future query tweak that drops or reorders the sort.
    """
    if upcoming.empty:
        return config.EM_DASH

    today_iso = date.today().isoformat()
    best_iso: str | None = None
    best_institute: str | None = None
    for _, row in upcoming.iterrows():
        v: Any = row["scheduled_date"]
        if pd.isna(v) or v == "" or v < today_iso:
            continue
        if best_iso is None or v < best_iso:
            best_iso = str(v)
            inst: Any = row["institute"]
            best_institute = None if pd.isna(inst) else str(inst)

    if best_iso is None:
        return config.EM_DASH

    d = date.fromisoformat(best_iso)
    label = f"{d.strftime('%b')} {d.day}"
    if best_institute and not pd.isna(best_institute):
        label += f" · {best_institute}"
    return label


# ── Top bar ───────────────────────────────────────────────────────────────────
# Plain title only — no 🔄 Refresh button per DESIGN D13. Streamlit reruns
# on any widget interaction; for a single-user local app a manual refresh
# is cognitive noise for the common case. (The pre-v1.3 C3-locked Refresh
# button was removed in Sub-task 12 alongside the DESIGN §8.0 alignment.)
st.title("Academic Application Tracker")

# ── KPI row ───────────────────────────────────────────────────────────────────
# Four equal columns per DESIGN.md §app.py. Labels are the UI contract.
# Tracked = saved + applied — "opportunities that might get moved forward".
# Applied and Interview are single-bucket counts of their namesake status.
# Next Interview = earliest future scheduled_date across all rows of
# database.get_upcoming_interviews() (row-per-interview post-Sub-task 8,
# DESIGN §6.2 + D18), rendered '{Mon D} · {institute}'; '—' when none
# (locked decision U3). All status literals via config.STATUS_* aliases.
_status_counts = database.count_by_status()
tracked = _status_counts.get(config.STATUS_SAVED, 0) + _status_counts.get(config.STATUS_APPLIED, 0)
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
        st.subheader("Welcome to your Academic Application Tracker")
        st.markdown(
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
    # DESIGN §8.1 locks the Tracked KPI's help-tooltip string — explains
    # the Saved + Applied arithmetic on hover so the reader doesn't have
    # to guess what "tracked" means here.
    st.metric(
        label="Tracked",
        value=str(tracked),
        help="Saved + Applied — positions you're still actively pursuing",
    )
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
    # ── Application Funnel (T2-A + T2-B + T2-D + T6 disclosure-toggle) ────────
    # Plotly horizontal bar driven by config.FUNNEL_BUCKETS. One bar per
    # VISIBLE bucket in list display order; the y-axis is reversed so the
    # pipeline reads top-down (first bucket at the top). Bar counts sum
    # count_by_status() over each bucket's raw-status tuple — "Archived"
    # aggregates [REJECTED] + [DECLINED] (DESIGN D17), other buckets map
    # one raw status each today.
    #
    # Bar colors come from FUNNEL_BUCKETS[i][2] — the BUCKET owns its
    # color because a bucket can aggregate multiple raw statuses
    # (STATUS_COLORS is for per-status surfaces: badges, tooltips).
    #
    # Visibility follows DESIGN §8.1 "Funnel visibility rules":
    #   - Default-visible: buckets whose label is NOT in FUNNEL_DEFAULT_HIDDEN.
    #   - When the user has clicked the disclosure toggle and
    #     st.session_state["_funnel_expanded"] is True: every bucket is
    #     visible for the current session (until they click again to
    #     collapse).
    #   State flag: st.session_state["_funnel_expanded"] — False by default.
    #
    # Disclosure toggle (T6 amendment, DESIGN §8.1):
    #   - Single `st.button(type="tertiary")` placed in the funnel
    #     subheader row via `st.columns([3, 1])` (subheader left, toggle
    #     right) — same idiom as the Upcoming panel's window selector.
    #   - Bidirectional: clicking from collapsed → expand; clicking from
    #     expanded → collapse. Solves the pre-T6 dead-end where
    #     `[expand]` had no companion `[collapse]` and the only way back
    #     to the focused view was a fresh session.
    #   - Label sourced from config.FUNNEL_TOGGLE_LABELS keyed by the
    #     state flag — describes what the click WILL do, not the
    #     current state.
    #   - Suppressed in branch (a) (nothing to disclose into) and when
    #     FUNNEL_DEFAULT_HIDDEN is empty (no buckets to hide). Otherwise
    #     the toggle persists across collapsed/expanded states so the
    #     user always has a return path.
    #
    # Three empty-state branches, evaluated in order (DESIGN §8.1):
    #   (a) total == 0 (no positions at all): info, NO toggle, bare
    #       subheader (no [3,1] split — nothing to dock in the right slot).
    #   (b) total > 0, not expanded, every non-hidden bucket is zero:
    #       info pointing at the toggle by LABEL ("Click 'Show all stages'
    #       to reveal them.") + toggle in the subheader row. Terminal-only
    #       DBs land here.
    #   (c) otherwise: render chart; toggle in the subheader row whenever
    #       FUNNEL_DEFAULT_HIDDEN is non-empty (in BOTH collapsed and
    #       expanded states — see toggle bullet above).
    # Subheader renders in ALL three branches for page-height stability.

    # Initialize the session flag once per session via setdefault so tests
    # (and the first render) see the canonical False rather than a KeyError.
    st.session_state.setdefault("_funnel_expanded", False)
    _funnel_expanded = st.session_state["_funnel_expanded"]

    def _toggle_funnel() -> None:
        """on_click callback — flips the flag BEFORE the next rerun so
        the funnel branches evaluate with the new value in the very
        same rerun (a plain `if st.button(): set state; st.rerun()`
        would need an extra pass and risks briefly drawing the old
        chart). Bidirectional: True ↔ False on each click."""
        st.session_state["_funnel_expanded"] = not st.session_state["_funnel_expanded"]

    # Per-bucket aggregated counts. A sparse-dict lookup (count_by_status
    # omits zero-count statuses) is fine — missing raws contribute 0.
    _bucket_counts: list[tuple[str, int, str]] = [
        (
            label,
            sum(_status_counts.get(raw, 0) for raw in raws),
            color,
        )
        for label, raws, color in config.FUNNEL_BUCKETS
    ]
    _total = sum(count for _, count, _ in _bucket_counts)

    # Branch (b) predicate — evaluated only when total > 0. "All non-zero
    # buckets are hidden" = every default-visible bucket has count 0.
    _all_visible_buckets_zero = all(
        count == 0
        for label, count, _ in _bucket_counts
        if label not in config.FUNNEL_DEFAULT_HIDDEN
    )

    # Toggle visibility predicate. Branch (a) is the only branch that
    # suppresses the toggle entirely (see comment block above); a
    # FUNNEL_DEFAULT_HIDDEN-empty config also suppresses it (nothing to
    # disclose, even when data is present). Computed before the branch
    # if/elif so the subheader-row layout uses one consistent rule.
    _show_funnel_toggle = (_total > 0) and bool(config.FUNNEL_DEFAULT_HIDDEN)

    if _show_funnel_toggle:
        # Branches (b) and (c): subheader-row layout with toggle on the right.
        # Mirrors the T4 Upcoming-panel idiom for chart-with-controls panels.
        _funnel_header_col, _funnel_toggle_col = st.columns([3, 1])
        with _funnel_header_col:
            st.subheader("Application Funnel")
        with _funnel_toggle_col:
            st.button(
                config.FUNNEL_TOGGLE_LABELS[_funnel_expanded],
                key="funnel_toggle",
                on_click=_toggle_funnel,
                type="tertiary",
            )
    else:
        # Branch (a) (or a hypothetical FUNNEL_DEFAULT_HIDDEN-empty
        # config): bare subheader, no [3,1] split — leaving the right
        # slot empty would render an awkward dead column.
        st.subheader("Application Funnel")

    if _total == 0:
        # Branch (a): no data anywhere — nothing to disclose into.
        st.info("Application funnel will appear once you've added positions.")
    elif (not _funnel_expanded) and _all_visible_buckets_zero:
        # Branch (b): data exists but all of it sits in hidden buckets.
        # Info copy points at the toggle by LABEL (not by spatial
        # direction "above" / "below") — DESIGN §8.1 T6 amendment — so
        # the copy stays correct regardless of where the toggle sits
        # relative to the info block.
        st.info("All your positions are in hidden buckets. Click 'Show all stages' to reveal them.")
    else:
        # Branch (c): render the chart.
        _visible_buckets = [
            (label, count, color)
            for label, count, color in _bucket_counts
            if _funnel_expanded or label not in config.FUNNEL_DEFAULT_HIDDEN
        ]
        _funnel_fig = go.Figure(
            data=[
                go.Bar(
                    x=[count for _, count, _ in _visible_buckets],
                    y=[label for label, _, _ in _visible_buckets],
                    orientation="h",
                    marker_color=[color for _, _, color in _visible_buckets],
                )
            ]
        )
        # Plotly renders horizontal bars bottom-to-top by default. Reverse
        # so the first visible bucket sits at the top (pipeline reads
        # top-down — same reasoning as pre-Sub-task-12, just bucket-scoped).
        _funnel_fig.update_yaxes(autorange="reversed")
        st.plotly_chart(_funnel_fig, key="funnel_chart")
        # The toggle has already been rendered above in the subheader row
        # (whenever `_show_funnel_toggle` is True); branch (c) does not
        # render its own button — that's the post-T6 placement contract.

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
            "Materials readiness will appear once you've added positions with required documents."
        )
    else:
        _total = max(_ready + _pending, 1)
        st.progress(_ready / _total, text=f"Ready to submit: {_ready}")
        st.progress(_pending / _total, text=f"Still missing: {_pending}")
        if st.button("→ Opportunities page", key="materials_readiness_cta"):
            st.switch_page("pages/1_Opportunities.py")

# ── Upcoming (T4) ─────────────────────────────────────────────────────────────
# Full-width panel BELOW the funnel/readiness st.columns(2) row, surfacing the
# merged upcoming feed (deadlines + interviews) from database.get_upcoming()
# (T4-A). DESIGN §8.1 + T4-0/T4-0b lock-down.
#
# Layout: an st.columns([3, 1]) pair carries the dynamic subheader on the left
# and the window-width selectbox on the right. Defining selected_window inside
# the right column first means the left column can interpolate it into the
# subheader on the same render — Python execution order is independent of
# visual placement, which is determined by column index.
#
# Display contract (DESIGN §8.1 "Upcoming-panel column contract"):
#   - Six columns renamed from T4-A's lowercase storage form:
#     date → Date (datetime.date, rendered 'Apr 24' via DateColumn(format="MMM D"))
#     days_left → Days left ('today' / 'in 1 day' / 'in N days')
#     label → Label ('{institute}: {position_name}' or bare position_name)
#     kind → Kind ('Deadline for application' or 'Interview N')
#     status → Status (mapped through STATUS_LABELS — DESIGN §8.0 strips
#              the bracketed sentinel; '.get' default keeps an unrecognised
#              status visible rather than producing NaN)
#     urgency → Urgency ('🔴' / '🟡' / '')
#   - Subheader 'Upcoming (next X days)' renders in BOTH branches for
#     page-height stability (T2/T3 precedent — without this, the layout
#     above shifts when the first qualifying row lands).
#   - Empty-state copy interpolates the selected window so the message
#     stays coherent under any user choice.
_header_col, _control_col = st.columns([3, 1])
with _control_col:
    selected_window = st.selectbox(
        "Window (days)",
        options=config.UPCOMING_WINDOW_OPTIONS,
        index=config.UPCOMING_WINDOW_OPTIONS.index(config.DEADLINE_ALERT_DAYS),
        key="upcoming_window",
        label_visibility="collapsed",
    )
with _header_col:
    st.subheader(f"Upcoming (next {selected_window} days)")

_upcoming = database.get_upcoming(days=selected_window)
if _upcoming.empty:
    st.info(f"No deadlines or interviews in the next {selected_window} days.")
else:
    _upcoming_display = _upcoming.rename(
        columns={
            "date": "Date",
            "days_left": "Days left",
            "label": "Label",
            "kind": "Kind",
            "status": "Status",
            "urgency": "Urgency",
        }
    )
    # Storage uses bracketed sentinels; UI strips them via STATUS_LABELS.
    # `.get(raw, raw)` keeps a stale value visible rather than producing NaN —
    # defensive belt-and-suspenders against an unrecognised status.
    _upcoming_display["Status"] = _upcoming_display["Status"].map(
        lambda raw: config.STATUS_LABELS.get(raw, raw)
    )
    st.dataframe(
        _upcoming_display,
        width="stretch",
        hide_index=True,
        column_config={
            "Date": st.column_config.DateColumn(format="MMM D"),
        },
    )

# ── Recommender Alerts (T5) ───────────────────────────────────────────────────
# Full-width panel BELOW the Upcoming row. Surfaces every recommender whose
# letter is past `RECOMMENDER_ALERT_DAYS` of being asked and still has no
# `submitted_date`. DESIGN §8.1 + TASKS.md T5-A locked contract:
#
#   - Subheader 'Recommender Alerts' renders in BOTH branches for page-height
#     stability (T2 / T3 / T4 precedent).
#   - Empty branch: st.info("No pending recommender follow-ups.").
#   - Populated branch: one st.container(border=True) per distinct
#     recommender_name (groupby aggregates a person's multiple-letter cases
#     into one card). Each card body is a single st.markdown call:
#       **⚠ {Name}**
#       - {institute}: {position_name} (asked {N}d ago, due {Mon D})
#       - ...
#     Bare {position_name} when institute is empty (T4 Label precedent);
#     'due —' (em dash) for NULL deadline (mirrors `config.EM_DASH`).
#
# The Compose-reminder-email button + LLM-prompts expander (DESIGN §8.4 D-C)
# live on the Recommenders PAGE (Phase 5 T6), NOT here — T5 only renders the
# alert cards.
st.subheader("Recommender Alerts")
_pending_recs = database.get_pending_recommenders()
if _pending_recs.empty:
    st.info(config.EMPTY_PENDING_RECOMMENDER_FOLLOWUPS)
else:
    _today = date.today()

    def _format_label(institute: str | None, position_name: str) -> str:
        """T4 Label precedent — '{institute}: {position_name}' when
        institute is non-empty; bare position_name otherwise. _safe-str
        coercion isn't needed here because get_pending_recommenders
        already returns Python strings (or None) from the SQL projection;
        pandas surfaces missing TEXT cells as None, which `or` treats as
        falsy alongside empty string."""
        if institute:
            return f"{institute}: {position_name}"
        return position_name

    def _format_due(deadline_iso: str | None) -> str:
        """Due-date in 'Mon D' form (T4 DateColumn precedent — no year,
        since alerts surface near-future deadlines). ``config.EM_DASH``
        for NULL — pd.isna catches both None and NaN-from-pandas
        (dev-notes gotcha #13)."""
        if deadline_iso is None or pd.isna(deadline_iso) or deadline_iso == "":
            return config.EM_DASH
        d = date.fromisoformat(deadline_iso)
        return f"{d.strftime('%b')} {d.day}"

    # Stable iteration order: get_pending_recommenders() already sorts by
    # recommender_name ASC, deadline_date ASC NULLS LAST, so a plain groupby
    # preserves both within-group order (deadline-asc) and across-group
    # alphabetical order without any extra sort.
    for _name, _group in _pending_recs.groupby("recommender_name", sort=False):
        with st.container(border=True):
            _bullets = []
            for _, _row in _group.iterrows():
                _inst: Any = _row["institute"]
                _pos_name: Any = _row["position_name"]
                _label = _format_label(_inst, str(_pos_name))
                _asked_iso: str = str(_row["asked_date"])
                _days_ago = (_today - date.fromisoformat(_asked_iso)).days
                _due_raw: Any = _row["deadline_date"]
                _due = _format_due(_due_raw)
                _bullets.append(f"- {_label} (asked {_days_ago}d ago, due {_due})")
            _body = f"**⚠ {_name}**\n" + "\n".join(_bullets)
            st.markdown(_body)
