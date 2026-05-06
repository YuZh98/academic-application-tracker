# pyright: strict
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

# ── Profile identity ─────────────────────────────────────────────────────────
# Database filename — rename the file on disk when changing this.
DB_FILENAME: str = "postdoc.db"

# Label used in recommender follow-up email subjects.
APPLICATION_LABEL: str = "academic application"

# ── Universal placeholder glyph ───────────────────────────────────────────────
# Em-dash (U+2014) used to render NULL / NaN / empty TEXT cells across every
# user-facing surface (page tables, dashboard KPIs, exports markdown).
# Single source of truth so a future glyph change is a one-line edit.
EM_DASH: str = "—"

# ── Status pipeline ───────────────────────────────────────────────────────────
# Ordered list: earlier index = earlier stage in the pipeline.
# Used by st.selectbox() in all page files — never hardcode status strings.
STATUS_VALUES: list[str] = [
    "[SAVED]",  # Found / saved for later; not yet applied
    "[APPLIED]",  # Application submitted
    "[INTERVIEW]",  # Interview stage reached
    "[OFFER]",  # Offer received
    "[CLOSED]",  # Deadline passed; did not apply
    "[REJECTED]",  # Rejection received
    "[DECLINED]",  # Offer turned down
]

# Maps each status to a color name for st.badge(color=...).
# Verified against st.badge signature in Streamlit 1.56.0:
#   accepted literals: 'red','orange','yellow','blue','green','violet','gray','grey','primary'
STATUS_COLORS: dict[str, str] = {
    "[SAVED]": "blue",
    "[APPLIED]": "orange",
    "[INTERVIEW]": "violet",
    "[OFFER]": "green",
    "[CLOSED]": "gray",
    "[REJECTED]": "red",
    "[DECLINED]": "gray",
}

# Storage-to-UI label map.
STATUS_LABELS: dict[str, str] = {
    "[SAVED]": "Saved",
    "[APPLIED]": "Applied",
    "[INTERVIEW]": "Interview",
    "[OFFER]": "Offer",
    "[CLOSED]": "Closed",
    "[REJECTED]": "Rejected",
    "[DECLINED]": "Declined",
}

# Named aliases for the individual pipeline statuses.
STATUS_SAVED: str = STATUS_VALUES[0]  # "[SAVED]"
STATUS_APPLIED: str = STATUS_VALUES[1]  # "[APPLIED]"
STATUS_INTERVIEW: str = STATUS_VALUES[2]  # "[INTERVIEW]"
STATUS_OFFER: str = STATUS_VALUES[3]  # "[OFFER]"
STATUS_CLOSED: str = STATUS_VALUES[4]  # "[CLOSED]"
STATUS_REJECTED: str = STATUS_VALUES[5]  # "[REJECTED]"
STATUS_DECLINED: str = STATUS_VALUES[6]  # "[DECLINED]"

# Terminal statuses — positions in these states are done and excluded from actionable views (upcoming deadlines, materials readiness, etc.).
TERMINAL_STATUSES: list[str] = ["[CLOSED]", "[REJECTED]", "[DECLINED]"]

# Applications-page filter sentinel + exclusion set (DESIGN §8.3).
STATUS_FILTER_ACTIVE: str = "Active"

# Universal "no narrowing applied" sentinel for filter selectboxes
# (Opportunities, Applications, Recommenders). The filter selectbox is
# rendered as `[FILTER_ALL] + <real options>` and the page checks
# `if selected != config.FILTER_ALL: ...narrow...`.
# Lives alongside STATUS_FILTER_ACTIVE because the two are the
# Applications page's two sentinel options on its single status filter.
FILTER_ALL: str = "All"

# Statuses removed by the "Active" filter sentinel above. Frozen so a
# page can't accidentally mutate it via .add()/.remove() and silently
# broaden the page's default filter at runtime. The selectbox stores
# the sentinel STATUS_FILTER_ACTIVE; the page resolves it to
# `set(STATUS_VALUES) - STATUS_FILTER_ACTIVE_EXCLUDED` at render time.
STATUS_FILTER_ACTIVE_EXCLUDED: frozenset[str] = frozenset(
    {
        STATUS_SAVED,
        STATUS_CLOSED,
    }
)


assert set(STATUS_VALUES) == set(STATUS_COLORS), (
    "STATUS_COLORS must have exactly one entry per STATUS_VALUES item. "
    f"Missing from STATUS_COLORS: {set(STATUS_VALUES) - set(STATUS_COLORS)}"
)
assert set(STATUS_VALUES) == set(STATUS_LABELS), (
    "STATUS_LABELS must have exactly one entry per STATUS_VALUES item. "
    f"Missing from STATUS_LABELS: {set(STATUS_VALUES) - set(STATUS_LABELS)}. "
    f"Extra: {set(STATUS_LABELS) - set(STATUS_VALUES)}."
)
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
# layout survives a STATUS_VALUES reorder or rename.
FUNNEL_BUCKETS: list[tuple[str, tuple[str, ...], str]] = [
    ("Saved", (STATUS_SAVED,), "#4F6BEF"),
    ("Applied", (STATUS_APPLIED,), "#F59E3A"),
    ("Interview", (STATUS_INTERVIEW,), "#8B5CF6"),
    ("Offer", (STATUS_OFFER,), "#10B981"),
    ("Closed", (STATUS_CLOSED,), "#94A3B8"),
    ("Archived", (STATUS_REJECTED, STATUS_DECLINED), "#94A3B8"),
]

