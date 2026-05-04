**Branch:** `feature/phase-7-tier2-PositionSearch`
**Scope:** Phase 7 T2 — free-text "Search positions" `text_input` on the Opportunities filter row, substring match against `position_name` (case-insensitive, regex=False, NaN-safe), AND-combined with the existing status / priority / field filters
**Stats:** 7 new tests across 2 classes (836 → 843 passed, 1 xfailed unchanged); +175 / −1 lines across 2 files; ruff clean; status-literal grep 0 lines; standing isolation gate empty; CI-mirror local check passes (843 + 1 xfailed with `postdoc.db` moved aside); **`Tests + Lint (3.14)` CI conclusion: SUCCESS** (`mergeStateStatus: BLOCKED`, `mergeable: MERGEABLE`)
**Verdict:** Approve

---

## Executive Summary

T2 adds a search box to the Opportunities filter row. Implementation
mirrors the existing field-filter idiom one row down:
`df["position_name"].str.contains(query, regex=False, case=False,
na=False)` row mask, AND-combined with the status / priority / field
filters via successive `df_filtered = df_filtered[mask]` narrowings.
Filter row layout shifts from `st.columns([2, 2, 3])` →
`st.columns([3, 2, 2, 3])` — search prepended at left with a wider
weight (variable-length user input vs fixed selectbox values).

Search scope: **`position_name` only**. Implementer flagged this as
the design call — institute and field deliberately excluded. Two
reasons cohabit: field already has its own filter widget, and a
narrower search scope keeps the user's mental model predictable
("what I type matches what's printed in the Position column").
Defensible — see Q1 below.

The 7 new tests split across two classes:
`TestPositionSearchStructure` (2) pins widget existence + label
verbatim; `TestPositionSearchBehaviour` (5) exercises the substring
match + empty-search-no-narrowing + zero-match-empty-state +
regex-special-chars-as-literal + AND-combined-with-status. Every
behaviour test that produces N=1 results carries a row-identity
assertion (not just count) — guards against a swapped predicate
that would coincidentally produce N=1 with the wrong row.

All six pre-merge gates green. CI conclusion SUCCESS verified per
the `c284c20` procedure.

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `tests/test_opportunities_page.py::TestPositionSearchBehaviour::test_search_combines_with_status_filter` | Three-row seeding wired so each pairwise predicate (search-only, status-only) admits two rows but only one row passes BOTH. Pinpoints AND-vs-OR semantics + correct predicate composition with a single row-identity assertion. Same precedent as the existing AND-combined filter tests in `TestFilterBarBehaviour`. | ℹ️ | Observation |

*No 🔴 / 🟠 / 🟡 / 🟢 findings.*

*Two kept-by-design choices (search scope `position_name` only; layout weights `[3, 2, 2, 3]` with the search column widest) live in the Q&A section per `GUIDELINES §10` ("`Kept by design` observations belong in the Q&A section, not in the Findings table").*

---

## Junior-Engineer Q&A

**Q1. Why is the search scope `position_name` only — not also institute / field?**

A. Three reasons cohabit. (1) Field is already covered by the dedicated `filter_field` selectbox one column over. Adding field as a search target would mean one query type matches against two filter mechanisms (selectbox + free-text), which is a footgun: the user types `"Statistics"` in search, the field selectbox is on `"Computer Science"`, the AND-combined result is empty, and the user can't tell whether the search has a typo or the field selectbox is mismatched. Single-purpose filter widgets keep the mental model clean. (2) Institute is implicit in `position_name` for most entries (`"MIT CSAIL Postdoc"` — searching `"MIT"` already hits via the position name). The cases where it doesn't (`"Postdoc in Bayesian Inference"` at Princeton) are rare enough that adding institute to the search scope adds more confusion (user types `"Princeton"` and the row surfaces — but for which institute string actually matched?) than it solves. (3) The implementer's framing — "what you type matches what's printed in the Position column" — is the strongest argument for narrow scope. Once Phase 3 T3-rev split Position + Institute into separate columns, the search bar's predicate can reasonably target just the leftmost column. If a user wants institute-based filtering, the natural shape is a future institute selectbox, not search-scope creep.

**Q2. The filter row reweights from `st.columns([2, 2, 3])` to `st.columns([3, 2, 2, 3])`. Why give search the widest non-field weight?**

A. The selectbox columns hold fixed-vocabulary values (`Active` / `All` / status names; `High` / `Medium` / `Low`); their column width only needs to fit the longest enum value. The text_input column holds **user typing** — variable-length queries up to whatever the longest position name is. A weight of `2` (matching status / priority) would clip placeholder text + truncate the user's query mid-word, which is the dominant friction point on narrow viewports. Weight `3` matches the existing field column's allotment because `field` is also user-editable free text. The leftmost placement mirrors common UX (Google search, GitHub repo search, etc.) — primary navigation tool sits left and prominent. The choice could be revisited in Phase 7 T5's responsive-layout sweep; today it reads cleanly at the implementer's spot-check viewport widths.

