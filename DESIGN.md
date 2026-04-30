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

### 5.1 Symbol index

The constants listed below are the v1 API of `config.py`. Actual
values, inline rationale, and defensive assertions live in
[`config.py`](config.py); this section is a DESIGN-level index of
**what each symbol is for and where it is consumed**. Literal values
are shown here only when they are short and architecturally stable
(e.g. the fixed set of pipeline statuses referenced by DDL and
auto-promotion rules). Longer enumerations are described by category
— open `config.py` for the exhaustive list.

#### Tracker identity

| Constant | Type | Role |
|----------|------|------|
| `TRACKER_PROFILE` | `str` | Profile discriminator; v1 = `"postdoc"`. Extension hook for v2+ profile variants (§12.1). |
| `VALID_PROFILES` | `set[str]` | Import-time validation set for `TRACKER_PROFILE`; guarded by §5.2 invariant #1. |

#### Status pipeline

| Constant | Type | Role |
|----------|------|------|
| `STATUS_VALUES` | `list[str]` | Ordered pipeline: `[SAVED]` → `[APPLIED]` → `[INTERVIEW]` → `[OFFER]` → `[CLOSED]` → `[REJECTED]` → `[DECLINED]`. Index = pipeline position. Referenced by §6.2 DDL `DEFAULT` clause, §8.1 funnel, and §9.3 auto-promotion rules. |
| `STATUS_SAVED` / `STATUS_APPLIED` / `STATUS_INTERVIEW` / `STATUS_OFFER` / `STATUS_CLOSED` / `STATUS_REJECTED` / `STATUS_DECLINED` | `str` | One named alias per `STATUS_VALUES[i]`. Page code uses these rather than literals — anti-typo guardrail enforced by pre-merge grep. |
| `TERMINAL_STATUSES` | `list[str]` | Subset of `STATUS_VALUES` (`[CLOSED]` / `[REJECTED]` / `[DECLINED]`). Excluded from "active" queries (upcoming deadlines, materials readiness); also guards R3 auto-promotion against regression (§9.3). |
| `STATUS_COLORS` | `dict[str, str]` | Per-status color for single-status surfaces (Opportunities-table badge, tooltips). Values drawn from the intersection of the `st.badge` color vocabulary and Plotly CSS color names. **Not** used for funnel bars — see `FUNNEL_BUCKETS`. Drift caught by §5.2 invariant #2. |
| `STATUS_LABELS` | `dict[str, str]` | Storage-to-UI label. Storage keeps bracketed values as enum sentinels; UI strips the brackets via this dict. Every status surface rendered to a user MUST go through this map — never print a raw key. Drift caught by §5.2 invariant #3. |
| `STATUS_FILTER_ACTIVE` | `str` | UI sentinel (`"Active"`) used as the default selection on the Applications page filter selectbox (§8.3, Phase 5 T1-B). Encodes "every actionable status" — the page resolves it to `set(STATUS_VALUES) - STATUS_FILTER_ACTIVE_EXCLUDED` at render time. The literal lives in config (not the page) so future surfaces — e.g. a "Tracked: Active" KPI variant on the dashboard — can reuse the same sentinel without hardcoding. Defensive guard in §5.2 invariant #12 ensures the sentinel does not collide with any real `STATUS_VALUES` entry. |
| `STATUS_FILTER_ACTIVE_EXCLUDED` | `frozenset[str]` | Statuses removed by the `STATUS_FILTER_ACTIVE` sentinel — `{STATUS_SAVED, STATUS_CLOSED}` (pre-application + withdrawn). Frozen so a page cannot mutate it via `.add()`/`.remove()` and silently broaden the page's default filter at runtime. Membership is part of the spec (§8.3); broadening the exclusion (e.g. to also exclude `[REJECTED]`/`[DECLINED]`) is a deliberate spec amendment. Drift caught by §5.2 invariant #12. |

#### Dashboard funnel (presentation layer)

| Constant | Type | Role |
|----------|------|------|
| `FUNNEL_BUCKETS` | `list[tuple[str, tuple[str, ...], str]]` | Presentation-layer grouping of raw statuses into funnel bars. Each entry: `(UI label, raw-status tuple, bucket color)`. Order = top-down display order (y-axis reversed). "Archived" aggregates `[REJECTED]` + `[DECLINED]` (D17); `[CLOSED]` stays its own bucket. Multiset coverage of `STATUS_VALUES` guarded by §5.2 invariant #5. |
| `FUNNEL_DEFAULT_HIDDEN` | `set[str]` | Bucket labels hidden by default on the dashboard funnel. The single disclosure toggle (DESIGN §8.1 T6 amendment) reveals/hides them as a group; state held in `st.session_state["_funnel_expanded"]` for the current session only (D24, §8.1). Validated by §5.2 invariant #6. |
| `FUNNEL_TOGGLE_LABELS` | `dict[bool, str]` | State-keyed labels for the funnel disclosure toggle (§8.1). Indexed by the bool value of `st.session_state["_funnel_expanded"]`: `False` → `"+ Show all stages"` (collapsed; click invites expand); `True` → `"− Show fewer stages"` (expanded; click invites collapse). Symbols are U+002B `+` and U+2212 `−` — they encode the click's effect direction. Vocabulary follows the project's `<symbol> <verb-phrase>` CTA convention. Validated by §5.2 invariant #11. |

