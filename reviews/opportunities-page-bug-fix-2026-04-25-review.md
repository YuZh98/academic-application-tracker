# Final Review — Opportunities-Page Bug Fix Round (2026-04-25)

## Executive Summary

Two user-reported bugs on `pages/1_Opportunities.py` (position-name
disappearing on tab switch; Requirements/Materials default-value drift)
were diagnosed, attempted-fixed once with a defensive `session_state`
restoration layer, and ultimately resolved by reverting the Sub-task 13
architecture change (`st.radio + conditional rendering` →
`st.tabs(...)`). User confirmed both bugs resolved in the browser.

**Verdict: Approve with two doc-drift nits (fixed in this review).**

Branch: `review/test-reliability-2026-04-25` (4 commits in this round).
Tests: 478 pass; 478 also pass under `-W error::DeprecationWarning`.
Net diff vs the start of this round:

```
 CHANGELOG.md                     |  73 ++++++
 DESIGN.md                        |  16 +-
 pages/1_Opportunities.py         | 327 ++++++++++++------------
 tests/test_opportunities_page.py | 521 ++++++++++++++++++++++++++-------------
 4 files changed, 616 insertions(+), 321 deletions(-)
```

---

## Findings

| # | File | Line | Description | Severity | Status |
|---|------|------|-------------|----------|--------|
| 1 | `pages/1_Opportunities.py` | 411 | Pre-seed block's "Bug 1 + Bug 2 fix" comment describes Sub-task 13's `st.radio + conditional rendering` swap as if it were currently in effect. Post-revert, the actual fix is the architecture revert; the two-phase pre-seed is defense-in-depth. A junior reading this comment will be confused about why a "fix" exists for a bug that the rest of the file says was fixed by reverting Sub-task 13. | 🟠 Drift | Fixed inline |
| 2 | `tests/test_opportunities_page.py` | 1609 | `test_text_area_renders_when_row_selected` docstring says "Sub-task 13: Notes widgets only render when active_tab == 'Notes'." Post-revert, every tab's widgets render every script run. | 🟠 Drift | Fixed inline |
| 3 | `pages/1_Opportunities.py` | ~607 (Save handlers) | Each save handler still pops `_edit_form_sid` and sets `_skip_table_reset`. The `_skip_table_reset` flag is independent of tab architecture (guards `st.dataframe` selection reset) and is correctly kept. The `_edit_form_sid` pop is correctly kept (forces post-save reload from DB). | 🟢 Kept by design | — |
| 4 | `pages/1_Opportunities.py` | 525–529 (two-phase apply) | Under `st.tabs`, the second branch (`key not in st.session_state`) is essentially dead code — every widget renders every run, so keys never go missing. Kept as defense-in-depth. | 🟢 Kept by design | — |
| 5 | `tests/test_opportunities_page.py` | TestTabSwitchWidgetStateSurvival (8 tests) | Originally written to reproduce the unmount-cleanup bug class. Under `st.tabs` they pass trivially. Kept as architectural regression guards. | 🟢 Kept by design | — |
| 6 | `tests/test_opportunities_page.py` | `_select_row_and_tab` helper | Soft-aliased to drop the `tab_name` effect rather than removing the function or renaming all ~30 call sites. Diff stays focused on the architectural fix. | 🟢 Kept by design | — |
| 7 | `GUIDELINES.md` | §7 (Pre-seeding edit forms — uses the `_edit_form_sid` sentinel) | Still accurate post-revert (the sentinel still exists and still drives the force-overwrite path). No update needed. | 🟢 Kept by design | — |

---

## Junior-Engineer Q&A

### Q1: Why keep the two-phase pre-seed if `st.tabs` already eliminates the cleanup bug?

Three reasons:
1. **Defense-in-depth.** Streamlit's widget-cleanup behavior is documented but
   has changed across versions (the cleanup-on-unmount semantics were
   introduced in v1.20). If a future version were to clean up `text_area`
   or `radio` on a configuration we hadn't anticipated, the missing-key
   restoration in the second branch would absorb it.
2. **The cost is microscopic.** The second-branch check is `key not in
   st.session_state` per widget key (~24 keys). Microseconds per render.
3. **The architectural-drift safety net.** If someone in the future
   re-introduces conditional rendering (intentionally for a feature that
   needs it, or accidentally via a refactor), the two-phase apply prevents
   user-visible data loss while the issue is being noticed.

### Q2: Why didn't you also remove `_skip_table_reset` if it was related to the same bug class?

