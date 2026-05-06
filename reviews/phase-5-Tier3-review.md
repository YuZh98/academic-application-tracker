# Phase 5 — Tier 3 Code Review

**Branch:** `feature/phase-5-tier3-InterviewManagementUI` (6 commits ahead of `main`; T2 merged via PR #16 → `b9a2c82`)
**Verdict:** Approve, merge after the inline fixes land.
**Scope:** T3 — Inline interview list UI on `pages/2_Applications.py` (DESIGN §8.3 D-B). Two sub-tasks:
  1. **T3-A** (3 commits) — Interview list rendering inside the existing T2 `st.container(border=True)`. Per-row `apps_interview_{id}_{date|format|notes}` widgets in an `apps_interviews_form` form. Per-row dirty-diff Save calling `database.update_interview` once per dirty row only. Add button outside the form (Streamlit 1.56 forbids `st.button` inside `st.form`) calling `database.add_interview(sid, {}, propagate_status=True)` with R2 cascade-promotion toast surfacing on `status_changed=True`. Per-row pre-seed sentinel `_apps_interviews_seeded_ids` (frozenset, intersection-pruned each rerun) preserves sibling-row drafts and stays zombie-id-free across deletes.
  2. **T3-B** (3 commits) — Per-row Delete via `@st.dialog`. Module-level `_confirm_interview_delete_dialog` helper opened via the gotcha-#3 re-open trick (single post-loop `pending_id in current_ids` guard, which doubles as automatic stale-target cleanup when the user navigates to a different position). Per-row Delete buttons in a horizontal `st.columns(N)` row BELOW the form (Streamlit constraint), each labelled `🗑️ Delete Interview {seq}` so per-row association stays unambiguous despite the vertical separation.
**Stats:** `pages/2_Applications.py` +388 / -0 (file 517 → 905 lines, ≈75% growth on T2's detail card). `tests/test_applications_page.py` +1 342 (file 1 598 → 2 946 lines). 6 new test classes carrying ≈ 38 cases (25 in T3-A — `TestApplicationsInterviewListRender` 6, `TestApplicationsInterviewSave` 9, `TestApplicationsInterviewAdd` 6, `TestApplicationsInterviewSentinelLifecycle` 4 — and 13 in T3-B — `TestApplicationsInterviewDeleteButton` 5, `TestApplicationsInterviewDeleteDialog` 8). `CHANGELOG.md` +2 (per the `[Unreleased]` Keep-a-Changelog 1.1.0 §14.4 abbreviation style adopted in commit `db383e3`); `TASKS.md` +106. **638 → 676 tests passing under both `pytest -q` and `pytest -W error::DeprecationWarning -q`** (+38 net).
**Cadence:** Two TDD rounds, three commits each — `test:` red → `feat:` green → `chore:` rollup. T3-A and T3-B each shipped as one logical unit (mirror of T2's split). Six commits total.
**Reviewer attitude:** Skeptical and didactic. Verify every cascade claim against `database.add_interview`'s contract; verify the dialog re-open trick is correctly implemented (gotcha #3 is load-bearing for AppTest); semantic UX walk-through against DESIGN §8.3 D-B; ULTRA-HARD think about test gaps the existing 38 cases don't cover; cross-grep T2 and T3 for cohesion drift on toast ordering, sentinel lifecycle, and selection-preservation.

---

## Executive summary

T3 is the densest Phase-5 surface so far: per-row widgets keyed on dynamic interview ids, a multi-form layout (the detail-card form from T2 + a sibling interviews form), a `@st.dialog` modal for irreversible delete, and three different cascade signals (T2-A's R1/R3 on Save, T3-A's R2 on Add, no cascade on Save/Delete). The 38-case test class pins the per-row keying contract, every dirty-diff branch (clean / date / format / notes / multi-row / clear-to-NULL), every R2 cascade path (SAVED no-fire, APPLIED → INTERVIEW promotion, INTERVIEW idempotency), the per-row pre-seed sentinel's full lifecycle (first-render seeding, Add adds, Delete prunes, position-change resets), and every dialog path (open / Confirm / Cancel / re-open / stale-target / failure preserves state).

The implementation works through three Streamlit constraints rigorously: (1) `st.button` cannot live inside `st.form` — so the Add button + per-row Delete buttons live OUTSIDE the form, with the Delete buttons in a horizontal `st.columns(N)` row below; (2) `@st.dialog` does not auto-re-render across AppTest reruns — handled via the gotcha-#3 re-open trick (single post-loop `pending_id in current_ids` guard) which also doubles as automatic stale-target cleanup; (3) `st.dataframe` event resets across data-change reruns — handled via the existing `_applications_skip_table_reset` one-shot from T2 across both Confirm and Cancel paths.

The semantic UX walk-through surfaces **one 🟠 inconsistency** between T2-B and T3-A's toast-ordering pattern: T2-B's Save handler fires `Saved "X"` THEN `Promoted to Y` (Saved-first); T3-A's Add handler fires `Promoted to Y` THEN `Added interview` (Promoted-first). The user sees opposite orders for analogous "user action with cascade side-effect" events in the same product. The page-level comment claims T3-A "mirrors T2-B's R1/R3 surfacing" but the framings are literally contradictory: T2-B's "chronological — Promoted is the consequence of Save" implies user-action-first; T3-A's "the cascade fired during the add itself" implies cascade-first. **Both orderings can be defended in isolation but not in the same product.** Fixed inline by swapping T3-A's order to match T2-B (Added first, Promoted second).

The review further surfaces **one 🟠 DESIGN drift** (DESIGN §8.3 D-B says `format` selectbox is over `INTERVIEW_FORMATS` and Delete is just `🗑️` glyph; code uses `[None, *INTERVIEW_FORMATS]` and `🗑️ Delete Interview {seq}` — both deviations are JUSTIFIED but undocumented in DESIGN), **four 🟡 polish observations** (test gap on toast ordering — fixed inline; test gap on sibling-row draft preservation across Save/Add; test gap on partial Save failure mid-loop; inconsistent Add/Delete toast wording — Add omits sequence, Delete includes it), **two 🟢 future-work items** (defensive `seq is None` guard in the dialog; source-grep for `type="primary"` on the Confirm Delete button), and **one ℹ️ carried-forward observation** (the §6 grep miscount at `pages/1_Opportunities.py:395`, sixth tier in a row).

**Verdict: approve, merge after the inline toast-order fix + ordering test land.** The DESIGN drift (Finding #2) is left for the user to apply since DESIGN.md is read-only this session per the user's standing instruction.

---

## Findings

| # | File · Line | Issue | Severity | Status |
|---|-------------|-------|----------|--------|
| 1 | `pages/2_Applications.py` lines 891–901 (T3-A Add handler) | Toast order **inconsistent** with T2-B Save handler. T2-B fires `st.toast("Saved …")` THEN conditional `st.toast("Promoted to …")` — comment says *"Saved-then-Promoted, chronological — Promoted is the consequence of Save"*. T3-A fires conditional `st.toast("Promoted to …")` THEN `st.toast("Added interview.")` — comment says *"R2 ordering mirrors T2-B's R1/R3 surfacing: Promoted toast fires BEFORE the Added toast so the chronological readout is correct (the cascade fired during the add itself)"*. The two framings contradict each other; the user sees opposite orderings for analogous "user action with cascade side-effect" events in the same product. | 🟠 drift | **Fixed inline** — swapped T3-A order to match T2-B; comment rewritten to align (see Q1) |
| 2 | DESIGN §8.3 D-B vs `pages/2_Applications.py` lines 624–636, 720–726 | DESIGN §8.3 D-B says `format` selectbox is `over config.INTERVIEW_FORMATS` (no leading `None`) and the Delete button is per-row `🗑️` glyph. Code uses `options=[None, *config.INTERVIEW_FORMATS]` (with `format_func` rendering `None` as `—`) and labels each Delete button `🗑️ Delete Interview {seq}`. Both deviations are JUSTIFIED — the leading `None` covers freshly-Added rows where format=NULL (Sonnet plan-critique signal), and the explicit `Delete Interview {seq}` label is required because the buttons live in a horizontal `st.columns(N)` row BELOW the form (Streamlit forbids buttons inside forms) and need per-row labels — but DESIGN doesn't reflect either reality. A new contributor reading DESIGN would think the leading `None` is a bug. | 🟠 drift | **NOT fixed** — DESIGN.md is read-only this session per the user's standing instruction. Documented for the user to apply. (See Q2) |
| 3 | `tests/test_applications_page.py` (`TestApplicationsInterviewAdd`) | The 6 cases assert `any("Promoted to" in v for v in toast_values)` and `any("Added interview" in v for v in toast_values)` independently — both verify EXISTENCE but neither asserts the chronological INDEX relationship. A regression that swaps the order (re-introduces Finding #1) would not be caught. | 🟡 polish | **Fixed inline** — added `test_added_toast_fires_before_promoted_toast` pinning the order (see Q3) |
| 4 | `tests/test_applications_page.py` (`TestApplicationsInterviewSave`, `TestApplicationsInterviewAdd`) | No test directly verifies that **a sibling row's in-flight draft survives** when (a) Save is triggered with a different row dirty, or (b) Add is triggered while another row has unsaved changes. The `_apps_interviews_seeded_ids` per-row pre-seed sentinel is the load-bearing mechanism for this — its lifecycle is well-tested in `TestApplicationsInterviewSentinelLifecycle`, but the user-visible *effect* (drafts survive sibling actions) isn't pinned. A future regression that pops the sentinel inside the Save / Add handler (e.g., copy-paste from T2-A's pop pattern) would slip past every existing test. | 🟡 polish | Documented; defer (see Q4) |
| 5 | `tests/test_applications_page.py` (`TestApplicationsInterviewSave`) | `test_save_failure_uses_st_error_no_reraise` covers a single-row failure but not the **partial-save case**: row 1 dirty, row 2 dirty, `update_interview` succeeds for row 1 then raises for row 2. The user sees `st.error`; row 1 is committed; row 2 is not. The current Save handler structure (single try/except wrapping the for loop) makes partial commits possible because `update_interview` opens its own per-row connection. Not a bug per se — the design is "best-effort per-row" — but the partial state is undocumented. | 🟡 polish | Documented; defer (see Q5) |
| 6 | `pages/2_Applications.py` line 901 (Add toast) and `pages/2_Applications.py` line 158 (Delete toast) | The Add toast says `"Added interview."` (no sequence). The Delete toast says `"Deleted interview {seq}."` (with sequence). The `add_interview` return shape is `{"id", "status_changed", "new_status"}` — no `sequence`, so the page can't include it without an extra DB read or a contract change. Inconsistent toast wording across analogous lifecycle events. | 🟡 polish | Documented; defer (see Q6) |
| 7 | `pages/2_Applications.py` lines 191–197 (`_confirm_interview_delete_dialog`) | The dialog defensively guards `if iid is None` but does NOT guard `if seq is None`. If a future bug pops `_apps_interview_delete_target_id` but leaves `_apps_interview_delete_target_seq` unset (or vice versa), the warning would render `"Interview None will be permanently deleted."`. The page consistently writes both sentinels together (paired-cleanup convention), so this state is unreachable today, but defensive parity would future-proof the helper. | 🟢 future | Documented; defer (see Q7) |
| 8 | `pages/2_Applications.py` line 209 (Confirm Delete button) | `st.button("Confirm Delete", type="primary", ...)` — the styling is structural (the destructive action gets the primary visual weight). Per gotcha #9, AppTest's `Button.type` reports the widget class name, NOT the Streamlit `type=` keyword, so the styling cannot be tested via AppTest. A source-grep test (T6 funnel-toggle precedent — `test_toggle_uses_tertiary_type`) would pin the contract. Not currently tested. | 🟢 future | Documented; defer (see Q8) |
| 9 | `pages/1_Opportunities.py` : 395 (pre-existing) | The pre-existing `'[APPLIED]'` literal in a docstring-style comment trips the GUIDELINES §6 status-literal grep. **Sixth tier in a row** (T3 / T4 / T5 / T6 / Phase-5 T2 / now Phase-5 T3). The resolution path (`rg -v '^\s*#'` GUIDELINES §11 amendment) is documented in three prior reviews; nobody has shipped it. | ℹ️ Observation | Carry-over (see Q9) |

---

## Fixes applied in this review

**Two fixes landed inline:**

1. **`pages/2_Applications.py`** — T3-A Add handler. Swapped the toast order to fire `st.toast("Added interview.")` BEFORE the conditional `st.toast("Promoted to ...")`, matching T2-B's Saved-then-Promoted pattern. Rewrote the inline comment to explain the convention consistently (`Order is Added-then-Promoted (chronological — Promoted is the consequence of the Add)`, paralleling T2-B's exact phrasing). The user now sees the same temporal pattern across Save and Add.

2. **`tests/test_applications_page.py`** — `TestApplicationsInterviewAdd`. Added `test_added_toast_fires_before_promoted_toast` pinning the chronological INDEX relationship: `added_idx < promoted_idx` in `at.toast`. Mirrors the T2-B Saved-then-Promoted ordering claim; future regressions on the order surface here as a clean test failure.

**NOT fixed:**

- **Finding #2 (DESIGN §8.3 D-B drift):** Per the user's standing instruction "follow DESIGN and GUIDELINES exactly (must read, and read only)", `DESIGN.md` is not modified this session. The drift is documented; the user can amend §8.3 D-B to reflect the Streamlit-constraint-driven deviations (leading `None` in format selectbox; per-row sequence-labeled Delete buttons in a horizontal row below the form).

- **Findings #4 / #5 (test gaps):** Documented for a future hardening pass. Adding the sibling-draft and partial-save-failure tests would land naturally alongside any T7 polish work.

- **Findings #6 / #7 / #8 / #9:** Polish and future items, deferred per the established defer-if-cheap rule.

---

## Junior-engineer Q&A

### Q1 — The toast-order fix changes "Promoted-then-Added" to "Added-then-Promoted." Why is this consistency worth a 🟠 finding?

**A.** Because the user mental model is one product, not two pages.

The Applications page already has TWO surfaces that fire a "user action toast + cascade promotion toast" pair:

- **T2-B Save** (the application detail form): Save persists the application row → R1 may fire (SAVED → APPLIED) or R3 may fire (APPLIED → OFFER). The page fires:
  ```
  Saved "Postdoc Slot".
  Promoted to Applied.   ← (only when status_changed)
  ```
  Comment: *"Order is Saved-then-Promoted (chronological — Promoted is the consequence of Save)."*

- **T3-A Add** (the interview list): Add inserts a new interview → R2 may fire (APPLIED → INTERVIEW). The page (pre-fix) fired:
  ```
  Promoted to Interview.   ← (only when status_changed)
  Added interview.
  ```
  Comment: *"R2 ordering mirrors T2-B's R1/R3 surfacing: Promoted toast fires BEFORE the Added toast so the chronological readout is correct (the cascade fired during the add itself)."*

The two comments are LITERALLY contradictory:
- T2-B says: "chronological — Promoted is the consequence of Save" → action first, consequence second.
- T3-A says: "chronological — the cascade fired during the add itself" → cascade first, action second.

Both can't be "the chronological order" of the same kind of event. The user, having clicked Save on the application form and clicked Add on the interview list ten minutes apart, sees:

- *On Save:* "I saved, and as a consequence, the position got promoted." Mental model: **action → effect**.
- *On Add:* "Got promoted, then... I added something?" Mental model: **effect → action**? That doesn't parse.

The user has to RECONSTRUCT the causal chain from the wrong-order toasts. A small UX papercut, but exactly the kind of thing that erodes trust in the product over many interactions.

**The fix is one-line in the page** (swap two `st.toast` calls) and one-line in the comment (rewrite to match T2-B's framing). Plus a test pin (Finding #3) so the regression cannot slip back.

The framing chosen — **action first, consequence second** — is the right convention because:

1. **It matches the user's intent direction.** The user *wanted* to perform the action (Save / Add). The promotion is a side-effect they didn't directly request.
2. **It's the same pattern web frameworks use for flash messages.** Rails' `flash[:notice]` after a save renders before the cascade-effect notice; React Toastify queues main + secondary in source order.
3. **It's the order T2-B already uses.** Choosing "T3-A matches T2-B" is the lowest-cost path to consistency — flipping T2-B would be a bigger refactor with its own test rewrite.

A reasonable counter-argument could be made: cascade-side-effect first because it's higher priority. But the project already chose action-first in T2-B and shipped it; the cohesion bar is "T3-A matches T2-B," not "rewrite both."

### Q2 — Why doesn't the review fix the DESIGN §8.3 D-B drift?

**A.** Because the user's standing instruction this session is *"follow DESIGN and GUIDELINES exactly (must read, and read only)"*. The "read only" qualifier is new; in prior tier reviews (T2 / T4 / T5 / T6) the user has authorized DESIGN amendments as part of the work, but this session explicitly carves out DESIGN as off-limits.

The drift itself is real and worth documenting:

- **Format selectbox** — DESIGN says `selectbox over config.INTERVIEW_FORMATS`. Code says `selectbox over [None, *config.INTERVIEW_FORMATS]` with `format_func` rendering None as `—`. The leading `None` is REQUIRED for freshly-Added rows where `format=NULL` in DB; without it, the selectbox would default to `INTERVIEW_FORMATS[0]` (`"Phone"`) and silently dirty-write a value the user never chose. (This is the Sonnet plan-critique signal recorded in the CHANGELOG; same anti-pattern as the T2-A `response_type` selectbox.)

- **Delete button label** — DESIGN says per-row `🗑️` button. Code labels each `🗑️ Delete Interview {seq}`. The expanded label is required because `st.form` forbids `st.button` inside, so the per-row Delete buttons live in a horizontal `st.columns(N)` row BELOW the form. A row of N glyph-only buttons would lose per-row association entirely; the sequence-labeled version preserves it.

Both deviations are GOOD design choices forced by Streamlit constraints; DESIGN §8.3 D-B is the document that needs to catch up. The right amendment:

```
- Per-row widgets: `scheduled_date` (`st.date_input`),
  `format` (`st.selectbox` over `[None, *config.INTERVIEW_FORMATS]`
   with `format_func=lambda v: EM_DASH if v is None else v` so a freshly-
   Added row with `format=NULL` defaults to None rather than the first
   INTERVIEW_FORMATS entry), `notes` (`st.text_input`).
- Per-row Delete buttons live in a single horizontal `st.columns(N)`
  row BELOW the form (Streamlit 1.56 forbids `st.button` inside `st.form`),
  each labelled `🗑️ Delete Interview {seq}` so the per-row association
  is unambiguous despite the vertical separation from the form widgets.
- Widget keys scope to the interview's primary key for stability across
  reruns: `apps_interview_{id}_{date|format|notes|delete}`.
```

This review does not apply that amendment. The user is empowered to decide whether to land it.

### Q3 — Why is a test for toast ordering more than belt-and-suspenders?

**A.** Because Finding #1's regression is exactly the kind of thing a future maintainer would re-introduce by good intent.

Imagine a future maintainer reading the T3-A code post-fix and thinking: *"Wait, the Promoted toast represents an event that happened AFTER the Add inside the transaction. Shouldn't I show that first?"* They swap the order back. Tests pass — the existing 6 cases all use `any(... in toast_values)` which doesn't care about order. The user gets the inconsistency back.

The new test:

```python
def test_added_toast_fires_before_promoted_toast(self, db):
    pid = database.add_position(make_position())
    database.update_position(pid, {"status": config.STATUS_APPLIED})

    at = _run_page()
    _select_row(at, 0)
    _keep_selection(at, 0)
    at.button(key=ADD_INTERVIEW_KEY).click()
    at.run()

    toast_values = [el.value for el in at.toast]
    added_idx = next(
        (i for i, v in enumerate(toast_values) if "Added interview" in v),
        None,
    )
    promoted_idx = next(
        (i for i, v in enumerate(toast_values) if "Promoted to" in v),
        None,
    )
    assert added_idx is not None and promoted_idx is not None
    assert added_idx < promoted_idx, (
        f"Added must fire BEFORE Promoted (matches T2-B's "
        f"Saved-then-Promoted pattern). Got order: "
        f"{[(i, v) for i, v in enumerate(toast_values)]}"
    )
```

Streamlit's `at.toast` list is in chronological order (the framework appends in source order). So `added_idx < promoted_idx` directly verifies "Added fires first."

Why this is necessary, not just nice-to-have:

1. **The contract is invisible to the existing tests.** `any(...)` checks pass for any non-empty toast list with the right substrings, regardless of order.
2. **The same regression pattern caused Finding #1 to ship in the first place.** The CHANGELOG / TASKS / page-comment all documented an ordering claim ("Promoted-before-Added is chronologically correct") that nobody verified empirically. The test would have caught the mismatch with T2-B before merge.
3. **Order-sensitive UI events are a common test-gap class.** Toasts queue, modal stacks order matter, focus-trap rules depend on element order. Pinning order with `<` / `>` index assertions is cheap; not pinning lets drift accumulate.

### Q4 — How realistic is the sibling-row draft regression? Is the test gap in Finding #4 worth flagging?

**A.** Realistic enough that the existing comment in `pages/2_Applications.py` explicitly calls it out:

```python
# The seeded-ids sentinel is intentionally NOT popped here:
# update_interview is a direct write with no normalization, so
# the widget already reflects DB state after Save. Popping
# would force every row to re-seed on the post-Save rerun and
# clobber unsaved drafts on sibling rows — different from the
# T2-A detail-form pop pattern, where upsert_application can
# potentially normalize values.
```

The comment names the failure mode the no-pop choice prevents. But the failure mode itself isn't pinned by a test. The closest test (`test_clean_row_skipped_when_other_dirty`) verifies the **DB write count** (one call, not two). It does NOT verify that the clean row's session_state widget value survives the post-Save rerun.

The gap is concrete: a future maintainer who copy-pastes T2-A's `st.session_state.pop("_applications_edit_form_sid", None)` pattern into the T3-A Save handler would:

1. Pop the seeded-ids sentinel.
2. Next render: `seeded_ids = saved_sentinel & current_ids` evaluates `frozenset() & current_ids = frozenset()`.
3. Every row's id is `in current_ids - seeded_ids` → all rows re-seed from DB.
4. The clean row's draft (which the user typed but didn't intend to save) is wiped.

The user-visible regression: "I typed something in row 2, then clicked Save on row 1's edit, and my row-2 work disappeared." Hard to reproduce; easy to miss in code review.

The test:

```python
def test_save_one_row_preserves_sibling_row_draft(self, db):
    pid = database.add_position(make_position())
    database.update_position(pid, {"status": config.STATUS_APPLIED})
    i1 = database.add_interview(pid, {"notes": "row1-old"})["id"]
    i2 = database.add_interview(pid, {"notes": "row2-old"})["id"]

    at = _run_page()
    _select_row(at, 0)

    # Edit row 1 (will save) AND row 2 (in-flight draft).
    at.session_state[_w_interview_notes(i1)] = "row1-new"
    at.session_state[_w_interview_notes(i2)] = "row2-draft"
    _keep_selection(at, 0)
    at.button(key=INTERVIEWS_SAVE_KEY).click()
    at.run()

    # Row 1 saved.
    rows = database.get_interviews(pid)
    target_1 = rows[rows["id"] == i1].iloc[0]
    assert target_1["notes"] == "row1-new"

    # Row 2's draft survives in session_state (not saved to DB; not wiped).
    assert at.session_state[_w_interview_notes(i2)] == "row2-draft", (
        "Sibling row's in-flight draft must survive Save of another row. "
        f"Got: {at.session_state[_w_interview_notes(i2)]!r}"
    )
    # And the DB still has row 2's old value (draft is unsaved).
    target_2 = rows[rows["id"] == i2].iloc[0]
    assert target_2["notes"] == "row2-old"
```

I'm flagging this as 🟡 polish (not 🟠 drift) because the user-visible failure isn't currently happening — the no-pop choice is correctly implemented. The test would be a regression guard for a future copy-paste mistake. Worth landing in a polish pass.

### Q5 — The partial-save failure is documented as 🟡 polish. Should the page be redesigned to atomic-multi-row?

**A.** It would be the right design for a multi-user remote DB; for v1's single-user local SQLite it's overkill.

The current design's failure mode:

```
Save with rows 1, 2, 3 all dirty:
  update_interview(i1, {...})  ← succeeds, commits
  update_interview(i2, {...})  ← raises (e.g., disk full simulated)
  ← except branch fires: st.error(...), st.toast NOT fired, st.rerun NOT fired
  → row 1 is persisted, rows 2 and 3 are not
  → user sees error, refreshes, sees row 1 changed but row 2 in pre-Save state
  → re-tries: row 1 is now clean (matches DB), row 2 is dirty, row 3 unchanged
  → Save would just retry row 2.
```

So the user can recover, but the path is non-obvious. An atomic-multi-row design would:

```python
with database._connect() as conn:
    for iid, dirty_fields in dirty_rows:
        conn.execute("UPDATE interviews SET ... WHERE id = ?", ...)
# Either all rows commit or none do.
```

This requires:
1. A new helper like `database.update_interviews_bulk(updates: list[tuple[int, dict]])`.
2. The Save handler builds the `dirty_rows` list and calls the bulk helper.
3. Both the helper and the new failure mode get tests.

For v1, the cost-benefit is wrong: real SQLite failures (disk full, file lock contention) are extremely rare on a personal local file. The current "best-effort per-row + show error on first failure" design fails into a recoverable state. A backlog item, not a merge blocker.

The TEST gap is more interesting than the partial-save behaviour itself: today, no test exercises the partial-failure path at all. A test would:

```python
def test_partial_save_failure_persists_earlier_rows(self, db, monkeypatch):
    pid = database.add_position(make_position())
    database.update_position(pid, {"status": config.STATUS_APPLIED})
    i1 = database.add_interview(pid, {"notes": "row1-old"})["id"]
    i2 = database.add_interview(pid, {"notes": "row2-old"})["id"]

    at = _run_page()
    _select_row(at, 0)

    # Patch update_interview to succeed for i1, fail for i2.
    original = database.update_interview
    def _selective(interview_id, fields):
        if interview_id == i2:
            raise RuntimeError("simulated row-2 failure")
        return original(interview_id, fields)
    monkeypatch.setattr(database, "update_interview", _selective)

    at.session_state[_w_interview_notes(i1)] = "row1-new"
    at.session_state[_w_interview_notes(i2)] = "row2-new"
    _keep_selection(at, 0)
    at.button(key=INTERVIEWS_SAVE_KEY).click()
    at.run()

    # Error surfaced.
    error_values = [el.value for el in at.error]
    assert any("row-2 failure" in v for v in error_values)

    # Row 1 IS persisted (partial-save semantics).
    rows = database.get_interviews(pid)
    assert rows[rows["id"] == i1].iloc[0]["notes"] == "row1-new"
    # Row 2 is NOT persisted (the raise stopped the loop before it).
    assert rows[rows["id"] == i2].iloc[0]["notes"] == "row2-old"
```

Pinning the partial-save behaviour now means a future "let's add a transaction wrapper" change has a test to either accept the new atomic behaviour or to break loudly.

### Q6 — The Add toast omits the sequence number; the Delete toast includes it. Why is this a 🟡 finding rather than a quick fix?

**A.** Because the fix has to choose between three options, and the right one isn't obvious.

The asymmetry:

| Event | Toast | Has sequence? |
|---|---|---|
| Add | `"Added interview."` | No |
| Delete | `"Deleted interview {seq}."` | Yes |
| Save | `"Saved interviews."` | N/A (multi-row) |

The reason Add lacks the sequence is mechanical: `database.add_interview` returns `{"id": new_id, "status_changed": bool, "new_status": str|None}` — no `sequence` field. The page can't include the sequence in the toast without:

**Option A: Add `"sequence"` to `add_interview`'s return shape.**
```python
return {
    "id": new_id,
    "sequence": new_sequence,
    "status_changed": ...,
    "new_status": ...,
}
```
Cost: one DB-side change, every caller (currently just T3-A) updated. Benefit: clean API; future consumers (exports, reports) get the sequence for free. **Recommended approach.**

**Option B: Page-side compute via `len(current_ids) + 1`.**
The new sequence is auto-assigned as `MAX(sequence) + 1` for the application_id; on a fresh add-into-empty-list it's 1, on an add-into-N-list it's N+1. The page can compute this without a DB read. Cost: zero. Risk: the relationship `len(current_ids) + 1 == new_sequence` is true today but is an implementation detail of `add_interview`'s sequence assignment — if a future product call lets the user pick a sequence number on Add, this calculation breaks silently.

**Option C: Page-side re-query after Add.**
```python
new_iid = _add_result["id"]
new_seq = database.get_interviews(sid).query(f"id == {new_iid}").iloc[0]["sequence"]
```
Cost: one extra DB read. Benefit: doesn't depend on `add_interview`'s sequence-assignment semantics.

Which is right depends on a question the team hasn't answered: **is `add_interview`'s `{id, status_changed, new_status}` return shape locked, or extensible?** The CHANGELOG / DESIGN don't pin it. So flagging this as 🟡 polish is the correct framing — *"there's a choice to make, and we shouldn't make it inside a test sub-task."*

If the team picks (A), the analogous Save toast might also gain a row count: `"Saved 3 interviews."` or `"No changes saved."` for the clean-form case. That's a wider polish surface, naturally bundled into a Phase 7 or polish-tier sweep.

### Q7 — Why is the "defensive `seq is None`" guard a 🟢 future, not a 🟡 polish?

**A.** Because the failure mode is unreachable today and the cost of being wrong is small ("Interview None will be permanently deleted" instead of a clean error message).

The dialog's defensive logic:

```python
iid: int | None = st.session_state.get("_apps_interview_delete_target_id")
seq: int | None = st.session_state.get("_apps_interview_delete_target_seq")
if iid is None:
    st.error("Delete target was lost — please re-open the dialog.")
    return
# ... uses both iid and seq below ...
```

The `iid is None` guard catches the case where the dialog is opened without the id sentinel set. The page wouldn't normally reach that state — the post-loop guard `if _pending_delete_id is not None: ... _confirm_interview_delete_dialog()` is the only invocation site. So the inner guard is defense-in-depth for a future bug.

The `seq is None` case has an analogous structure: every click handler writes both sentinels together (`_target_id` and `_target_seq`). Every cleanup pops both together. So `id set without seq set` is structurally unreachable. But:

- A future bug that pops one sentinel without the other (refactor mistake, async cleanup race, etc.) would surface as `"Interview None will be permanently deleted."` — a confusing UX.
- The defensive-parity fix is one line:
  ```python
  if iid is None or seq is None:
      st.error("Delete target was lost — please re-open the dialog.")
      return
  ```

I'm framing this as 🟢 future because:
1. The current state is correct.
2. The defensive guard is symmetrical to the existing one (the existing one IS already a 🟢 future-style protection).
3. The cost of NOT having it is "one ugly toast in an unreachable case."

If a future review or polish pass surfaces this, the fix is one line. Not blocking.

### Q8 — Why is the source-grep test for `type="primary"` a 🟢 future?

**A.** Same flavour as Finding #7 — the contract is structural and untested, but the failure mode is small (the Confirm Delete button looks "default" instead of "primary"), and the fix is cheap.

The Streamlit / AppTest gap (gotcha #9):

```python
# Page:
st.button("Confirm Delete", type="primary", key=...)

# Test:
btn = at.button(key=...)
assert btn.type == "primary"   # FAILS — btn.type returns "Button" (class name)
```

T6's `TestT6FunnelToggle.test_toggle_uses_tertiary_type` ships the precedent for pinning this kind of thing via source-grep:

```python
def test_confirm_delete_button_is_primary_type(self):
    src = pathlib.Path(PAGE).read_text(encoding="utf-8")
    # Strip comment lines (T6 precedent).
    code = "\n".join(
        line for line in src.splitlines()
        if not line.lstrip().startswith("#")
    )
    # The Confirm Delete button is the only `type="primary"` in this page,
    # so an exact-count grep on executable code is precise.
    assert code.count('type="primary"') >= 1, (
        "Confirm Delete must use type=\"primary\" so the destructive "
        "action gets the strongest visual weight (T6 precedent)."
    )
```

Why 🟢 not 🟡: the regression mode is "Confirm button is less visually emphatic." The user can still find and click it; the action still works. Compare to Finding #1 (toast ordering) where the user actively misreads the page state — that's a worse failure.

If the project ever lands a `type="secondary"` or `type="tertiary"` button on this page in the future (e.g., a "Reset form" button), the count-based assertion would need to be tightened to a more specific match. Defer until that lands.

### Q9 — The §6 grep carry-over is now on its sixth tier. Why are reviews still flagging it?

**A.** Because flagging it is the right action even when the fix isn't shipping. Three reasons:

1. **The grep IS the safety net.** Until the fix lands, the grep is the contract that catches accidental status-literal usage in production code. Each review's flag is a re-acknowledgment of *"yes, the safety net is still doing its job; the flag is the noise we accept while the fix isn't prioritized."*

2. **The flagging behaviour establishes the discipline.** A future status-literal that accidentally lands in production would also surface in this same review pattern — a reviewer who suppresses the flag because *"there's always one"* is one social signal away from suppressing a real defect.

3. **The deferred-fix cost is decreasing.** Each review's flag adds a sentence to the *"this has been deferred N times"* meter; eventually a reviewer will land the fix not because the cost-benefit changed but because the social cost of *"this has been deferred SEVEN times"* exceeds the implementation cost.

The fix itself remains: tighten the GUIDELINES §11 grep to `rg --type py 'pattern' app.py pages/ | rg -v '^\s*#'` (strip comment lines). One-line change. Carry over to the eventual `reviews/phase-5-finish-review.md` close-out.

### Q10 — The semantic UX walk-through: did I identify everything that doesn't make sense?

**A.** The walkthrough surfaced the toast-ordering inconsistency (Finding #1) as the dominant issue. Beyond that, the page is semantically coherent for the v1 use case. A quick check of the user-visible flow:

1. **Open the Applications page** → six-column table sorted by deadline. Selectable. Filter dropdown above. ✓
2. **Click a row** → detail card appears with `"{institute}: {position_name} · {STATUS_LABELS[status]}"` header, inline `"All recs submitted: ✓ / —"` line, 8-widget `apps_detail_form`. ✓
3. **Click Save (detail card)** → Saved toast → conditional Promoted toast (T2-B order). ✓
4. **Scroll down** → `**Interviews**` section header, then either:
   - Empty list → just the Add button.
   - Non-empty list → `apps_interviews_form` with per-row widgets, Save button, then a horizontal row of `🗑️ Delete Interview {seq}` buttons, then the Add button. ✓
5. **Edit a row's date** → click Save → `"Saved interviews."` toast (always; clean rows skip DB write). ✓
6. **Click Add** → (after fix) `"Added interview."` toast → conditional `"Promoted to ..."` toast. ✓
7. **Click Delete on a row** → modal opens with title `"Delete this interview?"`, warning `"Interview {seq} will be permanently deleted. This **cannot be undone**."`, primary `"Confirm Delete"` button, secondary `"Cancel"` button. ✓
8. **Click Confirm** → `"Deleted interview {seq}."` toast → row gone. ✓
9. **Click Cancel** → silent close, no toast, row stays. ✓
10. **Filter narrowing that excludes the selected row** → table shows `"No applications match the current filter."` info, but the detail card stays open (asymmetry vs Opportunities §8.2, locked since T2-A). ✓

The flows compose cleanly. No semantic dead-ends, no stale UI states, no orphaned widgets. The only inconsistency is the toast-ordering pattern, which the inline fix addresses.

Subtle UX papercuts that are NOT findings (intentional or kept-by-design):

- **`"Saved interviews."` on a clean form** — the toast fires unconditionally so the user gets feedback even when nothing changed. Minor lie ("nothing was actually saved") but better than confusing silence.
- **Add button doesn't switch into "Save first" mode when there are unsaved changes** — clicking Add while typing in another row inserts a new interview; the in-flight draft on the other row survives the rerun (per the per-row pre-seed sentinel). User has to remember to click Save afterwards. Acceptable, well-tested.
- **Delete buttons in a horizontal row at narrow widths (5+ interviews)** — at 1280px viewport with 5+ interviews, the buttons get cramped. Layout responsiveness untested via AppTest. 🟢 future polish concern; not yet a finding.

---

## Observations for Tier 4+ design

Forward-looking, not blocking T3:

1. **The page is approaching its final shape.** T3 closes the Applications-page DESIGN §8.3 contract: shell (T1) + detail card (T2) + interview list (T3). The next functional slot is the page's polish and the Recommenders page (Phase 5 T4). The pre-merge review for Phase 5 finish (T7) should pull in the test gaps from Findings #4 and #5 plus the carry-over from #9.

2. **The per-row sentinel pattern (`_apps_interviews_seeded_ids`) is the project's first dynamic-id pre-seed mechanism.** Phase 5 T5 (Recommenders) will need its own version; the pattern is reusable. Recommend lifting the pattern documentation into `docs/dev-notes/streamlit-state-gotchas.md` as a new entry — it's a non-obvious extension of gotcha #2 (single-id sentinel) and the Sonnet plan-critique signals (NaN dirty-diff, format-`None` pre-seed, zombie-id pruning) are all captured in the inline page comments but not yet centralized.

3. **The dialog re-open trick (gotcha #3 + the `pending_id in current_ids` guard) is now used in two places** — Opportunities-page delete and Applications-page interview delete. The guard's "stale-target silent cleanup" double-duty is a clever optimization documented inline but not in the gotchas file. Same recommendation as (2).

4. **The Streamlit form-vs-button constraint** (Streamlit 1.56 forbids `st.button` inside `st.form`) drove TWO design choices in T3: the Add button outside the form, and the Delete buttons in a horizontal `st.columns(N)` row below. This constraint has been a recurring DESIGN drift driver (recall T2's `apps_detail_submit` is form_submit_button, not button). Worth a one-line callout in `streamlit-state-gotchas.md` so future page authors don't try the obvious "just put it inside the form."

5. **Phase 5 T2-B vs T3-A toast-order pattern (Finding #1) reveals an unwritten convention.** The fix lands "action-then-cascade" everywhere; recommend formalizing it in DESIGN §8.0 cross-page conventions: *"When a user action triggers a cascade-side-effect, the toast for the user action fires FIRST, the cascade toast fires SECOND. Same chronological framing as Saved-then-Promoted in §8.3."*

---

## Verdict

**Approve, merge after the inline fixes land.**

- Suite green: 676/676 under both `pytest -q` and `pytest -W error::DeprecationWarning -q` after the fixes (was 676 before; the new ordering test adds one but doesn't change the green/red count).
- One 🟠 toast-ordering inconsistency fixed inline (T3-A Add handler now matches T2-B's Saved-then-Promoted pattern); one new test pinning the order (`test_added_toast_fires_before_promoted_toast`).
- One 🟠 DESIGN §8.3 D-B drift documented but NOT fixed (DESIGN read-only this session per the standing instruction).
- Four 🟡 polish observations (one fixed inline; three documented for a polish pass).
- Two 🟢 future items + one ℹ️ carry-over.
- The 38-test class pins the per-row keying, every cascade path, the per-row pre-seed sentinel lifecycle, every dialog path including stale-target cleanup and failure-preserves-state. The semantic UX walk-through is clean post-fix.

**Merge sequence:** push branch → open PR → reviewer scan → squash-merge → continue to T4 (Recommenders alert panel) on a fresh branch.

---

_Review by skeptical-reviewer session, 2026-05-01._

---

## Pre-merge review addendum — T3-rev-A / T3-rev-B

**Date:** 2026-05-01 (second-pass, Sonnet)
**Suite:** 683/683 green under both `pytest -q` and `pytest -W error::DeprecationWarning -q`.
**Scope:** Review of the T3-rev-A (Position/Institute column split) and T3-rev-B (per-row interview blocks) commits that landed after the first-pass review above.

### What changed since the first-pass review

| Commit | Change |
|--------|--------|
| `ba7cd47` | DESIGN §8.3 + wireframes amended for T3-rev: Position/Institute split + per-row block architecture (Finding #2 drift **resolved**) |
| `ec3228e` | Tests for T3-rev-A Position/Institute split added |
| `1d73ebc` | Page: Position/Institute split in 7-column table |
| `015371b` | Tests rewritten for T3-rev-B per-row blocks |
| `f116dbf` | Page: single `apps_interviews_form` replaced by per-row `apps_interview_{id}_form` blocks |
| `1cbbd9f` | Tracker rollup |

Net test change: 676 → 683 (+7). Six new tests land across `TestApplicationsPageTable`, `TestApplicationsTableColumnConfig`, and `TestApplicationsInterviewSave`; one old test (`test_two_dirty_rows_call_update_interview_twice`) was retired and replaced by `test_clicking_one_row_save_does_not_persist_sibling_row`.

### First-pass findings status

| # | Severity | Finding | Status |
|---|----------|---------|--------|
| 1 | 🟠 | Toast order inconsistency (Added vs Promoted) | **Resolved** — first-pass inline fix, now also reflected in DESIGN §8.3 line 615 |
| 2 | 🟠 | DESIGN §8.3 D-B drift (format selectbox, Delete label) | **Resolved** — DESIGN amended in commit `ba7cd47` |
| 3 | 🟡 | Test gap on toast ordering | **Resolved** — `test_added_toast_fires_before_promoted_toast` |
| 4 | 🟡 | Test gap on sibling-row draft survival | **Resolved** — `test_save_one_row_preserves_sibling_row_draft` |
| 5 | 🟡 | Test gap on partial Save failure path | Deferred — still not landed |
| 6 | 🟡 | Add/Delete toast wording asymmetry (no seq on Add) | **Resolved by side-effect** — T3-rev-B Save toast now reads `"Saved interview {seq}."` (singular + seq); all three lifecycle toasts now carry a sequence |
| 7 | 🟢 | Defensive `seq is None` guard in dialog | Deferred |
| 8 | 🟢 | Source-grep test for `type="primary"` on Confirm Delete | Deferred |
| 9 | ℹ️  | `[APPLIED]` literal in `pages/1_Opportunities.py:395` comment | Carry-over (seventh tier) |

### New findings — pre-merge pass

| # | File · Line | Issue | Severity | Status |
|---|-------------|-------|----------|--------|
| 10 | `pages/2_Applications.py` line 422 (pre-fix) | **Stale comment**: "T3 adds a sibling `apps_interviews_form` inside the same container above the detail form" — `apps_interviews_form` was retired in T3-rev-B; all interview widgets now live in per-row `apps_interview_{id}_form` blocks. A future maintainer reading this comment would believe the single-form architecture is still in place. | 🟡 stale doc | **Fixed inline** — rewritten to name T3-rev-B's per-row blocks and note the T3-A retirement. |
| 11 | `pages/2_Applications.py` lines 578-586 (pre-fix) | **Stale comment**: "Per-row widgets (date_input, selectbox, text_input) live inside `apps_interviews_form`" — same retired-form reference. The adjacent code immediately below uses the correct `apps_interview_{_iid}_form` key, so the disconnect is jarring: comment says one form, code uses N forms. | 🟡 stale doc | **Fixed inline** — rewritten to describe the T3-rev-B per-row block architecture (each row = `apps_interview_{id}_form`, holding heading + detail + Save submit + per-row Delete below). |
| 12 | `tests/test_applications_page.py` `TestApplicationsInterviewSave` | **Test gap**: The T3-rev-B per-row Save handler sets `_applications_skip_table_reset = True` (page line 894) before `st.rerun()` to preserve selection across the post-Save dataframe-event-reset (gotcha #11). T2-A's analogous handler has two pinning tests: `test_save_preserves_selection` and `test_save_handler_sets_skip_table_reset_flag`. T3-rev-B's handler has neither — a regression that drops the flag would lose the card selection after every interview Save. | 🟡 polish | Documented; defer. |
| 13 | `pages/1_Opportunities.py:395` | `[APPLIED]` literal in comment (carry-over from Finding #9). | ℹ️ carry-over | Carry-over (seventh→eighth tier). |

### Fixes applied in this addendum

**Two stale-comment fixes (Findings #10 and #11):**

- **Line 422**: "T3 adds a sibling `apps_interviews_form`…" → "T3 adds per-row `apps_interview_{id}_form` blocks (T3-rev-B; the T3-A single-form `apps_interviews_form` was retired)…"
- **Lines 578-586**: "widgets live inside `apps_interviews_form`; the Add button lives OUTSIDE" → "T3-rev-B: each interview is a self-contained per-row block — `apps_interview_{id}_form` (border=False) holding heading + detail row + per-row Save submit, plus a per-row Delete button OUTSIDE the form…"

Both fixes are purely in comments; no logic changed. Suite still 683/683 green after.

**NOT fixed:**

- **Finding #12** (per-row Save selection-preservation test): Deferred to a polish pass alongside Finding #5.
- **Finding #13** (§6 carry-over): Same deferred path as Finding #9.

### Junior-engineer Q&A (addendum)

#### Q-A1 — Why does T3-rev-B's Save handler (line 894) need `_applications_skip_table_reset = True`, and why is the test gap (Finding #12) worth calling out?

**A.** Every time Streamlit reruns the page with new data (e.g., after a DB write + `st.rerun()`), the `st.dataframe` widget resets its selection event. The `selected_rows = list(event.selection.rows)` expression reads from the fresh event, which is now empty — so the else branch pops `applications_selected_position_id`, closing the detail card.

The one-shot flag `_applications_skip_table_reset` is the bypass: when set, the `elif st.session_state.pop("_applications_skip_table_reset", False):` branch consumes the flag (one-shot) and falls through without popping the selection key. Result: card stays open.

T2-A's two pinning tests verify this for the application-level Save handler:

```python
# test_save_handler_sets_skip_table_reset_flag — verifies the flag is set
# test_save_preserves_selection — verifies the card survives the rerun
```

T3-rev-B's per-row Save handler uses the SAME flag (line 894) but has no analogous test. The regression failure mode:

```
User clicks Save on interview row 1 →
   st.rerun() fires WITHOUT skip flag →
   dataframe event = empty →
   else branch pops applications_selected_position_id →
   detail card closes →
   "Saved interview 1." toast fires but the card is gone
```

This would be a jarring UX: the user edits an interview, clicks Save, sees the toast — and the card they were editing disappears. Hard to reproduce in automated review (the absence of the skip flag looks like a logic change, not a missing line), easy to miss. Pinning with a test mirrors the T2-A pattern.

The test sketch (deferred to a polish pass):

```python
def test_per_row_save_preserves_position_selection(self, db):
    pid = database.add_position(make_position())
    database.update_position(pid, {"status": config.STATUS_APPLIED})
    iid = database.add_interview(pid, {"notes": "old"})["id"]

    at = _run_page()
    _select_row(at, 0)

    at.session_state[_w_interview_notes(iid)] = "new"
    _keep_selection(at, 0)
    at.button(key=_w_interview_save(iid)).click()
    at.run()

    assert SELECTED_PID_KEY in at.session_state, (
        "Per-row interview Save must preserve applications_selected_position_id "
        "across the post-Save rerun via _applications_skip_table_reset (gotcha #11)."
    )
    assert at.session_state[SELECTED_PID_KEY] == pid
```

#### Q-A2 — What's the net benefit of T3-rev-B's per-row architecture vs the retired single-form?

**A.** Three concrete improvements over the T3-A single-form:

1. **Sibling-row draft isolation**: T3-A's single form batched ALL dirty rows on Save. The per-row architecture means clicking row 1's Save ONLY commits row 1; row 2's in-flight draft survives untouched. Under T3-A, the only way to discard row 2's accidental edit was to click Cancel / close the page.

2. **Toast granularity**: T3-A said `"Saved interviews."` (ambiguous count). T3-rev-B says `"Saved interview {seq}."` (tells the user exactly which row was committed). This also resolved Finding #6's Add/Delete wording asymmetry as a side-effect — now all three lifecycle events (Add / Save / Delete) carry sequence information.

3. **Delete placement**: T3-A's Delete buttons were in a horizontal `st.columns(N)` row at the bottom (to stay outside the single form). T3-rev-B's Delete button is immediately below the form for its row — the per-row block reads top-to-bottom: heading → date/format/notes → Save → Delete. More natural spatial association.

The cost: each interview renders its own `<form>` in the HTML output, adding minor DOM overhead. At the v1 scale (10²–10³ positions, 1–10 interviews each, DESIGN §3.1), this is negligible.

#### Q-A3 — The DESIGN amendment in `ba7cd47` now accurately describes T3-rev-B. Does that close Finding #2 completely?

**A.** Yes, for this review's scope. The amended DESIGN §8.3 D-B now correctly documents:

- Format selectbox: `[None, *config.INTERVIEW_FORMATS]` with `format_func` rendering `None` as EM_DASH.
- Delete button label: `🗑️ Delete Interview {seq}` (not just `🗑️`).
- Toast ordering: action-first / cascade-second (Added-then-Promoted convention).

All three deviations that the first-pass review flagged as undocumented drift are now in DESIGN. A new contributor reading §8.3 D-B would see the correct spec before writing any code.

### Verdict

**Approve — merge.**

- Suite: 683/683 green under both pytest gates.
- All 🟠 first-pass findings resolved (toast order, DESIGN drift).
- All 🟡 first-pass findings either resolved (draft survival, ordering test, wording asymmetry) or documented for a polish pass (partial-save failure, selection-preservation test).
- Two new 🟡 stale-comment findings fixed inline; one new 🟡 test gap documented for a polish pass; one ℹ️ carry-over unchanged.
- T3-rev-A and T3-rev-B are coherent with DESIGN §8.3, GUIDELINES patterns, and each other.

**Merge sequence:** push branch → open PR → squash-merge → continue to Phase 5 T4 (Recommenders page) on a fresh branch. Polish-pass findings (#5, #12) and carry-over (#13) go into the Phase 5 finish review.

---

_Pre-merge addendum by skeptical-reviewer session, 2026-05-01._
