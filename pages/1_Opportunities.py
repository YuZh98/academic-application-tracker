# pages/1_Opportunities.py
# Opportunities page — position table, quick-add form, inline full edit.

import datetime
import math
from typing import Any, cast

import pandas as pd
import streamlit as st

import config
import database



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
    """Modal confirm dialog for irreversible position deletion.

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
        f'Delete **"{position_name}"**? This will also permanently delete all associated '
        f"application, interview, and recommender data. This **cannot be undone**."
    )
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Delete Position", key="edit_delete_confirm", type="primary"):
            if position_id is None:
                st.error(
                    "The position to delete could not be identified — please close this dialog and try again."
                )
                return
            try:
                database.delete_position(position_id)
                st.toast(f'Deleted "{position_name}".')
                st.session_state.pop("selected_position_id", None)
                st.session_state.pop("_edit_form_sid", None)
                st.session_state.pop("_delete_target_id", None)
                st.session_state.pop("_delete_target_name", None)
                st.rerun()
            except Exception as exc:
                st.error(f"Could not delete: {exc}")
    with col_cancel:
        if st.button("Cancel", key="edit_delete_cancel", width="stretch"):
            st.session_state.pop("_delete_target_id", None)
            st.session_state.pop("_delete_target_name", None)
            st.session_state["_skip_table_reset"] = True
            st.rerun()


def _deadline_urgency(date_str: Any) -> str:
    """Return the at-a-glance urgency glyph for a position's deadline.

    """
    if date_str is None or date_str == "":
        return config.urgency_glyph(None)
    if isinstance(date_str, float) and math.isnan(date_str):
        return config.urgency_glyph(None)
    try:
        days = (datetime.date.fromisoformat(str(date_str)) - datetime.date.today()).days
    except (ValueError, TypeError):
        return config.urgency_glyph(None)
    return config.urgency_glyph(days)


database.init_db()


st.set_page_config(
    page_title="Academic Application Tracker",
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
            link = st.text_input("Link", key="qa_link", placeholder="https://…")

        submitted = st.form_submit_button("+ Add Position", key="qa_submit")


if submitted:
    position_name = position_name.strip()
    institute = institute.strip()
    field = field.strip()
    link = link.strip()

    if not position_name:
        st.error("Position Name is required.")
    else:
        fields: dict[str, Any] = {  # F5: dict[str, Any] per project standard
            "position_name": position_name,
            "institute": institute,
            "field": field,
            "priority": priority,
            "link": link,
        }
        if deadline_date is not None:
            fields["deadline_date"] = deadline_date.isoformat()
        try:
            database.add_position(fields)
            st.toast(f'Added "{position_name}" to your list.')
            st.session_state.pop("positions_table", None)
            st.session_state.pop("selected_position_id", None)
            st.session_state.pop("_edit_form_sid", None)
            st.rerun()
        except Exception as e:
            st.error(f"Could not save position: {e}")

# ── TIER 2: Filter bar ────────────────────────────────────────────────────────
col_search, col_status, col_priority, col_field = st.columns([3, 2, 2, 3])
with col_search:
    search_filter = st.text_input(
        "Search",
        placeholder="Search by position name…",
        key="filter_search",
    )
with col_status:
    status_filter = st.selectbox(
        "Status",
        [config.FILTER_ALL] + config.STATUS_VALUES,
        index=0,
        format_func=lambda v: str(config.STATUS_LABELS.get(v, v)),
        key="filter_status",
    )
with col_priority:
    priority_filter = st.selectbox(
        "Priority", [config.FILTER_ALL] + config.PRIORITY_VALUES, index=0, key="filter_priority"
    )
with col_field:
    field_filter = st.text_input("Field", placeholder="Filter by field…", key="filter_field")

# ── TIER 3: Positions table ───────────────────────────────────────────────────
df = database.get_all_positions()

df_filtered: pd.DataFrame = df
if status_filter != config.FILTER_ALL:
    df_filtered = cast(pd.DataFrame, df_filtered[df_filtered["status"] == status_filter])
if priority_filter != config.FILTER_ALL:
    df_filtered = cast(pd.DataFrame, df_filtered[df_filtered["priority"] == priority_filter])
if field_filter.strip():
    # F1: regex=False treats the search term as a literal string, not a regex
    # pattern. Without it, "C++" raises re.error and crashes the page.
    df_filtered = cast(
        pd.DataFrame,
        df_filtered[
            df_filtered["field"].str.contains(
                field_filter.strip(), case=False, na=False, regex=False
            )
        ],
    )
if search_filter.strip():
    df_filtered = cast(
        pd.DataFrame,
        df_filtered[
            df_filtered["position_name"].str.contains(
                search_filter.strip(), case=False, na=False, regex=False
            )
        ],
    )

if df.empty:
    st.session_state.pop("selected_position_id", None)
    st.session_state.pop("_edit_form_sid", None)
    st.info(config.EMPTY_NO_POSITIONS)
elif df_filtered.empty:
    st.session_state.pop("selected_position_id", None)  # same reason
    st.session_state.pop("_edit_form_sid", None)  # F4: same pairing
    st.info(config.EMPTY_FILTERED_POSITIONS)
else:
    _n = len(df_filtered)
    st.caption(f"{_n} " + ("position" if _n == 1 else "positions") + " tracked.")

    df_display = df_filtered.copy()
    df_display["deadline_urgency"] = df_display["deadline_date"].apply(_deadline_urgency)
    df_display["status_label"] = df_display["status"].map(
        lambda v: config.STATUS_LABELS.get(v, v) if isinstance(v, str) else v
    )

    display_cols = [
        "position_name",
        "institute",
        "priority",
        "status_label",
        "deadline_date",
        "deadline_urgency",
        "link",
    ]
    event = st.dataframe(
        df_display,
        width="stretch",
        hide_index=True,
        column_order=display_cols,
        column_config={
            "position_name": st.column_config.TextColumn(
                "Position",
                width="large",
                help="Position title",
            ),
            "institute": st.column_config.TextColumn(
                "Institute",
                width="medium",
                help="Institution or organisation",
            ),
            "priority": st.column_config.TextColumn(
                "Priority",
                width="small",
                help="Your personal priority for this position",
            ),
            "status_label": st.column_config.TextColumn(
                "Status",
                width="medium",
                help="Current stage in the application pipeline",
            ),
            "deadline_date": st.column_config.TextColumn(
                "Deadline",
                width="small",
                help="Application submission deadline",
            ),
            "deadline_urgency": st.column_config.TextColumn(
                "Urgency",
                width="small",
                help="🔴 ≤7 days · 🟡 ≤30 days · blank = not urgent · — = no deadline",
            ),
            "link": st.column_config.LinkColumn(
                "Link",
                display_text="🔗 Open",
                width="small",
                help="Link to the job posting",
            ),
        },
        key="positions_table",
        on_select="rerun",
        selection_mode="single-row",
    )


    selected_rows = list(event.selection.rows) if event is not None else []  # type: ignore[attr-defined]
    if selected_rows and 0 <= selected_rows[0] < len(df_display):
        new_sid = int(df_display.iloc[selected_rows[0]]["id"])
        prev_sid = st.session_state.get("selected_position_id")
        if prev_sid is not None and prev_sid != new_sid:
            st.session_state.pop("_delete_target_id", None)
            st.session_state.pop("_delete_target_name", None)
        st.session_state["selected_position_id"] = new_sid
    elif (
        st.session_state.pop("_skip_table_reset", False) or "_delete_target_id" in st.session_state
    ):
        pass
    else:
        st.session_state.pop("selected_position_id", None)
        st.session_state.pop("_edit_form_sid", None)

# ── TIER 4: Edit panel (subheader + tabs shell) ──────────────────────────────

if "selected_position_id" in st.session_state:
    sid = st.session_state["selected_position_id"]
    selected_row = df[df["id"] == sid]
    if not selected_row.empty:
        r = selected_row.iloc[0]
       
        _status_label = config.STATUS_LABELS.get(r["status"], r["status"])
        st.subheader(f"{r['position_name']} · {_status_label}")

        
        
        safe_priority = (
            r["priority"] if r["priority"] in config.PRIORITY_VALUES else config.PRIORITY_VALUES[0]
        )
        safe_status = (
            r["status"] if r["status"] in config.STATUS_VALUES else config.STATUS_VALUES[0]
        )
        
        raw_work_auth = r["work_auth"] if "work_auth" in r.index else None
        safe_work_auth = (
            raw_work_auth
            if raw_work_auth in config.WORK_AUTH_OPTIONS
            else config.WORK_AUTH_OPTIONS[0]
        )
        
        try:
            safe_deadline = (
                datetime.date.fromisoformat(r["deadline_date"]) if r["deadline_date"] else None
            )
        except (ValueError, TypeError):
            safe_deadline = None


        canonical: dict[str, Any] = {
            "edit_position_name": _safe_str(r["position_name"]),
            "edit_institute": _safe_str(r["institute"]),
            "edit_field": _safe_str(r["field"]),
            "edit_priority": safe_priority,
            "edit_status": safe_status,
            "edit_deadline_date": safe_deadline,
            "edit_link": _safe_str(r["link"]),
            "edit_work_auth": safe_work_auth,
            "edit_work_auth_note": (
                _safe_str(r["work_auth_note"]) if "work_auth_note" in r.index else ""
            ),
            "edit_notes": _safe_str(r["notes"]),
        }
        for req_col, done_col, _label in config.REQUIREMENT_DOCS:
            v = r[req_col] if req_col in r.index else None
            canonical[f"edit_{req_col}"] = (
                v if v in config.REQUIREMENT_VALUES else config.REQUIREMENT_VALUES[-1]
            )
            d = r[done_col] if done_col in r.index else 0
            canonical[f"edit_{done_col}"] = d == 1

        sid_changed = st.session_state.get("_edit_form_sid") != sid
        for _key, _value in canonical.items():
            if sid_changed or _key not in st.session_state:
                st.session_state[_key] = _value
        st.session_state["_edit_form_sid"] = sid

    
        tabs = st.tabs(config.EDIT_PANEL_TABS)

        with tabs[0]: 
            with st.form("edit_overview_form"):
                st.text_input("Position Name", key="edit_position_name")
                st.text_input("Institute", key="edit_institute")
                st.text_input("Field", key="edit_field")
                st.selectbox("Priority", config.PRIORITY_VALUES, key="edit_priority")
                st.selectbox(
                    "Status",
                    config.STATUS_VALUES,
                    format_func=lambda v: str(config.STATUS_LABELS.get(v, v)),
                    key="edit_status",
                )
                st.date_input("Deadline", key="edit_deadline_date")
                st.text_input("Link", key="edit_link")
                st.selectbox(
                    "Work Authorization",
                    config.WORK_AUTH_OPTIONS,
                    key="edit_work_auth",
                    help="Does this posting explicitly accept your work authorization / visa status?",
                )
                st.text_area("Work Authorization Notes", key="edit_work_auth_note")
                overview_submitted = st.form_submit_button(
                    "Save Changes",
                    key="edit_overview_submit",
                )

        
            if overview_submitted:
                new_name = (st.session_state.get("edit_position_name") or "").strip()
                if not new_name:
                    st.error("Position Name is required.")
                else:
                    new_deadline = st.session_state.get("edit_deadline_date")
                    payload: dict[str, Any] = {
                        "position_name": new_name,
                        "institute": st.session_state.get("edit_institute", ""),
                        "field": st.session_state.get("edit_field", ""),
                        "priority": st.session_state["edit_priority"],
                        "status": st.session_state["edit_status"],
                        "deadline_date": (
                            new_deadline.isoformat()
                            if isinstance(new_deadline, datetime.date)
                            else None
                        ),
                        "link": st.session_state.get("edit_link", ""),
                        "work_auth": st.session_state["edit_work_auth"],
                        "work_auth_note": st.session_state.get("edit_work_auth_note", ""),
                    }
                    try:
                        database.update_position(sid, payload)
                        st.toast(f'Saved overview for "{new_name}".')
                        st.session_state.pop("_edit_form_sid", None)
                        st.session_state["_skip_table_reset"] = True
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save changes: {exc}")

           
            if st.button("Delete", type="primary", key="edit_delete"):
                st.session_state["_delete_target_id"] = sid
                st.session_state["_delete_target_name"] = r["position_name"]
                _confirm_delete_dialog()
            elif st.session_state.get("_delete_target_id") == sid:
                _confirm_delete_dialog()

        with tabs[1]: 
            with st.form("edit_requirements_form"):
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

        with tabs[2]:       
            visible = [
                (req_col, done_col, label)
                for req_col, done_col, label in config.REQUIREMENT_DOCS
                if st.session_state.get(f"edit_{req_col}") == "Yes"
            ]
            if not visible:
                st.info(
                    "No required documents yet — mark docs as required on the Requirements tab."
                )
            else:
                with st.form("edit_materials_form"):
                    for _req_col, done_col, label in visible:
                        st.checkbox(label, key=f"edit_{done_col}")
                    materials_submitted = st.form_submit_button(
                        "Save Changes",
                        key="edit_materials_submit",
                    )

                if materials_submitted:
                    payload: dict[str, Any] = {
                        done_col: int(bool(st.session_state.get(f"edit_{done_col}")))
                        for _req_col, done_col, _label in visible
                    }
                    try:
                        database.update_position(sid, payload)
                        st.toast(f'Saved materials for "{r["position_name"]}".')
                        st.session_state.pop("_edit_form_sid", None)
                        st.session_state["_skip_table_reset"] = True
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not save materials: {exc}")

        with tabs[3]: 
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
        st.session_state.pop("selected_position_id", None)
        st.session_state.pop("_edit_form_sid", None)

