# pages/2_Applications.py
# Applications page — submission/response/interview/result tracking per
# position. DESIGN §8.3.
#
# Phase 5 T1 ships the page shell — set_page_config, title, status filter
# bar, and the read-only Applications table sorted by deadline.
# Phase 5 T2-A adds the editable detail card: row selection on the table
# reveals a bordered container holding (1) a read-only header
# `f'{institute}: {position_name} · {STATUS_LABELS[raw]}'`, (2) an
# inline `All recs submitted: ✓ / —` line via
# `database.is_all_recs_submitted`, and (3) an `apps_detail_form` with
# 8 widgets (`apps_applied_date`, `apps_confirmation_received` checkbox,
# `apps_confirmation_date`, `apps_response_type` selectbox over
# `[None, *RESPONSE_TYPES]`, `apps_response_date`, `apps_result`
# selectbox over `RESULT_VALUES`, `apps_result_notify_date`,
# `apps_notes` text_area). Save calls
# `database.upsert_application(propagate_status=True)`; the R1/R3
# cascade-promotion toast lands in T2-B.
#
# T3 will add an inline interview list as a SIBLING form
# (`apps_interviews_form`) inside the same `st.container(border=True)`
# — see DESIGN §8.3 D-B.

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


def _coerce_iso_to_date(v: Any) -> datetime.date | None:
    """Coerce a stored ISO ``YYYY-MM-DD`` string to a ``datetime.date``
    for ``st.date_input`` pre-seed; return ``None`` for None / NaN /
    empty / unparseable.

    Date inputs accept ``value=None`` (renders an empty picker) and
    real ``datetime.date`` instances; they reject NaN, ``""``, and
    ISO strings (the widget itself does no parsing). The Opportunities
    page guards the same case via its F5 fix — a single malformed
    deadline cell would otherwise crash the whole page on
    `date.fromisoformat(...)`. Swallow that error so the widget renders
    empty and the user fixes the cell rather than seeing a traceback."""
    s = _safe_str(v)
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        return None


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
# wireframe columns; render via st.dataframe.
#
# T2-A: the table is selectable (`on_select='rerun'`,
# `selection_mode='single-row'`); the selection-resolution block below
# captures `applications_selected_position_id` for the detail card.
#
# Empty post-filter → info AND keep any `applications_selected_position_id`
# in session_state. **Asymmetry vs. Opportunities §8.2**, which pops
# selection on `df_filtered.empty` to dismiss a stale edit panel: the
# Applications-page detail card is intentionally tied to the *unfiltered*
# df, so a filter narrowing that excludes the selected row keeps the
# in-progress edit visible (DESIGN §8.3 — same principle as Opportunities
# uses for the unfiltered-`df` lookup, but applied here at the
# selection-popping site so the asymmetry is at the input layer).

df = database.get_applications_table()

if selected_filter == config.STATUS_FILTER_ACTIVE:
    df_filtered = df[~df["status"].isin(config.STATUS_FILTER_ACTIVE_EXCLUDED)]
elif selected_filter == _FILTER_ALL:
    df_filtered = df
else:
    df_filtered = df[df["status"] == selected_filter]

if df_filtered.empty:
    st.info("No applications match the current filter.")
    # Asymmetry vs. Opportunities §8.2: do NOT pop
    # applications_selected_position_id here. The detail card below
    # resolves against the unfiltered `df`, so an in-progress edit
    # survives a filter narrowing.
else:
    # Build the six display columns by applying per-row formatters to
    # the raw reader columns. Index resets so the display DataFrame
    # has its own positional order — `st.dataframe(hide_index=True)`
    # then suppresses the integer index column entirely. Reset on
    # df_filtered too, so iloc[selected_row] in the resolution block
    # below maps to the same row as event.selection.rows[0].
    df_filtered = df_filtered.reset_index(drop=True)
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

    # T2-A: column_config locks per-column widths so the selectable
    # table doesn't collapse to equal-width cells. AppTest can't see
    # column_config (gotcha #15 — the protobuf serializes the data,
    # not the construction kwargs), so the contract is pinned via
    # source-grep in TestApplicationsTableColumnConfig.
    event = st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Position":     st.column_config.TextColumn("Position",     width="large"),
            "Applied":      st.column_config.TextColumn("Applied",      width="small"),
            "Recs":         st.column_config.TextColumn("Recs",         width="small"),
            "Confirmation": st.column_config.TextColumn("Confirmation", width="medium"),
            "Response":     st.column_config.TextColumn("Response",     width="small"),
            "Result":       st.column_config.TextColumn("Result",       width="small"),
        },
        key="apps_table",
        on_select="rerun",
        selection_mode="single-row",
    )

    # T2-A: map the selected row index back to its DB position_id so
    # the detail card below can render. Mirror of Opportunities §8.2
    # selection-resolution structure; the elif branch consumes the
    # `_applications_skip_table_reset` one-shot to preserve selection
    # across the post-Save rerun (gotcha #11 — st.dataframe resets its
    # selection event on data-change reruns).
    selected_rows = list(event.selection.rows) if event is not None else []
    if selected_rows and 0 <= selected_rows[0] < len(df_filtered):
        new_sid = int(df_filtered.iloc[selected_rows[0]]["position_id"])
        st.session_state["applications_selected_position_id"] = new_sid
    elif st.session_state.pop("_applications_skip_table_reset", False):
        # One-shot consumed: the Save handler set this flag before
        # st.rerun(), so selected_position_id stays put while the
        # widget re-seeds from fresh DB values.
        pass
    else:
        # Empty selection on a real (non-empty) table → the user
        # clicked away. Pop both the selection key and the form-id
        # sentinel so the next pre-seed cycle starts clean.
        st.session_state.pop("applications_selected_position_id", None)
        st.session_state.pop("_applications_edit_form_sid", None)


