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
  — e.g. `chore(phase-7-CL5): trim CL4 doc-drift carry-overs`.
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
**`main` HEAD:** Phase 7 cleanup CL4 merged (PR #44, `9a5eded`); test suite at 879 passed + 1 xfailed; pyright fence holds (0/0); save-toast wording branched on dirty diff; mailto subject pluralizes at N=1; empty-state copy lifted to `config.py`

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
| **CL2** — `config.py` lifts ✅ PR #42 | 4 lifts (EM_DASH + urgency_glyph + FILTER_ALL + REMINDER_TONES) + 1 drop (TRACKER_PROFILE block + 4 tests). Carry-overs C2 + C3 closed. Pyright fence held (0/0 post-lift). | Implementer | done |
| **CL3** — `tests/helpers.py` extraction ✅ PR #43 | 4 helpers lifted (link_buttons + decode_mailto + download_buttons + download_button); leading-underscore dropped on lift; paren-anchored rename strategy preserved test method substring matches. | Implementer | done |
| **CL4** — Phase 7 polish batched ✅ PR #44 | Four UX fixes shipped in one PR (4 commits): (1) save-toast wording branched on dirty diff in apps_detail_form + per-row interview save + recs_edit_form (apps_detail_form gained dirty-diff infrastructure — no-op skips DB write AND R1/R3 cascade, pinned by spy test); (2) `_build_compose_mailto` subject branches on `n_positions` (N=1 → singular; N≥2 → plural); DESIGN §8.4 line 631 amended; (3) `app.py` empty-DB hero `st.write` → `st.markdown` (lone outlier in cross-page convention); (4) 5 empty-state strings lifted to per-surface `config.py` constants. Suite 875 → 879 under all seven gates (4 new tests). Pyright fence held (0/0). Branch auto-deleted on merge. Three 🟡 doc-drift findings (history-as-guidance leak in DESIGN.md line 631 + `_build_compose_mailto` docstring + repeated "Phase 7 CL4 Fix N:" comments) deferred to CL5. | Implementer | done |
| **CL5** — CL4 doc-drift carry-overs (code-area) | DESIGN §8.4 line 631 trim + `pages/3_Recommenders.py::_build_compose_mailto` docstring trim + ~17 `# Phase 7 CL4 Fix N:` comment cleanups across 5 source files + 5 test files. Keep forward-looking invariants (e.g. cascade-safety note on apps_detail_form save handler); drop change-log noise. History-as-guidance anti-pattern per the user's standing rule (codified `e4732f7` + `289f7dd` + `d937c28`). | Implementer | CL1-4 done |
| **CL6** — Process + retroactive doc drift | Two orchestrator-only items: (a) add `gh pr merge --delete-branch` to `ORCHESTRATOR_HANDOFF.md` "Recurring post-merge ritual" (4 consecutive proven uses CL1-CL4); (b) retroactive trim of older Phase 5 + Phase 6 tier reviews still carrying `Kept by design` rows in Findings tables (per GUIDELINES §10 those belong in Q&A) + older `[v0.6.0]`/`[v0.5.0]`/etc. CHANGELOG blocks with long-form descriptive entries (per §14.4 should be one-line imperatives). | Orchestrator | CL5 done |

### What's after Phase 7
v1.0-rc schema cleanup, then publish scaffolding (README, LICENSE,
Streamlit Cloud deploy). Full list in `TASKS.md` §"Up next".

---

## Immediate task — Phase 7 cleanup CL5 (CL4 doc-drift carry-overs)

**Spec:** This doc's "Phase 7 cleanup + polish sub-tier" table
(CL5 row) · `reviews/phase-7-CL4-review.md` Findings (3 🟡 items
deferred to CL5) · user's standing rule against history-as-guidance
prose in forward-looking specs (codified across `e4732f7`,
`289f7dd`, `d937c28`).

CL5 trims change-log narration that leaked into spec docs +
docstrings + inline comments during CL4. Pure cleanup — no new
behaviour. Existing 879 tests are the contract gate; suite must
stay at 879 / 1 xfailed post-CL5.

### CL5 — three trims

#### Trim 1 — `DESIGN.md` line 631

**Current shape:** Forward-looking pluralization rule followed by a
back-reference clause: *"Phase 7 CL4 Fix 2 amended this line: the
previously-locked verbatim plural-only form read 'letters for 1
postdoc applications' at N=1, which is grammatically awkward."*

**Fix:** Drop the back-reference clause. Forward-looking rule (the
part before "Phase 7 CL4 Fix 2 amended this line:") stays as-is.
DESIGN.md is forward-looking spec; rationale lives in commit
messages + the CL4 review doc, not in the spec itself.

#### Trim 2 — `pages/3_Recommenders.py::_build_compose_mailto` docstring

**Current shape (around line 154):** Docstring contains a sentence
prefixed *"Subject pluralization (Phase 7 CL4 Fix 2): the singular
form is …"* — back-reference narration to the CL4 amendment.

**Fix:** Trim to the forward-looking pluralization rule. Docstrings
should state what the code does, not what changed in PR #44.

#### Trim 3 — `# Phase 7 CL4 Fix N:` inline comments (sweep)

**Sites** (verify exact lines at edit time via
`grep -rn "Phase 7 CL4 Fix" app.py config.py pages/ tests/`):

- `app.py` lines 116, 424
- `pages/1_Opportunities.py:350`
- `pages/2_Applications.py` lines 337, 799, 976
- `pages/3_Recommenders.py` lines 154, 241, 794
- `tests/test_app_page.py:2392`
- `tests/test_applications_page.py` lines 305, 1336, 1368, 2281
- `tests/test_opportunities_page.py` lines 546, 646, 759
- `tests/test_recommenders_page.py` lines 154, 1208, 1497

**Rule (CL4 review Finding #3 verbatim):** keep the cascade-safety
note + drop the change-log noise.

- **Keep** comments that document a forward-looking invariant a
  future reader needs to know — e.g. the
  `pages/2_Applications.py:799` cascade-safety note explaining
  why `apps_detail_form`'s no-op short-circuit is safe (skipping
  the R1/R3 cascade is correct because there's no transition to
  fire when nothing changed). Strip the `Phase 7 CL4 Fix 1:`
  prefix; keep the rationale.
- **Drop** comments that narrate "this was changed in CL4" with no
  forward-looking content — e.g. the verbatim
  `# Phase 7 CL4 Fix 4: empty-state copy lifted to config so a
  future wording edit is a one-line change tracked via git blame.`
  repeated at 5 sites. The "lifted to config" framing rots once
  the rollup commit lands; `git blame` already tells the future
  reader where the constant came from.
- **Test docstrings** with `Phase 7 CL4 Fix N:` prefix should drop
  the prefix; the contract-pinning prose stays intact. Tests pin
  contracts forward; CL4 attribution is git-history info.

### Architecture rules (non-negotiable)
- No code changes — pure comment/docstring/spec text edits.
- Existing test contracts keep passing exactly. The 879-test
  suite + pyright + isolation gate + CI-mirror are the behavioural
  pin.

### Tests to write first (TDD red commit)
None — CL5 is doc cleanup, no new contracts to pin.

Verification is **negative**: post-CL5,
`grep -rn "Phase 7 CL4 Fix" app.py config.py pages/ tests/`
should return either zero matches (full sweep) or only
forward-looking-invariant comments with the `Phase 7 CL4 Fix N:`
prefix stripped + rationale text retained. Final count depends on
the implementer's judgment per comment.

### Pre-PR gates (GUIDELINES §11 + standing isolation gate + CI-mirror + pyright fence)
```bash
ruff check .
pyright .                                       # CL1 fence — must stay 0/0
pytest tests/ -q                                # 879 pre-CL5, expect 879 post-CL5
pytest -W error::DeprecationWarning tests/ -q
grep -rn '\[SAVED\]\|\[APPLIED\]\|\[INTERVIEW\]' app.py pages/ \
  | grep -v '^\([^:]*\):[0-9]*:\s*#'
git status --porcelain exports/
mv postdoc.db postdoc.db.bak && pytest tests/ -q && mv postdoc.db.bak postdoc.db
```

### Branch + cadence
- Branch name: `feature/phase-7-cleanup-CL5-DocDriftTrim`.
- One commit suggested (whole-tree sweep) OR three commits (one per
  trim) for clean per-line `git blame` if the implementer prefers.
  CL2's per-lift commit split is the recent precedent for "split
  into commits per logical change"; CL3's two-commit shape is the
  precedent for "single refactor, optional smoke tests on top".
  Either is fine; flag the shape in the PR description.

### After CL5 closes
Orchestrator picks up **CL6** (process amendment + retroactive
review/CHANGELOG drift trim — orchestrator-only, runs direct on
main without a feature branch) before T5 (responsive layout check,
user-driven, manual capture).

---

## TDD cadence (mandatory — GUIDELINES §11)

```
1. test → red (failing assertions for new behaviour)
2. feat → green (implementation; suite passes)
3. chore: rollup → orchestrator handles TASKS.md/CHANGELOG/review
                   doc (YOU do not touch these)
```

Multi-fix tiers may bundle several `test`+`feat` pairs into one PR
with one commit per fix for clean per-line `git blame` — CL4's
4-fix shape is the recent precedent.

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
| Open PR | You — branch name comes from the "Immediate task" block |
| Review + merge PR | Orchestrator (Claude in Zed) |
| Update TASKS.md, CHANGELOG.md, reviews/ | Orchestrator only |
| Push directly to `main` | Nobody — PRs only |

**If you're unsure about a design decision:** check `DESIGN.md §7` (exports contract) first for Phase 6 work; see DESIGN §8 for the per-page UI contracts.
If it's not there, leave a comment in the code and note it in the PR
description — the orchestrator will resolve it before merging.
