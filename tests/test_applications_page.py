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


def _run_page() -> AppTest:
    """Return a freshly-run AppTest for the Applications page."""
    at = AppTest.from_file(PAGE, default_timeout=10)
    at.run()
    return at


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
