# Code Review: Phase 2
**Branch:** _(direct-to-main; pre-branch-workflow)_
**Scope:** Phase 2 — `database.py` + `exports.py` + `config.py` interaction review.
**Commit reviewed:** Phase 2 — `database.py`, `exports.py`
**Date:** 2026-04-16
**Files reviewed:** `database.py`, `exports.py`, `config.py` (for interaction)
**Verdict:** Approved with fixes applied

---

## Summary

`database.py` is well-structured and faithful to DESIGN §7. The module contract is respected: no Streamlit imports, parameterized queries throughout, deferred export pattern correctly implemented. The schema generation and migration loop in `init_db()` are elegant. Four fixes were applied before Phase 3 begins. One design improvement (config-driven terminal statuses) strengthens the Open/Closed Principle already established in Phase 1. `exports.py` stub is minimal and correct.

---

## Findings

### F1 — Connection leak when PRAGMA setup raises *(Moderate — Fixed)*
**File:** `database.py` **Lines:** 28–38 (original)

The `PRAGMA foreign_keys = ON` call was placed **outside** the `try/finally` block:

```python
# BEFORE (defective)
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")   # ← outside the try
try:
    yield conn
    conn.commit()
except Exception:
    conn.rollback()
    raise
finally:
    conn.close()   # ← never reached if PRAGMA raised
```

If `conn.execute("PRAGMA foreign_keys = ON")` raised (rare, but theoretically possible if the connection was corrupt), the `finally` block would never execute, leaving an open file descriptor. SQLite holds a file lock on the `.db` file for the lifetime of an open connection. A leaked connection means the database could become inaccessible until the process exits.

**Fix applied:** Moved the PRAGMA call inside the `try` block so `conn.close()` in `finally` is always reached:
```python
# AFTER (correct)
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
    conn.close()   # ← guaranteed regardless of where the exception occurred
```

**Lesson:** The `finally` block only covers the `try` it is attached to. Code that allocates a resource (a connection, file handle, lock) must be inside the `try` that owns the `finally` which releases it.

---

### F2 — `update_position` and `update_recommender` crash on empty `fields` *(Moderate — Fixed)*
**File:** `database.py` **Lines:** 186–198, 291–303 (original)

Both functions build a dynamic `SET` clause by joining over `fields.keys()`. When `fields = {}`:
```python
set_clause = ", ".join(f"{k} = ?" for k in {})
# → set_clause = ""
# → SQL: "UPDATE positions SET  WHERE id = ?"
#                        ^^^^ empty — syntax error
```
SQLite raises `OperationalError: near "WHERE": syntax error`.

No page currently calls these with an empty dict, but defensively — and because future page code will — a guard is needed:

```python
# AFTER (correct)
def update_position(position_id: int, fields: dict[str, Any]) -> None:
    if not fields:
        return          # calling update with nothing to update is a no-op, not an error
    ...
```

**Lesson:** Whenever you build SQL dynamically from a collection, ask: "What happens when the collection is empty?" An empty set of changes is a valid no-op; it should not crash.

---

### F3 — `upsert_application` crashes on empty `fields` *(Minor — Fixed)*
**File:** `database.py` **Lines:** 227–244 (original)

Same root cause as F2. `ON CONFLICT(position_id) DO UPDATE SET ` with an empty SET clause is invalid SQL. Added the same `if not fields: return` guard.

---

### F4 — `fields` parameters typed as bare `dict` *(Minor — Fixed)*
**File:** `database.py` **Lines:** 143, 186, 227, 249, 291 (original)

All mutable-fields parameters were typed as `dict` without key/value types:
```python
# BEFORE
def add_position(fields: dict) -> int:
```
This tells a type checker and the next reader nothing about what the dict contains. Changed to `dict[str, Any]` (requiring `from typing import Any`):
```python
# AFTER
def add_position(fields: dict[str, Any]) -> int:
```
The values can be `str`, `int`, or `None` — `Any` is honest about that without overpromising. The keys are always `str` column names.

---

### F5 — Terminal status strings hardcoded in `database.py` *(Moderate — Fixed)*
**File:** `database.py` **Lines:** 344 (original)

`get_upcoming_deadlines` contained three hardcoded string literals:
```python
# BEFORE — violates GUIDELINES §6
params=(today, cutoff, "[CLOSED]", "[REJECTED]", "[DECLINED]"),
```
This directly violates the project rule: *"Never hardcode a status string in any file other than config.py."* If a new terminal status (e.g., `[WITHDRAWN]`) is added to `STATUS_VALUES` in the future, `get_upcoming_deadlines` would silently continue showing it — the rule is declared but not enforced by the architecture.

