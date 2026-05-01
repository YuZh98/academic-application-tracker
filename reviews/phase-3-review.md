# Phase 3 Tier 1 Code Review
**Branch:** _(direct-to-main; pre-branch-workflow)_
**Scope:** Phase 3 Tier 1 — Quick-Add form + empty state on `pages/1_Opportunities.py`.
**Verdict:** Request Changes (5 findings, all fixed in this review).
**Files reviewed:** `pages/1_Opportunities.py`, `tests/test_opportunities_page.py`
**Date:** 2026-04-17
**Reviewer:** Claude (skeptical + didactic)

---

## Summary

The quick-add form and empty state are structurally sound: the import contract is respected, controlled vocabularies are used correctly, form state is managed with `st.form()`, and the test suite covers all six fields plus key behaviour paths. However, one guideline is actively violated (no `try/except` around the DB write), one test-side design choice creates a fragile coupling to Streamlit internals, and whitespace-only input slips past validation. All five findings are fixed in this review.

---

## Findings

| # | File | Line | Issue | Severity |
|---|------|------|-------|----------|
| F1 | `pages/1_Opportunities.py` | 43–45 | No `try/except` around `database.add_position()` — violates GUIDELINES.md §8 | 🔴 Critical |
| F2 | `tests/test_opportunities_page.py` | 20 | `SUBMIT_KEY` hardcodes internal Streamlit key format `"FormSubmitter:{form}-{label}"` — breaks silently on version update | 🟡 Moderate |
| F3 | `pages/1_Opportunities.py` | 19–26, 31 | Text inputs not `.strip()`ped; whitespace-only `position_name` (e.g., `"   "`) is truthy so bypasses `if not position_name` guard and inserts a blank row | 🟡 Moderate |
| F4 | `pages/1_Opportunities.py` | 30 | `if submitted:` block lives inside the `with st.expander()` context — GUIDELINES.md §7 shows this pattern outside any container; error/success messages render inside the expander and are hidden when it collapses | 🟢 Minor |
| F5 | `pages/1_Opportunities.py` | 34 | `fields: dict` annotation; Phase 2 review already established `dict[str, Any]` as the project standard | 🟢 Minor |

---

## Finding Details

### F1 — No error handling for the database write (Critical)

**Current code (`pages/1_Opportunities.py:43–45`):**
```python
database.add_position(fields)
st.success(f'Added "{position_name}" to your list.')
st.rerun()
```

**Problem:** If `database.add_position()` raises — e.g., `sqlite3.OperationalError: database is locked`, `disk full`, or a future `UNIQUE` constraint — the exception propagates unhandled. Streamlit renders a full Python traceback in the browser. GUIDELINES.md §8 explicitly shows the pattern to follow:

```python
try:
    database.add_position(fields)
    st.success("Position saved.")
except Exception as e:
    st.error(f"Could not save position: {e}")
    raise   # re-raise so the full traceback appears in the terminal
```

The `raise` after `st.error()` is intentional: the user sees a clear message, and the developer still gets the full traceback in the terminal for diagnosis. Swallowing the exception silently would hide real bugs.

**Fix:** Wrap the write in `try/except Exception`.

---

### F2 — `SUBMIT_KEY` encodes an internal Streamlit convention (Moderate)

**Current code (`tests/test_opportunities_page.py:20`):**
```python
SUBMIT_KEY = "FormSubmitter:quick_add_form-+ Add Position"
```

**Problem:** This string is the key Streamlit auto-generates for `st.form_submit_button()` when no explicit `key=` is given. The format — `"FormSubmitter:{form_key}-{button_label}"` — is undocumented and an internal implementation detail. If Streamlit changes it in a future version, all 6 behaviour tests fail with a cryptic `KeyError` that looks like a widget is missing, not like a version mismatch.

The root cause is in the page file: `st.form_submit_button("+ Add Position")` has no `key=` argument. Adding one gives both the page and the test explicit, stable names.

**Fix:** Add `key="qa_submit"` to `st.form_submit_button()` in the page; update `SUBMIT_KEY` in the test.

---

### F3 — Whitespace-only input bypasses validation (Moderate)

**Current validation (`pages/1_Opportunities.py:31`):**
```python
if not position_name:
```

**Problem:** In Python, `not "   "` evaluates to `False` — a string of spaces is truthy. So a user who hits the spacebar five times and clicks "Add Position" passes this check and inserts a row with `position_name = "   "`. The empty-state check will then show the row count ("1 position(s) tracked") even though the position has no meaningful name.

Verified in a REPL:
```python
>>> not "   "
False
>>> not "   ".strip()
True
```

