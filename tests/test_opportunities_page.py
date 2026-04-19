# tests/test_opportunities_page.py
# Integration tests for pages/1_Opportunities.py using Streamlit AppTest.
#
# Uses the real SQLite database via the shared `db` fixture (conftest.py).
# No mocking — database.py is already unit-tested; running it for real here
# gives integration confidence that the page and DB layer actually agree.
#
# AppTest runs the page script in-process. The monkeypatch in conftest.py
# patches database.DB_PATH before each test, so AppTest picks up the temp DB.

import datetime
import pytest
import database
import config
from streamlit.testing.v1 import AppTest

PAGE = "pages/1_Opportunities.py"

# F2: use the explicit key passed to st.form_submit_button() rather than
# relying on Streamlit's internal auto-generated "FormSubmitter:{form}-{label}"
# format, which is undocumented and could change between library versions.
SUBMIT_KEY = "qa_submit"

# T4-A: key passed to st.dataframe() so tests can drive row selection by
# injecting into session_state (AppTest exposes no click-a-row API).
TABLE_KEY = "positions_table"


def _select_row(at: AppTest, row_index: int) -> None:
    """Simulate a single-row selection on the positions table.

    AppTest's Dataframe element has no select() method, so we write the
    selection state directly to session_state and rerun. Shape matches what
    Streamlit 1.56 writes for on_select='rerun' + selection_mode='single-row'."""
    at.session_state[TABLE_KEY] = {
        "selection": {"rows": [row_index], "columns": []}
    }
    at.run()


def _deselect_row(at: AppTest) -> None:
    """Simulate deselecting all rows on the positions table."""
    at.session_state[TABLE_KEY] = {
        "selection": {"rows": [], "columns": []}
    }
    at.run()


def _run_page() -> AppTest:
    """Return a freshly-run AppTest for the Opportunities page.
    Call after the `db` fixture has patched DB_PATH."""
    at = AppTest.from_file(PAGE)
    at.run()
    assert not at.exception, f"Page raised an exception: {at.exception}"
    return at


# ── Empty state ───────────────────────────────────────────────────────────────

class TestEmptyState:

    def test_shows_info_message_when_no_positions(self, db):
        """Page must display an info message when the positions table is empty."""
        at = _run_page()
        assert at.info, "Expected at least one st.info element when DB is empty"
        assert any("No positions" in el.value for el in at.info), (
            f"Expected 'No positions' in info text, got: {[el.value for el in at.info]}"
        )

    def test_hides_empty_message_when_positions_exist(self, db):
        """The empty-state message must not appear once a position exists."""
        database.add_position({"position_name": "Stanford BioStats"})
        at = _run_page()
        assert not any("No positions" in el.value for el in at.info), (
            "Empty-state info should not appear when the DB has rows"
        )


# ── Quick-add form structure ──────────────────────────────────────────────────

class TestQuickAddFormStructure:
    """All six QUICK_ADD_FIELDS must have corresponding widgets on the page."""

    def test_expander_labeled_quick_add(self, db):
        at = _run_page()
        labels = [e.label for e in at.expander]
        assert "Quick Add" in labels, f"Expected 'Quick Add' expander, got: {labels}"

    def test_form_has_position_name_field(self, db):
        at = _run_page()
        at.text_input(key="qa_position_name")  # raises KeyError if absent

    def test_form_has_institute_field(self, db):
        at = _run_page()
        at.text_input(key="qa_institute")

    def test_form_has_field_field(self, db):
        at = _run_page()
        at.text_input(key="qa_field")

    def test_form_has_deadline_field(self, db):
        at = _run_page()
        at.date_input(key="qa_deadline_date")

    def test_form_has_priority_field(self, db):
        at = _run_page()
        at.selectbox(key="qa_priority")

    def test_form_has_link_field(self, db):
        at = _run_page()
        at.text_input(key="qa_link")

    def test_priority_options_match_config(self, db):
        """Priority selectbox options must exactly match config.PRIORITY_VALUES."""
        at = _run_page()
        actual = list(at.selectbox(key="qa_priority").options)
        assert actual == config.PRIORITY_VALUES, (
            f"Priority options mismatch.\n"
            f"  Expected: {config.PRIORITY_VALUES}\n"
            f"  Got:      {actual}"
        )


# ── Quick-add form behaviour ──────────────────────────────────────────────────

