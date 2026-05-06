# Streamlit entry point — dashboard home page.
#

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

# ── Visual polish (CSS injection) ─────────────────────────────────────────────
# Injected once per session. Uses stable data-testid selectors (Streamlit 1.57).
# All widget contracts stay unchanged — this is purely presentational.
st.markdown(
    """
<style>
/* ── Typography ─────────────────────────────────────────────────── */
/* Set font on root elements only — no child wildcard (*). The system font
   cascades naturally to text nodes. Avoiding * + !important on children
   preserves Streamlit's Material Symbols Rounded font on icon elements
   (sidebar collapse arrows, etc.) which use ligature rendering. */
html, body {
    font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text',
                 'Segoe UI Variable', 'Segoe UI', Helvetica, Arial, sans-serif !important;
}

/* ── KPI metric cards — elevated card style ───────────────────── */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #eef2f7;
    border-radius: 14px;
    padding: 1.1rem 1.4rem 0.9rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 6px 20px rgba(0,0,0,0.04);
}
[data-testid="stMetricLabel"] p {
    font-size: 0.70rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    color: #94a3b8 !important;
    font-weight: 700 !important;
}
[data-testid="stMetricValue"] > div {
    font-size: 2rem !important;
    font-weight: 800 !important;
    color: #0f172a !important;
    line-height: 1.2 !important;
    overflow-wrap: break-word !important;
    word-break: break-word !important;
}

/* ── Hero container — soft indigo gradient ────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] > div > div {
    border-radius: 14px !important;
    background: linear-gradient(135deg, #f8faff 0%, #eef4ff 100%) !important;
    border-color: #d9e4ff !important;
}

/* ── Section subheaders ──────────────────────────────────────── */
[data-testid="stHeadingWithActionElements"] h3 {
    font-weight: 700 !important;
    color: #1e293b !important;
    letter-spacing: -0.01em !important;
}

/* ── Info / empty-state messages ─────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px;
    border-left-width: 3px;
}

/* ── Dataframe / table outer container ────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    border: 1px solid #eef2f7 !important;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

/* ── Primary buttons ─────────────────────────────────────────── */
[data-testid="stBaseButton-primary"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
}

/* ── Sidebar navigation pills ───────────────────────────────── */
section[data-testid="stSidebarNav"] a {
    border-radius: 8px;
    padding: 0.35rem 0.7rem;
    margin-bottom: 2px;
    transition: background 0.15s, color 0.15s;
    font-weight: 500;
}
section[data-testid="stSidebarNav"] a:hover {
    background: rgba(79, 107, 239, 0.08);
    color: #4F6BEF;
}
section[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(79, 107, 239, 0.10);
    color: #4F6BEF;
    font-weight: 600;
}

/* ── Dividers ──────────────────────────────────────────────── */
hr {
    border-color: #f0f3f8 !important;
    margin: 0.5rem 0 !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _next_interview_display(upcoming: pd.DataFrame) -> str:
    """Format the Next-Interview KPI value from get_upcoming_interviews().

    Behaviour:
      - Pick the EARLIEST future scheduled_date across all upcoming
        interviews.
      - The paired institute belongs to whichever position owns that date.
      - Render as '{Mon D} · {institute}' (short month + day, no year).
      - Empty / no upcoming date → ``config.EM_DASH`` ('—').

    Rows from the normalized interviews sub-table (DESIGN §6.2) carry
    future dates (the SQL filters on `scheduled_date >= today`)
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
# is cognitive noise for the common case.
st.title("Academic Application Tracker")
st.caption(
    "Your complete academic job search — deadlines, applications, and letters, all in one place."
)
# Gradient accent line — brand identity mark below the title.
st.markdown(
    "<div style='height:3px;background:linear-gradient(90deg,#4F6BEF 0%,"
    "#8B5CF6 50%,#10B981 100%);border-radius:2px;margin-bottom:0.25rem;'></div>",
    unsafe_allow_html=True,
)

# ── KPI row ───────────────────────────────────────────────────────────────────
# Four equal columns per DESIGN.md §app.py. Labels are the UI contract.
# Tracked = saved + applied — "opportunities that might get moved forward".
# Applied and Interview are single-bucket counts of their namesake status.
# Next Interview = earliest future scheduled_date across all rows of
# database.get_upcoming_interviews() (DESIGN §6.2), rendered '{Mon D} · {institute}'; '—' when none.
# All status literals via config.STATUS_* aliases.
_status_counts = database.count_by_status()
tracked = _status_counts.get(config.STATUS_SAVED, 0) + _status_counts.get(config.STATUS_APPLIED, 0)
applied = _status_counts.get(config.STATUS_APPLIED, 0)
interview = _status_counts.get(config.STATUS_INTERVIEW, 0)
next_interview = _next_interview_display(database.get_upcoming_interviews())

# ── Empty-DB hero ────────────────────────────────────────────────────────────
# When the counted KPI buckets are all zero, show a hero
# panel above the KPI grid with a CTA that routes to the Opportunities page.
# The grid still renders below. A DB with only terminal-status rows also
# triggers this; narrowing to 'total positions == 0' would require updating
# `test_terminal_only_db_still_shows_hero`.
if tracked == 0 and applied == 0 and interview == 0:
    with st.container(border=True):
        st.subheader("Get started")
        st.markdown(
            "You haven't added any positions yet. "
            "Start by adding one — even partial details count — "
            "and your application pipeline will appear here."
        )
        if st.button(
            "+ Add your first position",
            key="dashboard_empty_cta",
            type="primary",
        ):
            st.switch_page("pages/1_Opportunities.py")

# 4th column (Next Interview) gets extra width because its value can be
# a long string like 'May 3 · Stanford University'.
c1, c2, c3, c4 = st.columns([1, 1, 1, 1.5])
with c1:
    # DESIGN §8.1 locks the Tracked KPI's help-tooltip string — explains
    # the Saved + Applied arithmetic on hover so the reader doesn't have
    # to guess what "tracked" means here.
    st.metric(
        label="Tracked",
        value=str(tracked),
        help="Positions in your active pipeline before interview stage (Saved + Applied)",
    )
with c2:
    st.metric(label="Applied", value=str(applied))
with c3:
    st.metric(label="Interview", value=str(interview))
with c4:
    st.metric(label="Next Interview", value=next_interview)

# ── Funnel + Readiness row ───────────────────────────────────────────────────
# Two equal-width columns: Application Funnel on the
# left, Materials Readiness on the right. The split is created once here and reused so
# the dashboard stays a single 2-column row (no second `st.columns(2)` call).
_left_col, _right_col = st.columns(2)

with _left_col:
    # ── Application Funnel ──────────────────────────────────────────────────────
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
    # Disclosure toggle (DESIGN §8.1):
    #   - Single `st.button(type="tertiary")` placed in the funnel
    #     subheader row via `st.columns([3, 1])` (subheader left, toggle
    #     right) — same idiom as the Upcoming panel's window selector.
    #   - Bidirectional: clicking collapsed → expand, or expanded → collapse.
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
        st.info("The Application Funnel will appear once you've added positions.")
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
        # Colors come directly from config.FUNNEL_BUCKETS[i][2] — the
        # polished hex palette is defined there (per the test contract:
        # "a future color tweak should live in config.FUNNEL_BUCKETS").
        _funnel_fig = go.Figure(
            data=[
                go.Bar(
                    x=[count for _, count, _ in _visible_buckets],
                    y=[label for label, _, _ in _visible_buckets],
                    orientation="h",
                    marker_color=[color for _, _, color in _visible_buckets],
                    marker_line_width=0,
                    text=[str(count) if count else "" for _, count, _ in _visible_buckets],
                    textposition="outside",
                    textfont=dict(size=13, color="#374151"),
                )
            ]
        )
        # Plotly renders horizontal bars bottom-to-top by default. Reverse
        # so the first visible bucket sits at the top (pipeline reads top-down).
        _funnel_fig.update_yaxes(autorange="reversed")
        _funnel_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=40, t=8, b=4),
            font=dict(
                family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                size=13,
            ),
            xaxis=dict(
                gridcolor="#f0f2f6",
                zeroline=False,
                tickfont=dict(size=11, color="#94a3b8"),
                # Force integer-only ticks so the axis never shows 0.5 or 1.5
                # when there are only a few positions.
                dtick=1,
                tick0=0,
                tickmode="linear",
                rangemode="tozero",
            ),
            yaxis=dict(
                showgrid=False,
                tickfont=dict(size=13, color="#374151"),
            ),
            height=230,
            bargap=0.35,
        )
        st.plotly_chart(
            _funnel_fig,
            key="funnel_chart",
            config={"displayModeBar": False},
        )
        # The toggle is already rendered in the subheader row above; branch (c)
        # does not render its own button.

