# System Design: Postdoc Application Tracker
**Version:** 1.4 | **Last updated:** 2026-04-30 | **Status:** v1 target design (authoritative)

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
Postdoc search = track dozens positions parallel, diff institutions, each w/ unique deadlines, requirement checklists, rec letter logistics, outcome timelines. Markdown alone no answer daily question: **"What do I do today?"**

### Solution
Local single-user web app:
- Capture new positions <30s
- Auto-compute + surface urgent actions
- Track rec letter status per recommender, per position
- Maintain human-readable markdown exports as portable backup
- Extensible to general job tracker via single config file edit

### Explicit Non-Goals (v1)
- No auth
- No cloud deploy
- No mobile-first layout
- No email/calendar integration
- No multi-user

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

---

## 3. Technology Stack

| Component | Choice | Required ≥ | Rationale |
|-----------|--------|-----------|-----------|
| Language | Python | 3.14 | Already there; familiar to stats/data users |
| Environment | venv (`.venv/`) | stdlib | Zero extra tools; isolates pkgs; gitignored |
| UI framework | Streamlit | 1.50 | Python-native; `width="stretch"` and `st.switch_page` need ≥ 1.50 |
| Charts | Plotly (Graph Objects) | 5.22 | Used via `plotly.graph_objects.Figure` / `go.Bar`; click events for future interactivity |
| Data frames | pandas | 2.2 | Bridges SQLite rows ↔ Streamlit display widgets |
| Database | SQLite via `sqlite3` | stdlib | No server; single file; standard SQL; gitignored |

Pinned versions in `requirements.txt`; `Required ≥` col = min known-working version, floor for any dep upgrade policy.

### 3.1 Runtime assumptions

| Assumption | Value | Notes |
|------------|-------|-------|
| Expected scale | 10²–10³ positions, 1–10 interviews each, 1–20 recommenders total | SQLite handles fine; no perf tuning needed |
| File encoding | UTF-8 everywhere | `postdoc.db` binary; all markdown exports + `config.py` UTF-8 |
| Timezone | Local machine time | Single-user local; no cross-tz concerns. |
| Concurrency | One writer at a time (Streamlit process) | SQLite default serialization sufficient; no multi-thread/multi-proc writers |
| Persistence | `postdoc.db` on local disk | Loss-protect via committed markdown exports; cloud backup = v2 (§12.5) |

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

`exports/*.md` committed (human-readable DB backup). `postdoc.db`, `.venv/`, `.env*`, `__pycache__/` gitignored. See `.gitignore` for full list.

---

## 5. `config.py` — Specification

`config.py` = **single source of truth** for vocab, constants, field defs. Every other module reads from it; no other file hardcodes status string, priority value, or req-doc label.

### 5.1 Symbol index

#### Tracker identity

| Constant | Type | Role |
|----------|------|------|
| `TRACKER_PROFILE` | `str` | Profile discriminator; v1 = `"postdoc"`. Extension hook for v2+ profile variants (§12.1). |
| `VALID_PROFILES` | `set[str]` | Import-time validation set for `TRACKER_PROFILE`; guarded by §5.2 invariant #1. |

#### Status pipeline

| Constant | Type | Role |
|----------|------|------|
| `STATUS_VALUES` | `list[str]` | Ordered pipeline: `[SAVED]` → `[APPLIED]` → `[INTERVIEW]` → `[OFFER]` → `[CLOSED]` → `[REJECTED]` → `[DECLINED]`. Index = pipeline position. Referenced by §6.2 DDL `DEFAULT` clause, §8.1 funnel, §9.3 auto-promotion rules. |
| `STATUS_SAVED` / `STATUS_APPLIED` / `STATUS_INTERVIEW` / `STATUS_OFFER` / `STATUS_CLOSED` / `STATUS_REJECTED` / `STATUS_DECLINED` | `str` | One named alias per `STATUS_VALUES[i]`. Page code uses these not literals — anti-typo guardrail enforced by pre-merge grep. |
| `TERMINAL_STATUSES` | `list[str]` | Subset of `STATUS_VALUES` (`[CLOSED]` / `[REJECTED]` / `[DECLINED]`). Excluded from "active" queries (upcoming deadlines, materials readiness); also guards R3 auto-promotion against regression (§9.3). |
| `STATUS_COLORS` | `dict[str, str]` | Per-status color for single-status surfaces (Opportunities-table badge, tooltips). Values from intersection of `st.badge` color vocab + Plotly CSS color names. **Not** for funnel bars — see `FUNNEL_BUCKETS`. Drift caught by §5.2 invariant #2. |
| `STATUS_LABELS` | `dict[str, str]` | Storage→UI label. Storage keeps bracketed values as enum sentinels; UI strips brackets via this dict. Every status surface rendered to user MUST go through this map — never print raw key. Drift caught by §5.2 invariant #3. |
| `STATUS_FILTER_ACTIVE` | `str` | UI sentinel (`"Active"`) used as default selection on Applications page filter selectbox (§8.3). Encodes "every actionable status" — page resolves to `set(STATUS_VALUES) - STATUS_FILTER_ACTIVE_EXCLUDED` at render time. Defensive guard §5.2 invariant #12 ensures sentinel no collide w/ real `STATUS_VALUES` entry. |
| `STATUS_FILTER_ACTIVE_EXCLUDED` | `frozenset[str]` | Statuses removed by `STATUS_FILTER_ACTIVE` sentinel — `{STATUS_SAVED, STATUS_CLOSED}` (pre-application + withdrawn). Frozen so page cannot silently broaden filter at runtime. Membership = part of spec (§8.3); broadening exclusion (e.g. also exclude `[REJECTED]`/`[DECLINED]`) = deliberate spec amendment. Drift caught by §5.2 invariant #12. |

#### Dashboard funnel (presentation layer)

| Constant | Type | Role |
|----------|------|------|
| `FUNNEL_BUCKETS` | `list[tuple[str, tuple[str, ...], str]]` | Presentation-layer grouping of raw statuses into funnel bars. Each entry: `(UI label, raw-status tuple, bucket color)`. Order = top-down display order (y-axis reversed). "Archived" aggregates `[REJECTED]` + `[DECLINED]` (D17); `[CLOSED]` stays own bucket. Multiset coverage of `STATUS_VALUES` guarded by §5.2 invariant #5. |
| `FUNNEL_DEFAULT_HIDDEN` | `set[str]` | Bucket labels hidden by default on dashboard funnel. Single disclosure toggle (§8.1) reveals/hides as group; state held in `st.session_state["_funnel_expanded"]` for current session only (D24, §8.1). Validated by §5.2 invariant #6. |
| `FUNNEL_TOGGLE_LABELS` | `dict[bool, str]` | State-keyed labels for funnel disclosure toggle (§8.1). Indexed by bool of `st.session_state["_funnel_expanded"]`: `False` → `"+ Show all stages"` (collapsed; click invites expand); `True` → `"− Show fewer stages"` (expanded; click invites collapse). Vocab follows project's `<symbol> <verb-phrase>` CTA convention. Validated by §5.2 invariant #11. |

