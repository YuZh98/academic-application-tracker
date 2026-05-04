# Agent Handoff — Postdoc Application Tracker

> **How to use this document:** Read it top-to-bottom before touching any
> file. It replaces the need to read every spec doc on first contact.
> The orchestrator (Claude in Zed) keeps the "Current state" and
> "Immediate task" sections up to date after each merged PR.

---

## Session bootstrap (read first)

You are the **implementer agent** taking the next task in this
project. The orchestrator session in Zed has prepared everything you
need below; your job is to ship the "Immediate task" further down
this doc.

### Pre-flight (run before writing any code)

```bash
cd <repo-root>
git fetch && git checkout main && git pull --ff-only origin main
git log --oneline -5            # confirm main HEAD matches "Current state"
source .venv/bin/activate
pytest tests/ -q                # confirm baseline matches "Current state"
git status --porcelain exports/ # standing isolation gate — must be empty
git checkout -b <branch-name-from-Immediate-task>
```

The "Immediate task" section names the branch to create. If pytest
baseline or `git status exports/` doesn't match what's recorded under
"Current state", **stop and flag it** — the tracker is out of sync
with the repo and the orchestrator needs to hear about it before you
proceed.

### First action

Pre-announce in one sentence what you are about to do, then read in
order: `AGENTS.md` "Immediate task" block · `DESIGN.md` sections
cited there · the existing implementations the spec tells you to
mirror · the relevant existing tests. Only after that do you write
any code.

### Standing user preferences (apply throughout session)

- **Pre-announce non-trivial actions** in one sentence before doing
  them — not a plan document, just a sentence.
- **Didactic over terse.** When explaining a decision (architecture
  choice, why a test fails, what a Streamlit gotcha is), give the
  *reasoning*, not just the conclusion. The user is using this
  project to learn software engineering.
- **Show recommendations as something the user can redirect**, not a
  decided plan. The user reserves merge / strategy decisions.
- **Standing instruction formula.** When the user asks for a workflow
  they want repeatedly, codify it (the orchestrator updates this doc
  to capture it durably).

### Stop boundary

Stop after the PR opens. Do **not**:
- Touch `TASKS.md` / `CHANGELOG.md` / `reviews/` / `AGENTS.md`
  "Current state" + "Immediate task" sections — orchestrator-only.
- Push directly to `main` — PRs only.
- Skip the pre-commit checklist or the standing isolation gate.

After `gh pr create`, post the PR URL back and stop. The orchestrator
reviews, merges via admin bypass, and ships the `chore:` rollup
commit on main.

### PR conventions

- **PR title format:** `<type>(<scope>): <short description ≤72 chars>`
  — e.g. `feat(phase-6-T3): write_recommenders markdown generator`.
