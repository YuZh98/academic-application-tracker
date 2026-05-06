# pages/3_Recommenders.py
# Recommenders page — letter tracking, pending alerts, and reminder helpers.
import math
from datetime import date
from typing import Any, cast
from urllib.parse import quote

import pandas as pd
import streamlit as st

import config
import database

from config import EM_DASH

st.set_page_config(
    page_title="Recommenders — Academic Application Tracker",
    page_icon="📋",
    layout="wide",
)

database.init_db()

st.title("Recommenders")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _safe_str(v: Any) -> str:
    """Coerce a DataFrame cell to a widget-safe ``str``.

    Mirror of the helpers in pages/1_Opportunities.py +
    pages/2_Applications.py — pandas surfaces ``float('nan')`` for NULL
    TEXT cells once any other row in the column has a value, and the
    ``r[col] or ""`` idiom misfires because ``bool(float('nan')) is True``.
    Treat None and any NaN-truthy value as ``""``."""
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v)


def _safe_str_or_em(v: Any) -> str:
    """Render a TEXT cell as its string value or EM_DASH for empty."""
    s = _safe_str(v)
    return s if s else EM_DASH


def _format_date_or_em(v: Any) -> str:
    """Format an ISO date string as 'Mon D' or return EM_DASH for null."""
    if not v or (isinstance(v, float) and math.isnan(v)):
        return EM_DASH
    try:
        d = date.fromisoformat(str(v))
        return f"{d.strftime('%b')} {d.day}"
    except (ValueError, TypeError):
        return EM_DASH


def _coerce_iso_to_date(v: Any) -> date | None:
    """Coerce a stored ISO ``YYYY-MM-DD`` string to a ``datetime.date``
    for ``st.date_input`` pre-seed; return ``None`` for None / NaN /
    empty / unparseable."""
    s = _safe_str(v)
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _format_label(institute: Any, position_name: str) -> str:
    """'{institute}: {position_name}' when institute is non-empty; bare
    position_name otherwise. Mirrors app.py T5 Label precedent — 'or'
    treats None and '' both as falsy, so no explicit pd.isna guard needed
    here: get_pending_recommenders surfaces missing TEXT cells as None."""
    if institute:
        return f"{institute}: {position_name}"
    return position_name


def _format_due(deadline_iso: str | None) -> str:
    """Due-date in 'Mon D' form (no year — near-future deadlines).
    Em-dash for NULL/empty, mirroring NEXT_INTERVIEW_EMPTY.
    pd.isna() catches both None and NaN-from-pandas (dev-notes gotcha #13)."""
    if deadline_iso is None or pd.isna(deadline_iso) or deadline_iso == "":
        return EM_DASH
    d = date.fromisoformat(str(deadline_iso))
    return f"{d.strftime('%b')} {d.day}"


