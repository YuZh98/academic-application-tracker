# Agent Handoff — Postdoc Application Tracker

> **How to use this document:** Read it top-to-bottom before touching any
> file. It replaces the need to read every spec doc on first contact.
> The orchestrator (Claude in Zed) keeps the "Current state" and
> "Immediate task" sections up to date after each merged PR.

---

## What this project is

A local, single-user Streamlit web app that answers one daily question for
a postdoc job applicant: **"What do I do today?"** It tracks positions,
applications, interviews, and recommendation letters across institutions
with automated deadline alerts and markdown exports as portable backups.

**Stack:** Python 3.14 · Streamlit 1.57 · SQLite (`postdoc.db`) ·
pandas · Plotly · pytest · ruff

**Run it:** `source .venv/bin/activate && streamlit run app.py`
**Test it:** `pytest tests/ -q`
**Lint it:** `ruff check .`

---

## Repository layout (files you'll actually touch)

```
config.py              Constants only — statuses, thresholds, vocabularies
database.py            All SQL reads/writes; calls exports.write_all() after every write
exports.py             Markdown generators (Phase 6 stubs for now)
app.py                 Dashboard home page (Phase 4, complete)
pages/
  1_Opportunities.py   Position CRUD (Phase 3, complete)
  2_Applications.py    Application tracking (Phase 5 T1-T3, complete)
  3_Recommenders.py    Recommenders page (Phase 5 T4–T6 done; T7 close-out pending)
tests/
  conftest.py          Shared fixtures — `db` (temp SQLite) and `make_position()`
  test_database.py     Unit tests for database.py
  test_app_page.py     Integration tests for app.py (AppTest)
  test_applications_page.py
  test_recommenders_page.py   T4 + T5 + T6 tests done; T7 is close-out / no new tests
  test_opportunities_page.py
  test_exports.py
DESIGN.md              Authoritative spec — read §8.4 for Recommenders page contract
GUIDELINES.md          All coding conventions — READ THIS BEFORE WRITING CODE
TASKS.md               Sprint tracker — current task checkboxes live here
```

**Never touch:** `postdoc.db` · `exports/` · `CHANGELOG.md` ·
`TASKS.md` · `reviews/` · `CLAUDE.md`
(those are orchestrator-only; see "Coordination" below)

---

## Architecture rules (non-negotiable)

```
config.py   ← imports nothing from this project
database.py ← imports config only; NEVER imports streamlit
exports.py  ← imports database, config; NEVER imports streamlit
pages/*.py  ← imports database, config; NEVER imports exports
```

- **No raw SQL in page files.** All reads/writes go through `database.py`.
- **No `st.*` in `database.py`.** The DB layer must stay framework-agnostic.
- **Every `database.py` write function** must end with `exports.write_all()`
  called via deferred import (see existing write functions for the pattern).
- **Widget keys** use page-scoped prefixes:
  `qa_` (quick-add) · `edit_` (edit panel) · `apps_` (Applications page) ·
  `recs_` (Recommenders page) · `filter_` (filter bars) · `export_` (Export page)
- **Form ids** end with `_form`. Forms never contain `st.button` — use
  `st.form_submit_button` inside and `st.button` outside.
- **NaN coercion:** use `_safe_str(v)` before feeding DB values into widgets.
  Never use `r[col] or ""` — NaN is truthy.
- **Confirmations:** `st.toast`, not `st.success`.
  **Irreversible actions:** `@st.dialog` confirm gate.
- **Errors in save/delete handlers:** `st.error(str(e))`, never re-raise.
- **Type hints on all public functions.** Annotate `iterrows()` cells as `Any`.

---

## Current state (updated after each merged PR)

