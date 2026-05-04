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
  — e.g. `refactor(phase-7-CL2): lift EM_DASH + urgency_glyph + FILTER_ALL + REMINDER_TONES to config`.
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
  test_export_page.py    Phase 6 T4 + T5 complete (AppTest-driven)
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

**Latest tag:** `v0.7.0` (Phase 6 complete — Exports + Export page)
**`main` HEAD:** Phase 7 cleanup CL1 merged (PR #41); test suite at 864 passed + 1 xfailed; pyright fence in CI (0/0)

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

### Phase 6 — Exports (markdown generators) ✅ closed at `v0.7.0`

| Task | Status | Notes |
|------|--------|-------|
| T1 — `write_opportunities()` generator | ✅ PR #32 | `exports/OPPORTUNITIES.md` — 8-column contract pinned by `TestWriteOpportunities`; raw bracketed status sentinels; idempotent |
| T2 — `write_progress()` generator | ✅ PR #33 | `exports/PROGRESS.md` — positions × applications × interviews; `_format_confirmation` + `_format_interviews_summary` tri-state helpers; conftest fixture lift (mandatory ride-along) closed T1 pollution |
| T3 — `write_recommenders()` generator | ✅ PR #34 | `exports/RECOMMENDERS.md` — 8-column contract; new local `_format_confirmed` (`—`/`No`/`Yes`); Reminder cell reuses `_format_confirmation`; `notes` deliberately omitted; smoke-test `fix:` commit augmented `isolated_exports_dir` to also monkeypatch DB_PATH (closed CI-red regression that had been latent since T1) |
| T4 — Export page (manual regenerate button + file mtimes) | ✅ PR #35 | `pages/4_Export.py` shell + regenerate button (try/except `write_all`, success toast, friendly `st.error`) + per-file mtimes panel (`st.markdown` lines, `Path.exists()` check + `os.utime`-deterministic test) |
| T5 — Export page (`st.download_button` per file) | ✅ PR #36 | three `st.download_button` widgets (one per locked filename) + `st.divider()` + `st.subheader("Download")` section header; `disabled=True` + `data=b""` when file absent, `data=Path.read_bytes()` when present; stacked layout above existing T4 mtime line |
| T6 — Phase 6 close-out + tag `v0.7.0` | ✅ | Cohesion-smoke at [`reviews/phase-6-finish-cohesion-smoke.md`](reviews/phase-6-finish-cohesion-smoke.md); CHANGELOG `[v0.7.0]` split |

### Phase 7 — Polish

| Task | Status | Notes |
|------|--------|-------|
| T1 — Urgency colors on positions table (`st.column_config`) | ✅ PR #37 | `_deadline_urgency` returns `🔴`/`🟡`/`''`/`—` glyphs (was: `'urgent'`/`'alert'`/`''`); new em-dash branch distinguishes "no deadline at all" from "deadline far enough away"; explicit NaN guard |
| T2 — Position search bar on Opportunities | ✅ PR #38 | `filter_search` text_input prepended to filter row; `position_name` substring (case-insensitive, regex=False, NaN-safe); AND-combined with status/priority/field |
| T3 — `set_page_config` sweep on remaining pages | ✅ PR #39 | New `tests/test_pages_cohesion.py::TestSetPageConfigSweep` (10 parametrized tests) pins locked-kwargs source-grep + first-Streamlit-statement AST walk; audit found all 5 pages already conform — verification-only PR (no production code touched) |
| T4 — Confirm-dialog audit | ✅ PR #40 | New `TestConfirmDialogAudit` (11 tests across 3 destructive paths); audit surfaced + fixed real bug (position-delete dialog warning was missing "interview" from FK cascade enumeration) |
| **Cleanup + polish sub-tier** (CL1–CL5) | 🔲 in flight | Inserted between T4 and T5 — Pyright CI fence, `config.py` lifts, test-helper extraction, batched UX polish, retroactive doc-drift fix. See sub-table below. |
| T5 — Responsive layout check (1024/1280/1440/1680) | 🔲 postponed | resumes after CL5 closes |
| T6 — Phase 7 close-out + tag `v0.8.0` | 🔲 | after T5 |

### Phase 7 cleanup + polish sub-tier (between T4 and T5)

User-driven decision (2026-05-04): postpone T5 (responsive layout, user-driven) until accumulated cleanup + polish carry-overs are landed. Five sub-tiers:

| Sub-tier | What | Who | Blocks |
|---|---|---|---|
| **CL1** — Pyright in CI ✅ PR #41 | Pyright fence + 45 errors → 0 across 5 files. `pyright==1.1.409` pinned, `[tool.pyright]` basic mode in `pyproject.toml`, new CI step + checklist rows. | Implementer | done |
| **CL2** — `config.py` lifts | Lift duplicated constants + helpers to `config.py`: `EM_DASH`, urgency banding (`urgency_glyph(days)`), `"All"` filter sentinel, `_REMINDER_TONES`. Drop unused `TRACKER_PROFILE` (carry-over **C2**). Closes carry-over **C3**. | Implementer | CL1 fence valuable |
| **CL3** — `tests/helpers.py` extraction | Lift `_link_buttons`, `_decode_mailto`, `_download_buttons`, `_download_button` from per-page test files into shared helper module. | Implementer | parallel-able with CL2 |
| **CL4** — Phase 7 polish batched | 4 small UX fixes: Save-toast-when-no-dirty wording, subject-pluralization on N=1, `st.markdown` vs `st.write` cohesion, empty-state copy centralization. One PR with 4 commits. | Implementer | CL2 (touches EM_DASH + empty-state sites) |
| **CL5** — Doc drift + branch-cleanup process amendment | Retroactive trim of older review docs (Phase 5 + Phase 6 tier reviews still have `Kept by design` rows in Findings tables); CHANGELOG older blocks; add `--delete-branch` to ORCHESTRATOR_HANDOFF.md "Recurring post-merge ritual". | Orchestrator | CL1-4 done |

### What's after Phase 7
v1.0-rc schema cleanup, then publish scaffolding (README, LICENSE,
Streamlit Cloud deploy). Full list in `TASKS.md` §"Up next".

---

## Immediate task — Phase 7 cleanup CL2 (`config.py` lifts)

**Spec:** This doc's "Phase 7 cleanup + polish sub-tier" table
(between T4 and T5) · prior carry-overs **C2** (`TRACKER_PROFILE`
removal) + **C3** (`"All"` filter sentinel + `_REMINDER_TONES` lift)
logged across `reviews/phase-5-tier1-review.md`,
`reviews/phase-5-tier6-review.md`, `reviews/phase-7-tier1-review.md` ·
DESIGN §2 layer rules (config can be imported by all layers; pages
and exports cannot share helpers, but can share config constants).

CL2 lifts duplicated constants + helpers to `config.py` so the four
existing duplicate sites (`app.py`, `pages/1_Opportunities.py`,
`pages/2_Applications.py`, `exports.py`) become one definition.
Closes carry-overs **C2** + **C3** in one PR. CL1's pyright fence
(merged in PR #41) catches any type drift introduced by the lift.

### CL2 — `config.py` lifts

Four lifts + one drop:

1. **`EM_DASH = "—"` constant.** Currently duplicated in:
   - `app.py` (as `NEXT_INTERVIEW_EMPTY = "—"` — same value, different name)
   - `pages/1_Opportunities.py` line 25
   - `pages/2_Applications.py` (verify)
   - `pages/3_Recommenders.py` line 63
   - `exports.py` (as `_EM_DASH` — leading underscore for module-private)

   Lift: add `EM_DASH: str = "—"` to `config.py`. Update all five
   sites to `from config import EM_DASH` (or keep `config.EM_DASH`
   if cleaner). Remove the per-file constants. **Naming choice**:
   `EM_DASH` (matching the page-layer convention) over
   `NEXT_INTERVIEW_EMPTY` (app.py's specific framing) — the
   constant is generic, not interview-specific.

2. **Urgency-banding helper.** Currently duplicated as:
   - `pages/1_Opportunities.py::_deadline_urgency(date_str: Any) -> str`
     (returns 🔴 / 🟡 / `''` / `—` based on days until deadline)
   - `database.py::_urgency_glyph(days_away: int) -> str` (same
     banding, different signature — takes days, not date string)

   Lift: add `config.urgency_glyph(days_away: int | None) -> str`
   that handles both shapes — `None` → `EM_DASH`, otherwise the
   🔴 / 🟡 / `''` banding via the existing
   `DEADLINE_URGENT_DAYS` / `DEADLINE_ALERT_DAYS` thresholds.
   Both call sites become thin wrappers: the page-layer helper
   parses date string → days delta → calls `config.urgency_glyph`;
   the database-layer helper passes through directly. Mirror of
   how `STATUS_LABELS` is shared between layers via `config.py`.

3. **`"All"` filter sentinel.** Currently a magic literal in:
   - `pages/1_Opportunities.py` (verify locations)
   - `pages/2_Applications.py` (`STATUS_FILTER_ACTIVE` is in
     `config.py` already; `"All"` is the bare counterpart)
   - `pages/3_Recommenders.py` line 275 `_FILTER_ALL = "All"`

   Lift: add `FILTER_ALL: str = "All"` to `config.py` alongside
   `STATUS_FILTER_ACTIVE`. Update all three pages to import from
   config. Remove per-page literals.

4. **`_REMINDER_TONES` tuple.** Currently page-local:
   `pages/3_Recommenders.py` line 144
   `_REMINDER_TONES: tuple[str, ...] = ("gentle", "urgent")`.

   Lift: add `REMINDER_TONES: tuple[str, ...] = ("gentle",
   "urgent")` to `config.py`. Update Recommenders page to import.
   The `len(_REMINDER_TONES)` reference in the expander label
   becomes `len(config.REMINDER_TONES)`.

5. **Drop `TRACKER_PROFILE`** (carry-over **C2**) — currently in
   `config.py` lines 14-28: `TRACKER_PROFILE = "postdoc"`,
   `VALID_PROFILES = {"postdoc"}`, plus an import-time assertion.
   Never read by any module; unused since v1.1 doc refactor. Drop
   all three. Verify with `grep -rn "TRACKER_PROFILE\|VALID_PROFILES"`
   that no consumer survives — should return only the config.py
   definitions themselves.

### Architecture rules (non-negotiable — DESIGN §2)
- `config.py` imports nothing from this project. Pure constants
  (and now: pure functions like `urgency_glyph` that don't need
  to import database/streamlit).
- `database.py` + `pages/*.py` + `exports.py` import from `config`
  freely.
- Pages still do not import from each other; the lift to `config`
  is the structural fix for "two pages need the same string".

### Tests to write first (TDD red commit)
- Two test additions:
  - `tests/test_config.py` — extend with assertions that the new
    constants exist + have the expected values (`EM_DASH == "—"`,
    `FILTER_ALL == "All"`, `REMINDER_TONES == ("gentle",
    "urgent")`). Mirror of the existing `STATUS_FILTER_ACTIVE`
    invariant test.
  - `tests/test_config.py::test_urgency_glyph_*` — band the new
    helper at boundaries: `days = 0` → 🔴; `days =
    DEADLINE_URGENT_DAYS` → 🔴; `days = DEADLINE_URGENT_DAYS + 1`
    → 🟡; `days = DEADLINE_ALERT_DAYS` → 🟡; `days =
    DEADLINE_ALERT_DAYS + 1` → `''`; `days = None` → `—`. ~6
    tests covering the banding contract once at the source.
- Existing per-page tests (urgency tests in
  `test_opportunities_page.py`, etc.) should keep passing without
  modification — the lift is a behaviour-preserving refactor.

### Removal verification
After the lift, run:
```bash
grep -rn 'EM_DASH\s*=\s*"—"' app.py pages/ exports.py
grep -rn '"All"' pages/ | grep -v 'config\.FILTER_ALL\|"All", \*STATUS_VALUES'
grep -rn '_REMINDER_TONES' pages/
grep -rn 'TRACKER_PROFILE' .
```
First three should show only the new imports / config call sites
(no surviving local definitions). Last should show zero matches
(TRACKER_PROFILE fully removed).

### Pre-PR gates (GUIDELINES §11 + standing isolation gate + CI-mirror + pyright fence from CL1)
```bash
ruff check .
pyright .                                       # CL1 fence — must stay 0/0
pytest tests/ -q
pytest -W error::DeprecationWarning tests/ -q
grep -rn '\[SAVED\]\|\[APPLIED\]\|\[INTERVIEW\]' app.py pages/ \
  | grep -v '^\([^:]*\):[0-9]*:\s*#'
git status --porcelain exports/
mv postdoc.db postdoc.db.bak && pytest tests/ -q && mv postdoc.db.bak postdoc.db
```

### Branch + cadence
- Branch name: `feature/phase-7-cleanup-CL2-ConfigLifts`.
- One PR with the test commit (red) + the lift commit(s) (green).
  Implementer may split lifts into multiple commits (one per
  constant) for cleaner per-line `git blame` — same precedent as
  CL1's per-file fix-commit shape.

---

## TDD cadence (mandatory — GUIDELINES §11)

```
1. test: commit   → add tests/test_config.py assertions for the
                    new constants + urgency_glyph banding tests
                    (RED — constants/helper not yet defined)
2. refactor:      → add constants + helper to config.py; update
   commit(s)        every consumer (app.py, pages/, exports.py)
                    to import from config; drop duplicate
                    locals + TRACKER_PROFILE block (GREEN)
3. chore: rollup  → orchestrator handles TASKS.md/CHANGELOG/review
                    doc (YOU do not touch these)
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
pyright .                                       # must be clean (CL1 fence — added 2026-05-04)
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
| Open PR | You — branch name: `feature/phase-7-cleanup-CL2-ConfigLifts` |
| Review + merge PR | Orchestrator (Claude in Zed) |
| Update TASKS.md, CHANGELOG.md, reviews/ | Orchestrator only |
| Push directly to `main` | Nobody — PRs only |

**If you're unsure about a design decision:** check `DESIGN.md §7` (exports contract) first for Phase 6 work; see DESIGN §8 for the per-page UI contracts.
If it's not there, leave a comment in the code and note it in the PR
description — the orchestrator will resolve it before merging.
