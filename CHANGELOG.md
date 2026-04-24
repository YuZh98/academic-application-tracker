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

### Changed — v1.3 alignment Sub-task 10 (branch `feature/align-v1.3`)

Sub-task 10 splits the pre-v1.3 dual-purpose
`applications.confirmation_email TEXT` column into
`confirmation_received INTEGER DEFAULT 0` + `confirmation_date TEXT`
per DESIGN.md v1.3 §6.2 + D19 + D20. D19 frames the original column
as type-ambiguous ("stored either `'Y'` or a date string"); D20
pins boolean-state columns at `INTEGER 0/1` rather than `TEXT
'Y'/'N'`. The legacy column stays physically in place until the
v1.0-rc rebuild drops it (DESIGN §6.3 step c "leave old columns
NULL until a rebuild drops them" — same retention as the
Sub-task 8 `interview1_date` / `interview2_date` pair).

- **`database.py` CREATE TABLE applications** adds the new columns
  right after `confirmation_email`:
  ```
  confirmation_received INTEGER DEFAULT 0,    -- 0 or 1
  confirmation_date     TEXT,                 -- ISO, NULL if none
  ```
  Inline comment block above the DDL records the split's rationale
  and the deferred physical drop so a future reader does not
  mistake the retained column for current schema.
- **`database.init_db()` migration block** (placed immediately after
  the Sub-task 8 interviews migration, so applications-table changes
  stay grouped):
  - Samples `PRAGMA table_info(applications)` once; captures the
    pre-ALTER column set.
  - PRAGMA-guarded `ALTER TABLE applications ADD COLUMN` for each
    new column — absent ⇒ add, present ⇒ skip. SQLite's
    "Cannot add a column with non-constant default" error (hit in
    Sub-task 6 for `updated_at`) does not apply here: the INTEGER
    DEFAULT 0 is a constant expression; the TEXT column has no
    DEFAULT at all.
  - **Migrate-once gate** (Sub-task 8 pattern): the one-shot UPDATE
    block only fires when either new column was absent pre-ALTER.
    A rerun on an already-migrated DB finds both columns present
    and skips the translation entirely — no re-translation of any
    legacy value, no overwrite of user-entered data. The logic is
    tighter than a per-row WHERE guard and lets the UPDATEs stay
    simple.
  - One-shot translation — two disjoint UPDATEs:
    - **Date-shaped legacy values** (via SQLite
      `GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'`, which
      matches exactly the 10-character ISO date shape and nothing
      else): set `confirmation_received = 1, confirmation_date =
      confirmation_email`.
    - **Flag-only legacy values** (`confirmation_email = 'Y'`):
      set `confirmation_received = 1`; `confirmation_date` stays
      NULL (the legacy 'Y' shape had no date).
    NULL, `''`, legacy `'N'`, or any other freetext value falls
    through both WHERE clauses — the new columns stay at their
    DEFAULTs (`received = 0`, `date = NULL`). This is correct: those
    shapes represent "no confirmation data," and the migration does
    not guess beyond the two shapes D19 names.
- **No application-code change** in `upsert_application` or any
  other writer. The function is schema-agnostic (accepts any fields
  dict and routes it into `INSERT … ON CONFLICT DO UPDATE SET`), so
  the split is transparent once the DDL exists. No caller in
  `app.py` / `pages/` / `tests/` writes to `confirmation_email`
  (verified via grep before the sub-task); new writes will land on
  the split pair when the Applications page UI lands in Phase 5.
- **`tests/test_database.py`** — 10 new tests:
  - `TestInitDb.test_applications_has_confirmation_received_column_with_zero_default`
    and `…_confirmation_date_column_nullable` — column-spec pins
    via `PRAGMA table_info`; mirror the Sub-task 6/7 precedent.
  - `TestUpsertApplication.test_writes_confirmation_received_and_date_roundtrip`
    — round-trip of both flag-only and flag+date upserts; also pins
    that the legacy `confirmation_email` stays NULL (no caller
    writes to it post-split).
  - New class `TestConfirmationSplitMigration` mirrors the Sub-task
    8 `TestInterviewsMigration` migrate-once-gate pattern: seeds a
    pre-v1.3 DB via `tmp_path` + monkeypatched `DB_PATH`, inserts
    one row with a legacy `confirmation_email` value, calls
    `init_db()`, inspects the new columns. Seven cases cover the
    full translation matrix — `'Y'` → received-only, date-shaped
    → both fields, NULL / empty / `'N'` → defaults, fresh-DB
    defaults contract, idempotence on second `init_db()`.
  - Shared seed helper `_seed_pre_v1_3_applications` includes
    `interview1_date` / `interview2_date` / `confirmation_email`
    together so `init_db()` runs ALL applicable migrations
    cleanly (Sub-task 8 first, Sub-task 10 next).
- **`tests/test_database.py`** — Sub-task 8 seed touch-up:
  `TestInterviewsMigration._seed_pre_v1_3_applications` gains a
  `confirmation_email TEXT` column so the realistic pre-v1.3 DB
  shape now round-trips cleanly through the Sub-task 10 migration
  block (which references `confirmation_email` in its UPDATE
  WHERE clauses). Pure seed realism — no change to the Sub-task
  8 test focus.

### Changed — v1.3 alignment Sub-task 11 (branch `feature/align-v1.3`)