#### Vocabularies (user-facing selectbox options)

| Constant | Type | Role |
|----------|------|------|
| `PRIORITY_VALUES` | `list[str]` | User subjective fit — `High` / `Medium` / `Low` / `Stretch`. Stored; distinct from computed urgency. |
| `WORK_AUTH_OPTIONS` | `list[str]` | Three-value categorical (`Yes` / `No` / `Unknown`) answering "does posting accept this applicant's work auth?" Paired w/ freetext `work_auth_note` for nuance (D22). |
| `FULL_TIME_OPTIONS` | `list[str]` | Employment type: `Full-time` / `Part-time` / `Contract`. |
| `SOURCE_OPTIONS` | `list[str]` | Where posting found (lab site, job board, referral, etc.). Fuels P3 "source effectiveness" analytic in §12.7. |
| `RESPONSE_TYPES` | `list[str]` | First-response categorization. Value `"Offer"` fires auto-promotion R3 (§9.3); referenced from `database.py` via `RESPONSE_TYPE_OFFER` alias below. |
| `RESPONSE_TYPE_OFFER` | `str` | Named alias for R3 cascade trigger (`"Offer"`) — anti-typo guardrail mirroring `STATUS_*` alias pattern so `database.upsert_application` insulated from future rename of `RESPONSE_TYPES` entry. Drift caught by §5.2 invariant #9. |
| `RESULT_DEFAULT` | `str` | `"Pending"` — matches `applications.result` schema `DEFAULT` clause; rename needs one-shot `UPDATE` migration (§6.3). |
| `RESULT_VALUES` | `list[str]` | Final app outcome; starts with `RESULT_DEFAULT`, then accepted / declined / rejected / withdrawn. |
| `RELATIONSHIP_VALUES` | `list[str]` | Recommender→applicant relationship (advisor / committee / collaborator / …). |
| `INTERVIEW_FORMATS` | `list[str]` | Vocab for `interviews.format` col: `Phone` / `Video` / `Onsite` / `Other`. |

#### Requirement documents

| Constant | Type | Role |
|----------|------|------|
| `REQUIREMENT_VALUES` | `list[str]` | Canonical DB values for `req_*` cols: `Yes` / `Optional` / `No`. |
| `REQUIREMENT_LABELS` | `dict[str, str]` | UI labels for three canonical values. Radios use `format_func=REQUIREMENT_LABELS.get` so `session_state` holds DB value — no save-time translation. Drift caught by §5.2 invariant #7. |
| `REQUIREMENT_DOCS` | `list[tuple[str, str, str]]` | Doc-type schema driver: `(req_column, done_column, display_label)` per doc type. Append one tuple = whole contract for adding new doc type — `init_db()` auto-adds both cols on next start (§6.3). |

#### Forms and UI structure

| Constant | Type | Role |
|----------|------|------|
| `QUICK_ADD_FIELDS` | `list[str]` | Col names shown in quick-add form. Ordered: `position_name`, `institute`, `field`, `deadline_date`, `priority`, `link`. Keep ≤ 6 = capture-friction design rule (D6). |
| `EDIT_PANEL_TABS` | `list[str]` | Tab labels for Opportunities edit panel in display order: `Overview`, `Requirements`, `Materials`, `Notes`. |

#### Dashboard thresholds (days)

| Constant | Type | Role |
|----------|------|------|
| `DEADLINE_ALERT_DAYS` | `int` | Default upcoming-window width + upper edge of 🟡 urgency band. Deadline within this many days surfaces on Upcoming panel (§8.1) when panel's window selectbox at default. |
| `DEADLINE_URGENT_DAYS` | `int` | Inner urgency band. Deadline within this many days flagged 🔴; between this and `DEADLINE_ALERT_DAYS` = 🟡. Inclusive on narrower band: exactly N days away → urgent. Ordering guarded by §5.2 invariant #8. Urgency thresholds **fixed in config** — no track user-selected Upcoming window. |
| `RECOMMENDER_ALERT_DAYS` | `int` | Recommender asked ≥ this many days ago, no submitted letter → surfaces on Recommender Alerts (§8.1). |
| `UPCOMING_WINDOW_OPTIONS` | `list[int]` | User-selectable widths for Upcoming panel's window selectbox (§8.1). Default values: `[30, 60, 90]`. Panel selectbox defaults to `DEADLINE_ALERT_DAYS` (must be in this list — §5.2 invariant #10) and lets user widen view to 60 or 90 days. Urgency-glyph band NOT tied to this — wider window surfaces more rows but band thresholds stay at `DEADLINE_URGENT_DAYS` / `DEADLINE_ALERT_DAYS`. |

### 5.2 Import-time invariants

`config.py` runs these assertions at module import. Violation aborts app startup w/ clear traceback — catches drift before any page renders:

1. `TRACKER_PROFILE in VALID_PROFILES` — profile = known value
2. `set(STATUS_VALUES) == set(STATUS_COLORS)` — every status has per-status color
3. `set(STATUS_VALUES) == set(STATUS_LABELS)` — every status has UI label
4. `set(TERMINAL_STATUSES) <= set(STATUS_VALUES)` — terminals = subset
5. Let `F = [raw for (_, raws, _) in FUNNEL_BUCKETS for raw in raws]`. Require `sorted(F) == sorted(STATUS_VALUES)` (multiset equality).
6. `FUNNEL_DEFAULT_HIDDEN <= {label for label, _, _ in FUNNEL_BUCKETS}` — hidden-by-default set references real bucket labels
7. `set(REQUIREMENT_LABELS) == set(REQUIREMENT_VALUES)` — every req value has label
8. `DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS` — urgency thresholds order correctly
9. `RESPONSE_TYPE_OFFER in RESPONSE_TYPES` — R3 cascade trigger (§9.3) must be real `RESPONSE_TYPES` selectbox option; catches rename that drops `"Offer"` w/o updating alias
10. `DEADLINE_ALERT_DAYS in UPCOMING_WINDOW_OPTIONS` — Upcoming-panel selectbox default (= `DEADLINE_ALERT_DAYS`) must be real option in offered list; catches config edit that removes 30 from list w/o updating default
11. `set(FUNNEL_TOGGLE_LABELS.keys()) == {True, False}` — funnel disclosure toggle (§8.1) reads label as `FUNNEL_TOGGLE_LABELS[st.session_state["_funnel_expanded"]]` per render. Missing key → render-time `KeyError` on first toggle into that state; extra key → silent no-op. Caught at import.
12. `STATUS_FILTER_ACTIVE_EXCLUDED <= set(STATUS_VALUES)` — Applications-page "Active" filter sentinel (§8.3) excludes statuses in this frozenset; every entry must be real `STATUS_VALUES` member. Unknown entry → silent fail to filter at render time (unknown status never matches row), so guard fires at import-time instead.

