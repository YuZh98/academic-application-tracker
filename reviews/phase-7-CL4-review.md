**Branch:** `feature/phase-7-cleanup-CL4-PolishBatched`
**Scope:** Phase 7 cleanup CL4 — four UX polish items previously deferred to Phase 7 close-out, batched in one PR with four commits (one per fix). Fix 1: save-toast wording branched on dirty diff across three save handlers (apps_detail_form gains per-field dirty-diff infrastructure; per-row interview save + recs_edit_form get the toast-wording branch only). Fix 2: `_build_compose_mailto` subject pluralizes on N=1 + DESIGN §8.4 line 631 amend. Fix 3: `app.py` empty-DB hero `st.write` → `st.markdown` (sole outlier in cross-page convention). Fix 4: 5 hardcoded `st.info(...)` empty-state strings lifted to per-surface constants in `config.py`.
**Stats:** +336 / −56 across 10 files (DESIGN.md + 4 source files + 4 test files + config.py); 4 new tests; 875 → 879 passed (1 xfailed unchanged); ruff clean; **pyright 0/0** (CL1 fence held); status-literal grep 0 lines; standing isolation gate empty; CI-mirror local check passes (per implementer PR body); **`Tests + Lint (3.14)` CI conclusion: SUCCESS** (workflow run `25357461413`, 3m28s)
**Verdict:** Approve with carry-overs (3 🟡 doc-drift findings deferred to CL5)

---

## Executive Summary

CL4 ships the four UX polish items the user-driven 2026-05-04
"postpone T5 until accumulated cleanup lands" decision had set
aside. The implementer batched them into one PR with four commits
following CL2's per-lift commit-split precedent — clean per-line
`git blame` attribution survives the merge.

