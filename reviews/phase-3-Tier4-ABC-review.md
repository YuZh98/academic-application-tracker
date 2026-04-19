# Phase 3 Tier 4 (T4-A / T4-B / T4-C) Code Review
**Files reviewed:** `pages/1_Opportunities.py` (row selection, edit-panel shell, Overview tab)
**Date:** 2026-04-19
**Reviewer:** Claude (skeptical + didactic)
**Scope:** T4-A (single-row selection), T4-B (subheader + tab shell), T4-C (7 pre-filled Overview widgets in `st.form("edit_overview")`, `_edit_form_sid` pre-seed).

---

## Summary

The row-selection → edit-panel pipeline is structurally sound and well-tested (167 tests pass, 14 new for T4-A–C). The `_edit_form_sid` sentinel correctly defeats Streamlit's widget-value trap. However, a **silent-wrong-row bug** lurks in the interaction between Quick-Add's `st.rerun()` and the dataframe's row-index-based selection (F1), a **None-priority / unknown-status** fragility relies on undocumented Streamlit tolerance (F2), and the edit-panel state has several cleanup gaps (F3, F4). Two minor UX / robustness nits round out the set (F5, F6). One known-and-accepted risk (F7) is documented but not fixed.

All six actionable findings are fixed below; tests updated to guard each one.

---

## Findings

| # | File | Location | Issue | Severity |
|---|------|----------|-------|----------|
| F1 | `pages/1_Opportunities.py` | quick-add `try`-block (lines 75–81) | Quick-Add's `st.rerun()` does not clear the dataframe's selection state. Because `get_all_positions()` orders by `updated_at DESC`, the newly-added position takes row 0 and every prior row shifts down by one — the still-stored row index now points to a *different* position. The edit panel silently switches. | 🟡 Moderate |
| F2 | `pages/1_Opportunities.py` | T4-C pre-seed (line 193) | For a DB row with `priority IS NULL`, `r["priority"]` is `None`. Writing `None` into `session_state["edit_priority"]` works today only because Streamlit 1.56 tolerates an out-of-options session value and falls back to options[0]; this behaviour is undocumented. Same fragility for `r["status"]` if the DB ever holds a status outside `config.STATUS_VALUES`. | 🟡 Moderate |
| F3 | `pages/1_Opportunities.py` | T4-B stale-sid branch (line 179) | When the selected position has been deleted elsewhere, `selected_row.empty` is `True` and the edit panel silently does not render — but `selected_position_id` and `_edit_form_sid` stay in session_state forever. Stale state leak, not currently harmful but violates the "clean up your session_state" invariant. | 🟢 Minor |
| F4 | `pages/1_Opportunities.py` | filter-to-empty / df-empty branches (lines 119, 122) | `selected_position_id` is popped but `_edit_form_sid` is not. A later re-selection of a sid that happens to equal the stale sentinel would skip the pre-seed and risk showing widget values that no longer match the row. Defence-in-depth. | 🟢 Minor |
| F5 | `pages/1_Opportunities.py` | T4-C pre-seed (lines 195–197) | `datetime.date.fromisoformat(r["deadline_date"])` is unguarded. `_deadline_urgency` already caught `ValueError`/`TypeError` on this exact field (T2–T3 review F2); the pre-seed should be equally defensive so a single malformed row doesn't crash the whole page. | 🟢 Minor |
| F6 | `pages/1_Opportunities.py` | T4-C submit button (line 220) | The disabled "Save Changes" button is a placeholder for T5, but there is no `help=` tooltip and no caption explaining why it's disabled. A user who clicks it gets no feedback and no hint. | 🟢 Minor |
| F7 | `pages/1_Opportunities.py` | selection-after-filter (lines 102–114 + 161–168) | Same class of bug as F1 via a different path: changing a filter after selecting a row shifts the filtered-table order, so the stored row index now addresses a *different* row in `df_display`. Unlike F1 (Quick-Add, unexpected), filter changes are user-initiated and the caption updates visibly, so the cognitive cost is lower. **Documented, not fixed.** Revisit if users report confusion. | 🟢 Known / accepted |

---

## Finding Details

### F1 — Quick-Add silently switches the selected row (Moderate)

**Current code:**
```python
try:
    database.add_position(fields)
    st.toast(f'Added "{position_name}" to your list.')
    st.rerun()
```

