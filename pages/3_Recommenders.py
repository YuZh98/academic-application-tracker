# pages/3_Recommenders.py
# Streamlit page — Recommenders tracker.
#
# Phase 5 T4: page shell + Pending Alerts panel (DESIGN §8.4).
#   - set_page_config, st.title, database.init_db()
#   - get_pending_recommenders() grouped by recommender_name;
#     one st.container(border=True) per person.
# Phase 5 T5: All Recommenders table + filters + add form + inline edit.
#   - T5-A: read-only dataframe driven by database.get_all_recommenders;
#           position + recommender filters; row selection captures
#           recs_selected_id.
#   - T5-B: st.form("recs_add_form") with position / name / relationship /
#           asked-date widgets; database.add_recommender on submit.
#   - T5-C: inline edit card under the table — st.form("recs_edit_form")
#           with asked_date / confirmed / submitted_date / reminder_sent +
#           reminder_sent_date / notes; Save writes only the dirty diff
#           via database.update_recommender. Delete button outside the
#           form opens an @st.dialog confirm gate; Confirm cascades via
#           database.delete_recommender. Mirrors the Opportunities-page
#           dialog re-open trick (gotcha #3) so AppTest's script-run
#           model can reach the dialog body.
# Phase 5 T6: Reminder helpers wired into each Pending Alerts card.
#   - T6-A: st.link_button("Compose reminder email", url=mailto:?…) per card,
#           subject + body locked verbatim per DESIGN §8.4 with N (subject)
#           and recommender_name (body) interpolated. URL-quoted via
#           urllib.parse.quote so the OS hands the formatted draft to the
#           user's default mail client. No `to:` field — the recommenders
#           schema doesn't store emails today.
#   - T6-B: st.expander(f"LLM prompts ({len(TONES)} tones)", …) beneath the
#           Compose button, holding one st.code(prompt, language="text")
#           per tone (gentle / urgent). Each prompt embeds recommender
#           name + relationship + every owed position (name / institute /
#           deadline) + days-since-asked + tone + an instruction asking
#           the LLM to return both subject and body.

import math
from datetime import date
from typing import Any, cast
from urllib.parse import quote

import pandas as pd
import streamlit as st

import config
import database

# DESIGN §8.0 + D14: every page's FIRST Streamlit call is set_page_config
# with wide layout. Must precede any other st.* call.
st.set_page_config(
    page_title="Postdoc Tracker",
    page_icon="📋",
    layout="wide",
)

database.init_db()

st.title("Recommenders")


# ── Helpers ───────────────────────────────────────────────────────────────────


EM_DASH = "—"


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


# ── T6: Reminder helpers ──────────────────────────────────────────────────────
#
# DESIGN §8.4 + AGENTS §T6 pin two affordances per Pending-Alerts card:
#   - A `Compose reminder email` link button opening a `mailto:` URL with
#     the locked subject + body copy below.
#   - An `LLM prompts ({len(_REMINDER_TONES)} tones)` expander holding one
#     `st.code(prompt, language="text")` per tone.
# The tone vocabulary is locked at (gentle, urgent) per DESIGN §8.4; the
# expander label computes its count from `len(_REMINDER_TONES)` so a
# future tone addition flows through to the UI without a separate edit.

_REMINDER_TONES: tuple[str, ...] = ("gentle", "urgent")


def _build_compose_mailto(*, recommender_name: str, n_positions: int) -> str:
    """Build the verbatim DESIGN §8.4 mailto URL for the Compose button
    (T6-A). The subject interpolates the position count; the body
    interpolates the recommender's name. No `to:` field — the
    recommenders schema doesn't store emails today, so the OS-level
    mail client prompts the user for the recipient."""
    subject = f"Following up: letters for {n_positions} postdoc applications"
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
    rel_str = (
        f" ({relationship})"
        if relationship and not pd.isna(relationship)
        else ""
    )

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


# ── Pending Alerts ────────────────────────────────────────────────────────────
#
# Driven by database.get_pending_recommenders() (default RECOMMENDER_ALERT_DAYS).
# One st.container(border=True) per distinct recommender_name; each card lists
# every position that recommender still owes a letter for and (T6) carries the
# Compose reminder email link button + LLM prompts expander.
#
# Locked card format (DESIGN §8.4):
#   **⚠ {name}** ({relationship})          ← relationship omitted when NULL
#   - {institute}: {position_name} (asked {N}d ago, due {Mon D})
#   - ...
#   [Compose reminder email]               ← T6-A mailto link button
#   ▸ LLM prompts (N tones)                 ← T6-B expander, N = len(_REMINDER_TONES)