**Fix applied:** Added `TERMINAL_STATUSES: list[str]` to `config.py` with an import-time guard, and updated `database.py` to derive the IN-list from it:
```python
# config.py addition
TERMINAL_STATUSES: list[str] = ["[CLOSED]", "[REJECTED]", "[DECLINED]"]
assert set(TERMINAL_STATUSES) <= set(STATUS_VALUES), (...)

# database.py — now config-driven
terminal = tuple(config.TERMINAL_STATUSES)
not_in   = ", ".join("?" * len(terminal))
params   = (today, cutoff, *terminal)
```
Now adding a new terminal status to `config.py` automatically propagates to the deadline filter, the materials readiness query, and any future query that reads `TERMINAL_STATUSES`.

---

### F6 — No column-name validation on dynamic `fields` parameter *(Informational — No action)*

`add_position`, `update_position`, and similar functions trust that `fields.keys()` contains only valid column names. The column names are f-stringed into SQL (not parameterized — values are parameterized, but column names are structural). If a page file accidentally passed `{"invalid col": "value"}` or `{"status = '[OPEN]'; DROP TABLE positions; --": "value"}`, SQLite would raise an `OperationalError` (the parser rejects invalid identifiers), but the error message would be cryptic.

An assertion at the top of `add_position` could validate against the known schema:
```python
# Possible defensive addition (not applied — internal tool, callers are trusted)
known_cols = {r["name"] for r in conn.execute("PRAGMA table_info(positions)").fetchall()}
unknown = set(fields) - known_cols
assert not unknown, f"Unknown columns passed to add_position: {unknown}"
```
Not applied at this stage — this is an internal API, callers are the page files we write ourselves, and the SQLite error is informative enough. Worth revisiting if the project ever has external contributors.

---

## Five Questions from a Junior Engineer

---

### Q1 — "Why does `_connect()` use `@contextmanager` and `yield`? I've never seen `yield` inside a function that isn't a generator. Can't I just call `conn = _connect()` and `conn.close()` at the end?"

**Answer:**

You can — but then *you* are responsible for closing the connection, and one `if/else` branch with a missing `conn.close()` means you have a leaked file handle and a locked database.

`@contextmanager` turns a function with a single `yield` into a context manager. Everything *before* `yield` runs when you enter the `with` block. Everything *after* runs when you exit — whether you exit normally or via an exception. The `try/except/finally` structure we have in `_connect()` is the key part:

```python
@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn          # ← hand control to the caller's with-block
        conn.commit()       # ← runs if no exception was raised
    except Exception:
        conn.rollback()     # ← runs only if an exception occurred
        raise
    finally:
        conn.close()        # ← runs ALWAYS, no matter what

# Caller:
with _connect() as conn:
    conn.execute("INSERT ...")
    if something_wrong:
        raise ValueError("oops")    # ← _connect() STILL cleans up
```

Without the context manager:
```python
conn = sqlite3.connect(DB_PATH)
try:
    conn.execute("INSERT ...")
    if something_wrong:
        raise ValueError("oops")   # ← without except/finally here, conn leaks
    conn.commit()
    conn.close()
except Exception:
    conn.rollback()
    conn.close()   # ← easy to forget; easy to call twice; code is duplicated
```

The pattern you want is: "acquire → use → release, guaranteed." In C++ this is called RAII. In Python it's the context manager protocol. The rule: every resource that must be closed (connections, file handles, locks, network sockets) should be opened inside a `with` block.

---

### Q2 — "In `add_position`, you build `cols` from `fields.keys()` and put it in an f-string. But in `get_upcoming_deadlines`, you use `?` for the status values. You use f-strings for some things and `?` for others. What's the rule? Isn't this inconsistent?"

**Answer:**

It's the most important security rule in database programming, so this is worth spending time on.

The distinction is: **structure vs. data**.

- **Structure** (column names, table names, SQL keywords): determines *how* SQL is parsed. These go into f-strings — but only when they come from your own code (config constants), never from user input.
- **Data** (values stored in rows): what the SQL operates *on*. Always use `?` parameterized placeholders.

The reason parameterized queries are required for data:

```python
# Imagine a user types this into the position name field:
evil = "Test'); DROP TABLE positions; --"

# If you f-string it:
conn.execute(f"INSERT INTO positions (position_name) VALUES ('{evil}')")
# → INSERT INTO positions (position_name) VALUES ('Test'); DROP TABLE positions; --')
# SQLite sees TWO statements. The positions table is gone.

# With parameterization:
conn.execute("INSERT INTO positions (position_name) VALUES (?)", (evil,))
# → SQLite treats evil as a literal string value — single quotes inside
#   the value are automatically escaped. The table is safe.
```

