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

    Only structure is checked here — concrete KPI values come in T1-C/D.

    Sub-task 12 adds `st.set_page_config(layout="wide", ...)` at the top of
    app.py per DESIGN §8.0. AppTest does NOT surface st.set_page_config in
    its element tree, so the wide-layout contract is pinned via a source
    grep (same precedent as TestT1EEmptyDbHero.test_cta_targets_opportunities_page).
    """

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

    def test_page_config_sets_wide_layout(self, db):
        """DESIGN §8.0 requires `st.set_page_config(layout="wide", ...)` on
        every page — the app is data-heavy and needs horizontal room.

        AppTest does not surface set_page_config in the element tree (the
        call is consumed by the page-setup phase before widgets render),
        so the contract is pinned at the source level — same precedent as
        TestT1EEmptyDbHero.test_cta_targets_opportunities_page for
        st.switch_page. Checking for the three keyword bindings together
        keeps a partial change (e.g. someone accidentally dropping `layout`)
        from silently passing.
        """
        import pathlib
        src = pathlib.Path("app.py").read_text(encoding="utf-8")
        assert "st.set_page_config(" in src, (
            "app.py must call st.set_page_config(...) per DESIGN §8.0."
        )
        assert 'page_title="Postdoc Tracker"' in src, (
            "set_page_config must bind page_title=\"Postdoc Tracker\"."
        )
        assert 'page_icon="📋"' in src, (
            "set_page_config must bind page_icon=\"📋\" per DESIGN §8.0."
        )
        assert 'layout="wide"' in src, (
            "set_page_config must bind layout=\"wide\" per DESIGN §8.0 / D14."
        )


# ── T1-C: KPI count wiring + Tracked tooltip + refresh-button-absent ──────────

class TestT1CKpiCounts:
    """T1-C: wire `count_by_status()` into Tracked / Applied / Interview.

    Decision: Tracked = count([SAVED]) + count([APPLIED]) — the pool of
    positions that 'might still move forward'. Applied and Interview are
    single-bucket counts of their namesake status. Next Interview stays
    '—' until T1-D wires get_upcoming_interviews().

    Sub-task 12 (DESIGN.md §8.1 + D13) landed two user-visible changes on
    top of the original T1-C contract:
      - The top-bar 🔄 Refresh button is GONE (D13 dictates no manual
        refresh — Streamlit reruns on interaction). Class-level constant
        and a dedicated `test_refresh_button_absent` keep the regression
        guard explicit, not just an absence.
      - The Tracked metric now carries the locked help-tooltip string
        so hovering explains the arithmetic. AppTest surfaces the tooltip
        at `metric.proto.help` (probed before writing this test).
    """

    TRACKED_HELP = "Saved + Applied — positions you're still actively pursuing"

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
        """Tracked = count([SAVED]) + count([APPLIED]); INTERVIEW/OFFER are not 'tracked'."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        database.add_position(make_position({"position_name": "B", "status": "[SAVED]"}))
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
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        database.add_position(make_position({"position_name": "B", "status": "[APPLIED]"}))
        database.add_position(make_position({"position_name": "C", "status": "[APPLIED]"}))
        database.add_position(make_position({"position_name": "D", "status": "[INTERVIEW]"}))

        at = _run_page()
        kpis = self._kpis(at)
        assert kpis["Applied"] == "2", f"Applied should be 2, got {kpis['Applied']!r}"

    def test_interview_count_excludes_other_statuses(self, db):
        """Interview reflects the [INTERVIEW] bucket only."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
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

    def test_refresh_button_absent(self, db):
        """DESIGN D13: no 🔄 Refresh button on the dashboard top bar.

        Streamlit reruns on any interaction; a manual refresh is cognitive
        noise for a single-user local app. An absence test (rather than
        silent omission) keeps a regression visible if a future edit
        accidentally brings the button back — belt-and-suspenders since
        the label is a one-line regex away from reappearing by accident.
        """
        at = _run_page()
        refresh = [b for b in at.button if "Refresh" in b.label or "🔄" in b.label]
        assert refresh == [], (
            f"DESIGN D13 requires no Refresh button on the dashboard. "
            f"Got labels: {[b.label for b in at.button]}"
        )

    def test_tracked_kpi_help_tooltip(self, db):
        """DESIGN §8.1 locks the Tracked KPI's hover-tooltip copy.

        AppTest surfaces the tooltip at `metric.proto.help` (confirmed via
        the Streamlit 1.56 protobuf descriptor). Exact-match pin — a
        rephrase requires an explicit user decision, same discipline as
        the funnel / readiness empty-state copy pins.
        """
        at = _run_page()
        tracked = next(m for m in at.metric if m.label == "Tracked")
        assert tracked.proto.help == self.TRACKED_HELP, (
            f"Tracked KPI must carry the locked help tooltip. "
            f"expected: {self.TRACKED_HELP!r}\n"
            f"got:      {tracked.proto.help!r}"
        )


# ── T1-D: Next Interview KPI — wire get_upcoming_interviews() ─────────────────

class TestT1DNextInterviewKpi:
    """T1-D: wire database.get_upcoming_interviews() into the Next Interview
    KPI card per DESIGN.md §app.py; '—' on empty per locked decision U3.

    User decisions (2026-04-21):
    - Value format: "{Mon D} · {institute}" (e.g. 'May 3 · MIT') — short
      month + day, no year, with institute.
    - Selection: take the EARLIEST future scheduled_date across all
      upcoming interviews. The paired institute belongs to whichever
      position owns that winning interview.
    - No upcoming interview anywhere → '—'.

    Sub-task 8 rewrote get_upcoming_interviews() to return row-per-
    interview from the normalized interviews sub-table (DESIGN §6.2 +
    D18) instead of row-per-position with flat interview1_date /
    interview2_date columns. Tests now seed via database.add_interview
    and assert against the single scheduled_date column.
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
        """A tracked position with no interview rows scheduled must leave
        the Next Interview KPI empty."""
        database.add_position(make_position({"position_name": "P", "institute": "Stanford"}))
        at = _run_page()
        assert self._next(at) == "—"

    def test_all_past_interviews_show_em_dash(self, db):
        """If every seeded interview date is in the past, nothing is upcoming."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        pid = database.add_position(
            make_position({"position_name": "P", "institute": "Stanford"})
        )
        database.add_interview(pid, {"scheduled_date": yesterday})
        database.add_interview(pid, {"scheduled_date": yesterday})
        at = _run_page()
        assert self._next(at) == "—"

    def test_single_upcoming_interview_formats_date_and_institute(self, db):
        """One upcoming interview → '{Mon D} · {institute}'."""
        d_future = date.today() + timedelta(days=10)
        pid = database.add_position(
            make_position({"position_name": "BioStats Postdoc", "institute": "MIT"})
        )
        database.add_interview(pid, {"scheduled_date": d_future.isoformat()})

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
        database.add_interview(pid_a, {"scheduled_date": d_late.isoformat()})
        database.add_interview(pid_b, {"scheduled_date": d_early.isoformat()})

        at = _run_page()
        assert self._next(at) == self._expected(d_early, "MIT")

    def test_later_interview_on_same_position_does_not_override(self, db):
        """A position with multiple interviews contributes multiple rows
        to get_upcoming_interviews (D18). The Next-Interview KPI picks
        the globally earliest across all rows — a later interview on
        the same position must NOT promote past an earlier interview
        on a different position."""
        d_near = date.today() + timedelta(days=3)
        d_far  = date.today() + timedelta(days=30)
        pid_a = database.add_position(
            make_position({"position_name": "A", "institute": "Stanford"})
        )
        pid_b = database.add_position(
            make_position({"position_name": "B", "institute": "MIT"})
        )
        # Position A has the earlier interview (sequence 2), B has a far one.
        database.add_interview(pid_a, {"scheduled_date": d_near.isoformat()})
        database.add_interview(pid_b, {"scheduled_date": d_far.isoformat()})

        at = _run_page()
        assert self._next(at) == self._expected(d_near, "Stanford")

    def test_past_date_on_same_position_is_ignored(self, db):
        """Regression guard: a position with a past interview AND a
        far-future interview must NOT win over another position whose
        interview is future-near. The `scheduled_date >= today`
        filter in get_upcoming_interviews drops the past row entirely
        (one row per interview, so no row-level ambiguity between
        past and future dates)."""
        past   = (date.today() - timedelta(days=7)).isoformat()
        d_far  = (date.today() + timedelta(days=25)).isoformat()
        d_near = date.today() + timedelta(days=3)
        pid_a = database.add_position(
            make_position({"position_name": "A", "institute": "Stanford"})
        )
        pid_b = database.add_position(
            make_position({"position_name": "B", "institute": "MIT"})
        )
        database.add_interview(pid_a, {"scheduled_date": past})
        database.add_interview(pid_a, {"scheduled_date": d_far})
        database.add_interview(pid_b, {"scheduled_date": d_near.isoformat()})

        at = _run_page()
        assert self._next(at) == self._expected(d_near, "MIT"), (
            "Earliest FUTURE scheduled_date should win across all rows; "
            "a past interview on Position A must not beat a future "
            "interview on Position B."
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
        """A single [SAVED] position bumps Tracked off zero → hero hides."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
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


# ── T2-A: Application Funnel — Plotly horizontal bar from FUNNEL_BUCKETS ──────

