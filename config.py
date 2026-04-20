# config.py
# Single source of truth for all constants, vocabularies, and field definitions.
# This is the ONLY file that needs to change when:
#   - Adding a new document requirement type
#   - Adding a new vocabulary option
#   - Switching tracker profile (postdoc → software_eng, faculty, etc.)
#
# Rules:
#   - This file imports NOTHING from this project.
#   - No functions, no I/O, no side effects — constants only.
#   - All other modules import from here; never hardcode values in page files.

# ── Tracker identity ──────────────────────────────────────────────────────────
TRACKER_PROFILE: str = "postdoc"   # Options: "postdoc" | "software_eng" | "faculty"
# Note: TRACKER_PROFILE will be consumed by database.init_db() (Phase 2) and
# page files (Phase 3) to filter profile-specific fields. If unused after
# Phase 3, remove to avoid dead code.

# ── Status pipeline ───────────────────────────────────────────────────────────
# Ordered list: earlier index = earlier stage in the pipeline.
# Used by st.selectbox() in all page files — never hardcode status strings.
STATUS_VALUES: list[str] = [
    "[OPEN]",        # Found; not yet applied
    "[APPLIED]",     # Application submitted
    "[INTERVIEW]",   # Interview stage reached
    "[OFFER]",       # Offer received
    "[CLOSED]",      # Deadline passed; did not apply
    "[REJECTED]",    # Rejection received
    "[DECLINED]",    # Offer turned down
]

# Maps each status to a color name for st.badge(color=...).
# Verified against st.badge signature in Streamlit 1.56.0:
#   accepted literals: 'red','orange','yellow','blue','green','violet','gray','grey','primary'
STATUS_COLORS: dict[str, str] = {
    "[OPEN]":      "blue",
    "[APPLIED]":   "orange",
    "[INTERVIEW]": "violet",
    "[OFFER]":     "green",
    "[CLOSED]":    "gray",
    "[REJECTED]":  "red",
    "[DECLINED]":  "gray",
}

# Terminal statuses — positions in these states are done and excluded from
# actionable views (upcoming deadlines, materials readiness, etc.).
# database.py reads this list; never hardcode these strings outside config.py.
TERMINAL_STATUSES: list[str] = ["[CLOSED]", "[REJECTED]", "[DECLINED]"]

# Guard: STATUS_COLORS must have exactly one entry per STATUS_VALUES item.
# Catches drift at import time rather than as a KeyError deep in page code.
assert set(STATUS_VALUES) == set(STATUS_COLORS), (
    "STATUS_COLORS must have exactly one entry per STATUS_VALUES item. "
    f"Missing from STATUS_COLORS: {set(STATUS_VALUES) - set(STATUS_COLORS)}"
)
assert set(TERMINAL_STATUSES) <= set(STATUS_VALUES), (
    "TERMINAL_STATUSES must only contain values defined in STATUS_VALUES. "
    f"Unknown: {set(TERMINAL_STATUSES) - set(STATUS_VALUES)}"
)

# ── Controlled vocabularies ───────────────────────────────────────────────────
# Used by st.selectbox() in page files.
# Append to any list to add a new option — no other changes needed.

PRIORITY_VALUES: list[str] = ["High", "Med", "Low", "Stretch"]

WORK_AUTH_OPTIONS: list[str] = ["Any", "OPT", "J-1", "H1B", "No Sponsorship", "Ask"]

FULL_TIME_OPTIONS: list[str] = ["Yes", "No", "Part-time"]

SOURCE_OPTIONS: list[str] = [
    "Lab website", "AcademicJobsOnline", "HigherEdJobs",
    "LinkedIn", "Referral", "Conference", "Listserv", "Other",
]

RESPONSE_TYPES: list[str] = [
    "Acknowledgement", "Screening Call", "Interview Invite",
    "Rejection", "Offer", "Other",
]

# RESULT_DEFAULT must match the DEFAULT value in the applications table schema.
# If you rename this string, also update the DEFAULT clause in database.init_db().
RESULT_DEFAULT: str = "Pending"

