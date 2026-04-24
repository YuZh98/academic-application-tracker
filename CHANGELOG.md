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

### Changed — v1.3 alignment Sub-task 7 (branch `feature/align-v1.3`)

Sub-task 7 closes the vertical slice Sub-task 3 deferred: the
three-value `work_auth` vocabulary (Sub-task 3) plus a new
`work_auth_note` freetext column plus the Overview-tab widgets that
finally surface both to the user. DESIGN.md v1.3 §6.2 + §8.2 + D22.

- **`database.py`** — `CREATE TABLE positions` gains
  `work_auth_note TEXT` right after `work_auth`. `init_db()`
  migration block gets a `PRAGMA table_info`-guarded
  `ALTER TABLE positions ADD COLUMN work_auth_note TEXT`. Plain
  TEXT, no DEFAULT — the column is NULL-able on fresh rows and on
  migrated rows (v1.2 never collected this field, so NULL is the
  honest state). Because the DEFAULT is constant (absent), the ALTER
  works against non-empty tables unlike Sub-task 6's `updated_at`
  — no backfill UPDATE is needed.
- **`pages/1_Opportunities.py`** — pre-seed block gains
  `safe_work_auth` with F2-style in-vocab coercion (NULL or
  out-of-vocab → `config.WORK_AUTH_OPTIONS[0]`, matching the
  priority / status fallback) and `edit_work_auth_note` via
  `_safe_str` (same NaN-truthiness trap as notes / link).
  Overview form gains `st.selectbox("Work Authorization",
  config.WORK_AUTH_OPTIONS, key="edit_work_auth")` plus
  `st.text_area("Work Authorization Note",
  key="edit_work_auth_note")` between Link and the submit button —
  placement per DESIGN §8.2 ("text_area below the selectbox").
  Save payload extends with both keys so `database.update_position`
  ships them to the DB.
- **`tests/test_database.py`** — three new tests:
  `test_positions_has_work_auth_note_column` (PRAGMA pin: TEXT,
  `dflt_value IS NULL`), `test_migration_adds_work_auth_note_
  to_pre_v1_3_positions` (`tmp_path` + pre-v1.3 seed mirroring the
  Sub-task 6 migration test's shape; asserts column added, existing
  `work_auth` preserved, new `work_auth_note` is NULL, second
  `init_db()` is a no-op), and `test_work_auth_note_roundtrips`
  in `TestUpdatePosition` (add_position → get → update → get
  through both columns, plus empty-string round-trip as `""`).
- **`tests/test_opportunities_page.py`** — `EDIT_KEYS` gains two
  entries (`work_auth`, `work_auth_note`). New
  `TestOverviewWorkAuthWidgets` class with 5 tests: selectbox
  renders, text_area renders, options equal
  `config.WORK_AUTH_OPTIONS` (order pinned — `Yes/No/Unknown`),
  pre-seed populates both from the selected row, NULL fallback
  (work_auth → `WORK_AUTH_OPTIONS[0]`, work_auth_note → `""`).
  `TestOverviewSave.test_save_persists_work_auth_and_note` guards
  against the classic "added to form, forgot in payload"
  regression. `TestNotesTabWidgets.test_text_area_renders_when_
  row_selected` tight-bound `len(at.text_area)` goes from 1 → 2
  — the inline comment at that test already documented bumping
  this count explicitly for exactly this case.

### Changed — v1.3 alignment Sub-task 8 (branch `feature/align-v1.3`)

Sub-task 8 normalizes the two flat interview date columns on
`applications` into a proper `interviews` sub-table so a position can
carry arbitrarily many interviews. DESIGN.md v1.3 §6.2 + §6.3 + §7 +
D18. Scope expanded beyond the originally stated `database.py` /
`tests/test_database.py` / `CHANGELOG.md` to also touch `app.py` +
`tests/test_app_page.py` — the rewritten `get_upcoming_interviews`
changes its column contract (row-per-interview with a single
`scheduled_date` column, instead of row-per-position with flat
`interview1_date` / `interview2_date` columns), which the dashboard
Next-Interview KPI consumes.

- **`database.py — init_db()`**: samples `sqlite_master` for
  `interviews` BEFORE the `CREATE TABLE IF NOT EXISTS`; runs the
  one-shot copy-then-NULL-clear migration only on the "didn't
  exist pre-create" path (the "migrate-once gate"). Adds
  `idx_interviews_application` index per §6.2.
