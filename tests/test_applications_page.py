# tests/test_applications_page.py
# Integration tests for pages/2_Applications.py using Streamlit AppTest.
#
# Mirrors tests/test_opportunities_page.py for the Phase 5 T1+ page. The
# shared `db` fixture (conftest.py) monkeypatches database.DB_PATH so
# AppTest writes/reads land in a temp DB, isolated per test.
#
# AppTest runs the page script in-process. The set_page_config call is
# consumed by Streamlit before widgets render, so it does not surface
# in the AppTest element tree — that contract is pinned via source-grep
# (TestPageConfigSetsWideLayout) per the precedent set by
# test_opportunities_page.py and test_app_page.py.

import datetime
import pathlib
import pytest

import database
import config
from streamlit.testing.v1 import AppTest


PAGE = "pages/2_Applications.py"

# Widget-key prefix per GUIDELINES §13 + DESIGN §8.0 — the Applications
# page uses `apps_` so keys cannot collide with the Opportunities page's
# `qa_` / `edit_` / `filter_` namespaces.
FILTER_STATUS_KEY = "apps_filter_status"
TABLE_KEY = "apps_table"

# T2-A: detail card form + submit button keys, and the eight in-form
# widget keys for the editable application fields. Names follow the
# `apps_` widget-key prefix; the form id ends in `_form` (DESIGN §8.0,
# dev-notes gotcha #4 — form id ≠ any widget key inside).
DETAIL_FORM_ID = "apps_detail_form"
DETAIL_SUBMIT_KEY = "apps_detail_submit"

W_APPLIED_DATE        = "apps_applied_date"
W_CONFIRMATION_RCVD   = "apps_confirmation_received"
W_CONFIRMATION_DATE   = "apps_confirmation_date"
W_RESPONSE_TYPE       = "apps_response_type"
W_RESPONSE_DATE       = "apps_response_date"
W_RESULT              = "apps_result"
W_RESULT_NOTIFY_DATE  = "apps_result_notify_date"
W_NOTES               = "apps_notes"

# T2-A: page-prefixed internal sentinels so cross-page session_state on
# Opportunities (`_edit_form_sid`, `_skip_table_reset`) doesn't collide
# with Applications-page state. Leading underscore = internal sentinel
# (GUIDELINES §3); the long-form `applications` prefix avoids confusion
# with the dashboard page (`app.py`).
SELECTED_PID_KEY      = "applications_selected_position_id"
EDIT_FORM_SID_KEY     = "_applications_edit_form_sid"
SKIP_TABLE_RESET_KEY  = "_applications_skip_table_reset"


def _run_page() -> AppTest:
    """Return a freshly-run AppTest for the Applications page."""
    at = AppTest.from_file(PAGE, default_timeout=10)
    at.run()
    return at


def _select_row(at: AppTest, row_index: int) -> None:
    """Inject single-row dataframe selection + rerun.

    AppTest's Dataframe element exposes no click-a-row API, so the test
    writes the protobuf-shaped selection state directly. Mirror of the
    helper in tests/test_opportunities_page.py — the shape matches what
    Streamlit 1.56 produces for ``on_select='rerun'`` +
    ``selection_mode='single-row'``."""
    at.session_state[TABLE_KEY] = {
        "selection": {"rows": [row_index], "columns": []}
    }
    at.run()


def _deselect_row(at: AppTest) -> None:
    """Inject empty-selection state + rerun (the user clicked away)."""
    at.session_state[TABLE_KEY] = {
        "selection": {"rows": [], "columns": []}
    }
    at.run()


def _keep_selection(at: AppTest, row_index: int) -> None:
    """Re-inject selection state WITHOUT rerunning.

    AppTest does not persist the dataframe event across reruns (see
    Opportunities-page test helper of the same name + dev-notes gotcha
    #11). Multi-step flows that span an internal rerun (e.g., a Save
    handler that calls ``st.rerun()``) need this to mimic the
    browser-side selection persistence."""
    at.session_state[TABLE_KEY] = {
        "selection": {"rows": [row_index], "columns": []}
    }


def _ss_or_none(at: AppTest, key: str):
    """Read session_state[key] safely, returning None if absent.

    AppTest's session_state wrapper does NOT support ``.get()`` —
    calling it raises ``AttributeError`` (dev-notes gotcha #6). All
    "read-or-default" lookups must go through ``in`` + subscript;
    this helper hides that asymmetry so test bodies stay tidy."""
    return at.session_state[key] if key in at.session_state else None


# ── Page config (source-grep pin) ─────────────────────────────────────────────

