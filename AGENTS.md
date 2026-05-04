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
  3_Recommenders.py    Recommenders page (Phase 5 closed at v0.6.0)
tests/
  conftest.py          Shared fixtures — `db` (temp SQLite) and `make_position()`
  test_database.py     Unit tests for database.py
  test_app_page.py     Integration tests for app.py (AppTest)
  test_applications_page.py
  test_recommenders_page.py   Phase 5 tests complete; Phase 6 work touches test_exports.py
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

**Latest tag:** `v0.6.0` (Phase 5 complete — Applications + Recommenders pages)
**`main` HEAD:** Phase 5 closed; test suite at 777 passed + 1 xfailed; next functional work is Phase 6 T1

### Phase 5 — Applications + Recommenders pages ✅ closed at `v0.6.0`

| Task | Status | Notes |
|------|--------|-------|
| T1 — Applications page shell + table | ✅ PR #15 | |
| T2 — Application detail card + cascade toast | ✅ PR #16 | |
| T3 — Inline interview list UI | ✅ PR #19 | |
| T4 — Recommenders page shell + Pending Alerts panel | ✅ PR #28 | `pages/3_Recommenders.py` created |
| T5 — Recommenders table + add form + inline edit | ✅ PR #29 | All-Recommenders + filters + Add form + inline edit + dialog Delete |
| T6 — Reminder helpers (mailto + LLM prompts) | ✅ PR #31 | Compose mailto link button + LLM prompts (2 tones) expander per Pending Alerts card |
| T7 — Phase 5 close-out + tag `v0.6.0` | ✅ | Cohesion-smoke at [`reviews/phase-5-finish-cohesion-smoke.md`](reviews/phase-5-finish-cohesion-smoke.md); CHANGELOG `[v0.6.0]` split |

### What's after Phase 5
Phase 6 (Exports — markdown generators), Phase 7 (Polish),
v1.0-rc schema cleanup, then publish scaffolding (README, LICENSE,
Streamlit Cloud deploy). Full list in `TASKS.md` §"Up next".

---

## Immediate task — Phase 6 T1 (`write_opportunities()` exports generator)

**Spec:** `TASKS.md` current sprint Phase 6 T1 · `DESIGN §7` exports
contract (markdown generators, log-and-continue inside every
`database.py` writer, deferred-import to break circular import) ·
existing `exports.py` stub for the function signature

Phase 6 ships markdown export generators per **Q6 Option A** (plain
markdown tables). T1 is the first of three generators (T1
opportunities · T2 progress · T3 recommenders) plus an Export page
(T4 + T5) and a phase close-out (T6 → tag `v0.7.0`).

### T1 — `exports.write_opportunities()` generator
- Implement `exports.write_opportunities(conn=None)` returning the
  written file path (or whatever the existing stub signature pins —
  read `exports.py` first).
- Output: a single markdown file at `exports/opportunities.md` with
  one table row per row of `database.get_all_positions()` (or the
  joined frame the dashboard's Opportunities page uses — pick to
  match DESIGN §7 if the contract is explicit there).
- Column contract: read DESIGN §7 / wireframes — typically
  Position · Institute · Field · Deadline · Priority · Status (per
  the Opportunities-page table) plus any audit columns the spec
  calls for (created_at / updated_at).
- Sort order: deadline ASC NULLS LAST, position_id ASC (mirrors the
  upstream stable-tiebreaker invariant — see
  `database.get_applications_table` precedent).
- NaN / NULL handling: em-dash `—` for missing TEXT cells, ISO date
  for date cells (markdown tables aren't a working surface — ISO is
  unambiguous + sortable when grep'd).

### Architecture rules (non-negotiable — DESIGN §7)
- `exports.py` imports `database` and `config`; **NEVER** imports
  `streamlit`.
- Every `database.py` write function calls `exports.write_all()` via
  **deferred import** (the writer's first line of side-effect work
  imports `exports` inside the function body) to break the circular
  import. T1 doesn't add new wiring — `write_all()` stub already
  delegates; just implement the underlying `write_opportunities`.
- Wrap the file write in a try/except so a failure in exports
  doesn't kill the database write — log-and-continue per DESIGN §7
  contract #1.

### Tests to write first (TDD red commit)
- `tests/test_exports.py` already exists; extend it. Test class
  `TestWriteOpportunities`:
  - `test_writes_file_at_expected_path` — call writer, assert file
    exists at `exports/opportunities.md` (use `tmp_path` fixture).
  - `test_table_header_matches_contract` — read file, assert first
    table row is the locked column header.
  - `test_one_row_per_position` — seed N positions, assert N data
    rows in the markdown table.
  - `test_sort_order_by_deadline_asc_nulls_last` — seed 3 positions
    with mixed deadlines (one NULL, two distinct dates), assert
    rendered order.
  - `test_em_dash_for_missing_text_cells` — seed a position with
    NULL field, assert the rendered cell is `—`.
  - `test_iso_format_for_date_cells` — assert deadline column
    renders as `YYYY-MM-DD`.

### TDD cadence
Standard three-commit triplet — `test:` → `feat:` → `chore:` (the
`chore:` is the orchestrator's, not yours).

### Pre-PR gates (GUIDELINES §11)
```bash
ruff check .
pytest tests/ -q
pytest -W error::DeprecationWarning tests/ -q
grep -rn '\[SAVED\]\|\[APPLIED\]\|\[INTERVIEW\]' app.py pages/ \
  | grep -v '^\([^:]*\):[0-9]*:\s*#'
```

### Branch + cadence
- Branch name: `feature/phase-6-tier1-WriteOpportunities`.
- One PR for the test + feat commits; orchestrator handles the
  chore rollup post-merge.

---

## TDD cadence (mandatory — GUIDELINES §11)

```
1. test: commit  → add failing tests to tests/test_exports.py
                   (writer not implemented yet → RED)
2. feat: commit  → implement write_opportunities() in exports.py (GREEN)
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
| Open PR | You — branch name: `feature/phase-6-tier1-WriteOpportunities` |
| Review + merge PR | Orchestrator (Claude in Zed) |
| Update TASKS.md, CHANGELOG.md, reviews/ | Orchestrator only |
| Push directly to `main` | Nobody — PRs only |

**If you're unsure about a design decision:** check `DESIGN.md §7` (exports contract) first for Phase 6 work; see DESIGN §8 for the per-page UI contracts.
If it's not there, leave a comment in the code and note it in the PR
description — the orchestrator will resolve it before merging.
