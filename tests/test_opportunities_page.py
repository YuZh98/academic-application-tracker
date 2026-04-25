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
        # Contract 3: no success toast on the failure path. Mirrors all
        # four Tier-5 _db_failure_shows_error_no_traceback tests so the
        # success-path / failure-path split is symmetric across every
        # write handler on the page.
        assert not at.toast, (
            f"No success toast may appear when add_position raises; got "
            f"{[el.value for el in at.toast]}"
        )

    def test_submit_with_whitespace_only_name_shows_error(self, db):
        """Whitespace-only position_name must be treated as empty (F3 fix).

        Before the fix, `not "   "` evaluates to False so the insert ran.
        After stripping, `not "   ".strip()` is True and the error fires.
        The `not at.toast` check mirrors the Tier-5 save-validation tests
        (test_save_whitespace_only_name_blocked) so the contract holds at
        both ends: a validation failure NEVER fires the success toast."""
        at = _run_page()
        at.text_input(key="qa_position_name").input("   ")
        at.button(key=SUBMIT_KEY).click()
        at.run()
        assert at.error, "Expected st.error for whitespace-only position_name"
        assert database.get_all_positions().empty, (
            "No row should be inserted for whitespace-only position_name"
        )
        assert not at.toast, (
            f"No success toast may appear when validation rejects the input; "
            f"got {[el.value for el in at.toast]}"
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
        """Positions added via quick-add must default to STATUS_VALUES[0] ('[SAVED]')."""
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
        database.add_position({"position_name": "A"})                          # [SAVED] by default
        database.add_position({"position_name": "B"})                          # [SAVED] by default
        database.add_position({"position_name": "C", "status": "[APPLIED]"})
        at = _run_page()
        at.selectbox(key="filter_status").select("[SAVED]")
        at.run()
        assert not at.exception
        assert len(at.dataframe) == 1
        assert len(at.dataframe[0].value) == 2, (
            f"Expected 2 rows after status=[SAVED] filter, got {len(at.dataframe[0].value)}"
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
        """Status filter must offer 'All' plus an entry per config.STATUS_VALUES,
        exposed via format_func=STATUS_LABELS.get (Sub-task 13 / DESIGN §8.0)
        so the rendered options are display labels while the underlying raw
        values drive the filter predicate. Options list returned by AppTest
        is the post-format_func display strings."""
        at = _run_page()
        actual = list(at.selectbox(key="filter_status").options)
        expected = ["All"] + [config.STATUS_LABELS[v] for v in config.STATUS_VALUES]
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
        """Selecting a specific status must hide positions with other statuses,
        AND the surviving row must be the one whose status matches — not the
        opposite-status row. The count assertion alone would survive a
        match/no-match swap; the row-identity assertion pins which row was
        actually retained."""
        database.add_position({"position_name": "Open One"})                          # status defaults to [SAVED]
        database.add_position({"position_name": "Applied One", "status": "[APPLIED]"})
        at = _run_page()
        at.selectbox(key="filter_status").select("[SAVED]")
        at.run()
        assert not at.exception
        assert len(at.caption) == 1
        assert "1 position(s)" in at.caption[0].value, (
            f"Expected '1 position(s)' after status filter, got: {at.caption[0].value!r}"
        )
        names = list(at.dataframe[0].value["position_name"])
        assert names == ["Open One"], (
            f"Status=[SAVED] filter must retain the [SAVED] row only, "
            f"not the [APPLIED] row; got {names!r}"
        )

    def test_filter_by_status_no_match_shows_info(self, db):
        """When the status filter matches no rows, a specific info message must appear."""
        database.add_position({"position_name": "Open One"})  # [SAVED] by default
        at = _run_page()
        at.selectbox(key="filter_status").select("[APPLIED]")
        at.run()
        assert not at.exception
        assert any("No positions match" in el.value for el in at.info), (
            f"Expected 'No positions match' info; got: {[el.value for el in at.info]}"
        )

    def test_filter_by_priority_narrows_results(self, db):
        """Selecting a specific priority must hide positions with other
        priorities, AND the surviving row must be the matching-priority one.
        See test_filter_by_status_narrows_results for the count-vs-identity
        rationale."""
        database.add_position({"position_name": "High Prio", "priority": "High"})
        database.add_position({"position_name": "Med Prio",  "priority": "Medium"})
        at = _run_page()
        at.selectbox(key="filter_priority").select("High")
        at.run()
        assert not at.exception
        assert len(at.caption) == 1
        assert "1 position(s)" in at.caption[0].value, (
            f"Expected '1 position(s)' after priority filter, got: {at.caption[0].value!r}"
        )
        names = list(at.dataframe[0].value["position_name"])
        assert names == ["High Prio"], (
            f"Priority=High filter must retain the High row only, not the "
            f"Medium row; got {names!r}"
        )

    def test_filter_by_field_substring_match(self, db):
        """Field text filter must match positions whose field contains the
        search term, AND the surviving row must be the substring-matching
        one. See test_filter_by_status_narrows_results for the count-vs-
        identity rationale — a swapped predicate (e.g. ~contains) would
        also produce count=1 here, only the row identity catches it."""
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
        names = list(at.dataframe[0].value["position_name"])
        assert names == ["ML Postdoc"], (
            f"field~='Machine' must retain 'ML Postdoc' (field='Machine "
            f"Learning'), not 'Stats Postdoc'; got {names!r}"
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
        """Both status and priority filters apply simultaneously (AND logic).
        With 3 rows wired so each pairwise pair (A∩B is [SAVED]; A∩C is
        High) survives one filter alone, the AND-only survivor is A. The
        row-identity assertion catches an OR-mistake that would also
        produce count=1 in some seedings — and pins that A specifically
        is the surviving row."""
        database.add_position({"position_name": "A", "priority": "High"})                          # [SAVED] + High
        database.add_position({"position_name": "B", "priority": "Medium"})                           # [SAVED] + Med
        database.add_position({"position_name": "C", "priority": "High", "status": "[APPLIED]"})   # [APPLIED] + High
        at = _run_page()
        at.selectbox(key="filter_status").select("[SAVED]")
        at.selectbox(key="filter_priority").select("High")
        at.run()
        assert not at.exception
        assert len(at.caption) == 1
        assert "1 position(s)" in at.caption[0].value, (
            f"Expected only position A after combined filter, got: {at.caption[0].value!r}"
        )
        names = list(at.dataframe[0].value["position_name"])
        assert names == ["A"], (
            f"Combined filter [SAVED]+High must retain only A; B fails the "
            f"priority check, C fails the status check. Got {names!r}"
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
        'C++ Programming' correctly and return exactly 1 position. The row-identity
        assertion pins that the C++ row (not the Python row) is what survives —
        guards against a swapped predicate that would also produce count=1."""
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
        names = list(at.dataframe[0].value["position_name"])
        assert names == ["C++ Postdoc"], (
            f"field~='C++' (literal) must retain 'C++ Postdoc' only, not "
            f"'Python Postdoc'; got {names!r}"
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
            {"position_name": "Open One", "status": "[SAVED]"}
        )
        at = AppTest.from_file(PAGE)
        at.run()
        at.selectbox(key="filter_status").select("[SAVED]")
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
        database.add_position({"position_name": "Alpha", "status": "[SAVED]"})
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
             "status":         "[SAVED]",
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
        # Filter to [SAVED] → Beta filtered out, Alpha is the only visible row.
        at.selectbox(key="filter_status").select("[SAVED]")
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
# When a row is selected, the page renders a subheader + tab selector below
# the table. Tab bodies hold Overview / Requirements / Materials / Notes.
#
# v1.3 Sub-task 13 (DESIGN §8.2): the tab selector is a config-driven
# `st.radio(horizontal=True, label_visibility="collapsed",
# key="edit_active_tab")` — NOT `st.tabs(...)`. The swap is load-bearing:
# DESIGN §8.2 places the Delete button *outside* the tab container, visible
# only when the active tab is Overview; `st.tabs` in Streamlit 1.56 has no
# public active-tab API (the `key=` kwarg is accepted but does not populate
# session_state), so we use st.radio whose active value lives in
# session_state["edit_active_tab"] and can gate the Delete button below.
# (The key migrated from `_active_edit_tab` to `edit_active_tab` in the
# post-Sub-task-14 follow-up — DESIGN §8.0 reserves the `_` prefix for
# internal sentinels; this is a real edit-panel widget so it follows the
# `edit_` widget-key scope.)

TAB_SELECTOR_KEY = "edit_active_tab"


def _tab_selector_rendered(at: AppTest) -> bool:
    """True iff the edit-panel tab selector (st.radio key=edit_active_tab)
    is present on the rendered page.

    AppTest's `at.radio(key=...)` raises KeyError when no such widget exists,
    so this helper wraps the try/except for readability. Mirrors the
    `_checkbox_rendered` pattern used by TestMaterialsTabWidgets."""
    try:
        at.radio(key=TAB_SELECTOR_KEY)
        return True
    except KeyError:
        return False


class TestEditPanelShell:

    def test_no_tab_selector_when_no_selection(self, db):
        """The edit-panel tab selector must not render unless a row is selected."""
        database.add_position({"position_name": "Alpha"})
        at = _run_page()
        assert not _tab_selector_rendered(at), (
            "Expected no edit-panel tab selector without selection"
        )

    def test_no_subheader_when_no_selection(self, db):
        """Subheader (position_name · status) must not render without selection."""
        database.add_position({"position_name": "Alpha"})
        at = _run_page()
        assert len(at.subheader) == 0, (
            f"Expected 0 subheaders without selection, got {len(at.subheader)}"
        )

    def test_four_tab_options_when_row_selected(self, db):
        """Selecting a row must render the tab selector with exactly 4 options
        (Overview / Requirements / Materials / Notes)."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert not at.exception, f"Page raised after selection: {at.exception}"
        assert _tab_selector_rendered(at), (
            "Expected edit-panel tab selector to render after row selection"
        )
        options = list(at.radio(key=TAB_SELECTOR_KEY).options)
        assert len(options) == 4, (
            f"Expected 4 tab options after selection, got {len(options)}: {options}"
        )

    def test_tab_labels_match_config(self, db):
        """Tab-selector labels must come from config.EDIT_PANEL_TABS (proves config-drive)."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        labels = list(at.radio(key=TAB_SELECTOR_KEY).options)
        assert labels == config.EDIT_PANEL_TABS, (
            f"Tab labels must match config.EDIT_PANEL_TABS.\n"
            f"  Expected: {config.EDIT_PANEL_TABS}\n"
            f"  Got:      {labels}"
        )

    def test_default_active_tab_is_first_config_entry(self, db):
        """Without user interaction, the active tab must default to
        config.EDIT_PANEL_TABS[0] (Overview) — Streamlit's native st.radio
        default-index-0 behaviour, pinned here so a future default-changing
        refactor shows up loudly."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert at.radio(key=TAB_SELECTOR_KEY).value == config.EDIT_PANEL_TABS[0], (
            f"Default active tab must be config.EDIT_PANEL_TABS[0]="
            f"{config.EDIT_PANEL_TABS[0]!r}; got "
            f"{at.radio(key=TAB_SELECTOR_KEY).value!r}"
        )

    def test_tabs_disappear_when_deselected(self, db):
        """Deselecting the row must unrender the edit panel (tab selector + subheader)."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert _tab_selector_rendered(at)   # precondition
        _deselect_row(at)
        assert not _tab_selector_rendered(at), (
            "Deselection should unrender the tab selector"
        )
        assert len(at.subheader) == 0, (
            "Deselection should unrender the subheader"
        )

    def test_subheader_shows_position_name_and_status(self, db):
        """The subheader must confirm what's being edited — position name +
        labelled status. DESIGN §8.0 forbids raw bracketed storage values
        (`[APPLIED]`) in the UI; the status renders via
        `config.STATUS_LABELS[raw]` (`Applied`). Note: checking only
        `"Applied" in text` would not discriminate against the broken form
        because `"Applied"` is a substring of `"[APPLIED]"` — the negative
        `"[APPLIED]" not in text` assertion is the load-bearing pin."""
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
        assert "Applied" in text, (
            f"Subheader missing labelled status (STATUS_LABELS['[APPLIED]'] "
            f"= 'Applied') per DESIGN §8.0: {text!r}"
        )
        assert "[APPLIED]" not in text, (
            f"Subheader must not render raw bracketed storage value per "
            f"DESIGN §8.0 ('Pages never render a raw status value'); "
            f"got {text!r}"
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
        assert not _tab_selector_rendered(at), (
            "Edit panel (tab selector) must not render for a stale sid"
        )


# ── Overview tab widgets (T4-C) ───────────────────────────────────────────────
# The Overview tab holds editable widgets pre-filled from the selected row.
# Widgets live inside st.form("edit_overview") so edits don't save on keystroke
# — T5 adds the real save action; a disabled submit button is the placeholder.
#
# Widget key contract (page ↔ tests): keep these prefixed with "edit_" so they
# never collide with the quick-add "qa_*" keys.

EDIT_KEYS = {
    "position_name":  "edit_position_name",
    "institute":      "edit_institute",
    "field":          "edit_field",
    "priority":       "edit_priority",
    "status":         "edit_status",
    "deadline_date":  "edit_deadline_date",
    "link":           "edit_link",
    "work_auth":      "edit_work_auth",        # Sub-task 7 / DESIGN §8.2
    "work_auth_note": "edit_work_auth_note",   # Sub-task 7 / DESIGN §8.2
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
        """Status selectbox must expose one option per config.STATUS_VALUES,
        same order. Options render as display labels via
        format_func=STATUS_LABELS.get (Sub-task 13 / DESIGN §8.0): AppTest's
        `.options` returns the post-format_func strings, so the expected
        list is the STATUS_LABELS lookup over STATUS_VALUES."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        options = list(at.selectbox(key=EDIT_KEYS["status"]).options)
        expected = [config.STATUS_LABELS[v] for v in config.STATUS_VALUES]
        assert options == expected, (
            f"Status options must match [STATUS_LABELS[v] for v in STATUS_VALUES].\n"
            f"  Expected: {expected}\n"
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


class TestOverviewWorkAuthWidgets:
    """Sub-task 7 / DESIGN §6.2 + §8.2 + D22.

    The Overview tab gains two new widgets: a `work_auth` selectbox drawn
    from ``config.WORK_AUTH_OPTIONS`` (the categorical three-value
    Yes/No/Unknown enum) and a `work_auth_note` text_area below it
    holding the freetext posting-specific nuance (e.g. "green card
    required", "J-1 OK with a waiver"). Both pre-seed from the selected
    row; both ride the existing Overview Save path."""

    def test_work_auth_selectbox_renders_after_selection(self, db):
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert at.selectbox(key=EDIT_KEYS["work_auth"]) is not None, (
            "work_auth selectbox must render inside the Overview tab once a "
            "row is selected (DESIGN §8.2 Overview-tab row)."
        )

    def test_work_auth_note_text_area_renders_after_selection(self, db):
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert at.text_area(key=EDIT_KEYS["work_auth_note"]) is not None, (
            "work_auth_note text_area must render inside the Overview tab "
            "once a row is selected (DESIGN §8.2 — below the work_auth "
            "selectbox)."
        )

    def test_work_auth_selectbox_options_match_config(self, db):
        """Options must come from config.WORK_AUTH_OPTIONS — never
        hardcoded (GUIDELINES §6). Order matters: Sub-task 3 locked
        ['Yes', 'No', 'Unknown'] as the canonical order."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        options = list(at.selectbox(key=EDIT_KEYS["work_auth"]).options)
        assert options == config.WORK_AUTH_OPTIONS, (
            "work_auth selectbox options must match config.WORK_AUTH_OPTIONS "
            "exactly (same order).\n"
            f"  Expected: {config.WORK_AUTH_OPTIONS}\n"
            f"  Got:      {options}"
        )

    def test_widgets_pre_seed_from_selected_row(self, db):
        """Both widgets must carry the selected row's DB values on render
        — the same widget-value-trap pre-seed pattern as status/priority,
        via the _edit_form_sid sentinel. work_auth_note on a populated row
        is a string; work_auth is one of WORK_AUTH_OPTIONS."""
        database.add_position({
            "position_name":  "Stanford BioStats",
            "work_auth":      "Yes",
            "work_auth_note": "green card required",
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert at.selectbox(key=EDIT_KEYS["work_auth"]).value == "Yes"
        assert (
            at.text_area(key=EDIT_KEYS["work_auth_note"]).value
            == "green card required"
        )

    def test_null_work_auth_falls_back_to_first_option(self, db):
        """A row with work_auth IS NULL (never populated — quick-add
        doesn't set it) must not blow up the selectbox. F2-style
        coercion drops the value to WORK_AUTH_OPTIONS[0], mirroring the
        existing priority/status fallback for NULL / out-of-vocab
        values. An empty work_auth_note comes back as "" via _safe_str."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert not at.exception, (
            f"Page crashed on row with NULL work_auth: {at.exception}"
        )
        assert (
            at.selectbox(key=EDIT_KEYS["work_auth"]).value
            == config.WORK_AUTH_OPTIONS[0]
        ), (
            "NULL work_auth must coerce to WORK_AUTH_OPTIONS[0] — the F2 "
            "fallback precedent set by priority/status selectboxes."
        )
        assert at.text_area(key=EDIT_KEYS["work_auth_note"]).value == "", (
            "NULL work_auth_note must coerce to empty string via _safe_str "
            "— NaN-truthiness trap applies here too."
        )


# ── Requirements tab widgets (T4-D) ───────────────────────────────────────────
# The Requirements tab renders one st.radio per entry in
# config.REQUIREMENT_DOCS. Values are canonical DB strings ('Yes', 'Optional',
# 'No'); labels come from config.REQUIREMENT_LABELS via format_func so
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
        """Exactly one radio per REQUIREMENT_DOCS entry must render on the
        Requirements tab. Sub-task 13 (DESIGN §8.2) renders tab contents
        conditionally via the st.radio-based tab selector, so the test
        must switch to Requirements first; the tab selector itself also
        contributes one radio to the page's total, hence the +1."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Requirements")
        assert not at.exception, f"Page raised on selection: {at.exception}"
        for req_col, _done_col, _label in config.REQUIREMENT_DOCS:
            assert at.radio(key=_req_key(req_col)) is not None, (
                f"Missing radio for {req_col!r}"
            )
        # Total = REQUIREMENT_DOCS radios + 1 tab-selector radio (Sub-task 13).
        assert len(at.radio) == len(config.REQUIREMENT_DOCS) + 1, (
            f"Expected {len(config.REQUIREMENT_DOCS) + 1} radios "
            f"({len(config.REQUIREMENT_DOCS)} requirement radios "
            f"+ 1 tab selector), got {len(at.radio)}"
        )

    def test_radio_values_match_db(self, db):
        """Each radio must pre-fill from the selected row's req_* column value."""
        # Exercise all three vocabulary tiers so we catch one-way mappings.
        database.add_position({
            "position_name":        "Stanford BioStats",
            "req_cv":               "Yes",
            "req_cover_letter":     "Yes",
            "req_writing_sample":   "Optional",
            "req_teaching_statement": "No",
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Requirements")
        assert at.radio(key=_req_key("req_cv")).value             == "Yes"
        assert at.radio(key=_req_key("req_cover_letter")).value   == "Yes"
        assert at.radio(key=_req_key("req_writing_sample")).value == "Optional"
        assert at.radio(key=_req_key("req_teaching_statement")).value == "No"

    def test_radio_options_display_config_labels_in_order(self, db):
        """Every radio must expose the three tiers in config order, shown via
        config.REQUIREMENT_LABELS. AppTest surfaces `.options` as the
        formatted display strings (not the canonical values), so this is the
        observable side of the canonical-value contract; the canonical-value
        half is covered by test_radio_values_match_db."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Requirements")
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

    def test_null_req_falls_back_to_no(self, db):
        """Defensive coercion (F2 analog): an unknown or None req_* value
        must not crash the page and must not put an out-of-options value
        into the radio's session_state — fall back to 'No' (schema default)."""
        database.add_position({"position_name": "Alpha"})  # req_* defaults → 'No'
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
        _select_row_and_tab(at, 0, "Requirements")
        assert not at.exception, f"Page raised on unknown req_* value: {at.exception}"
        assert at.radio(key=_req_key("req_cv")).value == "No", (
            "Unknown req_* value must coerce to 'No' (schema default), "
            f"got {at.radio(key=_req_key('req_cv')).value!r}"
        )

    def test_widgets_update_on_selection_change(self, db):
        """Widget-value-trap regression guard on the req_* path: switching
        rows must re-seed the req_* widgets, not stick on the first."""
        database.add_position({"position_name": "Alpha", "req_cv": "Yes"})
        database.add_position({"position_name": "Beta",  "req_cv": "No"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Requirements")
        first = at.radio(key=_req_key("req_cv")).value
        _select_row_and_tab(at, 1, "Requirements")
        second = at.radio(key=_req_key("req_cv")).value
        assert {first, second} == {"Yes", "No"}, (
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
        _select_row_and_tab(at, 0, "Requirements")
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
        # And its default value (from the migration's DEFAULT 'No') should
        # land in session_state as 'No' after the pre-seed coercion — this
        # IS the canonical-value half of the contract.
        assert at.radio(key=_req_key("req_portfolio")).value == "No"


# ── Materials tab widgets (T4-E) ──────────────────────────────────────────────
# The Materials tab is state-driven: it renders one st.checkbox per done_*
# column ONLY for documents whose req_* is 'Yes' (matching the readiness
# definition in database.py ~line 404 — "A position is 'ready' if every
# document where req_* = 'Yes' has done_* = 1"). The source of truth for
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
        database.add_position({"position_name": "Alpha", "req_cv": "Yes"})
        at = _run_page()
        assert len(at.checkbox) == 0, (
            f"Expected 0 checkboxes before selection, got {len(at.checkbox)}"
        )

    def test_empty_state_when_no_required_docs(self, db):
        """With all req_* = 'No' (the schema default), the Materials tab must
        show an info hint directing the user to the Requirements tab — rendering
        zero checkboxes would be a silent dead-end UI."""
        database.add_position({"position_name": "Alpha"})   # all req_* default 'No'
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Materials")
        # No done_* checkboxes must render.
        assert len(at.checkbox) == 0, (
            f"With all req_* = 'No', no Materials checkboxes should render; "
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
        """With req_cv='Yes' and everything else 'No', exactly one checkbox
        (done_cv) must render — not zero, not len(REQUIREMENT_DOCS)."""
        database.add_position({"position_name": "Alpha", "req_cv": "Yes"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Materials")
        # done_cv is the only one required → exactly one checkbox rendered.
        assert _checkbox_rendered(at, _done_key("done_cv")), (
            "done_cv checkbox must render when req_cv == 'Yes'"
        )
        for _req_col, done_col, _label in config.REQUIREMENT_DOCS:
            if done_col == "done_cv":
                continue
            assert not _checkbox_rendered(at, _done_key(done_col)), (
                f"{done_col} checkbox should be hidden when its req_* is 'No'"
            )
        # Tight bound: no other page checkboxes exist today.
        assert len(at.checkbox) == 1, (
            f"Expected 1 Materials checkbox, got {len(at.checkbox)}"
        )

    def test_checkbox_initial_state_matches_db(self, db):
        """Pre-seed must translate done_* INTEGER (0/1) to bool correctly."""
        database.add_position({
            "position_name":   "Stanford BioStats",
            "req_cv":          "Yes",
            "done_cv":          1,
            "req_cover_letter": "Yes",
            "done_cover_letter": 0,
            "req_transcripts":  "Yes",
            # done_transcripts omitted → schema default 0
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Materials")
        # Use == (not `is`) because pandas surfaces numpy booleans
        # (numpy.bool_), and `np.True_ is True` is False.
        assert bool(at.checkbox(key=_done_key("done_cv")).value)          is True
        assert bool(at.checkbox(key=_done_key("done_cover_letter")).value) is False
        assert bool(at.checkbox(key=_done_key("done_transcripts")).value) is False

    def test_toggling_requirement_hides_checkbox(self, db):
        """State-driven behaviour: when the user flips req_cv from 'Yes' to 'No'
        on the Requirements tab, the done_cv checkbox on the Materials tab
        must disappear on the next rerun.

        We drive this via session_state["edit_req_cv"] rather than a raw DB
        update because the source of truth for 'is this required?' is the
        live widget state (_edit_form_sid only reseeds on selection change
        — a DB-only update would not re-trigger the pre-seed). This is the
        faithful test of state-driven design."""
        database.add_position({"position_name": "Alpha", "req_cv": "Yes"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Materials")
        assert _checkbox_rendered(at, _done_key("done_cv"))   # precondition
        # Simulate the user flipping the req_cv radio to "Not needed". We
        # keep the Materials tab active (and row selected) across the rerun
        # so the checkbox-absence is driven by the req flip alone, not by
        # the tab / selection state disappearing.
        at.session_state["edit_req_cv"] = "No"
        _keep_selection(at, 0)
        at.session_state[TAB_SELECTOR_KEY] = "Materials"
        at.run()
        assert not at.exception, f"Page raised on req toggle: {at.exception}"
        assert not _checkbox_rendered(at, _done_key("done_cv")), (
            "Toggling edit_req_cv → 'No' must hide the done_cv checkbox"
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
        _select_row_and_tab(at, 0, "Materials")
        assert not _checkbox_rendered(at, _done_key("done_cv")), (
            "'Optional' docs must be hidden from Materials (Y-only filter "
            "matches the readiness definition in database.py)"
        )

    def test_checkboxes_update_on_selection_change(self, db):
        """Widget-value-trap regression guard on the done_* path: selecting a
        different row must re-seed the done_* widgets with that row's values."""
        database.add_position({"position_name": "Alpha",
                               "req_cv": "Yes", "done_cv": 1})
        database.add_position({"position_name": "Beta",
                               "req_cv": "Yes", "done_cv": 0})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Materials")
        # bool() normalises numpy.bool_ → Python bool so set equality works.
        first = bool(at.checkbox(key=_done_key("done_cv")).value)
        _select_row_and_tab(at, 1, "Materials")
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
        """Baseline positive contract: switching to the Notes tab after a row
        is selected must render exactly one text_area with key=edit_notes.
        (Sub-task 13: Notes widgets only render when active_tab == 'Notes'.)"""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Notes")
        assert _text_area_rendered(at, NOTES_KEY), (
            "Notes tab must render a text_area keyed edit_notes after selection"
        )
        # Post-Sub-task-13: only one text_area renders on the Notes tab
        # (edit_work_auth_note lives on the Overview tab and only renders
        # when active_tab == "Overview"). If a future tier adds another
        # text_area to the Notes tab, bump this count rather than loosen
        # the inequality.
        assert len(at.text_area) == 1, (
            f"Expected 1 text_area on the Notes tab (edit_notes); "
            f"got {len(at.text_area)}"
        )

    def test_text_area_preseeded_from_db(self, db):
        """Pre-seed must copy positions.notes into session_state verbatim,
        so the widget displays the saved notes without the user clicking
        'edit'."""
        notes = "Follow up with Prof. Smith after SfN. Ref: lab website."
        database.add_position({"position_name": "Alpha", "notes": notes})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Notes")
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
        _select_row_and_tab(at, 0, "Notes")
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
        _select_row_and_tab(at, 0, "Notes")
        first = at.text_area(key=NOTES_KEY).value
        _select_row_and_tab(at, 1, "Notes")
        second = at.text_area(key=NOTES_KEY).value
        assert first == "alpha notes", f"Row 0 notes mis-seeded: {first!r}"
        assert second == "beta notes", (
            f"Row 1 notes did not re-seed on selection change — "
            f"widget-value trap. Got {second!r}"
        )

    def test_no_save_buttons_are_disabled_post_tier5(self, db):
        """Tier 5 fully shipped — every per-tab save button must render
        ENABLED. The previous form (test_unwired_save_buttons_still_disabled)
        iterated the remaining-disabled list and tooltip-checked each;
        once Tier 5 landed that list went empty and the for-loop became
        a no-op, asserting nothing.

        Inverting the assertion turns the same scaffolding into a real
        regression guard: if anyone re-introduces a `disabled=True` save
        button (e.g. by checking out an old branch and re-merging it
        without conflict resolution), this test fails loudly."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        # Each tab has its own save button — exercise all four to cover
        # every enabled-state.
        for tab_name in config.EDIT_PANEL_TABS:
            at.session_state[TAB_SELECTOR_KEY] = tab_name
            at.run()
            disabled = [
                b for b in at.button if getattr(b, "disabled", False)
            ]
            assert disabled == [], (
                f"On the {tab_name!r} tab, found disabled buttons "
                f"post-Tier-5: {[b.label for b in disabled]!r}. "
                "Tier 5 wired every per-tab save; a disabled save "
                "would mean a sub-task regression."
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


def _select_row_and_tab(at: AppTest, row_index: int, tab_name: str) -> None:
    """Set table row selection + edit-panel active tab, then rerun.

    Needed by tests that access widgets on a NON-Overview tab (Requirements,
    Materials, Notes). Sub-task 13 (DESIGN §8.2) swapped `st.tabs` for
    `st.radio(horizontal=True, key="edit_active_tab")` + branch-based tab
    rendering; unlike `st.tabs` — which used to render ALL tab bodies and
    CSS-hide the inactive ones — the radio-based panel renders ONLY the
    active tab's widgets, so a test that wants to access e.g. the
    `edit_req_cv` radio MUST first set `edit_active_tab = "Requirements"`.

    Writing session_state directly (rather than `at.radio(...).set_value(x)
    + at.run()`) keeps the single-rerun contract — the dataframe selection
    doesn't outlive its single-run signal (see `_keep_selection` docstring),
    so we write selection + tab together before the next rerun.

    `tab_name` must be one of config.EDIT_PANEL_TABS."""
    at.session_state[TABLE_KEY] = {
        "selection": {"rows": [row_index], "columns": []}
    }
    at.session_state[TAB_SELECTOR_KEY] = tab_name
    at.run()


class TestOverviewSave:

    def test_save_persists_all_nine_fields(self, db):
        """Round-trip: edit every Overview widget, click Save, assert the DB
        row reflects every new value. Guards against a field being added to
        the form but forgotten in the update_position payload.

        Coverage MUST equal EDIT_KEYS keys in the Overview save payload —
        the previous form covered 7 of 9 (work_auth and work_auth_note
        were missed when Sub-task 7 added them to the form), exactly the
        regression class this test was supposed to catch. The
        len(payload) == len(EDIT_KEYS) assertion below makes the
        invariant explicit: a future field addition that lands in
        EDIT_KEYS but not in the round-trip will fail loudly."""
        database.add_position({
            "position_name":  "Original Name",
            "institute":      "Original Inst",
            "field":          "Original Field",
            "priority":       "Medium",
            "status":         "[SAVED]",
            "deadline_date":  "2026-01-01",
            "link":           "https://old.example",
            "work_auth":      "Unknown",
            "work_auth_note": "original note",
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        sid = at.session_state["selected_position_id"]

        # Edit every field. New values keyed by the EDIT_KEYS logical
        # name so a future EDIT_KEYS rename surfaces here, and the
        # cardinality check below ties the test to EDIT_KEYS one-to-one.
        new_values: dict[str, object] = {
            "position_name":  "New Name",
            "institute":      "New Inst",
            "field":          "New Field",
            "priority":       "High",
            "status":         "[APPLIED]",
            "deadline_date":  datetime.date(2026, 9, 15),
            "link":           "https://new.example",
            "work_auth":      "Yes",
            "work_auth_note": "OPT eligible, sponsorship not needed",
        }
        assert set(new_values) == set(EDIT_KEYS), (
            "test_save_persists_all_nine_fields must cover every EDIT_KEYS "
            f"entry one-to-one. Diff: missing from new_values: "
            f"{set(EDIT_KEYS) - set(new_values)!r}; "
            f"extra in new_values: {set(new_values) - set(EDIT_KEYS)!r}. "
            "If you added a field to EDIT_KEYS, also add it here AND wire "
            "it into the Overview save payload in pages/1_Opportunities.py."
        )

        at.text_input(key=EDIT_KEYS["position_name"]).set_value(new_values["position_name"])
        at.text_input(key=EDIT_KEYS["institute"]).set_value(new_values["institute"])
        at.text_input(key=EDIT_KEYS["field"]).set_value(new_values["field"])
        at.selectbox(key=EDIT_KEYS["priority"]).set_value(new_values["priority"])
        at.selectbox(key=EDIT_KEYS["status"]).set_value(new_values["status"])
        at.date_input(key=EDIT_KEYS["deadline_date"]).set_value(new_values["deadline_date"])
        at.text_input(key=EDIT_KEYS["link"]).set_value(new_values["link"])
        at.selectbox(key=EDIT_KEYS["work_auth"]).set_value(new_values["work_auth"])
        at.text_area(key=EDIT_KEYS["work_auth_note"]).set_value(new_values["work_auth_note"])

        at.button(key=OVERVIEW_SUBMIT_KEY).click()
        _keep_selection(at, 0)   # mimic browser-side selection persistence
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        row = database.get_position(sid)
        assert row["position_name"]  == "New Name"
        assert row["institute"]      == "New Inst"
        assert row["field"]          == "New Field"
        assert row["priority"]       == "High"
        assert row["status"]         == "[APPLIED]"
        assert row["deadline_date"]  == "2026-09-15"
        assert row["link"]           == "https://new.example"
        assert row["work_auth"]      == "Yes"
        assert row["work_auth_note"] == "OPT eligible, sponsorship not needed"

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

    def test_save_persists_work_auth_and_note(self, db):
        """Sub-task 7 / DESIGN §6.2 + §8.2: the Overview Save payload must
        carry both work_auth and work_auth_note so the pair round-trips
        through the full UI path. Seeds a row with no work auth info, edits
        both widgets, clicks Save, and asserts the DB row reflects both —
        guards against either field being added to the form but forgotten
        in update_position's payload dict."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        sid = at.session_state["selected_position_id"]

        at.selectbox(key=EDIT_KEYS["work_auth"]).set_value("Yes")
        at.text_area(key=EDIT_KEYS["work_auth_note"]).set_value(
            "green card required"
        )
        at.button(key=OVERVIEW_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        row = database.get_position(sid)
        assert row["work_auth"]      == "Yes"
        assert row["work_auth_note"] == "green card required"


# ── Requirements tab Save (T5-B) ──────────────────────────────────────────────
# The Requirements form persists all req_* columns via database.update_position.
# Critical contract: Requirements Save NEVER writes done_* columns. The payload
# is built from config.REQUIREMENT_DOCS → req_col only, so update_position's
# parameterised UPDATE leaves the done_* columns of the row untouched. Flipping
# req_cv from 'Yes' to 'No' preserves done_cv — the user's "I've prepared the CV"
# status is independent of whether any given position requires it right now.
# DESIGN.md §6: Materials is checkbox-only; the readiness computation hides
# rows where req_* != 'Yes' but the underlying value is preserved.

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
        _select_row_and_tab(at, 0, "Requirements")
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
        req_cv from 'Yes' → 'No' and saving MUST leave done_cv == 1 in the DB.

        Rationale (DESIGN.md + user decision 2026-04-20): if req_cv later
        flips back to 'Yes', the Materials tab should again show 'CV: done'
        without the user having to re-tick — the CV didn't un-prepare itself."""
        database.add_position({
            "position_name": "Alpha",
            "req_cv":        "Yes",
            "done_cv":       1,
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Requirements")
        sid = at.session_state["selected_position_id"]

        # Flip req_cv to N.
        at.radio(key=_req_key("req_cv")).set_value("No")
        at.button(key=REQUIREMENTS_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        row = database.get_position(sid)
        assert row["req_cv"] == "No", (
            f"req_cv should have flipped to 'No', got {row['req_cv']!r}"
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
        _select_row_and_tab(at, 0, "Requirements")
        at.radio(key=_req_key("req_cv")).set_value("Yes")
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
        _select_row_and_tab(at, 0, "Requirements")
        sid_before = at.session_state["selected_position_id"]
        at.radio(key=_req_key("req_cv")).set_value("Yes")
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
        _select_row_and_tab(at, 0, "Requirements")
        at.radio(key=_req_key("req_cv")).set_value("Yes")
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


# ── Materials tab Save (T5-C) ────────────────────────────────────────────────
# The Materials form persists done_* columns via database.update_position.
# Critical contract: the payload contains done_* keys ONLY for docs whose
# matching req_* is currently 'Yes' on the LIVE session_state (the state-driven
# visibility pinned by T4-E). Any done_* for a non-visible doc is NEVER in the
# payload, so the user's prepared-documents history survives a req Y→N flip
# on this tab exactly as it does on the Requirements tab (T5-B contract,
# opposite direction).
#
# Storage: INT 0/1 (positions.done_* schema). The page casts bool → int before
# the DB write so the schema's declared integer domain is honoured regardless
# of SQLite's lenient type coercion.

MATERIALS_SUBMIT_KEY = "edit_materials_submit"


class TestMaterialsSave:

    def test_save_persists_only_visible_done_fields(self, db):
        """Round-trip: with two req_* = 'Yes' and the rest = 'No', tick the two
        visible checkboxes, click Save → the DB has done_* = 1 for the two
        visible docs and the hidden done_* columns are left at their prior DB
        values (here, 0 by schema default)."""
        # Pick the first two REQUIREMENT_DOCS entries as the 'required' pair;
        # the remainder stay at the schema-default 'No' / 0.
        visible = config.REQUIREMENT_DOCS[:2]
        hidden  = config.REQUIREMENT_DOCS[2:]
        seed: dict[str, Any] = {"position_name": "Alpha"}
        for req_col, _done_col, _label in visible:
            seed[req_col] = "Yes"
        sid = database.add_position(seed)

        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Materials")

        # Tick the visible checkboxes.
        for _req_col, done_col, _label in visible:
            at.checkbox(key=_done_key(done_col)).set_value(True)

        at.button(key=MATERIALS_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        row = database.get_position(sid)
        for _req_col, done_col, _label in visible:
            assert row[done_col] == 1, (
                f"{done_col} should have persisted to 1, got {row[done_col]!r}"
            )
        for _req_col, done_col, _label in hidden:
            assert row[done_col] == 0, (
                f"{done_col} is hidden (req != 'Yes') and must not be in the "
                f"payload; schema default 0 must be preserved, got "
                f"{row[done_col]!r}"
            )
        assert at.toast, "Expected st.toast after a successful Materials save"
        assert any("Alpha" in el.value for el in at.toast), (
            f"Toast should reference the position name; got "
            f"{[el.value for el in at.toast]}"
        )

    def test_save_preserves_done_fields_hidden_by_req_n(self, db):
        """Critical contract pin (mirror of T5-B's done_* preservation, from
        the Materials side): saving Materials MUST NOT touch any done_* whose
        req_* is currently not 'Yes'. Seed done_cv=1 while req_cv='No'; flip
        req_research_statement to 'Yes' live, tick that checkbox, save —
        done_cv must still be 1 in the DB. Prevents a regression where the
        page loops over ALL REQUIREMENT_DOCS and overwrites hidden done_*
        with their (possibly stale) seeded bool value."""
        sid = database.add_position({
            "position_name":            "Alpha",
            "req_cv":                   "No",
            "done_cv":                  1,   # prepared earlier; currently hidden
            "req_research_statement":   "No",
            "done_research_statement":  0,
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Materials")

        # Flip req_research_statement to 'Yes' live via session_state directly —
        # the Requirements-tab radio is inside st.form("edit_requirements") so
        # widget values there do not commit to session_state until that form
        # is submitted. Writing session_state is how T4-E's
        # test_toggling_requirement_hides_checkbox drives the same
        # state-driven visibility.
        at.session_state[_req_key("req_research_statement")] = "Yes"
        _keep_selection(at, 0)
        at.session_state[TAB_SELECTOR_KEY] = "Materials"
        at.run()

        # Tick the newly-visible checkbox and save.
        at.checkbox(key=_done_key("done_research_statement")).set_value(True)
        at.button(key=MATERIALS_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        row = database.get_position(sid)
        assert row["done_research_statement"] == 1, (
            f"done_research_statement should have persisted to 1, got "
            f"{row['done_research_statement']!r}"
        )
        assert row["done_cv"] == 1, (
            f"done_cv MUST be preserved across a Materials save when its "
            f"req_cv is 'No' (user-confirmed contract 2026-04-20); got "
            f"{row['done_cv']!r}. If this fails, the Materials-save payload "
            f"is writing done_* for docs whose req_* != 'Yes' — it must only "
            f"include done_* for visible docs."
        )

    def test_save_db_failure_shows_error_no_traceback(self, db, monkeypatch):
        """Mirror the F1 failure contract on the Materials path: a raising
        update_position must surface a friendly st.error without re-raising.
        """
        database.add_position({"position_name": "Alpha", "req_cv": "Yes"})

        def _boom(_position_id, _fields):
            raise RuntimeError("db unavailable")
        monkeypatch.setattr(database, "update_position", _boom)

        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Materials")
        at.checkbox(key=_done_key("done_cv")).set_value(True)
        at.button(key=MATERIALS_SUBMIT_KEY).click()
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
        """After Materials save, the edit panel must re-render for the SAME
        position — selected_position_id must survive the post-save rerun via
        the T5-A _skip_table_reset one-shot."""
        database.add_position({"position_name": "Alpha", "req_cv": "Yes"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Materials")
        sid_before = at.session_state["selected_position_id"]

        at.checkbox(key=_done_key("done_cv")).set_value(True)
        at.button(key=MATERIALS_SUBMIT_KEY).click()
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
        # Panel still rendered: the Materials checkbox is still there.
        assert _checkbox_rendered(at, _done_key("done_cv")), (
            "Materials checkbox must still render after save (req_cv is 'Yes')"
        )

    def test_save_toast_survives_rerun(self, db):
        """Regression guard for the Tier-1 st.success-clobber bug on the
        Materials path: st.toast must still be in at.toast after the post-save
        rerun completes."""
        database.add_position({"position_name": "Alpha", "req_cv": "Yes"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Materials")
        at.checkbox(key=_done_key("done_cv")).set_value(True)
        at.button(key=MATERIALS_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert at.toast, (
            "Toast should survive the post-save rerun. If this fails, check "
            "that the success path uses st.toast, not st.success."
        )
        success_texts = [el.value for el in at.success]
        assert not any("Saved" in t or "saved" in t for t in success_texts), (
            f"Materials save must use st.toast, not st.success; got "
            f"st.success messages: {success_texts}"
        )


# ── Notes tab Save (T5-D) ────────────────────────────────────────────────────
# The Notes form persists the free-form text_area via database.update_position.
# Storage contract (DESIGN.md §6 + CLAUDE.md 'Key Design Decisions'): empty
# input is stored as the empty string "" — NOT NULL — so round-trips through
# the pre-seed (NULL → "") and a no-op save leave the DB stable at "".
#
# Widget keys already pinned in T4-F:
#   • text_area: session_state key "edit_notes"  (NOTES_KEY constant)
#   • form id:   "edit_notes_form"  (deliberately != widget key to avoid
#                StreamlitValueAssignmentNotAllowedError — st.form registers
#                its id with writes_allowed=False).
# New in T5-D:
#   • submit key: "edit_notes_submit"

NOTES_SUBMIT_KEY = "edit_notes_submit"


class TestNotesSave:

    def test_save_persists_notes(self, db):
        """Round-trip: type text, click Save, assert the DB row reflects it.
        Also verifies the success toast fires with the position name."""
        sid = database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Notes")

        at.text_area(key=NOTES_KEY).set_value(
            "Contact: jane@example.edu\nFollow up after Oct 15."
        )
        at.button(key=NOTES_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        row = database.get_position(sid)
        assert row["notes"] == (
            "Contact: jane@example.edu\nFollow up after Oct 15."
        ), f"notes did not round-trip; got {row['notes']!r}"
        assert at.toast, "Expected st.toast after a successful Notes save"
        assert any("Alpha" in el.value for el in at.toast), (
            f"Toast should reference the position name; got "
            f"{[el.value for el in at.toast]}"
        )

    def test_save_empty_stored_as_empty_string(self, db):
        """DESIGN.md contract: empty notes are stored as '', not NULL, so the
        pre-seed (which coerces NULL → '') and a no-op save leave the DB
        stable at ''. Seeds a row with non-empty notes, clears the text_area,
        saves, and asserts the DB column is exactly the empty string."""
        sid = database.add_position({
            "position_name": "Alpha",
            "notes":         "something to clear",
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Notes")

        at.text_area(key=NOTES_KEY).set_value("")
        at.button(key=NOTES_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert not at.exception, f"Save raised: {at.exception}"
        row = database.get_position(sid)
        assert row["notes"] == "", (
            f"Empty notes must be stored as '' (not None / NULL); got "
            f"{row['notes']!r}. If this fails, the save path is likely "
            f"writing None for empty strings — the pre-seed would still "
            f"coerce on load, but the DB column would drift to NULL."
        )

    def test_save_db_failure_shows_error_no_traceback(self, db, monkeypatch):
        """Mirror the F1 failure contract on the Notes path: a raising
        update_position must surface a friendly st.error without re-raising.
        """
        database.add_position({"position_name": "Alpha"})

        def _boom(_position_id, _fields):
            raise RuntimeError("db unavailable")
        monkeypatch.setattr(database, "update_position", _boom)

        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Notes")
        at.text_area(key=NOTES_KEY).set_value("anything")
        at.button(key=NOTES_SUBMIT_KEY).click()
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
        """After Notes save, the edit panel must re-render for the SAME
        position — selected_position_id must survive the post-save rerun via
        the T5-A _skip_table_reset one-shot."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Notes")
        sid_before = at.session_state["selected_position_id"]

        at.text_area(key=NOTES_KEY).set_value("context")
        at.button(key=NOTES_SUBMIT_KEY).click()
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
        # Panel still rendered: the Notes text_area is still there.
        assert _text_area_rendered(at, NOTES_KEY), (
            "Notes text_area must still render after save"
        )

    def test_save_toast_survives_rerun(self, db):
        """Regression guard for the Tier-1 st.success-clobber bug on the
        Notes path: st.toast must still be in at.toast after the post-save
        rerun completes."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Notes")
        at.text_area(key=NOTES_KEY).set_value("context")
        at.button(key=NOTES_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert at.toast, (
            "Toast should survive the post-save rerun. If this fails, check "
            "that the success path uses st.toast, not st.success."
        )
        success_texts = [el.value for el in at.success]
        assert not any("Saved" in t or "saved" in t for t in success_texts), (
            f"Notes save must use st.toast, not st.success; got "
            f"st.success messages: {success_texts}"
        )


# ── Overview tab Delete (T5-E) ───────────────────────────────────────────────
# Delete lives on the Overview tab only (DESIGN.md §6 + user decision
# 2026-04-20). Clicking Delete opens an st.dialog; Confirm cascades the
# DELETE FROM positions via database.delete_position(sid), which removes
# the applications + recommenders rows via ON DELETE CASCADE on the FKs
# (schema: database.py ~lines 101 / 116). On success: toast, pop both
# selected_position_id and _edit_form_sid, st.rerun(). On cancel: just
# st.rerun() — no state change, no DB write. On DB failure: friendly
# st.error, no re-raise, no state cleared (so the user can retry).
#
# Widget keys (public test contract — do not rename without updating
# the constants here and the page):
#   • Delete button (outside the Overview form): edit_delete
#   • Confirm Delete button (inside dialog):     delete_confirm
#   • Cancel button (inside dialog):             delete_cancel

DELETE_BUTTON_KEY  = "edit_delete"
DELETE_CONFIRM_KEY = "delete_confirm"
DELETE_CANCEL_KEY  = "delete_cancel"


class TestDeleteAction:

    def test_delete_button_renders_on_overview(self, db):
        """Delete button with key 'edit_delete' must be present on the
        Overview tab after a row is selected. Must live OUTSIDE
        st.form('edit_overview') because st.form only permits
        st.form_submit_button inside (a plain st.button inside a form would
        raise at render).

        The button's visual type='primary' (destructive styling) is a UI
        concern not exposed by AppTest — the Button.type attribute there
        reports the widget-class name ('button'), not the Streamlit type
        parameter. Styling is verified manually / via the code review
        checklist, not automated here."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)

        assert not at.exception, f"Page raised on selection: {at.exception}"
        btn = at.button(key=DELETE_BUTTON_KEY)
        assert btn is not None, "Missing Delete button with key 'edit_delete'"
        assert (btn.label or "").lower() == "delete", (
            f"Delete button label should be 'Delete', got {btn.label!r}"
        )

    def test_dialog_warning_mentions_cascade_and_irreversibility(self, db):
        """DESIGN §8.0 Confirmation pattern + §8.2 Delete row require an
        @st.dialog confirm with explicit copy mentioning cascade effects.
        Pin the warning content directly: it must reference the position
        name (so the user knows which row they are about to delete), the
        cascade to application + recommender rows (so the user understands
        the impact beyond positions), and irreversibility (so the user
        knows there is no undo). A regression that drops any of these
        signals is a UX-correctness bug that the action-only delete tests
        cannot catch — they verify the row leaves the DB, not that the
        user was warned about what else goes with it."""
        sid = database.add_position({"position_name": "Stanford BioStats"})
        database.add_recommender(sid, {"recommender_name": "Prof X"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)

        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()

        # The dialog renders an st.warning whose text is what the user
        # actually sees. A bare existence check would pass even if the
        # copy were silently neutered — pin every load-bearing fragment.
        assert at.warning, (
            f"Delete dialog must render an st.warning; got "
            f"{[el.value for el in at.warning]}"
        )
        warning_text = " ".join(el.value for el in at.warning)
        assert "Stanford BioStats" in warning_text, (
            f"Dialog warning must reference the position name so the user "
            f"knows which row they are about to delete; got "
            f"{warning_text!r}"
        )
        assert "recommender" in warning_text.lower(), (
            f"Dialog warning must mention recommenders so the user "
            f"understands the FK cascade impact; got {warning_text!r}"
        )
        assert "application" in warning_text.lower(), (
            f"Dialog warning must mention applications so the user "
            f"understands the FK cascade impact; got {warning_text!r}"
        )
        assert "cannot be undone" in warning_text.lower(), (
            f"Dialog warning must signal irreversibility — without this "
            f"the user has no warning that there is no undo path; got "
            f"{warning_text!r}"
        )

    def test_confirm_deletes_position(self, db):
        """Click Delete → Confirm → the position is gone from the DB.
        database.get_position(sid) raises KeyError for missing rows."""
        sid = database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)

        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        # Dialog is now open; confirm must be reachable as a top-level button.
        at.button(key=DELETE_CONFIRM_KEY).click()
        at.run()

        assert not at.exception, f"Delete raised: {at.exception}"
        with pytest.raises(KeyError):
            database.get_position(sid)

    def test_confirm_cascades_applications_and_recommenders(self, db):
        """FK cascade pin: deleting a position must also remove its
        applications row (auto-created by add_position) and any recommender
        rows (PRAGMA foreign_keys=ON + ON DELETE CASCADE on both FKs —
        verified in database.py). Regression guard in case someone later
        turns off PRAGMA or replaces the FK with a plain REFERENCES."""
        sid = database.add_position({"position_name": "Alpha"})
        database.add_recommender(sid, {"recommender_name": "Prof X"})
        # Precondition: application + recommender rows exist for sid.
        assert database.get_application(sid), (
            "Application row should have been auto-created by add_position"
        )
        recs_before = database.get_recommenders(sid)
        assert len(recs_before) == 1, (
            f"Should have 1 recommender before delete, got {len(recs_before)}"
        )

        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        at.button(key=DELETE_CONFIRM_KEY).click()
        at.run()

        assert not at.exception, f"Delete raised: {at.exception}"
        # applications row cascaded away (get_application returns {} when no row).
        assert database.get_application(sid) == {}, (
            "applications row must be cascaded away by FK ON DELETE CASCADE"
        )
        # recommenders rows cascaded away too.
        recs_after = database.get_recommenders(sid)
        assert len(recs_after) == 0, (
            f"recommenders rows must be cascaded away, got {len(recs_after)} "
            f"leftover rows — check PRAGMA foreign_keys=ON in _connect()"
        )

    def test_confirm_clears_selection_state(self, db):
        """After confirm, both session_state keys that bind the edit panel to
        a position (selected_position_id AND _edit_form_sid) must be cleared
        together — they are paired throughout the page (T4 pattern), and
        leaving one behind would let the next rerun alias with a future sid
        and skip the pre-seed for the fresh selection."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        # Precondition: both keys are set by the row-selection flow.
        assert "selected_position_id" in at.session_state
        assert "_edit_form_sid" in at.session_state

        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        at.button(key=DELETE_CONFIRM_KEY).click()
        at.run()

        assert not at.exception, f"Delete raised: {at.exception}"
        assert "selected_position_id" not in at.session_state, (
            "selected_position_id must be popped after a successful delete"
        )
        assert "_edit_form_sid" not in at.session_state, (
            "_edit_form_sid must be popped alongside selected_position_id — "
            "the pair is paired throughout the page (T4 pattern)"
        )

    def test_confirm_shows_toast_with_position_name(self, db):
        """Success confirmation uses st.toast (survives the post-delete
        st.rerun()) and references the deleted position's name so the user
        sees which row went away."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        at.button(key=DELETE_CONFIRM_KEY).click()
        at.run()

        assert not at.exception, f"Delete raised: {at.exception}"
        assert at.toast, "Expected st.toast after a successful delete"
        assert any("Alpha" in el.value for el in at.toast), (
            f"Toast should reference the deleted position name; got "
            f"{[el.value for el in at.toast]}"
        )

    def test_cancel_does_not_delete_or_clear_state(self, db):
        """Cancel contract: clicking Cancel inside the dialog must close the
        dialog and leave state completely untouched — position still in DB,
        selection still active, no toast, no error."""
        sid = database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)

        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        at.button(key=DELETE_CANCEL_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert not at.exception, f"Cancel raised: {at.exception}"
        # Position still present.
        row = database.get_position(sid)
        assert row["position_name"] == "Alpha", (
            "Cancel must NOT delete the position"
        )
        # Selection still active — user's context preserved.
        # AppTest.session_state does NOT support .get() — use `in` + subscript.
        assert "selected_position_id" in at.session_state, (
            "Cancel must NOT clear selected_position_id"
        )
        assert at.session_state["selected_position_id"] == sid, (
            f"Cancel must not alter the selected id; got "
            f"{at.session_state['selected_position_id']} vs expected {sid}"
        )
        # No toast / no error.
        assert not at.toast, (
            f"Cancel must NOT fire a toast; got {[el.value for el in at.toast]}"
        )
        assert not at.error, (
            f"Cancel must NOT render an error; got "
            f"{[el.value for el in at.error]}"
        )

    def test_delete_db_failure_shows_error_no_traceback(self, db, monkeypatch):
        """Mirror the F1 failure contract on the Delete path: a raising
        delete_position must surface a friendly st.error without re-raising.
        Also defensive: selection state is NOT cleared on failure, so the
        user can retry rather than losing their context."""
        sid = database.add_position({"position_name": "Alpha"})

        def _boom(_position_id):
            raise RuntimeError("db unavailable")
        monkeypatch.setattr(database, "delete_position", _boom)

        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        at.button(key=DELETE_CONFIRM_KEY).click()
        at.run()

        assert at.error, "Expected st.error when delete_position raises"
        assert any("Could not delete" in el.value for el in at.error), (
            f"Expected 'Could not delete' prefix in error, got: "
            f"{[el.value for el in at.error]}"
        )
        assert not at.exception, (
            f"Delete handler must swallow the exception after st.error; "
            f"got uncaught: {at.exception}"
        )
        assert not at.toast, (
            f"No toast should appear on delete failure; got "
            f"{[el.value for el in at.toast]}"
        )
        # Position row still present — the raise happened BEFORE any state
        # was cleared. Retry-friendly.
        assert database.get_position(sid)["position_name"] == "Alpha", (
            "Position row must survive a failed delete (monkeypatched raise)"
        )

    # ── Review fixes (phase-3-tier5-review.md) ────────────────────────────

    def test_row_change_clears_pending_delete_target(self, db):
        """Review Fix #2: if the user dismisses the delete dialog via the X
        / Escape (neither fires a button click, neither runs our Cancel
        handler), _delete_target_id lingers in session_state. Switching to
        a DIFFERENT row must clear that stale target so that returning to
        the original row later does NOT re-open a phantom dialog without
        user intent.

        Pins the row-change cleanup block in the selection-resolution
        section of pages/1_Opportunities.py. Without the fix, the elif
        dialog-reopen branch fires whenever the user re-selects the
        original row, which is a surprise UX."""
        sid_a = database.add_position({"position_name": "Alpha"})
        sid_b = database.add_position({"position_name": "Beta"})
        at = AppTest.from_file(PAGE)
        at.run()

        # 1. Select row A and open the delete dialog.
        _select_row(at, 0)
        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        assert at.session_state["_delete_target_id"] == sid_a, (
            "Delete target should be row A after clicking Delete on it"
        )

        # 2. Simulate a UI-dismiss (no Cancel click) — no code runs, we
        #    just select row B. The dataframe positional order is by
        #    deadline_date ASC NULLS LAST; both rows have NULL deadline,
        #    so tiebreak is by id ASC: row 0 = sid_a, row 1 = sid_b.
        _keep_selection(at, 1)
        at.run()

        assert at.session_state["selected_position_id"] == sid_b, (
            "Selection should have moved to row B"
        )
        assert "_delete_target_id" not in at.session_state, (
            "Stale delete target must be cleared when the selected row "
            "changes — otherwise returning to row A would re-open the "
            "dialog without user action."
        )
        assert "_delete_target_name" not in at.session_state, (
            "_delete_target_name must be cleared alongside _delete_target_id "
            "(paired cleanup contract)."
        )

        # 3. Go back to row A — no phantom dialog must open.
        _keep_selection(at, 0)
        at.run()
        assert at.session_state["selected_position_id"] == sid_a
        # Confirm button only exists when the dialog body is currently
        # rendered. Its absence is the pin — if the elif re-opens the
        # dialog on row A, this button would exist.
        try:
            at.button(key=DELETE_CONFIRM_KEY)
            phantom = True
        except KeyError:
            phantom = False
        assert not phantom, (
            "Phantom dialog regression: returning to row A after dismissing "
            "the dialog and switching rows must NOT re-open the dialog."
        )

    # Note: Review Fix #1 (None guard in the Confirm handler) is pure
    # defense-in-depth — it is NOT reachable through the page UI, because
    # the only entry points to the dialog body (the Delete-button click
    # and the elif re-open) both require _delete_target_id to be set.
    # The guard is cheap insurance against a future refactor that drops
    # the assignment or pops the key prematurely. Verified by code
    # inspection; no regression test is possible without bypassing the
    # dialog entry points entirely. Documented in reviews/phase-3-tier5-review.md.


# ── Pre-seed NaN coercion (T5-D/E regression) ────────────────────────────────

class TestPreSeedNaNCoercion:
    """Pin the _safe_str fix for the TypeError-on-second-row bug.

    Reproduction (2026-04-20, user-reported):
      1. Quick Add three positions with only position_name set.
      2. Select row 0; click Save on the Overview tab (writes '' into the
         row's other TEXT columns).
      3. Select row 1.
      → st.text_area / st.text_input raise
         'TypeError: bad argument type for built-in operation'.

    Root cause: database.get_all_positions returns a pandas DataFrame.
    Once any row in a TEXT column has a real string, pandas upgrades the
    column dtype to object and hands back float('nan') for the NULL
    cells on the still-blank rows. The previous pre-seed idiom
    `r[col] or ""` then mis-fires because NaN is truthy — `nan or ""`
    evaluates to `nan`, and NaN in session_state blows up Streamlit's
    protobuf str type-check at widget render.

    Fix (pages/1_Opportunities.py): _safe_str helper applied to every
    text pre-seed (position_name / institute / field / link / notes).
    """

    def test_selecting_second_row_after_save_on_first_does_not_raise(self, db):
        """The exact user-reported flow, end-to-end.

        Save-then-switch-rows must not raise; Notes text_area must render
        for the second row without a NaN landing in session_state."""
        database.add_position({"position_name": "Alpha"})
        database.add_position({"position_name": "Beta"})
        database.add_position({"position_name": "Gamma"})

        at = AppTest.from_file(PAGE)
        at.run()
        # Row 0: trigger a Save so the first row gets explicit empty
        # strings in its text columns — this is what upgrades pandas's
        # dtype to object and puts NaN in the OTHER rows' cells.
        _select_row(at, 0)
        at.button(key="edit_overview_submit").click()
        _keep_selection(at, 0)
        at.run()
        assert not at.exception, (
            f"Saving Overview on row 0 unexpectedly raised: {at.exception}"
        )

        # Row 1: this is what blew up before the fix. Post-Sub-task-13 the
        # Notes text_area only renders when active_tab == "Notes", so we
        # combine row selection + tab switch so the text_area we're checking
        # below actually renders.
        _select_row_and_tab(at, 1, "Notes")
        assert not at.exception, (
            "Selecting row 1 after saving row 0 raised — NaN pre-seed "
            "regression:\n"
            f"{at.exception}"
        )

        # Sanity: the Notes text_area rendered at all, and its value is a
        # real empty string rather than something pandas-y that would
        # have crashed proto serialisation.
        notes = at.text_area(key="edit_notes")
        assert notes is not None, "Notes text_area missing after row switch"
        assert notes.value == "", (
            f"Expected '' for unsaved Beta.notes, got {notes.value!r}"
        )

        # And row 2 for good measure — pandas hands back NaN for its
        # text cells too. Keep the active tab at "Notes" so the pre-seed
        # code path exercised is the one that bit the user (Notes text_area).
        _select_row_and_tab(at, 2, "Notes")
        assert not at.exception, (
            f"Selecting row 2 also raised (NaN pre-seed regression): "
            f"{at.exception}"
        )

    def test_safe_str_coerces_nan_and_none_to_empty_string(self):
        """Unit pin on the production _safe_str helper itself.

        If anyone ever rewrites this with `if v is None` only, this
        test catches the NaN case that the integration test above would
        also flag — but this one pinpoints the failure without
        requiring an AppTest run."""
        # Load the page module directly so we can poke at its helpers
        # without actually running the page script's top-level code.
        # pages/1_Opportunities.py does call database.init_db() at
        # import time, but that's a no-op when the schema is current
        # and uses the `db` fixture's patched DB_PATH via conftest.
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "_opp_page_module", "pages/1_Opportunities.py"
        )
        # We need _safe_str only — executing the whole page runs every
        # top-level st.* call against no AppTest context. Instead,
        # read the source and exec just the helper definition.
        src = open("pages/1_Opportunities.py", "r", encoding="utf-8").read()
        # Extract the _safe_str definition up to the next top-level `def`
        # or blank-then-non-indented line. Simpler: find the string, take
        # a slice, exec into an isolated namespace.
        marker = "def _safe_str("
        start = src.index(marker)
        # The helper ends at the next blank line followed by a
        # non-indented `def` or any non-indented code.
        end = src.index("\n\n\n", start) if "\n\n\n" in src[start:] else len(src)
        # Widen a little to capture the full def+body; looking for the
        # next top-level `def ` after our function.
        next_def = src.find("\ndef ", start + len(marker))
        if next_def != -1:
            end = min(end, next_def)
        fn_src = src[start:end]

        import math as _math
        ns: dict = {"math": _math, "Any": object}
        exec(fn_src, ns)
        _safe_str = ns["_safe_str"]

        assert _safe_str(None) == ""
        assert _safe_str(float("nan")) == ""
        assert _safe_str("") == ""
        assert _safe_str("hello") == "hello"
        assert _safe_str(42) == "42"


# ── Sub-task 13: DESIGN §8.0 + §8.2 alignment ────────────────────────────────
# Contract tests for the v1.3 alignment pass on pages/1_Opportunities.py:
#
#   • §8.0 page-config: st.set_page_config(layout="wide", ...) is the first
#     Streamlit call on every page. Pinned via source-grep (AppTest does not
#     surface set_page_config in the element tree — same precedent as
#     test_app_page.py::TestT1AEmptyDbLayout::test_page_config_sets_wide_layout).
#
#   • §8.0 Status label convention: selectboxes use format_func=STATUS_LABELS.get
#     (or an "All"-aware wrapper for the filter). UI shows labels, storage holds
#     raw bracketed values.
#
#   • §8.2 Materials-tab predicate: visibility filter uses == "Yes" (the
#     canonical REQUIREMENT_VALUES entry for a required doc). Pinned here so
#     the DESIGN-contract is enforced regardless of vocabulary rewrites.
#
#   • §8.2 Delete-button placement: button renders BELOW the tab container
#     (outside the panel box), visible ONLY when the active tab is Overview.
#     Pin the tab-sensitivity by driving at.radio(key=edit_active_tab)
#     through each of the four EDIT_PANEL_TABS and asserting Delete-button
#     presence/absence accordingly.


class TestPageConfigSetsWideLayout:
    """Source-grep pin for DESIGN §8.0 + D14."""

    def test_page_config_sets_wide_layout(self, db):
        """DESIGN §8.0 requires `st.set_page_config(layout="wide", ...)` on
        every page — the app is data-heavy (positions table + edit panel)
        and needs horizontal room.

        AppTest does not surface set_page_config in the element tree (the
        call is consumed by the page-setup phase before widgets render),
        so the contract is pinned at the source level — same precedent as
        test_app_page.py::TestT1AEmptyDbLayout::test_page_config_sets_wide_layout.
        Checking for the three keyword bindings together prevents a
        partially-correct call (layout only, title only, …) from silently
        passing.
        """
        import pathlib
        src = pathlib.Path("pages/1_Opportunities.py").read_text(encoding="utf-8")
        assert "st.set_page_config(" in src, (
            "pages/1_Opportunities.py must call st.set_page_config(...) per DESIGN §8.0."
        )
        assert 'page_title="Postdoc Tracker"' in src, (
            'set_page_config must bind page_title="Postdoc Tracker" per DESIGN §8.0.'
        )
        assert 'page_icon="📋"' in src, (
            'set_page_config must bind page_icon="📋" per DESIGN §8.0.'
        )
        assert 'layout="wide"' in src, (
            'set_page_config must bind layout="wide" per DESIGN §8.0 / D14.'
        )


class TestFilterStatusFormatFunc:
    """DESIGN §8.0 + §8.2: filter_status selectbox shows display labels while
    storing raw bracketed values. The "All" sentinel passes through unchanged
    (STATUS_LABELS.get("All", "All") returns "All" by default).

    AppTest surfaces .options as the format_func-applied display strings (per
    TestRequirementsTabWidgets::test_radio_options_display_config_labels_in_order
    precedent) and .value as the underlying raw option — so checking both
    pins the storage/display split in a single test class.
    """

    def test_filter_status_options_display_labels(self, db):
        """The filter_status selectbox's .options must be ["All"] + the
        config.STATUS_LABELS[v] for each v in config.STATUS_VALUES — NOT
        the raw bracketed values. A format_func that returns None on the
        "All" sentinel (vanilla `STATUS_LABELS.get`) would leak `None` into
        the rendered option list, so the implementation MUST wrap with a
        default that passes "All" through. This test catches that regression.
        """
        at = _run_page()
        options = list(at.selectbox(key="filter_status").options)
        expected = ["All"] + [config.STATUS_LABELS[v] for v in config.STATUS_VALUES]
        assert options == expected, (
            f"filter_status options must be display labels via format_func "
            f"(with 'All' passthrough).\n"
            f"  Expected: {expected}\n"
            f"  Got:      {options}"
        )

    def test_filter_status_value_stays_raw_on_select(self, db):
        """After selecting a specific status via the UI, the selectbox's
        .value must be the raw storage string (brackets included) — the
        filter predicate downstream compares raw values to df["status"]."""
        database.add_position({"position_name": "Alpha", "status": "[APPLIED]"})
        at = _run_page()
        at.selectbox(key="filter_status").select(config.STATUS_APPLIED)
        at.run()
        assert not at.exception
        assert at.selectbox(key="filter_status").value == config.STATUS_APPLIED, (
            f"filter_status must store the raw status value (brackets included) "
            f"so filter predicates compare storage keys; got "
            f"{at.selectbox(key='filter_status').value!r}"
        )

    def test_filter_status_round_trip_filters_correctly(self, db):
        """End-to-end: selecting the display-labelled status must narrow the
        table to rows with the corresponding raw status — storage/display
        split works transparently. The row-identity assertion pins that
        the Applied row (not the Saved row) is what survives — a wrong-
        column-compared regression would also produce count=1 here."""
        database.add_position({"position_name": "Saved Row"})                       # [SAVED] by default
        database.add_position({"position_name": "Applied Row", "status": config.STATUS_APPLIED})
        at = _run_page()
        at.selectbox(key="filter_status").select(config.STATUS_APPLIED)
        at.run()
        assert not at.exception
        # One row after filtering to Applied.
        assert len(at.caption) == 1
        assert "1 position(s)" in at.caption[0].value, (
            f"Expected exactly 1 applied row after filter, got: "
            f"{at.caption[0].value!r}"
        )
        names = list(at.dataframe[0].value["position_name"])
        assert names == ["Applied Row"], (
            f"Filter=Applied must retain 'Applied Row' only, not 'Saved Row'; "
            f"got {names!r}"
        )


class TestEditStatusFormatFunc:
    """DESIGN §8.0 + §8.2: the Overview form's Status selectbox shows display
    labels (format_func=config.STATUS_LABELS.get) while storing raw bracketed
    values — mirrors the filter_status contract, minus the "All" sentinel.
    """

    def test_edit_status_options_display_labels(self, db):
        """The edit_status selectbox's .options must be the ordered
        config.STATUS_LABELS[v] for each v in config.STATUS_VALUES — NOT
        the raw bracketed values."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        options = list(at.selectbox(key=EDIT_KEYS["status"]).options)
        expected = [config.STATUS_LABELS[v] for v in config.STATUS_VALUES]
        assert options == expected, (
            f"edit_status options must be display labels via format_func.\n"
            f"  Expected: {expected}\n"
            f"  Got:      {options}"
        )

    def test_edit_status_value_stays_raw_on_select(self, db):
        """After selecting a specific status on the Overview form, the
        selectbox's .value must be the raw storage string — the Save
        handler writes the raw value into positions.status."""
        database.add_position({"position_name": "Alpha", "status": config.STATUS_SAVED})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        at.selectbox(key=EDIT_KEYS["status"]).select(config.STATUS_APPLIED)
        # Selection rerun needs the row kept (AppTest's on_select='rerun'
        # single-run contract — see `_keep_selection` docstring) so the
        # Overview form re-renders and the selectbox is reachable.
        _keep_selection(at, 0)
        at.run()
        assert not at.exception
        assert at.selectbox(key=EDIT_KEYS["status"]).value == config.STATUS_APPLIED, (
            f"edit_status must store the raw status value (brackets included) "
            f"so Save writes the storage key; got "
            f"{at.selectbox(key=EDIT_KEYS['status']).value!r}"
        )


class TestStatusColumnDisplaysLabels:
    """DESIGN §8.0 + §8.2: the positions table's Status column must render
    `config.STATUS_LABELS[raw]` ("Saved", "Applied", ...), never the raw
    bracketed storage value ("[SAVED]", "[APPLIED]", ...). The raw
    `status` column stays on the underlying df for selection plumbing
    (row-index → id) but is never shown to the user — DESIGN §8.0:
    "Pages never render a raw status value".

    Implemented by deriving `df_display["status_label"] = df_display[
    "status"].map(config.STATUS_LABELS)` and swapping `status` →
    `status_label` in both `display_cols` (column_order) and
    `column_config`. AppTest surfaces `st.dataframe(..., column_order=...)`
    as `at.dataframe[0].proto.column_order`, so we pin the displayed set
    directly; cell values come from `at.dataframe[0].value`.
    """

    def test_status_label_is_in_display_order_not_raw_status(self, db):
        """Displayed columns must include `status_label` and must NOT
        include raw `status`. Pins DESIGN §8.0's "UI never renders raw
        storage values" contract at the column-order level so a silent
        revert to the raw column on a future edit trips the test."""
        database.add_position({"position_name": "Pin"})
        at = _run_page()
        order = list(at.dataframe[0].proto.column_order)
        assert "status_label" in order, (
            f"Displayed columns must include 'status_label' per DESIGN §8.2 "
            f"('Status column displays STATUS_LABELS[raw]'); got {order}"
        )
        assert "status" not in order, (
            f"Displayed columns must NOT include raw 'status' per DESIGN §8.0 "
            f"('Pages never render a raw status value'); got {order}"
        )

    def test_status_label_column_values_are_human_labels(self, db):
        """For a position stored with status='[APPLIED]', the rendered
        `status_label` cell must equal STATUS_LABELS['[APPLIED]'] ==
        'Applied' — never the raw bracketed form. The negative pin on
        the bracketed value catches a future regression where someone
        aliases `status_label` back to `status`."""
        database.add_position(
            {"position_name": "LabelPin", "status": config.STATUS_APPLIED}
        )
        at = _run_page()
        df = at.dataframe[0].value
        row = df[df["position_name"] == "LabelPin"]
        assert len(row) == 1, f"Expected one row for LabelPin, got {len(row)}"
        cell = row["status_label"].iloc[0]
        expected = config.STATUS_LABELS[config.STATUS_APPLIED]
        assert cell == expected, (
            f"status_label must equal STATUS_LABELS[{config.STATUS_APPLIED!r}] "
            f"({expected!r}); got {cell!r}"
        )
        assert cell != config.STATUS_APPLIED, (
            f"status_label must not equal the raw bracketed storage value "
            f"{config.STATUS_APPLIED!r} — DESIGN §8.0 forbids raw values in UI."
        )

    @pytest.mark.parametrize("raw_status", config.STATUS_VALUES)
    def test_status_label_covers_every_status_value(self, db, raw_status):
        """Parametrized over every entry in config.STATUS_VALUES: each
        raw status must map to its labelled form in the rendered
        `status_label` column. Config invariant #3 covers the map
        itself; this pins the page-side wiring so a new pipeline stage
        cannot ship without its column_label surface."""
        pos_name = f"Pin-{raw_status}"
        database.add_position({"position_name": pos_name, "status": raw_status})
        at = _run_page()
        df = at.dataframe[0].value
        row = df[df["position_name"] == pos_name]
        assert len(row) == 1
        expected = config.STATUS_LABELS[raw_status]
        assert row["status_label"].iloc[0] == expected, (
            f"status_label for raw={raw_status!r} must be {expected!r}; "
            f"got {row['status_label'].iloc[0]!r}"
        )


class TestMaterialsFilterPredicateIsYes:
    """DESIGN §8.2 Materials-tab row: visibility filter is `session_state[
    f"edit_{req_col}"] == "Yes"`. Pinned here independent of Sub-task 2's
    own migration tests — this is the DESIGN-contract anchor for "Materials
    shows a doc iff its requirement is marked Required"."""

    def test_materials_tab_shows_only_docs_required_via_yes(self, db):
        """Seed a position with mixed req_* values (Yes / Optional / No)
        and assert the Materials tab renders checkboxes ONLY for the ones
        whose session_state value is 'Yes'."""
        database.add_position({
            "position_name":       "Alpha",
            "req_cv":              "Yes",        # visible
            "req_cover_letter":    "Optional",   # hidden
            "req_transcripts":     "No",         # hidden
            "req_writing_sample":  "Yes",        # visible
        })
        at = AppTest.from_file(PAGE)
        at.run()
        # Switch to Materials tab so its body renders. _select_row_and_tab
        # handles the two-piece state (row selection + active tab) in one
        # rerun so the Materials-tab code path is exercised.
        _select_row_and_tab(at, 0, "Materials")
        assert not at.exception, f"Page raised after tab switch: {at.exception}"
        # CV + Writing Sample visible (req == "Yes"); Cover Letter (Optional)
        # and Transcripts (No) hidden. _checkbox_rendered is defined earlier
        # in the test module for exactly this kind of conditional-widget check.
        assert _checkbox_rendered(at, "edit_done_cv"), (
            "req_cv='Yes' must render a Materials-tab checkbox"
        )
        assert _checkbox_rendered(at, "edit_done_writing_sample"), (
            "req_writing_sample='Yes' must render a Materials-tab checkbox"
        )
        assert not _checkbox_rendered(at, "edit_done_cover_letter"), (
            "req_cover_letter='Optional' must NOT render a Materials-tab checkbox "
            "(predicate is strictly == 'Yes' per DESIGN §8.2)"
        )
        assert not _checkbox_rendered(at, "edit_done_transcripts"), (
            "req_transcripts='No' must NOT render a Materials-tab checkbox"
        )


# ── Delete-button tab-sensitivity (DESIGN §8.2) ──────────────────────────────
# DESIGN §8.2 Delete row: "Button rendered below the edit panel (outside the
# panel box), visible only when the active tab is Overview." Pre-Sub-task-13
# the Delete button lived inside `with tabs[0]:` — the user never saw it
# on non-Overview tabs (Streamlit's tab CSS hid it) but the button was still
# in the DOM and clickable via AppTest regardless of active tab. Sub-task 13
# moves the button BELOW the tab selector and gates its render on
# session_state["edit_active_tab"] == "Overview", matching DESIGN's intent:
# the button's scope is the whole position, so it only shows up on the tab
# where the user reviews the position as a whole.

def _delete_button_rendered(at: AppTest) -> bool:
    """True iff the Overview Delete button (key=edit_delete) is on the page.

    Mirrors _tab_selector_rendered / _checkbox_rendered — AppTest raises
    KeyError for absent widget lookups, so the helper wraps the try/except."""
    try:
        at.button(key=DELETE_BUTTON_KEY)
        return True
    except KeyError:
        return False


class TestDeleteButtonTabSensitivity:

    def test_delete_visible_when_active_tab_is_overview(self, db):
        """With default tab selection (Overview, the first EDIT_PANEL_TABS
        entry and the st.radio default), the Delete button must render
        beneath the tab selector."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert not at.exception
        # Precondition: default active tab is Overview.
        assert at.radio(key=TAB_SELECTOR_KEY).value == "Overview", (
            "Precondition: initial active tab should default to 'Overview'"
        )
        assert _delete_button_rendered(at), (
            "Delete button must render when active tab is Overview "
            "(DESIGN §8.2)"
        )

    def test_delete_absent_when_active_tab_is_requirements(self, db):
        """Switching to Requirements via the tab selector must remove the
        Delete button from the page — the button's scope is the whole
        position, not the tab's data, so it only belongs on Overview."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Requirements")
        assert not at.exception, f"Page raised after switch to Requirements: {at.exception}"
        assert at.radio(key=TAB_SELECTOR_KEY).value == "Requirements"
        assert not _delete_button_rendered(at), (
            "Delete button must NOT render when active tab is Requirements "
            "(DESIGN §8.2 — Delete is Overview-only)"
        )

    def test_delete_absent_when_active_tab_is_materials(self, db):
        """Switching to Materials via the tab selector must remove the
        Delete button from the page."""
        database.add_position({"position_name": "Alpha", "req_cv": "Yes"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Materials")
        assert not at.exception, f"Page raised after switch to Materials: {at.exception}"
        assert at.radio(key=TAB_SELECTOR_KEY).value == "Materials"
        assert not _delete_button_rendered(at), (
            "Delete button must NOT render when active tab is Materials "
            "(DESIGN §8.2 — Delete is Overview-only)"
        )

    def test_delete_absent_when_active_tab_is_notes(self, db):
        """Switching to Notes via the tab selector must remove the Delete
        button from the page."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row_and_tab(at, 0, "Notes")
        assert not at.exception, f"Page raised after switch to Notes: {at.exception}"
        assert at.radio(key=TAB_SELECTOR_KEY).value == "Notes"
        assert not _delete_button_rendered(at), (
            "Delete button must NOT render when active tab is Notes "
            "(DESIGN §8.2 — Delete is Overview-only)"
        )

    def test_delete_reappears_when_returning_to_overview(self, db):
        """Round-trip: user switches away from Overview (Delete hides), then
        back (Delete reappears). Pins both directions of the gating."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        # Away
        _select_row_and_tab(at, 0, "Notes")
        assert not _delete_button_rendered(at)   # precondition
        # Back
        _select_row_and_tab(at, 0, "Overview")
        assert not at.exception
        assert _delete_button_rendered(at), (
            "Delete button must render again when user returns to Overview"
        )


# ── Tab-switch widget-state survival (Bug 1 + Bug 2 repro, 2026-04-25) ───────
# User-reported bugs:
#   • Bug 1: Position name disappears in Overview after switching to
#     Requirements and back. Same on second opportunity.
#   • Bug 2: Requirements tab shows every doc as "Required" (not the DB's
#     "No" default). Materials shows all 7 checkboxes; checking CV +
#     Saving leaves only 6, with CV gone.
#
# Hypothesis: Sub-task 13's conditional tab rendering means each tab body
# unmounts its widgets when the user switches tabs. Streamlit's documented
# v1.20+ behaviour: session_state for unmounted widgets is cleaned up. The
# pre-seed at pages/1_Opportunities.py is gated by `_edit_form_sid != sid`
# — runs only on row CHANGE, not on tab switch. So returning to a previously-
# active tab finds its widgets bereft of session_state and they fall back
# to the widget's default value (empty for text_input, index=0 for radio).
#
# These tests pin both the buggy behaviour today (so a fix lands as a
# behaviour change) AND the corrected contract once the fix is in.

class TestTabSwitchWidgetStateSurvival:
    """Diagnostic + regression coverage for the widget-state-loss-on-tab-
    switch family of bugs. Each test exercises one tab-switch sequence
    and pins the value the user MUST see after the switch."""

    # --- Baseline: first open of each tab ----------------------------------

    def test_overview_position_name_visible_on_initial_selection(self, db):
        """Sanity baseline: selecting a row must populate the Overview
        position name on the first script run (no tab switch yet)."""
        database.add_position({"position_name": "Stanford BioStats"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        assert at.text_input(key=EDIT_KEYS["position_name"]).value == "Stanford BioStats"

    def test_requirements_radios_show_db_value_on_first_tab_open(self, db):
        """First open of Requirements (after default-Overview render) must
        display the DB's req_* values. Schema default is 'No' (Not needed).
        If this fails on first open, Streamlit's cleanup is more aggressive
        than the 'unmount → cleanup' rule (it would mean programmatic-only
        session_state writes are also cleaned up). If it passes, the bug
        only fires on the SECOND open of Requirements (after a round-trip
        causes the widgets to mount-then-unmount)."""
        database.add_position({"position_name": "Alpha"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        _select_row_and_tab(at, 0, "Requirements")
        for req_col, _, _ in config.REQUIREMENT_DOCS:
            value = at.radio(key=_req_key(req_col)).value
            assert value == "No", (
                f"First open of Requirements: radio {req_col!r} must show "
                f"DB default 'No', got {value!r}. If failing here, "
                f"Streamlit cleans up session_state for widget keys whose "
                f"widgets have NOT YET been mounted (more aggressive than "
                f"the documented 'mount-then-unmount' rule)."
            )

    # --- Bug 1: Overview position name across round-trip --------------------

    def test_overview_position_name_persists_after_requirements_round_trip(self, db):
        """Bug 1 repro. Sequence: select row → switch to Requirements →
        switch back to Overview. The position name MUST still be the
        row's value, not "" (the text_input default after Streamlit
        cleaned up session_state on the Overview tab unmount)."""
        database.add_position({"position_name": "Stanford BioStats"})
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        # Round-trip: Overview → Requirements → Overview.
        _select_row_and_tab(at, 0, "Requirements")
        _select_row_and_tab(at, 0, "Overview")
        value = at.text_input(key=EDIT_KEYS["position_name"]).value
        assert value == "Stanford BioStats", (
            f"Bug 1: position name disappeared after Overview→Requirements"
            f"→Overview round-trip. Got {value!r}. Streamlit cleans up "
            f"session_state for unmounted widgets; the pre-seed gate "
            f"(_edit_form_sid == sid) blocked re-seeding on the same row."
        )

    def test_overview_all_text_fields_persist_after_round_trip(self, db):
        """Stronger Bug 1 pin: every text_input on Overview (position_name,
        institute, field, link) AND the work_auth_note text_area must
        survive an Overview→Notes→Overview round-trip with their DB
        values intact, not collapse to ""."""
        database.add_position({
            "position_name":  "Stanford BioStats",
            "institute":      "Stanford",
            "field":          "Biostatistics",
            "link":           "https://example.org/apply",
            "work_auth_note": "OPT eligible",
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        _select_row_and_tab(at, 0, "Notes")
        _select_row_and_tab(at, 0, "Overview")
        assert at.text_input(key=EDIT_KEYS["position_name"]).value == "Stanford BioStats"
        assert at.text_input(key=EDIT_KEYS["institute"]).value     == "Stanford"
        assert at.text_input(key=EDIT_KEYS["field"]).value         == "Biostatistics"
        assert at.text_input(key=EDIT_KEYS["link"]).value          == "https://example.org/apply"
        assert at.text_area(key=EDIT_KEYS["work_auth_note"]).value == "OPT eligible"

    # --- Bug 2: Requirements radios across round-trip -----------------------

    def test_requirements_radios_persist_after_overview_round_trip(self, db):
        """Bug 2 repro. Sequence: select row → switch to Requirements
        (radios mount with DB values) → switch to Overview (radios
        unmount → Streamlit cleans up their session_state) → switch back
        to Requirements. The radios MUST still show the DB's "No"
        (Not needed) for every doc, not the 'Yes' (Required) that
        index=0 would default to."""
        database.add_position({"position_name": "Alpha"})  # all req_* default to 'No'
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        _select_row_and_tab(at, 0, "Requirements")  # First open: widgets mount
        _select_row_and_tab(at, 0, "Overview")      # Widgets unmount → cleanup
        _select_row_and_tab(at, 0, "Requirements")  # Widgets remount → ???
        for req_col, _, _ in config.REQUIREMENT_DOCS:
            value = at.radio(key=_req_key(req_col)).value
            assert value == "No", (
                f"Bug 2: req radio {req_col!r} must show DB value 'No' "
                f"after Requirements→Overview→Requirements round-trip; "
                f"got {value!r}. Streamlit cleaned up the radio's "
                f"session_state when it unmounted on Overview, and the "
                f"pre-seed gate blocked the re-seed."
            )

    def test_notes_text_area_persists_after_round_trip(self, db):
        """Bug 1 / 2 cross-check: the Notes tab's text_area must survive
        a Notes→Overview→Notes round-trip with its DB value intact."""
        database.add_position({
            "position_name": "Alpha",
            "notes":         "Follow up with Prof. Smith after SfN.",
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        _select_row_and_tab(at, 0, "Notes")
        _select_row_and_tab(at, 0, "Overview")
        _select_row_and_tab(at, 0, "Notes")
        value = at.text_area(key=NOTES_KEY).value
        assert value == "Follow up with Prof. Smith after SfN.", (
            f"Bug-class repro on Notes tab: text_area lost its DB value "
            f"after Notes→Overview→Notes round-trip; got {value!r}."
        )

    def test_user_reported_two_opportunity_scenario(self, db):
        """Verbatim user-reported scenario (2026-04-25):

          1. Add two opportunities.
          2. Click first one → Overview shows position name.
          3. Click Requirements tab.
          4. Switch back to Overview → position name MUST still appear.
          5. Click the second opportunity → same expectations.

        Extends the per-tab round-trip tests above by also exercising
        the user's 'switch to a different opportunity' transition,
        which exercises both the cleanup-recovery path AND the
        row-change force-reseed path in the new two-phase pre-seed.
        """
        sid_a = database.add_position({"position_name": "Stanford BioStats"})
        sid_b = database.add_position({"position_name": "MIT CSAIL Postdoc"})
        at = AppTest.from_file(PAGE)
        at.run()

        # Step 2: select Alpha (row 0 — both have NULL deadline so the
        # tiebreak is by id ASC, sid_a is first).
        _select_row(at, 0)
        assert at.session_state["selected_position_id"] == sid_a
        assert at.text_input(key=EDIT_KEYS["position_name"]).value == "Stanford BioStats"

        # Steps 3-4: round-trip Overview → Requirements → Overview on Alpha.
        _select_row_and_tab(at, 0, "Requirements")
        _select_row_and_tab(at, 0, "Overview")
        assert at.text_input(key=EDIT_KEYS["position_name"]).value == "Stanford BioStats", (
            "User-reported Bug 1 on first opportunity: position name lost "
            "after Overview→Requirements→Overview round-trip"
        )

        # Step 5: switch to Beta (row 1).
        _select_row_and_tab(at, 1, "Overview")
        assert at.session_state["selected_position_id"] == sid_b
        assert at.text_input(key=EDIT_KEYS["position_name"]).value == "MIT CSAIL Postdoc", (
            "Switching to second opportunity must show its position name "
            "(force-reseed path: sid changed, pre-seed overwrites all keys)"
        )

        # Round-trip on Beta too.
        _select_row_and_tab(at, 1, "Requirements")
        _select_row_and_tab(at, 1, "Overview")
        assert at.text_input(key=EDIT_KEYS["position_name"]).value == "MIT CSAIL Postdoc", (
            "User-reported Bug 1 on second opportunity: position name lost "
            "after Overview→Requirements→Overview round-trip on the second "
            "selected row"
        )

    def test_materials_save_does_not_strand_visible_checkbox_set(self, db):
        """Bug 2 second-half repro. Sequence: open a row whose req_cv was
        EVER set to 'Yes' (so Materials shows the CV checkbox); switch
        Requirements→Materials, tick CV, click Save. After the save's
        rerun, CV must STILL be visible (req_cv is still 'Yes' in DB,
        Materials Save doesn't touch req_*). The user reported CV
        disappearing post-save — the only way that can happen is if the
        pre-seed re-loaded edit_req_cv as something other than 'Yes',
        which means the radio's session_state had drifted out of sync
        with DB during the round-trip."""
        sid = database.add_position({
            "position_name": "Alpha",
            "req_cv":        "Yes",   # CV is required by the row
        })
        at = AppTest.from_file(PAGE)
        at.run()
        _select_row(at, 0)
        _select_row_and_tab(at, 0, "Requirements")
        _select_row_and_tab(at, 0, "Materials")
        # Precondition: CV checkbox is visible because req_cv == 'Yes'.
        assert _checkbox_rendered(at, _done_key("done_cv")), (
            "Precondition failed: req_cv='Yes' must render done_cv checkbox"
        )
        at.checkbox(key=_done_key("done_cv")).set_value(True)
        at.button(key=MATERIALS_SUBMIT_KEY).click()
        _keep_selection(at, 0)
        at.run()
        assert not at.exception, f"Materials save raised: {at.exception}"
        # Post-save: req_cv is still 'Yes' in DB, so the CV checkbox
        # MUST still render. If the pre-seed reloaded req_cv as 'No'
        # (because the round-trip stranded session_state), CV would
        # disappear from the visible list — exactly the user's report.
        row = database.get_position(sid)
        assert row["req_cv"] == "Yes", (
            f"Materials Save must NOT alter req_*; got "
            f"req_cv={row['req_cv']!r} in DB"
        )
        assert _checkbox_rendered(at, _done_key("done_cv")), (
            "Bug 2: CV checkbox vanished after Materials Save even though "
            "req_cv is still 'Yes' in DB. The pre-seed must have reloaded "
            "session_state[edit_req_cv] as something != 'Yes' on the post-"
            "save rerun, which means edit_req_cv was already drifted by "
            "the time Materials rendered."
        )
