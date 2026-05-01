# Phase 3 Tier 4 — Full Code Review

**Branch:** `feature/phase-3-tier4` (baseline `9b84a38`)
**Scope:** `pages/1_Opportunities.py` — covers T4-A (row selection) through T4-F (Notes tab). The Quick-Add (T1), filter bar (T2), and positions table (T3) sections are reviewed inline where Tier 4 depends on them.
**Verdict:** Approve with fixes F1–F3 applied and F7 pinned by a test; F4–F6 accepted with rationale.
**Attitude:** skeptical and didactic — every question a junior engineer might ask is fair game, and "it's been that way since Tier 1" is not a defence.

**Baseline:** 190 tests green on `feature/phase-3-tier4` at commit `9b84a38`.

---

## Summary

Tier 4 is in good shape overall. The `_edit_form_sid` sentinel pattern is correct and re-used consistently across four tabs; the coercion discipline (`safe_*` variables before session_state assignment) is applied uniformly; session_state cleanup on every invariant-breaking event (empty DB, empty filter, disappeared row, Quick-Add reorder) is paired with its sentinel.

Three real defects escaped the prior review passes:

1. A **Tier-1 `raise` after `st.error`** that silently defeats the friendly-error contract by crashing the page immediately after showing the toast-like message (🟠 Moderate).
2. A **Streamlit 1.56 deprecation** (`use_container_width=True`) that logs a warning on every page load and every test run (🟡 Minor).
3. A **stale module header comment** that still claims "Tiers 2–5 will add…" months after Tiers 2–4 shipped (🟡 Minor).

One behaviour is worth pinning with a test rather than changing: positional-index row selection across filter changes (🟡 Note, F7).

---

## Findings

| # | File | Line | Severity | Category       | Status      |
|---|------|------|----------|----------------|-------------|
| F1 | pages/1_Opportunities.py | 91     | 🟠 Moderate | Correctness    | **Fix**     |
| F2 | pages/1_Opportunities.py | 158    | 🟡 Minor    | Deprecation    | **Fix**     |
| F3 | pages/1_Opportunities.py | 2–4    | 🟡 Minor    | Docs           | **Fix**     |
| F4 | pages/1_Opportunities.py | 285–365 | 🟢 Micro   | Duplication    | Accept      |
| F5 | pages/1_Opportunities.py | 299    | 🟢 Micro    | Coupling       | Accept      |
| F6 | pages/1_Opportunities.py | 31     | 🟢 Micro    | Performance    | Accept      |
| F7 | pages/1_Opportunities.py | 176–185 | 🟡 Note    | Correctness    | **Pin test**|

---

### F1 🟠 `raise` after `st.error` defeats the friendly-error contract

```python
# pages/1_Opportunities.py:75–91 (before)
try:
    database.add_position(fields)
    st.toast(f'Added "{position_name}" to your list.')
    …
    st.rerun()
except Exception as e:
    st.error(f"Could not save position: {e}")
    raise      # ← problem
```

**Why this is a bug.** The Phase 3 Tier 1 review (F1) wrapped `database.add_position` in `try/except` specifically so the user would get a "clear message on failure rather than … a raw traceback." The `raise` inside the except block immediately re-throws the exception, which Streamlit renders as a red stack-trace box at the top of the page — the exact outcome F1 was written to prevent. The `st.error(...)` call above it becomes redundant noise.

This is invisible today because every test exercises the happy path; no test triggers `add_position` failure.

**Fix.** Remove `raise`. Keep the friendly message. If we want diagnostics in future, add structured logging — never re-raise into Streamlit's default error renderer on a user-facing action.

---

### F2 🟡 `use_container_width=True` is deprecated

```python
# pages/1_Opportunities.py:158 (before)
event = st.dataframe(
    df_display,
    use_container_width=True,
    …
)
```

**Why this matters.** Streamlit 1.56 logs

> Please replace `use_container_width` with `width`.
> `use_container_width` will be removed after 2025-12-31.

on every render. This surfaces in every pytest run (≈60 warnings at 190 tests) and in the dev console. It will become a hard error after the removal date. The same warning does not appear elsewhere in the page — this is the only offender.

**Fix.** `width="stretch"` (documented replacement per Streamlit 1.56 release notes).

---

### F3 🟡 Stale module header

```python
# pages/1_Opportunities.py:1–4 (before)
# pages/1_Opportunities.py
# Opportunities page — position table, quick-add form, inline full edit.
# Phase 3 Tier 1: quick-add form + empty state.
# Tiers 2–5 will add: filter bar, table, row edit, save/delete.
```

Tiers 2–4 have shipped. The comment tells a new reader the file contains less than it does.

**Fix.** Update to reflect current state; keep the "what's still pending" bullet for Tier 5.

---

### F4 🟢 Duplicated Save-button placeholder — accept

Four `st.form_submit_button("Save Changes", disabled=True, help="Coming in Tier 5 …")` calls across Overview / Requirements / Materials / Notes. A helper would save ~5 LOC but add a function and an extra jump in the call stack. At Tier 5 we will replace `disabled=True` with real per-form save callbacks, and each form's logic will differ (write different columns) — the commonality is cosmetic, not behavioural. **Leave as four explicit calls.**