class TestQuickAddFormBehaviour:

    def test_submit_without_position_name_shows_error(self, db):
        """Submitting with empty position_name shows an error and inserts nothing."""
        at = _run_page()
        at.button(key=SUBMIT_KEY).click()
        at.run()
        assert at.error, "Expected st.error when position_name is blank"
        assert database.get_all_positions().empty, (
            "No row should be inserted when position_name is empty"
        )

    def test_submit_with_whitespace_only_name_shows_error(self, db):
        """Whitespace-only position_name must be treated as empty (F3 fix).

        Before the fix, `not "   "` evaluates to False so the insert ran.
        After stripping, `not "   ".strip()` is True and the error fires."""
        at = _run_page()
        at.text_input(key="qa_position_name").input("   ")
        at.button(key=SUBMIT_KEY).click()
        at.run()
        assert at.error, "Expected st.error for whitespace-only position_name"
        assert database.get_all_positions().empty, (
            "No row should be inserted for whitespace-only position_name"
        )

    def test_submit_with_position_name_only_adds_position(self, db):
        """Minimal valid submission (position_name only) must create one DB row."""
        at = _run_page()
        at.text_input(key="qa_position_name").input("Stanford BioStats")
        at.button(key=SUBMIT_KEY).click()
        at.run()
        assert not at.exception
        df = database.get_all_positions()
        assert len(df) == 1, f"Expected 1 row, got {len(df)}"
        assert df.iloc[0]["position_name"] == "Stanford BioStats"

    def test_submit_with_all_fields_stores_correct_data(self, db):
        """All 6 QUICK_ADD_FIELDS must be persisted correctly."""
        at = _run_page()
        at.text_input(key="qa_position_name").input("MIT CSAIL Postdoc")
        at.text_input(key="qa_institute").input("MIT")
        at.text_input(key="qa_field").input("Machine Learning")
        at.date_input(key="qa_deadline_date").set_value(datetime.date(2026, 6, 1))
        at.selectbox(key="qa_priority").select("High")
        at.text_input(key="qa_link").input("https://mit.edu/csail")
        at.button(key=SUBMIT_KEY).click()
        at.run()

        assert not at.exception
        df = database.get_all_positions()
        assert len(df) == 1
        row = df.iloc[0]
        assert row["position_name"] == "MIT CSAIL Postdoc"
        assert row["institute"]      == "MIT"
        assert row["field"]          == "Machine Learning"
        assert row["deadline_date"]  == "2026-06-01"
        assert row["priority"]       == "High"
        assert row["link"]           == "https://mit.edu/csail"

    def test_submit_shows_success_message(self, db):
        """A st.success element must appear after a valid submission."""
        at = _run_page()
        at.text_input(key="qa_position_name").input("Harvard Postdoc")
        at.button(key=SUBMIT_KEY).click()
        at.run()
        assert at.toast, "Expected st.toast after a valid quick-add submission"

    def test_new_position_has_open_status(self, db):
        """Positions added via quick-add must default to STATUS_VALUES[0] ('[OPEN]')."""
        at = _run_page()
        at.text_input(key="qa_position_name").input("Yale Postdoc")
        at.button(key=SUBMIT_KEY).click()
        at.run()
        df = database.get_all_positions()
        assert df.iloc[0]["status"] == config.STATUS_VALUES[0], (
            f"Expected status '{config.STATUS_VALUES[0]}', "
            f"got '{df.iloc[0]['status']}'"
        )

    def test_submit_twice_creates_two_separate_rows(self, db):
        """Two sequential quick-add submissions must produce two independent rows."""
        for name in ("Position A", "Position B"):
            at = AppTest.from_file(PAGE)
            at.run()
            at.text_input(key="qa_position_name").input(name)
            at.button(key=SUBMIT_KEY).click()
            at.run()
            assert not at.exception

        df = database.get_all_positions()
        assert len(df) == 2, f"Expected 2 rows after two submissions, got {len(df)}"
        names = set(df["position_name"].tolist())
        assert names == {"Position A", "Position B"}


# ── Positions table ───────────────────────────────────────────────────────────