class TestPageConfigSetsWideLayout:
    """Source-grep pin for DESIGN §8.0 + D14. AppTest does not surface
    set_page_config in the element tree (the call is consumed by the
    page-setup phase before widgets render), so the contract is pinned
    at the source level — same precedent as
    test_opportunities_page.py::TestPageConfigSetsWideLayout."""

    def test_page_config_sets_wide_layout(self, db):
        """DESIGN §8.0 requires `st.set_page_config(layout="wide", ...)`
        on every page. Checking the four keyword bindings together
        prevents a partially-correct call (layout only, title only, …)
        from silently passing."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert "st.set_page_config(" in src, (
            f"{PAGE} must call st.set_page_config(...) per DESIGN §8.0."
        )
        assert 'page_title="Postdoc Tracker"' in src, (
            'set_page_config must bind page_title="Postdoc Tracker" '
            'per DESIGN §8.0.'
        )
        assert 'page_icon="📋"' in src, (
            'set_page_config must bind page_icon="📋" per DESIGN §8.0.'
        )
        assert 'layout="wide"' in src, (
            'set_page_config must bind layout="wide" per DESIGN §8.0 / D14.'
        )


# ── Page shell ────────────────────────────────────────────────────────────────

class TestApplicationsPageShell:
    """T1-B: page renders without exception and surfaces the canonical
    'Applications' title per DESIGN §8.3."""

    PAGE_TITLE = "Applications"

    def test_page_runs_without_exception(self, db):
        """Sanity: the page renders without raising. Foundational —
        every other test in this module assumes this passes."""
        at = _run_page()
        assert not at.exception, (
            f"Page must render without exception; got {at.exception}"
        )

    def test_title_is_applications(self, db):
        """st.title('Applications') — per DESIGN §8.3 page heading
        contract."""
        at = _run_page()
        titles = [t.value for t in at.title]
        assert self.PAGE_TITLE in titles, (
            f"Expected '{self.PAGE_TITLE}' in {titles!r}"
        )


# ── Filter bar (T1-B) ─────────────────────────────────────────────────────────

class TestApplicationsFilterBar:
    """DESIGN §8.3: status filter selectbox with a default that
    excludes STATUS_SAVED + STATUS_CLOSED. The 'Active' sentinel from
    config.STATUS_FILTER_ACTIVE encodes that exclusion as a single
    selectbox option, so the user can flip to 'All' or a specific
    status without losing the canonical default and without the page
    needing a separate 'show inactive' toggle widget."""

    def test_status_filter_selectbox_renders(self, db):
        """Bare-existence pin: the selectbox is on the page with the
        documented `apps_filter_status` key."""
        at = _run_page()
        at.selectbox(key=FILTER_STATUS_KEY)  # raises KeyError if absent

    def test_status_filter_default_is_active(self, db):
        """Default selection = config.STATUS_FILTER_ACTIVE per
        DESIGN §8.3. AppTest's .value returns the underlying option
        value (round-trip through format_func per gotcha #15), not
        the formatted display string — so this comparison is against
        the raw sentinel, not 'Active' as a hardcoded literal."""
        at = _run_page()
        sb = at.selectbox(key=FILTER_STATUS_KEY)
        assert sb.value == config.STATUS_FILTER_ACTIVE, (
            f"Default filter must be {config.STATUS_FILTER_ACTIVE!r}; "
            f"got {sb.value!r}"
        )

    def test_status_filter_options_match_spec(self, db):
        """Filter options in display order:
          1. config.STATUS_FILTER_ACTIVE  (sentinel; the default)
          2. 'All'                         (sentinel; show every status)
          3. config.STATUS_LABELS[v] for each v in config.STATUS_VALUES

        AppTest's .options exposes the post-format_func display strings
        per gotcha #15 — the sentinels render as themselves because
        format_func is the standard `STATUS_LABELS.get(v, v)` pattern,
        which falls back to identity for keys it does not recognise."""
        at = _run_page()
        actual = list(at.selectbox(key=FILTER_STATUS_KEY).options)
        expected = [
            config.STATUS_FILTER_ACTIVE,
            "All",
            *[config.STATUS_LABELS[v] for v in config.STATUS_VALUES],
        ]
        assert actual == expected, (
            f"Status filter option mismatch.\n"
            f"  Expected: {expected}\n"
            f"  Got:      {actual}"
        )


# ── Table render (T1-C) ───────────────────────────────────────────────────────

# Local copy of the conftest helper (imported lazily to keep the page-test
# module self-contained; same shape as test_opportunities_page.py).
from tests.conftest import make_position


class TestApplicationsPageTable:
    """T1-C: read-only Applications table per DESIGN §8.3 + wireframe.

    Columns (display order, six total):
      Position / Applied / Recs / Confirmation / Response / Result

    Filter behaviour:
      - Default = config.STATUS_FILTER_ACTIVE → hides
        config.STATUS_FILTER_ACTIVE_EXCLUDED ({SAVED, CLOSED}).
      - "All" sentinel → show every row.
      - Specific STATUS_VALUES entry → narrow to exactly that status.

    Confirmation column inline format (DESIGN §8.3 D-A amendment —
    `st.dataframe` has no per-cell tooltip API in Streamlit 1.56;
    full resolution recorded in reviews/phase-5-tier1-review.md):
      - confirmation_received = 0 → "—"
      - confirmation_received = 1, confirmation_date set → "✓ {Mon D}"
      - confirmation_received = 1, confirmation_date NULL → "✓ (no date)"

    Sort: deadline_date ASC NULLS LAST (matches the
    get_applications_table contract pinned in T1-A)."""

    TABLE_KEY = "apps_table"
    EM_DASH = "—"

    DISPLAY_COLUMNS = [
        "Position", "Applied", "Recs", "Confirmation", "Response", "Result",
    ]

    EMPTY_COPY = "No applications match the current filter."

    def test_table_renders_with_six_display_columns(self, db):
        """The page must surface the six wireframe columns in this exact
        order — column rename in T2's detail card or T3's interview list
        should not silently shift the table's projection."""
        pid = database.add_position(make_position({"position_name": "P"}))
        database.update_position(pid, {"status": config.STATUS_APPLIED})
        at = _run_page()
        df = at.dataframe[0].value
        assert list(df.columns) == self.DISPLAY_COLUMNS, (
            f"Display columns must be {self.DISPLAY_COLUMNS!r} in this order; "
            f"got {list(df.columns)!r}"
        )

    def test_default_filter_active_excludes_saved_and_closed(self, db):
        """DESIGN §8.3: default filter excludes SAVED + CLOSED. The
        Active sentinel resolves to
        STATUS_VALUES \\ STATUS_FILTER_ACTIVE_EXCLUDED at render time —
        a [SAVED] row (pre-application) and a [CLOSED] row (withdrawn)
        must not appear, while [APPLIED] / [INTERVIEW] / [REJECTED] /
        [DECLINED] rows DO appear (only SAVED + CLOSED are excluded)."""
        # Seed one row per status so the test exercises the FULL exclusion
        # set (not just SAVED) and the FULL inclusion set.
        rows = {
            "Saved Pos":     config.STATUS_SAVED,
            "Applied Pos":   config.STATUS_APPLIED,
            "Interview Pos": config.STATUS_INTERVIEW,
            "Closed Pos":    config.STATUS_CLOSED,
            "Rejected Pos":  config.STATUS_REJECTED,
            "Declined Pos":  config.STATUS_DECLINED,
        }
        for name, status in rows.items():
            pid = database.add_position(make_position({"position_name": name}))
            if status != config.STATUS_SAVED:
                database.update_position(pid, {"status": status})

        at = _run_page()
        names = list(at.dataframe[0].value["Position"])

        # SAVED + CLOSED must be hidden (they're in
        # STATUS_FILTER_ACTIVE_EXCLUDED); the four other statuses
        # must all appear.
        for name in ("Saved Pos", "Closed Pos"):
            assert not any(name in n for n in names), (
                f"Expected {name!r} hidden under default Active filter; "
                f"got {names!r}"
            )
        for name in ("Applied Pos", "Interview Pos",
                     "Rejected Pos", "Declined Pos"):
            assert any(name in n for n in names), (
                f"Expected {name!r} visible under default Active filter; "
                f"got {names!r}"
            )

    def test_filter_all_shows_every_row(self, db):
        """Switching to the 'All' sentinel must surface every row,
        including the otherwise-hidden SAVED / CLOSED rows. This is the
        primary recovery path for a user who needs to revisit a
        pre-application or withdrawn position."""
        for name, status in [
            ("Saved Pos",   config.STATUS_SAVED),
            ("Applied Pos", config.STATUS_APPLIED),
            ("Closed Pos",  config.STATUS_CLOSED),
        ]:
            pid = database.add_position(make_position({"position_name": name}))
            if status != config.STATUS_SAVED:
                database.update_position(pid, {"status": status})

        at = _run_page()
        at.selectbox(key=FILTER_STATUS_KEY).select("All")
        at.run()

        names = list(at.dataframe[0].value["Position"])
        for name in ("Saved Pos", "Applied Pos", "Closed Pos"):
            assert any(name in n for n in names), (
                f"Expected {name!r} visible under 'All' filter; got {names!r}"
            )

    def test_filter_specific_status_narrows(self, db):
        """Picking a specific STATUS_VALUES entry must narrow the table
        to exactly that status — not approximately, not a superset."""
        pid_app = database.add_position(make_position({"position_name": "App One"}))
        database.update_position(pid_app, {"status": config.STATUS_APPLIED})
        pid_int = database.add_position(make_position({"position_name": "Int One"}))
        database.update_position(pid_int, {"status": config.STATUS_INTERVIEW})

        at = _run_page()
        at.selectbox(key=FILTER_STATUS_KEY).select(config.STATUS_INTERVIEW)
        at.run()

        names = list(at.dataframe[0].value["Position"])
        assert any("Int One" in n for n in names), (
            f"Specific-status filter must retain matching row; got {names!r}"
        )
        assert not any("App One" in n for n in names), (
            f"Specific-status filter must hide non-matching rows; got {names!r}"
        )

    @pytest.mark.parametrize("institute,expected_label", [
        ("Stanford", "Stanford: Title One"),
        ("",         "Title One"),
        (None,       "Title One"),
    ])
    def test_position_column_format(self, db, institute, expected_label):
        """DESIGN §8.3 + T4 precedent: Position cell is
        f'{institute}: {position_name}' when institute is non-empty;
        bare position_name when institute is missing or _safe_str-coerced
        empty. Pinned across the three NULL/empty/populated cases so a
        future _safe_str regression on the institute column shows up
        here rather than as a silent display drift."""
        pid = database.add_position(make_position({
            "position_name": "Title One",
            "institute":     institute,
        }))
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        labels = list(at.dataframe[0].value["Position"])
        assert labels == [expected_label], (
            f"Position label mismatch for institute={institute!r}: "
            f"expected [{expected_label!r}]; got {labels!r}"
        )

    @pytest.mark.parametrize("received,date,expected_cell", [
        (0, None,         "—"),
        (1, "2026-04-19", "✓ Apr 19"),
        (1, None,         "✓ (no date)"),
    ])
    def test_confirmation_column_inline_format(
        self, db, received, date, expected_cell,
    ):
        """DESIGN §8.3 D-A amendment (Phase 5 T1-C): Streamlit 1.56's
        st.dataframe does not expose a per-cell tooltip API, so the
        original D-A tooltip text ('Received {ISO date}' / 'Received
        (no date recorded)') folds into inline cell content. Three
        cases pinned across the parametrize:
          - flag=0          → '—' (em-dash, never received)
          - flag=1, date    → '✓ Mon D' (matches T4 'Apr 24' format)
          - flag=1, no date → '✓ (no date)' (explicit no-date marker)

        Resolution recorded in reviews/phase-5-tier1-review.md."""
        pid = database.add_position(make_position({"position_name": "P"}))
        database.upsert_application(
            pid,
            {
                "applied_date":          "2026-04-15",
                "confirmation_received": received,
                "confirmation_date":     date,
            },
            propagate_status=False,
        )
        # Force status off [SAVED] so the row passes the default filter.
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        cells = list(at.dataframe[0].value["Confirmation"])
        assert cells == [expected_cell], (
            f"Confirmation cell mismatch for "
            f"(received={received!r}, date={date!r}): "
            f"expected [{expected_cell!r}]; got {cells!r}"
        )

    def test_table_sort_by_deadline_asc_nulls_last(self, db):
        """The table inherits get_applications_table's sort
        (deadline_date ASC NULLS LAST, position_id ASC). The page
        must NOT re-sort or apply its own ordering — the database
        contract is the contract."""
        pid_a = database.add_position(make_position({
            "position_name": "Late Applicant",
            "deadline_date": "2026-08-30",
        }))
        pid_b = database.add_position(make_position({
            "position_name": "No Deadline",
            "deadline_date": None,
        }))
        pid_c = database.add_position(make_position({
            "position_name": "Soon Applicant",
            "deadline_date": "2026-05-05",
        }))
        for pid in (pid_a, pid_b, pid_c):
            database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        names = list(at.dataframe[0].value["Position"])
        assert names == [
            "Stanford: Soon Applicant",
            "Stanford: Late Applicant",
            "Stanford: No Deadline",
        ], (
            f"Sort must be deadline ASC NULLS LAST; got {names!r}"
        )

    def test_empty_state_info_when_filter_excludes_all(self, db):
        """When the post-filter DataFrame is empty, the page must
        surface an `st.info(...)` message — and the table must NOT
        render (an empty st.dataframe with column headers but no rows
        looks like a broken state). Mirrors the
        Opportunities-page filter empty-state precedent
        (test_filter_by_status_no_match_shows_info)."""
        pid = database.add_position(make_position({"position_name": "Saved Only"}))
        # Single SAVED row; default Active filter excludes it.

        at = _run_page()
        info_messages = [el.value for el in at.info]
        assert any(self.EMPTY_COPY in m for m in info_messages), (
            f"Expected info message {self.EMPTY_COPY!r} when default filter "
            f"excludes every row; got info={info_messages!r}"
        )


# ── Column widths (T2-A, source-grep) ─────────────────────────────────────────

class TestApplicationsTableColumnConfig:
    """T2-A: when the table becomes selectable (T2-A makes
    `on_select='rerun', selection_mode='single-row'` live on
    apps_table), equal-width columns across six cells look cramped.
    Add `column_config` with explicit widths — Position wide, the rest
    narrower. AppTest does not surface column_config on the dataframe
    element (gotcha #15 — the protobuf serializes the data, not the
    construction parameters), so the contract is pinned at the source
    level. Drift here either means the column_config block was deleted
    or the column-name keys were renamed."""

    def test_column_config_block_present(self):
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert "column_config=" in src, (
            "T2-A requires column_config={...} on apps_table so "
            "selectable column widths don't collapse to equal cells. "
            "See gotcha #15 — AppTest can't see column_config, so "
            "this contract lives in source."
        )

    def test_position_column_is_wide(self):
        """Position carries 'institute: position_name' for many rows
        (T1-C `_format_label`); allocating it the wide slot keeps long
        labels readable."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        # Match either positional or keyword `label=` form so a future
        # refactor that re-orders TextColumn arguments doesn't trip.
        assert (
            ('"Position"' in src and 'width="large"' in src)
        ), (
            "Position column must be configured with width='large' "
            "via st.column_config.TextColumn(...)."
        )


# ── Selection plumbing (T2-A) ─────────────────────────────────────────────────

class TestApplicationsTableSelection:
    """T2-A: the Applications table is selectable. Selecting a row
    captures `applications_selected_position_id` so the detail card
    below can render. Deselection clears the key. The
    `_applications_skip_table_reset` one-shot preserves selection
    across the Save rerun (st.dataframe event resets across data-change
    reruns — gotcha #11). Filter-narrowing that excludes the selected
    row preserves the selection (asymmetry vs. Opportunities §8.2 — the
    Applications card stays visible while the filter is narrowed,
    matching DESIGN §8.3 + §8.2's general 'use the unfiltered df for
    lookup so an in-progress edit is never dismissed' principle)."""

    def test_selecting_row_captures_position_id(self, db):
        pid = database.add_position(make_position({"position_name": "P"}))
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        assert SELECTED_PID_KEY in at.session_state, (
            f"Selecting row 0 must populate {SELECTED_PID_KEY!r} so the "
            f"detail card can resolve which position to render."
        )
        assert at.session_state[SELECTED_PID_KEY] == pid, (
            f"Expected selected pid = {pid!r}; got "
            f"{at.session_state[SELECTED_PID_KEY]!r}."
        )

    def test_deselecting_clears_position_id(self, db):
        """Empty-selection event with NO ``_applications_skip_table_reset``
        flag set → the page must pop the selection key. Otherwise a
        stale selection would keep the detail card open against an
        invisible row."""
        pid = database.add_position(make_position({"position_name": "P"}))
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)
        assert at.session_state[SELECTED_PID_KEY] == pid  # precondition
        _deselect_row(at)

        assert SELECTED_PID_KEY not in at.session_state, (
            f"Deselecting must pop {SELECTED_PID_KEY!r}; the page is "
            f"hiding selection plumbing the user can't see otherwise."
        )

    def test_skip_table_reset_preserves_selection(self, db):
        """Sets `_applications_skip_table_reset = True` and reruns
        WITHOUT re-injecting selection state. AppTest's dataframe event
        is empty across the rerun (gotcha #11), so without the
        skip-flag the page would pop the selection key in the else
        branch and the card would collapse. With the flag, the page
        consumes the one-shot and preserves the selection so the
        post-Save rerun keeps the card open with fresh DB values."""
        pid = database.add_position(make_position({"position_name": "P"}))
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        # Set the skip-flag and run WITHOUT re-injecting selection.
        at.session_state[SKIP_TABLE_RESET_KEY] = True
        at.run()

        assert at.session_state[SELECTED_PID_KEY] == pid, (
            f"{SKIP_TABLE_RESET_KEY!r}=True must preserve "
            f"{SELECTED_PID_KEY!r} across the rerun; got "
            f"{_ss_or_none(at, SELECTED_PID_KEY)!r}."
        )
        # One-shot — popped by the page on consumption.
        assert SKIP_TABLE_RESET_KEY not in at.session_state, (
            f"{SKIP_TABLE_RESET_KEY!r} is one-shot; the page must "
            f"pop it on consumption so the next rerun behaves normally."
        )

    def test_filter_narrowing_does_not_clear_selection(self, db):
        """Asymmetry vs. Opportunities §8.2 (which pops selection on
        ``df_filtered.empty``). DESIGN §8.3 + the wireframe show the
        detail card persisting while the user explores other filters
        — so a filter narrowing that excludes the currently-selected
        position must NOT dismiss the in-progress edit."""
        pid = database.add_position(make_position({"position_name": "Visible"}))
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)
        assert at.session_state[SELECTED_PID_KEY] == pid  # precondition

        # Narrow to a status that contains no rows. Re-inject selection
        # to mimic browser-side persistence (the dataframe event
        # resets across the selectbox rerun — same protective behaviour
        # pinned in Opportunities-page tests).
        _keep_selection(at, 0)
        at.selectbox(key=FILTER_STATUS_KEY).select(config.STATUS_INTERVIEW)
        at.run()

        assert _ss_or_none(at, SELECTED_PID_KEY) == pid, (
            f"Filter narrowing must preserve {SELECTED_PID_KEY!r} "
            f"(asymmetry vs. Opportunities §8.2); got "
            f"{_ss_or_none(at, SELECTED_PID_KEY)!r}."
        )


# ── Detail card render (T2-A) ─────────────────────────────────────────────────

class TestApplicationsDetailCardRender:
    """T2-A: the detail card renders below the table when (and only
    when) a row is selected. The card is wrapped in
    `st.container(border=True)` to allow T3 to add a sibling
    `apps_interviews_form` inside the same container later. Header
    contract: `f"{institute}: {position_name} · {STATUS_LABELS[raw]}"`
    (mirroring the Opportunities edit-panel subheader from §8.2 and
    DESIGN §8.3's status-shows-STATUS_LABELS rule); the wireframe-
    suggested 'just the position name' is approximate — the status
    suffix is required by §8.3. Inline 'All recs submitted: ✓ / —'
    surfaces `database.is_all_recs_submitted(pid)` (vacuous-true for
    zero recs)."""

    def test_no_card_when_no_selection_initial_render(self, db):
        """No row selected → no detail-card subheader. Avoids a
        ghost card that references a row the user didn't pick."""
        pid = database.add_position(make_position({"position_name": "Ghost"}))
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        # Don't select. The card subheader carries the position name —
        # if it appears here, the page is rendering the card unprompted.
        sub_values = [el.value for el in at.subheader]
        assert not any("Ghost" in v for v in sub_values), (
            f"No row selected must mean no detail card; got "
            f"subheaders={sub_values!r}."
        )

    def test_card_header_includes_position_and_status(self, db):
        """Subheader shows ``f'{institute}: {position_name} · {label}'``
        — `institute` from the Position-cell formatter, `label` via
        `STATUS_LABELS[raw]` per DESIGN §8.0 + §8.3."""
        pid = database.add_position(make_position({
            "position_name": "Postdoc Slot",
            "institute":     "MIT",
        }))
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        sub_values = [el.value for el in at.subheader]
        applied_label = config.STATUS_LABELS[config.STATUS_APPLIED]
        assert any(
            "MIT" in v and "Postdoc Slot" in v and applied_label in v
            for v in sub_values
        ), (
            f"Detail-card subheader must include institute, "
            f"position_name, and STATUS_LABELS[status]; got "
            f"subheaders={sub_values!r}."
        )

    def test_card_header_uses_label_not_raw_status(self, db):
        """Storage holds bracketed sentinels (`[APPLIED]`); UI strips
        them via STATUS_LABELS. The card header must NEVER expose the
        raw bracketed value — same status-label convention pinned
        across the dashboard + Opportunities surfaces."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        sub_values = [el.value for el in at.subheader]
        # The raw sentinel must NOT appear; the stripped label must.
        assert not any(config.STATUS_APPLIED in v for v in sub_values), (
            f"Subheader must not expose the raw bracketed status "
            f"{config.STATUS_APPLIED!r}; got {sub_values!r}."
        )
        assert any(
            config.STATUS_LABELS[config.STATUS_APPLIED] in v
            for v in sub_values
        ), (
            f"Subheader must contain "
            f"{config.STATUS_LABELS[config.STATUS_APPLIED]!r}; "
            f"got {sub_values!r}."
        )

    def test_recs_glyph_when_all_submitted(self, db):
        """Single recommender with `submitted_date` set → glyph = ✓.
        Surfaces `database.is_all_recs_submitted(pid)` inline so the
        user reads it at a glance — same spec as the table's Recs
        column from T1-C."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})
        database.add_recommender(pid, {
            "recommender_name": "Dr. A",
            "submitted_date":   "2026-04-25",
        })

        at = _run_page()
        _select_row(at, 0)

        # Card carries an inline 'All recs submitted: ✓' line. Look in
        # both markdown and write content — Streamlit can render either.
        haystack = " ".join(
            [el.value for el in at.markdown]
            + [el.value for el in at.caption]
        )
        assert "All recs submitted" in haystack, (
            f"Expected 'All recs submitted: ...' line in card; "
            f"got md/caption={haystack!r}."
        )
        # Glyph = ✓ when all submitted (or when there are no recs at
        # all — vacuous truth, separate test below).
        assert "✓" in haystack, (
            f"All recommenders submitted ⇒ ✓ glyph; got "
            f"md/caption={haystack!r}."
        )

    def test_recs_glyph_when_some_pending(self, db):
        """One submitted, one not → glyph = — (em-dash). Inverse of
        the all-submitted case; pinned so a logic flip on the
        is_all_recs_submitted call shows up as a per-row glyph drift."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})
        database.add_recommender(pid, {
            "recommender_name": "Dr. A",
            "submitted_date":   "2026-04-25",
        })
        database.add_recommender(pid, {
            "recommender_name": "Dr. B",
            "submitted_date":   None,  # pending
        })

        at = _run_page()
        _select_row(at, 0)

        haystack = " ".join(
            [el.value for el in at.markdown]
            + [el.value for el in at.caption]
        )
        assert "All recs submitted" in haystack
        assert "—" in haystack, (
            f"Pending recommender ⇒ em-dash glyph; got "
            f"md/caption={haystack!r}."
        )

    def test_recs_glyph_vacuous_true_for_zero_recs(self, db):
        """Zero recommenders → `is_all_recs_submitted` returns True
        (vacuous truth, D23). The card mirrors that without a special
        case so the helper composes cleanly."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})
        # No recommenders added.

        at = _run_page()
        _select_row(at, 0)

        haystack = " ".join(
            [el.value for el in at.markdown]
            + [el.value for el in at.caption]
        )
        assert "All recs submitted" in haystack
        assert "✓" in haystack, (
            f"Zero recommenders ⇒ vacuous-true ⇒ ✓ glyph; got "
            f"md/caption={haystack!r}."
        )


# ── Detail card form: widget existence + pre-seed (T2-A) ──────────────────────

class TestApplicationsDetailCardForm:
    """T2-A: 8 widgets inside `st.form('apps_detail_form')`. All
    widget keys are page-prefixed `apps_*`; the form id ends in
    `_form` to avoid collision with any widget key inside (DESIGN
    §8.0, gotcha #4). Pre-seed gates on the
    `_applications_edit_form_sid` sentinel — a row change forces a
    full re-seed (gotcha #2). Text values use `_safe_str` to coerce
    NaN-from-NULL pandas cells (gotcha #1) so the form never sends a
    NaN through Streamlit's protobuf serialiser."""

    def test_form_id_is_apps_detail_form(self):
        """Source-grep pin — AppTest does not expose `st.form` ids
        on the element tree (forms are layout containers; the submit
        button is the only directly-queryable element). The id is
        the contract for collision-avoidance with the inside widgets
        per gotcha #4."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert f'st.form("{DETAIL_FORM_ID}")' in src \
            or f"st.form('{DETAIL_FORM_ID}')" in src \
            or f"st.form(key=\"{DETAIL_FORM_ID}\")" in src, (
            f"Detail card must wrap its widgets in "
            f"st.form('{DETAIL_FORM_ID}')."
        )

    @pytest.mark.parametrize("key", [
        W_APPLIED_DATE,
        W_CONFIRMATION_RCVD,
        W_CONFIRMATION_DATE,
        W_RESPONSE_TYPE,
        W_RESPONSE_DATE,
        W_RESULT,
        W_RESULT_NOTIFY_DATE,
        W_NOTES,
    ])
    def test_widget_renders_when_row_selected(self, db, key):
        """Each of the 8 editable widgets must exist after row
        selection. AppTest's KeyError on missing-key is the failure
        mode — we just assert the widget is reachable. The save-time
        coverage tests below verify each widget round-trips a value."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        # Reach the widget by key — Streamlit raises KeyError if absent.
        # Use a generic accessor rather than specific .text_area / .selectbox
        # so this parametrize works across widget types.
        try:
            _ = at.session_state[key]
        except KeyError:
            pytest.fail(
                f"Widget {key!r} not in session_state after row select; "
                f"either the widget is missing from the form or its "
                f"key was renamed."
            )

    def test_preseed_applied_date_null(self, db):
        """Fresh application row → applied_date NULL → the date_input
        renders with value=None. Pre-seed must coerce NULL → None
        (date_input rejects NaN; string '' produces a parse error)."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        assert at.session_state[W_APPLIED_DATE] is None, (
            f"NULL applied_date must pre-seed as None; got "
            f"{at.session_state[W_APPLIED_DATE]!r}."
        )

    def test_preseed_applied_date_set(self, db):
        """ISO string in DB → datetime.date in widget. The page must
        translate at the boundary so the widget renders a real date."""
        pid = database.add_position(make_position())
        database.upsert_application(
            pid,
            {"applied_date": "2026-04-18"},
            propagate_status=False,
        )
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        assert at.session_state[W_APPLIED_DATE] == datetime.date(2026, 4, 18), (
            f"applied_date '2026-04-18' must pre-seed as "
            f"datetime.date(2026, 4, 18); got "
            f"{at.session_state[W_APPLIED_DATE]!r}."
        )

    def test_preseed_confirmation_received_zero(self, db):
        """Schema DEFAULT confirmation_received=0 (DESIGN §6.2) →
        checkbox unchecked."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        assert at.session_state[W_CONFIRMATION_RCVD] is False, (
            f"confirmation_received=0 must pre-seed as False; got "
            f"{at.session_state[W_CONFIRMATION_RCVD]!r}."
        )

    def test_preseed_confirmation_received_one(self, db):
        pid = database.add_position(make_position())
        database.upsert_application(
            pid,
            {"confirmation_received": 1, "confirmation_date": "2026-04-19"},
            propagate_status=False,
        )
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        assert at.session_state[W_CONFIRMATION_RCVD] is True, (
            f"confirmation_received=1 must pre-seed as True; got "
            f"{at.session_state[W_CONFIRMATION_RCVD]!r}."
        )
        assert at.session_state[W_CONFIRMATION_DATE] == datetime.date(2026, 4, 19)

    def test_preseed_response_type_null_is_none(self, db):
        """Nullable selectbox: option list is `[None, *RESPONSE_TYPES]`
        with `format_func` rendering None → '—'. NULL response_type
        in DB ⇒ None selected."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        assert at.session_state[W_RESPONSE_TYPE] is None, (
            f"NULL response_type must pre-seed as None (the explicit "
            f"'no response' selectbox option); got "
            f"{at.session_state[W_RESPONSE_TYPE]!r}."
        )

    def test_preseed_result_default_pending(self, db):
        """Schema DEFAULT result='Pending' (config.RESULT_DEFAULT) →
        selectbox pre-selects 'Pending' on a fresh application row."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        assert at.session_state[W_RESULT] == config.RESULT_DEFAULT, (
            f"Fresh application must pre-seed result selectbox to "
            f"config.RESULT_DEFAULT={config.RESULT_DEFAULT!r}; got "
            f"{at.session_state[W_RESULT]!r}."
        )

    def test_preseed_notes_handles_null_safely(self, db):
        """NULL TEXT cell ⇒ pandas NaN ⇒ `_safe_str` coercion to ''.
        Without the coercion, the text_area's protobuf serializer raises
        'TypeError: bad argument type for built-in operation' (gotcha
        #1). Test asserts the page rendered without exception AND the
        widget value is a real str."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        assert not at.exception, (
            f"NaN-from-NULL pre-seed must not raise; got "
            f"exception={at.exception!r}."
        )
        # Type check + value: real str, empty, never NaN.
        v = at.session_state[W_NOTES]
        assert isinstance(v, str) and v == "", (
            f"NULL notes must pre-seed as empty str; got {v!r} "
            f"(type={type(v).__name__})."
        )

    def test_edit_form_sid_set_after_first_seed(self, db):
        """The sentinel records which row the form is currently
        seeded against. After selecting row 0, sentinel = pid_0.
        Pre-seed gates on this — same-row reruns leave widget values
        alone (preserving the in-flight draft); row-change forces a
        full re-seed (gotcha #2)."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        assert _ss_or_none(at, EDIT_FORM_SID_KEY) == pid, (
            f"After selecting pid={pid!r}, "
            f"{EDIT_FORM_SID_KEY!r} must equal that pid; got "
            f"{_ss_or_none(at, EDIT_FORM_SID_KEY)!r}."
        )

    def test_preseed_resets_on_row_change(self, db):
        """Selecting a different row must overwrite every widget key
        with the new row's values (gotcha #2 — the widget-value trap
        ignores the `value=` argument once `session_state[key]` is
        set, so the pre-seed must be done explicitly via direct
        session_state assignment, gated by the sid sentinel)."""
        pid_a = database.add_position(make_position({
            "position_name": "Alpha",
            "deadline_date": "2026-05-01",
        }))
        pid_b = database.add_position(make_position({
            "position_name": "Bravo",
            "deadline_date": "2026-06-01",
        }))
        database.upsert_application(
            pid_a, {"notes": "alpha-notes"}, propagate_status=False,
        )
        database.upsert_application(
            pid_b, {"notes": "bravo-notes"}, propagate_status=False,
        )
        database.update_position(pid_a, {"status": config.STATUS_APPLIED})
        database.update_position(pid_b, {"status": config.STATUS_APPLIED})

        at = _run_page()
        # Sort is deadline ASC NULLS LAST → Alpha (May 1) is row 0, Bravo (Jun 1) is row 1.
        _select_row(at, 0)
        assert at.session_state[W_NOTES] == "alpha-notes"

        _select_row(at, 1)
        assert at.session_state[W_NOTES] == "bravo-notes", (
            f"Row change must overwrite pre-seeded widget values; "
            f"got W_NOTES={at.session_state[W_NOTES]!r} (expected "
            f"'bravo-notes' from row 1)."
        )
        assert at.session_state[EDIT_FORM_SID_KEY] == pid_b, (
            f"{EDIT_FORM_SID_KEY!r} must track the most recently-seeded "
            f"pid; got {at.session_state[EDIT_FORM_SID_KEY]!r}."
        )