Column names (structure) are different: `conn.execute("SELECT ? FROM positions", ("status",))` does NOT work — the `?` placeholder is for values, not identifiers. That's why we f-string column names. But column names come from `config.REQUIREMENT_DOCS`, which we wrote ourselves — they're constants, not user input.

The rule in one sentence: **anything that arrived from outside your code (user input, file content, external API) goes through `?`; anything that comes from your own config constants can go in an f-string, but document why.**

---

### Q3 — "Why does every write function call `exports.write_all()` at the end? If I'm just changing one field with `update_position`, we're rewriting three markdown files. That seems wasteful. Why not let the page call `exports.write_all()` once at the end of the user session?"

**Answer:**

Because discipline doesn't scale. Let me show you what "let the page call it" looks like after Phase 6 is written:

```
Phase 3: add_position → page calls exports.write_all() ✓
Phase 3: update_position → page calls exports.write_all() ✓
Phase 5: upsert_application → page calls exports.write_all() ✓
Phase 5: add_recommender → page calls exports.write_all()  ← we wrote this

# Six months later, someone adds:
Phase 8: bulk_close_positions() → page calls... hmm, did we remember?
```

If the responsibility lives in the page, it requires every person who adds a write function — across every session, for the lifetime of the project — to remember to add the call. One forgotten call = silently stale markdown files.

If the responsibility lives in `database.py`, inside every write function, it is structurally impossible to forget. New write functions are copy-paste from existing ones; they include the export call by default.

The cost is real but acceptable: rewriting three small markdown files costs ~5ms. We're talking about a personal tracker with tens of rows. The trade-off is correctness and maintainability for a tiny runtime cost.

This is an application of the **Principle of Least Surprise** and **Don't Repeat Yourself**. The invariant "after every write, the exports are current" should be enforced once, in one place — not scattered across four page files and six write functions.

---

### Q4 — "Why is `upsert_application` named 'upsert' instead of 'update_application'? And why use the complex `ON CONFLICT DO UPDATE` syntax? Couldn't you just SELECT to check if the row exists, then INSERT or UPDATE based on the result?"

**Answer:**

`upsert` = UPDATE + INSERT. It means: "update if the row exists; insert if it doesn't." A plain `UPDATE` would silently do nothing on a brand-new row. A plain `INSERT` would fail with a constraint violation on an existing row.

The "SELECT first, then INSERT or UPDATE" pattern is the obvious approach but has a fundamental flaw called a **race condition** (also known as a TOCTOU bug — Time Of Check, Time Of Use):

```python
# DANGEROUS: SELECT-then-act
row = conn.execute(
    "SELECT 1 FROM applications WHERE position_id=?", (pos_id,)
).fetchone()

# ← DANGER ZONE: another process could INSERT here between this SELECT and the next write

if row:
    conn.execute("UPDATE applications SET applied_date=? WHERE position_id=?", ...)
else:
    conn.execute("INSERT INTO applications (position_id, applied_date) VALUES (?,?)", ...)
```

If a second session executes the same function between your SELECT and your INSERT, both see "row doesn't exist," both try to INSERT, and one of them gets a UNIQUE constraint violation.

`ON CONFLICT DO UPDATE` is a single atomic operation. The database engine checks existence and writes in one step — no window for another operation to slip in between:

```sql
INSERT INTO applications (position_id, applied_date) VALUES (?, ?)
ON CONFLICT(position_id) DO UPDATE SET applied_date = excluded.applied_date
```

This project is single-user, so the race condition would never trigger in practice. But:
1. The upsert version is shorter and its intent is explicit in the name.
2. Learning the correct pattern now means you won't write the buggy SELECT-first version in a multi-user app later.
3. It saves one database round-trip (the SELECT), which matters in high-traffic systems.

---

### Q5 — "In `compute_materials_readiness`, you build the `has_any_req` and `all_done` conditions with f-strings and loop over `config.REQUIREMENT_DOCS`. Couldn't you just fetch all positions into a DataFrame and compute the counts in Python? Seven columns, a few dozen rows — it would be much easier to read."

**Answer:**

You could. For 20 rows it would be imperceptible. But I want to show you why the SQL approach is better, because the habit matters.

The Python approach would look like:
```python
df = get_all_positions()
active = df[df["status"].isin(["[OPEN]", "[APPLIED]", "[INTERVIEW]"])]
# Then for each row, check if any req_* = 'Y', then whether all done_* = 1 for those...
# This requires at least 2-3 pandas operations and a loop or apply()
```

The SQL approach:
```python
SUM(CASE WHEN req_cv != 'Y' OR done_cv = 1
         AND req_cover_letter != 'Y' OR done_cover_letter = 1
         AND ...
         THEN 1 ELSE 0 END) AS ready
```

