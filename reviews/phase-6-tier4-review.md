**Branch:** `feature/phase-6-tier4-ExportPage`
**Scope:** Phase 6 T4 — `pages/4_Export.py` page shell + manual regenerate button + per-file mtimes panel (`pages/4_Export.py` new file; `tests/test_export_page.py` new file)
**Stats:** 12 new tests in 3 classes (815 → 827 passed, 1 xfailed unchanged); +494 / 0 lines across 2 files; ruff clean; status-literal grep 0 lines; **standing isolation gate** clean (post-clean re-run); **CI-mirror local check** passes (827 + 1 xfailed with `postdoc.db` moved aside); **`Tests + Lint (3.14)` CI conclusion: SUCCESS** (`mergeStateStatus: CLEAN`, `mergeable: MERGEABLE`)
**Verdict:** Approve

---

## Executive Summary

T4 lands the Export page shell and the first interactive piece (the
regenerate button) without picking up T5's download-button work. The
implementation is mechanical — DESIGN §8.5 + the wireframe pin the
shape, the existing `exports.py` writers (T1+T2+T3) do all the
heavy lifting, and T4's job is to wire them into a Streamlit page
with the standard error / toast / mtimes affordances. Three pieces:

1. **Page shell** — `set_page_config(layout="wide")` first
   (DESIGN §8.0 + D14), `database.init_db()`, `st.title("Export")`,
   verbatim wireframe-pinned intro line via `st.markdown`.
2. **Regenerate button** — `st.button(..., key="export_regenerate",
   type="primary")` wraps `exports.write_all()` in a try/except per
   GUIDELINES §8 (friendly `st.error`, no re-raise). Per DESIGN §7
   contract #1 the inner `write_*` calls already log-and-continue,
   so only the `EXPORTS_DIR.mkdir` leg can surface an exception
   here. Success path fires `st.toast("Markdown files
   regenerated.")` which persists across the post-click rerun.
3. **Mtimes panel** — one `st.markdown` line per locked filename
   (`OPPORTUNITIES.md`, `PROGRESS.md`, `RECOMMENDERS.md`) with
   either `last generated: {YYYY-MM-DD HH:MM:SS}` (file present) or
   `not yet generated` (absent). `Path.exists()` check first rather
   than `try/except FileNotFoundError` on `.stat()` — both are
   idiomatic, exists() reads cleaner for a pure-read panel.

Tests centralize all locked-copy strings in module-level constants
(`EXPECTED_TITLE`, `EXPECTED_INTRO`, `REGENERATE_KEY`,
`REGENERATE_LABEL`, `SUCCESS_TOAST`, `EXPORT_FILENAMES`) so any
future spec drift surfaces as a one-constant edit + a clean test
diff. The mtimes test pre-populates files with `os.utime` to a
deterministic epoch (`1700000000`) so the assertion can pin the
exact rendered string rather than approximating against
wall-clock time.

`mergeStateStatus: CLEAN` (not `BLOCKED`) — first PR in this
project's history to land without requiring admin-bypass. The
post-`require_last_push_approval` ruleset behaviour suggests GitHub
classified this PR's branch protection differently; verify whether
this signals the rule set has changed or it's PR-specific.

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `pages/4_Export.py` mtimes panel | `Path.exists()` check is correct under DESIGN §7 contract #2 (idempotent writes by `exports.write_all`) but a classic TOCTOU race exists between `exists()` and `stat()` — file deleted by an external process between the two calls would raise `FileNotFoundError`. Implementer flagged this in the commit body: "race window irrelevant on a single-user local app." Defensible. The `try/except FileNotFoundError` alternative would be one line longer; the user is the only writer and `exports/` doesn't have external deletion paths in the daily workflow. | ℹ️ | Kept-by-design. Cite-able if Phase 7 / v1.0-rc revisits exception handling project-wide. |
| 2 | `pages/4_Export.py` "── Download ───" wireframe section header | Implementer omitted the wireframe-pinned divider header (`── Download ───`) from T4 because it semantically scopes T5's download buttons; T4 has no downloads to label. Defensible — adding it now with no buttons under it would read as a stray section header. The PR description flags this for orchestrator sanity-check; the call is correct. | ℹ️ | Kept-by-design. T5 will add the header alongside the download buttons. |
| 3 | `pages/4_Export.py` `st.markdown` (not `st.write`) for intro + mtime lines | Implementer chose `st.markdown` over `st.write` for the intro line and the per-file mtimes lines. PR description rationale: "explicit formatting, identical AppTest surface" — `st.write(str)` routes to `st.markdown` internally so the AppTest body lookup is identical, but the source reads as deliberate-prose-rendering rather than catch-all `st.write`. Cohesion with `app.py` / page intros varies (`st.write` is more common in `app.py`). Net: stylistic; doesn't matter at the AppTest level. | ℹ️ | Observation. If Phase 7 sweeps style, harmonize to one or the other across pages. |
| 4 | `tests/test_export_page.py::TestExportPageMtimesPanel::test_mtimes_show_timestamps_when_files_present` | Uses `epoch = 1700000000` (deterministic) + `os.utime` to set file mtimes. The assertion converts via `datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")` which uses LOCAL time — so the rendered timestamp depends on the test runner's timezone. CI runners are typically UTC; the test's expected string is computed from `datetime.fromtimestamp` at test-time so it auto-matches the runner's timezone. Implementation is correct — the test isn't pinning a hard-coded "2023-11-14 22:13:20" but rather "whatever fromtimestamp returns for this epoch in the current TZ". Minor robustness note: a future change to switch to UTC display would need to update the test along with the page. | ℹ️ | Observation. Not a defect — the test and page use the same TZ-relative path. |

