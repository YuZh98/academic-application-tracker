# pages/1_Opportunities.py
# Opportunities page — position table, quick-add form, inline full edit.
# Shipped: Tier 1 (quick-add + empty state), Tier 2 (filter bar),
#          Tier 3 (positions table + deadline urgency),
#          Tier 4 (row selection + Overview / Requirements / Materials / Notes tabs),
#          Tier 5 (Save on all four tabs + Overview Delete via @st.dialog confirm
#                  with FK cascade; _safe_str pre-seed guard).

import datetime
import math
from typing import Any

import streamlit as st
import database
import config

# Em-dash placeholder for missing / unparseable cells. Mirror of the same
# constant in app.py, pages/2_Applications.py, exports.py — pages and
# layers cannot share helpers (DESIGN §2), so the literal is duplicated
# rather than imported. Drift is caught at the test level (the urgency
# tests + applications tests + exports tests all assert against the
# same em-dash glyph U+2014).
EM_DASH = "—"


def _safe_str(v: Any) -> str:
    """Coerce a DataFrame cell to a widget-safe ``str``.

    Why this exists: ``database.get_all_positions`` returns a pandas
    DataFrame. Once **any** row in a TEXT column has a real string value,
    pandas upgrades the column dtype to ``object`` — but NULL SQLite
    values come back as ``float('nan')`` rather than ``None`` on the
    rows that never had a value. The obvious-looking ``r[col] or ""``
    idiom then mis-fires because ``nan`` is *truthy*
    (``bool(float('nan')) is True``), so ``nan or ""`` evaluates to
    ``nan`` and that NaN ends up assigned into ``session_state``.

    Streamlit's widget protobuf serialisation then raises
    ``TypeError: bad argument type for built-in operation`` the moment
    it tries to push a ``float('nan')`` through a C-level ``str``
    type-check (reproduced 2026-04-20 with three positions + Save on
    the first only + selecting row 1 / 2).

    Contract: ``None``, ``NaN`` (and any ``pd.isna``-truthy value) →
    ``""``; everything else → ``str(v)``.
    """
    if v is None:
        return ""
    # NaN self-compare is False — works even if pandas isn't imported here.
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v)


@st.dialog("Delete this position?")
def _confirm_delete_dialog() -> None:
    """Modal confirm dialog for irreversible position deletion (T5-E).

    The target position is read from session_state keys
    _delete_target_id / _delete_target_name set by the Overview tab's
    Delete-button handler. Passing via session_state (rather than function
    arguments) lets the caller re-invoke this dialog on every rerun while
    the pending flag is set — required so confirm/cancel clicks actually
    reach their branches. Streamlit's own "dialog auto-re-renders across
    reruns" magic does not carry through AppTest's script-run model
    (verified by an isolation probe 2026-04-20): the outer script has to
    re-open the dialog itself while the pending state is set.

    Outcomes:

    • Confirm → database.delete_position(position_id) cascades the DELETE
      through positions → applications + recommenders (schema FKs have
      ON DELETE CASCADE; PRAGMA foreign_keys=ON in database._connect).
      On success: st.toast, clear all four session_state keys (the
      _delete_target_* pair AND the selected_position_id / _edit_form_sid
      pair — paired cleanup per the T4 pattern), st.rerun() which closes
      the dialog.
    • Cancel → clear only the _delete_target_* pair; selected_position_id
      / _edit_form_sid are preserved so the user returns to the same
      edit context. Plain st.rerun() closes the dialog.

    Failure mode mirrors every other Tier-5 save path: a raising
    delete_position is caught, surfaced as a friendly st.error, and NOT
    re-raised — re-raising would make Streamlit render the very traceback
    the handler exists to prevent (F1 / GUIDELINES §8). Selection and
    pending-delete state are intentionally preserved on failure so the
    user can retry without losing context.
    """
    position_id: int | None = st.session_state.get("_delete_target_id")
    position_name: str = st.session_state.get("_delete_target_name", "")

    st.warning(
        f'Delete **"{position_name}"**? This also removes its application '
        f'and recommender rows (FK cascade) and **cannot be undone**.'
    )
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button(
            "Confirm Delete",
            type="primary",
            key="delete_confirm",
            width="stretch",
        ):
            # Review Fix #1 (phase-3-tier5-review.md): defend against a
            # missing _delete_target_id (stale session_state, orphaned
            # rerun, future refactor drops the assignment). Without this
            # guard, database.delete_position(None) silently no-ops
            # (WHERE id = NULL matches no rows) while the success toast
            # still fires — the user reads "Deleted" but the row is intact.
            # Surface a clear error and keep state untouched for retry.
            if position_id is None:
                st.error(
                    "Delete target was lost — please re-open the dialog."
                )
                return
            try:
                database.delete_position(position_id)
                st.toast(f'Deleted "{position_name}".')
                # Paired cleanup (T4 pattern): both sentinels go together.
                st.session_state.pop("selected_position_id", None)
                st.session_state.pop("_edit_form_sid", None)
                st.session_state.pop("_delete_target_id", None)
                st.session_state.pop("_delete_target_name", None)
                # No _skip_table_reset here: the row is gone, so the edit
                # panel SHOULD collapse on the next rerun.
                st.rerun()
            except Exception as exc:
                st.error(f"Could not delete: {exc}")
    with col_cancel:
        if st.button("Cancel", key="delete_cancel", width="stretch"):
            # Cancel contract: close the dialog, no data-state change.
            # Clear only the pending-delete pair; selected_position_id /
            # _edit_form_sid stay intact so the user returns to the same
            # edit panel with nothing else changed.
            st.session_state.pop("_delete_target_id", None)
            st.session_state.pop("_delete_target_name", None)
            # Reuse the T5-A one-shot: after this st.rerun(), the dataframe
            # widget resets its on_select event (same AppTest / data-change
            # behaviour pinned by T4), which would otherwise pop
            # selected_position_id in the else branch of the selection-
            # resolution block and collapse the edit panel. _skip_table_reset
            # preserves the selection so the user lands back on the same row.
            st.session_state["_skip_table_reset"] = True
            st.rerun()