RESULT_VALUES: list[str] = [
    RESULT_DEFAULT,          # DB default — do not rename without migrating schema
    "Offer Accepted", "Offer Declined", "Rejected", "Withdrawn",
]

RELATIONSHIP_TYPES: list[str] = [
    "PhD Advisor", "Committee Member", "Collaborator",
    "Postdoc Supervisor", "Department Faculty", "Other",
]

# ── Requirement document types ────────────────────────────────────────────────
# Each tuple: (db_req_column, db_done_column, display_label)
#
#   db_req_column  — TEXT column in positions table: 'Y' | 'N' | 'Optional'
#   db_done_column — INTEGER column in positions table: 0 = not ready, 1 = ready
#   display_label  — Human-readable name shown in the UI
#
# To add a new document type (e.g., Portfolio):
#   1. Append ("req_portfolio", "done_portfolio", "Portfolio") here.
#   2. database.init_db() will create the new columns on next run.
#   3. No other file needs to change.
# Canonical DB values for the req_* TEXT columns. Order is the display order
# the Requirements-tab radios use (T4-D) — "Required" first so the common
# case is the leftmost/default-read option. Per GUIDELINES §6, never hardcode
# these strings in page files.
REQUIREMENT_VALUES: list[str] = ["Y", "Optional", "N"]

# UI labels for each canonical value. `st.radio(..., format_func=...)` looks
# up display text here so session_state keeps the canonical DB value and no
# save-time translation is needed.
REQUIREMENT_LABELS: dict[str, str] = {
    "Y":        "Required",
    "Optional": "Optional",
    "N":        "Not needed",
}

# Guard: one label per canonical value — catches drift at import time.
assert set(REQUIREMENT_LABELS) == set(REQUIREMENT_VALUES), (
    "REQUIREMENT_LABELS must have exactly one entry per REQUIREMENT_VALUES item. "
    f"Missing: {set(REQUIREMENT_VALUES) - set(REQUIREMENT_LABELS)}"
)

REQUIREMENT_DOCS: list[tuple[str, str, str]] = [
    ("req_cv",                  "done_cv",                  "CV"),
    ("req_cover_letter",        "done_cover_letter",        "Cover Letter"),
    ("req_transcripts",         "done_transcripts",         "Transcripts"),
    ("req_research_statement",  "done_research_statement",  "Research Statement"),
    ("req_writing_sample",      "done_writing_sample",      "Writing Sample"),
    ("req_teaching_statement",  "done_teaching_statement",  "Teaching Statement"),
    ("req_diversity_statement", "done_diversity_statement", "Diversity Statement"),
]

# ── Quick-add form fields ─────────────────────────────────────────────────────
# The minimal set shown in the quick-add expander on the Opportunities page.
# Each string must be an exact column name in the positions table.
# Verified against DESIGN.md §6 database schema — all match.
QUICK_ADD_FIELDS: list[str] = [
    "position_name",   # text input
    "institute",       # text input
    "field",           # text input
    "deadline_date",   # st.date_input
    "priority",        # st.selectbox from PRIORITY_VALUES
    "link",            # text input (URL)
]

# ── Opportunities edit panel (Tier 4) ─────────────────────────────────────────
# Tab labels for the inline edit panel below the positions table.
# Order determines the display order of st.tabs(...); first item is shown by
# default. Rename or reorder here rather than in pages/1_Opportunities.py.
#
# To add a new tab (e.g., "Contacts"): append the label here and extend the
# page's tab-body dispatch in pages/1_Opportunities.py.
EDIT_PANEL_TABS: list[str] = ["Overview", "Requirements", "Materials", "Notes"]

# ── Dashboard display thresholds ──────────────────────────────────────────────
DEADLINE_ALERT_DAYS    = 30   # Show upcoming deadlines within this many days
DEADLINE_URGENT_DAYS   = 7    # Color a deadline red if it falls within this many days
RECOMMENDER_ALERT_DAYS = 7    # Alert if a recommender was asked N+ days ago with no submission
