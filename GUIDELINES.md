# Implementation Guidelines
_Read at the start of every coding session. Scannable checklist, not a tutorial.
For depth on Git and Streamlit state, see `docs/dev-notes/`._

**Version:** v1.1 (2026-04-23) | **Applies from:** v0.5 onward

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

| Package | Required ≥ | Tested with (v0.4.0) |
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
  `_edit_form_sid`, `_delete_target_id`, `_skip_table_reset`,
  `_active_edit_tab` (Opportunities edit-panel tab selector),
  `_funnel_expanded` (dashboard `[expand]` toggle)

### Page files
- Filename format: `N_Title.py` where `N` is the sort-order integer (`1_Opportunities.py`)
- Page title set with `st.title()` as the first visible element
- From v1.1, `st.set_page_config(page_title=..., layout=...)` sits at the top

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
- **Grep rule (pre-merge check):**
  `grep -nE "\[SAVED\]|\[APPLIED\]|\[INTERVIEW\]" app.py pages/*.py` must return zero hits.

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
See `docs/dev-notes/streamlit-state-gotchas.md §3`.

### Cross-page navigation via `st.switch_page`
```python
if st.button("→ Opportunities"):
    st.switch_page("pages/1_Opportunities.py")
```

### Pre-seeding edit forms — use the `_edit_form_sid` sentinel
Re-seeding widget session_state only works when gated by a selection-id
sentinel — otherwise Streamlit's widget-value trap keeps the old values.
See `docs/dev-notes/streamlit-state-gotchas.md §2`.

### Coerce NaN cells with `_safe_str` before feeding into widgets
Pandas returns `float('nan')` for NULL TEXT cells, which crashes widget
protobuf serialisation. See `docs/dev-notes/streamlit-state-gotchas.md §1`.

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
  Current files: `test_config.py`, `test_database.py`, `test_exports.py`,
  `test_opportunities_page.py`, `test_app_page.py`.
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
- `pytest.ini` has `pythonpath = .` so `pytest` runs without `PYTHONPATH=.`
  prefix (fix scheduled for v1.1 ship-prep).

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
   severity, status (fixed inline / deferred / kept-by-design).
3. **Junior-engineer Q&A** — 5–10 questions a reviewer new to the code
   might ask, answered in the didactic style. This is the teaching layer.
4. **Verdict** — Approve / Approve with nits / Request changes.

**Severity scale**

| Icon | Meaning | Action |
|------|---------|--------|
| 🔴 | Bug (behaviour wrong) | Fix before merge |
| 🟠 | Drift (doc↔code or code↔code inconsistency) | Fix before merge |
| 🟡 | Polish (readability, naming, comment gap) | Fix if cheap; defer if costly |
| 🟢 | Future (post-v1 or v2 concern) | Log in backlog |

**Kept-by-design observations** belong in the Q&A section, not Findings —
they are not defects.

---

## 11. Git Workflow — Summary

**Branches:** `main` is stable; all work on `feature/<name>`; merge via PR.

**Commit message format:**
```
<type>(<optional-scope>): <short imperative description>   ≤ 72 chars

<optional body: what and why>
```

**Types:** `feat` · `fix` · `schema` · `config` · `refactor` · `test` ·
`docs` · `review` · `chore`

**TDD cadence:** `test:` (red) → `feat:` (green) → `chore:` (tracker rollup).

**Version tags (from v1.1):** `v0.x.0` for each phase shipped; `v1.0.0` at
first publishable release; `v1.x.y` post-v1. Retroactive tags have been
applied: `v0.1.0` (Phase 3) · `v0.2.0`–`v0.4.0` (Phase 4 T1–T3).

**What never goes in git:** `postdoc.db` · `.venv/` · `.env` · `__pycache__/`
· `CLAUDE.md` · `PHASE_*_GUIDELINES.md` (gitignored from v1.1).

**Pre-commit checklist:**
- [ ] `pytest tests/ -q` passes
- [ ] `pytest -W error::DeprecationWarning tests/ -q` passes
- [ ] No `print()` debug left in
- [ ] `git diff --staged` shows only intended changes
- [ ] `postdoc.db` is not staged

**For depth** — branching details, commit-granularity examples, undo levels,
tagging mechanics, "when you're stuck" — see
[`docs/dev-notes/git-workflow-depth.md`](docs/dev-notes/git-workflow-depth.md).

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
| Tagging new milestones as `v1-phase-N` | Superseded by `v0.x.y` scheme in v1.1 |
