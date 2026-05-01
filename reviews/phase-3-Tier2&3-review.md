# Phase 3 Tier 2 & Tier 3 Code Review
**Branch:** _(direct-to-main; pre-branch-workflow)_
**Scope:** Phase 3 Tiers 2 + 3 — Filter bar + positions table on `pages/1_Opportunities.py`.
**Verdict:** Request Changes (5 findings, all fixed in this review).
**Files reviewed:** `pages/1_Opportunities.py` (Tier 2 filter bar + Tier 3 positions table), `tests/test_opportunities_page.py` (filter bar + table test classes)
**Date:** 2026-04-18
**Reviewer:** Claude (skeptical + didactic)

---

## Summary

The filter bar and positions table are structurally sound: filter logic follows the correct pandas pattern, the urgency flag correctly uses config constants, and the test suite covers the happy path for all three filter types and all urgency levels. However, one critical usability bug exists (the field filter will crash on very common input), one robustness gap exists in the urgency helper, and several boundary conditions in the test suite are unexercised. All five findings are fixed in this review.

---

## Findings

| # | File | Location | Issue | Severity |
|---|------|----------|-------|----------|
| F1 | `pages/1_Opportunities.py` | line 109–111 | `str.contains()` uses `regex=True` by default — field filter crashes on `"C++"`, `"Bio.stat"`, `"[ML]"` etc. | 🔴 Critical |
| F2 | `pages/1_Opportunities.py` | line 23 | `_deadline_urgency` catches only `ValueError`; `TypeError` from non-str input (e.g. `np.nan`) propagates uncaught | 🟡 Moderate |
| F3 | `tests/test_opportunities_page.py` | `TestPositionsTable` | Urgency threshold boundary values not tested — `days == DEADLINE_URGENT_DAYS` and `days == DEADLINE_ALERT_DAYS` are off-by-one risk areas | 🟡 Moderate |
| F4 | `tests/test_opportunities_page.py` | `TestPositionsTable` | Past-deadline positions (`days < 0`) not tested for urgency — correct "urgent" behavior is asserted nowhere | 🟡 Moderate |
| F5 | `tests/test_opportunities_page.py` | `TestFilterBarBehaviour` | No regression test for the F1 fix — `regex=False` could be silently removed in a future edit | 🟢 Minor |

---

## Finding Details

### F1 — `str.contains()` crashes on regex metacharacters (Critical)

**Current code (`pages/1_Opportunities.py:109–111`):**
```python
df_filtered = df_filtered[
    df_filtered["field"].str.contains(
        field_filter.strip(), case=False, na=False
    )
]
```

**Problem:** `str.contains()` defaults to `regex=True`. The search term is compiled as a regular expression. Common field strings a user would naturally type include:

| User types | Regex meaning | Result |
|------------|--------------|--------|
| `C++` | `+` = one-or-more quantifier with nothing preceding it | `re.error: nothing to repeat` → traceback in browser |
| `(AI)` | `(` = start of group | `re.error: unterminated subpattern` |
| `Bio.stat` | `.` = any character | Matches `BioXstat`, `Bio1stat` etc. — silently wrong |
| `[ML]` | `[...]` = character class | Matches any single char M or L, not the literal string |

The first two crash the Streamlit app with a visible Python traceback for the user. The second two produce silent wrong results with no error.

For a filter bar, the correct semantic is **literal substring match**: "does the `field` column contain exactly these characters, case-insensitively?" That is `regex=False`.

**Fix:**
```python
df_filtered = df_filtered[
    df_filtered["field"].str.contains(
        field_filter.strip(), case=False, na=False, regex=False
    )
]
```

---

### F2 — `_deadline_urgency` does not catch `TypeError` (Moderate)

**Current code (`pages/1_Opportunities.py:21–24`):**
```python
try:
    days = (datetime.date.fromisoformat(date_str) - datetime.date.today()).days
except ValueError:
    return ""
```

**Problem:** `datetime.date.fromisoformat()` raises `ValueError` for strings that are not valid ISO dates (e.g., `"asdf"`). It raises `TypeError` for non-string inputs (e.g., `np.nan`, an integer).