# Buckets hidden by default on the dashboard funnel. Users reveal them
# (and re-hide them) via a single `st.button(type="tertiary")` rendered
# in the funnel subheader row; state persists as
# st.session_state["_funnel_expanded"] for the current session only.
# Default-hiding the terminal outcomes keeps the dashboard focused on
# active work (DESIGN D24). Values must be labels that exist in
# FUNNEL_BUCKETS — enforced by invariant #6 below.
FUNNEL_DEFAULT_HIDDEN: set[str] = {"Closed", "Archived"}

# State-keyed labels for the funnel disclosure toggle (DESIGN §8.1).
# The toggle reads its label at render time
# via:
#     config.FUNNEL_TOGGLE_LABELS[st.session_state["_funnel_expanded"]]
FUNNEL_TOGGLE_LABELS: dict[bool, str] = {
    False: "+ Show all stages",
    True: "− Show fewer stages",
}


_funnel_flat: list[str] = [raw for _, raws, _ in FUNNEL_BUCKETS for raw in raws]
assert sorted(_funnel_flat) == sorted(STATUS_VALUES), (
    "FUNNEL_BUCKETS raw-status coverage must equal STATUS_VALUES as a multiset "
    "(each status in exactly one bucket, nothing missing, nothing duplicated). "
    f"Flattened buckets: {sorted(_funnel_flat)!r}. "
    f"STATUS_VALUES:     {sorted(STATUS_VALUES)!r}."
)

_bucket_labels: set[str] = {label for label, _, _ in FUNNEL_BUCKETS}
assert FUNNEL_DEFAULT_HIDDEN <= _bucket_labels, (
    "FUNNEL_DEFAULT_HIDDEN must reference labels that exist in FUNNEL_BUCKETS. "
    f"Unknown: {FUNNEL_DEFAULT_HIDDEN - _bucket_labels}"
)

# ── Controlled vocabularies ───────────────────────────────────────────────────
PRIORITY_VALUES: list[str] = ["High", "Medium", "Low", "Stretch"]
WORK_AUTH_OPTIONS: list[str] = ["Yes", "No", "Unknown"]
FULL_TIME_OPTIONS: list[str] = ["Full-time", "Part-time", "Contract"]
SOURCE_OPTIONS: list[str] = [
    "Lab website",
    "AcademicJobsOnline",
    "HigherEdJobs",
    "LinkedIn",
    "Referral",
    "Conference",
    "Listserv",
    "Other",
]
RESPONSE_TYPES: list[str] = [
    "Acknowledgement",
    "Screening Call",
    "Interview Invite",
    "Rejection",
    "Offer",
    "Other",
]
RESPONSE_TYPE_OFFER: str = "Offer"


assert RESPONSE_TYPE_OFFER in RESPONSE_TYPES, (
    f"RESPONSE_TYPE_OFFER={RESPONSE_TYPE_OFFER!r} must be a member of "
    f"RESPONSE_TYPES={RESPONSE_TYPES!r}. R3 cascade depends on this."
)

# RESULT_DEFAULT must match the DEFAULT value in the applications table schema.
# If you rename this string, also update the DEFAULT clause in database.init_db().
RESULT_DEFAULT: str = "Pending"

RESULT_VALUES: list[str] = [
    RESULT_DEFAULT,  # DB default — do not rename without migrating schema
    "Offer Accepted",
    "Offer Declined",
    "Rejected",
    "Withdrawn",
]

RELATIONSHIP_VALUES: list[str] = [
    "PhD Advisor",
    "Committee Member",
    "Collaborator",
    "Postdoc Supervisor",
    "Department Faculty",
    "Other",
]

# Maps recommender `confirmed` INTEGER (0/1/NULL) to display strings.
# 1 = confirmed, 0 = declined/no, None = pending (no response yet).
# Centralised here so pages and exports use the same labels.
CONFIRMED_LABELS: dict[int | None, str] = {
    1: "Yes",
    0: "No",
    None: EM_DASH,
}

# Vocabulary for the interviews sub-table's `format` column
INTERVIEW_FORMATS: list[str] = ["Phone", "Video", "Onsite", "Other"]
# Tones offered by the Recommenders-page LLM-prompts expander.
REMINDER_TONES: tuple[str, ...] = ("gentle", "urgent")

# Requirement document types
REQUIREMENT_VALUES: list[str] = ["Yes", "Optional", "No"]

