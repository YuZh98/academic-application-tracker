**Branch:** `feature/phase-7-tier3-SetPageConfigSweep`
**Scope:** Phase 7 T3 — verification-only sweep over `app.py` + four `pages/*.py` files; new `tests/test_pages_cohesion.py` with `TestSetPageConfigSweep` (parametrize-driven, 5 pages × 2 invariants = 10 tests). Audit outcome: all five pages already conform to the locked shape — no production code touched.
**Stats:** 10 new tests (843 → 853 passed, 1 xfailed unchanged); +141 / 0 lines across 1 file (test only); ruff clean; status-literal grep 0 lines; standing isolation gate empty; CI-mirror local check passes (853 + 1 xfailed); **`Tests + Lint (3.14)` CI conclusion: SUCCESS** (`mergeStateStatus: BLOCKED`, `mergeable: MERGEABLE`)
**Verdict:** Approve

---

## Executive Summary

T3 is a verification-only PR — the spec's no-op-outcome path. The
implementer audited all five pages (`app.py`,
`pages/1_Opportunities.py`, `pages/2_Applications.py`,
`pages/3_Recommenders.py`, `pages/4_Export.py`) for the locked
`set_page_config` shape (DESIGN §8.0 + D14, GUIDELINES §13 step 2)
and found every page already conforms. No production-code changes;
the PR ships only the new test file that pins the contract going
forward.

`tests/test_pages_cohesion.py` is a new top-level test file scoped
to cross-page cohesion contracts. T3 ships the `set_page_config`
sweep; the file's docstring earmarks it for T4 (confirm-dialog
audit) and T5 (responsive-layout check) as those tiers ship — a
single home for "this contract holds across the entire page
surface" tests rather than scattering across per-page files.

`TestSetPageConfigSweep` carries two parametrized tests over the
five pages:

1. **Locked-kwargs source-grep** — every page binds `page_title=
   "Postdoc Tracker"`, `page_icon="📋"`, `layout="wide"`. Mirror
   of the existing single-page pin in `test_export_page.py::
   TestExportPageShell::test_page_config_sets_wide_layout`,
   generalised across the page surface.
2. **First-Streamlit-statement AST walk** — no module-level bare
   `st.<X>()` expression statement may precede `set_page_config`.
   Catches a future edit that adds `st.title("X")` above the
   `set_page_config` line — Streamlit emits a runtime warning AND
   silently falls back to centered layout when this happens.

The implementer's design call (flagged in PR body): the AST helper
deliberately **skips decorators**. Load-bearing nuance — see Q1.

All six pre-merge gates green. CI conclusion SUCCESS verified per
the standing `c284c20` procedure.

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `tests/test_pages_cohesion.py` (new) | New top-level test file scoped to "cross-page cohesion contracts that don't fit any single per-page test file". T3 ships the `set_page_config` sweep; T4 (confirm-dialog audit) and T5 (responsive-layout check) earmarked for the same file. Single home for sweep-style tests. | ℹ️ | Observation |

*No 🔴 / 🟠 / 🟡 / 🟢 findings.*

*The decorator-skip design choice in `_first_module_level_st_call` lives in the Q&A section per `GUIDELINES §10` — kept-by-design.*

---

## Junior-Engineer Q&A

**Q1. The AST helper `_first_module_level_st_call` skips decorators. Why is that load-bearing rather than a test-level oversight?**

A. Streamlit's "set_page_config must be the first call" guard is a **render-call** guard, not a module-load-time guard. Decorators like `@st.dialog("...")` execute at module import time but they are factory-style higher-order calls — they construct a wrapper around the decorated function and don't trigger Streamlit's first-call gate. `pages/1_Opportunities.py` has `@st.dialog("Confirm Delete")` on `_confirm_delete_dialog` defined ABOVE its `set_page_config` call, and the page renders fine in production: Streamlit doesn't complain, the dialog works correctly when invoked, layout stays wide. If the AST check counted decorators as "first Streamlit call", the test would force a refactor that solves no real bug — moving `_confirm_delete_dialog` below `set_page_config` (or extracting the decorator) just to satisfy a check that doesn't match Streamlit's actual runtime behaviour. The implementer's docstring frames this honestly: "the AST check must match Streamlit's actual gate, otherwise the test would force a refactor for no real-world bug." Skipping decorators is the correct semantic match.

**Q2. The helper returns `None` when no module-level `st.<X>()` exists. What scenario produces `None`, and what does the test do with it?**

