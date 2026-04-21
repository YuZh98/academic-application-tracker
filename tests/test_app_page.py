# tests/test_app_page.py
# Integration tests for app.py (dashboard home) using Streamlit AppTest.
#
# One test file covers every Phase 4 tier (per PHASE_4_GUIDELINES.md §C8 —
# "One test file for the whole dashboard"). Classes are named TestT<N><Tier>
# and grow as each tier lands.
#
# Uses the shared `db` fixture from tests/conftest.py so each test runs
# against a fresh temp SQLite DB. Never touches postdoc.db.

from streamlit.testing.v1 import AppTest

PAGE = "app.py"

# DESIGN.md §app.py — Dashboard (Home) locks these four KPI labels as part
# of the UI contract. Tests assert on labels (not on implementation-detail
# keys) because st.metric has no `key=` parameter in Streamlit 1.56 and
# `label` is the idiomatic AppTest lookup path for display-only elements.
KPI_LABELS = ["Tracked", "Applied", "Interview", "Next Interview"]


def _run_page() -> AppTest:
    """Return a freshly-run AppTest for the dashboard.

    Call after the `db` fixture has patched database.DB_PATH."""
    at = AppTest.from_file(PAGE, default_timeout=10)
    at.run()
    assert not at.exception, f"Page raised an exception: {at.exception}"
    return at


# ── T1: App shell + KPI grid ──────────────────────────────────────────────────

class TestT1AppShell:
    """T1-A + T1-B: smoke test on an empty DB, and the 4-column KPI skeleton.

    Only structure is checked here — concrete KPI values come in T1-C/D."""

    def test_page_loads_on_empty_db(self, db):
        """Dashboard must render without exception against an empty DB."""
        at = _run_page()
        titles = [el.value for el in at.title]
        assert "Postdoc Tracker" in titles, (
            f"Expected page title 'Postdoc Tracker', got: {titles}"
        )

    def test_page_has_four_kpi_columns(self, db):
        """Dashboard must render exactly 4 KPI cards with the spec'd labels."""
        at = _run_page()
        assert len(at.metric) == 4, (
            f"Expected 4 st.metric cards, got {len(at.metric)}"
        )
        labels = [m.label for m in at.metric]
        assert labels == KPI_LABELS, (
            f"Expected KPI labels in order {KPI_LABELS}, got {labels}"
        )
