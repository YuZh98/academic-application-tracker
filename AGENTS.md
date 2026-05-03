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
  3_Recommenders.py    Recommenders page (Phase 5 T4 done; T5-T6 pending)
tests/
  conftest.py          Shared fixtures — `db` (temp SQLite) and `make_position()`
  test_database.py     Unit tests for database.py
  test_app_page.py     Integration tests for app.py (AppTest)
  test_applications_page.py
  test_recommenders_page.py   T4 tests done; T5-T6 tests to be added here
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
**`main` HEAD:** Phase 5 T4 merged (PR #28); test suite at 700 passed + 1 xfailed

### Phase 5 — Applications + Recommenders pages

| Task | Status | Notes |
|------|--------|-------|
| T1 — Applications page shell + table | ✅ PR #15 | |
| T2 — Application detail card + cascade toast | ✅ PR #16 | |
| T3 — Inline interview list UI | ✅ PR #19 | |
| T4 — Recommenders page shell + Pending Alerts panel | ✅ PR #28 | `pages/3_Recommenders.py` created |
| T5 — Recommenders table + add form + inline edit | 🔲 next | see "Immediate task" |
| T6 — Reminder helpers (mailto + LLM prompts) | 🔲 | after T5 |
| T7 — Phase 5 review + PR + tag `v0.6.0` | 🔲 | |

### What's after Phase 5
Phase 6 (Exports — markdown generators), Phase 7 (Polish),
v1.0-rc schema cleanup, then publish scaffolding (README, LICENSE,
Streamlit Cloud deploy). Full list in `TASKS.md` §"Up next".

---

## Immediate task — Phase 5 T5

**Spec:** `DESIGN.md §8.4` · `TASKS.md` current sprint T5 entry

T5 adds the "All Recommenders" section below the existing Pending Alerts
panel in `pages/3_Recommenders.py`. Three sub-areas:

### T5-A — Table display + filters
- Read-only `st.dataframe` of all recommenders joined with position name
- Two filter selectboxes: filter by position (key `recs_filter_position`),
  filter by recommender name (key `recs_filter_recommender`)
- Use `database.get_all_recommenders()` — already exists, returns
  `r.*, p.position_name, p.institute` ordered by `r.recommender_name ASC`
- Columns to display: Position · Recommender · Relationship · Asked · Confirmed · Submitted

### T5-B — Add recommender form
- `st.form("recs_add_form")` with:
  - Position selectbox (key `recs_add_position`): options from
    `get_all_positions()`, display `"{institute}: {position_name}"` or
    bare `position_name`, value is `position_id`
  - Recommender name text input (key `recs_add_name`)
  - Relationship selectbox (key `recs_add_relationship`):
    options from `config.RELATIONSHIP_VALUES` (check config.py — add
    the constant if it doesn't exist yet)
  - Asked date date_input (key `recs_add_asked_date`)
- On submit: `database.add_recommender(position_id, fields)`;
  success → `st.toast(f'Added {name}.')`;
  failure → `st.error(str(e))`

### T5-C — Row selection + inline edit
- `on_select="rerun"` + `selection_mode="single-row"` on the table
  (key `recs_table`)
- Session-state sentinel: `recs_selected_id`, `_recs_edit_form_sid`
  (mirrors Opportunities page `_edit_form_sid` pattern — DESIGN §8.2)
- Inline edit card (`st.container(border=True)`) below the table when
  a row is selected, with `st.form("recs_edit_form")`:
  - Editable: `asked_date`, `confirmed` (selectbox: None/0/1 rendered
    as `—`/`No`/`Yes`), `submitted_date`, `reminder_sent` checkbox +
    `reminder_sent_date`, `notes`
  - Save: `database.update_recommender(rec_id, dirty_fields_only)`;
    toast on success; `st.error` on failure
  - Delete: `st.button` outside the form → `@st.dialog` confirm →
    `database.delete_recommender(rec_id)`

---

## TDD cadence (mandatory — GUIDELINES §11)

```
1. test: commit  → add failing tests to tests/test_recommenders_page.py
                   (page doesn't implement T5 yet → RED)
2. feat: commit  → implement T5 in pages/3_Recommenders.py (GREEN)
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
| Open PR | You — branch name: `feature/phase-5-tier5-RecommendersTableAddEdit` |
| Review + merge PR | Orchestrator (Claude in Zed) |
| Update TASKS.md, CHANGELOG.md, reviews/ | Orchestrator only |
| Push directly to `main` | Nobody — PRs only |

**If you're unsure about a design decision:** check `DESIGN.md §8.4` first.
If it's not there, leave a comment in the code and note it in the PR
description — the orchestrator will resolve it before merging.