def _format_confirmed(v: Any) -> str:
    """Tri-state Confirmed column: NULL → '—', 0 → 'No', 1 → 'Yes'.
    Mirrors the same vocabulary used by the inline edit selectbox so the
    table cell and the edit widget read coherently for the user."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return EM_DASH
    try:
        i = int(v)
    except (TypeError, ValueError):
        return EM_DASH
    return "Yes" if i == 1 else "No"


# ── Reminder helpers ──────────────────────────────────────────────────────


def _build_compose_mailto(*, recommender_name: str, n_positions: int) -> str:
    """Build the DESIGN §8.4 mailto URL for the Compose button (T6-A).
    The subject interpolates the position count; the body interpolates
    the recommender's name. No `to:` field — the recommenders schema
    doesn't store emails today, so the OS-level mail client prompts
    the user for the recipient.

    Subject follows English pluralization rules (DESIGN §8.4): at
    ``N=1`` reads "letter for 1 <APPLICATION_LABEL>" (singular both
    nouns); at ``N≥2`` reads "letters for N <APPLICATION_LABEL>s"."""
    label = config.APPLICATION_LABEL
    if n_positions == 1:
        subject = f"Following up: letter for 1 {label}"
    else:
        subject = f"Following up: letters for {n_positions} {label}s"
    body = (
        f"Hi {recommender_name}, just a quick check-in on the letters of "
        f"recommendation you offered. Thank you so much!"
    )
    return f"mailto:?subject={quote(subject)}&body={quote(body)}"


def _build_llm_prompt(
    *,
    tone: str,
    recommender_name: str,
    relationship: str | None,
    group: pd.DataFrame,
    days_ago: int,
) -> str:
    """Build one LLM-prompt code block body per DESIGN §8.4 (T6-B).

    Embeds:
      - recommender name + relationship (relationship omitted on NULL),
      - every owed position (institute: position_name + deadline ISO),
      - days-since-asked summary (max wait across the group),
      - target tone keyword,
      - explicit instruction asking the LLM to return BOTH subject and
        body so the user can paste either / both into their mail client.

    The prompt is plain prose (rendered via `st.code(..., language='text')`
    so Streamlit's copy-on-hover button is exposed without applying any
    syntax highlighting that would mis-color the prose)."""
    rel_str = f" ({relationship})" if relationship and not pd.isna(relationship) else ""

    pos_lines: list[str] = []
    for _, row in group.iterrows():
        inst = _safe_str(row["institute"])
        pname = _safe_str(row["position_name"])
        label = f"{inst}: {pname}" if inst else pname
        deadline_iso = _safe_str(row["deadline_date"])
        deadline_part = deadline_iso if deadline_iso else "no deadline"
        pos_lines.append(f"- {label} (deadline {deadline_part})")
    positions_block = "\n".join(pos_lines)

    return (
        f"Please draft a {tone} reminder email to my recommender about "
        f"pending letters of recommendation.\n"
        f"\n"
        f"Recommender: {recommender_name}{rel_str}\n"
        f"Days since I asked: {days_ago}\n"
        f"Positions still owed:\n"
        f"{positions_block}\n"
        f"\n"
        f"Return BOTH a subject line and a body so I can paste either or "
        f"both into my mail client. Do not include a signature."
    )


# ── Recommender Alerts ───────────────────────────────────────────────────────

st.subheader("Recommender Alerts")
st.caption(
    f"Recommenders asked more than {config.RECOMMENDER_ALERT_DAYS} days ago who have not yet submitted a letter."
)
_pending_recs = database.get_pending_recommenders()

if _pending_recs.empty:
    st.info(config.EMPTY_PENDING_RECOMMENDERS)
else:
    _today = date.today()

    for _idx, (_name, _group) in enumerate(_pending_recs.groupby("recommender_name", sort=False)):
        with st.container(border=True):
            _rel: Any = _group.iloc[0]["relationship"]
            _rel_str = f" ({_rel})" if _rel and not pd.isna(_rel) else ""

            _bullets: list[str] = []
            _per_row_days: list[int] = []
            for _, _row in _group.iterrows():
                _inst: Any = _row["institute"]
                _pos_name: Any = _row["position_name"]
                _label = _format_label(_inst, str(_pos_name))
                _asked_iso: str = str(_row["asked_date"])
                _days_ago = (_today - date.fromisoformat(_asked_iso)).days
                _per_row_days.append(_days_ago)
                _due_raw: Any = _row["deadline_date"]
                _due = _format_due(_due_raw)
                _bullets.append(f"- {_label} (asked {_days_ago}d ago, due {_due})")

            _body = f"⚠️ **{_name}**{_rel_str}\n" + "\n".join(_bullets)
            st.markdown(_body)

            # ──  Compose reminder email ────────────────────────────
            
            _mailto_url = _build_compose_mailto(
                recommender_name=str(_name),
                n_positions=len(_group),
            )
            st.link_button(
                "📧 Compose Reminder Email",
                url=_mailto_url,
                key=f"recs_compose_{_idx}",
            )

            # ── LLM prompts expander ──────────────────────────────
            _max_days = max(_per_row_days) if _per_row_days else 0
            _rel_for_prompt: str | None = None if (_rel is None or pd.isna(_rel)) else str(_rel)
            with st.expander(
                f"Draft email with AI ({len(config.REMINDER_TONES)} styles)",
                expanded=False,
            ):
                for _tone in config.REMINDER_TONES:
                    _prompt = _build_llm_prompt(
                        tone=_tone,
                        recommender_name=str(_name),
                        relationship=_rel_for_prompt,
                        group=_group,
                        days_ago=_max_days,
                    )
                    st.code(_prompt, language="text")


# ── All Recommenders ─────────────────────────────────────────────────────

st.subheader("All Recommenders")

# ── Build label↔id mapping for the position selectboxes ─────────────────────

_positions_df = database.get_all_positions()
_position_label_to_id: dict[str, int] = {}
for _, _pos_row in _positions_df.iterrows():
    _label = _format_label(
        _safe_str(_pos_row["institute"]),
        _safe_str(_pos_row["position_name"]),
    )
    # CL1 type-clean: pandas-stubs widens iterrows cells to
    # Series | ndarray | Any. Funnel through Any so int() only sees
    # the runtime scalar (PR #22 precedent).
    _pos_id_raw: Any = _pos_row["id"]
    _position_label_to_id[_label] = int(_pos_id_raw)


# ── Add recommender form ───────────────────────────────────────────────


with st.expander("Add Recommender", expanded=False):
    with st.form("recs_add_form"):
        _add_col1, _add_col2 = st.columns(2)
        with _add_col1:
            st.selectbox(
                "Position",
                options=list(_position_label_to_id.keys()),
                key="recs_add_position",
            )
            st.text_input("Recommender Name *", key="recs_add_name")
        with _add_col2:
            st.selectbox(
                "Relationship",
                options=config.RELATIONSHIP_VALUES,
                key="recs_add_relationship",
            )
            st.date_input(
                "Asked date",
                value=None,
                key="recs_add_asked_date",
            )
        _add_submitted = st.form_submit_button("+ Add Recommender", key="recs_add_submit")

if _add_submitted:
    _name_raw = (st.session_state.get("recs_add_name") or "").strip()
    _pos_label = st.session_state.get("recs_add_position")
    _rel_pick = st.session_state.get("recs_add_relationship")
    _asked = st.session_state.get("recs_add_asked_date")

    if not _name_raw:
        st.error("Recommender Name is required.")
    elif _pos_label not in _position_label_to_id:
        st.error("Pick a position before adding a recommender.")
    else:
        _pos_id = _position_label_to_id[_pos_label]
        _fields: dict[str, Any] = {
            "recommender_name": _name_raw,
            "relationship": _rel_pick,
            "asked_date": _asked.isoformat() if _asked else None,
        }
        try:
            database.add_recommender(_pos_id, _fields)
            st.toast(f'Added "{_name_raw}".')
            st.rerun()
        except Exception as e:
            st.error(f"Could not add recommender: {e}")


# ── Filter bar ─────────────────────────────────────────────────────────

_recs_df = database.get_all_recommenders()


_position_filter_options = [config.FILTER_ALL] + list(_position_label_to_id.keys())

if _recs_df.empty:
    _recommender_filter_options = [config.FILTER_ALL]
else:
    _seen: list[str] = []
    for _n in _recs_df["recommender_name"]:
        _ns = _safe_str(_n)
        if _ns and _ns not in _seen:
            _seen.append(_ns)
    _recommender_filter_options = [config.FILTER_ALL] + _seen

_filter_col1, _filter_col2 = st.columns(2)
with _filter_col1:
    _pos_filter = st.selectbox(
        "Filter by position",
        options=_position_filter_options,
        index=0,
        key="recs_filter_position",
    )
with _filter_col2:
    _rec_filter = st.selectbox(
        "Filter by recommender",
        options=_recommender_filter_options,
        index=0,
        key="recs_filter_recommender",
    )


# ── Table render ──────────────────────────────────────────────────────
_filtered_df: pd.DataFrame = _recs_df.copy()
if _pos_filter != config.FILTER_ALL:
    _target_pos_id = _position_label_to_id.get(_pos_filter)
    if _target_pos_id is not None:
        _filtered_df = cast(
            pd.DataFrame,
            _filtered_df[_filtered_df["position_id"] == _target_pos_id],
        )
if _rec_filter != config.FILTER_ALL:
    _filtered_df = cast(
        pd.DataFrame,
        _filtered_df[_filtered_df["recommender_name"] == _rec_filter],
    )

_filtered_df = _filtered_df.reset_index(drop=True)

if _filtered_df.empty:
    _display_df = pd.DataFrame(
        columns=[
            "Position",
            "Recommender",
            "Relationship",
            "Asked",
            "Confirmed",
            "Submitted",
        ]
    )
else:
    _display_df = pd.DataFrame(
        {
            "Position": _filtered_df.apply(
                lambda r: _format_label(
                    _safe_str(r["institute"]),
                    _safe_str(r["position_name"]),
                ),
                axis=1,
            ),
            "Recommender": _filtered_df["recommender_name"].apply(_safe_str_or_em),
            "Relationship": _filtered_df["relationship"].apply(_safe_str_or_em),
            "Asked": _filtered_df["asked_date"].apply(_format_date_or_em),
            "Confirmed": _filtered_df["confirmed"].apply(_format_confirmed),
            "Submitted": _filtered_df["submitted_date"].apply(_format_date_or_em),
        }
    )

_event = st.dataframe(
    _display_df,
    width="stretch",
    hide_index=True,
    column_config={
        "Position": st.column_config.TextColumn(
            "Position",
            width="large",
            help="Position this recommendation is for",
        ),
        "Recommender": st.column_config.TextColumn(
            "Recommender",
            width="medium",
            help="Recommender's name",
        ),
        "Relationship": st.column_config.TextColumn(
            "Relationship",
            width="medium",
            help="Your relationship with this recommender",
        ),
        "Asked": st.column_config.TextColumn(
            "Asked",
            width="small",
            help="Date you asked for the letter",
        ),
        "Confirmed": st.column_config.TextColumn(
            "Confirmed",
            width="small",
            help="Whether the recommender confirmed they will write",
        ),
        "Submitted": st.column_config.TextColumn(
            "Submitted",
            width="small",
            help="Date the letter was submitted (— if not yet)",
        ),
    },
    key="recs_table",
    on_select="rerun",
    selection_mode="single-row",
)


# ── Selection resolution ─────────────────────────────────────────────

_selected_rows = list(_event.selection.rows) if _event is not None else []  # type: ignore[attr-defined]
if _selected_rows and 0 <= _selected_rows[0] < len(_filtered_df):
    _new_rec_id = int(_filtered_df.iloc[_selected_rows[0]]["id"])
    _prev_rec_id = st.session_state.get("recs_selected_id")
    if _prev_rec_id is not None and _prev_rec_id != _new_rec_id:
        st.session_state.pop("_recs_delete_target_id", None)
        st.session_state.pop("_recs_delete_target_name", None)
    st.session_state["recs_selected_id"] = _new_rec_id
elif (
    st.session_state.pop("_recs_skip_table_reset", False)
    or "_recs_delete_target_id" in st.session_state
):
    pass
else:
    st.session_state.pop("recs_selected_id", None)
    st.session_state.pop("_recs_edit_form_sid", None)


# ── Delete confirm dialog 
@st.dialog("Delete this recommender?")
def _confirm_delete_recommender_dialog() -> None:
    """Modal confirm dialog for irreversible recommender deletion. The
    target id + display name come from session_state sentinels set by
    the edit card's Delete-button click; passing via session_state lets
    the outer page re-invoke the dialog on every rerun while the pending
    flag is set, which is what keeps Confirm/Cancel reachable through
    AppTest's script-run model ."""
    rec_id_target: int | None = st.session_state.get("_recs_delete_target_id")
    rec_name_target: str = st.session_state.get("_recs_delete_target_name", "")
    st.warning(f'Delete **"{rec_name_target}"**? This **cannot be undone**.')
    _col_confirm, _col_cancel = st.columns(2)
    with _col_confirm:
        if st.button(
            "Confirm Delete",
            type="primary",
            key="recs_delete_confirm",
            width="stretch",
        ):
            if rec_id_target is None:
                st.error("Delete target was lost — please re-open the dialog.")
                return
            try:
                database.delete_recommender(rec_id_target)
                st.toast(f'Deleted "{rec_name_target}".')
                # Paired cleanup — the selection sentinel + form-id sentinel
                # go together throughout the page (mirror of the
                # Opportunities pattern).
                st.session_state.pop("recs_selected_id", None)
                st.session_state.pop("_recs_edit_form_sid", None)
                st.session_state.pop("_recs_delete_target_id", None)
                st.session_state.pop("_recs_delete_target_name", None)
                st.rerun()
            except Exception as e:
                # GUIDELINES §8: friendly error, no re-raise. Sentinels
                # survive so the dialog re-opens for retry on the next
                # rerun (matches the Opportunities precedent).
                st.error(f"Could not delete: {e}")
    with _col_cancel:
        if st.button(
            "Cancel",
            key="recs_delete_cancel",
            width="stretch",
        ):
            st.session_state.pop("_recs_delete_target_id", None)
            st.session_state.pop("_recs_delete_target_name", None)
            # Preserve selection across the cancel-driven rerun (mirror
            # of Opportunities: the dataframe event resets on rerun,
            # which would otherwise pop recs_selected_id and collapse
            # the edit panel).
            st.session_state["_recs_skip_table_reset"] = True
            st.rerun()


