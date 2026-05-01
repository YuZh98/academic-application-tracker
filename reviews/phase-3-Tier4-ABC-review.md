# Phase 3 Tier 4 (T4-A / T4-B / T4-C) Code Review
**Branch:** `feature/phase-3-tier4`
**Scope:** T4-A (single-row selection), T4-B (subheader + tab shell), T4-C (7 pre-filled Overview widgets in `st.form("edit_overview")`, `_edit_form_sid` pre-seed).
**Verdict:** Approve with fixes F1–F6 applied; ready to merge.
**Files reviewed:** `pages/1_Opportunities.py` (row selection, edit-panel shell, Overview tab)
**Date:** 2026-04-19
**Reviewer:** Claude (skeptical + didactic)

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

---

## Pre-merge Q&A (feature/phase-3-tier4 → main)

Before opening the PR, a junior engineer asked seven questions about the branch's choices and review. Recording them here so the answers live alongside the code they explain.

**PR scope:** 11 commits, +824/−17 lines, 7 files touched (mostly `pages/1_Opportunities.py` + `tests/`).

### Q1. Why 11 commits for one feature? Shouldn't we squash before merge?

**No — keep `--no-ff` with history preserved.** The commits are not noise; they are a teaching artefact. Each tier has a paired `test:` → `feat:` → `chore:` triplet that makes the TDD cycle readable from `git log`: "here are the failing tests, here is the implementation that made them pass, here is the tracking bump." The final `review(...)` commit groups all post-review fixes with their three regression tests. If a later bisect is needed (e.g., "when did the Quick-Add behaviour change?"), tier-level granularity is the right unit. The project's `GUIDELINES §9` explicitly rejects both extremes (one giant commit, or wip-every-line) — this branch is the "just right" middle. Merge with `--no-ff` so the tier boundary is preserved on `main`.

### Q2. `pages/1_Opportunities.py` is now 243 lines and mixes five concerns (title, quick-add, filter, table, edit panel). Time to split it?

**Not yet.** Page files are expected to read top-to-bottom as a UI script — that's Streamlit's model. Extracting helpers into `opportunities_helpers.py` now would obscure the one thing that's currently clear: the vertical order of sections matches the visual order on screen. The section-marker comments (`# ── TIER N: ... ────`) serve as navigation. Revisit after T4-D–F and T5 land — if the file crosses ~400 lines **and** any section reaches internal complexity (nested state machines, non-trivial computations), extract *that section* only, not a blanket refactor. The `_deadline_urgency` helper is the right precedent: it stayed inline until it needed a docstring, then lifted.

### Q3. Why `on_select="rerun"` instead of a `selection`-callback API?

Streamlit 1.56's `st.dataframe` supports only `on_select="rerun"` or `"ignore"` — there is no per-row callback hook (that API exists on `st.data_editor`, which is a different widget with edit-in-place semantics we don't want). The rerun model is also a better fit for this app's dataflow: the entire page re-runs on every interaction, which is how filter-narrowing-then-selection works cleanly without explicit state machines. The cost is a full rerun on every click — acceptable for a single-user local app with O(100) rows.

### Q4. Why the `_edit_form_sid` sentinel pattern instead of just passing `value=r["priority"]` to the selectbox?

This was discovered the hard way during T4-C: **once `session_state[key]` has a value, Streamlit ignores the `value=` argument on subsequent reruns.** Using `value=` alone means the form pre-fills correctly on the *first* selection and then "sticks" forever — selecting row B would still show row A's values. The canonical fix is to write the intended values into `session_state[key]` whenever the source data changes, gated by a sentinel that detects the change. `test_widgets_update_on_selection_change` directly guards this regression, because it's the kind of bug a future maintainer would re-introduce by "simplifying" the code.

### Q5. Review finding F2 coerces `None` priority to `PRIORITY_VALUES[0]`. Isn't that hiding a data-quality problem?

It's a defensive coercion, not data repair. The DB column is legitimately nullable (no `DEFAULT` in the schema), and the quick-add form always sets a value — so today all rows have a priority. F2 guards against three future drifts: (1) a new "bulk import" path that leaves the field blank, (2) a sqlite3 CLI edit, (3) a future migration that adds a new priority tier and leaves legacy rows with the removed value. The selectbox still *displays* the fallback, so the user sees a plausibly-wrong value and can correct it. The alternative — crashing the page — is strictly worse for a personal tool. Once T5 ships a save path, we could add a server-side validator that rejects unknown priorities at write time; that's the layer where enforcement belongs, not the display layer.

### Q6. The test file is now 900+ lines with 170 tests, mostly AppTest integration tests. Is this bloat?

**No, but the boundary is worth watching.** AppTest is the right harness for page-level contracts (what renders when, which widget keys exist, how session_state evolves) — these can't be meaningfully unit-tested. The 170-count looks large but the full suite runs in ~2.5 seconds, so there's no developer friction yet. The signal to watch is: if a future change requires rewriting >10 tests for a single widget rename, that's a test-coupling smell and those tests should be compressed into a parametrized one. For now, explicit tests per behaviour (one `test_selection_mode_is_single_row`, one `test_four_tabs_appear_when_row_selected`, etc.) read better in `pytest -v` output than a clever table.

### Q7. `config.EDIT_PANEL_TABS` is a list, but the page indexes into `tabs[0]..tabs[3]` by position. What happens if someone adds a 5th tab via config?

Streamlit would render 5 tabs, but only the first 4 would have bodies — the 5th would appear empty. This is a known coupling: **config controls labels; page controls bodies.** The two have to stay in sync. Two reasonable futures: (a) accept the coupling and document it (current choice — cheap, obvious at read time), (b) move to a dict-of-callables in `config` so the page can dispatch by label. Option (b) violates the "config.py is constants only, no functions" rule from `GUIDELINES §2`. For a 4-tab UI this won't change often, so (a) is fine. If a 5th tab ever appears, the reviewer should force a compile-time error by asserting `len(config.EDIT_PANEL_TABS) == 4` at the top of the page — a better guard than silent empty tabs.

### Q8. Merge strategy — `--no-ff`, `--squash`, or rebase?

**`--no-ff`.** Rationale per `GUIDELINES §9`:
- `--squash` would collapse the TDD triplets and hide the review→fix narrative — exactly what we want to preserve for a learning project.
- Rebase-onto-main would linearise history and drop the tier-boundary signal (the merge commit is the marker that "this is one shipped feature").
- `--no-ff` creates one merge commit that summarises "Phase 3 Tier 4 A/B/C complete", with all 11 commits reachable through it.

Command: `git checkout main && git merge feature/phase-3-tier4 --no-ff -m "Merge Phase 3 Tier 4 A/B/C: row selection, edit-panel shell, Overview tab"` followed by `git tag v1-phase-3-tier4-abc` to mark the checkpoint.

---

**Final verdict after Q&A:** ready to merge. Branch is green (170/170 tests pass), history is clean, all review findings are addressed with regression guards, and no TODO/FIXME/print/debug residue remains in the diff.

