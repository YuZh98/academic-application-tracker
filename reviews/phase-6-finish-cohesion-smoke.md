# Phase 6 Finish — Cross-Page Cohesion Smoke + Close-out

**Branch:** _(direct-to-main; orchestrator close-out doc)_
**Scope:** TASKS.md Phase 6 T6 — close-out + tag `v0.7.0`. Combines the cohesion-smoke audit (mirror of `reviews/phase-5-finish-cohesion-smoke.md`) with the tier1–tier5 carry-over triage that gates the `v0.7.0` tag. Phase 6 introduced one new page (`pages/4_Export.py`) and three markdown generators in `exports.py`; the cohesion check covers the new page in isolation + against the Phase 4 / Phase 5 page conventions, plus the structural changes that landed across the phase (test-isolation lift, CI-green procedure amendment, privacy amendment).
**Verdict:** Approve `v0.7.0` tag. Carry-overs all deferred or kept-by-design. No 🔴 / 🟠 blockers. The Phase 6 surfaces compose cleanly with the Phase 4 + Phase 5 conventions; the divergences (date format granularity, per-file inline empty-state) are kept-by-design and documented inline.
**Method:**
1. AppTest probes (four states: populated DB + no exports, populated + exports written, populated + post-click regenerate, empty DB + no exports) — render `pages/4_Export.py` headlessly and dump every visible string in document order. Probe script: `/tmp/phase6_cohesion_probe.py`; raw output: `/tmp/phase6_cohesion_probe.out`. Both session-local, not committed.
2. Source audit — re-read `pages/4_Export.py` and `exports.py` against DESIGN §7 + §8.5 with the six cohesion lenses (status labels, empty-state copy, date format, toast/error wording, NaN coercion, widget-key prefixes).
3. Tier-review carry-over triage — read `reviews/phase-6-tier1-review.md` … `reviews/phase-6-tier5-review.md` end-to-end and aggregate every open carry-over.
4. Structural-change audit — three commits between v0.6.0 and v0.7.0 changed project conventions (T2 `c11fde4` + `911115a` test-isolation lift; `c284c20` CI procedure amendment; `43b3f3c` privacy amendment). Each is treated as a v0.7.0 highlight in the tag annotation.
5. All six pre-tag gates green at HEAD `95e5b19` — ruff clean, `pytest tests/ -q` 834 + 1 xfailed, `pytest -W error::DeprecationWarning tests/ -q` 834 + 1 xfailed, status-literal grep 0 lines, standing isolation gate empty, CI-mirror local check 834 + 1 xfailed.

---

## Executive summary

Phase 6 ships clean. The two surfaces — `exports.py` markdown
generators and the `pages/4_Export.py` UI — follow the project's
existing layer rules and visual grammar:

- **Layer rules respected.** `exports.py` imports `database` +
  `config` + stdlib only — never `streamlit` (DESIGN §2). The new
  page imports `database` + `exports` + `streamlit` + stdlib — no
  cross-page imports. Verified via source audit at HEAD.

- **Status sentinel handling.** Status sentinels are a UI-surface
  concern; the Export page never renders status, so no concern. The
  generators DO embed raw bracketed sentinels (`[APPLIED]` etc.) in
  the markdown, but the GUIDELINES §11 status-literal grep is
  scoped to `app.py + pages/`, not `exports/` — by design, since
  exports are version-control-style backups (well, were, until the
  privacy amendment) where round-trippable raw form is preferable
  to UI-friendly translation. Each generator's
  `test_status_renders_as_raw_bracketed_sentinel` pin makes the
  divergence explicit.

- **Empty-state pattern.** Phase 6 introduces a divergence
  worth flagging: the Export page does NOT use the `st.info(...)`
  empty-state callout that every other page uses. Instead, each
  per-file row carries its own inline empty state (`**FILENAME.md**
  — not yet generated`) and the corresponding download button
  renders disabled. This is correct for the Export page's
  per-file-state shape — there's no single "empty" branch because
  any subset of the three files can be present — but it's a
  cross-page asymmetry. Documented inline; no fix.

