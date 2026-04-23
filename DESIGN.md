# System Design: Postdoc Application Tracker
**Version:** 1.2 | **Updated:** 2026-04-23 | **Status:** v1 target design (authoritative)

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
A postdoc job search involves tracking 20–40 positions simultaneously across
different institutions, each with unique deadlines, requirement checklists,
recommendation letter logistics, and outcome timelines. Markdown files alone
cannot answer the key daily question: **"What do I do today?"**

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
| Charts | Plotly (Graph Objects) | 5.22 | Used via `plotly.graph_objects.Figure` / `go.Bar`; interactive by default |
| Data frames | pandas | 2.2 | Bridges SQLite rows ↔ Streamlit display widgets |
| Database | SQLite via `sqlite3` | stdlib | No server; single file; standard SQL; gitignored |

Exact pinned versions live in `requirements.txt`; the `Required ≥`
column is the minimum known-working version and is the floor for any
dependency upgrade policy.

**Install:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install streamlit plotly pandas
pip freeze > requirements.txt
```

**Run:**
```bash
source .venv/bin/activate
streamlit run app.py
# → http://localhost:8501
```

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
│   ├── 2_Applications.py     Progress tracking — submission, response, outcome
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
| `.env`, `.env.*` | ❌ | Secrets |
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
    "[CLOSED]",      # Deadline passed; did not apply (user withdrew pre-application)
    "[REJECTED]",    # Rejection received after applying
    "[DECLINED]",    # Offer turned down (by applicant)
]

# Named aliases for specific pipeline stages. Page code references these
# rather than positional indices or literal strings — keeps the anti-typo
# guardrail in place (grep rule catches literal usage at merge time).
STATUS_SAVED     = STATUS_VALUES[0]   # "[SAVED]"
STATUS_APPLIED   = STATUS_VALUES[1]   # "[APPLIED]"
STATUS_INTERVIEW = STATUS_VALUES[2]   # "[INTERVIEW]"
STATUS_OFFER     = STATUS_VALUES[3]   # "[OFFER]"

# Terminal statuses — positions in these states are excluded from "active"
# queries (upcoming deadlines, materials readiness, application funnel
# active-only calculations, etc.).
TERMINAL_STATUSES: list[str] = ["[CLOSED]", "[REJECTED]", "[DECLINED]"]

# Storage-to-color map. Values must be from the palette accepted by both
# st.badge and Plotly marker_color (CSS color names are the safe overlap).
STATUS_COLORS: dict[str, str] = {
    "[SAVED]":     "blue",
    "[APPLIED]":   "orange",
    "[INTERVIEW]": "violet",
    "[OFFER]":     "green",
    "[CLOSED]":    "gray",
    "[REJECTED]":  "red",
    "[DECLINED]":  "gray",
}

# Storage-to-UI-label map. Storage retains square brackets (visual enum
# sentinel; avoids namespace collision with plain-English words elsewhere
# in the codebase); UI strips them via this dict. Every surface that
# renders a status to the user MUST go through STATUS_LABELS — never
# print the raw key.
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
# Each entry: (UI label, tuple of raw STATUS_VALUES contributing to this bar).
# The chart sums counts within each bucket. Order determines display order
# on the chart (top-down when the y-axis is reversed).
#
# "Archived" groups [REJECTED] + [DECLINED] only — both are outcomes after
# engagement. [CLOSED] stays its own bucket because pre-application
# withdrawal is a genuinely distinct state (see D17).
FUNNEL_BUCKETS: list[tuple[str, tuple[str, ...]]] = [
    ("Saved",     ("[SAVED]",)),
    ("Applied",   ("[APPLIED]",)),
    ("Interview", ("[INTERVIEW]",)),
    ("Offer",     ("[OFFER]",)),
    ("Closed",    ("[CLOSED]",)),
    ("Archived",  ("[REJECTED]", "[DECLINED]")),
]

# ── Controlled vocabularies ───────────────────────────────────────
PRIORITY_VALUES: list[str] = ["High", "Medium", "Low", "Stretch"]

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

# RESULT_DEFAULT is the applications.result DEFAULT in the schema.
# The schema DDL reads this constant via f-string, so renaming here
# propagates to the CREATE TABLE clause automatically (see §6.2).
RESULT_DEFAULT: str = "Pending"
RESULT_VALUES: list[str] = [
    RESULT_DEFAULT,
    "Offer Accepted", "Offer Declined", "Rejected", "Withdrawn",
]

RELATIONSHIP_TYPES: list[str] = [
    "PhD Advisor", "Committee Member", "Collaborator",
    "Postdoc Supervisor", "Department Faculty", "Other",
]

# ── Requirement document types ────────────────────────────────────
# Canonical DB values for req_* columns. Order = display order on the
# Requirements tab radio ("Required" leftmost as the common case).
REQUIREMENT_VALUES: list[str] = ["Y", "Optional", "N"]

# UI labels for each canonical value. Radios look up display text via
# format_func=REQUIREMENT_LABELS.get so session_state keeps the
# canonical DB value — no save-time translation needed.
REQUIREMENT_LABELS: dict[str, str] = {
    "Y":        "Required",
    "Optional": "Optional",
    "N":        "Not needed",
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
# Boundary semantics: inclusive on the lower-severity side.
# A deadline 7 days away → "urgent"; a deadline 30 days away → "alert".
DEADLINE_ALERT_DAYS: int    = 30
DEADLINE_URGENT_DAYS: int   = 7
RECOMMENDER_ALERT_DAYS: int = 7
```

