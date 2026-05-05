**Branch:** `feature/phase-7-cleanup-CL5-DocDriftTrim`
**Scope:** Phase 7 cleanup CL5 — three CL4 doc-drift carry-overs trimmed (Trim 1: DESIGN.md §8.4 line 631 back-reference clause dropped; Trim 2: `pages/3_Recommenders.py::_build_compose_mailto` docstring rewritten as forward-looking rule; Trim 3: ~17 `# Phase 7 CL4 Fix N:` inline comments swept across 4 source + 4 test files + `config.py` section header).
**Stats:** Net 0 test count change (879 → 879 passed, 1 xfailed unchanged); +47 / −97 lines across 10 files (net −50 — mostly comment deletions); ruff clean; **pyright 0/0** (CL1 fence held); status-literal grep 0 lines; standing isolation gate empty; CI-mirror local check passes (879 + 1 xfailed); **`Tests + Lint (3.14)` CI conclusion: SUCCESS** (`mergeStateStatus: CLEAN`)
**Verdict:** Approve

---

## Executive Summary

CL5 closes the three 🟡 doc-drift findings deferred from CL4's
review. Three commits on the branch, one per trim — same per-logical-
change attribution shape as CL2's 5-commit lift split:

- **Trim 1 (`78a5a8d`)** — `DESIGN.md` line 631 back-reference clause
  dropped: *"Phase 7 CL4 Fix 2 amended this line: the previously-
  locked verbatim plural-only form read 'letters for 1 postdoc
  applications' at N=1, which is grammatically awkward."* The
  forward-looking pluralization rule preceding it stays as-is.

- **Trim 2 (`73c75b5`)** — `pages/3_Recommenders.py::_build_compose_
  mailto` docstring rewritten from a 6-line history-as-guidance
  paragraph (`"Subject pluralization (Phase 7 CL4 Fix 2): the
  singular form is used when N=1 ... DESIGN §8.4 line 631 amends the
  previously-locked ... wording — the earlier verbatim form read
  ... at N=1, which is grammatically awkward."`) to a 3-line
  forward-looking rule (`"Subject follows English pluralization
  rules (DESIGN §8.4): at N=1 reads 'letter for 1 postdoc
  application' (singular both nouns); at N≥2 reads 'letters for N
  postdoc applications'."`).

- **Trim 3 (`af876d9`)** — sweep across ~17 sites in 4 source files
  (`app.py`, `pages/1_Opportunities.py`, `pages/2_Applications.py`,
  `pages/3_Recommenders.py`) + 4 test files + `config.py`'s empty-
  state section header. Implementer's judgment per CL4 review
  Finding #3 ("keep the cascade-safety note + drop the change-log
  noise"):

  - **Kept** (forward-looking invariants): the dirty-diff design
    rationale block in `pages/2_Applications.py:794-797` (explains
    why per-field comparison is needed: normalizes widget shape
    ↔ DB shape so the diff doesn't false-positive on cosmetic
    differences); the cascade-safety note explaining why no-op
    short-circuit is safe; "pin against constant by name"
    reasoning in test docstrings.
  - **Dropped** (change-log noise): 5 verbatim `# Phase 7 CL4
    Fix 4: empty-state copy lifted to config so a future wording
    edit is a one-line change tracked via git blame.` comments
    repeated at 5 sites (the "lifted to config" framing rots once
    the rollup commit lands; `git blame` already tells the future
    reader where the constant came from); 2 toast-wording-branch
    blocks; the `config.py` section-header CL4 attribution.

**Verification — full sweep clean.** Post-CL5,
`grep -rn "Phase 7 CL4 Fix" app.py config.py pages/ tests/`
returns **0 matches**. The implementer chose the full-sweep outcome
shape (not the selective-sweep with retained prefixes); every
change-log reference is gone, every forward-looking invariant
either stripped its prefix while keeping the rationale, or stayed
in surrounding prose without the `Phase 7 CL4 Fix N:` header.

