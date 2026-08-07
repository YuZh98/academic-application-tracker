# System Design: Academic Application Tracker
**Version:** 1.9 | **Last updated:** 2026-08-07 | **Status:** authoritative

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
12. [Future Directions](#12-future-directions)

---

## 1. Purpose & Scope

### Problem
An academic job search means tracking dozens of positions in parallel across different institutions, each with unique deadlines, document requirements, recommendation letter logistics, and outcome timelines. A spreadsheet or markdown file cannot answer the daily question: **"What do I do today?"**

### Solution
A local, single-user web app that:
- Captures new positions in under 30 seconds
- Auto-computes and surfaces urgent actions
- Tracks recommendation letter status per recommender, per position
- Maintains human-readable markdown exports as a portable backup
- Extends to a general job tracker via a single config file edit

### Explicit Non-Goals (v1)
- No auth
- No cloud deploy as a primary target — local is the only supported home for real data. A public demo runs on Streamlit Cloud with per-session throwaway sandboxes (see §7 `db_session.py`); it is a showcase, not a deployment path.
- No mobile-first layout
- No email/calendar integration
- No multi-user

---

## 2. Architecture Overview

```mermaid
flowchart BT
    config[config.py<br/><small>constants + pure functions</small>]
    database[database.py<br/><small>SQL only</small>]
    exports[exports.py<br/><small>markdown writers</small>]
    ui[ui.py<br/><small>design system</small>]
    db_session[db_session.py<br/><small>demo session wiring</small>]
    pages[pages/*.py<br/><small>display layer</small>]
    app[app.py<br/><small>Dashboard</small>]

    database -->|imports| config
    exports -->|imports| config
    exports -->|imports| database
    ui -->|imports| config
    db_session -->|imports| config
    db_session -->|imports| database
    app -->|imports| config
    app -->|imports| database
    app -->|imports| ui
    app -->|imports| db_session
    pages -->|imports| config
    pages -->|imports| database
    pages -->|imports| ui
    pages -->|imports| db_session

    database -.->|deferred import<br/>inside writers| exports

    classDef leaf fill:#e1f5fe,stroke:#01579b
    classDef data fill:#fff3e0,stroke:#e65100
    classDef ui fill:#f3e5f5,stroke:#4a148c
    classDef bridge fill:#e8f5e9,stroke:#1b5e20
    class config leaf
    class database,exports data
    class app,pages,ui ui
    class db_session bridge
```

The dotted edge from `database` to `exports` is the deferred-import escape hatch that breaks the otherwise-circular dependency. Solid edges represent module-top imports.

`db_session.py` is the one deliberate exception to the "nothing imports both `streamlit` and `database`" separation: it is the dependency-injection wiring that puts a per-session demo connection behind `database._connect()` without making `database.py` aware of Streamlit. See §7 for its contract.

### Layer rules (enforced)

| Layer | May import | May NOT import |
|-------|-----------|----------------|
| Page files | `database`, `config`, `ui`, `db_session` | `exports` (directly), each other |
| `database.py` | `config`, `sqlite3`, `pandas` | `streamlit`, `exports` (top-level — deferred import only) |
| `exports.py` | `database`, `config` | `streamlit` |
| `ui.py` | `config`, `streamlit` | `database`, `exports`, page modules |
| `db_session.py` | `config`, `database`, `streamlit`, `scripts/seed_demo_db` | `exports`, `ui`, page modules |
| `config.py` | stdlib only | anything from this project |

---

## 3. Technology Stack

| Component | Choice | Required ≥ | Rationale |
|-----------|--------|-----------|-----------|
| Language | Python | 3.11 | Declared floor in `pyproject.toml`; familiar to stats/data users |
| Environment | venv (`.venv/`) | stdlib | Zero extra tools; isolates pkgs; gitignored |
| UI framework | Streamlit | 1.50 | Python-native; `width="stretch"` and `st.switch_page` need ≥ 1.50 |
| Charts | Plotly (Graph Objects) | 5.22 | Used via `plotly.graph_objects.Figure` / `go.Bar`; click events for future interactivity |
| Data frames | pandas | 2.2 | Bridges SQLite rows ↔ Streamlit display widgets |
| Database | SQLite via `sqlite3` | stdlib | No server; single file; standard SQL; gitignored |

`requirements.txt` pins exact versions; the `Required ≥` column is the floor for any upgrade.

### 3.1 Runtime assumptions

Single-user, local-only. Expected scale: 10²–10³ positions, 1–10 interviews each, 1–20 recommenders. SQLite handles this without tuning. UTF-8 everywhere. Local machine timezone. One writer at a time (Streamlit process).

The public demo deploy relaxes "one process, one user" — many concurrent visitors share a single Python process, each isolated behind a per-session in-memory database. The concurrency invariants that make this safe live in `db_session.py` (§7).

---

## 4. File Structure

```
app.py                    Dashboard home page
config.py                 Single source of truth for constants and vocabulary
database.py               All SQLite I/O; no Streamlit imports
exports.py                Markdown generators; called by database.py writers
ui.py                     Shared design-system stylesheet + pill/header helpers
db_session.py             Demo-mode wiring: per-session in-memory SQLite for Streamlit Cloud
pages/
  1_Opportunities.py      Position CRUD + bulk actions
  2_Applications.py       Progress tracking + interviews
  3_Recommenders.py       Letter tracking + reminder helpers
  4_Export.py             Manual export + file download
  5_Settings.py           Tunable thresholds + append-only status vocabulary
scripts/
  seed_demo_db.py         Demo dataset: CLI seeder + seed() library entry for db_session
  release.sh              CHANGELOG rotation for release tags
  crop_screenshots.py     Idempotent crop helper for README captures
  build_collage.py        Headless-Chromium renderer for the marketing collage
  collage.html            CSS3D template loaded by build_collage.py
  build_ux_report.py      UX field-study PDF + chart builder
.streamlit/               Streamlit app configuration
exports/                  Auto-generated markdown backups (gitignored)
postdoc.db                SQLite database (gitignored)
tests/                    pytest suite
docs/
  adr/                    Architectural Decision Records
  dev-notes/              Deep-dive references
  ui/                     Wireframes + responsive screenshots
DESIGN.md                 This file
GUIDELINES.md             Coding conventions
roadmap.md                Development phases, backlog, and future plans
CHANGELOG.md              Release history
```

---

## 5. `config.py` — Specification

`config.py` is the **single source of truth** for vocabularies, constants, and field definitions. Every other module reads from it; no other file hardcodes a status string, priority value, or requirement-document label. The sole import-time side effect is `IS_DEMO`, which reads the `AAT_DEMO` env var once at module load — every other module reads `config.IS_DEMO`, never the env var.

### 5.1 Symbol index

#### App identity & demo mode

| Constant | Type | Role |
|----------|------|------|
| `APP_VERSION` | `str` | User-visible version string (sidebar About block). Sync with `pyproject.toml` pinned by `test_app_version_matches_pyproject`. |
| `IS_DEMO` | `bool` | True iff env `AAT_DEMO=1` (set only on the Streamlit Cloud dashboard). Gates `db_session.bind()`, export short-circuits, Settings save-disable, and the demo banner. |
| `DEMO_BANNER_HEADLINE` / `DEMO_BANNER_BODY` | `str` | Copy for the demo banner rendered by `ui.demo_banner()` when `IS_DEMO`. |
| `DEMO_SELF_HOST_URL` | `str` | Self-host instructions link rendered at the end of the demo banner. |

#### Profile identity & glyphs

| Constant | Type | Role |
|----------|------|------|
| `DB_FILENAME` | `str` | SQLite filename (`postdoc.db`). Rename the file on disk when changing. |
| `APPLICATION_LABEL` | `str` | Label used in recommender follow-up email subjects. |
| `FOOTER_AUTHOR_MARK` | `str` | Optional surname-style mark in the folio footer; empty by default so a fresh clone ships unbranded. |
| `EM_DASH` | `str` | Universal placeholder glyph for NULL / NaN / empty TEXT cells across every user-facing surface. |
| `WARN_GLYPH` | `str` | `▲` (U+25B2) — editorial warning mark replacing the legacy ⚠️ emoji on dashboard + Recommenders alert headers. |
| `ACCENT_VERMILION` | `str` | Python-side literal for the vermilion accent; the CSS `:root` block in `ui.py` intentionally duplicates the value. |

#### Status pipeline

| Constant | Type | Role |
|----------|------|------|
| `STATUS_VALUES` | `list[str]` | Ordered pipeline: `[SAVED]` → `[APPLIED]` → `[INTERVIEW]` → `[OFFER]` → `[CLOSED]` → `[REJECTED]` → `[DECLINED]`. |
| `STATUS_SAVED` … `STATUS_DECLINED` | `str` | Named aliases for each `STATUS_VALUES[i]`; page code uses these, never literals. |
| `TERMINAL_STATUSES` | `list[str]` | Subset (`[CLOSED]`/`[REJECTED]`/`[DECLINED]`) excluded from active queries and guarding R3 against regression. |
| `STATUS_COLORS` | `dict[str, str]` | Per-status color for badges and tooltips (not funnel bars — see `FUNNEL_BUCKETS`). |
| `STATUS_LABELS` | `dict[str, str]` | Storage→UI label map; every user-facing status surface must go through this. |
| `DEADLINE_ACTIONABLE_STATUSES` | `list[str]` | `[STATUS_SAVED]` — the only statuses whose deadlines surface on the dashboard Upcoming panel; once applied, the deadline is moot. |
| `MANUAL_STATUS_VALUES` | `list[str]` | Statuses the user can pick by hand in the Opportunities edit-panel Status selectbox. `[INTERVIEW]`/`[OFFER]` excluded — reachable only via the R2/R3 cascades. Filter selectboxes keep using `STATUS_VALUES`. |
| `FILTER_ALL` | `str` | Universal `"All"` sentinel for filter selectboxes; rendered as `[FILTER_ALL] + <options>`, page narrows only when the selection differs. |

#### Dashboard funnel (presentation layer)

| Constant | Type | Role |
|----------|------|------|
| `FUNNEL_BUCKETS` | `list[tuple[str, tuple[str, ...], str]]` | Groups raw statuses into funnel bars: `(UI label, raw-status tuple, color)`. Multiset coverage of `STATUS_VALUES` guarded by invariant #5. |
| `FUNNEL_DEFAULT_HIDDEN` | `set[str]` | Bucket labels hidden by default; revealed via disclosure toggle. |
| `FUNNEL_TOGGLE_LABELS` | `dict[bool, str]` | State-keyed labels for the funnel disclosure toggle (`False` → expand CTA, `True` → collapse CTA). |

#### Vocabularies (user-facing selectbox options)

| Constant | Type | Role |
|----------|------|------|
| `PRIORITY_VALUES` | `list[str]` | `High` / `Medium` / `Low` / `Stretch` — user subjective fit, distinct from computed urgency. |
| `WORK_AUTH_OPTIONS` | `list[str]` | `Yes` / `No` / `Unknown`; paired with freetext `work_auth_note` (D22). |
| `FULL_TIME_OPTIONS` | `list[str]` | `Full-time` / `Part-time` / `Contract`. |
| `SOURCE_OPTIONS` | `list[str]` | Where posting was found (lab site, job board, referral, etc.). |
| `RESPONSE_TYPES` | `list[str]` | First-response categorization; `"Offer"` fires auto-promotion R3 (§9.3). |
| `RESPONSE_TYPE_OFFER` | `str` | Named alias for R3 cascade trigger — anti-typo guardrail. |
| `RESULT_DEFAULT` | `str` | `"Pending"` — matches schema DEFAULT; renaming requires a migration (§6.3). |
| `RESULT_VALUES` | `list[str]` | Final outcome: Pending / Accepted / Declined / Rejected / Withdrawn. |
| `RELATIONSHIP_VALUES` | `list[str]` | Recommender→applicant relationship (advisor, committee, collaborator, …). |
| `INTERVIEW_FORMATS` | `list[str]` | `Phone` / `Video` / `Onsite` / `Other`. |
| `CONFIRMED_LABELS` | `dict[int \| None, str]` | Maps recommender `confirmed` (1/0/NULL) to display strings; shared by pages and exports. |
| `REMINDER_TONES` | `tuple[str, ...]` | `gentle` / `urgent` — tones offered by the Recommenders-page LLM-prompts expander. |

#### Requirement documents

| Constant | Type | Role |
|----------|------|------|
| `REQUIREMENT_VALUES` | `list[str]` | `Yes` / `Optional` / `No` — canonical DB values for `req_*` columns. |
| `REQUIREMENT_LABELS` | `dict[str, str]` | UI labels for the three values; radios use `format_func=REQUIREMENT_LABELS.get`. |
| `REQUIREMENT_DOCS` | `list[tuple[str, str, str]]` | `(req_column, done_column, display_label)` per doc type. Append one tuple to add a new doc type — `init_db()` auto-adds both columns on next start. |
| `REC_LETTERS_REQ_COL` / `REC_LETTERS_DONE_COL` / `REC_LETTERS_COUNT_COL` | `str` | Column names for the LOR-specific readiness rule; single source of truth shared by the Materials tab and `database.py`'s rec-letters sync helper (§7). |

#### Forms and UI structure

| Constant | Type | Role |
|----------|------|------|
| `QUICK_ADD_FIELDS` | `list[str]` | The six essential capture fields, ordered: `position_name`, `institute`, `field`, `deadline_date`, `priority`, `link`. The quick-add form renders these plus three fixed enrichment fields (`location`, `source`, `portal_url`) hardcoded on the page; total input cap ≤ 9 per D6. Coverage of the six pinned by `tests/test_opportunities_page.py`. |
| `EDIT_PANEL_TABS` | `list[str]` | Tab labels for Opportunities edit panel in display order: `Overview`, `Requirements`, `Materials`, `Notes`. |

#### Dashboard thresholds (days)

| Constant | Type | Role |
|----------|------|------|
| `DEADLINE_ALERT_DAYS` | `int` | Upper edge of 🟡 urgency band; also default Upcoming panel window width. |
| `DEADLINE_URGENT_DAYS` | `int` | Inner 🔴 urgency band. Must be ≤ `DEADLINE_ALERT_DAYS` (invariant #8). |
| `RECOMMENDER_ALERT_DAYS` | `int` | Days since asked with no submission → surfaces on Recommender Alerts. |
| `UPCOMING_WINDOW_OPTIONS` | `list[int]` | Selectable widths for Upcoming panel (`[30, 60, 90]`); `DEADLINE_ALERT_DAYS` must be in this list. |

#### Empty-state & fallback copy

| Constant | Type | Role |
|----------|------|------|
| `EMPTY_FILTERED_POSITIONS` / `EMPTY_NO_POSITIONS` / `EMPTY_FILTERED_APPLICATIONS` / `EMPTY_PENDING_RECOMMENDERS` / `EMPTY_PENDING_RECOMMENDER_FOLLOWUPS` | `str` | Canonical empty-state copy per surface; pages render these verbatim so tests can pin them. |
| `RECOMMENDER_NAME_FALLBACK` | `str` | Display sentinel for a pending-recommender row with NULL name — applied via `fillna` before any `groupby("recommender_name")` so pandas' `dropna=True` default cannot silently drop the row. |

#### Pure functions

| Function | Signature | Role |
|----------|-----------|------|
| `urgency_glyph` | `(days_away: int \| None) -> str` | Urgency banding: 🔴 ≤ `DEADLINE_URGENT_DAYS`, 🟡 ≤ `DEADLINE_ALERT_DAYS`, `""` beyond, `EM_DASH` for `None`. Negative (past-due) inputs stay urgent. |

### 5.2 Import-time invariants

`config.py` runs these assertions at module import. A violation aborts app startup with a clear traceback — catching drift before any page renders. Numbers are stable identifiers referenced by `test_invariant_<N>_*` in `tests/test_config.py`; #1 and #12 are retired and the slots are intentionally left empty (#12 guarded the removed `STATUS_FILTER_ACTIVE_EXCLUDED`):

2. `set(STATUS_VALUES) == set(STATUS_COLORS)` — every status has a color
3. `set(STATUS_VALUES) == set(STATUS_LABELS)` — every status has a UI label
4. `set(TERMINAL_STATUSES) <= set(STATUS_VALUES)` — terminals are a subset
5. Multiset equality: flattened `FUNNEL_BUCKETS` raw statuses == `STATUS_VALUES`
6. `FUNNEL_DEFAULT_HIDDEN <= {bucket labels}` — hidden set references real buckets
7. `set(REQUIREMENT_LABELS) == set(REQUIREMENT_VALUES)` — every req value has a label
8. `DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS` — thresholds ordered correctly
9. `RESPONSE_TYPE_OFFER in RESPONSE_TYPES` — R3 trigger must be a real option
10. `DEADLINE_ALERT_DAYS in UPCOMING_WINDOW_OPTIONS` — default must be in offered list
11. `set(FUNNEL_TOGGLE_LABELS.keys()) == {True, False}` — both toggle states have labels

Additional import-time guards without stable numbers (pinned by their own tests, not the `test_invariant_<N>` scheme):

- `set(MANUAL_STATUS_VALUES) <= set(STATUS_VALUES)` — manual picker options must be real statuses
- `STATUS_INTERVIEW not in MANUAL_STATUS_VALUES` and `STATUS_OFFER not in MANUAL_STATUS_VALUES` — cascade-owned statuses are never hand-assignable
- `set(CONFIRMED_LABELS.keys()) == {1, 0, None}` — every `confirmed` storage value has a display label

### 5.3 Extension recipes

| Goal | What to edit |
|------|--------------|
| Add new requirement document | Append one tuple to `REQUIREMENT_DOCS`. `init_db()` adds columns on next start. No other file changes. |
| Add a vocabulary option | Append to relevant list (`SOURCE_OPTIONS`, `RESPONSE_TYPES`, etc.). No DB change. |
| Add a new pipeline status | Append to `STATUS_VALUES` + add alias; add entries to `STATUS_COLORS`, `STATUS_LABELS`, `FUNNEL_BUCKETS`; if terminal, append to `TERMINAL_STATUSES`. |
| Rename a pipeline status | Edit all references + write one-shot `UPDATE` migration in CHANGELOG. |
| Change a dashboard threshold | Edit `DEADLINE_*` or `RECOMMENDER_ALERT_DAYS`. Invariants catch inverted thresholds. |
| Switch the tracker profile | See §12 and `roadmap`. |

---

## 6. Database Schema

Canonical DDL lives in `database.init_db()`. This section is the architectural description of that DDL.

### 6.1 Entity-Relationship summary

```
positions (1) ──< applications (1) ──< interviews (many)
positions (1) ──< recommenders (many)
```

### 6.2 Tables

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS positions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    status           TEXT    NOT NULL DEFAULT '<STATUS_SAVED>',
    priority         TEXT,
    created_at       TEXT    DEFAULT (date('now')),
    updated_at       TEXT    DEFAULT (datetime('now')),
    position_name    TEXT    NOT NULL,
    institute        TEXT,
    location         TEXT,
    field            TEXT,
    deadline_date    TEXT,         -- ISO-8601 'YYYY-MM-DD'
    deadline_note    TEXT,
    stipend          TEXT,
    work_auth        TEXT,         -- Yes/No/Unknown
    work_auth_note   TEXT,
    full_time        TEXT,         -- Full-time/Part-time/Contract
    source           TEXT,
    link             TEXT,
    mentor           TEXT,
    point_of_contact TEXT,
    portal_url       TEXT,
    keywords         TEXT,
    description      TEXT,
    num_rec_letters  INTEGER,
    reference_code   TEXT,
    notes            TEXT
    -- + req_* TEXT DEFAULT 'No' and done_* INTEGER DEFAULT 0 pairs
    -- generated from config.REQUIREMENT_DOCS by init_db()
);

CREATE TRIGGER IF NOT EXISTS positions_updated_at
    AFTER UPDATE ON positions FOR EACH ROW
BEGIN
    UPDATE positions SET updated_at = datetime('now') WHERE id = NEW.id;
END;

CREATE TABLE IF NOT EXISTS applications (
    position_id            INTEGER PRIMARY KEY,
    applied_date           TEXT,
    confirmation_received  INTEGER DEFAULT 0,
    confirmation_date      TEXT,
    response_date          TEXT,
    response_type          TEXT,
    result_notify_date     TEXT,
    result                 TEXT    DEFAULT '<RESULT_DEFAULT>',
    notes                  TEXT,
    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  INTEGER NOT NULL,
    sequence        INTEGER NOT NULL,
    scheduled_date  TEXT,
    format          TEXT,
    notes           TEXT,
    UNIQUE (application_id, sequence),
    FOREIGN KEY (application_id) REFERENCES applications(position_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS recommenders (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id         INTEGER NOT NULL,
    recommender_name    TEXT,
    relationship        TEXT,
    asked_date          TEXT,
    confirmed           INTEGER,
    submitted_date      TEXT,
    reminder_sent       INTEGER DEFAULT 0,
    reminder_sent_date  TEXT,
    notes               TEXT,
    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_positions_status      ON positions(status);
CREATE INDEX IF NOT EXISTS idx_positions_deadline    ON positions(deadline_date);
CREATE INDEX IF NOT EXISTS idx_interviews_application ON interviews(application_id);
```

**DDL DEFAULTs are config-driven.** `init_db()` builds DDL via f-strings reading `config.STATUS_VALUES[0]` and `config.RESULT_DEFAULT`. Column names for `req_*`/`done_*` pairs come from `config.REQUIREMENT_DOCS`.

### 6.3 Data migrations

`init_db()` is idempotent — safe to call on every app start. Schema evolution takes one of three shapes:

**Auto-migrated (handled by `init_db()` on next start):**

| Change | Mechanism |
|--------|-----------|
| New entry in `config.REQUIREMENT_DOCS` | `ALTER TABLE ADD COLUMN` for both `req_*` and `done_*`, guarded by `PRAGMA table_info` |
| New table, trigger, or index | `CREATE ... IF NOT EXISTS` |
| New vocab option | No DDL — columns are plain TEXT; dropdowns pick up on next render |
| New column on existing table | `ALTER TABLE ADD COLUMN` guarded by existence check |

**Manual (requires migration step, recorded in CHANGELOG):**

| Change | Required step |
|--------|---------------|
| Rename status value | `UPDATE positions SET status = '<new>' WHERE status = '<old>'` |
| Rename `RESULT_DEFAULT` | `UPDATE applications SET result = '<new>' WHERE result = '<old>'` |
| Split or normalize columns | `ALTER TABLE ADD COLUMN` + `UPDATE` to copy data; leave old col NULL until rebuild |
| Remove a column | SQLite 3.35+: `ALTER TABLE <t> DROP COLUMN <c>` when no constraints reference it. Otherwise requires table rebuild. |

**Migration discipline:** every schema or vocabulary change lands with a `Migration:` note in `CHANGELOG` under the release that introduces it, giving the exact `UPDATE` or rebuild SQL. A user upgrading between releases never has to guess which migration to run.

### 6.4 Schema design decisions

Rationale for the schema choices lives in §10.

---

## 7. Module Contracts

### `database.py`

**Role.** All SQLite I/O. No Streamlit imports; no display logic. Reads + writes SQLite DB file only — other filesystem I/O belongs in `exports.py`. Readers return pandas DataFrames for multi-row queries, plain dicts for single-row lookups. Writers return new row id (inserts) or `None` (updates, deletes).

**Public API (grouped by concern):**

| Group | Functions |
|-------|-----------|
| Schema lifecycle | `init_db` |
| Connection provider | `set_connection_provider` — installs a callable returning the connection `_connect()` should yield; `None` restores file mode. Demo-only injection point used by `db_session.py`. |
| Positions | `add_position`, `get_all_positions`, `get_position`, `update_position`, `delete_position` |
| Bulk actions | `bulk_promote_to_applied`, `bulk_set_requirement` |
| Applications | `get_application`, `upsert_application`, `is_all_recs_submitted`, `get_applications_table` |
| Interviews | `add_interview`, `get_interviews`, `update_interview`, `delete_interview` |
| Recommenders | `add_recommender`, `get_recommenders`, `get_all_recommenders`, `update_recommender`, `delete_recommender` |
| Dashboard queries | `count_by_status`, `get_upcoming_deadlines`, `get_upcoming_interviews`, `get_upcoming`, `get_pending_recommenders`, `compute_materials_readiness` |
| Export helpers | `regenerate_exports`, `get_export_paths` — Export page's manual trigger + download list |
| Settings | `load_settings`, `save_settings`, `update_status_vocabulary` — persistence behind the Settings page (§8.6) |

**Load-bearing contracts:**

1. **Exports after writes.** Every public write function calls `exports.write_all()` as its last step, inside a try/except that logs errors but does not re-raise. A write that succeeded in the DB always reports success to the caller, even if markdown regeneration failed. The import of `exports` inside each writer is deferred (not at module top) to break the circular import.

2. **Pipeline auto-promotion.** Two writers can promote `positions.status` as a side effect — `upsert_application` and `add_interview`. Both accept kwarg `propagate_status: bool = True`; when False, no pipeline side-effect fires. Promotion rules R1/R2/R3 are documented in §9.3 and run atomically inside the same transaction as the primary write. `delete_interview` applies the symmetric reverse cascade (§9.3 R2⁻) with no opt-out kwarg.

3. **Idempotent init.** `init_db()` runs on every app start. It creates tables, triggers, and indices with `IF NOT EXISTS`; runs the `REQUIREMENT_DOCS`-driven `ALTER TABLE ADD COLUMN` loop; and re-checks all invariants. Safe to call any number of times.

4. **Sparse-dict returns.** Aggregation queries (`count_by_status`, others) may omit zero-count keys. Callers fill missing keys with 0 before display.

5. **Sort orders are part of the contract.** `get_all_positions` returns rows ordered by `deadline_date ASC NULLS LAST`; `get_upcoming_*` queries return chronological order; `get_all_recommenders` orders by `recommender_name`.

6. **Rec-letters readiness sync.** Every recommender write (add / update / delete) and any `update_position` touching `num_rec_letters` recomputes `positions.done_rec_letters` inside the same transaction, so the stored flag never desyncs from the live recommenders table (the one deliberate carve-out from D3/D23's compute-don't-store rule; `compute_materials_readiness` reads the column directly). Rule: done iff `num_rec_letters` is NULL/≤ 0, or submitted count ≥ `num_rec_letters`. Column names come from `config.REC_LETTERS_*`.

7. **Settings demo short-circuit.** When `config.IS_DEMO` is True, `load_settings` returns pure config defaults without reading the overlay file and `save_settings` performs no write — demo sessions never touch the shared filesystem.

8. **DB path resolution.** `DB_PATH` = env `AAT_DB_PATH` (expanded + resolved) when set, else `config.DB_FILENAME` alongside the module — the override lets screenshot capture, demo seeds, and ad-hoc isolated runs target a throwaway database. Precedence when both demo and override are active: an installed connection provider (demo mode) wins over `AAT_DB_PATH`; `db_session.bind()` logs a warning when it ignores the override.

### `exports.py`

**Role.** Generate three markdown backup files. Imports `database` and `config`; never imports Streamlit. Called by `database.py` writers (via deferred import) and the Export page's manual-trigger button.

| Function | Output |
|----------|--------|
| `write_all` | Calls all three writers below |
| `write_opportunities` | `exports/OPPORTUNITIES.md` |
| `write_progress` | `exports/PROGRESS.md` |
| `write_recommenders` | `exports/RECOMMENDERS.md` |

**Contracts:** (1) Errors are logged but never propagate — the DB write already succeeded. (2) Output is deterministic and idempotent — same DB state produces byte-identical output. (3) Demo short-circuit: when `config.IS_DEMO` is True, every writer returns without touching the filesystem — the shared demo host cannot be safely written from concurrent visitor sessions.

### `db_session.py`

**Role.** Demo-mode wiring: per-session in-memory SQLite for the Streamlit Cloud deploy. The one sanctioned module importing both `streamlit` and `database` (§2) — dependency-injection glue that puts a per-session connection behind `database._connect()` without making `database.py` Streamlit-aware. Every entry point is a no-op when `config.IS_DEMO` is False.

**Public API:**

| Function | Purpose |
|----------|---------|
| `bind()` | One-shot per-session setup, called by every page bootstrap before any `database.*` call. First call per session: opens `:memory:`, caches the connection in `st.session_state`, installs the provider via `database.set_connection_provider`, runs `init_db()` + `scripts.seed_demo_db.seed()`. Idempotent thereafter. |
| `reset()` | Wipes the calling session's cached connection + sentinel so the next render re-binds and re-seeds. Wired to the sidebar "Reset demo data" button via callback injection (`ui.sidebar_demo_reset_block`). |

**Load-bearing contracts:**

1. **Failure boundary is all-or-nothing per session.** Any exception during setup pops the cache, clears the provider, closes the connection, and re-raises — the next render retries from scratch. No recoverable partial state.
2. **The provider callable is a process-global singleton; isolation comes from `st.session_state`.** Every concurrent visitor shares the same provider object; each invocation resolves the connection from the *calling* session's state. Corollary: `reset()` must never clear the provider — it is shared across all live sessions, and clearing it would break the next `database._connect()` in other visitors' threads.
3. **Bootstrap order is test-enforced.** `tests/structure/test_bootstrap_order.py` fails any page whose source references `database.` before calling `db_session.bind()` — a page that misses `bind()` silently falls back to file mode on Cloud, where visitors would share state.

---

## 8. UI Design — Page by Page

### 8.0 Cross-page conventions

- **Page config:** Every page calls `st.set_page_config(layout="wide")` as first statement.
- **Bootstrap order:** `st.set_page_config` → `db_session.bind()` → `database.init_db()` → `ui.inject_global_styles()`. `bind()` must precede any `database.*` call (§7 db_session contract #3; test-enforced).
- **Widget keys:** Scope prefixes (`qa_`, `edit_`, `filter_`, `_` for internals). Form ids suffixed `_form`.
- **Status labels:** Pages never render raw `[SAVED]` etc. — always through `STATUS_LABELS[raw]`.
- **Patterns:** Success → `st.toast`; failure → `st.error` (no traceback); irreversible → `@st.dialog` confirm; navigation → `st.switch_page`.

---

### 8.1 `app.py` — Dashboard (Home)

Answer "What do I do today?" in one glance. Layout wireframe: `docs/ui/wireframes §dashboard`.

**Panel specifications:**

| Panel | Data source | Behaviour |
|-------|------------|-----------|
| KPI grid | `count_by_status()` | Four metrics: Tracked (Saved+Applied), Applied, Interview, Next Interview (earliest future date + institute). |
| Funnel | `count_by_status()` summed into `FUNNEL_BUCKETS`; Plotly horizontal `go.Bar`, y-axis reversed so earliest pipeline stage on top; bar color from `FUNNEL_BUCKETS[i][2]`. A disclosure toggle reveals/hides terminal-stage buckets (config-driven labels, bidirectional). | Bucket labels = `FUNNEL_BUCKETS[i][0]` |
| Materials Readiness | `compute_materials_readiness()` | Two stacked progress bars (ready / missing); CTA button to Opportunities page. |
| Upcoming | `database.get_upcoming(days=selected_window)` merges deadlines + interviews; `st.dataframe` with six cols: Date, Days left, Label, Kind, Status, Urgency. Deadline rows are restricted to `DEADLINE_ACTIONABLE_STATUSES` ([SAVED]) so an already-submitted position never resurfaces as a looming deadline. Window controlled by `st.selectbox` over `UPCOMING_WINDOW_OPTIONS`. | 🔴 ≤ `DEADLINE_URGENT_DAYS`; 🟡 ≤ `DEADLINE_ALERT_DAYS`. |
| Recommender Alerts | `get_pending_recommenders(RECOMMENDER_ALERT_DAYS)` | Grouped by recommender name; one card per person listing all owed positions. |


**Empty-DB hero.** When DB has no Saved, Applied, or Interview-stage positions, bordered hero container above KPI grid shows welcome subheader, explanatory paragraph, and primary CTA button that `st.switch_page("pages/1_Opportunities.py")`. KPI grid renders beneath hero regardless.

**Empty-state behaviour.** Each panel shows contextual `st.info(...)` guidance when its data source is empty. The funnel has three branches: (a) no data at all — info message, toggle suppressed; (b) all non-zero buckets are hidden — info message pointing at toggle; (c) normal render with toggle. Subheaders render in all branches for page-height stability.

---

### 8.2 `pages/1_Opportunities.py` — Positions

Capture and manage all positions. Layout wireframe: `docs/ui/wireframes §opportunities`.

**Behaviour:**

| Element | Behaviour |
|---------|-----------|
| Quick-add | Expander with the six `config.QUICK_ADD_FIELDS` essentials plus three fixed enrichment fields (`location`, `source`, `portal_url`); ≤ 9 inputs total (D6). Saves with `status = STATUS_VALUES[0]`; auto-creates `applications` row; nonce-keyed widgets clear the form on successful save. |
| Filters | Search text input (case-insensitive substring on `position_name`), Status selectbox (`[FILTER_ALL] + STATUS_VALUES`, `format_func=STATUS_LABELS.get`), Priority selectbox (`[FILTER_ALL] + PRIORITY_VALUES`), Field text input (literal substring match). |
| Table | `st.dataframe` with single-row selection; sorted by `deadline_date ASC NULLS LAST`; urgency badge on Due column; Link column as `LinkColumn`. |
| Edit panel | Four tabs (`st.tabs`): Overview (all fields), Requirements (radios per `REQUIREMENT_DOCS`), Materials (checkboxes for required docs), Notes (text_area in form). |
| Delete | Button in Overview tab; `@st.dialog` confirmation; FK cascade removes all child rows atomically. |

**Edit-panel architecture.** Four tabs use `st.tabs(config.EDIT_PANEL_TABS)`, NOT `st.radio + conditional rendering`. `st.tabs` keeps every tab body mounted on every script run (CSS hides inactive ones), which is load-bearing: Streamlit's documented v1.20+ behaviour wipes `session_state` for unmounted widget keys, so any conditional-render approach causes user-visible data loss across tab switches.

**Selection-survival invariant.** Save on any tab, filter change that still includes selected row, and dialog-Cancel must all preserve `selected_position_id`.

---

### 8.3 `pages/2_Applications.py` — Progress

Track every position from submission to outcome, including full interview sequence. Layout wireframe: `docs/ui/wireframes §applications`.

**Behaviour:**
- **Status filter selectbox:** options = `[FILTER_ALL, *STATUS_VALUES]`; default = `FILTER_ALL` (no narrowing). Wraps the label getter so the sentinel renders unchanged: `lambda v: STATUS_LABELS.get(v, v)`.
- **Read-only table:** seven columns — Position, Institute, Applied, Recs (✓/—), Confirmation (✓ + date or —), Response, Result. Sort from `database.get_applications_table()`.
- **Interviews** edited as **per-row blocks** under the app detail card. Each block contains: scheduled_date, format, notes, a per-row Save button (inside its own `st.form`), and a per-row Delete button (outside form, routed through `@st.dialog` confirm). Blocks separated by `st.divider()`. Below the last block, an `Add another interview` button appends a new row; `database.add_interview` computes next `sequence` itself. If `add_interview` returns `status_changed=True` (R2 fired), page surfaces a promotion toast.
- **Pipeline promotions** fire inside `database.upsert_application` and `database.add_interview` — see §9.3. Page does NOT detect transitions; just calls writer and reads returned promotion indicator.

---

### 8.4 `pages/3_Recommenders.py` — Recommenders

Track every letter across every position; surface who needs a reminder. Layout wireframe: `docs/ui/wireframes §recommenders`.

**Behaviour:**
- **Alert panel grouping:** `get_pending_recommenders()` returns one row per (recommender × position); page groups by `recommender_name` so one recommender owing N letters appears as single card listing all N positions.
- **Reminder helpers** (per recommender card): two affordances — a `Compose reminder email` button that opens a `mailto:` URL with a professional subject/body (pluralization-aware), and an `LLM prompts` expander with pre-filled prompts (gentle / urgent tones) the user can paste into Claude or ChatGPT for a richer draft.
- **Add-recommender form:** position dropdown shows `position_name` + institute; IDs never surface to user.
- **Inline edit** for each row: `asked_date`, `confirmed` (0/1/NULL), `submitted_date`, `reminder_sent` + `reminder_sent_date`, `notes`.

---

### 8.5 `pages/4_Export.py` — Export

Manual export trigger and per-file download. Layout wireframe: `docs/ui/wireframes §export`.

---

### 8.6 `pages/5_Settings.py` — Settings

Tunable thresholds + append-only vocabulary editor. Two stacked forms:

- **Alert thresholds** — `DEADLINE_ALERT_DAYS`, `RECOMMENDER_ALERT_DAYS`, `UPCOMING_WINDOW_DAYS` as bounded `st.number_input` widgets. Saved values land in `settings_overrides.json` next to the SQLite DB; `database.load_settings()` overlays them on top of the `config.py` defaults so the import-time invariants stay authoritative.
- **Status vocabulary (append-only)** — text-input + Append button. Sentinels must be bracketed (`[GHOSTED]`). Removal of a status currently held by any position is blocked at the boundary in `database.update_status_vocabulary`.

Persistence layer: `database.load_settings`, `database.save_settings`, `database.update_status_vocabulary`.

**Demo mode:** both Save/Append buttons render disabled with an info banner explaining that edits do not persist; `load_settings`/`save_settings` short-circuit to config defaults regardless (§7 database contract #7 — defense in depth).

---

### 8.7 Design System (`ui.py`)

Shared presentation layer. All visual identity lives here so every
page renders with the same shell.

**Aesthetic charter (editorial-brutalist):**

- Three typographic voices — italic-serif display (`'New York', ui-serif, Georgia`), uppercase mono labels (`ui-monospace, 'SF Mono', Menlo`), system sans body. Display tightened to `-0.02em`; mono tracked to `+0.12em`.
- Palette — warm-cream paper (`--aat-paper #F4EDE0`) over ink (`--aat-ink #0A0A0A`), with vermilion (`--aat-vermilion #E63946`), cobalt (`--aat-cobalt #2541B2`), and citron (`--aat-citron #F4D35E`) as the editorial accents; sage and oxblood reserved for success / danger signalling.
- Tokens flip under `@media (prefers-color-scheme: dark)` so OS appearance is honoured (cream↔ink invert; vermilion / citron hold; cobalt brightens).
- Geometry — sharp. `0px` radius on sections, `2px` on inputs, `999px` on pills only. Hairlines (`1px solid var(--aat-rule)`) replace boxed cards. No drop shadows; depth comes from typographic mass and negative space.
- Motion — slow, deliberate. Hover / focus on `cubic-bezier(0.2, 0, 0, 1)`; the hero conic gradient rotates one full turn every 120s.

**Public API:**

| Function | Returns | Purpose |
|---|---|---|
| `inject_global_styles()` | None | Emits the full stylesheet via `st.markdown(..., unsafe_allow_html=True)` and installs a capture-phase `keydown` shield on the parent document so `Cmd`/`Ctrl` chords (copy, paste, reload, …) never trigger Streamlit's bare-letter dev hotkeys. Call once per page after `st.set_page_config` (and after `database.init_db()`). |
| `accent_bar()` | None | Vermilion + cobalt + citron Bauhaus block trio, butted edge-to-edge under page titles. |
| `section_header(text, *, eyebrow=None)` | None | Uppercase mono eyebrow + tight italic-serif H2 title. |
| `numbered_section(n, title)` | None | Editorial `01 — TITLE` mark — zero-padded italic-serif numeral, vermilion separator, uppercase mono title. |
| `hero_greeting(*, name=None, now=None)` | None | Dashboard masthead — time-of-day italic-serif greeting + uppercase mono date stamp. |
| `colophon(section, *, now=None)` | None | Magazine masthead strip rendered at the top of every page. |
| `folio_footer(*, now=None)` | None | Roman-numeral folio at the bottom of every page (`Vol. XIV · № 05 / 2026 · — fin —`). |
| `page_mark(glyph)` | None | Oversized faint vermilion italic mark in the top-right gutter; one glyph per page (Dashboard `№`, Opportunities `§`, Recommenders `※`, Export `⁂`). Applications deliberately omits this mark. |
| `status_pill(raw_status)` | HTML string | Ticket-stub pill rendering `STATUS_LABELS[raw]`. Unknown values fall back to a neutral class; label content is HTML-escaped. |
| `urgency_pill(days_left, *, urgent_d, alert_d)` | HTML string | Banded pill (urgent ≤ `DEADLINE_URGENT_DAYS`, alert ≤ `DEADLINE_ALERT_DAYS`, calm beyond). Negative inputs stay urgent. |
| `sidebar_about_block(version=None)` | None | Sidebar expander exposing version + repo link. `version` defaults to `config.APP_VERSION`. |
| `sidebar_shortcuts_block()` | None | Sidebar expander listing the Streamlit keyboard affordances. |
| `demo_banner()` | None | Demo-mode banner (`DEMO_BANNER_*` copy + self-host link). No-op when `config.IS_DEMO` is False — safe to call unconditionally on every page. |
| `sidebar_demo_reset_block(on_reset)` | None | Sidebar "Reset demo data" affordance in demo mode. Takes the reset callback as an argument (pages pass `db_session.reset`) so `ui.py` keeps its no-`database`/no-`db_session` import rule. |

**Architectural constraint:** `ui.py` imports `config` + `streamlit`
only; it never touches `database`, `db_session`, or `exports` (the demo
reset callback arrives by injection, never by import). Every page calls
`ui.inject_global_styles()`, `ui.demo_banner()`,
`ui.sidebar_about_block()`, `ui.sidebar_shortcuts_block()`, and
`ui.sidebar_demo_reset_block(db_session.reset)`.

---

## 9. Cross-page Data Flows

### 9.1 Adding a new position (quick-add path)

```
User fills the quick-add form (up to 9 fields) → st.form_submit_button
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
  → db_session.bind()    (demo only: installs per-session in-memory DB; local no-op)
  → database.init_db()   (idempotent; ALTER loops run if config grew)
  → database.load_settings()               → effective thresholds into session_state
  → database.count_by_status()             → KPI math + Funnel (via FUNNEL_BUCKETS)
  → database.compute_materials_readiness() → Readiness panel
  → database.get_upcoming_deadlines()   ┐
  → database.get_upcoming_interviews()  ├→ merge by date → Upcoming panel
  → database.get_pending_recommenders() → Alerts panel (grouped by recommender)
```

### 9.3 Pipeline auto-promotion

**Cascade fully owned by `database.py`. Pages = display-only (D12).**

Two writers can promote `positions.status` as side effect — both accept kwarg `propagate_status: bool = True`; when False, no pipeline promotion fires.

**Placeholder convention.** In SQL snippets below, `<STATUS_*>` and `<RESPONSE_TYPE_OFFER>` placeholders interpolate to corresponding `config.py` alias value at query-construction time, and `<TERMINAL_STATUSES>` interpolates to tuple of all terminal status values. References elsewhere in this section use alias names directly (e.g. `STATUS_APPLIED`, `RESPONSE_TYPE_OFFER`) rather than underlying literal (e.g. `[APPLIED]`, `"Offer"`), so a rename in `config.py` does not ripple into this section.

| # | Trigger (in which writer) | Condition | Cascade |
|---|--------------------------|-----------|---------|
| R1 | `upsert_application` | `applied_date` transitions from NULL to non-NULL | `UPDATE positions SET status = '<STATUS_APPLIED>' WHERE id = ? AND status = '<STATUS_SAVED>'` |
| R2 | `add_interview` | Any successful interview insert | `UPDATE positions SET status = '<STATUS_INTERVIEW>' WHERE id = ? AND status = '<STATUS_APPLIED>'` |
| R3 | `upsert_application` | `response_type` transitions to `<RESPONSE_TYPE_OFFER>` | `UPDATE positions SET status = '<STATUS_OFFER>' WHERE id = ? AND status NOT IN (<TERMINAL_STATUSES>)` |

**R1 and R2 are idempotent** — the `AND status = '<prev>'` guard makes the cascade a no-op when the position is already at or past the target stage.

**R3 overrides non-terminal stages but guards against terminals.** A position in a terminal stage is not silently regressed — the user must first move it out of terminal status.

**R2⁻ — symmetric reverse cascade in `delete_interview`.** When the deleted row was the application's last remaining interview AND the position currently sits at `<STATUS_INTERVIEW>`, the writer runs `UPDATE positions SET status = '<STATUS_APPLIED>' WHERE id = ? AND status = '<STATUS_INTERVIEW>'` in the same transaction. The narrow status guard mirrors R2's idempotency and protects `<STATUS_OFFER>` and terminal stages from regression. Unlike the forward cascades there is no `propagate_status` opt-out and no promotion indicator — `delete_interview` returns `None` and the retraction is silent.

All cascades execute inside the same transaction as the primary write. Each promoting writer returns `{"status_changed": bool, "new_status": str | None}` so callers can surface a toast.

Callers opt out with `propagate_status=False` for edits that should not move the pipeline (e.g. correcting a typo in application notes). The Applications page always calls with the default; the Recommenders and quick-add paths never touch these functions.

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
| D6 | Quick-add = six essentials (`config.QUICK_ADD_FIELDS`) + three fixed short-string enrichment fields (`location`, `source`, `portal_url`); hard cap ≤ 9 inputs | Capture must cost < 30s; the three promoted fields are cheap at discovery time, everything else enriches later in the edit panel | Full form on add — positions lost at discovery time; strict 6-field form — three fields users reliably have at discovery forced a second visit |
| D7 | Status via `st.selectbox(STATUS_VALUES, format_func=STATUS_LABELS.get)` | Prevents typo corruption; UI label decoupled from storage | Freetext — undetectable corruption |
| D8 | `ON DELETE CASCADE` on all child tables | One delete cleans every dependent row atomically | Manual multi-table delete — easy to orphan rows |
| D9 | Separate `applications` table | Different update cadence and concern from positions | Single wide table — harder to query, harder to reason about |
| D10 | Auto-create `applications` row on `add_position()` | Every position always has matching row | Create on first update — needs NULL handling everywhere |
| D11 | Presentation/storage split via `STATUS_LABELS` + `FUNNEL_BUCKETS` | Cheap UI renames (no schema migration); presentation grouping reversible at-will | Rename storage values — needs DB migration for every naming tweak |
| D12 | Cross-table cascade lives in `database.py` writers | Atomic, testable, pages stay display-only | Page-level detect-and-prompt — leaks business logic into UI; loses atomicity |
| D13 | No 🔄 Refresh button on dashboard top bar | Streamlit reruns on any interaction; single-user local app rarely has cross-tab writes | Manual refresh button — cognitive noise for common case |
| D14 | `st.set_page_config(layout="wide", ...)` on every page | Data-heavy views need horizontal room | Default centered layout — ~750px cramps every page |
| D15 | Hardcode the `"postdoc"` profile; no `TRACKER_PROFILE` indirection | Reduce v1 surface area; profile expansion deferred to §12 | Import-time profile validation — unused extension hook |
| D16 | Bracketed status storage values + bracket-stripped UI labels | Visual enum sentinel in logs/DB; `STATUS_LABELS` delivers clean UI | Raw labels in storage — harder to grep; conflicts w/ freetext "Saved" elsewhere |
| D17 | Archived = `[REJECTED]` + `[DECLINED]` on dashboard funnel only; `[CLOSED]` stays own bar | Rejection + declined-offer = both outcomes after engagement; CLOSED = pre-engagement withdrawal — a genuinely different state | Group all three terminals — loses semantic distinction |
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

See `dev-notes extending` for step-by-step recipes (add requirement document, add or rename pipeline status, switch tracker profile, etc.).

---

## 12. Future Directions

The tracker is designed so reskinning to a different job context (software engineering, faculty, etc.) requires **editing `config.py` only** — no changes to `database.py`, `exports.py`, or page files. Planned extensions include:

- **Profile expansion** — profile-specific vocabularies and requirement docs keyed by `TRACKER_PROFILE`
- **AI-populated quick-add** — paste a job-posting URL; LLM extracts fields into `QUICK_ADD_FIELDS` schema
- **Soft delete + undo** — `archived_at` column replaces hard delete; toast with undo action
- **File attachments** — `attachments` table with local-disk storage; upload auto-flips `done_*`
- **Interactive funnel** — click a bar to navigate to Opportunities with that status pre-filtered
- **Cloud backup** — periodic upload of `postdoc.db` + `exports/` to S3 / iCloud / Dropbox

See `roadmap` for full design sketches, implementation notes, and prioritized backlog.
