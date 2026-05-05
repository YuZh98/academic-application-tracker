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
# `database.upsert_application(propagate_status=True)`.
# Phase 5 T2-B surfaces R1 / R3 pipeline promotions as a second
# `st.toast(f"Promoted to {STATUS_LABELS[new_status]}.")` after the
# Saved toast whenever `upsert_application` reports
# `status_changed=True` (DESIGN §9.3).
#
# Phase 5 T3 adds the inline interview list inside the same
# `st.container(border=True)` (DESIGN §8.3 D-B). T3-rev-B refactored
# the list architecture from a single page-level `apps_interviews_form`
# (Save batches every row in one click) to per-row blocks: each
# interview owns its own `apps_interview_{id}_form` (`border=False`)
# carrying heading + detail row + per-row Save submit, plus a per-row
# Delete button outside the form (Streamlit 1.56 forbids `st.button`
# inside `st.form`). Save commits ONLY the clicked row's dirty fields
# via `database.update_interview`; sibling rows' in-flight drafts
# survive the rerun via the per-row pre-seed sentinel
# `_apps_interviews_seeded_ids` (frozenset, intersection-pruned).

import datetime
import math
from typing import Any, cast

import pandas as pd
import streamlit as st

import config
import database
# Phase 7 cleanup CL2: EM_DASH lifted to config; re-export under the
# bare name so existing per-page references remain unchanged (every
# in-file site reads it; ruff won't flag F401).
from config import EM_DASH


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