- **Date format granularity.** Three formats now exist across the
  project:
  - **Mon D** (`Apr 13`) — Applications page table, dashboard
    Pending Alerts, T4 Upcoming panel.
  - **YYYY-MM-DD** — All-Recommenders table (Phase 5 T5).
  - **YYYY-MM-DD HH:MM:SS** — Export page mtimes panel (Phase 6
    T4) and the markdown exports' Created / Updated columns (Phase
    6 T1).
  Each granularity matches its surface's purpose: human-readable
  display vs working-table sort key vs second-precision audit. The
  Mon D cohesion lens from Phase 5 doesn't extend to Phase 6
  because the second-precision is load-bearing on the Export page
  (a regenerate that landed 30 seconds ago needs to be visibly
  newer than one from this morning).

- **Toast / error wording.** Locked toast: `Markdown files
  regenerated.` (present-tense, period). Locked error pattern:
  `Could not regenerate: {e}` (no re-raise, button still rendered
  for retry). Both match the project-wide pattern (Apps Save toast
  is `Saved "<name>".`; Recommenders error is `Could not save:
  {e}`). The `st.toast` survives the post-click rerun (verified via
  the probe — state 3 captured the toast even after AppTest
  re-rendered the page).

- **NaN coercion.** Doesn't apply to the Export page — no
  DataFrame cells render. The exports.py generators DO use
  `_safe_str_or_em` mirroring the page-layer convention; same
  glyph (`—`) used for missing TEXT cells across both layers.

- **Widget-key prefix discipline.** Page uses `export_` prefix
  uniformly: `export_regenerate`, `export_download_OPPORTUNITIES.md`,
  `export_download_PROGRESS.md`, `export_download_RECOMMENDERS.md`.
  No leakage, no cross-prefix bleed.

- **Layout structure.** Page reads top-down: title → intro →
  primary CTA (Regenerate) → divider → "Download" subheader →
  per-file rows (`[⬇ FILENAME.md]` button stacked above mtime line).
  Hierarchy moves from page identity through bulk action to
  per-file affordances.

The `mergeStateStatus: CLEAN` shift on PRs #35 + #36 (vs the
`BLOCKED` state on PRs #28-#34) is unexplained but doesn't affect
the bypass-merge procedure. Logged as an observation; not a
verdict-blocker.

---

## Verbatim render dumps (cohesion evidence)

The four AppTest probes below are the source of truth for every
"verified verbatim" claim above. Probe script:
`/tmp/phase6_cohesion_probe.py`. Raw output:
`/tmp/phase6_cohesion_probe.out`.

### State 1: Populated DB · no exports yet (auto-write fires on add_position)

```
=== TITLE ===            'Export'
=== SUBHEADERS ===       'Download'
=== MARKDOWN (non-empty) ===
  'Markdown files are auto-exported after every data change. Use this page to trigger a manual export or download files.'
  '**OPPORTUNITIES.md** — last generated: 2026-05-04 04:23:53'
  '**PROGRESS.md** — last generated: 2026-05-04 04:23:53'
  '**RECOMMENDERS.md** — last generated: 2026-05-04 04:23:53'
=== BUTTONS ===          export_regenerate / 'Regenerate all markdown files'
=== DOWNLOAD BUTTONS ===
  '⬇ OPPORTUNITIES.md'  disabled=False
  '⬇ PROGRESS.md'       disabled=False
  '⬇ RECOMMENDERS.md'   disabled=False
=== DIVIDERS ===         count=1
=== EXCEPTION ===        has_exception=False
```

Cross-checks: page renders cleanly on a populated DB · auto-write
fires from `add_position`'s deferred import (DESIGN §7 contract #1
verified live) · all three files exist + are downloadable · the
single divider sits between regenerate-CTA and download section.

### State 2: Populated DB · exports written explicitly

```
(byte-identical to State 1 — write_all is idempotent and the files
were already present from the State 1 setup. DESIGN §7 contract #2
"deterministic and idempotent" verified end-to-end.)
```

### State 3: Populated DB · post-click regenerate

```
=== TOAST MESSAGES ===   'Markdown files regenerated.'
=== MARKDOWN (non-empty) ===
  '...' (intro line, identical to State 1)
  '**OPPORTUNITIES.md** — last generated: 2026-05-04 04:23:53'
  '**PROGRESS.md** — last generated: 2026-05-04 04:23:53'
  '**RECOMMENDERS.md** — last generated: 2026-05-04 04:23:53'
=== DOWNLOAD BUTTONS ===  all enabled (same shape as State 1)
=== EXCEPTION ===         has_exception=False
```