- **`database.py`** — new CRUD section between Applications and
  Recommenders, matching DESIGN §7's grouping:
  - `add_interview(application_id, fields, *, propagate_status=True)
    → {"id", "status_changed", "new_status"}`. Auto-assigns
    `sequence` via `COALESCE(MAX(sequence), 0) + 1` when the caller
    omits it; explicit `sequence` in `fields` is used verbatim and
    the `UNIQUE(application_id, sequence)` constraint catches
    collisions. The cascade body (R2 from §9.3) is deferred to
    Sub-task 9 — `status_changed` always reads `False` today and
    the keyword-only `propagate_status` kwarg is in place purely
    for API stability across the two sub-tasks. `fields` is
    defensively copied before the auto-sequence injection so the
    caller's dict is never mutated.
  - `get_interviews(application_id) -> DataFrame` ordered by
    `sequence ASC`.
  - `update_interview(interview_id, fields) -> None` — empty-fields
    no-op to match the other update_* conventions.
  - `delete_interview(interview_id) -> None`.
- **`database.py`** — `get_upcoming_interviews()` rewritten to JOIN
  interviews → applications → positions, filter
  `scheduled_date >= today`, order `scheduled_date ASC, sequence ASC`
  (sequence is the stable tiebreaker when two interviews share a
  date). Result columns: `interview_id, application_id, sequence,
  scheduled_date, format, position_id, position_name, institute`.
  Row-per-interview shape replaces the prior row-per-position shape
  — this is the load-bearing change for D18.
- **`app.py — _next_interview_display()`**: single-column scan of
  `scheduled_date` replaces the dual-column scan over
  `interview1_date` / `interview2_date`. Functionally equivalent
  semantics (earliest future date wins, institute paired with
  winner), simpler code. Header comment + docstring updated.
- **`tests/test_database.py`** — seven new test classes covering
  the full vertical: `TestInterviewsSchema` (5), `TestAddInterview`
  (9 incl. the `inspect.signature` pin on `propagate_status`),
  `TestGetInterviews` (3), `TestUpdateInterview` (3),
  `TestDeleteInterview` (2), `TestInterviewsCascade` (1 — full
  FK-chain transitive cascade), `TestInterviewsMigration` (6 — pins
  the migrate-once gate, legacy NULL-clear, sequence-1/2 copy
  assignments, NULL-in-NULL-out, and strict idempotence across a
  second `init_db()`). `TestGetUpcomingInterviews` rewritten from
  six `upsert_application`-based seeds to seven `add_interview`-
  based seeds incl. the new `test_returns_row_per_interview`
  D18-shape pin.
- **`tests/test_app_page.py — TestT1DNextInterviewKpi`** — five
  tests rewritten to seed interviews via `add_interview`; the old
  `test_interview2_date_beats_another_rows_interview1` becomes
  `test_later_interview_on_same_position_does_not_override`
  (equivalent semantic under row-per-interview shape); class
  docstring rewritten for the new column contract.

### Changed — v1.3 alignment Sub-task 9 (branch `feature/align-v1.3`)