with _right_col:
    # ── Materials Readiness ───────────────────────────────────────────────────
    # Two stacked st.progress bars — one for positions whose required docs
    # are all done, one for positions still missing at least one. Readiness
    # is active-pipeline-only by definition (see compute_materials_readiness),
    # so a DB with only terminal-status rows returns 0/0 and we show the
    # empty state. Denominator guarded via max(..., 1);
    # strictly speaking unnecessary inside the else-branch (both counts are
    # zero → we take the if-branch), but the explicit guard keeps the
    # contract close to the code for a future reader.
    #
    # Subheader renders in BOTH branches so page height doesn't flicker when
    # the first qualifying position lands (same stability pattern as the
    # funnel subheader).
    st.subheader("Materials Readiness")
    _readiness = database.compute_materials_readiness()
    _ready = _readiness["ready"]
    _pending = _readiness["pending"]
    if _ready + _pending == 0:
        st.info(
            "Materials readiness will appear once you've added positions with required documents."
        )
    else:
        # Plotly horizontal bar chart — same visual language as Application
        # Funnel (matching bar thickness, colors, layout, no toolbar).
        # height=120 gives ~39px bars with bargap=0.35 for 2 rows, close
        # to the funnel's ~37px bars for 4 rows at height=230.
        _pos_word_r = "position" if _ready == 1 else "positions"
        _pos_word_i = "position" if _pending == 1 else "positions"
        _mat_fig = go.Figure(
            data=[
                go.Bar(
                    x=[_ready, _pending],
                    y=["Ready to submit", "Incomplete"],
                    orientation="h",
                    marker_color=["#10B981", "#94A3B8"],
                    marker_line_width=0,
                    text=[
                        f"{_ready} {_pos_word_r}",
                        f"{_pending} {_pos_word_i}",
                    ],
                    textposition="outside",
                    textfont=dict(size=13, color="#374151"),
                )
            ]
        )
        _mat_fig.update_yaxes(autorange="reversed")
        _mat_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=80, t=4, b=4),
            font=dict(
                family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
                size=13,
            ),
            xaxis=dict(
                gridcolor="#f0f2f6",
                zeroline=False,
                tickfont=dict(size=11, color="#94a3b8"),
                dtick=1,
                tick0=0,
                tickmode="linear",
                rangemode="tozero",
            ),
            yaxis=dict(
                showgrid=False,
                tickfont=dict(size=13, color="#374151"),
            ),
            height=120,
            bargap=0.35,
        )
        st.plotly_chart(
            _mat_fig,
            key="materials_chart",
            config={"displayModeBar": False},
        )
        if st.button("→ Review in Opportunities", key="materials_readiness_cta"):
            st.switch_page("pages/1_Opportunities.py")

