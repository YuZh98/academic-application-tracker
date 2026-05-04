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

### CI-mirror local check (before opening / re-pushing a PR)

The developer's `postdoc.db` (real user DB, ~50 KB at project root)
is a fall-through target for any test that uses
`database.get_*` without monkeypatching `database.DB_PATH`. CI
runners have no `postdoc.db`, so a missing-DB-init regression
surfaces ONLY on CI — locally it passes silently against your real
data.

Run the suite with `postdoc.db` moved aside before pushing the PR:

```bash
mv postdoc.db postdoc.db.bak
pytest tests/ -q
mv postdoc.db.bak postdoc.db
```

If pytest fails in this CI-mirror env but passes in your normal
local env, you have a fixture gap — a test is reading the real DB
unintentionally. Fix it by adding the conftest `db` fixture parameter
(or `db_and_exports` for export-content tests) so the suite is
self-contained. **Do not push a PR that passes locally but fails
this CI-mirror check** — main will go red, the orchestrator catches
it on PR review, and the fix lands as an urgent commit on top of an
in-flight tier.

This rule was added 2026-05-04 after PRs #32–#34 hit the same gap
on three smoke tests in `tests/test_exports.py` — the orchestrator's
post-mortem is in `ORCHESTRATOR_HANDOFF.md` "CI must be green before
admin-bypass".

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
  — e.g. `feat(phase-6-T4): Export page shell + manual regenerate button`.
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
exports.py             Markdown generators (T1 + T2 + T3 all shipped; Phase 6 generator group complete)
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
  test_recommenders_page.py   Phase 5 tests complete
  test_export_page.py    Phase 6 T4 + T5 work creates this file (AppTest-driven)
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
**`main` HEAD:** Phase 6 T3 merged (PR #34); test suite at 815 passed + 1 xfailed

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
| T3 — `write_recommenders()` generator | ✅ PR #34 | `exports/RECOMMENDERS.md` — 8-column contract; new local `_format_confirmed` (`—`/`No`/`Yes`); Reminder cell reuses `_format_confirmation`; `notes` deliberately omitted; smoke-test `fix:` commit augmented `isolated_exports_dir` to also monkeypatch DB_PATH (closed CI-red regression that had been latent since T1) |
| T4 — Export page (manual regenerate button + file mtimes) | 🔲 next | see "Immediate task" |
| T5 — Export page (`st.download_button` per file) | 🔲 | after T4 |
| T6 — Phase 6 close-out + tag `v0.7.0` | 🔲 | after T5 |

### What's after Phase 6
Phase 7 (Polish), v1.0-rc schema cleanup, then publish scaffolding
(README, LICENSE, Streamlit Cloud deploy). Full list in `TASKS.md`
§"Up next".

---

## Immediate task — Phase 6 T4 (`pages/4_Export.py` — Export page shell + manual regenerate button + file mtimes)

**Spec:** `TASKS.md` current sprint Phase 6 T4 · `DESIGN §8.5`
(Export page) · `docs/ui/wireframes.md#export` (ASCII layout: title
+ intro line + `[ Regenerate all markdown files ]` button + per-file
"Last generated: <file mtime>" lines, with download buttons added in
T5) · existing `exports.py` (`write_all`, `write_opportunities`,
`write_progress`, `write_recommenders` all shipped) and DESIGN §7
contract #1 ("log-and-continue on failure") for the manual-trigger
error semantics.

T4 ships the Export page shell + the manual-regenerate button +
per-file mtimes display. **T5 adds the `st.download_button` per file
on top of this shell.** Keep T4 scoped to "Regenerate + show mtimes";
download buttons land separately so each tier stays one PR.

### T4 — `pages/4_Export.py`

- Create the file. Mirror the page-shell pattern of
  `pages/2_Applications.py` / `pages/3_Recommenders.py`:
  - `st.set_page_config(page_title="Postdoc Tracker",
    page_icon="📋", layout="wide")` as first executable statement
    (DESIGN §8.0 + D14).
  - `database.init_db()` — same idempotent-init pattern every page
    runs.
  - `st.title("Export")`.
  - One-line intro under the title per the wireframe: "Markdown
    files are auto-exported after every data change. Use this page
    to trigger a manual export or download files."
- **Regenerate button** (`st.button("Regenerate all markdown files",
  key="export_regenerate", type="primary")`):
  - Calls `exports.write_all()`. Per DESIGN §7 contract #1, that
    function logs-and-continues on individual writer failure (already
    done in `exports.py` — no changes needed there).
  - Success path: `st.toast("Markdown files regenerated.")`.
  - Failure path: `exports.write_all()` doesn't propagate per-writer
    exceptions, so the button itself shouldn't see one. But the
    `EXPORTS_DIR.mkdir` call inside `write_all` CAN raise
    (permissions, disk full); wrap the whole `write_all()` call in
    `try / except Exception as e: st.error(f"Could not regenerate:
    {e}")` per GUIDELINES §8 (friendly error, no re-raise).
- **File mtimes panel** below the regenerate button:
  - For each of `OPPORTUNITIES.md`, `PROGRESS.md`, `RECOMMENDERS.md`:
    - Compute `(exports.EXPORTS_DIR / filename).stat().st_mtime`
      converted to a human-readable timestamp via
      `datetime.fromtimestamp(...).strftime("%Y-%m-%d %H:%M:%S")`.
    - Render: `st.write(f"**{filename}** — last generated:
      {timestamp}")` (or `st.markdown(...)` per the
      wireframe-equivalent shape; pick whichever reads cleaner with
      the rest of the page).
  - **Missing-file branch:** if a file doesn't exist yet (fresh DB,
    user hasn't triggered the regen), render `st.write(f"**{filename}**
    — not yet generated")`. Catch `FileNotFoundError` (or check
    `Path.exists()` first — both are idiomatic, pick one).
  - The mtimes block is read-only — no widgets, just text. `st.rerun()`
    after the regenerate-button success refreshes them.

