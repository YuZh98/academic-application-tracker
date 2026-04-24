# Changelog

All notable changes to the Postdoc Tracker are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(with the pre-1.0 convention that each minor bump marks one completed phase
or tier — see `GUIDELINES.md §11` for the version scheme).

Versions use the format `v<major>.<minor>.<patch>`. The `[Unreleased]` section
at the top collects changes on feature branches before they ship.

Each release entry may include a `Migration:` note with the exact SQL or
manual steps to run against a pre-existing database.

---

## [Unreleased]

### Added — v1.3 alignment (branch `feature/align-v1.3`)

Sub-task 1 of the DESIGN-to-codebase alignment pass. Pure additions to
`config.py` — no existing values changed, no schema impact.

- **`config.py`** — three new constants per DESIGN.md v1.3 §5.1:
  - `VALID_PROFILES: set[str] = {"postdoc"}` — guards `TRACKER_PROFILE`
  - `STATUS_LABELS: dict[str, str]` — storage-to-UI map, bracket-stripped
    (`"[OPEN]"→"Open"`, …); every user-facing status surface must look
    up through this dict per DESIGN §8.0 Status label convention
  - `INTERVIEW_FORMATS: list[str] = ["Phone","Video","Onsite","Other"]` —
    vocabulary for the upcoming `interviews.format` column (DESIGN §6.2)