A. Two scenarios. (1) A future edit that moves `set_page_config` (and every other module-level `st.*` call) into a function body — possible if a refactor extracts page rendering into a `def render():` function. (2) A future page that does its rendering entirely through imported helpers without any module-level `st.*` calls. Both are theoretical regressions worth catching — the test's `assert first is not None` clause produces a clear "was set_page_config removed or moved into a function body?" diagnostic, which is more useful than the silent absence of any pinning. The error message tells the reader exactly what to investigate. Today no page has this shape; the assertion is forward-defence.

**Q3. The audit outcome was "all five pages already conform" — so this is essentially a test-only PR with no production change. Why is that the right outcome rather than a "no-op tier, skip"?**

A. The verification has long-term value even when the audit finds nothing. Without the test file, the contract holds **today** but is unenforced — a future edit that adds `st.title("X")` above `set_page_config` on a new page would silently degrade layout (Streamlit warns but the warning is in the server log, not a user-visible error). The 10 tests now pin the contract structurally: any future regression fails CI. The "no production change" framing is honest about today's state but understates the durable value — this is the cohesion contract Phase 7 was supposed to introduce, and shipping it as a test even when the audit passes is exactly the right move. The TASKS.md spec wording ("verify GUIDELINES §13 step 2 holds for every page") is satisfied either by fixing a divergence OR by pinning the contract that's already held — both produce a tier outcome.

**Q4. The PARAMETRIZE list `PAGE_FILES` is hardcoded. Doesn't that mean a future page (e.g. `pages/5_NewPage.py`) wouldn't get swept until someone remembers to update the list?**

A. Yes — and that's the correct trade-off. The alternative (auto-discovery via `glob`) has two problems: (1) it would sweep test files / `__init__.py` / accidental `pages/.DS_Store` if not carefully filtered, and (2) it would silently start checking newly-added files that may legitimately be in flight. The hardcoded list is the canonical "these are the pages on the project" registry; adding a new page is a deliberate act that should also include adding it to the sweep list. The convention surfaces in both directions: the sweep list documents which files are pages, and the page-add procedure includes registering it for the sweep. A drift-prevention test that asserts `PAGE_FILES` matches `glob('pages/*.py') + ['app.py']` would close the loop, but the value is marginal — page additions are rare and reviewable.

**Q5. The implementer mentioned a "branch flip" mid-task — working tree quietly switched from the feature branch back to `main` between `git checkout -b` and `git add`. Worth investigating?**

A. Worth a curious eyebrow but not blocking. The fact that the implementer caught it before committing on main + that the staged file traveled cleanly (because both branches had identical trees at that moment) means the integrity check held. Possible causes: (1) a shell hook or terminal session that auto-switches branches under some condition (none of the project's documented hooks do this; `pre-commit` runs lint/grep, doesn't touch HEAD); (2) a stale terminal pane the implementer reactivated mid-task that was on `main`; (3) a Claude Code session-start hook on a fresh shell. None of these are repeatable failure modes for the sweep itself. Going forward, the standing pre-flight (`git log --oneline -5` to confirm HEAD before any commit) catches this if it recurs. Logging here for future-orchestrator awareness; not a verdict-blocker.

**Q6. Why does `tests/test_pages_cohesion.py` belong in a new file instead of extending `tests/test_export_page.py` (which already has the precedent single-page pin)?**

A. The single-page pin in `test_export_page.py` is correctly scoped to "things about the Export page" — adding a parametrize over four other pages would dilute the file's purpose ("integration tests for `pages/4_Export.py` using AppTest"). The new file is correctly scoped to "cross-page cohesion contracts" — sweeps that hold across the entire page surface. T4 (confirm-dialog audit) and T5 (responsive-layout check) will share the same shape (parametrize over PAGE_FILES, pin a contract that should hold everywhere) and benefit from a shared `PAGE_FILES` constant + AST helper. Keeping the per-page test files focused + the cohesion file focused gives both better long-term maintainability than a monolithic `test_export_page.py` accumulating unrelated sweeps.

---

## Carry-overs

- **No new carry-overs introduced.** Pre-existing Phase 7 polish carry-over (`config.py` lift for `EM_DASH` + urgency banding) unchanged.

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-7-tier2` precedent. The six pre-merge
gates were re-run on the PR head locally (`pr-39` / `081a977`) at
review time: ruff clean · `pytest tests/ -q` 853 passed + 1
xfailed · `pytest -W error::DeprecationWarning tests/ -q` 853
passed + 1 xfailed · status-literal grep 0 lines · standing
isolation gate `git status --porcelain exports/` empty · CI-mirror
local check 853 + 1 xfailed with `postdoc.db` moved aside ·
`Tests + Lint (3.14)` CI **conclusion: SUCCESS** verified via
`gh pr checks 39 --watch` + `gh pr view 39 --json
statusCheckRollup --jq '...'` per the standing `c284c20`
procedure._
