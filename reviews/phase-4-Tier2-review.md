# Phase 4 — Tier 2 Code Review

**Branch:** `feature/phase-4-Tier2-ApplicationFunnel` (11 commits ahead of `main`)
**Scope:** T2-A (Plotly horizontal bar from `count_by_status()` + `STATUS_COLORS`) → T2-A y-axis reversal fix → T2-B (empty-state branch, Option C + wording γ) → T2-C (left half of `st.columns(2)` per U2)
**Stats:** `app.py` 124 → 170 lines (+46); `tests/test_app_page.py` 412 → 807 lines (+395), +17 tests across 3 new classes (`TestT2AFunnelBar` +7, `TestT2BFunnelEmptyState` +5, `TestT2CFunnelLayout` +5). **263 total tests passing, 0 deprecation warnings.**
**Reviewer attitude:** Skeptical. Trust nothing. Question every implicit assumption. Verify every Streamlit / Plotly API claim.

---

## Executive summary

Tier 2 delivers the Application Funnel panel — a single-trace Plotly horizontal bar sourced from `count_by_status()` with colors pulled verbatim from `config.STATUS_COLORS`, an empty-state branch that's intentionally decoupled from the T1-E hero, and the dashboard's first content row `st.columns(2)` split (T3 will reuse the right half).

The work is well-tested (every data shape, every empty-state branch, every layout slot has a pin), the locked decisions (Option C trigger, wording γ, U2 layout) are each pinned by at least one test, the TDD triplet cadence is clean on the git log (test → feat → chore × 3 + a test → fix pair for the y-axis reversal).

The review surfaces **no bugs**, **two test-drift hardening fixes** applied pre-merge, **one stale in-file doc comment** applied pre-merge, and **five intentional-but-worth-naming design choices** or coverage gaps that become relevant once T3–T5 land.

---

## Findings

