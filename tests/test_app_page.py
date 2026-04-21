# tests/test_app_page.py
# Integration tests for app.py (dashboard home) using Streamlit AppTest.
#
# One test file covers every Phase 4 tier (per PHASE_4_GUIDELINES.md §C8 —
# "One test file for the whole dashboard"). Classes are named TestT<N><Tier>
# and grow as each tier lands.
#
# Uses the shared `db` fixture from tests/conftest.py so each test runs
# against a fresh temp SQLite DB. Never touches postdoc.db.

from datetime import date, timedelta

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


# ── T1-D: Next Interview KPI — wire get_upcoming_interviews() ─────────────────

class TestT1DNextInterviewKpi:
    """T1-D: wire database.get_upcoming_interviews() into the Next Interview
    KPI card per DESIGN.md §app.py; '—' on empty per locked decision U3.

    User decisions (2026-04-21):
    - Value format: "{Mon D} · {institute}" (e.g. 'May 3 · MIT') — short
      month + day, no year, with institute.
    - Selection: take the EARLIEST future date across interview1_date AND
      interview2_date across all rows. The paired institute belongs to
      whichever position owns that winning date.
    - No upcoming interview anywhere → '—'.

    The underlying query (database.get_upcoming_interviews) returns each
    position as one row with two date columns, and a row is included when
    EITHER date is future — so the other may be in the past. The SQL
    ORDER BY sorts by interview1_date then interview2_date, which means
    'earliest future date' is not necessarily the first row's first column.
    The selection test cases below pin that.
    """

    @staticmethod
    def _next(at: AppTest) -> str:
        return next(str(m.value) for m in at.metric if m.label == "Next Interview")

    @staticmethod
    def _expected(d: date, institute: str) -> str:
        """The agreed Next-Interview format: '{Mon D} · {institute}'."""
        return f"{d.strftime('%b')} {d.day} · {institute}"

    def test_empty_db_shows_em_dash(self, db):
        at = _run_page()
        assert self._next(at) == "—", (
            f"Empty DB must show '—' per U3, got {self._next(at)!r}"
        )

    def test_position_without_interview_dates_shows_em_dash(self, db):
        """A tracked position with no application/interview rows scheduled
        must leave the Next Interview KPI empty."""
        database.add_position(make_position({"position_name": "P", "institute": "Stanford"}))
        at = _run_page()
        assert self._next(at) == "—"

    def test_all_past_interviews_show_em_dash(self, db):
        """If every seeded interview date is in the past, nothing is upcoming."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        pid = database.add_position(
            make_position({"position_name": "P", "institute": "Stanford"})
        )
        database.upsert_application(
            pid, {"interview1_date": yesterday, "interview2_date": yesterday}
        )
        at = _run_page()
        assert self._next(at) == "—"

    def test_single_upcoming_interview_formats_date_and_institute(self, db):
        """One upcoming interview → '{Mon D} · {institute}'."""
        d_future = date.today() + timedelta(days=10)
        pid = database.add_position(
            make_position({"position_name": "BioStats Postdoc", "institute": "MIT"})
        )
        database.upsert_application(pid, {"interview1_date": d_future.isoformat()})

        at = _run_page()
        assert self._next(at) == self._expected(d_future, "MIT"), (
            f"Expected {self._expected(d_future, 'MIT')!r}, got {self._next(at)!r}"
        )

    def test_earliest_among_positions_wins(self, db):
        """Across positions, the earliest future date wins — and it carries
        its own position's institute."""
        d_early = date.today() + timedelta(days=5)
        d_late  = date.today() + timedelta(days=20)
        pid_a = database.add_position(
            make_position({"position_name": "A", "institute": "Stanford"})
        )
        pid_b = database.add_position(
            make_position({"position_name": "B", "institute": "MIT"})
        )
        database.upsert_application(pid_a, {"interview1_date": d_late.isoformat()})
        database.upsert_application(pid_b, {"interview1_date": d_early.isoformat()})

        at = _run_page()
        assert self._next(at) == self._expected(d_early, "MIT")

    def test_interview2_date_beats_another_rows_interview1(self, db):
        """Columns are symmetric: an interview2_date that's earlier than
        another row's interview1_date wins, with its own row's institute."""
        d_near = date.today() + timedelta(days=3)
        d_far  = date.today() + timedelta(days=30)
        pid_a = database.add_position(
            make_position({"position_name": "A", "institute": "Stanford"})
        )
        pid_b = database.add_position(
            make_position({"position_name": "B", "institute": "MIT"})
        )
        database.upsert_application(pid_a, {"interview2_date": d_near.isoformat()})
        database.upsert_application(pid_b, {"interview1_date": d_far.isoformat()})

        at = _run_page()
        assert self._next(at) == self._expected(d_near, "Stanford")

    def test_past_date_in_same_row_is_ignored(self, db):
        """Regression guard: a row with interview1_date=past and
        interview2_date=future-far must NOT win over another position
        whose interview1_date is future-near. Picking blindly by column
        (or by row order) would mis-pick the past date."""
        past      = (date.today() - timedelta(days=7)).isoformat()
        d_far     = (date.today() + timedelta(days=25)).isoformat()
        d_near    = date.today() + timedelta(days=3)
        pid_a = database.add_position(
            make_position({"position_name": "A", "institute": "Stanford"})
        )
        pid_b = database.add_position(
            make_position({"position_name": "B", "institute": "MIT"})
        )
        database.upsert_application(
            pid_a, {"interview1_date": past, "interview2_date": d_far}
        )
        database.upsert_application(pid_b, {"interview1_date": d_near.isoformat()})

        at = _run_page()
        assert self._next(at) == self._expected(d_near, "MIT"), (
            "Earliest FUTURE date across both columns should win; past "
            "dates must not beat a later-but-future date from another row."
        )