class TestT2AFunnelBar:
    """T2-A: Plotly horizontal bar funnel built from `count_by_status()`
    aggregated into `config.FUNNEL_BUCKETS`.

    Contract (DESIGN.md §8.1 + Sub-task 12 + T6 amendment 2026-04-30):
      - One bar per **visible** `FUNNEL_BUCKETS` entry, in the list's
        display order (so the pipeline reads top-to-bottom once the
        y-axis is reversed). A bucket is visible when its label is NOT
        in `FUNNEL_DEFAULT_HIDDEN`, OR when
        `st.session_state["_funnel_expanded"] == True` (set by clicking
        the disclosure toggle) — the latter is exercised in
        `TestT2DFunnelExpand` (collapsed → expanded half) and
        `TestT6FunnelToggle` (expanded → collapsed half + round-trip).
      - A visible bucket with zero count renders as a zero-width bar
        so the chart shape stays stable as the pipeline fills up. This
        makes "no one applied yet" visually distinct from "bucket
        doesn't exist".
      - Orientation: horizontal (long bucket labels read on the y-axis).
      - Marker colors come from `FUNNEL_BUCKETS[i][2]` — bucket owns its
        color because a bucket may aggregate multiple raw statuses
        (e.g. "Archived" = [REJECTED] + [DECLINED]). Anti-typo guardrail
        still holds: the same "no hardcoded vocab" rule forbids inlining
        these strings in app.py.
      - Bucket x-values are the SUM of `count_by_status()` over the
        bucket's raw-status tuple — a bucket of 1 raw status reduces to
        the old per-status count, but a bucket of 2+ raw statuses
        aggregates correctly (Archived combines rejected + declined).

    Pre-Sub-task-12 the funnel was per-`STATUS_VALUES`: one bar per raw
    status, colors from `STATUS_COLORS`. The aggregation + default-hiding
    is what DESIGN §8.1 requires for v1; tests below assert the new
    contract directly.

    Test-access pattern: AppTest surfaces `st.plotly_chart` as an
    `UnknownElement` whose `.value` triggers a session_state KeyError for
    stateless charts. `json.loads(el.proto.spec)` is the stable path —
    the spec is a full plotly figure JSON (`{data: [...], layout: {...}}`).
    """

    @staticmethod
    def _visible_bucket_indices() -> list[int]:
        """Indices of FUNNEL_BUCKETS entries that render by default
        (i.e. not in FUNNEL_DEFAULT_HIDDEN)."""
        return [
            i for i, (label, _, _) in enumerate(config.FUNNEL_BUCKETS)
            if label not in config.FUNNEL_DEFAULT_HIDDEN
        ]

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
        """A plotly chart is present on the dashboard when any visible
        bucket has data (branch (c) trigger).

        Seeding a [SAVED] position puts a count in the 'Saved' bucket —
        a default-visible bucket — so the funnel renders. A DB with only
        hidden-bucket data would fire branch (b) instead (covered by
        `TestT2BFunnelEmptyState.test_all_hidden_bucket_data_fires_branch_b`).
        """
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        charts = at.get("plotly_chart")
        assert len(charts) >= 1, (
            f"Expected an Application Funnel plotly chart, got {len(charts)}."
        )

    def test_funnel_has_one_bar_per_visible_bucket_in_order(self, db):
        """y-axis labels match the visible-bucket subset of
        config.FUNNEL_BUCKETS, in that list's order.

        Pinning order (not just membership) because DESIGN.md reads the
        pipeline top-to-bottom — flipping Saved↔Archived would break the
        mental model without tripping any other test. Visible = NOT in
        FUNNEL_DEFAULT_HIDDEN; the expanded path gets its own pin in
        TestT2DFunnelExpand."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        trace = self._funnel_trace(at)
        expected_labels = [
            config.FUNNEL_BUCKETS[i][0] for i in self._visible_bucket_indices()
        ]
        assert list(trace["y"]) == expected_labels, (
            f"Funnel y-axis must list visible FUNNEL_BUCKETS labels in order.\n"
            f"  expected: {expected_labels}\n"
            f"  got:      {list(trace['y'])}"
        )

    def test_funnel_is_horizontal(self, db):
        """Orientation is 'h' — bucket labels on y-axis, counts on x-axis."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        trace = self._funnel_trace(at)
        assert trace.get("orientation") == "h", (
            f"Funnel must be horizontal (orientation='h'), got "
            f"{trace.get('orientation')!r}"
        )

    def test_funnel_x_values_sum_bucket_raw_statuses(self, db):
        """x-values are the SUM of `count_by_status()` over each bucket's
        raw-status tuple, in visible-bucket order.

        Seed mixes several raw statuses; assertion re-computes the
        expected sums directly from FUNNEL_BUCKETS to stay correct if
        someone reshuffles bucket-to-raw mappings in config.py."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        database.add_position(make_position({"position_name": "B", "status": "[SAVED]"}))
        database.add_position(make_position({"position_name": "C", "status": "[APPLIED]"}))
        database.add_position(make_position({"position_name": "D", "status": "[INTERVIEW]"}))
        database.add_position(make_position({"position_name": "E", "status": "[OFFER]"}))

        counts = database.count_by_status()
        expected = [
            sum(counts.get(raw, 0) for raw in config.FUNNEL_BUCKETS[i][1])
            for i in self._visible_bucket_indices()
        ]

        at = _run_page()
        trace = self._funnel_trace(at)
        assert list(trace["x"]) == expected, (
            f"Funnel x-values must sum count_by_status() per bucket, in "
            f"visible-bucket order.\n  expected: {expected}\n"
            f"  got:      {list(trace['x'])}"
        )

    def test_funnel_bar_colors_come_from_funnel_buckets(self, db):
        """Marker colors are `FUNNEL_BUCKETS[i][2]` for each visible
        bucket in display order. Pins that the bucket owns its color
        (the aggregation-aware choice) — not STATUS_COLORS which is for
        per-status surfaces (badges, tooltips). A future color tweak
        should live in config.FUNNEL_BUCKETS, not in app.py."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        trace = self._funnel_trace(at)
        marker = trace.get("marker", {})
        expected_colors = [
            config.FUNNEL_BUCKETS[i][2] for i in self._visible_bucket_indices()
        ]
        assert list(marker.get("color", [])) == expected_colors, (
            f"Funnel marker colors must come from FUNNEL_BUCKETS[i][2], in "
            f"visible-bucket order.\n  expected: {expected_colors}\n"
            f"  got:      {list(marker.get('color', []))}"
        )

    def test_funnel_y_axis_reads_top_down_in_pipeline_order(self, db):
        """Visual order must match reading order: the FIRST visible bucket
        ('Saved' by default) at the top, the LAST at the bottom — same
        top-down flow as FUNNEL_BUCKETS.

        Plotly renders horizontal bars bottom-to-top by default (first
        y-category sits at the bottom), which inverts the pipeline. The
        fix is `yaxis.autorange='reversed'`. Asserting on the layout flag
        (rather than, say, comparing screenshot pixels) keeps the test
        stable and tells a future reader exactly what went wrong if it
        trips — without it, flipping the data list would silently also
        flip the colors + the logical pairing."""
        import json
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        spec = json.loads(at.get("plotly_chart")[0].proto.spec)
        yaxis = spec.get("layout", {}).get("yaxis", {})
        assert yaxis.get("autorange") == "reversed", (
            "Funnel yaxis must set autorange='reversed' so the first visible "
            "bucket is at the top and the last at the bottom (pipeline reads "
            f"top-down). Got yaxis={yaxis!r}"
        )

    def test_funnel_missing_buckets_render_as_zero_bars(self, db):
        """count_by_status() OMITS zero-count statuses from its dict.
        The funnel must still render every VISIBLE bucket with the
        missing ones coerced to 0 — otherwise the chart's shape changes
        as buckets fill up, and color/position assertions elsewhere break.

        Seeds one [SAVED] position only. With default hiding the visible
        buckets are Saved/Applied/Interview/Offer; only Saved is non-zero."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        trace = self._funnel_trace(at)
        visible = self._visible_bucket_indices()
        assert len(trace["x"]) == len(visible)
        assert len(trace["y"]) == len(visible)
        # Every bucket except Saved should read 0.
        saved_label = config.FUNNEL_BUCKETS[0][0]  # "Saved"
        for label, count in zip(trace["y"], trace["x"]):
            if label == saved_label:
                assert count == 1, f"'Saved' bar should be 1, got {count}"
            else:
                assert count == 0, (
                    f"Bucket {label!r} has no seeded rows; expected 0, got {count}"
                )


# ── T2-B: Application Funnel empty-state (3 branches) ─────────────────────────

class TestT2BFunnelEmptyState:
    """T2-B: the three-branch empty-state matrix for the funnel
    (DESIGN §8.1 'Funnel visibility rules' + 'Empty-state branches').

    Sub-task 12 replaces the pre-v1.3 two-state model (Option C: render or
    info) with a three-branch model driven by FUNNEL_BUCKETS visibility:

      (a) NO DATA ANYWHERE. `sum(count_by_status().values()) == 0`:
          show `st.info(EMPTY_COPY_A)`, and SUPPRESS the `[expand]` button
          (nothing to expand into). Chart does not render.

      (b) NO VISIBLE DATA. Total > 0 but every non-zero bucket lies in
          FUNNEL_DEFAULT_HIDDEN and `_funnel_expanded` is False. Show
          `st.info(EMPTY_COPY_B)` and RENDER the `[expand]` button
          directly under the info — gives the user a single-click
          recovery path. Chart does not render in this branch either.
          A terminal-only DB falls here (all data in Closed + Archived,
          both hidden by default).

      (c) OTHERWISE. At least one visible bucket has data, OR the user
          has clicked `[expand]` so hidden buckets are now visible.
          Chart renders. The `[expand]` button renders below the chart
          whenever FUNNEL_DEFAULT_HIDDEN is non-empty AND not yet
          expanded.

    Subheader renders in ALL THREE branches so page height does not
    flicker across transitions. The `[expand]`-button toggling between
    branches is covered by TestT2DFunnelExpand.

    Pre-Sub-task-12 divergence: the earlier 'Option C' behaviour had
    terminal-only DBs STILL RENDER the figure with terminal bars
    non-zero. The v1.3 spec reverses that — terminal rows are all in
    hidden buckets, so branch (b) fires. Tests below pin the new
    behaviour; the pre-v1.3 Option C test is replaced.
    """

    EMPTY_COPY_A = "Application funnel will appear once you've added positions."
    # Branch (b) info copy points at the toggle by LABEL (not by spatial
    # direction) so the copy stays correct regardless of where the toggle
    # sits relative to the info — DESIGN §8.1 T6 amendment. Pre-T6 wording
    # ("Click [expand] below to reveal them.") was tied to the old
    # below-the-info placement.
    EMPTY_COPY_B = (
        "All your positions are in hidden buckets. "
        "Click 'Show all stages' to reveal them."
    )
    # Toggle label literal — duplicated from config.FUNNEL_TOGGLE_LABELS[False]
    # at class scope (rather than `config.FUNNEL_TOGGLE_LABELS[False]` directly)
    # so test collection succeeds even when this file is imported before
    # config has been re-imported with the new constant. The "literal matches
    # config" invariant is pinned in TestT6FunnelToggle.test_label_*; if
    # config drifts, that test catches it before this class's runtime
    # assertions surface a less-informative "label not found" error.
    EXPAND_LABEL = "+ Show all stages"

    @staticmethod
    def _info_bodies(at: AppTest) -> list[str]:
        return [i.value for i in at.info]

    @staticmethod
    def _copy_shown(at: AppTest, body: str) -> bool:
        return any(i.value == body for i in at.info)

    @staticmethod
    def _funnel_subheader_shown(at: AppTest) -> bool:
        """The 'Application Funnel' subheader must render in all branches."""
        return any("Application Funnel" in s.value for s in at.subheader)

    @staticmethod
    def _expand_button_rendered(at: AppTest) -> bool:
        return any(b.label == TestT2BFunnelEmptyState.EXPAND_LABEL for b in at.button)

    # ── Branch (a): no data anywhere ──────────────────────────────────────────

    def test_empty_db_fires_branch_a(self, db):
        """Branch (a): empty DB → EMPTY_COPY_A info; no chart; NO [expand]."""
        at = _run_page()
        assert len(at.get("plotly_chart")) == 0, (
            "Branch (a): chart must NOT render on an empty DB. "
            f"Got {len(at.get('plotly_chart'))} plotly_chart element(s)."
        )
        assert self._copy_shown(at, self.EMPTY_COPY_A), (
            f"Branch (a): expected info {self.EMPTY_COPY_A!r}. "
            f"Got info bodies: {self._info_bodies(at)}"
        )
        assert not self._expand_button_rendered(at), (
            "Branch (a): [expand] button must be SUPPRESSED — nothing "
            f"to expand into. Got labels: {[b.label for b in at.button]}"
        )

    def test_branch_a_empty_copy_is_spec_exact(self, db):
        """Exact copy pin — a rephrase needs a new user decision."""
        at = _run_page()
        matching = [i for i in at.info if i.value == self.EMPTY_COPY_A]
        assert len(matching) == 1, (
            f"Branch (a): expected exactly one info with copy "
            f"{self.EMPTY_COPY_A!r}. Got: {self._info_bodies(at)}"
        )

    # ── Branch (b): total > 0 but all non-zero buckets hidden ─────────────────

    def test_all_hidden_bucket_data_fires_branch_b(self, db):
        """Terminal-only DB: every position lands in Closed + Archived,
        both default-hidden. Branch (b) fires — info + [expand] button,
        no chart. This is the v1.3 replacement for the pre-Sub-task-12
        'terminal-only DB still renders figure' behaviour."""
        for term in config.TERMINAL_STATUSES:
            database.add_position(
                make_position({"position_name": f"P-{term}", "status": term})
            )
        at = _run_page()
        assert len(at.get("plotly_chart")) == 0, (
            "Branch (b): chart must NOT render when all non-zero buckets "
            f"are default-hidden. Got {len(at.get('plotly_chart'))} chart(s)."
        )
        assert self._copy_shown(at, self.EMPTY_COPY_B), (
            f"Branch (b): expected info {self.EMPTY_COPY_B!r}. "
            f"Got info bodies: {self._info_bodies(at)}"
        )
        assert self._expand_button_rendered(at), (
            "Branch (b): [expand] button must render directly under the "
            f"info. Got button labels: {[b.label for b in at.button]}"
        )
        assert not self._copy_shown(at, self.EMPTY_COPY_A), (
            "Branch (b): EMPTY_COPY_A must NOT appear — branches are "
            "mutually exclusive. Got info bodies: " f"{self._info_bodies(at)}"
        )

    def test_branch_b_empty_copy_is_spec_exact(self, db):
        """Exact copy pin for branch (b)."""
        for term in config.TERMINAL_STATUSES:
            database.add_position(
                make_position({"position_name": f"P-{term}", "status": term})
            )
        at = _run_page()
        matching = [i for i in at.info if i.value == self.EMPTY_COPY_B]
        assert len(matching) == 1, (
            f"Branch (b): expected exactly one info with copy "
            f"{self.EMPTY_COPY_B!r}. Got: {self._info_bodies(at)}"
        )

    # ── Branch (c): at least one visible bucket has data ──────────────────────

    def test_single_open_position_fires_branch_c(self, db):
        """A single [SAVED] position → chart renders (branch (c)); neither
        empty-state info shows."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        assert len(at.get("plotly_chart")) >= 1, (
            "Branch (c): chart must render when any visible bucket has data. "
            f"Got {len(at.get('plotly_chart'))} plotly_chart element(s)."
        )
        assert not self._copy_shown(at, self.EMPTY_COPY_A), (
            "Branch (c): EMPTY_COPY_A must NOT render once a visible "
            f"bucket has data. Got info bodies: {self._info_bodies(at)}"
        )
        assert not self._copy_shown(at, self.EMPTY_COPY_B), (
            "Branch (c): EMPTY_COPY_B must NOT render once a visible "
            f"bucket has data. Got info bodies: {self._info_bodies(at)}"
        )

    def test_mixed_visible_and_hidden_data_fires_branch_c(self, db):
        """A position in a visible bucket + another in a hidden bucket:
        branch (c) still fires because at least one visible bucket is
        non-zero. (Only 'all non-zero buckets hidden' triggers branch (b).)
        """
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        database.add_position(make_position({"position_name": "B", "status": "[CLOSED]"}))
        at = _run_page()
        assert len(at.get("plotly_chart")) >= 1, (
            "Branch (c): chart must render when at least one visible bucket "
            f"is non-zero. Got {len(at.get('plotly_chart'))} chart(s)."
        )
        assert not self._copy_shown(at, self.EMPTY_COPY_B), (
            "Branch (c) precondition: with a SAVED position present, "
            "branch (b) must NOT fire even though a hidden bucket has data."
        )

    # ── Subheader stability across all three branches ─────────────────────────

    def test_subheader_renders_in_all_branches(self, db):
        """'Application Funnel' subheader persists across branches (a) → (b)
        → (c), so the page height doesn't jump as data lands."""
        # Branch (a)
        at = _run_page()
        assert self._funnel_subheader_shown(at), (
            "Branch (a): 'Application Funnel' subheader missing. "
            f"Got: {[s.value for s in at.subheader]}"
        )
        # Branch (b) — terminal-only DB
        for term in config.TERMINAL_STATUSES:
            database.add_position(
                make_position({"position_name": f"P-{term}", "status": term})
            )
        at = _run_page()
        assert self._funnel_subheader_shown(at), (
            "Branch (b): 'Application Funnel' subheader missing. "
            f"Got: {[s.value for s in at.subheader]}"
        )
        # Branch (c) — add a visible-bucket row
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        assert self._funnel_subheader_shown(at), (
            "Branch (c): 'Application Funnel' subheader missing. "
            f"Got: {[s.value for s in at.subheader]}"
        )