**Fix:** Strip all text inputs before use. Update validation to check the stripped value. A new test verifies the fixed behaviour.

---

### F4 — `if submitted:` inside expander context (Minor)

**Current code (indentation at 4 spaces — inside `with st.expander()`):**
```python
with st.expander("Quick Add", expanded=False):
    with st.form(...):
        ...
        submitted = st.form_submit_button(...)

    if submitted:          # ← inside the expander
        ...
        st.error(...)      # renders inside the expander
```

**Problem:** GUIDELINES.md §7 shows `if submitted:` and its side-effect calls (`st.error`, `st.success`) **outside** any containing context manager. When `if submitted:` lives inside the expander, `st.error()` is rendered in the expander's DOM container. If the user collapses the expander — possible after submitting — the error vanishes. More importantly, the guidelines exist to keep page code predictable: feedback should render in the main content area, not nested inside a UI control.

**Fix:** Dedent `if submitted:` to the module level (outside the `with st.expander()` block). Error and success messages then render below the expander, always visible.

---

### F5 — `fields: dict` type annotation (Minor)

**Current code (`pages/1_Opportunities.py:34`):**
```python
fields: dict = {
```

**Problem:** The Phase 2 code review (F4) established `dict[str, Any]` as the project standard, applied to all `fields` parameters in `database.py`. This local variable annotation uses the bare `dict`, which is imprecise — it allows any key and value types without communicating intent.

**Fix:** Change to `dict[str, Any]`; add `from typing import Any` to the imports.

---

## Applied Fixes

| # | Status | Change |
|---|--------|--------|
| F1 | ✅ Applied | Wrapped `database.add_position()` in `try/except Exception` with `st.error()` + `raise` |
| F2 | ✅ Applied | Added `key="qa_submit"` to `st.form_submit_button()`; updated `SUBMIT_KEY` in test |
| F3 | ✅ Applied | Added `.strip()` to all text inputs in submit handler; updated guard to `if not position_name:`; added `test_submit_with_whitespace_only_name_shows_error` |
| F4 | ✅ Applied | Moved `if submitted:` block outside `with st.expander()` |
| F5 | ✅ Applied | Changed `fields: dict` → `fields: dict[str, Any]`; added `from typing import Any` |

---

## What Looks Good

- **Import contract honoured:** `pages/1_Opportunities.py` imports only `streamlit`, `database`, `config` — exactly as required by GUIDELINES.md §2. No `exports` import, no raw SQL.
- **Controlled vocabularies used correctly:** `config.PRIORITY_VALUES` drives the selectbox; status defaults to `STATUS_VALUES[0]` via `database.add_position()` defaults, not a hardcoded string.
- **`st.date_input(value=None)` + `.isoformat()`:** Exactly the pattern prescribed by GUIDELINES.md §7. Consistent handling of optional dates.
- **`st.form()` used for the write:** Prevents partial saves from widget interactions — guideline §7 followed.
- **Test design:** Using real SQLite (no mocks) for integration tests. Catches DB-layer regressions that mock-based tests would miss. Separate per-field structure tests give precise failure messages.
- **`_run_page()` helper:** Centralises the page-launch + exception-guard pattern. All 16 test methods benefit without repetition.

---

## Verdict: Request Changes

F1 (missing error handling) and F3 (whitespace bypass) are correctness bugs. F2 is a test maintainability time-bomb. All five findings are low-effort to fix and the changes are applied in this review.

---

## 5 Questions a Junior Engineer Would Ask

**Q1. Why do we call `st.rerun()` after adding a position? Wouldn't showing the success message and staying on the same page be cleaner?**

Without `st.rerun()`, the `df = database.get_all_positions()` call already ran at the top of the script — before the form was submitted. It returned the old data. The row count at the bottom ("1 position(s) tracked") reflects the state from the beginning of the script run, not the state after the insert. Calling `st.rerun()` forces the script to re-execute from the top, so every widget and query sees the freshly-inserted row. The tradeoff is that the success message appears for one render cycle then disappears. Once Tier 3 adds the full positions table, skipping `st.rerun()` would mean the table doesn't show the new row until the user manually refreshes.

**Q2. Why does `test_submit_twice_creates_two_separate_rows` create a brand-new `AppTest` object for each submission instead of reusing the same `at`?**

After the first submission, `st.rerun()` triggers a re-execution of the page script inside the same `AppTest`. The session state from that run persists inside `at` — including the form's internal state. Starting fresh with `AppTest.from_file(PAGE)` for the second submission avoids any subtle carry-over from the first run: clean session state, clean widget values. This is the safer pattern when testing sequences of user actions that span multiple independent visits to the page.