### 5.2 Import-time invariants

`config.py` executes the following assertions at module import. A
violation aborts app startup with a clear traceback — catches drift
before any page renders:

1. `TRACKER_PROFILE in VALID_PROFILES` — profile is a known value
2. `set(STATUS_VALUES) == set(STATUS_COLORS)` — every status has a color
3. `set(STATUS_VALUES) == set(STATUS_LABELS)` — every status has a UI label
4. `set(TERMINAL_STATUSES) <= set(STATUS_VALUES)` — terminals are a subset
5. The multiset of `STATUS_VALUES` contained in all `FUNNEL_BUCKETS` tuples, flattened, equals `set(STATUS_VALUES)` and contains no duplicates — every status lives in exactly one bucket
6. `set(REQUIREMENT_LABELS) == set(REQUIREMENT_VALUES)` — every req value has a label
7. `DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS` — urgency thresholds order correctly

### 5.3 Extension recipes

| Goal | What to edit |
|------|--------------|
| Add a new requirement document | Append one tuple to `REQUIREMENT_DOCS`. On next app start, `init_db()` adds `req_*` / `done_*` columns via the migration loop. No other file changes. |
| Add a priority / source / response-type / relationship option | Append to the relevant list. Dropdowns pick it up on next render. No DB change — columns are plain TEXT. |
| Add a new pipeline status | (1) Append to `STATUS_VALUES`; (2) add one entry each to `STATUS_COLORS` and `STATUS_LABELS`; (3) decide which `FUNNEL_BUCKETS` entry it belongs in (extend a tuple or add a new bucket); (4) if terminal, append to `TERMINAL_STATUSES`. No DDL change. |
| Rename a pipeline status | Edit `STATUS_VALUES[i]`, the corresponding keys in `STATUS_COLORS` and `STATUS_LABELS`, any references in `FUNNEL_BUCKETS` and `TERMINAL_STATUSES`. Write a one-shot migration in `CHANGELOG.md` under the release: `UPDATE positions SET status = '<new>' WHERE status = '<old>'`. The schema `DEFAULT` clause is config-driven; no DDL edit needed if renaming `STATUS_VALUES[0]`. |
| Switch the tracker profile | See §11 and §12.1. |

---

## 6. Database Schema

Canonical DDL lives in `database.init_db()`. This section is the
architectural description of that DDL.

### 6.1 Entity-Relationship summary

```
positions (1) ──< applications (1)      one-to-one
positions (1) ──< recommenders (many)   one-to-many
```

### 6.2 Tables