- **PR body:** `## Summary` bullets per deliverable + `## Test plan`
  checklist (mirror of recent merged PRs: #32, #33).
- If you made a non-obvious design call (cell shape, sort key,
  divergence from spec), flag it under Summary so the orchestrator
  can sanity-check before merge.

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
exports.py             Markdown generators (T1 `write_opportunities` + T2 `write_progress` shipped; T3 `write_recommenders` pending)
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
**`main` HEAD:** Phase 6 T2 merged (PR #33); test suite at 801 passed + 1 xfailed

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

### Phase 6 — Exports (markdown generators)

| Task | Status | Notes |
|------|--------|-------|
| T1 — `write_opportunities()` generator | ✅ PR #32 | `exports/OPPORTUNITIES.md` — 8-column contract pinned by `TestWriteOpportunities`; raw bracketed status sentinels; idempotent |
| T2 — `write_progress()` generator | ✅ PR #33 | `exports/PROGRESS.md` — positions × applications × interviews; `_format_confirmation` + `_format_interviews_summary` tri-state helpers; conftest fixture lift (mandatory ride-along) closed T1 pollution |
| T3 — `write_recommenders()` generator | 🔲 next | see "Immediate task" |
| T4 — Export page (manual regenerate button + file mtimes) | 🔲 | |
| T5 — Export page (`st.download_button` per file) | 🔲 | |
| T6 — Phase 6 close-out + tag `v0.7.0` | 🔲 | |

### What's after Phase 6
Phase 7 (Polish), v1.0-rc schema cleanup, then publish scaffolding
(README, LICENSE, Streamlit Cloud deploy). Full list in `TASKS.md`
§"Up next".

---

## Immediate task — Phase 6 T3 (`write_recommenders()` exports generator)

**Spec:** `TASKS.md` current sprint Phase 6 T3 · `DESIGN §7` exports
contract (`exports/RECOMMENDERS.md` from recommenders JOIN positions)
· `exports.py` existing T1 + T2 implementations as the reference for
shape (deferred-import, idempotency, em-dash + raw-bracketed-status
conventions, `_md_escape_cell`, `_format_confirmation` precedent).

T3 ships the third of three Phase 6 generators — last one before the
Export page work (T4 + T5) and the Phase 6 close-out (T6 → tag
`v0.7.0`). Same architectural shape as T1 + T2.

### T3 — `exports.write_recommenders()` generator

- Output: `exports/RECOMMENDERS.md` (UPPERCASE per DESIGN §7 line 464
  + the existing stub docstring + the T1 / T2 precedent).
- Source: `database.get_all_recommenders()` — already returns
  recommenders × positions LEFT JOIN ordered by `recommender_name
  ASC`. No new reader needed.
- Suggested column shape (verify against DESIGN §6 recommenders
  schema; pin via `TestWriteRecommenders` tests):
  - Recommender · Relationship · Position · Institute · Asked ·
    Confirmed · Submitted · Reminder
  - "Reminder" cell folds the `(reminder_sent, reminder_sent_date)`
    pair via the SAME tri-state shape as T2's
    `_format_confirmation` — `—` / `✓ {ISO}` / `✓ (no date)`. The
    semantic is identical (a flag + an optional date), so reuse the
    helper rather than building a new one. If you'd rather a
    differently-shaped cell, document why in the test class
    docstring + flag in the PR.
  - "Confirmed" cell uses the existing tri-state `_format_confirmed`
    convention from `pages/3_Recommenders.py` (`—` / `No` / `Yes`)
    — but you'll need a local `_format_confirmed` helper here per
    the DESIGN §2 layer rule (pages and exports cannot share
    helpers). Mirror semantics, ISO over Mon D where applicable.
- Sort order: `recommender_name ASC, deadline_date ASC NULLS LAST,
  id ASC`. The first key groups all of one person's owed letters
  together; the secondary keys order multiple positions for the
  same recommender by deadline. Re-apply via
  `pandas.sort_values(... kind="stable")` to defend against
  upstream SQL changes.
- Cell shapes — **mirror T1 + T2 conventions**:
  - `_safe_str_or_em` for missing TEXT cells.
  - Date cells pass-through ISO TEXT.
  - `_md_escape_cell` on every cell.
  - No status sentinel here — recommenders don't carry pipeline
    status — but if you surface anything ALL-CAPS-bracketed (e.g. a
    relationship enum), keep it raw per the backup-vs-UI rationale
    cited in T1 review Q1.
- Idempotency: pinned by `test_idempotent_across_two_calls`. Two
  calls with no DB change → byte-identical output.

### Architecture rules (non-negotiable — DESIGN §7)
- `exports.py` imports `database` + `config`; **NEVER** `streamlit`.
- Deferred `database` import inside `write_recommenders` body
  (mirror of T1 / T2) breaks the `database → exports → database`
  circular import.
- `EXPORTS_DIR.mkdir(exist_ok=True)` inside the function body
  (mirror of T1 / T2).

### Tests to write first (TDD red commit)
- Reuse the lifted `db_and_exports` wrapper from T2.
- `TestWriteRecommenders` class with:
  - `test_writes_file_at_expected_path` — `exports/RECOMMENDERS.md`
    exists.
  - `test_table_header_matches_contract` — locked column header.
  - `test_one_row_per_recommender_position_pair` — a recommender
    owing letters for N positions surfaces as N rows in the table
    (mirror of `get_all_recommenders` row shape).
  - `test_sort_order_groups_by_recommender_then_deadline` — two
    recommenders with overlapping positions render with all of
    person A's rows before any of person B's; within each
    recommender, rows order by deadline ASC NULLS LAST.
  - `test_em_dash_for_missing_text_cells` — NULL relationship /
    notes / etc. → `—`.
  - `test_iso_format_for_date_cells` — Asked / Submitted columns
    render as `YYYY-MM-DD`.
  - `test_idempotent_across_two_calls` — byte-identical output.
  - `test_empty_db_writes_header_only` — header + separator only on
    empty DB.
  - `test_confirmed_tri_state_<...>` — Confirmed cell renders the
    locked tri-state pattern (`—` / `No` / `Yes`).
  - `test_reminder_<...>` — Reminder cell renders the locked
    tri-state pattern (`—` / `✓ {ISO}` / `✓ (no date)`).

### TDD cadence
Standard three-commit triplet — `test:` → `feat:` → `chore:` (the
`chore:` is the orchestrator's).

### Pre-PR gates (GUIDELINES §11 + T2 isolation gate, now standing)
```bash
ruff check .
pytest tests/ -q
pytest -W error::DeprecationWarning tests/ -q
grep -rn '\[SAVED\]\|\[APPLIED\]\|\[INTERVIEW\]' app.py pages/ \
  | grep -v '^\([^:]*\):[0-9]*:\s*#'

# T2 isolation gate is permanent now — must stay empty.
git status --porcelain exports/
```

### Branch + cadence
- Branch name: `feature/phase-6-tier3-WriteRecommenders`.
- One PR for the test + feat commits; orchestrator handles the
  chore rollup post-merge.

---

## TDD cadence (mandatory — GUIDELINES §11)

```
1. test: commit  → add failing tests to tests/test_exports.py
                   (write_recommenders not implemented yet → RED)
2. feat: commit  → implement write_recommenders() in exports.py (GREEN)
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
# T2 isolation gate (standing — added 2026-05-04 with PR #33):
git status --porcelain exports/                 # must be empty post-pytest
```

---

## Coordination protocol

| Action | Who does it |
|--------|-------------|
| Write code, write tests | You (this agent) |
| Open PR | You — branch name: `feature/phase-6-tier3-WriteRecommenders` |
| Review + merge PR | Orchestrator (Claude in Zed) |
| Update TASKS.md, CHANGELOG.md, reviews/ | Orchestrator only |
| Push directly to `main` | Nobody — PRs only |

**If you're unsure about a design decision:** check `DESIGN.md §7` (exports contract) first for Phase 6 work; see DESIGN §8 for the per-page UI contracts.
If it's not there, leave a comment in the code and note it in the PR
description — the orchestrator will resolve it before merging.
