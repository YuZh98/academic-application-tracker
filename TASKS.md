# Tasks

_Scope: software for this application tracker only. Older completions move to
`CHANGELOG.md` at the end of each sprint._

---

## Current sprint — v1.1 doc refactor

Branch: `feature/docs-refactor-pre-t4` (off `main @ 5ac0f63`)

- [x] Commit 1: DESIGN + GUIDELINES drift fixes (C1–C13)
- [x] Commit 2: DESIGN restructure + `docs/adr/` skeleton
- [x] Commit 3: GUIDELINES restructure + `docs/dev-notes/` extraction
- [ ] Commit 4: TASKS + roadmap + CHANGELOG + .gitignore ← **in progress**
- [ ] Retroactive git tags: `v0.1.0` @ `c972385` · `v0.2.0` @ `f49ec5f` ·
      `v0.3.0` @ `96a5c76` · `v0.4.0` @ `5ac0f63`
- [ ] Push branch; open PR; merge to main

---

## Up next (post doc refactor)

### Code refactor pre-T4 (new branch off main after doc refactor merges)

These are the code-only changes that the v1.1 doc refactor flagged but
deferred. All require separate approval before execution.

- [ ] **C1** `database.py compute_materials_readiness` — replace hardcoded
      `("[OPEN]", "[APPLIED]", "[INTERVIEW]")` with
      `(config.STATUS_OPEN, STATUS_APPLIED, STATUS_INTERVIEW)`
- [ ] **C2** Delete unused `TRACKER_PROFILE` from `config.py`
- [ ] **C6/C7** Config-drive schema DEFAULTs in `init_db()` DDL
      (`DEFAULT '{config.STATUS_VALUES[0]}'` / `DEFAULT '{config.RESULT_DEFAULT}'`)
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

_Updated: 2026-04-23 (v1.1 doc refactor in flight, Commit 4/4)_
