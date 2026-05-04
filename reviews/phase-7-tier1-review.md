**Branch:** `feature/phase-7-tier1-UrgencyColors`
**Scope:** Phase 7 T1 — `pages/1_Opportunities.py::_deadline_urgency` returns inline glyphs (`🔴` / `🟡` / `''` / `—`) instead of literal-string flags (`'urgent'` / `'alert'` / `''`); display column unchanged. 7 existing urgency tests in `TestPositionsTable` updated in-place + 2 new tests added (boundary + invariant pin).
**Stats:** Net +9 tests / -7 tests = +2 net (834 → 836 passed, 1 xfailed unchanged); +130 / −50 lines across 2 files; ruff clean; status-literal grep 0 lines; standing isolation gate empty; CI-mirror local check passes (836 + 1 xfailed with `postdoc.db` moved aside); **`Tests + Lint (3.14)` CI conclusion: SUCCESS** (`mergeStateStatus: BLOCKED`, `mergeable: MERGEABLE` — back to BLOCKED state from the CLEAN shift on PRs #35/#36, no apparent rule-set change)
**Verdict:** Approve

---

## Executive Summary

T1 opens Phase 7 with a tight cosmetic-but-load-bearing change: the
deadline_urgency column on the Opportunities-page positions table
shifts from literal-string flags (`'urgent'` / `'alert'` / `''`) to
inline urgency glyphs (`🔴` / `🟡` / `''` / `—`). The column was
already in the display projection from Phase 3 T3; only the value
form changes. Same banding the dashboard's Upcoming panel uses —
gated by the same `config.DEADLINE_URGENT_DAYS` /
`DEADLINE_ALERT_DAYS` thresholds, so the two surfaces stay
synchronised through the shared config rather than through a shared
helper (DESIGN §2 layer rule keeps `database.py::_urgency_glyph`
unimportable into a page).

The new contract introduces a fourth state — em-dash for NULL /
unparseable — that the old contract collapsed into the empty-string
"no urgency" branch. This distinguishes "no deadline at all" (the
user hasn't filled in a deadline) from "deadline far enough away
that no urgency is signaled" (the user has time). Cohesion gain at
the page level; pinned by `test_null_deadline_renders_em_dash`.

Implementer's two design calls in the PR description — both
defensible:

1. **Tests updated in-place rather than parallel class.** Adding a
   `TestPositionsTableUrgencyGlyph` class would have left the
   existing `TestPositionsTable` urgency tests asserting against
   the *old* literal strings, contradicting the new tests' glyphs
   for the same column. In-place flip preserves the contract
   intent + the existing class structure; the rename pattern
   (`_flagged_as_urgent` → `_renders_red_glyph`) is honest about
   what the new contract actually pins.

2. **Duplicated banding logic instead of importing
   `database.py::_urgency_glyph`.** DESIGN §2 forbids pages from
   importing `database.py` private helpers (the `_` prefix flags
   it private even though Python doesn't enforce). The dashboard
   helper takes `days_away: int` while the page needs to start
   from a date string, so the two helpers also have different
   signatures. Duplication is the cleaner answer than plumbing a
   string-to-int adapter or breaking the layer rule. Both helpers
   read from the same `config` thresholds — drift is
   structurally-impossible because the constants are the
   single-source-of-truth.

NaN handling is the implementation tightening: the new
`_deadline_urgency` adds an explicit `isinstance(date_str, float)
and math.isnan(date_str)` branch ahead of the existing `not
date_str` + `try/except (ValueError, TypeError)` guards. Pandas
DataFrames surface NULL TEXT cells as `float('nan')` once any other
row carries a value (gotcha #1); the explicit check funnels every
NULL-shaped input — None, NaN, empty string — and every malformed
date string into the em-dash branch consistently. Type hint widened
from `str | None` to `Any` because pandas' `.apply()` on object
columns can hand the helper anything.

All six pre-merge gates green. CI conclusion SUCCESS verified
before admin-bypass per the standing `c284c20` procedure.

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `pages/1_Opportunities.py` `_deadline_urgency` helper duplication | Duplicates banding logic from `database.py::_urgency_glyph`. Implementer's commit body cites the DESIGN §2 layer rule (pages cannot import `database.py` privates) + the signature mismatch (page helper takes a date string, dashboard helper takes `days_away: int`) as the rationale. Both read from the same config thresholds, so drift is structurally-impossible — a future config change updates both surfaces in lockstep. The third-state em-dash branch is page-specific (the dashboard's `_urgency_glyph` doesn't have a "no deadline at all" case because Upcoming is filtered to known-future deadlines). | ℹ️ | Kept-by-design. Cite-able if Phase 7 / v1.0-rc surfaces a third consumer of the urgency banding — at that point a shared helper in `config.py` (which both layers can import) becomes worth extracting. |
| 2 | `pages/1_Opportunities.py` `EM_DASH = "—"` constant | New module-level constant. Mirror of the same literal in `app.py`, `pages/2_Applications.py`, `exports.py`. Implementer accepts the duplication per the same DESIGN §2 layer-rule rationale that drove the urgency-helper duplication. Drift is caught at the test level — every page test asserts against the same U+2014 glyph. | ℹ️ | Kept-by-design. Same Phase 7 / v1.0-rc carry-over as Finding #1 — a shared `config.EM_DASH` would consolidate four call sites if the project ever wants the lift. |
| 3 | `tests/test_opportunities_page.py::TestPositionsTable` in-place updates | 7 existing tests renamed + assertions flipped from literal strings to glyphs; 2 new tests added inside the same class. Implementer flagged this as a design call (PR description). The alternative — a parallel `TestPositionsTableUrgencyGlyph` class — would have left the existing 7 tests asserting against the *old* literal strings, contradicting the new ones for the same column on the same page. In-place flip is the correct framing: there's one column, one contract, one test class for it. | ℹ️ | Kept-by-design. |
| 4 | New contract introduces em-dash as a fourth state | Phase 3 T3's original contract collapsed "no deadline at all" and "deadline far enough away" both into `''`. Phase 7 T1 distinguishes the two (em-dash vs empty cell). Genuinely a contract widening — but the user-facing improvement is real (a position with no deadline can now be visually distinguished from one with a distant deadline at table-scan time). Pinned by `test_null_deadline_renders_em_dash`. The change is one-way: future tests / code reading the column should treat `''` and `—` as semantically distinct values. | ℹ️ | Observation. No drift risk — the contract is locked in tests. |

*No 🔴 / 🟠 / 🟡 findings.*

---

## Junior-Engineer Q&A

**Q1. The new contract distinguishes `''` ("deadline far enough away") from `—` ("no deadline at all"). Is that worth the API widening?**

A. The two states answer different questions. `''` answers "should I act on this?" — no, the deadline is far enough that nothing is urgent. `—` answers "is there a deadline at all?" — no, the user hasn't filled one in. The user-facing payoff: a position scanned on the table with `—` in the Urgency column flags "set a deadline for this position" as the next user action; a position with `''` flags "this is fine, look at it later". Same column, two distinguishable signals. The Phase 3 T3 collapse-into-`''` was a Phase-3-era simplification; Phase 7 T1's distinction is the polish that came with use. The cost is one test pinning the new branch (`test_null_deadline_renders_em_dash`) + updating one existing test's assertion (was: `''`, now: `—`); the renames in tests handle the contract clarification cleanly.

**Q2. Why does the helper widen its type hint from `str | None` to `Any`?**

A. Pandas surfaces NULL TEXT cells as `float('nan')` once any other row carries a value (gotcha #1 in `docs/dev-notes/streamlit-state-gotchas.md`). The helper is called via `df_display["deadline_date"].apply(_deadline_urgency)` — `.apply` hands each cell to the function unwrapped, and pandas' object-column dtype means the cell can be a `str`, a `float` (NaN), `None`, or — in pathological cases — anything serializable. Annotating the parameter as `str | None` would either lie about the runtime types or force the helper's body to cast/coerce at the boundary, which it already does (the `isinstance(date_str, float) and math.isnan(date_str)` branch is the explicit handling). `Any` is honest about the input type, with the body's three guards (None/empty, NaN, ValueError-on-fromisoformat) collectively covering every input shape that can actually arrive.

**Q3. The implementer chose to duplicate banding logic rather than reuse `database.py::_urgency_glyph`. Doesn't DRY apply here?**

A. DRY applies WITHIN a layer, not ACROSS layers. The DESIGN §2 layer split (`config` ← `database` ← `pages`/`exports`) is structural — pages cannot import `database.py` private helpers (the leading `_` flags them as not-public-API). The two helpers also have different signatures: the dashboard helper takes `days_away: int` (the dashboard already computed the delta), while the page helper takes the raw date string (the page is the one doing the parsing). Reusing `_urgency_glyph` would require either (a) plumbing a string-to-int adapter, which moves the parsing into the page layer anyway, or (b) lifting the helper into a third location both layers can import. Option (b) is the right answer if a third consumer ever appears (Phase 6 T6 carry-over: a `config.urgency_glyph(days)` lift); today there are only two consumers and the duplication cost is ~10 lines.

**Q4. Why does the boundary test for "today" pin `🔴` and not `🟡`?**

A. `days_to_deadline = 0` satisfies `0 <= DEADLINE_URGENT_DAYS` for any positive `DEADLINE_URGENT_DAYS`. The user is staring at a deadline that's literally today — the most urgent state the banding can express. The mathematical structure is `urgent_band = days <= URGENT_DAYS` and `alert_band = (days <= ALERT_DAYS) and not urgent_band`; today's delta lands in the urgent band by inclusive-LE construction. The test pins this explicitly because a `<` (strict) operator instead of `<=` would silently drop today's deadlines into the alert band — visually softer signaling at exactly the moment the user needs the strongest signal. The same boundary-`<=` rationale applies at `DEADLINE_URGENT_DAYS` and `DEADLINE_ALERT_DAYS` exact-match cases (already pinned by `test_urgency_at_urgent_threshold_boundary` and `test_urgency_at_alert_threshold_boundary`); the today-test extends the pattern to the delta=0 case.

**Q5. The tag-CI procedure (c284c20) was followed for the first time today — CI started IN_PROGRESS, the orchestrator waited for SUCCESS via `gh pr checks 37 --watch`, then admin-bypassed. How did that compare to the prior ad-hoc bypass pattern?**

A. The procedural cost is one extra `gh pr checks --watch` + `gh pr view ... --jq` step before merge, which adds ~3 minutes to the orchestrator's review-to-merge cycle (the time CI takes to run). The cost is bounded — the orchestrator can run local six-gate verification while CI is in flight, so the human-attention overhead is ~10 seconds for the verification command itself. The benefit: zero risk of merging a green-locally + red-on-CI regression like the smoke-test gap that shipped main red across PRs #32-#34. The procedure also doesn't depend on `mergeStateStatus` (CLEAN vs BLOCKED is unrelated to the verification step — the `c284c20` amendment cares about CI conclusion only). PR #37 surfaced the BLOCKED state again after PRs #35/#36's CLEAN shift; the procedure handled both transparently.

---

## Carry-overs

- **Phase 7 polish candidate:** the `EM_DASH` constant + the urgency banding logic are now duplicated across enough call sites (`app.py`, `pages/1_Opportunities.py`, `pages/2_Applications.py`, `exports.py`) that a `config.py` lift starts to make sense. Track for the eventual cleanup tier mentioned in `phase-6-finish-cohesion-smoke.md` (between Phase 7 polish and v1.0-rc).
- **No new carry-overs introduced.** Findings 1-4 are all kept-by-design or observations.

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-6-tier5` precedent. The six pre-merge gates
were re-run on the PR head locally (`pr-37` / `766b4fb`) at review
time: ruff clean · `pytest tests/ -q` 836 passed + 1 xfailed ·
`pytest -W error::DeprecationWarning tests/ -q` 836 passed + 1
xfailed · status-literal grep 0 lines · standing isolation gate
`git status --porcelain exports/` empty · CI-mirror local check
836 + 1 xfailed with `postdoc.db` moved aside · `Tests + Lint
(3.14)` CI **conclusion: SUCCESS** verified via
`gh pr checks 37 --watch` + `gh pr view 37 --json statusCheckRollup
--jq '...'` per the standing `c284c20` procedure._