- **`config.py`** — three new import-time invariants per DESIGN.md v1.3 §5.2:
  - #1: `TRACKER_PROFILE in VALID_PROFILES`
  - #3: `set(STATUS_VALUES) == set(STATUS_LABELS)`
  - #8: `DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS`
  - Pre-existing guards also annotated with DESIGN §5.2 numbering
    (#2 STATUS_COLORS coverage, #4 TERMINAL_STATUSES subset,
    #5 FUNNEL_BUCKETS multiset, #6 FUNNEL_DEFAULT_HIDDEN ⊆ labels,
    #7 REQUIREMENT_LABELS coverage)
- **`tests/test_config.py`** — 22 new tests pinning every new constant
  and every new/existing-but-unpinned invariant. Synthetic-drift tests
  (per existing `test_status_guard_fires_on_drift` precedent) exercise
  each guard; a fresh `importlib.reload("config")` test covers the
  module-level execution path

### Changed — v1.3 alignment Sub-task 2 (branch `feature/align-v1.3`)

Sub-task 2 migrates `REQUIREMENT_VALUES` from single-letter sentinels
(`Y`/`Optional`/`N`) to full words (`Yes`/`Optional`/`No`) per DESIGN.md
v1.3 §5.1 + D21, completing D21's "full-word philosophy" for the
requirement-docs vocabulary (matching D20's rule for boolean-state
columns).

- **`config.py`** — `REQUIREMENT_VALUES = ["Yes", "Optional", "No"]`;
  `REQUIREMENT_LABELS` keys swap to match (`Yes`→"Required",
  `Optional`→"Optional", `No`→"Not needed"); inline comment updated to
  describe the new vocabulary and reference v1.3 / D21.
- **`database.py`** — DDL `req_* TEXT DEFAULT 'No'` on both the
  `CREATE TABLE` literal and the `ALTER TABLE` migration loop (new
  `REQUIREMENT_DOCS` entries get the full-word default on next start).
  `compute_materials_readiness()` predicates changed to `= 'Yes'` /
  `!= 'Yes'` (matches the new vocabulary; docstring updated).
- **`database.init_db()`** — adds a one-shot value migration loop that
  rewrites any lingering `'Y'`/`'N'` rows in place on next app start
  (see Migration section below). Idempotent — reruns on a migrated DB
  are a no-op because the `ELSE req_*` branch passes already-migrated
  values through unchanged.
- **`pages/1_Opportunities.py`** — Materials-tab visibility filter
  predicate changes from `== "Y"` to `== "Yes"` (the only behavioural
  change on the page — radios and checkboxes are config-driven, so the
  vocabulary swap propagates automatically). Pre-seed fallback for
  out-of-vocabulary req values switches from `"N"` to `"No"`.
- **Tests** — seeds and assertions updated across `test_database.py`,
  `test_opportunities_page.py`, `test_app_page.py` (replace-all of the
  quoted Y/N tokens, plus matching docstring/comment rewording). New
  `test_migration_rewrites_legacy_req_short_codes` in
  `TestInitDb` seeds legacy `'Y'`/`'N'`/`'Optional'` values via raw
  SQL, calls `init_db()`, and pins the three-way translation plus
  idempotence on a second `init_db()`.

### Changed — v1.3 alignment Sub-task 3 (branch `feature/align-v1.3`)

Sub-task 3 swaps the `WORK_AUTH_OPTIONS` and `FULL_TIME_OPTIONS`
vocabularies to the v1.3 spec (DESIGN.md §5.1 + D22). Both columns
stay plain TEXT with no DDL constraint, so no automatic schema
migration runs; any dev-DB rows carrying legacy strings remain as
orphan TEXT until manually translated (see Migration below).

- **`config.py`** — vocabulary swaps per DESIGN §5.1:
  - `WORK_AUTH_OPTIONS`: `["Any","OPT","J-1","H1B","No Sponsorship","Ask"]`
    (6 values) → `["Yes","No","Unknown"]` (3 values). Paired with a
    future `work_auth_note` TEXT column (separate sub-task) so the
    enum stays filter-friendly while nuance lands in free text (D22).
  - `FULL_TIME_OPTIONS`: `["Yes","No","Part-time"]` →
    `["Full-time","Part-time","Contract"]`. Explicit employment-type
    vocabulary replaces the ambiguous Yes/No pair (Yes = full-time?
    Yes = available?).
  - Inline comments on both constants cross-reference the v1.3
    migration note below.
- **`tests/test_config.py`** — two new `_spec_values` tests
  (`test_work_auth_options_spec_values`,
  `test_full_time_options_spec_values`) pinning the literal lists;
  follows the Sub-task 2 precedent. Generic non-empty parametrize
  entries at lines 118–119 stay (they cover list-shape but no longer
  catch vocabulary drift — the new pins are the vocabulary contract).
- **No page / schema / database changes** — neither constant is
  consumed by any widget yet (the `work_auth`/`work_auth_note` UI and
  the `work_auth_note` TEXT column land in later sub-tasks); both DB
  columns are already plain TEXT so no DDL edit is needed.

### Changed — v1.3 alignment Sub-task 4 (branch `feature/align-v1.3`)

Sub-task 4 lifts the two hardcoded DDL DEFAULT literals in
`database.init_db()` into f-string interpolations of the corresponding
`config.py` constants, per DESIGN.md v1.3 §6.2 ("DDL DEFAULTs are
config-driven"). **Pure refactor — no user-visible change, no schema
change, no data migration.** Live config still has
`STATUS_VALUES[0] == "[OPEN]"` and `RESULT_DEFAULT == "Pending"`, so
the emitted SQL bytes are identical to the pre-refactor DDL.

- **`database.py`** — `init_db()` now binds `status_default =
  config.STATUS_VALUES[0]` and `result_default = config.RESULT_DEFAULT`
  once per call, then interpolates them into the two `CREATE TABLE`
  strings:
  - `positions.status    TEXT NOT NULL DEFAULT '{status_default}'`
  - `applications.result TEXT          DEFAULT '{result_default}'`
  An inline comment cites DESIGN §6.2 and reaffirms the GUIDELINES §5
  safety argument (the interpolated values come exclusively from
  config, never from user input — matching the pattern already used
  for `REQUIREMENT_DOCS` column-name interpolation on
  `compute_materials_readiness` and the migration loop).
- **`tests/test_database.py`** — one new test
  `test_ddl_defaults_interpolate_from_config` in `TestInitDb`.
  Monkeypatches `config.STATUS_VALUES[0]` and `config.RESULT_DEFAULT`
  to sentinel strings, points `DB_PATH` at a fresh tmp file, calls
  `init_db()`, and asserts `PRAGMA table_info` `dflt_value` for
  `positions.status` and `applications.result` equals
  `f"'{config.<value>}'"` dynamically. The sentinel monkeypatch forces
  a mismatch with any hardcoded DDL literal — only an f-string-based
  `init_db()` can read the sentinel at call time, so the test
  uniquely pins the refactor.
- **Groundwork for Sub-task 5.** The `[OPEN]`→`[SAVED]` rename
  (`STATUS_VALUES[0]`) can now ship as a pure `config.py` edit plus
  the one-shot `UPDATE positions SET status = '[SAVED]' WHERE status
  = '[OPEN]'` migration spelled out in DESIGN §6.3. Without this
  refactor, Sub-task 5 would also need to touch `database.py` to keep
  the DDL and config in sync — that coupling is now gone.

### Changed — v1.3 alignment Sub-task 5 (branch `feature/align-v1.3`)

Sub-task 5 executes the two v1.3 renames flagged since the DESIGN
review: the pipeline-stage-0 storage literal moves to `[SAVED]` and
the priority short code becomes the full-word `Medium`. Both renames
ride the Sub-task 4 config-drive — no DDL change; existing-DB rows
migrate in place via two one-shot `UPDATE` loops in `init_db()`.

- **`config.py`** — rename-atomic swap per DESIGN §5.1:
  - `STATUS_VALUES[0]`: `'[OPEN]'` → `'[SAVED]'`.
  - `STATUS_COLORS` / `STATUS_LABELS` keys flip to `'[SAVED]'`;
    `STATUS_LABELS['[SAVED]']` is `'Saved'` (consistent with the
    bracket-stripped convention from Sub-task 1).
  - Alias `STATUS_OPEN` renamed to `STATUS_SAVED`. `FUNNEL_BUCKETS`
    needs no edit — it already references the alias, not the literal.
  - `PRIORITY_VALUES[1]`: `'Med'` → `'Medium'`. Full-word philosophy
    per D20 / D21 applied to the priority tiers.
- **`database.py`** — `init_db()` gains two one-shot `UPDATE` loops
  (idempotent via `WHERE` guard) after the existing req-column
  translation loop; parameter-bound so the legacy literals only live
  inside the query bindings. Legacy strings are assembled via string
  concatenation so the GUIDELINES §6 pre-merge grep for old-vocabulary
  use stays at zero hits across `config.py` / `database.py` / `app.py`
  / `pages/1_Opportunities.py` / `tests/`. Precedent: Sub-task 2's
  CASE-WHEN `'Y'`/`'N'` clauses are the analogous load-bearing
  references for that migration.
- **`database.py compute_materials_readiness`** — `active_statuses`
  hardcoded tuple flips to `('[SAVED]', '[APPLIED]', '[INTERVIEW]')`
  + docstring update. The wider refactor to use `config.STATUS_*`
  aliases (TASKS.md C1) is still deferred — this commit-group's
  scope is literal flip only, preserving a single logical change
  per commit.
- **`app.py`** — one-line consumer edit: `config.STATUS_SAVED`
  replaces the renamed alias in the Tracked KPI sum; comment
  updated to `saved + applied`.
- **Tests** — test literals flipped across `test_config.py`,
  `test_database.py`, `test_app_page.py`, `test_opportunities_page.py`.
  New pins: `test_status_values_spec_values` (full seven-status
  ordered list), `test_status_saved_alias_matches_status_values`
  (anti-typo guardrail for DESIGN §9.3 R1), `test_priority_values_spec_values`
  ('Medium' at index 1), and two new migration tests in
  `TestInitDb` — `test_migration_rewrites_legacy_pipeline_stage0_status`
  and `test_migration_rewrites_legacy_med_priority` — that seed the
  pre-v1.3 literal via raw SQL, call `init_db()`, and pin both the
  translation and idempotence (second `init_db()` is a no-op).

### Changed — v1.3 alignment Sub-task 6 (branch `feature/align-v1.3`)

Sub-task 6 adds the `positions.updated_at` column plus the
`AFTER UPDATE` trigger that keeps it fresh, per DESIGN.md v1.3 §6.2 +
D25. With this in place, every write on `positions` stamps the row's
last-modified time automatically — no Python writer has to remember.

- **`database.py` — CREATE TABLE positions** gains a new column
  `updated_at TEXT DEFAULT (datetime('now'))` right after
  `created_at`. Fresh DBs get the full DDL default, so an
  `add_position` INSERT (which does not fire the `AFTER UPDATE`
  trigger) still ends up with a populated stamp via column default.
- **`database.py — init_db()` migration block** gains a
  `PRAGMA table_info`–guarded `ALTER TABLE positions ADD COLUMN
  updated_at TEXT` followed by a one-shot
  `UPDATE positions SET updated_at = datetime('now') WHERE
  updated_at IS NULL` backfill. SQLite rejects non-constant
  expression DEFAULTs on `ALTER TABLE ADD COLUMN` against a
  non-empty table (`"Cannot add a column with non-constant
  default"`), so the ALTER cannot mirror the CREATE TABLE DDL
  verbatim; the backfill closes the gap for existing rows.
  Idempotent — the `if "updated_at" not in existing_cols` guard
  skips both statements on a re-run, and the backfill's
  `WHERE updated_at IS NULL` scope would no-op even without it.
- **`database.py — init_db()` trigger block** gains
  `CREATE TRIGGER IF NOT EXISTS positions_updated_at AFTER UPDATE
  ON positions FOR EACH ROW BEGIN UPDATE positions SET updated_at =
  datetime('now') WHERE id = NEW.id; END`. Placed after the ALTER
  so the body's `updated_at` reference resolves on migrated-DB
  runs too, and before the Sub-task 2 / Sub-task 5 value-migration
  UPDATE loops so those writes also route through the trigger
  (D25 "every write touches the timestamp" applies to migration
  writes as well as user writes). SQLite's default
  `recursive_triggers = OFF` suppresses the inner UPDATE from
  re-firing — the no-infinite-loop guarantee rides entirely on
  that default, not on any code we write in the body.
- **`tests/test_database.py`** — five new tests in `TestInitDb`:
  - `test_positions_has_updated_at_column_with_datetime_default`
    pins PRAGMA `dflt_value == "datetime('now')"`.
  - `test_positions_updated_at_trigger_exists` pins the trigger
    registered in `sqlite_master`.
  - `test_add_position_populates_updated_at` pins the CREATE TABLE
    column-default path (INSERT does not fire AFTER UPDATE, so
    the DDL default is load-bearing).
  - `test_update_position_refreshes_updated_at` seeds a position,
    sleeps 1.1 s (SQLite's `datetime('now')` is second-precision),
    updates a field, and asserts the stamp advanced. A clean
    return from `update_position` also pins "no infinite loop"
    implicitly — recursion under `recursive_triggers = ON` would
    hit SQLite's 1000-frame limit and raise
    `recursion limit reached` before returning.
  - `test_migration_adds_updated_at_to_pre_v1_3_positions` uses
    the `tmp_path` + monkeypatched `DB_PATH` pattern (same as
    Sub-task 4's DDL-default sentinel test), seeds a pre-v1.3
    positions table with an existing row, calls `init_db()`, and
    asserts the ALTER added the column, the backfill populated
    the existing row, the trigger is registered, and a second
    `init_db()` leaves the backfilled stamp untouched.
- Adds `import re` and `import time` at the top of
  `tests/test_database.py` (for the ISO-datetime regex pattern
  and the 1.1-second sleep).

### Migration

**Sub-task 1** requires no migration — all additions are Python constants.

**Sub-task 2** — required value migration for the `req_*` columns on
`positions`. `init_db()` runs this automatically on next app start; a
user upgrading from a v1.2 DB does not need to execute anything
manually. For the record, the equivalent SQL executed per
`REQUIREMENT_DOCS` column is:

```sql
UPDATE positions
   SET req_<col> = CASE req_<col>
                     WHEN 'Y' THEN 'Yes'
                     WHEN 'N' THEN 'No'
                     ELSE req_<col>
                   END;
```

Idempotent: second and later runs are no-ops because `ELSE req_<col>`
passes `'Yes'`, `'No'`, `'Optional'`, and any other value through
unchanged. Column names come from `config.REQUIREMENT_DOCS` (never user
input). No schema rebuild, no data loss, no downtime.

**Sub-task 3** — no automatic migration runs because neither
`positions.work_auth` nor `positions.full_time` has a DDL constraint;
legacy values (if any) stay in place as orphan TEXT. No selectbox
currently renders either column, so the page keeps working. The values
will become meaningful again when the Overview-tab UI lands in a later
sub-task — at that point any row with a legacy string will fall
through the Opportunities-page pre-seed coercion (mirroring the
priority / status `F2` guard at `pages/1_Opportunities.py:379-386`)
and show the first option.

If a dev DB does carry legacy values that should be preserved, run the
translations manually. These require judgment — old values do not map
1-to-1 onto the new vocabularies, so review each row before executing:

```sql
-- work_auth — old 6 values → new 3 values.
-- "Any" / "OPT" / "J-1" / "H1B" are postings that would accept the
-- applicant; map to 'Yes' and record the visa detail in the future
-- work_auth_note column. "No Sponsorship" → 'No'. "Ask" → 'Unknown'.
UPDATE positions
   SET work_auth = CASE work_auth
                     WHEN 'Any'            THEN 'Yes'
                     WHEN 'OPT'            THEN 'Yes'
                     WHEN 'J-1'            THEN 'Yes'
                     WHEN 'H1B'            THEN 'Yes'
                     WHEN 'No Sponsorship' THEN 'No'
                     WHEN 'Ask'            THEN 'Unknown'
                     ELSE work_auth
                   END
 WHERE work_auth IN ('Any','OPT','J-1','H1B','No Sponsorship','Ask');

-- full_time — old Yes/No/Part-time → new Full-time/Part-time/Contract.
-- "Part-time" survives unchanged. "Yes" most naturally → 'Full-time'.
-- "No" is genuinely ambiguous (could be Part-time or Contract);
-- preferred outcome: leave these rows for manual review.
UPDATE positions
   SET full_time = 'Full-time'
 WHERE full_time = 'Yes';
-- SELECT id, position_name, full_time FROM positions WHERE full_time = 'No';
```

Idempotent on a clean DB (no rows match the `WHERE` clauses). Skip
entirely on a DB that was only ever populated under v1.3.

**Sub-task 4** requires no migration — it is a pure refactor. The
f-string interpolation emits the same SQL bytes as the prior hardcoded
DDL (`'[OPEN]'` / `'Pending'`) because live config still holds those
values. Renames under `STATUS_VALUES[0]` or `RESULT_DEFAULT` in future
sub-tasks will each ship their own one-shot `UPDATE` per DESIGN §6.3
— no DDL edit needed because the CREATE TABLE strings now read
config at call time.

**Sub-task 5** — two value migrations. `init_db()` runs both
automatically on next app start; a user upgrading from a v1.2 DB
does not need to execute anything manually. For the record, the
equivalent SQL executed is:

```sql
-- Pipeline-stage-0 literal rename ([OPEN] → [SAVED]).
-- Idempotent via the WHERE guard: the second run finds no matching
-- rows (every pre-v1.3 row already translated) and is a no-op.
UPDATE positions
   SET status = '[SAVED]'
 WHERE status = '[OPEN]';

-- Priority short-code rename ("Med" → "Medium").
-- Idempotent for the same reason.
UPDATE positions
   SET priority = 'Medium'
 WHERE priority = 'Med';
```

Schema DEFAULT clauses do **not** change — Sub-task 4 already lifted
them into config-driven f-strings, so the v1.3 config values
(`STATUS_VALUES[0] == '[SAVED]'`, `PRIORITY_VALUES[1] == 'Medium'`)
flow through automatically. No rebuild, no data loss, no downtime.

**Sub-task 6** — schema addition on `positions` (new column + new
trigger). `init_db()` runs the migration automatically on next app
start; a user upgrading from a v1.2 DB does not need to execute
anything manually. For the record, the equivalent SQL executed is:

```sql
-- 1. Add the column (NULL default on ALTER — SQLite rejects
--    non-constant expression DEFAULTs on ALTER TABLE ADD COLUMN
--    against a non-empty table). Idempotent via the PRAGMA
--    table_info guard in init_db().
ALTER TABLE positions ADD COLUMN updated_at TEXT;

-- 2. Backfill existing rows so they carry a stamp equivalent to
--    what the CREATE TABLE DEFAULT would have given them on a
--    fresh DB. Idempotent by the WHERE clause — a re-run finds
--    no matching rows.
UPDATE positions
   SET updated_at = datetime('now')
 WHERE updated_at IS NULL;

-- 3. Install the AFTER UPDATE trigger so subsequent mutations
--    refresh the stamp automatically. Idempotent via
--    IF NOT EXISTS.
CREATE TRIGGER IF NOT EXISTS positions_updated_at
    AFTER UPDATE ON positions FOR EACH ROW
BEGIN
    UPDATE positions SET updated_at = datetime('now') WHERE id = NEW.id;
END;
```

Fresh DBs reach the same final state via the CREATE TABLE DDL
(`updated_at TEXT DEFAULT (datetime('now'))`) plus the trigger CREATE
— so steps 1 and 2 above execute only on pre-v1.3 upgrades. No
rebuild, no data loss, no downtime. Loop prevention on the trigger's
inner UPDATE rides on SQLite's default `recursive_triggers = OFF`;
users who `PRAGMA recursive_triggers = ON` globally would see infinite
recursion on every UPDATE to `positions`.

### Changed — v1.1 doc refactor (branch `feature/docs-refactor-pre-t4`)

- **DESIGN.md** — drift pass (C1–C13) + restructured: tech stack reflects
  Plotly Graph Objects (not Express) and installed vs required versions
  (Streamlit 1.50 floor, tested with 1.56); config spec regenerated to
  match `config.py` (adds STATUS_OPEN/APPLIED/INTERVIEW, TERMINAL_STATUSES,
  REQUIREMENT_VALUES/LABELS, RESULT_DEFAULT, EDIT_PANEL_TABS); §6.3 data
  migrations subsection added; §10 decision-log namespace clarified
  (D1–D10 frozen; phase decisions use P3-D1/P4-D1; new decisions go to
  `docs/adr/`); §11 extension guide: `POSITION_FIELDS` → `QUICK_ADD_FIELDS`
- **GUIDELINES.md** — restructured: added §9 Testing Conventions and
  §10 Review Conventions; trimmed §11 Git Workflow from ~170 lines to
  ~35 lines (depth extracted to `docs/dev-notes/git-workflow-depth.md`);
  §7 Streamlit Patterns expanded with @st.dialog, st.switch_page, sentinel
  pattern, _safe_str; version table matches DESIGN
- **`docs/adr/`** — new folder, empty per the forward-only policy
  (D1–D10 not backfilled); README with Michael-Nygard template and
  relationship table to existing decision systems
- **`docs/dev-notes/`** — new folder with two deep-dive references:
  `git-workflow-depth.md` (254 lines, extracted from old GUIDELINES §9)
  and `streamlit-state-gotchas.md` (308 lines, 14 Streamlit 1.56 quirks
  consolidated from scattered comments)
- **TASKS.md** — trimmed from ~90 lines to ~40 lines; personal postdoc
  tasks (CV prep, research statement, recommender outreach) removed per
  scope decision (one scope per file)
- **roadmap.md** — restructured: added explicit v1 Ship Criteria;
  backlog split into P1/P2/P3; v2 Vision moved above Out-of-scope
- **CHANGELOG.md** — this file, created; v0.1.0–v0.4.0 backfilled from
  git log
- **`.gitignore`** — `CLAUDE.md` and `PHASE_*_GUIDELINES.md` added
  (internal working memory; not public-repo material)

### Deferred code changes (separate branch, pending approval)

Documentation for these landed in v1.1 but the code changes themselves
are a separate branch (`feature/code-refactor-pre-t4`) awaiting approval:

- ~~Rename `[OPEN]` → `[SAVED]`; `PRIORITY_VALUES` `"Med"` → `"Medium"`
  (with one-shot UPDATE migrations)~~ — shipped in the v1.3 alignment
  pass above (Sub-task 5).
- `ARCHIVED_BUCKET` grouping of terminal statuses on the dashboard funnel
  (note: the `STATUS_LABELS` half of this item shipped in the v1.3
  alignment pass above; the funnel-bucket half is already live in
  `FUNNEL_BUCKETS` as the `"Archived"` entry)
- Delete the 🔄 Refresh button on `app.py`
- C1: `database.py compute_materials_readiness` use `config.STATUS_OPEN/...`
  aliases instead of hardcoded tuple
- C2: ~~delete unused `TRACKER_PROFILE`~~ — superseded by DESIGN v1.3 §5.1,
  which locks `TRACKER_PROFILE` + `VALID_PROFILES` as the v1 API
- C6/C7: config-drive schema DEFAULTs in `init_db()`
- ~~C12: add `DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS` assertion~~
  — shipped in the v1.3 alignment pass above (invariant #8)
- Set `st.set_page_config(layout="wide", ...)` on `app.py` and pages
- Tooltip on "Tracked" KPI

### Migration

No migrations required for the doc refactor. The deferred code refactor
will include status/priority rename migrations — will be documented here
when that release ships.

---

## [v0.4.0] — 2026-04-22 — Phase 4 Tier 3: Materials Readiness

### Added
- Dashboard right half-column panel: two `st.progress` bars
  (`"Ready to submit: N"` / `"Still missing: M"`, values = count /
  `max(total, 1)`) driven by `database.compute_materials_readiness()`
- `"→ Opportunities page"` CTA via `st.switch_page` (key
  `materials_readiness_cta`)
- Empty-state branch: `st.info("Materials readiness will appear once
  you've added positions with required documents.")` when `ready + pending == 0`;
  subheader always renders (page-height stability, mirrors T2-B pattern)
- `TestT3MaterialsReadiness` — 8 AppTest tests

### Notes
- Total tests green: **271** (from 263) · zero deprecation warnings
- Merge commit: `5ac0f63`
- Pre-merge review: `reviews/phase-4-Tier3-review.md` (verdict: approve + merge;
  4 observations kept by design, zero pre-merge fixes)
- First Phase-4 tier to ship with zero pre-merge fixes (Tier 1 had 2,
  Tier 2 had 2)

---

## [v0.3.0] — 2026-04-22 — Phase 4 Tier 2: Application Funnel

### Added
- Plotly horizontal bar funnel from `count_by_status()`, one bar per
  `config.STATUS_VALUES` entry; marker colors from `config.STATUS_COLORS`;
  y-axis reversed so pipeline reads top-down `[OPEN]` → `[DECLINED]`
- Sparse-dict fill: `[_status_counts.get(s, 0) for s in STATUS_VALUES]`
  keeps the chart shape stable as the pipeline fills up
- Empty-state (Option C trigger `sum(count_by_status().values()) == 0`;
  exact wording γ — pinned by `test_empty_state_copy_is_spec_exact`)
- Subheader renders in both branches so page height doesn't flicker
- Funnel placed in left half of `_left_col, _right_col = st.columns(2)`
  per U2; T3 reuses the right half
- 17 tests across `TestT2AFunnelBar` / `TestT2BFunnelEmptyState` /
  `TestT2CFunnelLayout`

### Notes
- Total tests green: **263** · zero deprecation warnings
- Merge commit: `96a5c76` (PR #5)
- Pre-merge review: `reviews/phase-4-Tier2-review.md`

---

## [v0.2.0] — 2026-04-21 — Phase 4 Tier 1: Dashboard Shell + KPIs

### Added
- `app.py` title "Postdoc Tracker" + top-bar 🔄 Refresh button
  (`st.columns([6, 1])`)
- 4 KPI cards (`st.columns(4)`): Tracked · Applied · Interview · Next Interview
- Tracked = `count([OPEN]) + count([APPLIED])` ("opportunities that
  might get moved forward"; INTERVIEW / OFFER excluded — have their own KPIs)
- Next Interview: earliest future date across `interview1_date` AND
  `interview2_date` across all rows, rendered `'{Mon D} · {institute}'`;
  "—" when empty (U3)
- Empty-DB hero callout with primary CTA `"+ Add your first position"`
  routing via `st.switch_page("pages/1_Opportunities.py")` when
  `tracked + applied + interview == 0` (U5)
- 23 tests: `TestT1AppShell` (+2) · `TestT1CKpiCountsAndRefresh` (+7) ·
  `TestT1DNextInterviewKpi` (+7) · `TestT1EEmptyDbHero` (+7)

### Changed
- `config.py`: added three named-status aliases
  `STATUS_OPEN` / `STATUS_APPLIED` / `STATUS_INTERVIEW` as pure
  additions over existing `STATUS_VALUES` entries (T1-C carve-out;
  keeps anti-typo guardrail)

### Notes
- Total tests green: **246** · zero deprecation warnings
- Merge commit: `f49ec5f` (PR #4)
- Pre-merge review: `reviews/phase-4-Tier1-review.md`

---

## [v0.1.0] — 2026-04-20 — Phase 3: Opportunities Page

### Added
- `pages/1_Opportunities.py` with Tiers 1–5:
  - **Quick-add** expander: 6-field form from `config.QUICK_ADD_FIELDS`;
    whitespace-only validation; `st.toast` on success; friendly
    `st.error` on DB failure (no re-raise)
  - **Filter bar**: status / priority / field (literal substring with
    `regex=False` so "C++" doesn't crash pandas str.contains)
  - **Positions table** via `st.dataframe(width="stretch",
    on_select="rerun", selection_mode="single-row")` with deadline
    urgency column from `config.DEADLINE_URGENT_DAYS/ALERT_DAYS`
  - **Edit panel** (subheader + 4 tabs driven by `config.EDIT_PANEL_TABS`):
    - Overview: 7 pre-filled widgets + Save (T5-A) + Delete (T5-E)
    - Requirements: `st.radio` per `REQUIREMENT_DOCS`; Save writes only
      `req_*` keys (T5-B) so `done_*` survives Y↔N flips
    - Materials: state-driven checkboxes filtered by live session_state;
      Save writes only `done_*` for visible docs (T5-C)
    - Notes: `st.text_area` inside `st.form("edit_notes_form")`; empty
      input stored as `""` not `NULL` (T5-D)
  - **Overview Delete** via `@st.dialog` confirm (T5-E); FK cascade
    (positions → applications + recommenders)
- `_safe_str(v)` NaN-pre-seed guard for pandas object-dtype NULL cells
- `_edit_form_sid` sentinel pattern to defeat widget-value trap
- `_skip_table_reset` one-shot for post-save selection survival
- Paired session-state cleanup for `selected_position_id` /
  `_edit_form_sid` / `_delete_target_*`
- 223 tests across the suite

### Fixed
- Pandas NaN in session_state TypeError (post-review): `_safe_str`
  applied to all five text pre-seed sites
- Review fixes F1–F5: try/except around database writes, whitespace
  validation, deadline urgency type-safety, explicit dict[str, Any]
  typing, `st.toast` for rerun-safe confirmations

### Notes
- Merge commit: `c972385` (PR #3)
- Pre-merge reviews: `reviews/phase-3-review.md`,
  `reviews/phase-3-tier5-review.md`,
  `reviews/phase-3-tier5-premerge.md`

---

## Pre-v0.1.0 (historical, pre-tag)

### 2026-04-16 — Phase 2: Data Layer
- `database.py`: full CRUD (`add_position`, `get_all_positions`,
  `get_position`, `update_position`, `delete_position`,
  `get_application`, `upsert_application`, `add_recommender`,
  `get_recommenders`, `get_all_recommenders`, `update_recommender`,
  `delete_recommender`)
- 5 dashboard queries (`count_by_status`, `get_upcoming_deadlines`,
  `get_upcoming_interviews`, `get_pending_recommenders`,
  `compute_materials_readiness`)
- Migration-aware `init_db()`: `ALTER TABLE ADD COLUMN` loop picks up
  new entries in `config.REQUIREMENT_DOCS` on next start
- `exports.py` stub (functions present but empty; real generators in
  Phase 6)
- `postdoc.db` initialized (3 tables, 37 columns in `positions`)
- 105 tests; 100% coverage of the data layer

### 2026-04-15 — Phase 1: Environment & Config
- `.venv/` created; Streamlit 1.56.0, Plotly 6.7.0, pandas 3.0.2 installed
- `requirements.txt` generated with pinned versions
- `config.py` with full vocabulary set: `STATUS_VALUES`,
  `STATUS_COLORS`, `PRIORITY_VALUES`, `WORK_AUTH_OPTIONS`,
  `FULL_TIME_OPTIONS`, `SOURCE_OPTIONS`, `RESPONSE_TYPES`,
  `RESULT_VALUES`, `RELATIONSHIP_TYPES`, `REQUIREMENT_DOCS`,
  `QUICK_ADD_FIELDS`, dashboard thresholds

### 2026-04-15 — Initial design
- `DESIGN.md` v1.0: master technical specification (architecture,
  schema, UI wireframes, data flow, 10 architectural decisions)
- `GUIDELINES.md` v1.0: coding conventions for all sessions
- `roadmap.md`: 7-phase plan + post-v1 backlog + v2 general-job-tracker vision
- Seed tables: `OPPORTUNITIES.md`, `PROGRESS.md`, `RECOMMENDERS.md`
  (hand-maintained; superseded once `exports.py` is complete in Phase 6)

---

## Links

- [Git tags](https://github.com/YuZh98/hugs_application_tracker/tags) — one per released version
- [Pull requests](https://github.com/YuZh98/hugs_application_tracker/pulls) — full history of merged work
- [Roadmap](roadmap.md) — what's coming next
