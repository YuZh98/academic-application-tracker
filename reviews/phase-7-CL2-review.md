**Branch:** `feature/phase-7-cleanup-CL2-ConfigLifts`
**Scope:** Phase 7 cleanup CL2 — four lifts to `config.py` (`EM_DASH`, `urgency_glyph(days_away)`, `FILTER_ALL`, `REMINDER_TONES`) plus drop of unused `TRACKER_PROFILE` block (carry-over **C2**). Closes carry-over **C3** in the same PR.
**Stats:** 10 new tests + 4 dropped (TRACKER_PROFILE invariant tests) = net +6 (864 → 870 passed, 1 xfailed unchanged); +234 / −140 lines across 8 files; ruff clean; **pyright 0/0** (CL1 fence held); status-literal grep 0 lines; standing isolation gate empty; CI-mirror local check passes (870 + 1 xfailed); **`Tests + Lint (3.14)` CI conclusion: SUCCESS** (`mergeStateStatus: CLEAN`, `mergeable: MERGEABLE`)
**Verdict:** Approve

---

## Executive Summary

CL2 closes carry-overs **C2** + **C3** in one PR. Five commits on
the branch follow per-lift attribution: 1 test red commit + 4
refactor commits (one per lift/drop) so a future `git blame` on any
of the consolidated constants lands on the commit that did exactly
that lift, not on a mega-commit touching 8 files at once.

**Four lifts:**

1. **`EM_DASH = "—"`** — was duplicated in 5 modules (`app.py` as
   `NEXT_INTERVIEW_EMPTY`, three `pages/*.py`, `exports.py` as
   `_EM_DASH`). Now `config.EM_DASH`. Single source of truth.
2. **`urgency_glyph(days_away: int | None) -> str`** — new
   function on `config.py`. Was duplicated as
   `database.py::_urgency_glyph` (signature: `int`) and
   `pages/1_Opportunities.py::_deadline_urgency` (signature: `Any`
   date string). The lifted form takes the canonical
   `int | None` shape; the page-layer wrapper retains the
   date-string parsing concern + delegates; `database.py`'s
   `_urgency_glyph` is **deleted entirely** (the two call sites
   in `get_upcoming` now pass `config.urgency_glyph` directly to
   `Series.apply`). Also resolves the open question from
   Phase 7 T1 review Q3: "if a third consumer ever appears, lift
   to `config.py`" — CL2 is that lift.
3. **`FILTER_ALL = "All"`** — was a magic literal in 3 pages
   (`pages/1_Opportunities.py`, `pages/2_Applications.py`,
   `pages/3_Recommenders.py`). Lives next to
   `STATUS_FILTER_ACTIVE` in `config.py` since the two are the
   filter-bar's two sentinel options.
4. **`REMINDER_TONES: tuple[str, ...] = ("gentle", "urgent")`** —
   was a private `_REMINDER_TONES` in `pages/3_Recommenders.py`.
   Now public on `config.py` so a future implementer adding a
   third tone (e.g. `"formal"`) can do it as a config-only edit.

**One drop:**

5. **`TRACKER_PROFILE` block** — `TRACKER_PROFILE`,
   `VALID_PROFILES`, the import-time assertion, plus the 4
   corresponding tests in `tests/test_config.py::TestTrackerProfile`.
   Never read by any module since v1.1 doc refactor. Carry-over
   **C2** closed.

**Verification — removal greps clean** (per the spec's pre-PR
verification commands): no surviving `EM_DASH = "—"` literal in
source; no bare `"All"` filter literal in pages; no `_REMINDER_TONES`
references; zero `TRACKER_PROFILE` matches anywhere.

**Behavioural delta — zero.** All four lifts are
behaviour-preserving refactors (864 → 870 tests; the 6 net new
tests pin the new contracts at the lift surface). Existing per-page
urgency / filter / reminder tests pass without modification — the
refactor preserves runtime behaviour exactly. CL1's pyright fence
held through the lift — `pyright .` returns 0/0 post-CL2.

