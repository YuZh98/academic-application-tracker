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

# Set of known tracker-profile identifiers. Guards TRACKER_PROFILE at import
# time — catches typos or un-implemented profiles before any page renders.
# Extending to a new profile (e.g. "faculty") is a two-step: add the value
# here, then implement the profile-specific behaviour downstream per §12.1.
VALID_PROFILES: set[str] = {"postdoc"}

# Invariant (DESIGN §5.2 #1): TRACKER_PROFILE must be a known profile.
assert TRACKER_PROFILE in VALID_PROFILES, (
    f"TRACKER_PROFILE={TRACKER_PROFILE!r} is not a recognized profile. "
    f"Known: {sorted(VALID_PROFILES)!r}. Add it to VALID_PROFILES or fix the typo."
)

# ── Status pipeline ───────────────────────────────────────────────────────────
# Ordered list: earlier index = earlier stage in the pipeline.
# Used by st.selectbox() in all page files — never hardcode status strings.
STATUS_VALUES: list[str] = [
    "[SAVED]",       # Found / saved for later; not yet applied
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
    "[SAVED]":     "blue",
    "[APPLIED]":   "orange",
    "[INTERVIEW]": "violet",
    "[OFFER]":     "green",
    "[CLOSED]":    "gray",
    "[REJECTED]":  "red",
    "[DECLINED]":  "gray",
}

# Storage-to-UI label map. STATUS_VALUES keeps bracketed enum sentinels in
# storage so DB rows round-trip exactly and a raw status literal stays
# unambiguous in queries and logs; every user-facing surface goes through
# STATUS_LABELS to strip the brackets. Never print a raw STATUS_VALUES entry
# to the UI — look it up here instead (DESIGN §8.0 Status label convention).
# Drift caught by invariant #3 below.
STATUS_LABELS: dict[str, str] = {
    "[SAVED]":     "Saved",
    "[APPLIED]":   "Applied",
    "[INTERVIEW]": "Interview",
    "[OFFER]":     "Offer",
    "[CLOSED]":    "Closed",
    "[REJECTED]":  "Rejected",
    "[DECLINED]":  "Declined",
}

# Named aliases for the individual pipeline statuses. Page code that needs
# a *specific* status (e.g. the dashboard's per-bucket KPI counts) references
# these rather than hardcoding the literal — keeps the anti-typo guardrail in
# place without forcing positional-index access into STATUS_VALUES. Added in
# Phase 4 T1-C for app.py's Tracked / Applied / Interview counters; extended
# in the v1.1 doc refactor (F2 / F4 fix) so FUNNEL_BUCKETS below can be
# defined without literals. The stage-0 alias was renamed in v1.3
# Sub-task 5 alongside the stage-0 literal rename; existing rows migrate
# in place via the one-shot UPDATE in database.init_db() (DESIGN §6.3).
STATUS_SAVED:     str = STATUS_VALUES[0]  # "[SAVED]"
STATUS_APPLIED:   str = STATUS_VALUES[1]  # "[APPLIED]"
STATUS_INTERVIEW: str = STATUS_VALUES[2]  # "[INTERVIEW]"
STATUS_OFFER:     str = STATUS_VALUES[3]  # "[OFFER]"
STATUS_CLOSED:    str = STATUS_VALUES[4]  # "[CLOSED]"
STATUS_REJECTED:  str = STATUS_VALUES[5]  # "[REJECTED]"
STATUS_DECLINED:  str = STATUS_VALUES[6]  # "[DECLINED]"

# Terminal statuses — positions in these states are done and excluded from
# actionable views (upcoming deadlines, materials readiness, etc.).
# database.py reads this list; never hardcode these strings outside config.py.
TERMINAL_STATUSES: list[str] = ["[CLOSED]", "[REJECTED]", "[DECLINED]"]

