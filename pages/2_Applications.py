# pages/2_Applications.py
# Applications page — submission/response/interview/result tracking per position

import datetime
import math
from typing import Any, cast

import pandas as pd
import streamlit as st

import config
import database
from config import EM_DASH

st.set_page_config(
    page_title="Applications — Academic Application Tracker",
    page_icon="📋",
    layout="wide",
)


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
    Same shape as the Upcoming page's Label column."""
    inst = _safe_str(institute)
    name = _safe_str(position_name)
    if inst:
        return f"{inst}: {name}"
    return name


def _format_date_or_em(iso_str: Any) -> str:
    """Render an ISO ``YYYY-MM-DD`` string as ``'Mon D'`` (e.g.
    ``'Apr 19'``); return EM_DASH for None / NaN / empty / unparseable.

    Matches the Upcoming page's Date-column format (``MMM D``, no year).
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
    """Confirmation cell combining the boolean flag and date into a single
    readable string.

    ``st.dataframe`` does not expose a per-cell tooltip API
    (``st.column_config.Column(help=...)`` is column-header only; pandas
    Styler tooltips don't transfer through the Arrow protobuf), so the date
    is folded directly into the cell text rather than hidden in a tooltip:

      - ``received == 0``        → ``'—'``
      - ``received == 1`` + date → ``'✓ {Mon D}'`` (e.g. ``'✓ Apr 19'``)
      - ``received == 1`` + None → ``'✓ (no date)'``"""
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
    page guards the same case — a single malformed
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
    """Modal confirm dialog for irreversible interview deletion.
    Mirrors the Opportunities-page `_confirm_delete_dialog` pattern.

    The target interview is read from session_state keys
    `_apps_interview_delete_target_id` (the row's primary key) and
    `_apps_interview_delete_target_seq` (the sequence number, used in
    the warning copy so the user knows which row is about to go).
    Passing via session_state — rather than function arguments — is
    load-bearing: the outer script re-invokes this dialog on every rerun
    while the pending sentinels are set, so AppTest's script-run model
    can reach the Confirm/Cancel handlers (Streamlit's own dialog
    auto-re-render magic does not carry through AppTest).

    Outcomes:

    • Confirm → `database.delete_interview(id)` (a leaf delete; no FK
      cascade — the `interviews` table is on the child side of the
      application FK). On success: pop both pending sentinels,
      set `_applications_skip_table_reset=True` so the dataframe-event-
      reset rerun preserves the position selection,
      `st.toast(f"Deleted interview {seq}.")`, `st.rerun()` → dialog
      closes naturally on the next render (no pending sentinels).
    • Cancel → pop both pending sentinels, set
      `_applications_skip_table_reset=True` (preserves selection
      across the rerun), `st.rerun()`. No DB write.
    • Failure (delete raises) → `st.error(...)`; sentinels SURVIVE so
      the dialog re-opens on the next rerun and the user can retry.
      Mirrors the Opportunities-page failure-preserves-state precedent
      — there is no DB rollback to undo, the user just gets to try again.
    """
    iid: int | None = st.session_state.get("_apps_interview_delete_target_id")
    seq: int | None = st.session_state.get("_apps_interview_delete_target_seq")
    if iid is None:
        # Defensive: the post-loop guard already filters by
        # `pending_id in current_ids`, so this branch should be
        # unreachable in practice. Surfacing a friendly error keeps
        # behaviour graceful if a future refactor drops the guard.
        st.error("Delete target was lost — please re-open the dialog.")
        return

    st.warning(f"Interview {seq} will be permanently deleted. This **cannot be undone**.")
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
                    "_apps_interview_delete_target_id",
                    None,
                )
                st.session_state.pop(
                    "_apps_interview_delete_target_seq",
                    None,
                )
                st.toast(f"Deleted interview {seq}.")
                st.rerun()
            except Exception as e:
                # Friendly error, no re-raise. Sentinels survive so the
                # dialog re-opens on the next rerun for retry.
                st.error(f"Could not delete interview: {e}")
    with col_cancel:
        if st.button(
            "Cancel",
            key="apps_interview_delete_cancel",
            width="stretch",
        ):
            st.session_state.pop(
                "_apps_interview_delete_target_id",
                None,
            )
            st.session_state.pop(
                "_apps_interview_delete_target_seq",
                None,
            )
            st.session_state["_applications_skip_table_reset"] = True
            st.rerun()


# ── Filter bar ────────────────────────────────────────────────────────────────

selected_filter = st.selectbox(
    "Status",
    options=[config.FILTER_ALL, *config.STATUS_VALUES],
    index=0,
    format_func=lambda v: str(config.STATUS_LABELS.get(v, v)),
    key="apps_filter_status",
    help="Pick a specific status to narrow the table; 'All' shows every position.",
)


# ── Table render ──────────────────────────────────────────────────────────────


df = database.get_applications_table()

if selected_filter == config.FILTER_ALL:
    df_filtered = df
else:
    df_filtered = cast(pd.DataFrame, df[df["status"] == selected_filter])

if df_filtered.empty:
    st.info(config.EMPTY_FILTERED_APPLICATIONS)
else:
    df_filtered = df_filtered.reset_index(drop=True)
    display_df = pd.DataFrame(
        {
            "Position": df_filtered["position_name"].apply(_safe_str_or_em),
            "Institute": df_filtered["institute"].apply(_safe_str_or_em),
            "Applied": df_filtered["applied_date"].apply(_format_date_or_em),
            "Letters": df_filtered["position_id"].apply(database.is_all_recs_submitted),
            "Confirmation": df_filtered.apply(
                lambda r: _format_confirmation(
                    r["confirmation_received"],
                    r["confirmation_date"],
                ),
                axis=1,
            ),
            "Response": df_filtered["response_type"].apply(_safe_str_or_em),
            "Result": df_filtered["result"].apply(_safe_str_or_em),
        }
    ).reset_index(drop=True)

    event = st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Position": st.column_config.TextColumn(
                "Position",
                width="large",
                help="Position title",
            ),
            "Institute": st.column_config.TextColumn(
                "Institute",
                width="medium",
                help="Institution or organisation",
            ),
            "Applied": st.column_config.TextColumn(
                "Applied",
                width="small",
                help="Date application was submitted",
            ),
            "Letters": st.column_config.CheckboxColumn(
                "Letters",
                width="small",
                help="All recommendation letters submitted",
                disabled=True,
            ),
            "Confirmation": st.column_config.TextColumn(
                "Confirmation",
                width="medium",
                help="Whether a confirmation email was received",
            ),
            "Response": st.column_config.TextColumn(
                "Response",
                width="small",
                help="Type of response received (e.g. Interview Invite)",
            ),
            "Result": st.column_config.TextColumn(
                "Result",
                width="small",
                help="Final outcome of the application",
            ),
        },
        key="apps_table",
        on_select="rerun",
        selection_mode="single-row",
    )

    selected_rows = list(event.selection.rows) if event is not None else []  # type: ignore[attr-defined]
    if selected_rows and 0 <= selected_rows[0] < len(df_filtered):
        new_sid = int(df_filtered.iloc[selected_rows[0]]["position_id"])
        st.session_state["applications_selected_position_id"] = new_sid
    elif st.session_state.pop("_applications_skip_table_reset", False):
        pass
    else:
        st.session_state.pop("applications_selected_position_id", None)
        st.session_state.pop("_applications_edit_form_sid", None)


# ── Detail card ────────────────────────────────────────────────────────


if "applications_selected_position_id" in st.session_state:
    sid = st.session_state["applications_selected_position_id"]
    selected_row = df[df["position_id"] == sid]
    if not selected_row.empty:
        r = selected_row.iloc[0]
        app_row = database.get_application(sid)
        interviews_df = database.get_interviews(sid)

        with st.container(border=True):
            label = _format_label(r["institute"], r["position_name"])
            status_label = config.STATUS_LABELS.get(r["status"], r["status"])
            st.subheader(f"{label} · {status_label}")

            recs_submitted = database.is_all_recs_submitted(sid)
            _recs_label = "✓ Yes" if recs_submitted else "✗ No"
            st.markdown(f"All recommendation letters submitted: {_recs_label}")

            sid_changed = st.session_state.get("_applications_edit_form_sid") != sid

            raw_response_type = app_row.get("response_type")
            safe_response_type = (
                raw_response_type if raw_response_type in config.RESPONSE_TYPES else None
            )
            raw_result = app_row.get("result")
            safe_result = (
                raw_result if raw_result in config.RESULT_VALUES else config.RESULT_DEFAULT
            )

            canonical: dict[str, Any] = {
                "apps_applied_date": _coerce_iso_to_date(app_row.get("applied_date")),
                "apps_confirmation_received": bool(app_row.get("confirmation_received") or 0),
                "apps_confirmation_date": _coerce_iso_to_date(app_row.get("confirmation_date")),
                "apps_response_type": safe_response_type,
                "apps_response_date": _coerce_iso_to_date(app_row.get("response_date")),
                "apps_result": safe_result,
                "apps_result_notify_date": _coerce_iso_to_date(app_row.get("result_notify_date")),
                "apps_notes": _safe_str(app_row.get("notes")),
            }
            for _key, _value in canonical.items():
                if sid_changed or _key not in st.session_state:
                    st.session_state[_key] = _value
            st.session_state["_applications_edit_form_sid"] = sid

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
                    st.selectbox(
                        "Response type",
                        options=[None, *config.RESPONSE_TYPES],
                        format_func=lambda v: "— No response yet" if v is None else v,
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
                        "Result notification date",
                        value=None,
                        key="apps_result_notify_date",
                    )

                st.text_area("Notes", key="apps_notes")

                detail_submitted = st.form_submit_button("Save", key="apps_detail_submit")

            # ── Interviews list ──────────────────────────────────────

            st.markdown("#### Interviews")

            current_ids = (
                frozenset(int(i) for i in interviews_df["id"])
                if not interviews_df.empty
                else frozenset()
            )
            saved_sentinel = st.session_state.get(
                "_apps_interviews_seeded_ids",
                frozenset(),
            )
            seeded_ids = saved_sentinel & current_ids
            for _, _iv_row in interviews_df.iterrows():
                _iid_raw: Any = _iv_row["id"]
                _iid = int(_iid_raw)
                if _iid in seeded_ids:
                    continue
                _fmt_str = _safe_str(_iv_row["format"])
                _fmt = _fmt_str if _fmt_str in config.INTERVIEW_FORMATS else None
                st.session_state[f"apps_interview_{_iid}_date"] = _coerce_iso_to_date(
                    _iv_row["scheduled_date"]
                )
                st.session_state[f"apps_interview_{_iid}_format"] = _fmt
                st.session_state[f"apps_interview_{_iid}_notes"] = _safe_str(_iv_row["notes"])
            st.session_state["_apps_interviews_seeded_ids"] = seeded_ids | current_ids

            # ── Per-row blocks  ────────────────────────────

            saves_clicked: list[tuple[int, int]] = []
            for _i, (_, _iv_row) in enumerate(interviews_df.iterrows()):
                # pandas-stubs widens iterrows() cell types to Series;
                # funnel through Any so int() only sees the runtime scalar.
                _iid_raw: Any = _iv_row["id"]
                _seq_raw: Any = _iv_row["sequence"]
                _iid = int(_iid_raw)
                _seq = int(_seq_raw)

                if _i > 0:
                    st.divider()

                with st.form(f"apps_interview_{_iid}_form", border=False):
                    st.markdown(f"**Interview {_seq}**")
                    _cols = st.columns([2, 2, 4])
                    with _cols[0]:
                        st.date_input(
                            "Interview date",
                            value=None,
                            key=f"apps_interview_{_iid}_date",
                        )
                    with _cols[1]:
                        st.selectbox(
                            "Format",
                            options=[None, *config.INTERVIEW_FORMATS],
                            format_func=lambda v: "— No format set" if v is None else v,
                            key=f"apps_interview_{_iid}_format",
                        )
                    with _cols[2]:
                        st.text_input(
                            "Notes",
                            key=f"apps_interview_{_iid}_notes",
                        )
                    if st.form_submit_button(
                        "Save",
                        key=f"apps_interview_{_iid}_save",
                    ):
                        saves_clicked.append((_iid, _seq))

                if st.button(
                    f"🗑️ Delete Interview {_seq}",
                    key=f"apps_interview_{_iid}_delete",
                ):
                    st.session_state["_apps_interview_delete_target_id"] = _iid
                    st.session_state["_apps_interview_delete_target_seq"] = _seq

            _pending_delete_id = st.session_state.get("_apps_interview_delete_target_id")
            if _pending_delete_id is not None:
                if _pending_delete_id in current_ids:
                    _confirm_interview_delete_dialog()
                else:
                    # Stale target — silent cleanup, no error / toast.
                    st.session_state.pop(
                        "_apps_interview_delete_target_id",
                        None,
                    )
                    st.session_state.pop(
                        "_apps_interview_delete_target_seq",
                        None,
                    )

            # ── Add button  ─────
            _add_label = "Add interview" if interviews_df.empty else "Add another interview"
            add_clicked = st.button(_add_label, key="apps_add_interview")

        if detail_submitted:
            applied_d = st.session_state["apps_applied_date"]
            conf_d = st.session_state["apps_confirmation_date"]
            resp_d = st.session_state["apps_response_date"]
            result_n_d = st.session_state["apps_result_notify_date"]
            _w_applied_iso = applied_d.isoformat() if applied_d else None
            _w_conf_received = int(st.session_state["apps_confirmation_received"])
            _w_conf_iso = conf_d.isoformat() if conf_d else None
            _w_response_type = st.session_state["apps_response_type"]
            _w_response_iso = resp_d.isoformat() if resp_d else None
            _w_result = st.session_state["apps_result"]
            _w_result_notify_iso = result_n_d.isoformat() if result_n_d else None
            _w_notes = st.session_state["apps_notes"]

            _db_applied_iso = _safe_str(app_row.get("applied_date")) or None
            _db_conf_received = int(app_row.get("confirmation_received") or 0)
            _db_conf_iso = _safe_str(app_row.get("confirmation_date")) or None
            _db_response_type_raw = app_row.get("response_type")
            _db_response_type = (
                _db_response_type_raw if _db_response_type_raw in config.RESPONSE_TYPES else None
            )
            _db_response_iso = _safe_str(app_row.get("response_date")) or None
            _db_result_raw = app_row.get("result")
            _db_result = (
                _db_result_raw if _db_result_raw in config.RESULT_VALUES else config.RESULT_DEFAULT
            )
            _db_result_notify_iso = _safe_str(app_row.get("result_notify_date")) or None
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
                    st.session_state["_applications_skip_table_reset"] = True
                    st.session_state.pop(
                        "_applications_edit_form_sid",
                        None,
                    )
                    st.toast("No changes to save.")
                    st.rerun()
                result = database.upsert_application(
                    sid,
                    fields,
                    propagate_status=True,
                )
                st.session_state["_applications_skip_table_reset"] = True
                st.session_state.pop("_applications_edit_form_sid", None)
                st.toast(f'Saved "{r["position_name"]}".')
                if result["status_changed"]:
                    promo_label = config.STATUS_LABELS.get(
                        result["new_status"], result["new_status"]
                    )
                    st.toast(f"Promoted to {promo_label}.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not save: {e}")

        # ── per-row interviews Save handler ────────────────
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
                        f"apps_interview_{_iid}_notes",
                        "",
                    )
                )
                _w_date_iso = _w_date.isoformat() if _w_date else None
                _w_notes = _w_notes_str if _w_notes_str else None

                _db_date_str = _safe_str(_db_row["scheduled_date"])
                _db_date_iso = _db_date_str if _db_date_str else None
                _db_fmt_str = _safe_str(_db_row["format"])
                _db_format = _db_fmt_str if _db_fmt_str in config.INTERVIEW_FORMATS else None
                _db_notes_str = _safe_str(_db_row["notes"])
                _db_notes = _db_notes_str if _db_notes_str else None

                _dirty: dict[str, Any] = {}
                if _w_date_iso != _db_date_iso:
                    _dirty["scheduled_date"] = _w_date_iso
                if _w_format != _db_format:
                    _dirty["format"] = _w_format
                if _w_notes != _db_notes:
                    _dirty["notes"] = _w_notes

                st.session_state["_applications_skip_table_reset"] = True
                if _dirty:
                    database.update_interview(_iid, _dirty)
                    st.toast(f"Saved interview {_seq}.")
                else:
                    st.toast("No changes to save.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not save interview {_seq}: {e}")

        # ── interviews Add handler ─────────────────────────────
        if add_clicked:
            try:
                _add_result = database.add_interview(
                    sid,
                    {},
                    propagate_status=True,
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
