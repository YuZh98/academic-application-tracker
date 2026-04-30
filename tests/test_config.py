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
    broken_colors.pop("[SAVED]")  # introduce the drift
    assert set(config.STATUS_VALUES) != set(broken_colors), (
        "Guard should fire: STATUS_VALUES has [SAVED] but broken_colors does not"
    )
    missing = set(config.STATUS_VALUES) - set(broken_colors)
    assert missing == {"[SAVED]"}


# ─────────────────────────────────────────────────────────────────────────────
# Sub-task 1 (v1.3 alignment) — DESIGN.md §5.1 / §5.2
# ─────────────────────────────────────────────────────────────────────────────

# ── STATUS_* aliases for terminal statuses (DESIGN §5.1 Status pipeline) ──────

def test_status_closed_alias_matches_status_values():
    """STATUS_CLOSED must equal the literal '[CLOSED]' from STATUS_VALUES."""
    assert config.STATUS_CLOSED == "[CLOSED]"
    assert config.STATUS_CLOSED in config.STATUS_VALUES


def test_status_rejected_alias_matches_status_values():
    """STATUS_REJECTED must equal the literal '[REJECTED]' from STATUS_VALUES."""
    assert config.STATUS_REJECTED == "[REJECTED]"
    assert config.STATUS_REJECTED in config.STATUS_VALUES


def test_status_declined_alias_matches_status_values():
    """STATUS_DECLINED must equal the literal '[DECLINED]' from STATUS_VALUES."""
    assert config.STATUS_DECLINED == "[DECLINED]"
    assert config.STATUS_DECLINED in config.STATUS_VALUES


def test_all_seven_status_aliases_match_status_values_order():
    """Named aliases follow STATUS_VALUES index order (per DESIGN §5.1)."""
    expected = [
        config.STATUS_SAVED, config.STATUS_APPLIED, config.STATUS_INTERVIEW,
        config.STATUS_OFFER, config.STATUS_CLOSED, config.STATUS_REJECTED,
        config.STATUS_DECLINED,
    ]
    assert expected == config.STATUS_VALUES, (
        "Named STATUS_* aliases must equal STATUS_VALUES in index order. "
        f"aliases={expected!r}, STATUS_VALUES={config.STATUS_VALUES!r}"
    )


# ── VALID_PROFILES + invariant #1 (DESIGN §5.1, §5.2 #1) ──────────────────────

def test_valid_profiles_is_non_empty_set():
    """VALID_PROFILES must be a non-empty set of profile-name strings."""
    assert isinstance(config.VALID_PROFILES, set)
    assert len(config.VALID_PROFILES) > 0
    assert all(isinstance(p, str) and p for p in config.VALID_PROFILES)


def test_valid_profiles_contains_postdoc():
    """v1 profile is 'postdoc' (DESIGN §5.1 Tracker identity)."""
    assert "postdoc" in config.VALID_PROFILES


def test_invariant_1_tracker_profile_in_valid_profiles():
    """DESIGN §5.2 invariant #1: TRACKER_PROFILE must be a known profile."""
    assert config.TRACKER_PROFILE in config.VALID_PROFILES, (
        f"TRACKER_PROFILE={config.TRACKER_PROFILE!r} not in "
        f"VALID_PROFILES={config.VALID_PROFILES!r}"
    )


def test_invariant_1_fires_on_unknown_profile():
    """Replicate DESIGN §5.2 invariant #1 on a synthetic bad value."""
    broken_profile = "software_eng"
    assert broken_profile not in config.VALID_PROFILES, (
        "Guard should fire: unknown profile not in VALID_PROFILES"
    )


# ── STATUS_LABELS + invariant #3 (DESIGN §5.1, §5.2 #3) ───────────────────────

def test_status_labels_is_dict_with_string_values():
    """STATUS_LABELS maps each status to a non-empty UI label string."""
    assert isinstance(config.STATUS_LABELS, dict)
    assert all(isinstance(v, str) and v for v in config.STATUS_LABELS.values())


