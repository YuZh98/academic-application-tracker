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
- [ ] Sub-task 5+: remaining v1.3 alignment items per
      `memory/project_state.md` (status rename `[OPEN]→[SAVED]` +
      one-shot UPDATE migration, `"Med"→"Medium"`, schema overhauls
      incl. `work_auth_note`, interviews sub-table, cascade rewire)
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

- [ ] **C1** `database.py compute_materials_readiness` — replace hardcoded
      `("[OPEN]", "[APPLIED]", "[INTERVIEW]")` with
      `(config.STATUS_OPEN, STATUS_APPLIED, STATUS_INTERVIEW)`
- [ ] **C2** Delete unused `TRACKER_PROFILE` from `config.py`
- [x] **C6/C7** Config-drive schema DEFAULTs in `init_db()` DDL
      (`DEFAULT '{config.STATUS_VALUES[0]}'` / `DEFAULT '{config.RESULT_DEFAULT}'`)
      — shipped as v1.3 alignment Sub-task 4
- [ ] **C12** Add `assert DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS` to `config.py`
- [ ] Rename `[OPEN]` → `[SAVED]` + idempotent `UPDATE positions SET status=...` migration
- [ ] Rename `PRIORITY_VALUES` `"Med"` → `"Medium"` + migration
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

_Updated: 2026-04-24 (v1.3 alignment — Sub-tasks 1–4 shipped; Sub-task 5+ next)_