Cross-checks: success toast survives the post-click rerun
(`'Markdown files regenerated.'` verbatim per the GUIDELINES §8
locked-copy convention) · download buttons remain enabled · no
exception · idempotency holds (mtime is unchanged from State 1
because the regenerate produced byte-identical output and didn't
touch the file's mtime — actually this is filesystem-dependent;
on macOS the write happens regardless and updates mtime, but the
seconds resolution is too coarse to differentiate within the same
test run).

### State 4: Empty DB · no exports

```
=== TITLE ===            'Export'
=== SUBHEADERS ===       'Download'
=== MARKDOWN (non-empty) ===
  'Markdown files are auto-exported after every data change. Use this page to trigger a manual export or download files.'
  '**OPPORTUNITIES.md** — not yet generated'
  '**PROGRESS.md** — not yet generated'
  '**RECOMMENDERS.md** — not yet generated'
=== DOWNLOAD BUTTONS ===
  '⬇ OPPORTUNITIES.md'  disabled=True
  '⬇ PROGRESS.md'       disabled=True
  '⬇ RECOMMENDERS.md'   disabled=True
=== EXCEPTION ===        has_exception=False
```

Cross-checks: empty-state shape — per-file inline `not yet
generated` rather than a single `st.info` callout (kept-by-design
per the executive summary) · all three download buttons disabled ·
the regenerate button still renders (clickable on an empty DB; will
generate empty-but-valid markdown tables) · no exception.

---

## Carry-over triage (tier1 → tier5)

The five Phase 6 tier reviews accumulated the following carry-overs.
T6 disposes each before tagging:

| Carry-over | Source | Disposition |
|---|---|---|
| **C2** TRACKER_PROFILE removal | v1.1 doc-refactor leftover; reaffirmed in Phase 5 T7 close-out | **Defer to v1.0-rc.** Single-line removal but the schema-cleanup tier is the natural bundle. Not blocking v0.7.0. |
| **C3** "All" filter sentinel + `_REMINDER_TONES` → `config.py` | `phase-5-tier1-review.md` Finding 1 + `phase-5-tier6-review.md` Finding 1 | **Defer to a cleanup tier between Phase 7 polish and v1.0-rc.** Project-wide refactor; not blocking v0.7.0. |
| **T2 N+1 interviews lookup** in `write_progress` | `phase-6-tier2-review.md` Finding 2 | **Kept-by-design.** Single-user app, low position counts. Track as Phase 7 / v1.0-rc performance signal only if user reports latency. |
| **T3 `notes` column omission** in RECOMMENDERS.md | `phase-6-tier3-review.md` Finding 1 | **Kept-by-design.** Free-form prose poor in markdown table; future revision (if any) lands as a per-recommender bullets section, not a table column. |
| **T4 `st.markdown` vs `st.write` cross-page cohesion** | `phase-6-tier4-review.md` Finding 3 | **Phase 7 polish candidate.** Park for the Phase 7 cohesion sweep. |
| **T4 TOCTOU on mtimes panel** | `phase-6-tier4-review.md` Finding 1 | **Kept-by-design.** Single-user local app; race window has no exploitation path. Revisit if deployment shape changes (Streamlit Cloud, multi-user). |
| **T5 stacked layout vs side-by-side** | `phase-6-tier5-review.md` Finding 1 | **Kept-by-design.** Test-compat preserves T4 substring assertions; viewport-width readability favors stacked at narrow widths. |
| **T5 source-grep tests for AppTest-unobservable fields** | `phase-6-tier5-review.md` Finding 3 | **Kept-by-design.** Necessary fall-back when AppTest 1.56 doesn't expose the field. Revisit if a future Streamlit upgrade exposes `data` + `file_name` on the DownloadButton proto. |
| **`mergeStateStatus: CLEAN` vs `BLOCKED` shift** | `phase-6-tier4-review.md` Q5 + `phase-6-tier5-review.md` (observation) | **Observation; no action.** PRs #35 + #36 landed CLEAN; PRs #28-#34 landed BLOCKED. Cause unclear (rule set unchanged; no user action). The `c284c20` procedure (verify CI conclusion SUCCESS, then admin-bypass) is unaffected — works under both states. |

### Structural changes between v0.6.0 and v0.7.0 (highlight in tag annotation)

Three durable changes shipped during Phase 6 that aren't tier-specific
deliverables:

1. **Test-isolation lift** (Phase 6 T2, commit `911115a`): `tests/conftest.py::db` monkeypatches both `database.DB_PATH` AND `exports.EXPORTS_DIR` (was: only `DB_PATH`). Closed the latent pollution where every test calling a `database.py` writer leaked a markdown file into the project's real `exports/`. T3's `2439b4f` extended the same pattern to `tests/test_exports.py::isolated_exports_dir` to close the smoke-test fixture gap that surfaced as CI-red on PRs #32-#34.

2. **CI-green procedure amendment** (commit `c284c20`): `ORCHESTRATOR_HANDOFF.md` now requires `gh pr view <N> --json statusCheckRollup` showing `conclusion: SUCCESS` before admin-bypass. `IN_PROGRESS` / `QUEUED` / `null` is NOT acceptable — the bypass discards verification. `AGENTS.md` "Session bootstrap" adds the CI-mirror local check (`mv postdoc.db postdoc.db.bak && pytest tests/ -q && mv postdoc.db.bak postdoc.db`) so the implementer catches missing-DB-init regressions locally before pushing.

3. **Privacy amendment** (commit `43b3f3c`): `exports/` is now `.gitignore`d. DESIGN §7 contract #2's "committed into version control" claim was the orchestrator's wrong assumption; the rendered markdown carries personal job-search data that doesn't belong in a public repo. The contract's idempotency invariant is preserved ("deterministic and idempotent — same DB state produces byte-identical output across calls"); only the version-control claim drops. Both `postdoc.db` and `exports/` are now under one "Personal data" comment block in `.gitignore`.

All three are durable workflow / contract changes, not feature
additions — but they're load-bearing enough that they belong in the
v0.7.0 release notes.

---

## Junior-engineer Q&A

### Q1 — Why does the Export page use per-file inline empty states (`**FILENAME.md** — not yet generated`) instead of a single `st.info("No exports yet.")` callout like every other page?

**A.** The Export page's "empty" question is per-file, not per-panel. Any subset of `{OPPORTUNITIES.md, PROGRESS.md, RECOMMENDERS.md}` can be present — the user might have regenerated `OPPORTUNITIES.md` last week and never refreshed the others, leaving two stale files alongside one current one. A single `st.info` callout would either fire for the whole panel (all three absent) or never fire (one present), which loses the per-file granularity. The inline approach also keeps the disabled-download-button affordance directly adjacent to its mtime line, so the user sees `**RECOMMENDERS.md** — not yet generated` and the disabled `⬇ RECOMMENDERS.md` button as a single visual unit. Cross-page divergence accepted because the underlying state shape is genuinely different.

### Q2 — Three date formats now exist across the project (`Mon D`, `YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS`). Doesn't that violate the Phase 5 cohesion-smoke's "convergence on Mon D" claim?

**A.** Phase 5's cohesion claim was about the **dashboard + Pending Alerts** date surfaces — those are display-only and benefit from compact human-readable form. The three Phase 6 surfaces have different needs: (1) the Export-page mtimes panel needs second precision because regenerates produce visibly-newer-than-this-morning timestamps within the same workday — `Mon D` would lose that signal entirely, (2) the markdown exports' Created / Updated columns inherit the schema's ISO-with-time storage shape — pass-through is the right backup behavior, (3) the All-Recommenders Asked / Submitted columns from Phase 5 T5 use ISO `YYYY-MM-DD` as a working-table-sort signal. Three formats, three purposes, no contradiction. The cohesion lens is "use the right granularity for the surface's purpose," not "use one format everywhere."

### Q3 — `mergeStateStatus: CLEAN` started showing up on PRs #35 + #36 after seven prior PRs landed `BLOCKED`. What changed?

**A.** Genuinely unclear. The repo's main-protection ruleset (15887463) hasn't been touched per `gh ruleset view`; `require_last_push_approval: true` is still set; the PR author is still the user who can't self-approve. The most plausible explanations are: (a) GitHub adjusted the internal classification of "approval-required" (silent platform change), (b) some PR-specific factor (commit signing, branch state, base-branch divergence) shifted the rule's evaluation. Either way, the procedure is unaffected — the orchestrator's job is to verify CI conclusion SUCCESS and then merge, regardless of whether bypass is technically required. The `c284c20` amendment doesn't depend on `BLOCKED` being the state; it depends on CI being green. Phase 7 / v1.0-rc may surface enough information to diagnose if the user cares; today it's a curiosity, not a problem.