### 5.3 Extension recipes

| Goal | What to edit |
|------|--------------|
| Add new requirement document | Append one tuple to `REQUIREMENT_DOCS`. On next app start, `init_db()` adds `req_*` / `done_*` cols via migration loop. No other file changes. |
| Add a priority / source / response-type / relationship / interview-format option | Append to relevant list. Dropdowns pick up on next render. No DB change — cols are plain TEXT. |
| Add a new pipeline status | (1) Append to `STATUS_VALUES` and add matching `STATUS_<name>` alias; (2) add one entry each to `STATUS_COLORS` and `STATUS_LABELS`; (3) decide which `FUNNEL_BUCKETS` entry it belongs in — extend existing bucket's tuple or add new 3-tuple `(label, (raw,...), color)` in right display position; (4) if terminal, append to `TERMINAL_STATUSES`. No DDL change. |
| Rename a pipeline status | Edit `STATUS_VALUES[i]`, matching alias, and keys in `STATUS_COLORS` / `STATUS_LABELS` / `FUNNEL_BUCKETS` / `TERMINAL_STATUSES`. Write one-shot migration in `CHANGELOG.md` under release: `UPDATE positions SET status = '<new>' WHERE status = '<old>'`. Schema `DEFAULT` clause = config-driven; no DDL edit needed if renaming `STATUS_VALUES[0]`. |
| Hide or un-hide a funnel bucket by default | Edit `FUNNEL_DEFAULT_HIDDEN`. Values must be existing bucket labels. |
| Rephrase the funnel disclosure toggle | Edit both keys of `FUNNEL_TOGGLE_LABELS`. Stay within `<symbol> <verb-phrase>` CTA convention (matches `+ Add your first position` and `→ Opportunities page`). `+` / `−` pairing recommended — symbol encodes click effect direction — but invariant #11 only enforces dict shape, not symbol choice. |
| Change a dashboard threshold | Edit `DEADLINE_*` or `RECOMMENDER_ALERT_DAYS`. Import-time invariants catch inverted thresholds. |
| Switch the tracker profile | See §12.1. |

---

## 6. Database Schema

Canonical DDL lives in `database.init_db()`. This section = architectural description of that DDL.

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
    status           TEXT    NOT NULL DEFAULT '<STATUS_SAVED>',   -- placeholder: interpolated from config
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
    result                 TEXT    DEFAULT '<RESULT_DEFAULT>',   -- placeholder: interpolated from config
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
    relationship        TEXT,                   -- from config.RELATIONSHIP_VALUES
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

**DDL DEFAULTs = config-driven.** `init_db()` builds `CREATE TABLE` statements via f-strings reading `config.STATUS_VALUES[0]` and `config.RESULT_DEFAULT`. Col names for `req_*` / `done_*` pairs come from `config.REQUIREMENT_DOCS`. No user-supplied value ever reaches DDL; `config.py` = only string source.

### 6.3 Data migrations

`init_db()` idempotent — safe to call on every app start. Schema evolution = one of three shapes:

**Auto-migrated (handled by `init_db()` on next start):**

| Change | Mechanism |
|--------|-----------|
| New entry in `config.REQUIREMENT_DOCS` | `ALTER TABLE positions ADD COLUMN req_<x> TEXT DEFAULT 'No'` + `ADD COLUMN done_<x> INTEGER DEFAULT 0`, guarded by `PRAGMA table_info` existence check |
| Brand-new table | `CREATE TABLE IF NOT EXISTS <name> (...)` in `init_db()` |
| Brand-new trigger or index | `CREATE TRIGGER / INDEX IF NOT EXISTS` in `init_db()` |
| New entry in any vocab list (`SOURCE_OPTIONS`, `RESPONSE_TYPES`, `INTERVIEW_FORMATS`, etc.) | No DDL — cols plain TEXT; dropdowns pick up on next render |
| New top-level cols on existing table when config or schema adds them | `ALTER TABLE ... ADD COLUMN` guarded by `PRAGMA table_info`, parallel to REQUIREMENT_DOCS loop |

**Manual (requires migration step, recorded in CHANGELOG):**

| Change | Required step |
|--------|---------------|
| Rename status value | One-shot `UPDATE positions SET status = '<new>' WHERE status = '<old>'`. Schema DEFAULT = config-driven, so no DDL edit. |
| Rename `RESULT_DEFAULT` | One-shot `UPDATE applications SET result = '<new>' WHERE result = '<old>'`. |
| Split dual-purpose col | (a) `ALTER TABLE ... ADD COLUMN` for new cols; (b) one-shot `UPDATE` translating old col values into new cols; (c) leave old col NULL until follow-up release rebuilds table to drop it. |
| Normalize flat cols into sub-table | (a) `CREATE TABLE` new sub-table; (b) `INSERT INTO` copying old cols; (c) leave old cols NULL until rebuild drops them; (d) update app code to read from sub-table. |
| Remove a col | SQLite needs table rebuild: `CREATE TABLE new AS SELECT <kept cols> FROM <t>; DROP TABLE <t>; ALTER TABLE new RENAME TO <t>`. Breaking change — document in CHANGELOG. |

**Migration discipline:** every schema or vocab change lands w/ `Migration:` note in `CHANGELOG.md` under release that introduces it, giving exact `UPDATE` or rebuild SQL. User upgrading between releases never has to guess which migration to run.

### 6.4 Schema design decisions

