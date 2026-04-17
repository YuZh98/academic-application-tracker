# pages/1_Opportunities.py
# Opportunities page — position table, quick-add form, inline full edit.
# Phase 3 Tier 0 skeleton: section markers only.
# Tiers 1–5 will fill each section in order.

import streamlit as st
import database
import config

database.init_db()

st.title("Opportunities")

# ── TIER 1: Quick-add expander ────────────────────────────────────────────────
# with st.expander("Quick Add", expanded=False):
#   Fields driven by config.QUICK_ADD_FIELDS:
#     position_name (text_input)
#     institute     (text_input)
#     field         (text_input)
#     deadline_date (date_input, value=None)
#     priority      (selectbox, options=config.PRIORITY_VALUES)
#     link          (text_input)
#   with st.form(key="quick_add_form"):
#     ... inputs ...
#     submitted = st.form_submit_button("+ Add Position")
#     if submitted:
#         database.add_position(fields)
#         st.rerun()

# ── TIER 2: Filter bar ────────────────────────────────────────────────────────
# col_status, col_priority, col_field = st.columns([2, 2, 3])
# with col_status:
#     status_filter = st.selectbox("Status", ["All"] + config.STATUS_VALUES, index=0)
# with col_priority:
#     priority_filter = st.selectbox("Priority", ["All"] + config.PRIORITY_VALUES, index=0)
# with col_field:
#     field_filter = st.text_input("Field", placeholder="Filter by field…")

# ── TIER 3: Positions table ───────────────────────────────────────────────────
# df = database.get_all_positions()
# Apply status_filter / priority_filter / field_filter to df
# st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
# — deadline cell colored red if ≤ config.DEADLINE_URGENT_DAYS days away

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

st.caption("Phase 3 Tier 0 scaffold — feature tiers coming next.")
