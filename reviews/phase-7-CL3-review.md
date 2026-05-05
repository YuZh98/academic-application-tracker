**Branch:** `feature/phase-7-cleanup-CL3-TestHelpers`
**Scope:** Phase 7 cleanup CL3 — extract 4 AppTest helpers from per-page test files into shared `tests/helpers.py` (lifted: `link_buttons` + `decode_mailto` from `tests/test_recommenders_page.py`; `download_buttons` + `download_button` from `tests/test_export_page.py`). Leading-underscore dropped on lift since the names become module-public. Optional 5 smoke tests in new `tests/test_helpers.py`.
**Stats:** 5 new tests; 870 → 875 passed (1 xfailed unchanged); +171 / −75 lines across 4 files; ruff clean; **pyright 0/0** (CL1 fence held); status-literal grep 0 lines; standing isolation gate empty; CI-mirror local check passes (875 + 1 xfailed); **`Tests + Lint (3.14)` CI conclusion: SUCCESS** (`mergeStateStatus: CLEAN`)
**Verdict:** Approve

---

## Executive Summary

CL3 lifts 4 AppTest helpers verbatim from per-page test files into
a new `tests/helpers.py` module. Pure refactor — every helper's
body is unchanged from the source location; the call sites in the
two consumer files (`test_recommenders_page.py` +
`test_export_page.py`) get a one-line import + a mechanical rename
(drop leading underscore on each helper name). The existing 114
tests across the two consumer files are the load-bearing
behavioural pin; CL3 adds 5 small smoke tests in
`tests/test_helpers.py` covering `decode_mailto` (the only helper
that's exercisable without a Streamlit AppTest fixture) plus an
import-compat check that all four names are callable post-lift.

The implementer's flagged design call — "paren-anchored rename
strategy (`_helper(` → `helper(`)" — is the right move and worth
preserving as a precedent. Without paren-anchoring, a naive
`_download_buttons` → `download_buttons` rename would have
clobbered substring matches in test method names like
`test_three_download_buttons_render` (which contains
`download_buttons` as a substring of the test name). Anchoring on
the trailing paren limits the rename to function-call sites only.
This is the same intuition that drives `re.sub(r'\bword\b', ...)`
patterns elsewhere — match the function, not the substring.

The lift is structurally clean: helpers go from page-test-private
(`_`-prefixed) to test-module-public; consumer files lose ~40
lines of duplicated helper definitions; the new
`tests/helpers.py` is 74 lines (4 functions + module docstring +
imports). Net delta is −31 lines via deduplication. CL1's pyright
fence held through the lift (0/0 post-CL3), confirming no type
drift in the rename.

All seven pre-merge gates green. CI conclusion SUCCESS verified
per the standing `c284c20` procedure (CI was already SUCCESS at
PR-creation time; mergeStateStatus CLEAN).

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `tests/helpers.py::download_button` return type | Function returns `UnknownElement` (per AppTest's typed-accessor-missing pattern) but the type annotation is implicit `Any` (no return type hint). Pyright basic mode accepts this since `at.get(...)` itself returns an iterable of UnknownElement; explicit `-> Any` would document intent. Cosmetic; doesn't affect correctness or coverage. | ℹ️ | Observation |
| 2 | `tests/test_helpers.py` smoke-test scope | Only `decode_mailto` is exercised in the new smoke tests — the three AppTest-dependent helpers (`link_buttons`, `download_buttons`, `download_button`) get only an import-compat smoke check (`assert callable(...)`). Implementer's framing is correct: behavioural coverage for those three is in the 114 existing consumer-file tests; duplicating it here would just create AppTest fixture overhead in a different file. | ℹ️ | Observation |

*No 🔴 / 🟠 / 🟡 / 🟢 findings.*

---

## Junior-Engineer Q&A

**Q1. The implementer flagged "paren-anchored rename strategy (`_helper(` → `helper(`)" as a design call. Why is the paren load-bearing?**

A. Without paren-anchoring, a naive sed/global-replace of
`_download_buttons` → `download_buttons` would clobber substring
matches in test method names. Concrete example:
`test_three_download_buttons_render` contains `download_buttons`
as a substring (`download_buttons_render` follows the helper name
in the test name) — a substring rename would corrupt the test
name into a mangled form, breaking pytest collection. Anchoring on
the trailing paren `_download_buttons(` limits the match to
function-call sites only. Test method names end in `:` (def line)
or are part of identifier strings (in error messages); they don't
include the call paren. The intuition is the same as `re.sub`'s
`\bword\b` word-boundary pattern: when you mean "the function" not
"the substring", you need a syntactic anchor that distinguishes
the two. Paren after the name is the simplest such anchor for
function-call sites in Python. Worth recording as a precedent for
future rename-on-lift refactors.

**Q2. The four lifted helpers drop their leading underscore on lift (`_link_buttons` → `link_buttons` etc.). Why is that the right call rather than keeping the underscore?**

A. The underscore in Python signals "module-private" — convention,
not enforcement. When the helper lived in
`tests/test_recommenders_page.py`, the underscore meant "this is
internal to this test file, not for other test files to import".
Once the helper lives in `tests/helpers.py` whose entire purpose
is "things other test files import", the underscore would be
inverted — the names ARE the public API of `tests/helpers.py`.
Keeping the underscore would mean every consumer writes
`from tests.helpers import _link_buttons` which reads wrong
(importing a private name from a sibling module is a code smell).
Dropping the underscore matches Python's stdlib convention: when
you lift a function from internal to shared, you also un-private
its name. Same pattern as moving a `_` helper from `_internal.py`
to `__init__.py`'s `__all__`.

**Q3. The smoke tests in `tests/test_helpers.py` only cover `decode_mailto`. Why isn't `link_buttons` / `download_buttons` covered with their own tests?**

A. Two reasons. (1) **Test cost-benefit**: testing
`link_buttons(at)` requires a live AppTest fixture, which means
either a fake page rendered just for the test or running one of
the existing pages headlessly. The existing consumer-file tests
already do exactly this — `TestT6ComposeButton` in
`test_recommenders_page.py` exercises `link_buttons` against the
real Recommenders page; `TestExportPageDownloadButtons` exercises
`download_buttons` + `download_button` against the real Export
page. Re-doing this in `test_helpers.py` against a synthetic page
would add coverage without adding signal — the same call paths
already run. (2) **`decode_mailto` is special**: it's the only
helper that's pure-logic (URL parsing, no AppTest needed). The
smoke tests there cover positive case (round-trip), URL-decoding
(special chars), missing-field defaults (no body / subject), and
the scheme-assertion safety net (rejects `https://` URLs). All
four shapes; ~15 lines of assertions. Testing what's testable
without overhead, leaving the AppTest-dependent behaviour to its
existing live coverage.

**Q4. The consumer files (`test_recommenders_page.py` +
`test_export_page.py`) had 114 tests using the old `_helper`
names. The PR diff is small (−75 / +171). How did 114 call sites
get renamed cleanly?**

A. The paren-anchored rename (Q1) handled it mechanically —
likely a sed or IDE find-replace with the `_helper(` → `helper(`
pattern across both files, followed by the import line addition
at the top. The diff is small because most lines just shifted by
one character (drop underscore); the deletion lines are the
~40-line helper definitions removed from each consumer file, and
the addition lines are the new `tests/helpers.py` module + the
two import lines + the 5 smoke tests. Net: 4 helpers × ~10 lines
each ≈ 40 lines duplicated → 74 lines centralized = +34 cohesion
gain at the cost of one new file. Each subsequent test that needs
these helpers gets them via import for free.

**Q5. The new `tests/helpers.py` imports `streamlit.testing.v1`
(for the `AppTest` type annotation). Doesn't that pull Streamlit
into every test that uses these helpers, even tests that don't
actually run AppTest?**

A. Streamlit is already a dev-dependency of the project (the page
files import it, the app runs on it, AppTest is part of the
Streamlit package). The import in `tests/helpers.py` is purely a
type-annotation source — `AppTest` is referenced in function
signatures (`def link_buttons(at: AppTest) -> list`) but the
helpers don't construct AppTest instances themselves. The runtime
cost is ~the same as any other module that imports Streamlit
(Python caches the import after first load), and the type-check
benefit is real: pyright can verify that callers pass an AppTest
instance, not e.g. a string or None. The alternative
(`def link_buttons(at: Any)`) would lose that type signal. Net:
import is correctly scoped, no runtime degradation, pyright
coverage preserved.

**Q6. The PR's diff `tests/test_export_page.py` has more deletion
lines than the lift accounted for — 44 lines deleted vs ~25 from
the helper bodies alone. What else got removed?**

A. The implementer also dropped the section-header comment block
that scoped the now-deleted helper definitions ("`# ── Phase 6 T5:
Download buttons ──`" plus the prose block above the helpers
explaining they're page-local). Once the helpers lift to
`tests/helpers.py`, that scoping comment becomes misleading — the
section ABOVE the test class no longer contains anything but the
comment itself. The implementer replaced it with a 4-line
breadcrumb pointing at the new location ("`download_buttons` +
`download_button` helpers live in tests/helpers.py..."), keeping
forward-discoverability without orphaned scope comments. Same
shape happened in `test_recommenders_page.py` for the
`link_buttons` + `decode_mailto` lift. Net: the deletion count is
helpers + their scope-comments; the addition count is helpers +
new home + breadcrumbs.

---

## Carry-overs

- **No new carry-overs introduced.** CL3 is a pure-refactor lift; behaviour preserved exactly.
- The `download_button` return type annotation (Finding #1) could be tightened from implicit-`Any` to explicit `-> Any` in a future cleanup chore; not blocking.

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-7-CL2` precedent. The seven pre-merge
gates were re-run on the PR head locally (`pr-43` / `ccd4ea6`) at
review time: ruff clean · **pyright 0 errors / 0 warnings / 0
informations** (CL1 fence held through the lift) · `pytest tests/
-q` 875 passed + 1 xfailed · `pytest -W
error::DeprecationWarning tests/ -q` 875 passed + 1 xfailed ·
status-literal grep 0 lines · standing isolation gate `git status
--porcelain exports/` empty · CI-mirror local check 875 + 1
xfailed with `postdoc.db` moved aside · `Tests + Lint (3.14)` CI
**conclusion: SUCCESS** (`mergeStateStatus: CLEAN`) verified per
the standing `c284c20` procedure._