Fix 1 is the only behaviourally non-trivial change: `apps_detail_form`
on `pages/2_Applications.py` gains a per-field dirty diff that
short-circuits the Save handler when nothing changed. The previous
shape was an unconditional `upsert_application(propagate_status=True)`
with the full 8-field payload on every click — even idempotent clicks
fired both the DB write and the R1/R3 cascade machinery. The new
shape compares each widget value against the persisted `app_row` and
only proceeds if the resulting `fields` dict is non-empty. The
implementer correctly normalized the comparison (date ↔ ISO string,
bool ↔ 0/1 INTEGER) using `_safe_str` for nullable text fields, so
the diff doesn't false-positive on cosmetic differences. Cascade
safety is reasoned correctly in the inline comment ("there's no
transition to fire against") and pinned by the spy test
`test_save_with_no_changes_skips_upsert`. The two other Fix 1 sites
(per-row interview save + recs_edit_form save) already had the
dirty-diff write-gate; only the toast wording was previously
dishonest, and the change is a one-line branch.

Fix 1's deliberate scope exclusion — `pages/1_Opportunities.py` save
handlers (overview / requirements / materials / notes) — is the
correct call. Those four save paths currently rewrite the full
payload on every Save (no dirty-diff infrastructure); adding the
infrastructure to four more handlers would balloon CL4's "small UX
fixes" mandate. The implementer flagged this in the PR description
as a follow-up, which is the right shape.

Fix 2 is a clean two-line branch in `_build_compose_mailto` plus a
DESIGN §8.4 amend in the same commit. The N=1 wording
(`"Following up: letter for 1 postdoc application"`) and the N≥2
wording (unchanged from the previous plural-only form) cover both
branches. The existing test
`test_subject_uses_locked_string_with_position_count` updated in
place; the multi-position pin is unchanged.

Fix 3 is a one-call swap on `app.py:116`. The implementer surveyed
the codebase first (PR body lists every prose call site by file —
`app.py` Pending-Alerts cards, `pages/2_Applications.py` "All
recs..." + Interviews subheader + per-row Interview, etc.) and
identified the empty-DB hero as the lone `st.write` outlier in a
codebase that otherwise uses `st.markdown` for prose. Behaviour is
identical because `st.write(str)` routes to `st.markdown`
internally; the AppTest `at.markdown[i].value` lookups continue to
work; no test changes needed. Cohesion-only refactor.

Fix 4 lifts the five `st.info(...)` empty-state strings to
per-surface constants in `config.py` (per-surface naming, not a
single template — the wording is intentionally surface-specific).
Tests in all four affected test files updated to assert against
the constants by name (CL2's `EM_DASH` / `FILTER_ALL` precedent),
so a future copy edit lands once in `config.py` and flows through
to assertions automatically.

All seven pre-merge gates green. CI conclusion SUCCESS verified
per the standing `c284c20` procedure (CI was already SUCCESS at
PR-merge time). Branch auto-deleted via `--delete-branch`.

The three 🟡 findings below are doc-drift only — none affects
runtime behaviour or test correctness. They are deferred to CL5
where the existing scope (Phase 5 + Phase 6 review-doc trim,
CHANGELOG older blocks, ritual `--delete-branch` codification)
already aligns with the cleanup pattern these need.

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `DESIGN.md:631` | Spec line includes back-reference narration: *"Phase 7 CL4 Fix 2 amended this line: the previously-locked verbatim plural-only form read 'letters for 1 postdoc applications' at N=1, which is grammatically awkward."* This is the **history-as-guidance anti-pattern** the user codified through three cycles (`e4732f7` history-as-guidance pass; `289f7dd` user-driven §14.4 rewrite; `d937c28` §11 + §14 prose cleanup). DESIGN.md is forward-looking spec; rationale belongs in commit messages + this review doc, not in the spec itself. The forward-looking part of the line ("subject follows English pluralization rules — at `N=1` reads ...; at `N≥2` reads ...") is correct and stays; the trailing back-reference clause is the part to trim. | 🟡 | Deferred to CL5 |
| 2 | `pages/3_Recommenders.py::_build_compose_mailto` docstring (lines 269–275 of diff) | Same anti-pattern in the docstring: "DESIGN §8.4 line 631 amends the previously-locked '...' wording — the earlier verbatim form read '...' at N=1, which is grammatically awkward." Docstrings should state the rule, not narrate the change history. Trim to the forward-looking pluralization rule. | 🟡 | Deferred to CL5 |
| 3 | Repeated `# Phase 7 CL4 Fix N: ...` comment blocks across `app.py`, `pages/1_Opportunities.py`, `pages/2_Applications.py`, `pages/3_Recommenders.py`, `config.py`, tests | Comments narrate *why this was changed in this PR* rather than what the code does. Some are genuinely useful (the Fix 1 cascade-safety note explaining why the no-op short-circuit is safe — that's a forward-looking invariant a future reader needs); others are change-log noise that rots after the rollup commit (e.g. `# Phase 7 CL4 Fix 4: empty-state copy lifted to config so a future wording edit is a one-line change tracked via git blame.` repeated verbatim at five sites). The "lifted to config" framing is the kind of historical narration the user has consistently pushed back on. CL5 sweep should keep the cascade-safety note + drop the change-log noise. | 🟡 | Deferred to CL5 |
| 4 | `pages/2_Applications.py` apps_detail_form behavioural change | Was unconditional `upsert_application` with full 8-field payload + cascade. Now per-field dirty diff + skip on empty `fields` dict. Cascade-safety reasoned correctly inline + pinned by `test_save_with_no_changes_skips_upsert` spy. The per-field comparison correctly normalizes widget shape ↔ DB shape (date ↔ ISO, bool ↔ 0/1 INTEGER) so the diff doesn't false-positive on cosmetic differences; the `RESULT_DEFAULT` and `RESPONSE_TYPES`-membership guards on the DB-side comparison correctly mirror how the widgets seed (no false dirty-diff when DB holds an out-of-vocab value). | 🟢 | Verified |
| 5 | Fix 1 scope on `pages/1_Opportunities.py` deferred | PR explicitly flags overview / requirements / materials / notes save handlers as out-of-scope (no dirty-diff infrastructure today; would balloon CL4's mandate). Reasonable scoping; logged as follow-up in PR body. | ℹ️ | Observation |

*No 🔴 / 🟠 findings.*

---

## Junior-Engineer Q&A

**Q1. Fix 1 introduced a per-field dirty diff to `apps_detail_form` — eight `_w_*` widget reads + eight `_db_*` DB reads + eight `if` checks. Isn't this a lot of new code for a wording polish?**

A. The dirty-diff machinery isn't *for* the wording polish — it's
the prerequisite to honest wording. To say "No changes to save."
truthfully, the page has to actually know whether anything changed.
The two other Fix 1 sites (per-row interview save + recs_edit_form
save) already had the dirty diff because their save handlers were
written from day one to gate the DB write on `_dirty`; the wording
fix there was a one-line branch on the existing `_dirty` check.
`apps_detail_form` was the outlier — its T2-A original called
`upsert_application(propagate_status=True)` with the full 8-field
payload unconditionally, then surfaced both Saved + cascade
toasts based on the writer's return value. Adding the dirty diff
brings it into structural parity with the other two save handlers,
and it has a real correctness benefit independent of the toast
wording: a no-op Save on a `[OFFER]` row no longer fires the R3
"already-Offer" self-write through the database, which (a) saves
a transaction round-trip on every idempotent click, and (b)
removes the (theoretical) risk that a future change to R3's
`status_changed` semantics would surface a spurious cascade toast
on no-op Saves. The spy test
`test_save_with_no_changes_skips_upsert` pins this contract
explicitly so the savings can't regress silently.

**Q2. The implementer added the dirty diff to `apps_detail_form` but explicitly skipped the same pattern on `pages/1_Opportunities.py`. Why is that not a consistency problem?**

A. CL4 is scoped as "small UX fixes" — it batches four polish
items that don't structurally change anything. Opportunities has
four save handlers (overview, requirements, materials, notes),
each with its own widget set (mostly multi-select / checkbox
groups, not the date / response-type / notes shape that
Applications has). Adding the dirty-diff infrastructure to four
more sites means four more 16-line `_w_*` / `_db_*` blocks plus
four more spy tests, plus reasoning about widget-shape ↔ DB-shape
normalization for each one. That's structurally a separate
sub-tier — call it CL6 or fold it into a future polish PR — not
something to backdoor into a "wording polish" tier. The
implementer's PR body flags this as a follow-up, which is the
honest framing. The consistency cost is real but bounded:
Opportunities' Save handlers will fire the dishonest `Saved`
toast on no-op clicks until the follow-up lands, which is the
same shape they had pre-CL4. No regression, just a deferred
improvement.

**Q3. Fix 4 added five constants to `config.py` instead of a single `EMPTY_FILTERED_TEMPLATE`. The PR body and AGENTS.md both call out the per-surface choice as deliberate. What's the actual cost of choosing wrong here?**

A. The single-template path would write
`EMPTY_FILTERED_TEMPLATE = "No {noun} match the current filter(s)."`
and ask each consumer to interpolate `noun="positions"` /
`noun="applications"` etc. Two costs: (1) the singular/plural
mismatch — Opportunities has three filters in its bar (status +
priority + field + Phase 7 T2 search), so "filters" plural is
honest; Applications has one filter, so "filter" singular is
honest. The template would have to choose one or the other
(losing the truth signal) or branch on a parameter (adding
complexity that defeats the point of centralization). (2) The
"yet — use Quick Add above to get started" copy on the empty-DB
branch and the "No pending recommenders" / "No pending recommender
follow-ups" copy on the alert panels don't fit a "X match the
current filter" template at all — they're surface-specific phrases
that say something narrative-specific about each surface. So even
choosing the template path leaves three of the five strings with
their own constants. Five per-surface constants is the honest
shape. The "cost" of this choice is just five constant names
instead of one, which is what test files now consume by name
(mirror of CL2's `EM_DASH` / `FILTER_ALL` test-update pattern).

**Q4. The Findings table flags three 🟡 doc-drift items but recommends Approve. Why aren't these merge blockers?**

A. The user has been clear (project memory + GUIDELINES §14)
that the history-as-guidance anti-pattern is load-bearing for
spec docs. The blocking question is "does this anti-pattern
proliferate or does it stay contained?" If the orchestrator
blocks merges on every spec line that drifts, the implementer
loop slows and the user's "merge-when-CI-green" signal is
overridden. The structural answer the project already has is
**CL5** — it's an orchestrator-only sub-tier explicitly scoped
for doc-drift retroactive trim. Adding the three CL4 findings to
CL5's existing scope (Phase 5 + Phase 6 review-doc `Kept by
design` row trim, CHANGELOG older-block trim, ritual
`--delete-branch` codification) costs ~20 minutes of orchestrator
work, lands on main as a single docs-only commit, and never
touches code or tests. The alternative — block CL4, hand back to
implementer for a docs-only fix-up commit — costs more cycles
(implementer round-trip + new CI run + new admin-bypass merge)
for a strictly worse outcome (the trim still has to happen; it
just happens twice across two PRs instead of once on main). The
user's "PR is green; merge it" signal in this session
acknowledged the trade-off implicitly.

**Q5. The PR description listed two manual smoke tests as unchecked. The orchestrator merged anyway. Was that the right call?**

A. The unchecked smokes were "open Streamlit + click Save with
no changes + visually confirm the new toast wording" and "open a
recommender card with N=1 and N=2 owed letters + visually confirm
singular vs. plural subject in the mailto URL". Both are pinned
by AppTest tests in the PR (`test_save_with_no_changes_fires_no_changes_toast`
+ `test_subject_uses_locked_string_with_position_count` updated
shape) — the AppTest layer covers the same toast / URL the human
would see, just without the visual rendering. The manual smokes
would catch a Streamlit-specific rendering bug that the AppTest
layer can't see (toast text getting truncated by the toast
container's CSS, e.g.), but those are exceptionally rare for
text-only changes in already-tested call sites. The CI-mirror
suite passing + AppTest pins on the new behaviour + 879 / 1
xfailed under all seven pre-merge gates is sufficient signal for
text-only polish. If the user opens the app post-merge and the
toast renders weird, the fix is a CSS-style follow-up, not a CL4
revert.

---

## Carry-overs

The three 🟡 findings above (DESIGN §8.4 line 631 history-as-guidance
trim · `_build_compose_mailto` docstring trim · `# Phase 7 CL4 Fix N:`
comment-noise sweep) added to **CL5**'s existing scope. CL5 is
orchestrator-only and runs next on main without a feature branch.

Fix 1's deferred sites — `pages/1_Opportunities.py` save handlers
(overview / requirements / materials / notes) — logged for a future
polish PR (CL6 candidate or fold into a Phase-7-T-something tier
that already touches Opportunities). No dirty-diff infrastructure
today; adding four more sites is a structurally separate sub-tier,
not a "wording polish" follow-up.

---

## Lessons

- **Wording polish often requires structural plumbing.** The
  Fix 1 case where Applications gained the dirty diff for the first
  time is the obvious instance, but the broader pattern is: any
  time a UI message claims something about the underlying state, the
  page has to actually know that thing. "No changes to save." is
  truthful only after the dirty diff exists.
- **Per-surface constants beat single templates when the wording
  carries truth signals.** Fix 4's choice locked in the
  singular/plural distinction between Opportunities ("filters") and
  Applications ("filter") — a template would have erased it. When
  copy carries semantic information about the surface, the
  centralization shape needs to preserve that information.
- **Spec amends + back-references are the wrong shape.** The
  history-as-guidance anti-pattern keeps surfacing because it feels
  natural to explain *why* a spec line changed in the spec line
  itself. The discipline is: spec states the rule; commit message +
  review doc explains the rationale; future readers find the
  rationale via `git blame`. CL4's DESIGN §8.4 amend is a textbook
  instance — Fix 2's commit message + this review doc + the
  CHANGELOG entry collectively cover the rationale; the spec line
  should just state the pluralization rule.
