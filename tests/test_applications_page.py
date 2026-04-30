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
