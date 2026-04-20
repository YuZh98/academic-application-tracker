# pages/1_Opportunities.py
# Opportunities page — position table, quick-add form, inline full edit.
# Shipped: Tier 1 (quick-add + empty state), Tier 2 (filter bar),
#          Tier 3 (positions table + deadline urgency),
#          Tier 4 (row selection + Overview / Requirements / Materials / Notes tabs).
# Pending: Tier 5 (Save / Delete actions with confirm dialog).

import datetime
from typing import Any

import streamlit as st
import database
import config


def _deadline_urgency(date_str: str | None) -> str:
    """Return 'urgent', 'alert', or '' based on days until the deadline.

    Thresholds come from config so changing DEADLINE_URGENT_DAYS /
    DEADLINE_ALERT_DAYS in one place updates both the flag and the dashboard."""
    if not date_str:
        return ""
    try:
        days = (datetime.date.fromisoformat(date_str) - datetime.date.today()).days
    except (ValueError, TypeError):
        return ""
    if days <= config.DEADLINE_URGENT_DAYS:
        return "urgent"
    if days <= config.DEADLINE_ALERT_DAYS:
        return "alert"
    return ""

database.init_db()

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
col_status, col_priority, col_field = st.columns([2, 2, 3])
with col_status:
    status_filter = st.selectbox(
        "Status", ["All"] + config.STATUS_VALUES, index=0, key="filter_status"
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

    display_cols = [
        "position_name", "institute", "priority", "status",
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
            "status":           st.column_config.TextColumn("Status",    width="medium"),
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
        st.session_state["selected_position_id"] = int(
            df_display.iloc[selected_rows[0]]["id"]
        )
    elif st.session_state.pop("_skip_table_reset", False):
        # T5-A: one-shot bypass consumed here. The save handler sets
        # _skip_table_reset=True before its st.rerun() so this branch
        # preserves selected_position_id across the save cycle — otherwise
        # st.dataframe resets its event (same protective behaviour pinned
        # by test_filter_change_after_selection_clears_selection) and the
        # edit panel would collapse right after the user hit Save.
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
        st.subheader(f"{r['position_name']} · {r['status']}")

        # T4-C: widget-value trap — once session_state[key] is set, Streamlit
        # ignores the `value=` argument on later reruns, so the form would
        # "stick" on the first selected row. Pre-seed widget state whenever
        # the selection changes, tracked via the internal _edit_form_sid
        # sentinel. Stored values match widget types: str for text, date|None
        # for date_input, config-vocabulary strings for the selectboxes.
        if st.session_state.get("_edit_form_sid") != sid:
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

            st.session_state["edit_position_name"] = r["position_name"] or ""
            st.session_state["edit_institute"]     = r["institute"] or ""
            st.session_state["edit_field"]         = r["field"] or ""
            st.session_state["edit_priority"]      = safe_priority
            st.session_state["edit_status"]        = safe_status
            st.session_state["edit_deadline_date"] = safe_deadline
            st.session_state["edit_link"]          = r["link"] or ""

            # T4-D: pre-seed one session_state slot per req_* column so the
            # Requirements-tab radios render with the row's current values.
            # Same F2-style coercion as priority/status: if a column holds
            # an unknown string (future migration, raw SQL edit) or is
            # missing from the row (e.g. during a migration-in-progress
            # test), fall back to 'N' — the schema default.
            for req_col, done_col, _label in config.REQUIREMENT_DOCS:
                v = r[req_col] if req_col in r.index else None
                safe_v = v if v in config.REQUIREMENT_VALUES else "N"
                st.session_state[f"edit_{req_col}"] = safe_v

                # T4-E: pre-seed one bool per done_* column for the Materials
                # checkboxes. done_* is INTEGER 0/1; anything else (None,
                # unexpected values) coerces to False. The checkbox itself
                # is only rendered by the Materials tab when its req_* is
                # 'Y' — but we seed unconditionally so switching a
                # requirement on mid-edit doesn't flash an unseeded checkbox.
                d = r[done_col] if done_col in r.index else 0
                st.session_state[f"edit_{done_col}"] = (d == 1)

            # T4-F: pre-seed the Notes text_area. positions.notes is TEXT
            # NULL-able (schema: database.py ~line 84), so coerce None → ""
            # before it reaches st.text_area — the widget expects str.
            st.session_state["edit_notes"] = r["notes"] or ""

            st.session_state["_edit_form_sid"]     = sid

        # config.EDIT_PANEL_TABS is the single source for label + order.
        # Unpacking by index keeps T4-C–F wiring readable even if tabs grow.
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
                st.selectbox("Status",   config.STATUS_VALUES,
                             key="edit_status")
                st.date_input("Deadline",      key="edit_deadline_date")
                st.text_input("Link",          key="edit_link")
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
            # ...) is preserved across any req_* flip Y↔Optional↔N. If the
            # user later switches req_cv back to 'Y', the Materials tab will
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
        with tabs[2]:   # Materials — T4-E
            # State-driven: the visible checkbox list is built from the LIVE
            # session_state["edit_{req_col}"] values (not the DB row), so
            # toggling a radio on the Requirements tab updates this tab on
            # the next rerun. Uses the Y-only filter that matches the
            # readiness definition in database.py (~line 404).
            visible = [
                (req_col, done_col, label)
                for req_col, done_col, label in config.REQUIREMENT_DOCS
                if st.session_state.get(f"edit_{req_col}") == "Y"
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
                    # Mirror T4-C/T4-D placeholder submit.
                    st.form_submit_button(
                        "Save Changes",
                        disabled=True,
                        help="Coming in Tier 5 — Save/Delete actions.",
                    )
        with tabs[3]:   # Notes — T4-F
            # Single free-form text_area for miscellaneous context (contact
            # details, interview prep hints, follow-up reminders). Pre-seeded
            # from the row's notes column via the _edit_form_sid block above,
            # so selecting a different row re-loads its notes. Mirrors the
            # T4-C/D/E submit-button placeholder contract — real save wires in
            # Tier 5.
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
                st.form_submit_button(
                    "Save Changes",
                    disabled=True,
                    help="Coming in Tier 5 — Save/Delete actions.",
                )
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