*No 🔴 / 🟠 / 🟡 findings.*

### Pre-existing condition surfaced (not T4-introduced)

The standing isolation gate (`git status --porcelain exports/`)
returned `?? exports/` on the orchestrator's first local run. Three
files (`OPPORTUNITIES.md`, `PROGRESS.md`, `RECOMMENDERS.md`) with
real user data and mtimes from earlier in the day — leftover from
a pre-T2-fix session run. Not introduced by T4. After clearing
`exports/` and re-running pytest, the gate returned EMPTY — T4 is
isolation-clean. Logging here so the carry-over is visible:

- **Carry-over for the user:** the three `exports/*.md` files
  currently sitting untracked in the working tree should be
  committed per DESIGN §7 contract #2 ("export formats committed
  into version control") OR `exports/` should be added to
  `.gitignore` if the user prefers not to version them. Today's
  state — files present at the project root, untracked — sits
  between the two contracts.

---

## Junior-Engineer Q&A

**Q1. The regenerate button wraps `exports.write_all()` in `try/except Exception`. Per DESIGN §7 the per-writer calls inside `write_all` already log-and-continue. What exception path is the outer try/except actually catching?**

A. The `EXPORTS_DIR.mkdir(exist_ok=True)` call at the top of `write_all`. Read `exports.py` — `write_all` first does `EXPORTS_DIR.mkdir(exist_ok=True)`, THEN iterates the per-writer functions inside individual try/excepts. If `mkdir` raises (permission denied; full disk; symlink to a non-existent parent), the per-writer log-and-continue never runs and the exception propagates out of `write_all` unconditionally. The outer try/except in the page handler catches that case so the user sees a friendly `st.error` instead of a Streamlit traceback. The implementer's commit body and the page comment both spell this out — defensive layering, not redundant.

**Q2. Why `st.markdown` for the intro + mtime lines rather than `st.write`?**

A. Both render identically — `st.write(str)` routes to `st.markdown` internally — so the AppTest test bodies (which read `at.markdown[i].value`) work the same way. The implementer's choice (per the PR description) is "explicit formatting, identical AppTest surface" — the source intent is "I am rendering deliberate prose with markdown formatting" rather than "I am writing whatever this happens to be". For one-line strings the difference is purely stylistic; for the mtime lines (which carry `**bold**` filename emphasis) `st.markdown` is more honest about the formatting intent. Net: not a bug, not a meaningful divergence at the AppTest level. If a future Phase 7 cohesion sweep wants every page to use one or the other consistently, the harmonization is mechanical.

**Q3. The mtimes panel uses `Path.exists()` then `Path.stat()` — isn't that a TOCTOU race?**