# Guard (DESIGN §5.2 #2): STATUS_COLORS must have exactly one entry per
# STATUS_VALUES item. Catches drift at import time rather than as a
# KeyError deep in page code.
assert set(STATUS_VALUES) == set(STATUS_COLORS), (
    "STATUS_COLORS must have exactly one entry per STATUS_VALUES item. "
    f"Missing from STATUS_COLORS: {set(STATUS_VALUES) - set(STATUS_COLORS)}"
)
# Invariant (DESIGN §5.2 #3): every status has a UI label, no extras.
assert set(STATUS_VALUES) == set(STATUS_LABELS), (
    "STATUS_LABELS must have exactly one entry per STATUS_VALUES item. "
    f"Missing from STATUS_LABELS: {set(STATUS_VALUES) - set(STATUS_LABELS)}. "
    f"Extra: {set(STATUS_LABELS) - set(STATUS_VALUES)}."
)
# Invariant (DESIGN §5.2 #4): terminal statuses are a subset of all statuses.
assert set(TERMINAL_STATUSES) <= set(STATUS_VALUES), (
    "TERMINAL_STATUSES must only contain values defined in STATUS_VALUES. "
    f"Unknown: {set(TERMINAL_STATUSES) - set(STATUS_VALUES)}"
)

# ── Funnel buckets (dashboard presentation layer) ─────────────────────────────
# Presentation-layer grouping of raw statuses into dashboard-funnel bars.
# Each entry: (UI label, tuple of raw STATUS_VALUES contributing to this bar,
# bucket color). Order = display order (top-down when the y-axis is reversed).
# The bucket owns its color because a bucket can aggregate multiple raw
# statuses — STATUS_COLORS[raw] is a per-status concern (badges, tooltips).
#
# "Archived" groups rejection + declined-offer — both are outcomes after
# engagement. "Closed" stays its own bucket because pre-application
# withdrawal is a genuinely distinct state (DESIGN D17).
#
# Raw statuses are referenced via the named aliases above so the bucket
# layout survives a STATUS_VALUES reorder or rename (the stage-0 rename
# in v1.3 Sub-task 5 was a single-line swap of the stage-0 alias without
# changing this table).
FUNNEL_BUCKETS: list[tuple[str, tuple[str, ...], str]] = [
    ("Saved",     (STATUS_SAVED,),                    "blue"),
    ("Applied",   (STATUS_APPLIED,),                  "orange"),
    ("Interview", (STATUS_INTERVIEW,),                "violet"),
    ("Offer",     (STATUS_OFFER,),                    "green"),
    ("Closed",    (STATUS_CLOSED,),                   "gray"),
    ("Archived",  (STATUS_REJECTED, STATUS_DECLINED), "gray"),
]

# Buckets hidden by default on the dashboard funnel. Users reveal them
# all at once via a single `[expand]` button rendered below the chart;
# state persists as st.session_state["_funnel_expanded"] for the current
# session only. Default-hiding the terminal outcomes keeps the dashboard
# focused on active work (DESIGN D24). Values must be labels that exist
# in FUNNEL_BUCKETS — enforced below.
FUNNEL_DEFAULT_HIDDEN: set[str] = {"Closed", "Archived"}

# Invariant (DESIGN §5.2 #5): flatten the raw-status tuples across all
# FUNNEL_BUCKETS entries; the result must be a multiset-equal permutation
# of STATUS_VALUES. This asserts two facts at once — every raw status
# appears in some bucket, AND no status appears in more than one bucket.
# A violation means either a new status was added to STATUS_VALUES without
# placing it in a bucket, or a status was duplicated across buckets.
_funnel_flat: list[str] = [raw for _, raws, _ in FUNNEL_BUCKETS for raw in raws]
assert sorted(_funnel_flat) == sorted(STATUS_VALUES), (
    "FUNNEL_BUCKETS raw-status coverage must equal STATUS_VALUES as a multiset "
    "(each status in exactly one bucket, nothing missing, nothing duplicated). "
    f"Flattened buckets: {sorted(_funnel_flat)!r}. "
    f"STATUS_VALUES:     {sorted(STATUS_VALUES)!r}."
)