All seven pre-merge gates green. CI conclusion SUCCESS verified
per the standing `c284c20` procedure (CI was already SUCCESS at
PR-creation time; mergeStateStatus CLEAN this round).

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `pages/1_Opportunities.py::_deadline_urgency` | Page-layer wrapper retains the date-string parsing concern (not lifted to config). Three NULL-shape branches now all return `config.urgency_glyph(None)` — five lines that could be a single guard returning `config.urgency_glyph(None)` if any of them matches. Implementer's choice keeps the explicit branches for clarity (each branch documents the specific NULL shape it catches: `None`, empty string, NaN, malformed-string-via-`ValueError`). Cosmetic; no functional difference. | ℹ️ | Observation |
| 2 | `database.py::_urgency_glyph` deleted entirely | The function is removed from `database.py` rather than kept as a thin pass-through. Both `get_upcoming` call sites now pass `config.urgency_glyph` directly into `Series.apply`. Cleaner — no redundant wrapper layer — but means `database.py` no longer carries an `_urgency_glyph` symbol. Anyone searching `git log -- database.py` for the old function will find the CL2 deletion commit; the new home is config. | ℹ️ | Observation |

*No 🔴 / 🟠 / 🟡 / 🟢 findings.*

---

## Junior-Engineer Q&A

**Q1. The CL2 spec listed `urgency_glyph` as a "lift" but the implementer actually deleted `database.py::_urgency_glyph` rather than keeping a thin wrapper. Was that the right call?**