The guard `if not date_str` catches `None` and `""` (both falsy). It does **not** catch `np.nan`, which is a float and therefore truthy:

```python
>>> bool(np.nan)  # np.nan is a non-zero float
True
>>> not np.nan
False
```

If `date_str` is `np.nan`, the guard is bypassed, `fromisoformat(np.nan)` raises `TypeError`, and the exception propagates to Streamlit as an unhandled error.

**When can `np.nan` appear?** Pandas uses `None` for NULL values in object-dtype (TEXT) columns, which is the current behavior of `pd.read_sql_query` on SQLite. So today this path is never hit. However:
- A future pandas version or dtype inference change could produce `np.nan` instead of `None`
- A test that constructs DataFrames directly (rather than via `get_all_positions()`) might accidentally pass `np.nan`

The fix is one word and makes the function unconditionally safe.

**Fix:**
```python
    except (ValueError, TypeError):
        return ""
```

---

### F3 — Urgency threshold boundary values not tested (Moderate)

**Current tests:**
```python
# URGENT - 1 = 6 days → "urgent"   (tested)
# URGENT + 1 = 8 days → "alert"    (tested)
# ALERT + 10 = 40 days → ""        (tested)
```

**Missing:** `days == DEADLINE_URGENT_DAYS` (exactly 7) and `days == DEADLINE_ALERT_DAYS` (exactly 30).

The urgency conditions are:
```python
if days <= config.DEADLINE_URGENT_DAYS:   # ← ≤ not <
    return "urgent"
if days <= config.DEADLINE_ALERT_DAYS:    # ← ≤ not <
    return "alert"
```

Off-by-one errors here (`<` vs `<=`) would be caught by nothing in the current test suite. A future refactor that changes `<=` to `<` would silently break the intended behaviour — a deadline that is *exactly* 7 days away would no longer be considered urgent, potentially causing the user to miss a deadline.

**Fix:** Add two boundary tests:
- `days == DEADLINE_URGENT_DAYS` → must produce `"urgent"`
- `days == DEADLINE_ALERT_DAYS` → must produce `"alert"`

---

### F4 — Past-deadline urgency not tested (Moderate)

**Problem:** `days < 0` means the deadline has already passed. The expression `days <= DEADLINE_URGENT_DAYS` evaluates to `True` for any negative value, so `_deadline_urgency` correctly returns `"urgent"` for past deadlines. This is the right behaviour — a missed deadline is the most urgent state.

However, it is **not tested**. A refactor that adds `days > 0 and days <= URGENT` (to avoid flagging expired deadlines as urgent) would silently remove this behaviour. For a job application tracker, knowing that past deadlines are still flagged is important: it surfaces positions the user may have missed.

**Fix:** Add one test:
- Past deadline (days = −5) → must produce `"urgent"`

---

### F5 — No regression test for `regex=False` (Minor)

**Problem:** Once F1 is fixed, the literal-match behaviour (`regex=False`) is tested implicitly only by `test_filter_by_field_substring_match` and `test_filter_by_field_is_case_insensitive` — but those tests use plain alphabetic strings that are valid regex patterns too. If someone removes `regex=False` in the future, those tests still pass, because alphabetic strings produce identical results with or without regex mode.

**Fix:** Add a test that uses `"C++"` as the field filter — this string is a valid literal substring but an invalid regex. With `regex=False` it matches correctly; without it, the test fails with `re.error`.

---

## Applied Fixes

| # | Status | Change |
|---|--------|--------|
| F1 | ✅ Applied | Added `regex=False` to `str.contains()` in the field filter |
| F2 | ✅ Applied | Changed `except ValueError` to `except (ValueError, TypeError)` in `_deadline_urgency` |
| F3 | ✅ Applied | Added `test_urgency_at_urgent_threshold_boundary` and `test_urgency_at_alert_threshold_boundary` |
| F4 | ✅ Applied | Added `test_past_deadline_flagged_as_urgent` |
| F5 | ✅ Applied | Added `test_filter_by_field_with_special_characters` |

