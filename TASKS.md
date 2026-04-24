# Tasks

_Scope: software for this application tracker only. Older completions move to
`CHANGELOG.md` at the end of each sprint._

---

## Current sprint — v1.3 DESIGN-to-codebase alignment

Branch: `feature/align-v1.3` (off `main @ cf45c09`, after v1.1 doc refactor merged via PR #7)

- [x] Sub-task 1: `config.py` constants + invariants (VALID_PROFILES,
      STATUS_LABELS, INTERVIEW_FORMATS + 3 invariants)
- [x] Sub-task 2: `REQUIREMENT_VALUES` Y/N → Yes/No migration (D21) —
      `config.py` vocab swap, `database.py` DDL `DEFAULT 'No'` + one-shot
      UPDATE migration in `init_db()`, `pages/1_Opportunities.py`
      Materials-tab filter `== "Yes"`; CHANGELOG Migration note landed.
- [x] Sub-task 3: `WORK_AUTH_OPTIONS` / `FULL_TIME_OPTIONS` vocabulary
      swap per DESIGN §5.1 + D22 — `config.py` lists collapsed to
      Yes/No/Unknown and Full-time/Part-time/Contract; 2 new `_spec_values`
      tests; no DDL change (both columns plain TEXT); CHANGELOG Migration
      note documents manual translation for dev DBs carrying legacy values.
- [x] Sub-task 4: config-drive the two DDL DEFAULT clauses in
      `database.init_db()` per DESIGN §6.2 — `positions.status` and
      `applications.result` DEFAULTs now f-string-interpolate from
      `config.STATUS_VALUES[0]` and `config.RESULT_DEFAULT`. Pure
      refactor, no behaviour change; sets up Sub-task 5 as a
      config-only edit. New pin: `test_ddl_defaults_interpolate_from_config`
      (monkeypatches to sentinels + reads `PRAGMA table_info`). Closes
      the C6/C7 pre-T4 item.
- [x] Sub-task 5: `[OPEN]→[SAVED]` status rename + `"Med"→"Medium"`
      priority rename, applied atomically across `config.py`,
      `database.py` (incl. two idempotent `UPDATE positions` loops in
      `init_db()`), `app.py` (Tracked KPI consumer), and all tests.
      No DDL edit (Sub-task 4 config-drive carries the DEFAULT swap).
      Acceptance grep clean: `grep -nE '\[OPEN\]|STATUS_OPEN|"Med"'
      *.py pages/ tests/` → 0 hits. 305 tests green (+5 new pins).
- [x] Sub-task 6: `positions.updated_at` column + `AFTER UPDATE`
      trigger per DESIGN §6.2 + D25. `CREATE TABLE` gains
      `updated_at TEXT DEFAULT (datetime('now'))`; `init_db()`
      migration block gains `PRAGMA table_info`-guarded
      `ALTER TABLE positions ADD COLUMN updated_at TEXT` +
      one-shot backfill `UPDATE ... WHERE updated_at IS NULL`
      (SQLite disallows non-constant DEFAULT on ALTER against a
      non-empty table); `CREATE TRIGGER IF NOT EXISTS
      positions_updated_at` stamps the row on every UPDATE, with
      loop prevention riding on SQLite's default
      `recursive_triggers = OFF`. 5 new `TestInitDb` tests (column
      spec, trigger registered, INSERT via DDL default, UPDATE via
      trigger + 1.1 s sleep, pre-v1.3 migration path + idempotence).
      CHANGELOG Migration note recorded. 310 tests green.
- [x] Sub-task 7: `positions.work_auth_note` column + Overview-tab
      `work_auth` selectbox + `work_auth_note` text_area per
      DESIGN §6.2 + §8.2 + D22. Closes the vertical slice
      Sub-task 3 deferred (WORK_AUTH_OPTIONS vocabulary landed;
      UI deferred). `database.py` CREATE TABLE adds
      `work_auth_note TEXT` after `work_auth`; `init_db()`
      migration adds a PRAGMA-guarded `ALTER TABLE ADD COLUMN`
      (no DEFAULT, constant-expression-free so it works against
      non-empty tables; no backfill needed — NULL is the honest
      "unknown" state for pre-v1.3 rows). `pages/1_Opportunities.py`
      pre-seed gains F2-style work_auth coercion +
      `_safe_str(work_auth_note)`, Overview form adds selectbox +
      text_area between Link and submit, Save payload extends
      with both. 9 new tests (2 TestInitDb, 1 TestUpdatePosition
      roundtrip, 5 TestOverviewWorkAuthWidgets, 1 TestOverviewSave);
      `TestNotesTabWidgets` text_area tight-bound bumps 1 → 2 per
      its own in-line maintenance note. CHANGELOG Migration note
      recorded. 319 tests green.
- [x] Sub-task 8: `interviews` sub-table + CRUD + one-shot
      migration from `applications.interview1_date`/`interview2_date`
      + row-per-interview rewrite of `get_upcoming_interviews`, per
      DESIGN §6.2 + §6.3 + §7 + D18. `database.py` gains
      `CREATE TABLE IF NOT EXISTS interviews` + FK cascade +
      UNIQUE(application_id, sequence) + `idx_interviews_application`,
      a migrate-once gate (sqlite_master probe pre-CREATE) that
      drives the one-shot INSERT SELECT copy of legacy `interview1_date`
      (sequence=1) and `interview2_date` (sequence=2) into the new
      table then NULL-clears the source columns, and a full CRUD
      section (`add_interview` with auto-sequence and a
      keyword-only `propagate_status=True` kwarg reserved for
      Sub-task 9's R2 cascade body; `get_interviews`,
      `update_interview`, `delete_interview`).
      `get_upcoming_interviews` rewritten to row-per-interview
      over `interviews JOIN applications JOIN positions`.
      **Scope expanded beyond the originally stated database-only
      scope**: `app.py._next_interview_display` migrated from
      dual-column to single-`scheduled_date` scan; five
      `tests/test_app_page.py::TestT1DNextInterviewKpi` tests
      rewritten to seed via `add_interview`. 30 new tests:
      5 schema, 9 add_interview, 3 get_interviews, 3
      update_interview, 2 delete_interview, 1 full-cascade,
      6 migration, 1 new row-per-interview pin in
      `TestGetUpcomingInterviews`. CHANGELOG Migration note
      records the full SQL including the migrate-once gate
      rationale. 349 tests green.
- [x] Sub-task 9: R1/R2/R3 pipeline auto-promotion cascade per
      DESIGN §9.3 + §7 + D12 + D23. `upsert_application`
      signature bumps to
      `(position_id, fields, *, propagate_status=True) -> dict`
      returning `{"status_changed", "new_status"}`; R1 (applied_date
      NULL→set + status=SAVED guard → STATUS_APPLIED) and R3
      (response_type=Offer + status NOT IN TERMINAL_STATUSES →
      STATUS_OFFER) both fire inside the primary-write transaction
      (atomicity via `_connect()` rollback). `add_interview` R2
      body (Sub-task 8 stub) now wired: status=APPLIED guard →
      STATUS_INTERVIEW, count-free per §9.3 narrative. `status_changed`
      compares status STRING pre/post so the STATUS_OFFER + R3
      self-assignment reads as no-change. New
      `is_all_recs_submitted(position_id) -> bool` helper
      (Applications group); zero-recs = True (vacuous truth per D23).
      `compute_materials_readiness` swaps hardcoded tuple for
      `(config.STATUS_SAVED, config.STATUS_APPLIED, config.STATUS_INTERVIEW)`
      — closes the C1 carry-over from Sub-task 5. 40 new tests:
      4 R1 isolation, 9 R3 isolation (incl. 3-terminal parametrize),
      7 combined R1+R3 matrix, 3 indicator shape, 1 upsert atomicity,
      9 R2 isolation (incl. 3-terminal parametrize), 1 add_interview
      atomicity, 5 is_all_recs_submitted, 1 sentinel for the
      materials-readiness alias swap. Pure behavioural change — no
      schema, no Migration entry. 389 tests green.
- [x] Sub-task 10: `applications.confirmation_email` split into
      `confirmation_received INTEGER DEFAULT 0` +
      `confirmation_date TEXT` per DESIGN §6.2 + §6.3 + D19 + D20.
      `CREATE TABLE applications` adds the new columns right after
      the legacy one; `init_db()` migration block adds a PRAGMA-
      guarded `ALTER TABLE ADD COLUMN` pair + migrate-once gate
      (Sub-task 8 pattern) running two disjoint one-shot UPDATEs:
      date-shaped values (via SQLite
      `GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'`) populate
      both new columns; flag-only `'Y'` sets `confirmation_received
      = 1` and leaves `confirmation_date` NULL. NULL / empty /
      `'N'` / freetext fall through — defaults persist. Physical
      drop of the legacy `confirmation_email` column is deferred to
      v1.0-rc (DESIGN §6.3 step c). `upsert_application` is
      schema-agnostic so no writer-side change was needed; no
      caller writes to the legacy column post-split (verified via
      grep). 10 new tests: 2 `TestInitDb` column specs, 1
      `TestUpsertApplication` round-trip (incl. legacy column
      stays NULL), new `TestConfirmationSplitMigration` class
      (7 tests: 'Y' → received-only, date-shaped → both columns,
      NULL / empty / 'N' → defaults, fresh-DB DDL defaults, second
      `init_db()` idempotence). Sub-task 8 seed updated to include
      `confirmation_email TEXT` for realism (Sub-task 10's UPDATEs
      reference it in WHERE). 399 tests green. CHANGELOG Migration
      note records the full SQL (ALTER + GLOB-based translation +
      flag-only UPDATE).
- [ ] Sub-task 11+: remaining v1.3 alignment items per
      `memory/project_state.md` (`recommenders.reminder_sent` TEXT
      → INTEGER flag + `reminder_sent_date TEXT` split;
      `recommenders.confirmed` TEXT → INTEGER 0/1/NULL)
- [ ] Push branch; open PR; merge to main

## Prior sprint — v1.1 doc refactor (merged via PR #7)

- [x] Commit 1: DESIGN + GUIDELINES drift fixes (C1–C13)
- [x] Commit 2: DESIGN restructure + `docs/adr/` skeleton
- [x] Commit 3: GUIDELINES restructure + `docs/dev-notes/` extraction
- [x] Commit 4: TASKS + roadmap + CHANGELOG + .gitignore
- [x] Retroactive git tags: `v0.1.0` · `v0.2.0` · `v0.3.0` · `v0.4.0`
- [x] Push branch; open PR; merge to main

---

## Up next (post doc refactor)

### Code refactor pre-T4 (new branch off main after doc refactor merges)

These are the code-only changes that the v1.1 doc refactor flagged but
deferred. All require separate approval before execution.

- [x] **C1** `database.py compute_materials_readiness` — replace hardcoded
      `("[OPEN]", "[APPLIED]", "[INTERVIEW]")` with
      `(config.STATUS_OPEN, STATUS_APPLIED, STATUS_INTERVIEW)`
      — shipped as v1.3 alignment Sub-task 9 (targeting the renamed
      `config.STATUS_SAVED`/`STATUS_APPLIED`/`STATUS_INTERVIEW` trio;
      pinned by `test_active_statuses_drive_from_config_aliases`)
- [ ] **C2** Delete unused `TRACKER_PROFILE` from `config.py`
- [x] **C6/C7** Config-drive schema DEFAULTs in `init_db()` DDL
      (`DEFAULT '{config.STATUS_VALUES[0]}'` / `DEFAULT '{config.RESULT_DEFAULT}'`)
      — shipped as v1.3 alignment Sub-task 4
- [ ] **C12** Add `assert DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS` to `config.py`
- [x] Rename `[OPEN]` → `[SAVED]` + idempotent `UPDATE positions SET status=...` migration
      — shipped as v1.3 alignment Sub-task 5
- [x] Rename `PRIORITY_VALUES` `"Med"` → `"Medium"` + migration
      — shipped as v1.3 alignment Sub-task 5
- [ ] Add `config.STATUS_LABELS` (presentation-layer UI strings) +
      `ARCHIVED_BUCKET` grouping of `TERMINAL_STATUSES` on the funnel
- [ ] Delete the 🔄 Refresh button from `app.py`
- [ ] `st.set_page_config(layout="wide", page_title="Postdoc Tracker", page_icon="📋")` on `app.py`
      and every `pages/*.py`
- [ ] Tooltip on "Tracked" KPI via `st.metric(..., help="...")`

### Phase 4 T4 — Upcoming timeline (~2.5 hr, 2 sessions)

- [ ] **T4-A** Merge `get_upcoming_deadlines(30)` + `get_upcoming_interviews()`
      into a single DataFrame keyed by date
- [ ] **T4-B** Urgency column from `config.DEADLINE_URGENT_DAYS` /
      `DEADLINE_ALERT_DAYS` (no hardcoded thresholds)
- [ ] **T4-C** Display via `st.dataframe(width="stretch")` with columns
      `(date, label, kind, urgency)`; `kind ∈ {"deadline", "interview"}`
- [ ] **T4-D** Empty state ("No deadlines or interviews in the next 30 days")

---

## Blocked / awaiting input

_(none)_

---

## Recently done

- 2026-04-22 — **v0.4.0** Phase 4 T3 Materials Readiness merged to main (`5ac0f63`)
- 2026-04-22 — **v0.3.0** Phase 4 T2 Application Funnel merged (`96a5c76`)
- 2026-04-21 — **v0.2.0** Phase 4 T1 App shell + KPI cards merged (`f49ec5f`)

For earlier completions see [`CHANGELOG.md`](CHANGELOG.md).

---

_Updated: 2026-04-24 (v1.3 alignment — Sub-tasks 1–10 shipped; Sub-task 11+ next)_