Sub-task 9 wires the R1/R2/R3 pipeline auto-promotion cascades across
`upsert_application` and `add_interview`, adds the
`is_all_recs_submitted` query helper, and swaps the hardcoded
`("[SAVED]", "[APPLIED]", "[INTERVIEW]")` tuple in
`compute_materials_readiness` for `config.STATUS_*` aliases (closes the
TASKS.md C1 carry-over that's been open since Sub-task 5). Pure
behavioural / refactor change — no schema edit, so no Migration entry.
DESIGN.md v1.3 §9.3 + §7 + D12 + D23.

- **`database.py — upsert_application`** signature bumps to
  `(position_id, fields, *, propagate_status: bool = True) -> dict`,
  returning `{"status_changed": bool, "new_status": str | None}`.
  Existing call sites that ignored the `None` return continue to
  work; the empty-fields early return still no-ops and hands the
  caller the indicator shape (both keys falsy) so unpacking is
  unconditional.
  - **R1**: when `pre_applied_date IS NULL AND
    fields["applied_date"] IS NOT NULL`, emit
    `UPDATE positions SET status = STATUS_APPLIED
     WHERE id = ? AND status = STATUS_SAVED`. Scoped to the
    NULL→non-NULL transition on the `applied_date` column rather
    than every touch, so a later upsert that merely updates the
    date leaves status alone.
  - **R3**: when `fields["response_type"] == "Offer"`, emit
    `UPDATE positions SET status = STATUS_OFFER
     WHERE id = ? AND status NOT IN TERMINAL_STATUSES`. Terminal
    guard in the WHERE prevents regression. The self-assignment
    that fires when the pre-state is already STATUS_OFFER reads
    as "no change" in the indicator because `status_changed`
    compares the status *string* pre/post, not whether an UPDATE
    executed.
- **`database.py — add_interview`** cascade body (Sub-task 8 left
  the body deferred for API stability) now emits R2:
  `UPDATE positions SET status = STATUS_INTERVIEW
   WHERE id = application_id AND status = STATUS_APPLIED`.
  Count-free per DESIGN §9.3 narrative — status guard alone handles
  all edges, including the back-edit-to-APPLIED-retaining-existing-
  interviews scenario that a count-based variant would miss.
- **`database.py — is_all_recs_submitted(position_id) -> bool`**
  new helper in the Applications group. Returns True iff every
  recommender for the position has a non-NULL, non-empty
  `submitted_date`. Zero-recs position returns True (vacuous truth)
  per D23's "summary that could be computed" framing — "nothing
  outstanding" holds trivially, and downstream aggregators like
  "is everything ready?" compose cleanly. Empty string is treated
  as equal to NULL (the page writes `""` when clearing a date field
  per the Notes-tab round-trip contract).
- **`database.py — compute_materials_readiness`** swaps the
  hardcoded `("[SAVED]", "[APPLIED]", "[INTERVIEW]")` tuple for
  `(config.STATUS_SAVED, config.STATUS_APPLIED, config.STATUS_INTERVIEW)`.
  Read at call time, not module load, so a future rename flows
  through immediately. Docstring updated to reference the alias
  names.
- **Atomicity** (DESIGN §9.3): every cascade runs inside the same
  `with _connect() as conn:` block as its primary write. When the
  cascade UPDATE raises (e.g. a bound parameter the SQLite driver
  cannot adapt), the context manager's except clause rolls back
  the whole transaction — neither the primary write nor any earlier
  cascade UPDATE persists.
- **`tests/test_database.py`** — 40 new tests structured by concern:
  - `TestUpsertApplicationR1` (4) — isolation: SAVED→APPLIED
    promote, applied_date-already-set noop, non-SAVED status
    guard, propagate_status=False suppression.
  - `TestUpsertApplicationR3` (9 incl. 3-value terminal
    parametrize) — SAVED/APPLIED/INTERVIEW promote to OFFER,
    already-OFFER self-assignment reads as no-change, terminal
    guard blocks CLOSED/REJECTED/DECLINED, propagate_status=False
    suppression, non-Offer response_type does nothing.
  - `TestUpsertApplicationR1R3Matrix` (7 incl. 3-value terminal
    parametrize) — every row of the DESIGN §9.3 combined-cascade
    matrix pinned (5 non-terminal pre-states + 3 terminals).
  - `TestUpsertApplicationIndicator` (3) — `inspect.signature`
    pin on the keyword-only `propagate_status=True`, return-shape
    pin, empty-fields return.
  - `TestUpsertApplicationAtomicity` (1) — monkeypatches
    `config.STATUS_APPLIED` to a non-bindable `object()`, forcing
    R1's UPDATE to raise `InterfaceError`, asserts primary write
    rolls back (applied_date stays NULL, status stays SAVED).
  - `TestAddInterviewR2` (9 incl. 3-value terminal parametrize)
    — APPLIED→INTERVIEW promotion, SAVED guard, INTERVIEW
    idempotence, OFFER guard, terminal guard, propagate_status
    opt-out, and the explicit "back-edit to APPLIED retaining
    existing interviews" scenario from the DESIGN §9.3 narrative.
  - `TestAddInterviewAtomicity` (1) — sibling of the upsert
    atomicity test for R2.
  - `TestIsAllRecsSubmitted` (5) — vacuous-truth on zero recs,
    all-submitted True, any-unsubmitted False, empty-string
    counts as unsubmitted, scoped to position_id.
  - `TestComputeMaterialsReadiness.test_active_statuses_drive_
    from_config_aliases` (1) — sentinel pattern (Sub-task 4
    precedent): monkeypatches the three aliases to strings the
    DB never holds, asserts the aggregation collapses to zero.
  Shared helper `_force_position_status(pid, status)` at module
  scope for raw-SQL pre-state staging (the user-facing writers
  would themselves fire the cascade and pollute the scenario).
- **`tests/test_database.py`** — existing
  `TestAddInterview.test_returns_indicator_dict` docstring updated
  to reflect the Sub-task 9 semantics (the assertions still hold
  because the seed's STATUS_SAVED pre-state doesn't trip R2's
  STATUS_APPLIED guard, not because the cascade body is absent).

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

**Sub-task 7** — schema addition on `positions` (new freetext
companion column for the categorical `work_auth` field).
`init_db()` runs the migration automatically on next app start; a
user upgrading from a v1.2 DB does not need to execute anything
manually. For the record, the equivalent SQL executed is:

```sql
-- Plain TEXT, no DEFAULT — existing rows correctly carry NULL
-- (v1.2 never collected this field, so NULL is the honest
-- "unknown" state). The PRAGMA table_info guard in init_db()
-- makes the ALTER idempotent.
ALTER TABLE positions ADD COLUMN work_auth_note TEXT;
```

Unlike Sub-task 6's `updated_at` migration, no backfill UPDATE
is needed here — the fresh-DB CREATE TABLE DDL and the migration
ALTER both produce the same "NULL-able TEXT, no DEFAULT" column,
so the two paths converge without any extra SQL. If a dev DB
carries legacy six-value `work_auth` strings (Sub-task 3 noted
those would need manual translation; no auto-migration runs),
the `work_auth_note` column is still added cleanly by this
step — translating the old `work_auth` enum values is an
independent manual action.

**Sub-task 8** — schema normalization (new `interviews` sub-table
replacing `applications.interview1_date` / `interview2_date`).
`init_db()` runs this automatically on the first app start after
upgrade; a user does not need to execute anything manually. For
the record, the equivalent SQL executed is:

```sql
-- (a) New sub-table (see DESIGN §6.2 for the full column spec).
CREATE TABLE IF NOT EXISTS interviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  INTEGER NOT NULL,
    sequence        INTEGER NOT NULL,
    scheduled_date  TEXT,
    format          TEXT,
    notes           TEXT,
    UNIQUE (application_id, sequence),
    FOREIGN KEY (application_id) REFERENCES applications(position_id)
        ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_interviews_application
    ON interviews(application_id);

-- (b) One-shot copy of legacy flat columns into the sub-table.
--     Only rows whose source date is non-NULL contribute.
INSERT INTO interviews (application_id, sequence, scheduled_date)
    SELECT position_id, 1, interview1_date
      FROM applications WHERE interview1_date IS NOT NULL;
INSERT INTO interviews (application_id, sequence, scheduled_date)
    SELECT position_id, 2, interview2_date
      FROM applications WHERE interview2_date IS NOT NULL;

-- (c) NULL-clear the legacy columns (DESIGN §6.3 step c).
--     Physical columns stay in CREATE TABLE applications until
--     a future rebuild drops them.
UPDATE applications
   SET interview1_date = NULL,
       interview2_date = NULL
 WHERE interview1_date IS NOT NULL
    OR interview2_date IS NOT NULL;
```

Idempotence is implemented via a **migrate-once gate** rather than
by per-statement guards: `init_db()` samples `sqlite_master` BEFORE
the `CREATE TABLE IF NOT EXISTS interviews` and only runs steps
(b) + (c) on the first call (when interviews was absent
pre-create). Subsequent calls find interviews already present and
skip the copy entirely — no INSERT OR IGNORE, no WHERE IS NULL
re-checks. A dev DB that somehow has an interviews table but
un-cleared legacy data (hand-built, partial failed migration) is
out of scope for the auto-path; recover with a one-time manual run
of steps (b) + (c). No rebuild, no data loss, no downtime on the
normal v1.2 → v1.3 upgrade.

**Sub-task 9** requires no migration — the cascade rewire + new
`is_all_recs_submitted` helper + `compute_materials_readiness`
alias swap are all pure behavioural / refactor changes. Existing
applications / interviews / recommenders rows persist untouched;
`upsert_application` and `add_interview` return a dict now instead
of `None`, but existing callers ignored the return value.

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