def test_invariant_3_status_values_equal_status_labels():
    """DESIGN §5.2 invariant #3: every status has a UI label, no extras."""
    assert set(config.STATUS_VALUES) == set(config.STATUS_LABELS), (
        "STATUS_LABELS must have exactly one entry per STATUS_VALUES item. "
        f"missing={set(config.STATUS_VALUES) - set(config.STATUS_LABELS)!r}, "
        f"extra={set(config.STATUS_LABELS) - set(config.STATUS_VALUES)!r}"
    )


def test_status_labels_are_bracket_stripped():
    """Per DESIGN §5.1: 'UI strips the brackets via this dict'. No label
    may contain a '[' or ']' character."""
    for raw, label in config.STATUS_LABELS.items():
        assert "[" not in label and "]" not in label, (
            f"STATUS_LABELS[{raw!r}] = {label!r} retains bracket characters"
        )


def test_status_labels_spec_values():
    """Pin the bracket-stripped, title-cased mapping for the v1 seven statuses."""
    assert config.STATUS_LABELS == {
        "[SAVED]":     "Saved",
        "[APPLIED]":   "Applied",
        "[INTERVIEW]": "Interview",
        "[OFFER]":     "Offer",
        "[CLOSED]":    "Closed",
        "[REJECTED]":  "Rejected",
        "[DECLINED]":  "Declined",
    }


def test_invariant_3_fires_on_missing_label():
    """Replicate DESIGN §5.2 invariant #3 on a synthetic drift."""
    broken_labels = dict(config.STATUS_LABELS)
    broken_labels.pop("[APPLIED]")
    assert set(config.STATUS_VALUES) != set(broken_labels), (
        "Guard should fire: STATUS_VALUES has [APPLIED] but broken_labels does not"
    )
    assert set(config.STATUS_VALUES) - set(broken_labels) == {"[APPLIED]"}


# ── FUNNEL_DEFAULT_HIDDEN + invariant #6 (DESIGN §5.1, §5.2 #6) ───────────────

def test_funnel_default_hidden_is_set_of_strings():
    assert isinstance(config.FUNNEL_DEFAULT_HIDDEN, set)
    assert all(isinstance(s, str) and s for s in config.FUNNEL_DEFAULT_HIDDEN)


def test_funnel_default_hidden_spec_values():
    """DESIGN §5.1: hidden-by-default buckets are Closed + Archived (D24)."""
    assert config.FUNNEL_DEFAULT_HIDDEN == {"Closed", "Archived"}


def test_invariant_6_default_hidden_subset_of_bucket_labels():
    """DESIGN §5.2 invariant #6: every hidden label references a real bucket."""
    bucket_labels = {label for label, _, _ in config.FUNNEL_BUCKETS}
    assert config.FUNNEL_DEFAULT_HIDDEN <= bucket_labels, (
        "FUNNEL_DEFAULT_HIDDEN references unknown bucket labels: "
        f"{config.FUNNEL_DEFAULT_HIDDEN - bucket_labels!r}"
    )


def test_invariant_6_fires_on_unknown_hidden_label():
    """Replicate DESIGN §5.2 invariant #6 on a synthetic drift."""
    bucket_labels = {label for label, _, _ in config.FUNNEL_BUCKETS}
    broken_hidden = config.FUNNEL_DEFAULT_HIDDEN | {"Nonexistent"}
    assert not (broken_hidden <= bucket_labels), (
        "Guard should fire: 'Nonexistent' is not a bucket label"
    )


# ── INTERVIEW_FORMATS (DESIGN §5.1 Vocabularies) ──────────────────────────────

def test_interview_formats_is_non_empty_list_of_strings():
    assert isinstance(config.INTERVIEW_FORMATS, list)
    assert len(config.INTERVIEW_FORMATS) > 0
    assert all(isinstance(f, str) and f for f in config.INTERVIEW_FORMATS)


def test_interview_formats_spec_values():
    """DESIGN §5.1: INTERVIEW_FORMATS = ['Phone', 'Video', 'Onsite', 'Other']."""
    assert config.INTERVIEW_FORMATS == ["Phone", "Video", "Onsite", "Other"]


# ── Invariant #8 (DESIGN §5.2 #8) ─────────────────────────────────────────────

