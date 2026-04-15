# Implementation Guidelines
_Read this at the start of every coding session. These rules ensure the codebase stays consistent across sessions and contributors._

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
| Package | Minimum |
|---------|---------|
| streamlit | 1.35 |
| plotly | 5.22 |
| pandas | 2.2 |
| sqlite3 | stdlib — no install needed |

**Never install packages globally.** Always install inside `.venv`.

---

## 2. File & Module Rules

### The import contract (enforced, no exceptions)
```
config.py     ← imports nothing from this project
database.py   ← imports config; never imports streamlit
exports.py    ← imports database, config; never imports streamlit
app.py        ← imports database, config
pages/*.py    ← imports database, config; never imports exports directly
```

`exports.write_all()` is called inside `database.py` write functions — page files never call it directly.

### One responsibility per file
- `database.py` — SQL only. No display logic, no st.* calls.
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

### Database columns
- All lowercase with underscores: `position_name`, `deadline_date`, `req_cv`
- Requirement flags prefixed `req_`: `req_cv`, `req_cover_letter`
- Materials-done flags prefixed `done_`: `done_cv`, `done_cover_letter`
- Date fields suffixed `_date`: `asked_date`, `submitted_date`, `deadline_date`
- Boolean-like integer fields: `0` = false, `1` = true (SQLite has no BOOLEAN type)

### Streamlit pages
- Filename format: `N_Title.py` where N is the sort order integer
- Page title set with `st.title()` as the first visible element

---

## 4. Type Hints & Docstrings

All **public functions** (not prefixed with `_`) in `database.py` and `exports.py` require:
- Type hints on all parameters and return values
- A one-line docstring if the function name is not fully self-explanatory

```python
# Good
def get_upcoming_deadlines(days: int) -> pd.DataFrame:
    """Return positions with deadline_date within the next `days` days."""
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

### Always use parameterised queries — never f-strings in SQL
```python
# GOOD
cursor.execute("SELECT * FROM positions WHERE status = ?", (status,))

# BAD — SQL injection risk even in personal tools; teaches bad habits
cursor.execute(f"SELECT * FROM positions WHERE status = '{status}'")
```

### Connection pattern (use context manager)
```python
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "postdoc.db"

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # enables dict-style column access
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# In every write function:
with _connect() as conn:
    conn.execute("INSERT INTO ...", (...))
    # conn.commit() is called automatically by context manager
```

### Every write function ends with an export call
```python
def add_position(fields: dict) -> int:
    with _connect() as conn:
        ...
    exports.write_all()   # ← always last line of every write function
    return new_id
```

---

## 6. Config Usage Rules

- **Never hardcode a status string, priority value, or vocabulary option** in any file other than `config.py`.
- Always import the constant and use it:
```python
# GOOD
from config import STATUS_VALUES
st.selectbox("Status", STATUS_VALUES)

# BAD
st.selectbox("Status", ["[OPEN]", "[APPLIED]", "[INTERVIEW]", ...])
```
- When adding a new document type (e.g., "Portfolio"), add it to `REQUIREMENT_DOCS` in `config.py` only. The form, the DB schema query, and the export will pick it up automatically.

---

## 7. Streamlit Patterns

### Always use controlled inputs for enumerated values
```python
status = st.selectbox("Status", config.STATUS_VALUES)
priority = st.selectbox("Priority", config.PRIORITY_VALUES)
```

### Always use `st.date_input()` for dates — never `st.text_input()`
```python
# GOOD — returns a Python date object; format enforced
deadline = st.date_input("Deadline", value=None)
deadline_str = deadline.isoformat() if deadline else None   # store as "YYYY-MM-DD"

# BAD — user can type anything
deadline = st.text_input("Deadline (YYYY-MM-DD)")
```

### Use `st.form()` for all data writes
Prevents partial saves on widget interaction:
```python
with st.form("add_position"):
    name = st.text_input("Position Name")
    submitted = st.form_submit_button("Save")
if submitted:
    database.add_position({"position_name": name, ...})
    st.success("Position added.")
    st.rerun()
```

### Show errors with `st.error()`, successes with `st.success()`
Never use `print()` for user-facing messages in Streamlit.

---

## 8. Error Handling

This is a personal tool. The goal is **clear messages, not silent failures**.

```python
# Preferred pattern for database operations
try:
    database.add_position(fields)
    st.success("Position saved.")
except sqlite3.IntegrityError as e:
    st.error(f"Could not save: {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
    raise   # re-raise so the full traceback appears in the terminal
```

- Do not `try/except` around everything. Let unexpected errors propagate to the terminal where they can be diagnosed.
- Do validate user input before calling database functions: check required fields are non-empty before attempting a write.

---

## 9. Git Commit Conventions

Format: `<type>: <short description>` (imperative mood, ≤ 72 chars)

| Type | When |
|------|------|
| `feat` | New feature or page |
| `fix` | Bug fix |
| `schema` | Database schema change |
| `config` | Changes to config.py |
| `refactor` | Code reorganisation, no behaviour change |
| `docs` | CLAUDE.md, GUIDELINES.md, roadmap.md, comments |
| `chore` | requirements.txt, .gitignore, tooling |

**Examples:**
```
feat: add quick-add form to Opportunities page
schema: split deadline_date from deadline_note
config: add req_portfolio to REQUIREMENT_DOCS
fix: materials readiness count excludes Optional docs
docs: update roadmap — Phase 2 complete
```

One commit per phase minimum. Commit working code; never commit a broken app to main.

---

## 10. What Not to Do

| Avoid | Reason |
|-------|--------|
| Storing computed values in the DB | Materials readiness, days-until-deadline — derive at query time |
| Adding columns not in `config.REQUIREMENT_DOCS` without updating config | Breaks the auto-generate logic in exports.py |
| Using `st.experimental_*` APIs | These are deprecated in Streamlit ≥ 1.35 |
| Magic numbers in page files | Put thresholds in `config.py` (e.g., `DEADLINE_ALERT_DAYS`) |
| Catching `Exception` broadly and swallowing it silently | Hides real bugs |
| Modifying `exports/` files by hand | They are generated; edits will be overwritten |
