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

# ── Universal placeholder glyph ───────────────────────────────────────────────
# Em-dash (U+2014) used to render NULL / NaN / empty TEXT cells across every
# user-facing surface (page tables, dashboard KPIs, exports markdown). Lifted
# to config in Phase 7 cleanup CL2 — was previously duplicated as
# `EM_DASH = "—"` in pages/1_Opportunities.py + pages/2_Applications.py +
# pages/3_Recommenders.py, as `_EM_DASH` in exports.py, and as
# `NEXT_INTERVIEW_EMPTY` in app.py (same value, different name). Single
# source of truth so a future glyph change is a one-line edit.
EM_DASH: str = "—"

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

# Applications-page filter sentinel + exclusion set (DESIGN §8.3, Phase 5
# T1-B). The Applications page selectbox offers an "Active" sentinel as
# its default — semantically "every status that is still actionable"
# (excludes pre-application STATUS_SAVED and withdrawn STATUS_CLOSED).
# The literal lives in config (not the page) so a future surface — e.g.
# a "Tracked: Active" KPI variant on the dashboard — can reference it
# without hardcoding. Drift caught by §5.2 invariant #12.
STATUS_FILTER_ACTIVE: str = "Active"

# Universal "no narrowing applied" sentinel for filter selectboxes
# (Opportunities, Applications, Recommenders). The filter selectbox is
# rendered as `[FILTER_ALL] + <real options>` and the page checks
# `if selected != config.FILTER_ALL: ...narrow...`. Lifted to config in
# Phase 7 cleanup CL2 — was a magic "All" literal in three pages.
# Lives alongside STATUS_FILTER_ACTIVE because the two are the
# Applications page's two sentinel options on its single status filter.
FILTER_ALL: str = "All"

# Statuses removed by the "Active" filter sentinel above. Frozen so a
# page can't accidentally mutate it via .add()/.remove() and silently
# broaden the page's default filter at runtime. The selectbox stores
# the sentinel STATUS_FILTER_ACTIVE; the page resolves it to
# `set(STATUS_VALUES) - STATUS_FILTER_ACTIVE_EXCLUDED` at render time.
STATUS_FILTER_ACTIVE_EXCLUDED: frozenset[str] = frozenset({
    STATUS_SAVED,
    STATUS_CLOSED,
})

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
# (and re-hide them) via a single `st.button(type="tertiary")` rendered
# in the funnel subheader row; state persists as
# st.session_state["_funnel_expanded"] for the current session only.
# Default-hiding the terminal outcomes keeps the dashboard focused on
# active work (DESIGN D24). Values must be labels that exist in
# FUNNEL_BUCKETS — enforced by invariant #6 below.
FUNNEL_DEFAULT_HIDDEN: set[str] = {"Closed", "Archived"}

# State-keyed labels for the funnel disclosure toggle (DESIGN §8.1
# T6 amendment, 2026-04-30). The toggle reads its label at render time
# via:
#     config.FUNNEL_TOGGLE_LABELS[st.session_state["_funnel_expanded"]]
#
# A label describes what the click WILL DO, not the current state:
#   key=False (currently collapsed) → label invites EXPAND   ("+ Show all stages")
#   key=True  (currently expanded ) → label invites COLLAPSE ("− Show fewer stages")
#
# Locked in config so the page file never carries a user-facing literal
# (GUIDELINES §6 "no hardcoded vocab"). The `<symbol> <verb-phrase>`
# shape matches the project's CTA convention used by the empty-DB hero
# ("+ Add your first position") and the Materials Readiness CTA
# ("→ Opportunities page") — visual-vocabulary cohesion across all four
# dashboard CTAs. The leading `+` (U+002B) / `−` (U+2212 minus, NOT the
# hyphen-minus U+002D) encode the click's effect direction: adds buckets
# to the view / removes some from it.
#
# Invariant #11 below pins the dict to exactly the keys {True, False};
# a missing key would surface as a render-time KeyError on first toggle.
FUNNEL_TOGGLE_LABELS: dict[bool, str] = {
    False: "+ Show all stages",
    True:  "− Show fewer stages",
}

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

# Named alias for the response that fires the R3 auto-promotion cascade
# (DESIGN §9.3). database.upsert_application reads this rather than the
# hardcoded literal so a future rename of the 'Offer' entry inside
# RESPONSE_TYPES doesn't silently break R3 — same anti-typo guardrail
# as the STATUS_* aliases. The literal lives here (not as
# RESPONSE_TYPES[i]) because RESPONSE_TYPES order is not a contract;
# only membership matters, and invariant #9 below catches drift.
RESPONSE_TYPE_OFFER: str = "Offer"