def _deadline_urgency(date_str: Any) -> str:
    """Return the at-a-glance urgency glyph for a position's deadline.

    Phase 7 T1 contract:
        days_to_deadline ≤ DEADLINE_URGENT_DAYS → '🔴'
        ≤ DEADLINE_ALERT_DAYS (but past urgent)  → '🟡'
        beyond DEADLINE_ALERT_DAYS               → ''  (no urgency signal)
        NULL / empty / NaN / unparseable date    → '—' (em-dash placeholder)

    Mirrors the dashboard's ``database.py::_urgency_glyph`` banding
    (DESIGN §2 layer rule prevents importing it directly into a page —
    helpers stay duplicated rather than crossing the layer boundary).

    Thresholds come from config so changing DEADLINE_URGENT_DAYS /
    DEADLINE_ALERT_DAYS in one place updates both the page and the
    dashboard.

    NaN handling: pandas DataFrames surface NULL TEXT cells as
    ``float('nan')`` once any other row in the column has a value.
    ``not date_str`` doesn't catch NaN (NaN is truthy), so the
    explicit ``math.isnan`` branch + the ``date.fromisoformat``
    try/except together cover all three NULL-shaped inputs (None,
    NaN, empty string) plus malformed strings."""
    if date_str is None or date_str == "":
        return EM_DASH
    if isinstance(date_str, float) and math.isnan(date_str):
        return EM_DASH
    try:
        days = (datetime.date.fromisoformat(str(date_str)) - datetime.date.today()).days
    except (ValueError, TypeError):
        return EM_DASH
    if days <= config.DEADLINE_URGENT_DAYS:
        return "🔴"
    if days <= config.DEADLINE_ALERT_DAYS:
        return "🟡"
    return ""

database.init_db()

# DESIGN §8.0 / D14: page-wide layout is mandatory — positions table + edit
# panel are data-heavy, a centered default layout crams every row. Sub-task 12
# added the matching call to app.py; Sub-task 13 brings pages/1_Opportunities.py
# in line. Must be the first Streamlit call on the page (after this point any
# other st.* fires page-setup).
st.set_page_config(
    page_title="Postdoc Tracker",
    page_icon="📋",
    layout="wide",
)

st.title("Opportunities")