```sql
PRAGMA foreign_keys = ON;

-- ── Table 1: positions ─────────────────────────────────────────
-- One row per position.
CREATE TABLE IF NOT EXISTS positions (

    -- Identity & metadata
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    status           TEXT    NOT NULL DEFAULT '[SAVED]',  -- from config.STATUS_VALUES[0]
    priority         TEXT,
    created_at       TEXT    DEFAULT (date('now')),

    -- Overview
    position_name    TEXT    NOT NULL,
    institute        TEXT,
    location         TEXT,
    field            TEXT,
    deadline_date    TEXT,       -- ISO-8601 'YYYY-MM-DD' — drives all time math
    deadline_note    TEXT,       -- Freetext context: "rolling after initial review"
    stipend          TEXT,
    work_auth        TEXT,
    full_time        TEXT,
    source           TEXT,
    link             TEXT,

    -- Details
    mentor           TEXT,
    point_of_contact TEXT,
    portal_url       TEXT,       -- Submission portal URL (may differ from link)
    keywords         TEXT,
    description      TEXT,
    num_rec_letters  INTEGER,
    reference_code   TEXT,
    notes            TEXT

    -- req_* TEXT DEFAULT 'N' and done_* INTEGER DEFAULT 0 pairs,
    -- one per entry in config.REQUIREMENT_DOCS, generated by init_db().
    -- Values: req_* ∈ {'Y', 'Optional', 'N'}; done_* ∈ {0, 1}.
);

-- ── Table 2: applications ──────────────────────────────────────
-- One row per position. Tracks submission, response, and outcome.
-- Automatically created when a position is added (all fields NULL).
CREATE TABLE IF NOT EXISTS applications (
    position_id          INTEGER PRIMARY KEY,
    applied_date         TEXT,
    all_recs_submitted   TEXT,       -- 'Y' when all letters are in
    confirmation_email   TEXT,       -- 'Y' or date string
    response_date        TEXT,
    response_type        TEXT,
    interview1_date      TEXT,
    interview2_date      TEXT,
    result_notify_date   TEXT,
    result               TEXT    DEFAULT 'Pending',   -- from config.RESULT_DEFAULT
    notes                TEXT,
    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
);

-- ── Table 3: recommenders ──────────────────────────────────────
-- Many rows per position; one row per (position × recommender) pair.
CREATE TABLE IF NOT EXISTS recommenders (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id      INTEGER NOT NULL,
    recommender_name TEXT,
    relationship     TEXT,
    asked_date       TEXT,
    confirmed        TEXT,       -- 'Y' | 'N' | NULL (pending)
    submitted_date   TEXT,
    reminder_sent    TEXT,
    notes            TEXT,
    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
);

-- ── Indices (queried most often by dashboard / filters) ───────
CREATE INDEX IF NOT EXISTS idx_positions_status   ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_deadline ON positions(deadline_date);
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
| New entry in `config.REQUIREMENT_DOCS` | `ALTER TABLE positions ADD COLUMN req_<x> TEXT DEFAULT 'N'` + `ADD COLUMN done_<x> INTEGER DEFAULT 0`, guarded by a `PRAGMA table_info` existence check |
| A brand-new table | `CREATE TABLE IF NOT EXISTS <name> (...)` in `init_db()` |
| New entry in any vocabulary list (`SOURCE_OPTIONS`, `RESPONSE_TYPES`, etc.) | No DDL — columns are plain TEXT; dropdowns pick up new values on next render |

**Manual (requires a migration step, recorded in CHANGELOG):**

| Change | Required step |
|--------|---------------|
| Rename a status value (e.g. `[OPEN]` → `[SAVED]`) | One-shot `UPDATE positions SET status = '<new>' WHERE status = '<old>'`. Schema DEFAULT is config-driven, so no DDL edit. |
| Rename `RESULT_DEFAULT` | One-shot `UPDATE applications SET result = '<new>' WHERE result = '<old>'`. |
| Add a new top-level (non-`req_*`/`done_*`) column to `positions` | Extend the `CREATE TABLE` clause **and** add an `ALTER TABLE ... ADD COLUMN` guarded by a `PRAGMA table_info` check — mirror the existing REQUIREMENT_DOCS loop. |
| Remove a column | SQLite requires a table rebuild: `CREATE TABLE new AS SELECT <kept cols> FROM positions; DROP TABLE positions; ALTER TABLE new RENAME TO positions`. Document as a breaking change in CHANGELOG. |

**Migration discipline:** every schema or vocabulary change lands with a
`Migration:` note in `CHANGELOG.md` under the release that introduces
it, giving the exact `UPDATE` or rebuild SQL. A user upgrading between
releases should never have to guess which migration to run.

### 6.4 Schema design notes

| Decision | Reason |
|----------|--------|
| `deadline_date` is ISO text, not a DATE column | SQLite has no native DATE type; ISO-8601 strings sort and compare correctly as TEXT |
| `done_*` columns are `INTEGER 0/1` | SQLite has no BOOLEAN; materials readiness is computed at query time, not stored as a summary field |
| Separate `applications` table (not merged into `positions`) | Different update cadence; `positions` = "what exists", `applications` = "what you did" |
| `ON DELETE CASCADE` on both child tables | Deleting a position removes its application row and all recommender rows atomically |
| Auto-create `applications` row on `add_position()` | Every position always has a matching row; no NULL-check overhead in joins |

---

## 7. Module Contracts

### `database.py` — public API

```python
from pathlib import Path
from typing import Any
import sqlite3
import pandas as pd

DB_PATH: Path                          # resolved relative to database.py location

# ── Init ──────────────────────────────────────────────────────────
def init_db() -> None:
    """Create tables and indices if they don't exist. Safe to call on every start.
    DDL DEFAULTs derive from config; req_*/done_* columns derive from
    config.REQUIREMENT_DOCS with an idempotent ALTER TABLE migration loop
    covering entries added after the initial CREATE."""

# ── Positions ─────────────────────────────────────────────────────
def add_position(fields: dict[str, Any]) -> int:
    """Insert a new position row and its blank applications row.
    Returns the new position id. Calls exports.write_all()."""

def get_all_positions() -> pd.DataFrame:
    """Return all positions ordered by deadline_date ASC, NULLs last."""