---

### F5 🟢 Comment on line 299 names a test — accept

```python
# …is what makes test_config_driven_new_doc_renders_new_widget green.
```

Normally production code shouldn't name tests (the dependency direction is tests → production). This file is consciously didactic, and the reference clarifies *why* the implementation looks the way it does. **Accept, don't replicate elsewhere.**

---

### F6 🟢 `database.init_db()` runs on every page render — accept

```python
# pages/1_Opportunities.py:31
database.init_db()
```

`init_db()` issues `CREATE TABLE IF NOT EXISTS` + a handful of migration-aware `ALTER TABLE` guards. Each call is a few SQLite master-table reads — effectively free for a personal tracker. Wrapping in `st.cache_resource` would avoid the re-calls but adds test complexity (cache clears between tests). **Not worth the cost today.** Revisit if positional page-render latency becomes noticeable.

---

### F7 🟡 Filter change after selection — protective behaviour, pin with a test

```python
# pages/1_Opportunities.py:176–185
selected_rows = list(event.selection.rows) if event is not None else []
if selected_rows and 0 <= selected_rows[0] < len(df_display):
    st.session_state["selected_position_id"] = int(
        df_display.iloc[selected_rows[0]]["id"]
    )
else:
    st.session_state.pop("selected_position_id", None)
    st.session_state.pop("_edit_form_sid", None)
```

**The naive concern (inverted by evidence).** I started this review suspecting a silent-rebind bug: selection is a positional row index, so a filter change that shuffles which position lives at row 0 would silently re-bind `selected_position_id` to the new same-index row.

**What actually happens (probed during review).** Streamlit **resets** the dataframe's selection to `{'rows': []}` when a filter widget change triggers the rerun and the underlying data differs. The page's `else` branch then pops `selected_position_id` and `_edit_form_sid` cleanly. The user sees the edit panel disappear on filter change — surprising but safe, and far better than silent rebind to a different position's id.

**Why pin, not fix.** The protective reset is *not documented* in Streamlit's API; it's an observed behaviour of the dataframe widget. A future Streamlit release could change it without warning. A regression from "clear on filter change" to "preserve stale positional index" would become a data-correctness bug once Tier 5 wires Save — we'd silently save the wrong position's edits. Pinning the current behaviour ensures a Streamlit upgrade that regresses this fails loudly in CI.

**Action.** `test_filter_change_after_selection_clears_selection` asserts that filter change after selection pops both `selected_position_id` and `_edit_form_sid`. If Streamlit ever stops resetting the dataframe selection under these conditions, this test catches it before it becomes user-visible.

---

## What Looks Good

- **Sentinel pattern (`_edit_form_sid`)**: correctly defeats Streamlit's widget-value trap across all four tabs. Cleanup paired in every branch that invalidates the selection (empty DB, empty filter, vanished row, Quick-Add reorder, explicit deselect).
- **Coercion discipline**: `safe_priority`, `safe_status`, `safe_deadline`, `safe_v` all normalise DB values to in-vocabulary before session_state assignment. The fallback choices (`PRIORITY_VALUES[0]`, `STATUS_VALUES[0]`, `"N"` for requirements) match schema defaults and are defensible.
- **State-driven Materials tab**: filtering by *live* session_state rather than DB is correct — the user should see the checkbox appear the instant they flip a radio, not after a save round-trip.
- **Config-drive**: no status/priority/requirement strings hardcoded outside `config.py`. `REQUIREMENT_DOCS` drives schema, Requirements radios, and Materials checkboxes; adding a new doc type is a one-line change.
- **Form id / widget key separation**: the T4-F discovery (form id shares writes_allowed=False namespace with widget session_state) was documented inline at line 349–353. That single comment may save the next developer hours.
- **Comments are purposeful**: every non-obvious block (`F1`–`F6` tags, `Tier-4 review` qualifiers) points to the review finding it addresses. Didactic, not decorative.

---

## Junior Engineer Q&A

### Q1 — Why does `_edit_form_sid` exist? Can't we just pass `value=` to the widgets?

Streamlit has a "widget-value trap": once `st.session_state[key]` is set, Streamlit ignores the `value=` kwarg on every subsequent rerun of that script. If you seed widget values with `value=r[...]` and the user selects a different row, the widget keeps showing the *first* row's data forever. `_edit_form_sid` tracks which row id the widget state was seeded from. When the selection changes, the sentinel mismatches, and we explicitly re-write `session_state["edit_*"]` — the only path Streamlit *does* honour once a widget is in play.

### Q2 — Why is the Notes form keyed `"edit_notes_form"` when every other form is just `"edit_X"`?

`st.form(key)` registers its id with `writes_allowed=False`, so the form id can't collide with any pre-existing key in `session_state`. The Notes tab pre-seeds `st.session_state["edit_notes"]` (the text_area key), so a form also named `"edit_notes"` raises `StreamlitValueAssignmentNotAllowedError` at render. `"edit_overview"`, `"edit_requirements"`, `"edit_materials"` don't collide because no widget inside them happens to share that exact name. Convention to adopt going forward: **never give a form id the same name as a widget key inside it** — suffix forms with `_form` if in doubt.

