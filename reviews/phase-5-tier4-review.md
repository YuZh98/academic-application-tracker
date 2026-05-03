**Branch:** `feature/phase-5-tier4-RecommendersAlertPanel`
**Scope:** Phase 5 T4 — `pages/3_Recommenders.py` page shell + Pending Alerts panel
**Stats:** 18 new tests · suite 682 → 700 green · 0 xfail regressions
**Verdict:** Approve

---

## Executive Summary

Phase 5 T4 lands the `pages/3_Recommenders.py` page shell and its Pending
Alerts panel. The implementation is a clean port of the dashboard's T5
recommender-alert cards (already battle-tested) onto the dedicated page,
with the addition of the `relationship` field in the card header. All 18
new tests pass; all four GUIDELINES §11 pre-commit checks are green.

---

## Findings

| # | File | Location | Description | Severity | Status |
|---|------|----------|-------------|----------|--------|
| 1 | `pages/3_Recommenders.py` | top-level imports | `import config` was initially present but unused in T4; removed before commit. | 🟡 | Fixed inline |
| 2 | `tests/test_recommenders_page.py` | imports | `import pytest` and `import config` were initially present but unused; removed before commit. `AppTest` import was accidentally removed alongside them and restored. | 🟡 | Fixed inline |

*No 🔴 or 🟠 findings.*

---

## Junior-Engineer Q&A

**Q1. Why is `_format_label` and `_format_due` defined again here rather than imported from `app.py`?**

A. Page helpers are intentionally kept local per the project's layering rules (DESIGN §2 + GUIDELINES §2). `app.py` is a Streamlit entry point, not a library — importing from it would couple two presentation-layer files and force AppTest to load the entire dashboard when running Recommenders-page tests. The duplication is deliberate and acceptable given the helpers are short (~5 lines each); if they ever grow materially they should be promoted to a shared `ui_helpers.py` module.

**Q2. Why is `relationship` taken from the first row of the group rather than asserting all rows agree?**

A. `relationship` is stored on the `recommenders` row, not the `positions` row, so every row for the same recommender necessarily carries the same relationship value. Taking `_group.iloc[0]["relationship"]` is therefore correct and avoids an unnecessary aggregation. If the schema ever changes to allow per-position relationship overrides, the page would need revisiting — but that is a v2 concern (DESIGN §12).

**Q3. The `_rel_str` guard uses both `_rel and not pd.isna(_rel)`. Why two checks?**

A. `None` is falsy so `_rel` short-circuits it. `pd.isna` catches `float('nan')` which is *truthy* but represents a missing value (pandas surfaces NaN for NULL TEXT cells when a left-join or groupby operation converts None). Without the second guard, a NaN relationship would produce `" (nan)"` in the header. The double guard matches the pattern used in `app.py` `_next_interview_display`.

**Q4. Why does `_format_due` cast `deadline_iso` to `str()` before `date.fromisoformat()`?**

A. `deadline_iso` is typed `str | None` but comes from an `Any`-annotated `iterrows()` cell, which could be a pandas Timestamp or other numeric type in pathological cases. `str()` is a defensive no-op for true string inputs and makes the intent explicit. Mirrors the `_asked_iso: str = str(_row["asked_date"])` pattern elsewhere on the page.

**Q5. The test `test_relationship_absent_when_null` asserts `"None" not in bodies[0]`. Why not assert the full expected body structure?**

A. The test is a *negative* correctness pin: its job is to catch the naive `f" ({_rel})"` path that would render `" (None)"` when relationship is NULL. Asserting the full body structure would over-constrain the test to the exact formatting of unrelated fields (position name, dates) and make it fragile to future T5/T6 additions. A targeted `"None" not in` assertion is sufficient to pin the specific failure mode.

**Q6. Why is `recs_` established as the widget-key prefix in GUIDELINES §13 even though T4 has no widgets?**

A. GUIDELINES §13 step 5 mandates picking the prefix at page-creation time so it is consistently applied from the first widget added in T5 onwards. Recording it now (in the GUIDELINES table, which already lists `recs_`) avoids a later refactor where some early T5 widgets ship without the prefix and then need renaming.
