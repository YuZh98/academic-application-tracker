# Implementation Guidelines
_Read at the start of every coding session. Scannable checklist, not a tutorial.
For depth on Git and Streamlit state, see `docs/dev-notes/`._

**Version:** v1.3 | **Last updated:** 2026-05-02 | **Status:** authoritative

---

## 1. Environment

```
Python   3.14.0   (Homebrew, system-managed)
venv     .venv/   (project-local; gitignored)
```

**Always activate before coding or running:**
```bash
source .venv/bin/activate
```

**Pinned minimum versions** (exact pins in `requirements.txt` after first install):

| Package | Required ≥ | Tested with (latest tag) |
|---------|-----------|----------------------|
| streamlit | 1.50 | 1.56.0 |
| plotly | 5.22 | 6.7.0 |
| pandas | 2.2 | 3.0.2 |
| sqlite3 | stdlib — no install needed | — |

The `Required ≥` column is the floor (APIs used in the current codebase
won't work on older versions — `width="stretch"` needs Streamlit ≥ 1.50).
Bump the floor when a newer API is adopted; keep Tested-with in sync with
what CI actually runs.

**Never install packages globally.** Always install inside `.venv`.

---

## 2. Module Import Contract

```
config.py     ← imports nothing from this project
database.py   ← imports config; never imports streamlit
exports.py    ← imports database, config; never imports streamlit
app.py        ← imports database, config
pages/*.py    ← imports database, config; never imports exports directly
```

`exports.write_all()` is called **inside** `database.py` write functions — page
files never call it directly. The `database ↔ exports` cycle is broken by
importing `exports` lazily inside each write function (not at module top).

### One responsibility per file
- `database.py` — SQL only. No display logic, no `st.*` calls.
- `exports.py` — File writing only. No business logic.
- `config.py` — Constants only. No functions, no I/O.
- Page files — Display only. No raw SQL. No file I/O.

---

## 3. Naming Conventions

### Python (PEP 8 throughout)
| Thing | Convention | Example |
|-------|-----------|---------|
| Functions | `snake_case` | `get_all_positions()` |
| Variables | `snake_case` | `deadline_date` |
| Constants | `UPPER_SNAKE_CASE` | `STATUS_VALUES`, `DEADLINE_ALERT_DAYS` |
| Files | `snake_case.py` | `database.py`, `exports.py` |
| Classes | `PascalCase` (rare in this project) | `PositionForm` |
| Private helpers | `_leading_underscore` | `_safe_str`, `_connect` |

### Database columns
- All lowercase with underscores: `position_name`, `deadline_date`, `req_cv`
- Requirement flags prefixed `req_`: `req_cv`, `req_cover_letter`
- Materials-done flags prefixed `done_`: `done_cv`, `done_cover_letter`
- Date fields suffixed `_date`: `asked_date`, `submitted_date`, `deadline_date`
- Boolean-like integer fields: `0` = false, `1` = true (SQLite has no BOOLEAN)

### Streamlit widget keys and session-state
- **Quick-add form** widgets: prefix `qa_` (`qa_position_name`, `qa_deadline_date`)
- **Edit panel** widgets: prefix `edit_` (`edit_position_name`, `edit_notes`)
- **Filter bar** widgets: prefix `filter_` (`filter_status`, `filter_field`)
- **Form ids** end with `_form` to avoid collision with widget keys inside:
  `edit_notes_form` contains the widget `edit_notes`
- **Internal sentinels** start with `_` and describe state, not widgets:
  `_edit_form_sid`, `_delete_target_id`, `_delete_target_name`,
  `_skip_table_reset`, `_funnel_expanded` (dashboard funnel disclosure toggle)

### Page files
- Filename format: `N_Title.py` where `N` is the sort-order integer (`1_Opportunities.py`)
- Page title set with `st.title()` as the first visible element
- `st.set_page_config(page_title=..., layout=...)` sits at the top

---

## 4. Type Hints & Docstrings

All **public functions** (not prefixed with `_`) in `database.py` and `exports.py`
require:
- Type hints on all parameters and return values
- A one-line docstring if the name is not fully self-explanatory

```python
# Good
def get_upcoming_deadlines(days: int) -> pd.DataFrame:
    """Return non-terminal positions with deadline_date within the next `days` days."""
    ...

# Good — name is self-explanatory, no docstring needed
def get_all_positions() -> pd.DataFrame:
    ...

# Bad — no type hints
def add_position(fields):
    ...
```

Private helpers (prefixed `_`) don't need docstrings but must still have type hints.

---

## 5. Database Access Patterns

### Always use parameterised queries — never f-strings in SQL for **values**
```python
# GOOD
cursor.execute("SELECT * FROM positions WHERE status = ?", (status,))

# BAD — SQL injection risk even in personal tools; teaches bad habits
cursor.execute(f"SELECT * FROM positions WHERE status = '{status}'")
```

**Exception — column names from config:** f-strings are allowed for **column
identifiers** sourced exclusively from `config.REQUIREMENT_DOCS`. Document
the exception inline (see `compute_materials_readiness`).

### Connection pattern (context manager)
```python
from contextlib import contextmanager

@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### Every write function ends with an export call
```python
def add_position(fields: dict) -> int:
    with _connect() as conn:
        ...
    import exports as _exports      # deferred to break circular import
    _exports.write_all()
    return new_id
```

---

## 6. Config Usage

- **Never hardcode a status string, priority value, or vocabulary option** in any
  file other than `config.py`.
- Always import the constant and use it:
```python
# GOOD
from config import STATUS_VALUES, STATUS_SAVED, STATUS_LABELS
st.selectbox("Status", STATUS_VALUES, format_func=STATUS_LABELS.get)
if row["status"] == STATUS_SAVED: ...

# BAD
st.selectbox("Status", ["[SAVED]", "[APPLIED]", ...])
if row["status"] == "[SAVED]": ...
```
- When adding a new document type (e.g., "Portfolio"), add it to `REQUIREMENT_DOCS`
  in `config.py` only. The form, schema migration, and export pick it up.
- **Grep rule (pre-merge check; also enforced by CI + pre-commit):**
  `rg --type py -n '\[SAVED\]|\[APPLIED\]|\[INTERVIEW\]' app.py pages/ | rg -v '^[^:]+:[0-9]+:\s*#'` must return zero lines.
  The `rg -v` filter excludes lines whose content begins with `#`, so
  explanatory comments (e.g. [pages/1_Opportunities.py:395](pages/1_Opportunities.py)) don't trip the rule.
  Wired into [`.github/workflows/ci.yml`](.github/workflows/ci.yml) and the
  `status-literal-grep` hook in [`.pre-commit-config.yaml`](.pre-commit-config.yaml).

---

## 7. Streamlit Patterns

### Controlled inputs for enumerated values
```python
status = st.selectbox(
    "Status", config.STATUS_VALUES,
    format_func=config.STATUS_LABELS.get,   # display labels; storage stays raw
)
priority = st.selectbox("Priority", config.PRIORITY_VALUES)
```
Status selectboxes go through `format_func=config.STATUS_LABELS.get` per
DESIGN §8.0 — storage keeps raw bracketed sentinels, UI shows stripped
labels. Selectboxes with an `"All"` passthrough wrap the getter in a
lambda so the sentinel renders unchanged: `lambda v: STATUS_LABELS.get(v, v)`.

### Dates via `st.date_input()` — never `st.text_input()`
```python
deadline = st.date_input("Deadline", value=None)
deadline_str = deadline.isoformat() if deadline else None
```

### `st.form()` for all data writes
```python
with st.form("add_position_form"):      # form id ≠ any widget key inside
    name = st.text_input("Position Name", key="add_position_name")
    submitted = st.form_submit_button("Save")
if submitted:
    try:
        database.add_position(fields)
        st.toast(f'Added "{name}".')
        st.rerun()
    except Exception as e:
        st.error(f"Could not save: {e}")
```

### Confirmations via `st.toast`, not `st.success`
`st.toast` persists across `st.rerun()`; `st.success` gets clobbered.
Failures use `st.error()` with a friendly message.

### Irreversible actions via `@st.dialog`
Delete confirmations use a modal dialog (see Opportunities-page
`_confirm_delete_dialog`). AppTest has a quirk here — the outer script must
re-open the dialog on every rerun while the pending flag is set.
See dev-notes gotcha #3.

### Cross-page navigation via `st.switch_page`
```python
if st.button("→ Opportunities"):
    st.switch_page("pages/1_Opportunities.py")
```

### Pre-seeding edit forms — use the `_edit_form_sid` sentinel
Re-seeding widget session_state only works when gated by a selection-id
sentinel — otherwise Streamlit's widget-value trap keeps the old values.
See dev-notes gotcha #2.

### Coerce NaN cells with `_safe_str` before feeding into widgets
Pandas returns `float('nan')` for NULL TEXT cells, which crashes widget
protobuf serialisation. See dev-notes gotcha #1.

---

## 8. Error Handling

Goal: **clear messages, not silent failures.** This is a personal tool — users
should never see a raw traceback.

```python
# Preferred pattern for user-facing database writes
try:
    database.add_position(fields)
    st.toast("Position saved.")
except sqlite3.IntegrityError as e:
    st.error(f"Could not save: {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
    # DO NOT re-raise in user-facing paths — re-raising renders the very
    # traceback the handler exists to hide.
```

- In **user-facing save/delete paths**, catch `Exception` broadly, show
  `st.error(...)`, and **do not re-raise**.
- In **non-UI code paths** (startup, `init_db`, tests), let unexpected errors
  propagate to the terminal where they can be diagnosed.
- Validate user input before calling `database.*`: reject whitespace-only
  strings in required fields before attempting a write.

---

## 9. Testing Conventions

**Layout**

- Test files live at `tests/test_<module>.py` or `tests/test_<page>.py`.
- One test class per logical unit: `Test<TierOrFeature>` (e.g.,
  `TestT3MaterialsReadiness`, `TestQuickAddFormBehaviour`).

**Class structure**

- Pin fixed copy / keys / routes as **class-level constants** — not literals
  in method bodies:
  ```python
  class TestT3MaterialsReadiness:
      SUBHEADER    = "Materials Readiness"
      EMPTY_COPY   = "Materials readiness will appear once you've added positions..."
      CTA_KEY      = "materials_readiness_cta"
      TARGET_PAGE  = "pages/1_Opportunities.py"
  ```
- A rename in copy shows up as a one-line class-constant edit, not dozens of
  method edits.

**AppTest usage**

- Instantiate at method start: `at = AppTest.from_file("app.py", default_timeout=10)`.
- Seed data via `database.add_position()` / `upsert_application()` —
  **never raw SQL** in tests.
- Shared DB isolation via the `db` fixture in `conftest.py`.
- `pytest.ini` has `pythonpath = .` so `pytest` runs without a `PYTHONPATH=.`
  prefix.

**Element lookup**

- **Display-only primitives** (`st.metric`, `st.subheader`, `st.info`) do
  not accept `key=` in Streamlit 1.56. Identify them by **label** (matches
  DESIGN contract) or by **positional order** within a known column container.
- **Stateful widgets** (`st.text_input`, `st.selectbox`, `st.checkbox`,
  `st.button`) accept `key=` and should be looked up by key.
- For conditionally-rendered widgets, use a try/except helper:
  ```python
  def _checkbox_rendered(at, key):
      try:
          at.checkbox(key=key)
          return True
      except KeyError:
          return False
  ```

**Coverage bar (enforced per tier)**

- Every KPI card / chart / empty-state branch pinned by at least one test.
- Every Save path: success case + DB-failure case + state-preservation case.
- Every pre-merge check: `pytest tests/ -q` + `pytest -W error::DeprecationWarning tests/ -q`, both green.

---

## 10. Review Conventions

Every tier ends with a pre-merge review doc at
`reviews/phase-<N>-tier<M>-review.md`. Structure:

1. **Executive summary** — 2–3 sentences; verdict upfront.
2. **Findings table** — numbered rows, each with file/line, description,
   severity (icons below), and status (see Status column values below).
3. **Junior-engineer Q&A** — 5–8 questions for standard reviews; none
   required for trivial reviews; no hard ceiling for deep reviews
   (per §14.3 doc tiering). Answered in the didactic style — this is
   the teaching layer.
4. **Verdict** — Approve / Approve with nits / Request changes.

**Severity scale**

| Icon | Meaning | Action |
|------|---------|--------|
| 🔴 | Bug (behaviour wrong) | Fix before merge |
| 🟠 | Drift (doc↔code or code↔code inconsistency) | Fix before merge |
| 🟡 | Polish (readability, naming, comment gap) | Fix if cheap; defer if costly |
| 🟢 | Future (post-v1 or v2 concern) | Log in backlog |
| ℹ️ | Observation (no defect; reader awareness) | None — informational only |

**Status column values**: `Fixed inline` · `Deferred` · `Backlog` ·
`Kept by design` · `Carry-over`. Use `Carry-over` for pre-existing items
the current change does not regress (e.g. an inherited inconsistency
that previous reviews logged but didn't fix). `Kept by design`
observations belong in the Q&A section, not in the Findings table —
they are not defects.

---

## 11. Git Workflow

**Branches:** `main` is stable; all work on `feature/<name>`; merge via PR.

**Commit message format:**
```
<type>(<optional-scope>): <short imperative description>   ≤ 72 chars

<optional body: what and why>
```

**Types:** `feat` · `fix` · `schema` · `config` · `refactor` · `test` ·
`docs` · `review` · `chore`

**TDD cadence:** `test:` (red) → `feat:` (green) → `chore:` (tracker rollup).

**Version tags:** `v0.x.0` for each phase shipped; `v1.0.0` at first
publishable release; `v1.x.y` post-v1.

**What never goes in git:** `postdoc.db` · `.venv/` · `.env` · `__pycache__/`
· `CLAUDE.md` · `PHASE_*_GUIDELINES.md`.

**Pre-commit checklist** (CI re-runs the first three on every push and PR
via [`.github/workflows/ci.yml`](.github/workflows/ci.yml)):

- [ ] `ruff check .` clean
- [ ] `pytest tests/ -q` passes
- [ ] `pytest -W error::DeprecationWarning tests/ -q` passes
- [ ] §6 status-literal grep clean (code-only):
      `rg --type py -n '\[SAVED\]|\[APPLIED\]|\[INTERVIEW\]' app.py pages/ | rg -v '^[^:]+:[0-9]+:\s*#'` returns 0 lines
- [ ] No `print()` debug left in
- [ ] `git diff --staged` shows only intended changes
- [ ] `postdoc.db` is not staged

**Local automation:** install dev deps once per clone, then pre-commit
runs `ruff --fix` and the status-literal grep on every `git commit`:

```bash
pip install -r requirements-dev.txt
pre-commit install
```

For branching, commit-granularity, undo levels, and tagging mechanics in depth, see [`docs/dev-notes/git-workflow-depth.md`](docs/dev-notes/git-workflow-depth.md).

---

## 12. Anti-patterns

| Avoid | Reason |
|-------|--------|
| Storing computed values in the DB | Materials readiness, days-until-deadline — derive at query time |
| Adding columns not in `config.REQUIREMENT_DOCS` without updating config | Breaks auto-migration in `init_db()` |
| Using `st.experimental_*` APIs | Deprecated in Streamlit ≥ 1.35; pinned APIs wanted |
| Magic numbers in page files | Thresholds live in `config.py` (e.g., `DEADLINE_ALERT_DAYS`) |
| Catching `Exception` and swallowing silently | Hides real bugs — always `st.error(...)` with the message |
| Re-raising in user-facing save/delete handlers | Renders the traceback the handler exists to hide |
| Modifying `exports/` files by hand | They are generated; edits will be overwritten |
| `use_container_width=True` | Deprecated → use `width="stretch"` |
| `r[col] or ""` for DB text pre-seed | NaN is truthy — use `_safe_str(v)` |
| Tagging new milestones as `v1-phase-N` | Use `v0.x.y` scheme instead (see §11) |

---

## 13. Adding a new page

A procedural checklist for `pages/N_Title.py`. The list below is the
mechanical sequence — see DESIGN §8.0 for cross-page conventions and
DESIGN §8.x for each page's panel/widget contract.

1. **Filename**: `pages/N_Title.py` where `N` is the next sort-order
   integer.
2. **First Streamlit call**: `st.set_page_config(page_title="Postdoc Tracker", page_icon="📋", layout="wide")`
   — DESIGN §8.0 + D14. Must precede every other `st.*` call; Streamlit
   raises otherwise.
3. **Schema bootstrap**: `database.init_db()` — idempotent; ensures
   any pending migration loops run when the page is the first one
   opened in a session.
4. **Page heading**: `st.title("...")` as the next visible element.
5. **Page-scoped widget-key prefix**: pick from the table below and
   use it consistently for every widget key on the page.

   | Page | Prefix |
   |------|--------|
   | Quick-add (Opportunities) | `qa_` |
   | Edit panel (Opportunities) | `edit_` |
   | Filter bar (any page) | `filter_` |
   | Applications page | `apps_` |
   | Recommenders page | `recs_` |
   | Export page | `export_` |

6. **Form ids**: suffix with `_form` to avoid collision with widget
   keys inside (§3 + dev-notes gotcha #4).
7. **Test file**: `tests/test_<page_name>.py`, one class per logical
   unit (`TestApplicationsTable`, etc., per §9).

---

## 14. Documentation Conventions

For review-doc structure see §10; for git-side rules see §11.

### 14.1 File-header schema

Every authoring-class doc opens with metadata immediately under the
title. Required fields by doc class:

| Doc class | Required header fields |
|---|---|
| Spec / guideline (`DESIGN`, `GUIDELINES`) | **Version:** · **Last updated:** · **Status:** (the doc's own status taxonomy) |
| Dev-note (`docs/dev-notes/*`) | Title only; cross-refs in body |
| Review (`reviews/*`) | **Branch:** · **Scope:** · **Stats:** (optional) · **Verdict:** |
| ADR (`docs/adr/ADR-*.md`) | **Status:** · **Date:** · **Deciders:** (per `docs/adr/README.md` template) |

Tracker docs (`TASKS.md`, `roadmap.md`, `CHANGELOG.md`) are not authoring-class; their conventions live in §14.4 and §14.5.

### 14.2 Cross-reference canonical form

Lock one form: `DESIGN §8.1`, `GUIDELINES §11`, `dev-notes gotcha #16`.
No `.md` suffix, no `#anchor`, no markdown link unless navigation is
load-bearing. Mixed shapes in the same prose are a 🟠 drift finding.

### 14.3 Doc tiering — when to add depth

| Class | Length budget | When to expand |
|---|---|---|
| Spec (`DESIGN`) | (no cap) | Architectural change |
| Guideline (this file) | Scannable; bullets > prose | New convention |
| Dev-note | One topic per file; 50–400 lines | Reproduced + pinned by test |
| ADR | 1–3 pages with template | Hard-to-reverse architectural decision |
| Review (trivial: ≤ 3 findings, no surprises) | Exec summary → findings → verdict; no Q&A | Routine merges |
| Review (standard) | + 5–8 Q&A | Default for tier work |
| Review (deep: > 8 findings, bug repro, architecture) | + verbatim source dumps OK | Bug-fix rounds, DESIGN reviews |

Review structure itself is locked at §10.

### 14.4 CHANGELOG discipline

A changelog is a navigable record of notable changes. Detail belongs in
commit messages and review docs; the changelog is an index into them.

#### Structure
- File `CHANGELOG.md` at repo root. `[Unreleased]` at the top
  accumulates new entries. On each release tag, rotate `[Unreleased]`
  to `## [vX.Y.Z] - YYYY-MM-DD` (ISO 8601) in the same commit.
- Versions ordered latest-first; every version header is clickable
  via bottom-of-file link references (e.g.
  `[v0.5.0]: https://github.com/.../releases/tag/v0.5.0` and
  `[Unreleased]: https://github.com/.../compare/v0.5.0...HEAD`).
- Within a version, subsections may appear once each, in this order:
  `### Added` · `### Changed` · `### Fixed` · `### Removed` ·
  `### Deprecated` · `### Security`. Headings are plain — `### Changed`,
  never `### Changed — <topic>`.

#### What counts as an entry
- An entry records a notable change — one a future reader needs to
  know about. Changes with no observable effect (pure refactors,
  tests-only commits, formatting, typo fixes) are not notable.
- One change → one entry, regardless of how many commits implemented it.

#### Entry shape
- One line per entry, two if a qualifier is genuinely needed; three
  lines means the detail belongs in the commit message.
- Imperative mood: "Add X", "Fix Y", "Remove Z".
- End each entry with a navigation target — commit hash, PR number, or
  review-doc path.
- Breaking changes prefix `**Breaking:**`.

#### Migrations
If a version requires a schema or vocabulary change, add one
`**Migration:**` block at the end of that version section listing
the SQL or manual steps. One block per version.

#### Avoid
- Process narrative — review notes, internal decisions, branch references.
- Forensic detail — rationale, alternatives considered, file:line refs,
  test counts. Those live in the commit message body or the review doc.

### 14.5 TASKS.md scope rules

`TASKS.md` is a sprint tracker, not a project history. The
`Recently done` section caps at the **10 most recent items**; items
older than the last shipped version tag are trimmed and live in
`CHANGELOG.md` under their version block.

`Current sprint` uses `- [ ]` / `- [x]` checkboxes — top-level boxes
are tiers; sub-task boxes nest. When all sub-tasks under a tier check,
the tier rolls up to `Recently done` on the next `chore:` commit.

### 14.6 Wireframe scope

`docs/ui/wireframes.md` is "intent-only — not pixel-exact" for visual
layout (column widths, exact emoji choice, ASCII alignment).

It is NOT intent-only for **column order**, **panel ordering**, or
**panel presence**. Structural divergence from `DESIGN` is a 🟠
finding (drift), not 🟡 (polish).

### 14.7 Reviews folder index

`reviews/` carries a `README.md` index — one row per review, columns
`(date, scope, branch, verdict, link)`. Reverse-chronological;
prepend on each new review.

Naming: `phase-<N>-tier<M>-review.md` (lowercase `tier`); date-stamped
one-offs use `<topic>-YYYY-MM-DD-review.md`.

### 14.8 What lives where

Pick the home for decision-class content in this order:

| Content | Home | Why |
|---|---|---|
| Cross-cutting architectural decisions | `docs/adr/` | Forward-only ADR ledger per `docs/adr/README.md` |
| Tier-local implementation choices | `reviews/phase-*.md` Q&A | Bound to the change that introduced them |
| Streamlit / library quirks | `docs/dev-notes/streamlit-state-gotchas.md` | Per-quirk Symptom / Cause / Workaround |
| Config-extension procedural recipes | `docs/dev-notes/extending.md` | "How": step-by-step walkthrough |
| Config-extension architectural index | `DESIGN §5.3` | "What changes where": one row per goal |
| User-facing release narrative | `CHANGELOG.md` | Keep-a-Changelog formatted |
| Sprint state | `TASKS.md` | Hand-maintained per §14.5 |
| Phase planning | `roadmap.md` | Phases + ship criteria + post-v1 backlog |

Content placed in a lower-priority home when a higher one applies is
a 🟠 drift finding.