`_skip_table_reset` is **independent** of the tab architecture. It guards
against `st.dataframe`'s on-data-change behavior: when any save commits
data, the dataframe widget resets its `selection` event to `{rows: []}`
on the next rerun. Without `_skip_table_reset = True`, the
selection-resolution block at the top of the page would interpret the
empty selection as "user deselected" and pop `selected_position_id`,
collapsing the edit panel right after Save. This still happens under
`st.tabs`. `_skip_table_reset` is correctly kept.

This is a good example of why "small one-shot flags" should be looked at
case-by-case during a refactor: it's tempting to delete them all when
their original justification is no longer obvious, but each can have
multiple reasons-to-exist.

### Q3: Why keep `TestTabSwitchWidgetStateSurvival`'s 8 tests if they pass trivially under `st.tabs`?

They serve as **architectural regression guards**. The next contributor
who proposes "let's swap `st.tabs` for `st.radio + conditional rendering`
to expose `active_tab` programmatically" will run the tests, see them
pass, and feel safe — then fail browser-side just like Sub-task 13 did.

This wouldn't catch them.

The tests pass under `st.tabs` because no widget unmount happens, but
the test names (`_persists_after_round_trip`, `_persists_when_switching_row`)
and assertion strings ("Bug 1: position name disappeared") describe a
bug class. A future regression that re-introduces conditional rendering
would trip them in AppTest the same way the original Bug 1 did. They are
cheap (run in seconds) and high-signal — keep.

A future review could *strengthen* them by adding a class-level docstring
that explicitly says: "if you find these passing trivially because
nothing's mounting/unmounting, do NOT remove them — they exist as
regression guards against re-introducing conditional rendering."

### Q4: Why soft-alias `_select_row_and_tab(at, i, tab_name)` instead of removing it or renaming all 30 call sites?

Two reasons:
1. **Minimum-diff principle.** The change is architectural. Sweeping
   ~30 test call sites with a rename has zero behavioural value and
   bloats the PR. A reviewer scrolling the diff has to verify each rename
   is harmless rather than focusing on the actual structural change.
2. **Future re-purposability.** If we ever DO need a programmatic
   tab-selection helper (e.g., for an AppTest path that simulates a tab
   click via a hypothetical `at.tabs[i].click()`), the function signature
   is already in place. The body becomes a one-line update.

The function docstring is updated to make the no-op behavior explicit, so
a reader of the helper immediately knows what's going on.

### Q5: How does a future contributor know not to re-introduce conditional rendering?

Three places now have explicit warnings:

1. **`pages/1_Opportunities.py:531-545`** — comment block above
   `tabs = st.tabs(config.EDIT_PANEL_TABS)` documents the load-bearing
   reason for `st.tabs` (no widget unmount → no `session_state` cleanup)
   and references the 2026-04-25 user-reported bug.
2. **`DESIGN.md` §8.2 "Edit-panel architecture" paragraph** — pinned
   architecturally, so a contributor reading the design doc before
   touching code sees the rule.
3. **`tests/test_opportunities_page.py` `TestTabSwitchWidgetStateSurvival`
   class** — the tests themselves codify the contract.

If a contributor still re-attempts the swap, the tests fail loudly
in AppTest the moment a `text_input` round-trip is run. The pre-seed
defense-in-depth would mask the failure for `text_input` specifically,
but `radio` cleanup (which is browser-only, not AppTest-modeled) would
still surface as Bug-2-shaped browser-side data loss. Defense-in-depth
buys time to notice; the architectural pin is the real prevention.

### Q6: Aren't form drafts still lost if the user types in one tab without submitting and switches to another?

Yes — but this is **unchanged** by the fix. Drafts inside an unsubmitted
`st.form` are Streamlit-form-internal state, not `session_state`. They
do not survive a rerun. With `st.tabs`, switching tabs IS a rerun (the
tab widget is interactive), so unsaved drafts in the previously-active
tab's form are lost.

This was true before Sub-task 13, true during Sub-task 13, and remains
true after the revert. It is a pre-existing UX trait of `st.form`, not
a regression introduced or fixed by this round of work.

If we ever want unsaved-draft survival across tab switches, the fix is
either (a) auto-save on tab change (complex, risky), or (b) move the
"per-tab-Save" pattern to a single "Save All" button at the page level.
Both are v2 design discussions, not bug-fix scope.

### Q7: Why is the Delete button reachable in the DOM regardless of which tab is "active"?