# Invariant (DESIGN §5.2 #6): FUNNEL_DEFAULT_HIDDEN must reference labels
# that actually exist in FUNNEL_BUCKETS — otherwise a label could be
# hidden by default with no corresponding bucket to reveal.
_bucket_labels: set[str] = {label for label, _, _ in FUNNEL_BUCKETS}
assert FUNNEL_DEFAULT_HIDDEN <= _bucket_labels, (
    "FUNNEL_DEFAULT_HIDDEN must reference labels that exist in FUNNEL_BUCKETS. "
    f"Unknown: {FUNNEL_DEFAULT_HIDDEN - _bucket_labels}"
)

# ── Controlled vocabularies ───────────────────────────────────────────────────
# Used by st.selectbox() in page files.
# Append to any list to add a new option — no other changes needed.

PRIORITY_VALUES: list[str] = ["High", "Medium", "Low", "Stretch"]

# Three-value categorical answering "does the posting accept this applicant's
# work authorization?" Paired with the freetext `work_auth_note` column so the
# enum stays filter-friendly while nuance ("green card required", "J-1 OK
# with a waiver") lands in free text (DESIGN §5.1 + D22). Replaced the
# six-value Any/OPT/J-1/H1B/No Sponsorship/Ask list in v1.3 — any legacy
# values lingering in a dev DB stay as orphan TEXT (column has no constraint);
# see CHANGELOG [Unreleased] Sub-task 3 for the recommended manual translation.
WORK_AUTH_OPTIONS: list[str] = ["Yes", "No", "Unknown"]

# Employment type. The pre-v1.3 Yes/No/Part-time list was ambiguous
# (Yes = full-time? Yes = available?); the v1.3 vocabulary names the
# category explicitly (DESIGN §5.1). Column remains plain TEXT — no DDL
# change — so dev DBs carrying 'Yes' / 'No' need manual translation
# (CHANGELOG [Unreleased] Sub-task 3).
FULL_TIME_OPTIONS: list[str] = ["Full-time", "Part-time", "Contract"]

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

# Vocabulary for the interviews sub-table's `format` column (DESIGN §6.2).
# Kept small on purpose — "Other" is the escape hatch for edge cases so the
# list doesn't bloat with one-off formats (hybrid, dinner, campus visit…).
INTERVIEW_FORMATS: list[str] = ["Phone", "Video", "Onsite", "Other"]

# ── Requirement document types ────────────────────────────────────────────────
# Each tuple: (db_req_column, db_done_column, display_label)
#
#   db_req_column  — TEXT column in positions table: 'Yes' | 'Optional' | 'No'
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
# these strings in page files. DESIGN §5.1 + D21 pin the full-word vocabulary
# (Yes/Optional/No) — consistent with D20's full-word philosophy for
# type-safe, self-descriptive raw dumps; the short-code form (Y/Optional/N)
# was used before v1.3 and migrates in place via init_db() on next start.
REQUIREMENT_VALUES: list[str] = ["Yes", "Optional", "No"]

# UI labels for each canonical value. `st.radio(..., format_func=...)` looks
# up display text here so session_state keeps the canonical DB value and no
# save-time translation is needed.
REQUIREMENT_LABELS: dict[str, str] = {
    "Yes":      "Required",
    "Optional": "Optional",
    "No":       "Not needed",
}

# Invariant (DESIGN §5.2 #7): one label per canonical value — catches drift at
# import time rather than as a KeyError deep in page code.
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

# Invariant (DESIGN §5.2 #8): urgency window cannot exceed the alert window.
# Swapping these by accident would mark every upcoming deadline "urgent"
# (collapsing the urgency signal) — caught at import before any page renders.
assert DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS, (
    f"DEADLINE_URGENT_DAYS={DEADLINE_URGENT_DAYS} must be <= "
    f"DEADLINE_ALERT_DAYS={DEADLINE_ALERT_DAYS}"
)
