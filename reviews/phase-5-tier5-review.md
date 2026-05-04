**Branch:** `feature/phase-5-tier5-RecommendersTableAddEdit`
**Scope:** Phase 5 T5 — `pages/3_Recommenders.py` All-Recommenders table + filters + Add form + inline edit card with dialog-gated Delete; `RELATIONSHIP_TYPES` → `RELATIONSHIP_VALUES` rename
**Stats:** 56 new tests (700 → 756 passed, 1 xfailed); +1642 / −9 lines across 6 files; ruff clean; status-literal grep 0 lines
**Verdict:** Approve (post-merge — PR #29 already squashed to `2293ebd`)

---

## Executive Summary

T5 layers the working surface of the Recommenders page on top of T4's
Pending Alerts: a six-column read-only `st.dataframe` (`recs_table`)
with two filter selectboxes, an Add-Recommender form gated behind an
expander, and an inline edit card behind row selection with a
dirty-diff Save and a `@st.dialog`-gated Delete. All four AGENTS §T5
contracts (T5-A / T5-B / T5-C plus the `RELATIONSHIP_VALUES` rename)
land in one PR, with the test suite climbing 700 → 756 (1 xfailed
unchanged). Architecture mirrors precedents the project already pays
for: Opportunities §8.2 selection-resolution + dialog re-open trick
(gotcha #3), Applications T2-A `_safe_str`-normalized dirty-diff Save,
Applications T3-B single dialog call site with stale-target cleanup,
and the Opportunities Quick-Add expander idiom for the Add form.

---

## Findings

| # | File | Location | Description | Severity | Status |
|---|------|----------|-------------|----------|--------|
| 1 | `pages/3_Recommenders.py` | `_FILTER_ALL = "All"` (line 275) | The "All" filter sentinel is a third site of the same magic literal — joining `pages/1_Opportunities.py` and `pages/2_Applications.py`. Logged carry-over **C3** in `reviews/phase-5-tier1-review.md` covers this; T5 inherits the issue rather than introducing it. No action this tier. | 🟢 | Tracked under C3 |
| 2 | `pages/3_Recommenders.py` | Save handler (lines 622–633) | When the dirty-diff is empty, the page still fires `st.toast(f'Saved "{name}".')` even though no DB write happened. Honest read — Save's contract is "no error" — but the toast wording "Saved" can read as "persisted a change" to the user. Cohesion is internal (Applications T2-A behaves the same way for an unchanged form). Note for a future Phase 7 polish pass; not a defect. | ℹ️ | Observation |
| 3 | `pages/3_Recommenders.py` | Recommender-filter dedupe (lines 290–296) | `_seen` is a `list` with O(n) `in`-lookups inside an O(n) iteration — O(n²). For `n` recommenders, n is tiny. A `set`-tracked guard with a separate ordered list would be O(n) and equivalent. Cosmetic; do not refactor for its own sake. | ℹ️ | Observation |
| 4 | `pages/3_Recommenders.py` | Position filter options (lines 281–282) | Position filter options come from `get_all_positions()` (the add-form's source) rather than the joined recommenders frame. Net effect: a position without recommenders shows in the filter dropdown but never narrows results to anything. Documented in code; matches the dashboard T4 precedent of "filter coverage ≥ data coverage" so a fresh-add target stays selectable. Intentional. | ℹ️ | Observation |

*No 🔴 / 🟠 / 🟡 findings.*

---

## Junior-Engineer Q&A

**Q1. The position selectboxes use `"{institute}: {position_name}"` as the option *value*, then look up `position_id` at submit time via `_position_label_to_id`. Why not use the id as the value with a `format_func`?**

A. Two reasons cohabit. First, DESIGN §8.4 pins "IDs never surface to the user" — using the label as the value keeps the rendered widget value AND `st.session_state["recs_add_position"]` human-readable, so debugging in the Streamlit session inspector or in test fixtures stays grounded. Second, `AppTest` exposes selectbox options as the raw `options=` list with no `format_func` applied; if the option values were ids, every test that picks a position would have to know the id, and most tests work in terms of position names. The label-as-value encoding makes both human and AppTest read paths agree, at the cost of one dict lookup at submit time.

**Q2. Why does the Save handler compute a dirty diff against the persisted DB row instead of just sending the full widget snapshot?**

A. Three reasons. (1) The AGENTS §T5-C contract says "Save writes only dirty fields" — pinned by `test_save_writes_only_dirty_fields`. (2) `database.update_recommender(rec_id, fields)` is a partial-update writer; if the page sent a full snapshot, an unchanged TEXT field that the user never touched would still get re-written, and the `updated_at` audit trail (when added) would lose meaning. (3) The dirty-diff is a forward-compatibility hedge — when Phase 6 exports start watching `updated_at` to decide what changed since the last export, full-snapshot writes would trip every export to mark every row dirty.

**Q3. The Save toast fires `Saved "{name}"` even when `_dirty` is empty (no DB write). Is that wrong?**

A. It is honest under the contract "Save means I tried, no error happened" — and matches the Applications T2-A precedent of always toasting after a successful Save attempt. The cost is that "Saved" reads as "persisted a change" to a user who pressed Save without editing anything. Two cleaner options exist: (a) toast `No changes to save.` when `not _dirty`, or (b) suppress the toast entirely on no-op. Either is a Phase 7 polish concern, not a T5 defect. Logged as Finding #2 above for visibility.

**Q4. `_confirm_delete_recommender_dialog()` is called from BOTH the `if st.button(...)` branch AND the `elif st.session_state.get("_recs_delete_target_id") == _rec_id` branch. Isn't the elif redundant — the button click already opened the dialog?**

A. This is gotcha #3 — Streamlit's `@st.dialog` does not auto-re-render across `st.rerun()` triggered by widgets *inside* the dialog. When the user clicks Confirm or Cancel, Streamlit reruns the page; on the rerun, the original `st.button("Delete", ...)` click is no longer "true" (button clicks don't persist), so the `if` branch wouldn't re-invoke the dialog body and AppTest's script-run model would never reach Confirm/Cancel. The `elif` re-opens the dialog as long as the pending sentinels are set; the Confirm/Cancel handlers pop those sentinels, which is what closes the dialog cleanly. The single dialog call site post-loop is also the same shape Applications T3-B used for multi-row interview Delete (`pending_id in current_ids` guard — automatic stale-target cleanup).

**Q5. The selection-resolution block pops `_recs_delete_target_id` and `_recs_delete_target_name` when the user switches to a different row. Why?**

A. Without it, the dialog re-open path (`elif st.session_state.get("_recs_delete_target_id") == _rec_id`) would fail silently on the new row (target id mismatch) but the sentinels would still sit in session state. Then when the user switches *back* to the original recommender, the dialog would re-fire as a phantom — they pressed Delete on Person A, switched to Person B, switched back to A, and suddenly the dialog is open again with no fresh user action. Popping on row-change is the precedent fix from the Opportunities-page review (fix #2 in `opportunities-page-bug-fix-2026-04-25-review.md`).

**Q6. The widget pre-seed loop uses `if _sid_changed or _key not in st.session_state` — what does the `or _key not in st.session_state` clause buy on top of `_sid_changed`?**

A. It handles the second-rerun case where the user clicks Save, the handler pops `_recs_edit_form_sid` (so the post-Save rerun re-seeds widgets from the freshly-persisted DB row), and then on the post-Save rerun the sid sentinel comes back as `_rec_id` (so `_sid_changed` is False) — but the widget keys have NOT been re-seeded yet, because the `pop` only cleared the sid sentinel, not every widget key. The `or _key not in st.session_state` clause re-seeds widgets that aren't yet in session state on the rerun, which is what makes "click Save → see the toast → see the form reflect the saved values" work cleanly. Two-phase apply, gotcha #2.

**Q7. Why does `_db_confirmed = _safe_confirmed` reuse the pre-seed normalisation rather than reading `_rec_row["confirmed"]` again?**

A. The dirty-diff comparator must use the *same* `int | None` normalisation as the widget's pre-seed, because `_w_confirmed` is whatever the user picked from the `[None, 0, 1]` selectbox — already an `int | None` — and a NaN-from-NULL on the DB side would compare unequal to `None` (NaN ≠ NaN, NaN ≠ None) and trip a phantom dirty write on every Save. Reusing `_safe_confirmed` keeps the two sides of the equality check on the same ladder; pulling fresh would risk a NaN sneaking through.

**Q8. Why is the Add form inside `with st.expander("Add Recommender", expanded=False)` rather than rendered inline above the table?**

A. The page's primary surface is the table — the user opens the page to *see* recommenders, not to add one (Adds are sparse; viewing is constant). Putting Add behind an expander keeps the table above the fold while still giving the Add path a single, discoverable home. This is the same idiom the Opportunities page uses for Quick Add (`with st.expander("Quick Add", ...)`); cohesion across pages 1 and 3 is the reason DESIGN §8 is structured as per-page contracts rather than per-feature ones.

---

## Carry-overs

- **C3** ("All" filter sentinel → `config.py`) extends to `pages/3_Recommenders.py`. Logged in `reviews/phase-5-tier1-review.md`; deferred to a cleanup tier per that review.
- **Phase 7 polish candidate** — Save-toast wording when `_dirty` is empty (Finding #2). Park here; revisit during the Phase 7 confirm-dialog audit (TASKS.md).

---

_Written 2026-05-03 post-merge as the T5 close-out doc per the
`phase-5-tier1` / `phase-5-Tier2` / `phase-5-Tier3` / `phase-5-tier4`
precedent. PR #29 was merged via admin-bypass (`gh pr merge 29
--squash --admin`) per `ORCHESTRATOR_HANDOFF.md` "Branch-protection
note" before this review was written; the verdict is recorded as
Approve given the green pre-merge gates and the clean architectural
reuse of established precedents._
