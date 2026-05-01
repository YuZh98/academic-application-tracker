# Phase 4 — Tier 3 Code Review

**Branch:** `feature/phase-4-tier3-MaterialReadiness` (3 commits ahead of `main`)
**Scope:** T3 — Materials Readiness panel inside the right half-width column of the T2-C `st.columns(2)` pair. Subheader + `st.info` empty-state + two `st.progress` bars (Ready / Missing) + `"→ Opportunities page"` CTA → `st.switch_page("pages/1_Opportunities.py")`.
**Stats:** `app.py` 170 → 201 lines (+31/-1, the `-1` is the header-comment flip `T3 → ✅ done`); `tests/test_app_page.py` 807 → 1086 lines (+273 including a 2-line trailing whitespace delta), +8 tests under one new class `TestT3MaterialsReadiness`. **263 → 271 tests passing, zero deprecation warnings.**
**Verdict:** Approve, merge.
**Cadence:** `test(phase-4-t3)` red → `feat(phase-4-t3)` green → `chore(phase-4-t3)` tracker rollup. Perfect TDD isolation per commit (`test:` → only `tests/test_app_page.py`; `feat:` → only `app.py`; `chore:` → only tracker markdowns).
**Reviewer attitude:** Skeptical. Verify every Streamlit API claim. Trust no "looks fine" statements; grep every assertion.

---

## Executive summary

Tier 3 delivers the Materials Readiness panel — the dashboard's right-column counterpart to the Application Funnel. The implementation is the shortest Phase-4 feature shipped so far (one `with _right_col:` block, 31 lines) and yet has the best test-to-code ratio of any Phase-4 tier to date (8 tests → 31 lines, roughly 4 lines of test per line of production code).

The eight tests pin every piece of the locked design contract: subheader stability across empty↔seeded transitions (D3), left-column non-leak (U2 layout invariant), empty-state info copy exact to the byte (D3 + wording), two bars with 1/3 and 2/3 values (D1 + D5 guard math), label strings verbatim, terminal-only DB → empty-state (semantic correctness of `compute_materials_readiness`'s active-only scope), CTA button existence + switch-page target at source level (D2, T1-E precedent for AppTest's single-file routing limitation).

The review surfaces **zero bugs**, **zero pre-merge fixes applied**, and **four intentional-but-worth-naming observations** for the tier-3 design record. Verdict: **approve, merge.**

---

## Findings

| # | File · Line | Issue | Severity | Status |
|---|-------------|-------|----------|--------|
| 1 | `app.py` : 196 | `_total = max(_ready + _pending, 1)` is provably dead code inside the `else` branch: we only enter `else` when `_ready + _pending > 0`, so the `max(..., 1)` never triggers. The worker's inline comment admits this and argues "keeps the contract close to the code for a future reader." | ℹ️ Observation | Kept by design (see Q1) |
| 2 | `app.py` : 131 | A pre-existing T2-C comment reads `…no second `st.columns(2)` call.` — which trips the Tier-3 conductor brief's pre-merge grep `st\.columns\(2\)` by returning two matches instead of the expected one (the live call at line 132 plus the comment). The brief's grep was imprecise; the invariant itself (one live call) holds. | ℹ️ Observation | Kept; brief-grep lesson (see Q2) |
| 3 | `tests/test_app_page.py` : `test_cta_button_routes_to_opportunities_page` | The test mixes black-box (AppTest button props) with white-box (grep of `app.py` source for the `st.switch_page(...)` literal). Works, mirrors the T1-E precedent, but the string match is formatting-fragile — a reformat to `st.switch_page(\n    "pages/1_Opportunities.py"\n)` would break it. | 🟢 Minor | Kept — T1-E precedent (see Q3) |
| 4 | `tests/test_app_page.py` : `test_populated_db_renders_two_progress_bars` | Tolerance `< 0.02` on `proto.value / 100.0` is comfortable (1/3 ↔ stored int 33 → 0.33, delta 0.003), but the test leans on an implementation detail: AppTest exposes `st.progress`'s float input as an int 0-100 through `proto.value`. A hypothetical Streamlit change to expose the raw float would silently un-scale the comparison. | 🟢 Minor | Kept (see Q4) |

---

## Fixes applied in this review

**None.** The worker shipped work that does not require pre-merge patching. This is the first Phase-4 tier with zero fix commits in the review pass (Tier 1 had 2 fixes applied; Tier 2 had 2 fixes applied).

---

## Junior-engineer Q&A

### Q1 — Why keep `max(_ready + _pending, 1)` if it's dead code in the `else` branch?

**A.** Three readings, weighed:

1. **Strict correctness.** Inside `else`, `_ready + _pending >= 1` by negation of the `if`. So `max(..., 1)` is `_ready + _pending` always. Pure overhead.

2. **Defense-in-depth.** If a later refactor moves the division out of the `else`, or if a caller changes the shape of `compute_materials_readiness()` to ever return a negative count, the guard catches it. The cost is one function call; the benefit is that the invariant (denominator is never zero) lives next to the division.