st.subheader("Pending Alerts")
_pending_recs = database.get_pending_recommenders()

if _pending_recs.empty:
    st.info("No pending recommenders.")
else:
    _today = date.today()

    # Stable iteration order: get_pending_recommenders() already sorts by
    # recommender_name ASC, deadline_date ASC NULLS LAST, so a plain groupby
    # preserves both within-group deadline order and across-group alphabetical
    # order without any extra sort. enumerate() supplies a per-card index for
    # the T6 link-button key so two cards never collide on a duplicate widget id.
    for _idx, (_name, _group) in enumerate(
        _pending_recs.groupby("recommender_name", sort=False)
    ):
        with st.container(border=True):
            # Relationship: first row's value (same recommender → same person).
            # Guard against NaN surfaced by pandas for NULL TEXT columns.
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

            _body = f"**⚠ {_name}**{_rel_str}\n" + "\n".join(_bullets)
            st.markdown(_body)

            # ── T6-A: Compose reminder email ────────────────────────────
            # Locked-copy mailto URL per DESIGN §8.4. N (subject) is the
            # owed-position count for THIS card; recommender_name (body)
            # is interpolated. Per-card unique key avoids a Streamlit
            # DuplicateWidgetID across multiple cards.
            _mailto_url = _build_compose_mailto(
                recommender_name=str(_name),
                n_positions=len(_group),
            )
            st.link_button(
                "Compose reminder email",
                url=_mailto_url,
                key=f"recs_compose_{_idx}",
            )

            # ── T6-B: LLM prompts expander ──────────────────────────────
            # One st.code(prompt, language="text") per locked tone. The
            # expander label computes its tone count from
            # _REMINDER_TONES so a future tone addition flows through to
            # the UI label automatically. days-since-asked is the MAX
            # across the card's positions (the longest wait) — the
            # prompt is one block per tone, not per position, so a
            # single integer summary keeps the prompt text clean.
            _max_days = max(_per_row_days) if _per_row_days else 0
            _rel_for_prompt: str | None = (
                None if (_rel is None or pd.isna(_rel)) else str(_rel)
            )
            with st.expander(
                f"LLM prompts ({len(_REMINDER_TONES)} tones)",
                expanded=False,
            ):
                for _tone in _REMINDER_TONES:
                    _prompt = _build_llm_prompt(
                        tone=_tone,
                        recommender_name=str(_name),
                        relationship=_rel_for_prompt,
                        group=_group,
                        days_ago=_max_days,
                    )
                    st.code(_prompt, language="text")


# ── T5: All Recommenders ─────────────────────────────────────────────────────
#
# Layout-stability anchor — the subheader stays visible on an empty DB so the
# "Recommenders" page always reads as a section even before the user adds any
# rows. Same precedent as the dashboard T5 KPI block + Pending Alerts panel
# above.

st.subheader("All Recommenders")


# ── Build label↔id mapping for the position selectboxes ─────────────────────
#
# AGENTS §T5-B: position dropdowns display "{institute}: {position_name}"
# (or bare position_name) but the underlying value the page persists is
# the position_id. Streamlit's AppTest exposes selectbox options as the
# raw values passed in (no format_func application), so the cleanest
# encoding is: use the LABEL as the option value, and look up the id at
# submit time via this dict. The reverse lookup (label → id) keeps the
# id off the rendered UI per DESIGN §8.4 ("IDs never surface to user").

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


# ── T5-B: Add recommender form ───────────────────────────────────────────────
#
# Inside an expander to keep the page's primary surface (the table) above
# the fold. Mirror of the Opportunities-page Quick Add expander; the
# expander is closed by default — the user opens it when they want to
# add a new recommender.

with st.expander("Add Recommender", expanded=False):
    with st.form("recs_add_form"):
        _add_col1, _add_col2 = st.columns(2)
        with _add_col1:
            # Position selectbox: options are LABELS; the page maps back
            # to the position_id via _position_label_to_id at submit time.
            # Empty options list when the user has no positions yet —
            # st.selectbox tolerates an empty list; the submit handler
            # rejects the no-position case before reaching add_recommender.
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
        _add_submitted = st.form_submit_button(
            "+ Add Recommender", key="recs_add_submit"
        )