# ── Upcoming ─────────────────────────────────────────────────────────────────
# Full-width panel BELOW the funnel/readiness st.columns(2) row, surfacing the
# merged upcoming feed (deadlines + interviews) from database.get_upcoming().
# DESIGN §8.1.
#
# Layout: an st.columns([3, 1]) pair carries the dynamic subheader on the left
# and the window-width selectbox on the right. Defining selected_window inside
# the right column first means the left column can interpolate it into the
# subheader on the same render — Python execution order is independent of
# visual placement, which is determined by column index.
#
# Display contract (DESIGN §8.1 "Upcoming-panel column contract"):
#   - Six columns renamed from storage-form names:
#     date → Date (datetime.date, rendered 'Apr 24' via DateColumn(format="MMM D"))
#     days_left → Days left ('today' / 'in 1 day' / 'in N days')
#     label → Label ('{institute}: {position_name}' or bare position_name)
#     kind → Kind ('Deadline for application' or 'Interview N')
#     status → Status (mapped through STATUS_LABELS — DESIGN §8.0 strips
#              the bracketed sentinel; '.get' default keeps an unrecognised
#              status visible rather than producing NaN)
#     urgency → Urgency ('🔴' / '🟡' / '' / '—' for no deadline)
#   - Subheader 'Upcoming (next X days)' renders in BOTH branches for
#     page-height stability (without this, the layout
#     above shifts when the first qualifying row lands).
#   - Empty-state copy interpolates the selected window so the message
#     stays coherent under any user choice.
st.divider()
_header_col, _control_col = st.columns([3, 1])
with _control_col:
    # Segmented control shows '30d | 60d | 90d' pill buttons — cleaner
    # than a dropdown, and avoids a redundant number in the header.
    # Returns None on first render if no default is applied yet; the
    # `or` fallback keeps selected_window an int in all cases.
    selected_window = (
        st.segmented_control(
            "Window",
            options=config.UPCOMING_WINDOW_OPTIONS,
            default=config.DEADLINE_ALERT_DAYS,
            key="upcoming_window",
            format_func=lambda x: f"{x}d",
            label_visibility="collapsed",
        )
        or config.DEADLINE_ALERT_DAYS
    )
with _header_col:
    st.subheader(f"Upcoming (next {selected_window} days)")

_upcoming = database.get_upcoming(days=selected_window)
if _upcoming.empty:
    st.info(f"No deadlines or interviews in the next {selected_window} days.")