def get_position(position_id: int) -> dict[str, Any]:
    """Return a single position as a dict. Raises KeyError if not found."""

def update_position(position_id: int, fields: dict[str, Any]) -> None:
    """Update provided fields on an existing position. Calls exports.write_all()."""

def delete_position(position_id: int) -> None:
    """Delete position; applications + recommenders cascade.
    Calls exports.write_all()."""

# ── Applications ──────────────────────────────────────────────────
def get_application(position_id: int) -> dict[str, Any]:
    """Return the application row as a dict.
    Returns {} if no row exists (should not happen after add_position)."""

def upsert_application(
    position_id: int,
    fields: dict[str, Any],
    *,
    propagate_status: bool = True,
) -> dict[str, Any]:
    """INSERT or UPDATE the application row for a position.

    When propagate_status is True (default), the pipeline-promotion rules
    in §9.3 fire atomically within the same transaction as the application
    upsert. Callers that are editing purely-application fields (e.g.
    fixing a typo in notes) and don't want pipeline side-effects pass
    propagate_status=False.

    Returns a dict:
        {
            "status_changed": bool,
            "new_status":     str | None,   # the new positions.status if changed
        }
    so callers can surface a toast when a promotion fires.

    Calls exports.write_all()."""

# ── Recommenders ──────────────────────────────────────────────────
def add_recommender(position_id: int, fields: dict[str, Any]) -> int:
    """Insert a new recommender row. Returns the new id. Calls exports.write_all()."""

def get_recommenders(position_id: int) -> pd.DataFrame:
    """Return recommenders for one position, ordered by id ASC."""

def get_all_recommenders() -> pd.DataFrame:
    """Return all recommenders joined with position_name and institute,
    ordered by recommender_name ASC, id ASC."""

def update_recommender(rec_id: int, fields: dict[str, Any]) -> None:
    """Update fields on a recommender row. Calls exports.write_all()."""

def delete_recommender(rec_id: int) -> None:
    """Delete one recommender row. Calls exports.write_all()."""

# ── Dashboard queries ─────────────────────────────────────────────
def count_by_status() -> dict[str, int]:
    """Return {raw_status_value: count}. Zero-count statuses are OMITTED
    (sparse dict); callers fill missing keys with 0 before display.
    Keys are the raw storage values (e.g. '[SAVED]'), not UI labels —
    the presentation layer translates via config.STATUS_LABELS and groups
    via config.FUNNEL_BUCKETS."""

def get_upcoming_deadlines(days: int = config.DEADLINE_ALERT_DAYS) -> pd.DataFrame:
    """Return non-terminal positions with deadline_date in [today, today+days],
    ordered by deadline_date ASC.
    Excludes positions with status in config.TERMINAL_STATUSES."""

def get_upcoming_interviews() -> pd.DataFrame:
    """Return rows where interview1_date OR interview2_date is today or later,
    joined with position_name and institute, ordered by
    interview1_date ASC NULLS LAST, interview2_date ASC NULLS LAST.

    Note: a row where only interview2_date is future (interview1 in the
    past) is still included — callers that need the earliest future date
    scan both columns per row."""

def get_pending_recommenders(
    days: int = config.RECOMMENDER_ALERT_DAYS,
) -> pd.DataFrame:
    """Return recommender rows with asked_date >= `days` ago and
    submitted_date IS NULL, joined with position_name, institute, and
    deadline_date, ordered by recommender_name ASC, deadline_date ASC NULLS LAST."""

def compute_materials_readiness() -> dict[str, int]:
    """Return {"ready": N, "pending": M} for active-pipeline positions.

    Active = status in (config.STATUS_SAVED, STATUS_APPLIED, STATUS_INTERVIEW).
    "Ready" = every doc with req_* = 'Y' also has done_* = 1.
    Only positions with at least one required doc (req_* = 'Y') are
    counted — a position with all docs 'N' contributes to neither
    bucket."""
```

### `exports.py` — public API

```python
def write_all() -> None:
    """Regenerate all three markdown export files. Called from every
    database.py writer.

    Errors are logged but do not propagate — a failed export must not
    cause a successful DB write to surface as a UI error. Callers see
    "Saved", even if the markdown regeneration failed; the missing
    backup is visible on the Export page."""

def write_opportunities() -> None:
    """Generate exports/OPPORTUNITIES.md from the positions table."""

def write_progress() -> None:
    """Generate exports/PROGRESS.md from positions JOIN applications."""

def write_recommenders() -> None:
    """Generate exports/RECOMMENDERS.md from recommenders JOIN positions."""