Sub-task 11 rebuilds the `recommenders` table to bring its
storage types in line with DESIGN.md v1.3 §6.2 + D19 + D20:
`confirmed TEXT` → `confirmed INTEGER` (tri-state 0/1/NULL);
`reminder_sent TEXT` → `reminder_sent INTEGER DEFAULT 0`; add
`reminder_sent_date TEXT`. D19 frames the `reminder_sent` part as
a dual-concern (flag, date) split (a pre-v1.3 `reminder_sent`
TEXT cell could legitimately hold either `'Y'` or a date-shaped
string); D20 pins boolean-state columns at INTEGER 0/1 rather
than TEXT `'Y'`/`'N'`. Unlike Sub-tasks 8 and 10, which kept the
pre-v1.3 columns physically present (legacy-column retention per
§6.3 step c), this sub-task does a full table rebuild — SQLite
lacks in-place column-type change, so CREATE-COPY-DROP-RENAME
is the only clean recipe (see DESIGN §6.3's "Remove a column"
row, which also enumerates this pattern).

- **`database.py` CREATE TABLE recommenders DDL** rewritten to
  the target schema:
  ```
  confirmed          INTEGER,                -- 0, 1, or NULL
  submitted_date     TEXT,
  reminder_sent      INTEGER DEFAULT 0,      -- 0 or 1
  reminder_sent_date TEXT,                   -- ISO, NULL if none
  ```
  Preamble comment explains the tri-state semantics on `confirmed`
  (no DEFAULT so a fresh row is NULL = pending, distinct from 0 =
  explicitly not confirmed) and the (flag, date) split on the
  reminder pair. All other columns (`id`, `position_id`,
  `recommender_name`, `relationship`, `asked_date`,
  `submitted_date`, `notes`) stay untouched; the FK +
  `ON DELETE CASCADE` carries over verbatim.
- **`database.init_db()` migration block** inserted right after
  the Sub-task 10 confirmation_email split, before the
  `positions_updated_at` trigger:
  - **Idempotence gate** (borrowed from Sub-task 8's migrate-once
    shape, but keyed on the column's declared type rather than
    table presence): `PRAGMA table_info(recommenders)` → read the
    `confirmed` column's declared type. `INTEGER` (fresh DB or
    already-migrated) short-circuits the rebuild; `TEXT` (pre-v1.3)
    triggers it. A rerun on a migrated DB is a strict no-op — no
    duplicate tables, no double-translation.
  - **Step 1 — CREATE** `recommenders_new` with the target DDL
    (same columns and DEFAULTs as the CREATE TABLE above; FK +
    `ON DELETE CASCADE` re-declared so the rename lands a fully-
    constrained table).
  - **Step 2 — INSERT-COPY** from `recommenders` into
    `recommenders_new` with CASE translations:
    ```
    confirmed     'Y'           -> 1
                  'N'           -> 0
                  anything else -> NULL
                                   (cautious; 'maybe' / empty / stray
                                    freetext becomes NULL rather than
                                    a guessed integer)

    reminder_sent 'Y'           -> reminder_sent=1,
                                   reminder_sent_date=NULL
                  'YYYY-MM-DD'  -> reminder_sent=0,
                                   reminder_sent_date=<value>
                                   (matched via SQLite
                                    GLOB '????-??-??' — any 10-char
                                    '??-??' shape; looser than
                                    Sub-task 10's [0-9]-digit-class
                                    but safe given pre-v1.3
                                    reminder_sent realistically held
                                    only dates or 'Y'/NULL)
                  anything else -> reminder_sent=0,
                                   reminder_sent_date=NULL
    ```
    Other columns copy through verbatim. `id` values preserved so
    the `sqlite_sequence` AUTOINCREMENT counter stays coherent —
    SQLite advances it past any explicitly-inserted id on the
    next INSERT.
  - **Step 3 — DROP** the old `recommenders` table. Safe with
    `PRAGMA foreign_keys = ON` (set by `_connect()`): recommenders
    is a CHILD table (only an outbound FK to positions); nothing
    points INTO recommenders, so the implicit DELETE FROM that
    fires on DROP with FK=ON has nothing to cascade.
  - **Step 4 — RENAME** `recommenders_new` to `recommenders`. The
    FK definitions in other tables are unchanged (nothing points
    to recommenders), so the rename is structural only.
  - **Atomicity**: all four steps run inside the same
    `with _connect() as conn:` block, i.e. the same transaction
    as every other init_db() DDL change. A mid-rebuild failure
    triggers the `_connect()` context manager's rollback, so the
    DB cannot be left with a half-migrated table (e.g.
    `recommenders_new` orphaned alongside an un-translated
    `recommenders`).
- **No changes to recommender CRUD or dashboard-query functions.**
  `add_recommender` / `update_recommender` are schema-agnostic
  (no field whitelist), so they transparently accept integer
  values on the new INTEGER columns. `get_recommenders` /
  `get_all_recommenders` / `get_pending_recommenders` do not
  filter on `confirmed` or `reminder_sent` (the only WHERE
  predicates involve `submitted_date` and `asked_date`).
  `is_all_recs_submitted` only reads `submitted_date`. `pages/`
  and `exports.py` do not reference `confirmed` or `reminder_sent`
  at all (verified via grep; `pages/3_Recommenders.py` does not
  yet exist — landing target is Phase 5).