# UI labels for each canonical value. `st.radio(..., format_func=...)` looks
# up display text here so session_state keeps the canonical DB value and no
# save-time translation is needed.
REQUIREMENT_LABELS: dict[str, str] = {
    "Yes": "Required",
    "Optional": "Optional",
    "No": "Not needed",
}

assert set(REQUIREMENT_LABELS) == set(REQUIREMENT_VALUES), (
    "REQUIREMENT_LABELS must have exactly one entry per REQUIREMENT_VALUES item. "
    f"Missing: {set(REQUIREMENT_VALUES) - set(REQUIREMENT_LABELS)}"
)

REQUIREMENT_DOCS: list[tuple[str, str, str]] = [
    ("req_cv", "done_cv", "CV"),
    ("req_cover_letter", "done_cover_letter", "Cover Letter"),
    ("req_transcripts", "done_transcripts", "Transcripts"),
    ("req_research_statement", "done_research_statement", "Research Statement"),
    ("req_writing_sample", "done_writing_sample", "Writing Sample"),
    ("req_teaching_statement", "done_teaching_statement", "Teaching Statement"),
    ("req_diversity_statement", "done_diversity_statement", "Diversity Statement"),
]

# ── Quick-add form fields ─────────────────────────────────────────────────────
QUICK_ADD_FIELDS: list[str] = [
    "position_name",  # text input
    "institute",  # text input
    "field",  # text input
    "deadline_date",  # st.date_input
    "priority",  # st.selectbox from PRIORITY_VALUES
    "link",  # text input (URL)
]

# ── Opportunities edit panel ────────────────────────────────────────────────────

EDIT_PANEL_TABS: list[str] = ["Overview", "Requirements", "Materials", "Notes"]

# ── Dashboard display thresholds ──────────────────────────────────────────────
DEADLINE_ALERT_DAYS = 30  # Default Upcoming-panel window + upper edge of 🟡 band
DEADLINE_URGENT_DAYS = 7  # Color a deadline red if it falls within this many days
RECOMMENDER_ALERT_DAYS = 7  # Alert if a recommender was asked N+ days ago with no submission

# User-selectable widths (in days) for the dashboard's Upcoming-panel
UPCOMING_WINDOW_OPTIONS: list[int] = [30, 60, 90]

assert DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS, (
    f"DEADLINE_URGENT_DAYS={DEADLINE_URGENT_DAYS} must be <= "
    f"DEADLINE_ALERT_DAYS={DEADLINE_ALERT_DAYS}"
)
assert DEADLINE_ALERT_DAYS in UPCOMING_WINDOW_OPTIONS, (
    f"DEADLINE_ALERT_DAYS={DEADLINE_ALERT_DAYS} must appear in "
    f"UPCOMING_WINDOW_OPTIONS={UPCOMING_WINDOW_OPTIONS!r}. The "
    f"Upcoming-panel selectbox default uses DEADLINE_ALERT_DAYS — "
    f"dropping it from the list would leave the default unable to render."
)
assert set(FUNNEL_TOGGLE_LABELS.keys()) == {True, False}, (
    f"FUNNEL_TOGGLE_LABELS must have exactly the keys {{True, False}}. "
    f"Got: {sorted(FUNNEL_TOGGLE_LABELS.keys())!r}. The page indexes "
    f"this dict by the bool value of st.session_state['_funnel_expanded']."
)
assert STATUS_FILTER_ACTIVE_EXCLUDED <= set(STATUS_VALUES), (
    f"STATUS_FILTER_ACTIVE_EXCLUDED must be a subset of STATUS_VALUES. "
    f"Unknown entries: "
    f"{STATUS_FILTER_ACTIVE_EXCLUDED - set(STATUS_VALUES)!r}"
)
assert set(CONFIRMED_LABELS.keys()) == {1, 0, None}, (
    "CONFIRMED_LABELS must have exactly keys {1, 0, None}."
)


# ── Empty-state copy ──────────────────────────────────────────────────────────
EMPTY_FILTERED_POSITIONS: str = "No positions match the current filters."
EMPTY_NO_POSITIONS: str = "No positions yet — use Quick Add above to get started."
EMPTY_FILTERED_APPLICATIONS: str = "No applications match the current filter."
EMPTY_PENDING_RECOMMENDERS: str = "No pending recommenders."
EMPTY_PENDING_RECOMMENDER_FOLLOWUPS: str = "No pending recommender follow-ups."


# ── Urgency banding ──────────────────────────────────────────────────────────
def urgency_glyph(days_away: int | None) -> str:
    """Return the urgency glyph for ``days_away`` days until a deadline.

    Banding (lower-inclusive at every boundary):
        days_away ≤ DEADLINE_URGENT_DAYS    → '🔴'
        ≤ DEADLINE_ALERT_DAYS (past urgent)  → '🟡'
        beyond DEADLINE_ALERT_DAYS           → ''     (no signal)
        None (no deadline at all)            → EM_DASH

    The ``None`` branch distinguishes "no deadline at all" (em-dash
    placeholder) from "deadline far enough away that no
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
