# System Design: Postdoc Application Tracker
**Version:** 1.3 | **Updated:** 2026-04-23 | **Status:** v1 target design (authoritative)

This document is the authoritative design specification. It describes
**the target design for v1** (what the system will be at v1.0.0 release)
and flags **forward-looking ideas for v2+** where they affect
architectural decisions today (see §12). Implementation status (what's
in code right now vs. what the spec says) lives in `CHANGELOG.md` and
`TASKS.md` — not here.

DESIGN.md is updated only on architectural change. Small corrections
land as patch-style edits; structural changes bump the `Version:` line.

---

## Table of Contents

1. [Purpose & Scope](#1-purpose--scope)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [File Structure](#4-file-structure)
5. [config.py — Specification](#5-configpy--specification)
6. [Database Schema](#6-database-schema)
7. [Module Contracts](#7-module-contracts)
8. [UI Design — Page by Page](#8-ui-design--page-by-page)
9. [Cross-page Data Flows](#9-cross-page-data-flows)
10. [Key Architectural Decisions](#10-key-architectural-decisions)
11. [Extension Guide](#11-extension-guide)
12. [v2 Design Notes](#12-v2-design-notes)

---

## 1. Purpose & Scope

### Problem
A postdoc job search involves tracking dozens of positions simultaneously
across different institutions, each with unique deadlines, requirement
checklists, recommendation letter logistics, and outcome timelines.
Markdown files alone cannot answer the key daily question: **"What do I
do today?"**

### Solution
A local, single-user web application that:
- Captures new positions in under 30 seconds
- Computes and surfaces the most urgent actions automatically
- Tracks recommendation letter status per recommender, per position
- Maintains human-readable markdown exports as a portable backup
- Is extensible to a general job tracker by editing a single configuration file

### Explicit Non-Goals (v1)
- No user authentication
- No cloud deployment
- No mobile-first layout
- No email or calendar integration
- No multi-user support

Forward-looking ideas for v2+ that influence v1 architecture are collected
in §12.

---

## 2. Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER                                            │
│                                                                │
│  app.py              pages/1_Opportunities.py                  │
│  (Dashboard)         pages/2_Applications.py                   │
│                      pages/3_Recommenders.py                   │
│                      pages/4_Export.py                         │
│                                                                │
│  Framework: Streamlit  |  Charts: Plotly (Graph Objects)       │
└────────────────────┬───────────────────────────────────────────┘
                     │ Python function calls (no SQL in pages)
┌────────────────────▼───────────────────────────────────────────┐
│  LOGIC LAYER                                                   │
│                                                                │
│  database.py                    exports.py                     │
│  (all reads/writes)             (markdown generators)          │
│                                                                │
│  Both import config.py. Neither imports Streamlit.             │
└────────────────────┬──────────────────────┬────────────────────┘
                     │ SQL via sqlite3       │ writes files
┌────────────────────▼──┐          ┌────────▼───────────────────┐
│  DATA LAYER           │          │  EXPORT LAYER              │
│                       │          │                            │
│  postdoc.db           │          │  exports/                  │
│  (SQLite, gitignored) │          │  OPPORTUNITIES.md          │
│                       │          │  PROGRESS.md               │
│  Single source of     │          │  RECOMMENDERS.md           │
│  truth for all data   │          │                            │
│                       │          │  Regenerated after every   │
└───────────────────────┘          │  write; human-readable     │
                                   │  backup; git-committed     │
                                   └────────────────────────────┘
```

### Layer rules (enforced)

| Layer | May import | May NOT import |
|-------|-----------|----------------|
| Page files | `database`, `config` | `exports` (directly), each other |
| `database.py` | `config`, `sqlite3`, `pandas` | `streamlit`, `exports` (top-level — deferred import only) |
| `exports.py` | `database`, `config` | `streamlit` |
| `config.py` | stdlib only | anything from this project |

`exports.write_all()` is called as the last step of every `database.py`
write function. Page files never call `exports` directly. The
`database → exports → database` cycle is broken by importing `exports`
lazily inside each database write function.

---

## 3. Technology Stack

| Component | Choice | Required ≥ | Rationale |
|-----------|--------|-----------|-----------|
| Language | Python | 3.14 | Already available; familiar to stats/data users |
| Environment | venv (`.venv/`) | stdlib | Zero extra tools; isolates packages; gitignored |
| UI framework | Streamlit | 1.50 | Python-native; `width="stretch"` and `st.switch_page` require ≥ 1.50 |
| Charts | Plotly (Graph Objects) | 5.22 | Used via `plotly.graph_objects.Figure` / `go.Bar`; click events for future interactivity |
| Data frames | pandas | 2.2 | Bridges SQLite rows ↔ Streamlit display widgets |
| Database | SQLite via `sqlite3` | stdlib | No server; single file; standard SQL; gitignored |

Exact pinned versions live in `requirements.txt`; the `Required ≥`
column is the minimum known-working version and is the floor for any
dependency upgrade policy.

See [`docs/dev-notes/dev-setup.md`](docs/dev-notes/dev-setup.md) for
the exact `venv` create / `pip install` / `streamlit run` commands.

### 3.1 Runtime assumptions

| Assumption | Value | Notes |
|------------|-------|-------|
| Expected scale | 10²–10³ positions, 1–10 interviews each, 1–20 recommenders total | SQLite handles this comfortably; no performance tuning needed |
| File encoding | UTF-8 everywhere | `postdoc.db` is binary; all markdown exports and `config.py` are UTF-8 |
| Timezone | Local machine time | SQLite `date('now')` uses UTC by default; the app explicitly uses `datetime.date.today()` (local). For a single-user local app the user's timezone is implicit and consistent. |
| Concurrency | One writer at a time (the Streamlit process) | SQLite's default serialization is sufficient; no multi-threading / multi-process writers |
| Persistence | `postdoc.db` on local disk | Loss-protection via the committed markdown exports; cloud backup is a v2 concern (§12.5) |

---

## 4. File Structure

```
Postdoc/
│
├── app.py                    Streamlit entry point; dashboard home page
├── config.py                 Single source of truth for constants and vocabulary
├── database.py               All SQLite I/O; imports config; no Streamlit imports
├── exports.py                Markdown generators; called by database.py writers
│
├── pages/
│   ├── 1_Opportunities.py    Positions — quick-add, filter, table, edit, delete
│   ├── 2_Applications.py     Progress tracking — submission, response, interviews, outcome
│   ├── 3_Recommenders.py     Letter tracking — grouped alerts, mailto link
│   └── 4_Export.py           Manual export + file download
│
├── exports/                  Auto-generated markdown backups (COMMITTED)
│   ├── OPPORTUNITIES.md
│   ├── PROGRESS.md
│   └── RECOMMENDERS.md
│
├── postdoc.db                SQLite database (GITIGNORED — binary, personal data)
├── requirements.txt          Pinned versions (committed)
│
├── tests/                    pytest suite (committed)
├── reviews/                  Pre-merge review docs, one per tier (committed)
├── docs/                     Supplemental documentation (committed)
│   ├── adr/                  Architectural Decision Records (forward-only)
│   └── dev-notes/            Deep-dive references (git, Streamlit state)
│
├── DESIGN.md                 This file
├── GUIDELINES.md             Coding conventions (read at every session start)
├── roadmap.md                Phases, v1 ship criteria, backlog (P1/P2/P3)
├── CHANGELOG.md              Release history (Keep a Changelog format)
├── README.md                 Public entry point
├── LICENSE                   MIT
│
├── CLAUDE.md                 Internal working memory (GITIGNORED)
├── PHASE_*_GUIDELINES.md     Internal phase playbooks (GITIGNORED)
│
└── .gitignore
```

### Gitignore status

| Path | Tracked? | Reason |
|------|----------|--------|
| `postdoc.db` | ❌ | Binary; personal data |
| `.venv/` | ❌ | Local environment; platform-specific |
| `.env`, `.env.*` | ❌ | Secrets (reserved for v2 AI ingestion) |
| `__pycache__/`, `*.pyc` | ❌ | Auto-generated |
| `exports/*.md` | ✅ | **Committed** — human-readable backup of the DB |
| `CLAUDE.md` | ❌ | Internal session memory |
| `PHASE_*_GUIDELINES.md` | ❌ | Internal phase playbooks |
| All other source, tests, docs | ✅ | |

---

## 5. `config.py` — Specification

`config.py` is the **single source of truth** for vocabulary, constants,
and field definitions. Every other module reads from it; no other file
hardcodes a status string, priority value, or requirement-doc label.

### 5.1 Constants

```python
# ── Tracker profile ────────────────────────────────────────────────
# The profile discriminator for this tracker build. v1 supports "postdoc"
# only; VALID_PROFILES is both the import-time validation set and the
# extension hook for v2+ profile variants (see §12.1).
TRACKER_PROFILE: str = "postdoc"
VALID_PROFILES: set[str] = {"postdoc"}   # v2 may add "software_eng", "faculty", ...

# ── Status pipeline (ordered: index = pipeline position) ──────────
STATUS_VALUES: list[str] = [
    "[SAVED]",       # Found; saved for review; not yet applied
    "[APPLIED]",     # Application submitted
    "[INTERVIEW]",   # Interview stage reached
    "[OFFER]",       # Offer received
    "[CLOSED]",      # Deadline passed or user withdrew pre-application
    "[REJECTED]",    # Rejection received after applying
    "[DECLINED]",    # Offer turned down by applicant
]

# Named aliases for each pipeline stage. Page code references these
# rather than positional indices or literal strings — keeps the
# anti-typo guardrail in place (grep rule catches literal usage at
# merge time). All seven statuses have aliases for symmetry.
STATUS_SAVED     = STATUS_VALUES[0]   # "[SAVED]"
STATUS_APPLIED   = STATUS_VALUES[1]   # "[APPLIED]"
STATUS_INTERVIEW = STATUS_VALUES[2]   # "[INTERVIEW]"
STATUS_OFFER     = STATUS_VALUES[3]   # "[OFFER]"
STATUS_CLOSED    = STATUS_VALUES[4]   # "[CLOSED]"
STATUS_REJECTED  = STATUS_VALUES[5]   # "[REJECTED]"
STATUS_DECLINED  = STATUS_VALUES[6]   # "[DECLINED]"

# Terminal statuses — positions in these states are excluded from "active"
# queries (upcoming deadlines, materials readiness, etc.).
TERMINAL_STATUSES: list[str] = [STATUS_CLOSED, STATUS_REJECTED, STATUS_DECLINED]

# Storage-to-color map for **per-status surfaces** (status badge on the
# Opportunities table, tooltip indicators, any place where a single raw
# status value needs a color). Values are from the overlap of the
# st.badge palette and Plotly marker_color CSS-color vocabulary.
#
# Funnel bar colors come from FUNNEL_BUCKETS, not this dict — the funnel
# renders presentation buckets, not raw statuses.
STATUS_COLORS: dict[str, str] = {
    "[SAVED]":     "blue",
    "[APPLIED]":   "orange",
    "[INTERVIEW]": "violet",
    "[OFFER]":     "green",
    "[CLOSED]":    "gray",
    "[REJECTED]":  "red",
    "[DECLINED]":  "gray",
}

# Storage-to-UI-label map. Storage retains square brackets as a visual
# enum sentinel; UI strips them via this dict. Every surface that
# renders a status to a user MUST go through STATUS_LABELS — never
# print a raw key.
STATUS_LABELS: dict[str, str] = {
    "[SAVED]":     "Saved",
    "[APPLIED]":   "Applied",
    "[INTERVIEW]": "Interview",
    "[OFFER]":     "Offer",
    "[CLOSED]":    "Closed",
    "[REJECTED]":  "Rejected",
    "[DECLINED]":  "Declined",
}

# Presentation-layer groupings for the dashboard funnel.
# Each entry: (UI label, tuple of raw STATUS_VALUES contributing to this
# bar, bucket color).
#
# The chart sums counts within each bucket. Order = display order
# (top-down when the y-axis is reversed).
#
# "Archived" groups [REJECTED] + [DECLINED] — both are outcomes after
# engagement. [CLOSED] stays its own bucket because pre-application
# withdrawal is a genuinely distinct state.
#
# Bucket colors live here (not in STATUS_COLORS) because the funnel
# groups multiple raw statuses per bar; the bucket owns its color.
FUNNEL_BUCKETS: list[tuple[str, tuple[str, ...], str]] = [
    ("Saved",     ("[SAVED]",),                  "blue"),
    ("Applied",   ("[APPLIED]",),                "orange"),
    ("Interview", ("[INTERVIEW]",),              "violet"),
    ("Offer",     ("[OFFER]",),                  "green"),
    ("Closed",    ("[CLOSED]",),                 "gray"),
    ("Archived",  ("[REJECTED]", "[DECLINED]"),  "gray"),
]

# Buckets hidden by default on the dashboard funnel. Users reveal them
# all at once by clicking a single `[expand]` button rendered below the
# chart; the reveal persists via `st.session_state['_funnel_expanded']`
# for the current session only. Default-hiding terminal outcomes keeps
# the dashboard focused on active work (D24). Values must be bucket
# labels from FUNNEL_BUCKETS.
FUNNEL_DEFAULT_HIDDEN: set[str] = {"Closed", "Archived"}

# ── Position priority ─────────────────────────────────────────────
# Subjective user judgment of fit / want. User sets at add-time and
# can edit. Informs the Opportunities filter and attention-ordering.
# Distinct from **urgency** (see dashboard thresholds below): priority
# is subjective and stored; urgency is objective and computed.
PRIORITY_VALUES: list[str] = ["High", "Medium", "Low", "Stretch"]

# ── Work authorization ─────────────────────────────────────────────
# Three-value categorical answering "Does the posting accept the
# applicant's work authorization?":
#   "Yes"     — posting explicitly welcomes OPT / international applicants
#   "No"      — posting explicitly requires US citizenship or permanent residency
#   "Unknown" — posting does not say; user has not investigated yet
#
# Complementary freetext column work_auth_note (on the positions table)
# captures posting-specific detail ("green card required", "EU citizens
# preferred", "STEM OPT extension accepted"). The categorical drives
# filtering; the note preserves nuance without bloating the vocabulary.
WORK_AUTH_OPTIONS: list[str] = ["Yes", "No", "Unknown"]

# ── Full-time / part-time / contract ──────────────────────────────
FULL_TIME_OPTIONS: list[str] = ["Full-time", "Part-time", "Contract"]

# ── Where the posting was found ───────────────────────────────────
SOURCE_OPTIONS: list[str] = [
    "Lab website", "AcademicJobsOnline", "HigherEdJobs",
    "LinkedIn", "Referral", "Conference", "Listserv", "Other",
]

# ── Application response types ────────────────────────────────────
RESPONSE_TYPES: list[str] = [
    "Acknowledgement", "Screening Call", "Interview Invite",
    "Rejection", "Offer", "Other",
]

# ── Application outcome ───────────────────────────────────────────
# RESULT_DEFAULT is the applications.result DEFAULT in the schema.
# The schema DDL reads this constant via f-string, so renaming here
# propagates to the CREATE TABLE clause automatically (see §6.2).
RESULT_DEFAULT: str = "Pending"
RESULT_VALUES: list[str] = [
    RESULT_DEFAULT,
    "Offer Accepted", "Offer Declined", "Rejected", "Withdrawn",
]

# ── Recommender relationship types ────────────────────────────────
RELATIONSHIP_TYPES: list[str] = [
    "PhD Advisor", "Committee Member", "Collaborator",
    "Postdoc Supervisor", "Department Faculty", "Other",
]

# ── Interview format ──────────────────────────────────────────────
# Vocabulary for the format column on the interviews sub-table.
INTERVIEW_FORMATS: list[str] = ["Phone", "Video", "Onsite", "Other"]

# ── Requirement document types ────────────────────────────────────
# Canonical DB values for req_* columns. Order = display order on the
# Requirements tab radio ("Required" leftmost as the common case).
REQUIREMENT_VALUES: list[str] = ["Yes", "Optional", "No"]

# UI labels for each canonical value. Radios look up display text via
# format_func=REQUIREMENT_LABELS.get so session_state keeps the
# canonical DB value — no save-time translation needed.
REQUIREMENT_LABELS: dict[str, str] = {
    "Yes":      "Required",
    "Optional": "Optional",
    "No":       "Not needed",
}

# Each tuple: (db_req_column, db_done_column, display_label).
# To add a new document type (e.g., Portfolio): append one tuple here.
# database.init_db() auto-migrates the schema on next start.
REQUIREMENT_DOCS: list[tuple[str, str, str]] = [
    ("req_cv",                  "done_cv",                  "CV"),
    ("req_cover_letter",        "done_cover_letter",        "Cover Letter"),
    ("req_transcripts",         "done_transcripts",         "Transcripts"),
    ("req_research_statement",  "done_research_statement",  "Research Statement"),
    ("req_writing_sample",      "done_writing_sample",      "Writing Sample"),
    ("req_teaching_statement",  "done_teaching_statement",  "Teaching Statement"),
    ("req_diversity_statement", "done_diversity_statement", "Diversity Statement"),
]

# ── Quick-add form fields (minimal — capture at discovery) ────────
# Each string must be an exact column name on the positions table.
QUICK_ADD_FIELDS: list[str] = [
    "position_name",   # text input
    "institute",       # text input
    "field",           # text input
    "deadline_date",   # st.date_input
    "priority",        # st.selectbox from PRIORITY_VALUES
    "link",            # text input (URL)
]

# ── Opportunities edit panel ──────────────────────────────────────
# Tab labels + order for the inline edit panel on pages/1_Opportunities.py.
# To add a new tab, append the label here and extend the page's tab-body
# dispatch in pages/1_Opportunities.py.
EDIT_PANEL_TABS: list[str] = ["Overview", "Requirements", "Materials", "Notes"]

# ── Dashboard display thresholds ──────────────────────────────────
# "Urgency" is **computed** from deadline_date at query time — it is
# NOT stored. Distinct from "priority" (user's subjective fit).
# Boundaries are inclusive on the narrower band:
#   days-until-deadline ≤ DEADLINE_URGENT_DAYS → urgent  (flagged 🔴)
#   days-until-deadline ≤ DEADLINE_ALERT_DAYS  → alert   (flagged 🟡)
#   days-until-deadline >  DEADLINE_ALERT_DAYS → normal
# A deadline exactly 7 days away is urgent (not alert).
DEADLINE_ALERT_DAYS: int    = 30
DEADLINE_URGENT_DAYS: int   = 7
RECOMMENDER_ALERT_DAYS: int = 7
```

### 5.2 Import-time invariants

`config.py` executes the following assertions at module import. A
violation aborts app startup with a clear traceback — catches drift
before any page renders:

1. `TRACKER_PROFILE in VALID_PROFILES` — profile is a known value
2. `set(STATUS_VALUES) == set(STATUS_COLORS)` — every status has a per-status color
3. `set(STATUS_VALUES) == set(STATUS_LABELS)` — every status has a UI label
4. `set(TERMINAL_STATUSES) <= set(STATUS_VALUES)` — terminals are a subset
5. Let `F = [raw for (_, raws, _) in FUNNEL_BUCKETS for raw in raws]`. Require `sorted(F) == sorted(STATUS_VALUES)` (multiset equality). This asserts two facts at once: every raw status appears in some bucket, **and** no status appears in more than one bucket.
6. `FUNNEL_DEFAULT_HIDDEN <= {label for label, _, _ in FUNNEL_BUCKETS}` — the hidden-by-default set references real bucket labels
7. `set(REQUIREMENT_LABELS) == set(REQUIREMENT_VALUES)` — every req value has a label
8. `DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS` — urgency thresholds order correctly

### 5.3 Extension recipes

| Goal | What to edit |
|------|--------------|
| Add a new requirement document | Append one tuple to `REQUIREMENT_DOCS`. On next app start, `init_db()` adds `req_*` / `done_*` columns via the migration loop. No other file changes. |
| Add a priority / source / response-type / relationship / interview-format option | Append to the relevant list. Dropdowns pick it up on next render. No DB change — columns are plain TEXT. |
| Add a new pipeline status | (1) Append to `STATUS_VALUES` and add the matching `STATUS_<name>` alias; (2) add one entry each to `STATUS_COLORS` and `STATUS_LABELS`; (3) decide which `FUNNEL_BUCKETS` entry it belongs in — extend an existing bucket's tuple or add a new 3-tuple `(label, (raw,...), color)` in the right display position; (4) if terminal, append to `TERMINAL_STATUSES`. No DDL change. |
| Rename a pipeline status | Edit `STATUS_VALUES[i]`, the matching alias, and the keys in `STATUS_COLORS` / `STATUS_LABELS` / `FUNNEL_BUCKETS` / `TERMINAL_STATUSES`. Write a one-shot migration in `CHANGELOG.md` under the release: `UPDATE positions SET status = '<new>' WHERE status = '<old>'`. The schema `DEFAULT` clause is config-driven; no DDL edit needed if renaming `STATUS_VALUES[0]`. |
| Hide or un-hide a funnel bucket by default | Edit `FUNNEL_DEFAULT_HIDDEN`. Values must be existing bucket labels. |
| Change a dashboard threshold | Edit `DEADLINE_*` or `RECOMMENDER_ALERT_DAYS`. Import-time invariants catch inverted thresholds. |
| Switch the tracker profile | See §12.1. |

---

## 6. Database Schema

Canonical DDL lives in `database.init_db()`. This section is the
architectural description of that DDL.

### 6.1 Entity-Relationship summary

```
positions (1) ──< applications (1) ──< interviews (many)
positions (1) ──< recommenders (many)
```

### 6.2 Tables

```sql
PRAGMA foreign_keys = ON;

-- ── Table 1: positions ─────────────────────────────────────────
-- One row per position.
CREATE TABLE IF NOT EXISTS positions (

    -- Identity & metadata
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    status           TEXT    NOT NULL DEFAULT '[SAVED]',   -- from config.STATUS_VALUES[0]
    priority         TEXT,                                 -- from config.PRIORITY_VALUES
    created_at       TEXT    DEFAULT (date('now')),
    updated_at       TEXT    DEFAULT (datetime('now')),    -- maintained by trigger

    -- Overview
    position_name    TEXT    NOT NULL,
    institute        TEXT,
    location         TEXT,
    field            TEXT,
    deadline_date    TEXT,         -- ISO-8601 'YYYY-MM-DD' — drives all time math
    deadline_note    TEXT,         -- Freetext: "rolling after initial review"
    stipend          TEXT,
    work_auth        TEXT,         -- from config.WORK_AUTH_OPTIONS (Yes/No/Unknown)
    work_auth_note   TEXT,         -- Freetext detail (e.g., "green card required")
    full_time        TEXT,         -- from config.FULL_TIME_OPTIONS
    source           TEXT,         -- from config.SOURCE_OPTIONS
    link             TEXT,

    -- Details
    mentor           TEXT,
    point_of_contact TEXT,
    portal_url       TEXT,         -- Submission portal URL (may differ from link)
    keywords         TEXT,
    description      TEXT,
    num_rec_letters  INTEGER,
    reference_code   TEXT,
    notes            TEXT

    -- req_* TEXT DEFAULT 'No' and done_* INTEGER DEFAULT 0 pairs,
    -- one per entry in config.REQUIREMENT_DOCS, generated by init_db().
    -- Values: req_* ∈ {'Yes', 'Optional', 'No'}; done_* ∈ {0, 1}.
);

-- Trigger: keep updated_at fresh on every row mutation.
-- Relies on SQLite's default recursive_triggers = OFF — the inner
-- UPDATE fires the trigger again in principle, but is suppressed by
-- the default setting, preventing an infinite loop.
CREATE TRIGGER IF NOT EXISTS positions_updated_at
    AFTER UPDATE ON positions FOR EACH ROW
BEGIN
    UPDATE positions SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- ── Table 2: applications ──────────────────────────────────────
-- One row per position. Tracks submission, response, and outcome.
-- Automatically created when a position is added (all nullable fields NULL).
--
-- Interviews are normalized into a separate sub-table — see Table 3.
-- all_recs_submitted is NOT stored; compute from recommenders via
-- database.is_all_recs_submitted().
CREATE TABLE IF NOT EXISTS applications (
    position_id            INTEGER PRIMARY KEY,
    applied_date           TEXT,
    confirmation_received  INTEGER DEFAULT 0,     -- 0 or 1
    confirmation_date      TEXT,                   -- ISO, NULL if not yet received
    response_date          TEXT,
    response_type          TEXT,                   -- from config.RESPONSE_TYPES
    result_notify_date     TEXT,
    result                 TEXT    DEFAULT 'Pending',   -- from config.RESULT_DEFAULT
    notes                  TEXT,
    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
);

-- ── Table 3: interviews ────────────────────────────────────────
-- One row per interview slot. An application can have arbitrarily many
-- interviews (phone screen, committee, chalk talk, dean meeting, ...).
-- Replaces the earlier flat interview1_date / interview2_date columns
-- on the applications table (see D18).
CREATE TABLE IF NOT EXISTS interviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  INTEGER NOT NULL,
    sequence        INTEGER NOT NULL,        -- 1, 2, 3, ... (display order)
    scheduled_date  TEXT,                     -- ISO 'YYYY-MM-DD'
    format          TEXT,                     -- from config.INTERVIEW_FORMATS
    notes           TEXT,
    UNIQUE (application_id, sequence),
    FOREIGN KEY (application_id) REFERENCES applications(position_id) ON DELETE CASCADE
);

-- ── Table 4: recommenders ──────────────────────────────────────
-- Many rows per position; one row per (position × recommender) pair.
CREATE TABLE IF NOT EXISTS recommenders (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id         INTEGER NOT NULL,
    recommender_name    TEXT,
    relationship        TEXT,                   -- from config.RELATIONSHIP_TYPES
    asked_date          TEXT,
    confirmed           INTEGER,                -- 0, 1, or NULL (pending response)
    submitted_date      TEXT,
    reminder_sent       INTEGER DEFAULT 0,      -- 0 or 1
    reminder_sent_date  TEXT,                   -- ISO, NULL if none
    notes               TEXT,
    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
);

-- ── Indices (queried most often by dashboard / filters) ───────
CREATE INDEX IF NOT EXISTS idx_positions_status      ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_deadline    ON positions(deadline_date);
CREATE INDEX IF NOT EXISTS idx_interviews_application ON interviews(application_id);
```

**DDL DEFAULTs are config-driven.** `init_db()` constructs the `CREATE
TABLE` statements via f-strings that read `config.STATUS_VALUES[0]` and
`config.RESULT_DEFAULT`. Column names for the `req_*` / `done_*` pairs
come from `config.REQUIREMENT_DOCS`. No user-supplied value ever reaches
the DDL; `config.py` is the only string source.

### 6.3 Data migrations

`init_db()` is idempotent — safe to call on every app start. Schema
evolution happens in one of three shapes:

**Auto-migrated (handled by `init_db()` on next start):**

| Change | Mechanism |
|--------|-----------|
| New entry in `config.REQUIREMENT_DOCS` | `ALTER TABLE positions ADD COLUMN req_<x> TEXT DEFAULT 'No'` + `ADD COLUMN done_<x> INTEGER DEFAULT 0`, guarded by a `PRAGMA table_info` existence check |
| A brand-new table | `CREATE TABLE IF NOT EXISTS <name> (...)` in `init_db()` |
| A brand-new trigger or index | `CREATE TRIGGER / INDEX IF NOT EXISTS` in `init_db()` |
| New entry in any vocabulary list (`SOURCE_OPTIONS`, `RESPONSE_TYPES`, `INTERVIEW_FORMATS`, etc.) | No DDL — columns are plain TEXT; dropdowns pick up new values on next render |
| New top-level columns on an existing table when config or schema adds them | `ALTER TABLE ... ADD COLUMN` guarded by `PRAGMA table_info`, parallel to the REQUIREMENT_DOCS loop |

**Manual (requires a migration step, recorded in CHANGELOG):**

| Change | Required step |
|--------|---------------|
| Rename a status value | One-shot `UPDATE positions SET status = '<new>' WHERE status = '<old>'`. Schema DEFAULT is config-driven, so no DDL edit. |
| Rename `RESULT_DEFAULT` | One-shot `UPDATE applications SET result = '<new>' WHERE result = '<old>'`. |
| Split a dual-purpose column | (a) `ALTER TABLE ... ADD COLUMN` for the new columns; (b) one-shot `UPDATE` translating the old column's values into the new columns; (c) leave the old column NULL until a follow-up release rebuilds the table to drop it. |
| Normalize flat columns into a sub-table | (a) `CREATE TABLE` the new sub-table; (b) `INSERT INTO` copying old columns; (c) leave old columns NULL until a rebuild drops them; (d) update application code to read from the sub-table. |
| Remove a column | SQLite requires a table rebuild: `CREATE TABLE new AS SELECT <kept cols> FROM <t>; DROP TABLE <t>; ALTER TABLE new RENAME TO <t>`. Breaking change — document in CHANGELOG. |

**Migration discipline:** every schema or vocabulary change lands with a
`Migration:` note in `CHANGELOG.md` under the release that introduces
it, giving the exact `UPDATE` or rebuild SQL. A user upgrading between
releases should never have to guess which migration to run.

### 6.4 Schema design decisions

| Decision | Reason |
|----------|--------|
| Dates stored as ISO TEXT, not DATE type | SQLite has no native DATE type; ISO strings sort and compare correctly as TEXT; time math uses `datetime.date.fromisoformat` |
| Boolean-state columns as INTEGER 0/1 (never TEXT `'Y'`/`'N'`) | Type-consistent; trivial SQL predicates (`WHERE col = 1`); applies to `done_*`, `confirmation_received`, `reminder_sent`, `confirmed` (on recommenders). See D20. |
| Three-state columns as TEXT with full-word values | `req_*` stores `{"Yes", "Optional", "No"}`. Can't collapse to a boolean (three states); full words are self-descriptive in raw DB dumps; no storage penalty on TEXT. See D21. |
| Dual-concern fields split into (flag, date) column pairs | Prevents type confusion: `confirmation_received INTEGER` + `confirmation_date TEXT`, `reminder_sent INTEGER` + `reminder_sent_date TEXT`. Never one column holding either a flag or a date. See D19. |
| Summary flags that *could* be computed **are** computed, never stored | D3 applied consistently: `is_all_recs_submitted()` is a query helper, not a column — eliminates desync between recommenders and applications |
| `status` TEXT uses bracketed sentinel values (`[SAVED]`, etc.) | D16 — visual enum marker in logs/DB dumps; avoids namespace collision with plain-English words |
| `interviews` as its own sub-table (not flat columns) | Applications can have 3+ interviews (phone → committee → chalk talk → dean); flat columns cap at an unrealistic limit. See D18. |
| `work_auth` is a three-value categorical + freetext `work_auth_note` | Keeps filter dropdowns simple while preserving posting-specific nuance. See D23. |
| Separate `applications` table (not merged into `positions`) | D9 — different update cadence + concern |
| `ON DELETE CASCADE` on all child tables | D8 — one delete cleans positions + applications + interviews + recommenders atomically |
| Auto-create `applications` row on `add_position()` | D10 — every position has a matching row; no NULL-check overhead in joins |
| `updated_at` on `positions` maintained by an `AFTER UPDATE` trigger | Enables "recently touched" sorts + stale-position detection without each writer having to remember to set it. See D25. |

---

## 7. Module Contracts

This section describes **what each module does and how to reach it**. Full
function signatures (parameters, return types, detailed docstrings) live
in the source as docstrings — they are the single source of implementation
truth. DESIGN.md specifies the **roles, calling conventions, and
load-bearing invariants** that cross module boundaries.

### `database.py`

**Role.** All SQLite I/O. No Streamlit imports; no display logic.
Reads and writes the SQLite database file only — other filesystem I/O
belongs in `exports.py`. Readers return pandas DataFrames for
multi-row queries and plain dicts for single-row lookups. Writers
return the new row id (inserts) or `None` (updates, deletes).

**Public API (grouped by concern):**

| Group | Functions |
|-------|-----------|
| Schema lifecycle | `init_db` |
| Positions | `add_position`, `get_all_positions`, `get_position`, `update_position`, `delete_position` |
| Applications | `get_application`, `upsert_application`, `is_all_recs_submitted` |
| Interviews | `add_interview`, `get_interviews`, `update_interview`, `delete_interview` |
| Recommenders | `add_recommender`, `get_recommenders`, `get_all_recommenders`, `update_recommender`, `delete_recommender` |
| Dashboard queries | `count_by_status`, `get_upcoming_deadlines`, `get_upcoming_interviews`, `get_pending_recommenders`, `compute_materials_readiness` |

**Load-bearing contracts:**

1. **Exports after writes.** Every public write function calls
   `exports.write_all()` as its last step, inside a try/except that
   logs errors but does not re-raise. A write that succeeded in the DB
   always reports success to its caller, even if markdown regeneration
   failed. The import of `exports` inside each writer is deferred (not
   at module top) to break the circular import.

2. **Pipeline auto-promotion.** Two writers can promote
   `positions.status` as a side effect — `upsert_application` and
   `add_interview`. Both accept a keyword argument
   `propagate_status: bool = True`; when False, no pipeline side-effect
   fires. The promotion rules R1/R2/R3 are documented in §9.3 and run
   atomically inside the same transaction as the primary write.

3. **Idempotent init.** `init_db()` runs on every app start. It creates
   tables, triggers, and indices with `IF NOT EXISTS`; it runs the
   `REQUIREMENT_DOCS`-driven `ALTER TABLE ADD COLUMN` loop; it re-checks
   all invariants. Safe to call any number of times.

4. **Sparse-dict returns.** Aggregation queries (`count_by_status`,
   others) may omit zero-count keys. Callers fill missing keys with 0
   before display.

5. **Sort orders are part of the contract.** `get_all_positions` returns
   rows ordered by `deadline_date ASC NULLS LAST`; `get_upcoming_*`
   queries return chronological order; `get_all_recommenders` orders
   by `recommender_name`. Tests and pages rely on these orderings.

### `exports.py`

**Role.** Generate the three markdown backup files. Imports `database`
and `config`; never imports Streamlit. Called only by `database.py`
writers (via deferred import) and by the Export page's manual-trigger
button.

**Public API:**

| Function | What it writes |
|----------|----------------|
| `write_all` | All three files below (calls the individual writers) |
| `write_opportunities` | `exports/OPPORTUNITIES.md` from the positions table |
| `write_progress` | `exports/PROGRESS.md` from positions JOIN applications JOIN interviews |
| `write_recommenders` | `exports/RECOMMENDERS.md` from recommenders JOIN positions |

**Load-bearing contracts:**

1. **Log-and-continue on failure.** Errors inside `write_all` are logged
   but never propagate past its boundary. The DB write that triggered
   the export has already succeeded, and the user should see "Saved"
   — not a traceback. The Export page surfaces file mtimes so stale
   backups become visible.

2. **Stable markdown format.** Export formats are committed into
   version control; changes to the output format are documented in
   CHANGELOG alongside any change in the generator.

---

## 8. UI Design — Page by Page

### 8.0 Cross-page conventions

These conventions apply to every page.

#### Page configuration

Every page's first executable Streamlit call is:

```python
st.set_page_config(
    page_title="Postdoc Tracker",
    page_icon="📋",
    layout="wide",
)
```

`layout="wide"` is essential: the app is data-heavy (tables, KPI grids,
funnel chart, timeline). `set_page_config` runs at the top of `app.py`
and every `pages/*.py` — it is re-executed on every page switch.

#### Widget-key prefix conventions

Widget keys follow a scope prefix so tests can pin them reliably across
reruns:

| Scope | Prefix | Example |
|-------|--------|---------|
| Quick-add form | `qa_` | `qa_position_name`, `qa_deadline_date` |
| Edit panel (row-scoped) | `edit_` | `edit_position_name`, `edit_notes` |
| Filter bar | `filter_` | `filter_status`, `filter_field` |
| Internal sentinels | `_` prefix | `_edit_form_sid`, etc. |
| Form ids | suffix `_form` | `edit_notes_form` (contains `edit_notes`) |

**Form ids MUST NOT collide with any widget key inside the form.**
Streamlit registers form ids with `writes_allowed=False`; a collision
raises `StreamlitValueAssignmentNotAllowedError` at render. Suffixing
form ids with `_form` is the project convention.

#### Status label convention

Pages **never render a raw status value** (e.g. `[SAVED]`) to the user.
Storage uses bracketed values for enum-sentinel clarity; display uses
`config.STATUS_LABELS[raw]` (e.g. `"Saved"`). Streamlit selectboxes use
`format_func=config.STATUS_LABELS.get` to show labels while storing raw
values.

#### Confirmation & error patterns

| Event | Pattern |
|-------|---------|
| Successful write | `st.toast(f'Saved "{name}".')` — persists across `st.rerun()` |
| Write failure | `st.error(f"Could not save: {e}")` — no re-raise; no traceback leaks to the user |
| Irreversible action | `@st.dialog` confirm with Confirm + Cancel buttons; explicit copy mentioning cascade effects |
| Cross-page navigation | `st.switch_page("pages/<N_Title>.py")` |

---

### 8.1 `app.py` — Dashboard (Home)

**Purpose:** Answer "What do I do today?" in one glance.

```
╔════════════════════════════════════════════════════════════════╗
║  Postdoc Tracker                                               ║
╠══════════════╦══════════════╦══════════════╦═══════════════════╣
║  12          ║  4           ║  2           ║  May 3 · MIT      ║
║  Tracked ⓘ  ║  Applied     ║  Interview   ║  Next Interview   ║
║              ║              ║              ║                   ║
╠══════════════╩══════════════╩══════════════╩═══════════════════╣
║                             ║                                  ║
║  Application Funnel         ║   Materials Readiness            ║
║                             ║                                  ║
║  Saved       ████████  8    ║                                  ║
║  Applied     ██████    4    ║  Ready to submit:  3             ║
║  Interview   ████      2    ║  ███                             ║
║  Offer       ██        1    ║                                  ║
║  [expand]                   ║  Still missing:    5             ║
║                             ║  █████                           ║
║                             ║                                  ║
║                             ║  [→ Opportunities page]          ║
║                             ║                                  ║
╠═════════════════════════════╩══════════════════════════════════╣
║  Upcoming (next 30 days)                                       ║
║                                                                ║
║  Apr 24  Stanford BioStats   Saved      deadline    9d  🔴     ║
║  May 3   Stanford BioStats   Applied    Interview  18d         ║
║  May 15  MIT CSAIL           Saved      deadline   30d         ║
║                                                                ║
╠════════════════════════════════════════════════════════════════╣
║  Recommender Alerts                                            ║
║                                                                ║
║  ⚠  Dr. Smith  →  Stanford, MIT CSAIL  (asked 14 days ago)     ║
║  ✓  Dr. Jones  →  Stanford             (submitted Apr 20)      ║
╚════════════════════════════════════════════════════════════════╝
```

**Panel specifications:**

| Panel | Data source | Labels | Warn/flag trigger |
|-------|------------|--------|-------------------|
| KPI: Tracked | `count_by_status()` summed over `STATUS_SAVED + STATUS_APPLIED` | `st.metric(..., help="Saved + Applied — positions you're still actively pursuing")` | — |
| KPI: Applied | `count_by_status().get(STATUS_APPLIED, 0)` | — | — |
| KPI: Interview | `count_by_status().get(STATUS_INTERVIEW, 0)` | — | — |
| KPI: Next Interview | `get_upcoming_interviews()` scanned for earliest FUTURE `scheduled_date`; rendered `'{Mon D} · {institute}'`; "—" when none | — | — |
| Funnel | `count_by_status()` summed into `FUNNEL_BUCKETS`; Plotly horizontal `go.Bar`, one bar per **visible** bucket in list order; a visible bucket with zero count renders as a zero-width bar (category preserved for axis stability); y-axis reversed so earliest pipeline stage sits on top; bar color comes from `FUNNEL_BUCKETS[i][2]` | Bucket labels = `FUNNEL_BUCKETS[i][0]` (UI, no brackets) | — |
| Funnel `[expand]` button | Single button rendered below the chart whenever `FUNNEL_DEFAULT_HIDDEN` is non-empty; clicking flips the session flag `st.session_state["_funnel_expanded"]` to `True`, which promotes every bucket in `FUNNEL_DEFAULT_HIDDEN` (currently Closed + Archived) to visible for the rest of the session. Replaces the earlier per-bucket checkbox model (one click reveals all hidden buckets at once). | Button label: `"[expand]"` | — |
| Materials Readiness | `compute_materials_readiness()` → two stacked `st.progress` bars labelled `"Ready to submit: N"` / `"Still missing: M"`; values = count / `max(ready + pending, 1)`; CTA button `"→ Opportunities page"` via `st.switch_page` | — | Empty state when `ready + pending == 0` |
| Upcoming | Merge of `get_upcoming_deadlines()` + `get_upcoming_interviews()` by date; `st.dataframe(width="stretch")`, columns (Date, Label, Kind, Urgency); Status shown via `STATUS_LABELS[raw]`; Kind ∈ {"deadline", "interview"} | — | 🔴 when days-away ≤ `DEADLINE_URGENT_DAYS`; 🟡 when ≤ `DEADLINE_ALERT_DAYS` |
| Recommender Alerts | `get_pending_recommenders(RECOMMENDER_ALERT_DAYS)` grouped by `recommender_name` — one card per person with all their owed positions listed | — | All shown rows are warnings |

**Funnel visibility rules.** The funnel renders buckets in the order
listed in `FUNNEL_BUCKETS`. A bucket is visible when **not** in
`FUNNEL_DEFAULT_HIDDEN`, or when the user has clicked `[expand]` in
the current session (flipping `st.session_state["_funnel_expanded"]`
to `True` reveals every `FUNNEL_DEFAULT_HIDDEN` bucket at once).
Hiding the terminal buckets by default keeps the dashboard focused on
active work (D24).

**Empty-DB hero.** When

```python
count_by_status().get(STATUS_SAVED, 0)
+ count_by_status().get(STATUS_APPLIED, 0)
+ count_by_status().get(STATUS_INTERVIEW, 0) == 0
```

a bordered hero container above the KPI grid shows a welcome subheader,
an explanatory paragraph, and a primary CTA button that
`st.switch_page("pages/1_Opportunities.py")`. The KPI grid renders
beneath the hero regardless. A DB holding only terminal-status rows
still triggers the hero — nothing actionable remains on the dashboard.

**Empty-state branches** (each panel, when its relevant data is empty):

| Panel | Empty-state behaviour |
|-------|-----------------------|
| Funnel | **Three branches, evaluated in order.** (a) *No data anywhere* — `sum(count_by_status().values()) == 0`: show `st.info("Application funnel will appear once you've added positions.")` and suppress the `[expand]` button (nothing to expand into). (b) *No visible data* — total is non-zero but every non-zero bucket lies in `FUNNEL_DEFAULT_HIDDEN` and `st.session_state["_funnel_expanded"]` is `False`: show `st.info("All your positions are in hidden buckets. Click [expand] below to reveal them.")` and render the `[expand]` button directly under the info. (c) *Otherwise* render the chart; the `[expand]` button renders below the chart whenever `FUNNEL_DEFAULT_HIDDEN` is non-empty and not yet expanded. Subheader renders in all three branches for page-height stability. Rationale: without branch (b), a user returning mid-cycle with only archived / closed applications would see a subheader above a chart of zero-width bars — a broken-looking state. Branch (b) explains what's happening and points at the recovery path (the `[expand]` button). |
| Materials Readiness | If `ready + pending == 0`, show `st.info("Materials readiness will appear once you've added positions with required documents.")`. Subheader renders in both branches. |
| Upcoming | If merged DataFrame is empty, show `st.info("No deadlines or interviews in the next {DEADLINE_ALERT_DAYS} days.")`. |
| Recommender Alerts | If `get_pending_recommenders()` returns empty, show `st.info("No pending recommender follow-ups.")`. |

---

### 8.2 `pages/1_Opportunities.py` — Positions

**Purpose:** Capture and manage all positions.

```
╔════════════════════════════════════════════════════════════════╗
║  Opportunities                                                 ║
║                                                                ║
║  ▼ Quick Add  ──────────────────────────────────────────────  ║
║  │ Position Name*  │ Institute  │ Field  │ Deadline  │Priority║
║  │ ______________ │ __________ │ ______ │ 📅 date   │ High ▼ ║
║  │ Link: ___________________________ [ + Add Position ]       ║
║  └─────────────────────────────────────────────────────────── ║
║                                                                ║
║  Filter: Status [All ▼]  Priority [All ▼]  Field [________]   ║
║                                                                ║
║  Position Name        Institute  Priority   Status    Due      ║
║  ────────────────────────────────────────────────────────────  ║
║  Stanford BioStats    Stanford   🟡 High   Applied   ——        ║
║  MIT CSAIL Postdoc    MIT        🟡 High   Saved     May 15    ║
║  ··· (click row to expand) ···                                 ║
║                                                                ║
║  ┌──── Stanford BioStats Postdoc  ·  Applied  ─────────────┐   ║
║  │  [ Overview ] [ Requirements ] [ Materials ] [ Notes ]   │  ║
║  │  ─────────────────────────────────────────────────────── │  ║
║  │  (tab content — full edit form fields)                   │  ║
║  │  [ Save Changes ]                                        │  ║
║  └──────────────────────────────────────────────────────────┘  ║ 
║  [ Delete ]                                                    ║  
╚════════════════════════════════════════════════════════════════╝
```

**Behaviour:**

| Element | Behaviour |
|---------|-----------|
| Quick-add | Exactly the fields listed in `config.QUICK_ADD_FIELDS`; saves with `status = config.STATUS_VALUES[0]`; auto-creates `applications` row. Whitespace-only `position_name` rejected with `st.error`; success → `st.toast`. |
| Filter: Status | `st.selectbox(["All"] + STATUS_VALUES, format_func=STATUS_LABELS.get)` — UI shows labels; filter compares raw values |
| Filter: Priority | `st.selectbox(["All"] + PRIORITY_VALUES)` |
| Filter: Field | `st.text_input`; substring match via `df["field"].str.contains(..., case=False, na=False, regex=False)` — literal match so `"C++"` doesn't crash pandas |
| Table | `st.dataframe(width="stretch", on_select="rerun", selection_mode="single-row")`; sorted by `deadline_date ASC NULLS LAST`; Status column displays `STATUS_LABELS[raw]`; Due column carries an urgency badge driven by the DEADLINE thresholds |
| Row click | Selects row; edit panel renders beneath using the **unfiltered** `df` for lookup (so narrowing the filter never dismisses an in-progress edit) |
| Overview tab | Pre-filled edit widgets for all overview columns; Status selectbox uses `format_func` convention; `work_auth` uses `WORK_AUTH_OPTIONS` selectbox + `work_auth_note` text_area below it |
| Requirements tab | One `st.radio` per `REQUIREMENT_DOCS` entry; options = `REQUIREMENT_VALUES`; `format_func=REQUIREMENT_LABELS.get`; Save writes only `req_*` keys so `done_*` survives flips between states |
| Materials tab | Live-filtered: only docs with `session_state[f"edit_{req_col}"] == "Yes"` render a checkbox; Save writes only `done_*` for visible docs (hidden `done_*` preserved) |
| Notes tab | Single `st.text_area` inside `st.form("edit_notes_form")`; empty input persists as `""` not `NULL` |
| Delete | Button rendered **below the edit panel** (outside the panel box), **visible only when the active tab is Overview**. Clicking opens an `@st.dialog` confirmation (outside `st.form`); on Confirm, `delete_position(id)` runs and the FK cascade removes the position's `applications`, `interviews`, and `recommenders` rows atomically. The button's scope is the whole position, not the active tab's data — hence the Overview-only placement, matching the tab where the user is reviewing the position as a whole. |

**Selection-survival invariant.** Save on any tab, filter change that
still includes the selected row, and dialog-Cancel must all preserve
`selected_position_id`. Implementation hides the state-management
details from users.

---

### 8.3 `pages/2_Applications.py` — Progress

**Purpose:** Track every position from submission to outcome, including
the full interview sequence.

```
╔════════════════════════════════════════════════════════════════╗
║  Applications                                                  ║
║                                                                ║
║  Filter: Status [Applied+ ▼]   Sort: [Deadline ▼]             ║
║                                                                ║
║  Position           Applied    Recs  Conf.  Response  Result   ║
║  ──────────────────────────────────────────────────────────── ║
║  Stanford BioStats  Apr 18     ✓     ✓      Interview  Pending ║
║  MIT CSAIL          ——         ——    ——      ——         ——      ║
║                                                                ║
║  ┌──── Stanford BioStats Postdoc ──────────────────────────┐  ║
║  │  Applied: Apr 18       All recs submitted: ✓            │  ║
║  │  Confirmation: ✓  (received Apr 19)                     │  ║
║  │  Response type: Interview Invite ▼  Date: Apr 22        │  ║
║  │  ──────  Interviews  ──────                             │  ║
║  │  1.  📅 May 3    Video    (notes)         [ Edit ]      │  ║
║  │  2.  📅 May 17   Onsite   (notes)         [ Edit ]      │  ║
║  │  [ + Add another interview ]                            │  ║
║  │  ──────                                                  │  ║
║  │  Result notify date: 📅 ——  Result: Pending ▼           │  ║
║  │  Notes: ___________________________________  [ Save ]   │  ║
║  └──────────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════════╝
```

**Behaviour:**
- **Default filter** excludes positions with status `[SAVED]` or `[CLOSED]` — they are pre-application or withdrawn and have no application data worth showing.
- **"All recs submitted"** column is a live computation via `database.is_all_recs_submitted(position_id)`; no stored summary.
- **"Confirmation"** column reads `confirmation_received` (flag) and displays its `confirmation_date` (if set) as a tooltip.
- **Interviews** are edited as a list: one row per `interviews` record, ordered by `sequence`. Each row has `scheduled_date`, `format`, `notes`. Add appends a new interview with the next `sequence`. Delete removes one row (FK from `applications`).
- **Pipeline promotions** fire inside `database.upsert_application(propagate_status=True)` and `database.add_interview(propagate_status=True)` — see §9.3. The page does NOT detect transitions; it just calls the writer and reads the returned promotion indicator to surface a `st.toast`.
- **Status selectbox** (read-only here; this page edits applications, not the pipeline) shows `STATUS_LABELS[raw]`.

---

### 8.4 `pages/3_Recommenders.py` — Recommenders

**Purpose:** Track every letter across every position; surface who needs a reminder.

```
╔════════════════════════════════════════════════════════════════╗
║  Recommenders                                                  ║
║                                                                ║
║  ── Pending Alerts ─────────────────────────────────────────  ║
║  ⚠  Dr. Smith  (PhD Advisor)  ·  asked 14 days ago            ║
║     → Stanford BioStats (due May 1)                           ║
║     → MIT CSAIL Postdoc (due May 15)                          ║
║     [ Compose reminder email ]                                 ║
║                                                                ║
║  ── All Recommenders ───────────────────────────────────────  ║
║  Filter by position: [All ▼]   Filter by recommender: [All ▼] ║
║                                                                ║
║  Position         Recommender   Asked    Confirmed  Submitted  ║
║  ──────────────────────────────────────────────────────────── ║
║  Stanford Bio     Dr. Smith     Apr 10   ✓          ——         ║
║  Stanford Bio     Dr. Jones     Apr 10   ✓          Apr 20 ✓   ║
║  MIT CSAIL        Dr. Smith     Apr 12   ✓          ——         ║
║                                                                ║
║  [ + Add recommender for position ▼ ]                         ║
╚════════════════════════════════════════════════════════════════╝
```

**Behaviour:**
- **Alert panel grouping:** `get_pending_recommenders()` returns one row per (recommender × position); the page groups by `recommender_name` so one recommender who owes N letters appears as a single card listing all N positions.
- **Compose reminder email:** opens a `mailto:` URL with subject pre-filled (e.g. "Following up: letters for N postdoc applications") and body listing the position names + deadlines. No outbound email integration — the OS hands off to the user's mail client.
- **Add-recommender form:** position dropdown shows `position_name` + institute; IDs never surface to the user.
- **Inline edit** for each row: `asked_date`, `confirmed` (0/1/NULL), `submitted_date`, `reminder_sent` + `reminder_sent_date`, `notes`.

---

### 8.5 `pages/4_Export.py` — Export

**Purpose:** Manual export trigger and file download.

```
╔════════════════════════════════════════════════════════════════╗
║  Export                                                        ║
║                                                                ║
║  Markdown files are auto-exported after every data change.     ║
║  Use this page to trigger a manual export or download files.   ║
║                                                                ║
║  [ Regenerate all markdown files ]                             ║
║                                                                ║
║  ── Download ───────────────────────────────────────────────  ║
║  [ ⬇ OPPORTUNITIES.md ]   Last generated: <file mtime>         ║
║  [ ⬇ PROGRESS.md ]        Last generated: <file mtime>         ║
║  [ ⬇ RECOMMENDERS.md ]    Last generated: <file mtime>         ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 9. Cross-page Data Flows

### 9.1 Adding a new position (quick-add path)

```
User fills 6 fields → st.form_submit_button
  → database.add_position(fields)
      → INSERT INTO positions (... status = config.STATUS_VALUES[0] ...)
      → INSERT INTO applications (position_id, default columns)
      → exports.write_all()          (log-and-continue on failure)
  → st.toast("Added ...")
  → st.rerun()
  → table refreshes with the new row
```

### 9.2 Dashboard load

```
app.py runs (fresh or on rerun)
  → st.set_page_config(layout="wide", ...)
  → database.init_db()   (idempotent; ALTER loops run if config grew)
  → database.count_by_status()             → KPI math + Funnel (via FUNNEL_BUCKETS)
  → database.compute_materials_readiness() → Readiness panel
  → database.get_upcoming_deadlines()   ┐
  → database.get_upcoming_interviews()  ├→ merge by date → Upcoming panel
  → database.get_pending_recommenders() → Alerts panel (grouped by recommender)
```

### 9.3 Pipeline auto-promotion

**The cascade is fully owned by `database.py`. Pages are display-only
(D12).**

Two writers can promote `positions.status` as a side effect — both
accept a keyword argument `propagate_status: bool = True`; when False,
no pipeline promotion fires.

| # | Trigger (in which writer) | Condition | Cascade |
|---|--------------------------|-----------|---------|
| R1 | `upsert_application` | `applied_date` transitions from NULL to non-NULL | `UPDATE positions SET status = '[APPLIED]' WHERE id = ? AND status = '[SAVED]'` |
| R2 | `add_interview` | Any successful interview insert | `UPDATE positions SET status = '[INTERVIEW]' WHERE id = ? AND status = '[APPLIED]'` |
| R3 | `upsert_application` | `response_type` transitions to `"Offer"` | `UPDATE positions SET status = '[OFFER]' WHERE id = ? AND status NOT IN (<TERMINAL_STATUSES>)` |

**R1 and R2 are idempotent by construction** — the `AND status = '<prev>'`
guard makes the cascade a no-op when the position is already at or past
the target stage. R2 does **not** inspect the interview count: the
status guard alone delivers the correct semantics (first interview on an
`[APPLIED]` position promotes; subsequent interviews on an `[INTERVIEW]`
position are no-ops; a position at `[OFFER]` or terminal is not
regressed). An earlier draft of R2 counted interviews ("exactly one
after insert") but that over-restricts: if the user back-edits status to
`[APPLIED]` while retaining existing interviews, adding another
interview would fail to promote. The count-free form avoids this.

**R3 overrides non-terminal stages but guards against terminals.**
Receiving an Offer while at `[SAVED]`, `[APPLIED]`, or `[INTERVIEW]`
lands the position at `[OFFER]` directly. A position already in a
terminal stage (`[CLOSED]`, `[REJECTED]`, `[DECLINED]`) is **not**
silently regressed — the user must first move the status out of the
terminal bucket, and then the next `upsert_application` with
`response_type = "Offer"` will promote. This prevents a stray edit, data
import, or misread response from clobbering a terminal decision.

If R1 and R3 fire from the same `upsert_application` call, the combined
effect depends on the pre-state. The per-state behaviour is:

| Pre-state | R1 fires? | R3 fires? | Post-state |
|-----------|-----------|-----------|------------|
| `[SAVED]` | Yes (→ `[APPLIED]`) | Yes (→ `[OFFER]`) | `[OFFER]` |
| `[APPLIED]` | No | Yes (→ `[OFFER]`) | `[OFFER]` |
| `[INTERVIEW]` | No | Yes (→ `[OFFER]`) | `[OFFER]` |
| `[OFFER]` | No | Yes (no-op, already there) | `[OFFER]` |
| `[CLOSED]` / `[REJECTED]` / `[DECLINED]` | No | No (terminal guard) | unchanged |

All cascades execute inside the same transaction as the primary write,
so a failure rolls the whole call back.

Each writer that can promote returns an indicator
`{"status_changed": bool, "new_status": str | None}` so callers can
surface a toast when a promotion fires.

Callers opt out with `propagate_status=False` for edits that should
not move the pipeline (e.g. correcting a typo in application notes).
The Applications page always calls with the default; Recommenders and
the quick-add path never touch these functions.

**Rationale for locating the cascade in `database.py`:**
- Atomicity — a failed propagation rolls back the primary write too
- Testable without an AppTest harness (pure database + config)
- Keeps pages display-only per GUIDELINES §2
- Uniform firing whether the caller is a page, a CLI, an exporter, or a future background job

### 9.4 Deleting a position

```
User clicks Delete on Overview tab
  → @st.dialog opens with the position's name + cascade warning
  → User clicks Confirm
      → database.delete_position(id)
          → DELETE FROM positions WHERE id = ?
             (applications + interviews + recommenders cascade via
              ON DELETE CASCADE)
          → exports.write_all()
      → st.toast("Deleted ...")
      → session-state cleanup (selected row + dialog pending flags)
      → st.rerun() → edit panel collapses
```

Cancel preserves the current edit context (selected row and its tab
state) so the user returns where they were.

### 9.5 Export pipeline

```
Any database.py writer ends with:
  → exports.write_all()
      → write_opportunities()  → exports/OPPORTUNITIES.md
      → write_progress()       → exports/PROGRESS.md
      → write_recommenders()   → exports/RECOMMENDERS.md
```

A failure in any `write_*` is caught at the `write_all` boundary,
logged, and swallowed — the DB write has already succeeded, so the
user should see "Saved", not a traceback. The Export page surfaces the
file mtimes so a user notices if backups stop regenerating.

---

## 10. Key Architectural Decisions

The v1 design rests on these choices. Alternatives considered briefly
in each row.

| ID | Decision | Rationale | Alternative rejected |
|----|----------|-----------|----------------------|
| D1 | All field/vocab definitions in `config.py` | Open/Closed Principle — extend by editing one file | Hardcoded in page files — fails on generalization |
| D2 | `deadline_date` is ISO text, separate from `deadline_note` | Time computations need a real date; context note is a separate concern | Single freetext field — cannot compute "X days away" |
| D3 | `done_*` columns are `INTEGER 0/1`; readiness is computed | Avoids stale summary fields; single source of truth | Stored `materials_ready` — desynchronizes |
| D4 | `exports.write_all()` called inside every `database.py` writer | Markdown always current; no manual sync step | On-demand export only — backup lags after every write |
| D5 | Internal IDs; UI shows `position_name + institute` | Users never see or manage database IDs | User-managed codes (P001) — error-prone, sync burden |
| D6 | Quick-add captures minimal essentials (see `config.QUICK_ADD_FIELDS`) | Capture must cost < 30 seconds; enrichment later | Full form on add — positions get lost at discovery time |
| D7 | Status via `st.selectbox(STATUS_VALUES, format_func=STATUS_LABELS.get)` | Prevents typo corruption; UI label decoupled from storage | Freetext — undetectable corruption |
| D8 | `ON DELETE CASCADE` on all child tables | One delete cleans every dependent row atomically | Manual multi-table delete — easy to orphan rows |
| D9 | Separate `applications` table | Different update cadence + concern from positions | Single wide table — harder to query, harder to reason about |
| D10 | Auto-create `applications` row on `add_position()` | Every position always has a matching row | Create on first update — requires NULL handling everywhere |
| D11 | Presentation/storage split via `STATUS_LABELS` + `FUNNEL_BUCKETS` | Cheap UI renames (no schema migration); presentation grouping is reversible at-will | Rename storage values — requires DB migration for every naming tweak |
| D12 | Cross-table cascade lives in `database.py` writers | Atomic, testable, pages stay display-only | Page-level detect-and-prompt — leaks business logic into UI; loses atomicity |
| D13 | No 🔄 Refresh button on the dashboard top bar | Streamlit reruns on any interaction; single-user local app rarely has cross-tab writes | Manual refresh button — cognitive noise for the common case |
| D14 | `st.set_page_config(layout="wide", ...)` on every page | Data-heavy views need horizontal room | Default centered layout — ~750px cramps every page |
| D15 | `TRACKER_PROFILE` validated at import time against `VALID_PROFILES` | Cheap forward-compat hook for v2 profile variants; catches typos now | Hardcode `"postdoc"` — no v2 extension point |
| D16 | Bracketed status storage values + bracket-stripped UI labels | Visual enum sentinel in logs/DB; `STATUS_LABELS` delivers clean UI | Raw labels in storage — harder to grep; conflicts with freetext "Saved" elsewhere |
| D17 | Archived = `[REJECTED]` + `[DECLINED]` on the dashboard funnel only; `[CLOSED]` stays its own bar | Rejection + declined-offer are both outcomes after engagement; CLOSED is pre-engagement withdrawal — a genuinely different state | Group all three terminals — loses semantic distinction |
| D18 | `interviews` sub-table instead of flat `interview1_date`/`interview2_date` columns | Real applications have 3+ interviews (phone → committee → chalk talk → dean); a flat cap is an arbitrary cliff | Flat columns — capped the data model at an unrealistic limit |
| D19 | Dual-concern columns split into `(flag, date)` pairs | Type-consistent; predicates are simple; no column holds either a flag or a date | Single TEXT column storing `'Y'` or a date string — type-ambiguous, hard to query |
| D20 | Boolean-state columns as `INTEGER 0/1` (never TEXT `'Y'`/`'N'`) | Consistent, grep-friendly, trivial SQL predicates | TEXT `'Y'`/`'N'` — mixes with `req_*`'s three-state TEXT and confuses readers |
| D21 | Three-state requirement columns use full words `"Yes"`/`"Optional"`/`"No"` | Consistent with D20's full-word philosophy; self-descriptive in raw dumps; no storage penalty on TEXT | `"Y"`/`"Optional"`/`"N"` — mixed length, inconsistent, harder to read |
| D22 | `work_auth` three-value categorical + `work_auth_note` freetext | Categorical keeps filters simple; freetext preserves posting-specific nuance (e.g. "green card only") | Many-value enum — unused detail; or freetext only — not filterable |
| D23 | Summary flags that could be computed **are** computed, never stored | D3 applied consistently — `is_all_recs_submitted()` is a query helper, not a column | Store `all_recs_submitted` — desynchronizes with the recommenders table |
| D24 | Terminal funnel buckets default-hidden, user opts in | Dashboard focuses on active work; rejection/close counts are available on-demand, not in the face of a user who doesn't want them there | Always show all buckets — demoralizing and noisy |
| D25 | `positions.updated_at` maintained by an `AFTER UPDATE` trigger | Every write touches the timestamp without requiring each writer to remember it | Explicit update in each writer — easy to forget on the next writer added |

---

## 11. Extension Guide

### Add a new requirement document
1. Open `config.py`.
2. Append one tuple to `REQUIREMENT_DOCS`:
   ```python
   ("req_portfolio", "done_portfolio", "Portfolio"),
   ```
3. Restart the app. `init_db()` adds the two columns via `ALTER TABLE`.
4. The Requirements tab, Materials tab, materials readiness query, and markdown export pick it up without further code changes.

### Add a new vocabulary option
1. Append to the relevant list (`WORK_AUTH_OPTIONS`, `SOURCE_OPTIONS`, `RESPONSE_TYPES`, `RESULT_VALUES`, `RELATIONSHIP_TYPES`, `INTERVIEW_FORMATS`, etc.).
2. Selectboxes pick the new value up on next render.
3. No DB change — column is plain TEXT.

### Add a new pipeline status
1. Append to `STATUS_VALUES` and add the matching `STATUS_<name>` alias.
2. Add one entry each to `STATUS_COLORS` and `STATUS_LABELS`.
3. Decide which `FUNNEL_BUCKETS` entry it belongs in — extend an existing bucket's tuple or add a new `(label, (raw,...), color)` 3-tuple in the right display position.
4. If the new status should be hidden by default on the funnel, add its bucket label to `FUNNEL_DEFAULT_HIDDEN`.
5. If terminal (no downstream pipeline stage), append to `TERMINAL_STATUSES`.
6. No DB change; status column is TEXT.

### Rename a pipeline status
1. Edit `STATUS_VALUES[i]`, the matching `STATUS_<name>` alias, and the keys in `STATUS_COLORS` / `STATUS_LABELS` / `FUNNEL_BUCKETS` / `TERMINAL_STATUSES`.
2. Write a `Migration:` note in `CHANGELOG.md` with the one-shot SQL:
   ```sql
   UPDATE positions SET status = '<new>' WHERE status = '<old>';
   ```
3. Schema DDL is config-driven (`DEFAULT` reads `config.STATUS_VALUES[0]`), so renaming the first status value propagates without DDL edits.

### Add a new interview format
1. Append to `INTERVIEW_FORMATS`.
2. The Applications page's interview-row dropdown picks it up on next render.

### Switch the tracker profile
See §12.1. v1 supports `"postdoc"` only; the hook to add another is in place but not wired.

### Change a dashboard threshold
Edit `DEADLINE_ALERT_DAYS` / `DEADLINE_URGENT_DAYS` / `RECOMMENDER_ALERT_DAYS` in `config.py`. The import-time invariants catch inverted thresholds on next import.

---

## 12. v2 Design Notes

These are architectural ideas for post-v1 releases. They inform v1
decisions (e.g. keeping `TRACKER_PROFILE` + `VALID_PROFILES` as hooks)
but are not implemented in v1.

### 12.1 General job tracker — profile expansion

The tracker is designed so reskinning to a different job context
requires **editing `config.py` only**. v1 keeps
`VALID_PROFILES = {"postdoc"}`.

A v2 multi-profile expansion:

1. Extend `VALID_PROFILES` to include `"software_eng"`, `"faculty"`, etc.
2. Profile-specific vocabularies are keyed by profile:
   ```python
   PROFILE_REQUIREMENT_DOCS = {
       "postdoc": [...],         # current REQUIREMENT_DOCS
       "software_eng": [
           ("req_cv",               "done_cv",               "CV / Resume"),
           ("req_coding_challenge", "done_coding_challenge", "Coding Challenge"),
           ("req_cover_letter",     "done_cover_letter",     "Cover Letter"),
       ],
       # ...
   }
   REQUIREMENT_DOCS = PROFILE_REQUIREMENT_DOCS[TRACKER_PROFILE]
   ```
3. Profile-specific columns are added to `positions` via the
   `init_db()` migration loop but conditionally hidden in the UI based
   on `TRACKER_PROFILE`. Users keep existing data through a profile
   switch — the schema is additive.

### 12.2 Soft delete + undo

Introduce `positions.archived_at TIMESTAMP NULL`. Deletion becomes
`UPDATE positions SET archived_at = datetime('now')` instead of `DELETE`;
`get_all_positions()` filters `WHERE archived_at IS NULL` by default.
An "Archived" section on the Opportunities page surfaces soft-deleted
rows with a "Restore" button. An `st.toast(..., icon="🗑️")` with a
5-second Undo action handles the grace period.

FK cascade semantics change slightly: cascading deletes still fire on
hard-delete only. Soft-delete leaves applications, interviews, and
recommenders rows intact but hidden alongside their parent position.

### 12.3 File attachments on Materials

New `attachments` table with `UNIQUE(position_id, doc_type)`. Files live
on local disk under `attachments/<position_id>/<doc_type>.<ext>`; paths
stored in DB. Upload auto-flips `done_* = 1`. Delete-position path
additionally calls `shutil.rmtree(f"attachments/{position_id}")` to
clean orphaned files.

### 12.4 AI-populated quick-add

Paste a job-posting URL or free-form description; an LLM extracts
fields and pre-fills the quick-add form. Requires:
- A new module (`ai_ingest.py`) with a narrow public API: `extract_fields(source: str) -> dict[str, Any]`
- API key handling via `.env` — the `.env*` gitignore rule reserved from v1 covers the secrets; the runtime will need `python-dotenv` added to `requirements.txt` when this lands
- Careful prompt discipline (structured output schema matching `QUICK_ADD_FIELDS`)

v1's quick-add should accept a `prefill: dict` parameter shape (a
two-line change today) so the v2 AI module wires in without
restructuring the page.

### 12.5 Cloud backup of `postdoc.db`

Periodic upload of `postdoc.db` + `exports/` (+ `attachments/` once 12.3
lands) to a cloud blob store (S3, iCloud Drive, Dropbox). Scheduled via
`APScheduler` or cron. v1 users get a free workaround today by placing
the project folder inside an iCloud/Dropbox-synced directory.

### 12.6 Interactive funnel

Click a bar on the dashboard funnel → navigate to the Opportunities
page with the corresponding `FUNNEL_BUCKETS` status set pre-selected in
the status filter. Implementation path: Plotly click events return a
bucket index; the handler writes the list of raw statuses to
`st.session_state["pending_status_filter"]`; the Opportunities page
reads and applies it on next render, then clears.

### 12.7 Additional analytics (post-v1)

- **Source effectiveness chart** — which `source` values yield the most `[INTERVIEW]` conversions
- **Application timeline chart** — histogram of `applied_date` clustering around deadlines
- **Offer details sub-table** — new `offers` table FK'd from `applications` (start date, salary notes, decision deadline)
- **Application goals** — `settings` table storing a target count and deadline; dashboard surfaces progress
- **Interview-velocity metric** — avg. days from `applied_date` to first `interviews.scheduled_date`, segmented by `source`