| # | File · Line | Issue | Severity | Status |
|---|-------------|-------|----------|--------|
| 1 | `app.py` : 4–10 | Top-of-file comment still says `T2 — application funnel (next)` even though Tier 2 is shipped. Same header-drift bug that Tier-1 review caught in Finding #2. | 🟢 Minor | **Fix applied** |
| 2 | `tests/test_app_page.py` : 803 | `test_empty_state_info_renders_inside_left_column` hardcodes the empty-state copy as a local `expected = "Application funnel will appear once you've added positions."`, duplicating the `TestT2BFunnelEmptyState.EMPTY_COPY` class constant. A future wording change (requires a new user decision per §T2-B) would update the T2-B constant but NOT the T2-C test — silent drift between tests. | 🟡 Moderate | **Fix applied** (reference the shared constant) |
| 3 | `tests/test_app_page.py` : `TestT2AFunnelBar._funnel_trace` | Seven of the eight T2-A tests go through `at.get("plotly_chart")[0]` — i.e. "the first plotly chart on the page is the funnel." That's true today; it stops being true the moment T4 or T5 adds another Plotly chart. Verified empirically: AppTest's `plotly_chart.key` attribute is **always `None`** (same pattern as `st.metric` — the user-supplied `key=` only round-trips through `proto.id` as a suffix, which is an implementation detail). | 🟡 Moderate | Kept by design (see Q3 below — migration path is "scope to left column" when T4 lands) |
| 4 | `app.py` : 170 | `st.plotly_chart(_funnel_fig, key="funnel_chart")` — no explicit `width` or figure `height`. Streamlit 1.56 default for `st.plotly_chart` is `use_container_width=True` when omitted (the **explicit** `use_container_width=True` is the deprecated form; the omitted-default path doesn't warn). Plotly figure height defaults to ~450px. The funnel may not align visually with T3's Readiness panel. | ℹ️ Observation | Deferred to Phase 7 / T3 visual tuning |
| 5 | `app.py` : 102 vs. 151 | Two different "empty" triggers live on the same dashboard. The T1-E hero fires on `tracked == 0 and applied == 0 and interview == 0`; the T2-B funnel info fires on `sum(count_by_status().values()) == 0`. On a terminal-only DB, the hero **does** render and the funnel **does** render (as a chart with non-zero terminal bars). | ℹ️ Observation | Intentional (see Q5 below — confirmed by user-locked decisions) |
| 6 | `tests/test_app_page.py` : `test_funnel_is_in_left_half` | We assert the funnel subheader is NOT in the right column, but we do **not** assert the right column is empty overall today. A misplaced widget ending up in `_right_col` wouldn't be caught. | 🟢 Minor | Kept (see Q6 — T3-B will populate the right half; a negative "empty right column" test would need immediate reversal) |
| 7 | `config.STATUS_COLORS` | The dict values (`'blue'`, `'orange'`, `'violet'`, `'green'`, `'gray'`, `'red'`) are chosen to satisfy `st.badge()` (Streamlit's limited color vocabulary; see the comment on line 33 of `config.py`). T2-A adds Plotly as a **second consumer** of the same dict. Plotly accepts a much larger color vocabulary. If anyone later swaps an entry for a hex like `'#ff7f0e'`, it silently breaks `st.badge()` — no test covers that dual-consumer assumption. | ℹ️ Observation | Deferred (Phase 7 polish flag) |
| 8 | `tests/test_app_page.py` : `test_subheader_renders_in_both_branches` | Creates a fresh `AppTest` twice rather than running one AppTest through an `add_position → rerun` cycle. Effectively two independent state snapshots, not a transition. Passes today, but the test name implies a transition it doesn't actually test. | 🟢 Minor | Kept (see Q8 — splitting or renaming is a cleanup pass, not a bug) |

---

## Fixes applied in this review

### Fix #1 — Update `app.py` header comment (Finding #1)

**Why:** Same failure mode Tier 1 review caught and Tier 2 re-introduced — the file's top comment block says T2 is "next" when it has just landed. Junior contributors reading the file head are misled about state. The comment block is also the easiest place for a reader to learn what `app.py` is for — stale comments actively mislead.

**Fix:** mark T2 ✅ with a short description of what it rendered; leave T3–T5 unchanged. Same shape as Tier-1 review's Fix #2 so the pattern is discoverable.

### Fix #2 — Reference `TestT2BFunnelEmptyState.EMPTY_COPY` in the T2-C test (Finding #2)

**Why:** The empty-state copy (`"Application funnel will appear once you've added positions."`) is user-locked under wording γ (2026-04-21). `TestT2BFunnelEmptyState.EMPTY_COPY` is the canonical pin. The T2-C test `test_empty_state_info_renders_inside_left_column` duplicated the literal as a local `expected = "..."` — a re-wording would update the T2-B constant but leave the T2-C test stuck with a stale string. The failure mode is insidious: **all tests still pass**, because each test asserts against its own copy of the string; the drift only surfaces when a reader notices one assertion says "once you've added" and another says (post-rename) "once you add".

**Fix:** replace the local `expected` literal in `test_empty_state_info_renders_inside_left_column` with `TestT2BFunnelEmptyState.EMPTY_COPY`. Zero runtime change; one source of truth.

---

## Junior-engineer Q&A

### Q1 — Why is `_funnel_trace` accessed via `at.get("plotly_chart")[0]`? What happens when T4 or T5 adds a second plotly chart?

**A.** Today, there is only one `st.plotly_chart` call on the entire dashboard (the funnel), so `charts[0]` is unambiguous. Tomorrow — if T4's Upcoming timeline or T5's Recommender alerts adds a second chart — `charts[0]` will silently target the *first* chart rendered in page order, which may or may not still be the funnel.

Three things we considered and rejected:

1. **Filter by `key`.** `st.plotly_chart(fig, key="funnel_chart")` *looks* like it should let us write `charts_with_key("funnel_chart")`. Verified empirically: `plotly_chart.key` in AppTest is **always `None`** — same pattern as `st.metric` (see Tier-1 review finding #1). The key only surfaces through `proto.id` as a suffix, which is an implementation detail we shouldn't grep.
2. **Scope to the left column.** `_left_col.get("plotly_chart")` would find only charts inside T2-C's left half. This works but **couples T2-A tests to T2-C's column layout** — every T2-A test would have to first call `TestT2CFunnelLayout._half_width_columns(at)[0]` to find the left column, then query it. That's a tight coupling between two classes that, today, have separate jobs.
3. **Add a figure-level identifier.** Set `fig.update_layout(meta={"panel": "funnel"})` and filter on `spec["layout"]["meta"]["panel"] == "funnel"`. Clean, but infra for one hypothetical edge case.

**Decision:** accept the brittleness today, migrate to Option 2 when the second chart lands. The `charts[0]` failure mode is loud (wrong data shape, wrong colors, wrong orientation, wrong y-axis reversal — at least one T2-A test trips immediately), not silent. Logged as a coverage gap for T6-A review.

---

### Q2 — Why was the stale `app.py` header comment shipped if the same bug was already fixed in Tier 1?

**A.** Honest answer: it wasn't on the T2 chore checklist. The T1 `chore:` rollup explicitly marked T1 ✅ in the file header (shipped in `ce1389e`). The T2 chore rollups updated `CLAUDE.md`, `TASKS.md`, `roadmap.md`, and `memory/project_state.md` — but not the file's self-describing comment.

The fix to prevent recurrence would be adding "update the file header comment" to a `chore:` checklist that lives in `PHASE_4_GUIDELINES.md`. Deferred as a process-tweak proposal to T6-A; this review's Fix #1 just cleans up the symptom.

---

### Q3 — `sum(_status_counts.values()) == 0` for T2-B, `tracked == 0 and applied == 0 and interview == 0` for T1-E. Aren't those the same check? Why write them differently?

**A.** They are intentionally **different**. The hero (T1-E) gates on *active-pipeline zeroness*: "no positions that are still in play" — a DB with only terminal-status rows ([CLOSED], [REJECTED], [DECLINED]) satisfies it. The funnel (T2-B Option C) gates on *DB zeroness*: "no positions at all, of any status." A terminal-only DB fires the hero but still renders the funnel (with non-zero terminal bars and zero active bars).

The divergence is user-locked — `test_terminal_only_db_still_shows_hero` (T1-E) and `test_terminal_only_db_still_renders_figure` (T2-B) pin both sides of the split. If either decision ever flips, exactly one test trips, making the change visible at review time. Flipping just one of the two to match the other is a one-test change; the decisions-log in `CLAUDE.md` documents both.

The naming of the underlying `_status_counts` variable is shared between the two branches — that's deliberate. One DB read, two views.

---

### Q4 — `at.info[i].value` returns the body of `st.info(...)`. Is that stable? `st.metric` doesn't expose its key, neither do plotly charts — why does `st.info` get a value?

**A.** Because `st.info` is a pure display element with a string body — the body **is** its identity. Streamlit's internal `Element.value` attribute is populated whenever the element's semantics are captured by a single primitive (string / number / bool). Stateful widgets (`st.text_input`, `st.checkbox`, etc.) round-trip through `session_state` and need a `key=` to disambiguate. Display-only elements don't.

This is the same reason `at.metric[i].label` is reliable (the label IS the element's identity) but `at.metric[i].key` is always `None` (the key doesn't matter for a display-only metric). We lean on this pattern throughout: identify display elements by their visible content; identify stateful widgets by `key=`.

One caveat to flag: `_empty_state_shown` uses **substring** match (`EMPTY_COPY in i.value`), while `test_empty_state_copy_is_spec_exact` uses **equality** match. That's intentional — the helper is a "did the empty state show up at all" probe that survives minor punctuation fiddling; the explicit exact-match test is the user-locked γ copy pin. Two jobs, two matchers.

---

### Q5 — The hero + funnel both react to emptiness. If the DB has zero rows, the user sees a hero card AND an info box at the same time. Isn't that a lot of "empty" noise?

**A.** Fair point. The current behaviour is:

- Fully-empty DB (T1-E trigger + T2-B trigger both fire): hero card (big, welcoming, CTA button) **AND** a small info box in the left column of the Funnel+Readiness row saying the funnel will appear once positions are added.
- Terminal-only DB (only T1-E fires): hero card **AND** the funnel chart renders with non-zero terminal bars.
- Active-pipeline DB (neither fires): plain dashboard — no hero, full funnel.

The user visually verified the fully-empty-DB rendering between T2-B and T2-C (see project_state.md 2026-04-21). The two messages are deliberately different in tone and size — the hero is the primary call to action ("add your first position"), the info box is a grid-stability glue ("this specific panel will appear…"). Removing the T2-B info and letting the empty-state branch render nothing inside `_left_col` would break the column alignment once T3-B lands its content in `_right_col` — the right column would have content, the left column would be a blank slot. That's the sort of skewed layout that looks like a bug.

If Phase 7 polish decides the info box is visually redundant on a fully-empty DB, the branch becomes `if sum(...) == 0 and not hero_is_rendered: st.info(...)` — one conditional extension. No structural refactor needed.

---

### Q6 — Why don't we pin that the *right half* column is empty today?

**A.** Because T3-B is the next tier up, and it will populate the right half with Materials Readiness. A test `assert _right_col is empty today` would go green now, red the moment T3-B lands, and we'd be deleting or inverting it two sessions from now.

The question is: does the right column being empty reveal anything we don't already test? We already pin that:

- The funnel subheader is in the LEFT column (`test_funnel_is_in_left_half` — left has subheader, right does NOT).
- The funnel figure is inside the LEFT column (`test_funnel_figure_renders_inside_left_column`).
- The empty-state info is inside the LEFT column (`test_empty_state_info_renders_inside_left_column`).

The failure mode we'd catch with an additional "right is empty" test is: "a widget accidentally rendered in the right column that belongs in the left." The three existing tests catch this for the three things that belong in the left column. A new widget rendering somewhere it doesn't belong would either:

1. trip `test_funnel_lives_in_a_half_width_column` (if it was a subheader named "Application Funnel"), or
2. be caught at T3-B review (when the right column becomes the reader's focus).

Adding a negative test is more ceremony than insight.

---

### Q7 — `config.STATUS_COLORS` uses color names that are valid for `st.badge()`. Plotly accepts a much larger vocabulary. Is there a risk of drift?

**A.** Yes, and it's worth naming explicitly.

`config.py` line 33 documents the `st.badge()` constraint: `accepted literals: 'red','orange','yellow','blue','green','violet','gray','grey','primary'`. Phase 4 T2-A added Plotly as a second consumer of the same dict. Plotly will happily accept `'#ff7f0e'`, `'rgb(255,127,14)'`, or any other CSS color — `st.badge()` will not.

If someone in Phase 7 decides "let's use brand-specific hex colors in the funnel," they'd edit `STATUS_COLORS`, the funnel updates cleanly, and the next `st.badge()` call on the Opportunities page silently fails the Streamlit vocabulary check (typically: falls back to default color or raises at render).

**Mitigation options (none required today):**

1. Add a `config.py`-level assertion: `assert all(v in _STREAMLIT_BADGE_COLORS for v in STATUS_COLORS.values())`. Pros: enforced at import time. Cons: locks us into Streamlit's vocabulary forever.
2. Split the dict — `STATUS_BADGE_COLORS` (for `st.badge`) and `STATUS_FUNNEL_COLORS` (for Plotly). Pros: flexible. Cons: config.py gains a second dict that must stay in sync.
3. Document the dual-purpose constraint in the `STATUS_COLORS` comment. Pros: free. Cons: relies on reader noticing.

Phase 4 is the wrong tier to make this decision — the question only exists because the second consumer landed in Phase 4. Deferred to Phase 7 polish with the note "if we ever want non-Streamlit-vocab colors in the funnel, split the dict."

---

### Q8 — `test_subheader_renders_in_both_branches` runs `_run_page()` twice rather than `add_position → rerun`. Why?

**A.** `_run_page()` creates a fresh `AppTest` — the helper runs `AppTest.from_file(PAGE, default_timeout=10).run()`. So the test is really two independent state-checks, not a transition:

1. Empty DB state → subheader renders.
2. Seeded DB state → subheader renders.

The name `_renders_in_both_branches` is accurate: it asserts the subheader is present in both code branches of the `if sum(...) == 0: ... else: ...` block in `app.py`. It does not assert anything about the transition between them (no widget state survives a fresh `AppTest`, so "transition" has no AppTest-level meaning anyway).

If we cared about the transition — e.g., to verify that widget state survives the empty→seeded flip — we'd need to call `at.run()` twice on the same AppTest instance, with a `database.add_position` between them. AppTest does support that pattern (it's used in `test_refresh_button_rerenders_with_updated_counts` for the KPI wiring). For subheader presence alone, the two-snapshot approach is sufficient and easier to read.

**Cleanup candidate (not a fix):** rename to `test_subheader_present_in_empty_and_seeded_states` to match what the body actually does. Deferred to T6-A sweep.

---

## Coverage gaps for the T6-A pre-merge sweep

Carrying forward from the Tier-1 review (each of these is a deliberate deferral, not an oversight):

1. **Funnel-chart scoping when a second Plotly chart lands** (Finding #3 / Q1). Migration path: T2-A tests scope to `_left_col.get("plotly_chart")` when T4 or T5 adds a chart.
2. **Figure height / width alignment with T3's Readiness panel** (Finding #4). Deferred to Phase 7 visual tuning.
3. **`STATUS_COLORS` dual-consumer assumption** (Finding #7 / Q7). Defer to Phase 7 polish.
4. **`test_subheader_renders_in_both_branches` naming** (Finding #8 / Q8). Cleanup pass.

New-in-Tier-2:

5. **No test pins the `funnel_chart` key itself** — `key="funnel_chart"` exists in `app.py` line 170 but no test verifies it. Since the key only surfaces through `proto.id`, pinning it would require grepping the string out of an implementation-detail field; skip until Streamlit's AppTest exposes keys on display elements.

Still-open from Tier-1 (unchanged by Tier 2):

6. **Tied earliest dates** in `_next_interview_display`.
7. **NULL/empty-institute date-only-label fallback** in `_next_interview_display`.
8. **Hero-copy exact-match decision after Phase 7.**

---

## Acceptance gate for PR merge

- [x] `pytest tests/ -q` — 263 green
- [x] `pytest -W error::DeprecationWarning tests/ -q` — 263 green (0 deprecation warnings)
- [x] `git diff main..HEAD -- database.py config.py exports.py pages/1_Opportunities.py` — empty (no scope creep)
- [x] `grep -nE "\[OPEN\]|\[APPLIED\]|\[INTERVIEW\]" app.py` — zero hits (code and comments)
- [x] `grep -nE "^\s*[0-9]+\s*#\s*(days|urgent|alert)" app.py` — zero hits
- [x] Every locked decision (Option C, wording γ, U2) has at least one test pin
- [x] User-visible empty-state behaviour verified by user between T2-B and T2-C
- [x] Review findings #1 and #2 applied in a single `review(phase-4-t2):` commit
- [x] Remaining findings documented here with clear accept/defer rationale

---

_Initial draft: 2026-04-22, immediately before PR open on `feature/phase-4-Tier2-ApplicationFunnel`._