# T5-B submit handler — outside the form so st.error / st.toast render in
# the page body (the quick-add precedent on the Opportunities page).
if _add_submitted:
    _name_raw = (st.session_state.get("recs_add_name") or "").strip()
    _pos_label = st.session_state.get("recs_add_position")
    _rel_pick = st.session_state.get("recs_add_relationship")
    _asked = st.session_state.get("recs_add_asked_date")

    if not _name_raw:
        # Mirror Opportunities §8.2 quick-add F3: whitespace-only is
        # treated as empty. No DB write, no toast.
        st.error("Recommender Name is required.")
    elif _pos_label not in _position_label_to_id:
        # Defensive: empty positions table or stale label. Surface a
        # friendly error rather than letting the lookup raise KeyError.
        st.error("Pick a position before adding a recommender.")
    else:
        _pos_id = _position_label_to_id[_pos_label]
        _fields: dict[str, Any] = {
            "recommender_name": _name_raw,
            "relationship": _rel_pick,
            "asked_date": _asked.isoformat() if _asked else None,
        }
        # GUIDELINES §8: friendly error on failure, no re-raise — the
        # caller never sees the traceback the handler exists to hide.
        try:
            database.add_recommender(_pos_id, _fields)
            st.toast(f"Added {_name_raw}.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not add recommender: {e}")


# ── T5-A: Filter bar ─────────────────────────────────────────────────────────
#
# Two selectboxes — by position and by recommender name. Both default to
# the "All" sentinel (no filter applied). The recommender filter dedupes
# by name so the dropdown carries each person at most once even when they
# owe letters for several positions.

_FILTER_ALL = "All"

_recs_df = database.get_all_recommenders()

# Position filter options: derive from the positions table so a position
# without recommenders still appears (matches the add-form selectbox's
# coverage). Sentinel first.
_position_filter_options = [_FILTER_ALL] + list(_position_label_to_id.keys())

# Recommender filter options: distinct recommender_names ordered by the
# upstream `r.recommender_name ASC` from get_all_recommenders. Drop NULLs
# (rare — a recommender without a name is degenerate but possible while
# the user is still filling things in).
if _recs_df.empty:
    _recommender_filter_options = [_FILTER_ALL]
else:
    _seen: list[str] = []
    for _n in _recs_df["recommender_name"]:
        _ns = _safe_str(_n)
        if _ns and _ns not in _seen:
            _seen.append(_ns)
    _recommender_filter_options = [_FILTER_ALL] + _seen

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


# ── T5-A: Table render ──────────────────────────────────────────────────────
#
# Apply filters, then project the joined recommenders × positions frame
# into the six-column display contract pinned by tests:
#   Position · Recommender · Relationship · Asked · Confirmed · Submitted
# `recs_table` is the dataframe key — selectable via on_select='rerun'
# / selection_mode='single-row'. The selection-resolution block below
# captures `recs_selected_id` for the inline edit card.

# CL1 type-clean: boolean indexing widens df to Series | DataFrame
# per pandas-stubs, so cast each filter step's RHS back to
# `pd.DataFrame` so downstream `.reset_index` / `.apply` / `.iloc` /
# `.empty` access stays typed.
_filtered_df: pd.DataFrame = _recs_df.copy()
if _pos_filter != _FILTER_ALL:
    _target_pos_id = _position_label_to_id.get(_pos_filter)
    if _target_pos_id is not None:
        _filtered_df = cast(
            pd.DataFrame,
            _filtered_df[_filtered_df["position_id"] == _target_pos_id],
        )
if _rec_filter != _FILTER_ALL:
    _filtered_df = cast(
        pd.DataFrame,
        _filtered_df[_filtered_df["recommender_name"] == _rec_filter],
    )

_filtered_df = _filtered_df.reset_index(drop=True)

if _filtered_df.empty:
    # Render a six-column empty frame so the column contract pinned by
    # `test_table_renders_with_six_display_columns` holds even on an
    # empty DB / heavily-filtered view.
    _display_df = pd.DataFrame(
        columns=[
            "Position", "Recommender", "Relationship",
            "Asked", "Confirmed", "Submitted",
        ]
    )