class TestPositionsTable:

    def test_no_table_when_no_positions(self, db):
        """st.dataframe must not appear when the DB is empty."""
        at = _run_page()
        assert not at.dataframe, "Expected no dataframe element when DB is empty"

    def test_table_appears_with_positions(self, db):
        """st.dataframe must appear exactly once when positions exist."""
        database.add_position({"position_name": "Stanford Postdoc"})
        at = _run_page()
        assert len(at.dataframe) == 1, (
            f"Expected exactly one dataframe element, got {len(at.dataframe)}"
        )

    def test_table_row_count_matches_filtered_count(self, db):
        """Row count in the dataframe must match the filter-narrowed position count."""
        database.add_position({"position_name": "A"})                          # [OPEN] by default
        database.add_position({"position_name": "B"})                          # [OPEN] by default
        database.add_position({"position_name": "C", "status": "[APPLIED]"})
        at = _run_page()
        at.selectbox(key="filter_status").select("[OPEN]")
        at.run()
        assert not at.exception
        assert len(at.dataframe) == 1
        assert len(at.dataframe[0].value) == 2, (
            f"Expected 2 rows after status=[OPEN] filter, got {len(at.dataframe[0].value)}"
        )

    def test_table_has_required_columns(self, db):
        """The captured dataframe must contain all required display columns."""
        database.add_position({"position_name": "Test"})
        at = _run_page()
        cols = set(at.dataframe[0].value.columns)
        required = {"position_name", "institute", "priority", "status",
                    "deadline_date", "deadline_urgency"}
        missing = required - cols
        assert not missing, f"Columns missing from table: {missing}"

    def test_urgent_deadline_flagged_as_urgent(self, db):
        """Deadline within DEADLINE_URGENT_DAYS must produce deadline_urgency='urgent'."""
        deadline = (
            datetime.date.today()
            + datetime.timedelta(days=config.DEADLINE_URGENT_DAYS - 1)
        ).isoformat()
        database.add_position({"position_name": "Urgent", "deadline_date": deadline})
        at = _run_page()
        df = at.dataframe[0].value
        row = df[df["position_name"] == "Urgent"]
        assert row["deadline_urgency"].iloc[0] == "urgent", (
            f"Expected 'urgent' for deadline {deadline}, "
            f"got '{row['deadline_urgency'].iloc[0]}'"
        )

    def test_alert_deadline_flagged_as_alert(self, db):
        """Deadline > DEADLINE_URGENT_DAYS but ≤ DEADLINE_ALERT_DAYS must produce
        deadline_urgency='alert'."""
        deadline = (
            datetime.date.today()
            + datetime.timedelta(days=config.DEADLINE_URGENT_DAYS + 1)
        ).isoformat()
        database.add_position({"position_name": "Alert", "deadline_date": deadline})
        at = _run_page()
        df = at.dataframe[0].value
        row = df[df["position_name"] == "Alert"]
        assert row["deadline_urgency"].iloc[0] == "alert", (
            f"Expected 'alert' for deadline {deadline}, "
            f"got '{row['deadline_urgency'].iloc[0]}'"
        )

    def test_normal_deadline_not_flagged(self, db):
        """Deadline beyond DEADLINE_ALERT_DAYS must produce deadline_urgency=''."""
        deadline = (
            datetime.date.today()
            + datetime.timedelta(days=config.DEADLINE_ALERT_DAYS + 10)
        ).isoformat()
        database.add_position({"position_name": "Normal", "deadline_date": deadline})
        at = _run_page()
        df = at.dataframe[0].value
        row = df[df["position_name"] == "Normal"]
        assert row["deadline_urgency"].iloc[0] == "", (
            f"Expected '' for deadline {deadline}, "
            f"got '{row['deadline_urgency'].iloc[0]}'"
        )

    def test_no_deadline_not_flagged(self, db):
        """A position without a deadline_date must produce deadline_urgency=''."""
        database.add_position({"position_name": "No Deadline"})   # no deadline_date supplied
        at = _run_page()
        df = at.dataframe[0].value
        row = df[df["position_name"] == "No Deadline"]
        assert row["deadline_urgency"].iloc[0] == "", (
            f"Expected '' when no deadline, got '{row['deadline_urgency'].iloc[0]}'"
        )

    def test_urgency_at_urgent_threshold_boundary(self, db):
        """Deadline exactly DEADLINE_URGENT_DAYS away must produce 'urgent' (F3: ≤ boundary).

        Tests the boundary of `days <= DEADLINE_URGENT_DAYS` — a `<` operator
        would incorrectly return 'alert' for this case."""
        deadline = (
            datetime.date.today()
            + datetime.timedelta(days=config.DEADLINE_URGENT_DAYS)
        ).isoformat()
        database.add_position({"position_name": "At Urgent Boundary", "deadline_date": deadline})
        at = _run_page()
        df = at.dataframe[0].value
        row = df[df["position_name"] == "At Urgent Boundary"]
        assert row["deadline_urgency"].iloc[0] == "urgent", (
            f"Expected 'urgent' at boundary days={config.DEADLINE_URGENT_DAYS}, "
            f"got '{row['deadline_urgency'].iloc[0]}'"
        )

    def test_urgency_at_alert_threshold_boundary(self, db):
        """Deadline exactly DEADLINE_ALERT_DAYS away must produce 'alert' (F3: ≤ boundary).

        Tests the boundary of `days <= DEADLINE_ALERT_DAYS` — a `<` operator
        would incorrectly return '' for this case."""
        deadline = (
            datetime.date.today()
            + datetime.timedelta(days=config.DEADLINE_ALERT_DAYS)
        ).isoformat()
        database.add_position({"position_name": "At Alert Boundary", "deadline_date": deadline})
        at = _run_page()
        df = at.dataframe[0].value
        row = df[df["position_name"] == "At Alert Boundary"]
        assert row["deadline_urgency"].iloc[0] == "alert", (
            f"Expected 'alert' at boundary days={config.DEADLINE_ALERT_DAYS}, "
            f"got '{row['deadline_urgency'].iloc[0]}'"
        )

    def test_past_deadline_flagged_as_urgent(self, db):
        """A deadline that has already passed (days < 0) must produce 'urgent' (F4).

        days < 0 satisfies `days <= DEADLINE_URGENT_DAYS`, so past deadlines are
        surfaced as urgent — the user must either apply or close them."""
        deadline = (
            datetime.date.today() - datetime.timedelta(days=5)
        ).isoformat()
        database.add_position({"position_name": "Expired", "deadline_date": deadline})
        at = _run_page()
        df = at.dataframe[0].value
        row = df[df["position_name"] == "Expired"]
        assert row["deadline_urgency"].iloc[0] == "urgent", (
            f"Expected 'urgent' for past deadline {deadline}, "
            f"got '{row['deadline_urgency'].iloc[0]}'"
        )