Storage decisions affecting this schema recorded in [§10 Key Architectural Decisions](#10-key-architectural-decisions): D2, D3, D8, D9, D10, D11, D16, D18, D19, D20, D21, D22, D23, D25. Each entry in §10 gives decision, rationale, alternative rejected — this section intentionally no restate them.

---

## 7. Module Contracts

### `database.py`

**Role.** All SQLite I/O. No Streamlit imports; no display logic. Reads + writes SQLite DB file only — other filesystem I/O belongs in `exports.py`. Readers return pandas DataFrames for multi-row queries, plain dicts for single-row lookups. Writers return new row id (inserts) or `None` (updates, deletes).

**Public API (grouped by concern):**

| Group | Functions |
|-------|-----------|
| Schema lifecycle | `init_db` |
| Positions | `add_position`, `get_all_positions`, `get_position`, `update_position`, `delete_position` |
| Applications | `get_application`, `upsert_application`, `is_all_recs_submitted` |
| Interviews | `add_interview`, `get_interviews`, `update_interview`, `delete_interview` |
| Recommenders | `add_recommender`, `get_recommenders`, `get_all_recommenders`, `update_recommender`, `delete_recommender` |
| Dashboard queries | `count_by_status`, `get_upcoming_deadlines`, `get_upcoming_interviews`, `get_upcoming`, `get_pending_recommenders`, `compute_materials_readiness` |

**Load-bearing contracts:**

1. **Exports after writes.** Every public write fn calls `exports.write_all()` as last step, inside try/except that logs errors but no re-raise. Write that succeeded in DB always reports success to caller, even if markdown regen failed. Import of `exports` inside each writer = deferred (not at module top) to break circular import.

2. **Pipeline auto-promotion.** Two writers can promote `positions.status` as side effect — `upsert_application` and `add_interview`. Both accept kwarg `propagate_status: bool = True`; when False, no pipeline side-effect fires. Promotion rules R1/R2/R3 documented in §9.3, run atomically inside same transaction as primary write.

3. **Idempotent init.** `init_db()` runs on every app start. Creates tables, triggers, indices w/ `IF NOT EXISTS`; runs `REQUIREMENT_DOCS`-driven `ALTER TABLE ADD COLUMN` loop; re-checks all invariants. Safe to call any number of times.

4. **Sparse-dict returns.** Aggregation queries (`count_by_status`, others) may omit zero-count keys. Callers fill missing keys w/ 0 before display.

5. **Sort orders = part of contract.** `get_all_positions` returns rows ordered by `deadline_date ASC NULLS LAST`; `get_upcoming_*` queries return chronological order; `get_all_recommenders` orders by `recommender_name`.

### `exports.py`

**Role.** Generate three markdown backup files. Imports `database` and `config`; never imports Streamlit. Called only by `database.py` writers (via deferred import) and Export page's manual-trigger button.

**Public API:**

| Function | What it writes |
|----------|----------------|
| `write_all` | All three files below (calls individual writers) |
| `write_opportunities` | `exports/OPPORTUNITIES.md` from positions table |
| `write_progress` | `exports/PROGRESS.md` from positions JOIN applications JOIN interviews |
| `write_recommenders` | `exports/RECOMMENDERS.md` from recommenders JOIN positions |

**Load-bearing contracts:**

1. **Log-and-continue on failure.** Errors inside `write_all` logged but never propagate past boundary. DB write that triggered export already succeeded, user should see "Saved" — not traceback. Export page surfaces file mtimes so stale backups become visible.

2. **Stable markdown format.** Output format is deterministic and idempotent — same DB state produces byte-identical output across calls. Output-format changes documented in CHANGELOG alongside any generator change. (Originally framed as "committed into version control"; amended 2026-05-04 — `exports/` is `.gitignore`d because the rendered files contain personal job-search data and the public repo is the wrong home for it. The user's local `exports/` directory is the durable surface; the regenerate button on `pages/4_Export.py` + the auto-write hook in every `database.py` writer keep it fresh.)

---

## 8. UI Design — Page by Page

### 8.0 Cross-page conventions

These conventions apply to every page.

#### Page configuration

Every page calls `st.set_page_config(page_title="Postdoc Tracker", page_icon="📋", layout="wide")` as first executable statement. `layout="wide"` essential: app data-heavy. `set_page_config` runs at top of `app.py` and every `pages/*.py` — re-executed on every page switch.

#### Widget-key prefix conventions

Widget keys follow scope prefix so tests can pin reliably across reruns:

| Scope | Prefix | Example |
|-------|--------|---------|
| Quick-add form | `qa_` | `qa_position_name`, `qa_deadline_date` |
| Edit panel (row-scoped) | `edit_` | `edit_position_name`, `edit_notes` |
| Filter bar | `filter_` | `filter_status`, `filter_field` |
| Internal sentinels | `_` prefix | `_edit_form_sid`, etc. |
| Form ids | suffix `_form` | `edit_notes_form` (contains `edit_notes`) |

**Form ids MUST NOT collide w/ any widget key inside form.** Suffixing form ids w/ `_form` = project convention.

#### Status label convention

Pages **never render raw status value** (e.g. `[SAVED]`) to user. Storage uses bracketed values for enum-sentinel clarity; display uses `config.STATUS_LABELS[raw]` (e.g. `"Saved"`). Streamlit selectboxes use `format_func=config.STATUS_LABELS.get` to show labels while storing raw values.

#### Confirmation & error patterns

| Event | Pattern |
|-------|---------|
| Successful write | `st.toast(f'Saved "{name}".')` — persists across `st.rerun()` |
| Write failure | `st.error(f"Could not save: {e}")` — no re-raise; no traceback leaks to user |
| Irreversible action | `@st.dialog` confirm w/ Confirm + Cancel buttons; explicit copy mentioning cascade effects |
| Cross-page navigation | `st.switch_page("pages/<N_Title>.py")` |

---

### 8.1 `app.py` — Dashboard (Home)

**Purpose:** Answer "What do I do today?" in one glance.

Layout wireframe: [`docs/ui/wireframes.md#dashboard`](docs/ui/wireframes.md#dashboard).

**Panel specifications:**

| Panel | Data source | Labels | Warn/flag trigger |
|-------|------------|--------|-------------------|
| KPI: Tracked | `count_by_status()` summed over `STATUS_SAVED + STATUS_APPLIED` | `st.metric(..., help="Saved + Applied — positions you're still actively pursuing")` | — |
| KPI: Applied | `count_by_status().get(STATUS_APPLIED, 0)` | — | — |
| KPI: Interview | `count_by_status().get(STATUS_INTERVIEW, 0)` | — | — |
| KPI: Next Interview | `get_upcoming_interviews()` scanned for earliest FUTURE `scheduled_date`; rendered `'{Mon D} · {institute}'`; "—" when none | — | — |
| Funnel | `count_by_status()` summed into `FUNNEL_BUCKETS`; Plotly horizontal `go.Bar`, one bar per **visible** bucket in list order; visible bucket w/ zero count renders as zero-width bar (category preserved for axis stability); y-axis reversed so earliest pipeline stage on top; bar color from `FUNNEL_BUCKETS[i][2]` | Bucket labels = `FUNNEL_BUCKETS[i][0]` (UI, no brackets) | — |
| Funnel disclosure toggle | Single `st.button(..., type="tertiary")` placed in funnel **subheader row** via `st.columns([3, 1])` (subheader left, toggle right) — same layout idiom as Upcoming panel's window selector. Renders whenever `FUNNEL_DEFAULT_HIDDEN` non-empty AND funnel not in empty-DB branch (a). Click flips session flag `st.session_state["_funnel_expanded"]`; chart re-renders w/ hidden buckets revealed (False→True) or hidden (True→False). Toggle = **bidirectional** — user who expanded to verify archived count can return to focused view w/o ending session. | Labels (config-locked, state-keyed): `config.FUNNEL_TOGGLE_LABELS[False] = "+ Show all stages"` (collapsed) · `config.FUNNEL_TOGGLE_LABELS[True] = "− Show fewer stages"` (expanded). Labels follow `<symbol> <verb-phrase>` CTA convention. | — |
| Materials Readiness | `compute_materials_readiness()` → two stacked `st.progress` bars labelled `"Ready to submit: N"` / `"Still missing: M"`; values = count / `max(ready + pending, 1)`; CTA button `"→ Opportunities page"` via `st.switch_page` | — | Empty state when `ready + pending == 0` |
| Upcoming | Merge of `get_upcoming_deadlines()` + `get_upcoming_interviews()` via `database.get_upcoming(days=selected_window)`; `st.dataframe(width="stretch", hide_index=True)`. Six cols in display order: **Date**, **Days left**, **Label**, **Kind**, **Status**, **Urgency** — see "Upcoming-panel column contract" below for cell formats. Sort: by date ascending (stable). Window controlled by inline `st.selectbox` (key: `upcoming_window`) over `UPCOMING_WINDOW_OPTIONS`, default = `DEADLINE_ALERT_DAYS`; subheader text dynamic: `f"Upcoming (next {selected_window} days)"`. | — | 🔴 when days-away ≤ `DEADLINE_URGENT_DAYS`; 🟡 when ≤ `DEADLINE_ALERT_DAYS`; otherwise empty. Rows surfaced by wider selected window (e.g. 60 / 90) but past `DEADLINE_ALERT_DAYS` show NO urgency glyph — band fixed in config, not tied to user-selected window. |
| Recommender Alerts | `get_pending_recommenders(RECOMMENDER_ALERT_DAYS)` grouped by `recommender_name` — one card per person w/ all owed positions listed | — | All shown rows = warnings |


**Upcoming-panel column contract.** Six cols left-to-right display order:

| Header | Cell format | Source |
|--------|-------------|--------|
| **Date** | Displayed as `f'{d.strftime("%b")} {d.day}'` — e.g. `'Apr 24'`, no year. Underlying dtype = `datetime.date` so col-header re-sort = chronological, not lexicographic. "No year" choice intentional: panel covers 30 / 60 / 90 day forward window, so year never ambiguous to reader. | `deadline_date` for deadline rows; `scheduled_date` for interview rows |
| **Days left** | `"today"` for 0 days; `"in 1 day"` for exactly 1; `"in N days"` for N > 1 | Derived once from `(date - today).days` per row; same int feeds **Urgency** so two cols cannot drift |
| **Label** | `f"{institute}: {position_name}"` when `institute` non-empty; bare `position_name` when institute missing or `_safe_str`-coerced empty. Institute prefix lets reader disambiguate two postings at diff orgs sharing same job-title text (e.g. "Stanford: Postdoc in Biostatistics" vs "MIT: Postdoc in Biostatistics"). | `position_name` + `institute` from positions (already in both helpers) |
| **Kind** | `"Deadline for application"` for deadline rows; `f"Interview {sequence}"` for interview rows (e.g. `"Interview 1"`, `"Interview 2"`). Sequence num 1-indexed, sourced from `interviews.sequence` so position's three-interview sequence reads as three rows: `Interview 1`, `Interview 2`, `Interview 3`. | Constant string for deadlines; `interviews.sequence` for interviews |
| **Status** | UI label via `STATUS_LABELS[raw]` (e.g. `"Saved"`) per §8.0 — never raw bracketed sentinel | `positions.status` for deadlines (already in `get_upcoming_deadlines`); enriched via `get_all_positions` for interviews |
| **Urgency** | `"🔴"` if days-away ≤ `DEADLINE_URGENT_DAYS`; `"🟡"` if ≤ `DEADLINE_ALERT_DAYS`; `""` otherwise | Same `days_away` int as **Days left** col — coherence guaranteed by construction |

`database.get_upcoming(days=selected_window)` returns these six cols named in lowercase storage form (`date, days_left, label, kind, status, urgency`); page renames to Title-Case headers above and maps `status` through `STATUS_LABELS` at render time. Empty result → `st.info(f"No deadlines or interviews in the next {selected_window} days.")`. Subheader `f"Upcoming (next {selected_window} days)"` renders in BOTH branches for page-height stability.


**Empty-DB hero.** When DB has no Saved, Applied, or Interview-stage positions, bordered hero container above KPI grid shows welcome subheader, explanatory paragraph, and primary CTA button that `st.switch_page("pages/1_Opportunities.py")`. KPI grid renders beneath hero regardless. DB holding only terminal-status rows still triggers hero — nothing actionable remains on dashboard.

**Empty-state branches** (each panel, when relevant data empty):

| Panel | Empty-state behaviour |
|-------|-----------------------|
| Funnel | **Three branches, evaluated in order.** (a) *No data anywhere* — `sum(count_by_status().values()) == 0`: show `st.info("Application funnel will appear once you've added positions.")`. **Disclosure toggle suppressed** (nothing to disclose into); subheader row degrades from `st.columns([3, 1])` to bare `st.subheader` so right-column slot no render empty box. (b) *No visible data* — total non-zero but every non-zero bucket lies in `FUNNEL_DEFAULT_HIDDEN` and `st.session_state["_funnel_expanded"]` = `False`: show `st.info("All your positions are in hidden buckets. Click 'Show all stages' to reveal them.")` and render disclosure toggle in **subheader row** (same `st.columns([3, 1])` placement as branch (c) — toggle position invariant across (b) and (c) for layout stability, info copy points at toggle by label not spatial direction so copy stays correct regardless of where toggle sits). Click toggle in branch (b) round-trips into branch (c). (c) *Otherwise* render chart; disclosure toggle renders in subheader row whenever `FUNNEL_DEFAULT_HIDDEN` non-empty (in **both** collapsed and expanded states — toggle persists post-click w/ flipped label, so user always has return path). Subheader renders in all three branches for page-height stability. Rationale: w/o branch (b), user returning mid-cycle w/ only archived / closed apps would see subheader above chart of zero-width bars — broken-looking state. Branch (b) explains what's happening + points at recovery path (disclosure toggle), which is bidirectional. |
| Materials Readiness | If `ready + pending == 0`, show `st.info("Materials readiness will appear once you've added positions with required documents.")`. Subheader renders in both branches. |
| Upcoming | If merged DataFrame empty, show `st.info(f"No deadlines or interviews in the next {selected_window} days.")` where `selected_window` = current value of panel's window selectbox (defaults to `DEADLINE_ALERT_DAYS`). Subheader and empty-state copy both interpolate same `selected_window` so they stay coherent under any user choice. |
| Recommender Alerts | If `get_pending_recommenders()` returns empty, show `st.info("No pending recommender follow-ups.")`. |

---

### 8.2 `pages/1_Opportunities.py` — Positions

**Purpose:** Capture and manage all positions.

Layout wireframe: [`docs/ui/wireframes.md#opportunities`](docs/ui/wireframes.md#opportunities).

**Behaviour:**

| Element | Behaviour |
|---------|-----------|
| Quick-add | Exactly fields listed in `config.QUICK_ADD_FIELDS`; saves w/ `status = config.STATUS_VALUES[0]`; auto-creates `applications` row. Whitespace-only `position_name` rejected w/ `st.error`; success → `st.toast`. |
| Filter: Status | `st.selectbox(["All"] + STATUS_VALUES, format_func=STATUS_LABELS.get)` — UI shows labels; filter compares raw values |
| Filter: Priority | `st.selectbox(["All"] + PRIORITY_VALUES)` |
| Filter: Field | `st.text_input`; substring match via `df["field"].str.contains(..., case=False, na=False, regex=False)` — literal match so `"C++"` no crash pandas |
| Table | `st.dataframe(width="stretch", on_select="rerun", selection_mode="single-row")`; sorted by `deadline_date ASC NULLS LAST`; Status col displays `STATUS_LABELS[raw]`; Due col carries urgency badge driven by DEADLINE thresholds |
| Row click | Selects row; edit panel renders beneath using **unfiltered** `df` for lookup (so narrowing filter never dismisses in-progress edit) |
| Overview tab | Pre-filled edit widgets for all overview cols; Status selectbox uses `format_func` convention; `work_auth` uses `WORK_AUTH_OPTIONS` selectbox + `work_auth_note` text_area below it |
| Requirements tab | One `st.radio` per `REQUIREMENT_DOCS` entry; options = `REQUIREMENT_VALUES`; `format_func=REQUIREMENT_LABELS.get`; Save writes only `req_*` keys so `done_*` survives flips between states |
| Materials tab | Live-filtered: only docs w/ `session_state[f"edit_{req_col}"] == "Yes"` render checkbox; Save writes only `done_*` for visible docs (hidden `done_*` preserved) |
| Notes tab | Single `st.text_area` inside `st.form("edit_notes_form")`; empty input persists as `""` not `NULL` |
| Delete | Button rendered **below form** (outside `st.form` box), **inside Overview tab body** (`with tabs[0]:`) so `st.tabs`'s natural CSS-hide makes it user-visible only when Overview tab active. Click opens `@st.dialog` confirmation (outside `st.form`); on Confirm, `delete_position(id)` runs and FK cascade removes position's `applications`, `interviews`, `recommenders` rows atomically. Button scope = whole position, not active tab's data — hence Overview-only placement, matching tab where user reviews position as whole. |

**Edit-panel architecture.** Four tabs use `st.tabs(config.EDIT_PANEL_TABS)`, NOT `st.radio + conditional rendering`. `st.tabs` keeps every tab body mounted on every script run (CSS hides inactive ones), which = load-bearing: Streamlit documented v1.20+ behaviour wipes `session_state` for unmounted widget keys, so any conditional-render approach causes user-visible data loss across tab switches (text_input value silently resets to its `value=` default on remount).

**Selection-survival invariant.** Save on any tab, filter change that still includes selected row, and dialog-Cancel must all preserve `selected_position_id`. Implementation hides state-mgmt details from users.

---

### 8.3 `pages/2_Applications.py` — Progress

**Purpose:** Track every position from submission to outcome, including full interview sequence.

Layout wireframe: [`docs/ui/wireframes.md#applications`](docs/ui/wireframes.md#applications).

**Behaviour:**
- **Status filter selectbox** (`apps_filter_status`): options in display order = `[STATUS_FILTER_ACTIVE, "All", *STATUS_VALUES]`; default = `STATUS_FILTER_ACTIVE` (`"Active"`); rendered via `format_func=STATUS_LABELS.get(v, v)` so known status values render through `STATUS_LABELS` while sentinel labels (`Active`, `All`) fall through to identity case (not in dict). `Active` excludes `config.STATUS_FILTER_ACTIVE_EXCLUDED = {STATUS_SAVED, STATUS_CLOSED}` (§5.1) — pre-application + withdrawn statuses w/ no app data worth showing. `All` applies no exclusion; specific status narrows view.
- **Read-only table column contract.** Renders **seven cols** in display order: **Position** (bare `position_name`, EM_DASH on empty), **Institute** (bare `institute`, EM_DASH on empty), **Applied** (`applied_date` formatted `MMM D` or EM_DASH), **Recs** (`✓` / `—` via `database.is_all_recs_submitted(position_id)` — live, no stored summary), **Confirmation** (D-A inline cell text — see below), **Response** (`response_type` or EM_DASH), **Result** (`result` or EM_DASH). Sort inherited from `database.get_applications_table()` (`deadline_date ASC NULLS LAST, position_id ASC`); page no re-sort.
- **"Confirmation"** col inlines `confirmation_received` + `confirmation_date` into cell text:

    | State | Cell text |
    |-------|-----------|
    | `confirmation_received == 0` | `—` |
    | `confirmation_received == 1`, `confirmation_date` set | `✓ {Mon D}` (e.g. `✓ Apr 19`) |
    | `confirmation_received == 1`, `confirmation_date` NULL | `✓ (no date)` |

    Raw int never shown.
- **Interviews** edited as **per-row blocks** under app detail card. Each interview = self-contained block w/ four elements:
  1. `**Interview {seq}**` heading (`st.markdown`).
  2. **Detail row** — three widgets in `st.columns([2, 2, 4])`: `scheduled_date` (`st.date_input`), `format` (`st.selectbox` over `[None, *config.INTERVIEW_FORMATS]` w/ `format_func` rendering `None` as EM_DASH so freshly-Added rows where `format` is NULL pre-seed correctly), `notes` (`st.text_input`).
  3. **Per-row Save submit button** (`st.form_submit_button`, key `apps_interview_{id}_save`) — sits inside the block's per-row form `apps_interview_{id}_form` (`border=False` so the parent `st.container(border=True)` stays the only visual frame). Save commits ONLY this row's dirty fields via `database.update_interview` (page no batches across rows). Toast: `st.toast(f"Saved interview {seq}.")`. Failure: `st.error(f"Could not save interview {seq}: {e}")`, no re-raise (GUIDELINES §8).
  4. **Per-row Delete button** (`st.button`, key `apps_interview_{id}_delete`, label `🗑️ Delete Interview {seq}`) — sits OUTSIDE the form (Streamlit 1.56 forbids `st.button` inside `st.form`), immediately below the Save line. Routes through `@st.dialog` confirm before `database.delete_interview(id)`. `interviews` FK CASCADE rooted at `applications.position_id` per §6.2.

  Per-row widget keys (full list): `apps_interview_{id}_{date|format|notes|save|delete}`. Per-row form id: `apps_interview_{id}_form`. Blocks separated by `st.divider()` between rows.

  Below the last block, `Add another interview` button (`apps_add_interview`) appends a new row; `database.add_interview` computes next `sequence` itself. On add, if `add_interview` returns `status_changed=True` (R2 fired, see §9.3), page surfaces `st.toast(f"Promoted to {STATUS_LABELS[new_status]}.")` AFTER the `"Added interview."` toast (action-first / cascade-second — matches the T2-B Save handler's Saved-then-Promoted convention).
- **Pipeline promotions** fire inside `database.upsert_application(propagate_status=True)` and `database.add_interview(propagate_status=True)` — see §9.3. Page does NOT detect transitions; just calls writer and reads returned promotion indicator to surface `st.toast`.
- **Status selectbox** (read-only here; this page edits applications, not pipeline) shows `STATUS_LABELS[raw]`.

---

### 8.4 `pages/3_Recommenders.py` — Recommenders

**Purpose:** Track every letter across every position; surface who needs reminder.

Layout wireframe: [`docs/ui/wireframes.md#recommenders`](docs/ui/wireframes.md#recommenders).

**Behaviour:**
- **Alert panel grouping:** `get_pending_recommenders()` returns one row per (recommender × position); page groups by `recommender_name` so one recommender owing N letters appears as single card listing all N positions.
- **Reminder helpers** (per recommender card): two affordances — quick mailto for simple case, LLM-prompt expander for users who want richer drafted email.
  - **Primary `Compose reminder email` button** opens `mailto:` URL w/ locked, professional copy:
    - Subject: follows English pluralization rules — at `N=1` reads `Following up: letter for 1 postdoc application` (singular both nouns); at `N≥2` reads `Following up: letters for N postdoc applications` (where `N` = position count for that recommender). Phase 7 CL4 Fix 2 amended this line: the previously-locked verbatim plural-only form read "letters for 1 postdoc applications" at `N=1`, which is grammatically awkward.
    - Body: `Hi {recommender_name}, just a quick check-in on the letters of recommendation you offered. Thank you so much!`

    OS hands off to user's default mail client; no outbound email integration. No signature appended — mail client appends one.
  - **Secondary `LLM prompts (N tones)` expander** beneath primary button reveals one or more pre-filled prompts user can paste into Claude / ChatGPT for richer email draft. Prompts render as `st.code(...)` blocks so Streamlit's built-in copy button on hover available. Each prompt filled with:
    - recommender name + relationship,
    - positions owed (position name, institute, deadline),
    - days since recommender was asked,
    - target tone — one prompt per tone (gentle / urgent).

    Expander label includes prompt count, e.g. `LLM prompts (2 tones)`. Prompts ask LLM to return both subject and body so user can paste either / both into mail client.
- **Add-recommender form:** position dropdown shows `position_name` + institute; IDs never surface to user.
- **Inline edit** for each row: `asked_date`, `confirmed` (0/1/NULL), `submitted_date`, `reminder_sent` + `reminder_sent_date`, `notes`.

---

### 8.5 `pages/4_Export.py` — Export

**Purpose:** Manual export trigger and file download.

Layout wireframe: [`docs/ui/wireframes.md#export`](docs/ui/wireframes.md#export).

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

**Cascade fully owned by `database.py`. Pages = display-only (D12).**

Two writers can promote `positions.status` as side effect — both accept kwarg `propagate_status: bool = True`; when False, no pipeline promotion fires.

**Placeholder convention.** In SQL snippets below, `<STATUS_*>` and `<RESPONSE_TYPE_OFFER>` placeholders interpolate to corresponding `config.py` alias value at query-construction time, and `<TERMINAL_STATUSES>` interpolates to tuple of all terminal status values. References elsewhere in this section use alias names directly (e.g. `STATUS_APPLIED`, `RESPONSE_TYPE_OFFER`) rather than underlying literal (e.g. `[APPLIED]`, `"Offer"`), so rename in `config.py` no ripple into this section.

| # | Trigger (in which writer) | Condition | Cascade |
|---|--------------------------|-----------|---------|
| R1 | `upsert_application` | `applied_date` transitions from NULL to non-NULL | `UPDATE positions SET status = '<STATUS_APPLIED>' WHERE id = ? AND status = '<STATUS_SAVED>'` |
| R2 | `add_interview` | Any successful interview insert | `UPDATE positions SET status = '<STATUS_INTERVIEW>' WHERE id = ? AND status = '<STATUS_APPLIED>'` |
| R3 | `upsert_application` | `response_type` transitions to `<RESPONSE_TYPE_OFFER>` | `UPDATE positions SET status = '<STATUS_OFFER>' WHERE id = ? AND status NOT IN (<TERMINAL_STATUSES>)` |

**R1 and R2 idempotent by construction** — `AND status = '<prev>'` guard makes cascade no-op when position already at or past target stage. R2 does **not** inspect interview count: status guard alone delivers correct semantics (first interview on `STATUS_APPLIED` position promotes; subsequent interviews on `STATUS_INTERVIEW` position = no-ops; position at `STATUS_OFFER` or terminal not regressed).

**R3 overrides non-terminal stages but guards against terminals.** Receiving Offer while at `STATUS_SAVED`, `STATUS_APPLIED`, or `STATUS_INTERVIEW` lands position at `STATUS_OFFER` directly. Position already in terminal stage (any member of `TERMINAL_STATUSES`) **not** silently regressed — user must first move status out of terminal bucket, then next `upsert_application` w/ `response_type = RESPONSE_TYPE_OFFER` will promote. Prevents stray edit, data import, or misread response from clobbering terminal decision.

All cascades execute inside same transaction as primary write, so failure rolls whole call back.

Each writer that can promote returns indicator `{"status_changed": bool, "new_status": str | None}` so callers can surface toast when promotion fires.

Callers opt out w/ `propagate_status=False` for edits that should not move pipeline (e.g. correcting typo in app notes). Applications page always calls w/ default; Recommenders and quick-add path never touch these fns.

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

Cancel preserves current edit context (selected row + tab state) so user returns where they were.

---

## 10. Key Architectural Decisions

| ID | Decision | Rationale | Alternative rejected |
|----|----------|-----------|----------------------|
| D1 | All field/vocab defs in `config.py` | Open/Closed Principle — extend by editing one file | Hardcoded in page files — fails on generalization |
| D2 | `deadline_date` = ISO text, separate from `deadline_note` | Time computations need real date; context note = separate concern | Single freetext field — cannot compute "X days away" |
| D3 | `done_*` cols = `INTEGER 0/1`; readiness computed | Avoids stale summary fields; single source of truth | Stored `materials_ready` — desyncs |
| D4 | `exports.write_all()` called inside every `database.py` writer | Markdown always current; no manual sync step | On-demand export only — backup lags after every write |
| D5 | Internal IDs; UI shows `position_name + institute` | Users never see/manage DB IDs | User-managed codes (P001) — error-prone, sync burden |
| D6 | Quick-add captures minimal essentials (see `config.QUICK_ADD_FIELDS`) | Capture must cost < 30s; enrichment later | Full form on add — positions lost at discovery time |
| D7 | Status via `st.selectbox(STATUS_VALUES, format_func=STATUS_LABELS.get)` | Prevents typo corruption; UI label decoupled from storage | Freetext — undetectable corruption |
| D8 | `ON DELETE CASCADE` on all child tables | One delete cleans every dependent row atomically | Manual multi-table delete — easy to orphan rows |
| D9 | Separate `applications` table | Diff update cadence + concern from positions | Single wide table — harder to query, harder to reason about |
| D10 | Auto-create `applications` row on `add_position()` | Every position always has matching row | Create on first update — needs NULL handling everywhere |
| D11 | Presentation/storage split via `STATUS_LABELS` + `FUNNEL_BUCKETS` | Cheap UI renames (no schema migration); presentation grouping reversible at-will | Rename storage values — needs DB migration for every naming tweak |
| D12 | Cross-table cascade lives in `database.py` writers | Atomic, testable, pages stay display-only | Page-level detect-and-prompt — leaks business logic into UI; loses atomicity |
| D13 | No 🔄 Refresh button on dashboard top bar | Streamlit reruns on any interaction; single-user local app rarely has cross-tab writes | Manual refresh button — cognitive noise for common case |
| D14 | `st.set_page_config(layout="wide", ...)` on every page | Data-heavy views need horizontal room | Default centered layout — ~750px cramps every page |
| D15 | `TRACKER_PROFILE` validated at import time against `VALID_PROFILES` | Cheap forward-compat hook for v2 profile variants; catches typos now | Hardcode `"postdoc"` — no v2 extension point |
| D16 | Bracketed status storage values + bracket-stripped UI labels | Visual enum sentinel in logs/DB; `STATUS_LABELS` delivers clean UI | Raw labels in storage — harder to grep; conflicts w/ freetext "Saved" elsewhere |
| D17 | Archived = `[REJECTED]` + `[DECLINED]` on dashboard funnel only; `[CLOSED]` stays own bar | Rejection + declined-offer = both outcomes after engagement; CLOSED = pre-engagement withdrawal — genuinely diff state | Group all three terminals — loses semantic distinction |
| D18 | `interviews` sub-table instead of flat `interview1_date`/`interview2_date` cols | Real apps have 3+ interviews (phone → committee → chalk talk → dean); flat cap = arbitrary cliff | Flat cols — capped data model at unrealistic limit |
| D19 | Dual-concern cols split into `(flag, date)` pairs | Type-consistent; predicates simple; no col holds either flag or date | Single TEXT col storing `'Y'` or date string — type-ambiguous, hard to query |
| D20 | Boolean-state cols as `INTEGER 0/1` (never TEXT `'Y'`/`'N'`) | Consistent, grep-friendly, trivial SQL predicates | TEXT `'Y'`/`'N'` — mixes w/ `req_*`'s three-state TEXT, confuses readers |
| D21 | Three-state requirement cols use full words `"Yes"`/`"Optional"`/`"No"` | Consistent w/ D20's full-word philosophy; self-descriptive in raw dumps; no storage penalty on TEXT | `"Y"`/`"Optional"`/`"N"` — mixed length, inconsistent, harder to read |
| D22 | `work_auth` three-value categorical + `work_auth_note` freetext | Categorical keeps filters simple; freetext preserves posting-specific nuance (e.g. "green card only") | Many-value enum — unused detail; or freetext only — not filterable |
| D23 | Summary flags that could be computed **are** computed, never stored | D3 applied consistently — `is_all_recs_submitted()` = query helper, not column | Store `all_recs_submitted` — desyncs w/ recommenders table |
| D24 | Terminal funnel buckets default-hidden, user opts in | Dashboard focuses on active work; rejection/close counts available on-demand, not in face of user who doesn't want them there | Always show all buckets — demoralizing and noisy |
| D25 | `positions.updated_at` maintained by `AFTER UPDATE` trigger | Every write touches timestamp w/o requiring each writer to remember it | Explicit update in each writer — easy to forget on next writer added |

---

## 11. Extension Guide

See [`docs/dev-notes/extending.md`](docs/dev-notes/extending.md) for step-by-step recipes (add requirement document, add or rename pipeline status, switch tracker profile, etc.).

---

## 12. v2 Design Notes

### 12.1 General job tracker — profile expansion

Tracker designed so reskinning to diff job context needs **editing `config.py` only**. v1 keeps `VALID_PROFILES = {"postdoc"}`.

v2 multi-profile expansion:

1. Extend `VALID_PROFILES` to include `"software_eng"`, `"faculty"`, etc.
2. Profile-specific vocabularies keyed by profile:
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
3. Profile-specific cols added to `positions` via `init_db()` migration loop but conditionally hidden in UI based on `TRACKER_PROFILE`. Users keep existing data through profile switch — schema additive.

### 12.2 Soft delete + undo

Introduce `positions.archived_at TIMESTAMP NULL`. Delete becomes `UPDATE positions SET archived_at = datetime('now')` instead of `DELETE`; `get_all_positions()` filters `WHERE archived_at IS NULL` by default. "Archived" section on Opportunities page surfaces soft-deleted rows w/ "Restore" button. `st.toast(..., icon="🗑️")` w/ 5-second Undo action handles grace period.

FK cascade semantics change slightly: cascading deletes still fire on hard-delete only. Soft-delete leaves applications, interviews, recommenders rows intact but hidden alongside parent position.

### 12.3 File attachments on Materials

New `attachments` table w/ `UNIQUE(position_id, doc_type)`. Files live on local disk under `attachments/<position_id>/<doc_type>.<ext>`; paths stored in DB. Upload auto-flips `done_* = 1`. Delete-position path additionally calls `shutil.rmtree(f"attachments/{position_id}")` to clean orphaned files.

### 12.4 AI-populated quick-add

Paste job-posting URL or free-form description; LLM extracts fields and pre-fills quick-add form. Needs:
- New module (`ai_ingest.py`) w/ narrow public API: `extract_fields(source: str) -> dict[str, Any]`
- API key handling via `.env` — `.env*` gitignore rule reserved from v1 covers secrets; runtime needs `python-dotenv` added to `requirements.txt` when this lands
- Careful prompt discipline (structured output schema matching `QUICK_ADD_FIELDS`)

### 12.5 Cloud backup of `postdoc.db`

Periodic upload of `postdoc.db` + `exports/` (+ `attachments/` once 12.3 lands) to cloud blob store (S3, iCloud Drive, Dropbox). Scheduled via `APScheduler` or cron.

### 12.6 Interactive funnel

Click bar on dashboard funnel → navigate to Opportunities page w/ corresponding `FUNNEL_BUCKETS` status set pre-selected in status filter. Implementation path: Plotly click events return bucket index; handler writes list of raw statuses to `st.session_state["pending_status_filter"]`; Opportunities page reads + applies on next render, then clears.

### 12.7 Additional analytics (post-v1)

- **Source effectiveness chart** — which `source` values yield most `[INTERVIEW]` conversions
- **Application timeline chart** — histogram of `applied_date` clustering around deadlines
- **Offer details sub-table** — new `offers` table FK'd from `applications` (start date, salary notes, decision deadline)
- **Application goals** — `settings` table storing target count + deadline; dashboard surfaces progress
- **Interview-velocity metric** — avg days from `applied_date` to first `interviews.scheduled_date`, segmented by `source`