# ── Detail card (T2-A) ────────────────────────────────────────────────────────
#
# Renders only when a row is selected. Uses the unfiltered `df` for the
# row lookup so a filter narrowing does not dismiss the in-progress
# edit (the asymmetry-vs-Opportunities note above is the input-side
# half of the same contract).
#
# `st.container(border=True)` is the outer wrapper — T3 adds a sibling
# `apps_interviews_form` inside the same container above the detail
# form (DESIGN §8.3 D-B). The container is intentionally architected
# to accept N siblings so T3's interleaving is a pure addition rather
# than a refactor of T2's container boundaries.

if "applications_selected_position_id" in st.session_state:
    sid = st.session_state["applications_selected_position_id"]
    selected_row = df[df["position_id"] == sid]
    if not selected_row.empty:
        r = selected_row.iloc[0]
        # `r` carries only the 10 columns from get_applications_table's
        # projection (T1-A contract): position_id, position_name,
        # institute, deadline_date, status, applied_date,
        # confirmation_received, confirmation_date, response_type,
        # result. The form needs response_date / result_notify_date /
        # notes too — read the full applications row separately rather
        # than widening the T1-A reader (its 10-col contract is pinned
        # by tests + DESIGN §8.3 + the merged review doc).
        app_row = database.get_application(sid)

        with st.container(border=True):
            # DESIGN §8.0 + §8.3 status-label convention: render
            # STATUS_LABELS[raw], never the bracketed storage value.
            # `.get(..., raw)` is the last-resort passthrough so an
            # un-labelled status (legacy DB / future migration) does
            # not crash with a KeyError — same defensive pattern as
            # Opportunities §8.2 edit-panel header.
            label = _format_label(r["institute"], r["position_name"])
            status_label = config.STATUS_LABELS.get(r["status"], r["status"])
            st.subheader(f"{label} · {status_label}")

            # Inline "All recs submitted" line — surfaces
            # `database.is_all_recs_submitted(sid)` (vacuous-true for
            # zero recs per D23). Uses the same ✓ / em-dash glyph pair
            # as the table's Recs column so the two stay coherent.
            recs_glyph = (
                "✓" if database.is_all_recs_submitted(sid) else EM_DASH
            )
            st.markdown(f"All recs submitted: {recs_glyph}")

            # ── Pre-seed widget state via the _applications_edit_form_sid
            # sentinel. Two-phase apply (gotcha #2 — once
            # session_state[key] is set, Streamlit ignores the widget's
            # `value=` argument, so pre-seed must happen via direct
            # session_state assignment):
            #   (a) Row CHANGE → force-overwrite every key (fresh row's
            #       data replaces the previously-cached values).
            #   (b) Same row, key missing → restore from canonical.
            #   (c) Same row, key present → leave alone (preserves the
            #       in-flight form draft / AppTest set_value semantics).
            # The Save handler pops this sentinel before st.rerun() so
            # the post-Save render fires branch (a) and re-seeds widgets
            # from the just-persisted DB values.
            sid_changed = (
                st.session_state.get("_applications_edit_form_sid") != sid
            )

            # F-style coercion (mirrors Opportunities §8.2 F2/F5 helpers)
            # so out-of-vocab / NULL cells never reach a widget in an
            # unsupported form. `app_row` is a dict from the sqlite3
            # row — `.get` returns None for absent / NULL cells.
            raw_response_type = app_row.get("response_type")
            safe_response_type = (
                raw_response_type if raw_response_type in config.RESPONSE_TYPES
                else None
            )
            raw_result = app_row.get("result")
            safe_result = (
                raw_result if raw_result in config.RESULT_VALUES
                else config.RESULT_DEFAULT
            )

            canonical: dict[str, Any] = {
                "apps_applied_date":          _coerce_iso_to_date(app_row.get("applied_date")),
                # confirmation_received is INTEGER 0/1; coerce via
                # bool() with `or 0` covering None — `bool(None or 0)`
                # is False; `bool(1 or 0)` is True.
                "apps_confirmation_received": bool(app_row.get("confirmation_received") or 0),
                "apps_confirmation_date":     _coerce_iso_to_date(app_row.get("confirmation_date")),
                "apps_response_type":         safe_response_type,
                "apps_response_date":         _coerce_iso_to_date(app_row.get("response_date")),
                "apps_result":                safe_result,
                "apps_result_notify_date":    _coerce_iso_to_date(app_row.get("result_notify_date")),
                "apps_notes":                 _safe_str(app_row.get("notes")),
            }
            for _key, _value in canonical.items():
                if sid_changed or _key not in st.session_state:
                    st.session_state[_key] = _value
            st.session_state["_applications_edit_form_sid"] = sid

            # Form id `apps_detail_form` ends in `_form` so it cannot
            # collide with any widget key inside (all widget keys are
            # `apps_<field>` — gotcha #4). Save batches every widget
            # change in the form into one DB write on submit.
            with st.form("apps_detail_form"):
                st.date_input("Applied date", value=None, key="apps_applied_date")

                conf_cols = st.columns(2)
                with conf_cols[0]:
                    st.checkbox(
                        "Confirmation received",
                        key="apps_confirmation_received",
                    )
                with conf_cols[1]:
                    st.date_input(
                        "Confirmation date",
                        value=None,
                        key="apps_confirmation_date",
                    )

                resp_cols = st.columns(2)
                with resp_cols[0]:
                    # Nullable selectbox: None is the explicit "no
                    # response yet" option, rendered as EM_DASH via
                    # format_func. Real RESPONSE_TYPES entries render
                    # as themselves.
                    st.selectbox(
                        "Response type",
                        options=[None, *config.RESPONSE_TYPES],
                        format_func=lambda v: EM_DASH if v is None else v,
                        key="apps_response_type",
                    )
                with resp_cols[1]:
                    st.date_input(
                        "Response date",
                        value=None,
                        key="apps_response_date",
                    )

                result_cols = st.columns(2)
                with result_cols[0]:
                    st.selectbox(
                        "Result",
                        options=config.RESULT_VALUES,
                        key="apps_result",
                    )
                with result_cols[1]:
                    st.date_input(
                        "Result notify date",
                        value=None,
                        key="apps_result_notify_date",
                    )

                st.text_area("Notes", key="apps_notes")

                detail_submitted = st.form_submit_button(
                    "Save", key="apps_detail_submit"
                )

        if detail_submitted:
            # Build the upsert payload. Date inputs return either
            # `datetime.date` or None; isoformat() handles only the
            # former, so guard with a truthiness check.
            applied_d   = st.session_state["apps_applied_date"]
            conf_d      = st.session_state["apps_confirmation_date"]
            resp_d      = st.session_state["apps_response_date"]
            result_n_d  = st.session_state["apps_result_notify_date"]
            fields: dict[str, Any] = {
                "applied_date":          applied_d.isoformat() if applied_d else None,
                "confirmation_received": int(st.session_state["apps_confirmation_received"]),
                "confirmation_date":     conf_d.isoformat() if conf_d else None,
                "response_type":         st.session_state["apps_response_type"],
                "response_date":         resp_d.isoformat() if resp_d else None,
                "result":                st.session_state["apps_result"],
                "result_notify_date":    result_n_d.isoformat() if result_n_d else None,
                "notes":                 st.session_state["apps_notes"],
            }
            try:
                # propagate_status=True fires R1 + R3 cascades inside
                # the same transaction; the returned indicator is
                # ignored here in T2-A (T2-B will surface a second
                # toast on `status_changed=True`).
                database.upsert_application(sid, fields, propagate_status=True)
                # Set the skip-flag BEFORE st.rerun() so the
                # selection-resolution block on the post-Save rerun
                # preserves applications_selected_position_id (gotcha
                # #11). Pop the form-id sentinel so the post-rerun
                # pre-seed re-fires branch (a) and refreshes widgets
                # from fresh DB values rather than the in-flight
                # session_state cache.
                st.session_state["_applications_skip_table_reset"] = True
                st.session_state.pop("_applications_edit_form_sid", None)
                st.toast(f'Saved "{r["position_name"]}".')
                st.rerun()
            except Exception as e:
                # GUIDELINES §8: surface failures via st.error, do NOT
                # re-raise (re-raise would render the very traceback
                # the handler exists to hide). Sentinel survives so
                # the user's dirty form input is preserved for retry.
                st.error(f"Could not save: {e}")
