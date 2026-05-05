# Phase 7 Finish — Cross-Page Cohesion Smoke + Close-out

**Branch:** _(direct-to-main; orchestrator close-out doc)_
**Scope:** TASKS.md Phase 7 T6 — close-out + tag `v0.8.0`. Combines the cohesion survey (mirror of `reviews/phase-6-finish-cohesion-smoke.md`) with the T1-T4 + CL1-CL6 carry-over triage that gates the `v0.8.0` tag. Phase 7 introduced no new pages; surface work was UX polish (urgency glyphs, search bar, confirm-dialog audit, save-toast wording) on existing pages plus a six-changelist cleanup sub-tier (CL1 pyright fence, CL2 `config.py` lifts, CL3 `tests/helpers.py` extraction, CL4 four batched UX fixes, CL5 doc-drift sweep, CL6 process + retroactive doc trim).
**Verdict:** Approve `v0.8.0` tag. All carry-overs deferred or kept-by-design. T5 (responsive layout) explicitly skipped — no Chrome DevTools MCP available; deferred to v1.0-rc as user-driven manual capture. The Phase 7 surfaces compose cleanly with Phase 4 / Phase 5 / Phase 6 conventions; Phase 7's contribution is convergence, not divergence.
**Method:**
1. Source survey via parallel Explore-agent audit — 6 cohesion lenses (urgency glyph routing, `set_page_config` first-statement, confirm-dialog gating, save-toast wording, empty-state copy, `config.py` lifts consumed). Survey report logged in pre-tag audit transcript.
2. `tests/test_pages_cohesion.py` two pinning suites — `TestSetPageConfigSweep` (10 parametrized tests, AST walk + locked-kwargs source-grep across all 5 pages) and `TestConfirmDialogAudit` (11 tests across 3 destructive paths) — provide the durable structural pin; the cohesion claims here are not narrative-only but test-enforced.
3. Tier-review carry-over triage — read `reviews/phase-7-tier1-review.md` … `reviews/phase-7-CL5-review.md` end-to-end + `reviews/phase-6-tier4-review.md` cross-references; aggregate every open carry-over.
4. Pre-tag comprehensive audit (8 parallel Explore agents) covered DESIGN drift, GUIDELINES drift, TASKS vs reality, CHANGELOG completeness, AGENTS currency, reviews/README index, cross-doc references, Phase 7 cohesion. 5 🟡 nits surfaced + closed in CL6c (`079564b`) before this close-out.
5. All seven pre-tag gates green at HEAD `079564b` — ruff clean, `pytest tests/ -q` 879 passed + 1 xfailed, `pytest -W error::DeprecationWarning tests/ -q` same, status-literal grep 0 lines, standing isolation gate empty, CI-mirror local check 879 + 1 xfailed, pyright `0 errors, 0 warnings, 0 informations`. CI conclusion SUCCESS verified on every CL1-CL6 push.

---

## Executive summary

Phase 7 ships clean. The phase's contribution is **cross-page
convergence** — it took three pages of inconsistent micro-state
(urgency rendering, page-config calls, save-toast wording, magic
literals) and routed them through shared `config.py` lifts,
shared `tests/helpers.py`, and explicit cohesion-pinning tests.
The seven pre-tag gates green; pyright fence (added CL1) holds
through every refactor PR that followed (4 consecutive 0/0
runs across CL2-CL5 + CL6 doc work). The `tests/test_pages_cohesion.py`
file (T3 + T4) is the durable structural pin: any future page-
authoring drift on `set_page_config` or `@st.dialog` gating will
fail tests rather than silently land.

Six cohesion areas verified uniform:

- **Urgency glyph routing.** `config.urgency_glyph(days_away: int | None) -> str` (lifted in CL2 PR#42) is the single source of truth. Call sites verified at `pages/1_Opportunities.py::_deadline_urgency` (delegates to `config.urgency_glyph`), `database.py::get_upcoming_deadlines` + `get_upcoming_interviews` (`Series.apply(config.urgency_glyph)`), and `app.py` (uses `config.EM_DASH` for NULL-deadline / no-upcoming-date paths). No hardcoded `🔴` / `🟡` / `—` literals remain.
- **`set_page_config` first-statement.** All five Streamlit entry points (`app.py` + `pages/1_Opportunities.py` + `pages/2_Applications.py` + `pages/3_Recommenders.py` + `pages/4_Export.py`) call `st.set_page_config(page_title="Postdoc Tracker", page_icon="📋", layout="wide")` as the first non-import Streamlit statement. Pinned by `TestSetPageConfigSweep` (10 parametrized tests; AST walk + locked-kwargs source-grep). T3 PR#39 added the test; audit confirmed all 5 pages already conformed (verification-only).
- **Confirm-dialog cohesion.** Every `database.delete_*` call site is wrapped in an `@st.dialog`-decorated function with a Confirm + Cancel button row, an irreversibility cue, an enumerated cascade-effect description, and a failure path that preserves the dialog sentinels for retry. Pinned by `TestConfirmDialogAudit` (11 tests). The audit surfaced + fixed one real bug: position-delete dialog warning text was missing "interview" from the FK cascade enumeration (fixed in CL4 PR#40 alongside the test).
- **Save-toast wording on dirty diff.** Three forms (`apps_detail_form` + per-row `apps_interview_{id}_form` + `recs_edit_form`) compute a per-field dirty diff against the persisted row before writing. No-op clicks fire `st.toast("No changes to save.")` instead of the misleading `Saved "<name>".`. apps_detail_form's no-op path also skips the R1/R3 cascade (pinned by spy test). CL4 PR#44 shipped the dirty-diff infrastructure; CL5 PR#45 swept the doc-drift comments left behind.
- **Empty-state copy lifted.** Five `config.py` constants (`EMPTY_FILTERED_POSITIONS`, `EMPTY_NO_POSITIONS`, `EMPTY_FILTERED_APPLICATIONS`, `EMPTY_PENDING_RECOMMENDERS`, `EMPTY_PENDING_RECOMMENDER_FOLLOWUPS`) consumed verbatim by their respective surfaces; per-page tests assert against the constants by name (so any future copy edit on the constant cascades into the test). No hardcoded empty-state strings remain at the surface layer.
- **`config.py` lifts consumed.** Four lifts from CL2 PR#42 — `EM_DASH`, `urgency_glyph`, `FILTER_ALL`, `REMINDER_TONES` — all imported and used at every site that previously carried a duplicate. Audit confirmed zero remaining magic literals where lifts apply.

The pyright fence (CL1 PR#41) deserves its own line. Before
CL1, 45 type-drift errors had accumulated since PR #22. CL1
resolved all 45 (every fix a runtime no-op; six commits on the
branch for per-line `git blame`) and added a CI step that holds
the line. Across the four refactor PRs that followed (CL2 + CL3
+ CL4 + CL5), pyright stayed 0/0 — proof that the fence catches
new drift at PR boundary rather than letting it accumulate. The
fence is the closest thing this project has to a "type contract"
and is what makes the rest of Phase 7's refactors safe.

---

## T5 deferral — responsive layout check

T5 ("responsive layout check at 1024 / 1280 / 1440 / 1680
widths; capture screenshots to `docs/ui/screenshots/v0.8.0/`")
was originally scoped between CL6 and T6. The deferral
rationale:

1. **Tooling not available.** Chrome DevTools MCP is the natural automation surface for this work — set viewport, navigate to each `streamlit run` page, capture full-page screenshot, repeat across widths. The current Claude Code environment has no browser-automation MCP installed (Gmail / Calendar / Drive / Mem / Notion / PDF Viewer / Context7 are the configured MCPs; none are browser).
2. **Fully manual is heavy.** The fall-back is the user driving Streamlit locally + resizing Chrome DevTools device toolbar + capturing 5 pages × 4 widths = 20+ PNGs. That's not blocking on the orchestrator; it's blocking on the user's calendar.
3. **Phase 7's wins land without T5.** T1-T4 + CL1-CL6 are independent of layout-width verification. Tagging `v0.8.0` without T5 ships the convergence work (which has durable test pins) and leaves layout verification as a v1.0-rc deliverable where it composes naturally with the publish-scaffolding tier (`README.md` screenshots, deploy verification).

Tag `v0.8.0` is therefore Phase 7 **without T5**. The roadmap
keeps T5 as an outstanding item against v1.0-rc; if the user
wants to land it earlier, the orchestrator can spec a one-shot
T5 tier directly off main without blocking other v1.0-rc work.

---

## Carry-over triage (T1 → CL6)

The four tier reviews + six changelist reviews accumulated the
following carry-overs. T6 disposes each before tagging:

| Carry-over | Source | Disposition |
|---|---|---|
| **C2** TRACKER_PROFILE removal | v1.1 doc-refactor leftover; reaffirmed in Phase 5 + Phase 6 close-outs | **Closed by CL2 PR#42.** `TRACKER_PROFILE` + `VALID_PROFILES` + import-time assert + 4 `TestTrackerProfile` tests deleted entirely. |
| **C3** `"All"` filter sentinel + `_REMINDER_TONES` → `config.py` | Phase 5 T1 + T6 reviews | **Closed by CL2 PR#42.** `FILTER_ALL = "All"` and `REMINDER_TONES = ("gentle", "urgent")` lifted to `config.py`; all sites now consume by name. |
| **EM_DASH duplication** (5 modules carried `"—"` literals) | surfaced during CL2 planning | **Closed by CL2 PR#42.** `config.EM_DASH` consumed at all 5 sites. |
| **`urgency_glyph` duplication** (`database.py::_urgency_glyph` + `pages/1_Opportunities.py::_deadline_urgency`) | surfaced during CL2 planning | **Closed by CL2 PR#42.** `config.urgency_glyph(days_away: int \| None) -> str` lifted; database.py call site uses it directly via `Series.apply`; page-layer wrapper retains date-string parsing concern + delegates. |
| **Test-helper duplication** (`link_buttons` + `decode_mailto` + `download_buttons` + `download_button` repeated across page tests) | surfaced during CL3 planning | **Closed by CL3 PR#43.** Four helpers lifted to `tests/helpers.py`; leading-underscore dropped on lift; paren-anchored rename strategy preserved test method substring matches. |
| **45 pyright drift errors** across 5 files | surfaced at CL1 fence-add time | **Closed by CL1 PR#41.** All 45 errors → 0; six commits for per-line `git blame`; runtime no-ops; CI step locks the contract. |
| **Save-toast misleading on no-op** (`apps_detail_form` + `apps_interview_form` + `recs_edit_form` fired `Saved "<name>".` even when nothing changed) | Phase 5 T2/T3/T5 reviews + Phase 6 cross-page audit | **Closed by CL4 PR#44.** Per-field dirty diff against persisted row; no-op path fires `st.toast("No changes to save.")` instead. apps_detail_form no-op also skips R1/R3 cascade (pinned by spy test). |
| **`_build_compose_mailto` subject N=1 vs N≥2 plural agreement** | DESIGN §8.4 line 631 | **Closed by CL4 PR#44.** Subject branches on `n_positions`: N=1 → `letter for 1 postdoc application` (singular); N≥2 → `letters for {n} postdoc applications` (plural). |
| **`app.py` empty-DB hero `st.write` outlier** | cross-page convention audit (`st.markdown` for prose, `st.write` for ambiguous-type renders) | **Closed by CL4 PR#44.** `st.write` → `st.markdown`; behaviour identical (`st.write(str)` routes to `st.markdown` internally); source intent now reads consistent with sibling pages. |
| **5 hardcoded empty-state strings** | reviews + cohesion audit | **Closed by CL4 PR#44.** Five `config.py` constants added; surfaces consume by name; per-page tests assert against the constant by name. |
| **CL4 doc-drift carry-overs** (DESIGN line 631 back-ref + `_build_compose_mailto` docstring narration + ~17 `# Phase 7 CL4 Fix N:` inline comments) | CL4 review | **Closed by CL5 PR#45.** Full-sweep — `grep -rn "Phase 7 CL4 Fix"` returns 0 matches post-CL5. |
| **`gh pr merge --delete-branch` discoverability** (5 consecutive proven uses CL1-CL5 not yet codified) | CL5 review observation | **Closed by CL6a (`04fa7a3`).** `ORCHESTRATOR_HANDOFF.md` "Recurring post-merge ritual" now leads with the flag. |
| **Older review docs carrying `Kept by design` rows in Findings tables** (per `GUIDELINES §10` those belong in Q&A) | CL5 review observation | **Partly closed by CL6b (`bc1017e`).** Phase 6 T2/T3/T4 trimmed (T2: 4→1 row, T3: 4→2, T4: 4→2 + new Q7); Phase 5 reviews deferred by design (predate the convention). |
| **Pre-§14.4 CHANGELOG version blocks** (long-form descriptive entries) | CL5 review observation | **Closed by CL6b (`bc1017e`).** Forensic-preservation framing paragraphs added to `[v0.4.0]` / `[v0.3.0]` / `[v0.2.0]` / `[v0.1.0]` matching the existing `[v0.7.0]` / `[v0.6.0]` / `[v0.5.0]` pattern. |
| **5 minor doc-drift nits** (DESIGN history-as-guidance × 2, GUIDELINES checklist parenthetical, TASKS footer hash, CHANGELOG bare placard) | pre-tag comprehensive audit | **Closed by CL6c (`079564b`).** All 5 fixed in single commit. |
| **T5 — responsive layout check** | TASKS.md "Up next" pre-Phase-7 | **Deferred to v1.0-rc.** No browser-automation MCP available; user-driven manual capture is the fall-back. Documented above. |

### Structural changes between v0.7.0 and v0.8.0 (highlight in tag annotation)

Three durable changes shipped during Phase 7 that aren't tier-specific
deliverables:

1. **Pyright fence in CI** (CL1 PR#41, commit `eac75c3`): `pyright==1.1.409` pinned in `requirements-dev.txt`; `[tool.pyright]` basic-mode block in `pyproject.toml`; new "Pyright type-check" CI step in `.github/workflows/ci.yml` between Ruff lint and Pytest; `pyright .` row added to `AGENTS.md` + `GUIDELINES.md` pre-commit checklists. The fence is forward-looking: any new type drift fails CI at PR boundary rather than accumulating across releases. Held 0/0 across the four refactor PRs that followed (CL2-CL5).

2. **`tests/test_pages_cohesion.py`** (T3 + T4 PR#39 + PR#40, commits `85968bb` + `952f0e9`): two pinning suites — `TestSetPageConfigSweep` (locked-kwargs source-grep + first-Streamlit-statement AST walk across all 5 pages, 10 parametrized tests) and `TestConfirmDialogAudit` (dialog title shape, irreversibility cue, cascade-effect copy enumeration, dialog-gating of every `database.delete_*` caller, failure-preserves-pending-sentinel; 11 tests). Both are structural pins — they assert page-shape invariants rather than per-feature behaviour, so they catch cross-page drift the per-page tests miss.

3. **`gh pr merge --delete-branch` codification** (CL6a, commit `04fa7a3`): `ORCHESTRATOR_HANDOFF.md` "Recurring post-merge ritual" now leads with the flag. Five consecutive proven uses across CL1-CL5 demonstrated the pattern; CL6a wrote it down. Side benefit: orchestrator no longer needs to run `git push origin --delete <branch>` after each merge.

All three are durable workflow / contract changes, not feature
additions — but they're load-bearing enough that they belong in
the v0.8.0 release notes.

---

## Junior-engineer Q&A

### Q1 — T5 was originally part of Phase 7. Why is `v0.8.0` shipping without it?

**A.** Tooling and timing. T5's natural automation surface is a Chrome DevTools / Playwright MCP that can set viewport widths and capture full-page screenshots; the current Claude Code environment has none of those (Gmail / Calendar / Drive / Mem / Notion / PDF Viewer / Context7 are configured; no browser-automation MCP). The fall-back is the user driving Streamlit locally + Chrome DevTools device toolbar + 20+ manual screenshots, which is user-time work that isn't blocking on the orchestrator. Phase 7's polish + cleanup wins (T1-T4 + CL1-CL6) are independent of layout-width verification — they ship as v0.8.0 with durable test pins, and T5 lands as a v1.0-rc deliverable where it composes naturally with publish scaffolding (`README.md` screenshots, deploy verification, recorded demo GIF). The roadmap reflects this.

### Q2 — Why six changelists (CL1-CL6) instead of one or two? Isn't that overhead?

**A.** Each changelist had a different cost-of-failure shape. CL1 (pyright fence) was a CI-touching change that needed isolated verification — bundling it with anything else would muddy "did the fence catch real drift or did the bundled refactor introduce new drift?". CL2 (`config.py` lifts) was a multi-site refactor where atomicity is essential (every site must lift on the same commit or the project is half-lifted). CL3 (test helpers) was independent test-file work. CL4 (4 batched UX fixes) was the only multi-fix-in-one-PR pattern — four small fixes that each needed a `test:` + `feat:` cadence but composed naturally into one PR with one commit per fix. CL5 swept CL4's doc drift (the kind of cleanup that benefits from being its own commit so `git blame` shows the sweep date). CL6 was orchestrator-only (no implementer touch) and split into CL6a/CL6b/CL6c by content domain. The split paid off in `git log` legibility — every cleanup decision has its own commit hash, every PR has one reviewable scope, and pyright + the cohesion-pinning tests caught any cross-CL drift at PR boundary.

### Q3 — `tests/test_pages_cohesion.py` looks like it duplicates per-page tests. Why a separate file?

**A.** Different invariants. Per-page tests (`tests/test_opportunities_page.py` etc.) assert per-feature behaviour — "the urgency glyph for an overdue deadline is 🔴", "the position-delete dialog enumerates the cascade chain". `tests/test_pages_cohesion.py` asserts cross-page **structural** invariants — "every page calls `set_page_config` as the first Streamlit statement with the locked kwargs", "every `database.delete_*` call site is inside a `@st.dialog`-decorated function". Cross-page invariants need their own location because they parametrize over the page set and would otherwise duplicate test setup across 5 files. They're also the durable shape that catches *new pages* drifting on day 1 — when v1.0-rc adds a publish-scaffolding page, the existing parametrize will fail until the new page conforms. That's a feature, not a duplication.

### Q4 — CL6 shipped as three commits direct on main with no PR. Doesn't that bypass the review cadence?

**A.** Orchestrator-only work doesn't fit the implementer-PR / orchestrator-review cadence — the orchestrator is the reviewer, so a PR routes to the same person with no second pair of eyes. The mitigation is that CL6's content was small (each commit ≤ 50 lines), entirely doc-only (no code paths touched), and surfaced by an audit (CL6c specifically — the audit caught 5 nits + the orchestrator fixed them). The pre-tag comprehensive audit (8 parallel Explore agents covering DESIGN drift, GUIDELINES drift, TASKS-vs-reality, CHANGELOG completeness, AGENTS currency, reviews/README index, cross-doc references, Phase 7 cohesion) is the orchestrator's substitute for the missing implementer-PR review pass. Findings logged + closed before tag; that's the audit trail.

### Q5 — Why isn't T5 in CHANGELOG `[v0.8.0]` as a "Removed" or "Skipped" entry?

**A.** Keep a Changelog 1.1.0 (which `CHANGELOG.md` follows per the header) doesn't have a "Skipped" section, and "Removed" is for code removed in this version, not features dropped from this version's scope. The right place to surface T5's deferral is the tag annotation + the close-out doc (this file, "T5 deferral" section) + `TASKS.md` "Up next" carrying T5 forward against v1.0-rc. Reading the v0.8.0 release notes alone shouldn't suggest T5 was attempted; the roadmap is the durable record of what's still owed. The CHANGELOG is for what shipped.

### Q6 — The `docs/designupdate` remote branch was deleted as part of pre-tag cleanup. Was that work salvageable?

**A.** Probably, but not as a merge target. The branch was 4 days stale, 30+ commits behind main (entire Phase 7 sub-tier shipped after), and showed 15,009 line deletions vs 1,700 insertions across 58 files — a heavy DESIGN-compression + test-file gutting attempt that would have erased the CL1-CL6 work on merge. The intent (DESIGN.md prose tightening, meta-commentary trim) is still good and survives in spirit through CL6b's review-doc Findings-table strip + CL6c's history-as-guidance trim. If the user wants the broader DESIGN compression done, the right move is a fresh branch off current main with an explicit scope (one section at a time, rebased after each merge to stay current). Reflog keeps the deleted branch's commits accessible locally for ~30 days if any specific compression idea wants resurrecting.

---

## v0.8.0 tag preparation (orchestrator checklist)

Standing close-out steps. All blocking gates already green at HEAD `079564b` per the method block above; the rest is mechanical.

1. **CHANGELOG.md split** — `[Unreleased]` → `[v0.8.0]` — 2026-05-05 — Phase 7: Polish (UX micro-fixes + 6-CL cleanup sub-tier) at the boundary commit (the T6 close-out commit itself), mirroring the v0.7.0 split precedent (commit `6f70db2`).
2. **Tag** — `git tag -a v0.8.0 -m "Phase 7 — Polish (UX micro-fixes + 6-CL cleanup sub-tier)"` with annotation listing the headline T1-T4 + CL1-CL6 deliverables + the three structural changes (pyright fence, cohesion-pinning tests, `--delete-branch` codification).
3. **TASKS.md / AGENTS.md final flip** — T6 ✅; main HEAD line bumped; latest-tag bumped to `v0.8.0`; Phase 7 marked closed; Immediate-task block replaced with **v1.0-rc / publish scaffolding** (per `TASKS.md` "Up next").
4. **reviews/README.md index** — prepend a row for this close-out doc.
5. **Recently-done entry** — one bullet for the v0.8.0 tag close-out.
6. **Push commit + tag.**
7. **GitHub release** — `gh release create v0.8.0 --notes-from-tag` (or paste curated notes if richer formatting helps).

---

_Written 2026-05-05 as the Phase 7 close-out doc per the
`reviews/phase-6-finish-cohesion-smoke.md` precedent. Cohesion
evidence sourced from the parallel Explore-agent survey + the
two pinning suites in `tests/test_pages_cohesion.py`. Suite green
at 879 passed + 1 xfailed under both pytest gates. Pyright 0/0.
Standing isolation gate empty post-pytest. CI-mirror local check
green. Verdict: Approve `v0.8.0` tag._