**Q3. Why does the form expander have `expanded=False` (collapsed by default)? Won't new users miss it?**

DESIGN.md §8 specifies this explicitly: the Quick Add expander starts collapsed so the table is the first thing a returning user sees. The primary daily workflow is reviewing existing positions, not adding new ones. For a brand-new user with an empty DB, the empty-state message ("No positions yet — use Quick Add above") acts as the signpost. The "above" is deliberate — it points up to the collapsed expander.

**Q4. `database.add_position(fields)` receives a `dict` of column names and values. How does it know those column names are safe to put in an SQL `INSERT` statement?**

`database.py` builds the INSERT like this:
```python
cols = ", ".join(fields.keys())
placeholders = ", ".join("?" * len(fields))
conn.execute(f"INSERT INTO positions ({cols}) VALUES ({placeholders})", vals)
```
The column names come from the dict keys — which in the quick-add form are the same strings as `config.QUICK_ADD_FIELDS` (`"position_name"`, `"institute"`, etc.), all of which are known good column names. The VALUES are parameterised (`?`), so there is no injection risk for the data. The column name substitution via f-string is safe here because the names come from `config.py` constants, never from user input. GUIDELINES.md §5 documents this distinction ("f-strings only for column names from config constants").

**Q5. The `test_form_has_X` tests just call `at.text_input(key="qa_X")` and don't assert anything. If the call succeeds, the test passes; if the key doesn't exist, `KeyError` fails the test. Is that intentional?**

Yes, intentionally. `AppTest.__call__(key=...)` raises `KeyError` when the widget is not found — so the test passes if and only if the widget exists and has the right key. There is nothing else to assert about the widget's presence. The explicit `key=` argument in the page code (`key="qa_position_name"`, etc.) is what makes these tests both precise and stable: they test the exact contract between the test and the page.

---

## Lessons

1. **GUIDELINES.md §8 is mandatory, not advisory.** Every database write in a page file needs a `try/except`. "It's a personal tool" is not an excuse — unhandled exceptions produce confusing user experiences and hide bugs during development.

2. **Test keys should be explicit, not inferred.** When you rely on an auto-generated key, you create a hidden dependency on a library implementation detail. Add `key=` to every interactive widget you intend to test.

3. **`.strip()` user text input before validation and storage.** "Is the field non-empty?" must mean "does it contain non-whitespace content?" `if not field` only catches empty string; `if not field.strip()` catches both empty and whitespace-only.

4. **Match the example in GUIDELINES.md.** When guidelines show a pattern (like `if submitted:` outside a container), follow it exactly. Deviations accumulate into an inconsistent codebase that is harder for the next developer — or your future self — to read.

---

## Addendum — AppTest Rerun Capture Behaviour

Discovered during fix verification: `test_submit_shows_success_message` failed even after F1–F5 were applied.

**Root cause:** AppTest captures the state of the **last complete script run**. When `st.rerun()` is called:
1. **First run:** `submitted=True` → the handler fires → `st.success()` renders → `st.rerun()` raises `RerunException` (a `BaseException`, **not** caught by `except Exception`)
2. **Second run (post-rerun):** `submitted=False` → handler is skipped → the unconditional `df = database.get_all_positions()` at the bottom executes → `st.caption(...)` renders

AppTest captures run 2. `at.success` is empty. `at.caption` is populated.

**Important:** `RerunException` is a `BaseException`. The `except Exception` in the F1 fix does **not** catch it — the rerun proceeds normally. This is not a bug in the fix; it is the expected Streamlit behaviour.

**Why this didn't surface before F4:** Before F4, `st.success()` was rendered inside `with st.expander()`. The AppTest element tree differs for widgets inside containers vs. at module scope. After F4 moved the handler to module scope, AppTest resolved the rerun consistently and the second-run capture became observable.

**Fix applied:** Replace `st.success()` with `st.toast()`. `st.toast()` is enqueued in a separate queue that AppTest persists across reruns, so `at.toast` returns the toast even when run 2 is what AppTest captures.

```python
# pages/1_Opportunities.py — inside try block
st.toast(f'Added "{position_name}" to your list.')   # ← not st.success
st.rerun()
```

```python
# tests/test_opportunities_page.py — test_submit_shows_success_message
assert at.toast, "Expected st.toast after a valid quick-add submission"
```

**Lesson:** When a Streamlit page calls `st.rerun()` and has **any unconditional rendering code** below the handler, AppTest will capture the post-rerun state. Feedback that must be testable after a rerun should use `st.toast()`, not `st.success()` / `st.error()` / `st.info()` — unless those messages are rendered unconditionally (not inside an `if submitted:` block).