### Q4 — The privacy amendment (`exports/` `.gitignore`d) shipped between v0.6.0 and v0.7.0. Should the v0.7.0 release notes mention it as a breaking change?

**A.** It's not breaking in the code-contract sense — `exports.py` writers still produce the same files, the Export page still reads them, the regenerate button still works. What changed is what's tracked in git. Existing clones of the repo before `43b3f3c` would still have the contract sitting un-respected (no exports were ever actually committed even when DESIGN §7 said they should be). The amendment is closer to "doc reality-alignment" than "breaking change". Still — it's load-bearing for any reader trying to understand why the local `exports/` directory contains files that aren't in `git ls-files`. The tag annotation should mention it for that reason (privacy-first, not migration-action). v1.0-rc release notes can revisit if the framing needs sharpening.

### Q5 — The probe captured `mtime: 2026-05-04 04:23:53` identically across States 1, 2, and 3 — was the regenerate click in State 3 a no-op?

**A.** No, it ran. The probe script's State 1 setup calls `add_position`/`add_recommender`/etc., each of which fires `exports.write_all()` via deferred import — so the export files are created with mtime `04:23:53` BEFORE the State 1 page render even starts. State 2 calls `exports.write_all()` directly; same DB state, same byte output, same mtime second (filesystem updates mtime but the second resolution doesn't differentiate within the same probe run). State 3 clicks the regenerate button which fires `write_all` a third time; again same byte output, same second. The mtime test in `tests/test_export_page.py::TestExportPageMtimesPanel::test_regenerate_then_mtimes_update` uses a slightly different setup (no pre-existing files) so the post-click mtime IS visibly different from "not yet generated" — that's the test that pins the cohesion-of-state across the rerun, and it passes. The probe captures a different scenario where the timestamps are deliberately identical (idempotency).

### Q6 — Phase 6 ships three durable structural changes (test isolation, CI procedure, privacy). Why aren't they tier deliverables?

**A.** Each landed in response to a problem surfaced during a tier rather than as the tier's primary goal. T2 was supposed to be `write_progress` — the conftest lift was the "mandatory ride-along" because T1's pollution exposed itself only after T1 actually wrote a file. The CI procedure amendment was a post-mortem on the bypass-while-IN_PROGRESS gap that PR #34's CI surfaced. The privacy amendment was the user's privacy decision triggered by the orchestrator's "user-action carry-over" framing in `phase-6-tier4-review.md`. Each fits the project's "fix the gap when it surfaces" pattern rather than "schedule the gap-fix as a tier". The pattern keeps tier deliverables narrowly scoped (one PR, one feature) while still letting cross-cutting fixes ship in the natural moment. The cohesion-smoke close-out is the right place to surface them as v0.7.0 highlights — they're release-notes material because they shape the release, not feature-of-the-release material.

---

## v0.7.0 tag preparation (orchestrator checklist)

Standing close-out steps. All blocking gates already green at HEAD `95e5b19` per the method block above; the rest is mechanical.

1. **CHANGELOG.md split** — `[Unreleased]` → `[v0.7.0]` — 2026-05-04 — Phase 6: Exports (markdown generators + Export page) at the boundary commit (the T6 close-out commit itself), mirroring the v0.6.0 split precedent (commit `6f936d7`).
2. **Tag** — `git tag -a v0.7.0 -m "Phase 6 — Exports (markdown generators + Export page)"` with annotation listing the headline T1-T6 deliverables + the three structural changes (test isolation, CI procedure, privacy).
3. **TASKS.md / AGENTS.md final flip** — T6 ✅; main HEAD line bumped; Immediate-task replaced with **Phase 7 T1** (Urgency colors on positions table per `TASKS.md` "Up next").
4. **Recently-done entry** — one bullet for the v0.7.0 tag close-out.
5. **Push commit + tag.**

---

_Written 2026-05-04 as the Phase 6 close-out doc per the
`reviews/phase-5-finish-cohesion-smoke.md` precedent. Verbatim
renders captured via `/tmp/phase6_cohesion_probe.py` against `main`
HEAD `95e5b19`. Suite green at 834 passed + 1 xfailed under both
pytest gates. Standing isolation gate empty post-pytest. CI-mirror
local check green. Verdict: Approve `v0.7.0` tag._