**Latest tag:** `v0.5.0` (Phase 4 complete — dashboard)
**`main` HEAD:** Phase 5 T6 merged (PR #31); test suite at 777 passed + 1 xfailed

### Phase 5 — Applications + Recommenders pages

| Task | Status | Notes |
|------|--------|-------|
| T1 — Applications page shell + table | ✅ PR #15 | |
| T2 — Application detail card + cascade toast | ✅ PR #16 | |
| T3 — Inline interview list UI | ✅ PR #19 | |
| T4 — Recommenders page shell + Pending Alerts panel | ✅ PR #28 | `pages/3_Recommenders.py` created |
| T5 — Recommenders table + add form + inline edit | ✅ PR #29 | All-Recommenders + filters + Add form + inline edit + dialog Delete |
| T6 — Reminder helpers (mailto + LLM prompts) | ✅ PR #31 | Compose mailto link button + LLM prompts (2 tones) expander per Pending Alerts card |
| T7 — Phase 5 review + PR + tag `v0.6.0` | 🔲 next | see "Immediate task" |

### What's after Phase 5
Phase 6 (Exports — markdown generators), Phase 7 (Polish),
v1.0-rc schema cleanup, then publish scaffolding (README, LICENSE,
Streamlit Cloud deploy). Full list in `TASKS.md` §"Up next".

---

## Immediate task — Phase 5 T7 (close-out + tag `v0.6.0`)

**Spec:** `TASKS.md` current sprint T7 entry · `GUIDELINES §11` (version
scheme: each minor bump marks one completed phase) · prior precedent
`reviews/phase-4-finish-cohesion-smoke.md` + the Phase 4 close-out
pattern documented in `TASKS.md` "Prior sprint — Phase 4 finish"

T7 closes Phase 5. No new feature code. Three deliverables:

### T7-A — Phase 5 cohesion sweep (audit doc)
Mirror of `reviews/phase-4-finish-cohesion-smoke.md`. Survey the
six pages of Phase 5 surface (`pages/2_Applications.py`,
`pages/3_Recommenders.py`) plus their existing test files end-to-end
under both populated and empty DB seeds; capture verbatim AppTest
renders or screenshots. Six cohesion dimensions:
1. Status / pipeline labels — every UI surface uses
   `STATUS_LABELS.get(v, v)`; no leaked bracketed sentinels (the
   GUIDELINES §11 status-literal grep is the gate).
2. Empty-state copy — every panel that can be empty has an
   explicit `st.info(...)` / equivalent (no silent rendering).
3. Date formatting — `Mon D` short form on Pending Alerts, ISO on
   tables; em-dash for NULL.
4. Toast / error wording — `st.toast` for confirmations,
   `st.error(str(e))` for handler failures; no `st.success`; no
   re-raises in save / delete handlers.
5. NaN coercion — every page uses `_safe_str` / `_safe_str_or_em`
   on TEXT cells; no `r[col] or ""` idiom (gotcha #1).
6. Widget-key prefixes — `apps_` on Applications page, `recs_` on
   Recommenders page; no cross-prefix bleed.

Output: `reviews/phase-5-finish-cohesion-smoke.md` per the §14.1
header schema. Verdict format: 🔴 (block) / 🟠 (must-fix pre-tag) /
🟡 (nice-to-fix) / 🟢 (defer) per `GUIDELINES §10`.

### T7-B — Phase 5 close-out review
Tier-style review doc at `reviews/phase-5-finish-review.md` (or fold
into the cohesion smoke per the Phase 4 precedent — re-read
`reviews/phase-4-finish-cohesion-smoke.md` for which approach fit
that close-out). Structured findings list aggregating any open
carry-overs from `phase-5-tier1` … `phase-5-tier6` reviews. Closes
out: which carry-overs survive past v0.6.0 (logged in TASKS.md
"Up next" / "Code carry-overs"); which were resolved during Phase 5;
which want addressing as 🟠 hold-the-tag fixes.

Existing carry-overs to triage:
- **C2** — `TRACKER_PROFILE` removal (deferred from v1.1)
- **C3** — `"All"` filter sentinel → `config.py` (logged in
  `phase-5-tier1-review.md` Finding 1; extended through T5 + T6)
- **C4** — `CHANGELOG.md` `[Unreleased]` → `[v0.5.0]` split
  (logged in `phase-5-tier1-review.md` Finding 3 — already
  partially done; verify the `v0.5.0` section is in place)
- Phase 7 polish candidates from T5 + T6 reviews
  (Save-toast-when-no-dirty wording, subject-pluralization on N=1
  Compose body)

### T7-C — Tag `v0.6.0` + CHANGELOG version-block split
- Final pre-merge gates run end-to-end (the four GUIDELINES §11
  checks).
- `CHANGELOG.md`: split `[Unreleased]` → `[v0.6.0]` at the
  T6-merge boundary commit `6993ea9`, mirroring the precedent
  documented in `[v0.5.0]` (commit `db383e3`).
- `git tag -a v0.6.0 -m "Phase 5 — Applications + Recommenders pages"`
  with annotation listing the headline T1-T6 deliverables.
- Push tag.

### Pre-PR gates (GUIDELINES §11) — run before tagging
```bash
ruff check .
pytest tests/ -q
pytest -W error::DeprecationWarning tests/ -q
grep -rn '\[SAVED\]\|\[APPLIED\]\|\[INTERVIEW\]' app.py pages/ \
  | grep -v '^\([^:]*\):[0-9]*:\s*#'
```

### Branch + cadence
- Branch name: `feature/phase-5-tier7-Phase5Closeout` (or
  `chore/phase-5-finish` per the Phase 4 precedent — implementer
  picks per project naming convention).
- T7 is doc-only; no `feat:` commit. Cadence: one `docs:` or
  `chore:` commit per deliverable (cohesion smoke, close-out
  review, CHANGELOG split). Tag annotation written by orchestrator.

---

## TDD cadence (mandatory — GUIDELINES §11)

```
1. (T7 is doc-only — no test: / feat: commits)
2. docs: / chore: commit per deliverable (cohesion smoke, close-out
                   review, CHANGELOG split)
3. chore: commit → orchestrator handles TASKS.md/CHANGELOG/review doc
                   (YOU do not touch these)
```

**Commit message format:**
```
<type>(<scope>): <short description ≤72 chars>

<optional body>
```
Types: `feat` · `fix` · `test` · `chore` · `docs` · `refactor`

---

## Pre-commit checklist (run before opening PR)

```bash
ruff check .                                    # must be clean
pytest tests/ -q                                # all pass (+ 1 xfail OK)
pytest -W error::DeprecationWarning tests/ -q   # same
# status-literal grep (must return 0 lines):
grep -rn '\[SAVED\]\|\[APPLIED\]\|\[INTERVIEW\]' app.py pages/ \
  | grep -v '^\([^:]*\):[0-9]*:\s*#'
```

---

## Coordination protocol

| Action | Who does it |
|--------|-------------|
| Write code, write tests | You (this agent) |
| Open PR | You — branch name: `feature/phase-5-tier7-Phase5Closeout` |
| Review + merge PR | Orchestrator (Claude in Zed) |
| Update TASKS.md, CHANGELOG.md, reviews/ | Orchestrator only |
| Push directly to `main` | Nobody — PRs only |

**If you're unsure about a design decision:** check `DESIGN.md §8.4` first.
If it's not there, leave a comment in the code and note it in the PR
description — the orchestrator will resolve it before merging.
