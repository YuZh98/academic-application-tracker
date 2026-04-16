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
TRACKER_PROFILE = "postdoc"   # Options: "postdoc" | "software_eng" | "faculty"

# ── Status pipeline ───────────────────────────────────────────────────────────
# Ordered list: earlier index = earlier stage in the pipeline.
# Used by st.selectbox() in all page files — never hardcode status strings.
STATUS_VALUES = [
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
STATUS_COLORS = {
    "[OPEN]":      "blue",
    "[APPLIED]":   "orange",
    "[INTERVIEW]": "violet",
    "[OFFER]":     "green",
    "[CLOSED]":    "gray",
    "[REJECTED]":  "red",
    "[DECLINED]":  "gray",
}

# ── Controlled vocabularies ───────────────────────────────────────────────────
# Used by st.selectbox() in page files.
# Append to any list to add a new option — no other changes needed.

PRIORITY_VALUES = ["High", "Med", "Low", "Stretch"]

WORK_AUTH_OPTIONS = ["Any", "OPT", "J-1", "H1B", "No Sponsorship", "Ask"]

FULL_TIME_OPTIONS = ["Yes", "No", "Part-time"]

SOURCE_OPTIONS = [
    "Lab website", "AcademicJobsOnline", "HigherEdJobs",
    "LinkedIn", "Referral", "Conference", "Listserv", "Other",
]

RESPONSE_TYPES = [
    "Acknowledgement", "Screening Call", "Interview Invite",
    "Rejection", "Offer", "Other",
]

RESULT_VALUES = [
    "Pending", "Offer Accepted", "Offer Declined", "Rejected", "Withdrawn",
]

RELATIONSHIP_TYPES = [
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
REQUIREMENT_DOCS = [
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
QUICK_ADD_FIELDS = [
    "position_name",   # text input
    "institute",       # text input
    "field",           # text input
    "deadline_date",   # st.date_input
    "priority",        # st.selectbox from PRIORITY_VALUES
    "link",            # text input (URL)
]

# ── Dashboard display thresholds ──────────────────────────────────────────────
DEADLINE_ALERT_DAYS   = 30   # Show upcoming deadlines within this many days
DEADLINE_URGENT_DAYS  = 7    # Color a deadline red if it falls within this many days
RECOMMENDER_ALERT_DAYS = 7   # Alert if a recommender was asked N+ days ago with no submission