# ── T1-E: fully-empty-DB hero callout + CTA into Opportunities ────────────────

class TestT1EEmptyDbHero:
    """T1-E: hero panel above the KPI grid when Tracked + Applied + Interview
    are all zero, with a CTA that `st.switch_page()`s to the Opportunities
    page. Per locked decision U5 (PHASE_4_GUIDELINES.md).

    Trigger semantics: all three counted-KPI buckets read zero. A DB that
    contains only terminal-status rows ([CLOSED]/[REJECTED]/[DECLINED])
    satisfies this too — the test_terminal_only_db_still_shows_hero case
    pins that behaviour explicitly so any future refactor (e.g. switching
    the trigger to 'total positions == 0') shows up as a test change.

    CTA discoverability: tests look for the button by label, not by key —
    same AppTest convention used elsewhere in this file.
    """

    CTA_LABEL = "+ Add your first position"
    HERO_TARGET_PAGE = "pages/1_Opportunities.py"

    @staticmethod
    def _has_cta(at: AppTest) -> bool:
        return any(
            b.label == TestT1EEmptyDbHero.CTA_LABEL for b in at.button
        )

    @staticmethod
    def _hero_heading_rendered(at: AppTest) -> bool:
        """Heuristic: the hero places a subheader above the KPI grid. We
        don't pin the exact copy (it may be tuned in Phase 7 polish) but
        we do require *some* subheader — the KPI-only render has none."""
        return len(at.subheader) >= 1

    def test_empty_db_renders_hero_with_cta(self, db):
        """Fresh DB: hero + CTA are visible."""
        at = _run_page()
        assert self._has_cta(at), (
            f"Expected a CTA button labelled {self.CTA_LABEL!r} on an empty DB. "
            f"Got labels: {[b.label for b in at.button]}"
        )
        assert self._hero_heading_rendered(at), (
            "Expected a hero subheader above the KPI grid on an empty DB."
        )

    def test_kpi_grid_still_renders_beneath_hero(self, db):
        """Hero does not replace the KPI grid — it sits above it."""
        at = _run_page()
        assert len(at.metric) == 4, (
            f"KPI grid must still render beneath the hero, got {len(at.metric)} metrics"
        )
        labels = [m.label for m in at.metric]
        assert labels == KPI_LABELS, (
            f"KPI labels unchanged on empty-DB: expected {KPI_LABELS}, got {labels}"
        )

    def test_hero_hidden_when_open_position_exists(self, db):
        """A single [OPEN] position bumps Tracked off zero → hero hides."""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        at = _run_page()
        assert not self._has_cta(at), (
            "Hero CTA must NOT render once a trackable position exists."
        )

    def test_hero_hidden_when_applied_position_exists(self, db):
        database.add_position(make_position({"position_name": "A", "status": "[APPLIED]"}))
        at = _run_page()
        assert not self._has_cta(at)

    def test_hero_hidden_when_interview_position_exists(self, db):
        database.add_position(make_position({"position_name": "A", "status": "[INTERVIEW]"}))
        at = _run_page()
        assert not self._has_cta(at)

    def test_terminal_only_db_still_shows_hero(self, db):
        """Edge case: a DB with only terminal-status rows still has all
        three counted KPIs at zero, so the hero fires. This pins the
        'all three counts == 0' trigger — swap to a total-positions gate
        later via a single test update if the product call changes."""
        for term in config.TERMINAL_STATUSES:
            database.add_position(
                make_position({"position_name": f"P-{term}", "status": term})
            )
        at = _run_page()
        assert self._has_cta(at), (
            "With only terminal-status rows, all three counted KPIs are zero "
            "→ hero should render per the current trigger."
        )

    def test_cta_targets_opportunities_page(self, db):
        """The CTA must route to pages/1_Opportunities.py via st.switch_page.

        AppTest single-file mode does not register sibling pages, so clicking
        st.switch_page raises; instead we pin the target by reading app.py's
        source — the page path is part of the UI contract."""
        import pathlib
        src = pathlib.Path("app.py").read_text(encoding="utf-8")
        assert self.HERO_TARGET_PAGE in src, (
            f"app.py must st.switch_page() to {self.HERO_TARGET_PAGE!r}; "
            f"target path not found in source."
        )
        assert "st.switch_page" in src, (
            "CTA must use st.switch_page() per U5 (not a link or markdown)."
        )