### Q3 — Selection is a positional row index, and Quick-Add reorders the table. Doesn't that silently re-bind the selected position?

Yes, and we handle it explicitly. `database.get_all_positions()` orders `deadline_date ASC NULLS LAST`, so a quick-added position's positional index depends on its deadline relative to existing rows — it can land anywhere and shift the index of a previously-selected row. Lines 85–87 clear `positions_table`, `selected_position_id`, and `_edit_form_sid` together after a successful Quick-Add, so the pre-existing selection can't persist into the re-ordered dataframe. `test_quick_add_clears_selection` pins this.

**Side finding from this review:** the Tier-4 F1 comment previously claimed the ordering was `updated_at DESC`. That was wrong — the rationale still holds (positional index is volatile under reorder) but the mechanism is deadline-based, not recency-based. Both the inline comment and the test's docstring were corrected as part of this review.

### Q4 — Why the asymmetric coercion — `safe_priority` for selectbox but `r["position_name"] or ""` for text_input?

`text_input` accepts any string including `""`. `selectbox`, `radio`, and `date_input` have closed vocabularies / closed types — feeding an out-of-options value is at best a warning, at worst a render error depending on Streamlit version. Coerce only where the widget enforces a vocabulary. The `or ""` idiom handles the one realistic case for text fields: DB `NULL` → Python `None` → falsy → `""`.

### Q5 — Why does Materials filter by live session_state rather than the DB row?

Because the user's mental model is "I just flipped req_cv to Required on the Requirements tab — the CV checkbox should appear on Materials now." If we filtered by the DB row, Materials would show yesterday's requirements until the user saved. The live filter gives instant feedback; there is no consistency risk because widget values always reflect the currently-selected row (see Q1).

### Q6 — We pre-seed `edit_done_*` for *all* requirements even when the checkbox is hidden. Isn't that wasteful?

Seven booleans per row selection — negligible memory. The alternative is real risk: if we seed only currently-visible done checkboxes, and the user flips a radio `N → Y`, the newly-visible checkbox has no seed on the first render after the flip and would render with `False` regardless of the DB value. Brief flash of wrong state, then correct after the next rerun. Pre-seeding unconditionally keeps the state continuous and matches the "sentinel gates pre-seed" design.

### Q7 — `r["notes"] or ""` — what if someone legitimately stores the string `"0"`?

`"0"` is truthy in Python (`bool("0") == True`), so `"0" or ""` returns `"0"` — correct. The only values the `or ""` fallback catches are the falsy ones: `None`, `""`, `0`, `False`. Of those, `None` is the only realistic value from SQLite NULL, and it's exactly what we want to coerce. `""` and the integers/booleans aren't possible for a TEXT column from a well-formed write.

### Q8 — Four nearly-identical disabled Save buttons. Why no helper?

Because they *will* diverge in Tier 5 — each form saves different columns with different validation. Extracting a `_disabled_save_button()` helper today would need to grow parameters for the callback, the success message, the specific columns, and the error path as soon as Tier 5 lands. Four explicit calls is five fewer LOC than a helper that handles all the future cases, and the commonality is cosmetic (same label, same tooltip). We will introduce per-form save helpers in Tier 5 where the abstraction has real work to do.

### Q9 — `database.init_db()` on every render — isn't that expensive?

Not measurably. `init_db()` is idempotent: `CREATE TABLE IF NOT EXISTS` plus a handful of migration-aware `ALTER TABLE` guards. Each call issues a few SQLite master-table reads (cached by SQLite itself) and no writes. We could wrap in `st.cache_resource` to call once per Streamlit process, but that adds test-isolation complexity (cache has to be cleared between tests) for savings measured in microseconds. Wrong trade at this scale.

### Q10 — Why not write an id-based selection to replace the positional-index model?

Not needed. Probing during this review showed Streamlit itself *resets* the dataframe selection on data change — the protective behaviour we'd re-implement on top of id-based selection happens for free. An id-based layer would require either reverse-engineering Streamlit's internal `positions_table` payload (fragile across versions) or a parallel reconciliation slot (complexity not justified by threat model). We pin Streamlit's protective reset with a test (F7) and revisit at Tier 5 only if Save introduces new invariants.

---

## Tests Added / Changed

1. **`test_save_error_shows_error_without_raising`** (new) — patches `database.add_position` to raise; asserts the page shows an `st.error` and does **not** record an uncaught exception. Directly guards F1's fix.
2. **`test_filter_change_after_selection_clears_selection`** (new) — pins F7's *protective* behaviour: Streamlit resets the dataframe selection on filter-triggered rerun, and our else-branch pops `selected_position_id` + `_edit_form_sid`. A future Streamlit release regressing this fails here before it becomes a data-correctness bug at Tier 5.

---

## Verdict

**Approve with fixes F1–F3 applied and F7 pinned by a test.** F4–F6 accepted as-is with rationale documented. No security, performance, or architectural blockers. Ready to merge after fixes land and all 192 tests are green.