# ── Filter bar structure ──────────────────────────────────────────────────────

class TestFilterBarStructure:
    """All three filter widgets must be present with correct keys and options."""

    def test_has_status_selectbox(self, db):
        at = _run_page()
        at.selectbox(key="filter_status")  # raises KeyError if absent

    def test_has_priority_selectbox(self, db):
        at = _run_page()
        at.selectbox(key="filter_priority")

    def test_has_field_text_input(self, db):
        at = _run_page()
        at.text_input(key="filter_field")

    def test_status_options_match_config(self, db):
        """Status filter must offer 'All' plus every value from config.STATUS_VALUES."""
        at = _run_page()
        actual = list(at.selectbox(key="filter_status").options)
        expected = ["All"] + config.STATUS_VALUES
        assert actual == expected, (
            f"Status filter options mismatch.\n"
            f"  Expected: {expected}\n"
            f"  Got:      {actual}"
        )

    def test_priority_options_match_config(self, db):
        """Priority filter must offer 'All' plus every value from config.PRIORITY_VALUES."""
        at = _run_page()
        actual = list(at.selectbox(key="filter_priority").options)
        expected = ["All"] + config.PRIORITY_VALUES
        assert actual == expected, (
            f"Priority filter options mismatch.\n"
            f"  Expected: {expected}\n"
            f"  Got:      {actual}"
        )


# ── Filter bar behaviour ──────────────────────────────────────────────────────

