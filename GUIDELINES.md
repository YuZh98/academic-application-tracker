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
with st.form("add_position_form"):   # form id ≠ any widget key inside
    name = st.text_input("Position Name", key="add_position_name")
    submitted = st.form_submit_button("Save")
if submitted:
    database.add_position({"position_name": name, ...})
    st.toast("Position added.")      # st.toast survives st.rerun; st.success gets clobbered
    st.rerun()
```

**Form id ≠ any widget key inside the form.** `st.form` registers with
`writes_allowed=False`; a collision raises at render. Convention: suffix
form ids with `_form` (e.g. `edit_notes_form` with widget key `edit_notes`).

### Show errors with `st.error()`, successes with `st.toast()`
Never use `print()` for user-facing messages in Streamlit.
Prefer `st.toast` over `st.success` — toasts persist across `st.rerun()`;
`st.success` is cleared on the next script run.

---

## 8. Error Handling

This is a personal tool. The goal is **clear messages, not silent failures**.

```python
# Preferred pattern for user-facing database writes
try:
    database.add_position(fields)
    st.toast("Position saved.")
except sqlite3.IntegrityError as e:
    st.error(f"Could not save: {e}")
except Exception as e:
    st.error(f"Unexpected error: {e}")
    # Do NOT re-raise in user-facing save paths — re-raising renders the
    # very traceback the handler exists to hide. Log to the terminal via
    # the exception context if needed; the friendly message is the UX.
```

- Do not `try/except` around everything. Let unexpected errors **in non-UI code paths** (e.g. startup, `init_db`) propagate to the terminal where they can be diagnosed.
- In user-facing save/delete paths, catch `Exception` broadly, show `st.error(...)`, and **do not re-raise** — the point of the handler is to hide the traceback from the end user.
- Do validate user input before calling database functions: check required fields are non-empty (including whitespace-only strings) before attempting a write.

---

## 9. Git Workflow & Commit Conventions

### The single most important rule
**Commits are permanent checkpoints, not save files.**
Every commit should leave the repository in a state that could ship — tests passing, no debug code, no `print()` statements left in, no partial features half-wired.

---

### Branch strategy

```
main            ← always stable; only working code lands here
feature/<name>  ← all new development; merge to main when done
```

**When to create a feature branch:**
```bash
# Starting a new phase or multi-session feature
git checkout -b feature/phase-3-opportunities
```

**When to merge back to main:**
Only when the feature is complete and all tests pass.
```bash
git checkout main
git merge feature/phase-3-opportunities --no-ff   # --no-ff preserves history
git tag v1-phase-3                                 # tag each completed phase
```

For a solo project, you can work directly on main for small fixes, but use feature branches for any multi-session work. The discipline pays off when something breaks and you need to find the offending commit.

---

### Commit frequency and granularity

**Commit once per logical change — not once per session, not after every line.**

Too coarse:
```
feat: Phase 2 complete
```
This lumps schema design, all CRUD functions, dashboard queries, and test code into one diff. When a query bug is found later, you cannot revert just the query.

Too fine:
```
wip: started add_position
wip: added conn.execute line
wip: debugging
```
Meaningless history; can't rollback to anything meaningful.

Just right:
```
feat: add init_db with schema and migration loop
feat: add position CRUD (add, get, update, delete)
feat: add upsert_application
feat: add dashboard queries (count, deadlines, interviews, recommenders)
test: add 98-test suite for config and database
```

---

### Commit message format

```
<type>: <short description>   ← subject line: imperative mood, ≤ 72 chars

<optional body>               ← blank line, then longer explanation if needed
<optional body>               ← what and WHY, not how (the diff shows how)
```

| Type | When |
|------|------|
| `feat` | New feature or page |
| `fix` | Bug fix |
| `schema` | Database schema change |
| `config` | Changes to config.py |
| `refactor` | Code reorganisation, no behaviour change |
| `test` | Adding or updating tests |
| `docs` | CLAUDE.md, GUIDELINES.md, roadmap.md, comments |
| `chore` | requirements.txt, .gitignore, tooling |

**Examples (subject only):**
```
feat: add quick-add form to Opportunities page
schema: split deadline_date from deadline_note
config: add req_portfolio to REQUIREMENT_DOCS
fix: materials readiness count excludes Optional docs
docs: update roadmap — Phase 2 complete
```

**Example with body (when the why isn't obvious):**
```
fix: move PRAGMA foreign_keys inside try block in _connect()

The PRAGMA call was outside the try/finally, so a rare connection-setup
failure would leak the file descriptor. Moved inside the try so conn.close()
is guaranteed via the finally block regardless of where the exception occurs.
```

---

### Staging discipline — review before you commit

Never `git add -A` or `git add .` blindly. You will accidentally commit:
- Debug `print()` statements
- Leftover `TODO` that shouldn't ship
- The `.env` file with your API keys
- `postdoc.db` (personal data — already gitignored, but worth knowing why)

**Preferred workflow:**
```bash
# See what changed
git status
git diff                    # unstaged changes
git diff --staged           # what is already staged (review this BEFORE committing)

# Stage specific files (preferred)
git add config.py database.py

# Or stage specific hunks (when a file has both good and debug changes)
git add -p database.py      # interactive: approve/skip each chunk
```

**Pre-commit checklist:**
- [ ] `python3 -m pytest` passes
- [ ] No `print()` debug statements left in
- [ ] No hardcoded paths or secrets
- [ ] `postdoc.db` is NOT staged (check `git status`)
- [ ] `git diff --staged` shows only what you intend to commit

---

### What NEVER goes in git

| File / pattern | Why | How it's handled |
|---|---|---|
| `postdoc.db` | Personal data; binary; cannot be merged | Listed in `.gitignore` |
| `.venv/` | Platform-specific binaries; 200+ MB | Listed in `.gitignore` |
| `.env` | Secrets and credentials | Listed in `.gitignore` |
| `__pycache__/` | Auto-generated bytecode | Listed in `.gitignore` |
| `exports/` markdown | Auto-generated; committed as a backup | Exception: committed intentionally as human-readable backup |

If you accidentally commit a secret, it is not enough to delete it in a later commit — the secret is still in history. You must rewrite history (`git filter-branch` or `git filter-repo`). Avoid the problem entirely by checking `git diff --staged` before every commit.

---

### Undoing mistakes — three levels

**Level 1 — Unstage a file you accidentally staged (nothing is lost):**
```bash
git restore --staged database.py   # removes from staging area; file unchanged
```

**Level 2 — Discard changes to a file (irreversible — file goes back to last commit):**
```bash
git restore database.py            # ← permanent; make sure you mean it
```

**Level 3 — Undo the last commit but keep the changes (staged):**
```bash
git reset --soft HEAD~1            # last commit is gone; changes back in staging area
```

**Level 4 — Revert a commit safely (creates a new undo commit; history preserved):**
```bash
git revert <commit-hash>           # safest; never rewrites history
```

**Rule of thumb:** `restore` and `reset --soft` are safe for local work. Never force-push to a shared branch. If you are not sure, `git stash` first.

---

### Tagging milestones

Tag each completed phase so you can return to any known-good state:
```bash
git tag v1-phase-1    # after Phase 1 is complete and committed
git tag v1-phase-2    # after Phase 2
# etc.

git checkout v1-phase-1   # return to that exact state (read-only)
```

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