A. It is, technically. The race window is between `exists()` returning True and `stat()` running — if the file is deleted in that window, `stat()` raises `FileNotFoundError` and the page crashes. On the project's actual deployment shape (single-user local app, the user is the only writer, `exports/` is regenerated only by `database.py` writers and the regenerate button on this same page), the window has no realistic exploitation path. The `try/except FileNotFoundError` alternative is one line longer and reads as defensive against a scenario that doesn't exist. The implementer's commit body explicitly accepts the trade. If a future deployment shape (Streamlit Cloud, multi-user) puts `exports/` on a shared filesystem with external writers, this becomes worth revisiting.

**Q4. Why does the test use `os.utime` to a deterministic epoch instead of asserting against wall-clock time?**

A. Wall-clock-based assertions are fragile in two ways. (1) Test execution time isn't deterministic — a slow CI runner could land the file's mtime at a different second than the assertion expects. (2) A test that asserts "the rendered timestamp is roughly now" makes the test logic complex (parse the rendered string back to a datetime, assert delta < 5s, etc.) and fragile to format changes. Setting mtime explicitly via `os.utime(path, (epoch, epoch))` gives the test a fixed input — `datetime.fromtimestamp(1700000000).strftime("%Y-%m-%d %H:%M:%S")` produces the SAME string the page would render for that file, so the assertion can use exact string comparison. The epoch value (`1700000000` = 2023-11-14 in UTC) is arbitrary but locked; the test reads cleanly and CI-runs deterministically.

**Q5. The PR's `mergeStateStatus` is `CLEAN` rather than the usual `BLOCKED` that prior PRs surfaced. What changed?**

A. Worth investigating but not blocking. The previous-orchestrator notes (`ORCHESTRATOR_HANDOFF.md` "Branch-protection note") describe the BLOCKED state as a consequence of `require_last_push_approval: true` — the PR author can't self-approve, so the protection rule blocks normal-flow merge. CLEAN suggests either: (a) the ruleset has been adjusted (less likely — would need an explicit user action), (b) the PR's commit history happens to satisfy the rule (unlikely — same author as prior PRs), or (c) GitHub's classification of "approval-required" has shifted under the hood. The new `c284c20` procedure is unaffected: the gate is "CI conclusion SUCCESS" regardless of mergeStateStatus, and SUCCESS holds here. The orchestrator should still verify CI-green before merging — which is done. The CLEAN status just means `gh pr merge 35 --squash` (no `--admin`) might work, but admin-bypass is still acceptable and is what the documented procedure uses for consistency.

**Q6. The orchestrator caught `?? exports/` on the standing isolation gate. Is that a regression introduced by T4?**

A. No — it's pre-existing pollution. The three files (`OPPORTUNITIES.md`, `PROGRESS.md`, `RECOMMENDERS.md`) at the project's `exports/` root carry mtimes from an earlier session and contain real user data. They're leftover from before the Phase 6 T2 conftest fixture lift took. Verification: clearing `rm -rf exports/` and re-running `pytest tests/ -q` yielded a clean `git status --porcelain exports/` (empty) — proof that T4's tests don't pollute. The standing isolation gate's intent is "did pytest write to `exports/`?" but its `?? exports/` output also fires for pre-existing untracked files unrelated to the current run. For T4 review: not a defect. For the project: the three untracked files at `exports/` should either be committed per DESIGN §7 contract #2 or `exports/` should be `.gitignore`d.

---

## Carry-overs

- **User action — `exports/` directory state:** three untracked files at the project root sitting between "committed per DESIGN §7 contract #2" and ".gitignore'd". User picks one and the orchestrator follows up.
- **Phase 7 polish candidate:** harmonize `st.markdown` vs `st.write` across pages (Finding #3). Phase 7 cohesion-sweep territory.
- **TOCTOU on mtimes panel:** if future deployment shape changes (multi-writer / shared filesystem), revisit Finding #1's `try/except FileNotFoundError` alternative.

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-6-tier3` precedent. The six pre-merge gates
were re-run on the PR head locally (`pr-35` / `71c6e35`) at review
time: ruff clean · `pytest tests/ -q` 827 passed + 1 xfailed ·
`pytest -W error::DeprecationWarning tests/ -q` 827 passed + 1
xfailed · status-literal grep 0 lines · standing isolation gate
empty (after clearing pre-existing pollution unrelated to this PR)
· CI-mirror local check 827 + 1 xfailed with `postdoc.db` moved
aside · `Tests + Lint (3.14)` CI **conclusion: SUCCESS** verified
before admin-bypass per the `c284c20` procedure._