`st.tabs` renders every tab body on every script run. CSS hides the
inactive tabs' content visually, but the DOM contains them all. So
`at.button(key="edit_delete")` finds the button whether the user is
"on" Overview or not. AppTest does not model CSS visibility — it sees
the DOM.

User-visible behavior is unchanged: the user sees the Delete button
only when on the Overview tab (because `st.tabs` CSS-hides the
non-active tabs' content). This is a perfectly fine separation
of concerns: the user sees CSS, the test sees the DOM.

The four `test_delete_absent_when_active_tab_is_*` tests we removed
asserted DOM-absence — that was an artifact of Sub-task 13's
conditional rendering. After the revert, those assertions no longer
match user-visible behavior, so the tests had to go.

If we ever want to assert "Delete button is CSS-hidden on non-Overview
tabs," that's a UI-layer test (browser-driven via Selenium /
Playwright), not an AppTest test. Out of scope here.

### Q8: What's the lifecycle of `_edit_form_sid` after the revert?

Identical to before:
1. **Pre-seed run #1 after a row is selected.** `_edit_form_sid` is
   missing from `session_state`. Pre-seed sees `sid_changed = True`,
   force-overwrites all widget keys from the row, sets
   `_edit_form_sid = sid`.
2. **Subsequent reruns on the same row (no save).** `_edit_form_sid ==
   sid`, so `sid_changed = False`. Pre-seed's force-overwrite path
   doesn't fire. The missing-key restoration path checks each widget
   key and only fills it if absent (under `st.tabs`, keys don't go
   missing, so this is also a no-op).
3. **User selects a different row.** `selected_position_id` changes
   (row-resolution block at the top). On the next pre-seed run,
   `_edit_form_sid != new_sid` → force-overwrite all keys from the
   new row, set `_edit_form_sid = new_sid`.
4. **User clicks Save.** Save handler pops `_edit_form_sid` and sets
   `_skip_table_reset`. On the post-`st.rerun()` script run,
   `_edit_form_sid` is missing → `sid_changed = True` → force-overwrite
   all keys from the freshly-saved DB row.

The sentinel's role is to differentiate "selected row CHANGED" from
"selected row stayed the same" so that user edits-in-progress don't
get overwritten by the pre-seed every time the page reruns for an
unrelated reason (filter change, dataframe interaction, etc.).

### Q9: Did we cover every save path's contract under the new architecture?

Yes. All four `Test*Save` classes are intact:
- `TestOverviewSave` (7 tests including the all-9-fields round-trip)
- `TestRequirementsSave` (5 tests including the done-fields-preserved-on-req-flip pin)
- `TestMaterialsSave` (5 tests including the done-fields-preserved-on-req-N pin)
- `TestNotesSave` (5 tests including the empty-stored-as-empty-string pin)

All five Tier-5 save contracts (success toast, DB-failure friendly
error, no-traceback, selection survival across rerun, toast survives
rerun) are pinned per tab. The only deletions in this round were five
Sub-task-13-specific tests; none of the save-path coverage was touched.

### Q10: Why isn't there a test that verifies the CSS-hide actually hides the Delete button?

Two reasons:
1. **AppTest doesn't model CSS.** It has no concept of which DOM
   elements are user-visible. To test CSS visibility we'd need a
   browser-driven test framework (Selenium / Playwright / Streamlit's
   own browser-mode), which would add an entirely new test runtime,
   dependency surface, and CI time budget.
2. **`st.tabs` CSS-hide is a Streamlit invariant.** If `st.tabs`
   stopped CSS-hiding inactive tabs, that would be a Streamlit
   regression. We trust it, the same way we trust `st.toast` to
   actually render a toast.

The user verified browser-side that the Delete button is visible only
on Overview. That's the reality check that matters; pinning the same
property in an automated test is a v2/CI-investment question, not a
bug-fix-scope question.

### Q11: What's the actual cost of running pre-seed on every render?

Profiling not done, but reasoning:
- Computing `canonical` is ~10 dict literal entries + 7 iterations of
  `REQUIREMENT_DOCS` (each: 2 lookups, 1 conditional, 1 cast). All
  in-process, no I/O. Microseconds.
- The two-phase apply loop is `len(canonical)` ≈ 24 iterations of
  `if cond or key not in dict: dict[key] = value`. Microseconds.
- Compared to: `database.get_all_positions()` at the top of the page
  (SQLite query + pandas DataFrame construction), `st.dataframe`
  rendering, every other widget instantiation. The pre-seed is rounding
  error.

