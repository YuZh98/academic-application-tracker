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
  3_Recommenders.py    Recommenders page (Phase 5 T4 + T5 done; T6 pending)
tests/
  conftest.py          Shared fixtures — `db` (temp SQLite) and `make_position()`
  test_database.py     Unit tests for database.py
  test_app_page.py     Integration tests for app.py (AppTest)
  test_applications_page.py
  test_recommenders_page.py   T4 + T5 tests done; T6 tests to be added here
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
**`main` HEAD:** Phase 5 T5 merged (PR #29); test suite at 756 passed + 1 xfailed

### Phase 5 — Applications + Recommenders pages

| Task | Status | Notes |
|------|--------|-------|
| T1 — Applications page shell + table | ✅ PR #15 | |
| T2 — Application detail card + cascade toast | ✅ PR #16 | |
| T3 — Inline interview list UI | ✅ PR #19 | |
| T4 — Recommenders page shell + Pending Alerts panel | ✅ PR #28 | `pages/3_Recommenders.py` created |
| T5 — Recommenders table + add form + inline edit | ✅ PR #29 | All-Recommenders + filters + Add form + inline edit + dialog Delete |
| T6 — Reminder helpers (mailto + LLM prompts) | 🔲 next | see "Immediate task" |
| T7 — Phase 5 review + PR + tag `v0.6.0` | 🔲 | after T6 |

### What's after Phase 5
Phase 6 (Exports — markdown generators), Phase 7 (Polish),
v1.0-rc schema cleanup, then publish scaffolding (README, LICENSE,
Streamlit Cloud deploy). Full list in `TASKS.md` §"Up next".

---

## Immediate task — Phase 5 T6

**Spec:** `DESIGN.md §8.4` "Reminder helpers" bullet (lines 629–641) ·
`TASKS.md` current sprint T6 entry · the host surface is the existing
**Pending Alerts** cards in `pages/3_Recommenders.py` (T4 surface, NOT
the T5-C inline edit card)

T6 wires the reminder-composition helpers into each Pending Alerts
card. The card already renders one `st.container(border=True)` per
recommender with a list of positions they owe letters for; T6 adds
two affordances per card:

### T6-A — Primary `Compose reminder email` button
- Render INSIDE the per-recommender alert card, after the bullet
  list of positions. Key: `recs_compose_{recommender_name_slug}`
  (or per-row index — whichever stays unique across cards).
- DESIGN §8.4 pins the subject + body **verbatim**:
  - Subject: `Following up: letters for {N} postdoc applications`
    (`N` = position count for that recommender)
  - Body: `Hi {recommender_name}, just a quick check-in on the
    letters of recommendation you offered. Thank you so much!`
- Implementation: `st.link_button("Compose reminder email",
  url=f"mailto:?subject={quote(subject)}&body={quote(body)}")` using
  `urllib.parse.quote`. No `to:` field — the user's mail client
  prompts for the address (the schema doesn't store recommender
  emails today, per `DESIGN §6` recommenders table).
- No outbound email integration — OS hands off to default mail
  client. No signature appended — the mail client adds one.

### T6-B — Secondary `LLM prompts (N tones)` expander
- `with st.expander(f"LLM prompts ({N} tones)", expanded=False):`
  beneath the Compose button on each alert card. `N` = number of
  tone variants; DESIGN §8.4 specifies **gentle** and **urgent**
  (so `N=2`, expander label `LLM prompts (2 tones)`).
- Each prompt block: `st.code(prompt_text, language="text")` so
  Streamlit's built-in copy-on-hover affordance is available.
- Each prompt fills:
  - recommender name + relationship,
  - positions owed (position name, institute, deadline),
  - days since the recommender was asked,
  - target tone (one prompt per tone),
  - instruction asking the LLM to return BOTH subject and body so
    the user can paste either / both into a mail client.

### Tests to write first (TDD red commit)
- `TestT6ComposeButton` — link button renders per alert card, the
  `mailto:` URL contains the verbatim locked subject (with correct
  `N`) and body (with correct `recommender_name`) when URL-decoded.
- `TestT6LLMPromptsExpander` — expander label includes the live
  tone count, expected number of `st.code` blocks render, each
  contains the recommender name + relationship + every position's
  details + the days-since-asked count + the target tone string.

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

---

## TDD cadence (mandatory — GUIDELINES §11)

```
1. test: commit  → add failing tests to tests/test_recommenders_page.py
                   (page doesn't implement T6 yet → RED)
2. feat: commit  → implement T6 in pages/3_Recommenders.py (GREEN)
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
| Open PR | You — branch name: `feature/phase-5-tier6-RecommenderReminders` |
| Review + merge PR | Orchestrator (Claude in Zed) |
| Update TASKS.md, CHANGELOG.md, reviews/ | Orchestrator only |
| Push directly to `main` | Nobody — PRs only |

**If you're unsure about a design decision:** check `DESIGN.md §8.4` first.
If it's not there, leave a comment in the code and note it in the PR
description — the orchestrator will resolve it before merging.