class TestFilterBarBehaviour:

    def test_default_shows_all_positions(self, db):
        """With default filters (All/All/''), every position in the DB is counted."""
        database.add_position({"position_name": "Position A"})
        database.add_position({"position_name": "Position B"})
        at = _run_page()
        assert not at.exception
        assert len(at.caption) == 1
        assert "2 position(s)" in at.caption[0].value, (
            f"Expected '2 position(s)' in caption, got: {at.caption[0].value!r}"
        )

    def test_filter_by_status_narrows_results(self, db):
        """Selecting a specific status must hide positions with other statuses."""
        database.add_position({"position_name": "Open One"})                          # status defaults to [OPEN]
        database.add_position({"position_name": "Applied One", "status": "[APPLIED]"})
        at = _run_page()
        at.selectbox(key="filter_status").select("[OPEN]")
        at.run()
        assert not at.exception
        assert len(at.caption) == 1
        assert "1 position(s)" in at.caption[0].value, (
            f"Expected '1 position(s)' after status filter, got: {at.caption[0].value!r}"
        )

    def test_filter_by_status_no_match_shows_info(self, db):
        """When the status filter matches no rows, a specific info message must appear."""
        database.add_position({"position_name": "Open One"})  # [OPEN] by default
        at = _run_page()
        at.selectbox(key="filter_status").select("[APPLIED]")
        at.run()
        assert not at.exception
        assert any("No positions match" in el.value for el in at.info), (
            f"Expected 'No positions match' info; got: {[el.value for el in at.info]}"
        )

    def test_filter_by_priority_narrows_results(self, db):
        """Selecting a specific priority must hide positions with other priorities."""
        database.add_position({"position_name": "High Prio", "priority": "High"})
        database.add_position({"position_name": "Med Prio",  "priority": "Med"})
        at = _run_page()
        at.selectbox(key="filter_priority").select("High")
        at.run()
        assert not at.exception
        assert len(at.caption) == 1
        assert "1 position(s)" in at.caption[0].value, (
            f"Expected '1 position(s)' after priority filter, got: {at.caption[0].value!r}"
        )

    def test_filter_by_field_substring_match(self, db):
        """Field text filter must match positions whose field contains the search term."""
        database.add_position({"position_name": "ML Postdoc",    "field": "Machine Learning"})
        database.add_position({"position_name": "Stats Postdoc", "field": "Statistics"})
        at = _run_page()
        at.text_input(key="filter_field").input("Machine")
        at.run()
        assert not at.exception
        assert len(at.caption) == 1
        assert "1 position(s)" in at.caption[0].value, (
            f"Expected '1 position(s)' after field filter, got: {at.caption[0].value!r}"
        )

    def test_filter_by_field_is_case_insensitive(self, db):
        """Field filter must match regardless of letter case."""
        database.add_position({"position_name": "ML Postdoc", "field": "Machine Learning"})
        at = _run_page()
        at.text_input(key="filter_field").input("MACHINE")
        at.run()
        assert not at.exception
        assert len(at.caption) == 1
        assert "1 position(s)" in at.caption[0].value, (
            "Expected case-insensitive field filter to match 'Machine Learning'"
        )

    def test_combined_status_and_priority_narrows_results(self, db):
        """Both status and priority filters apply simultaneously (AND logic)."""
        database.add_position({"position_name": "A", "priority": "High"})                          # [OPEN] + High
        database.add_position({"position_name": "B", "priority": "Med"})                           # [OPEN] + Med
        database.add_position({"position_name": "C", "priority": "High", "status": "[APPLIED]"})   # [APPLIED] + High
        at = _run_page()
        at.selectbox(key="filter_status").select("[OPEN]")
        at.selectbox(key="filter_priority").select("High")
        at.run()
        assert not at.exception
        assert len(at.caption) == 1
        assert "1 position(s)" in at.caption[0].value, (
            f"Expected only position A after combined filter, got: {at.caption[0].value!r}"
        )

    def test_db_empty_with_filter_shows_original_empty_message(self, db):
        """When the DB has no rows at all, the 'No positions yet' message must appear
        even if a filter is active — not the 'No positions match' filter message."""
        at = _run_page()
        at.selectbox(key="filter_status").select(config.STATUS_VALUES[0])
        at.run()
        assert not at.exception
        assert any("No positions yet" in el.value for el in at.info), (
            f"Expected 'No positions yet' when DB is empty; got: {[el.value for el in at.info]}"
        )

    def test_filter_by_field_with_special_characters(self, db):
        """Field filter must treat the search term as a literal string, not a regex (F5).

        'C++' contains regex metacharacters ('+' = one-or-more quantifier) that would
        raise re.error with str.contains(regex=True). With regex=False, it must match
        'C++ Programming' correctly and return exactly 1 position."""
        database.add_position({"position_name": "C++ Postdoc",    "field": "C++ Programming"})
        database.add_position({"position_name": "Python Postdoc", "field": "Python"})
        at = _run_page()
        at.text_input(key="filter_field").input("C++")
        at.run()
        assert not at.exception, f"Field filter raised an exception: {at.exception}"
        assert len(at.caption) == 1
        assert "1 position(s)" in at.caption[0].value, (
            f"Expected 'C++ Programming' to match literal 'C++' filter; "
            f"got: {at.caption[0].value!r}"
        )