**Why SQL wins here:**

1. **Volume**: `SELECT *` fetches every column (37 columns × N rows). `compute_materials_readiness` returns two integers regardless of how many rows exist. If you have 500 positions, the SQL version is 500× more efficient in data transfer.

2. **Location**: The data lives in SQLite. SQLite is written in C, runs close to the disk, and is optimized for exactly this kind of aggregation. Moving data to Python to count it in Python is called "shipping data to the computation." The alternative — "shipping the computation to the data" (SQL) — is almost always faster.

3. **Semantics**: `SUM(CASE WHEN condition THEN 1 ELSE 0 END)` is idiomatic SQL. Every experienced SQL developer reads it instantly as "count rows satisfying condition." The Python equivalent requires reading 3-4 lines of pandas before the intent is clear.

4. **Habit**: A future version of this tracker might have 500 positions. If you wrote "fetch all, compute in Python" for everything, and the app slows down at 500 rows, finding all the N+1 queries and fix them is painful. Writing close-to-the-data SQL from the start prevents the slowdown from ever appearing.

The general rule: **filter and aggregate in SQL; format and display in Python**.

---

## What Looked Good

| Observation | Why it matters |
|-------------|---------------|
| `_connect()` context manager with commit/rollback | Resource safety is structural, not dependent on every caller remembering to close |
| `init_db()` migration loop using `PRAGMA table_info` | Adding a document type to config.py is a genuinely zero-touch operation |
| `cursor.lastrowid` used correctly — captured before `with` block exits | Closing the connection doesn't invalidate lastrowid, but capturing it explicitly avoids confusion |
| `pd.read_sql_query` used for read functions, manual `conn.execute` for writes | Appropriate tool for each job; DataFrames for display, cursor for writes |
| `date.today().isoformat()` for date comparisons, not `date('now')` | Correctly avoids SQLite's UTC offset when the user is in a non-UTC timezone |
| Deferred `import exports as _exports` pattern explained in comments | The next session won't be confused by seeing an import inside a function |
| `compute_materials_readiness` excludes positions with no required docs | Correctly avoids polluting the dashboard with positions that haven't been configured yet |
| All values in SQL queries parameterized with `?` | No SQL injection surface, even for internal tools |

---

## Lessons and Good Practices from This Review

### 1. Your `finally` block only protects the `try` it's attached to
Every line between "acquire resource" and the start of the `try` is unprotected. If it raises, the `finally` doesn't run. Move all post-acquisition setup inside the `try`.

### 2. Dynamic SQL has two kinds of inputs — treat them differently
- **Column names** (structural): safe to f-string *only if* they come from your own code. Document this explicitly in every function that does it.
- **Values** (data): always `?` parameterized. This is non-negotiable, even for personal tools. The habit saves you when the code later handles real user input.

### 3. Guard against degenerate inputs at the boundary
Functions that build SQL dynamically from collections must handle empty collections. `update_position({})` is a valid no-op — it shouldn't crash. Ask yourself: "what does this function do when the key argument is empty, zero, or None?"

### 4. Config constants belong in config.py — period
If `GUIDELINES.md` says "never hardcode a status string outside config.py," that rule applies to `database.py` too — not just page files. A codebase where the rule has exceptions is a codebase where the rule is eventually ignored entirely.

### 5. Push aggregation to the database
When you need counts or sums, do them in SQL with `SUM(CASE WHEN ...)` or `COUNT(*)` + `GROUP BY`. Fetching all rows to count them in Python transfers unnecessary data and is orders of magnitude slower for large tables. SQLite can aggregate a million rows faster than pandas can load them into memory.

### 6. Make invariants structurally impossible to violate
Calling `exports.write_all()` inside every write function means the "exports are always current" invariant cannot be broken by forgetting. The alternative — relying on callers to remember — is a time bomb. When in doubt, make the safe behavior the default behavior.

### 7. Type hints are documentation, not decoration
`dict` says "a dict." `dict[str, Any]` says "a dict where keys are column names (strings) and values are any SQLite-compatible type." The second form prevents the reader from having to trace all callers to understand the shape. Specific type hints also let IDEs flag type errors before you run the code.

---

## Post-Review State

After applying all five fixes, the test suite was re-run:
- `_connect()` PRAGMA inside try block ✓
- `update_position({})` is a silent no-op ✓
- `update_recommender({})` is a silent no-op ✓
- `upsert_application({})` is a silent no-op ✓
- `config.TERMINAL_STATUSES` drives `get_upcoming_deadlines` filter ✓
- `TERMINAL_STATUSES` guard assertion fires on drift ✓
- `dict[str, Any]` on all `fields` parameters ✓
- **103/103 tests pass**