**Q3. Every N=1 behaviour test includes a row-identity assertion (e.g. `assert names == ["Postdoc Stanford"]`). Why not just `assert len(rows) == 1`?**

A. A swapped predicate (e.g. `not contains` instead of `contains`, or comparison against `field` instead of `position_name`) can coincidentally produce N=1 results with the WRONG row in this two-row seeding. `assert len(rows) == 1` would pass; `assert names == ["Postdoc Stanford"]` would fail with an explicit "got `["Faculty MIT"]` instead". The diagnostic is significantly better when the assertion fires. Same intuition as the Phase 6 T2 `test_interviews_summary_uses_max_scheduled_date_as_last` test (intentionally non-monotonic seeding to defeat `iloc[-1]` regressions); same intuition as the `test_search_special_chars_no_regex_interpretation` test pinning the literal-`"++"`-in-`"C++ Postdoc"` row identity (a regex-interpretation bug would treat `"++"` as a quantifier and either crash via `re.error` or match nothing — both produce N=0, which the count-only assertion would also catch, but the row-identity assertion stays robust against future seeding additions).

**Q4. The search filter uses `regex=False`. The `test_search_special_chars_no_regex_interpretation` test seeds `"C++ Postdoc"` and queries `"++"`. What concrete bug does this catch?**

A. Two regression classes. (1) **Forgotten `regex=False`**: `pandas.Series.str.contains` defaults to `regex=True` if not specified. With regex semantics, `"++"` is a quantifier that's invalid at the start of a pattern → `re.error: nothing to repeat at position 0`. The page would either crash on render or surface an exception in the AppTest harness. The test asserts `at.exception` is empty — a regression that drops `regex=False` would surface as the exception path firing. (2) **Subtler regex-interpretation bug**: a query like `"."` would match every position name as the regex wildcard if `regex=True` is forgotten — but `"."` is also a real character that the user might type (uncommon in position names but plausible for "Postdoc 1.5 yr"). The literal-substring contract removes the entire class of "user typed something that has special meaning in regex" surprises. The test pins this at the boundary case (`"++"` is invalid regex AND a real character substring) so any regression surfaces with a clear failure mode rather than silent wrong-results.

**Q5. The `test_search_no_match_renders_empty_state` test asserts the empty-state info message uses the substring `"No positions match"`. Doesn't pinning a substring make the test fragile to copy edits?**

A. Substring-match is the right granularity here because (a) the existing empty-state copy is shared across status / priority / field / search filters (it's the page's single empty-state branch), and (b) any future copy edit that changes the message is itself a contract change that should fail multiple tests, not just this one. The substring `"No positions match"` is short enough that a deliberate copy refresh ("No positions found") would update both the page string and this test's expected substring in the same commit; an accidental wording drift in the page (without test update) would surface as the existing empty-state tests AND this new search test all failing — easier to triage than a single full-string assertion. The page's empty-state copy isn't pinned anywhere centrally (no `EMPTY_STATE_TEXT` constant); centralizing it in `pages/1_Opportunities.py` is a Phase 7 polish candidate that would tighten this test along with the field/status/priority empty-state tests.

**Q6. CI procedure (c284c20) followed end-to-end again — `gh pr checks 38 --watch` blocked from IN_PROGRESS to SUCCESS, then admin-bypass merge. Any wrinkles compared to PR #37's first clean run?**

A. Identical shape. PR #38 hit `IN_PROGRESS` at PR-creation, the orchestrator kicked off `gh pr checks 38 --watch` in background while running the local six-gate set in parallel — both completed cleanly (~3 minutes wall-clock for CI, ~2 minutes for local gates). Post-completion verification: `gh pr view 38 --json statusCheckRollup --jq '...'` returned `Tests + Lint (3.14): SUCCESS`. The `mergeStateStatus: BLOCKED` shape is back (PR #37 also hit BLOCKED; PRs #35/#36 were the CLEAN outliers); the procedure handles both transparently because the bypass step doesn't depend on `mergeStateStatus`. The pattern is now load-bearing for the orchestrator's review-to-merge cycle — third clean end-to-end run-through.

---

## Carry-overs

- **Phase 7 polish candidate** — empty-state copy is currently a literal `"No positions match the current filters."` in `pages/1_Opportunities.py` rather than a centralized constant. Centralizing would tighten the search test (Q5) along with the existing filter tests. Track for the Phase 7 close-out / cleanup tier.
- **No new carry-overs introduced.**

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-7-tier1` precedent. The six pre-merge gates
were re-run on the PR head locally (`pr-38` / `43f24c7`) at review
time: ruff clean · `pytest tests/ -q` 843 passed + 1 xfailed ·
`pytest -W error::DeprecationWarning tests/ -q` 843 passed + 1
xfailed · status-literal grep 0 lines · standing isolation gate
`git status --porcelain exports/` empty · CI-mirror local check
843 + 1 xfailed with `postdoc.db` moved aside · `Tests + Lint
(3.14)` CI **conclusion: SUCCESS** verified via `gh pr checks 38
--watch` + `gh pr view 38 --json statusCheckRollup --jq '...'` per
the standing `c284c20` procedure._
