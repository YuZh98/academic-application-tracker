**Branch:** `feature/phase-7-cleanup-CL1-PyrightCI`
**Scope:** Phase 7 cleanup CL1 — pyright type-check fence in CI + drift cleanup. New `pyproject.toml` `[tool.pyright]` block (basic mode, pythonVersion 3.14, explicit include/exclude), pinned `pyright==1.1.409` in `requirements-dev.txt`, new `Pyright type-check` step in `.github/workflows/ci.yml` between Ruff and Pytest, `pyright .` row added to both AGENTS.md and GUIDELINES.md pre-commit checklists. **45 type-drift errors → 0** across 5 files (`tests/test_app_page.py`, `exports.py`, `pages/1_Opportunities.py`, `pages/2_Applications.py`, `pages/3_Recommenders.py`).
**Stats:** 0 net test count change (864 → 864 passed, 1 xfailed unchanged); +197 / −45 lines across 10 files; ruff clean; **pyright 0/0**; status-literal grep 0 lines; standing isolation gate empty; CI-mirror local check passes (864 + 1 xfailed); **`Tests + Lint (3.14)` CI conclusion: SUCCESS**
**Verdict:** Approve

---

## Executive Summary

CL1 lands the type-check fence postponed since PR #22. Six commits
on the branch: one `chore:` adding the CI step + config + dev-dep
pin + checklist updates, plus five `fix:` commits (one per source
file with errors) closing the 45-error drift that accumulated
since PR #22 fixed the original sweep but didn't enforce
ongoing-cleanliness.

The fence shape:

