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
cd /Users/zhengyu/Desktop/Claude/Project/Postdoc
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
  — e.g. `feat(phase-6-T5): Export page download buttons`.
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
**`main` HEAD:** Phase 6 T4 merged (PR #35); test suite at 827 passed + 1 xfailed

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
| T4 — Export page (manual regenerate button + file mtimes) | ✅ PR #35 | `pages/4_Export.py` shell + regenerate button (try/except `write_all`, success toast, friendly `st.error`) + per-file mtimes panel (`st.markdown` lines, `Path.exists()` check + `os.utime`-deterministic test) |
| T5 — Export page (`st.download_button` per file) | 🔲 next | see "Immediate task" |
| T6 — Phase 6 close-out + tag `v0.7.0` | 🔲 | after T5 |

### What's after Phase 6
Phase 7 (Polish), v1.0-rc schema cleanup, then publish scaffolding
(README, LICENSE, Streamlit Cloud deploy). Full list in `TASKS.md`
§"Up next".

---

## Immediate task — Phase 6 T5 (Export page — `st.download_button` per file + "── Download ───" wireframe section header)

**Spec:** `TASKS.md` current sprint Phase 6 T5 · `DESIGN §8.5`
(Export page) · `docs/ui/wireframes.md#export` (ASCII layout pins
the "── Download ───" section header above three `[ ⬇ FILENAME.md ]`
buttons next to their `Last generated: <file mtime>` lines) ·
existing `pages/4_Export.py` shipped in T4 (page shell + regenerate
button + mtimes panel — extend, don't rewrite) · DESIGN §7 (exports
contract).

T5 adds three `st.download_button` widgets to the existing T4
Export-page shell, alongside the wireframe-pinned "── Download ───"
section header that T4 deliberately omitted. Mechanical extension
on top of T4.

### T5 — extend `pages/4_Export.py` with download buttons

- **Section header:** render `"── Download ───"` (or whatever the
  wireframe shape resolves to once you read it — verify against
  `docs/ui/wireframes.md#export` line 176) ABOVE the three
  download-button + mtime rows. Implementer's call: keep the rule
  prose-as-markdown (`st.markdown("── Download ───")`) or use a
  Streamlit primitive (`st.divider()` + a subheader). Pick what
  reads cleanest; flag the choice in the PR description.
- **Three `st.download_button` widgets**, one per locked filename,
  in the wireframe order (`OPPORTUNITIES.md` → `PROGRESS.md` →
  `RECOMMENDERS.md`):
  - `st.download_button(label=f"⬇ {filename}", data=file_bytes,
    file_name=filename, mime="text/markdown",
    key=f"export_download_{filename}")`.
  - `data` arg is `(EXPORTS_DIR / filename).read_bytes()` if the
    file exists.
  - **Missing-file branch:** if `(EXPORTS_DIR / filename).exists()`
    is False, render the button as **disabled** (`disabled=True`
    on `st.download_button`) with empty `data=b""`. The user gets
    the "click Regenerate first" affordance from the existing
    mtimes panel ("not yet generated" placeholder); the disabled
    button is the visual signal that the file isn't downloadable yet.
- **Layout:** the wireframe shows download button + mtime line on
  the same logical row. Two valid renderings: (a) `st.columns([1, 3])`
  per file with the button left + the mtime line right, or (b)
  keep the existing per-file `st.markdown` mtime line and render
  the download button right above or below it. Pick (a) if it
  reads close to the wireframe; (b) if column rendering looks
  awkward at narrow viewports.
- **Re-use the existing T4 mtimes panel** — don't duplicate the
  `Path.exists()` + `datetime.fromtimestamp` logic. T5 either
  inserts the download button into the existing per-file loop, or
  the loop is restructured to render `(button, mtime-line)` pairs.

### Architecture rules (non-negotiable)
- Same as T4 — `pages/4_Export.py` imports `database`, `config`,
  `exports`, `streamlit`, `datetime`, `pathlib`. **NEVER** imports
  `pages/` modules.
- Widget keys: `export_download_<filename>` per the
  Coordination-protocol-pinned page prefix.

### Tests to write first (TDD red commit)
- Extend the existing `tests/test_export_page.py`. Mirror the
  three-class shape from T4.
- New `TestExportPageDownloadButtons` class:
  - `test_three_download_buttons_render` — three widgets with
    keys `export_download_OPPORTUNITIES.md`,
    `export_download_PROGRESS.md`,
    `export_download_RECOMMENDERS.md` exist with labels matching
    the wireframe (`⬇ OPPORTUNITIES.md` etc.).
  - `test_download_button_disabled_when_file_absent` — fresh DB,
    no files in `EXPORTS_DIR`; each download button has
    `disabled=True`. AppTest exposes button disabled-state via
    `at.download_button(key=...).disabled`.
  - `test_download_button_enabled_when_file_present` — pre-populate
    a file; the corresponding download button has `disabled=False`.
  - `test_download_data_matches_file_bytes` — pre-populate a file
    with known content; the button's `data` value matches the file
    bytes. AppTest exposes the download button's data via
    `.data` or similar — verify against
    `streamlit.testing.v1` API at implementation time.
  - `test_download_filename_attribute` — the button's `file_name`
    attribute matches the locked export filename (so the user's
    saved file lands as `OPPORTUNITIES.md`, not the page's
    internal slug).
  - `test_download_section_header_rendered` — the wireframe-pinned
    "── Download ───" header (or whatever shape lands per the
    above) appears in the rendered page above the buttons.
  - `test_regenerate_then_download_buttons_enable` — cohesion test:
    fresh DB → buttons disabled → click regenerate → re-rendered
    buttons enabled. Catches a bug where the disabled state is
    cached across the rerun.

### Architecture rules (non-negotiable — DESIGN §2 + §7)
- `pages/4_Export.py` extends the existing file (created in T4);
  do not rewrite the page-shell / regenerate-button / mtimes
  sections.
- Imports already in place from T4 (`from pathlib import Path`,
  `import streamlit as st`, `import exports`); add only what's
  new.

### Pre-PR gates (GUIDELINES §11 + standing isolation gate + standing CI-mirror check)
Standing checklist below in "Pre-commit checklist" + the CI-mirror
check from "Session bootstrap" — both apply to every PR.

### Branch + cadence
- Branch name: `feature/phase-6-tier5-DownloadButtons`.
- One PR for the test + feat commits; orchestrator handles the
  chore rollup post-merge.

---

## TDD cadence (mandatory — GUIDELINES §11)

```
1. test: commit  → add failing tests to tests/test_export_page.py
                   (download buttons not implemented yet → RED)
2. feat: commit  → extend pages/4_Export.py with download buttons (GREEN)
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
| Open PR | You — branch name: `feature/phase-6-tier5-DownloadButtons` |
| Review + merge PR | Orchestrator (Claude in Zed) |
| Update TASKS.md, CHANGELOG.md, reviews/ | Orchestrator only |
| Push directly to `main` | Nobody — PRs only |

**If you're unsure about a design decision:** check `DESIGN.md §7` (exports contract) first for Phase 6 work; see DESIGN §8 for the per-page UI contracts.
If it's not there, leave a comment in the code and note it in the PR
description — the orchestrator will resolve it before merging.
