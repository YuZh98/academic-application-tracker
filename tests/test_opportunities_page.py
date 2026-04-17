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

# Auto-generated key for st.form_submit_button inside st.form("quick_add_form")
SUBMIT_KEY = "FormSubmitter:quick_add_form-+ Add Position"


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
        assert at.success, "Expected st.success after a valid quick-add submission"

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