All seven pre-merge gates green. CI conclusion SUCCESS verified per
the standing `c284c20` procedure (CI was already SUCCESS at
PR-creation; mergeStateStatus CLEAN).

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `tests/test_applications_page.py` (and 3 other test files) | Several test docstrings dropped the `Phase 7 CL4 Fix N:` prefix and now read more cleanly as contract-pinning prose (e.g. "clicking Save when the form has no dirty fields..."). The contract content survives unchanged; only the change-log preface is gone. Mirrors the same pattern across the 4 test files swept. | ℹ️ | Observation |
| 2 | `pages/2_Applications.py:794-797` dirty-diff design rationale block | Implementer correctly retained the multi-line explanation of why per-field comparison normalizes widget shape ↔ DB shape (date ↔ ISO string, bool ↔ 0/1 INTEGER) — that's a forward-looking invariant a future reader needs. Only the trailing `Phase 7 CL4 Fix 1 — was previously an unconditional ...` back-reference clause was stripped. | ℹ️ | Observation |

*No 🔴 / 🟠 / 🟡 / 🟢 findings.*

---

## Junior-Engineer Q&A

**Q1. The implementer chose the full-sweep outcome (zero matches post-CL5) rather than selectively retaining `Phase 7 CL4 Fix N:` prefixes on forward-looking comments. Why is that the right call?**

A. The prefix itself is the change-log noise — a future reader hitting `# Phase 7 CL4 Fix 1: branch toast wording on the dirty diff so a no-op Save reads "No changes to save."` sees two pieces of information: (a) "this was changed in CL4" (transient git-history fact) and (b) "branch toast wording on the dirty diff" (forward-looking invariant). The prefix carries only (a); stripping it leaves (b) intact. Keeping the prefix would have saved a search through `git blame` for context but at the cost of every future reader of the file having to mentally filter the noise. The implementer's "full sweep + de-prefix where rationale matters" shape is honest about which information lives where: the rationale lives in the comment, the change history lives in `git log`. Same intuition that drives `git commit --amend` over leaving a trail of `WIP:` commits — squash the noise, keep the signal.

**Q2. The diff is +47 / −97 — net −50 lines. Most of that is comment deletions. Are we losing valuable comments along with the change-log noise?**

A. No — the deletions are exactly the change-log noise the CL4 review flagged. The valuable comments (cascade-safety note in apps_detail_form, dirty-diff design rationale, "pin against constant by name" reasoning) all survive — they were already separate paragraphs from the `Phase 7 CL4 Fix N:` prefix sentences, so the implementer could strip the prefix while leaving the surrounding rationale intact. The 5 verbatim "lifted to config" comments at empty-state sites were the largest contributor to the deletion count (5 × ~3 lines each = ~15 lines just from those) — those carried zero forward-looking value because the lift itself is documented in `config.py`'s constant definitions and `git blame` shows when each call site switched. The 2 toast-wording-branch comment blocks were similarly redundant with the now-self-explanatory branched code structure. Net: comment density dropped, comment signal-to-noise ratio improved.

**Q3. Trim 2 rewrote a 6-line docstring to 3 lines. Doesn't shorter mean less informative?**

A. Shorter does not mean less informative when the deleted lines were saying the same thing twice in different framings. The original docstring had: (1) a "what the function does" line ("Subject pluralization (Phase 7 CL4 Fix 2): ..."), (2) a "history" line ("DESIGN §8.4 line 631 amends the previously-locked ..."), and (3) a "why we changed" line ("the earlier verbatim form read 'letters for 1 postdoc applications' at N=1, which is grammatically awkward"). Lines (2) and (3) carry the change history; line (1) carries the contract. Stripping (2) and (3) and keeping (1) (with its `Phase 7 CL4 Fix 2:` prefix removed, replaced by a forward-looking `(DESIGN §8.4)` cross-reference) leaves the contract intact while removing the change narration. The new 3-line form actually adds precision via the explicit DESIGN cross-link — readers can follow back to the spec for the canonical statement of the rule. Less prose, more pointer to authoritative source.

