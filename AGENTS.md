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
exports.py             Markdown generators (T1 `write_opportunities` shipped; T2 / T3 pending)
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
**`main` HEAD:** Phase 6 T1 merged (PR #32); test suite at 786 passed + 1 xfailed

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
| T2 — `write_progress()` generator | 🔲 next | see "Immediate task" |
| T3 — `write_recommenders()` generator | 🔲 | after T2 |
| T4 — Export page (manual regenerate button + file mtimes) | 🔲 | |
| T5 — Export page (`st.download_button` per file) | 🔲 | |
| T6 — Phase 6 close-out + tag `v0.7.0` | 🔲 | |

### What's after Phase 6
Phase 7 (Polish), v1.0-rc schema cleanup, then publish scaffolding
(README, LICENSE, Streamlit Cloud deploy). Full list in `TASKS.md`
§"Up next".

---

## Immediate task — Phase 6 T2 (`write_progress()` exports generator)

**Spec:** `TASKS.md` current sprint Phase 6 T2 · `DESIGN §7` exports
contract (`exports/PROGRESS.md` from positions JOIN applications
JOIN interviews) · `exports.py` existing T1 implementation as the
reference for shape (column contract pinning, idempotency,
deferred-import, em-dash + raw-bracketed-status conventions).

T2 ships the second of three Phase 6 generators. Same architectural
shape as T1 — read DB → render markdown table → write to
`exports/PROGRESS.md`. The data is **richer** than T1 (positions
JOIN applications JOIN interviews) so the column set + sort + cell
shapes need spec'ing first.

### T2 — `exports.write_progress()` generator

- Output: `exports/PROGRESS.md` (UPPERCASE; mirror of T1
  `OPPORTUNITIES.md` precedent + DESIGN §7 line 463).
- Source: positions × applications × interviews join. The closest
  existing reader is `database.get_applications_table()` (10-column
  projection) — it covers the positions+applications side; the
  interviews side needs an additional read (`get_interviews(pid)`
  per row, OR a richer joined query if you'd rather add one to
  `database.py`). Pick what reads cleanest; if you add a new query,
  pin it with tests in `test_database.py` first.
- Suggested column shape (verify against DESIGN §7 / wireframes
  before locking; pin via `TestWriteProgress` tests):
  - Position · Institute · Status · Applied · Confirmation ·
    Response · Result · Interviews-summary
  - "Interviews-summary" is the open question — could be a count
    (`2`), a comma-joined date list (`2026-05-08, 2026-05-15`), or a
    next-interview cell (`2026-05-08 Virtual`). Pick one and
    document why in the test class docstring; flag in the PR
    description so the orchestrator can sanity-check.
- Sort order: same shape as T1 — `deadline_date ASC NULLS LAST,
  position_id ASC`, with `pandas.sort_values(... kind="stable")` to
  add the position_id tiebreaker on top of the upstream SQL order.
- Cell shapes — **mirror T1 conventions** so the three exports read
  coherently:
  - `_safe_str_or_em` for missing TEXT cells → em-dash (`—`).
  - Date cells pass-through ISO TEXT.
  - Status renders **raw bracketed sentinel** (`[APPLIED]`, not
    `Applied`) — same backup-vs-UI rationale as T1 (cite
    `reviews/phase-6-tier1-review.md` Q1 if you need the long form).
  - `_md_escape_cell` on every cell (pipe + newline safety net).
- Idempotency: same DESIGN §7 #2 contract — pin with
  `test_idempotent_across_two_calls`. Two calls with no DB change
  must produce byte-identical output.

### Architecture rules (non-negotiable — DESIGN §7)
- `exports.py` imports `database` + `config`; **NEVER** `streamlit`.
- Deferred `database` import inside `write_progress` body (mirror of
  T1) breaks the `database → exports → database` circular import.
- `EXPORTS_DIR.mkdir(exist_ok=True)` inside the function body
  (mirror of T1) so it works independently of `write_all`'s prior
  mkdir — required for the Phase 6 T4 manual-trigger button.

### Mandatory ride-along — lift `db_and_exports` fixture into `tests/conftest.py`

**This is a load-bearing fix, not optional.** With T1 shipped, every
test that calls `database.add_position` (and there are dozens across
`test_applications_page.py` / `test_recommenders_page.py` /
`test_database.py` / etc.) now writes to the project's REAL
`exports/OPPORTUNITIES.md` as a side effect of the deferred
`exports.write_all()` call inside the writer. The `db` fixture in
`conftest.py` only monkeypatches `database.DB_PATH`; without an
`exports.EXPORTS_DIR` monkeypatch in the same fixture, every full
pytest run pollutes `exports/` with junk content from whichever test
ran last. Symptom: `git status` after pytest shows a modified or new
`exports/OPPORTUNITIES.md` whose content is whatever the last test
seeded.

T2 lands in the same change set as T1's exposed pollution, so the
implementer fixes it here. Two acceptable shapes:

1. **Augment the existing `db` fixture** (preferred — single
   fixture, every consumer benefits automatically):
   ```python
   @pytest.fixture
   def db(tmp_path, monkeypatch):
       monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
       import exports as _exports
       monkeypatch.setattr(_exports, "EXPORTS_DIR", tmp_path / "exports")
       database.init_db()
       yield
   ```
   After this lands, `tests/test_exports.py::db_and_exports` becomes
   redundant for every consumer EXCEPT the T1 + T2 + T3 export tests
   (which need the `exports_dir` path returned for `_read_output`).
   Keep `db_and_exports` as a thin wrapper that calls into the new
   conftest `db` and returns the path.

2. **Add a new `_isolated_exports_writer_path` fixture** to
   conftest.py and explicitly request it from every page test that
   triggers a DB write — strictly worse (touches every page test
   file); flagged for completeness only. Don't pick this.

Verify the fix with: `git status` after `pytest tests/ -q` shows
**zero changes** to `exports/`. If exports/ is dirty after a clean
run, the lift didn't take.

Document the lift in the PR description as a separate bullet under
Summary so the orchestrator can cite it cleanly in the close-out
review.

### Tests to write first (TDD red commit)
- After the conftest lift, `db_and_exports` keeps its current shape
  (returns the exports path) but delegates the DB monkeypatch to
  the lifted `db` fixture.
- `TestWriteProgress` class with:
  - `test_writes_file_at_expected_path` — `exports/PROGRESS.md`
    exists.
  - `test_table_header_matches_contract` — locked column header.
  - `test_one_row_per_position` — N positions → N data rows
    (positions ∩ applications LEFT JOIN; rows that lack an
    application still show up — applications row is auto-inserted
    by `add_position` per `database.add_position` contract).
  - `test_sort_order_by_deadline_asc_nulls_last` — mixed deadlines
    sort correctly.
  - `test_em_dash_for_missing_text_cells` — NULL `applied_date` /
    `notes` / etc. surface as `—`.
  - `test_iso_format_for_date_cells` — Applied column renders as
    `YYYY-MM-DD`.
  - `test_status_renders_as_raw_bracketed_sentinel` — `[APPLIED]`
    in the Status cell (not `Applied`).
  - `test_idempotent_across_two_calls` — byte-identical output.
  - `test_empty_db_writes_header_only` — header + separator only on
    empty DB (Phase 6 T4 manual-trigger button must work fresh).
  - `test_interviews_summary_<...>` — pin whatever
    "interviews-summary" choice you make; multiple interviews → a
    deterministic single cell.

### TDD cadence
Standard three-commit triplet — `test:` → `feat:` → `chore:` (the
`chore:` is the orchestrator's).

### Pre-PR gates (GUIDELINES §11) + T2 isolation gate
```bash
ruff check .
pytest tests/ -q
pytest -W error::DeprecationWarning tests/ -q
grep -rn '\[SAVED\]\|\[APPLIED\]\|\[INTERVIEW\]' app.py pages/ \
  | grep -v '^\([^:]*\):[0-9]*:\s*#'

# T2-specific isolation gate — verifies the conftest lift took.
# After a clean pytest run, exports/ must be untouched. If this prints
# anything, the conftest fixture isn't monkeypatching EXPORTS_DIR
# correctly and the lift needs revisiting.
git status --porcelain exports/
```

If `git status --porcelain exports/` produces any output after the
suite runs, the conftest lift is incomplete — fix before opening the
PR.

### Branch + cadence
- Branch name: `feature/phase-6-tier2-WriteProgress`.
- One PR for the test + feat commits (the conftest lift lands in the
  test commit); orchestrator handles the chore rollup post-merge.

---

## TDD cadence (mandatory — GUIDELINES §11)

```
1. test: commit  → add failing tests to tests/test_exports.py
                   (write_progress not implemented yet → RED)
2. feat: commit  → implement write_progress() in exports.py (GREEN)
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
| Open PR | You — branch name: `feature/phase-6-tier2-WriteProgress` |
| Review + merge PR | Orchestrator (Claude in Zed) |
| Update TASKS.md, CHANGELOG.md, reviews/ | Orchestrator only |
| Push directly to `main` | Nobody — PRs only |

**If you're unsure about a design decision:** check `DESIGN.md §7` (exports contract) first for Phase 6 work; see DESIGN §8 for the per-page UI contracts.
If it's not there, leave a comment in the code and note it in the PR
description — the orchestrator will resolve it before merging.
