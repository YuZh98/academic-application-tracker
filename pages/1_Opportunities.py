# pages/1_Opportunities.py
# Opportunities page — position table, quick-add form, inline full edit.
# Phase 3 Tier 1: quick-add form + empty state.
# Tiers 2–5 will add: filter bar, table, row edit, save/delete.

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
        try:
            database.add_position(fields)
            st.toast(f'Added "{position_name}" to your list.')
            st.rerun()
        except Exception as e:
            st.error(f"Could not save position: {e}")
            raise

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
    st.session_state.pop("selected_position_id", None)
    st.info("No positions yet — use Quick Add above to get started.")
elif df_filtered.empty:
    st.session_state.pop("selected_position_id", None)   # T4-A: same reason
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
        use_container_width=True,
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
    else:
        # Empty selection, or index out-of-bounds after filter/data change.
        st.session_state.pop("selected_position_id", None)

# ── TIER 4: Row-click inline expansion ───────────────────────────────────────
# selected_id stored in st.session_state["selected_position_id"]
# Clicking a row sets selected_id; clicking again collapses.
# tab_overview, tab_req, tab_mat, tab_notes = st.tabs(
#     ["Overview", "Requirements", "Materials", "Notes"]
# )
# Each tab renders the corresponding edit fields for the selected position.
# Status dropdown: st.selectbox(options=config.STATUS_VALUES)
# All date fields: st.date_input(value=None) → stored as .isoformat() if not None

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