# ── Row selection (T4-A) ──────────────────────────────────────────────────────
# The positions table uses st.dataframe(on_select='rerun', selection_mode='single-row').
# When a row is selected, the row's DB id must land in session_state as
# 'selected_position_id'. T4-B (tabs) and T4-C–F (edit fields) will read that key.

class TestRowSelection:

    def test_no_selection_in_session_state_initially(self, db):
        """With no user interaction, 'selected_position_id' must not be in session_state."""
        database.add_position({"position_name": "Alpha"})
        at = _run_page()
        assert "selected_position_id" not in at.session_state, (
            "selected_position_id should be absent until a row is explicitly selected"
        )

    def test_selecting_row_sets_selected_position_id(self, db):
        """Injecting a single-row selection must populate selected_position_id with the row's DB id."""
        pid_alpha = database.add_position({"position_name": "Alpha"})
        pid_beta  = database.add_position({"position_name": "Beta"})

        at = AppTest.from_file(PAGE)
        at.run()
        assert not at.exception

        # Find the display-row index of "Beta" so we don't assume ordering.
        df = at.dataframe[0].value
        beta_positional = list(df["position_name"]).index("Beta")

        _select_row(at, beta_positional)
        assert not at.exception, f"Page raised after selection: {at.exception}"
        assert "selected_position_id" in at.session_state, (
            "Row selection did not set selected_position_id"
        )
        assert at.session_state["selected_position_id"] == pid_beta, (
            f"Expected selected_position_id={pid_beta} (Beta), "
            f"got {at.session_state['selected_position_id']}"
        )

    def test_deselecting_clears_selected_position_id(self, db):
        """Setting rows=[] (deselection) must remove selected_position_id from session_state."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert "selected_position_id" in at.session_state, (
            "Precondition failed: row selection did not set selected_position_id"
        )
        _deselect_row(at)
        assert "selected_position_id" not in at.session_state, (
            "Deselecting a row should remove selected_position_id from session_state"
        )

    def test_selection_respects_active_filter(self, db):
        """Row 0 of a filtered view must map to the filtered row's id, not an unfiltered row."""
        pid_applied = database.add_position(
            {"position_name": "Applied One", "status": "[APPLIED]"}
        )
        pid_open = database.add_position(
            {"position_name": "Open One", "status": "[OPEN]"}
        )
        at = AppTest.from_file(PAGE)
        at.run()
        at.selectbox(key="filter_status").select("[OPEN]")
        at.run()
        # df_display now has exactly one row: "Open One". Row 0 must map to pid_open.
        _select_row(at, 0)
        assert "selected_position_id" in at.session_state
        assert at.session_state["selected_position_id"] == pid_open, (
            f"Filtered row 0 should map to pid_open={pid_open}, "
            f"got {at.session_state['selected_position_id']}"
        )

    def test_filter_to_empty_clears_stale_selection(self, db):
        """When an active filter hides all rows (or the DB goes empty), any stale
        selection must be cleared so later tiers (tabs, edit panel) don't render
        for a position the user can no longer see."""
        database.add_position({"position_name": "Alpha", "status": "[OPEN]"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert "selected_position_id" in at.session_state   # precondition
        # Apply a filter that matches nothing.
        at.selectbox(key="filter_status").select("[APPLIED]")
        at.run()
        assert "selected_position_id" not in at.session_state, (
            "Stale selected_position_id must be cleared when filter hides all rows"
        )

    def test_selection_mode_is_single_row(self, db):
        """Regression guard: multi-row selection would let the user pick N positions
        but the edit panel can only show one. The widget must be configured for
        single-row selection."""
        database.add_position({"position_name": "Alpha"})
        at = _run_page()
        # `selection_mode` is a repeated enum field on the Arrow proto; resolve
        # the integer values to their enum names via the DESCRIPTOR so the test
        # fails loudly if Streamlit renumbers the enum in a future release.
        proto = at.dataframe[0].proto
        enum_type = proto.DESCRIPTOR.fields_by_name["selection_mode"].enum_type
        modes = [enum_type.values_by_number[v].name for v in proto.selection_mode]
        assert modes == ["SINGLE_ROW"], (
            f"Expected selection_mode == ['SINGLE_ROW'], got {modes!r}"
        )