3. **Readability / contract locality.** A reader landing on line 197 (`_ready / _total`) and scrolling up finds a guard that tells them: "the denominator is guaranteed non-zero, by construction." Without the guard, they have to reason about the `if` branch to prove the division is safe. For a dashboard that may be read by a tired human at 9 PM trying to decide whether to flip a `done_*` flag, local readability wins.

The locked decision D5 in the conductor brief called for the guard explicitly. This review does not revisit it. If a later reviewer (Phase 7 polish?) wants to delete the guard, they'll leave a clearer git log for doing so after this tier than before: the comment names the trade-off.

### Q2 — Why did the pre-merge grep for `st\.columns\(2\)` return two matches and not one?

**A.** Because the pre-merge grep in the conductor brief was naive by design — it matched the **literal text** `st.columns(2)` anywhere in `app.py`, not just live call sites. There are two occurrences:

- Line 131 — a comment added by T2-C explaining the layout invariant: *"the dashboard stays a single 2-column row (no second `st.columns(2)` call)."* The comment literally contains the forbidden phrase **as part of explaining why the phrase must not appear as a call**.
- Line 132 — the actual live `st.columns(2)` call that creates `_left_col, _right_col`.

So the grep is a lower-bound invariant check, not an upper-bound one. The invariant ("only one live `st.columns(2)` call") holds; the grep over-matches when the file also documents that invariant in prose. This pattern — the guard-in-a-comment triggering the guard's own grep — is worth naming because we'll hit it again. Two acceptable responses next time:

- **A (simpler):** accept a comment-vs-call split in the review, as here.
- **B (more rigorous):** tighten the grep to exclude comment lines — `grep -nE "^[^#]*st\.columns\(2\)"` — which allow-lists hash-prefixed lines. Worth adopting in the Phase 4 T6 pre-merge checklist.

### Q3 — The CTA test mixes AppTest button assertions with a `grep` of `app.py` source. Is that an anti-pattern?

**A.** In principle, yes — mixing black-box (render state) and white-box (source text) tests makes the test brittle to refactors that preserve behaviour. In practice, here, we have no choice:

AppTest in single-file mode cannot actually navigate to sibling pages. Clicking the button in the test would raise — either because `st.switch_page` isn't resolvable, or because the target page isn't mounted in the single-file test session. So we cannot black-box-test the route target.

The T1-E empty-DB hero landed the exact same pattern and justified it in the Tier-1 review: "pin the destination at the source level because AppTest can't navigate." T3 follows that precedent to stay consistent. Two things would break the current test:

1. **Semantic breakage:** someone changes the target page and forgets to update the test → test fails, which is what we want.
2. **Formatting breakage:** someone reformats the call over multiple lines → test fails spuriously, which is what we *don't* want.

Mitigation for (2), not adopted here: replace the substring match with a regex that accepts whitespace — `re.search(r'st\.switch_page\(\s*"pages/1_Opportunities\.py"\s*\)', src)`. The migration cost is small; we haven't done it yet in T1-E either. If T4 or T5 adds a third source-level route assertion, promote the regex into a shared test helper `_source_has_switch_page(target)`.

### Q4 — Why scale `proto.value` by `/ 100.0`? What guarantees that's correct?

**A.** Streamlit's `st.progress` takes a float in `[0.0, 1.0]` as its `value` argument. Internally (verified against Streamlit 1.56 source), that float is serialized to a protobuf `int` field in the range `[0, 100]` — same wire shape `st.metric` uses for numeric values. AppTest reads back `proto.value`, so the raw number coming off the wire is `33` for `1/3`, `66` for `2/3`, etc.

We divide by `100.0` to return the assertion-space to the same `[0.0, 1.0]` domain the production code operates in. Two things could go wrong:

1. **Streamlit changes the wire format.** If a future version serializes `value` as a raw float, `proto.value / 100` would become nonsense. The test would fail loudly (33.3/100 = 0.333 → assertion passes; 0.333/100 = 0.00333 → assertion fails). So the test catches this drift rather than silently accepting it.
2. **Streamlit changes the clamping behaviour.** If the wire format switches from [0, 100] to [0, 1000] for precision reasons, our tolerance `< 0.02` becomes either too tight or too loose. Again, the test fails loudly.

Both failure modes are visible, not silent. That's the important property. The alternative — bypassing `proto.value` and probing `at.get("progress")[i].value` directly — doesn't work because AppTest's high-level `.value` attribute on progress elements is `None` (progress bars are stateless display elements, same pattern as `st.metric`; only stateful widgets round-trip `.value`).

### Q5 — Why does `test_terminal_only_db_shows_empty_state` live in T3's file rather than `test_database.py`?

**A.** Because it's testing an **integration contract**, not the database query itself. The underlying behaviour — `compute_materials_readiness()` returning `{ready: 0, pending: 0}` when all positions are in terminal statuses — is already pinned in `tests/test_database.py` (Phase 2 coverage). The T3 test exercises a different claim: *given that query behaviour, the dashboard's right-column panel chooses to render the empty state.*