# Invariant (DESIGN §5.2 #9): RESPONSE_TYPE_OFFER must be a real
# selectbox option. If a future rename drops 'Offer' from
# RESPONSE_TYPES without also updating the alias, the user's pick
# would never match the cascade trigger — caught at import-time
# rather than as a silent R3 no-op in production.
assert RESPONSE_TYPE_OFFER in RESPONSE_TYPES, (
    f"RESPONSE_TYPE_OFFER={RESPONSE_TYPE_OFFER!r} must be a member of "
    f"RESPONSE_TYPES={RESPONSE_TYPES!r}. R3 cascade depends on this."
)

# RESULT_DEFAULT must match the DEFAULT value in the applications table schema.
# If you rename this string, also update the DEFAULT clause in database.init_db().
RESULT_DEFAULT: str = "Pending"

RESULT_VALUES: list[str] = [
    RESULT_DEFAULT,          # DB default — do not rename without migrating schema
    "Offer Accepted", "Offer Declined", "Rejected", "Withdrawn",
]

RELATIONSHIP_VALUES: list[str] = [
    "PhD Advisor", "Committee Member", "Collaborator",
    "Postdoc Supervisor", "Department Faculty", "Other",
]

# Vocabulary for the interviews sub-table's `format` column (DESIGN §6.2).
# Kept small on purpose — "Other" is the escape hatch for edge cases so the
# list doesn't bloat with one-off formats (hybrid, dinner, campus visit…).
INTERVIEW_FORMATS: list[str] = ["Phone", "Video", "Onsite", "Other"]

# Tones offered by the Recommenders-page LLM-prompts expander
# (Phase 5 T6). The expander renders one prompt per tone — the label
# `f"LLM prompts ({len(REMINDER_TONES)} tones)"` reads its count from
# this tuple so adding a third tone (e.g. "formal") is a config-only
# edit. Tuple (not list) so it's hashable + immutable. Lifted to config
# in Phase 7 cleanup CL2 — was a private `_REMINDER_TONES` in
# pages/3_Recommenders.py.
REMINDER_TONES: tuple[str, ...] = ("gentle", "urgent")

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
DEADLINE_ALERT_DAYS    = 30   # Default Upcoming-panel window + upper edge of 🟡 band
DEADLINE_URGENT_DAYS   = 7    # Color a deadline red if it falls within this many days
RECOMMENDER_ALERT_DAYS = 7    # Alert if a recommender was asked N+ days ago with no submission

# User-selectable widths (in days) for the dashboard's Upcoming-panel
# selectbox (DESIGN §8.1, T4-0b lock-down). The selectbox defaults to
# DEADLINE_ALERT_DAYS and lets the user widen the view to see further
# ahead. The urgency band (🔴 / 🟡) stays tied to DEADLINE_URGENT_DAYS /
# DEADLINE_ALERT_DAYS regardless of the selected window — wider windows
# surface more rows but do not lower urgency. Invariant #10 below
# guarantees the default value is a real option.
UPCOMING_WINDOW_OPTIONS: list[int] = [30, 60, 90]

# Invariant (DESIGN §5.2 #8): urgency window cannot exceed the alert window.
# Swapping these by accident would mark every upcoming deadline "urgent"
# (collapsing the urgency signal) — caught at import before any page renders.
assert DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS, (
    f"DEADLINE_URGENT_DAYS={DEADLINE_URGENT_DAYS} must be <= "
    f"DEADLINE_ALERT_DAYS={DEADLINE_ALERT_DAYS}"
)

# Invariant (DESIGN §5.2 #10): the Upcoming-panel selectbox default
# (= DEADLINE_ALERT_DAYS) must be a real option in the offered list,
# otherwise the selectbox couldn't render at the spec'd default.
# Catches a config edit that drops 30 from UPCOMING_WINDOW_OPTIONS
# without updating the default.
assert DEADLINE_ALERT_DAYS in UPCOMING_WINDOW_OPTIONS, (
    f"DEADLINE_ALERT_DAYS={DEADLINE_ALERT_DAYS} must appear in "
    f"UPCOMING_WINDOW_OPTIONS={UPCOMING_WINDOW_OPTIONS!r}. The "
    f"Upcoming-panel selectbox default uses DEADLINE_ALERT_DAYS — "
    f"dropping it from the list would leave the default unable to render."
)

