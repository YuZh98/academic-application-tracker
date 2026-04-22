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
        """Pin: the hero subheader contains the load-bearing word 'Welcome'.

        Substring (rather than exact copy) survives Phase 7 polish that may
        rephrase around the same greeting verb, but will fail if Phase 7
        drops the welcome message entirely OR if a future tier (T2 funnel,
        T3 readiness, etc.) lands a panel subheader and the hero is silently
        removed — counting subheaders alone would mask that regression once
        the page has any other subheader on it."""
        return any("Welcome" in s.value for s in at.subheader)

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


# ── T2-A: Application Funnel — Plotly horizontal bar from count_by_status ─────

class TestT2AFunnelBar:
    """T2-A: Plotly horizontal bar funnel built from `count_by_status()`.

    Contract (DESIGN.md §app.py + PHASE_4_GUIDELINES.md §T2-A):
      - One bar per `config.STATUS_VALUES` entry, in the canonical order of
        that list (so the pipeline reads top-to-bottom OPEN → DECLINED).
      - A status with zero positions still renders as a zero-width bar —
        keeps the grid shape stable and makes "no applied" visually
        distinct from "status doesn't exist".
      - Orientation: horizontal (long status labels are readable on the y-axis).
      - Marker colors sourced from `config.STATUS_COLORS` — never hardcoded
        in `app.py`. This is the same anti-typo guardrail as STATUS_VALUES.
      - Chart renders whether the DB is empty or not; T2-B will later swap
        the figure for descriptive text on the fully-empty-DB branch.

    Test-access pattern: AppTest surfaces `st.plotly_chart` as an
    `UnknownElement` whose `.value` triggers a session_state KeyError for
    stateless charts. `json.loads(el.proto.spec)` is the stable path —
    the spec is a full plotly figure JSON (`{data: [...], layout: {...}}`).
    """

    @staticmethod
    def _funnel_trace(at: AppTest) -> dict:
        """Return the first trace dict of the first plotly chart on the page.

        Fails the test (via assert) if no chart is found — used as the
        single entry point for every T2-A assertion to keep one failure
        message per missing-chart scenario."""
        import json
        charts = at.get("plotly_chart")
        assert len(charts) >= 1, (
            f"Expected at least one plotly chart on the dashboard (the "
            f"Application Funnel), got {len(charts)}."
        )
        spec = json.loads(charts[0].proto.spec)
        assert spec.get("data"), (
            "Funnel chart spec has no data traces — expected a single Bar trace."
        )
        return spec["data"][0]

    def test_funnel_chart_is_rendered(self, db):
        """A plotly chart is present on the dashboard even on an empty DB.

        (T2-B will later make the empty-DB branch show descriptive text
        instead; when that lands this test is updated in the same commit.)"""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        at = _run_page()
        charts = at.get("plotly_chart")
        assert len(charts) >= 1, (
            f"Expected an Application Funnel plotly chart, got {len(charts)}."
        )

    def test_funnel_has_one_bar_per_status_value_in_order(self, db):
        """y-axis labels match config.STATUS_VALUES, in that exact order.

        Pinning order (not just membership) because DESIGN.md reads the
        pipeline top-to-bottom — flipping OPEN↔DECLINED would break the
        mental model without tripping any other test."""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        at = _run_page()
        trace = self._funnel_trace(at)
        assert list(trace["y"]) == list(config.STATUS_VALUES), (
            f"Funnel y-axis must list every STATUS_VALUE in config order.\n"
            f"  expected: {config.STATUS_VALUES}\n"
            f"  got:      {list(trace['y'])}"
        )

    def test_funnel_is_horizontal(self, db):
        """Orientation is 'h' — status labels on y-axis, counts on x-axis."""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        at = _run_page()
        trace = self._funnel_trace(at)
        assert trace.get("orientation") == "h", (
            f"Funnel must be horizontal (orientation='h'), got "
            f"{trace.get('orientation')!r}"
        )

    def test_funnel_x_values_match_count_by_status(self, db):
        """x-values read from `count_by_status()` in STATUS_VALUES order.

        Seeds a mix of statuses and checks the bar lengths. This also
        verifies that count_by_status's sparse dict (zero-count statuses
        omitted) is expanded to the full STATUS_VALUES length with zeros."""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        database.add_position(make_position({"position_name": "B", "status": "[OPEN]"}))
        database.add_position(make_position({"position_name": "C", "status": "[APPLIED]"}))
        database.add_position(make_position({"position_name": "D", "status": "[INTERVIEW]"}))
        database.add_position(make_position({"position_name": "E", "status": "[OFFER]"}))

        counts = database.count_by_status()
        expected = [counts.get(s, 0) for s in config.STATUS_VALUES]

        at = _run_page()
        trace = self._funnel_trace(at)
        assert list(trace["x"]) == expected, (
            f"Funnel x-values must mirror count_by_status() in STATUS_VALUES "
            f"order.\n  expected: {expected}\n  got:      {list(trace['x'])}"
        )

    def test_funnel_bar_colors_come_from_config(self, db):
        """Marker colors are `config.STATUS_COLORS[s]` for each status,
        in STATUS_VALUES order. Anti-typo guardrail — the same grep rule
        that forbids hardcoded status literals in app.py forbids hardcoded
        colors (they'd drift from STATUS_COLORS silently)."""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        at = _run_page()
        trace = self._funnel_trace(at)
        marker = trace.get("marker", {})
        expected_colors = [config.STATUS_COLORS[s] for s in config.STATUS_VALUES]
        assert list(marker.get("color", [])) == expected_colors, (
            f"Funnel marker colors must come from config.STATUS_COLORS, in "
            f"STATUS_VALUES order.\n  expected: {expected_colors}\n"
            f"  got:      {list(marker.get('color', []))}"
        )

    def test_funnel_y_axis_reads_top_down_in_pipeline_order(self, db):
        """Visual order must match reading order: [OPEN] at the TOP of the
        chart, [DECLINED] at the bottom — the same top-down flow as
        config.STATUS_VALUES.

        Plotly renders horizontal bars bottom-to-top by default (first
        y-category sits at the bottom), which inverts the pipeline. The
        fix is `yaxis.autorange='reversed'`. Asserting on the layout flag
        (rather than, say, comparing screenshot pixels) keeps the test
        stable and tells a future reader exactly what went wrong if it
        trips — without it, flipping the data list would silently also
        flip the colors + the logical pairing."""
        import json
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        at = _run_page()
        spec = json.loads(at.get("plotly_chart")[0].proto.spec)
        yaxis = spec.get("layout", {}).get("yaxis", {})
        assert yaxis.get("autorange") == "reversed", (
            "Funnel yaxis must set autorange='reversed' so [OPEN] is at "
            "the top and [DECLINED] at the bottom (pipeline reads top-down). "
            f"Got yaxis={yaxis!r}"
        )

    def test_funnel_missing_statuses_render_as_zero_bars(self, db):
        """count_by_status() OMITS zero-count statuses from its dict.
        The funnel must still render every STATUS_VALUES bar with the
        missing ones coerced to 0 — otherwise the chart's shape changes
        as buckets fill up, and color/position assertions elsewhere break."""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        at = _run_page()
        trace = self._funnel_trace(at)
        assert len(trace["x"]) == len(config.STATUS_VALUES)
        assert len(trace["y"]) == len(config.STATUS_VALUES)
        # Every status except [OPEN] should read 0.
        for status, count in zip(trace["y"], trace["x"]):
            if status == config.STATUS_OPEN:
                assert count == 1, f"[OPEN] bar should be 1, got {count}"
            else:
                assert count == 0, (
                    f"Status {status!r} has no seeded rows; expected 0, got {count}"
                )