#### Vocabularies (user-facing selectbox options)

| Constant | Type | Role |
|----------|------|------|
| `PRIORITY_VALUES` | `list[str]` | User's subjective fit — `High` / `Medium` / `Low` / `Stretch`. Stored; distinct from computed urgency. |
| `WORK_AUTH_OPTIONS` | `list[str]` | Three-value categorical (`Yes` / `No` / `Unknown`) answering "does the posting accept this applicant's work authorization?" Paired with freetext `work_auth_note` for nuance (D22). |
| `FULL_TIME_OPTIONS` | `list[str]` | Employment type: `Full-time` / `Part-time` / `Contract`. |
| `SOURCE_OPTIONS` | `list[str]` | Where the posting was found (lab site, job board, referral, etc.). Fuels the P3 "source effectiveness" analytic sketched in §12.7. |
| `RESPONSE_TYPES` | `list[str]` | First-response categorization. The value `"Offer"` fires auto-promotion rule R3 (§9.3); referenced from `database.py` via the `RESPONSE_TYPE_OFFER` alias below. |
| `RESPONSE_TYPE_OFFER` | `str` | Named alias for the R3 cascade trigger (`"Offer"`) — anti-typo guardrail mirroring the `STATUS_*` alias pattern so `database.upsert_application` is insulated from a future rename of the `RESPONSE_TYPES` entry. Drift caught by §5.2 invariant #9. |
| `RESULT_DEFAULT` | `str` | `"Pending"` — matches the `applications.result` schema `DEFAULT` clause; renaming requires a one-shot `UPDATE` migration (§6.3). |
| `RESULT_VALUES` | `list[str]` | Final application outcome; starts with `RESULT_DEFAULT`, then accepted / declined / rejected / withdrawn. |
| `RELATIONSHIP_TYPES` | `list[str]` | Recommender-to-applicant relationship (advisor / committee / collaborator / …). |
| `INTERVIEW_FORMATS` | `list[str]` | Vocabulary for the `interviews.format` column: `Phone` / `Video` / `Onsite` / `Other`. |

#### Requirement documents

| Constant | Type | Role |
|----------|------|------|
| `REQUIREMENT_VALUES` | `list[str]` | Canonical DB values for `req_*` columns: `Yes` / `Optional` / `No`. |
| `REQUIREMENT_LABELS` | `dict[str, str]` | UI labels for the three canonical values. Radios use `format_func=REQUIREMENT_LABELS.get` so `session_state` holds the DB value — no save-time translation. Drift caught by §5.2 invariant #7. |
| `REQUIREMENT_DOCS` | `list[tuple[str, str, str]]` | Document-type schema driver: `(req_column, done_column, display_label)` per document type. Appending one tuple is the whole contract for adding a new document type — `init_db()` auto-adds both columns on next start (§6.3). |

#### Forms and UI structure

| Constant | Type | Role |
|----------|------|------|
| `QUICK_ADD_FIELDS` | `list[str]` | Column names shown in the quick-add form. Ordered: `position_name`, `institute`, `field`, `deadline_date`, `priority`, `link`. Keeping this ≤ 6 is a capture-friction design rule (D6). |
| `EDIT_PANEL_TABS` | `list[str]` | Tab labels for the Opportunities edit panel in display order: `Overview`, `Requirements`, `Materials`, `Notes`. |

#### Dashboard thresholds (days)