# Invariant (DESIGN §5.2 #11): FUNNEL_TOGGLE_LABELS must have exactly
# the keys {True, False}. The page reads it as
# config.FUNNEL_TOGGLE_LABELS[st.session_state["_funnel_expanded"]] —
# a missing key surfaces as a render-time KeyError on first toggle into
# that state; an extra key would silently no-op (harmless but confusing
# for a future maintainer). Caught at import before any page renders.
assert set(FUNNEL_TOGGLE_LABELS.keys()) == {True, False}, (
    f"FUNNEL_TOGGLE_LABELS must have exactly the keys {{True, False}}. "
    f"Got: {sorted(FUNNEL_TOGGLE_LABELS.keys())!r}. The page indexes "
    f"this dict by the bool value of st.session_state['_funnel_expanded']."
)

# Invariant (DESIGN §5.2 #12): STATUS_FILTER_ACTIVE_EXCLUDED must be a
# subset of STATUS_VALUES. Catches a typo in the exclusion set or a
# rename of a STATUS_VALUES entry that doesn't propagate. Without this
# guard, an unknown status in the exclusion set would surface as a
# silent filter no-op (page hides nothing extra) rather than a clear
# import-time AssertionError.
assert STATUS_FILTER_ACTIVE_EXCLUDED <= set(STATUS_VALUES), (
    f"STATUS_FILTER_ACTIVE_EXCLUDED must be a subset of STATUS_VALUES. "
    f"Unknown entries: "
    f"{STATUS_FILTER_ACTIVE_EXCLUDED - set(STATUS_VALUES)!r}"
)


# ── Empty-state copy (Phase 7 CL4 lift) ───────────────────────────────────────
# Locked copy for the five `st.info(...)` empty-state messages surfaced
# across the app — one constant per surface (per-surface naming, not a
# single template, because the wording is intentionally surface-specific:
# "filters" plural for Opportunities, "filter" singular for Applications
# matches each page's filter-bar cardinality; "recommenders" on the
# Recommenders page vs. "recommender follow-ups" on the dashboard
# distinguishes the page-level vs. alert-panel framing).
#
# Lifted to config in Phase 7 cleanup CL4 so a future copy edit is a
# one-line change tracked in `git blame` against this constant rather
# than a five-page hunt-and-replace. Tests assert against the constant
# by name, so a future copy update flows through to assertions
# automatically — no test churn.
EMPTY_FILTERED_POSITIONS:               str = "No positions match the current filters."
EMPTY_NO_POSITIONS:                     str = "No positions yet — use Quick Add above to get started."
EMPTY_FILTERED_APPLICATIONS:            str = "No applications match the current filter."
EMPTY_PENDING_RECOMMENDERS:             str = "No pending recommenders."
EMPTY_PENDING_RECOMMENDER_FOLLOWUPS:    str = "No pending recommender follow-ups."


# ── Urgency banding (Phase 7 T1 contract; CL2 lift) ───────────────────────────
# The same banding fires on the dashboard's Upcoming panel, in the
# Opportunities table's Urgency column, and (potentially) in any
# future surface that needs the at-a-glance "how close is this?" cue.
# Lifted here in CL2 so the threshold logic exists in exactly one
# place — page + database wrappers parse their input shapes (date
# string vs. integer days) and delegate to this function.
def urgency_glyph(days_away: int | None) -> str:
    """Return the urgency glyph for ``days_away`` days until a deadline.

    Banding (lower-inclusive at every boundary):
        days_away ≤ DEADLINE_URGENT_DAYS    → '🔴'
        ≤ DEADLINE_ALERT_DAYS (past urgent)  → '🟡'
        beyond DEADLINE_ALERT_DAYS           → ''     (no signal)
        None (no deadline at all)            → EM_DASH

    The ``None`` branch distinguishes "no deadline at all" (em-dash
    placeholder, Phase 7 T1) from "deadline far enough away that no
    signal fires" (empty string). Both look "absent" to a casual
    reader, but the em-dash makes "we know there's nothing scheduled"
    visible, while the empty string lets the table cell read as
    ordinary whitespace for a far-future deadline.

    Negative inputs (past-due) fall into the urgent band — at least
    as extreme as 'due today', and pinned by
    test_urgency_glyph_negative_days_is_red so a future band-rewrite
    can't silently regress this case.
    """
    if days_away is None:
        return EM_DASH
    if days_away <= DEADLINE_URGENT_DAYS:
        return "🔴"
    if days_away <= DEADLINE_ALERT_DAYS:
        return "🟡"
    return ""