- **Tool:** `pyright==1.1.409` pinned in `requirements-dev.txt`.
  Project precedent (PR #22 used pyright); fast; matches the
  prior cleanup's working point.
- **Config:** `pyproject.toml` `[tool.pyright]` block —
  `pythonVersion = "3.14"`, `typeCheckingMode = "basic"`,
  explicit `include` + `exclude` lists. Strict mode would require
  widespread additional annotations and was deliberately scoped
  out (matching PR #22's "basic" working point).
- **CI integration:** new `Pyright type-check` step in the
  existing `Tests + Lint (3.14)` job, placed between Ruff lint
  and Pytest. Same Python 3.14 environment; `pip install -r
  requirements-dev.txt` already runs earlier in the job, so no
  separate setup-pyright action needed.
- **Pre-commit checklists:** `pyright .` row added to both
  AGENTS.md "Pre-commit checklist" + GUIDELINES.md §11
  "Pre-commit checklist". GUIDELINES bumps the CI re-run count
  from "first three" to "first four".

The 45-error drift cleanup follows PR #22's precedent patterns
exactly:

- **`Any`-typed locals for `iterrows` cells** — pandas-stubs types
  `iterrows` cells as `Series | ndarray | Any` union, which
  pyright basic mode rejects when fed to `int()` / `str()`. Fix:
  intermediate `pid_raw: Any = row["position_id"]` then
  `int(pid_raw)`. Mirrors `exports.py::write_progress`'s existing
  pattern from earlier in the project.
- **`# type: ignore[call-overload]` on the pandas `rename`** — the
  `rename` overload-resolution churn between pandas-stubs versions
  has surfaced before; ignoring at the call site with the explicit
  error code is the documented escape hatch (mirrors PR #22's same
  approach).
- **`is not None` guards for AppTest helpers** — `at.button(key=...)`
  returns `Button | None` in pyright's view; project tests assume
  the lookup succeeds, so guards land at every call site.
- **`cast(pd.DataFrame, ...)`** — pandas-stubs occasionally types
  `df[mask]` as `DataFrame | Series | Scalar`; cast narrows when
  the runtime guarantee is "always DataFrame here".

All 45 fixes are runtime no-ops (verified via `pytest tests/ -q`
delta: 864 → 864). The fence value is what matters going forward —
every CL2-CL5 PR (and onward) gets free type-check coverage.

All seven pre-merge gates green. CI conclusion SUCCESS verified
per the standing `c284c20` procedure.

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `pyproject.toml` `[tool.pyright]` `exclude` | Includes `"exports"` even though `.gitignore` already excludes the directory and a fresh CI clone has no `exports/` checkout. Defensive; harmless. The pre-existing comment block addresses this — "a fresh CI clone may still see stub directories in some setups". | ℹ️ | Observation |
| 2 | `requirements-dev.txt` `pyright==1.1.409` pin | Hard pin on a single version. Pyright ships frequent point releases; the pin guarantees CI + local stay byte-identical, but means dependabot won't auto-bump. Tradeoff favors determinism; renovation is a future cleanup chore. | ℹ️ | Observation |

*No 🔴 / 🟠 / 🟡 / 🟢 findings.*

---

## Junior-Engineer Q&A

**Q1. The drift was "45 errors → 0" — but PR #22 cleaned everything to 0 originally. What surfaced 45 new errors between PR #22 and now?**

A. Three accretion sources, in roughly decreasing order of contribution. (1) **Phase 5 / Phase 6 / Phase 7 feature code added to surfaces PR #22 didn't touch**: the Recommenders page (Phase 5 T4–T6), the Export page (Phase 6 T4–T5), the search bar + urgency glyph (Phase 7 T1–T2), and the new cohesion-test file (Phase 7 T3+T4). Every new function had to satisfy pyright basic mode from scratch; without the fence, drift went unnoticed. (2) **Phase 7 T1's `Any`-widening of `_deadline_urgency`** — implementer flagged this in the T1 review; pyright basic mode is happy with `Any`, but downstream pandas `.apply()` call sites needed type-narrowing fixes. (3) **AppTest helper accretion** — the T6 LLM-prompts test, T5 download-button helpers, and T4 confirm-dialog AST helpers all introduced new `at.get('...')` / `proto.<field>` accesses. Pyright sees `UnknownElement` returns and flags the protobuf attribute reads. The fixes are mechanical (`# type: ignore` or `is not None` guards) but the count adds up. The implementer's per-file commit split (5 commits, one per file) makes the per-error attribution traceable.

**Q2. Why `typeCheckingMode = "basic"` rather than `"strict"`?**

A. PR #22's working point was basic mode — strict would require widespread additional annotations (return types on every helper, explicit `dict[str, Any]` instead of bare `dict`, etc.) that are out of scope for a fence-establishment PR. The CL1 spec explicitly called this out: "matches PR #22's working point — strict would require widespread additional annotations and is out of scope here". A future "tighten to strict" PR is defensible if the project ever wants more aggressive type coverage; today the fence catches the regressions that matter (None access, type confusion, undefined attributes) without forcing decorative annotations. The basic mode also matches what most Python projects ship — strict is a sharp tool for libraries with public API contracts, not for a single-user app's UI layer.

**Q3. The implementer pinned `pyright==1.1.409` exactly. Doesn't that block dependabot's auto-renovation?**

A. It does, by design. Pyright's basic-mode behaviour shifts subtly between point releases — a version that flags zero errors today might flag five next month (or vice versa) as the type-stub data shifts. Pinning to `1.1.409` guarantees CI + every developer's local environment evaluate the same rule set; an auto-bump that flagged a new error mid-tier would block an unrelated PR's merge until someone fixed the new errors. The pin is the same reasoning that drives `pytest==9.0.3` + `ruff==0.15.12` pins one line above — deterministic CI is more valuable than auto-rolling versions for tools that gate merges. A future "renovation tier" can do a controlled bump (read changelog, fix new errors in one PR, bump pin to latest); without an explicit moment to do that, the pin holds.

**Q4. The drift surfaced primarily because Phase 5–7 features added new code that PR #22 couldn't have covered. Doesn't that mean per-PR pyright would have been better than waiting until now?**

A. Yes — and that's exactly the lesson. The fence shipping at CL1 instead of as part of PR #22's follow-up was the gap; once it exists, every subsequent PR (CL2 onward) catches drift at PR-review time rather than batched. The CL1 outcome (45 errors fixed in one tier) would have been ~5 errors per merged PR caught during review of the original feature work — much easier to triage in context, harder to compound. The cleanup-tier framing here is "we shipped without the fence for two phases; pay the bill now". Going forward, the orchestrator's six-gate local check + CI's seven-gate run both include pyright; new drift surfaces inline.

**Q5. The implementer split fixes across 5 file-scoped commits. Why not one mega-fix commit?**

A. Per-file commits give per-error attribution that survives `git blame` + `git log -p`. A future engineer reading "why does `pages/1_Opportunities.py` have a `# type: ignore[call-overload]` on the pandas `rename` call?" can `git log -1 --follow` that line and land on the CL1 fix commit with the rationale in the commit body, not on a mega-commit that touches 5 files at once. Same intuition that drove Phase 5 + Phase 6 to ship one tier per PR rather than batching. Cost: 5 commits in one PR is more to scan than 1; benefit: each fix's reason is explicit in its own commit. The PR's `chore:` commit (the fence + config) sits cleanly above the 5 fix commits — reviewers can read the fence first, then the per-file fixes, in dependency order.

**Q6. The local pyright run printed `0 errors, 0 warnings, 0 informations` after CL1's fixes. The CI also reported SUCCESS. Should we trust both equally?**

A. They run the same `pyright .` invocation against the same `pyproject.toml` config + the same pinned pyright version, so equivalence is structural — local and CI evaluate the identical rule set against the identical code. The only divergence vector is the type-stub data shipped with pyright itself (mostly bundled but some pandas-stubs come from `pip install`); the `pip install -r requirements-dev.txt` step on CI mirrors the local `.venv` exactly because the dev-deps are pinned. Functionally: the local run is the early-warning signal during PR work; the CI run is the merge gate. CL1's outcome shows both agree at zero — that's the contract the fence is supposed to enforce. Going forward, any divergence between local and CI pyright would itself be a regression worth investigating.

---

## Carry-overs

- **Pyright pin renovation** — at some point a controlled bump from `1.1.409` to whatever's current makes sense (read changelog, fix any new errors in one PR, bump). Not blocking; track for v1.0-rc or a future cleanup chore.
- **Strict mode upgrade** — defensible if the project ever wants more aggressive type coverage. Not in scope for CL1; would be its own tier.

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-7-tier4` precedent. The seven pre-merge
gates were re-run on the PR head locally (`pr-41` / `1ea52d7`) at
review time: ruff clean · **pyright 0 errors / 0 warnings / 0
informations** · `pytest tests/ -q` 864 passed + 1 xfailed ·
`pytest -W error::DeprecationWarning tests/ -q` 864 passed + 1
xfailed · status-literal grep 0 lines · standing isolation gate
`git status --porcelain exports/` empty · CI-mirror local check
864 + 1 xfailed with `postdoc.db` moved aside · `Tests + Lint
(3.14)` CI **conclusion: SUCCESS** verified via `gh pr checks 41
--watch` + `gh pr view 41 --json statusCheckRollup --jq '...'`
per the standing `c284c20` procedure._