---

## What Looks Good

- **Filter logic is correct and composable.** Status, priority, and field filters apply sequentially using simple pandas boolean indexing — each active filter narrows `df_filtered` independently. The AND semantics are exactly what a user expects.
- **`df_filtered = df` without `.copy()` is safe here.** Pandas boolean indexing (`df[condition]`) always returns a new DataFrame, so `df_filtered` is always a fresh object after any filter is applied. The only time `df_filtered is df` is when all filters are "All"/empty — and in that case `df_display = df_filtered.copy()` ensures we never modify `df` in place.
- **`df_display = df_filtered.copy()` before adding the urgency column is correct.** Assigning a new column to a view (non-copy slice) would produce `SettingWithCopyWarning`. The explicit `.copy()` avoids this.
- **`column_order` in `st.dataframe()` is the right approach.** Passing `df_display` with all 37+ columns and letting Streamlit hide the rest is cleaner than manually selecting 6 columns into a new DataFrame — and AppTest's `.value` still has access to all columns for testing.
- **Urgency thresholds come from `config.py`.** `DEADLINE_URGENT_DAYS` and `DEADLINE_ALERT_DAYS` are read at call time, so changing a threshold in `config.py` automatically updates both the table flag and (in Phase 4) the dashboard without touching page code.
- **`not date_str` correctly handles both `None` and `""`** (both falsy), covering the two ways an "empty" deadline can appear from the DB.
- **`str.contains(na=False)`** correctly treats NULL/NaN field values as non-matching, rather than propagating NaN into the boolean mask (which would cause a `ValueError` in pandas).

---

## Verdict: Request Changes

F1 is a real user-facing crash on common input. F2 is a latent robustness gap. F3 and F4 are test coverage gaps at boundary conditions that protect against off-by-one regressions. All five are low-effort to fix and are applied in this review.

---

## 9 Questions a Junior Engineer Would Ask

**Q1. Why does `str.contains()` need `regex=False`? Can't I just tell users not to type regex characters?**

You can't control what users type in a free-text search box, and you shouldn't require them to know what a regex is. "C++" is a completely normal programming language name. "Bio.stat" is a normal department abbreviation. A filter bar should behave like a search bar: type what you're looking for, get a substring match. `regex=True` is the right default for developer APIs (where the caller controls the input), not for user-facing search boxes.

**Q2. Why is `np.nan` truthy but `None` falsy? I expected `not np.nan` to be `True`.**

`np.nan` is a IEEE 754 "not a number" float value — specifically `float('nan')`. In Python, the truthiness of a float is determined by `bool(x)`, which returns `False` only for `0.0`. Since `nan != 0.0`, `bool(np.nan)` is `True`, and `not np.nan` is `False`. This surprises almost every developer once. `None` is its own type (`NoneType`) and is always falsy by Python's object protocol. The lesson: never use `not x` to guard against "missing" values — `x is None` or `pd.isna(x)` is precise.

**Q3. Why test boundary values (days == 7 and days == 30) separately? Aren't nearby values enough?**

Testing `days = 6` and `days = 8` tells you the function produces the right output on either *side* of the threshold. It tells you nothing about the threshold itself. Changing `≤` to `<` would make `days = 7` return `"alert"` instead of `"urgent"` — and that bug would be invisible to tests that only check 6 and 8. Boundary tests are the minimum evidence that the threshold operator is correct.

**Q4. What does `df_filtered = df` (without `.copy()`) actually mean in Python?**

It creates a second name that refers to the *same* DataFrame object in memory — no data is copied. If you then do `df_filtered.loc[0, "status"] = "X"`, you've also modified `df`, because they point to the same object. However, `df_filtered = df_filtered[condition]` (boolean indexing) *reassigns* the variable to a brand-new DataFrame returned by the `[]` operator — `df` is unaffected. The current code only uses boolean indexing (never in-place modification), so the aliasing is harmless. The risk is that a future developer adds `df_filtered.loc[...] = ...` without realizing it would mutate `df`.