**Q4. The CL5 spec said the verification is "negative — `grep` should return 0 matches OR only forward-looking-invariant comments with prefix stripped." The implementer chose 0 matches. Was the alternative also acceptable?**

A. Both were acceptable per the spec; the choice is judgment-based. The full-sweep path (0 matches) is cleaner — every CL4 reference goes away, future readers don't see a CL4-attributed comment and wonder "why did THIS one survive when the others didn't?" The selective-sweep path would have been defensible if some forward-looking comments genuinely needed the attribution to be parseable (e.g. "this design was settled in PR #44, see review for trade-off analysis"); but in practice, every forward-looking comment in CL4's surface had a self-contained rationale that didn't need the PR-number anchor. The implementer's full-sweep is the simpler outcome — fewer rules to apply per comment. If a future tier hits a similar carry-over situation where some comments DO need the attribution preserved, the selective-sweep path is still available.

**Q5. The CL1 pyright fence held through three refactor PRs (CL2 lifts, CL3 helper extraction, CL4 polish) and now through CL5 doc-trim. Is the fence's value proposition fully validated?**

A. CL5's pyright pass adds a slightly different signal than the prior three: the previous PRs all touched executable code (consumer-site rewrites, function relocations, behaviour branches), where type drift would manifest as concrete signature mismatches. CL5 touches almost only comments + docstrings, where type drift is ostensibly impossible. The 0/0 result here confirms the pyright invocation itself is robust — comment-only changes don't accidentally trigger spurious "import is unused" or "type narrowing failed" reports. That's a different validation than CL2-CL4 provided. Together, four consecutive PRs across orthogonal change classes (lift, extract, behavioural-branch, comment-trim) all maintaining 0/0 is strong evidence the fence is correctly scoped — not too strict (would surface false positives on cosmetic changes), not too loose (catches the regression classes from PR #22's original cleanup).

**Q6. CL5 closes the implementer-shippable Phase 7 cleanup work. What's left in the cleanup arc before T5 + T6?**

A. **CL6 — orchestrator-only chore.** Two items: (a) codify `gh pr merge --delete-branch` into `ORCHESTRATOR_HANDOFF.md` "Recurring post-merge ritual" — 4 consecutive proven uses across CL1-CL4 (PRs #41, #42, #43, #44) plus CL5 (PR #45 ahead) means the pattern is well-established + worth pinning structurally; (b) retroactive trim of older Phase 5 + Phase 6 tier reviews still carrying `Kept by design` rows in Findings tables (per GUIDELINES §10 those belong in Q&A — the earlier `5f1d0f3` audit only fixed the two most-recent reviews) + older `[v0.6.0]` / `[v0.5.0]` / etc. CHANGELOG blocks with long-form descriptive entries (per §14.4 should be one-line imperatives). CL6 runs direct on main — no feature branch — because both deliverables are orchestrator-territory files that the implementer can't touch under the Coordination Protocol's file-ownership rules. Then T5 (responsive layout, user-driven manual capture) → T6 (Phase 7 close-out + tag `v0.8.0`).

---

## Carry-overs

- **No new carry-overs introduced.** CL5 closed all 3 🟡 findings from CL4's review.
- CL6 (orchestrator chore) picks up next per the AGENTS.md sub-tier table.

---

_Written 2026-05-05 as a pre-merge review per the
`phase-5-tier1` … `phase-7-CL4` precedent. The seven pre-merge
gates were re-run on the PR head locally (`pr-45` / `af876d9`) at
review time: ruff clean · **pyright 0 errors / 0 warnings / 0
informations** (CL1 fence held through the doc-trim) · `pytest
tests/ -q` 879 passed + 1 xfailed · `pytest -W
error::DeprecationWarning tests/ -q` 879 passed + 1 xfailed ·
status-literal grep 0 lines · standing isolation gate `git status
--porcelain exports/` empty · CI-mirror local check 879 + 1
xfailed with `postdoc.db` moved aside · `Tests + Lint (3.14)` CI
**conclusion: SUCCESS** (`mergeStateStatus: CLEAN`) verified per
the standing `c284c20` procedure._