# ── Detail card save (T2-A) ───────────────────────────────────────────────────

class TestApplicationsDetailCardSave:
    """T2-A: Save handler builds a `fields` dict from the 8 widgets,
    calls `database.upsert_application(pid, fields, propagate_status=
    True)`, and on success: sets `_applications_skip_table_reset=True`
    (so the dataframe-event-reset rerun preserves the selection),
    pops `_applications_edit_form_sid` (so the next rerun re-seeds
    from fresh DB values), `st.toast(f'Saved …')`, `st.rerun()`. On
    Exception: `st.error(...)`, no re-raise (GUIDELINES §8), no
    toast, sentinel STAYS set so the user's dirty input is preserved
    in the form for retry. The R1/R3 cascade-promotion toast
    (`status_changed=True` returns ⇒ second toast) lands in T2-B —
    these tests pin only the basic Save path."""

    def _select_and_set_widget(
        self, at: AppTest, widget_key: str, value
    ) -> None:
        """Inject a widget value via session_state so the form picks
        it up on the next at.run() (which fires the form_submit click).
        AppTest's per-widget `.set_value` / `.select` methods also
        work, but a shared session_state-write helper keeps the save
        tests parametrize-friendly across widget types."""
        at.session_state[widget_key] = value

    @pytest.mark.parametrize("widget_key,db_field,widget_value,db_expected", [
        (W_APPLIED_DATE,       "applied_date",          datetime.date(2026, 4, 18), "2026-04-18"),
        (W_CONFIRMATION_RCVD,  "confirmation_received", True,                       1),
        (W_CONFIRMATION_DATE,  "confirmation_date",     datetime.date(2026, 4, 19), "2026-04-19"),
        (W_RESPONSE_DATE,      "response_date",         datetime.date(2026, 4, 22), "2026-04-22"),
        (W_RESULT_NOTIFY_DATE, "result_notify_date",    datetime.date(2026, 5, 1),  "2026-05-01"),
        (W_NOTES,              "notes",                 "interview prep",            "interview prep"),
    ])
    def test_save_persists_field(
        self, db, widget_key, db_field, widget_value, db_expected,
    ):
        """Per-widget round-trip: set widget → click Save → assert DB
        row reflects the new value. Coverage MUST equal the form's
        editable fields (similar regression-prevention to the
        Opportunities-page save_persists_all_nine_fields test)."""
        pid = database.add_position(make_position())
        # Move off [SAVED] so the row passes the default Active filter
        # (and so R1's NULL→non-NULL transition isn't accidentally
        # firing — applied_date is NULL on a fresh row, but we're
        # already on STATUS_APPLIED so no R1 toast surfaces).
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        self._select_and_set_widget(at, widget_key, widget_value)
        # Re-inject selection — the click below triggers an internal
        # rerun that resets the dataframe event without this guard.
        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        row = database.get_application(pid)
        assert row[db_field] == db_expected, (
            f"Save must persist {widget_key} → {db_field}; "
            f"expected {db_expected!r}, got {row[db_field]!r}."
        )

    def test_save_persists_response_type(self, db):
        """Selectbox needs `.select(...)` rather than direct
        session_state write — Streamlit batches selectbox state via
        a different protocol inside forms. Carved out of the
        parametrize since the access pattern differs."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        # Pick a non-Offer response so R3 doesn't fire (T2-B's territory).
        non_offer = next(
            v for v in config.RESPONSE_TYPES if v != config.RESPONSE_TYPE_OFFER
        )
        at.selectbox(key=W_RESPONSE_TYPE).select(non_offer)
        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        row = database.get_application(pid)
        assert row["response_type"] == non_offer, (
            f"Save must persist response_type; expected {non_offer!r}, "
            f"got {row['response_type']!r}."
        )

    def test_save_persists_result(self, db):
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        # Pick something other than RESULT_DEFAULT so the test exercises
        # a real change rather than a no-op self-write.
        new_result = next(
            v for v in config.RESULT_VALUES if v != config.RESULT_DEFAULT
        )
        at.selectbox(key=W_RESULT).select(new_result)
        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        row = database.get_application(pid)
        assert row["result"] == new_result, (
            f"Save must persist result; expected {new_result!r}, "
            f"got {row['result']!r}."
        )

    def test_save_fires_saved_toast(self, db):
        """Per DESIGN §8.0 cross-page convention: successful writes
        surface via `st.toast(f'Saved "<name>".')` because toast
        persists across the `st.rerun()` triggered after Save."""
        pid = database.add_position(make_position({"position_name": "Toasty"}))
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        at.session_state[W_NOTES] = "any change"
        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        toast_values = [el.value for el in at.toast]
        assert any("Saved" in v and "Toasty" in v for v in toast_values), (
            f"Successful save must fire st.toast(\"Saved …Toasty…\"); "
            f"got toasts={toast_values!r}."
        )

    def test_save_preserves_selection(self, db):
        """Post-Save invariant: ``applications_selected_position_id``
        survives the Save round-trip so the detail card stays open
        and re-seeds with fresh DB values rather than collapsing.

        The page's mechanism is the ``_applications_skip_table_reset``
        one-shot — set inside the Save handler before ``st.rerun()``,
        consumed by the selection-resolution block's elif branch on
        the post-Save rerun (when the dataframe event resets per
        gotcha #11). In AppTest the injected ``apps_table`` selection
        state persists across the rerun, so the if-branch fires and
        the flag is left set (harmless: it's a one-shot, the next
        empty-event rerun consumes it). Either way the user-visible
        invariant holds: selection is preserved. The
        ``test_skip_table_reset_preserves_selection`` test pins the
        elif-branch consumption path independently; the source-grep
        test below pins that the Save handler actually sets the flag."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        at.session_state[W_NOTES] = "trigger save"
        # _keep_selection mimics browser-side selection persistence —
        # AppTest leaves the dataframe event empty across reruns
        # without it, the form would not render on the post-click
        # rerun, and Save would never fire.
        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        assert SELECTED_PID_KEY in at.session_state, (
            f"Save must preserve {SELECTED_PID_KEY!r}; got it absent."
        )
        assert at.session_state[SELECTED_PID_KEY] == pid, (
            f"Save must preserve {SELECTED_PID_KEY!r} == pid={pid!r}; "
            f"got {_ss_or_none(at, SELECTED_PID_KEY)!r}."
        )

    def test_save_handler_sets_skip_table_reset_flag(self):
        """Source-grep pin: the Save handler must contain the
        `_applications_skip_table_reset = True` assignment.
        AppTest cannot observe the flag's life cycle end-to-end
        (see ``test_save_preserves_selection`` for why), so the
        existence of the assignment is pinned at source level.
        The behavioral counterpart — the elif branch CONSUMING the
        flag — is pinned by
        ``test_skip_table_reset_preserves_selection``; together the
        two tests cover both halves of the one-shot contract."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert (
            f'st.session_state["{SKIP_TABLE_RESET_KEY}"] = True' in src
            or f"st.session_state['{SKIP_TABLE_RESET_KEY}'] = True" in src
        ), (
            f"Save handler must set "
            f'st.session_state["{SKIP_TABLE_RESET_KEY}"] = True '
            f"before st.rerun(). Without it, selection collapses on "
            f"the post-Save rerun in a real browser (gotcha #11)."
        )

    def test_save_pops_edit_form_sid_to_force_reseed(self, db):
        """Save success → page pops `_applications_edit_form_sid` so
        the next render re-seeds widgets from fresh DB values. Without
        the pop, the widget-value trap would show stale form values
        even after a successful DB update (gotcha #2)."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)
        # Sentinel set by initial pre-seed.
        assert _ss_or_none(at, EDIT_FORM_SID_KEY) == pid

        at.session_state[W_NOTES] = "change"
        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        # After the post-Save rerun, the page re-seeds (the popped
        # sentinel triggers the row-change branch), and the sentinel
        # is set back to pid by that re-seed. So the FINAL state has
        # the sentinel = pid again — but that's the re-seed value, not
        # the stale pre-Save value. The way to assert "pop happened" is
        # to confirm the widget reflects the just-saved DB value (not
        # the old in-form draft), which is the integration check.
        assert at.session_state[W_NOTES] == "change", (
            f"After Save, the notes widget must reflect the just-saved "
            f"value via re-seed from DB; got "
            f"{at.session_state[W_NOTES]!r}."
        )
        # And the sentinel still matches the row (set by the re-seed).
        assert _ss_or_none(at, EDIT_FORM_SID_KEY) == pid

    def test_save_db_failure_shows_error_no_toast(self, db, monkeypatch):
        """`upsert_application` raises → page surfaces `st.error(...)`,
        does NOT fire the Saved toast, and does NOT pop the sentinel
        (so the user's dirty input stays in the form for retry).
        Mirrors the Opportunities-page save-failure precedent
        (GUIDELINES §8 — no re-raise in user-facing handlers)."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)
        sid_before = _ss_or_none(at, EDIT_FORM_SID_KEY)

        # Patch upsert_application on the module the page imports —
        # the page imports `database` as a module, so the page's
        # binding is `database.upsert_application`. Monkeypatch the
        # module attribute so the page's lookup finds the raising
        # version without modifying the test's import.
        def _boom(*args, **kwargs):
            raise RuntimeError("database is on fire")
        monkeypatch.setattr(database, "upsert_application", _boom)

        at.session_state[W_NOTES] = "this won't save"
        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, (
            f"Save failure must be caught and surfaced via st.error; "
            f"page must not re-raise per GUIDELINES §8. Got "
            f"exception={at.exception!r}."
        )
        # st.error message contains the failure copy.
        error_values = [el.value for el in at.error]
        assert any("database is on fire" in v for v in error_values) \
            or any("Could not save" in v for v in error_values), (
            f"Save failure must surface via st.error containing the "
            f"underlying message; got errors={error_values!r}."
        )
        # No Saved toast.
        toast_values = [el.value for el in at.toast]
        assert not any("Saved" in v for v in toast_values), (
            f"Failed save must NOT fire the Saved toast; got "
            f"toasts={toast_values!r}."
        )
        # Sentinel survives so the form stays seeded with dirty input.
        assert _ss_or_none(at, EDIT_FORM_SID_KEY) == sid_before, (
            f"Failed save must keep {EDIT_FORM_SID_KEY!r} set so the "
            f"user's dirty input isn't wiped by an unintended re-seed; "
            f"sid_before={sid_before!r}, after_failure="
            f"{_ss_or_none(at, EDIT_FORM_SID_KEY)!r}."
        )


# ── Cascade-promotion toast (T2-B) ────────────────────────────────────────────

class TestApplicationsCascadePromotionToast:
    """T2-B: when ``database.upsert_application(propagate_status=True)``
    returns ``status_changed=True``, the Save handler fires a SECOND
    ``st.toast(f"Promoted to {STATUS_LABELS[new_status]}.")`` after
    the existing ``Saved "<name>"`` toast. DESIGN §9.3 names two
    cascade rules R1 + R3 (R2 belongs to ``add_interview``, which is
    T3 territory):

      R1 — ``applied_date`` NULL → non-NULL on STATUS_SAVED →
           STATUS_APPLIED
      R3 — ``response_type == "Offer"`` on non-terminal status →
           STATUS_OFFER

    Both run inside the same DB transaction. status_changed compares
    status STRINGS (so an Offer→Offer self-write reports no change).
    Terminal guard on R3: positions in TERMINAL_STATUSES (CLOSED /
    REJECTED / DECLINED) are NOT regressed by R3.

    Tests source the expected promotion toast text through
    ``config.STATUS_LABELS[<status>]`` rather than literal ``"Applied"``
    / ``"Offer"`` strings — same convention as
    ``test_card_header_uses_label_not_raw_status`` in the T2-A
    detail-card render tests, so a future label rename surfaces here
    as a clean test failure rather than a silent miss.
    """

    def _saved_toast_text(self, name: str) -> str:
        """Build the canonical Saved-toast substring so tests don't
        re-derive the format string."""
        return f'Saved "{name}"'

    def _promo_toast_text(self, raw_status: str) -> str:
        """Build the canonical Promoted-toast substring sourced
        through STATUS_LABELS — matches the page's format exactly."""
        return f"Promoted to {config.STATUS_LABELS[raw_status]}"

    def test_r1_only_promotes_saved_to_applied(self, db):
        """R1 — STATUS_SAVED + applied_date NULL→non-NULL → STATUS_APPLIED.
        Default filter is Active (excludes SAVED), so the test flips
        the filter to All before selection so the SAVED row is
        addressable."""
        pid = database.add_position(make_position({"position_name": "R1Pos"}))
        # add_position seeds STATUS_SAVED via the schema DEFAULT
        # (config.STATUS_VALUES[0]) — no explicit update_position needed.

        at = _run_page()
        at.selectbox(key=FILTER_STATUS_KEY).select("All")
        at.run()
        _select_row(at, 0)

        at.session_state[W_APPLIED_DATE] = datetime.date(2026, 4, 18)
        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        toast_values = [el.value for el in at.toast]
        # Both toasts must be present.
        assert any(self._saved_toast_text("R1Pos") in v for v in toast_values), (
            f"Saved toast must fire on every successful save; "
            f"got toasts={toast_values!r}."
        )
        expected_promo = self._promo_toast_text(config.STATUS_APPLIED)
        assert any(expected_promo in v for v in toast_values), (
            f"R1 cascade must fire promotion toast {expected_promo!r}; "
            f"got toasts={toast_values!r}."
        )
        # And the position actually moved.
        assert database.get_position(pid)["status"] == config.STATUS_APPLIED

    def test_r3_only_promotes_applied_to_offer(self, db):
        """R3 — response_type=Offer on non-terminal status (here
        STATUS_APPLIED, with applied_date already set so R1 cannot
        also fire) → STATUS_OFFER."""
        pid = database.add_position(make_position({"position_name": "R3Pos"}))
        # Pre-state: applied_date set + STATUS_APPLIED. Use
        # propagate_status=False on this seeding upsert so we don't
        # spuriously fire R1 / R3 during setup.
        database.upsert_application(
            pid, {"applied_date": "2026-04-15"}, propagate_status=False,
        )
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        # Select "Offer" via the selectbox — the option list is
        # [None, *RESPONSE_TYPES] in the page, so .select(...) takes
        # the underlying value.
        at.selectbox(key=W_RESPONSE_TYPE).select(config.RESPONSE_TYPE_OFFER)
        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        toast_values = [el.value for el in at.toast]
        assert any(self._saved_toast_text("R3Pos") in v for v in toast_values)
        expected_promo = self._promo_toast_text(config.STATUS_OFFER)
        assert any(expected_promo in v for v in toast_values), (
            f"R3 cascade must fire promotion toast {expected_promo!r}; "
            f"got toasts={toast_values!r}."
        )
        assert database.get_position(pid)["status"] == config.STATUS_OFFER

    def test_r1_plus_r3_chained_promotes_saved_to_offer(self, db):
        """R1 + R3 chained inside one transaction: STATUS_SAVED with
        applied_date NULL→non-NULL AND response_type=Offer in the
        SAME upsert call. Per the §9.3 per-state table, R1 fires
        first (SAVED → APPLIED), R3 then fires (APPLIED → OFFER) —
        post-state is OFFER. The test verifies BOTH the toast AND
        the DB endpoint so a regression where R3 stalls on the
        intermediate APPLIED state surfaces here (Sonnet plan-review
        signal — the toast alone proves the endpoint, not the chain;
        only the DB probe disambiguates 'R3 stalled' from 'R3
        chained correctly')."""
        pid = database.add_position(make_position({"position_name": "ChainPos"}))
        # Default STATUS_SAVED post-add_position; no setup write.

        at = _run_page()
        at.selectbox(key=FILTER_STATUS_KEY).select("All")
        at.run()
        _select_row(at, 0)

        # Both R1 trigger (applied_date) AND R3 trigger (response_type)
        # in the same form submit → one upsert_application call →
        # one transaction → both cascades fire in §9.3 order.
        at.session_state[W_APPLIED_DATE] = datetime.date(2026, 4, 18)
        at.selectbox(key=W_RESPONSE_TYPE).select(config.RESPONSE_TYPE_OFFER)
        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        toast_values = [el.value for el in at.toast]
        # Final toast says OFFER (the post-state), not APPLIED (the
        # intermediate). status_changed reports the pre→post diff —
        # SAVED → OFFER → status_changed=True, new_status=OFFER.
        expected_promo = self._promo_toast_text(config.STATUS_OFFER)
        assert any(expected_promo in v for v in toast_values), (
            f"R1+R3 chained must end at STATUS_OFFER (toast "
            f"{expected_promo!r}); got toasts={toast_values!r}."
        )
        # `all(... not in ...)` (NOT `any(... not in ...)`) — the `any`
        # form is a tautology: it would pass whenever at least ONE toast
        # lacks the substring (e.g. the Saved toast or the final Offer
        # toast), which is true even when an intermediate "Promoted to
        # Applied" IS present. `all` requires every toast to lack it,
        # which is the actual no-intermediate-toast contract.
        assert all(
            self._promo_toast_text(config.STATUS_APPLIED) not in v
            for v in toast_values
        ), (
            "Chained cascade must NOT surface an intermediate "
            "'Promoted to Applied' toast — only the post-state."
        )
        # DB probe — proves R3 actually fired AFTER R1 (Sonnet
        # signal). If R3 had stalled on STATUS_SAVED, the position
        # would have ended at STATUS_APPLIED.
        post_status = database.get_position(pid)["status"]
        assert post_status == config.STATUS_OFFER, (
            f"R1+R3 must land at STATUS_OFFER; got {post_status!r}. "
            f"If APPLIED, R3 stalled on the intermediate state."
        )

    def test_terminal_guard_no_promotion_on_closed(self, db):
        """R3 has a terminal guard:
        ``WHERE status NOT IN TERMINAL_STATUSES``. Setting
        response_type=Offer on a STATUS_CLOSED position must NOT
        promote — but the Save itself MUST succeed (the application
        row's response_type is updated; only the position's status
        is preserved). Saved toast still fires; promotion toast does
        not."""
        pid = database.add_position(make_position({"position_name": "ClosedPos"}))
        database.update_position(pid, {"status": config.STATUS_CLOSED})

        at = _run_page()
        at.selectbox(key=FILTER_STATUS_KEY).select("All")
        at.run()
        _select_row(at, 0)

        at.selectbox(key=W_RESPONSE_TYPE).select(config.RESPONSE_TYPE_OFFER)
        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        toast_values = [el.value for el in at.toast]
        # Saved toast fires (the Save itself succeeded).
        assert any(
            self._saved_toast_text("ClosedPos") in v for v in toast_values
        ), (
            f"Save on a CLOSED position must still fire the Saved "
            f"toast (the application row was updated); got "
            f"toasts={toast_values!r}."
        )
        # Promotion toast does NOT fire — terminal guard kicked in.
        # Check against the Promoted prefix so any STATUS_LABELS
        # value would be caught (defense against a future status
        # rename).
        assert not any("Promoted to" in v for v in toast_values), (
            f"Terminal guard must suppress promotion toast on "
            f"CLOSED → response_type=Offer; got toasts={toast_values!r}."
        )
        # DB probe — application row updated, but position status
        # unchanged. Proves the Save persisted (the cascade is
        # cosmetically suppressed, not the entire write).
        assert database.get_application(pid)["response_type"] == config.RESPONSE_TYPE_OFFER
        assert database.get_position(pid)["status"] == config.STATUS_CLOSED, (
            "Terminal-status position must NOT be regressed by R3."
        )


# ── Cohesion sweep (T2-B) ─────────────────────────────────────────────────────

class TestApplicationsCohesionSweep:
    """T2-B cohesion bar: a small set of integration smoke tests
    catching combination-level regressions that the per-feature tests
    above don't. Per the 2026-04-30 Sonnet plan critique, the
    `filter-narrowing keeps form values` combination is intentionally
    OMITTED — the pre-seed gate `(sid != current OR key missing)`
    means filter narrowing alone (which doesn't change pid or pop
    widget keys) cannot corrupt pre-seeded values; the test would
    just exercise Streamlit's session_state persistence, not page
    code."""

    @pytest.mark.parametrize("widget_key", [
        W_APPLIED_DATE,
        W_CONFIRMATION_DATE,
        W_RESPONSE_DATE,
        W_RESULT_NOTIFY_DATE,
    ])
    def test_null_date_field_preseeds_to_none(self, db, widget_key):
        """All four ``st.date_input`` widgets pre-seed to ``None``
        when the underlying DB cell is NULL. T2-A pinned the
        applied_date and confirmation_date paths individually
        (``test_preseed_applied_date_null``,
        ``test_preseed_confirmation_received_zero``); the parametrize
        here closes the cohesion gap on response_date and
        result_notify_date too. ``_coerce_iso_to_date`` is the
        load-bearing helper — without it, a malformed cell or NaN
        would crash the page on ``date.fromisoformat``."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})
        # add_position auto-creates an applications row with every
        # date column NULL — no upsert needed.

        at = _run_page()
        _select_row(at, 0)

        assert not at.exception, (
            f"NULL pre-seed of {widget_key} must not raise; got "
            f"exception={at.exception!r}."
        )
        v = at.session_state[widget_key]
        assert v is None, (
            f"NULL date cell must pre-seed widget {widget_key!r} as "
            f"None; got {v!r} (type={type(v).__name__})."
        )

    def test_save_error_preserves_form_field_values(self, db, monkeypatch):
        """Extends T2-A's ``test_save_db_failure_shows_error_no_toast``
        (which asserts the sentinel survives) with a direct check on
        the actual widget VALUES. T2-A's coverage proves the sentinel
        survives — implying via the (sid_changed OR key missing)
        pre-seed gate that the values stay — but doesn't directly
        assert the user's dirty input is intact. This test closes
        that loop: type something, fail the save, assert the form
        still shows what the user typed so they can fix and retry."""
        pid = database.add_position(make_position())
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        at = _run_page()
        _select_row(at, 0)

        # Set distinguishable values across multiple widgets so we
        # can verify ALL of them survive the failure (not just the
        # one we typed last).
        dirty_notes = "the save will fail"
        dirty_applied = datetime.date(2026, 4, 18)
        at.session_state[W_NOTES]        = dirty_notes
        at.session_state[W_APPLIED_DATE] = dirty_applied
        at.selectbox(key=W_RESPONSE_TYPE).select(config.RESPONSE_TYPE_OFFER)

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated DB failure")
        monkeypatch.setattr(database, "upsert_application", _boom)

        _keep_selection(at, 0)
        at.button(key=DETAIL_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, (
            f"Save failure must be caught (GUIDELINES §8 — no "
            f"re-raise). Got exception={at.exception!r}."
        )
        # Every widget value the user typed must still be present
        # after the failure rerun. Without this guarantee, a save
        # error would silently wipe their work.
        assert at.session_state[W_NOTES] == dirty_notes, (
            f"Failed save must preserve text_area content; got "
            f"{at.session_state[W_NOTES]!r}."
        )
        assert at.session_state[W_APPLIED_DATE] == dirty_applied, (
            f"Failed save must preserve date_input content; got "
            f"{at.session_state[W_APPLIED_DATE]!r}."
        )
        assert at.session_state[W_RESPONSE_TYPE] == config.RESPONSE_TYPE_OFFER, (
            f"Failed save must preserve selectbox content; got "
            f"{at.session_state[W_RESPONSE_TYPE]!r}."
        )
