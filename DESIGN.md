# System Design: Postdoc Application Tracker
**Version:** 1.1 | **Updated:** 2026-04-23 | **Status:** Living reference (drift pass — pre-v1-ship refactor, no architectural change)

---

## Table of Contents
1. [Purpose & Scope](#1-purpose--scope)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [File Structure](#4-file-structure)
5. [config.py — Full Specification](#5-configpy--full-specification)
6. [Database Schema](#6-database-schema)
7. [Module Contracts](#7-module-contracts)
8. [UI Design — Page by Page](#8-ui-design--page-by-page)
9. [Data Flow](#9-data-flow)
10. [Design Decisions Log](#10-design-decisions-log)
11. [Extension Guide](#11-extension-guide)

---

## 1. Purpose & Scope

### Problem
A postdoc job search involves tracking 20–40 positions simultaneously across different institutions, each with unique deadlines, requirement checklists, recommendation letter logistics, and outcome timelines. Markdown files alone cannot answer the key daily question: **"What do I do today?"**

### Solution
A local, single-user web application that:
- Captures new positions in under 30 seconds
- Computes and surfaces the most urgent actions automatically
- Tracks recommendation letter status per recommender, per position
- Maintains human-readable markdown exports as a portable backup
- Can be extended to a general job tracker by editing one configuration file

### Explicit Non-Goals (v1)
- No user authentication
- No cloud deployment
- No mobile-first layout
- No email or calendar integration
- No multi-user support

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
│  Framework: Streamlit  |  Charts: Plotly Express               │
└────────────────────┬───────────────────────────────────────────┘
                     │ Python function calls (no SQL)
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
│                       │          │  Generated after every     │
└───────────────────────┘          │  write; human-readable     │
                                   │  backup; git-committed     │
                                   └────────────────────────────┘
```

### Layer Rules (enforced)
| Layer | May import | May NOT import |
|-------|-----------|----------------|
| Page files | `database`, `config` | `exports`, each other |
| `database.py` | `config`, `sqlite3`, `pandas` | `streamlit`, `exports` |
| `exports.py` | `database`, `config` | `streamlit` |
| `config.py` | nothing | anything |

`exports.write_all()` is called as the last line of every `database.py` write function. Page files never call `exports` directly.

---

## 3. Technology Stack

| Component | Choice | Required ≥ | Rationale |
|-----------|--------|-----------|-----------|
| Language | Python | 3.14.0 (system) | Already installed; familiar to stats/data users |
| Environment | venv (`.venv/`) | stdlib | Zero extra tools; isolates packages; gitignored |
| UI framework | Streamlit | 1.50 | Python-native; R Shiny equivalent; `width="stretch"` requires ≥ 1.50 |
| Charts | Plotly (Graph Objects) | 5.22 | Interactive by default; used via `plotly.graph_objects.Figure` / `go.Bar` |
| Data frames | Pandas | 2.2 | Bridges SQLite rows and Streamlit display |
| Database | SQLite via `sqlite3` | stdlib | No server; single file; standard SQL; gitignored |

**Tested with (as of v0.4.0, 2026-04-23):** Streamlit 1.56.0 · Plotly 6.7.0 · pandas 3.0.2 · Python 3.14.0.
The `Required ≥` column is the minimum known-working version; if a user clones with
older versions, features like `st.dataframe(width="stretch")` and `st.switch_page()`
will fail. Bump the minimum when a new API is adopted.

**Install command:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install streamlit plotly pandas
pip freeze > requirements.txt
```

**Run command:**
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
├── app.py                    ← Streamlit entry point; dashboard home page
├── config.py                 ← ALL constants, field defs, vocabulary (read by all)
├── database.py               ← All SQLite reads and writes; no Streamlit imports
├── exports.py                ← Markdown generators; called by database.py writes
│
├── pages/
│   ├── 1_Opportunities.py    ← Position table + quick-add + full edit
│   ├── 2_Applications.py     ← Progress tracking + status updates
│   ├── 3_Recommenders.py     ← Recommender log + pending alerts
│   └── 4_Export.py           ← Manual export trigger + file download
│
├── exports/                  ← Auto-generated markdown (COMMITTED — human-readable backup)
│   ├── OPPORTUNITIES.md      ← Generated from positions table
│   ├── PROGRESS.md           ← Generated from applications table
│   └── RECOMMENDERS.md       ← Generated from recommenders table
│
├── postdoc.db                ← SQLite database (GITIGNORED — binary, personal data)
├── requirements.txt          ← Exact pinned versions (committed)
│
├── tests/                    ← pytest suite (committed)
├── reviews/                  ← pre-merge review docs, one per tier (committed)
├── docs/                     ← supplemental docs (committed — added in v1.1 refactor)
│   ├── adr/                  ← architectural decision records (new decisions only)
│   └── dev-notes/            ← deep dives: git workflow, Streamlit state gotchas
│
├── DESIGN.md                 ← This file — master technical specification
├── GUIDELINES.md             ← Coding conventions for all sessions
├── roadmap.md                ← Phase tracker and backlog
├── CHANGELOG.md              ← Release history (v0.x.y, append-only)
├── README.md                 ← Public entry point (added at v1 ship prep)
├── LICENSE                   ← MIT (added at v1 ship prep)
│
├── CLAUDE.md                 ← Session working memory (GITIGNORED since v1.1)
├── PHASE_*_GUIDELINES.md     ← Phase-specific internal playbooks (GITIGNORED since v1.1)
│
└── .gitignore
```

### Transition note on root-level markdown files
`OPPORTUNITIES.md`, `PROGRESS.md`, and `RECOMMENDERS.md` in the project root are the **hand-maintained originals** created before the app existed. Once Phase 6 is complete, the `exports/` versions become the live copies. The root files are retained as the initial seed reference.

---

## 5. `config.py` — Full Specification

`config.py` is the **single source of truth** for vocabulary, constants, and field
definitions. Every other module reads from it; no other file hardcodes a status
string, priority value, or requirement-doc label.

The block below mirrors `config.py` as of **v0.4.0 (2026-04-23)**.
The `config.py` file itself remains canonical — if this mirror drifts, the file wins.

### 5.1 Constants

```python
# ── Tracker identity ──────────────────────────────────────────────
TRACKER_PROFILE = "postdoc"   # Options: "postdoc" | "software_eng" | "faculty"
# NOTE: currently UNUSED by any module (no init_db or page reads it).
# Tracked as C2 in v1.1 refactor: either wire (import-time validation +
# profile-gated fields) or remove. Code cleanup pending user decision.

# ── Status pipeline (ordered: index = pipeline position) ─────────
STATUS_VALUES = [
    "[OPEN]",        # Found; not yet applied     — rename to "[SAVED]" planned for v0.5
    "[APPLIED]",     # Application submitted
    "[INTERVIEW]",   # Interview stage reached
    "[OFFER]",       # Offer received
    "[CLOSED]",      # Deadline passed; did not apply
    "[REJECTED]",    # Rejection received
    "[DECLINED]",    # Offer turned down
]

# Named aliases for specific pipeline stages — page code references these
# instead of positional indices or literal strings (added Phase 4 T1-C).
STATUS_OPEN      = STATUS_VALUES[0]   # "[OPEN]"
STATUS_APPLIED   = STATUS_VALUES[1]   # "[APPLIED]"
STATUS_INTERVIEW = STATUS_VALUES[2]   # "[INTERVIEW]"

# Terminal = pipeline-end states; excluded from "active" queries
# (upcoming deadlines, materials readiness, etc.).
TERMINAL_STATUSES = ["[CLOSED]", "[REJECTED]", "[DECLINED]"]

# Status → Streamlit color name (valid for st.badge AND Plotly marker_color).
STATUS_COLORS = {
    "[OPEN]":      "blue",
    "[APPLIED]":   "orange",
    "[INTERVIEW]": "violet",
    "[OFFER]":     "green",
    "[CLOSED]":    "gray",
    "[REJECTED]":  "red",
    "[DECLINED]":  "gray",
}

# ── Controlled vocabularies ───────────────────────────────────────
PRIORITY_VALUES    = ["High", "Med", "Low", "Stretch"]   # "Med"→"Medium" planned for v0.5
WORK_AUTH_OPTIONS  = ["Any", "OPT", "J-1", "H1B", "No Sponsorship", "Ask"]
FULL_TIME_OPTIONS  = ["Yes", "No", "Part-time"]
SOURCE_OPTIONS     = [
    "Lab website", "AcademicJobsOnline", "HigherEdJobs",
    "LinkedIn", "Referral", "Conference", "Listserv", "Other",
]
RESPONSE_TYPES     = [
    "Acknowledgement", "Screening Call", "Interview Invite",
    "Rejection", "Offer", "Other",
]
# RESULT_DEFAULT must match DEFAULT in applications table DDL (C7 coupling).
RESULT_DEFAULT    = "Pending"
RESULT_VALUES     = [
    RESULT_DEFAULT,
    "Offer Accepted", "Offer Declined", "Rejected", "Withdrawn",
]
RELATIONSHIP_TYPES = [
    "PhD Advisor", "Committee Member", "Collaborator",
    "Postdoc Supervisor", "Department Faculty", "Other",
]

# ── Requirement document types ────────────────────────────────────
# Canonical DB values for req_* columns. Display order: "Required" first.
REQUIREMENT_VALUES = ["Y", "Optional", "N"]

# UI labels for each canonical value — used by st.radio(format_func=...).
REQUIREMENT_LABELS = {
    "Y":        "Required",
    "Optional": "Optional",
    "N":        "Not needed",
}

# Each tuple: (db_req_column, db_done_column, display_label).
# To add a new document type (e.g., Portfolio): append one tuple here.
# database.init_db() auto-migrates the schema; no other file needs changing.
REQUIREMENT_DOCS = [
    ("req_cv",                  "done_cv",                  "CV"),
    ("req_cover_letter",        "done_cover_letter",        "Cover Letter"),
    ("req_transcripts",         "done_transcripts",         "Transcripts"),
    ("req_research_statement",  "done_research_statement",  "Research Statement"),
    ("req_writing_sample",      "done_writing_sample",      "Writing Sample"),
    ("req_teaching_statement",  "done_teaching_statement",  "Teaching Statement"),
    ("req_diversity_statement", "done_diversity_statement", "Diversity Statement"),
]

# ── Quick-add form fields (must stay minimal — capture at discovery) ─
QUICK_ADD_FIELDS = [
    "position_name",   # text
    "institute",       # text
    "field",           # text
    "deadline_date",   # date
    "priority",        # select from PRIORITY_VALUES
    "link",            # text (URL)
]

# ── Opportunities edit panel ──────────────────────────────────────
# Tab labels + order for the inline edit panel on pages/1_Opportunities.py.
EDIT_PANEL_TABS = ["Overview", "Requirements", "Materials", "Notes"]

# ── Dashboard display thresholds ──────────────────────────────────
DEADLINE_ALERT_DAYS    = 30   # Show upcoming deadlines within this window
DEADLINE_URGENT_DAYS   = 7    # Color deadline red if within this many days
RECOMMENDER_ALERT_DAYS = 7    # Alert if asked N+ days ago, no submission yet
```

### 5.2 Invariants enforced at import time

`config.py` runs these assertions at module import; they catch drift
before any page renders:

1. `set(STATUS_VALUES) == set(STATUS_COLORS)` — every status has a color.
2. `set(TERMINAL_STATUSES) <= set(STATUS_VALUES)` — terminals are a subset.
3. `set(REQUIREMENT_LABELS) == set(REQUIREMENT_VALUES)` — every req value has a label.

**Planned (v1.1 refactor — C12):** add `DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS`.

### 5.3 Extension recipes

| Goal | What to edit |
|------|--------------|
| Add a new requirement document | Append one tuple to `REQUIREMENT_DOCS`; restart the app so `init_db()` migrates columns |
| Add a priority / source / response type | Append to the relevant vocabulary list |
| Add a new pipeline status | Append to `STATUS_VALUES` AND add an entry to `STATUS_COLORS`; decide if it's terminal (then add to `TERMINAL_STATUSES`) |
| Switch to `software_eng` profile | Change `TRACKER_PROFILE`; edit `REQUIREMENT_DOCS` / vocabularies as the new domain needs; no DB migration required for renamed columns (add new columns; old columns persist until you wipe the DB) |

---

## 6. Database Schema

> **Canonical definition:** `database.init_db()` in `database.py`. The DDL
> and column reference below mirror that code as of v0.4.0 (2026-04-23).
> If the code drifts from this doc, the code wins.
>
> **Known coupling (C6/C7, slated for v0.5 code cleanup):** the `positions.status`
> `DEFAULT '[OPEN]'` and `applications.result DEFAULT 'Pending'` are SQL literals —
> they are **not** read from `config.STATUS_VALUES[0]` / `config.RESULT_DEFAULT`.
> A rename in `config.py` does not propagate to the schema DEFAULTs. When renaming
> either constant, also update `init_db()` DDL and write a one-shot `UPDATE`
> migration for existing rows.

### Entity-Relationship Summary
```
positions (1) ──< applications (1)      one-to-one
positions (1) ──< recommenders (many)   one-to-many
```

### Full SQL

```sql
PRAGMA foreign_keys = ON;

-- ── Table 1: positions ─────────────────────────────────────────
-- One row per position. Combines overview (Table A) and
-- requirements + materials (Table B) from the markdown design.
CREATE TABLE IF NOT EXISTS positions (

    -- Identity & metadata
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    status           TEXT    NOT NULL DEFAULT '[OPEN]',
    priority         TEXT,
    created_at       TEXT    DEFAULT (date('now')),

    -- Overview (Table A equivalent)
    position_name    TEXT    NOT NULL,
    institute        TEXT,
    location         TEXT,
    field            TEXT,
    deadline_date    TEXT,       -- ISO-8601: 'YYYY-MM-DD'. Drives all time computations.
    deadline_note    TEXT,       -- Human context: "rolling after initial review"
    stipend          TEXT,
    work_auth        TEXT,
    full_time        TEXT,
    source           TEXT,
    link             TEXT,

    -- Details (Table B equivalent)
    mentor           TEXT,
    point_of_contact TEXT,
    portal_url       TEXT,       -- Submission portal URL (may differ from link)
    keywords         TEXT,
    description      TEXT,
    num_rec_letters  INTEGER,
    reference_code   TEXT,
    notes            TEXT,

    -- Requirements: 'Y' | 'N' | 'Optional'
    -- Column list is driven by config.REQUIREMENT_DOCS
    req_cv                   TEXT,
    req_cover_letter         TEXT,
    req_transcripts          TEXT,
    req_research_statement   TEXT,
    req_writing_sample       TEXT,
    req_teaching_statement   TEXT,
    req_diversity_statement  TEXT,

    -- Materials done: 0 = not ready, 1 = ready
    -- Readiness is COMPUTED (query) not stored as a summary field
    done_cv                  INTEGER DEFAULT 0,
    done_cover_letter        INTEGER DEFAULT 0,
    done_transcripts         INTEGER DEFAULT 0,
    done_research_statement  INTEGER DEFAULT 0,
    done_writing_sample      INTEGER DEFAULT 0,
    done_teaching_statement  INTEGER DEFAULT 0,
    done_diversity_statement INTEGER DEFAULT 0
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
    result               TEXT    DEFAULT 'Pending',
    notes                TEXT,
    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
);

-- ── Table 3: recommenders ──────────────────────────────────────
-- Many rows per position. One row per (position × recommender) pair.
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

-- ── Indices ────────────────────────────────────────────────────
-- These two columns are queried most often (dashboard, filters)
CREATE INDEX IF NOT EXISTS idx_positions_status   ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_deadline ON positions(deadline_date);
```

### Schema Design Notes
| Decision | Reason |
|----------|--------|
| `deadline_date` is ISO text, not a DATE column | SQLite has no native DATE type; ISO strings sort and compare correctly as text |
| `done_*` columns are `INTEGER 0/1` | SQLite has no BOOLEAN; readiness is computed as a query, not stored as a summary |
| Separate `applications` table (not merged into `positions`) | Different update cadence; different concern: positions = "what exists", applications = "what you did" |
| `ON DELETE CASCADE` on both child tables | Deleting a position removes its application row and all recommender rows automatically |
| Auto-create `applications` row on `add_position()` | Guarantees every position always has a matching row; avoids NULL-check overhead in queries |

---

## 7. Module Contracts

### `database.py` — Public Function Signatures

```python
from pathlib import Path
import sqlite3
import pandas as pd

DB_PATH: Path                          # resolved relative to database.py location

# ── Init ──────────────────────────────────────────────────────────
def init_db() -> None:
    """Create tables and indices if they don't exist. Safe to call on every start."""

# ── Positions ─────────────────────────────────────────────────────
def add_position(fields: dict) -> int:
    """Insert a new position row and its blank applications row.
    Returns the new position id. Calls exports.write_all()."""

def get_all_positions() -> pd.DataFrame:
    """Return all positions ordered by deadline_date ASC, NULLs last."""

def get_position(position_id: int) -> dict:
    """Return a single position as a dict. Raises KeyError if not found."""

def update_position(position_id: int, fields: dict) -> None:
    """Update provided fields on an existing position. Calls exports.write_all()."""

def delete_position(position_id: int) -> None:
    """Delete position and cascade-delete its application + recommender rows.
    Calls exports.write_all()."""

# ── Applications ──────────────────────────────────────────────────
def get_application(position_id: int) -> dict:
    """Return the application row for a position as a dict."""

def upsert_application(position_id: int, fields: dict) -> None:
    """INSERT or UPDATE the application row for a position.
    Calls exports.write_all()."""

# ── Recommenders ──────────────────────────────────────────────────
def add_recommender(position_id: int, fields: dict) -> int:
    """Insert a new recommender row. Returns new id. Calls exports.write_all()."""

def get_recommenders(position_id: int) -> pd.DataFrame:
    """Return all recommenders for a given position."""

def get_all_recommenders() -> pd.DataFrame:
    """Return all recommender rows joined with position_name and institute."""

def update_recommender(rec_id: int, fields: dict) -> None:
    """Update provided fields on an existing recommender row. Calls exports.write_all()."""

def delete_recommender(rec_id: int) -> None:
    """Delete a single recommender row. Calls exports.write_all()."""

# ── Dashboard queries ─────────────────────────────────────────────
def count_by_status() -> dict[str, int]:
    """Return {status_value: count} for all positions."""

def get_upcoming_deadlines(days: int = config.DEADLINE_ALERT_DAYS) -> pd.DataFrame:
    """Return non-terminal positions with deadline_date within the next
    `days` days, ordered by deadline_date ASC.
    Excludes positions whose status is in config.TERMINAL_STATUSES."""

def get_upcoming_interviews() -> pd.DataFrame:
    """Return application rows where interview1_date or interview2_date
    is in the future, ordered by date ASC."""

def get_pending_recommenders(days: int) -> pd.DataFrame:
    """Return recommender rows where asked_date was >= `days` ago
    and submitted_date IS NULL, joined with position_name."""

def compute_materials_readiness() -> dict[str, int]:
    """Return {"ready": N, "pending": M} for active positions.
    Active = status in (config.STATUS_OPEN, STATUS_APPLIED, STATUS_INTERVIEW).
    A position is "ready" if every document where req_* = 'Y' has done_* = 1.
    Only positions with at least one required doc (req_* = 'Y') are counted —
    a position with all docs set to 'N' contributes to neither ready nor pending."""
```

### `exports.py` — Public Function Signatures

```python
def write_all() -> None:
    """Write all three markdown export files. Called by database.py after every write."""

def write_opportunities() -> None:
    """Generate exports/OPPORTUNITIES.md from positions table."""

def write_progress() -> None:
    """Generate exports/PROGRESS.md from positions + applications tables."""

def write_recommenders() -> None:
    """Generate exports/RECOMMENDERS.md from recommenders table."""
```

---

## 8. UI Design — Page by Page

### `app.py` — Dashboard (Home)

**Purpose:** Answer "What do I do today?" in one glance.

```
╔════════════════════════════════════════════════════════════════╗
║  Postdoc Tracker                              [🔄 Refresh]    ║
╠══════════════╦══════════════╦══════════════╦═══════════════════╣
║  12          ║  4           ║  2           ║  May 3 · MIT      ║
║  Tracked     ║  Applied     ║  Interview   ║  Next Interview   ║
║              ║              ║  Stage       ║                   ║
╠══════════════╩══════════════╩══════════════╩═══════════════════╣
║                                                                ║
║  Application Funnel         ║  Materials Readiness            ║
║                             ║                                 ║
║  [OPEN]      ████████  8    ║  Ready to submit  ███  3        ║
║  [APPLIED]   ██████    4    ║  Still missing    █████ 5       ║
║  [INTERVIEW] ████      2    ║                                 ║
║  [OFFER]     ██        1    ║  [→ Opportunities page]         ║
║                             ║                                 ║
╠═════════════════════════════╩═════════════════════════════════╣
║  Upcoming (next 30 days)                                       ║
║                                                                ║
║  Apr 24  Stanford BioStats   [OPEN]     deadline    9d  🔴    ║
║  May 3   Stanford BioStats   [APPLIED]  Interview  18d        ║
║  May 15  MIT CSAIL           [OPEN]     deadline   30d        ║
║                                                                ║
╠════════════════════════════════════════════════════════════════╣
║  Recommender Alerts                                            ║
║                                                                ║
║  ⚠  Dr. Smith  →  Stanford, MIT CSAIL  (asked 14 days ago)    ║
║  ✓  Dr. Jones  →  Stanford             (submitted Apr 20)      ║
╚════════════════════════════════════════════════════════════════╝
```

**Panel specifications:**

| Panel | Data source | Trigger for red/warning |
|-------|------------|------------------------|
| KPI cards | `count_by_status()`, `get_upcoming_interviews()` | "Next Interview" blank if none scheduled |
| Funnel | `count_by_status()` | Color from `STATUS_COLORS` in config |
| Materials Readiness | `compute_materials_readiness()` | "Still missing" bar always present |
| Upcoming | `get_upcoming_deadlines()` + `get_upcoming_interviews()` merged | Red 🔴 if ≤ `DEADLINE_URGENT_DAYS` days away |
| Recommender Alerts | `get_pending_recommenders(RECOMMENDER_ALERT_DAYS)` | Grouped by recommender name |

---

### `pages/1_Opportunities.py` — Positions

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
║  Stanford BioStats    Stanford   🟡 High   [APPLIED]  ——       ║
║  MIT CSAIL Postdoc    MIT        🟡 High   [OPEN]     May 15   ║
║  ··· (click row to expand) ···                                 ║
║                                                                ║
║  ┌──── Stanford BioStats Postdoc  ·  [APPLIED]  ────────────┐ ║
║  │  [ Overview ] [ Requirements ] [ Materials ] [ Notes ]    │ ║
║  │  ──────────────────────────────────────────────────────── │ ║
║  │  (tab content — full edit form fields)                    │ ║
║  │                              [ Save Changes ] [ Delete ]  │ ║
║  └───────────────────────────────────────────────────────────┘ ║
╚════════════════════════════════════════════════════════════════╝
```

**Behaviour specifications:**

| Element | Behaviour |
|---------|-----------|
| Quick-add | Shows only `QUICK_ADD_FIELDS` from config; saves with `status='[OPEN]'`; auto-creates blank `applications` row |
| Table | Sorted by deadline_date ASC; deadline cell red if ≤ `DEADLINE_URGENT_DAYS` days away |
| Row click | Expands inline below the row; one expansion at a time |
| Status dropdown | `st.selectbox(options=STATUS_VALUES)` — never freetext |
| All date inputs | `st.date_input()` — returns Python `date`, stored as `.isoformat()` |
| Requirements tab | Checkboxes: Y / N / Optional for each doc type in `REQUIREMENT_DOCS` |
| Materials tab | Checkboxes: done or not, shown only for docs where `req_* = 'Y'`; shows readiness score |
| Delete | Confirmation dialog before calling `database.delete_position()` |

---

### `pages/2_Applications.py` — Progress

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

**Behaviour specifications:**
- Default filter: show all positions except `[OPEN]` and `[CLOSED]`
- Saving an application update that changes `response_type` to "Offer" automatically prompts the user to update `positions.status` to `[OFFER]`
- Status changes here write to both `applications` and `positions` tables

---

### `pages/3_Recommenders.py` — Recommenders

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

**Behaviour specifications:**
- Alert panel grouped by recommender (not by position), so one recommender who owes 3 letters shows as one entry with all positions listed
- "Compose reminder email" opens `mailto:` link — no email integration required
- Add-recommender form prefills position from dropdown (position_name shown, not id)
- Clicking a row expands inline edit (asked_date, confirmed, submitted_date, reminder_sent, notes)

---

### `pages/4_Export.py` — Export

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
║  [ ⬇ OPPORTUNITIES.md ]   Last generated: 2026-04-15 14:32    ║
║  [ ⬇ PROGRESS.md ]        Last generated: 2026-04-15 14:32    ║
║  [ ⬇ RECOMMENDERS.md ]    Last generated: 2026-04-15 14:32    ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 9. Data Flow

### Adding a new position (quick-add path)
```
User fills 6 fields → st.form submit
  → database.add_position(fields)
      → INSERT INTO positions (6 fields + defaults)
      → INSERT INTO applications (position_id, all NULLs)
      → exports.write_all()
          → exports/OPPORTUNITIES.md regenerated
          → exports/PROGRESS.md regenerated
          → exports/RECOMMENDERS.md regenerated
  → st.rerun() → table refreshes with new row
```

### Dashboard load
```
app.py starts
  → database.init_db()           (no-op if tables exist)
  → database.count_by_status()   → KPI cards + funnel
  → database.compute_materials_readiness()  → readiness panel
  → database.get_upcoming_deadlines(30)     ┐
  → database.get_upcoming_interviews()      ├→ merged timeline
  → database.get_pending_recommenders(7)    → alerts panel
```

### Status change (applications page)
```
User updates response_type to "Offer" and saves
  → database.upsert_application(pos_id, fields)
      → UPDATE applications SET ...
      → exports.write_all()
  → page detects response_type == "Offer"
  → st.warning("Update position status to [OFFER]?")
  → User confirms → database.update_position(pos_id, {"status": "[OFFER]"})
      → UPDATE positions SET status = '[OFFER]'
      → exports.write_all()
```

> **Design TBD for Phase 5 (C13):** the "page detects response_type == 'Offer'
> and prompts" step puts cross-table business logic in the page file, which
> conflicts with GUIDELINES §2 "page files — display only." Two options:
>
> - **Option A (keep in page):** the prompt is a UX concern, not business logic —
>   the underlying writes stay atomic in `database.py`. Accept a narrow carve-out.
> - **Option B (move to database.py):** add a
>   `upsert_application(..., propagate_status: bool = True)` kwarg. The cascade
>   becomes atomic and the page stays dumb.
>
> Decide before Phase 5 builds the Applications page. Recommended: **Option B**
> (atomicity + testability); will be logged as an ADR when the decision lands.

---

## 10. Design Decisions Log

> **Namespace note (added v1.1, 2026-04-23):** The `D1`–`D10` entries below are the
> original v1.0 architectural decisions and retain their bare numbering.
> Decisions made **during implementation phases** are namespaced by phase:
> `P3-D1`, `P4-D1`, etc. (see `CLAUDE.md` / phase review docs).
> Decisions made **from v1.1 forward** land in `docs/adr/` as
> `ADR-NNNN` files (Michael-Nygard format). An entry should appear in only
> one of these systems at a time; avoid cross-listing.

| ID | Decision | Rationale | Alternative considered |
|----|----------|-----------|----------------------|
| D1 | All field/vocab definitions in `config.py` | Open/Closed Principle — extend by editing one file | Hardcoded in each page file — fails when generalising |
| D2 | `deadline_date` as ISO text, separate from `deadline_note` | All "X days away" computations need a real date; context note is separate concern | Single freetext `deadline_window` field — cannot compute on it |
| D3 | `done_*` columns are `INTEGER 0/1`; readiness is computed | Avoids stale summary fields; single source of truth | Stored `materials_ready` text field — desynchronises |
| D4 | `exports.write_all()` called inside every `database.py` write | Markdown files are always current; no manual sync needed | On-demand export only — backup exists only after Phase 6 |
| D5 | IDs are internal; UI shows names | Users never need to know or type database IDs | User-managed P001 codes — error-prone, sync burden |
| D6 | Quick-add form has exactly 6 fields | Capture must cost < 30 seconds; enrichment happens later | Full form on add — high friction, positions get lost |
| D7 | Status via `st.selectbox(STATUS_VALUES)` | Typo in status silently breaks funnel chart | Free text input — undetectable corruption |
| D8 | `ON DELETE CASCADE` on child tables | Deleting a position cleans up all related rows automatically | Manual delete in all three tables — easy to orphan rows |
| D9 | Separate `applications` table (not merged into `positions`) | Different update cadence; different concern | Single wide table — harder to query, harder to reason about |
| D10 | Auto-create `applications` row on `add_position()` | Every position always has a matching row; no NULL-check overhead | Create on first update — requires NULL handling everywhere |

---

## 11. Extension Guide

### Adding a new document requirement type
1. Open `config.py`
2. Append to `REQUIREMENT_DOCS`:
   ```python
   ("req_portfolio", "done_portfolio", "Portfolio"),
   ```
3. Run `database.init_db()` — the new columns appear in the schema automatically
4. The Requirements tab, Materials tab, readiness computation, and markdown export all pick it up without code changes

### Adding a new vocabulary option
1. Open `config.py`
2. Append to the relevant list (e.g., `WORK_AUTH_OPTIONS`, `SOURCE_OPTIONS`)
3. The relevant `st.selectbox()` in the page file picks it up on next render

### Switching to a general job tracker profile
1. Open `config.py`
2. Change `TRACKER_PROFILE = "software_eng"` (note: currently unused; C2)
3. Update `REQUIREMENT_DOCS` to remove postdoc-specific docs and add new ones (e.g., `req_coding_challenge`)
4. Update `QUICK_ADD_FIELDS` if the default-capture set should differ, plus
   relevant vocabulary lists (e.g., add `"remote_ok"` to a new `FULL_TIME_OPTIONS` entry
   or create a `REMOTE_OPTIONS` list)
5. For postdoc-specific columns that no longer make sense (`mentor`, `stipend`), the
   schema retains them — they'll be NULL. A future profile-aware `init_db()` could
   conditionally include them; v1 leaves the columns and hides them from the UI.
6. No changes to `database.py`, `exports.py`, or any page file beyond removing the
   unused columns from page forms.

### Adding a new tracker profile (postdoc + software simultaneously)
The current design supports one active profile. A future v2 could add a `profile` column to the `positions` table, allowing mixed-profile tracking within one database. This is a schema migration, not an architectural change.

### Adding file attachments to the Materials panel (deferred — see roadmap backlog)
Today the Materials tab is checkbox-only (`done_* INTEGER 0/1`). A future version can let the user attach the actual document (PDF / Markdown / TeX) without rewriting existing tabs.

**Approach:** files on local disk, paths in DB.

1. Add `ATTACHMENT_FORMATS = {"pdf", "md", "tex"}` and `ATTACHMENT_MAX_MB = 10` to `config.py`.
2. Add a new table in `database.init_db()`:
   ```sql
   attachments(
     id INTEGER PRIMARY KEY,
     position_id INTEGER NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
     doc_type TEXT NOT NULL,        -- key from REQUIREMENT_DOCS
     file_path TEXT NOT NULL,       -- relative: attachments/<position_id>/<doc_type>.<ext>
     file_format TEXT NOT NULL,     -- one of ATTACHMENT_FORMATS
     uploaded_at TEXT NOT NULL,
     UNIQUE(position_id, doc_type)
   )
   ```
3. Add three functions to `database.py`: `save_attachment`, `get_attachment`, `delete_attachment`. Each calls `exports.write_all()` for parity with other writers.
4. Create `attachments/` folder at project root; add to `.gitignore` like `postdoc.db`.
5. In `pages/1_Opportunities.py` Materials tab, add `st.file_uploader(type=list(config.ATTACHMENT_FORMATS))` per required-doc row, plus Open / Replace / Remove buttons when a file exists. A successful upload auto-flips the checkbox to `done = 1` (still user-overridable).
6. Delete cascade already removes attachment rows; add `shutil.rmtree(f"attachments/{position_id}")` to the delete-position path so orphaned files are cleaned.

**Why filesystem, not BLOB:** keeps `postdoc.db` small, lets the user open files in their native editor, makes manual backup obvious. Trade-off: backup script must include `attachments/` alongside `postdoc.db`.

**Non-goals:** in-app editing of attached files, version history, cloud sync. The user edits files in their preferred editor and re-uploads.