A. Yes. The wrapper would have been a one-line passthrough (`def _urgency_glyph(d: int) -> str: return config.urgency_glyph(d)`) with no value-add — same signature, same behaviour, same import path within `database.py`. The two call sites in `get_upcoming` already use `Series.apply(_urgency_glyph)`; flipping them to `Series.apply(config.urgency_glyph)` is a one-token change per call site (2 lines edited). The deletion saves ~7 lines (the function body + the surrounding comment block) without changing any behaviour. The page-layer wrapper IS kept (Finding #1) because it carries a non-trivial concern (parse date string → days delta with NaN handling) that the database layer doesn't need; symmetry between layers isn't a goal in itself. The implementer's instinct here is right — keep the wrapper where it adds parsing logic; delete it where it would just forward.

**Q2. The `urgency_glyph` signature is `int | None`. Why `None` rather than a separate `urgency_glyph_for_no_deadline()` function?**

A. Three reasons. (1) **Single call site in the page wrapper**: `_deadline_urgency` has four branches that produce a "no usable date" outcome (None, empty string, NaN, ValueError). Without `None` in the signature, each of the four branches needs an `if no_date: return EM_DASH else: return config.urgency_glyph(parsed_days)` shape — duplicated four times. With `None`, all four branches collapse to `return config.urgency_glyph(None)`. Cleaner at the call site. (2) **Database layer never has the no-deadline case**: `get_upcoming` filters to known-future deadlines before computing `days_away`, so the `None` branch never fires from there. The signature accepts `None` for the page-layer's benefit; the database layer just never passes `None`. Optional-input is the standard Python idiom for "this function handles a missing-input case along with the present-input cases". (3) **Test contract is single-helper**: one `urgency_glyph` function with full banding + `None` handling has one test class (`TestUrgencyGlyph`) instead of two, which keeps the boundary tests grouped logically.

**Q3. The CL2 spec also mentioned `app.py`'s `NEXT_INTERVIEW_EMPTY` as a duplicate of `EM_DASH`. The implementer renamed it to use `config.EM_DASH`. Doesn't that lose semantic information ("this specifically marks an absent next-interview")?**

A. The semantic information was always orthogonal to the value. The constant's job is "render a placeholder when there's no value to show"; the *meaning* of "no value" varies by surface (no recommender, no deadline, no next interview, no application response), but the *glyph* doesn't. Naming the constant `NEXT_INTERVIEW_EMPTY` muddies that distinction by suggesting the value differs in this context, when in fact the project pinned a single em-dash for every absent-value cell as a cohesion contract (Phase 4 cohesion-smoke confirmed this verbatim). Lifting to `config.EM_DASH` makes the cohesion contract first-class. If a future surface genuinely needs a different placeholder (e.g. `?` for "unknown" vs `—` for "absent"), it adds a second config constant; today every surface uses the same em-dash and a single constant matches reality.

**Q4. The 4 dropped tests in `tests/test_config.py::TestTrackerProfile` were testing an import-time assertion that's now gone. Why drop the tests rather than keeping them as a regression-prevent against TRACKER_PROFILE coming back?**

A. The tests pinned **a contract that no longer exists**. Testing "TRACKER_PROFILE must be in VALID_PROFILES" requires both `TRACKER_PROFILE` and `VALID_PROFILES` to exist; once both are dropped, the test would fail with `AttributeError` (not even reach its assertion) — that's not a regression-prevent, that's a broken test. Carry-over **C2** said "drop unused TRACKER_PROFILE" — partially keeping the tests would defeat the cleanup. If a future iteration genuinely wants tracker-profile gating (a "faculty profile" in `roadmap.md`'s v2 plan), the contract gets re-added with new tests appropriate to the new shape. The tests didn't carry forward-looking value — they pinned a feature that was never used.

**Q5. The pyright fence (CL1) held through CL2 — 0/0 errors before AND after the lift. What does that signal about the refactor's correctness?**

A. Pyright caught a class of regression that's hard to surface otherwise: type-shape drift in the consumer modules. CL2 changed how 6 different files interact with the lifted constants (every consumer renamed an import, replaced a literal, swapped a function reference). A wrong import path, a wrong type signature on `urgency_glyph`, or a missing `Optional` annotation would show up as a pyright error — not a runtime test failure (the suite would still pass because the values are right) but a structural drift. CL1's value proposition pays out exactly here: every refactor PR after CL1 gets a "your types still hold" check for free. Without the fence, CL2 could have shipped with subtly-wrong type annotations that wouldn't surface until CL3 or CL4 tried to consume the new contracts. The 0/0 result is the post-refactor confirmation that the lift was clean.

**Q6. The implementer split CL2 into 5 commits (1 test red + 4 refactor commits, one per lift/drop). Each refactor commit touches 2-4 files. Why this granularity?**

A. **Per-line `git blame` attribution that survives.** A future engineer running `git blame -L <line> pages/3_Recommenders.py` on the line that imports `config.REMINDER_TONES` lands on the CL2 refactor commit titled `refactor(phase-7-CL2): lift _REMINDER_TONES to config.REMINDER_TONES`, with the rationale in the commit body. A mega-commit titled `refactor(phase-7-CL2): config lifts` would show "we lifted some stuff" — readable but not pinpoint. The per-lift commit shape mirrors CL1's per-file fix-commit shape; same intuition, different axis (CL1 split by file, CL2 splits by logical change). The cost is 5 commits in one PR vs 2; the benefit is every consolidated symbol carries its rationale via `git log --follow` in perpetuity. The single test-red commit at the top of the stack is the standard TDD shape; the refactor commits each turn one batch of consumers green.

---

## Carry-overs

- **C2** (TRACKER_PROFILE removal) — **CLOSED** in this PR.
- **C3** ("All" filter sentinel + `_REMINDER_TONES` to config) — **CLOSED** in this PR.
- **No new carry-overs introduced.**

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-7-CL1` precedent. The seven pre-merge
gates were re-run on the PR head locally (`pr-42` / `40df61b`) at
review time: ruff clean · **pyright 0 errors / 0 warnings / 0
informations** (CL1 fence held through the lift) · `pytest tests/
-q` 870 passed + 1 xfailed · `pytest -W error::DeprecationWarning
tests/ -q` 870 passed + 1 xfailed · status-literal grep 0 lines ·
standing isolation gate `git status --porcelain exports/` empty ·
CI-mirror local check 870 + 1 xfailed with `postdoc.db` moved
aside · `Tests + Lint (3.14)` CI **conclusion: SUCCESS**
(`mergeStateStatus: CLEAN`) verified per the standing `c284c20`
procedure._