else:
    _today = date.today()
    _upcoming_display = pd.DataFrame(
        {
            "Date": _upcoming["date"],
            "Days Left": _upcoming["days_left"],
            "Label": _upcoming["label"],
            "Kind": _upcoming["kind"],
            "Status": _upcoming["status"].map(lambda raw: config.STATUS_LABELS.get(raw, raw)),
            # Numeric days remaining drives ProgressColumn below.
            # Rows without a deadline (interviews with no scheduled_date)
            # fall back to selected_window so their bar is full (not urgent).
            "Urgency": _upcoming["date"].apply(
                lambda d: max(0, (d - _today).days) if pd.notna(d) else selected_window
            ),
        }
    )
    st.dataframe(
        _upcoming_display,
        width="stretch",
        hide_index=True,
        column_config={
            "Date": st.column_config.DateColumn(
                "Date",
                format="MMM D",
                help="Deadline or scheduled interview date",
            ),
            "Days Left": st.column_config.TextColumn(
                "Days Left",
                width="small",
                help="Time remaining until this event",
            ),
            "Label": st.column_config.TextColumn(
                "Label",
                width="large",
                help="Position and institution",
            ),
            "Kind": st.column_config.TextColumn(
                "Kind",
                width="medium",
                help="'Deadline for application' or interview sequence number",
            ),
            "Status": st.column_config.TextColumn(
                "Status",
                width="small",
                help="Current pipeline stage",
            ),
            "Urgency": st.column_config.ProgressColumn(
                "Urgency",
                min_value=0,
                max_value=selected_window,
                format="%d d",
                help="Days remaining — shorter bar = more urgent",
            ),
        },
    )

# ── Recommender Alerts ───────────────────────────────────────────────────────
# Full-width panel BELOW the Upcoming row. Surfaces every recommender whose
# letter is past `RECOMMENDER_ALERT_DAYS` of being asked and still has no
# `submitted_date`. DESIGN §8.1:
#
#   - Subheader 'Recommender Alerts' renders in BOTH branches for page-height
#     stability.
#   - Empty branch: st.info("No pending recommender follow-ups.").
#   - Populated branch: one st.container(border=True) per distinct
#     recommender_name (groupby aggregates a person's multiple-letter cases
#     into one card). Each card body is a single st.markdown call:
#       **⚠ {Name}**
#       - {institute}: {position_name} (asked {N}d ago, due {Mon D})
#       - ...
#     Bare {position_name} when institute is empty;
#     'due —' (em dash) for NULL deadline (mirrors `config.EM_DASH`).
#
# The Compose-reminder-email button + LLM-prompts expander (DESIGN §8.4 D-C)
# live on the Recommenders PAGE, NOT here — this panel only renders the
# alert cards.
st.divider()
st.subheader("Recommender Alerts")
_pending_recs = database.get_pending_recommenders()
if _pending_recs.empty:
    st.info(config.EMPTY_PENDING_RECOMMENDER_FOLLOWUPS)
else:
    _today = date.today()

    def _format_label(institute: str | None, position_name: str) -> str:
        """Format as '{institute}: {position_name}' when
        institute is non-empty; bare position_name otherwise. _safe-str
        coercion isn't needed here because get_pending_recommenders
        already returns Python strings (or None) from the SQL projection;
        pandas surfaces missing TEXT cells as None, which `or` treats as
        falsy alongside empty string."""
        if institute:
            return f"{institute}: {position_name}"
        return position_name

    def _format_due(deadline_iso: str | None) -> str:
        """Due-date in 'Mon D' form (no year, since alerts surface
        near-future deadlines). ``config.EM_DASH`` for NULL —
        pd.isna catches both None and NaN-from-pandas."""
        if deadline_iso is None or pd.isna(deadline_iso) or deadline_iso == "":
            return config.EM_DASH
        d = date.fromisoformat(deadline_iso)
        return f"{d.strftime('%b')} {d.day}"

    # groupby preserves the sort order of get_pending_recommenders()
    # (recommender_name ASC, deadline_date ASC NULLS LAST).
    for _name, _group in _pending_recs.groupby("recommender_name", sort=False):
        with st.container(border=True):
            _rel = str(_group.iloc[0]["relationship"] or "")
            _rel_str = f" ({_rel})" if _rel else ""
            _bullets = []
            for _, _row in _group.iterrows():
                _inst: Any = _row["institute"]
                _pos_name: Any = _row["position_name"]
                _label = _format_label(_inst, str(_pos_name))
                _asked_iso: str = str(_row["asked_date"])
                _days_ago = (_today - date.fromisoformat(_asked_iso)).days
                _due_raw: Any = _row["deadline_date"]
                _due = _format_due(_due_raw)
                _bullets.append(f"- {_label} (asked {_days_ago} days ago, due {_due})")
            _body = f"⚠️ **{_name}**{_rel_str}\n" + "\n".join(_bullets)
            st.markdown(_body)