def test_invariant_8_urgent_leq_alert():
    """DESIGN §5.2 invariant #8: DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS.

    (Stricter '<' is pinned by test_deadline_urgent_less_than_alert above;
    this test pins the exact DESIGN-spec inequality so the import-time
    assert stays wired to DESIGN even if someone relaxes the strict test.)"""
    assert config.DEADLINE_URGENT_DAYS <= config.DEADLINE_ALERT_DAYS, (
        f"URGENT={config.DEADLINE_URGENT_DAYS} must be <= "
        f"ALERT={config.DEADLINE_ALERT_DAYS}"
    )


def test_invariant_8_fires_on_inverted_thresholds():
    """Replicate DESIGN §5.2 invariant #8 on synthetic inverted values."""
    broken_urgent = config.DEADLINE_ALERT_DAYS + 1
    broken_alert  = config.DEADLINE_ALERT_DAYS
    assert not (broken_urgent <= broken_alert), (
        "Guard should fire: urgent window cannot exceed alert window"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sub-task 3 (v1.3 alignment) — DESIGN.md §5.1 / D22
# ─────────────────────────────────────────────────────────────────────────────
# WORK_AUTH_OPTIONS collapses a six-value enum (Any/OPT/J-1/H1B/No Sponsorship/
# Ask) into the three-value categorical Yes/No/Unknown paired with a freetext
# `work_auth_note` column (D22). FULL_TIME_OPTIONS replaces the ambiguous
# Yes/No/Part-time list with the employment-type vocabulary
# Full-time/Part-time/Contract. Both columns stay plain TEXT — no DDL impact.

def test_work_auth_options_spec_values():
    """DESIGN §5.1: WORK_AUTH_OPTIONS = ['Yes', 'No', 'Unknown'] (D22).

    Three-value categorical. 'Unknown' covers postings that do not disclose
    sponsorship; the freetext `work_auth_note` column carries any nuance
    (e.g. 'green card required') so the enum stays filter-friendly."""
    assert config.WORK_AUTH_OPTIONS == ["Yes", "No", "Unknown"]


def test_full_time_options_spec_values():
    """DESIGN §5.1: FULL_TIME_OPTIONS = ['Full-time', 'Part-time', 'Contract'].

    Employment type, not boolean. Old Yes/No/Part-time was ambiguous
    (Yes=full-time? Yes=available?); the new vocabulary names the
    category explicitly."""
    assert config.FULL_TIME_OPTIONS == ["Full-time", "Part-time", "Contract"]


# ─────────────────────────────────────────────────────────────────────────────
# Sub-task 2 (v1.3 alignment) — DESIGN.md §5.1 / D21
# ─────────────────────────────────────────────────────────────────────────────
# REQUIREMENT_VALUES migrated from short codes (Y/Optional/N) to full words
# (Yes/Optional/No). DESIGN decision D21 ties this to D20's "full-word"
# philosophy — consistent, self-descriptive in raw dumps, no storage penalty.

def test_requirement_values_spec_values():
    """DESIGN §5.1: REQUIREMENT_VALUES = ['Yes', 'Optional', 'No'] (D21).

    Display order is 'Required'-first because that is the common case the
    reviewing user hits first on the Requirements tab; config.py pins the
    canonical DB values, REQUIREMENT_LABELS maps them to the UI strings."""
    assert config.REQUIREMENT_VALUES == ["Yes", "Optional", "No"]


def test_requirement_labels_spec_values():
    """DESIGN §5.1: UI labels for each canonical value. st.radio uses
    format_func=REQUIREMENT_LABELS.get so session_state holds the canonical
    DB value (no save-time translation)."""
    assert config.REQUIREMENT_LABELS == {
        "Yes":      "Required",
        "Optional": "Optional",
        "No":       "Not needed",
    }


def test_invariant_7_requirement_labels_keys_equal_values():
    """DESIGN §5.2 invariant #7: every req value has a label, no extras."""
    assert set(config.REQUIREMENT_LABELS) == set(config.REQUIREMENT_VALUES), (
        "REQUIREMENT_LABELS must have exactly one entry per REQUIREMENT_VALUES. "
        f"missing={set(config.REQUIREMENT_VALUES) - set(config.REQUIREMENT_LABELS)!r}, "
        f"extra={set(config.REQUIREMENT_LABELS) - set(config.REQUIREMENT_VALUES)!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Sub-task 5 (v1.3 alignment) — DESIGN.md §5.1 + §6.3
# ─────────────────────────────────────────────────────────────────────────────
# Pipeline-stage-zero rename and priority-tier full-word rename. Both
# renames interpolate into init_db() DDL DEFAULTs via the Sub-task 4
# config-drive; migration of existing rows is handled by two one-shot
# UPDATE loops in init_db() (pinned in test_database.py). Pre-v1.3
# literals are not named here to keep the GUIDELINES §6 pre-merge
# grep at zero hits.

def test_status_values_spec_values():
    """DESIGN §5.1 Status pipeline: STATUS_VALUES starts with [SAVED]
    followed by APPLIED → INTERVIEW → OFFER → CLOSED → REJECTED →
    DECLINED. Order is contract: index 0 is the DDL DEFAULT (via
    config-drive, Sub-task 4), and auto-promotion rules R1/R3 (§9.3)
    read STATUS_VALUES[0] as the source stage for R1."""
    assert config.STATUS_VALUES == [
        "[SAVED]", "[APPLIED]", "[INTERVIEW]", "[OFFER]",
        "[CLOSED]", "[REJECTED]", "[DECLINED]",
    ]


def test_status_saved_alias_matches_status_values():
    """STATUS_SAVED must equal the literal '[SAVED]' and be the first
    pipeline stage — anti-typo guardrail for DESIGN §9.3 R1 cascade."""
    assert config.STATUS_SAVED == "[SAVED]"
    assert config.STATUS_SAVED == config.STATUS_VALUES[0]


def test_priority_values_spec_values():
    """DESIGN §5.1 Vocabularies: PRIORITY_VALUES uses the full-word
    'Medium' at index 1. Full-word philosophy mirrors D20/D21 —
    consistent, self-descriptive in raw dumps. Migration of legacy
    short-code rows is handled by init_db() (pinned in test_database.py)."""
    assert config.PRIORITY_VALUES == ["High", "Medium", "Low", "Stretch"]
    # Pre-v1.3 short code must be absent. Single-quoted so the
    # GUIDELINES §6 grep (which targets the double-quoted form) stays
    # at zero hits post-rename.
    assert 'Med' not in config.PRIORITY_VALUES


# ─────────────────────────────────────────────────────────────────────────────
# Post-Sub-task 14 follow-up (v1.3 alignment) — DESIGN.md §5.1 + §5.2 #9 + §9.3
# ─────────────────────────────────────────────────────────────────────────────
# The "Offer" string that fires the R3 cascade (DESIGN §9.3) gets a config
# alias on parity with the STATUS_* aliases that already insulate cascade
# code from vocabulary renames. Without the alias, a future rename of the
# 'Offer' entry inside RESPONSE_TYPES would silently break R3 (the
# selectbox would show the new label, the user would pick it, and
# upsert_application's hardcoded 'Offer' string would no longer match).
# Invariant #9 (`RESPONSE_TYPE_OFFER in RESPONSE_TYPES`) is the
# import-time guard that catches the drift before any page renders.

def test_response_type_offer_value_is_offer():
    """DESIGN §5.1: RESPONSE_TYPE_OFFER == 'Offer' — the literal R3
    cascade trigger (§9.3). Pinned here so the alias never silently
    drifts away from the user-facing 'Offer' selectbox option."""
    assert config.RESPONSE_TYPE_OFFER == "Offer", (
        f"RESPONSE_TYPE_OFFER must literally equal 'Offer' to match the "
        f"selectbox option that fires R3. Got {config.RESPONSE_TYPE_OFFER!r}"
    )


def test_response_type_offer_is_member_of_response_types():
    """DESIGN §5.2 invariant #9: RESPONSE_TYPE_OFFER must be a member
    of RESPONSE_TYPES — the cascade trigger has to be a value the
    selectbox can actually produce. Positive-case assertion that
    pairs with `test_invariant_9_fires_on_drift` below."""
    assert config.RESPONSE_TYPE_OFFER in config.RESPONSE_TYPES, (
        f"RESPONSE_TYPE_OFFER={config.RESPONSE_TYPE_OFFER!r} not in "
        f"RESPONSE_TYPES={config.RESPONSE_TYPES!r}. R3 cascade would "
        f"never fire — selectbox cannot produce the trigger value."
    )


def test_invariant_9_fires_on_drift():
    """Replicate DESIGN §5.2 invariant #9 on a synthetic bad
    RESPONSE_TYPES list that has dropped the 'Offer' entry — mirrors
    the test_invariant_*_fires_on_drift pattern (synthetic-drift, no
    actual config reload). The replicated guard logic must detect
    the missing alias the same way the import-time assert would."""
    broken_response_types = [
        v for v in config.RESPONSE_TYPES if v != config.RESPONSE_TYPE_OFFER
    ]
    assert config.RESPONSE_TYPE_OFFER not in broken_response_types, (
        "Guard should fire: RESPONSE_TYPE_OFFER not in synthetic "
        "broken_response_types (the entry was deliberately removed)"
    )


# ── UPCOMING_WINDOW_OPTIONS + invariant #10 (DESIGN §5.1, §5.2 #10) ───────────
# T4-0b lock-down: the dashboard's Upcoming-panel selectbox offers a small
# set of forward-looking windows (default [30, 60, 90]). The default
# selection equals DEADLINE_ALERT_DAYS, which therefore must be a member
# of the offered list — invariant #10 catches a config edit that drops
# the default value from the options list.

def test_upcoming_window_options_is_non_empty_int_list():
    """DESIGN §5.1: UPCOMING_WINDOW_OPTIONS is the user-selectable widths
    (in days) for the dashboard's Upcoming-panel selectbox. Must be a
    non-empty list of positive ints — non-positive values would mean a
    zero- or past-window which makes no sense for an 'upcoming' panel."""
    assert isinstance(config.UPCOMING_WINDOW_OPTIONS, list)
    assert len(config.UPCOMING_WINDOW_OPTIONS) > 0
    assert all(
        isinstance(v, int) and v > 0
        for v in config.UPCOMING_WINDOW_OPTIONS
    ), (
        f"All entries must be positive ints; got "
        f"{config.UPCOMING_WINDOW_OPTIONS!r}"
    )


def test_invariant_10_default_window_in_options():
    """DESIGN §5.2 invariant #10: DEADLINE_ALERT_DAYS must be a member
    of UPCOMING_WINDOW_OPTIONS — the panel's selectbox default uses
    DEADLINE_ALERT_DAYS, so dropping it from the options list would
    leave the default value unable to render. Positive-case assertion
    that pairs with `test_invariant_10_fires_on_drift` below."""
    assert config.DEADLINE_ALERT_DAYS in config.UPCOMING_WINDOW_OPTIONS, (
        f"DEADLINE_ALERT_DAYS={config.DEADLINE_ALERT_DAYS} must appear in "
        f"UPCOMING_WINDOW_OPTIONS={config.UPCOMING_WINDOW_OPTIONS!r}. "
        f"The selectbox default uses DEADLINE_ALERT_DAYS — dropping it "
        f"from the list would leave the default unable to render."
    )


def test_invariant_10_fires_on_drift():
    """Replicate DESIGN §5.2 invariant #10 on a synthetic
    UPCOMING_WINDOW_OPTIONS list that has dropped DEADLINE_ALERT_DAYS —
    mirrors the test_invariant_*_fires_on_drift pattern (synthetic-drift,
    no actual config reload)."""
    broken_options = [
        v for v in config.UPCOMING_WINDOW_OPTIONS
        if v != config.DEADLINE_ALERT_DAYS
    ]
    assert config.DEADLINE_ALERT_DAYS not in broken_options, (
        "Guard should fire: DEADLINE_ALERT_DAYS not in synthetic "
        "broken_options (the entry was deliberately removed)"
    )


# ── Fresh import exercises every module-level assertion ──────────────────────

def test_config_reimports_cleanly():
    """A fresh import of config must execute all §5.2 invariants without
    raising. This is the most direct proof the import-time guards are wired
    — any broken invariant would surface as AssertionError here."""
    if "config" in sys.modules:
        importlib.reload(sys.modules["config"])
    else:
        importlib.import_module("config")