### Architecture rules (non-negotiable)
- `pages/4_Export.py` imports `database`, `config`, `exports`,
  `streamlit`, `datetime`, `pathlib`. **NEVER** imports `pages/`
  modules (no cross-page imports per DESIGN §2 layer rules).
- Widget keys use the `export_` prefix (the
  Coordination-protocol-pinned page prefix). Today T4 has only
  `export_regenerate`; T5 will add `export_download_<filename>`.

### Tests to write first (TDD red commit)
- New test file `tests/test_export_page.py`. Mirror the
  AppTest-driven pattern in `test_applications_page.py` /
  `test_recommenders_page.py`.
- `TestExportPageShell` class:
  - `test_page_runs_without_exception_on_empty_db` — AppTest renders
    the page on an empty (init'd) DB; `at.exception` is empty.
  - `test_page_title_is_export` — `at.title[0].value == "Export"`.
  - `test_intro_line_present` — verifies the wireframe-pinned intro.
  - `test_regenerate_button_renders` — `at.button(key="export_
    regenerate")` exists, label matches the wireframe.
- `TestExportPageRegenerateButton` class:
  - `test_click_calls_write_all` — monkeypatch `exports.write_all`
    to a tracking lambda; click the button; assert it was called
    once.
  - `test_click_emits_toast_on_success` — click; assert
    `at.toast[0].value` matches the locked-copy success toast.
  - `test_click_emits_error_on_write_all_failure` — monkeypatch
    `exports.write_all` to raise `OSError("simulated")`; click;
    assert `at.error[0].value` includes the error message and the
    button is still rendered (no re-raise).
- `TestExportPageMtimesPanel` class:
  - `test_mtimes_show_not_yet_generated_when_files_absent` — fresh
    DB, no files in `EXPORTS_DIR`; rendered text contains
    `"OPPORTUNITIES.md"` + `"not yet generated"` for each of the
    three filenames.
  - `test_mtimes_show_timestamps_when_files_present` — pre-create
    each of the three files (touch + set mtime); assert rendered
    text includes the expected `YYYY-MM-DD HH:MM:SS` formatted
    string for each.
  - `test_regenerate_then_mtimes_update` — click regenerate; the
    rerendered mtimes panel shows non-"not yet generated" timestamps
    for all three files (cohesion-of-state across the rerun).

### Architecture rules (non-negotiable — DESIGN §2 + §7)
- `pages/4_Export.py` imports `streamlit` (UI surface).
- `database.init_db()` runs at top of every page.

### Pre-PR gates (GUIDELINES §11 + standing isolation gate)
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
- Branch name: `feature/phase-6-tier4-ExportPage`.
- One PR for the test + feat commits; orchestrator handles the
  chore rollup post-merge.

---

## TDD cadence (mandatory — GUIDELINES §11)

```
1. test: commit  → add failing tests to tests/test_export_page.py
                   (Export page not implemented yet → RED)
2. feat: commit  → implement pages/4_Export.py (GREEN)
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
| Open PR | You — branch name: `feature/phase-6-tier4-ExportPage` |
| Review + merge PR | Orchestrator (Claude in Zed) |
| Update TASKS.md, CHANGELOG.md, reviews/ | Orchestrator only |
| Push directly to `main` | Nobody — PRs only |

**If you're unsure about a design decision:** check `DESIGN.md §7` (exports contract) first for Phase 6 work; see DESIGN §8 for the per-page UI contracts.
If it's not there, leave a comment in the code and note it in the PR
description — the orchestrator will resolve it before merging.
