# pages/1_Opportunities.py
# Opportunities page — position table, quick-add form, inline full edit.
# Phase 3 Tier 1: quick-add form + empty state.
# Tiers 2–5 will add: filter bar, table, row edit, save/delete.

import streamlit as st
import database
import config

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

        submitted = st.form_submit_button("+ Add Position")

    if submitted:
        if not position_name:
            st.error("Position Name is required.")
        else:
            fields: dict = {
                "position_name": position_name,
                "institute":     institute,
                "field":         field,
                "priority":      priority,
                "link":          link,
            }
            if deadline_date is not None:
                fields["deadline_date"] = deadline_date.isoformat()
            database.add_position(fields)
            st.success(f'Added "{position_name}" to your list.')
            st.rerun()

# ── TIER 2: Filter bar ────────────────────────────────────────────────────────
# col_status, col_priority, col_field = st.columns([2, 2, 3])
# with col_status:
#     status_filter = st.selectbox("Status", ["All"] + config.STATUS_VALUES, index=0)
# with col_priority:
#     priority_filter = st.selectbox("Priority", ["All"] + config.PRIORITY_VALUES, index=0)
# with col_field:
#     field_filter = st.text_input("Field", placeholder="Filter by field…")

# ── TIER 3: Positions table ───────────────────────────────────────────────────
df = database.get_all_positions()

if df.empty:
    st.info("No positions yet — use Quick Add above to get started.")
else:
    # Full table display (Tier 3) and row-click edit (Tiers 4–5) come next.
    st.caption(f"{len(df)} position(s) tracked.")

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
