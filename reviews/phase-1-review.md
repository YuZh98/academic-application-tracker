# Code Review: Phase 1
**Commit reviewed:** `219741e` — `chore: set up venv and config.py`
**Date:** 2026-04-16
**Files reviewed:** `config.py`, `requirements.txt`
**Verdict:** Approved with fixes applied in commit `{post-review commit}`

---

## Summary

`config.py` is clean, well-structured, and faithful to DESIGN.md §5. Comments are thorough — especially the live-verified `st.badge` color note and the REQUIREMENT_DOCS extension procedure. No critical issues. Five findings were resolved before Phase 2 begins. `requirements.txt` received a provenance header. Two informational notes require no action.

---

## Findings

### F1 — Silent drift between `STATUS_VALUES` and `STATUS_COLORS` *(Moderate — Fixed)*
**Lines:** 19–40

If a new status is added to `STATUS_VALUES` but omitted from `STATUS_COLORS`, no error occurs at import time. The failure surfaces as a `KeyError` deep in a page file. A module-level assertion now catches this at import time with a descriptive message.

**Fix applied:**
```python
assert set(STATUS_VALUES) == set(STATUS_COLORS), (
    "STATUS_COLORS must have exactly one entry per STATUS_VALUES item. "
    f"Missing from STATUS_COLORS: {set(STATUS_VALUES) - set(STATUS_COLORS)}"
)
```
**Verification:** Test with a `[WAITLISTED]` value added only to STATUS_VALUES confirmed the assertion fires with message: `Missing from STATUS_COLORS: {'[WAITLISTED]'}`.

---

### F2 — `RESULT_VALUES[0]` silently couples to DB schema default *(Minor — Fixed)*
**Lines:** 62–64

The `applications` table schema has `result TEXT DEFAULT 'Pending'`. If `"Pending"` were renamed in `RESULT_VALUES`, the DB would continue inserting `'Pending'` for new rows, but the selectbox would no longer offer it.

**Fix applied:** Extracted `RESULT_DEFAULT = "Pending"` as a named constant with a coupling note. `RESULT_VALUES[0]` now references `RESULT_DEFAULT` directly. `database.init_db()` in Phase 2 will use `RESULT_DEFAULT` in the schema's DEFAULT clause.

---

### F3 — No type annotations on constants *(Minor — Fixed)*
**Lines:** 14, 19, 32, 46–103

PEP 526 module-level variable annotations were absent. Added on all 13 named constants. IDE autocompletion for `REQUIREMENT_DOCS: list[tuple[str, str, str]]` now correctly reflects the three-element tuple structure without requiring the consumer to read the comment.

---

### F4 — Threshold `=` signs misaligned *(Cosmetic — Fixed)*
**Lines:** 106–108

`RECOMMENDER_ALERT_DAYS` (22 chars) is two characters longer than `DEADLINE_URGENT_DAYS` (20 chars), so its `=` was one column to the right. Adjusted spacing to align all three `=` signs.

---

### F5 — `requirements.txt` had no provenance header *(Minor — Fixed)*
**Line:** 1

`pip freeze` output is platform-specific. Added a two-line header recording the generation date, command, Python version, and OS. Also documents the regeneration command for future sessions.

---

### F6 — `TRACKER_PROFILE` has no consuming code yet *(Informational — No action)*

`TRACKER_PROFILE = "postdoc"` is defined as forward-looking design (DESIGN.md §11). It will be consumed by `database.init_db()` in Phase 2 and by page files in Phase 3 to filter profile-specific fields. Added a code comment noting the expected consumption points and a warning to remove it if still unused after Phase 3.

---

### F7 — `six==1.17.0` is a deprecated transitive dependency *(Informational — No action)*

`six` (Python 2/3 compatibility shim, deprecated post-2020) appears via `python-dateutil` → `pandas`. Harmless with Python 3.14. No action needed.

---

## What Looked Good

| Observation | Why it matters |
|-------------|---------------|
| `STATUS_COLORS` comment documents Streamlit version + full accepted color literal set | Future sessions won't re-do the API verification |
| `REQUIREMENT_DOCS` extension comment is step-by-step and accurate | Unambiguous for any future contributor |
| `QUICK_ADD_FIELDS` comment confirms schema cross-verification was done | Establishes that "verified" means something in this codebase |
| All vocabulary lists use consistent `"Other"` as last-option catch-all | Predictable UX pattern |
| Threshold assertion `URGENT < ALERT` was checked in the pre-commit test script | Logical constraint was verified, not assumed |
| Module rule comment at top of file states three rules clearly | Import contract is self-documenting |

---

## Post-Review State

After applying all five fixes, the verification script was re-run:
- All 13 constants have type annotations ✓
- `STATUS_COLORS` guard assertion fires correctly on bad input ✓
- `RESULT_VALUES[0] == RESULT_DEFAULT == "Pending"` ✓
- Threshold alignment corrected ✓
- `requirements.txt` header present ✓