**Problem:** `get_all_positions()` orders `updated_at DESC`, so the new row lands at index 0 and every previously-rendered row shifts to index +1. The `positions_table` widget state is not touched by `st.rerun()` — it still holds `{"selection": {"rows": [N]}}`. After the rerun, row N points to a *different* position (or off the end of the table, in which case the bounds check pops the selection entirely, which is also surprising).

**Why it matters:** The edit panel silently reloads for a different position. If the user was mid-edit (once T5 ships), those edits would apply to the wrong row.

**Fix:** Clear both the dataframe-widget selection state and the sentinel before `st.rerun()`. Also pop `selected_position_id` to keep all three invariants aligned in one place.

```python
database.add_position(fields)
st.toast(f'Added "{position_name}" to your list.')
# F1: a new row shifts every existing row index by +1 — clear the
# selection so the edit panel does not silently re-bind to a
# different position. Paired pop of _edit_form_sid keeps the pre-seed
# invariant (popped selected_position_id → popped sentinel).
st.session_state.pop("positions_table", None)
st.session_state.pop("selected_position_id", None)
st.session_state.pop("_edit_form_sid", None)
st.rerun()
```

**Test added:** `TestRowSelection.test_quick_add_clears_selection` — select a row, submit a new position via Quick-Add, assert `selected_position_id` is not in `session_state`.

---

### F2 — None priority / unknown status relies on undocumented Streamlit tolerance (Moderate)

**Current code:**
```python
st.session_state["edit_priority"] = r["priority"]
st.session_state["edit_status"]   = r["status"]
```

**Problem:** A position row with `priority = NULL` produces `r["priority"] is None`. Writing `None` into `session_state` for a selectbox key that lists `config.PRIORITY_VALUES` as options is an *out-of-options* value. Today Streamlit quietly falls back (which is why `test_widgets_handle_null_fields` passes), but this tolerance is undocumented and can flip to `StreamlitAPIException` in any minor release.

Same fragility for `status`: the DB column defaults to `[OPEN]` and every add path goes through a config-driven selectbox, so today all rows are in-vocabulary. But nothing enforces that invariant at the DB layer — a sqlite3 CLI session or a future migration could leave a row with e.g. `[LEGACY]`, and the page would crash on selection.

**Fix:** Coerce both values to a safe in-options default. For `priority`, the first option (`High`) is a sensible fallback because absence of a priority in this tool really means "I haven't triaged this yet". For `status`, treat an unknown value as `[OPEN]` (the schema default) — the user can then correct it.

```python
priority = r["priority"] if r["priority"] in config.PRIORITY_VALUES \
    else config.PRIORITY_VALUES[0]
status   = r["status"]   if r["status"]   in config.STATUS_VALUES   \
    else config.STATUS_VALUES[0]
st.session_state["edit_priority"] = priority
st.session_state["edit_status"]   = status
```

**Test added:** `TestOverviewTabWidgets.test_null_priority_falls_back_to_first_option` — insert a position with no priority, select it, assert the `edit_priority` selectbox value equals `config.PRIORITY_VALUES[0]` (not `None`).

---

### F3 — Stale sid when the selected position is deleted (Minor)

**Current code:**
```python
if "selected_position_id" in st.session_state:
    sid = st.session_state["selected_position_id"]
    selected_row = df[df["id"] == sid]
    if not selected_row.empty:
        ...
    # (no else — state silently leaks)
```

**Problem:** If `sid` references a row that's no longer in `df` (deletion in another session, externally modified DB, etc.), the panel disappears silently and `selected_position_id` + `_edit_form_sid` stay in session_state across every rerun. Cheap, but not zero-cost, and gives the sentinel a chance to alias with a future sid.

**Fix:** Add an explicit `else` that clears both keys.

```python
if not selected_row.empty:
    ...
else:
    # F3: the selected row vanished from df (deleted elsewhere, DB
    # wiped, etc.). Clear both keys so later reruns don't keep
    # re-checking and the sentinel can't alias with a future sid.
    st.session_state.pop("selected_position_id", None)
    st.session_state.pop("_edit_form_sid", None)
```

**Test added:** `TestEditPanelShell.test_stale_sid_is_cleared_silently` — select a row, manually set `selected_position_id` to a non-existent id, rerun, assert both keys are gone.