# ── T2-C: Application Funnel — placed in left half of st.columns(2) (U2) ──────

class TestT2CFunnelLayout:
    """T2-C: place the funnel inside the LEFT half of an `st.columns(2)` so
    the right half can host T3's Materials Readiness panel (locked user
    decision U2 — PHASE_4_GUIDELINES.md §Locked decisions).

    Layout-detection strategy:
      AppTest exposes each column as `Column` objects in `at.columns`. Each
      column's `proto.weight` attribute is the fraction of the flex
      container it occupies — for `st.columns(2)` both halves have
      weight == 0.5, distinct from the existing dashboard columns:
        - title row: `st.columns([6, 1])` → weights ≈0.857 / 0.143
        - KPI grid: `st.columns(4)`        → weight == 0.25 each
      So `weight == 0.5` uniquely identifies the T2-C pair.

    T3-B will REUSE this same `st.columns(2)` (not create a new one), so
    the "exactly 2 columns with weight 0.5" invariant holds through T3
    landing as well — any future tier that adds another 2-col split on
    the dashboard will trip this test, which is the desired guard.

    Tests pin the structural contract (column weight + which half holds
    the subheader) rather than raw AppTest indices, so reordering or
    adding widgets around the funnel doesn't cause spurious failures.
    """

    FUNNEL_SUBHEADER = "Application Funnel"

    @staticmethod
    def _half_width_columns(at: AppTest):
        """Return (in page order) every AppTest Column with weight == 0.5."""
        return [c for c in at.columns if c.proto.weight == 0.5]

    @classmethod
    def _column_has_funnel_subheader(cls, col) -> bool:
        return any(s.value == cls.FUNNEL_SUBHEADER for s in col.subheader)

    def test_exactly_two_half_width_columns_exist(self, db):
        """The T2-C wrap creates the single `st.columns(2)` pair on the
        dashboard. Two half-width columns = one pair = the funnel split.
        Any additional 2-col split (until an explicit layout-change
        decision) would trip this test — desired guard."""
        at = _run_page()
        halves = self._half_width_columns(at)
        assert len(halves) == 2, (
            f"Expected exactly 2 half-width columns (the T2-C pair), got "
            f"{len(halves)}. Dashboard column weights: "
            f"{[c.proto.weight for c in at.columns]}"
        )

    def test_funnel_lives_in_a_half_width_column(self, db):
        """Exactly one half-width column carries the 'Application Funnel'
        subheader — pins the wrap is actually inside the new 2-col split
        (not accidentally left at the top level)."""
        at = _run_page()
        halves = self._half_width_columns(at)
        owners = [c for c in halves if self._column_has_funnel_subheader(c)]
        assert len(owners) == 1, (
            f"Expected exactly one half-width column to own the "
            f"'Application Funnel' subheader, got {len(owners)}. "
            f"Subheaders per half-width column: "
            f"{[[s.value for s in c.subheader] for c in halves]}"
        )

    def test_funnel_is_in_left_half(self, db):
        """Left half = first half-width column in page order (U2: funnel
        LEFT, readiness right — DESIGN.md §app.py wireframe)."""
        at = _run_page()
        halves = self._half_width_columns(at)
        assert len(halves) == 2, (
            f"Precondition for this test: exactly 2 half-width columns. "
            f"Got {len(halves)}."
        )
        left, right = halves[0], halves[1]
        assert self._column_has_funnel_subheader(left), (
            "Funnel must be in the LEFT half-width column (first in page "
            f"order). Left-column subheaders: {[s.value for s in left.subheader]}"
        )
        assert not self._column_has_funnel_subheader(right), (
            "Funnel subheader must NOT leak into the RIGHT half — that "
            "column is reserved for T3's Materials Readiness. Right-column "
            f"subheaders: {[s.value for s in right.subheader]}"
        )

    def test_funnel_figure_renders_inside_left_column(self, db):
        """Seeded DB: the plotly chart must live INSIDE the left half
        column, not at top-level. Asserting scoped retrieval (col.get
        rather than at.get) pins that the whole funnel block was moved
        as a unit, not just the subheader."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        halves = self._half_width_columns(at)
        left = halves[0]
        charts_in_left = left.get("plotly_chart")
        assert len(charts_in_left) >= 1, (
            f"Funnel figure must render inside the left half-width column. "
            f"Got {len(charts_in_left)} charts in left; "
            f"{len(at.get('plotly_chart'))} at top level."
        )

    def test_empty_state_info_renders_inside_left_column(self, db):
        """Empty DB: the branch-(a) info copy must live INSIDE the left
        half column too — otherwise the empty-state branch accidentally
        escapes the layout wrap and the right-half alignment breaks
        when T3-B lands.

        References `TestT2BFunnelEmptyState.EMPTY_COPY_A` rather than
        re-literalizing the string so a future wording change (which
        requires a new user decision per §T2-B) updates one constant,
        not multiple. See phase-4-Tier2 review Fix #2. Sub-task 12
        renamed `EMPTY_COPY` → `EMPTY_COPY_A` to disambiguate from the
        new branch-(b) copy."""
        at = _run_page()
        halves = self._half_width_columns(at)
        left = halves[0]
        left_info_bodies = [i.value for i in left.info]
        expected = TestT2BFunnelEmptyState.EMPTY_COPY_A
        assert expected in left_info_bodies, (
            f"Empty-state info must render inside the left half-width "
            f"column. Got left-column info bodies: {left_info_bodies}"
        )


# ── T2-D: Funnel [expand] toggle (Sub-task 12) ────────────────────────────────

class TestT2DFunnelExpand:
    """T2-D: clicking the funnel disclosure toggle from its default
    (collapsed) state reveals every `FUNNEL_DEFAULT_HIDDEN` bucket for
    the rest of the session (DESIGN §8.1 'Funnel visibility rules' + D24).

    **Scope after the T6 polish (DESIGN §8.1 T6 amendment):** this class
    pins the *collapsed → expanded* half of the bidirectional contract —
    label correctness in the collapsed state, click-flips-state, click-
    reveals-buckets, branch-(a)-suppression, branch-(b) recovery path.
    The *expanded → collapsed* half (round-trip, post-T6) is pinned by
    the new `TestT6FunnelToggle` class below. The pre-T6 single-direction
    `test_expand_button_hides_after_click` test was deleted because the
    toggle no longer hides post-click — it relabels and stays put so the
    user can collapse.

    Contract pins (collapsed half):
      - Toggle label in collapsed state: exactly
        `config.FUNNEL_TOGGLE_LABELS[False]` (= "+ Show all stages" today,
        but sourced from config so a relabel ripples).
      - Click from collapsed flips `st.session_state["_funnel_expanded"]`
        to True. Implementation uses `on_click` callback so the flag is
        set BEFORE the next script rerun — probed in AppTest before
        writing this class.
      - Post-click: every `FUNNEL_BUCKETS` label is visible on the chart
        in list order. The toggle PERSISTS at its subheader-row position
        (this is the key behavioural difference from pre-T6).
      - In branch (a) (no data), the toggle is SUPPRESSED regardless of
        state — nothing to disclose into.
      - In branch (b), clicking the toggle round-trips into branch (c)
        with the chart drawn across all buckets.

    Branch-(a)-suppression is also covered in TestT2BFunnelEmptyState but
    is re-pinned here to keep the disclosure-affordance contract close
    to its click-behaviour pins.

    Visibility formula (applied after click):
      visible_bucket_labels = every label in FUNNEL_BUCKETS (in order).
    """

    # Collapsed-state label literal — duplicated at class scope (not
    # `config.FUNNEL_TOGGLE_LABELS[False]`) so test collection survives
    # being run against a tree that hasn't re-imported config. Drift
    # against config is pinned in TestT6FunnelToggle (Group A.3 + E).
    EXPAND_LABEL = "+ Show all stages"
    STATE_KEY = "_funnel_expanded"

    @staticmethod
    def _expand_buttons(at: AppTest):
        return [b for b in at.button if b.label == TestT2DFunnelExpand.EXPAND_LABEL]

    @staticmethod
    def _chart_y_labels(at: AppTest) -> list[str]:
        import json
        charts = at.get("plotly_chart")
        assert len(charts) >= 1, "Expected a chart after expanding."
        spec = json.loads(charts[0].proto.spec)
        return list(spec["data"][0]["y"])

    def test_expand_button_renders_in_branch_c_by_default(self, db):
        """Branch (c) + FUNNEL_DEFAULT_HIDDEN non-empty + not expanded →
        exactly one `[expand]` button renders. This is the common path
        on a fresh session with any visible-bucket data."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        assert len(self._expand_buttons(at)) == 1, (
            f"Expected exactly one {self.EXPAND_LABEL!r} button in branch "
            f"(c) with default-hidden buckets. Got button labels: "
            f"{[b.label for b in at.button]}"
        )

    def test_expand_button_absent_in_branch_a(self, db):
        """Branch (a) re-pin (also tested in TestT2BFunnelEmptyState):
        empty DB → no `[expand]` button — nothing to expand into."""
        at = _run_page()
        assert self._expand_buttons(at) == [], (
            "Branch (a): [expand] must be SUPPRESSED. "
            f"Got labels: {[b.label for b in at.button]}"
        )

    def test_expand_button_present_in_branch_b(self, db):
        """Branch (b) re-pin: terminal-only DB → `[expand]` renders
        directly under the empty-state info."""
        for term in config.TERMINAL_STATUSES:
            database.add_position(
                make_position({"position_name": f"P-{term}", "status": term})
            )
        at = _run_page()
        assert len(self._expand_buttons(at)) == 1, (
            "Branch (b): expected exactly one [expand] button. "
            f"Got button labels: {[b.label for b in at.button]}"
        )

    def test_funnel_expanded_defaults_false(self, db):
        """Fresh page load → `st.session_state["_funnel_expanded"]` is
        initialized to False via setdefault (covered by `in` check since
        bare absence would also satisfy "not expanded" semantically)."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        assert self.STATE_KEY in at.session_state, (
            f"Expected {self.STATE_KEY!r} to be initialized via setdefault."
        )
        assert at.session_state[self.STATE_KEY] is False, (
            f"Fresh page: {self.STATE_KEY} must default to False. "
            f"Got {at.session_state[self.STATE_KEY]!r}."
        )

    def test_clicking_expand_sets_session_state_true(self, db):
        """Single click → state flag flips to True via on_click callback."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        buttons = self._expand_buttons(at)
        assert len(buttons) == 1
        buttons[0].click().run()
        assert not at.exception, f"[expand] click raised: {at.exception}"
        assert at.session_state[self.STATE_KEY] is True, (
            f"After click: {self.STATE_KEY} must be True. "
            f"Got {at.session_state[self.STATE_KEY]!r}."
        )

    def test_clicking_expand_reveals_all_buckets_on_chart(self, db):
        """Branch (c) click → y-axis now lists every `FUNNEL_BUCKETS` label
        in order (hidden buckets promoted). Key behavioural pin."""
        # Seed data in both a visible bucket and both hidden buckets so
        # expansion produces non-trivial post-expand bars. Bucket-count
        # assertion is covered by TestT2AFunnelBar; here we pin the label
        # list only.
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        database.add_position(make_position({"position_name": "B", "status": "[CLOSED]"}))
        database.add_position(make_position({"position_name": "C", "status": "[REJECTED]"}))
        at = _run_page()

        # Pre-click: only default-visible buckets on the y-axis.
        pre = self._chart_y_labels(at)
        expected_pre = [
            label for label, _, _ in config.FUNNEL_BUCKETS
            if label not in config.FUNNEL_DEFAULT_HIDDEN
        ]
        assert pre == expected_pre, (
            f"Pre-click y-axis must match default-visible buckets. "
            f"expected: {expected_pre}\n got: {pre}"
        )

        # Click
        buttons = self._expand_buttons(at)
        assert len(buttons) == 1
        buttons[0].click().run()
        assert not at.exception, f"[expand] click raised: {at.exception}"

        # Post-click: every bucket in FUNNEL_BUCKETS order.
        post = self._chart_y_labels(at)
        expected_post = [label for label, _, _ in config.FUNNEL_BUCKETS]
        assert post == expected_post, (
            f"Post-click y-axis must include every FUNNEL_BUCKETS label. "
            f"expected: {expected_post}\n got: {post}"
        )

    # NOTE: Pre-T6 `test_expand_button_hides_after_click` was deleted.
    # Its premise (button disappears post-click) inverts under the
    # bidirectional toggle contract — the toggle now PERSISTS post-click
    # with a flipped label so the user can collapse. The "post-click
    # toggle behaviour" is now pinned by `TestT6FunnelToggle`:
    #   - test_click_when_expanded_collapses (collapse path)
    #   - test_round_trip_returns_to_initial_state (involution)
    #   - test_branch_c_renders_toggle_in_both_states (persistence)

    def test_clicking_expand_from_branch_b_renders_chart(self, db):
        """Click from branch (b): all-hidden data becomes visible, so the
        next render is branch (c) with the chart drawn across ALL buckets.
        Verifies the `[expand]` recovery path DESIGN §8.1 promises."""
        for term in config.TERMINAL_STATUSES:
            database.add_position(
                make_position({"position_name": f"P-{term}", "status": term})
            )
        at = _run_page()
        # Branch (b): no chart yet.
        assert len(at.get("plotly_chart")) == 0, (
            "Precondition: branch (b) renders no chart."
        )
        buttons = self._expand_buttons(at)
        assert len(buttons) == 1
        buttons[0].click().run()
        # AppTest captures callback exceptions on at.exception; assert it
        # didn't fire so a broken _toggle_funnel callback is visible
        # before the chart-presence assertion below.
        assert not at.exception, f"Toggle click raised: {at.exception}"
        # Post-click: branch (c) with chart including all buckets.
        assert len(at.get("plotly_chart")) >= 1, (
            "Post-click from branch (b): chart must render."
        )
        post = self._chart_y_labels(at)
        expected_post = [label for label, _, _ in config.FUNNEL_BUCKETS]
        assert post == expected_post, (
            f"Post-click y-axis must include every FUNNEL_BUCKETS label. "
            f"expected: {expected_post}\n got: {post}"
        )