else:
    _display_df = pd.DataFrame({
        "Position": _filtered_df.apply(
            lambda r: _format_label(
                _safe_str(r["institute"]),
                _safe_str(r["position_name"]),
            ),
            axis=1,
        ),
        "Recommender":  _filtered_df["recommender_name"].apply(_safe_str_or_em),
        "Relationship": _filtered_df["relationship"].apply(_safe_str_or_em),
        "Asked":        _filtered_df["asked_date"].apply(_safe_str_or_em),
        "Confirmed":    _filtered_df["confirmed"].apply(_format_confirmed),
        "Submitted":    _filtered_df["submitted_date"].apply(_safe_str_or_em),
    })

_event = st.dataframe(
    _display_df,
    width="stretch",
    hide_index=True,
    column_config={
        "Position":     st.column_config.TextColumn("Position",     width="large"),
        "Recommender":  st.column_config.TextColumn("Recommender",  width="medium"),
        "Relationship": st.column_config.TextColumn("Relationship", width="medium"),
        "Asked":        st.column_config.TextColumn("Asked",        width="small"),
        "Confirmed":    st.column_config.TextColumn("Confirmed",    width="small"),
        "Submitted":    st.column_config.TextColumn("Submitted",    width="small"),
    },
    key="recs_table",
    on_select="rerun",
    selection_mode="single-row",
)


# ── T5-C: Selection resolution ─────────────────────────────────────────────
#
# Map the selected positional row back to its recommender id. Mirror of
# the Opportunities / Applications selection-resolution structure, with
# the same `_recs_skip_table_reset` one-shot for post-Save / post-Confirm
# reruns where AppTest's dataframe event resets across the rerun
# (gotcha #11). Switching rows clears any stale `_recs_delete_target_*`
# pair so a previously-opened-but-X-dismissed dialog can't re-fire as a
# phantom on a sibling row (Opportunities review fix #2 precedent).

# CL1 type-clean: streamlit-stubs declares DataframeState as
# TypedDict so attribute access trips pyright; runtime exposes a
# wrapper supporting both subscript and attribute. Mirror the form
# used on pages/1_Opportunities.py + pages/2_Applications.py.
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
    # One-shot consumed: the Save / Cancel handlers set this flag before
    # st.rerun() so selection survives the rerun. The dialog-pending
    # branch keeps the selection so the dialog stays reachable.
    pass
else:
    # Empty selection on a real (non-empty) table → user clicked away.
    st.session_state.pop("recs_selected_id", None)
    st.session_state.pop("_recs_edit_form_sid", None)


# ── T5-C: Delete confirm dialog (defined before use so the click handler
# can call it directly — same shape as the Opportunities-page
# `_confirm_delete_dialog`).
@st.dialog("Delete this recommender?")
def _confirm_delete_recommender_dialog() -> None:
    """Modal confirm dialog for irreversible recommender deletion. The
    target id + display name come from session_state sentinels set by
    the edit card's Delete-button click; passing via session_state lets
    the outer page re-invoke the dialog on every rerun while the pending
    flag is set, which is what keeps Confirm/Cancel reachable through
    AppTest's script-run model (gotcha #3)."""
    rec_id_target: int | None = st.session_state.get("_recs_delete_target_id")
    rec_name_target: str = st.session_state.get(
        "_recs_delete_target_name", ""
    )
    st.warning(
        f'Delete **"{rec_name_target}"**? This **cannot be undone**.'
    )
    _col_confirm, _col_cancel = st.columns(2)
    with _col_confirm:
        if st.button(
            "Confirm Delete",
            type="primary",
            key="recs_delete_confirm",
            width="stretch",
        ):
            if rec_id_target is None:
                st.error(
                    "Delete target was lost — please re-open the dialog."
                )
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


# ── T5-C: Inline edit card ──────────────────────────────────────────────────
#
# Renders only when a recommender row is selected. Wrapped in
# `st.container(border=True)` per DESIGN §8.0 visual-grouping convention.
# Pre-seed widgets via the `_recs_edit_form_sid` sentinel (same widget-
# value-trap pattern as Opportunities / Applications).