**Q5. Why do we check `df.empty` first, before `df_filtered.empty`? Why not just check `df_filtered.empty`?**

Because the error messages are different:
- `df.empty` → "No positions yet — use Quick Add above to get started." (empty DB)
- `df_filtered.empty` with `df` non-empty → "No positions match the current filters."

If we only checked `df_filtered.empty`, an empty DB with an active filter would show "No positions match the current filters." — which is misleading. The user hasn't filtered down to nothing; they simply have no data yet. The two-stage check communicates the actual cause clearly.

**Q6. What happens to a position with an expired deadline (days < 0)? Is "urgent" the right label?**

Yes. If a deadline has passed and you haven't applied, one of two things is true: you missed it (most urgent action: mark it `[CLOSED]` or `[REJECTED]`) or it was extended (you need to update it). Either way, it demands immediate attention. Treating expired deadlines as "not urgent" would hide them from the user's attention — the worst possible outcome for a tracker.

**Q7. Why does `column_order` hide columns rather than us just selecting 6 columns from `df_display` before calling `st.dataframe()`?**

Both work, but `column_order` is declarative: you tell Streamlit what to *show*, not what to *drop*. The underlying DataFrame passed to `st.dataframe()` — and therefore `at.dataframe[0].value` in AppTest — still contains all columns, including `deadline_urgency`. If we sliced to 6 columns first, the test `test_table_has_required_columns` would only see those 6 columns (which is still correct), but future code wanting to access other columns (e.g., `id` for Tier 4 row selection) would need additional changes.

**Q8. Why does `_deadline_urgency` take `date_str: str | None` as a type hint when the `field` column in the DataFrame might have other types (like `np.nan`)?**

The type hint documents the *intended* contract. `database.get_all_positions()` stores deadline_date as a TEXT column and reads it back as object dtype (Python `None` for NULL, `str` for everything else). `np.nan` shouldn't appear — but defensive coding catches reality drifting from intent. Widening the `except` clause to include `TypeError` (F2 fix) costs nothing and handles the case where pandas or a test fixture diverges from the expected dtype.

**Q9. The `priority` filter uses `config.PRIORITY_VALUES` as its options. What happens if a position has a priority string not in that list (e.g., inserted via a script with `"Extra High"`)?**

It would appear in "All" mode but would be unreachable via any specific priority filter option. Selecting "High" would filter to rows where `priority == "High"`, which excludes `"Extra High"`. This is correct: the filter only offers options that the UI formally supports. The position is not lost — it's just only visible without a priority filter. In practice this shouldn't happen because the quick-add form only offers `config.PRIORITY_VALUES` options. For direct DB inserts (tests, scripts, future bulk-import), it's worth knowing this behaviour.

---

## Lessons

1. **`str.contains()` is a regex engine, not a string search.** Always pass `regex=False` for literal text search in user-facing filter boxes. Reserve `regex=True` for power users and developer tools where the caller knows they're writing a pattern.

2. **Catch the exceptions the function can actually raise, not just the ones you expect.** `fromisoformat` documents `ValueError`; that's the common case. But `TypeError` is also possible when the contract is violated (non-string input). `except (ValueError, TypeError)` is the safe pattern for functions that convert external data.

3. **Boundary tests are not redundant with nearby-value tests.** If the only tests are at `threshold - 1` and `threshold + 1`, you have zero coverage of the threshold itself. Always test the exact boundary for `≤`, `<`, `≥`, `>` conditions.

4. **Test the fix, not just the behaviour.** The F5 test (`"C++"` as search term) specifically exercises the code path that F1 broke. If `regex=False` is removed in the future, this test fails immediately with an unambiguous error — not a subtle wrong result.

5. **`not x` is not the same as `x is None`.** Use `x is None` when you mean "this value was not provided." Use `pd.isna(x)` when you mean "this value is missing from a DataFrame." Use `not x` only when you mean "this value is falsy" — which can include `0`, `""`, `[]`, `False` in addition to `None`.