| Constant | Type | Role |
|----------|------|------|
| `DEADLINE_ALERT_DAYS` | `int` | Default upcoming-window width and the upper edge of the 🟡 urgency band. A deadline within this many days surfaces on the Upcoming panel (§8.1) when the panel's window selectbox is at its default. |
| `DEADLINE_URGENT_DAYS` | `int` | Inner urgency band. A deadline within this many days is flagged 🔴; between this and `DEADLINE_ALERT_DAYS` is 🟡. Inclusive on the narrower band: exactly N days away → urgent. Ordering guarded by §5.2 invariant #8. The urgency thresholds are **fixed in config** — they do not track the user-selected Upcoming window. |
| `RECOMMENDER_ALERT_DAYS` | `int` | Recommender asked ≥ this many days ago with no submitted letter → surfaces on Recommender Alerts (§8.1). |
| `UPCOMING_WINDOW_OPTIONS` | `list[int]` | User-selectable widths for the Upcoming panel's window selectbox (§8.1). Default values: `[30, 60, 90]`. The panel's selectbox defaults to `DEADLINE_ALERT_DAYS` (which must be in this list — §5.2 invariant #10) and lets the user widen the view to 60 or 90 days. The urgency-glyph band is NOT tied to this — selecting a wider window surfaces more rows but the band thresholds stay at `DEADLINE_URGENT_DAYS` / `DEADLINE_ALERT_DAYS`. |

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
9. `RESPONSE_TYPE_OFFER in RESPONSE_TYPES` — the R3 cascade trigger (§9.3) must be a real `RESPONSE_TYPES` selectbox option; catches a rename that drops `"Offer"` without updating the alias
10. `DEADLINE_ALERT_DAYS in UPCOMING_WINDOW_OPTIONS` — the Upcoming-panel selectbox default (= `DEADLINE_ALERT_DAYS`) must be a real option in the offered list; catches a config edit that removes 30 from the list without updating the default
11. `set(FUNNEL_TOGGLE_LABELS.keys()) == {True, False}` — the funnel disclosure toggle (§8.1) reads its label as `FUNNEL_TOGGLE_LABELS[st.session_state["_funnel_expanded"]]` per render. A missing key would surface as a render-time `KeyError` on first toggle into that state; an extra key would silently no-op. Caught at import.
12. `STATUS_FILTER_ACTIVE_EXCLUDED <= set(STATUS_VALUES)` — the Applications-page "Active" filter sentinel (§8.3) excludes statuses listed in this frozenset; every entry must be a real `STATUS_VALUES` member. An unknown entry would silently fail to filter at render time (the unknown status would never match a row), so the guard fires at import-time instead.

### 5.3 Extension recipes

| Goal | What to edit |
|------|--------------|
| Add a new requirement document | Append one tuple to `REQUIREMENT_DOCS`. On next app start, `init_db()` adds `req_*` / `done_*` columns via the migration loop. No other file changes. |
| Add a priority / source / response-type / relationship / interview-format option | Append to the relevant list. Dropdowns pick it up on next render. No DB change — columns are plain TEXT. |
| Add a new pipeline status | (1) Append to `STATUS_VALUES` and add the matching `STATUS_<name>` alias; (2) add one entry each to `STATUS_COLORS` and `STATUS_LABELS`; (3) decide which `FUNNEL_BUCKETS` entry it belongs in — extend an existing bucket's tuple or add a new 3-tuple `(label, (raw,...), color)` in the right display position; (4) if terminal, append to `TERMINAL_STATUSES`. No DDL change. |
| Rename a pipeline status | Edit `STATUS_VALUES[i]`, the matching alias, and the keys in `STATUS_COLORS` / `STATUS_LABELS` / `FUNNEL_BUCKETS` / `TERMINAL_STATUSES`. Write a one-shot migration in `CHANGELOG.md` under the release: `UPDATE positions SET status = '<new>' WHERE status = '<old>'`. The schema `DEFAULT` clause is config-driven; no DDL edit needed if renaming `STATUS_VALUES[0]`. |
| Hide or un-hide a funnel bucket by default | Edit `FUNNEL_DEFAULT_HIDDEN`. Values must be existing bucket labels. |
| Rephrase the funnel disclosure toggle | Edit both keys of `FUNNEL_TOGGLE_LABELS`. Stay within the `<symbol> <verb-phrase>` CTA convention (matches `+ Add your first position` and `→ Opportunities page`). The `+` / `−` pairing is recommended — the symbol encodes the click's effect direction — but invariant #11 only enforces dict shape, not symbol choice. Tests in `TestT6FunnelToggle` (`test_label_symbols_match_cta_convention`) pin the current `+` / `−` pair; relax that test if you adopt a different symbol pair. |
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

The DDL above shows DEFAULT clauses with `<ALIAS_NAME>` placeholders
(e.g. `'<STATUS_SAVED>'`, `'<RESULT_DEFAULT>'`); at `init_db()`
construction time, the f-strings substitute in the current config
value. The placeholders let DESIGN stay immune to a rename of the
underlying constant: rename `STATUS_VALUES[0]` from `"[SAVED]"` to
something else and only `config.py` changes.

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

**Flag/date split divergence — `confirmation_email` vs `reminder_sent`.**
Both migrations split a dual-purpose TEXT column into a
`(flag INTEGER, date TEXT)` pair but translate a date-shaped legacy
value differently — intentionally, not by accident.
`applications.confirmation_email`'s date-shape lands as `received = 1`
+ `date = value` because pre-v1.3 semantics tied a recorded date
strongly to "received" (a user wouldn't write a date if no receipt
happened). `recommenders.reminder_sent`'s date-shape lands as
`reminder_sent = 0` + `reminder_sent_date = value` (the conservative
reading) because pre-v1.3 reminder_sent saw both date-only and
`'Y'`-only legacy use without a clear "date implies sent" rule; the
user re-saves to flip the flag if intended. Pinned by
`test_migration_copies_date_string_to_both_fields` and
`test_migration_splits_date_shaped_reminder_sent_into_new_column`
respectively. A future maintainer reading the two tests side-by-side
should expect the divergence rather than treat one as a bug relative
to the other.

**Pending column drops (committed for v1.0-rc).** After the v1.3
alignment pass, one column remains physically present but operationally
NULL: `applications.confirmation_email`, split into
`confirmation_received` + `confirmation_date` in Sub-task 10. Per the
"Remove a column" row above, SQLite requires a table rebuild; a single
commit during the v1.0-rc release will run
`CREATE TABLE applications_new AS SELECT <kept cols> FROM applications;
DROP TABLE applications;
ALTER TABLE applications_new RENAME TO applications;`
inside one transaction. Idempotent via a `PRAGMA table_info(applications)`
check on `confirmation_email` presence — a rerun on an already-dropped
DB short-circuits. Migration SQL recorded in CHANGELOG under v1.0-rc.
No other pending drops at this time.

**Migration discipline:** every schema or vocabulary change lands with a
`Migration:` note in `CHANGELOG.md` under the release that introduces
it, giving the exact `UPDATE` or rebuild SQL. A user upgrading between
releases should never have to guess which migration to run.

### 6.4 Schema design decisions

Storage decisions affecting this schema are recorded in [§10 Key
Architectural Decisions](#10-key-architectural-decisions): D2, D3,
D8, D9, D10, D11, D16, D18, D19, D20, D21, D22, D23, D25. Each entry
in §10 gives the decision, its rationale, and the alternative that
was rejected — this section intentionally does not restate them.

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
| Dashboard queries | `count_by_status`, `get_upcoming_deadlines`, `get_upcoming_interviews`, `get_upcoming`, `get_pending_recommenders`, `compute_materials_readiness` |

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

Layout wireframe: [`docs/ui/wireframes.md#dashboard`](docs/ui/wireframes.md#dashboard).

**Panel specifications:**

| Panel | Data source | Labels | Warn/flag trigger |
|-------|------------|--------|-------------------|
| KPI: Tracked | `count_by_status()` summed over `STATUS_SAVED + STATUS_APPLIED` | `st.metric(..., help="Saved + Applied — positions you're still actively pursuing")` | — |
| KPI: Applied | `count_by_status().get(STATUS_APPLIED, 0)` | — | — |
| KPI: Interview | `count_by_status().get(STATUS_INTERVIEW, 0)` | — | — |
| KPI: Next Interview | `get_upcoming_interviews()` scanned for earliest FUTURE `scheduled_date`; rendered `'{Mon D} · {institute}'`; "—" when none | — | — |
| Funnel | `count_by_status()` summed into `FUNNEL_BUCKETS`; Plotly horizontal `go.Bar`, one bar per **visible** bucket in list order; a visible bucket with zero count renders as a zero-width bar (category preserved for axis stability); y-axis reversed so earliest pipeline stage sits on top; bar color comes from `FUNNEL_BUCKETS[i][2]` | Bucket labels = `FUNNEL_BUCKETS[i][0]` (UI, no brackets) | — |
| Funnel disclosure toggle | Single `st.button(..., type="tertiary")` placed in the funnel **subheader row** via `st.columns([3, 1])` (subheader left, toggle right) — same layout idiom as the Upcoming panel's window selector (see "Window selector" below). Renders whenever `FUNNEL_DEFAULT_HIDDEN` is non-empty AND the funnel is not in the empty-DB branch (a). Clicking flips the session flag `st.session_state["_funnel_expanded"]`; the chart re-renders with the hidden buckets revealed (False→True) or hidden (True→False). The toggle is **bidirectional** — a user who expanded to verify their archived count can return to the focused view without ending the session. **T6 amendment (2026-04-30)** replaces the earlier unidirectional `[expand]` button (which had no companion `[collapse]`) and the pre-Sub-task-12 per-bucket checkbox model. | Labels (config-locked, state-keyed): `config.FUNNEL_TOGGLE_LABELS[False] = "+ Show all stages"` (collapsed) · `config.FUNNEL_TOGGLE_LABELS[True] = "− Show fewer stages"` (expanded). The leading `+` (U+002B) and `−` (U+2212) match the project's `<symbol> <verb-phrase>` CTA convention used by `+ Add your first position` and `→ Opportunities page`. | — |
| Materials Readiness | `compute_materials_readiness()` → two stacked `st.progress` bars labelled `"Ready to submit: N"` / `"Still missing: M"`; values = count / `max(ready + pending, 1)`; CTA button `"→ Opportunities page"` via `st.switch_page` | — | Empty state when `ready + pending == 0` |
| Upcoming | Merge of `get_upcoming_deadlines()` + `get_upcoming_interviews()` via `database.get_upcoming(days=selected_window)` (T4-A); `st.dataframe(width="stretch", hide_index=True)`. Six columns in display order: **Date**, **Days left**, **Label**, **Kind**, **Status**, **Urgency** — see "Upcoming-panel column contract" below for cell formats. Sort: by date ascending (stable). Window controlled by an inline `st.selectbox` (key: `upcoming_window`) over `UPCOMING_WINDOW_OPTIONS`, default = `DEADLINE_ALERT_DAYS`; subheader text is dynamic: `f"Upcoming (next {selected_window} days)"`. | — | 🔴 when days-away ≤ `DEADLINE_URGENT_DAYS`; 🟡 when ≤ `DEADLINE_ALERT_DAYS`; otherwise empty. Rows surfaced by a wider selected window (e.g. 60 / 90) but past `DEADLINE_ALERT_DAYS` show NO urgency glyph — the band is fixed in config, not tied to the user-selected window. |
| Recommender Alerts | `get_pending_recommenders(RECOMMENDER_ALERT_DAYS)` grouped by `recommender_name` — one card per person with all their owed positions listed | — | All shown rows are warnings |

**Funnel visibility rules.** The funnel renders buckets in the order
listed in `FUNNEL_BUCKETS`. A bucket is visible when **not** in
`FUNNEL_DEFAULT_HIDDEN`, or when `st.session_state["_funnel_expanded"]`
is `True` (which reveals every `FUNNEL_DEFAULT_HIDDEN` bucket at
once). The disclosure toggle is **bidirectional**: clicking from the
collapsed state expands; clicking from the expanded state collapses.
The collapsed state is the *default-focused* view (active pipeline
only, per D24); the expanded state is the *full-pipeline* view
including terminal stages. Round-tripping between the two within a
single session is supported and tested — a user verifying their
archived count can return to the focused view without a fresh
session.

The toggle's *label* describes the action a click *will* perform, not
the current state — `"+ Show all stages"` means *"clicking this will
show all"* (you're currently collapsed); `"− Show fewer stages"`
means *"clicking this will show fewer"* (you're currently expanded).
Both labels are config-locked in `FUNNEL_TOGGLE_LABELS` (DESIGN §5.1)
and follow the project's `<symbol> <verb-phrase>` CTA convention.

**Upcoming-panel column contract.** Six columns in left-to-right display
order:

| Header | Cell format | Source |
|--------|-------------|--------|
| **Date** | Displayed as `f'{d.strftime("%b")} {d.day}'` — e.g. `'Apr 24'`, no year. Underlying dtype is `datetime.date` so column-header re-sort is chronological, not lexicographic. The "no year" choice is intentional: the panel covers a 30 / 60 / 90 day forward window, so the year is never ambiguous to the reader. | `deadline_date` for deadline rows; `scheduled_date` for interview rows |
| **Days left** | `"today"` for 0 days; `"in 1 day"` for exactly 1; `"in N days"` for N > 1 | Derived once from `(date - today).days` per row; the same integer feeds **Urgency** so the two columns cannot drift |
| **Label** | `f"{institute}: {position_name}"` when `institute` is non-empty; bare `position_name` when institute is missing or `_safe_str`-coerced empty. The institute prefix lets the reader disambiguate two postings at different organizations sharing the same job-title text (e.g. "Stanford: Postdoc in Biostatistics" vs "MIT: Postdoc in Biostatistics"). | `position_name` + `institute` from positions (already in both helpers) |
| **Kind** | `"Deadline for application"` for deadline rows; `f"Interview {sequence}"` for interview rows (e.g. `"Interview 1"`, `"Interview 2"`). The sequence number is 1-indexed, sourced from `interviews.sequence` so a position's three-interview sequence reads as three rows: `Interview 1`, `Interview 2`, `Interview 3`. | Constant string for deadlines; `interviews.sequence` for interviews |
| **Status** | UI label via `STATUS_LABELS[raw]` (e.g. `"Saved"`) per §8.0 — never the raw bracketed sentinel | `positions.status` for deadlines (already in `get_upcoming_deadlines`); enriched via `get_all_positions` for interviews |
| **Urgency** | `"🔴"` if days-away ≤ `DEADLINE_URGENT_DAYS`; `"🟡"` if ≤ `DEADLINE_ALERT_DAYS`; `""` otherwise | Same `days_away` integer as the **Days left** column — coherence guaranteed by construction |

`database.get_upcoming(days=selected_window)` returns these six
columns named in lowercase storage form
(`date, days_left, label, kind, status, urgency`); the page renames
them to the Title-Case headers above and maps `status` through
`STATUS_LABELS` at render time. Empty result →
`st.info(f"No deadlines or interviews in the next {selected_window} days.")`.
The subheader `f"Upcoming (next {selected_window} days)"` renders in
BOTH branches for page-height stability (T2/T3 precedent).

**Window selector.** The panel renders a small `st.selectbox`
(key: `upcoming_window`, label hidden via `label_visibility="collapsed"`)
inline with the subheader, offering options from
`config.UPCOMING_WINDOW_OPTIONS` (`[30, 60, 90]` by default). The selected
value drives `database.get_upcoming(days=selected_window)`, the dynamic
subheader, and the empty-state copy. Default selection =
`DEADLINE_ALERT_DAYS`, pinned by §5.2 invariant #10
(`DEADLINE_ALERT_DAYS in UPCOMING_WINDOW_OPTIONS`). Streamlit persists
the selection in `st.session_state["upcoming_window"]` for the session.
Layout: place the selectbox in a narrow right-side column, subheader on
the left — same `st.columns([3, 1])` weight pair on every render so the
T2/T3 page-height-stability guarantee extends to this panel too. The
Urgency band is **independent of** the selected window: a row 50 days
away in a 60-day window shows no urgency glyph, by design.

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
| Funnel | **Three branches, evaluated in order.** (a) *No data anywhere* — `sum(count_by_status().values()) == 0`: show `st.info("Application funnel will appear once you've added positions.")`. **Disclosure toggle is suppressed** (nothing to disclose into); the subheader row degrades from `st.columns([3, 1])` to a bare `st.subheader` so the right-column slot doesn't render an empty box. (b) *No visible data* — total is non-zero but every non-zero bucket lies in `FUNNEL_DEFAULT_HIDDEN` and `st.session_state["_funnel_expanded"]` is `False`: show `st.info("All your positions are in hidden buckets. Click 'Show all stages' to reveal them.")` and render the disclosure toggle in the **subheader row** (same `st.columns([3, 1])` placement as branch (c) — toggle position is invariant across (b) and (c) for layout stability, and the info copy points at the toggle by label rather than by spatial direction so the copy stays correct regardless of where the toggle sits). Clicking the toggle in branch (b) round-trips into branch (c). (c) *Otherwise* render the chart; the disclosure toggle renders in the subheader row whenever `FUNNEL_DEFAULT_HIDDEN` is non-empty (in **both** collapsed and expanded states — the post-T6 contract is that the toggle persists post-click with a flipped label, so the user always has a return path). Subheader renders in all three branches for page-height stability. Rationale: without branch (b), a user returning mid-cycle with only archived / closed applications would see a subheader above a chart of zero-width bars — a broken-looking state. Branch (b) explains what's happening and points at the recovery path (the disclosure toggle); the T6 amendment makes that recovery a true round-trip rather than a one-way trapdoor. |
| Materials Readiness | If `ready + pending == 0`, show `st.info("Materials readiness will appear once you've added positions with required documents.")`. Subheader renders in both branches. |
| Upcoming | If merged DataFrame is empty, show `st.info(f"No deadlines or interviews in the next {selected_window} days.")` where `selected_window` is the current value of the panel's window selectbox (defaults to `DEADLINE_ALERT_DAYS`). The subheader and empty-state copy both interpolate the same `selected_window` so they stay coherent under any user choice. |
| Recommender Alerts | If `get_pending_recommenders()` returns empty, show `st.info("No pending recommender follow-ups.")`. |

---

### 8.2 `pages/1_Opportunities.py` — Positions

**Purpose:** Capture and manage all positions.

Layout wireframe: [`docs/ui/wireframes.md#opportunities`](docs/ui/wireframes.md#opportunities).

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
| Delete | Button rendered **below the form** (outside the `st.form` box), **inside the Overview tab body** (`with tabs[0]:`) so `st.tabs`'s natural CSS-hide makes it user-visible only when the Overview tab is active. Clicking opens an `@st.dialog` confirmation (outside `st.form`); on Confirm, `delete_position(id)` runs and the FK cascade removes the position's `applications`, `interviews`, and `recommenders` rows atomically. The button's scope is the whole position, not the active tab's data — hence the Overview-only placement, matching the tab where the user is reviewing the position as a whole. |

**Edit-panel architecture.** The four tabs use `st.tabs(config.EDIT_PANEL_TABS)`,
NOT `st.radio + conditional rendering`. `st.tabs` keeps every tab body
mounted on every script run (CSS hides the inactive ones), which is
load-bearing: Streamlit's documented v1.20+ behaviour wipes
`session_state` for unmounted widget keys, so any conditional-render
approach causes user-visible data loss across tab switches (the
text_input's value silently resets to its `value=` default on remount).
A short-lived 2026-04-25 experiment with `st.radio + conditional
rendering` — which had been chosen to expose a programmatic
`active_tab` for the Delete-button gate — was reverted after this
class of bug surfaced. The Delete-button placement above does not
require a programmatic active-tab signal: placing the button inside
`with tabs[0]:` lets `st.tabs`'s CSS-hide handle visibility naturally.

**Selection-survival invariant.** Save on any tab, filter change that
still includes the selected row, and dialog-Cancel must all preserve
`selected_position_id`. Implementation hides the state-management
details from users.

---

### 8.3 `pages/2_Applications.py` — Progress

**Purpose:** Track every position from submission to outcome, including
the full interview sequence.

Layout wireframe: [`docs/ui/wireframes.md#applications`](docs/ui/wireframes.md#applications).

**Behaviour:**
- **Default filter** excludes positions with status `STATUS_SAVED` or `STATUS_CLOSED` — they are pre-application or withdrawn and have no application data worth showing. The exclusion set is encoded in `config.STATUS_FILTER_ACTIVE_EXCLUDED` (§5.1) and exposed as a single selectbox sentinel `config.STATUS_FILTER_ACTIVE` (`"Active"`); the user can flip to the explicit `"All"` sentinel or a specific status to widen the view.
- **"All recs submitted"** column is a live computation via `database.is_all_recs_submitted(position_id)`; no stored summary.
- **"Confirmation"** column inlines `confirmation_received` + `confirmation_date` into the cell text:

    | State | Cell text |
    |-------|-----------|
    | `confirmation_received == 0` | `—` |
    | `confirmation_received == 1`, `confirmation_date` set | `✓ {Mon D}` (e.g. `✓ Apr 19`) |
    | `confirmation_received == 1`, `confirmation_date` NULL | `✓ (no date)` |

    The raw integer is never shown. **D-A amendment (Phase 5 T1-C, 2026-04-30):** the original D-A wording specified a per-cell tooltip (`Received {ISO date}` / `Received (no date recorded)`), but Streamlit 1.56's `st.dataframe` does not expose a per-cell tooltip API — `st.column_config.Column(help=...)` is column-header only, and pandas Styler tooltips do not transfer through the Arrow protobuf. Folding the tooltip text into inline cell content honors every piece of D-A's information visibly at-a-glance and matches the T4 Upcoming Date-column format (`MMM D`, no year). Resolution recorded in `reviews/phase-5-tier1-review.md`.
- **Interviews** are edited as an **inline list** under the application detail card:
  - Each row in the list = one `interviews` record, ordered by `sequence`. Per-row widgets: `scheduled_date` (`st.date_input`), `format` (`st.selectbox` over `config.INTERVIEW_FORMATS`), `notes` (`st.text_input`), and a Delete `🗑️` button. Widget keys scope to the interview's primary key for stability across reruns: `apps_interview_{id}_{date|format|notes|delete}`.
  - Below the list, an `Add another interview` button (`apps_add_interview`) appends a new row; `database.add_interview` computes the next `sequence` itself.
  - Save commits all dirty rows in one click via an `apps_interviews_form` form (one `database.update_interview` call per dirty row).
  - Delete on any row routes through a `@st.dialog` confirm before `database.delete_interview(id)`. The `interviews` FK CASCADE is rooted at `applications.position_id` per §6.2.
  - On add, if `add_interview` returns `status_changed=True` (R2 fired, see §9.3), the page surfaces `st.toast(f"Promoted to {STATUS_LABELS[new_status]}.")`.
- **Pipeline promotions** fire inside `database.upsert_application(propagate_status=True)` and `database.add_interview(propagate_status=True)` — see §9.3. The page does NOT detect transitions; it just calls the writer and reads the returned promotion indicator to surface a `st.toast`.
- **Status selectbox** (read-only here; this page edits applications, not the pipeline) shows `STATUS_LABELS[raw]`.

---

### 8.4 `pages/3_Recommenders.py` — Recommenders

**Purpose:** Track every letter across every position; surface who needs a reminder.

Layout wireframe: [`docs/ui/wireframes.md#recommenders`](docs/ui/wireframes.md#recommenders).

**Behaviour:**
- **Alert panel grouping:** `get_pending_recommenders()` returns one row per (recommender × position); the page groups by `recommender_name` so one recommender who owes N letters appears as a single card listing all N positions.
- **Reminder helpers** (per recommender card): two affordances — a quick mailto for the simple case, and an LLM-prompt expander for users who want a richer drafted email.
  - **Primary `Compose reminder email` button** opens a `mailto:` URL with locked, professional copy:
    - Subject: `Following up: letters for N postdoc applications` (where `N` is the position count for that recommender)
    - Body: `Hi {recommender_name}, just a quick check-in on the letters of recommendation you offered. Thank you so much!`

    The OS hands off to the user's default mail client; no outbound email integration. No signature is appended — the mail client appends one.
  - **Secondary `LLM prompts (N tones)` expander** beneath the primary button reveals one or more pre-filled prompts the user can paste into Claude / ChatGPT for a richer email draft. Prompts render as `st.code(...)` blocks so Streamlit's built-in copy button on hover is available. Each prompt is filled with:
    - the recommender's name + relationship,
    - the positions owed (position name, institute, deadline),
    - days since the recommender was asked,
    - a target tone — one prompt per tone (gentle / urgent).

    The expander label includes the prompt count, e.g. `LLM prompts (2 tones)`. The prompts ask the LLM to return both subject and body so the user can paste either / both into their mail client.
- **Add-recommender form:** position dropdown shows `position_name` + institute; IDs never surface to the user.
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

**The cascade is fully owned by `database.py`. Pages are display-only
(D12).**

Two writers can promote `positions.status` as a side effect — both
accept a keyword argument `propagate_status: bool = True`; when False,
no pipeline promotion fires.

**Placeholder convention.** In the SQL snippets below, `<STATUS_*>`
and `<RESPONSE_TYPE_OFFER>` placeholders interpolate to the
corresponding `config.py` alias value at query-construction time, and
`<TERMINAL_STATUSES>` interpolates to the tuple of all terminal status
values. References elsewhere in this section use the alias names
directly (e.g. `STATUS_APPLIED`, `RESPONSE_TYPE_OFFER`) rather than
the underlying literal (e.g. `[APPLIED]`, `"Offer"`), so a rename in
`config.py` does not ripple into this section.

| # | Trigger (in which writer) | Condition | Cascade |
|---|--------------------------|-----------|---------|
| R1 | `upsert_application` | `applied_date` transitions from NULL to non-NULL | `UPDATE positions SET status = '<STATUS_APPLIED>' WHERE id = ? AND status = '<STATUS_SAVED>'` |
| R2 | `add_interview` | Any successful interview insert | `UPDATE positions SET status = '<STATUS_INTERVIEW>' WHERE id = ? AND status = '<STATUS_APPLIED>'` |
| R3 | `upsert_application` | `response_type` transitions to `<RESPONSE_TYPE_OFFER>` | `UPDATE positions SET status = '<STATUS_OFFER>' WHERE id = ? AND status NOT IN (<TERMINAL_STATUSES>)` |

**R1 and R2 are idempotent by construction** — the `AND status = '<prev>'`
guard makes the cascade a no-op when the position is already at or past
the target stage. R2 does **not** inspect the interview count: the
status guard alone delivers the correct semantics (first interview on a
`STATUS_APPLIED` position promotes; subsequent interviews on a
`STATUS_INTERVIEW` position are no-ops; a position at `STATUS_OFFER` or
terminal is not regressed). An earlier draft of R2 counted interviews
("exactly one after insert") but that over-restricts: if the user
back-edits status to `STATUS_APPLIED` while retaining existing
interviews, adding another interview would fail to promote. The
count-free form avoids this.

**R3 overrides non-terminal stages but guards against terminals.**
Receiving an Offer while at `STATUS_SAVED`, `STATUS_APPLIED`, or
`STATUS_INTERVIEW` lands the position at `STATUS_OFFER` directly. A
position already in a terminal stage (any member of
`TERMINAL_STATUSES`) is **not** silently regressed — the user must
first move the status out of the terminal bucket, and then the next
`upsert_application` with `response_type = RESPONSE_TYPE_OFFER` will
promote. This prevents a stray edit, data import, or misread response
from clobbering a terminal decision.

If R1 and R3 fire from the same `upsert_application` call, the combined
effect depends on the pre-state. The per-state behaviour is:

| Pre-state | R1 fires? | R3 fires? | Post-state |
|-----------|-----------|-----------|------------|
| `STATUS_SAVED` | Yes (→ `STATUS_APPLIED`) | Yes (→ `STATUS_OFFER`) | `STATUS_OFFER` |
| `STATUS_APPLIED` | No | Yes (→ `STATUS_OFFER`) | `STATUS_OFFER` |
| `STATUS_INTERVIEW` | No | Yes (→ `STATUS_OFFER`) | `STATUS_OFFER` |
| `STATUS_OFFER` | No | Yes (no-op, already there) | `STATUS_OFFER` |
| any member of `TERMINAL_STATUSES` | No | No (terminal guard) | unchanged |

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

See [`docs/dev-notes/extending.md`](docs/dev-notes/extending.md) for
step-by-step recipes (add a requirement document, add or rename a
pipeline status, switch the tracker profile, etc.). For the concise
summary of what editing each `config.py` constant affects, see
[§5.3 Extension recipes](#53-extension-recipes) above.

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
