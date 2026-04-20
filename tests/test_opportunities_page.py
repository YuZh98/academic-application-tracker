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

    def test_save_error_shows_error_without_raising(self, db, monkeypatch):
        """F1 (Tier-4 full review) regression guard: when database.add_position
        raises, the page must surface an st.error but NOT re-raise the
        exception. The previous implementation did `raise` after st.error,
        which made Streamlit render the very traceback the handler exists
        to prevent. This test patches add_position to raise and verifies
        both sides of the contract."""
        def _boom(_fields):
            raise RuntimeError("db unavailable")
        monkeypatch.setattr(database, "add_position", _boom)

        at = _run_page()
        at.text_input(key="qa_position_name").input("Stanford BioStats")
        at.button(key=SUBMIT_KEY).click()
        at.run()

        # Contract 1: user sees the friendly message.
        assert at.error, "Expected st.error when add_position raises"
        assert any("Could not save position" in el.value for el in at.error), (
            f"Expected 'Could not save position' prefix in error, "
            f"got: {[el.value for el in at.error]}"
        )
        # Contract 2: no uncaught exception reaches Streamlit's renderer.
        assert not at.exception, (
            f"Save handler must swallow the exception after st.error; "
            f"got uncaught: {at.exception}"
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

    def test_quick_add_clears_selection(self, db):
        """Regression guard for Tier-4 review F1: Quick-Add's st.rerun() must
        clear the dataframe selection state, because get_all_positions()
        orders deadline_date ASC NULLS LAST — a new position's index
        depends on its deadline relative to existing rows and can land
        anywhere, so a surviving selection index could silently re-bind
        the edit panel to a different position."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert "selected_position_id" in at.session_state   # precondition
        # Submit a quick-add for a new position via the real form.
        at.text_input(key="qa_position_name").set_value("Beta")
        at.button(key="qa_submit").click()
        at.run()
        assert not at.exception, f"Quick-add raised after selection: {at.exception}"
        assert "selected_position_id" not in at.session_state, (
            "Quick-Add must clear selected_position_id so the post-rerun "
            "row-index shift doesn't silently switch the selected position"
        )
        assert "_edit_form_sid" not in at.session_state, (
            "Sentinel must be cleared alongside selected_position_id"
        )

    def test_filter_change_after_selection_clears_selection(self, db):
        """F7 (Tier-4 full review) pin-down — PROTECTIVE behaviour regression
        guard.

        Naive mental model: selection is a positional row index, so a filter
        change that shuffles which position lives at row 0 would silently
        rebind selected_position_id to a different position's id.

        Observed behaviour (probed in review): when a filter widget change
        triggers the rerun, Streamlit resets the dataframe's selection
        state to {'rows': []}. Our line 176–185 else-branch then pops
        selected_position_id + _edit_form_sid. The user sees the edit
        panel disappear on filter change — a safe, surprising-but-defensible
        outcome (better than silent rebind to a wrong position).

        This test pins that protective behaviour so a future Streamlit
        release that changes the selection-on-data-change contract fails
        loudly here, and we notice before it becomes a data-correctness
        bug once Tier 5 Save wires up."""
        pid_alpha = database.add_position(
            {"position_name":  "Alpha",
             "status":         "[OPEN]",
             "deadline_date":  "2026-06-01"}
        )
        pid_beta = database.add_position(
            {"position_name":  "Beta",
             "status":         "[APPLIED]",
             "deadline_date":  "2026-05-01"}
        )
        at = AppTest.from_file(PAGE)
        at.run()
        # get_all_positions orders deadline_date ASC NULLS LAST → Beta at row 0.
        _select_row(at, 0)
        assert at.session_state["selected_position_id"] == pid_beta, (
            f"Precondition: row 0 unfiltered must bind to Beta={pid_beta}; "
            f"got {at.session_state['selected_position_id']}"
        )
        # Filter to [OPEN] → Beta filtered out, Alpha is the only visible row.
        at.selectbox(key="filter_status").select("[OPEN]")
        at.run()
        assert not at.exception, f"Filter change raised: {at.exception}"
        # Key assertion: Streamlit cleared the dataframe selection on the
        # data change, so our page popped selected_position_id — NOT
        # silently rebound it to pid_alpha.
        assert "selected_position_id" not in at.session_state, (
            "Filter change after selection must clear selected_position_id "
            "(Streamlit resets dataframe selection when data changes + our "
            "else-branch pops). If this fails, Streamlit's protective "
            "reset may have changed — silent rebind to a different id "
            f"(expected Alpha={pid_alpha}) is a data-correctness risk at "
            f"Tier 5. Got: {at.session_state.get('selected_position_id')}"
        )
        assert "_edit_form_sid" not in at.session_state, (
            "Sentinel must be popped alongside selected_position_id to keep "
            "the pair invariant (F4 cleanup pairing)."
        )


# ── Edit-panel shell (T4-B) ───────────────────────────────────────────────────
# When a row is selected, the page renders a subheader + st.tabs(...) below
# the table. The tabs are empty in T4-B — T4-C–F fill the bodies.

class TestEditPanelShell:

    def test_no_tabs_when_no_selection(self, db):
        """Tabs must not render unless a row is selected."""
        database.add_position({"position_name": "Alpha"})
        at = _run_page()
        assert len(at.tabs) == 0, (
            f"Expected 0 tabs without selection, got {len(at.tabs)}"
        )

    def test_no_subheader_when_no_selection(self, db):
        """Subheader (position_name · status) must not render without selection."""
        database.add_position({"position_name": "Alpha"})
        at = _run_page()
        assert len(at.subheader) == 0, (
            f"Expected 0 subheaders without selection, got {len(at.subheader)}"
        )

    def test_four_tabs_appear_when_row_selected(self, db):
        """Selecting a row must render exactly 4 tabs (Overview / Req / Mat / Notes)."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert not at.exception, f"Page raised after selection: {at.exception}"
        assert len(at.tabs) == 4, (
            f"Expected 4 tabs after selection, got {len(at.tabs)}"
        )

    def test_tab_labels_match_config(self, db):
        """Tab labels must come from config.EDIT_PANEL_TABS (proves config-drive)."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        labels = [t.label for t in at.tabs]
        assert labels == config.EDIT_PANEL_TABS, (
            f"Tab labels must match config.EDIT_PANEL_TABS.\n"
            f"  Expected: {config.EDIT_PANEL_TABS}\n"
            f"  Got:      {labels}"
        )

    def test_tabs_disappear_when_deselected(self, db):
        """Deselecting the row must unrender the edit panel (tabs + subheader)."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert len(at.tabs) == 4   # precondition
        _deselect_row(at)
        assert len(at.tabs) == 0, (
            "Deselection should unrender tabs"
        )
        assert len(at.subheader) == 0, (
            "Deselection should unrender the subheader"
        )

    def test_subheader_shows_position_name_and_status(self, db):
        """The subheader must confirm what's being edited — position name + status."""
        database.add_position(
            {"position_name": "Stanford BioStats", "status": "[APPLIED]"}
        )
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert len(at.subheader) == 1, (
            f"Expected exactly 1 subheader after selection, got {len(at.subheader)}"
        )
        text = at.subheader[0].value
        assert "Stanford BioStats" in text, (
            f"Subheader missing position name: {text!r}"
        )
        assert "[APPLIED]" in text, (
            f"Subheader missing status: {text!r}"
        )

    def test_stale_sid_is_cleared_silently(self, db):
        """Regression guard for Tier-4 review F3: if selected_position_id
        points to a row that's no longer in df (deleted elsewhere, external
        DB edit), both the sid and the _edit_form_sid sentinel must be
        cleared on the next rerun so state doesn't leak forever."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        # Inject a sid that doesn't exist in the DB.
        at.session_state["selected_position_id"] = 99999
        at.session_state["_edit_form_sid"] = 99999
        # Also wipe the dataframe widget's own selection so the page doesn't
        # re-derive selected_position_id from the row-0 click on this rerun.
        at.session_state[TABLE_KEY] = {"selection": {"rows": [], "columns": []}}
        at.run()
        assert not at.exception, f"Page raised on stale sid: {at.exception}"
        assert "selected_position_id" not in at.session_state, (
            "Stale sid must be cleared when the row is absent from df"
        )
        assert "_edit_form_sid" not in at.session_state, (
            "Sentinel must be cleared alongside the stale sid"
        )
        assert len(at.tabs) == 0, "Edit panel must not render for a stale sid"


# ── Overview tab widgets (T4-C) ───────────────────────────────────────────────
# The Overview tab holds editable widgets pre-filled from the selected row.
# Widgets live inside st.form("edit_overview") so edits don't save on keystroke
# — T5 adds the real save action; a disabled submit button is the placeholder.
#
# Widget key contract (page ↔ tests): keep these prefixed with "edit_" so they
# never collide with the quick-add "qa_*" keys.

EDIT_KEYS = {
    "position_name": "edit_position_name",
    "institute":     "edit_institute",
    "field":         "edit_field",
    "priority":      "edit_priority",
    "status":        "edit_status",
    "deadline_date": "edit_deadline_date",
    "link":          "edit_link",
}


class TestOverviewTabWidgets:

    def test_no_overview_widgets_without_selection(self, db):
        """None of the edit_* widgets must render before a row is selected."""
        database.add_position({"position_name": "Alpha"})
        at = _run_page()
        for k in EDIT_KEYS.values():
            assert k not in at.session_state, (
                f"Widget {k!r} should not exist before a row is selected"
            )

    def test_all_seven_widgets_present_when_selected(self, db):
        """All seven Overview widgets must render with the correct keys."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        # Text inputs
        text_keys = [at.text_input(key=EDIT_KEYS[f]) for f in
                     ("position_name", "institute", "field", "link")]
        assert all(w is not None for w in text_keys), (
            "Expected 4 text_input widgets (position_name, institute, field, link)"
        )
        # Selectboxes
        assert at.selectbox(key=EDIT_KEYS["priority"]) is not None
        assert at.selectbox(key=EDIT_KEYS["status"]) is not None
        # Date input
        assert at.date_input(key=EDIT_KEYS["deadline_date"]) is not None

    def test_widget_values_match_selected_row(self, db):
        """Each widget must pre-fill from the selected row's DB values."""
        database.add_position({
            "position_name": "Stanford BioStats",
            "institute":     "Stanford",
            "field":         "Biostatistics",
            "priority":      "High",
            "status":        "[APPLIED]",
            "deadline_date": "2026-12-01",
            "link":          "https://example.org/apply",
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert at.text_input(key=EDIT_KEYS["position_name"]).value == "Stanford BioStats"
        assert at.text_input(key=EDIT_KEYS["institute"]).value     == "Stanford"
        assert at.text_input(key=EDIT_KEYS["field"]).value         == "Biostatistics"
        assert at.selectbox(key=EDIT_KEYS["priority"]).value       == "High"
        assert at.selectbox(key=EDIT_KEYS["status"]).value         == "[APPLIED]"
        assert at.date_input(key=EDIT_KEYS["deadline_date"]).value == datetime.date(2026, 12, 1)
        assert at.text_input(key=EDIT_KEYS["link"]).value          == "https://example.org/apply"

    def test_status_selectbox_options_match_config(self, db):
        """Status selectbox must expose exactly config.STATUS_VALUES, same order."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        options = list(at.selectbox(key=EDIT_KEYS["status"]).options)
        assert options == config.STATUS_VALUES, (
            f"Status options must match config.STATUS_VALUES.\n"
            f"  Expected: {config.STATUS_VALUES}\n"
            f"  Got:      {options}"
        )

    def test_priority_selectbox_options_match_config(self, db):
        """Priority selectbox must expose exactly config.PRIORITY_VALUES, same order."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        options = list(at.selectbox(key=EDIT_KEYS["priority"]).options)
        assert options == config.PRIORITY_VALUES, (
            f"Priority options must match config.PRIORITY_VALUES.\n"
            f"  Expected: {config.PRIORITY_VALUES}\n"
            f"  Got:      {options}"
        )

    def test_selection_works_with_active_filter(self, db):
        """With a field filter already active, selecting a still-visible row
        must populate the edit panel with that row's values. This exercises
        the same property as 'filter preserves selection' via a path AppTest
        can actually drive (injected dataframe selection state does not
        survive a rerun triggered by a different widget)."""
        database.add_position({"position_name": "Alpha", "field": "Biostatistics"})
        database.add_position({"position_name": "Beta",  "field": "Machine Learning"})
        at = AppTest.from_file(PAGE)
        at.run()
        # Narrow the filter first so df_filtered has exactly one row (Alpha).
        at.text_input(key="filter_field").input("Bio")
        at.run()
        _select_row(at, 0)
        assert "selected_position_id" in at.session_state, (
            "Selecting row 0 of the filtered table must set selected_position_id"
        )
        assert at.text_input(key=EDIT_KEYS["position_name"]).value == "Alpha", (
            "Edit panel must load the filtered-and-selected row's values"
        )

    def test_widgets_handle_null_fields(self, db):
        """A row with NULL optional fields must not crash the form — empty
        strings for text, None for the date."""
        database.add_position({"position_name": "Alpha"})   # everything else default/NULL
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert not at.exception, f"Page crashed on row with NULLs: {at.exception}"
        assert at.text_input(key=EDIT_KEYS["institute"]).value == ""
        assert at.text_input(key=EDIT_KEYS["field"]).value     == ""
        assert at.text_input(key=EDIT_KEYS["link"]).value      == ""
        assert at.date_input(key=EDIT_KEYS["deadline_date"]).value is None

    def test_widgets_update_on_selection_change(self, db):
        """Selecting a different row must re-seed the widgets with that row's
        values. This is the widget-value trap: if session_state already holds a
        value for the key, Streamlit ignores `value=` on re-render, so the form
        would 'stick' on the first row. The page must pre-seed on selection
        change (tracked via an internal sentinel)."""
        # Insert in a known order — get_all_positions orders by updated_at DESC,
        # so the most-recently-added row lands at index 0.
        database.add_position({"position_name": "Alpha", "institute": "A-Inst"})
        database.add_position({"position_name": "Beta",  "institute": "B-Inst"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        first_name = at.text_input(key=EDIT_KEYS["position_name"]).value
        first_inst = at.text_input(key=EDIT_KEYS["institute"]).value
        # Select the other row.
        _select_row(at, 1)
        second_name = at.text_input(key=EDIT_KEYS["position_name"]).value
        second_inst = at.text_input(key=EDIT_KEYS["institute"]).value
        assert {first_name, second_name} == {"Alpha", "Beta"}, (
            f"Selection change must switch widget values; got {first_name!r} → {second_name!r}"
        )
        assert {first_inst, second_inst} == {"A-Inst", "B-Inst"}
        assert first_name != second_name, (
            "Widget did not update on selection change — classic value= trap"
        )

    def test_null_priority_falls_back_to_first_option(self, db):
        """Regression guard for Tier-4 review F2: a DB row with priority=NULL
        must not put None into the selectbox's session_state — today Streamlit
        tolerates an out-of-options value silently, but the tolerance is
        undocumented. Coerce to PRIORITY_VALUES[0] so the selectbox always
        gets a valid option."""
        database.add_position({"position_name": "Alpha"})   # priority omitted → NULL
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert not at.exception, f"Page raised on NULL priority: {at.exception}"
        assert at.selectbox(key=EDIT_KEYS["priority"]).value == config.PRIORITY_VALUES[0], (
            f"NULL priority must coerce to config.PRIORITY_VALUES[0] "
            f"(= {config.PRIORITY_VALUES[0]!r}); got "
            f"{at.selectbox(key=EDIT_KEYS['priority']).value!r}"
        )


# ── Requirements tab widgets (T4-D) ───────────────────────────────────────────
# The Requirements tab renders one st.radio per entry in
# config.REQUIREMENT_DOCS. Values are canonical DB strings ('Y', 'Optional',
# 'N'); labels come from config.REQUIREMENT_LABELS via format_func so
# session_state always holds the canonical value — no save-time translation.
#
# Widget key convention: "edit_" + req_col (e.g. "edit_req_cv").

def _req_key(req_col: str) -> str:
    """Return the session_state key for a given req_* column's radio widget."""
    return f"edit_{req_col}"


class TestRequirementsTabWidgets:

    def test_no_requirements_widgets_without_selection(self, db):
        """None of the edit_req_* keys must be seeded before a row is selected."""
        database.add_position({"position_name": "Alpha"})
        at = _run_page()
        for req_col, _done_col, _label in config.REQUIREMENT_DOCS:
            assert _req_key(req_col) not in at.session_state, (
                f"Widget {_req_key(req_col)!r} should not exist before selection"
            )

    def test_one_radio_per_requirement_doc(self, db):
        """Exactly one radio per REQUIREMENT_DOCS entry must render after selection."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert not at.exception, f"Page raised on selection: {at.exception}"
        for req_col, _done_col, _label in config.REQUIREMENT_DOCS:
            assert at.radio(key=_req_key(req_col)) is not None, (
                f"Missing radio for {req_col!r}"
            )
        # And the total radio count equals the config length — guards against
        # a stray hardcoded radio slipping in.
        assert len(at.radio) == len(config.REQUIREMENT_DOCS), (
            f"Expected {len(config.REQUIREMENT_DOCS)} radios, got {len(at.radio)}"
        )

    def test_radio_values_match_db(self, db):
        """Each radio must pre-fill from the selected row's req_* column value."""
        # Exercise all three vocabulary tiers so we catch one-way mappings.
        database.add_position({
            "position_name":        "Stanford BioStats",
            "req_cv":               "Y",
            "req_cover_letter":     "Y",
            "req_writing_sample":   "Optional",
            "req_teaching_statement": "N",
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert at.radio(key=_req_key("req_cv")).value             == "Y"
        assert at.radio(key=_req_key("req_cover_letter")).value   == "Y"
        assert at.radio(key=_req_key("req_writing_sample")).value == "Optional"
        assert at.radio(key=_req_key("req_teaching_statement")).value == "N"

    def test_radio_options_display_config_labels_in_order(self, db):
        """Every radio must expose the three tiers in config order, shown via
        config.REQUIREMENT_LABELS. AppTest surfaces `.options` as the
        formatted display strings (not the canonical values), so this is the
        observable side of the canonical-value contract; the canonical-value
        half is covered by test_radio_values_match_db."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        expected_labels = [config.REQUIREMENT_LABELS[v]
                           for v in config.REQUIREMENT_VALUES]
        for req_col, _done_col, _label in config.REQUIREMENT_DOCS:
            options = list(at.radio(key=_req_key(req_col)).options)
            assert options == expected_labels, (
                f"Radio {req_col!r} options must match "
                f"[REQUIREMENT_LABELS[v] for v in REQUIREMENT_VALUES].\n"
                f"  Expected: {expected_labels}\n"
                f"  Got:      {options}"
            )

    def test_null_req_falls_back_to_N(self, db):
        """Defensive coercion (F2 analog): an unknown or None req_* value
        must not crash the page and must not put an out-of-options value
        into the radio's session_state — fall back to 'N' (schema default)."""
        database.add_position({"position_name": "Alpha"})  # req_* defaults → 'N'
        # Manually corrupt one req_* column to simulate an unknown value
        # (e.g. from a future migration or sqlite3 CLI edit).
        import sqlite3
        with sqlite3.connect(database.DB_PATH) as conn:
            conn.execute(
                "UPDATE positions SET req_cv = 'Maybe' WHERE position_name = ?",
                ("Alpha",),
            )
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert not at.exception, f"Page raised on unknown req_* value: {at.exception}"
        assert at.radio(key=_req_key("req_cv")).value == "N", (
            "Unknown req_* value must coerce to 'N' (schema default), "
            f"got {at.radio(key=_req_key('req_cv')).value!r}"
        )

    def test_widgets_update_on_selection_change(self, db):
        """Widget-value-trap regression guard on the req_* path: switching
        rows must re-seed the req_* widgets, not stick on the first."""
        database.add_position({"position_name": "Alpha", "req_cv": "Y"})
        database.add_position({"position_name": "Beta",  "req_cv": "N"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        first = at.radio(key=_req_key("req_cv")).value
        _select_row(at, 1)
        second = at.radio(key=_req_key("req_cv")).value
        assert {first, second} == {"Y", "N"}, (
            f"Selection change must re-seed req_cv; got {first!r} → {second!r}"
        )
        assert first != second, (
            "req_cv did not update on selection change — widget-value trap"
        )

    def test_config_driven_new_doc_renders_new_widget(self, db, monkeypatch):
        """The core config-drive proof: appending a new tuple to
        config.REQUIREMENT_DOCS (and re-running init_db to add the column)
        must make a new radio appear automatically, with no page-file change."""
        new_docs = config.REQUIREMENT_DOCS + [
            ("req_portfolio", "done_portfolio", "Portfolio"),
        ]
        monkeypatch.setattr(config, "REQUIREMENT_DOCS", new_docs)
        # init_db is migration-aware: ALTER TABLE ADD COLUMN for the new doc.
        database.init_db()
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert not at.exception, f"Page raised with extended config: {at.exception}"
        assert at.radio(key=_req_key("req_portfolio")) is not None, (
            "Adding a new doc to config.REQUIREMENT_DOCS must render a new "
            "radio automatically — this proves the page is config-driven, "
            "not hardcoded. If this fails, the page loops over a local "
            "constant instead of config.REQUIREMENT_DOCS."
        )
        # The new widget must participate in the same options contract as
        # the others — AppTest surfaces .options as display labels, so the
        # expected list is REQUIREMENT_LABELS[v] for v in REQUIREMENT_VALUES.
        expected_labels = [config.REQUIREMENT_LABELS[v]
                           for v in config.REQUIREMENT_VALUES]
        assert list(at.radio(key=_req_key("req_portfolio")).options) \
            == expected_labels
        # And its default value (from the migration's DEFAULT 'N') should
        # land in session_state as 'N' after the pre-seed coercion — this
        # IS the canonical-value half of the contract.
        assert at.radio(key=_req_key("req_portfolio")).value == "N"


# ── Materials tab widgets (T4-E) ──────────────────────────────────────────────
# The Materials tab is state-driven: it renders one st.checkbox per done_*
# column ONLY for documents whose req_* is 'Y' (matching the readiness
# definition in database.py ~line 404 — "A position is 'ready' if every
# document where req_* = 'Y' has done_* = 1"). The source of truth for
# "is this required?" is session_state["edit_{req_col}"], not the raw DB
# value, so a user toggling a Requirements-tab radio sees the Materials
# tab update on the next rerun.
#
# Widget key convention: "edit_" + done_col (e.g. "edit_done_cv"), mirroring
# the edit_req_* keys from T4-D.

def _done_key(done_col: str) -> str:
    """Return the session_state key for a given done_* column's checkbox."""
    return f"edit_{done_col}"


def _checkbox_rendered(at: AppTest, key: str) -> bool:
    """True iff a checkbox with the given key is present on the rendered page.

    AppTest's `at.checkbox(key=...)` raises KeyError when no match exists, so
    checking 'is this widget rendered?' needs to catch that. We cannot use
    'key in session_state' as a proxy because the pre-seed populates
    edit_done_* unconditionally (so 'user toggles req include mid-edit'
    doesn't flash an unseeded checkbox)."""
    try:
        at.checkbox(key=key)
        return True
    except KeyError:
        return False


class TestMaterialsTabWidgets:

    def test_no_materials_widgets_without_selection(self, db):
        """No done_* checkbox may render before a row is selected."""
        database.add_position({"position_name": "Alpha", "req_cv": "Y"})
        at = _run_page()
        assert len(at.checkbox) == 0, (
            f"Expected 0 checkboxes before selection, got {len(at.checkbox)}"
        )

    def test_empty_state_when_no_required_docs(self, db):
        """With all req_* = 'N' (the schema default), the Materials tab must
        show an info hint directing the user to the Requirements tab — rendering
        zero checkboxes would be a silent dead-end UI."""
        database.add_position({"position_name": "Alpha"})   # all req_* default 'N'
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        # No done_* checkboxes must render.
        assert len(at.checkbox) == 0, (
            f"With all req_* = 'N', no Materials checkboxes should render; "
            f"got {len(at.checkbox)}"
        )
        # An info hint must be present — substring match on "Requirements tab"
        # so the exact wording can evolve without churning the test.
        info_texts = [el.value for el in at.info]
        assert any("Requirements tab" in t for t in info_texts), (
            f"Expected a Materials empty-state hint pointing to the "
            f"Requirements tab; got info elements: {info_texts}"
        )

    def test_only_required_doc_checkboxes_shown(self, db):
        """With req_cv='Y' and everything else 'N', exactly one checkbox
        (done_cv) must render — not zero, not len(REQUIREMENT_DOCS)."""
        database.add_position({"position_name": "Alpha", "req_cv": "Y"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        # done_cv is the only one required → exactly one checkbox rendered.
        assert _checkbox_rendered(at, _done_key("done_cv")), (
            "done_cv checkbox must render when req_cv == 'Y'"
        )
        for _req_col, done_col, _label in config.REQUIREMENT_DOCS:
            if done_col == "done_cv":
                continue
            assert not _checkbox_rendered(at, _done_key(done_col)), (
                f"{done_col} checkbox should be hidden when its req_* is 'N'"
            )
        # Tight bound: no other page checkboxes exist today.
        assert len(at.checkbox) == 1, (
            f"Expected 1 Materials checkbox, got {len(at.checkbox)}"
        )

    def test_checkbox_initial_state_matches_db(self, db):
        """Pre-seed must translate done_* INTEGER (0/1) to bool correctly."""
        database.add_position({
            "position_name":   "Stanford BioStats",
            "req_cv":          "Y",
            "done_cv":          1,
            "req_cover_letter": "Y",
            "done_cover_letter": 0,
            "req_transcripts":  "Y",
            # done_transcripts omitted → schema default 0
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        # Use == (not `is`) because pandas surfaces numpy booleans
        # (numpy.bool_), and `np.True_ is True` is False.
        assert bool(at.checkbox(key=_done_key("done_cv")).value)          is True
        assert bool(at.checkbox(key=_done_key("done_cover_letter")).value) is False
        assert bool(at.checkbox(key=_done_key("done_transcripts")).value) is False

    def test_toggling_requirement_hides_checkbox(self, db):
        """State-driven behaviour: when the user flips req_cv from 'Y' to 'N'
        on the Requirements tab, the done_cv checkbox on the Materials tab
        must disappear on the next rerun.

        We drive this via session_state["edit_req_cv"] rather than a raw DB
        update because the source of truth for 'is this required?' is the
        live widget state (_edit_form_sid only reseeds on selection change
        — a DB-only update would not re-trigger the pre-seed). This is the
        faithful test of state-driven design."""
        database.add_position({"position_name": "Alpha", "req_cv": "Y"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert _checkbox_rendered(at, _done_key("done_cv"))   # precondition
        # Simulate the user flipping the req_cv radio to "Not needed".
        at.session_state["edit_req_cv"] = "N"
        at.run()
        assert not at.exception, f"Page raised on req toggle: {at.exception}"
        assert not _checkbox_rendered(at, _done_key("done_cv")), (
            "Toggling edit_req_cv → 'N' must hide the done_cv checkbox"
        )

    def test_optional_docs_are_hidden(self, db):
        """Pins the Y-only filter choice: 'Optional' docs are NOT shown in
        Materials. If the product later decides Optional should participate
        in the readiness view, this test will fail loudly and force an
        explicit re-evaluation (alongside the matching change in
        database.count_materials_ready / get_positions_missing_docs)."""
        database.add_position({"position_name": "Alpha", "req_cv": "Optional"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert not _checkbox_rendered(at, _done_key("done_cv")), (
            "'Optional' docs must be hidden from Materials (Y-only filter "
            "matches the readiness definition in database.py)"
        )

    def test_checkboxes_update_on_selection_change(self, db):
        """Widget-value-trap regression guard on the done_* path: selecting a
        different row must re-seed the done_* widgets with that row's values."""
        database.add_position({"position_name": "Alpha",
                               "req_cv": "Y", "done_cv": 1})
        database.add_position({"position_name": "Beta",
                               "req_cv": "Y", "done_cv": 0})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        # bool() normalises numpy.bool_ → Python bool so set equality works.
        first = bool(at.checkbox(key=_done_key("done_cv")).value)
        _select_row(at, 1)
        second = bool(at.checkbox(key=_done_key("done_cv")).value)
        assert {first, second} == {True, False}, (
            f"Selection change must re-seed done_cv; got {first!r} → {second!r}"
        )
        assert first != second, (
            "done_cv did not update on selection change — widget-value trap"
        )


# ═══════════════════════════════════════════════════════════════════════════
# T4-F — Notes tab
# ═══════════════════════════════════════════════════════════════════════════
# Widget key: "edit_notes" (session_state) on a single st.text_area inside an
# st.form("edit_notes"). Pre-seeded from positions.notes via the same
# _edit_form_sid-gated block as the other tabs.

NOTES_KEY = "edit_notes"


def _text_area_rendered(at: AppTest, key: str) -> bool:
    """True iff a text_area with the given key is present on the rendered page.

    Mirrors `_checkbox_rendered`: AppTest raises KeyError when no match
    exists, so we can't probe with `key in session_state` (pre-seed may have
    populated the slot even when the widget is not currently drawn)."""
    try:
        at.text_area(key=key)
        return True
    except KeyError:
        return False


class TestNotesTabWidgets:

    def test_no_text_area_without_selection(self, db):
        """No Notes text_area may render before a row is selected — the edit
        panel (and everything in it) is gated by selected_position_id."""
        database.add_position({"position_name": "Alpha"})
        at = _run_page()
        assert not _text_area_rendered(at, NOTES_KEY), (
            "edit_notes text_area must not render before row selection"
        )

    def test_text_area_renders_when_row_selected(self, db):
        """Baseline positive contract: selecting a row must produce exactly
        one text_area with key=edit_notes on the page."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert _text_area_rendered(at, NOTES_KEY), (
            "Notes tab must render a text_area keyed edit_notes after selection"
        )
        # Tight bound: no other page text_area exists today. If a future tier
        # adds more, update this count explicitly rather than loosening it.
        assert len(at.text_area) == 1, (
            f"Expected 1 text_area on the page, got {len(at.text_area)}"
        )

    def test_text_area_preseeded_from_db(self, db):
        """Pre-seed must copy positions.notes into session_state verbatim,
        so the widget displays the saved notes without the user clicking
        'edit'."""
        notes = "Follow up with Prof. Smith after SfN. Ref: lab website."
        database.add_position({"position_name": "Alpha", "notes": notes})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert at.text_area(key=NOTES_KEY).value == notes, (
            f"Expected edit_notes pre-seeded to {notes!r}, "
            f"got {at.text_area(key=NOTES_KEY).value!r}"
        )

    def test_null_notes_coerced_to_empty_string(self, db):
        """positions.notes is nullable (TEXT without NOT NULL); a NULL value
        must coerce to '' so st.text_area gets a valid str, never a None
        that would crash the widget or render literal 'None'."""
        database.add_position({"position_name": "Alpha"})   # notes omitted → NULL
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert at.text_area(key=NOTES_KEY).value == "", (
            f"NULL notes must coerce to empty string, got "
            f"{at.text_area(key=NOTES_KEY).value!r}"
        )

    def test_notes_reseed_on_selection_change(self, db):
        """Widget-value-trap regression guard: once session_state['edit_notes']
        is set, Streamlit ignores the `value=` kwarg on later reruns. The
        _edit_form_sid sentinel must force a re-seed when the user selects a
        different row — otherwise row B's notes would show row A's text."""
        database.add_position({"position_name": "Alpha", "notes": "alpha notes"})
        database.add_position({"position_name": "Beta",  "notes": "beta notes"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        first = at.text_area(key=NOTES_KEY).value
        _select_row(at, 1)
        second = at.text_area(key=NOTES_KEY).value
        assert first == "alpha notes", f"Row 0 notes mis-seeded: {first!r}"
        assert second == "beta notes", (
            f"Row 1 notes did not re-seed on selection change — "
            f"widget-value trap. Got {second!r}"
        )

    def test_unwired_save_buttons_still_disabled(self, db):
        """The Notes save button must remain disabled with the Tier-5 tooltip
        until T5-D wires it. Catches accidental enabling before the Notes
        write lands.

        T5-A enabled Overview. T5-B enabled Requirements. With all req_* = 'N',
        Materials renders no form → Notes is the only disabled form submit
        on the page (>= 1). Assertion relaxed accordingly; the tooltip check
        still pins every remaining disabled placeholder."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        disabled = [b for b in at.button if getattr(b, "disabled", False)]
        assert len(disabled) >= 1, (
            f"Expected at least 1 disabled Save button (Notes), "
            f"got {len(disabled)}"
        )
        # The Tier-5 tooltip must appear on every disabled placeholder.
        for b in disabled:
            assert "Tier 5" in (b.help or ""), (
                f"Disabled Save button missing Tier-5 tooltip: help={b.help!r}"
            )


# ── Overview tab Save (T5-A) ──────────────────────────────────────────────────
# The Overview form persists its 7 fields via database.update_position. Save is
# per-tab (four independent submit buttons, one per tab) so the user can revise
# and save in isolation; DESIGN.md §6 wireframe.
#
# Contract pinned here:
#   • All 7 edited fields round-trip through update_position to the DB row.
#   • Success → st.toast (survives the post-save rerun, unlike st.success).
#   • Whitespace-only position_name blocked with st.error, no DB write.
#   • Any exception from update_position surfaces as a friendly st.error
#     without Streamlit rendering the traceback (F1 / GUIDELINES §8).
#   • The selection (selected_position_id) survives the save → rerun so the
#     edit panel re-renders for the same position instead of collapsing.
#
# Widget key for the submit button is part of the page's test contract —
# do not rename without updating OVERVIEW_SUBMIT_KEY below.

OVERVIEW_SUBMIT_KEY = "edit_overview_submit"


def _keep_selection(at: AppTest, row_index: int) -> None:
    """Re-inject the positions_table selection state before the next at.run().

    AppTest treats the dataframe's on_select='rerun' event as a single-run
    signal: the injected `positions_table` session_state does NOT persist
    across reruns. In a real browser the user's click is remembered in
    widget session_state naturally. Multi-step tests that span a rerun
    must re-assert the selection to mimic that browser-side persistence."""
    at.session_state[TABLE_KEY] = {
        "selection": {"rows": [row_index], "columns": []}
    }


class TestOverviewSave:

    def test_save_persists_all_seven_fields(self, db):
        """Round-trip: edit every Overview widget, click Save, assert the DB
        row reflects every new value. Guards against a field being added to
        the form but forgotten in the update_position payload."""
        database.add_position({
            "position_name": "Original Name",
            "institute":     "Original Inst",
            "field":         "Original Field",
            "priority":      "Medium",
            "status":        "[OPEN]",
            "deadline_date": "2026-01-01",
            "link":          "https://old.example",
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        sid = at.session_state["selected_position_id"]

        # Edit every field.
        at.text_input(key=EDIT_KEYS["position_name"]).set_value("New Name")
        at.text_input(key=EDIT_KEYS["institute"]).set_value("New Inst")
        at.text_input(key=EDIT_KEYS["field"]).set_value("New Field")
        at.selectbox(key=EDIT_KEYS["priority"]).set_value("High")
        at.selectbox(key=EDIT_KEYS["status"]).set_value("[APPLIED]")
        at.date_input(key=EDIT_KEYS["deadline_date"]).set_value(
            datetime.date(2026, 9, 15)
        )
        at.text_input(key=EDIT_KEYS["link"]).set_value("https://new.example")

        at.button(key=OVERVIEW_SUBMIT_KEY).click()
        _keep_selection(at, 0)   # mimic browser-side selection persistence
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        row = database.get_position(sid)
        assert row["position_name"] == "New Name"
        assert row["institute"]     == "New Inst"
        assert row["field"]         == "New Field"
        assert row["priority"]      == "High"
        assert row["status"]        == "[APPLIED]"
        assert row["deadline_date"] == "2026-09-15"
        assert row["link"]          == "https://new.example"

    def test_save_shows_toast_on_success(self, db):
        """Success confirmation uses st.toast (not st.success) so it survives
        the post-save st.rerun() — the same Tier-1 lesson as quick-add."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        at.text_input(key=EDIT_KEYS["institute"]).set_value("MIT")
        at.button(key=OVERVIEW_SUBMIT_KEY).click()
        _keep_selection(at, 0)   # mimic browser-side selection persistence
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        assert at.toast, "Expected st.toast after a successful Overview save"
        assert any("Alpha" in el.value for el in at.toast), (
            f"Toast should reference the position name; got "
            f"{[el.value for el in at.toast]}"
        )

    def test_save_toast_survives_rerun(self, db):
        """Explicit regression guard for the Tier-1 st.success-clobber bug:
        AppTest captures the LAST script run. After save+rerun, st.toast must
        still appear. st.success would be gone here — the whole reason we use
        toast on write paths."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        at.text_input(key=EDIT_KEYS["field"]).set_value("Biostatistics")
        at.button(key=OVERVIEW_SUBMIT_KEY).click()
        _keep_selection(at, 0)   # mimic browser-side selection persistence
        at.run()

        # at.toast populated → the post-rerun script run still rendered it.
        assert at.toast, (
            "Toast should survive the post-save rerun. If this fails, check "
            "that the success path uses st.toast, not st.success."
        )
        # And no st.success from the save handler — that would be a silent
        # regression back to the rerun-clobbered pattern.
        success_texts = [el.value for el in at.success]
        assert not any("Saved" in t or "saved" in t for t in success_texts), (
            f"Save handler must use st.toast, not st.success; got "
            f"st.success messages: {success_texts}"
        )

    def test_save_whitespace_only_name_blocked(self, db):
        """Whitespace-only position_name must be rejected with st.error and
        must not write to the DB — mirrors the quick-add contract (F3) so
        the same invariant holds for edits."""
        database.add_position({
            "position_name": "Original Name",
            "institute":     "Original Inst",
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        sid = at.session_state["selected_position_id"]
        at.text_input(key=EDIT_KEYS["position_name"]).set_value("   ")
        at.button(key=OVERVIEW_SUBMIT_KEY).click()
        _keep_selection(at, 0)   # mimic browser-side selection persistence
        at.run()

        assert at.error, "Expected st.error for whitespace-only position_name"
        # DB unchanged.
        row = database.get_position(sid)
        assert row["position_name"] == "Original Name", (
            f"DB must not be updated on validation failure; got "
            f"position_name={row['position_name']!r}"
        )
        assert row["institute"] == "Original Inst"
        # And no toast — success path must not fire on a validation error.
        assert not at.toast, (
            f"No toast should appear when save is blocked by validation; "
            f"got {[el.value for el in at.toast]}"
        )

    def test_save_db_failure_shows_error_no_traceback(self, db, monkeypatch):
        """Mirror of the Tier-4 F1 regression guard (quick-add path) on the
        save path: when database.update_position raises, the page must show
        a friendly st.error and NOT re-raise. The previous quick-add
        implementation did `raise` after st.error, which made Streamlit
        render the very traceback the handler existed to prevent."""
        database.add_position({"position_name": "Alpha"})

        def _boom(_position_id, _fields):
            raise RuntimeError("db unavailable")
        monkeypatch.setattr(database, "update_position", _boom)

        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        at.text_input(key=EDIT_KEYS["institute"]).set_value("MIT")
        at.button(key=OVERVIEW_SUBMIT_KEY).click()
        _keep_selection(at, 0)   # mimic browser-side selection persistence
        at.run()

        assert at.error, "Expected st.error when update_position raises"
        assert any("Could not save" in el.value for el in at.error), (
            f"Expected 'Could not save' prefix in error, got: "
            f"{[el.value for el in at.error]}"
        )
        assert not at.exception, (
            f"Save handler must swallow the exception after st.error; "
            f"got uncaught: {at.exception}"
        )
        # And no success toast on the failure path.
        assert not at.toast, (
            f"No toast should appear on save failure; got "
            f"{[el.value for el in at.toast]}"
        )

    def test_save_preserves_selection_across_rerun(self, db):
        """After save, the edit panel must re-render for the SAME position —
        selected_position_id must survive the post-save st.rerun(), and the
        Overview widgets must still be on the page. Guards against a Tier-5
        implementation that accidentally pops the selection (as the
        quick-add path deliberately does, but for a different reason)."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        sid_before = at.session_state["selected_position_id"]
        at.text_input(key=EDIT_KEYS["institute"]).set_value("MIT")
        at.button(key=OVERVIEW_SUBMIT_KEY).click()
        _keep_selection(at, 0)   # mimic browser-side selection persistence
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        assert "selected_position_id" in at.session_state, (
            "Selection must survive the post-save rerun — without it the "
            "edit panel collapses and the user loses context."
        )
        assert at.session_state["selected_position_id"] == sid_before, (
            f"Selected id drifted across rerun: {sid_before} → "
            f"{at.session_state['selected_position_id']}"
        )
        # Edit panel is still rendered (Overview widgets present).
        assert at.text_input(key=EDIT_KEYS["position_name"]) is not None
        # And the displayed institute reflects the persisted value.
        assert at.text_input(key=EDIT_KEYS["institute"]).value == "MIT", (
            "Post-save widget value must reflect the saved state, not the "
            "pre-edit value. If this fails, the sentinel may be stuck on "
            "the pre-save render cycle."
        )


# ── Requirements tab Save (T5-B) ──────────────────────────────────────────────
# The Requirements form persists all req_* columns via database.update_position.
# Critical contract: Requirements Save NEVER writes done_* columns. The payload
# is built from config.REQUIREMENT_DOCS → req_col only, so update_position's
# parameterised UPDATE leaves the done_* columns of the row untouched. Flipping
# req_cv from 'Y' to 'N' preserves done_cv — the user's "I've prepared the CV"
# status is independent of whether any given position requires it right now.
# DESIGN.md §6: Materials is checkbox-only; the readiness computation hides
# rows where req_* != 'Y' but the underlying value is preserved.

REQUIREMENTS_SUBMIT_KEY = "edit_requirements_submit"


class TestRequirementsSave:

    def test_save_persists_all_req_columns(self, db):
        """Round-trip: set every req_* radio to a mix of values, click Save,
        assert every req_* in the DB matches. Guards against a req column
        being added to the form but forgotten in the update_position payload.
        Also verifies the success toast fires with the position name."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        sid = at.session_state["selected_position_id"]

        # Set each req_* to a value drawn from config.REQUIREMENT_VALUES,
        # cycling through Y/Optional/N so every vocabulary tier is written
        # at least once on a large-enough REQUIREMENT_DOCS list.
        chosen = {}
        for idx, (req_col, _done_col, _label) in enumerate(config.REQUIREMENT_DOCS):
            value = config.REQUIREMENT_VALUES[idx % len(config.REQUIREMENT_VALUES)]
            at.radio(key=_req_key(req_col)).set_value(value)
            chosen[req_col] = value

        at.button(key=REQUIREMENTS_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        row = database.get_position(sid)
        for req_col, expected in chosen.items():
            assert row[req_col] == expected, (
                f"{req_col} should be {expected!r}, got {row[req_col]!r}"
            )
        assert at.toast, "Expected st.toast after a successful Requirements save"
        assert any("Alpha" in el.value for el in at.toast), (
            f"Toast should reference the position name; got "
            f"{[el.value for el in at.toast]}"
        )

    def test_save_preserves_done_fields_on_req_flip(self, db):
        """Critical contract pin: Requirements Save must NOT touch done_*
        columns. The user's "I've prepared the CV" status is independent of
        whether any given position currently requires a CV. Flipping
        req_cv from 'Y' → 'N' and saving MUST leave done_cv == 1 in the DB.

        Rationale (DESIGN.md + user decision 2026-04-20): if req_cv later
        flips back to 'Y', the Materials tab should again show 'CV: done'
        without the user having to re-tick — the CV didn't un-prepare itself."""
        database.add_position({
            "position_name": "Alpha",
            "req_cv":        "Y",
            "done_cv":       1,
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        sid = at.session_state["selected_position_id"]

        # Flip req_cv to N.
        at.radio(key=_req_key("req_cv")).set_value("N")
        at.button(key=REQUIREMENTS_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        row = database.get_position(sid)
        assert row["req_cv"] == "N", (
            f"req_cv should have flipped to 'N', got {row['req_cv']!r}"
        )
        assert row["done_cv"] == 1, (
            f"done_cv MUST be preserved across a req flip (user-confirmed "
            f"contract 2026-04-20); got {row['done_cv']!r}. If this fails, "
            f"the Requirements-save payload is writing done_* columns — it "
            f"must contain only req_* keys."
        )

    def test_save_db_failure_shows_error_no_traceback(self, db, monkeypatch):
        """Mirror T5-A / Tier-4 F1 on the Requirements path: a raising
        update_position must surface a friendly st.error without re-raising."""
        database.add_position({"position_name": "Alpha"})

        def _boom(_position_id, _fields):
            raise RuntimeError("db unavailable")
        monkeypatch.setattr(database, "update_position", _boom)

        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        at.radio(key=_req_key("req_cv")).set_value("Y")
        at.button(key=REQUIREMENTS_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert at.error, "Expected st.error when update_position raises"
        assert any("Could not save" in el.value for el in at.error), (
            f"Expected 'Could not save' prefix in error, got: "
            f"{[el.value for el in at.error]}"
        )
        assert not at.exception, (
            f"Save handler must swallow the exception after st.error; "
            f"got uncaught: {at.exception}"
        )
        assert not at.toast, (
            f"No toast should appear on save failure; got "
            f"{[el.value for el in at.toast]}"
        )

    def test_save_preserves_selection_across_rerun(self, db):
        """After Requirements save, the edit panel must re-render for the
        SAME position — selected_position_id must survive the post-save
        st.rerun() (via the T5-A _skip_table_reset one-shot)."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        sid_before = at.session_state["selected_position_id"]
        at.radio(key=_req_key("req_cv")).set_value("Y")
        at.button(key=REQUIREMENTS_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        assert "selected_position_id" in at.session_state, (
            "Selection must survive the post-save rerun — without it the "
            "edit panel collapses and the user loses context."
        )
        assert at.session_state["selected_position_id"] == sid_before, (
            f"Selected id drifted across rerun: {sid_before} → "
            f"{at.session_state['selected_position_id']}"
        )
        # Panel still rendered: the Requirements radio is still there.
        assert at.radio(key=_req_key("req_cv")) is not None

    def test_save_toast_survives_rerun(self, db):
        """Regression guard for the Tier-1 st.success-clobber bug on the
        Requirements path: st.toast must still be in at.toast after the
        post-save rerun completes."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        at.radio(key=_req_key("req_cv")).set_value("Y")
        at.button(key=REQUIREMENTS_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert at.toast, (
            "Toast should survive the post-save rerun. If this fails, check "
            "that the success path uses st.toast, not st.success."
        )
        success_texts = [el.value for el in at.success]
        assert not any("Saved" in t or "saved" in t for t in success_texts), (
            f"Requirements save must use st.toast, not st.success; got "
            f"st.success messages: {success_texts}"
        )