# ── T2-B: Application Funnel empty-state ──────────────────────────────────────

class TestT2BFunnelEmptyState:
    """T2-B: when there are literally no positions, swap the Plotly figure
    for descriptive text so the dashboard doesn't render an empty/broken
    chart with seven zero-width bars.

    Trigger semantics (user decision 2026-04-21, Option C):
      - Empty-state fires iff `sum(count_by_status().values()) == 0` — i.e.
        no rows in the positions table at all.
      - A DB with only terminal-status rows ([CLOSED]/[REJECTED]/[DECLINED])
        still has positions, so the figure STILL RENDERS (with the terminal
        bars non-zero and the active bars at 0). This differs intentionally
        from T1-E's hero trigger, which fires on 'no active pipeline'. The
        funnel's job is visual pipeline state; terminal-only rows are valid
        state to visualize.

    Copy (user decision 2026-04-21, wording γ):
      'Application funnel will appear once you've added positions.'

    Rendered via st.info(...). AppTest exposes info elements at `at.info`,
    each with `.value` returning the body string.

    Subheader stability:
      'Application Funnel' renders in BOTH branches so the page shape does
      not flicker when the first position is added.
    """

    EMPTY_COPY = "Application funnel will appear once you've added positions."

    @staticmethod
    def _empty_state_shown(at: AppTest) -> bool:
        return any(
            TestT2BFunnelEmptyState.EMPTY_COPY in (i.value or "")
            for i in at.info
        )

    @staticmethod
    def _funnel_subheader_shown(at: AppTest) -> bool:
        """The 'Application Funnel' subheader must render in both branches."""
        return any("Application Funnel" in s.value for s in at.subheader)

    def test_empty_db_hides_figure_and_shows_empty_state(self, db):
        """No positions at all → no plotly_chart; empty-state info is shown."""
        at = _run_page()
        charts = at.get("plotly_chart")
        assert len(charts) == 0, (
            f"Empty DB must not render the funnel chart (T2-B Option C); "
            f"got {len(charts)} plotly_chart element(s)."
        )
        assert self._empty_state_shown(at), (
            f"Expected empty-state info with copy {self.EMPTY_COPY!r} on "
            f"empty DB. Got info bodies: {[i.value for i in at.info]}"
        )

    def test_empty_state_copy_is_spec_exact(self, db):
        """Exact copy pin — guards against accidental rewording (the user
        locked wording γ on 2026-04-21; a rephrase needs a new decision)."""
        at = _run_page()
        matching = [i for i in at.info if i.value == self.EMPTY_COPY]
        assert len(matching) == 1, (
            f"Expected exactly one info element with the exact copy "
            f"{self.EMPTY_COPY!r}. Got info bodies: {[i.value for i in at.info]}"
        )

    def test_single_open_position_renders_figure_not_empty_state(self, db):
        """A single [OPEN] position → funnel chart renders; empty-state hides."""
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        at = _run_page()
        charts = at.get("plotly_chart")
        assert len(charts) >= 1, (
            f"Funnel must render when at least one position exists; "
            f"got {len(charts)} plotly_chart element(s)."
        )
        assert not self._empty_state_shown(at), (
            "Empty-state info must NOT render once any position exists. "
            f"Found info bodies: {[i.value for i in at.info]}"
        )

    def test_terminal_only_db_still_renders_figure(self, db):
        """Option C guard: terminal-only DB has positions, so the funnel
        still renders (with terminal bars non-zero and active bars at 0).

        This is the critical Option C vs Option A divergence — the T1-E
        hero DOES fire in this case (it gates on active-pipeline counts),
        but the funnel renders regardless because terminal rows are valid
        visual state. Swapping to Option A here is a single-test change."""
        for term in config.TERMINAL_STATUSES:
            database.add_position(
                make_position({"position_name": f"P-{term}", "status": term})
            )
        at = _run_page()
        charts = at.get("plotly_chart")
        assert len(charts) >= 1, (
            "Terminal-only DB has positions (just not active ones); the "
            "funnel must still render. Got 0 plotly_chart elements."
        )
        assert not self._empty_state_shown(at), (
            "Empty-state copy must NOT render when any position exists, "
            "even in terminal statuses. Got info bodies: "
            f"{[i.value for i in at.info]}"
        )

    def test_subheader_renders_in_both_branches(self, db):
        """'Application Funnel' subheader persists across the empty → seeded
        transition, so the page height doesn't jump when the first
        position is added."""
        at = _run_page()
        assert self._funnel_subheader_shown(at), (
            "Empty-state branch must still render the 'Application Funnel' "
            f"subheader. Got: {[s.value for s in at.subheader]}"
        )
        database.add_position(make_position({"position_name": "A", "status": "[OPEN]"}))
        at = _run_page()
        assert self._funnel_subheader_shown(at), (
            "Seeded branch must still render the 'Application Funnel' "
            f"subheader. Got: {[s.value for s in at.subheader]}"
        )