# ── T6 polish: Funnel disclosure toggle (round-trip + tertiary + subheader-row)─

class TestT6FunnelToggle:
    """Phase 4 T6 polish — Funnel disclosure toggle: bidirectional state,
    tertiary visual weight, subheader-row inline placement (DESIGN §8.1
    'Funnel disclosure toggle' row + 'Funnel visibility rules' paragraph,
    T6 amendment 2026-04-30).

    This class pins the THREE new contract claims that the pre-T6
    one-way `[expand]` button didn't carry:

      1. **Bidirectional state.** The toggle has TWO labels, one per
         state of `st.session_state["_funnel_expanded"]`, sourced from
         `config.FUNNEL_TOGGLE_LABELS`. Clicking from the collapsed
         state expands; clicking from the expanded state collapses. A
         round-trip click returns the page to its initial state and
         visible-bucket count (toggle is an involution modulo two
         clicks). This solves the user-reported gap: pre-T6, after
         clicking `[expand]` there was no way back to the focused view
         without ending the session.

      2. **Tertiary visual weight.** The button uses
         `type="tertiary"` so it reads as a chart control rather than
         a primary CTA (lighter than the Materials Readiness CTA's
         default-typed `→ Opportunities page` button — the difference
         in visual weight encodes the difference in role: disclosure
         vs cross-page navigation). Pinned by source grep because
         AppTest's `Button.type` attribute reports the widget class
         name, not the Streamlit `type=` keyword (dev-notes
         streamlit-state-gotchas.md §9).

      3. **Subheader-row inline placement.** The toggle docks at the
         right edge of the funnel subheader row via
         `st.columns([3, 1])` — the same idiom T4 Upcoming uses to
         place its window selector. The pre-T6 placement (button below
         the chart in branch (c), button below the info in branch (b))
         created an inconsistent affordance position across branches;
         the subheader-row placement is invariant across branches
         (b) and (c), so the user's eye doesn't have to re-locate the
         control after a state change. Pinned by source grep alongside
         the tertiary-type pin.

    Group D coverage extends the empty-state matrix by re-asserting
    the toggle's empty-DB suppression (branch (a) — D1) and verifying
    the new branch (b) info copy that points at the toggle by label
    rather than spatial direction (D2 / D3).

    Group E pins the project's `<symbol> <verb-phrase>` CTA convention
    (the leading `+` / `−` characters) so a future label rephrase can't
    silently drift back to the bracket convention.
    """

    # ── Locked vocab + state ───────────────────────────────────────────────
    # Class-scope literals (not `config.FUNNEL_TOGGLE_LABELS[...]`) so
    # collection survives a tree where config hasn't been re-imported
    # — same reasoning documented in TestT2BFunnelEmptyState. Drift
    # against config is pinned by Group A.3 below + the invariant #11
    # tests in test_config.py.
    EXPAND_LABEL    = "+ Show all stages"
    COLLAPSE_LABEL  = "− Show fewer stages"   # U+2212 minus, paired with U+002B '+'
    STATE_KEY       = "_funnel_expanded"
    SUBHEADER       = "Application Funnel"
    BRANCH_B_COPY   = (
        "All your positions are in hidden buckets. "
        "Click 'Show all stages' to reveal them."
    )

    # ── Helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def _toggle(at: AppTest, *, label: str | None = None):
        """Return the toggle button (any state) — match by `label` if
        given, else any of the two valid labels. Returns None when the
        toggle is not rendered (branch (a) — D1)."""
        valid = (
            {label}
            if label is not None
            else {TestT6FunnelToggle.EXPAND_LABEL, TestT6FunnelToggle.COLLAPSE_LABEL}
        )
        matches = [b for b in at.button if b.label in valid]
        return matches[0] if matches else None

    @staticmethod
    def _chart_bucket_count(at: AppTest) -> int:
        """How many bars the funnel chart renders. Used by the
        round-trip tests to verify the chart shrinks back to the
        default-visible buckets after a collapse click."""
        import json
        charts = at.get("plotly_chart")
        if not charts:
            return 0
        spec = json.loads(charts[0].proto.spec)
        return len(spec["data"][0]["y"])

    @staticmethod
    def _read_app_source() -> str:
        """Read app.py source for the C1/C2 source-grep tests. Sourced
        once; sub-string assertions per call. The repo path is computed
        from this test file's location so the test is robust to a
        different cwd at runtime (project doesn't pin cwd in pytest
        fixtures)."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parent.parent
        return (repo_root / "app.py").read_text(encoding="utf-8")

    # ── Group A: label correctness in each state ──────────────────────────

    def test_collapsed_state_shows_expand_label(self, db):
        """A.1 — Default render (collapsed) → toggle label is
        `config.FUNNEL_TOGGLE_LABELS[False]`."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        assert at.session_state[self.STATE_KEY] is False
        toggle = self._toggle(at)
        assert toggle is not None, (
            "Collapsed state: toggle must render. "
            f"Got button labels: {[b.label for b in at.button]}"
        )
        assert toggle.label == self.EXPAND_LABEL, (
            f"Collapsed state: label must be {self.EXPAND_LABEL!r}. "
            f"Got {toggle.label!r}."
        )

    def test_expanded_state_shows_collapse_label(self, db):
        """A.2 — After clicking expand → label flips to
        `config.FUNNEL_TOGGLE_LABELS[True]`."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        at = _run_page()
        toggle = self._toggle(at, label=self.EXPAND_LABEL)
        assert toggle is not None
        toggle.click().run()
        assert not at.exception, f"Toggle click raised: {at.exception}"
        assert at.session_state[self.STATE_KEY] is True
        post = self._toggle(at, label=self.COLLAPSE_LABEL)
        assert post is not None, (
            f"Expanded state: label must flip to {self.COLLAPSE_LABEL!r}. "
            f"Got button labels: {[b.label for b in at.button]}"
        )

    def test_class_literals_match_config(self, db):
        """A.3a — The class-scope `EXPAND_LABEL` / `COLLAPSE_LABEL`
        literals (duplicated at class scope for collection-time
        stability) must equal the canonical values in
        `config.FUNNEL_TOGGLE_LABELS`. Drift between this class and
        config would silently weaken every other assertion in the
        class (the buttons would carry config's label, but tests
        would compare against the class literal). Pinned with a
        single-line equality."""
        assert config.FUNNEL_TOGGLE_LABELS[False] == self.EXPAND_LABEL, (
            f"Class literal EXPAND_LABEL={self.EXPAND_LABEL!r} drifted "
            f"from config.FUNNEL_TOGGLE_LABELS[False]="
            f"{config.FUNNEL_TOGGLE_LABELS[False]!r}. Update both."
        )
        assert config.FUNNEL_TOGGLE_LABELS[True] == self.COLLAPSE_LABEL, (
            f"Class literal COLLAPSE_LABEL={self.COLLAPSE_LABEL!r} drifted "
            f"from config.FUNNEL_TOGGLE_LABELS[True]="
            f"{config.FUNNEL_TOGGLE_LABELS[True]!r}. Update both."
        )

    def test_no_hardcoded_label_literal_in_app_source(self, db):
        """A.3 — Source grep: app.py must not carry the literal
        `[expand]` or `[collapse]` (pre-T6 pre-CTA-convention strings)
        nor the new literals `+ Show all stages` / `− Show fewer stages`.
        Both labels go through `config.FUNNEL_TOGGLE_LABELS` per
        GUIDELINES §6 'no hardcoded vocab'.

        The test guards two drift modes at once:
          - Stale: someone re-introduces `[expand]` in a comment or
            string when adding a feature.
          - Fresh-but-wrong: someone copies the new literal directly
            into app.py instead of reading from config.
        """
        src = self._read_app_source()
        forbidden = [
            # Pre-T6 bracket literals.
            '"[expand]"',
            "'[expand]'",
            '"[collapse]"',
            "'[collapse]'",
            # New literals — must arrive via config, not as strings here.
            f'"{self.EXPAND_LABEL}"',
            f"'{self.EXPAND_LABEL}'",
            f'"{self.COLLAPSE_LABEL}"',
            f"'{self.COLLAPSE_LABEL}'",
        ]
        hits = [needle for needle in forbidden if needle in src]
        assert hits == [], (
            f"app.py carries forbidden hardcoded toggle label literal(s): "
            f"{hits!r}. Use config.FUNNEL_TOGGLE_LABELS[bool] instead — "
            f"GUIDELINES §6, DESIGN §8.1 T6 amendment."
        )

    # ── Group B: round-trip behaviour ─────────────────────────────────────

    def test_click_when_collapsed_expands(self, db):
        """B.1 — Click from collapsed → state True + visible-bucket
        count jumps from `len(visible default buckets)` to
        `len(FUNNEL_BUCKETS)`."""
        # Seed across visible + hidden buckets so the count diff is
        # non-trivial and visible.
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        database.add_position(make_position({"position_name": "B", "status": "[CLOSED]"}))
        database.add_position(make_position({"position_name": "C", "status": "[REJECTED]"}))
        at = _run_page()
        n_pre = self._chart_bucket_count(at)
        expected_pre = len([
            label for label, _, _ in config.FUNNEL_BUCKETS
            if label not in config.FUNNEL_DEFAULT_HIDDEN
        ])
        assert n_pre == expected_pre, (
            f"Pre-click: expected {expected_pre} default-visible bars; "
            f"got {n_pre}."
        )
        toggle = self._toggle(at, label=self.EXPAND_LABEL)
        assert toggle is not None
        toggle.click().run()
        assert not at.exception, f"Expand click raised: {at.exception}"
        assert at.session_state[self.STATE_KEY] is True
        n_post = self._chart_bucket_count(at)
        assert n_post == len(config.FUNNEL_BUCKETS), (
            f"Post-expand: expected all {len(config.FUNNEL_BUCKETS)} bars; "
            f"got {n_post}."
        )

    def test_click_when_expanded_collapses(self, db):
        """B.2 — Click from expanded → state False + visible-bucket
        count drops back to default. **This is the test that pins the
        user-reported bug fix** — pre-T6, no second click was possible."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        database.add_position(make_position({"position_name": "B", "status": "[CLOSED]"}))
        # First click to expand.
        at = _run_page()
        toggle = self._toggle(at, label=self.EXPAND_LABEL)
        assert toggle is not None
        toggle.click().run()
        assert at.session_state[self.STATE_KEY] is True
        # Second click to collapse.
        toggle_post = self._toggle(at, label=self.COLLAPSE_LABEL)
        assert toggle_post is not None, (
            "After expand: collapse-labelled toggle must be present. "
            f"Got: {[b.label for b in at.button]}"
        )
        toggle_post.click().run()
        assert not at.exception, f"Collapse click raised: {at.exception}"
        assert at.session_state[self.STATE_KEY] is False, (
            "Post-collapse: state must flip back to False."
        )
        n_post = self._chart_bucket_count(at)
        expected_post = len([
            label for label, _, _ in config.FUNNEL_BUCKETS
            if label not in config.FUNNEL_DEFAULT_HIDDEN
        ])
        assert n_post == expected_post, (
            f"Post-collapse: visible-bar count must shrink back to "
            f"default ({expected_post}); got {n_post}."
        )

    def test_round_trip_returns_to_initial_state(self, db):
        """B.3 — Two clicks in succession → label, state flag, and
        visible-bucket count are pixel-equal to the initial render
        (toggle is a true involution modulo two clicks)."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        database.add_position(make_position({"position_name": "B", "status": "[CLOSED]"}))
        at = _run_page()
        initial_toggle = self._toggle(at)
        assert initial_toggle is not None, (
            "Initial render: toggle must exist (branch (c)). "
            f"Got button labels: {[b.label for b in at.button]}"
        )
        initial_label = initial_toggle.label
        initial_state = at.session_state[self.STATE_KEY]
        initial_count = self._chart_bucket_count(at)
        # Click 1 (expand).
        toggle_1 = self._toggle(at, label=self.EXPAND_LABEL)
        assert toggle_1 is not None, (
            "Round-trip click 1: expand-labelled toggle must render."
        )
        toggle_1.click().run()
        assert not at.exception
        # Click 2 (collapse) — state-aware lookup so a missing button
        # surfaces a clearer assertion than a cryptic NoneType chain.
        toggle_2 = self._toggle(at, label=self.COLLAPSE_LABEL)
        assert toggle_2 is not None, (
            "Round-trip click 2: collapse-labelled toggle must be "
            f"available after click 1. Got: {[b.label for b in at.button]}"
        )
        toggle_2.click().run()
        assert not at.exception
        # Final state matches initial — involution.
        final_toggle = self._toggle(at)
        assert final_toggle is not None, (
            "Final render: toggle must exist after round-trip."
        )
        final_label = final_toggle.label
        final_state = at.session_state[self.STATE_KEY]
        final_count = self._chart_bucket_count(at)
        assert final_label == initial_label, (
            f"Involution: label must return to {initial_label!r}; "
            f"got {final_label!r}."
        )
        assert final_state == initial_state, (
            f"Involution: state flag must return to {initial_state!r}; "
            f"got {final_state!r}."
        )
        assert final_count == initial_count, (
            f"Involution: visible-bar count must return to "
            f"{initial_count}; got {final_count}."
        )

    def test_round_trip_through_branch_b(self, db):
        """B.4 — Toggle works across the branch (b) ↔ (c) boundary.
        Start: terminal-only DB → branch (b) (info, no chart). Click
        once → branch (c) (chart with all buckets). Click again →
        branch (b) (info reappears, chart gone). Pins that the toggle
        round-trips through the empty-state matrix without trapping
        the user in either branch."""
        for term in config.TERMINAL_STATUSES:
            database.add_position(
                make_position({"position_name": f"P-{term}", "status": term})
            )
        at = _run_page()
        # Precondition: branch (b).
        assert len(at.get("plotly_chart")) == 0, "Precondition: branch (b)."
        assert any(i.value == self.BRANCH_B_COPY for i in at.info), (
            "Precondition: branch (b) info copy must render."
        )
        # Click 1: expand → branch (c).
        toggle_1 = self._toggle(at, label=self.EXPAND_LABEL)
        assert toggle_1 is not None, (
            "Branch (b) → (c) expand: toggle must render in the info "
            "branch so the user can flip into the chart branch."
        )
        toggle_1.click().run()
        assert not at.exception
        assert at.session_state[self.STATE_KEY] is True
        assert len(at.get("plotly_chart")) >= 1, (
            "Post-expand: branch (c) chart must render."
        )
        assert not any(i.value == self.BRANCH_B_COPY for i in at.info), (
            "Post-expand: branch (b) info must NOT render alongside chart."
        )
        # Click 2: collapse → back to branch (b).
        toggle_2 = self._toggle(at, label=self.COLLAPSE_LABEL)
        assert toggle_2 is not None
        toggle_2.click().run()
        assert not at.exception
        assert at.session_state[self.STATE_KEY] is False
        assert len(at.get("plotly_chart")) == 0, (
            "Post-collapse: chart must disappear (back to branch (b))."
        )
        assert any(i.value == self.BRANCH_B_COPY for i in at.info), (
            "Post-collapse: branch (b) info must reappear."
        )

    # ── Group C: subheader-row placement (source-grep) ────────────────────

    def test_subheader_row_uses_columns_3_1(self, db):
        """C.1 — Source grep: app.py contains the `st.columns([3, 1])`
        idiom in **executable code** (not just comments) at least
        twice — once for the funnel subheader row (T6), once for the
        Upcoming subheader row (pre-existing T4 idiom). The test
        filters out comment lines first, mirroring the §6 status-
        literal grep cleanup direction noted in `project_state.md`
        (the project's existing comment-FP carry-over).

        Why ≥ 2 not == 2: a future panel (e.g. Phase 7 T1 urgency-
        color toggle on Opportunities, or Phase 5 Recommenders alert
        filter) is encouraged to reuse the same idiom — DESIGN §8.1
        T6 amendment establishes it as the canonical
        chart-with-controls pattern. Allowing > 2 future-proofs the
        test against incidental adoption."""
        src = self._read_app_source()
        # Strip comment-only lines so the comment at app.py:290
        # ("# Layout: an st.columns([3, 1]) pair...") doesn't satisfy
        # the count vacuously. Inline `# foo` after code is not stripped
        # because the line still contains executable code; that's the
        # right semantics — a real call would still count.
        code_lines = [
            line for line in src.splitlines()
            if not line.lstrip().startswith("#")
        ]
        code = "\n".join(code_lines)
        count = code.count("st.columns([3, 1])") + code.count("st.columns([3,1])")
        assert count >= 2, (
            f"DESIGN §8.1 T6 amendment: funnel must adopt the same "
            f"`st.columns([3, 1])` subheader-row idiom as Upcoming. "
            f"Expected ≥ 2 executable-code occurrences in app.py "
            f"(Funnel + Upcoming); found {count}. Comment-only lines "
            f"were filtered before counting."
        )

    def test_toggle_uses_tertiary_type(self, db):
        """C.2 — Source grep: the funnel toggle is rendered with
        `type="tertiary"`. Pinned by grep because AppTest's
        `Button.type` reports the widget class name, not the
        Streamlit `type=` keyword (dev-notes gotcha #9). The assertion
        is structural: the only `type="tertiary"` button on the
        dashboard is the funnel toggle, so an exact-count grep on
        executable code is a precise pin.

        Comment-only lines are stripped before counting — same
        carve-out as C.1 — so descriptive comments that quote
        `type="tertiary"` (e.g. the section header explaining the
        toggle) don't double-count."""
        src = self._read_app_source()
        code_lines = [
            line for line in src.splitlines()
            if not line.lstrip().startswith("#")
        ]
        code = "\n".join(code_lines)
        count = code.count('type="tertiary"')
        assert count == 1, (
            f"DESIGN §8.1 T6 amendment: funnel toggle must be the only "
            f"`type=\"tertiary\"` button on app.py (a tertiary CTA "
            f"elsewhere would break the disclosure-affordance contract). "
            f"Expected exactly 1 executable-code occurrence; found "
            f"{count}. Comment-only lines were filtered before counting."
        )

    # ── Group D: empty-state matrix (re-pin under new contract) ───────────

    def test_branch_a_suppresses_toggle(self, db):
        """D.1 — Empty DB → no toggle in either label form. (Re-pinned
        from T2D under the renamed-contract docs; pre-T6 this asserted
        absence of `[expand]`; post-T6 same suppression but covering
        both labels in case state somehow flipped True before the
        first render.)"""
        at = _run_page()
        assert self._toggle(at) is None, (
            "Branch (a): toggle must be SUPPRESSED — nothing to "
            f"disclose into. Got: {[b.label for b in at.button]}"
        )

    def test_branch_b_renders_toggle_with_collapsed_label(self, db):
        """D.2 — Branch (b) (terminal-only DB) → toggle present with
        the COLLAPSED label (state defaults False; user hasn't clicked
        yet). New: the toggle now sits in the subheader row, not below
        the info — but presence is what the matrix pins, not position
        (position is C.1)."""
        for term in config.TERMINAL_STATUSES:
            database.add_position(
                make_position({"position_name": f"P-{term}", "status": term})
            )
        at = _run_page()
        toggle = self._toggle(at)
        assert toggle is not None, (
            "Branch (b): toggle must render. "
            f"Got: {[b.label for b in at.button]}"
        )
        assert toggle.label == self.EXPAND_LABEL, (
            f"Branch (b) at default state: label must be "
            f"{self.EXPAND_LABEL!r}; got {toggle.label!r}."
        )

    def test_branch_b_info_copy_is_spec_exact(self, db):
        """D.3 — Branch (b) info copy points at the toggle by LABEL,
        not by spatial direction. Pre-T6 wording said
        `Click [expand] below to reveal them.` (tied to the now-
        relocated below-the-info button); post-T6 wording references
        the literal label so the copy stays correct regardless of where
        the toggle sits visually."""
        for term in config.TERMINAL_STATUSES:
            database.add_position(
                make_position({"position_name": f"P-{term}", "status": term})
            )
        at = _run_page()
        matching = [i for i in at.info if i.value == self.BRANCH_B_COPY]
        assert len(matching) == 1, (
            f"Branch (b): expected exactly one info with copy "
            f"{self.BRANCH_B_COPY!r}. Got info bodies: "
            f"{[i.value for i in at.info]}"
        )

    def test_branch_c_renders_toggle_in_both_states(self, db):
        """D.4 — Branch (c) renders the toggle in BOTH collapsed and
        expanded states (the second is the user's reported bug fix —
        post-T6 the toggle persists as `− Show fewer stages`)."""
        database.add_position(make_position({"position_name": "A", "status": "[SAVED]"}))
        # Collapsed.
        at = _run_page()
        assert self._toggle(at, label=self.EXPAND_LABEL) is not None, (
            "Branch (c) collapsed: expand-labelled toggle must render."
        )
        # Expanded — click to flip.
        expand_toggle = self._toggle(at, label=self.EXPAND_LABEL)
        assert expand_toggle is not None, (
            "Branch (c) collapsed: expand toggle must render before flip."
        )
        expand_toggle.click().run()
        assert not at.exception
        assert self._toggle(at, label=self.COLLAPSE_LABEL) is not None, (
            "Branch (c) expanded: collapse-labelled toggle must render. "
            "This is the user-reported bug fix — pre-T6 no toggle "
            "persisted post-click."
        )

    # ── Group E: vocabulary cohesion across CTAs ──────────────────────────

    def test_label_symbols_match_cta_convention(self, db):
        """E.2 — The two toggle labels follow the project's
        `<symbol> <verb-phrase>` CTA convention used by the empty-DB
        hero (`+ Add your first position`) and the Materials Readiness
        CTA (`→ Opportunities page`). Pinned here so a future
        well-meaning rephrase (e.g. back to bracket form) trips the
        test rather than silently drifting the four dashboard CTAs out
        of cohesion."""
        # `+` for collapsed (clicking adds buckets to the view) and
        # `−` for expanded (clicking removes some) — the symbol is the
        # delta direction the click will produce.
        assert self.EXPAND_LABEL.startswith("+ "), (
            f"CTA convention: collapsed label must start with '+ ' "
            f"(symbol-prefix CTA). Got {self.EXPAND_LABEL!r}."
        )
        assert self.COLLAPSE_LABEL.startswith("− "), (  # U+2212 minus
            f"CTA convention: expanded label must start with '− ' "
            f"(U+2212 minus, paired with the '+' on the collapsed side "
            f"for a + / − reversibility cue). Got {self.COLLAPSE_LABEL!r}."
        )


# ── T3: Materials Readiness — right half of the T2-C `st.columns(2)` ──────────

class TestT3MaterialsReadiness:
    """T3: Materials Readiness panel on the dashboard.

    Locked design decisions (conductor brief, 2026-04-22):
      D1. Visual = TWO `st.progress` bars (Ready, Missing); each value =
          count / max(ready + pending, 1). No st.metric, no Plotly.
      D2. CTA button labelled exactly '→ Opportunities page' with
          key='materials_readiness_cta' calling
          st.switch_page('pages/1_Opportunities.py') on click.
      D3. Empty state: when `ready + pending == 0`, skip both bars + CTA
          and render st.info with the locked copy. Subheader ALWAYS renders.
      D4. Ship as one commit-triple (no T3-A / T3-B split).
      D5. Denominator guarded by `max(ready + pending, 1)`.

    Layout: the panel lives in the RIGHT half of the SINGLE `st.columns(2)`
    created in T2-C (no new split). The `proto.weight == 0.5` pair is the
    structural marker — same pattern as TestT2CFunnelLayout.

    AppTest access pattern (probed against Streamlit 1.56):
      - `st.progress(value: float, text: str | None)` — AppTest exposes
        each bar as an `UnknownElement` at `at.get("progress")`; the
        underlying proto has `.value` (int 0-100) and `.text` (label).
        Column-scoped retrieval (`col.get("progress")`) works identically.
      - CTA route: AppTest single-file mode cannot navigate siblings, so
        the switch_page target is pinned at the source level (T1-E precedent).
    """

    SUBHEADER = "Materials Readiness"
    EMPTY_COPY = (
        "Materials readiness will appear once you've added positions "
        "with required documents."
    )
    CTA_LABEL = "→ Opportunities page"
    CTA_KEY = "materials_readiness_cta"
    TARGET_PAGE = "pages/1_Opportunities.py"

    @staticmethod
    def _half_width_columns(at: AppTest):
        return [c for c in at.columns if c.proto.weight == 0.5]

    @classmethod
    def _right_col(cls, at: AppTest):
        halves = cls._half_width_columns(at)
        assert len(halves) == 2, (
            f"T3 precondition: the T2-C `st.columns(2)` pair must exist. "
            f"Got {len(halves)} half-width columns."
        )
        return halves[1]

    @classmethod
    def _left_col(cls, at: AppTest):
        halves = cls._half_width_columns(at)
        assert len(halves) == 2, (
            f"T3 precondition: the T2-C `st.columns(2)` pair must exist. "
            f"Got {len(halves)} half-width columns."
        )
        return halves[0]

    @classmethod
    def _subheader_in(cls, col) -> bool:
        return any(s.value == cls.SUBHEADER for s in col.subheader)

    def test_subheader_renders_in_right_column_always(self, db):
        """The 'Materials Readiness' subheader renders inside the right
        half-width column on BOTH an empty DB and a populated DB — so
        page height doesn't flicker across the empty-to-seeded transition
        (mirrors T2-C's stability pin on the funnel subheader)."""
        at_empty = _run_page()
        assert self._subheader_in(self._right_col(at_empty)), (
            "Expected 'Materials Readiness' subheader inside the right "
            "half-width column on an empty DB. Right subheaders: "
            f"{[s.value for s in self._right_col(at_empty).subheader]}"
        )

        database.add_position(
            make_position({"position_name": "A", "status": "[SAVED]", "req_cv": "Yes"})
        )
        at_seeded = _run_page()
        assert self._subheader_in(self._right_col(at_seeded)), (
            "Expected 'Materials Readiness' subheader inside the right "
            "half-width column on a populated DB. Right subheaders: "
            f"{[s.value for s in self._right_col(at_seeded).subheader]}"
        )

    def test_subheader_does_not_leak_into_left_column(self, db):
        """The left half is reserved for the Application Funnel — the
        Readiness subheader must not appear there. Pins that the block
        is actually inside `with _right_col:` and not leaked to the
        top-level or the wrong column."""
        database.add_position(
            make_position({"position_name": "A", "status": "[SAVED]", "req_cv": "Yes"})
        )
        at = _run_page()
        left = self._left_col(at)
        assert not self._subheader_in(left), (
            "'Materials Readiness' subheader must NOT appear in the left "
            "half-width column (reserved for the funnel). Left subheaders: "
            f"{[s.value for s in left.subheader]}"
        )

    def test_empty_db_shows_info_empty_state(self, db):
        """Empty DB (ready + pending == 0): exactly one st.info inside
        the right column, zero progress bars, no CTA button. D3 locked."""
        at = _run_page()
        right = self._right_col(at)
        assert len(right.get("progress")) == 0, (
            f"Empty DB must render NO progress bars in the right column "
            f"(D3). Got {len(right.get('progress'))}."
        )
        info_bodies = [i.value for i in right.info]
        assert len(info_bodies) == 1, (
            f"Empty DB must render exactly one st.info in the right "
            f"column (the readiness empty state). Got: {info_bodies}"
        )
        cta_buttons = [b for b in right.button if b.key == self.CTA_KEY]
        assert cta_buttons == [], (
            f"CTA button must NOT render in the empty state (D3). "
            f"Got buttons with key={self.CTA_KEY!r}: {cta_buttons}"
        )

    def test_readiness_copy_is_spec_exact(self, db):
        """Empty-state copy matches the locked string verbatim.

        Mirrors TestT2BFunnelEmptyState.test_empty_state_copy_is_spec_exact —
        guards against accidental rewording; a rephrase requires a new
        user decision."""
        at = _run_page()
        right = self._right_col(at)
        matching = [i for i in right.info if i.value == self.EMPTY_COPY]
        assert len(matching) == 1, (
            f"Expected exactly one info in the right column with the exact "
            f"copy {self.EMPTY_COPY!r}. Got: {[i.value for i in right.info]}"
        )

    def test_populated_db_renders_two_progress_bars(self, db):
        """Seed 1 ready + 2 pending → exactly 2 progress bars (values
        1/3 and 2/3) in the right column, no empty-state info.

        Readiness semantics (database.compute_materials_readiness):
          - Active-only (status in OPEN / APPLIED / INTERVIEW).
          - 'Ready' iff every req_* = 'Yes' also has done_* = 1.
          - Only counts positions with at least one required doc.
        Using req_cv='Yes' for all three; flip done_cv for the ready one."""
        database.add_position(make_position({
            "position_name": "Ready-A", "status": "[SAVED]",
            "req_cv": "Yes", "done_cv": 1,
        }))
        database.add_position(make_position({
            "position_name": "Pending-B", "status": "[APPLIED]",
            "req_cv": "Yes", "done_cv": 0,
        }))
        database.add_position(make_position({
            "position_name": "Pending-C", "status": "[INTERVIEW]",
            "req_cv": "Yes", "done_cv": 0,
        }))

        at = _run_page()
        right = self._right_col(at)
        bars = right.get("progress")
        assert len(bars) == 2, (
            f"Populated DB (1 ready + 2 pending) must render exactly 2 "
            f"progress bars in the right column. Got {len(bars)}."
        )
        # proto.value is the 0-100 int form of the float passed to st.progress.
        v0 = bars[0].proto.value / 100.0
        v1 = bars[1].proto.value / 100.0
        assert abs(v0 - (1 / 3)) < 0.02, (
            f"First bar (Ready) should be 1/3 ≈ 0.333; got {v0} "
            f"(proto.value={bars[0].proto.value})."
        )
        assert abs(v1 - (2 / 3)) < 0.02, (
            f"Second bar (Missing) should be 2/3 ≈ 0.667; got {v1} "
            f"(proto.value={bars[1].proto.value})."
        )
        assert all(i.value != self.EMPTY_COPY for i in right.info), (
            "Empty-state info must NOT render once any position has a "
            "required doc. Got right-column info bodies: "
            f"{[i.value for i in right.info]}"
        )

    def test_progress_labels_include_counts(self, db):
        """Progress bar labels carry the exact 'Ready to submit: N' and
        'Still missing: M' copy, in that order. The conductor brief
        accepts the verified parameter name (`text=`) — asserting on the
        visible string is what the UI contract promises."""
        database.add_position(make_position({
            "position_name": "Ready-A", "status": "[SAVED]",
            "req_cv": "Yes", "done_cv": 1,
        }))
        database.add_position(make_position({
            "position_name": "Pending-B", "status": "[APPLIED]",
            "req_cv": "Yes", "done_cv": 0,
        }))
        database.add_position(make_position({
            "position_name": "Pending-C", "status": "[INTERVIEW]",
            "req_cv": "Yes", "done_cv": 0,
        }))

        at = _run_page()
        right = self._right_col(at)
        bars = right.get("progress")
        assert len(bars) == 2, (
            f"Precondition for this test: 2 progress bars. Got {len(bars)}."
        )
        label0 = bars[0].proto.text
        label1 = bars[1].proto.text
        assert label0 == "Ready to submit: 1", (
            f"First bar label must be 'Ready to submit: 1', got {label0!r}"
        )
        assert label1 == "Still missing: 2", (
            f"Second bar label must be 'Still missing: 2', got {label1!r}"
        )

    def test_terminal_only_db_shows_empty_state(self, db):
        """A DB with only terminal-status rows has no active positions,
        so compute_materials_readiness() returns 0/0 — the empty-state
        info must render (and no progress bars, no CTA).

        This differs from the T2-B funnel (which still renders on a
        terminal-only DB) because the readiness panel is definitionally
        scoped to the active pipeline."""
        for term in config.TERMINAL_STATUSES:
            database.add_position(make_position({
                "position_name": f"P-{term}", "status": term, "req_cv": "Yes",
            }))
        at = _run_page()
        right = self._right_col(at)
        assert len(right.get("progress")) == 0, (
            "Terminal-only DB → ready + pending == 0 → no progress bars."
        )
        matching = [i for i in right.info if i.value == self.EMPTY_COPY]
        assert len(matching) == 1, (
            f"Terminal-only DB must render the readiness empty-state info. "
            f"Got right-column info bodies: {[i.value for i in right.info]}"
        )
        cta_buttons = [b for b in right.button if b.key == self.CTA_KEY]
        assert cta_buttons == [], (
            "CTA must NOT render in the terminal-only (empty-state) case."
        )

    def test_cta_button_routes_to_opportunities_page(self, db):
        """CTA contract (D2):
          (a) A button with key='materials_readiness_cta' and label
              '→ Opportunities page' renders in the populated case.
          (b) app.py source contains the st.switch_page('pages/1_Opportunities.py')
              call inside the readiness block (AppTest single-file mode
              cannot navigate siblings — T1-E precedent)."""
        database.add_position(make_position({
            "position_name": "A", "status": "[SAVED]",
            "req_cv": "Yes", "done_cv": 0,
        }))
        at = _run_page()
        right = self._right_col(at)
        cta_buttons = [b for b in right.button if b.key == self.CTA_KEY]
        assert len(cta_buttons) == 1, (
            f"Expected exactly one CTA button with key={self.CTA_KEY!r} "
            f"in the right column. Got keys: {[b.key for b in right.button]}"
        )
        assert cta_buttons[0].label == self.CTA_LABEL, (
            f"CTA button label must be exactly {self.CTA_LABEL!r}, got "
            f"{cta_buttons[0].label!r}"
        )

        import pathlib
        src = pathlib.Path("app.py").read_text(encoding="utf-8")
        assert f'st.switch_page("{self.TARGET_PAGE}")' in src, (
            f"app.py must call st.switch_page(\"{self.TARGET_PAGE}\") — "
            "T1-E precedent pins the route target at the source level."
        )


# ── T4: Upcoming timeline panel ───────────────────────────────────────────────

class TestT4UpcomingTimeline:
    """T4-B: Upcoming panel rendering on the dashboard.

    DESIGN §8.1 (T4-0 + T4-0b lock-down): a single full-width section
    below the funnel/readiness `st.columns(2)` row. Layout is an
    `st.columns([3, 1])` pair carrying the dynamic subheader on the
    left and a window-width selectbox on the right.

    Locked panel contract:
      - Subheader 'Upcoming (next X days)' renders in BOTH empty and
        populated branches for page-height stability (T2/T3 precedent).
      - Window selectbox (key=`upcoming_window`) offers
        `config.UPCOMING_WINDOW_OPTIONS`; default = DEADLINE_ALERT_DAYS.
      - Empty branch: `st.info` with `EMPTY_COPY_DEFAULT` verbatim
        (interpolating the selected window).
      - Populated branch: `st.dataframe` with display headers
        (Date, Days left, Label, Kind, Status, Urgency); Date column
        rendered via `st.column_config.DateColumn(format="MMM D")`
        for the spec'd 'Apr 24' phrasing; Status mapped through
        STATUS_LABELS (DESIGN §8.0 — never raw bracketed sentinels);
        Days left / Kind / Urgency / Label pass through T4-A's
        projection unchanged.

    AppTest access patterns (verified against Streamlit 1.56):
      - `at.dataframe[0].value` returns the underlying pandas DataFrame
        (Date column carries datetime.date objects; the DateColumn
        format string is applied client-side and is invisible to AppTest,
        so the format string is pinned via a source grep — T1-E precedent).
      - `at.selectbox(key=...).value` returns the option (not the index);
        `at.selectbox(key=...).set_value(v).run()` triggers a rerun
        with the new value.
    """

    SUBHEADER_DEFAULT = f"Upcoming (next {config.DEADLINE_ALERT_DAYS} days)"
    EMPTY_COPY_DEFAULT = (
        f"No deadlines or interviews in the next "
        f"{config.DEADLINE_ALERT_DAYS} days."
    )
    DISPLAY_COLUMNS = ["Date", "Days left", "Label", "Kind", "Status", "Urgency"]
    WINDOW_KEY = "upcoming_window"
    DATE_COLUMN_FORMAT_SOURCE = 'st.column_config.DateColumn(format="MMM D")'

    @staticmethod
    def _half_width_columns(at: AppTest):
        return [c for c in at.columns if c.proto.weight == 0.5]

    @classmethod
    def _has_subheader(cls, container, value: str | None = None) -> bool:
        target = value or cls.SUBHEADER_DEFAULT
        return any(s.value == target for s in container.subheader)

    # ── Group A: subheader stability + layout ─────────────────────────────

    def test_subheader_renders_on_empty_db(self, db):
        """Page-height stability: the subheader renders even when there
        is nothing to show, so the layout above doesn't shift when the
        first qualifying deadline lands."""
        at = _run_page()
        assert self._has_subheader(at), (
            f"Empty DB: expected top-level {self.SUBHEADER_DEFAULT!r} "
            f"subheader. Got: {[s.value for s in at.subheader]}"
        )

    def test_subheader_renders_on_populated_db(self, db):
        """Same page-height-stability invariant on the populated path."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=10)).isoformat(),
        }))
        at = _run_page()
        assert self._has_subheader(at), (
            f"Populated DB: expected top-level {self.SUBHEADER_DEFAULT!r} "
            f"subheader. Got: {[s.value for s in at.subheader]}"
        )

    def test_panel_lives_outside_funnel_readiness_columns_pair(self, db):
        """Layout: the T4 panel sits BELOW the funnel/readiness
        st.columns(2) pair, NOT inside either half-column. Combines a
        top-level existence check with two column-exclusion checks so
        the test cannot pass vacuously when the panel is unwired."""
        at = _run_page()
        halves = self._half_width_columns(at)
        assert len(halves) == 2, (
            f"Precondition: T2-C creates exactly one st.columns(2) pair. "
            f"Got {len(halves)} half-width columns."
        )
        left, right = halves
        assert self._has_subheader(at), (
            f"{self.SUBHEADER_DEFAULT!r} must appear on the page "
            f"(existence check, guards against vacuous pass). Got "
            f"top-level subheaders: {[s.value for s in at.subheader]}"
        )
        assert not self._has_subheader(left), (
            f"{self.SUBHEADER_DEFAULT!r} must NOT appear in the left "
            f"half-width column. Got left subheaders: "
            f"{[s.value for s in left.subheader]}"
        )
        assert not self._has_subheader(right), (
            f"{self.SUBHEADER_DEFAULT!r} must NOT appear in the right "
            f"half-width column. Got right subheaders: "
            f"{[s.value for s in right.subheader]}"
        )

    # ── Group B: window selectbox ─────────────────────────────────────────

    def test_window_selector_default_is_deadline_alert_days(self, db):
        """The selectbox lands at DEADLINE_ALERT_DAYS on first render —
        the dashboard's default 'how far ahead am I looking?' answer
        comes from a single config constant and stays in sync with the
        urgency band."""
        at = _run_page()
        sb = at.selectbox(key=self.WINDOW_KEY)
        assert sb.value == config.DEADLINE_ALERT_DAYS, (
            f"Selectbox default must equal DEADLINE_ALERT_DAYS="
            f"{config.DEADLINE_ALERT_DAYS}. Got {sb.value!r}"
        )

    def test_window_selector_offers_config_window_options(self, db):
        """Selectbox options come from config.UPCOMING_WINDOW_OPTIONS —
        no hardcoded list in app.py per GUIDELINES §6 (no hardcoded
        vocab). Pins the spec→config→page chain.

        AppTest 1.56 quirk: `selectbox.options` returns the
        protobuf-serialized form (strings) regardless of the original
        Python type, while `selectbox.value` round-trips correctly
        back to the original type. Compare against the stringified
        config list, with the original list shown in the message for
        debug clarity."""
        at = _run_page()
        sb = at.selectbox(key=self.WINDOW_KEY)
        expected_strs = [str(v) for v in config.UPCOMING_WINDOW_OPTIONS]
        assert list(sb.options) == expected_strs, (
            f"AppTest exposes selectbox options as strings; expected "
            f"{expected_strs!r} (stringified config.UPCOMING_WINDOW_OPTIONS="
            f"{config.UPCOMING_WINDOW_OPTIONS!r}). Got {list(sb.options)!r}"
        )

    # ── Group C: empty / populated branches ───────────────────────────────

    def test_empty_db_renders_info_with_locked_copy(self, db):
        """Empty DB at default window: exactly one st.info matching
        EMPTY_COPY_DEFAULT verbatim, no st.dataframe."""
        at = _run_page()
        matching = [i for i in at.info if i.value == self.EMPTY_COPY_DEFAULT]
        assert len(matching) == 1, (
            f"Empty DB: expected exactly one st.info with copy "
            f"{self.EMPTY_COPY_DEFAULT!r}. Got info bodies: "
            f"{[i.value for i in at.info]}"
        )
        assert len(at.dataframe) == 0, (
            f"Empty DB: no st.dataframe should render in the Upcoming "
            f"panel. Got {len(at.dataframe)} dataframe(s)."
        )

    def test_populated_db_renders_dataframe(self, db):
        """Populated DB: an st.dataframe renders; the empty-state info
        must NOT appear (branches are mutually exclusive)."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=10)).isoformat(),
        }))
        at = _run_page()
        assert len(at.dataframe) == 1, (
            f"Populated DB: expected exactly one dataframe in the "
            f"Upcoming panel. Got {len(at.dataframe)}."
        )
        assert all(i.value != self.EMPTY_COPY_DEFAULT for i in at.info), (
            f"Populated DB: empty-state info must NOT render. "
            f"Got info bodies: {[i.value for i in at.info]}"
        )

    # ── Group D: display contract ─────────────────────────────────────────

    def test_populated_dataframe_has_six_display_column_headers(self, db):
        """Display-header rename contract: T4-A's lowercase
        (date, days_left, label, kind, status, urgency) become
        Title-Case headers in the rendered dataframe."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=10)).isoformat(),
        }))
        at = _run_page()
        df = at.dataframe[0].value
        assert list(df.columns) == self.DISPLAY_COLUMNS, (
            f"Expected display column headers {self.DISPLAY_COLUMNS!r}, "
            f"got {list(df.columns)!r}"
        )

    def test_status_column_shows_ui_labels_not_raw_sentinels(self, db):
        """DESIGN §8.0: pages NEVER render a raw bracketed status to
        the user. T4-B maps T4-A's raw `status` through STATUS_LABELS
        for the displayed Status column — both an equality check and a
        belt-and-suspenders startswith('[') guard."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=10)).isoformat(),
        }))
        at = _run_page()
        df = at.dataframe[0].value
        statuses = list(df["Status"])
        expected_label = config.STATUS_LABELS[config.STATUS_SAVED]
        assert all(s == expected_label for s in statuses), (
            f"Status column must contain UI-mapped labels (e.g. "
            f"{expected_label!r}), never raw bracketed sentinels. "
            f"Got: {statuses}"
        )
        for s in statuses:
            assert not (isinstance(s, str) and s.startswith("[")), (
                f"Raw bracketed sentinel leaked into Status: {s!r}"
            )

    def test_date_column_carries_date_objects(self, db):
        """T4-A's date-object contract must survive the column rename.
        DateColumn formatting is applied client-side; the underlying
        column dtype + cell types are what tests can see."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=5)).isoformat(),
        }))
        at = _run_page()
        df = at.dataframe[0].value
        cells = list(df["Date"])
        assert all(isinstance(c, date) for c in cells), (
            f"Every Date cell must be a datetime.date. Got types: "
            f"{[type(c).__name__ for c in cells]}"
        )

    def test_date_column_uses_moment_format_string(self, db):
        """DateColumn `format=` is applied client-side; AppTest cannot
        see the rendered string. Pin the moment.js format string at the
        source level — same precedent as st.switch_page targets in T1-E."""
        import pathlib
        src = pathlib.Path("app.py").read_text(encoding="utf-8")
        assert self.DATE_COLUMN_FORMAT_SOURCE in src, (
            f"app.py must call {self.DATE_COLUMN_FORMAT_SOURCE!r} for "
            f"the Date column so the dashboard renders dates as 'Apr 24'."
        )

    def test_kind_column_for_deadline_renders_friendly_string(self, db):
        """T4-A returns 'Deadline for application' for deadline rows;
        T4-B passes it through unchanged — the Kind cell reads as
        natural language for the user."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=10)).isoformat(),
        }))
        at = _run_page()
        kinds = list(at.dataframe[0].value["Kind"])
        assert "Deadline for application" in kinds, (
            f"Deadline row Kind must read 'Deadline for application'. "
            f"Got Kind cells: {kinds}"
        )

    def test_kind_column_for_interview_includes_sequence_number(self, db):
        """Interview rows use the sequence-aware 'Interview N' phrasing.
        Position with no deadline + one interview at +5d → exactly one
        'Interview 1' row."""
        pos_id = database.add_position(make_position({
            "position_name": "P-int",
            "deadline_date": None,
        }))
        database.add_interview(pos_id, {
            "scheduled_date": (date.today() + timedelta(days=5)).isoformat(),
        })
        at = _run_page()
        kinds = list(at.dataframe[0].value["Kind"])
        assert kinds == ["Interview 1"], (
            f"Single-interview row Kind must read ['Interview 1']. "
            f"Got: {kinds}"
        )

    def test_label_column_includes_institute(self, db):
        """Label format '{institute}: {position_name}' makes it through
        T4-A's projection and T4-B's column rename without
        modification."""
        database.add_position(make_position({
            "position_name": "Postdoc-X",
            "institute":     "Stanford",
            "deadline_date": (date.today() + timedelta(days=10)).isoformat(),
        }))
        at = _run_page()
        labels = list(at.dataframe[0].value["Label"])
        assert "Stanford: Postdoc-X" in labels, (
            f"Expected 'Stanford: Postdoc-X' label. Got: {labels}"
        )

    def test_urgency_column_passes_through_emoji_glyphs(self, db):
        """T4-A returns '🔴' for in-7d rows; T4-B's column rename does
        not strip the glyph."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=2)).isoformat(),
        }))
        at = _run_page()
        urgencies = list(at.dataframe[0].value["Urgency"])
        assert "🔴" in urgencies, (
            f"In-2d row should show '🔴' in Urgency. Got: {urgencies}"
        )

    def test_days_left_column_passes_through_phrasing(self, db):
        """T4-A's days_left phrasing ('in N days') makes it into the
        rendered Days left column unchanged."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=5)).isoformat(),
        }))
        at = _run_page()
        days_left = list(at.dataframe[0].value["Days left"])
        assert "in 5 days" in days_left, (
            f"Expected 'in 5 days' in Days left column. Got: {days_left}"
        )

    # ── Group E: selectbox interaction ────────────────────────────────────

    def test_changing_window_updates_subheader(self, db):
        """Selecting a wider window updates the dynamic subheader text.
        Pins that the subheader is f-string-driven, not hardcoded."""
        at = _run_page()
        at.selectbox(key=self.WINDOW_KEY).set_value(60).run()
        expected_60 = "Upcoming (next 60 days)"
        assert any(s.value == expected_60 for s in at.subheader), (
            f"After selecting 60, expected subheader {expected_60!r}. "
            f"Got: {[s.value for s in at.subheader]}"
        )

    def test_changing_window_updates_empty_copy(self, db):
        """The empty-state copy interpolates the selected window — when
        the user widens to 60 days, the empty info reflects that."""
        at = _run_page()
        at.selectbox(key=self.WINDOW_KEY).set_value(60).run()
        expected_60 = "No deadlines or interviews in the next 60 days."
        assert any(i.value == expected_60 for i in at.info), (
            f"After selecting 60 on empty DB, expected info "
            f"{expected_60!r}. Got info bodies: "
            f"{[i.value for i in at.info]}"
        )

    def test_changing_window_widens_data_fetch(self, db):
        """A position at +50d sits OUTSIDE the default 30-day window
        (empty state). After widening to 60-day, the row appears in
        the dataframe — proves the selectbox value drives
        get_upcoming(days=...)."""
        database.add_position(make_position({
            "position_name": "Far",
            "deadline_date": (date.today() + timedelta(days=50)).isoformat(),
        }))
        at = _run_page()
        assert len(at.dataframe) == 0, (
            "Default 30-day window must NOT surface the +50d position "
            "(it's outside the window)."
        )
        at.selectbox(key=self.WINDOW_KEY).set_value(60).run()
        assert len(at.dataframe) == 1, (
            f"After widening to 60-day window, expected one dataframe. "
            f"Got {len(at.dataframe)}."
        )
        labels = list(at.dataframe[0].value["Label"])
        assert any("Far" in label for label in labels), (
            f"After widening, expected the +50d 'Far' position in the "
            f"Label column. Got: {labels}"
        )