If perf ever becomes a concern, the pre-seed could be wrapped in a
`@st.cache_data` (with `_edit_form_sid` as the cache key), but
that's premature optimization today.

### Q12: Did `GUIDELINES.md` need updating?

GUIDELINES §7 has a paragraph "Pre-seeding edit forms — use the
`_edit_form_sid` sentinel." That paragraph is still accurate after
the revert: the sentinel still exists, still drives the force-overwrite
path. The two-phase apply is an *additional* defensive layer; the
GUIDELINES paragraph doesn't need to mention it because the
GUIDELINES is about the contract/intent, not the implementation
detail.

If the cleanup-on-unmount Streamlit gotcha needs to be documented for
contributors, the right place is `docs/dev-notes/streamlit-state-gotchas.md`
(referenced from GUIDELINES §7). That's a separate doc-improvement task
worth deferring to a follow-up rather than scope-creeping this PR.

### Q13: How do we know AppTest's behavior won't catch us off-guard somewhere else?

Honestly: we don't, fully. The Bug-2 case (radio cleanup not reproducing
in AppTest) showed AppTest's widget-cleanup model diverges from the
real browser. The mitigation is:
- **Use AppTest for what it CAN model.** Wiring, assertions on widget
  values when widgets are mounted, save-handler logic, DB round-trips.
- **Don't lean on AppTest to pin CSS-visibility, browser-side
  cleanup, real-time tab transitions.** Those are user-facing
  behaviors that need user testing.
- **Prefer architectures that don't depend on AppTest-vs-browser
  fidelity.** This bug-fix round is a perfect example: the chosen fix
  (revert to `st.tabs`) is structural — eliminating the bug class —
  rather than reactive. A reactive fix (defensive `session_state`
  restoration only) would have left us depending on AppTest fidelity
  to verify Bug 2 was actually fixed, and AppTest couldn't model it.
  Structural fixes are better insurance against test-runtime
  divergence.

---

## What the round did well

- **Test-first diagnosis.** The first move on hearing "Bug 1" was to
  write `TestTabSwitchWidgetStateSurvival` and run it. The two failures
  (`test_overview_position_name_persists_after_requirements_round_trip`
  and the all-text-fields variant) made the bug class concrete and
  let us reason about the fix design with empirical grounding.
- **Empirical Streamlit probing.** Rather than assuming what
  `text_input` / `text_area` / `radio` / `checkbox` do under unmount,
  the inline `python << 'EOF'` probes pinned actual behavior. This
  caught the `text_input`-only-cleanup quirk that informed the
  defensive-fix design.
- **Recognizing the failed defensive fix.** When the user reported
  the cross-row variant of Bug 1 still failing in browser despite
  the AppTest tests passing, the response was to acknowledge the
  AppTest-vs-browser divergence and re-evaluate the architecture
  rather than adding more defensive layers. This is the correct call.
- **Atomic, green commits.** Each commit (e2bce18, 3495d61, 2c3a682,
  3dd5703) leaves the suite green. Bisect-friendly.
- **Documenting the architectural decision in DESIGN.md.** The new
  "Edit-panel architecture" paragraph means the next contributor
  has the rationale at hand without needing to dig through commit
  history.

## What could be better next time

- **Reach for the architecture-revert hammer faster.** The defensive
  `e2bce18` fix took ~30 minutes to design and write, and ultimately
  didn't solve the user-visible bug. If we'd assessed "is this bug
  intrinsic to Sub-task 13's architecture?" upfront, we could have
  proposed the revert in the first response.
- **Add a `docs/dev-notes/streamlit-state-gotchas.md` entry** for
  the unmount-cleanup gotcha. The current GUIDELINES.md mentions the
  doc as a depth pointer; the gotcha deserves an entry. Deferred to
  follow-up.
- **Consider a CI step that diffs against a "golden" post-revert
  architecture marker.** A simple `grep -q "tabs = st.tabs("
  pages/1_Opportunities.py` in CI would catch any future swap to
  conditional rendering immediately. Worth a 5-line addition.

---

## Verdict

**Approve with two doc-drift nits (fixed in this review).**

The four-commit round is well-structured, the bug-fix mechanism is
sound, the test churn is justified and minimal, and the documentation
of the architectural decision is thorough. Both nits are
documentation-only and do not affect runtime behavior; they are fixed
in this same PR for cleanliness.