---

### F4 — `_edit_form_sid` outlives `selected_position_id` on filter-to-empty (Minor)

**Current code:**
```python
if df.empty:
    st.session_state.pop("selected_position_id", None)
    ...
elif df_filtered.empty:
    st.session_state.pop("selected_position_id", None)
    ...
```

**Problem:** The pairing `selected_position_id` + `_edit_form_sid` is an invariant: whenever one is popped, the other should be too. Today only one is. If the user filters to empty (popping sid), then removes the filter and re-selects a row whose id happens to equal the surviving sentinel, the pre-seed is skipped and widgets retain their last-seen values — which may no longer match the row.

**Fix:** Always pop both together.

```python
if df.empty:
    st.session_state.pop("selected_position_id", None)
    st.session_state.pop("_edit_form_sid", None)
    ...
elif df_filtered.empty:
    st.session_state.pop("selected_position_id", None)
    st.session_state.pop("_edit_form_sid", None)
    ...
# also in the `else` branch of the selection mapping:
else:
    st.session_state.pop("selected_position_id", None)
    st.session_state.pop("_edit_form_sid", None)
```

**No new test** — covered by F1's test, which asserts both keys are absent after Quick-Add clears state.

---

### F5 — Unguarded `fromisoformat` in the pre-seed (Minor)

**Current code:**
```python
st.session_state["edit_deadline_date"] = (
    datetime.date.fromisoformat(r["deadline_date"])
    if r["deadline_date"] else None
)
```

**Problem:** `_deadline_urgency` already documented that `deadline_date` can be malformed in edge cases (T2–T3 review F2 caught this) and swallows both `ValueError` and `TypeError`. The pre-seed does not — one bad row crashes the whole page.

**Fix:** Wrap in try/except mirroring `_deadline_urgency`, falling back to `None` so the `st.date_input` renders empty.

```python
try:
    edit_deadline = (
        datetime.date.fromisoformat(r["deadline_date"])
        if r["deadline_date"] else None
    )
except (ValueError, TypeError):
    edit_deadline = None
st.session_state["edit_deadline_date"] = edit_deadline
```

**No new test** — pure defensive; would require inserting a malformed date via raw SQL (outside the page's input paths). Documented via comment.

---

### F6 — Disabled Save button has no help text (Minor)

**Current code:**
```python
st.form_submit_button("Save Changes", disabled=True)
```

**Problem:** A disabled button with no `help=` tooltip is a dead end — the user clicks, nothing happens, and there is no signal that this is a placeholder. Streamlit supports a `help=` tooltip on form submit buttons.

**Fix:**
```python
st.form_submit_button(
    "Save Changes",
    disabled=True,
    help="Coming in Tier 5 — Save/Delete actions.",
)
```

---

### F7 — Filter change can silently switch the selected row (Known / accepted)

Same mechanism as F1: the `positions_table` widget's selection state is an index into the *current* `df_display`, so changing a filter can make index `N` point to a different row. Unlike F1, filter changes are user-initiated and the table caption updates visibly, so the cognitive cost is lower. Leaving as-is; revisit if users report confusion.

**Possible future fix:** track the previous `(status_filter, priority_filter, field_filter)` tuple and pop the `positions_table` state whenever it changes.

---

## What Looks Good

- **Config-driven tab labels** (`config.EDIT_PANEL_TABS`) — adding a new tab is a 1-line config edit, per the project's extensibility goal.
- **Sentinel pre-seed pattern** is the correct, minimal fix for Streamlit's widget-value trap — clearly commented and isolated to T4-C.
- **Unfiltered `df` is the lookup source for the edit panel**, so filter-narrowing does not dismiss an in-progress edit. Deliberate and well-commented.
- **The `TABLE_KEY` constant** in the tests is called out as part of the page's public contract — protects against silent breakage if the key is renamed.
- **`test_widgets_update_on_selection_change`** directly guards the widget-value trap regression, which is exactly the kind of non-obvious bug future maintainers would re-introduce.

---

## Verdict

**Approve with fixes** — all findings are fixable inside T4-C's scope and are applied in this review. Re-run `pytest tests/` after fixes; expected count: 167 → 170 (three new regression tests: F1, F2, F3).
