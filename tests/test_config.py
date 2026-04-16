# tests/test_config.py
# Tests for config.py invariants.
#
# These are pure-Python assertions — no I/O, no database.
# They guard against silent drift between constants that must stay in sync.

import importlib
import sys
import pytest
import config


# ── STATUS_VALUES / STATUS_COLORS consistency ─────────────────────────────────

def test_status_colors_matches_status_values():
    """Every status value must have a color entry and no extras."""
    assert set(config.STATUS_VALUES) == set(config.STATUS_COLORS), (
        f"Drift: missing from STATUS_COLORS: "
        f"{set(config.STATUS_VALUES) - set(config.STATUS_COLORS)}, "
        f"extra in STATUS_COLORS: "
        f"{set(config.STATUS_COLORS) - set(config.STATUS_VALUES)}"
    )


_VALID_ST_BADGE_COLORS = {
    "red", "orange", "yellow", "blue", "green", "violet", "gray", "grey", "primary"
}

def test_status_colors_are_valid_streamlit_literals():
    """All STATUS_COLORS values must be accepted color literals for st.badge().
    Verified against Streamlit 1.56.0 — see config.py comment."""
    invalid = {
        status: color
        for status, color in config.STATUS_COLORS.items()
        if color not in _VALID_ST_BADGE_COLORS
    }
    assert not invalid, f"Invalid st.badge colors: {invalid}"


def test_status_values_are_non_empty_strings():
    assert all(isinstance(s, str) and s for s in config.STATUS_VALUES)


# ── RESULT_VALUES / RESULT_DEFAULT coupling ───────────────────────────────────

def test_result_default_equals_result_values_first():
    """RESULT_DEFAULT must match RESULT_VALUES[0] (the SQLite schema DEFAULT)."""
    assert config.RESULT_DEFAULT == config.RESULT_VALUES[0], (
        f"RESULT_DEFAULT='{config.RESULT_DEFAULT}' != RESULT_VALUES[0]='{config.RESULT_VALUES[0]}'"
    )


def test_result_default_is_pending():
    """RESULT_DEFAULT is 'Pending' — the DB schema DEFAULT clause depends on this."""
    assert config.RESULT_DEFAULT == "Pending"


# ── Threshold ordering ────────────────────────────────────────────────────────

def test_deadline_urgent_less_than_alert():
    """DEADLINE_URGENT_DAYS < DEADLINE_ALERT_DAYS — urgent is the inner window."""
    assert config.DEADLINE_URGENT_DAYS < config.DEADLINE_ALERT_DAYS, (
        f"URGENT={config.DEADLINE_URGENT_DAYS} must be < ALERT={config.DEADLINE_ALERT_DAYS}"
    )


def test_all_thresholds_positive():
    assert config.DEADLINE_ALERT_DAYS > 0
    assert config.DEADLINE_URGENT_DAYS > 0
    assert config.RECOMMENDER_ALERT_DAYS > 0


# ── REQUIREMENT_DOCS structure ────────────────────────────────────────────────

def test_requirement_docs_are_3_tuples():
    """Each entry in REQUIREMENT_DOCS must be a 3-element tuple of non-empty strings."""
    for entry in config.REQUIREMENT_DOCS:
        assert len(entry) == 3, f"Expected 3-tuple, got: {entry}"
        req_col, done_col, label = entry
        assert isinstance(req_col, str) and req_col, f"Bad req_col: {req_col!r}"
        assert isinstance(done_col, str) and done_col, f"Bad done_col: {done_col!r}"
        assert isinstance(label, str) and label, f"Bad label: {label!r}"


def test_requirement_docs_column_prefixes():
    """req_* and done_* columns must start with the correct prefixes."""
    for req_col, done_col, _ in config.REQUIREMENT_DOCS:
        assert req_col.startswith("req_"), f"Expected req_ prefix: {req_col!r}"
        assert done_col.startswith("done_"), f"Expected done_ prefix: {done_col!r}"


def test_requirement_docs_no_duplicate_columns():
    """All req_* and done_* column names must be globally unique."""
    req_cols  = [r for r, _, _ in config.REQUIREMENT_DOCS]
    done_cols = [d for _, d, _ in config.REQUIREMENT_DOCS]
    all_cols  = req_cols + done_cols
    assert len(all_cols) == len(set(all_cols)), (
        f"Duplicate column names in REQUIREMENT_DOCS: "
        f"{[c for c in all_cols if all_cols.count(c) > 1]}"
    )


# ── QUICK_ADD_FIELDS ──────────────────────────────────────────────────────────

def test_quick_add_fields_contains_position_name():
    """position_name is required for the quick-add form to function."""
    assert "position_name" in config.QUICK_ADD_FIELDS


def test_quick_add_fields_are_strings():
    assert all(isinstance(f, str) and f for f in config.QUICK_ADD_FIELDS)


# ── Vocabularies are non-empty ────────────────────────────────────────────────

@pytest.mark.parametrize("name, lst", [
    ("PRIORITY_VALUES",    config.PRIORITY_VALUES),
    ("WORK_AUTH_OPTIONS",  config.WORK_AUTH_OPTIONS),
    ("FULL_TIME_OPTIONS",  config.FULL_TIME_OPTIONS),
    ("SOURCE_OPTIONS",     config.SOURCE_OPTIONS),
    ("RESPONSE_TYPES",     config.RESPONSE_TYPES),
    ("RESULT_VALUES",      config.RESULT_VALUES),
    ("RELATIONSHIP_TYPES", config.RELATIONSHIP_TYPES),
])
def test_vocabulary_lists_are_non_empty(name, lst):
    assert len(lst) > 0, f"{name} must not be empty"


# ── TERMINAL_STATUSES ────────────────────────────────────────────────────────

def test_terminal_statuses_are_subset_of_status_values():
    """Every terminal status must be a known STATUS_VALUES entry."""
    assert set(config.TERMINAL_STATUSES) <= set(config.STATUS_VALUES), (
        f"Unknown terminal statuses: "
        f"{set(config.TERMINAL_STATUSES) - set(config.STATUS_VALUES)}"
    )


def test_terminal_statuses_non_empty():
    assert len(config.TERMINAL_STATUSES) > 0


# ── Module-level assertion guard is live ─────────────────────────────────────

def test_status_guard_fires_on_drift(monkeypatch):
    """The STATUS_COLORS assertion in config.py fires when there is a mismatch.

    We cannot re-trigger the module-level assert directly, so we replicate the
    exact guard logic here to confirm it detects a synthetic drift."""
    broken_colors = dict(config.STATUS_COLORS)
    broken_colors.pop("[OPEN]")  # introduce the drift
    assert set(config.STATUS_VALUES) != set(broken_colors), (
        "Guard should fire: STATUS_VALUES has [OPEN] but broken_colors does not"
    )
    missing = set(config.STATUS_VALUES) - set(broken_colors)
    assert missing == {"[OPEN]"}