@st.dialog("Delete this interview?")
def _confirm_interview_delete_dialog() -> None:
    """T3-B: modal confirm dialog for irreversible interview deletion
    (DESIGN §8.3 D-B). Mirrors the Opportunities-page
    `_confirm_delete_dialog` pattern.

    The target interview is read from session_state keys
    `_apps_interview_delete_target_id` (the row's primary key) and
    `_apps_interview_delete_target_seq` (the sequence number, used in
    the warning copy so the user knows which row is about to go).
    Passing via session_state — rather than function arguments — is
    load-bearing for the gotcha #3 re-open trick: the outer script
    re-invokes this dialog on every rerun while the pending sentinels
    are set, so AppTest's script-run model can reach the
    Confirm/Cancel handlers (Streamlit's own dialog auto-re-render
    magic does not carry through AppTest).

    Outcomes:

    • Confirm → `database.delete_interview(id)` (a leaf delete; no FK
      cascade — the `interviews` table is on the child side of the
      one FK in DESIGN §6.2). On success: pop both pending sentinels,
      set `_applications_skip_table_reset=True` so the dataframe-event-
      reset rerun preserves the position selection (gotcha #11),
      `st.toast(f"Deleted interview {seq}.")`, `st.rerun()` → dialog
      closes naturally on the next render (no pending sentinels).
    • Cancel → pop both pending sentinels, set
      `_applications_skip_table_reset=True` (preserves selection
      across the rerun), `st.rerun()`. No DB write.
    • Failure (delete raises) → `st.error(...)` per GUIDELINES §8;
      sentinels SURVIVE so the dialog re-opens on the next rerun
      and the user can retry. Mirrors the Opportunities-page
      failure-preserves-state precedent — there is no DB rollback to
      undo, the user just gets to try again.
    """
    iid: int | None = st.session_state.get(
        "_apps_interview_delete_target_id"
    )
    seq: int | None = st.session_state.get(
        "_apps_interview_delete_target_seq"
    )
    if iid is None:
        # Defensive: the post-loop guard already filters by
        # `pending_id in current_ids`, so this branch should be
        # unreachable in practice. Surfacing a friendly error keeps
        # behaviour graceful if a future refactor drops the guard.
        st.error("Delete target was lost — please re-open the dialog.")
        return

    st.warning(
        f"Interview {seq} will be permanently deleted. "
        f"This **cannot be undone**."
    )
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button(
            "Confirm Delete",
            type="primary",
            key="apps_interview_delete_confirm",
            width="stretch",
        ):
            try:
                database.delete_interview(iid)
                st.session_state["_applications_skip_table_reset"] = True
                st.session_state.pop(
                    "_apps_interview_delete_target_id", None,
                )
                st.session_state.pop(
                    "_apps_interview_delete_target_seq", None,
                )
                st.toast(f"Deleted interview {seq}.")
                st.rerun()
            except Exception as e:
                # GUIDELINES §8: friendly error, no re-raise. Sentinels
                # survive so the dialog re-opens on the next rerun for
                # retry — Opportunities-page failure-preserves-state
                # precedent.
                st.error(f"Could not delete interview: {e}")
    with col_cancel:
        if st.button(
            "Cancel",
            key="apps_interview_delete_cancel",
            width="stretch",
        ):
            st.session_state.pop(
                "_apps_interview_delete_target_id", None,
            )
            st.session_state.pop(
                "_apps_interview_delete_target_seq", None,
            )
            # _applications_skip_table_reset preserves the position
            # selection across the cancel-driven rerun (gotcha #11):
            # the dataframe widget would otherwise reset its event
            # and the selection-resolution else-branch would pop
            # `applications_selected_position_id`.
            st.session_state["_applications_skip_table_reset"] = True
            st.rerun()


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
# Phase 7 cleanup CL2 closed the previous "magic literal" carry-over —
# the "All" sentinel now lives on `config.FILTER_ALL` alongside
# STATUS_FILTER_ACTIVE, so all three pages reach for the same name.
selected_filter = st.selectbox(
    "Status",
    options=[
        config.STATUS_FILTER_ACTIVE,
        config.FILTER_ALL,
        *config.STATUS_VALUES,
    ],
    index=0,
    # CL1 type-clean (mirror of pages/1_Opportunities.py): wrap in
    # `str(...)` so format_func unambiguously returns `str`. Runtime
    # no-op — every option value is already a `str`.
    format_func=lambda v: str(config.STATUS_LABELS.get(v, v)),
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

# CL1 type-clean: pandas-stubs declares Series.isin with a Series /
# DataFrame / Sequence / Mapping union — `frozenset` doesn't satisfy
# any branch of that, so wrap in `list(...)` (runtime no-op for set
# membership). Same boolean-indexing widening as pages/1_Opportunities
# requires `cast(pd.DataFrame, ...)` on each branch's RHS so downstream
# `.reset_index` / `.apply` / `.iloc` / `.empty` access stays typed.
if selected_filter == config.STATUS_FILTER_ACTIVE:
    df_filtered = cast(
        pd.DataFrame,
        df[~df["status"].isin(list(config.STATUS_FILTER_ACTIVE_EXCLUDED))],
    )
elif selected_filter == config.FILTER_ALL:
    df_filtered = df
else:
    df_filtered = cast(pd.DataFrame, df[df["status"] == selected_filter])

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
    # T3-rev-A: split the previously-combined Position cell into TWO
    # cells per DESIGN §8.3 column contract — Position carries the bare
    # position_name, Institute carries the bare institute. Both go
    # through `_safe_str_or_em` so a NULL/NaN cell renders as EM_DASH
    # rather than crashing the widget protobuf (gotcha #1). The
    # `_format_label` helper that combined them is still used by the
    # detail-card header below; only the table render switched to bare
    # cells.
    display_df = pd.DataFrame({
        "Position":  df_filtered["position_name"].apply(_safe_str_or_em),
        "Institute": df_filtered["institute"].apply(_safe_str_or_em),
        "Applied":   df_filtered["applied_date"].apply(_format_date_or_em),
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
        "Result":   df_filtered["result"].apply(_safe_str_or_em),
    }).reset_index(drop=True)

    # T2-A / T3-rev-A: column_config locks per-column widths so the
    # selectable table doesn't collapse to equal-width cells. Position
    # keeps `width="large"` (bare position_name can still be long, e.g.
    # "Senior Postdoctoral Researcher in Computational Biostatistics").
    # Institute is `width="medium"` — institute names like "MIT" or
    # "Stanford" fit easily, but full names like "Massachusetts
    # Institute of Technology" don't fit in `small`. AppTest can't see
    # column_config (gotcha #15 — the protobuf serializes the data,
    # not the construction kwargs), so the contract is pinned via
    # source-grep in TestApplicationsTableColumnConfig.
    event = st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Position":     st.column_config.TextColumn("Position",     width="large"),
            "Institute":    st.column_config.TextColumn("Institute",    width="medium"),
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
    # CL1 type-clean: streamlit-stubs declares DataframeState as
    # TypedDict so attribute access trips pyright; runtime exposes a
    # wrapper supporting both subscript and attribute. Mirror the form
    # used on pages/1_Opportunities.py + pages/3_Recommenders.py.
    selected_rows = list(event.selection.rows) if event is not None else []  # type: ignore[attr-defined]
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
# `st.container(border=True)` is the outer wrapper — T3 adds per-row
# `apps_interview_{id}_form` blocks (T3-rev-B; the T3-A single-form
# `apps_interviews_form` was retired) inside the same container after
# the detail form (DESIGN §8.3 D-B). The container is intentionally
# architected to accept N siblings so T3's interleaving is a pure
# addition rather than a refactor of T2's container boundaries.

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
        # T3-A: read interviews for this position alongside the
        # application row. database.get_interviews orders by sequence
        # ASC (database.py contract); the page does not re-sort. Empty
        # frame is the natural state for a freshly-selected position
        # with no interviews yet.
        interviews_df = database.get_interviews(sid)

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

            # ── Interviews list (T3-A / T3-rev-B) ───────────────────
            #
            # DESIGN §8.3 D-B: an inline interview list under the app
            # detail card. T3-rev-B: each interview is a self-contained
            # per-row block — `apps_interview_{id}_form` (border=False)
            # holding heading + detail row + per-row Save submit, plus a
            # per-row Delete button OUTSIDE the form (Streamlit 1.56
            # forbids st.button inside st.form). add_interview
            # auto-assigns the next sequence and writes NULL date/
            # format/notes (the schema DEFAULTs).
            #
            # Visual placement vs wireframe: docs/ui/wireframes.md
            # shows interviews interleaved between Response and Result
            # widgets. Streamlit forms cannot be opened/closed mid-
            # rendering, so the interviews block is rendered AFTER
            # the detail form ends (still inside the same bordered
            # container per "under app detail card"). Wireframes are
            # intent-only for layout (wireframes.md line 3).
            st.markdown("**Interviews**")

            # ── Pre-seed sentinel: per-row, frozenset of seeded ids ──
            #
            # Per-row pre-seeding (one sentinel entry per id) preserves
            # in-flight drafts on sibling rows when the user clicks
            # Add: only the new id (current_ids - seeded_ids = {new})
            # gets pre-seeded; existing rows keep their session_state
            # values across the rerun.
            #
            # The intersection step (saved_sentinel & current_ids)
            # prunes deleted ids on every rerun so the sentinel never
            # accumulates zombie entries (Sonnet plan-critique signal
            # — without the intersection an ever-growing frozenset
            # would carry deleted ids forever).
            #
            # int() cast normalizes pandas int64 ids to native int so
            # frozenset comparisons in tests don't drift on dtype.
            current_ids = (
                frozenset(int(i) for i in interviews_df["id"])
                if not interviews_df.empty
                else frozenset()
            )
            saved_sentinel = st.session_state.get(
                "_apps_interviews_seeded_ids", frozenset(),
            )
            seeded_ids = saved_sentinel & current_ids
            for _, _iv_row in interviews_df.iterrows():
                # CL1 type-clean: pandas-stubs widens iterrows cells to
                # Series | ndarray | Any. Funnel through Any so int()
                # only sees the runtime scalar (PR #22 precedent).
                _iid_raw: Any = _iv_row["id"]
                _iid = int(_iid_raw)
                if _iid in seeded_ids:
                    continue
                # Pre-seed every widget key for this fresh id. The
                # _safe_str / _coerce_iso_to_date helpers cover NaN-
                # from-NULL (gotcha #1); the format guard rejects any
                # legacy / out-of-vocab value so the selectbox only
                # ever sees a member of [None, *INTERVIEW_FORMATS].
                _fmt_str = _safe_str(_iv_row["format"])
                _fmt = _fmt_str if _fmt_str in config.INTERVIEW_FORMATS else None
                st.session_state[f"apps_interview_{_iid}_date"] = (
                    _coerce_iso_to_date(_iv_row["scheduled_date"])
                )
                st.session_state[f"apps_interview_{_iid}_format"] = _fmt
                st.session_state[f"apps_interview_{_iid}_notes"] = (
                    _safe_str(_iv_row["notes"])
                )
            st.session_state["_apps_interviews_seeded_ids"] = (
                seeded_ids | current_ids
            )

            # ── Per-row blocks (T3-rev-B) ────────────────────────────
            #
            # DESIGN §8.3 D-B per-row block architecture: each interview
            # is a self-contained block of {Interview number heading +
            # Detail row + per-row Save submit + per-row Delete}. The
            # single page-level `apps_interviews_form` from T3-A was
            # retired; each row now owns `apps_interview_{id}_form`
            # (`border=False` so the parent st.container(border=True)
            # stays the only visual frame).
            #
            # Streamlit guarantees at most ONE form's submit fires per
            # click rerun, so `saves_clicked` is either empty or carries
            # exactly one `(iid, seq)` tuple — the post-container handler
            # processes it without ambiguity.
            #
            # Delete button stays OUTSIDE the per-row form (Streamlit
            # 1.56 forbids `st.button` inside `st.form` — only
            # `st.form_submit_button` is allowed). It renders
            # immediately below the row's form so the per-row block
            # reads top-to-bottom: heading → detail → Save → Delete.
            saves_clicked: list[tuple[int, int]] = []
            for _i, (_, _iv_row) in enumerate(interviews_df.iterrows()):
                # CL1 type-clean: same iterrows-Series-widening fix as
                # the seed loop above. Funnel through Any before int().
                _iid_raw: Any = _iv_row["id"]
                _seq_raw: Any = _iv_row["sequence"]
                _iid = int(_iid_raw)
                _seq = int(_seq_raw)

                if _i > 0:
                    # Visual separator between blocks. The first row
                    # has the **Interviews** section header above it
                    # already, so no leading divider.
                    st.divider()

                with st.form(f"apps_interview_{_iid}_form", border=False):
                    st.markdown(f"**Interview {_seq}**")
                    _cols = st.columns([2, 2, 4])
                    with _cols[0]:
                        st.date_input(
                            "Date",
                            value=None,
                            key=f"apps_interview_{_iid}_date",
                        )
                    with _cols[1]:
                        # Mirror of T2-A's response_type selectbox:
                        # leading None makes "no format chosen" a
                        # legal pre-seed value; format_func renders
                        # None as the em-dash glyph.
                        st.selectbox(
                            "Format",
                            options=[None, *config.INTERVIEW_FORMATS],
                            format_func=lambda v: EM_DASH if v is None else v,
                            key=f"apps_interview_{_iid}_format",
                        )
                    with _cols[2]:
                        st.text_input(
                            "Notes",
                            key=f"apps_interview_{_iid}_notes",
                        )
                    if st.form_submit_button(
                        "Save", key=f"apps_interview_{_iid}_save",
                    ):
                        saves_clicked.append((_iid, _seq))

                # Delete OUTSIDE the form, immediately below the Save
                # line. Click handler sets the two pending-target
                # sentinels (`_apps_interview_delete_target_id` +
                # `..._seq`); the dialog itself opens via the post-loop
                # guard below so there is exactly one call site for
                # the dialog, regardless of which button was clicked.
                if st.button(
                    f"🗑️ Delete Interview {_seq}",
                    key=f"apps_interview_{_iid}_delete",
                ):
                    st.session_state[
                        "_apps_interview_delete_target_id"
                    ] = _iid
                    st.session_state[
                        "_apps_interview_delete_target_seq"
                    ] = _seq

            # ── Dialog re-open guard (T3-B; gotcha #3) ───────────────
            #
            # Single dialog call site. Fires whenever the pending-id
            # sentinel is set AND the id is in the current position's
            # interviews. The `pending_id in current_ids` check
            # provides automatic stale-target cleanup: navigating to
            # a different position (sid changes → current_ids changes)
            # silently pops the sentinels because the pending id no
            # longer matches anything in view. Same guard catches the
            # post-confirm rerun (the deleted id is no longer in
            # current_ids — but the Confirm handler also pops the
            # sentinels itself so this is belt-and-suspenders).
            _pending_delete_id = st.session_state.get(
                "_apps_interview_delete_target_id"
            )
            if _pending_delete_id is not None:
                if _pending_delete_id in current_ids:
                    _confirm_interview_delete_dialog()
                else:
                    # Stale target — silent cleanup, no error / toast.
                    st.session_state.pop(
                        "_apps_interview_delete_target_id", None,
                    )
                    st.session_state.pop(
                        "_apps_interview_delete_target_seq", None,
                    )

            # ── Add button (outside the form per Streamlit 1.56) ─────
            #
            # st.form forbids st.button inside (only st.form_submit_
            # button is allowed). The Add button lives outside the
            # form and triggers add_interview(sid, {}) which auto-
            # assigns the next sequence.
            #
            # Add does NOT discard in-flight drafts to OTHER interview
            # rows: the per-row pre-seed sentinel only fires for the
            # newly-Added id (current_ids - seeded_ids = {new_id}), so
            # existing widget session_state values survive the rerun
            # untouched.
            add_clicked = st.button(
                "Add another interview", key="apps_add_interview",
            )

        if detail_submitted:
            # Build the dirty diff against the persisted application row
            # so a no-op Save (user clicked Save with nothing changed)
            # short-circuits with an honest "No changes to save." toast
            # instead of mis-claiming a write happened. Per-field
            # comparison normalizes widget shape ↔ DB shape (date ↔ ISO
            # string, bool ↔ 0/1 INTEGER) so the diff doesn't
            # false-positive on cosmetic differences. Phase 7 CL4 Fix 1
            # — was previously an unconditional `upsert_application` +
            # Saved toast on every click (T2-A original).
            applied_d   = st.session_state["apps_applied_date"]
            conf_d      = st.session_state["apps_confirmation_date"]
            resp_d      = st.session_state["apps_response_date"]
            result_n_d  = st.session_state["apps_result_notify_date"]
            _w_applied_iso = applied_d.isoformat() if applied_d else None
            _w_conf_received = int(
                st.session_state["apps_confirmation_received"]
            )
            _w_conf_iso = conf_d.isoformat() if conf_d else None
            _w_response_type = st.session_state["apps_response_type"]
            _w_response_iso = resp_d.isoformat() if resp_d else None
            _w_result = st.session_state["apps_result"]
            _w_result_notify_iso = (
                result_n_d.isoformat() if result_n_d else None
            )
            _w_notes = st.session_state["apps_notes"]

            _db_applied_iso = _safe_str(app_row.get("applied_date")) or None
            _db_conf_received = int(app_row.get("confirmation_received") or 0)
            _db_conf_iso = (
                _safe_str(app_row.get("confirmation_date")) or None
            )
            _db_response_type_raw = app_row.get("response_type")
            _db_response_type = (
                _db_response_type_raw
                if _db_response_type_raw in config.RESPONSE_TYPES
                else None
            )
            _db_response_iso = _safe_str(app_row.get("response_date")) or None
            _db_result_raw = app_row.get("result")
            _db_result = (
                _db_result_raw
                if _db_result_raw in config.RESULT_VALUES
                else config.RESULT_DEFAULT
            )
            _db_result_notify_iso = (
                _safe_str(app_row.get("result_notify_date")) or None
            )
            _db_notes = _safe_str(app_row.get("notes"))

            fields: dict[str, Any] = {}
            if _w_applied_iso != _db_applied_iso:
                fields["applied_date"] = _w_applied_iso
            if _w_conf_received != _db_conf_received:
                fields["confirmation_received"] = _w_conf_received
            if _w_conf_iso != _db_conf_iso:
                fields["confirmation_date"] = _w_conf_iso
            if _w_response_type != _db_response_type:
                fields["response_type"] = _w_response_type
            if _w_response_iso != _db_response_iso:
                fields["response_date"] = _w_response_iso
            if _w_result != _db_result:
                fields["result"] = _w_result
            if _w_result_notify_iso != _db_result_notify_iso:
                fields["result_notify_date"] = _w_result_notify_iso
            if _w_notes != _db_notes:
                fields["notes"] = _w_notes

            try:
                if not fields:
                    # No-op: nothing changed. Skip the DB write (and the
                    # R1/R3 cascade — there's no transition to fire
                    # against) and surface an honest no-op toast. Still
                    # set the skip-flag + pop the form-id sentinel so
                    # the post-toast rerun preserves selection (the
                    # detail card stays open) and re-seeds from DB
                    # (idempotent — fresh values will match in-flight).
                    st.session_state["_applications_skip_table_reset"] = True
                    st.session_state.pop(
                        "_applications_edit_form_sid", None,
                    )
                    st.toast("No changes to save.")
                    st.rerun()
                # propagate_status=True fires R1 + R3 cascades inside
                # the same transaction; the returned indicator drives
                # the cascade-promotion toast surfaced below.
                result = database.upsert_application(
                    sid, fields, propagate_status=True,
                )
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
                # T2-B: surface R1 / R3 pipeline promotions as a
                # second toast (Saved-then-Promoted, chronological).
                # `result["new_status"]` is non-None whenever
                # status_changed=True per the upsert_application
                # contract; trust the contract and let any future
                # violation raise a KeyError loudly rather than
                # swallowing it here. STATUS_LABELS.get(..., raw)
                # passthrough is the project's status-display
                # convention (matches the card header above and
                # DESIGN §8.0); the fallback is unreachable in
                # practice given config invariant #3.
                if result["status_changed"]:
                    promo_label = config.STATUS_LABELS.get(
                        result["new_status"], result["new_status"]
                    )
                    st.toast(f"Promoted to {promo_label}.")
                st.rerun()
            except Exception as e:
                # GUIDELINES §8: surface failures via st.error, do NOT
                # re-raise (re-raise would render the very traceback
                # the handler exists to hide). Sentinel survives so
                # the user's dirty form input is preserved for retry.
                st.error(f"Could not save: {e}")

        # ── T3-rev-B: per-row interviews Save handler ────────────────
        #
        # Per-row Save. Streamlit fires at most one form's submit per
        # click rerun, so `saves_clicked` is either empty or carries
        # exactly one `(iid, seq)` tuple — the click that just landed.
        # The handler computes a per-row dirty diff using _safe_str-
        # normalized comparison so NaN-from-NULL on the DB side doesn't
        # false-positive against an empty widget value (T3 review
        # carry-over from the T3-A single-form architecture; the same
        # diff logic now scoped to one row).
        #
        # Toast wording: `Saved interview {seq}.` (singular + sequence,
        # symmetric with the existing `Deleted interview {seq}.` toast
        # — addresses T3 review Finding #6 wording asymmetry by
        # side-effect of the architectural refactor).
        #
        # The seeded-ids sentinel is intentionally NOT popped here:
        # update_interview is a direct write with no normalization, so
        # the widget already reflects DB state after Save. Popping
        # would force EVERY row to re-seed on the post-Save rerun and
        # clobber unsaved drafts on sibling rows — load-bearing for
        # the per-row block architecture (a sibling row whose user
        # just typed a draft must survive the rerun untouched).
        if saves_clicked:
            _iid, _seq = saves_clicked[0]
            try:
                _db_row = interviews_df[interviews_df["id"] == _iid].iloc[0]

                _w_date = st.session_state.get(
                    f"apps_interview_{_iid}_date",
                )
                _w_format = st.session_state.get(
                    f"apps_interview_{_iid}_format",
                )
                _w_notes_str = _safe_str(
                    st.session_state.get(
                        f"apps_interview_{_iid}_notes", "",
                    )
                )
                _w_date_iso = _w_date.isoformat() if _w_date else None
                _w_notes = _w_notes_str if _w_notes_str else None

                _db_date_str = _safe_str(_db_row["scheduled_date"])
                _db_date_iso = _db_date_str if _db_date_str else None
                _db_fmt_str = _safe_str(_db_row["format"])
                _db_format = (
                    _db_fmt_str
                    if _db_fmt_str in config.INTERVIEW_FORMATS
                    else None
                )
                _db_notes_str = _safe_str(_db_row["notes"])
                _db_notes = _db_notes_str if _db_notes_str else None

                _dirty: dict[str, Any] = {}
                if _w_date_iso != _db_date_iso:
                    _dirty["scheduled_date"] = _w_date_iso
                if _w_format != _db_format:
                    _dirty["format"] = _w_format
                if _w_notes != _db_notes:
                    _dirty["notes"] = _w_notes

                # Phase 7 CL4 Fix 1: branch toast wording on the dirty
                # diff so a no-op Save (clicking Save with nothing
                # changed) reads as "No changes to save." rather than
                # mis-claiming a write happened. The DB call is gated
                # on `_dirty` already; only the toast wording was
                # previously dishonest.
                st.session_state["_applications_skip_table_reset"] = True
                if _dirty:
                    database.update_interview(_iid, _dirty)
                    st.toast(f"Saved interview {_seq}.")
                else:
                    st.toast("No changes to save.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not save interview {_seq}: {e}")

        # ── T3-A: interviews Add handler ─────────────────────────────
        #
        # Inserts a blank interview row via add_interview(sid, {}).
        # The function auto-assigns the next sequence and runs the R2
        # cascade (STATUS_APPLIED → STATUS_INTERVIEW on the first
        # interview, DESIGN §9.3); the page surfaces the promotion
        # via a separate toast when status_changed=True.
        #
        # Order is Added-then-Promoted (chronological — Promoted is
        # the consequence of the Add). Matches T2-B Save handler's
        # Saved-then-Promoted convention so the user sees the same
        # action-first / cascade-second pattern across both surfaces
        # (the application detail-card Save and the interview-list
        # Add). Pinned by
        # `test_added_toast_fires_before_promoted_toast` in
        # `TestApplicationsInterviewAdd`.
        if add_clicked:
            try:
                _add_result = database.add_interview(
                    sid, {}, propagate_status=True,
                )
                st.session_state["_applications_skip_table_reset"] = True
                st.toast("Added interview.")
                if _add_result["status_changed"]:
                    _promo_label = config.STATUS_LABELS.get(
                        _add_result["new_status"],
                        _add_result["new_status"],
                    )
                    st.toast(f"Promoted to {_promo_label}.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not add interview: {e}")