if "recs_selected_id" in st.session_state:
    _rec_id = int(st.session_state["recs_selected_id"])
    # Look up the selected row in the UNFILTERED frame so a filter
    # narrowing that excludes the row doesn't dismiss an in-progress
    # edit (Opportunities/Applications precedent).
    _selected_match = _recs_df[_recs_df["id"] == _rec_id]
    if not _selected_match.empty:
        _rec_row = _selected_match.iloc[0]
        _rec_name = _safe_str(_rec_row["recommender_name"])

        with st.container(border=True):
            st.markdown(f"**Editing: {_rec_name or EM_DASH}**")

            # ── Pre-seed widget state ───────────────────────────────────
            #
            # Two-phase apply (gotcha #2 — once session_state[key] is
            # set, Streamlit ignores `value=`, so pre-seed must happen
            # via direct session_state assignment):
            #   (a) Row CHANGE → force-overwrite every key.
            #   (b) Same row, key missing → restore from canonical.
            #   (c) Same row, key present → leave it alone (preserves
            #       in-flight form draft / AppTest set_value semantics).
            _sid_changed = (
                st.session_state.get("_recs_edit_form_sid") != _rec_id
            )

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
                "recs_edit_asked_date":         _coerce_iso_to_date(_rec_row["asked_date"]),
                "recs_edit_confirmed":          _safe_confirmed,
                "recs_edit_submitted_date":     _coerce_iso_to_date(_rec_row["submitted_date"]),
                "recs_edit_reminder_sent":      bool(_rec_row.get("reminder_sent") or 0),
                "recs_edit_reminder_sent_date": _coerce_iso_to_date(
                    _rec_row["reminder_sent_date"]
                ),
                "recs_edit_notes":              _safe_str(_rec_row["notes"]),
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
                            EM_DASH if v is None
                            else ("Yes" if v == 1 else "No")
                        ),
                        key="recs_edit_confirmed",
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
                        "Reminder sent date",
                        value=None,
                        key="recs_edit_reminder_sent_date",
                    )
                st.text_area(
                    "Notes",
                    key="recs_edit_notes",
                )
                _edit_submitted = st.form_submit_button(
                    "Save Changes",
                    key="recs_edit_submit",
                )

            # ── Save handler — outside the form so st.error/toast render
            # in the page body, not nested inside the form.
            if _edit_submitted:
                # Build the dirty diff against the persisted DB row so
                # Save writes ONLY changed fields. Untouched widgets
                # don't appear in the payload — load-bearing for the
                # AGENTS §T5-C "dirty_fields_only" contract and pinned
                # by `test_save_writes_only_dirty_fields`.
                _w_asked = st.session_state.get("recs_edit_asked_date")
                _w_confirmed = st.session_state.get("recs_edit_confirmed")
                _w_submitted = st.session_state.get("recs_edit_submitted_date")
                _w_reminder_bool = bool(
                    st.session_state.get("recs_edit_reminder_sent")
                )
                _w_reminder_date = st.session_state.get(
                    "recs_edit_reminder_sent_date"
                )
                _w_notes = _safe_str(
                    st.session_state.get("recs_edit_notes", "")
                )

                _w_asked_iso     = _w_asked.isoformat()     if _w_asked     else None
                _w_submitted_iso = _w_submitted.isoformat() if _w_submitted else None
                _w_reminder_iso  = _w_reminder_date.isoformat() if _w_reminder_date else None

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
                    # Pop the sentinel so the post-Save rerun re-seeds
                    # widgets from the just-persisted DB values; the
                    # skip flag preserves selection across the dataframe-
                    # event-reset rerun (gotcha #11).
                    st.session_state.pop("_recs_edit_form_sid", None)
                    st.session_state["_recs_skip_table_reset"] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not save: {e}")

            # ── Delete button — OUTSIDE the form (Streamlit 1.56 forbids
            # st.button inside st.form). Click stashes target sentinels
            # and opens the dialog; the elif re-opens it on subsequent
            # reruns while the sentinels remain set, which is what makes
            # Confirm/Cancel reachable through AppTest's script-run model.
            if st.button("Delete", type="primary", key="recs_edit_delete"):
                st.session_state["_recs_delete_target_id"] = _rec_id
                st.session_state["_recs_delete_target_name"] = _rec_name
                _confirm_delete_recommender_dialog()
            elif st.session_state.get("_recs_delete_target_id") == _rec_id:
                _confirm_delete_recommender_dialog()
    else:
        # The selected row vanished from the unfiltered df (deleted
        # elsewhere, DB wiped). Pop both sentinels so later reruns don't
        # keep referencing a missing row.
        st.session_state.pop("recs_selected_id", None)
        st.session_state.pop("_recs_edit_form_sid", None)