```

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
funnel chart, timeline). Default centered layout crams every view.
`set_page_config` runs at the top of `app.py` and every `pages/*.py` —
it is re-executed on every page switch.

#### Widget-key prefix conventions

Widget keys follow a scope prefix so tests can pin them reliably across
reruns:

| Scope | Prefix | Example |
|-------|--------|---------|
| Quick-add form | `qa_` | `qa_position_name`, `qa_deadline_date` |
| Edit panel (row-scoped) | `edit_` | `edit_position_name`, `edit_notes` |
| Filter bar | `filter_` | `filter_status`, `filter_field` |
| Internal sentinels | `_` prefix | `_edit_form_sid`, `_delete_target_id`, `_skip_table_reset` |
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
║  Tracked ⓘ   ║  Applied     ║  Interview   ║  Next Interview   ║
║              ║              ║              ║                   ║
╠══════════════╩══════════════╩══════════════╩═══════════════════╣
║                                                                ║
║  Application Funnel         ║  Materials Readiness            ║
║                             ║                                 ║
║  Saved       ████████  8    ║  Ready to submit:  3            ║
║  Applied     ██████    4    ║  ███                             ║
║  Interview   ████      2    ║                                 ║
║  Offer       ██        1    ║  Still missing:    5            ║
║  Closed      —         0    ║  █████                           ║
║  Archived    ██        2    ║                                 ║
║                             ║  [→ Opportunities page]         ║
║                             ║                                 ║
╠═════════════════════════════╩═════════════════════════════════╣
║  Upcoming (next 30 days)                                       ║
║                                                                ║
║  Apr 24  Stanford BioStats   Saved      deadline    9d  🔴    ║
║  May 3   Stanford BioStats   Applied    Interview  18d        ║
║  May 15  MIT CSAIL           Saved      deadline   30d        ║
║                                                                ║
╠════════════════════════════════════════════════════════════════╣
║  Recommender Alerts                                            ║
║                                                                ║
║  ⚠  Dr. Smith  →  Stanford, MIT CSAIL  (asked 14 days ago)    ║
║  ✓  Dr. Jones  →  Stanford             (submitted Apr 20)      ║
╚════════════════════════════════════════════════════════════════╝
```

**Top bar:** Title only. No manual refresh button — Streamlit reruns on
any widget interaction; for a single-user local app the cross-tab write
case is rare enough that a refresh button is net cognitive noise (D13).

**Panel specifications:**

| Panel | Data source | Labels | Warn/flag trigger |
|-------|------------|--------|-------------------|
| KPI: Tracked | `count_by_status()` summed over `STATUS_SAVED + STATUS_APPLIED` | `st.metric(..., help="Saved + Applied — positions you're still actively pursuing")` | — |
| KPI: Applied | `count_by_status().get(STATUS_APPLIED, 0)` | — | — |
| KPI: Interview | `count_by_status().get(STATUS_INTERVIEW, 0)` | — | — |
| KPI: Next Interview | `get_upcoming_interviews()` scanned per-cell for earliest FUTURE date across `interview1_date` + `interview2_date`; rendered `'{Mon D} · {institute}'`; "—" when none | — | — |
| Funnel | `count_by_status()` summed into `FUNNEL_BUCKETS`; Plotly horizontal `go.Bar`, one bar per bucket in list order; y-axis reversed so the earliest pipeline stage sits on top; single-status buckets use `STATUS_COLORS[raw]`; the "Archived" bucket uses `"gray"` | Bucket labels = `FUNNEL_BUCKETS[i][0]` (UI, no brackets) | — |
| Materials Readiness | `compute_materials_readiness()` → two stacked `st.progress` bars labelled `"Ready to submit: N"` / `"Still missing: M"`; values = count / `max(ready + pending, 1)`; CTA button `"→ Opportunities page"` calling `st.switch_page` | — | Empty state when `ready + pending == 0` |
| Upcoming | Merge of `get_upcoming_deadlines()` + `get_upcoming_interviews()` by date; `st.dataframe(width="stretch")`, columns (Date, Label, Kind, Urgency); Status shown via `STATUS_LABELS[raw]`; Kind ∈ {"deadline", "interview"} | — | 🔴 when days-away ≤ `DEADLINE_URGENT_DAYS`; 🟡 when ≤ `DEADLINE_ALERT_DAYS` |
| Recommender Alerts | `get_pending_recommenders(RECOMMENDER_ALERT_DAYS)` grouped by `recommender_name` — one card per person with all their owed positions listed | — | All shown rows are warnings (the query filters for them) |

**Empty-DB hero:** When

```python
count_by_status().get(STATUS_SAVED, 0)
+ count_by_status().get(STATUS_APPLIED, 0)
+ count_by_status().get(STATUS_INTERVIEW, 0) == 0
```

a bordered hero container above the KPI grid shows a welcome subheader,
an explanatory paragraph, and a primary CTA button that
`st.switch_page("pages/1_Opportunities.py")`. The KPI grid renders
beneath the hero regardless. A DB holding only terminal-status rows
(`[CLOSED]` / `[REJECTED]` / `[DECLINED]`) still triggers the hero —
there is nothing actionable on the dashboard in that state.

**Empty-state branches** (each panel, when its relevant data is empty):

| Panel | Empty-state behaviour |
|-------|-----------------------|
| Funnel | If `sum(count_by_status().values()) == 0` (no rows anywhere), show `st.info("Application funnel will appear once you've added positions.")`. A DB with only terminal-status rows still renders the chart. Subheader renders in both branches (page-height stability). |
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
║  ──────────────────────────────────────────────────────────── ║
║  Stanford BioStats    Stanford   🟡 High   Applied   ——        ║
║  MIT CSAIL Postdoc    MIT        🟡 High   Saved     May 15    ║
║  ··· (click row to expand) ···                                 ║
║                                                                ║
║  ┌──── Stanford BioStats Postdoc  ·  Applied  ─────────────┐  ║
║  │  [ Overview ] [ Requirements ] [ Materials ] [ Notes ]   │  ║
║  │  ─────────────────────────────────────────────────────── │  ║
║  │  (tab content — full edit form fields)                   │  ║
║  │                            [ Save Changes ] [ Delete ]   │  ║
║  └──────────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════════╝
```

**Behaviour:**

| Element | Behaviour |
|---------|-----------|
| Quick-add | Exactly the 6 fields from `config.QUICK_ADD_FIELDS`; saves with `status = config.STATUS_VALUES[0]` (i.e. `[SAVED]`); auto-creates `applications` row. Whitespace-only `position_name` rejected with `st.error`; success → `st.toast`. |
| Filter: Status | `st.selectbox(["All"] + STATUS_VALUES, format_func=STATUS_LABELS.get)` — UI shows labels; filter compares raw values |
| Filter: Priority | `st.selectbox(["All"] + PRIORITY_VALUES)` |
| Filter: Field | `st.text_input`; substring match via `df["field"].str.contains(..., case=False, na=False, regex=False)` — literal match so `"C++"` doesn't crash pandas |
| Table | `st.dataframe(width="stretch", on_select="rerun", selection_mode="single-row")`; sorted by `deadline_date ASC NULLS LAST`; Status column displays `STATUS_LABELS[raw]`; Due column carries an urgency column driven by `DEADLINE_URGENT_DAYS` / `DEADLINE_ALERT_DAYS` |
| Row click | Selects row; edit panel renders beneath using the **unfiltered** `df` for lookup (so narrowing the filter never dismisses an in-progress edit) |
| Status selectbox (Overview tab) | Same format_func convention — display label, store raw |
| Date inputs | `st.date_input()` everywhere dates are entered; stored as `.isoformat()` |
| Requirements tab | One `st.radio` per `REQUIREMENT_DOCS` entry; options = `REQUIREMENT_VALUES`; `format_func=REQUIREMENT_LABELS.get`; Save writes only `req_*` keys so `done_*` survives Y↔N flips |
| Materials tab | Live-filtered: only docs with `session_state[f"edit_{req_col}"] == 'Y'` render a checkbox; Save writes only `done_*` for visible docs (hidden `done_*` preserved) |
| Notes tab | Single `st.text_area` inside `st.form("edit_notes_form")`; empty input persists as `""` not `NULL` |
| Delete | `@st.dialog` confirmation dialog outside `st.form` (st.form only permits form_submit_button inside); FK cascade removes applications + recommenders atomically |

**Selection-survival invariant.** The following operations must NOT
collapse the edit panel:
- Save on any tab (post-save rerun)
- Filter change that still includes the selected row
- Dialog open → cancel

Streamlit's `st.dataframe(on_select="rerun")` resets its event on
data-change reruns; a one-shot `_skip_table_reset` flag set before
`st.rerun()` in each Save path (and the dialog-Cancel path) preserves
`selected_position_id` across the cycle.

---

### 8.3 `pages/2_Applications.py` — Progress

**Purpose:** Track every position from submission to outcome.

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
║  │  Confirmation email: ✓                                  │  ║
║  │  Response type: Interview Invite ▼  Date: Apr 22        │  ║
║  │  Interview 1: 📅 May 3     Interview 2: 📅 ——           │  ║
║  │  Result notify date: 📅 ——  Result: Pending ▼           │  ║
║  │  Notes: ___________________________________  [ Save ]   │  ║
║  └──────────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════════╝
```

**Behaviour:**
- **Default filter** excludes positions with status `[SAVED]` or `[CLOSED]` — they're pre-application or withdrawn and have no application data worth showing.
- **Pipeline promotions** (application edits auto-advancing `positions.status`) fire inside `database.upsert_application(propagate_status=True)` — see §9.3. The page does NOT detect the transition or prompt the user; it just calls upsert, then reads the return dict and surfaces a `st.toast` if `status_changed` is True.
- **Status selectbox** (read-only here; this page edits application, not pipeline) shows `STATUS_LABELS[raw]`.

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
- **Alert panel grouping:** `get_pending_recommenders()` returns one row per (recommender × position); the page groups by `recommender_name` so one recommender who owes 3 letters appears as a single card listing all 3 positions.
- **Compose reminder email:** opens a `mailto:` URL with subject pre-filled ("Following up: letters for N postdoc applications") and body listing the position names + deadlines. No outbound email integration — the OS hands off to the user's mail client.
- **Add-recommender form:** position dropdown shows `position_name` + institute; IDs never surface to the user.
- **Inline edit:** clicking a row in the "All Recommenders" table opens inline fields for `asked_date`, `confirmed`, `submitted_date`, `reminder_sent`, `notes`.

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
      → INSERT INTO applications (position_id, all NULLs)
      → exports.write_all()          (logged-and-continue on failure)
  → st.toast("Added ...")
  → st.rerun()
  → table refreshes with the new row
```

### 9.2 Dashboard load

```
app.py runs (fresh or on rerun)
  → st.set_page_config(layout="wide", ...)
  → database.init_db()   (no-op on existing tables; ALTER loops run if
                           config.REQUIREMENT_DOCS grew)
  → database.count_by_status()             → KPI math + Funnel (via FUNNEL_BUCKETS)
  → database.compute_materials_readiness() → Readiness panel
  → database.get_upcoming_deadlines()   ┐
  → database.get_upcoming_interviews()  ├→ merge by date → Upcoming panel
  → database.get_pending_recommenders() → Alerts panel (grouped by recommender)
```

### 9.3 Pipeline auto-promotion (application edits)

**The cascade is fully owned by `database.py`. Pages are display-only
(D12).**

`upsert_application(position_id, fields, *, propagate_status=True)`
runs the following rules atomically within the same transaction as the
application UPDATE:

| # | Condition detected on the effective post-upsert row | Cascade |
|---|------------------------------------------------------|---------|
| R1 | `applied_date` transitions from NULL to a non-NULL value | `UPDATE positions SET status = '[APPLIED]' WHERE id = ? AND status = '[SAVED]'` |
| R2 | `interview1_date` OR `interview2_date` transitions from NULL to non-NULL | `UPDATE positions SET status = '[INTERVIEW]' WHERE id = ? AND status = '[APPLIED]'` |
| R3 | `response_type` transitions to `"Offer"` | `UPDATE positions SET status = '[OFFER]' WHERE id = ?` (unconditional — Offer overrides earlier stages) |

Rules fire in listed order. R1 and R2 are **guarded** — they only
promote from the immediately-previous stage, so a backward edit (e.g.
clearing an interview date on a position already at `[OFFER]`) does
not regress the pipeline. R3 is **unconditional** — receiving an Offer
always lands the position at `[OFFER]` regardless of prior stage.

If both R1 and R3 fire on the same upsert, R3 wins (applied later and
unconditional). The combined effect equals `[SAVED]` → `[OFFER]` in one
transaction.

`upsert_application` returns `{"status_changed": bool, "new_status": str | None}`
so the page can surface a `st.toast` when a promotion fires
(e.g. `"Promoted to Offer"`).

Callers opt out with `propagate_status=False` for edits that should not
move the pipeline (e.g. correcting a typo in application notes). The
Applications page always calls with the default; Recommenders and the
quick-add path never touch this function.

**Rationale for locating the cascade in `database.py`:**
- Atomicity — a failed propagation rolls back the application update too
- Testable without an AppTest harness (pure database + config)
- Keeps pages display-only per GUIDELINES §2
- If a future page (or export batch job) writes applications, the cascade fires uniformly without each caller reimplementing it

### 9.4 Deleting a position

```
User clicks Delete on Overview tab
  → @st.dialog opens with the position's name + cascade warning
  → User clicks Confirm
      → database.delete_position(id)
          → DELETE FROM positions WHERE id = ?
             (applications + recommenders cascade via ON DELETE CASCADE)
          → exports.write_all()
      → st.toast("Deleted ...")
      → session_state cleanup (paired: selected_position_id, _edit_form_sid,
        _delete_target_id, _delete_target_name)
      → st.rerun() → edit panel collapses
```

Cancel clears only the `_delete_target_*` pair, preserving
`selected_position_id` via the `_skip_table_reset` one-shot so the user
returns to the same edit context.

### 9.5 Export pipeline

```
Any database.py writer ends with:
  → exports.write_all()
      → write_opportunities()  → exports/OPPORTUNITIES.md
      → write_progress()       → exports/PROGRESS.md
      → write_recommenders()   → exports/RECOMMENDERS.md
```

A failure in any `write_*` is caught at `write_all()` boundary, logged,
and swallowed — the DB write has already succeeded, so the user should
see "Saved", not a traceback. The Export page surfaces the file mtimes
so a user notices if backups stopped regenerating.

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
| D6 | Quick-add is exactly 6 fields | Capture must cost < 30 seconds; enrichment later | Full form on add — positions get lost at discovery time |
| D7 | Status via `st.selectbox(STATUS_VALUES, format_func=STATUS_LABELS.get)` | Prevents typo corruption; UI label decoupled from storage | Freetext — undetectable corruption |
| D8 | `ON DELETE CASCADE` on child tables | One delete cleans three tables atomically | Manual multi-table delete — easy to orphan rows |
| D9 | Separate `applications` table | Different update cadence + concern from positions | Single wide table — harder to query, harder to reason about |
| D10 | Auto-create `applications` row on `add_position()` | Every position always has a matching row | Create on first update — requires NULL handling everywhere |
| D11 | Presentation/storage split via `STATUS_LABELS` + `FUNNEL_BUCKETS` | Cheap UI renames (no schema migration); presentation grouping is reversible at-will | Rename storage values — requires DB migration for every naming tweak |
| D12 | Cross-table cascade lives in `database.upsert_application` | Atomic, testable, pages stay display-only | Page-level detect-and-prompt — leaks business logic into UI; loses atomicity |
| D13 | No 🔄 Refresh button on the dashboard top bar | Streamlit reruns on any interaction; single-user local app rarely has cross-tab writes; fewer buttons = less clutter | Manual refresh button — cognitive noise for the common case |
| D14 | `st.set_page_config(layout="wide", ...)` on every page | Data-heavy views need horizontal room | Default centered layout — ~750px cramps every page |
| D15 | `TRACKER_PROFILE` validated at import time against `VALID_PROFILES` | Cheap forward-compat hook for v2 profile variants; catches typos now | Hardcode `"postdoc"` — no v2 extension point |
| D16 | Bracketed status storage values (`"[SAVED]"` etc.) + bracket-stripped UI labels | Visual enum sentinel in logs/DB; `STATUS_LABELS` delivers clean UI | Raw labels in storage — harder to grep; conflicts with freetext "Saved" elsewhere |
| D17 | Archived = `[REJECTED]` + `[DECLINED]` on the dashboard funnel only; `[CLOSED]` stays its own bar | Rejection + declined-offer are both outcomes after engagement; CLOSED is pre-engagement withdrawal — a genuinely different state | Group all three terminals — loses semantic distinction |

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
1. Append to the relevant list (`WORK_AUTH_OPTIONS`, `SOURCE_OPTIONS`, `RESPONSE_TYPES`, `RESULT_VALUES`, `RELATIONSHIP_TYPES`).
2. Selectboxes pick the new value up on next render.
3. No DB change — column is plain TEXT.

### Add a new pipeline status
1. Append to `STATUS_VALUES`.
2. Add one entry each to `STATUS_COLORS` and `STATUS_LABELS`.
3. Decide which `FUNNEL_BUCKETS` entry it belongs in — extend an existing tuple or add a new bucket in the right display position.
4. If terminal (no downstream pipeline stage), append to `TERMINAL_STATUSES`.
5. No DB change; status column is TEXT.

### Rename a pipeline status
1. Edit `STATUS_VALUES[i]`, the matching keys in `STATUS_COLORS` and `STATUS_LABELS`, and any references in `FUNNEL_BUCKETS` / `TERMINAL_STATUSES`.
2. Write a `Migration:` note in `CHANGELOG.md` with the one-shot SQL:
   ```sql
   UPDATE positions SET status = '<new>' WHERE status = '<old>';
   ```
3. Schema DDL is config-driven (`DEFAULT` reads `config.STATUS_VALUES[0]`), so renaming the first status value propagates without DDL edits.

### Switch the tracker profile
See §12.1. v1 supports `"postdoc"` only; the hook to add another is in place but not wired.

### Change a dashboard threshold
Edit `DEADLINE_ALERT_DAYS` / `DEADLINE_URGENT_DAYS` / `RECOMMENDER_ALERT_DAYS` in `config.py`. The import-time invariant
(`DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS`) catches inverted thresholds on next import.

---

## 12. v2 Design Notes

These are architectural ideas for post-v1 releases. They inform v1
decisions (e.g. keeping `TRACKER_PROFILE` + `VALID_PROFILES` as hooks)
but are not implemented in v1.

### 12.1 General job tracker — profile expansion

The tracker is designed so reskinning to a different job context
requires **editing `config.py` only**. v1 keeps `VALID_PROFILES =
{"postdoc"}`.

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
hard-delete only. Soft-delete leaves applications + recommenders rows
intact but hidden alongside their parent position.

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
- API key handling via `.env` (already gitignored)
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