# ── T5: Recommender Alerts panel ──────────────────────────────────────────────

class TestT5RecommenderAlerts:
    """T5-A: Recommender Alerts panel rendering on the dashboard.

    DESIGN §8.1 (Recommender Alerts row): a single full-width section
    BELOW the Upcoming row. Driven by `database.get_pending_recommenders()`
    (default `RECOMMENDER_ALERT_DAYS`) and grouped by `recommender_name`
    so each person appears in exactly one bordered card carrying every
    letter they still owe.

    Locked panel contract:
      - Subheader 'Recommender Alerts' renders in BOTH empty and
        populated branches for page-height stability (T2 / T3 / T4
        precedent).
      - Empty branch: `st.info(EMPTY_COPY)` verbatim, no markdown cards.
      - Populated branch: one `st.container(border=True)` per distinct
        `recommender_name`. Each card renders as a single
        `st.markdown(...)` block whose body starts with `**⚠ {Name}**`
        and lists each owed position on its own bullet line:
        `- {institute}: {position_name} (asked {N}d ago, due {Mon D})`.
        Bare `position_name` when institute is missing; `due —` when
        deadline_date is NULL.
      - The Compose-reminder-email button + LLM-prompts expander
        (DESIGN §8.4 D-C) belong on the Recommenders PAGE (Phase 5 T6),
        NOT on the dashboard. T5 only renders the alert cards.

    AppTest access patterns (verified against Streamlit 1.56):
      - `at.markdown[i].value` returns the raw markdown source string
        passed to `st.markdown(...)` — multi-line content with `\\n`
        between header and bullet lines comes back as one element.
      - `st.container(border=True)` is a CSS-styled wrapper; AppTest
        does not surface a distinct element for it, so the bordered
        contract is pinned via a source-level grep (T1-E
        `test_cta_targets_opportunities_page` precedent).
    """

    SUBHEADER = "Recommender Alerts"
    # Phase 7 CL4 Fix 4: pin against config.EMPTY_PENDING_RECOMMENDER_FOLLOWUPS
    # by name so a future wording edit in config.py flows through here
    # automatically — no test churn on copy updates.
    EMPTY_COPY = config.EMPTY_PENDING_RECOMMENDER_FOLLOWUPS
    BORDER_SOURCE = "st.container(border=True)"
    WARN_GLYPH = "⚠"

    @staticmethod
    def _has_subheader(at: AppTest, value: str) -> bool:
        return any(s.value == value for s in at.subheader)

    @classmethod
    def _alert_markdowns(cls, at: AppTest) -> list[str]:
        """Markdown bodies that look like a Recommender-Alerts card.

        Identified by the warn-glyph header — keeps the helper robust
        against any future `st.markdown` calls landing elsewhere on the
        page (e.g., Phase 7 polish)."""
        return [m.value for m in at.markdown if cls.WARN_GLYPH in m.value]

    @staticmethod
    def _seed_pending(
        days_ago: int = 14,
        position_name: str = "BioStats Postdoc",
        institute: str = "Stanford",
        recommender_name: str = "Dr. Smith",
        deadline_offset: int | None = 10,
    ) -> int:
        """Seed one pending recommender (asked >= RECOMMENDER_ALERT_DAYS
        ago, no submitted_date yet) and return the recommender row id."""
        pos_id = database.add_position(make_position({
            "position_name": position_name,
            "institute":     institute,
            "deadline_date": (
                (date.today() + timedelta(days=deadline_offset)).isoformat()
                if deadline_offset is not None
                else None
            ),
        }))
        return database.add_recommender(pos_id, {
            "recommender_name": recommender_name,
            "asked_date": (date.today() - timedelta(days=days_ago)).isoformat(),
        })

    # ── Group A: subheader stability + layout ─────────────────────────────

    def test_subheader_renders_on_empty_db(self, db):
        """Page-height stability: the subheader renders even when the
        pending list is empty, so the layout above doesn't shift when
        the first owed letter lands."""
        at = _run_page()
        assert self._has_subheader(at, self.SUBHEADER), (
            f"Empty DB: expected top-level {self.SUBHEADER!r} subheader. "
            f"Got: {[s.value for s in at.subheader]}"
        )

    def test_subheader_renders_on_populated_db(self, db):
        """Same page-height-stability invariant on the populated path."""
        self._seed_pending()
        at = _run_page()
        assert self._has_subheader(at, self.SUBHEADER), (
            f"Populated DB: expected top-level {self.SUBHEADER!r} "
            f"subheader. Got: {[s.value for s in at.subheader]}"
        )

    def test_panel_uses_bordered_container_per_card(self, db):
        """Each card wraps in `st.container(border=True)`. AppTest does
        not surface bordered-container styling, so the contract is
        pinned at the source level — same precedent as
        TestT1EEmptyDbHero.test_cta_targets_opportunities_page for
        st.switch_page and TestT4UpcomingTimeline for the DateColumn
        format string.

        Why `>= 2`: the empty-DB hero (T1-E) already calls
        `st.container(border=True)` once. A single occurrence would
        therefore pass vacuously without any T5 implementation. We
        require AT LEAST TWO so the red→green transition actually
        gates on the T5 panel adding its own bordered-container call.
        """
        import pathlib
        src = pathlib.Path("app.py").read_text(encoding="utf-8")
        count = src.count(self.BORDER_SOURCE)
        assert count >= 2, (
            f"app.py must call {self.BORDER_SOURCE!r} at least twice "
            f"(once for the empty-DB hero, once for the Recommender-"
            f"Alerts cards loop). Got {count} occurrence(s)."
        )

    # ── Group B: empty / populated branches ───────────────────────────────

    def test_empty_db_renders_info_with_locked_copy(self, db):
        """Empty DB: exactly one st.info matching EMPTY_COPY verbatim,
        and no Recommender-Alerts markdown cards."""
        at = _run_page()
        matching = [i for i in at.info if i.value == self.EMPTY_COPY]
        assert len(matching) == 1, (
            f"Empty DB: expected exactly one st.info with copy "
            f"{self.EMPTY_COPY!r}. Got info bodies: "
            f"{[i.value for i in at.info]}"
        )
        assert self._alert_markdowns(at) == [], (
            f"Empty DB: no alert cards should render. Got bodies: "
            f"{self._alert_markdowns(at)}"
        )

    def test_unsubmitted_but_recent_ask_does_not_fire(self, db):
        """Boundary check: a recommender asked TODAY (well inside
        RECOMMENDER_ALERT_DAYS) is NOT yet pending. Pins that the
        panel inherits the days-cutoff filter from
        `get_pending_recommenders()` rather than firing on every
        unsubmitted letter."""
        self._seed_pending(days_ago=0)
        at = _run_page()
        matching = [i for i in at.info if i.value == self.EMPTY_COPY]
        assert len(matching) == 1, (
            f"Asked-today: expected the empty-state info to still fire "
            f"(0d < RECOMMENDER_ALERT_DAYS={config.RECOMMENDER_ALERT_DAYS}). "
            f"Got info bodies: {[i.value for i in at.info]}"
        )
        assert self._alert_markdowns(at) == [], (
            f"Asked-today recommender should NOT produce a card. "
            f"Got: {self._alert_markdowns(at)}"
        )

    def test_asked_at_alert_boundary_fires(self, db):
        """Boundary inclusivity: a recommender asked exactly
        `RECOMMENDER_ALERT_DAYS` ago (the SQL cutoff `<=` is
        inclusive) IS pending and produces a card. Pairs with
        `test_unsubmitted_but_recent_ask_does_not_fire` to pin both
        sides of the alert-days boundary; mirrors the two-sided
        boundary coverage T4 lands in `TestGetUpcoming`
        (`test_urgency_red_within_urgent_threshold`,
        `test_urgency_yellow_between_urgent_and_alert`).

        A future tightening of the SQL filter to `<` would silently
        drop the at-the-boundary case — this test is the explicit
        pin against that drift."""
        self._seed_pending(days_ago=config.RECOMMENDER_ALERT_DAYS)
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert len(bodies) >= 1, (
            f"At-the-boundary recommender (asked exactly "
            f"{config.RECOMMENDER_ALERT_DAYS}d ago) should produce a "
            f"card; SQL cutoff is `asked_date <= today - "
            f"{config.RECOMMENDER_ALERT_DAYS}d`. Got bodies: {bodies}"
        )
        assert all(i.value != self.EMPTY_COPY for i in at.info), (
            f"At-the-boundary populated DB: empty-state info must NOT "
            f"render. Got info bodies: {[i.value for i in at.info]}"
        )

    def test_populated_db_suppresses_empty_info(self, db):
        """Populated DB: at least one alert card renders, and the
        empty-state info must NOT appear (branches mutually exclusive)."""
        self._seed_pending()
        at = _run_page()
        assert len(self._alert_markdowns(at)) >= 1, (
            f"Populated DB: expected at least one alert card. "
            f"Got bodies: {self._alert_markdowns(at)}"
        )
        assert all(i.value != self.EMPTY_COPY for i in at.info), (
            f"Populated DB: empty-state info must NOT render. "
            f"Got info bodies: {[i.value for i in at.info]}"
        )

    # ── Group C: card content contract ────────────────────────────────────

    def test_card_header_uses_warn_glyph_and_bold_name(self, db):
        """`**⚠ {Name}**` header — bold so it stands apart from the
        bullets visually, with the warn-glyph as the at-a-glance
        signal that the card is an alert."""
        self._seed_pending(recommender_name="Dr. Smith")
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert any("**⚠ Dr. Smith**" in body for body in bodies), (
            f"Expected '**⚠ Dr. Smith**' header in some card body. "
            f"Got: {bodies}"
        )

    def test_card_bullet_includes_institute_and_position_name(self, db):
        """Bullet uses the T4 Label precedent
        '{institute}: {position_name}' so the user sees which posting
        the letter is for, not just the job title."""
        self._seed_pending(
            position_name="BioStats Postdoc",
            institute="Stanford",
        )
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert any("Stanford: BioStats Postdoc" in body for body in bodies), (
            f"Expected 'Stanford: BioStats Postdoc' (T4 Label precedent) "
            f"in some card body. Got: {bodies}"
        )

    def test_card_bullet_falls_back_to_position_name_when_institute_missing(self, db):
        """T4 Label precedent: bare `position_name` when institute is
        empty / missing — same fallback as the Upcoming panel."""
        self._seed_pending(position_name="LonePost", institute="")
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert any(
            "LonePost" in body and "Stanford:" not in body
            for body in bodies
        ), (
            f"Expected bare 'LonePost' (no institute prefix) when "
            f"institute is empty. Got: {bodies}"
        )

    def test_card_bullet_includes_asked_days_phrasing(self, db):
        """`asked Nd ago` phrasing per TASKS.md (supersedes the older
        wireframe '14 days ago')."""
        self._seed_pending(days_ago=14)
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert any("asked 14d ago" in body for body in bodies), (
            f"Expected 'asked 14d ago' in some card body. Got: {bodies}"
        )

    def test_card_bullet_includes_due_date_in_short_format(self, db):
        """Due-date renders in Mon-D form (T4 DateColumn precedent —
        no year, since the panel surfaces near-future deadlines)."""
        target_date = date.today() + timedelta(days=10)
        self._seed_pending(deadline_offset=10)
        at = _run_page()
        bodies = self._alert_markdowns(at)
        expected = f"due {target_date.strftime('%b')} {target_date.day}"
        assert any(expected in body for body in bodies), (
            f"Expected {expected!r} in some card body. Got: {bodies}"
        )

    def test_card_bullet_uses_em_dash_for_null_deadline(self, db):
        """Em-dash glyph for missing deadline mirrors
        NEXT_INTERVIEW_EMPTY in app.py (locked decision U3)."""
        self._seed_pending(deadline_offset=None)
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert any("due —" in body for body in bodies), (
            f"Expected 'due —' (em dash) for null deadline. Got: {bodies}"
        )

    # ── Group D: grouping by recommender_name ─────────────────────────────

    def test_two_letters_for_one_recommender_render_one_card(self, db):
        """Two pending letters owed by Dr. Smith → exactly ONE card
        with TWO bullet lines. Pins the group-by-recommender_name
        contract — the user sees one row per person, not per letter."""
        # Two distinct positions, same recommender.
        pos1 = database.add_position(make_position({
            "position_name": "Pos-A",
            "institute":     "Stanford",
            "deadline_date": (date.today() + timedelta(days=10)).isoformat(),
        }))
        pos2 = database.add_position(make_position({
            "position_name": "Pos-B",
            "institute":     "MIT",
            "deadline_date": (date.today() + timedelta(days=20)).isoformat(),
        }))
        asked_iso = (date.today() - timedelta(days=14)).isoformat()
        database.add_recommender(pos1, {
            "recommender_name": "Dr. Smith",
            "asked_date": asked_iso,
        })
        database.add_recommender(pos2, {
            "recommender_name": "Dr. Smith",
            "asked_date": asked_iso,
        })

        at = _run_page()
        bodies = self._alert_markdowns(at)
        smith_cards = [b for b in bodies if "**⚠ Dr. Smith**" in b]
        assert len(smith_cards) == 1, (
            f"Two pending letters for Dr. Smith should produce ONE "
            f"card (grouped by recommender_name). Got {len(smith_cards)} "
            f"Smith card(s): {smith_cards}"
        )
        body = smith_cards[0]
        assert "Stanford: Pos-A" in body and "MIT: Pos-B" in body, (
            f"Single Smith card should list BOTH positions as bullets. "
            f"Got body: {body!r}"
        )

    def test_two_recommenders_render_two_cards(self, db):
        """Two distinct recommender names → two separate cards."""
        pos1 = database.add_position(make_position({
            "position_name": "Pos-A",
            "institute":     "Stanford",
        }))
        pos2 = database.add_position(make_position({
            "position_name": "Pos-B",
            "institute":     "MIT",
        }))
        asked_iso = (date.today() - timedelta(days=14)).isoformat()
        database.add_recommender(pos1, {
            "recommender_name": "Dr. Smith",
            "asked_date": asked_iso,
        })
        database.add_recommender(pos2, {
            "recommender_name": "Dr. Jones",
            "asked_date": asked_iso,
        })

        at = _run_page()
        bodies = self._alert_markdowns(at)
        smith_cards = [b for b in bodies if "**⚠ Dr. Smith**" in b]
        jones_cards = [b for b in bodies if "**⚠ Dr. Jones**" in b]
        assert len(smith_cards) == 1, (
            f"Expected exactly one Dr. Smith card. Got {len(smith_cards)}: "
            f"{smith_cards}"
        )
        assert len(jones_cards) == 1, (
            f"Expected exactly one Dr. Jones card. Got {len(jones_cards)}: "
            f"{jones_cards}"
        )

    def test_submitted_letters_do_not_appear(self, db):
        """A recommender whose `submitted_date` is set must NOT appear
        in the alerts panel — the SQL filter `submitted_date IS NULL`
        is doing the work, but pin it from the page side too."""
        pos_id = database.add_position(make_position({
            "position_name": "Done-Letter-Pos",
        }))
        rec_id = database.add_recommender(pos_id, {
            "recommender_name": "Dr. Done",
            "asked_date": (date.today() - timedelta(days=14)).isoformat(),
        })
        database.update_recommender(rec_id, {
            "submitted_date": date.today().isoformat(),
        })
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert all("Dr. Done" not in body for body in bodies), (
            f"Submitted-letter recommender 'Dr. Done' must NOT appear. "
            f"Got bodies: {bodies}"
        )