# ── Inline edit card ──────────────────────────────────────────────────

if "recs_selected_id" in st.session_state:
    _rec_id = int(st.session_state["recs_selected_id"])
    _selected_match = _recs_df[_recs_df["id"] == _rec_id]
    if not _selected_match.empty:
        _rec_row = _selected_match.iloc[0]
        _rec_name = _safe_str(_rec_row["recommender_name"])

        with st.container(border=True):
            st.markdown(f"**Editing: {_rec_name or EM_DASH}**")

            # ── Pre-seed widget state ───────────────────────────────────
    
            _sid_changed = st.session_state.get("_recs_edit_form_sid") != _rec_id

            _raw_confirmed = _rec_row["confirmed"]
            _safe_confirmed: int | None
            if _raw_confirmed is None or (
                isinstance(_raw_confirmed, float) and math.isnan(_raw_confirmed)
            ):
                _safe_confirmed = None
            else:
                try:
                    _safe_confirmed = int(_raw_confirmed)
                except (TypeError, ValueError):
                    _safe_confirmed = None
            if _safe_confirmed not in (None, 0, 1):
                _safe_confirmed = None

            _canonical: dict[str, Any] = {
                "recs_edit_asked_date": _coerce_iso_to_date(_rec_row["asked_date"]),
                "recs_edit_confirmed": _safe_confirmed,
                "recs_edit_submitted_date": _coerce_iso_to_date(_rec_row["submitted_date"]),
                "recs_edit_reminder_sent": bool(_rec_row.get("reminder_sent") or 0),
                "recs_edit_reminder_sent_date": _coerce_iso_to_date(_rec_row["reminder_sent_date"]),
                "recs_edit_notes": _safe_str(_rec_row["notes"]),
            }
            for _key, _value in _canonical.items():
                if _sid_changed or _key not in st.session_state:
                    st.session_state[_key] = _value
            st.session_state["_recs_edit_form_sid"] = _rec_id

            # ── Edit form ───────────────────────────────────────────────
            with st.form("recs_edit_form"):
                _e_col1, _e_col2 = st.columns(2)
                with _e_col1:
                    st.date_input(
                        "Asked date",
                        value=None,
                        key="recs_edit_asked_date",
                    )
                    st.selectbox(
                        "Confirmed",
                        options=[None, 0, 1],
                        format_func=lambda v: (
                            "Not yet / unknown" if v is None else ("Yes" if v == 1 else "No")
                        ),
                        key="recs_edit_confirmed",
                        help="Whether the recommender has confirmed they will write the letter.",
                    )
                    st.date_input(
                        "Submitted date",
                        value=None,
                        key="recs_edit_submitted_date",
                    )
                with _e_col2:
                    st.checkbox(
                        "Reminder sent",
                        key="recs_edit_reminder_sent",
                    )
                    st.date_input(
                        "Reminder date",
                        value=None,
                        key="recs_edit_reminder_sent_date",
                    )
                st.text_area(
                    "Notes",
                    key="recs_edit_notes",
                )
                _edit_submitted = st.form_submit_button(
                    "Save",
                    key="recs_edit_submit",
                )

            
            if _edit_submitted:
                _w_asked = st.session_state.get("recs_edit_asked_date")
                _w_confirmed = st.session_state.get("recs_edit_confirmed")
                _w_submitted = st.session_state.get("recs_edit_submitted_date")
                _w_reminder_bool = bool(st.session_state.get("recs_edit_reminder_sent"))
                _w_reminder_date = st.session_state.get("recs_edit_reminder_sent_date")
                _w_notes = _safe_str(st.session_state.get("recs_edit_notes", ""))

                _w_asked_iso = _w_asked.isoformat() if _w_asked else None
                _w_submitted_iso = _w_submitted.isoformat() if _w_submitted else None
                _w_reminder_iso = _w_reminder_date.isoformat() if _w_reminder_date else None

                _db_asked_iso = _safe_str(_rec_row["asked_date"]) or None
                _db_submitted_iso = _safe_str(_rec_row["submitted_date"]) or None
                _db_reminder_iso = _safe_str(_rec_row["reminder_sent_date"]) or None
                _db_confirmed = _safe_confirmed  # already normalised above
                _db_reminder_int = int(_rec_row["reminder_sent"] or 0)
                _db_notes = _safe_str(_rec_row["notes"])

                _dirty: dict[str, Any] = {}
                if _w_asked_iso != _db_asked_iso:
                    _dirty["asked_date"] = _w_asked_iso
                if _w_confirmed != _db_confirmed:
                    _dirty["confirmed"] = _w_confirmed
                if _w_submitted_iso != _db_submitted_iso:
                    _dirty["submitted_date"] = _w_submitted_iso
                if int(_w_reminder_bool) != _db_reminder_int:
                    _dirty["reminder_sent"] = int(_w_reminder_bool)
                if _w_reminder_iso != _db_reminder_iso:
                    _dirty["reminder_sent_date"] = _w_reminder_iso
                if _w_notes != _db_notes:
                    _dirty["notes"] = _w_notes

                try:
                    if _dirty:
                        database.update_recommender(_rec_id, _dirty)
                        st.toast(f'Saved "{_rec_name}".')
                    else:
                        st.toast("No changes to save.")
                    st.session_state.pop("_recs_edit_form_sid", None)
                    st.session_state["_recs_skip_table_reset"] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not save: {e}")

            if st.button("Delete", type="primary", key="recs_edit_delete"):
                st.session_state["_recs_delete_target_id"] = _rec_id
                st.session_state["_recs_delete_target_name"] = _rec_name
                _confirm_delete_recommender_dialog()
            elif st.session_state.get("_recs_delete_target_id") == _rec_id:
                _confirm_delete_recommender_dialog()
    else:
        st.session_state.pop("recs_selected_id", None)
        st.session_state.pop("_recs_edit_form_sid", None)