# ── TIER 1: Quick-add expander ────────────────────────────────────────────────
with st.expander("Quick Add", expanded=False):
    with st.form(key="quick_add_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            position_name = st.text_input("Position Name *", key="qa_position_name")
            deadline_date = st.date_input("Deadline", value=None, key="qa_deadline_date")
        with col2:
            institute = st.text_input("Institute", key="qa_institute")
            priority = st.selectbox("Priority", config.PRIORITY_VALUES, key="qa_priority")
        with col3:
            field = st.text_input("Field", key="qa_field")
            link = st.text_input("Link (URL)", key="qa_link")

        submitted = st.form_submit_button("+ Add Position", key="qa_submit")

# F4: submit handler outside the expander so error/success render in the main
# content area and remain visible even if the expander is collapsed.
if submitted:
    # F3: strip all text inputs before validation and storage so whitespace-only
    # values (e.g., "   ") do not bypass the required-field check.
    position_name = position_name.strip()
    institute     = institute.strip()
    field         = field.strip()
    link          = link.strip()

    if not position_name:
        st.error("Position Name is required.")
    else:
        fields: dict[str, Any] = {      # F5: dict[str, Any] per project standard
            "position_name": position_name,
            "institute":     institute,
            "field":         field,
            "priority":      priority,
            "link":          link,
        }
        if deadline_date is not None:
            fields["deadline_date"] = deadline_date.isoformat()
        # F1: wrap database write per GUIDELINES.md §8 — show a clear message on
        # failure rather than exposing a raw traceback to the user.
        # F1 (Tier-4 full review): the previous version re-raised after
        # st.error, which made Streamlit render the very traceback this
        # handler exists to prevent. Swallow the exception here — the
        # friendly message is the intended user-facing behaviour.
        try:
            database.add_position(fields)
            st.toast(f'Added "{position_name}" to your list.')
            # F1 (Tier-4 review): get_all_positions() orders
            # deadline_date ASC NULLS LAST. A quick-added position's
            # positional index depends on its deadline relative to existing
            # rows — it can land anywhere, shifting the index of the
            # previously-selected row. The dataframe widget's selection
            # state is an index into df_display, so leaving it intact
            # would silently re-bind the edit panel to a different
            # position. Clear all three session keys together to keep the
            # selection/sentinel invariant aligned in one place.
            st.session_state.pop("positions_table", None)
            st.session_state.pop("selected_position_id", None)
            st.session_state.pop("_edit_form_sid", None)
            st.rerun()
        except Exception as e:
            st.error(f"Could not save position: {e}")

# ── TIER 2: Filter bar ────────────────────────────────────────────────────────
# Phase 7 T2: prepend a free-text search box at the start of the filter row.
# Wider weight (3) than status / priority (2) because typed queries are
# variable-length and the search is the primary navigation tool — placing
# it left, prominent, mirrors common UX (Google / GitHub search).
col_search, col_status, col_priority, col_field = st.columns([3, 2, 2, 3])
with col_search:
    # Phase 7 T2: substring search against position_name. Scope is
    # position_name only — institute / field are intentionally excluded
    # (field already has its own filter widget; narrowing the search to
    # one column keeps "what you type matches what's printed in the
    # Position column" predictable).
    search_filter = st.text_input(
        "Search positions",
        placeholder="Search by position name…",
        key="filter_search",
    )
with col_status:
    # DESIGN §8.0 Status label convention: UI shows labels
    # (`config.STATUS_LABELS`), storage/compare holds the raw bracketed
    # values. format_func wraps the literal dict.get so the "All" sentinel
    # passes through (vanilla `STATUS_LABELS.get("All")` would return None
    # and leak a blank option into the rendered dropdown).
    status_filter = st.selectbox(
        "Status",
        ["All"] + config.STATUS_VALUES,
        index=0,
        format_func=lambda v: config.STATUS_LABELS.get(v, v),
        key="filter_status",
    )
with col_priority:
    priority_filter = st.selectbox(
        "Priority", ["All"] + config.PRIORITY_VALUES, index=0, key="filter_priority"
    )
with col_field:
    field_filter = st.text_input(
        "Field", placeholder="Filter by field…", key="filter_field"
    )

# ── TIER 3: Positions table ───────────────────────────────────────────────────
df = database.get_all_positions()

# T2-B: apply filters sequentially; each active filter narrows df_filtered further.
df_filtered = df
if status_filter != "All":
    df_filtered = df_filtered[df_filtered["status"] == status_filter]
if priority_filter != "All":
    df_filtered = df_filtered[df_filtered["priority"] == priority_filter]
if field_filter.strip():
    # F1: regex=False treats the search term as a literal string, not a regex
    # pattern. Without it, "C++" raises re.error and crashes the page.
    df_filtered = df_filtered[
        df_filtered["field"].str.contains(
            field_filter.strip(), case=False, na=False, regex=False
        )
    ]
# Phase 7 T2: position-name search. Mirrors the field-filter idiom above
# (regex=False so '++' / '.' are literals; case=False; na=False so any
# theoretical NULL position_name is filtered out rather than NaN-propagated).
# AND-combined with the other filters — each row mask narrows further.
if search_filter.strip():
    df_filtered = df_filtered[
        df_filtered["position_name"].str.contains(
            search_filter.strip(), case=False, na=False, regex=False
        )
    ]

if df.empty:
    # T4-A: table not rendered → clear any stale selection from a prior rerun
    # so Tier-4 edit panels do not show for a position the user can't see.
    # F4 (Tier-4 review): pop the sentinel alongside selected_position_id so
    # the pair stays in sync — otherwise a later sid that happens to equal
    # the stale sentinel would skip the pre-seed.
    st.session_state.pop("selected_position_id", None)
    st.session_state.pop("_edit_form_sid", None)
    st.info("No positions yet — use Quick Add above to get started.")
elif df_filtered.empty:
    st.session_state.pop("selected_position_id", None)   # T4-A: same reason
    st.session_state.pop("_edit_form_sid", None)         # F4: same pairing
    st.info("No positions match the current filters.")
else:
    st.caption(f"{len(df_filtered)} position(s) tracked.")

    # T3-A / T3-B: build display DataFrame with urgency flag, then render table.
    df_display = df_filtered.copy()
    df_display["deadline_urgency"] = df_display["deadline_date"].apply(
        _deadline_urgency
    )
    # DESIGN §8.0 + §8.2 Status label convention: the table's Status column
    # displays the human-readable label (`config.STATUS_LABELS[raw]`), never
    # the bracketed storage value. Derive a `status_label` column from the
    # raw `status` and render that one instead — the raw column stays on
    # df_display for the row-index → id lookup below (selection plumbing),
    # but is kept out of column_order so the UI never surfaces it.
    df_display["status_label"] = df_display["status"].map(config.STATUS_LABELS)

    display_cols = [
        "position_name", "institute", "priority", "status_label",
        "deadline_date", "deadline_urgency",
    ]
    # T4-A: enable single-row selection. AppTest drives this by writing to
    # session_state["positions_table"] directly (no click-a-row API exists),
    # so the key is part of the page's public test contract — do not rename
    # without updating TABLE_KEY in tests/test_opportunities_page.py.
    event = st.dataframe(
        df_display,
        # F2 (Tier-4 full review): use_container_width=True is deprecated in
        # Streamlit 1.56 (removal after 2025-12-31) — replaced with the
        # documented `width="stretch"` equivalent. Silences ~60 warnings
        # per test run.
        width="stretch",
        hide_index=True,
        column_order=display_cols,
        column_config={
            "position_name":    st.column_config.TextColumn("Position",  width="large"),
            "institute":        st.column_config.TextColumn("Institute", width="medium"),
            "priority":         st.column_config.TextColumn("Priority",  width="small"),
            # DESIGN §8.0 + §8.2: header reads "Status" (the UI-facing
            # concept); the underlying df column is `status_label` so the
            # cell values go through the STATUS_LABELS map.
            "status_label":     st.column_config.TextColumn("Status",    width="medium"),
            "deadline_date":    st.column_config.TextColumn("Due",       width="small"),
            "deadline_urgency": st.column_config.TextColumn("Urgency",   width="small"),
        },
        key="positions_table",
        on_select="rerun",
        selection_mode="single-row",
    )

    # T4-A: map the selected positional row index back to its DB id so later
    # tiers (tabs, edit fields, Save/Delete) can load the right position.
    selected_rows = list(event.selection.rows) if event is not None else []
    if selected_rows and 0 <= selected_rows[0] < len(df_display):
        new_sid = int(df_display.iloc[selected_rows[0]]["id"])
        # Review Fix #2 (phase-3-tier5-review.md): clear any stale
        # pending-delete target when the selected row *changes*. Without
        # this, a user who dismisses the delete dialog via the X/Escape
        # (neither fires a button click, neither runs our Cancel handler)
        # leaves _delete_target_id in session_state. If they then select
        # a different row and later return to the original row, the
        # elif-reopen branch in the Overview tab would fire a *phantom
        # dialog* — no user click, no user intent. Clearing on row-change
        # contains the leak to the original row. The X-dismiss-then-same-
        # row case remains a known Streamlit limitation (no dialog-close
        # event in 1.56); documented at the elif-reopen site.
        prev_sid = st.session_state.get("selected_position_id")
        if prev_sid is not None and prev_sid != new_sid:
            st.session_state.pop("_delete_target_id", None)
            st.session_state.pop("_delete_target_name", None)
        st.session_state["selected_position_id"] = new_sid
    elif (
        st.session_state.pop("_skip_table_reset", False)
        or "_delete_target_id" in st.session_state
    ):
        # T5-A: one-shot bypass consumed here. The save handler sets
        # _skip_table_reset=True before its st.rerun() so this branch
        # preserves selected_position_id across the save cycle — otherwise
        # st.dataframe resets its event (same protective behaviour pinned
        # by test_filter_change_after_selection_clears_selection) and the
        # edit panel would collapse right after the user hit Save.
        # T5-E: while a delete dialog is pending (_delete_target_id set),
        # the Confirm/Cancel click fires an internal rerun that resets the
        # dataframe event. Without this guard, selected_position_id would
        # be popped, the edit panel would collapse, and the elif
        # dialog-reopen branch in the Overview tab would never execute —
        # swallowing the click. Preserving selection keeps the dialog
        # reachable until the user resolves it.
        pass
    else:
        # Empty selection, or index out-of-bounds after filter/data change.
        # F4 (Tier-4 review): keep the sentinel paired with the sid.
        st.session_state.pop("selected_position_id", None)
        st.session_state.pop("_edit_form_sid", None)

# ── TIER 4: Edit panel (subheader + tabs shell) ──────────────────────────────
# Renders only when a row is selected. Uses the unfiltered `df` to look up
# the selected row so that narrowing the filter does not dismiss an
# in-progress edit — the user can still see and edit what they picked.
# Tab bodies are empty here; T4-C–F will fill Overview / Requirements /
# Materials / Notes respectively.
if "selected_position_id" in st.session_state:
    sid = st.session_state["selected_position_id"]
    selected_row = df[df["id"] == sid]
    if not selected_row.empty:
        r = selected_row.iloc[0]
        # DESIGN §8.0 Status label convention: render STATUS_LABELS[raw]
        # ('Applied'), never the raw bracketed storage value ('[APPLIED]').
        # The pre-seed block below already coerces an out-of-vocab status
        # to STATUS_VALUES[0] via safe_status, so the map lookup is safe
        # in practice — we still use .get(..., raw) as a last-resort
        # passthrough to avoid a KeyError surfacing as an uncaught
        # exception if a row ever carries an un-labelled status.
        _status_label = config.STATUS_LABELS.get(r['status'], r['status'])
        st.subheader(f"{r['position_name']} · {_status_label}")

        # T4-C: widget-value trap — once session_state[key] is set, Streamlit
        # ignores the `value=` argument on later reruns, so the form would
        # "stick" on the first selected row. Pre-seed widget state whenever
        # the selection changes, tracked via the internal _edit_form_sid
        # sentinel. Stored values match widget types: str for text, date|None
        # for date_input, config-vocabulary strings for the selectboxes.
        #
        # Two-phase apply — defence-in-depth against the unmount-cleanup
        # bug class (the actual fix is the `st.tabs` architecture below;
        # this is the safety net):
        #   (a) Row CHANGE — force-overwrite every key so a fresh row's
        #       data replaces the previously-cached values.
        #   (b) Same row, key missing — restore from canonical (would
        #       repair Streamlit's tab-unmount cleanup of widget
        #       session_state IF a future architectural change ever
        #       re-introduced conditional rendering).
        #   (c) Same row, key present — leave it alone (preserves
        #       AppTest set_value semantics and any in-flight form draft
        #       commit).
        #
        # Background: a 2026-04-25 user report (position name vanishing
        # on Overview→Requirements→Overview round-trip) traced to
        # Sub-task 13's swap of `st.tabs` for `st.radio + conditional
        # rendering`. Conditional rendering unmounts each tab body's
        # widgets on tab switch, and Streamlit's documented v1.20+
        # behaviour wipes session_state for unmounted widget keys
        # (empirically confirmed for `st.text_input` on Streamlit 1.56
        # + AppTest; see tests/test_opportunities_page.py::
        # TestTabSwitchWidgetStateSurvival). The sid-only gate alone
        # never re-seeded on tab switch, so the cleaned-up text_input
        # rendered its empty default. Sub-task 13 was reverted to
        # `st.tabs` (CSS-hide instead of unmount → no cleanup → no
        # data loss); under that architecture the missing-key path
        # below is effectively dead code. Kept anyway because the
        # cost is microseconds and it absorbs any future Streamlit
        # behaviour change or accidental re-introduction of
        # conditional rendering.
        # F2 (Tier-4 review): a DB row can legitimately hold priority=NULL
        # (no DEFAULT in schema) and could theoretically hold an unknown
        # status value (sqlite CLI, future migration). Coerce both to
        # in-vocabulary values so the selectboxes never get an
        # out-of-options session_state value — today Streamlit tolerates
        # it silently, but the tolerance is undocumented.
        safe_priority = (
            r["priority"] if r["priority"] in config.PRIORITY_VALUES
            else config.PRIORITY_VALUES[0]
        )
        safe_status = (
            r["status"] if r["status"] in config.STATUS_VALUES
            else config.STATUS_VALUES[0]
        )
        # Sub-task 7 / DESIGN §8.2: work_auth is the categorical
        # three-value enum. Same F2-style coercion as priority /
        # status — NULL on quick-add rows and any legacy-vocabulary
        # string (Sub-task 3 collapsed the pre-v1.3 six-value list
        # manually, so dev DBs can carry 'OPT' / 'H1B' / …) must
        # drop to WORK_AUTH_OPTIONS[0] so the selectbox always
        # reads a valid in-vocab value.
        raw_work_auth = r["work_auth"] if "work_auth" in r.index else None
        safe_work_auth = (
            raw_work_auth if raw_work_auth in config.WORK_AUTH_OPTIONS
            else config.WORK_AUTH_OPTIONS[0]
        )
        # F5 (Tier-4 review): mirror the try/except in _deadline_urgency —
        # one malformed deadline row should render an empty date input,
        # not crash the whole page.
        try:
            safe_deadline = (
                datetime.date.fromisoformat(r["deadline_date"])
                if r["deadline_date"] else None
            )
        except (ValueError, TypeError):
            safe_deadline = None

        # _safe_str (not `r[col] or ""`) is load-bearing: pandas returns
        # float('nan') for NULL text cells once any row has a real string,
        # and NaN is truthy — `nan or ""` evaluates to `nan`, which then
        # blows up st.text_input/text_area's protobuf str check with a
        # bare "TypeError: bad argument type for built-in operation".
        canonical: dict[str, Any] = {
            "edit_position_name":  _safe_str(r["position_name"]),
            "edit_institute":      _safe_str(r["institute"]),
            "edit_field":          _safe_str(r["field"]),
            "edit_priority":       safe_priority,
            "edit_status":         safe_status,
            "edit_deadline_date":  safe_deadline,
            "edit_link":           _safe_str(r["link"]),
            # Sub-task 7: work_auth selectbox + work_auth_note text_area.
            # _safe_str on work_auth_note handles both None (fresh row)
            # and pandas float('nan') (NULL cell in a mixed-dtype TEXT
            # column — the same NaN-truthiness trap that bit notes /
            # link pre-seeds). Without it, st.text_area's protobuf
            # serialisation raises "bad argument type for built-in
            # operation".
            "edit_work_auth":      safe_work_auth,
            "edit_work_auth_note": (
                _safe_str(r["work_auth_note"])
                if "work_auth_note" in r.index else ""
            ),
            # T4-F: pre-seed the Notes text_area. positions.notes is TEXT
            # NULL-able (schema: database.py ~line 84), so coerce None/NaN → ""
            # before it reaches st.text_area — the widget expects str, and
            # pandas hands back float('nan') for NULL cells on mixed-dtype
            # object columns (see _safe_str docstring for the TypeError).
            "edit_notes":          _safe_str(r["notes"]),
        }
        # T4-D / T4-E: one slot per req_* column for the Requirements radios
        # and one slot per done_* column for the Materials checkboxes.
        # Same F2-style coercion as priority/status: if a req_* column holds
        # an unknown string (future migration, raw SQL edit) or is missing
        # from the row (e.g. during a migration-in-progress test), fall back
        # to 'No' — the schema default (DESIGN §5.1 + D21 Yes/Optional/No
        # vocabulary). done_* is INTEGER 0/1; anything else coerces to
        # False. The checkbox itself is only rendered by the Materials tab
        # when its req_* is 'Yes', but we seed unconditionally so switching
        # a requirement on mid-edit doesn't flash an unseeded checkbox.
        for req_col, done_col, _label in config.REQUIREMENT_DOCS:
            v = r[req_col] if req_col in r.index else None
            canonical[f"edit_{req_col}"] = (
                v if v in config.REQUIREMENT_VALUES else "No"
            )
            d = r[done_col] if done_col in r.index else 0
            canonical[f"edit_{done_col}"] = (d == 1)

        # Two-phase apply (see Bug 1 / Bug 2 fix block above):
        #   (a) Row CHANGE → force-overwrite every key so a fresh row's
        #       data replaces the previously-cached values.
        #   (b) Same row, key missing → restore from canonical (repairs
        #       Streamlit's tab-unmount cleanup of widget session_state).
        #   (c) Same row, key present → leave it alone (preserves AppTest
        #       set_value semantics and any in-flight form draft commit).
        sid_changed = st.session_state.get("_edit_form_sid") != sid
        for _key, _value in canonical.items():
            if sid_changed or _key not in st.session_state:
                st.session_state[_key] = _value
        st.session_state["_edit_form_sid"] = sid

        # DESIGN §8.2 + config.EDIT_PANEL_TABS: edit-panel tabs render via
        # `st.tabs(...)`, which keeps every tab body mounted on every script
        # run (CSS hides the inactive ones rather than unmounting them).
        # This is load-bearing for state survival: Sub-task 13 originally
        # swapped st.tabs for `st.radio + conditional rendering` so the
        # Delete button could be gated on a programmatically-readable
        # active_tab — but conditional rendering unmounted the inactive
        # tab's widgets, and Streamlit's documented v1.20+ behaviour wipes
        # `session_state` for unmounted widget keys. The result was
        # cross-tab data loss (text_input contents disappearing on tab
        # switch — user-reported 2026-04-25). The reversal restores the
        # original architecture; the Delete-button placement (DESIGN §8.2
        # "below the edit panel, outside the panel box, visible only when
        # the active tab is Overview") is satisfied by placing the button
        # inside `with tabs[0]:` after the form — st.tabs CSS-hides it on
        # the other tabs naturally.
        tabs = st.tabs(config.EDIT_PANEL_TABS)

        with tabs[0]:   # Overview — T4-C + T5-A
            # st.form batches edits so nothing writes on keystroke; the
            # submit button below is the only trigger that commits the
            # changes via database.update_position (T5-A).
            #
            # Form id "edit_overview" does not collide with any widget key
            # inside the form (all widget keys are prefixed edit_ + field
            # name, e.g. edit_position_name); st.form registers the id with
            # writes_allowed=False, so collision would raise
            # StreamlitValueAssignmentNotAllowedError at render.
            with st.form("edit_overview"):
                st.text_input("Position Name", key="edit_position_name")
                st.text_input("Institute",     key="edit_institute")
                st.text_input("Field",         key="edit_field")
                st.selectbox("Priority", config.PRIORITY_VALUES,
                             key="edit_priority")
                # DESIGN §8.0 Status label convention: UI shows labels
                # (`config.STATUS_LABELS`), storage holds raw bracketed
                # values. The Overview form only shows real pipeline
                # statuses (no "All" sentinel to pass through), so the
                # vanilla `STATUS_LABELS.get` is sufficient here —
                # mirrors the filter_status call above, minus the "All"
                # passthrough wrapper.
                st.selectbox("Status",   config.STATUS_VALUES,
                             format_func=config.STATUS_LABELS.get,
                             key="edit_status")
                st.date_input("Deadline",      key="edit_deadline_date")
                st.text_input("Link",          key="edit_link")
                # Sub-task 7 / DESIGN §8.2 + D22: work_auth categorical
                # (Yes/No/Unknown) pinned as a selectbox over
                # config.WORK_AUTH_OPTIONS; work_auth_note is the
                # freetext companion immediately below so the pair
                # reads as one conceptual field (category + posting-
                # specific nuance — "green card required", "J-1 OK
                # with a waiver"). Keys do not collide with the form
                # id "edit_overview" per DESIGN §8.0.
                st.selectbox("Work Authorization", config.WORK_AUTH_OPTIONS,
                             key="edit_work_auth")
                st.text_area("Work Authorization Note",
                             key="edit_work_auth_note")
                overview_submitted = st.form_submit_button(
                    "Save Changes",
                    key="edit_overview_submit",
                )

            # T5-A: submit handler lives OUTSIDE the form (mirrors the
            # quick-add pattern above) so st.error / st.toast render in the
            # page body rather than nested inside the form, which would
            # re-render on every form interaction.
            if overview_submitted:
                new_name = (
                    st.session_state.get("edit_position_name") or ""
                ).strip()
                if not new_name:
                    # Mirror quick-add F3: whitespace-only is treated as
                    # empty. No DB write, no toast.
                    st.error("Position Name is required.")
                else:
                    new_deadline = st.session_state.get("edit_deadline_date")
                    payload: dict[str, Any] = {
                        "position_name": new_name,
                        "institute":     st.session_state.get("edit_institute", ""),
                        "field":         st.session_state.get("edit_field", ""),
                        "priority":      st.session_state["edit_priority"],
                        "status":        st.session_state["edit_status"],
                        "deadline_date": (
                            new_deadline.isoformat()
                            if isinstance(new_deadline, datetime.date)
                            else None
                        ),
                        "link":          st.session_state.get("edit_link", ""),
                        "work_auth":      st.session_state["edit_work_auth"],
                        "work_auth_note": st.session_state.get(
                            "edit_work_auth_note", ""
                        ),
                    }
                    # Mirror F1 (Tier-4 review) on the save path: surface a
                    # friendly st.error on failure and DO NOT re-raise —
                    # re-raising makes Streamlit render the very traceback
                    # the handler exists to prevent.
                    try:
                        database.update_position(sid, payload)
                        st.toast(f'Saved "{new_name}".')
                        # Pop the sentinel so the next render re-seeds the
                        # widgets from the freshly-persisted DB values
                        # (e.g. position_name is now the stripped version).
                        # selected_position_id is INTENTIONALLY preserved:
                        # the user's context — which row they're editing —
                        # must survive the rerun.
                        st.session_state.pop("_edit_form_sid", None)
                        # One-shot: tells the selection-resolution block
                        # above to keep selected_position_id even if the
                        # dataframe resets its selection on the post-save
                        # rerun (pinned by T4 behaviour notes).
                        st.session_state["_skip_table_reset"] = True
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save changes: {exc}")

            # ── Delete button (DESIGN §8.2) ─────────────────────────────────
            # DESIGN §8.2 Delete row: the button renders BELOW the edit
            # panel (outside the panel/form box), visible ONLY when the
            # active tab is Overview. Placement inside `with tabs[0]:`
            # after the form gives both: it is below the form box (✓
            # "below the edit panel"), outside `st.form("edit_overview")`
            # (✓ "outside the panel box"), and st.tabs CSS-hides it on
            # the other tabs naturally (✓ "visible only when the active
            # tab is Overview"). The Sub-task 13 refactor moved it out
            # of `with tabs[0]:` and gated it on a `st.radio`-derived
            # `active_tab` variable — that broke widget state survival
            # across tab switches (text_input session_state cleanup on
            # unmount), and the Delete-button gating was the only
            # justification for that change. Reverted 2026-04-25.
            #
            # The button MUST live outside st.form("edit_overview") —
            # st.form only permits st.form_submit_button inside; a plain
            # st.button inside the form would raise. type='primary'
            # marks the action as destructive in the UI.
            #
            # Dialog lifecycle: clicking Delete stashes the target id +
            # name in session_state (_delete_target_id /
            # _delete_target_name) and opens the dialog. The elif
            # re-opens the same dialog on every subsequent rerun while
            # those keys remain — without this, confirm/cancel clicks
            # inside the dialog would not reach their branches in
            # AppTest, because Streamlit's "dialog auto-re-renders
            # across reruns" behaviour does not carry through AppTest's
            # script-run model (verified by isolation probe 2026-04-20).
            # Confirm and Cancel handlers inside the dialog clear the
            # _delete_target_* pair themselves before st.rerun(), so
            # the dialog disappears naturally on the next run.
            #
            # Review Fix #2 (phase-3-tier5-review.md): cross-row phantom
            # dialogs (dismiss via X on row A, switch to row B, come
            # back to row A, dialog reopens) are fixed by the row-change
            # cleanup in the selection-resolution block above. Same-row
            # phantom (dismiss via X on row A, stay on row A, reopens
            # on next rerun) remains a known limitation — Streamlit
            # 1.56 does not expose an on_close event for @st.dialog.
            # Users can always click Cancel to dismiss cleanly.
            if st.button("Delete", type="primary", key="edit_delete"):
                st.session_state["_delete_target_id"]   = sid
                st.session_state["_delete_target_name"] = r["position_name"]
                _confirm_delete_dialog()
            elif st.session_state.get("_delete_target_id") == sid:
                _confirm_delete_dialog()

        with tabs[1]:   # Requirements — T4-D + T5-B
            # One st.radio per entry in config.REQUIREMENT_DOCS. The options
            # are the canonical DB values (REQUIREMENT_VALUES) so
            # session_state holds exactly what will go into the TEXT column
            # at save time; format_func looks up the friendly UI label via
            # REQUIREMENT_LABELS. Per GUIDELINES §6 the page never hardcodes
            # vocabulary — everything comes from config, which is what
            # makes test_config_driven_new_doc_renders_new_widget green.
            with st.form("edit_requirements"):
                for req_col, _done_col, label in config.REQUIREMENT_DOCS:
                    st.radio(
                        label,
                        options=config.REQUIREMENT_VALUES,
                        format_func=config.REQUIREMENT_LABELS.get,
                        key=f"edit_{req_col}",
                        horizontal=True,
                    )
                requirements_submitted = st.form_submit_button(
                    "Save Changes",
                    key="edit_requirements_submit",
                )

            # T5-B: critical contract — the payload is built from req_col
            # keys ONLY. done_* columns are NEVER written by this save path,
            # so the user's prepared-documents state (done_cv, done_transcripts,
            # ...) is preserved across any req_* flip Yes↔Optional↔No. If the
            # user later switches req_cv back to 'Yes', the Materials tab will
            # again show the CV as done without the user re-ticking.
            if requirements_submitted:
                payload: dict[str, Any] = {
                    req_col: st.session_state[f"edit_{req_col}"]
                    for req_col, _done_col, _label in config.REQUIREMENT_DOCS
                }
                try:
                    database.update_position(sid, payload)
                    st.toast(f'Saved requirements for "{r["position_name"]}".')
                    st.session_state.pop("_edit_form_sid", None)
                    # Same one-shot as T5-A: preserve the selection across
                    # the post-save rerun despite st.dataframe resetting
                    # its event on data-change reruns.
                    st.session_state["_skip_table_reset"] = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not save requirements: {exc}")

        with tabs[2]:   # Materials — T4-E + T5-C
            # State-driven: the visible checkbox list is built from the LIVE
            # session_state["edit_{req_col}"] values (not the DB row), so
            # toggling a radio on the Requirements tab updates this tab on
            # the next rerun. Uses the 'Yes'-only filter (DESIGN §8.2) that
            # matches the readiness definition in database.py (~line 404).
            visible = [
                (req_col, done_col, label)
                for req_col, done_col, label in config.REQUIREMENT_DOCS
                if st.session_state.get(f"edit_{req_col}") == "Yes"
            ]
            if not visible:
                st.info(
                    "No required documents yet — mark docs as required on "
                    "the Requirements tab."
                )
            else:
                with st.form("edit_materials"):
                    for _req_col, done_col, label in visible:
                        st.checkbox(label, key=f"edit_{done_col}")
                    materials_submitted = st.form_submit_button(
                        "Save Changes",
                        key="edit_materials_submit",
                    )

                # T5-C: critical contract — the payload contains done_* keys
                # ONLY for docs currently visible (req_* == 'Yes'). done_* for
                # hidden docs are never written, so prior prepared-doc state
                # survives any req_* Yes↔No flip — mirrors T5-B's preservation
                # contract from the opposite side. Cast bool → int so the
                # positions.done_* INTEGER 0/1 schema domain is honoured
                # explicitly (SQLite would coerce a bool regardless, but the
                # explicit cast matches how done_* is read elsewhere).
                if materials_submitted:
                    payload: dict[str, Any] = {
                        done_col: int(
                            bool(st.session_state.get(f"edit_{done_col}"))
                        )
                        for _req_col, done_col, _label in visible
                    }
                    try:
                        database.update_position(sid, payload)
                        st.toast(f'Saved materials for "{r["position_name"]}".')
                        st.session_state.pop("_edit_form_sid", None)
                        # Same one-shot as T5-A / T5-B: preserve selection
                        # across the post-save rerun despite st.dataframe
                        # resetting its event on data-change reruns.
                        st.session_state["_skip_table_reset"] = True
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save materials: {exc}")

        with tabs[3]:   # Notes — T4-F + T5-D
            # Single free-form text_area for miscellaneous context (contact
            # details, interview prep hints, follow-up reminders). Pre-seeded
            # from the row's notes column via the _edit_form_sid block above,
            # so selecting a different row re-loads its notes.
            # Form id is "edit_notes_form" (not "edit_notes") to avoid a key
            # collision with the text_area's session_state slot — st.form
            # registers its id with writes_allowed=False, so sharing a name
            # with any existing session_state key raises
            # StreamlitValueAssignmentNotAllowedError at render time.
            with st.form("edit_notes_form"):
                st.text_area(
                    "Notes",
                    key="edit_notes",
                    height=200,
                    placeholder="Free-form notes — contacts, prep hints, follow-ups…",
                )
                notes_submitted = st.form_submit_button(
                    "Save Changes",
                    key="edit_notes_submit",
                )

            # T5-D: notes column is TEXT NULL-able, but the storage contract
            # (DESIGN.md §6 + CLAUDE.md 'Key Design Decisions') is that empty
            # input is persisted as "" — not None / NULL. Pre-seed coerces
            # NULL → "" on load so a no-op save leaves the DB stable at "".
            # Mirrors all other Tier-5 save paths: toast, friendly st.error
            # without re-raise, _edit_form_sid pop, _skip_table_reset one-shot.
            if notes_submitted:
                payload: dict[str, Any] = {
                    "notes": st.session_state.get("edit_notes", "") or "",
                }
                try:
                    database.update_position(sid, payload)
                    st.toast(f'Saved notes for "{r["position_name"]}".')
                    st.session_state.pop("_edit_form_sid", None)
                    st.session_state["_skip_table_reset"] = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not save notes: {exc}")

    else:
        # F3 (Tier-4 review): the selected position vanished from df
        # (deleted elsewhere, DB wiped, etc.). Clear both keys so later
        # reruns don't keep re-checking an absent row, and the sentinel
        # can't alias with a future sid.
        st.session_state.pop("selected_position_id", None)
        st.session_state.pop("_edit_form_sid", None)

# ── TIER 5: Save / Delete actions ────────────────────────────────────────────
# col_save, col_delete = st.columns([1, 1])
# with col_save:
#     if st.button("Save Changes"):
#         database.update_position(selected_id, changed_fields)
#         st.rerun()
# with col_delete:
#     if st.button("Delete", type="primary"):
#         if st.session_state.get("confirm_delete"):
#             database.delete_position(selected_id)
#             st.session_state.pop("selected_position_id", None)
#             st.rerun()
#         else:
#             st.session_state["confirm_delete"] = True
#             st.warning("Click Delete again to confirm.")