That's a composition test: it verifies the dashboard's `if _ready + _pending == 0` branch selects the correct visual for the underlying semantic. Moving this test to `test_database.py` would lose the UI-behaviour pin; deleting it would allow a future regression (e.g. someone swapping the condition to `if _ready == 0` — "no ready positions" — would break this test but not any database test).

This is the Phase-4 pattern more generally: `test_database.py` covers data shape; `test_app_page.py` covers "data shape X → UI shape Y." The same test literal can appear in both files with different jobs.

### Q6 — The deviation-log entry is now **inline** inside `PHASE_4_GUIDELINES.md`. Isn't that polluting the spec?

**A.** Yes, and deliberately. The T1-B metric-key deviation entry set the precedent: keep deviations **inline next to the sub-task they're about** so a session resuming cold can see both the original plan and what actually shipped on the same screen. The alternative — a separate `DEVIATIONS.md` — fragments the context and makes it harder to answer "what is the actual shape of T3?" from a single file.

The trade-off:

- **Inline (current):** spec + reality in one place; spec grows over time; readable.
- **Separate file:** spec stays pristine; reality lives elsewhere; two-document problem.

For a small personal project with one writer, inline wins. If this were a multi-contributor project, a separate DEVIATIONS log would be better because the spec-vs-reality tension scales with contributor count. Revisit at Phase 5.

### Q7 — Is 8 tests for 31 lines of production code over-engineering?

**A.** No, for two reasons specific to this code:

1. **High decision density.** The 31 lines encode five locked design decisions (D1–D5), two exact strings (empty-state copy, CTA label), two exact key values (CTA button key, switch-page target), and two invariants (subheader in both branches, progress bar order). Each test pins exactly one of those — there's no coverage-per-coverage's-sake here; every test defends one specific user decision.
2. **Layout coupling to T2-C.** Because T3 reuses `_right_col` from T2-C rather than creating its own column, two of the eight tests are specifically about **not** breaking the T2-C invariant ("funnel on left, readiness on right, nothing leaks"). Those tests are insurance against T4/T5 accidentally adding content to the wrong column — a real risk given that T4's timeline is designed to span the full width below the Funnel+Readiness row.

The test-to-code ratio looks high because the code is **contract-dense**, not because the tests are redundant. Grep-level evidence: every assertion in the class references exactly one class constant (`SUBHEADER`, `EMPTY_COPY`, `CTA_LABEL`, `CTA_KEY`, `TARGET_PAGE`) — so a re-wording that "shouldn't" break behaviour will break the tests, which is the intended signal.

---

## Observations for Tier 4+ design

These are intentionally deferred but worth naming so T4's design inherits the current state cleanly:

1. **The `st\.columns\(2\)` grep will keep over-matching until it's tightened.** Two acceptable paths: (a) accept the miscount and eyeball the two hits, as here; (b) tighten to `grep -nE "^[^#]*st\.columns\(2\)"` and add to the T6 pre-merge checklist. Recommend (b) before T6.

2. **The layout grows by accretion, not replacement.** T1's `st.columns(4)` → T2's `st.columns(2)` → T4's (likely) full-width row. There's currently no test that pins "the dashboard's top-level vertical order" — e.g. "empty-DB hero → KPI row → Funnel+Readiness row → T4 timeline → T5 alerts." A single structural test in `TestT6PreMergeShape` would be a cheap insurance policy. Recommend adding at T4 entry, not earlier.

3. **`st.progress` has a `width` parameter on Streamlit 1.56.** Worker's verification left the default `width="stretch"` implicit. For T4's timeline (which will use tables, not progress bars), this is a non-issue; for Phase 7 visual tuning, it becomes one — the ready/missing bars might look proportionally different from the funnel bars because Plotly and `st.progress` take independent width defaults.

4. **The readiness panel is purely read-only.** Clicking "→ Opportunities page" is a navigation, not a write. Consistent with the dashboard's read-only contract (no `database.update_*` calls anywhere in `app.py`). T4/T5 should preserve this — any "mark this recommender as followed up" affordance belongs on the Applications/Recommenders page, not on the home dashboard.

---

## Verdict

**Approve, merge.**

- All pre-merge checks pass independently re-verified (271 green, 0 warnings, grep rules clean modulo the one commented-out T2-C reference, scope fence intact, TDD cadence textbook).
- Zero bugs; zero fixes applied; the four observations are all either intentional by design or forward-looking recommendations for T4+.
- The work is demonstrably more polished than Tier 1 or Tier 2 at the same pre-merge stage — a result of the conductor-pattern (this session) writing the decisions out explicitly before the worker session started, so there were no mid-implementation ambiguities to resolve.

**Merge via PR web UI** (gh still unauthenticated) → **delete branch on origin** → **update `memory/project_state.md`** to reflect Tier 3 shipped.

---

_Review by conductor session, 2026-04-22._
