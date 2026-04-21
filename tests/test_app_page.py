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

import config
import database
from tests.conftest import make_position

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


# ── T1-C: KPI count wiring + refresh button ───────────────────────────────────

class TestT1CKpiCountsAndRefresh:
    """T1-C: wire `count_by_status()` into Tracked / Applied / Interview and
    expose a top-bar 🔄 refresh button (DESIGN.md §app.py; C3 locked).

    Decision: Tracked = count([OPEN]) + count([APPLIED]) — the pool of
    positions that 'might still move forward'. Applied and Interview are
    single-bucket counts of their namesake status. Next Interview stays
    '—' until T1-D wires get_upcoming_interviews().
    """

    @staticmethod
    def _kpis(at: AppTest) -> dict[str, str]:
        """Return {label: str(value)} for every KPI card on the page."""
        return {m.label: str(m.value) for m in at.metric}

    def test_empty_db_shows_zero_counts(self, db):
        """Empty DB: Tracked/Applied/Interview read '0'; Next Interview still '—'."""
        at = _run_page()
        kpis = self._kpis(at)
        assert kpis["Tracked"] == "0", f"Tracked on empty DB should be 0, got {kpis['Tracked']!r}"
        assert kpis["Applied"] == "0", f"Applied on empty DB should be 0, got {kpis['Applied']!r}"
        assert kpis["Interview"] == "0", f"Interview on empty DB should be 0, got {kpis['Interview']!r}"
        assert kpis["Next Interview"] == "—", (
            f"Next Interview is T1-D's to wire; should still be em-dash, got {kpis['Next Interview']!r}"
        )

    def test_tracked_equals_open_plus_applied(self, db):
        """Tracked = count([OPEN]) + count([APPLIED]); INTERVIEW/OFFER are not 'tracked'."""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        database.add_position(make_position({"position_name": "B", "status": "[OPEN]"}))
        database.add_position(make_position({"position_name": "C", "status": "[APPLIED]"}))
        database.add_position(make_position({"position_name": "D", "status": "[INTERVIEW]"}))
        database.add_position(make_position({"position_name": "E", "status": "[OFFER]"}))

        at = _run_page()
        kpis = self._kpis(at)
        assert kpis["Tracked"] == "3", (
            f"Tracked should count 2 OPEN + 1 APPLIED = 3, got {kpis['Tracked']!r}"
        )

    def test_applied_count_excludes_other_statuses(self, db):
        """Applied reflects the [APPLIED] bucket only — not OPEN, INTERVIEW, OFFER."""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        database.add_position(make_position({"position_name": "B", "status": "[APPLIED]"}))
        database.add_position(make_position({"position_name": "C", "status": "[APPLIED]"}))
        database.add_position(make_position({"position_name": "D", "status": "[INTERVIEW]"}))

        at = _run_page()
        kpis = self._kpis(at)
        assert kpis["Applied"] == "2", f"Applied should be 2, got {kpis['Applied']!r}"

    def test_interview_count_excludes_other_statuses(self, db):
        """Interview reflects the [INTERVIEW] bucket only."""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        database.add_position(make_position({"position_name": "B", "status": "[INTERVIEW]"}))
        database.add_position(make_position({"position_name": "C", "status": "[OFFER]"}))

        at = _run_page()
        kpis = self._kpis(at)
        assert kpis["Interview"] == "1", f"Interview should be 1, got {kpis['Interview']!r}"

    def test_terminal_statuses_are_not_tracked(self, db):
        """Positions in TERMINAL_STATUSES are neither tracked nor applied nor interviewing."""
        for term in config.TERMINAL_STATUSES:
            database.add_position(
                make_position({"position_name": f"P-{term}", "status": term})
            )

        at = _run_page()
        kpis = self._kpis(at)
        assert kpis["Tracked"] == "0", (
            f"Terminal statuses must not inflate Tracked, got {kpis['Tracked']!r}"
        )
        assert kpis["Applied"] == "0"
        assert kpis["Interview"] == "0"

    def test_refresh_button_rendered(self, db):
        """Top bar exposes a 🔄 refresh button (DESIGN.md §app.py; C3 locked)."""
        at = _run_page()
        refresh = [b for b in at.button if "Refresh" in b.label]
        assert len(refresh) == 1, (
            f"Expected exactly one Refresh button, got labels {[b.label for b in at.button]}"
        )
        assert "🔄" in refresh[0].label, (
            f"Refresh button should carry the 🔄 glyph per DESIGN wireframe, "
            f"got {refresh[0].label!r}"
        )

    def test_refresh_button_rerenders_with_updated_counts(self, db):
        """Clicking Refresh picks up rows added since the last render."""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))

        at = _run_page()
        assert self._kpis(at)["Tracked"] == "1"

        # Simulate: another position lands (e.g., via the Opportunities page
        # in another tab). The dashboard shouldn't know about it until a rerun.
        database.add_position(make_position({"position_name": "B", "status": "[APPLIED]"}))

        refresh = next(b for b in at.button if "Refresh" in b.label)
        refresh.click().run()
        assert not at.exception, f"Refresh click raised: {at.exception}"

        kpis = self._kpis(at)
        assert kpis["Tracked"] == "2", f"After refresh, Tracked should be 2, got {kpis['Tracked']!r}"
        assert kpis["Applied"] == "1", f"After refresh, Applied should be 1, got {kpis['Applied']!r}"