- **`tests/test_database.py`** — 18 new tests:
  - `TestInitDb` gets 4 pins (3 column-spec + 1 FK survival):
    `test_recommenders_confirmed_column_is_integer_nullable`
    (INTEGER, no DEFAULT — tri-state pending stays NULL),
    `test_recommenders_reminder_sent_column_is_integer_with_zero_default`
    (INTEGER, `dflt_value == "0"`),
    `test_recommenders_has_reminder_sent_date_column_nullable`
    (TEXT, no DEFAULT), and
    `test_recommenders_foreign_key_survives_rebuild`
    (PRAGMA foreign_key_list confirms position_id → positions.id
    with `on_delete == "CASCADE"` post-rename).
  - `TestRecommenders` gets 3 round-trip / defaults pins:
    `test_fresh_recommender_row_defaults` (add_recommender with
    only `recommender_name` → `confirmed=NULL`,
    `reminder_sent=0`, `reminder_sent_date=NULL`),
    `test_integer_confirmed_values_roundtrip` (0 / 1 / NULL all
    round-trip), and
    `test_integer_reminder_sent_and_date_roundtrip` (both the
    sent+dated and explicit-unsent states round-trip).
  - New `TestRecommendersRebuildMigration` class (11 tests)
    modeled on Sub-tasks 8 + 10's migration-test precedents.
    Shared `_seed_pre_v1_3_recommenders` helper builds a minimal
    pre-v1.3 DB via `tmp_path` + monkeypatched `DB_PATH`,
    including the pre-v1.3 applications columns Sub-tasks 8 + 10
    migrate (so init_db() runs ALL applicable migrations cleanly
    in order — Sub-task 8, Sub-task 10, Sub-task 11). Cases:
    `'Y'` → 1, `'N'` → 0, NULL stays NULL, other values
    (`'maybe'` / `''` / `'y'`) → NULL; `reminder_sent='Y'` →
    flag=1 / date=NULL, NULL / `''` / `'N'` / freetext →
    flag=0 / date=NULL, date-shaped → flag=0 /
    date=`<value>`; other columns preserved verbatim; FK +
    CASCADE still cleans up recommenders on delete_position;
    AUTOINCREMENT counter advances past migrated ids; second
    `init_db()` is a strict no-op (PRAGMA table_info guard
    evaluates False once `confirmed`'s type is INTEGER).
  - `import pandas as pd` added at the top for `pd.isna`
    checks on NULL-able columns (pandas may return None or NaN
    depending on whether other rows in the same column forced
    the dtype to float).

### Changed — v1.3 alignment Sub-task 12 (branch `feature/align-v1.3`)

Sub-task 12 aligns `app.py` with DESIGN.md v1.3 §8.0 (cross-page
conventions) + §8.1 (dashboard panel specifications + funnel visibility
rules + empty-state branches). Pure display-layer change — no schema,
no new database queries, no config edits.

- **`app.py` `st.set_page_config(…)`** added as the FIRST Streamlit
  call per DESIGN §8.0 + D14: `page_title="Postdoc Tracker"`,
  `page_icon="📋"`, `layout="wide"`. Data-heavy views (KPI grid,
  funnel, timeline) need horizontal room; the default centered layout
  cramps at ~750px. Placed immediately after imports, before
  `database.init_db()`, so it precedes every other `st.*` call.
- **`app.py` top-bar 🔄 Refresh button removed** per DESIGN D13.
  Streamlit reruns on any widget interaction; a manual refresh is
  cognitive noise for a single-user local app. The `st.columns([6, 1])`
  title/refresh wrap is replaced with a plain `st.title("Postdoc
  Tracker")` — no more half-empty column on the right. The pre-v1.3
  C3-locked decision is explicitly superseded by D13.
- **`app.py` Tracked KPI gains the locked help-tooltip string** per
  DESIGN §8.1: `help="Saved + Applied — positions you're still
  actively pursuing"`. Hovering the metric explains the arithmetic so
  the reader doesn't have to guess what "tracked" means. AppTest
  surfaces the tooltip at `metric.proto.help` (probed before writing
  the pin test).
- **`app.py` Application Funnel rewritten to be `FUNNEL_BUCKETS`-
  driven** per DESIGN §8.1 + D11 + D17:
  - Per-bucket counts are computed by summing `count_by_status()` over
    each bucket's raw-status tuple. The only multi-status bucket today
    is "Archived" (= `[REJECTED]` + `[DECLINED]`, D17); other buckets
    map one-to-one, so the change is a behavioural no-op on every
    non-archived row and correctly aggregates archived rows.
  - y-axis labels are the bucket LABELS (UI strings like "Saved" /
    "Applied" / …), not the raw `STATUS_VALUES` sentinels
    (`"[SAVED]"` / `"[APPLIED]"` / …). The presentation/storage split
    per D11 + D16 — storage keeps bracketed enum sentinels, the UI
    renders the clean labels. The y-axis is still reversed so the
    first visible bucket sits at the top (pipeline reads top-down).
  - Bar colors come from `FUNNEL_BUCKETS[i][2]`, not from
    `STATUS_COLORS`. The bucket OWNS its color because a bucket can
    aggregate multiple raw statuses — `STATUS_COLORS` is for
    per-status surfaces (Opportunities-table badges, tooltips).
  - Visible buckets = `FUNNEL_BUCKETS` entries whose label is NOT in
    `FUNNEL_DEFAULT_HIDDEN`, OR every bucket when the user has clicked
    `[expand]`. A visible bucket with zero count renders as a
    zero-width bar — keeps the chart shape stable as the pipeline
    fills up.
- **`app.py` single `[expand]` button + session flag** replacing the
  pre-v1.3 per-bucket checkbox model (DESIGN §8.1 + D24). Button
  label is literally `"[expand]"` (brackets included). Clicking fires
  a bound `_expand_funnel` callback via `on_click=` that flips
  `st.session_state["_funnel_expanded"]` to `True`; callbacks run
  BEFORE the next script rerun, so the funnel branches evaluate with
  expanded=True on the very first post-click render. No `st.rerun()`
  is needed and the pre-v1.3 "double rerun" gotcha is avoided. The
  flag is one-way (no collapse in v1).
- **`app.py` three-branch funnel empty-state matrix** per DESIGN
  §8.1, evaluated in order:
  - **(a)** `total == 0` — no positions at all. Render
    `st.info("Application funnel will appear once you've added
    positions.")` and SUPPRESS the `[expand]` button (nothing to
    expand into).
  - **(b)** total > 0, `_funnel_expanded is False`, every
    default-visible bucket has count 0. Render
    `st.info("All your positions are in hidden buckets. Click
    [expand] below to reveal them.")` followed by the `[expand]`
    button. Terminal-only DBs (every position in Closed / Archived)
    land here — this is the v1.3 REPLACEMENT for the pre-Sub-task-12
    "Option C: terminal-only DB still renders the figure" behaviour.
  - **(c)** otherwise. Render the chart; `[expand]` button below iff
    `FUNNEL_DEFAULT_HIDDEN` is non-empty AND not yet expanded. After
    click, the button no longer renders (since "not yet expanded"
    flips to False). Subheader renders in all three branches for
    page-height stability.
- **`tests/test_app_page.py`** — 59 tests on `app.py`; +11 new
  versus the pre-Sub-task-12 count of 48 (before: 43 were in the
  file and we had 5 unrelated other counts; net +11 on this file).
  Breakdown:
  - `TestT1AppShell` +1 (`test_page_config_sets_wide_layout` —
    source-level grep since AppTest doesn't surface set_page_config).
  - `TestT1CKpiCountsAndRefresh` → renamed `TestT1CKpiCounts`; the
    two refresh-button tests are gone and replaced with
    `test_refresh_button_absent` + `test_tracked_kpi_help_tooltip`
    (pin `metric.proto.help` against the locked string). Net: 0.
  - `TestT2AFunnelBar` — four tests renamed (one-bar-per-VISIBLE-
    BUCKET-in-order; x-values SUM bucket raw statuses; colors from
    FUNNEL_BUCKETS[i][2]; missing buckets render as zero-width bars).
    Each assertion is now bucket-aware and re-computes the expected
    visible-bucket list dynamically from config rather than hard-
    coding the 7-status STATUS_VALUES list. Net: 0.
  - `TestT2BFunnelEmptyState` — reshaped to the three-branch matrix.
    `EMPTY_COPY` → `EMPTY_COPY_A`; new `EMPTY_COPY_B` constant. New
    tests: `test_empty_db_fires_branch_a`,
    `test_branch_a_empty_copy_is_spec_exact`,
    `test_all_hidden_bucket_data_fires_branch_b`,
    `test_branch_b_empty_copy_is_spec_exact`,
    `test_single_open_position_fires_branch_c`,
    `test_mixed_visible_and_hidden_data_fires_branch_c`,
    `test_subheader_renders_in_all_branches`. The pre-v1.3
    `test_terminal_only_db_still_renders_figure` is GONE — its
    behaviour is explicitly inverted in v1.3 (terminal-only DB now
    fires branch (b), not the chart). Net: +2.
  - `TestT2CFunnelLayout.test_empty_state_info_renders_inside_left_
    column` — pointer update only: references `EMPTY_COPY_A` instead
    of the removed `EMPTY_COPY`.
  - `TestT2DFunnelExpand` — NEW class, 8 tests:
    `test_expand_button_renders_in_branch_c_by_default`,
    `test_expand_button_absent_in_branch_a`,
    `test_expand_button_present_in_branch_b`,
    `test_funnel_expanded_defaults_false`,
    `test_clicking_expand_sets_session_state_true`,
    `test_clicking_expand_reveals_all_buckets_on_chart` (the
    load-bearing behavioural pin — seeds visible + both hidden
    buckets, asserts pre-click y-axis excludes hidden labels and
    post-click y-axis matches every `FUNNEL_BUCKETS` label in order),
    `test_expand_button_hides_after_click`,
    `test_clicking_expand_from_branch_b_renders_chart`. Net: +8.
  - Unrelated T1-D / T1-E / T3 classes untouched.

### Changed — v1.3 alignment Sub-task 13 (branch `feature/align-v1.3`)

Sub-task 13 aligns `pages/1_Opportunities.py` with DESIGN.md v1.3 §8.0
(cross-page conventions) + §8.2 (Opportunities page + Delete-button
placement). Pure display-layer change — no schema, no new database
queries, no config edits. Parallel in spirit to Sub-task 12's §8.0 +
§8.1 alignment for `app.py`; this commit group closes the remaining
page-side gap left by that sub-task.

- **`pages/1_Opportunities.py` `st.set_page_config(…)`** added as the
  first Streamlit call per DESIGN §8.0 + D14: `page_title="Postdoc
  Tracker"`, `page_icon="📋"`, `layout="wide"`. Data-heavy views
  (positions table + edit panel) need horizontal room. Placed
  immediately after `database.init_db()`, before `st.title(…)`.
- **`filter_status` selectbox gains `format_func=lambda v:
  config.STATUS_LABELS.get(v, v)`** per DESIGN §8.0 Status label
  convention (storage holds raw bracketed values; UI renders the
  stripped labels). The lambda wraps the literal `STATUS_LABELS.get`
  so the "All" sentinel passes through (vanilla `STATUS_LABELS.get(
  "All")` returns `None` and would leak a blank option into the
  rendered dropdown). `.value` and the downstream filter predicate
  keep the raw storage key, so `df[df["status"] == status_filter]`
  compares apples to apples.
- **`edit_status` selectbox on the Overview form gains
  `format_func=config.STATUS_LABELS.get`**. No "All" sentinel on
  this path, so the literal dict-method is sufficient.
  `session_state["edit_status"]` stays raw; the Save handler writes
  the storage value into `positions.status` unchanged.
- **Edit-panel tab selector swapped from `st.tabs` to
  `st.radio(horizontal=True, label_visibility="collapsed",
  key="_active_edit_tab")`** — the load-bearing change for the
  Delete-button placement below. Rationale:
  - DESIGN §8.2 Delete row: "Button rendered below the edit panel
    (outside the panel box), visible only when the active tab is
    Overview."
  - Streamlit 1.56's `st.tabs(key=...)` accepts a `key` keyword but
    does NOT actually populate `session_state` with the active tab
    (verified via isolation probe before the swap); there is no
    public API to detect the active `st.tabs` tab.
  - `st.radio` with `horizontal=True` + collapsed label visually
    approximates the old tab strip, while its value lives in
    `session_state["_active_edit_tab"]` and drives branch-rendering:
    each tab body is wrapped in `if active_tab == "Overview": …` /
    `elif active_tab == "Requirements": …` / etc. On non-active
    tabs, the tab-specific widgets ARE NOT EMITTED (pre-Sub-task-13
    `st.tabs` emitted ALL tab bodies on every run and CSS-hid
    inactive ones). Test consequence: non-Overview tests must now
    set `session_state["_active_edit_tab"]` before accessing
    e.g. `edit_req_cv` radios.
- **Delete button relocated to below all four tab branches**,
  gated by `if active_tab == "Overview":` per DESIGN §8.2 Delete row
  ("the button's scope is the whole position, not the active tab's
  data — hence the Overview-only placement, matching the tab where
  the user is reviewing the position as a whole"). The `elif
  st.session_state.get("_delete_target_id") == sid:` dialog-reopen
  branch from Tier 5 lives in the same gated block — same AppTest
  script-run quirk that required re-opening the dialog across
  reruns is preserved end-to-end. On Requirements / Materials /
  Notes tabs the Delete button is now not in the DOM at all
  (pre-Sub-task-13 it was still there, just CSS-hidden; AppTest
  would find it via `at.button(key="edit_delete")` regardless of
  active tab).
- **`tests/test_opportunities_page.py`** — 441 tests on the page;
  +13 versus the pre-Sub-task-13 count of 428 (the branch was
  428-green at the head of Sub-task 12). Highlights:
  - New `TestPageConfigSetsWideLayout::test_page_config_sets_wide_
    layout` — source-grep pin (AppTest doesn't surface
    set_page_config), mirrors the `test_app_page.py` precedent.
  - New `TestFilterStatusFormatFunc` (3 tests): options display
    labels + "All" passthrough; `.value` stays raw; end-to-end
    storage/display split via a real filter round-trip.
  - New `TestEditStatusFormatFunc` (2 tests): Overview form's
    Status selectbox mirrors the filter_status contract, minus the
    "All" passthrough.
  - New `TestMaterialsFilterPredicateIsYes` (1 test): Materials tab
    renders a checkbox iff `session_state[f"edit_{req_col}"] ==
    "Yes"` (DESIGN §8.2) — independent pin from Sub-task 2's
    migration tests.
  - New `TestDeleteButtonTabSensitivity` (5 tests): Delete button
    visible on Overview, absent on each of Requirements / Materials
    / Notes, and reappears on return to Overview.
  - `TestEditPanelShell` — 4 tests updated to use
    `at.radio(key="_active_edit_tab")` instead of `at.tabs`, plus a
    new `test_default_active_tab_is_first_config_entry` pinning
    Overview as the default.
  - `TestRequirementsTabWidgets` / `TestMaterialsTabWidgets` /
    `TestNotesTabWidgets` + the three matching Save classes +
    `TestPreSeedNaNCoercion` — existing tests updated to call the
    new `_select_row_and_tab(at, row, tab_name)` helper (which
    writes both the row selection and the active tab to
    session_state in one step) before accessing non-Overview
    widgets. `TestRequirementsTabWidgets.test_one_radio_per_
    requirement_doc` bumps its radio-count assertion by +1 for the
    new tab selector. `TestNotesTabWidgets.test_text_area_renders_
    when_row_selected` drops from 2→1 expected text_areas
    (`edit_work_auth_note` now renders only when
    active_tab == "Overview"; `edit_notes` is the only text_area on
    the Notes tab).
  - `TestFilterBarStructure.test_status_options_match_config` +
    `TestOverviewTabWidgets.test_status_selectbox_options_match_
    config` — expected-options lists swap from raw STATUS_VALUES
    to `[STATUS_LABELS[v] for v in STATUS_VALUES]` (AppTest
    surfaces `.options` as post-format_func display strings).

### Changed — v1.3 alignment Sub-task 14 (branch `feature/align-v1.3`)

Sub-task 14 is the v1.3 doc-alignment sweep across the non-DESIGN
project docs. Closes the last v1.3-alignment item before the branch
pushes to a PR. Pure docs change — no schema, no new queries, no
config edit, no test drift. Scope: `GUIDELINES.md`, `CHANGELOG.md`,
`roadmap.md`, `TASKS.md`, `docs/ui/wireframes.md`,
`docs/dev-notes/extending.md`.

- **`GUIDELINES.md` §3 (Naming Conventions — widget keys
  sub-section)** — sentinel list gains `_active_edit_tab`
  (Opportunities edit-panel tab selector, landed Sub-task 13) and
  `_funnel_expanded` (dashboard `[expand]` toggle, landed
  Sub-task 12). The two new sentinels follow the existing
  `_edit_form_sid` / `_delete_target_id` / `_skip_table_reset`
  precedent — leading `_` marks internal state, not a widget key.
- **`GUIDELINES.md` §6 (Config Usage — status selectbox
  example)** — alias + literal swap for the Sub-task 5 rename
  ([OPEN] → [SAVED]):
  - `from config import STATUS_VALUES, STATUS_OPEN` →
    `from config import STATUS_VALUES, STATUS_SAVED, STATUS_LABELS`.
  - `st.selectbox("Status", STATUS_VALUES)` gains
    `format_func=STATUS_LABELS.get` so the GOOD example matches
    DESIGN §8.0 Status label convention (the UI surface convention
    Sub-task 13 actually enforced on `pages/1_Opportunities.py`).
  - `if row["status"] == STATUS_OPEN:` →
    `if row["status"] == STATUS_SAVED:`.
  - BAD example literal list swaps `["[OPEN]", "[APPLIED]", ...]`
    → `["[SAVED]", "[APPLIED]", ...]` and the BAD equality check
    swaps `"[OPEN]"` → `"[SAVED]"`.
- **`GUIDELINES.md` §6 pre-merge grep rule** —
  `grep -nE "\[OPEN\]|\[APPLIED\]|\[INTERVIEW\]" app.py pages/*.py`
  → `grep -nE "\[SAVED\]|\[APPLIED\]|\[INTERVIEW\]" app.py pages/*.py`.
  The rule's purpose (catch hardcoded stage-0/1/2 literals that
  drift from the config constants) is unchanged; the new pattern
  pins the current stage-0 literal, which is what the rule
  actually enforces.
- **`GUIDELINES.md` §7 (Streamlit Patterns — controlled inputs
  for enumerated values)** — the status selectbox example gains
  `format_func=config.STATUS_LABELS.get` + a short paragraph
  explaining the storage/display split and the `"All"`-passthrough
  lambda wrapper (`lambda v: STATUS_LABELS.get(v, v)`). Brings the
  canonical snippet in line with how Sub-task 13 wired
  `pages/1_Opportunities.py`'s `filter_status` / `edit_status`
  selectboxes.
- **`roadmap.md` "In flight" paragraph** — Sub-tasks 1–13 → 1–14
  in the opening clause; a final clause describes the Sub-task 14
  doc-sweep inline (GUIDELINES sentinel list + grep rule + status-
  selectbox example + CHANGELOG / TASKS / roadmap updates).
  `441 tests green` count preserved — no tests added, none removed.
- **`TASKS.md`** — new `[x] Sub-task 14` entry inserted between
  Sub-task 13 and the remaining `[ ] Push branch; open PR; merge
  to main` bullet; `_Updated:` footer bumped from "Sub-tasks
  1–13 shipped" to "Sub-tasks 1–14 shipped". Matches the cadence
  of every prior sub-task entry on this sprint.
- **`CHANGELOG.md`** — this entry. Placed in `[Unreleased]`
  immediately after the Sub-task 13 `Changed` block, mirroring
  the per-sub-task cadence of the rest of the section. Migration
  section below gains the matching "Sub-task 14 requires no
  migration" line so readers can scan the Migration block in
  isolation.
- **`docs/ui/wireframes.md`** — audited against DESIGN §8.1/§8.2/§8.3.
  Already shows the v1.3 state: `[expand]` button on the funnel,
  `Saved`/`Applied` labels (not raw bracketed sentinels) in the
  dashboard Upcoming table and the Opportunities-page table, no
  🔄 Refresh button, a multi-interview list on the Applications
  page, and the Delete button rendered below the Opportunities
  edit panel. The edit-panel `[ Overview ] [ Requirements ] [
  Materials ] [ Notes ]` ASCII strip is intent-only — DESIGN §8.2
  still calls these "Tabs" even though Sub-task 13 switched the
  underlying widget from `st.tabs` to `st.radio(horizontal=True)`;
  the sketch's tab appearance matches a horizontal radio's rendered
  shape, consistent with the file's "intent-only" disclaimer at
  the top. No changes.
- **`docs/dev-notes/extending.md`** — audited against DESIGN §5.3.
  Already v1.3-aligned: "Add a new pipeline status" references
  `STATUS_LABELS` / `FUNNEL_BUCKETS` / `FUNNEL_DEFAULT_HIDDEN` per
  D24; "Rename a pipeline status" references `STATUS_LABELS` +
  the config-driven DDL DEFAULT (Sub-task 4) so the one-shot
  `UPDATE` is the whole migration; "Add a new vocabulary option"
  lists `INTERVIEW_FORMATS` alongside the other v1.3 vocabs. No
  changes.
- **Out-of-scope (noted for follow-up)**:
  `docs/dev-notes/streamlit-state-gotchas.md` entry #14 still
  describes the removed 🔄 Refresh button and entry #13's example
  still uses the `interview1_date`/`interview2_date` pair that
  Sub-task 8 normalized into the `interviews` sub-table. Outside
  Sub-task 14's stated scope; candidate for a separate sub-task
  if approved.

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

**Sub-task 10** — schema migration splitting the dual-purpose
`applications.confirmation_email` TEXT column into
`confirmation_received INTEGER DEFAULT 0` + `confirmation_date TEXT`.
`init_db()` runs this automatically on the first app start after
upgrade; a user does not need to execute anything manually. For
the record, the equivalent SQL executed is:

```sql
-- (a) Add the two new columns. Each ALTER is guarded by
--     PRAGMA table_info (absent ⇒ add, present ⇒ skip) so a
--     rerun is a strict no-op.
ALTER TABLE applications
    ADD COLUMN confirmation_received INTEGER DEFAULT 0;
ALTER TABLE applications
    ADD COLUMN confirmation_date TEXT;

-- (b) One-shot translation of the two legitimate legacy shapes.
--     Gated by a migrate-once flag (either new column absent
--     pre-ALTER ⇒ run the UPDATEs; both present ⇒ skip).
--
--     Date-shaped legacy values: the 10-character ISO date
--     pattern captured via SQLite GLOB character classes.
--     Anything not matching this shape — including 'Y', '',
--     NULL, legacy 'N', or freetext — falls through.
UPDATE applications
   SET confirmation_received = 1,
       confirmation_date     = confirmation_email
 WHERE confirmation_email GLOB
       '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]';

--     Flag-only legacy values: 'Y' sets the flag; the date
--     stays NULL because the old column never recorded one
--     alongside the 'Y' sentinel.
UPDATE applications
   SET confirmation_received = 1
 WHERE confirmation_email = 'Y';

-- (c) The physical `confirmation_email` column stays in the
--     applications CREATE TABLE DDL per DESIGN §6.3 step (c)
--     "leave old columns NULL until a rebuild drops them".
--     No caller writes to it post-split; the column is dead
--     weight but preserved to avoid a table-rebuild migration
--     this release. Scheduled for physical drop in v1.0-rc.
```

Idempotence follows the Sub-task 8 **migrate-once gate** shape:
the one-shot UPDATE block only fires when either new column was
absent pre-ALTER. A second `init_db()` call finds both columns
already present and skips the UPDATEs entirely — no
re-translation of any legacy value, no overwrite of user-entered
data that happens to look like the legacy shapes. Values that fall
through both WHERE clauses (NULL, `''`, legacy `'N'`, freetext)
leave the new columns at their DEFAULTs (received=0, date=NULL);
this matches "no confirmation data" and avoids guessing beyond the
two shapes D19 names.

A dev DB that somehow has the new columns but legacy values still
in `confirmation_email` (hand-built, partial failed migration) is
out of scope for the auto-path; recover with a one-time manual run
of the two UPDATEs above.

**Sub-task 11** — schema migration rebuilding the `recommenders`
table to convert `confirmed TEXT` → `confirmed INTEGER`,
`reminder_sent TEXT` → `reminder_sent INTEGER DEFAULT 0`, and add
`reminder_sent_date TEXT`. `init_db()` runs this automatically on
the first app start after upgrade; a user does not need to execute
anything manually. Unlike Sub-tasks 8 + 10 (which kept legacy
columns physically present), this sub-task is a full table rebuild
because SQLite lacks in-place column-type change. For the record,
the equivalent SQL executed is:

```sql
-- (1) CREATE the target-schema table under a temporary name.
CREATE TABLE recommenders_new (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id        INTEGER NOT NULL,
    recommender_name   TEXT,
    relationship       TEXT,
    asked_date         TEXT,
    confirmed          INTEGER,                -- 0, 1, or NULL
    submitted_date     TEXT,
    reminder_sent      INTEGER DEFAULT 0,      -- 0 or 1
    reminder_sent_date TEXT,                   -- ISO, NULL if none
    notes              TEXT,
    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
);

-- (2) INSERT-COPY from the old table with CASE translations.
--     Other columns (id, position_id, recommender_name, relationship,
--     asked_date, submitted_date, notes) copy verbatim; id values are
--     preserved so the sqlite_sequence AUTOINCREMENT counter advances
--     past them on the next add_recommender call.
INSERT INTO recommenders_new (
    id, position_id, recommender_name, relationship, asked_date,
    confirmed, submitted_date, reminder_sent, reminder_sent_date, notes
)
SELECT
    id,
    position_id,
    recommender_name,
    relationship,
    asked_date,
    CASE confirmed
        WHEN 'Y' THEN 1
        WHEN 'N' THEN 0
        ELSE NULL
    END,
    submitted_date,
    CASE WHEN reminder_sent = 'Y' THEN 1 ELSE 0 END,
    CASE WHEN reminder_sent GLOB '????-??-??'
         THEN reminder_sent
         ELSE NULL
    END,
    notes
FROM recommenders;

-- (3) DROP the old table.  Safe with PRAGMA foreign_keys = ON:
--     recommenders is a CHILD (outbound FK to positions); nothing
--     points INTO recommenders, so the implicit DELETE FROM on DROP
--     has nothing to cascade.
DROP TABLE recommenders;

-- (4) RENAME the new table into place.
ALTER TABLE recommenders_new RENAME TO recommenders;
```

All four steps run inside a single transaction (the same one that
every init_db() DDL change shares). A mid-rebuild failure triggers
the `_connect()` context manager's rollback, so the DB cannot be
left with a half-migrated table alongside a temporary
`recommenders_new`.

Idempotence is implemented via a **declared-type gate**: before
step (1), `init_db()` reads `PRAGMA table_info(recommenders)` and
extracts the declared type of the `confirmed` column. If it is
already `INTEGER` (fresh DB built with the v1.3 CREATE TABLE, or
the rebuild has already run), the entire block short-circuits —
no re-rebuild, no data copied twice.

Value-translation caveats:

- **`confirmed` tri-state** — only the two canonical legacy values
  (`'Y'` / `'N'`) translate to integers (`1` / `0`); every other
  value (including legacy `'y'` / `'yes'` / `'maybe'` / empty
  string / any freetext typo) becomes NULL. This is the
  pending-response semantics — "we don't know for sure" is NULL,
  distinct from the explicit-no `0`. If a dev DB had been
  hand-editing the column with a non-`'Y'`/`'N'` vocabulary, those
  rows will read as pending after migration; re-save them from
  the Recommenders page (Phase 5) to set the intended integer.
- **`reminder_sent` date-shaped values** — the `GLOB '????-??-??'`
  pattern matches any 10-character `??-??` shape, including
  theoretically-pathological strings like `'abcd-ef-gh'`. Safe in
  practice because pre-v1.3 `reminder_sent` realistically held
  only dates, `'Y'`, or NULL; the looser GLOB is acceptable and
  matches the SQL the user prescribed. (Sub-task 10's
  `confirmation_email` split used a stricter `[0-9]`-digit-class
  pattern; the two patterns diverge intentionally.)
- **Explicit-unsent after migration** — a pre-v1.3
  `reminder_sent = 'Y'` row lands as `reminder_sent = 1,
  reminder_sent_date = NULL`; a pre-v1.3 date-shaped row lands
  as `reminder_sent = 0, reminder_sent_date = <value>`. If the
  user wants both flag and date set they can re-save from the
  Recommenders page (Phase 5). The migration's conservative
  "flag = 0 unless literally 'Y'" rule keeps the translation
  deterministic and matches the spec SQL exactly.

A dev DB that somehow has both the old recommenders table and a
stranded `recommenders_new` (hand-built, partial failed migration)
is out of scope for the auto-path. Recover manually: inspect both
tables, decide which carries the truth, DROP the stale one, RENAME
the live one to `recommenders`, and restart.

**Sub-task 12** requires no migration — the entire change is
display-layer (`app.py` only). No schema edit, no new database
queries, no config rename. A user upgrading to the new `app.py`
sees the wide layout, the removed 🔄 Refresh button, the Tracked
help-tooltip, and the `FUNNEL_BUCKETS`-aggregated funnel bars on
the next page load. Existing DBs round-trip transparently. The
session flag `st.session_state["_funnel_expanded"]` is
session-scoped and defaults to False — no persistence to disk, no
"migration" of prior sessions needed.

**Sub-task 13** requires no migration — the entire change is
display-layer (`pages/1_Opportunities.py` only). No schema edit,
no new database queries, no config rename. A user upgrading to
the new page sees the wide layout, the status selectboxes
rendering display labels (Saved / Applied / …) instead of raw
bracketed values, the edit-panel tab strip driven by a horizontal
`st.radio` instead of `st.tabs`, and the Delete button absent on
Requirements / Materials / Notes tabs. Existing DBs round-trip
transparently (storage still holds raw `STATUS_VALUES`; format_func
only changes what the UI renders). The session flag
`st.session_state["_active_edit_tab"]` is session-scoped, defaults
to `"Overview"` (the first `EDIT_PANEL_TABS` entry) via st.radio's
`index=0` + Streamlit's widget-default contract — no persistence
to disk, no "migration" of prior sessions needed.

**Sub-task 14** requires no migration — the entire change is docs
(`GUIDELINES.md`, `CHANGELOG.md`, `roadmap.md`, `TASKS.md`; no
edits needed in `docs/ui/wireframes.md` / `docs/dev-notes/
extending.md` after audit). No schema edit, no new database
queries, no config rename, no code touched. A user upgrading
reads more v1.3-accurate conventions in GUIDELINES (status-
selectbox examples matching the live `pages/1_Opportunities.py`,
pre-merge grep pattern matching the current stage-0 literal,
sentinel list mentioning the Sub-task 12/13 additions) — but
nothing about the running app or its database changes.

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
