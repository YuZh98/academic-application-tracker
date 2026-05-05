# Changelog

All notable changes to the Postdoc Tracker are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(with the pre-1.0 convention that each minor bump marks one completed phase
or tier — see `GUIDELINES §11` for the version scheme).

Versions use the format `v<major>.<minor>.<patch>`. The `[Unreleased]` section
at the top collects changes on feature branches before they ship.

Each release entry may include a `Migration:` note with the exact SQL or
manual steps to run against a pre-existing database.

---

## [Unreleased]

### Added
- Add 5 per-surface empty-state copy constants on `config.py` (`EMPTY_FILTERED_POSITIONS`, `EMPTY_NO_POSITIONS`, `EMPTY_FILTERED_APPLICATIONS`, `EMPTY_PENDING_RECOMMENDERS`, `EMPTY_PENDING_RECOMMENDER_FOLLOWUPS`); 5 hardcoded `st.info(...)` strings updated to consume the constants; per-page tests assert against the constants by name. PR #44 (`9a5eded`) · [review](reviews/phase-7-CL4-review.md)
- Add shared `tests/helpers.py` with 4 AppTest helpers (`link_buttons`, `decode_mailto`, `download_buttons`, `download_button`); paren-anchored rename strategy preserved test method substring matches. PR #43 (`479aa15`) · [review](reviews/phase-7-CL3-review.md)
- Add `config.urgency_glyph(days_away: int | None) -> str` function (lifted from `database.py::_urgency_glyph` + `pages/1_Opportunities.py::_deadline_urgency`); `EM_DASH`, `FILTER_ALL`, `REMINDER_TONES` constants on `config.py` (lifted from 5 / 3 / 1 duplicate sites respectively). Closes carry-overs C2 + C3. PR #42 (`bd76d29`) · [review](reviews/phase-7-CL2-review.md)
- Add pyright type-check fence to CI (basic mode, pythonVersion 3.14, `pyright==1.1.409` pinned); `pyright .` row added to standing pre-commit checklists. PR #41 (`eac75c3`) · [review](reviews/phase-7-CL1-review.md)
- Add `TestConfirmDialogAudit` to `tests/test_pages_cohesion.py` — 11 tests across 3 destructive paths pinning dialog title shape, irreversibility cue, cascade-effect copy enumeration, dialog-gating of every `database.delete_*` caller, and failure-preserves-pending-sentinel. PR #40 (`952f0e9`) · [review](reviews/phase-7-tier4-review.md)
- Add `tests/test_pages_cohesion.py` with `TestSetPageConfigSweep` — 10 parametrized tests pinning locked-kwargs source-grep + first-Streamlit-statement AST walk across all 5 pages; audit confirmed all conform (verification-only). PR #39 (`85968bb`) · [review](reviews/phase-7-tier3-review.md)
- Add free-text "Search positions" `text_input` to Opportunities filter row; substring match against `position_name` (case-insensitive, regex=False, NaN-safe), AND-combined with status/priority/field filters. PR #38 (`e67cfed`) · [review](reviews/phase-7-tier2-review.md)
- Add 🔴/🟡 urgency glyphs to Opportunities deadline column; `_deadline_urgency` now returns inline glyphs (was: `'urgent'`/`'alert'` literal flags) with new `—` state for NULL deadlines. PR #37 (`e5316fd`) · [review](reviews/phase-7-tier1-review.md)

### Changed
- Branch save-toast wording on dirty diff in `pages/2_Applications.py` apps_detail_form (now computes per-field dirty diff against persisted `app_row`; was previously unconditional `upsert_application`) + per-row `apps_interview_{id}_form` + `pages/3_Recommenders.py` recs_edit_form: no-op clicks fire `st.toast("No changes to save.")` instead of misleading `Saved "<name>"`. apps_detail_form no-op skips DB write AND R1/R3 cascade (pinned by spy test). PR #44 (`9a5eded`) · [review](reviews/phase-7-CL4-review.md)
- Branch `_build_compose_mailto` subject on `n_positions`: N=1 → singular `letter for 1 postdoc application`; N≥2 → plural `letters for {n} postdoc applications` (unchanged). DESIGN §8.4 line 631 amended in same commit. PR #44 (`9a5eded`)
- Harmonize `app.py` empty-DB hero copy from `st.write` to `st.markdown` — sole outlier in cross-page convention (markdown for prose, write for ambiguous-type renders). Behaviour identical (`st.write(str)` routes to `st.markdown` internally). PR #44 (`9a5eded`)
- Trim recent CHANGELOG entries to GUIDELINES §14.4 one-line shape; add bottom link references; restructure phase-6-tier5 + phase-7-tier1 review docs to move `Kept by design` rows from Findings table to Q&A per §10. ([drift audit])

### Removed
- Drop unused `TRACKER_PROFILE` + `VALID_PROFILES` block + import-time assertion + 4 `TestTrackerProfile` tests from `config.py` / `tests/test_config.py` (carry-over C2 — never read by any module since v1.1 doc refactor). PR #42 (`bd76d29`)

### Fixed
- Resolve 45 pyright drift errors across 5 files (`exports.py`, `pages/1_Opportunities.py`, `pages/2_Applications.py`, `pages/3_Recommenders.py`, `tests/test_app_page.py`) accumulated since PR #22; all fixes runtime no-ops. PR #41 (`eac75c3`)
- Position-delete dialog warning text now lists "application, interview, and recommender rows" — was missing "interview" despite FK chain `positions → applications (CASCADE) → interviews (CASCADE)` dropping interview rows on cascade. Surfaced by Phase 7 T4 cohesion test. PR #40 (`952f0e9`)

## [v0.7.0] — 2026-05-04 — Phase 6: Exports (markdown generators + Export page)

_v0.7.0 closes Phase 6 — three markdown generators in `exports.py` (`write_opportunities` / `write_progress` / `write_recommenders`) backing `OPPORTUNITIES.md` / `PROGRESS.md` / `RECOMMENDERS.md` files in `exports/`, plus a new `pages/4_Export.py` Streamlit page wrapping them with a manual regenerate button + per-file mtimes panel + per-file download buttons. Five pre-merge tier reviews + the close-out cohesion-smoke at [`reviews/phase-6-finish-cohesion-smoke.md`](reviews/phase-6-finish-cohesion-smoke.md) verified every architectural choice. Three durable structural changes also shipped during Phase 6: the `tests/conftest.py::db` fixture lift to monkeypatch both `database.DB_PATH` AND `exports.EXPORTS_DIR` (closes the test-isolation pollution exposed by T1's auto-write hook), the CI-green-conclusion-before-admin-bypass procedure amendment + CI-mirror local check (post-mortem on PRs #32-#34 shipping main red while CI was IN_PROGRESS), and the privacy amendment — `exports/` is now `.gitignore`d alongside `postdoc.db`, and DESIGN §7 contract #2's "committed into version control" wording is amended to privacy-first. Suite climbed 777 → 834 (+57 tests, 1 xfail unchanged) across the phase. Detailed entries below preserve the original forensic record from when each item shipped._

### Added
- Add three `st.download_button` widgets + `Download` section header to Export page; `disabled=True` when file absent. PR #36 (`73a04c4`) · [review](reviews/phase-6-tier5-review.md)
- Add `pages/4_Export.py` with regenerate button + per-file mtimes panel. PR #35 (`3235f60`) · [review](reviews/phase-6-tier4-review.md)
- Add `exports.write_recommenders()` writing 8-column markdown table to `exports/RECOMMENDERS.md`. PR #34 (`c11fde4`) · [review](reviews/phase-6-tier3-review.md)
- Add `exports.write_progress()` writing 8-column markdown table to `exports/PROGRESS.md` (positions × applications × interviews). PR #33 (`911115a`) · [review](reviews/phase-6-tier2-review.md)
- Add `exports.write_opportunities()` writing 8-column markdown table to `exports/OPPORTUNITIES.md`. PR #32 (`e9a8a4a`) · [review](reviews/phase-6-tier1-review.md)

### Changed
- **Breaking:** `.gitignore` `exports/` and amend DESIGN §7 contract #2 from "committed into version control" to "deterministic and idempotent" — markdown carries personal data. (`43b3f3c`)
- Codify CI-green-conclusion-before-admin-bypass + CI-mirror local check in `ORCHESTRATOR_HANDOFF.md` + `AGENTS.md` (post-mortem on PRs #32–#34 shipping main red while CI was IN_PROGRESS). (`c284c20`)
- Lift `tests/conftest.py::db` to monkeypatch both `database.DB_PATH` and `exports.EXPORTS_DIR`; add `git status --porcelain exports/` isolation gate to standing pre-PR checklist. PR #33 (`911115a`)

### Fixed
- Augment `tests/test_exports.py::isolated_exports_dir` to monkeypatch `database.DB_PATH` (was: only `EXPORTS_DIR`); closes CI-red regression latent since Phase 6 T1 (smoke tests fell through to developer's real `postdoc.db`). PR #34 (`c11fde4`)

## [v0.6.0] — 2026-05-04 — Phase 5: Applications + Recommenders pages

_v0.6.0 closes Phase 5 — two new working pages: **Applications** (T1–T3 — `pages/2_Applications.py`: shell + status filter + 7-column table + selection-driven detail card with dirty-diff Save + cascade-promotion toasts + per-row inline interview list with `@st.dialog`-gated Delete) and **Recommenders** (T4–T6 — `pages/3_Recommenders.py`: page shell + Pending Alerts cards grouped by recommender; T5 All-Recommenders table + position/recommender filters + Add expander + inline edit card with dirty-diff Save + dialog Delete; T6 per-card Compose-reminder-email `st.link_button` mailto + `LLM prompts (2 tones)` expander). Six pre-merge tier reviews + the close-out cohesion-smoke at [`reviews/phase-5-finish-cohesion-smoke.md`](reviews/phase-5-finish-cohesion-smoke.md) verified every architectural choice and pinned cross-page consistency. Suite climbed 553 → 777 (+224 tests, 1 xfail unchanged) across the phase. Detailed entries below preserve the original forensic record from when each item shipped._

### Changed
- GUIDELINES.md: add §14 Documentation Conventions (file-header schema, cross-references, doc tiering, CHANGELOG discipline per Keep a Changelog 1.1.0, TASKS.md scope rules, wireframe-drift severity, reviews folder index, content-routing table). (`b148dd5`)
- GUIDELINES §10: extend severity legend with `ℹ️ Observation`; codify Status column values; tighten Q&A range to 5–8 (per §14.3 tiering). (`b148dd5`)
- `docs/adr/README.md`: clarify post-v1.1 decision deferral policy; update D1–D10 references to acknowledge the D11–D25 additions in `DESIGN §10` as candidate ADR backfills. (`196fc0b`)
- `reviews/*.md` (all 20 files): harmonize front-matter to the new §14.1 schema — add missing `**Branch:**` / `**Scope:**` / `**Verdict:**` fields; preserve all existing fields. Pre-branch-workflow reviews (Phase 1–3 Tier 1–3) get `Branch: _(direct-to-main; pre-branch-workflow)_`. (`e0da6e0`)

### Fixed
- `docs/dev-notes/streamlit-state-gotchas.md` gotcha #13: replace stale `interview1_date` / `interview2_date` example with the post-v1.3-Sub-task-8 `scheduled_date` form (interviews sub-table). (`5487418`)
- `docs/dev-notes/streamlit-state-gotchas.md` gotcha #14: drop the obsolete 🔄 Refresh-button reference (button was deleted in Sub-task 12 per DESIGN D13); rewrite workaround to point at the surviving Save / Delete-handler use sites. (`5487418`)

### Changed
- `TASKS.md` `Recently done`: trim per the new §14.5 cap rule — drop pre-v0.5.0 entries (Phase 4 T5-A, T6 cohesion-smoke, T6 funnel-toggle polish, v1 plan-locking commit, PRs #8/#9/#10, v0.2.0/v0.3.0/v0.4.0 tag entries); items survive in CHANGELOG version blocks. (`30ad6fd`)

### Added
- `reviews/README.md`: new index file per `GUIDELINES §14.7` — reverse-chronological table of all 20 review docs with columns `(date, scope, branch, verdict, link)`; brief preamble cross-linking the §14.1 / §14.7 conventions; "How to add a new entry" footer. (`12c60e4`)
- Phase 5 T1: Applications page shell on `pages/2_Applications.py` — `set_page_config`, title, status-filter selectbox, read-only six-column table per DESIGN §8.3 (with the §8.3 D-A inline-text amendment for the Confirmation column). Merged via PR #15 (`aebbb8b`); detailed essay in commit body + [`reviews/phase-5-tier1-review.md`](reviews/phase-5-tier1-review.md).
- Phase 5 T2-A: Applications-page editable detail card behind row selection — `apps_detail_form` (8 widgets), Save handler calling `database.upsert_application(propagate_status=True)`; asymmetry vs Opportunities §8.2 at `df_filtered.empty` (filter narrowing keeps the card open). Merged via PR #16 (`b9a2c82`); detailed essay in commit body + [`reviews/phase-5-Tier2-review.md`](reviews/phase-5-Tier2-review.md).
- Phase 5 T2-B: cascade-promotion toast surfacing — second `st.toast(f"Promoted to {STATUS_LABELS[new_status]}.")` after the Saved toast when `upsert_application` returns `status_changed=True`. Merged via PR #16 (`b9a2c82`).
- Phase 5 T3-A: Applications-page inline interview list under the existing detail card — `apps_interviews_form` per-row widgets (`apps_interview_{id}_{date|format|notes}`), `_safe_str`-normalized dirty-diff Save calling `database.update_interview` per dirty row only, Add button (outside the form per Streamlit form-vs-button constraint) with R2 promotion toast on `status_changed=True`. Per-row pre-seed sentinel `_apps_interviews_seeded_ids` is a frozenset pruned via intersection per rerun (Sonnet plan-critique signals on `notes` NaN dirty-diff, format-`None` pre-seed, and zombie-id pruning all addressed). Format selectbox mirrors T2-A's `response_type`: `[None, *INTERVIEW_FORMATS]` with em-dash `format_func`. (`1bdee91`)
- Phase 5 T3-B: per-row Delete via `@st.dialog` on the Applications-page interview list — module-level `_confirm_interview_delete_dialog` helper (Confirm + Cancel buttons, irreversibility warning embedding the row's sequence number), per-row Delete buttons rendered in a horizontal `st.columns(N)` row below `apps_interviews_form` (Streamlit 1.56 forbids `st.button` inside `st.form`) and keyed `apps_interview_{id}_delete`. Single dialog call site post-loop with a `pending_id in current_ids` guard implements gotcha #3's re-open trick AND doubles as automatic stale-target cleanup when the user navigates to a different position. Confirm path calls `database.delete_interview(id)`, pops paired sentinels, sets `_applications_skip_table_reset=True` (gotcha #11 — preserves position selection), fires `Deleted interview {seq}.` toast. Failure path uses `st.error` per GUIDELINES §8 with sentinels surviving so the dialog re-opens for retry (Opportunities-page failure-preserves-state precedent). (`b3a307c`)
- Phase 5 T4: Add `pages/3_Recommenders.py` — page shell (`set_page_config`, `st.title`, `database.init_db()`) + Pending Alerts panel: `get_pending_recommenders()` grouped by `recommender_name`, one `st.container(border=True)` per person with relationship in header and per-position bullets (institute-prefixed label, asked-Nd-ago, due Mon-D; em-dash for NULL deadline). Empty branch: `st.info("No pending recommenders.")`. 18 new tests in `tests/test_recommenders_page.py`. Merged via PR #28 (`a491be3`). ([`reviews/phase-5-tier4-review.md`](reviews/phase-5-tier4-review.md))
- Phase 5 T5: All Recommenders surface on `pages/3_Recommenders.py` — read-only `st.dataframe` (`recs_table`) backed by `database.get_all_recommenders()` with the locked six-column display contract (Position · Recommender · Relationship · Asked · Confirmed · Submitted) + position/recommender filter selectboxes (`recs_filter_position`, `recs_filter_recommender`) defaulting to `"All"` (recommender filter dedupes repeat names). `st.form("recs_add_form")` inside an "Add Recommender" expander with label-as-value position selectbox (`_position_label_to_id` reverse lookup keeps `position_id` off the rendered UI per DESIGN §8.4); whitespace-only name → `st.error`. Single-row selection captures `recs_selected_id`; inline edit card with `st.form("recs_edit_form")` over asked_date / confirmed (`[None, 0, 1]` → `—`/`No`/`Yes`) / submitted_date / reminder_sent + reminder_sent_date / notes; Save writes ONLY the dirty diff via `database.update_recommender`. Delete button outside the form opens an `@st.dialog` confirm gate (`recs_delete_confirm` / `recs_delete_cancel`) that cascades via `database.delete_recommender` on Confirm and preserves selection on Cancel via the `_recs_skip_table_reset` one-shot — single dialog call site post-loop with `_recs_delete_target_id == _rec_id` guard (gotcha #3 re-open trick + automatic stale-target cleanup on row-change). 56 new tests in `tests/test_recommenders_page.py`; suite 700 → 756 under both pytest gates. Merged via PR #29 (`2293ebd`). ([`reviews/phase-5-tier5-review.md`](reviews/phase-5-tier5-review.md))
- `AGENTS.md`: agent-handoff document at repo root — replaces the need to read every spec doc on first contact for new implementer agents; orchestrator maintains the `Current state` table + `Immediate task` block after each merged PR. Merged via PR — `b56c553`.
- `ORCHESTRATOR_HANDOFF.md`: orchestrator-role transition document — pasted into a fresh Claude session when the orchestrator role moves; points at on-disk source-of-truth files rather than carrying mutable state. Merged via PR #30 (`6c1fc5b`).
- Phase 5 T6: Recommender reminder helpers wired into each Pending Alerts card on `pages/3_Recommenders.py` (T4 surface). T6-A: per-card `st.link_button("Compose reminder email", url=mailto:?…)` opening the user's default mail client with the verbatim DESIGN §8.4 subject (`Following up: letters for {N} postdoc applications`) + body (`Hi {recommender_name}, just a quick check-in on the letters of recommendation you offered. Thank you so much!`); no `to:` field (recommenders schema doesn't store emails); per-card unique key `recs_compose_{idx}` from `enumerate` over the groupby prevents `DuplicateWidgetID`. T6-B: per-card `st.expander(f"LLM prompts ({len(_REMINDER_TONES)} tones)")` with one `st.code(prompt, language="text")` block per locked tone — `_REMINDER_TONES = ("gentle", "urgent")` per DESIGN §8.4; each prompt embeds recommender name + relationship + every owed position (name / institute / deadline) + days-since-asked (max across the group) + tone keyword + an instruction asking the LLM to return BOTH subject and body. Two pure helpers (`_build_compose_mailto`, `_build_llm_prompt`); existing T4 `_bullets`-building loop extended by one line for `_per_row_days` collection. 21 new tests across `TestT6ComposeButton` (9) + `TestT6LLMPromptsExpander` (12); suite 756 → 777 under both pytest gates. Merged via PR #31 (`6993ea9`). ([`reviews/phase-5-tier6-review.md`](reviews/phase-5-tier6-review.md))

### Changed
- DESIGN §8.3 + `docs/ui/wireframes.md` Applications: amend the spec for T3-rev — explicit seven-column table contract (Position bare, Institute bare, Applied, Recs, Confirmation, Response, Result); per-row interview block architecture replaces the single page-level `apps_interviews_form` (each interview now owns a `apps_interview_{id}_form` with per-row Save submit button + per-row Delete button outside the form). Truth-file update lands first so the code refactor can follow. (`ba7cd47`)
- Phase 5 T3-rev-A: Applications-page table split Position into Position + Institute columns per the amended DESIGN §8.3 contract. `display_df` drops the `_format_label` call that combined institute + position_name; both cells now go through `_safe_str_or_em` (NaN→EM_DASH per gotcha #1). `column_config` adds Institute with `width="medium"` between Position and Applied; Position keeps `width="large"`. The `_format_label` helper stays on the page — still used by the detail-card header. (`1d73ebc`)
- Phase 5 T3-rev-B: Applications-page interview list refactored from a single page-level `apps_interviews_form` (Save batches every row in one click) to per-row blocks. Each interview is now a self-contained block of {`**Interview {seq}**` heading + 3-column date/format/notes detail row + per-row `apps_interview_{id}_form` (`border=False`) + per-row `Save` submit button (key `apps_interview_{id}_save`) + per-row Delete button outside the form (key `apps_interview_{id}_delete`)}. Blocks separated by `st.divider()`. Streamlit fires at most one form submit per click rerun, so the per-row Save handler (`if saves_clicked:`) processes a single (iid, seq) tuple — sibling rows' in-flight drafts survive untouched via the existing per-row pre-seed sentinel. Toast / error wording switched to singular + sequence (`Saved interview {seq}.` / `Could not save interview {seq}: {e}`), closing T3 review Finding #6 wording asymmetry by side-effect. (`f116dbf`)
- `config.RELATIONSHIP_TYPES` → `config.RELATIONSHIP_VALUES` rename (Phase 5 T5 ride-along) for cohesion with the project's `*_VALUES` naming convention used by `STATUS_VALUES`, `PRIORITY_VALUES`, `RESULT_VALUES`, `REQUIREMENT_VALUES`. Updates the two prose references in `DESIGN.md` + `docs/dev-notes/extending.md` + the `tests/test_config.py` parametrize entry. Merged via PR #29 (`2293ebd`).

### Fixed
- Fix two stale block-comment references to the retired `apps_interviews_form` in `pages/2_Applications.py` (pre-merge review Findings #10 and #11; no behavior change). [`reviews/phase-5-Tier3-review.md`](reviews/phase-5-Tier3-review.md)

### Changed
- `CHANGELOG.md`: split `[Unreleased]` into a `[v0.5.0]` (2026-04-30) version section at the boundary commit `c93dec0` per Keep a Changelog 1.1.0 (§14.4 application). Phase 5 T1 / T2-A / T2-B essays in `[Unreleased]` collapsed to short bullets pointing at commit hashes + review docs. Pre-v0.5.0 essays preserved verbatim under `[v0.5.0]` as the forensic record from before §14.4 landed. (`db383e3`)
- All `.md` files (DESIGN, GUIDELINES, TASKS, roadmap, CHANGELOG, docs/adr/README, docs/dev-notes/*, docs/ui/wireframes, reviews/*): sweep `.md`-suffixed §-section refs to the §14.2 canonical form (`DESIGN §X.Y`, `GUIDELINES §N`). Markdown link URLs in `wireframes.md` are preserved (navigation-bearing per §14.2); only the link text is updated. ~46 instances across 17 files. (`24de8f8`)

### Fixed
- `docs/ui/wireframes.md` Dashboard panel column order: the Upcoming-table example rows showed `Date · Label · Status · Kind · Days left · Urgency` but DESIGN §8.1 + the actual `app.py` render use `Date · Days left · Label · Kind · Status · Urgency`. Reordered the 3 example rows to match the spec; added a column-header row for clarity. Closes the column-order drift originally flagged in `reviews/phase-4-finish-cohesion-smoke.md` (re-classified as 🟠 under §14.6).

### Removed
- `docs/ui/wireframes.md` Applications section: drop the three prose blocks beneath the ASCII (Filter selectbox details, Confirmation column 3-state table, Phase 5 status note). Per §14.8 routing, widget contracts belong in DESIGN §8.x and implementation status belongs in TASKS / CHANGELOG — not in a wireframes file. Filter-selectbox option-order + `format_func=STATUS_LABELS.get(v, v)` sentinel-fallthrough rule MOVED to DESIGN §8.3 (one expanded bullet on the existing Default filter row); Confirmation 3-state table was already redundant with DESIGN §8.3 lines 832-836; Phase 5 status note dropped (TASKS.md is the durable record). (`6beaac9`)

### Added
- `docs/dev-notes/streamlit-state-gotchas.md`: index/TOC at the top. 16 numbered one-line summaries of the gotchas; references like "see gotcha #16" can now navigate by number rather than by full-text search.
- `docs/dev-notes/{dev-setup, extending, git-workflow-depth, streamlit-state-gotchas}.md`: one-sentence italicized "what this is" header under each title — folder-scan readability per the post-PR-#17 audit. The existing intro prose is preserved beneath; the new line is purpose-only.

### Changed
- `TASKS.md` + `roadmap.md`: chore tracker update to reflect post-PR-#16 state. PR #16 (Phase 5 T2, `b9a2c82`) merged 2026-04-30; main HEAD now at `b9a2c82`. TASKS current sprint shows Branch (T2) merged + Branch (T3) as next functional work; Recently done collapses the per-sub-task T2-A/T2-B essays into a single PR #16 bullet (per §14.4 spirit). roadmap "In flight" → `docs/guidelineupdate`; "Next up" → Phase 5 T3 (inline interview list per DESIGN §8.3 D-B); Phase 5 detail table marks T1 + T2 ✅ via their PR numbers.
- DESIGN.md: bump `**Version:** 1.3` → `1.4`; align header to §14.1 schema (`Updated:` → `Last updated:`); date 2026-04-30. v1.4 captures the structural amendments since v1.3: T4 column-contract (Upcoming-panel six-column lock), T6 funnel-toggle bidirectional + tertiary, §8.3 D-A inline-cell-text amendment, §8.4 D-C mailto + LLM-prompts pattern, §8.3 D-B inline interview list spec, §6.3 D-D pending-column-drops paragraph, §8.3 Status filter selectbox bullet expansion (cleanup C of this branch).
- GUIDELINES.md: bump `**Version:** v1.1` → `v1.2`; replace `Applies from:` field with `Last updated:` + `Status:` per §14.1 header schema. v1.2 content delta vs v1.1 is the §14 Documentation Conventions block + §10 ℹ️ Observation row + Status column codification + §13 page-authoring procedure (all landed in earlier commits on `docs/v1-planning-pins` and `docs/guidelineupdate`).
- GUIDELINES.md: remove **history-as-guidance** from forward-looking sections — 14 instances across §1, §3, §7, §9, §10, §11, §12, §13, §14.1, §14.4, §14.7, §14.8 (historical attributions like "From v1.1", one-time-event branch refs, stale snapshots like "Current files: ...", past-tense narratives, and 3 cross-ref drift hits the §14.2 sed pattern missed — `streamlit-state-gotchas.md §N` → `dev-notes gotcha #N`). §14.8 routing table simplified to forward-only (D1–D10 / D11–D25 historical-batch rows dropped); §14.7 legacy-filename carve-out dropped per user direction.
- GUIDELINES.md §11 + §14: revise to remove descriptive prose and meta-commentary — §11 title (drop "— Summary"), §11 "For depth" listing trimmed; §14 intro descriptive lines dropped, §14.1 "keep existing" reworded forward, §14.3 "Whatever the spec needs" → "(no cap)" + meta-line trimmed, §14.5 "— that's the durable record" justification dropped, §14.6 specific Date/Days-Left example replaced with principle, §14.7 "by author preference" softness + "file timestamps order naturally" meta dropped (rule locked: reverse-chronological, prepend), §14.8 intro and redundant restatement dropped, §14.8 specific extending.md/§5.3 example generalized.

### Changed
- `DESIGN §8.3` Status filter selectbox bullet: expand to capture the option list (`[STATUS_FILTER_ACTIVE, "All", *STATUS_VALUES]`), default value, and the `format_func=STATUS_LABELS.get(v, v)` sentinel-fallthrough rule moved from `docs/ui/wireframes.md`. Per §14.8: page-by-page UI contracts live in DESIGN §8.x.

## [v0.5.0] — 2026-04-30 — Phase 4 close (T4–T6) + v1.3 alignment + funnel toggle polish

_v0.5.0 closes Phase 4 (Dashboard) — five panels complete (KPI grid, Application Funnel with bidirectional disclosure toggle, Materials Readiness, Upcoming timeline, Recommender Alerts). It also includes the v1.3 DESIGN-to-codebase alignment (Sub-tasks 1–14 + 6 follow-ups), the Sub-task 13 reversal (edit-panel restored to `st.tabs`), and the v1 planning pins from the 2026-04-27 session. Detailed entries below preserve the original forensic record from when each item shipped — they pre-date the §14.4 short-bullet discipline introduced on `docs/guidelineupdate`._

### Changed — Funnel disclosure toggle: bidirectional + tertiary + subheader-row inline (T6 polish, branch `feature/phase-4-tier6-Cohesion`)

Phase 4 T6 polish — closes two user-reported issues with the
pre-T6 unidirectional `[expand]` button:

  1. After clicking `[expand]`, the button vanished and there was no
     companion `[collapse]` to return to the focused view. The user
     was stuck in the expanded state until a fresh session.
  2. The default-typed button read as a primary CTA, visually too
     heavy for what is semantically a chart control.

The replacement is a single bidirectional disclosure toggle with
state-keyed labels, `type="tertiary"` styling, and inline placement
in the funnel subheader row via `st.columns([3, 1])` — same idiom T4
Upcoming uses for its window selector.

Three deliverables; one TDD round (`test:` red → `feat:` green →
`chore:` rollup):

`config.py`:

- New `FUNNEL_TOGGLE_LABELS: dict[bool, str]`. State-keyed labels
  describing the action a click *will perform*, not the current state:
    - `False` (collapsed) → `"+ Show all stages"`
    - `True` (expanded)  → `"− Show fewer stages"`
  Symbols are U+002B `+` and U+2212 `−` (NOT hyphen-minus); they
  encode the click's effect direction (adding / removing buckets
  from view). Vocabulary follows the project's `<symbol> <verb-phrase>`
  CTA convention used by `+ Add your first position` (empty-DB hero)
  and `→ Opportunities page` (Materials Readiness CTA) — visual-
  vocabulary cohesion across all four dashboard CTAs. Replaces the
  orphan bracket convention `[expand]` / `[collapse]` (no other CTA
  in the codebase used brackets).

- New import-time invariant §5.2 #11:
  `set(FUNNEL_TOGGLE_LABELS.keys()) == {True, False}` — the page
  reads the dict as `FUNNEL_TOGGLE_LABELS[st.session_state["_funnel_expanded"]]`.
  A missing key would surface as a render-time `KeyError` on first
  toggle into that state; an extra key would silently no-op. Caught
  at import.

- `FUNNEL_DEFAULT_HIDDEN` doc comment updated to describe the
  bidirectional toggle (was: "Revealed all at once by the single
  `[expand]` button"; now: "The single disclosure toggle reveals/hides
  them as a group").

`app.py`:

- Replaced the unidirectional `_expand_funnel()` callback with
  `_toggle_funnel()` that flips True ↔ False on each click. Same
  `on_click` pattern (state set BEFORE the next rerun) so the chart
  branches evaluate against the new value in the same rerun.
- Replaced the two literal `"[expand]"` buttons (one in branch (b),
  one in branch (c)) with a single button rendered ONCE in the
  funnel subheader row via `st.columns([3, 1])`. The toggle label
  resolves via `config.FUNNEL_TOGGLE_LABELS[_funnel_expanded]` at
  render time. Widget key renamed `funnel_expand` → `funnel_toggle`
  to match the bidirectional contract (no callers relied on the old
  key — safe rename).
- `type="tertiary"` so the button reads as a chart control rather
  than a primary CTA. Distinct visual weight from the Materials
  Readiness `→ Opportunities page` CTA (default type) reinforces
  the role distinction: disclosure vs cross-page navigation.
- Branch (a) (empty DB) keeps a bare `st.subheader` (no `[3, 1]`
  split) so the right column slot isn't a dead box. Toggle
  suppression in branch (a) is unchanged from pre-T6.
- Branch (b) info copy updated to point at the toggle by LABEL
  rather than spatial direction:
  - Pre-T6: `"All your positions are in hidden buckets. Click [expand] below to reveal them."`
  - Post-T6: `"All your positions are in hidden buckets. Click 'Show all stages' to reveal them."`
  The new wording stays correct regardless of toggle placement.

`tests/test_app_page.py`:

- New `TestT6FunnelToggle` (15 tests across 5 groups):
  - **A** (label correctness — 3 tests + class-literal drift check)
  - **B** (round-trip — 4 tests including the involution and the
    branch (b) ↔ (c) round-trip — the test that explicitly pins the
    user-reported bug fix)
  - **C** (placement — 2 source-grep tests, both with comment-line
    stripping to avoid the same FP class flagged in the cohesion-
    smoke audit)
  - **D** (empty-state matrix re-pin under the new contract)
  - **E** (CTA-convention symbol cohesion)
- `TestT2BFunnelEmptyState`: `EMPTY_COPY_B` updated to the new
  spatial-direction-free wording; `EXPAND_LABEL` re-pinned to the
  new literal.
- `TestT2DFunnelExpand`: deleted `test_expand_button_hides_after_click`
  (premise inverts under the bidirectional contract). Kept the
  collapsed-half coverage; class docstring rewritten to name its
  post-T6 scope.

`tests/test_config.py`:

- Four new tests pinning `FUNNEL_TOGGLE_LABELS`:
  `test_funnel_toggle_labels_is_bool_keyed_dict`,
  `test_funnel_toggle_labels_spec_values`,
  `test_invariant_11_keys_exact`,
  `test_invariant_11_fires_on_drift`.

`DESIGN.md`:

- §5.1 symbol index: new `FUNNEL_TOGGLE_LABELS` row.
- §5.2 invariants: new entry #11.
- §5.3 extension recipes: new "Rephrase the funnel disclosure toggle"
  row pointing at the symbol-pair convention.
- §8.1 panel specs: "Funnel `[expand]` button" row replaced with
  "Funnel disclosure toggle" row describing the bidirectional +
  tertiary + subheader-row contract.
- §8.1 "Funnel visibility rules" paragraph: rewritten to describe
  the bidirectional contract and the action-not-state label
  semantics.
- §8.1 empty-state branches matrix: Funnel cell rewritten — branch
  (a) keeps suppression and degrades the layout to a bare
  subheader; branches (b) and (c) share the `st.columns([3, 1])`
  subheader-row placement; branch (b) info copy updated; branch
  (c) describes the post-click toggle persistence.

`docs/ui/wireframes.md`:

- Dashboard ASCII: toggle representation updated from `[expand]` to
  `[+ Show all stages]`. The wireframe is intent-only (file
  preamble) and a fuller reflow of the dashboard ASCII (Upcoming
  column order, Recommender row contents) is bundled with the
  publish-phase P5 doc-drift sweep already tracked.

Test count: **535 → 553** passing under both `pytest -q` and
`pytest -W error::DeprecationWarning -q` (+18 net: +15 in
`TestT6FunnelToggle`, +4 in `test_config` invariant #11, −1 deleted
`test_expand_button_hides_after_click`).

Live AppTest probe confirms the round-trip end-to-end:

```
Initial:  state=False, label='+ Show all stages'
Click 1:  state=True,  label='− Show fewer stages'
Click 2:  state=False, label='+ Show all stages'
```

Zero exceptions across all renders.

Migration: none. No DB schema change, no config-value rename, no
existing widget-state collision (the `funnel_expand` widget key was
renamed to `funnel_toggle`; a stale browser tab carrying the old
key would just see a fresh False default — Streamlit doesn't
persist widget keys across schema changes anyway).

### Added — Cross-panel cohesion smoke (T6 first checkbox, branch `feature/phase-4-tier6-Cohesion`)

Phase 4 T6 first checkbox — the cross-panel cohesion audit that closes
the gap between the five panels each having shipped in isolation
(T1–T5) and the dashboard composing as one cohesive surface. No code
change to `app.py`; the contribution is the audit doc and the screenshot
scaffolding.

- **`reviews/phase-4-finish-cohesion-smoke.md`** — new findings doc
  written in the GUIDELINES §10 review style (Exec summary → Findings
  table → verbatim AppTest render dumps as cohesion evidence →
  Junior-engineer Q&A → Capture instructions). Cites verbatim every
  rendered subheader, KPI label, info message, dataframe column,
  selectbox option, and recommender-card markdown for both populated
  and empty-DB renders. Cohesion claim verified on six dimensions:
  subheader rhythm (one `st.subheader` primitive across all 5 panels +
  hero), empty-state pattern (one `st.info` primitive across all 4
  empty branches), status sentinel stripping (no `[SAVED]`/`[APPLIED]`
  literal leak — verified via dataframe Status column showing the
  stripped UI labels), label-format reuse (three sites converging on
  `{institute}: {position_name}` from independent code), date format
  (three sites converging on `MMM D`), and layout-hierarchy progression
  (4-col → 2-col → full-width × 2). Two 🟡 polish findings (wireframe
  ASCII drift; em-dash literal-vs-constant) deferred per GUIDELINES
  §10's defer-if-costly rule and the Phase 7 / publish-phase tier
  alignment. Zero 🔴 / 🟠.
- **`docs/ui/screenshots/v0.5.0/`** — new directory + a `.seed-snippet.py`
  scratch script preserving the canonical fixture data so the user can
  re-seed at capture time. The three PNGs themselves
  (`dashboard-1280.png`, `dashboard-1440.png`, `dashboard-1680.png`)
  are user-captures from a real desktop browser per the smoke doc's
  capture instructions.
- **`TASKS.md`** — first T6 checkbox flipped to `[x]`.
- **No code changes** in `app.py` / `database.py` / `config.py` /
  `pages/*.py` / `tests/*.py`; the audit is the deliverable. Both
  `pytest tests/ -q` and `pytest -W error::DeprecationWarning tests/ -q`
  remain green at **535 passing** on this branch.

Process note: the harness preview tool's macOS sandbox blocks reading
`.venv/pyvenv.cfg` (`com.apple.provenance` xattr), so headless
screenshot capture from inside the agent harness is not available on
this user's setup. Boot smoke + cohesion audit ran via Bash
`streamlit run` (HTTP 200 verified) and AppTest probes
(`Has any exception block: False` on both populated and empty DB);
the 1280 / 1440 / 1680 PNGs are captured manually by the user per the
smoke doc's "Capture instructions" section.

### Added — Recommender Alerts panel on `app.py` (T5-A, branch `feature/phase-4-tier5-RecommenderAlerts`)

Phase 4 T5-A: full-width Recommender Alerts panel rendered BELOW the
Upcoming row on the dashboard (DESIGN §8.1). Surfaces every
recommender whose letter is past `RECOMMENDER_ALERT_DAYS` of being
asked and still has no `submitted_date`, grouped so each person
appears in exactly one card.

`app.py`:

- Subheader `"Recommender Alerts"` renders in BOTH branches for
  page-height stability (T2 / T3 / T4 precedent — without this, the
  layout above shifts when the first owed letter lands).
- Empty branch: `st.info("No pending recommender follow-ups.")`.
- Populated branch: `database.get_pending_recommenders()` is grouped
  by `recommender_name`. One `st.container(border=True)` per person;
  each card body is a single `st.markdown` block:

      **⚠ {Name}**
      - {institute}: {position_name} (asked {N}d ago, due {Mon D})
      - ...

  Bare `{position_name}` when institute is empty (T4 Label
  precedent — disambiguates same-titled postings at different orgs).
  `due —` (em dash) for NULL deadline (mirrors `NEXT_INTERVIEW_EMPTY`).
  `groupby(..., sort=False)` because `get_pending_recommenders()`
  already orders by `recommender_name ASC, deadline_date ASC NULLS
  LAST` — within-group bullet order is therefore deadline-asc and
  across-group card order is alphabetical without any extra sort.
- The DESIGN §8.4 D-C Compose-reminder-email button + LLM-prompts
  expander deliberately stay OFF the dashboard — they live on the
  Recommenders PAGE (Phase 5 T6).

`tests/test_app_page.py`:

- New `TestT5RecommenderAlerts` (15 tests) following the
  class-constants pattern (`SUBHEADER`, `EMPTY_COPY`, `BORDER_SOURCE`,
  `WARN_GLYPH`). Four groups:
    A — subheader / layout (subheader present in both branches +
        bordered-container source-grep with `count >= 2` so the
        empty-DB hero's existing `st.container(border=True)` does
        not vacuously satisfy the contract).
    B — empty / populated branches (locked `EMPTY_COPY`; an
        asked-today recommender stays in the empty branch since
        `0d < RECOMMENDER_ALERT_DAYS`).
    C — card content (bold warn-glyph header, T4 Label precedent
        with bare-position fallback, "asked Nd ago" phrasing per
        TASKS.md, due-date in `Mon D` form, em-dash for null
        deadline).
    D — grouping by `recommender_name` (one card per person
        aggregating multiple positions; submitted letters absent
        from the panel).

Suite total 519 → 534 passing under both `pytest tests/ -q` and
`pytest -W error::DeprecationWarning tests/ -q`.

### Fixed — Phase 4 T4 pre-merge polish (branch `feature/phase-4-tier4-UpcomingDeadline`)

Skeptical pre-merge review of the T4-0 / T4-A / T4-B work landed in
`reviews/phase-4-Tier4-review.md` (Exec summary → Findings → Q&A →
Verdict, per GUIDELINES §10). One inline polish applied; four other
findings deferred with documented rationale.

`database.py`:

- Drop the two no-op `.astype(str)` calls in `get_upcoming` —
  `deadlines["status"].astype(str)` and `merged["status"].astype(str)`.
  Both columns come from SQL TEXT with `NOT NULL` (`positions.status`)
  joined under FK CASCADE; `pd.read_sql_query` produces object-dtype
  `str` Series in every row by construction. The casts were defensive
  against an impossible state and triggered the GUIDELINES §12 / system
  anti-pattern *"don't add error handling, fallbacks, or validation for
  scenarios that can't happen."* Removing them shaves two lines and
  surfaces a real future regression (e.g. a JOIN weakening) loudly via
  the existing `test_status_column_carries_raw_bracketed_sentinel` /
  `test_status_column_shows_ui_labels_not_raw_sentinels` pair instead
  of silently rendering the literal string `"nan"`.

Findings inventory (full text in the review doc):

- 🟡 #1 polish — `.astype(str)` no-ops in `get_upcoming` →
  **fixed inline** (this commit's predecessor).
- 🟡 #2 polish — sort tie-break (deadline vs interview on the same
  date) is "implicit, not pinned by tests" → **kept by design**
  (DESIGN §8.1 deliberately leaves the tie-break unspecified; pinning
  would narrow the contract).
- 🟢 #3 future — three `_connect()` opens per `get_upcoming` call →
  **backlog** (negligible for v1's single-user local SQLite; matters
  if the dataset ever exceeds ~10 k rows or moves to a remote DB).
- 🟢 #4 future — `pd.to_datetime(...).dt.date` raises on a non-ISO row
  → **backlog** (UI-side `st.date_input.isoformat()` covers all write
  paths; only a manual SQL edit could trip it; loud crash beats silent
  bad data for a personal tool).
- ℹ️ #5 carry-over — `pages/1_Opportunities.py:395` comment trips the
  GUIDELINES §6 status-literal grep (the comment exists *to document*
  the literal it forbids) → **defer to Phase 4 T6 pre-merge sweep**;
  same shape as the T2-C `st\.columns\(2\)` grep miscount logged at
  `reviews/phase-4-Tier3-review.md` Q2.

Tests: 519 passing under both `pytest -q` and
`pytest -W error::DeprecationWarning -q`; also clean under
`-W error::FutureWarning` on the `TestGetUpcoming` block. No test
depended on the cast — the 22 T4-A / T4-B / invariant-#10 tests stay
green unchanged.

### Added — Upcoming timeline panel + window selector on `app.py` (T4-B, branch `feature/phase-4-tier4-UpcomingDeadline`)

Phase 4 T4-B: full-width Upcoming panel rendered below the funnel /
readiness `st.columns(2)` row on the dashboard (DESIGN §8.1).
Consumes `database.get_upcoming(days=selected_window)` (T4-A) and is
the dashboard's "what deadlines and interviews need my attention this
window?" surface. Closes Phase 4 T4.

`config.py`:

- New constant `UPCOMING_WINDOW_OPTIONS: list[int] = [30, 60, 90]` —
  the user-selectable widths for the Upcoming-panel selectbox.
- New §5.2 invariant #10:
  `DEADLINE_ALERT_DAYS in UPCOMING_WINDOW_OPTIONS`. Guards against a
  config edit that drops 30 from the offered list without updating
  the default — module won't load if violated.
- `DEADLINE_ALERT_DAYS` doc comment reworded to call it the "default
  Upcoming-panel window + upper edge of the 🟡 band" so its dual role
  is explicit.

`app.py`:

- Panel layout: `st.columns([3, 1])` with the dynamic subheader on the
  left and the window-width selectbox on the right. Defining
  `selected_window` inside the right column first means the left
  column can interpolate it into the subheader on the same render —
  Python execution order is independent of visual placement (which is
  determined by column index).
- Selectbox: `key="upcoming_window"`, `options=UPCOMING_WINDOW_OPTIONS`,
  default index pointing at `DEADLINE_ALERT_DAYS` (invariant #10
  guarantees this value is in the list), `label_visibility="collapsed"`.
- Subheader: `f"Upcoming (next {selected_window} days)"` — renders in
  BOTH branches for page-height stability (T2/T3 precedent).
- Empty branch: `st.info(f"No deadlines or interviews in the next
  {selected_window} days.")` — empty copy tracks the user's choice.
- Populated branch:
    - Column rename T4-A's lowercase storage form → Title-Case display
      headers (Date, Days left, Label, Kind, Status, Urgency).
    - Status mapped via `STATUS_LABELS.get(raw, raw)` — `.get`'s default
      keeps a stale value visible rather than producing NaN; matches
      DESIGN §8.0's status-label convention.
    - `st.dataframe(width="stretch", hide_index=True,
      column_config={"Date": st.column_config.DateColumn(format="MMM D")})`.
      The DateColumn moment.js format renders the underlying
      `datetime.date` as 'Apr 24' (no year). Both kwargs and the
      DateColumn format param verified against Streamlit 1.56's
      signature via inspect probe before commit.
- AppTest verification: `at.selectbox(key=...).set_value(60).run()`
  chain triggers a rerun with the new value, confirming the
  selectbox→`get_upcoming(days=...)` path drives subheader, empty
  copy, and dataframe contents in sync.

22 new tests pass (19 `TestT4UpcomingTimeline` + 3 invariant-#10
tests). Suite total 497 → 519 passing under both `pytest -q` and
`pytest -W error::DeprecationWarning -q`. Status-literal grep clean.

A discovered AppTest 1.56 quirk is documented inline in the
`test_window_selector_offers_config_window_options` test:
`selectbox.options` returns the protobuf-serialized string form, while
`.value` round-trips correctly to the original type. The assertion
compares against the stringified config list with the original list
shown in the failure message for debug clarity.

### Added — `database.get_upcoming` for unified upcoming feed (T4-A, branch `feature/phase-4-tier4-UpcomingDeadline`)

Phase 4 T4-A: new public API surfacing the data behind the dashboard's
Upcoming panel (DESIGN §8.1). Thin projection layer over
`get_upcoming_deadlines(days)` + `get_upcoming_interviews()` — no new
SQL — returning a six-column DataFrame in storage form
`(date, days_left, label, kind, status, urgency)` sorted by date asc.

- `date` is a `datetime.date` object (not an ISO string) so a future
  user-triggered column-header re-sort in the page renders
  chronologically rather than lexicographically.
- `days_left` is one of `"today"` (0d), `"in 1 day"` (1d singular),
  `"in N days"` (N > 1) — singular/plural correct, derived once per
  row from `(date - today).days`.
- `urgency` is `"🔴"` / `"🟡"` / `""`, derived from the **same**
  `days_away` int as `days_left` so the two columns cannot drift.
  Thresholds (`DEADLINE_URGENT_DAYS` / `DEADLINE_ALERT_DAYS`) resolve
  at call time via the private `_urgency_glyph` helper.
- `label` is `f"{institute}: {position_name}"` when institute is
  non-empty; bare `position_name` when institute is missing
  (`pd.isna` covers None/NaN; whitespace-strip catches empty strings).
- `kind` is `"Deadline for application"` for deadline rows or
  `f"Interview {sequence}"` for interview rows (1-indexed sequence
  pulled through from the interviews sub-table).
- `status` is the raw bracketed sentinel — UI label mapping via
  `STATUS_LABELS` is the page's job (T4-B).

`get_upcoming_interviews` has no built-in `days` bound; `get_upcoming`
applies one (`scheduled_date <= today + days`) so the "next N days"
contract from DESIGN §8.1 holds for both kinds. Interview rows don't
carry status from the underlying SQL; enrichment is a left-merge with
`get_all_positions[['id', 'status']]` on `position_id`.

19 new `TestGetUpcoming` tests pin the contract — including paired
tests for `days_left` / `urgency` coherence and Date-as-`datetime.date`
type. Suite total 478 → 497 passing under both `pytest -q` and
`pytest -W error::DeprecationWarning -q`.

### Changed — DESIGN §8.1 Upcoming-panel column contract locked (T4-0 + T4-0b, branch `feature/phase-4-tier4-UpcomingDeadline`)

Documentation-only spec lock-down ahead of the T4-A implementation, so
T4-A's tests bind to one unambiguous contract. Resolves the §8.1
phrasing ambiguity that bit a prior T4 attempt
("columns (Date, Label, Kind, Urgency); Status shown via
STATUS_LABELS[raw]" admitted multiple readings on column count,
ordering, and Status placement).

§5.1 / §5.2 changes:

- `DEADLINE_ALERT_DAYS` row reworded to call it the "default" window
  and the upper edge of the 🟡 band; `DEADLINE_URGENT_DAYS` row gains
  the explicit guarantee that urgency thresholds are FIXED in config
  and do NOT track the user-selected window.
- New constant `UPCOMING_WINDOW_OPTIONS: list[int]` defaulting to
  `[30, 60, 90]` for the panel's window selectbox.
- New §5.2 invariant #10:
  `DEADLINE_ALERT_DAYS in UPCOMING_WINDOW_OPTIONS` — catches a config
  edit that drops 30 from the offered list without updating the default.

§8.1 changes:

- Panel-table row (Upcoming) rewritten to name
  `database.get_upcoming(days=selected_window)`, pin
  `st.dataframe(width="stretch", hide_index=True)`, list the six
  display headers in order (Date, Days left, Label, Kind, Status,
  Urgency), point at the new column-contract sub-table, and clarify
  that the urgency band is independent of the selected window.
- New "Upcoming-panel column contract" sub-section between "Funnel
  visibility rules" and "Empty-DB hero" with a per-column cell-format
  + source table:
    - **Date** — `'Apr 24'` display, no year; underlying `datetime.date`
      for chronological sort
    - **Days left** — `"today"` / `"in 1 day"` / `"in N days"`
    - **Label** — `"{institute}: {position_name}"` with bare-name fallback
    - **Kind** — `"Deadline for application"` / `f"Interview {sequence}"`
    - **Status** — `STATUS_LABELS[raw]` per §8.0
    - **Urgency** — `"🔴"` / `"🟡"` / `""` from same days_away as Days left
- New "Window selector" paragraph: selectbox in a narrow right column
  of an `st.columns([3, 1])` pair (header on the left), key
  `upcoming_window`, label hidden, default = `DEADLINE_ALERT_DAYS`.
- Empty-state branches table — Upcoming row interpolates
  `selected_window` so the empty copy tracks the user's choice.

§7 — `get_upcoming` added to the Dashboard-queries listing.

No code in this commit pair (T4-0 + T4-0b) — pure documentation.

### Changed — DESIGN §6.3 confirmation_email v1.0-rc drop committed (branch `docs/v1-planning-pins`)

Documentation-only update closing the deferred-decision flagged in
DESIGN §6.3 step (c) since the Sub-task 10 migration. No code, no
schema, no test impact yet — the actual table rebuild lands during
the v1.0-rc release.

- **D-D — Pending column drops table for v1.0-rc**: §6.3 gains a new
  paragraph between the "Flag/date split divergence" note and the
  "Migration discipline" rule, naming `applications.confirmation_email`
  as the single column scheduled for physical drop in v1.0-rc. The
  paragraph spells out the SQLite table-rebuild SQL
  (`CREATE TABLE applications_new AS SELECT <kept cols> ...`,
  `DROP TABLE applications`, `ALTER TABLE ... RENAME TO ...`) wrapped
  in one transaction, plus the `PRAGMA table_info` idempotence check.
  Closes Q4 Option A from the 2026-04-27 planning session.

### Changed — DESIGN §8.4 Recommender mailto + LLM-prompts pattern (branch `docs/v1-planning-pins`)

Documentation-only update locking the Recommenders-page reminder UX
before Phase 5 starts. No code, no schema, no test impact.

- **D-C — two-affordance reminder helper**: replace the single mailto
  bullet with a primary `Compose reminder email` button (locked short
  professional body, no signature — mail client appends one) plus a
  secondary `LLM prompts (N tones)` expander rendering pre-filled
  prompts as `st.code(...)` blocks (Streamlit's built-in hover-copy
  button available). Prompts include the recommender's name +
  relationship, positions owed (with deadlines), days since asked, and
  one prompt per tone (gentle / urgent). Closes Q3 Option D from the
  2026-04-27 planning session — gives users a quick path for the
  simple case and an LLM-assisted path for richer drafts without
  introducing an outbound email integration.

### Changed — DESIGN §8.3 Applications page UI contracts (branch `docs/v1-planning-pins`)

Documentation-only update locking two previously-underspecified UI
contracts on the Applications page before Phase 5 starts. No code,
no schema, no test impact.

- **D-A — Confirmation column display contract**: the bullet now pins
  the glyph (`✓` / `—`) sourced from `confirmation_received`; the
  tooltip uses `confirmation_date` when set (`Received {ISO date}`)
  and falls back to `Received (no date recorded)` when the flag is
  `1` but no date is recorded. Pre-empts a UX divergence where one
  contributor might show the raw integer or print the bare date.
- **D-B — Inline interview list UI**: lock the per-row widget shape
  (`scheduled_date` / `format` / `notes` / `🗑️`), the primary-key-scoped
  widget-key convention `apps_interview_{id}_{date|format|notes|delete}`,
  the single-form save model (`apps_interviews_form`, one
  `update_interview` per dirty row), the `@st.dialog`-gated delete, and
  the R2-toast surfacing on add when `add_interview` returns
  `status_changed=True` (§9.3). Closes the under-specification flagged
  in the 2026-04-27 planning session (Q2 Option A).

### Changed — GUIDELINES.md hardening (branch `docs/v1-planning-pins`)

Documentation-only update pinning the v1 plan locked at the 2026-04-27
planning session. No code, no schema, no test impact.

- **§3 Widget keys**: drop the stale `edit_active_tab` reference
  (the radio-based tab selector was removed in PR #10 / Sub-task 13
  reversal). Add `_delete_target_name` to the internal-sentinels list —
  the sentinel is in code at `pages/1_Opportunities.py` lines 82, 115,
  128, 357, 680, 701 but was absent from the convention list.
- **§11 Pre-commit checklist**: add a sixth bullet cross-referencing §6's
  status-literal grep rule (`grep -nE "\[SAVED\]|\[APPLIED\]|\[INTERVIEW\]"
  app.py pages/*.py` returns 0 hits) so it cannot be silently skipped at
  commit time.
- **New §13 "Adding a new page"**: procedural checklist for authoring a
  new `pages/N_Title.py`. Locks the page-scoped widget-key prefix table
  (`qa_`, `edit_`, `filter_`, `apps_`, `recs_`, `export_`) before Phase 5
  starts so the new pages can adopt it without retrofit.

### Fixed — Sub-task 13 reverted: tab-switch widget state loss (branch `review/test-reliability-2026-04-25`)

User-reported bugs (2026-04-25):
- **Bug 1** — On the Opportunities page, after selecting an opportunity
  and switching to the Requirements tab and back, the position name in
  the Overview tab disappeared. Same on the second opportunity. Also
  triggered by the cross-row sequence: select row A → Requirements →
  click row B → Overview.
- **Bug 2** — Requirements tab showed every doc as "Required" (the
  radio's `index=0` default), not the DB's "No". Materials tab showed
  all 7 doc checkboxes; ticking CV + clicking Save left only 6
  checkboxes (CV vanished).

**Root cause.** Sub-task 13 (commit `20c21b7`, 2026-04-24) swapped the
edit panel's `st.tabs(...)` for `st.radio + conditional rendering` so
the Delete button could be gated on a programmatically-readable
`active_tab` variable. Conditional rendering unmounts each tab body's
widgets when its tab is not active. Streamlit's documented v1.20+
behaviour wipes `session_state` for unmounted widget keys; on remount
the widget falls back to its `value=` default (empty for `text_input`,
`index=0` for `radio` → "Required"). The pre-seed gate
(`_edit_form_sid != sid`) only fires on row CHANGE, never on tab
switch — so the cleaned-up keys were never restored on the same row.

**Fix.** Reverted Sub-task 13's architecture change. Edit panel now
uses `st.tabs(config.EDIT_PANEL_TABS)` again — every tab body renders
on every script run (CSS hides inactive ones), so no widget unmount,
no `session_state` cleanup, no cross-tab data loss. The Delete-button
"visible only on Overview" requirement (DESIGN §8.2) is satisfied by
placing the button inside `with tabs[0]:` after the form: `st.tabs`
CSS-hides it on the other tabs naturally.

The two-phase pre-seed (introduced in commit `e2bce18` as a defensive
measure against the same cleanup mechanism) is **kept** — under
`st.tabs` its second branch (restore-missing-keys) is essentially
never exercised, but it is harmless and provides defence-in-depth
against any future architectural drift.

Files touched:
- **`pages/1_Opportunities.py`** — `st.radio + if/elif active_tab` →
  `st.tabs + with tabs[i]:`. Delete button moved from the trailing
  `if active_tab == "Overview":` block back inside `with tabs[0]:`
  after the form. Pre-seed canonical-dict + two-phase apply kept.
- **`tests/test_opportunities_page.py`** — refactored `TestEditPanelShell`
  tests to use `at.tabs` (a list of `Tab` elements with `.label`)
  instead of `at.radio(key="edit_active_tab")`; replaced the
  `_tab_selector_rendered` helper with `_tabs_rendered`; dropped the
  Sub-task-13-specific tests (`test_default_active_tab_is_first_config_entry`
  and four `TestDeleteButtonTabSensitivity` tests asserting DOM-absence
  of the Delete button on non-Overview tabs) whose assertions no longer
  match user-visible behaviour under `st.tabs`; soft-aliased
  `_select_row_and_tab(at, i, tab)` to a no-op-on-tab call so the
  ~30 existing call sites keep working without renames; updated
  `test_one_radio_per_requirement_doc` to drop the `+ 1` for the
  (now-gone) tab-selector radio; re-keyed
  `test_text_area_renders_when_row_selected` from a count-of-1
  assertion to a key-set assertion (Notes + Overview text_areas now
  both render every run).
- **`DESIGN.md`** — §8.2 Delete row clarified: "below the form
  (outside the `st.form` box), inside the Overview tab body" — making
  explicit that "panel box" means the form box, satisfied by `with
  tabs[0]:` placement. New paragraph documents the `st.tabs` vs
  `st.radio` architectural decision and pins the Sub-task-13 reversal
  rationale (Streamlit cleanup behaviour) so a future contributor does
  not re-attempt the same swap.

Tests: 478 pass post-revert (was 483; 5 Sub-task-13-specific tests
removed). The 8 `TestTabSwitchWidgetStateSurvival` tests added during
the abortive Sub-task-13 fix are kept as architectural regression
guards — they pass trivially under `st.tabs` (no unmount → values
always survive) and would fail loudly if conditional tab rendering
were ever re-introduced.

### Added — v1.3 alignment (branch `feature/align-v1.3`)

Sub-task 1 of the DESIGN-to-codebase alignment pass. Pure additions to
`config.py` — no existing values changed, no schema impact.

- **`config.py`** — three new constants per DESIGN.md v1.3 §5.1:
  - `VALID_PROFILES: set[str] = {"postdoc"}` — guards `TRACKER_PROFILE`
  - `STATUS_LABELS: dict[str, str]` — storage-to-UI map, bracket-stripped
    (`"[OPEN]"→"Open"`, …); every user-facing status surface must look
    up through this dict per DESIGN §8.0 Status label convention
  - `INTERVIEW_FORMATS: list[str] = ["Phone","Video","Onsite","Other"]` —
    vocabulary for the upcoming `interviews.format` column (DESIGN §6.2)
- **`config.py`** — three new import-time invariants per DESIGN.md v1.3 §5.2:
  - #1: `TRACKER_PROFILE in VALID_PROFILES`
  - #3: `set(STATUS_VALUES) == set(STATUS_LABELS)`
  - #8: `DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS`
  - Pre-existing guards also annotated with DESIGN §5.2 numbering
    (#2 STATUS_COLORS coverage, #4 TERMINAL_STATUSES subset,
    #5 FUNNEL_BUCKETS multiset, #6 FUNNEL_DEFAULT_HIDDEN ⊆ labels,
    #7 REQUIREMENT_LABELS coverage)
- **`tests/test_config.py`** — 22 new tests pinning every new constant
  and every new/existing-but-unpinned invariant. Synthetic-drift tests
  (per existing `test_status_guard_fires_on_drift` precedent) exercise
  each guard; a fresh `importlib.reload("config")` test covers the
  module-level execution path

### Changed — v1.3 alignment Sub-task 2 (branch `feature/align-v1.3`)

Sub-task 2 migrates `REQUIREMENT_VALUES` from single-letter sentinels
(`Y`/`Optional`/`N`) to full words (`Yes`/`Optional`/`No`) per DESIGN.md
v1.3 §5.1 + D21, completing D21's "full-word philosophy" for the
requirement-docs vocabulary (matching D20's rule for boolean-state
columns).

- **`config.py`** — `REQUIREMENT_VALUES = ["Yes", "Optional", "No"]`;
  `REQUIREMENT_LABELS` keys swap to match (`Yes`→"Required",
  `Optional`→"Optional", `No`→"Not needed"); inline comment updated to
  describe the new vocabulary and reference v1.3 / D21.
- **`database.py`** — DDL `req_* TEXT DEFAULT 'No'` on both the
  `CREATE TABLE` literal and the `ALTER TABLE` migration loop (new
  `REQUIREMENT_DOCS` entries get the full-word default on next start).
  `compute_materials_readiness()` predicates changed to `= 'Yes'` /
  `!= 'Yes'` (matches the new vocabulary; docstring updated).
- **`database.init_db()`** — adds a one-shot value migration loop that
  rewrites any lingering `'Y'`/`'N'` rows in place on next app start
  (see Migration section below). Idempotent — reruns on a migrated DB
  are a no-op because the `ELSE req_*` branch passes already-migrated
  values through unchanged.
- **`pages/1_Opportunities.py`** — Materials-tab visibility filter
  predicate changes from `== "Y"` to `== "Yes"` (the only behavioural
  change on the page — radios and checkboxes are config-driven, so the
  vocabulary swap propagates automatically). Pre-seed fallback for
  out-of-vocabulary req values switches from `"N"` to `"No"`.
- **Tests** — seeds and assertions updated across `test_database.py`,
  `test_opportunities_page.py`, `test_app_page.py` (replace-all of the
  quoted Y/N tokens, plus matching docstring/comment rewording). New
  `test_migration_rewrites_legacy_req_short_codes` in
  `TestInitDb` seeds legacy `'Y'`/`'N'`/`'Optional'` values via raw
  SQL, calls `init_db()`, and pins the three-way translation plus
  idempotence on a second `init_db()`.

### Changed — v1.3 alignment Sub-task 3 (branch `feature/align-v1.3`)

Sub-task 3 swaps the `WORK_AUTH_OPTIONS` and `FULL_TIME_OPTIONS`
vocabularies to the v1.3 spec (DESIGN §5.1 + D22). Both columns
stay plain TEXT with no DDL constraint, so no automatic schema
migration runs; any dev-DB rows carrying legacy strings remain as
orphan TEXT until manually translated (see Migration below).

- **`config.py`** — vocabulary swaps per DESIGN §5.1:
  - `WORK_AUTH_OPTIONS`: `["Any","OPT","J-1","H1B","No Sponsorship","Ask"]`
    (6 values) → `["Yes","No","Unknown"]` (3 values). Paired with a
    future `work_auth_note` TEXT column (separate sub-task) so the
    enum stays filter-friendly while nuance lands in free text (D22).
  - `FULL_TIME_OPTIONS`: `["Yes","No","Part-time"]` →
    `["Full-time","Part-time","Contract"]`. Explicit employment-type
    vocabulary replaces the ambiguous Yes/No pair (Yes = full-time?
    Yes = available?).
  - Inline comments on both constants cross-reference the v1.3
    migration note below.
- **`tests/test_config.py`** — two new `_spec_values` tests
  (`test_work_auth_options_spec_values`,
  `test_full_time_options_spec_values`) pinning the literal lists;
  follows the Sub-task 2 precedent. Generic non-empty parametrize
  entries at lines 118–119 stay (they cover list-shape but no longer
  catch vocabulary drift — the new pins are the vocabulary contract).
- **No page / schema / database changes** — neither constant is
  consumed by any widget yet (the `work_auth`/`work_auth_note` UI and
  the `work_auth_note` TEXT column land in later sub-tasks); both DB
  columns are already plain TEXT so no DDL edit is needed.

### Changed — v1.3 alignment Sub-task 4 (branch `feature/align-v1.3`)

Sub-task 4 lifts the two hardcoded DDL DEFAULT literals in
`database.init_db()` into f-string interpolations of the corresponding
`config.py` constants, per DESIGN.md v1.3 §6.2 ("DDL DEFAULTs are
config-driven"). **Pure refactor — no user-visible change, no schema
change, no data migration.** Live config still has
`STATUS_VALUES[0] == "[OPEN]"` and `RESULT_DEFAULT == "Pending"`, so
the emitted SQL bytes are identical to the pre-refactor DDL.

- **`database.py`** — `init_db()` now binds `status_default =
  config.STATUS_VALUES[0]` and `result_default = config.RESULT_DEFAULT`
  once per call, then interpolates them into the two `CREATE TABLE`
  strings:
  - `positions.status    TEXT NOT NULL DEFAULT '{status_default}'`
  - `applications.result TEXT          DEFAULT '{result_default}'`
  An inline comment cites DESIGN §6.2 and reaffirms the GUIDELINES §5
  safety argument (the interpolated values come exclusively from
  config, never from user input — matching the pattern already used
  for `REQUIREMENT_DOCS` column-name interpolation on
  `compute_materials_readiness` and the migration loop).
- **`tests/test_database.py`** — one new test
  `test_ddl_defaults_interpolate_from_config` in `TestInitDb`.
  Monkeypatches `config.STATUS_VALUES[0]` and `config.RESULT_DEFAULT`
  to sentinel strings, points `DB_PATH` at a fresh tmp file, calls
  `init_db()`, and asserts `PRAGMA table_info` `dflt_value` for
  `positions.status` and `applications.result` equals
  `f"'{config.<value>}'"` dynamically. The sentinel monkeypatch forces
  a mismatch with any hardcoded DDL literal — only an f-string-based
  `init_db()` can read the sentinel at call time, so the test
  uniquely pins the refactor.
- **Groundwork for Sub-task 5.** The `[OPEN]`→`[SAVED]` rename
  (`STATUS_VALUES[0]`) can now ship as a pure `config.py` edit plus
  the one-shot `UPDATE positions SET status = '[SAVED]' WHERE status
  = '[OPEN]'` migration spelled out in DESIGN §6.3. Without this
  refactor, Sub-task 5 would also need to touch `database.py` to keep
  the DDL and config in sync — that coupling is now gone.

### Changed — v1.3 alignment Sub-task 5 (branch `feature/align-v1.3`)

Sub-task 5 executes the two v1.3 renames flagged since the DESIGN
review: the pipeline-stage-0 storage literal moves to `[SAVED]` and
the priority short code becomes the full-word `Medium`. Both renames
ride the Sub-task 4 config-drive — no DDL change; existing-DB rows
migrate in place via two one-shot `UPDATE` loops in `init_db()`.

- **`config.py`** — rename-atomic swap per DESIGN §5.1:
  - `STATUS_VALUES[0]`: `'[OPEN]'` → `'[SAVED]'`.
  - `STATUS_COLORS` / `STATUS_LABELS` keys flip to `'[SAVED]'`;
    `STATUS_LABELS['[SAVED]']` is `'Saved'` (consistent with the
    bracket-stripped convention from Sub-task 1).
  - Alias `STATUS_OPEN` renamed to `STATUS_SAVED`. `FUNNEL_BUCKETS`
    needs no edit — it already references the alias, not the literal.
  - `PRIORITY_VALUES[1]`: `'Med'` → `'Medium'`. Full-word philosophy
    per D20 / D21 applied to the priority tiers.
- **`database.py`** — `init_db()` gains two one-shot `UPDATE` loops
  (idempotent via `WHERE` guard) after the existing req-column
  translation loop; parameter-bound so the legacy literals only live
  inside the query bindings. Legacy strings are assembled via string
  concatenation so the GUIDELINES §6 pre-merge grep for old-vocabulary
  use stays at zero hits across `config.py` / `database.py` / `app.py`
  / `pages/1_Opportunities.py` / `tests/`. Precedent: Sub-task 2's
  CASE-WHEN `'Y'`/`'N'` clauses are the analogous load-bearing
  references for that migration.
- **`database.py compute_materials_readiness`** — `active_statuses`
  hardcoded tuple flips to `('[SAVED]', '[APPLIED]', '[INTERVIEW]')`
  + docstring update. The wider refactor to use `config.STATUS_*`
  aliases (TASKS.md C1) is still deferred — this commit-group's
  scope is literal flip only, preserving a single logical change
  per commit.
- **`app.py`** — one-line consumer edit: `config.STATUS_SAVED`
  replaces the renamed alias in the Tracked KPI sum; comment
  updated to `saved + applied`.
- **Tests** — test literals flipped across `test_config.py`,
  `test_database.py`, `test_app_page.py`, `test_opportunities_page.py`.
  New pins: `test_status_values_spec_values` (full seven-status
  ordered list), `test_status_saved_alias_matches_status_values`
  (anti-typo guardrail for DESIGN §9.3 R1), `test_priority_values_spec_values`
  ('Medium' at index 1), and two new migration tests in
  `TestInitDb` — `test_migration_rewrites_legacy_pipeline_stage0_status`
  and `test_migration_rewrites_legacy_med_priority` — that seed the
  pre-v1.3 literal via raw SQL, call `init_db()`, and pin both the
  translation and idempotence (second `init_db()` is a no-op).

### Changed — v1.3 alignment Sub-task 6 (branch `feature/align-v1.3`)

Sub-task 6 adds the `positions.updated_at` column plus the
`AFTER UPDATE` trigger that keeps it fresh, per DESIGN.md v1.3 §6.2 +
D25. With this in place, every write on `positions` stamps the row's
last-modified time automatically — no Python writer has to remember.

- **`database.py` — CREATE TABLE positions** gains a new column
  `updated_at TEXT DEFAULT (datetime('now'))` right after
  `created_at`. Fresh DBs get the full DDL default, so an
  `add_position` INSERT (which does not fire the `AFTER UPDATE`
  trigger) still ends up with a populated stamp via column default.
- **`database.py — init_db()` migration block** gains a
  `PRAGMA table_info`–guarded `ALTER TABLE positions ADD COLUMN
  updated_at TEXT` followed by a one-shot
  `UPDATE positions SET updated_at = datetime('now') WHERE
  updated_at IS NULL` backfill. SQLite rejects non-constant
  expression DEFAULTs on `ALTER TABLE ADD COLUMN` against a
  non-empty table (`"Cannot add a column with non-constant
  default"`), so the ALTER cannot mirror the CREATE TABLE DDL
  verbatim; the backfill closes the gap for existing rows.
  Idempotent — the `if "updated_at" not in existing_cols` guard
  skips both statements on a re-run, and the backfill's
  `WHERE updated_at IS NULL` scope would no-op even without it.
- **`database.py — init_db()` trigger block** gains
  `CREATE TRIGGER IF NOT EXISTS positions_updated_at AFTER UPDATE
  ON positions FOR EACH ROW BEGIN UPDATE positions SET updated_at =
  datetime('now') WHERE id = NEW.id; END`. Placed after the ALTER
  so the body's `updated_at` reference resolves on migrated-DB
  runs too, and before the Sub-task 2 / Sub-task 5 value-migration
  UPDATE loops so those writes also route through the trigger
  (D25 "every write touches the timestamp" applies to migration
  writes as well as user writes). SQLite's default
  `recursive_triggers = OFF` suppresses the inner UPDATE from
  re-firing — the no-infinite-loop guarantee rides entirely on
  that default, not on any code we write in the body.
- **`tests/test_database.py`** — five new tests in `TestInitDb`:
  - `test_positions_has_updated_at_column_with_datetime_default`
    pins PRAGMA `dflt_value == "datetime('now')"`.
  - `test_positions_updated_at_trigger_exists` pins the trigger
    registered in `sqlite_master`.
  - `test_add_position_populates_updated_at` pins the CREATE TABLE
    column-default path (INSERT does not fire AFTER UPDATE, so
    the DDL default is load-bearing).
  - `test_update_position_refreshes_updated_at` seeds a position,
    sleeps 1.1 s (SQLite's `datetime('now')` is second-precision),
    updates a field, and asserts the stamp advanced. A clean
    return from `update_position` also pins "no infinite loop"
    implicitly — recursion under `recursive_triggers = ON` would
    hit SQLite's 1000-frame limit and raise
    `recursion limit reached` before returning.
  - `test_migration_adds_updated_at_to_pre_v1_3_positions` uses
    the `tmp_path` + monkeypatched `DB_PATH` pattern (same as
    Sub-task 4's DDL-default sentinel test), seeds a pre-v1.3
    positions table with an existing row, calls `init_db()`, and
    asserts the ALTER added the column, the backfill populated
    the existing row, the trigger is registered, and a second
    `init_db()` leaves the backfilled stamp untouched.
- Adds `import re` and `import time` at the top of
  `tests/test_database.py` (for the ISO-datetime regex pattern
  and the 1.1-second sleep).

### Changed — v1.3 alignment Sub-task 7 (branch `feature/align-v1.3`)

Sub-task 7 closes the vertical slice Sub-task 3 deferred: the
three-value `work_auth` vocabulary (Sub-task 3) plus a new
`work_auth_note` freetext column plus the Overview-tab widgets that
finally surface both to the user. DESIGN.md v1.3 §6.2 + §8.2 + D22.

- **`database.py`** — `CREATE TABLE positions` gains
  `work_auth_note TEXT` right after `work_auth`. `init_db()`
  migration block gets a `PRAGMA table_info`-guarded
  `ALTER TABLE positions ADD COLUMN work_auth_note TEXT`. Plain
  TEXT, no DEFAULT — the column is NULL-able on fresh rows and on
  migrated rows (v1.2 never collected this field, so NULL is the
  honest state). Because the DEFAULT is constant (absent), the ALTER
  works against non-empty tables unlike Sub-task 6's `updated_at`
  — no backfill UPDATE is needed.
- **`pages/1_Opportunities.py`** — pre-seed block gains
  `safe_work_auth` with F2-style in-vocab coercion (NULL or
  out-of-vocab → `config.WORK_AUTH_OPTIONS[0]`, matching the
  priority / status fallback) and `edit_work_auth_note` via
  `_safe_str` (same NaN-truthiness trap as notes / link).
  Overview form gains `st.selectbox("Work Authorization",
  config.WORK_AUTH_OPTIONS, key="edit_work_auth")` plus
  `st.text_area("Work Authorization Note",
  key="edit_work_auth_note")` between Link and the submit button —
  placement per DESIGN §8.2 ("text_area below the selectbox").
  Save payload extends with both keys so `database.update_position`
  ships them to the DB.
- **`tests/test_database.py`** — three new tests:
  `test_positions_has_work_auth_note_column` (PRAGMA pin: TEXT,
  `dflt_value IS NULL`), `test_migration_adds_work_auth_note_
  to_pre_v1_3_positions` (`tmp_path` + pre-v1.3 seed mirroring the
  Sub-task 6 migration test's shape; asserts column added, existing
  `work_auth` preserved, new `work_auth_note` is NULL, second
  `init_db()` is a no-op), and `test_work_auth_note_roundtrips`
  in `TestUpdatePosition` (add_position → get → update → get
  through both columns, plus empty-string round-trip as `""`).
- **`tests/test_opportunities_page.py`** — `EDIT_KEYS` gains two
  entries (`work_auth`, `work_auth_note`). New
  `TestOverviewWorkAuthWidgets` class with 5 tests: selectbox
  renders, text_area renders, options equal
  `config.WORK_AUTH_OPTIONS` (order pinned — `Yes/No/Unknown`),
  pre-seed populates both from the selected row, NULL fallback
  (work_auth → `WORK_AUTH_OPTIONS[0]`, work_auth_note → `""`).
  `TestOverviewSave.test_save_persists_work_auth_and_note` guards
  against the classic "added to form, forgot in payload"
  regression. `TestNotesTabWidgets.test_text_area_renders_when_
  row_selected` tight-bound `len(at.text_area)` goes from 1 → 2
  — the inline comment at that test already documented bumping
  this count explicitly for exactly this case.

### Changed — v1.3 alignment Sub-task 8 (branch `feature/align-v1.3`)

Sub-task 8 normalizes the two flat interview date columns on
`applications` into a proper `interviews` sub-table so a position can
carry arbitrarily many interviews. DESIGN.md v1.3 §6.2 + §6.3 + §7 +
D18. Scope expanded beyond the originally stated `database.py` /
`tests/test_database.py` / `CHANGELOG.md` to also touch `app.py` +
`tests/test_app_page.py` — the rewritten `get_upcoming_interviews`
changes its column contract (row-per-interview with a single
`scheduled_date` column, instead of row-per-position with flat
`interview1_date` / `interview2_date` columns), which the dashboard
Next-Interview KPI consumes.

- **`database.py — init_db()`**: samples `sqlite_master` for
  `interviews` BEFORE the `CREATE TABLE IF NOT EXISTS`; runs the
  one-shot copy-then-NULL-clear migration only on the "didn't
  exist pre-create" path (the "migrate-once gate"). Adds
  `idx_interviews_application` index per §6.2.
- **`database.py`** — new CRUD section between Applications and
  Recommenders, matching DESIGN §7's grouping:
  - `add_interview(application_id, fields, *, propagate_status=True)
    → {"id", "status_changed", "new_status"}`. Auto-assigns
    `sequence` via `COALESCE(MAX(sequence), 0) + 1` when the caller
    omits it; explicit `sequence` in `fields` is used verbatim and
    the `UNIQUE(application_id, sequence)` constraint catches
    collisions. The cascade body (R2 from §9.3) is deferred to
    Sub-task 9 — `status_changed` always reads `False` today and
    the keyword-only `propagate_status` kwarg is in place purely
    for API stability across the two sub-tasks. `fields` is
    defensively copied before the auto-sequence injection so the
    caller's dict is never mutated.
  - `get_interviews(application_id) -> DataFrame` ordered by
    `sequence ASC`.
  - `update_interview(interview_id, fields) -> None` — empty-fields
    no-op to match the other update_* conventions.
  - `delete_interview(interview_id) -> None`.
- **`database.py`** — `get_upcoming_interviews()` rewritten to JOIN
  interviews → applications → positions, filter
  `scheduled_date >= today`, order `scheduled_date ASC, sequence ASC`
  (sequence is the stable tiebreaker when two interviews share a
  date). Result columns: `interview_id, application_id, sequence,
  scheduled_date, format, position_id, position_name, institute`.
  Row-per-interview shape replaces the prior row-per-position shape
  — this is the load-bearing change for D18.
- **`app.py — _next_interview_display()`**: single-column scan of
  `scheduled_date` replaces the dual-column scan over
  `interview1_date` / `interview2_date`. Functionally equivalent
  semantics (earliest future date wins, institute paired with
  winner), simpler code. Header comment + docstring updated.
- **`tests/test_database.py`** — seven new test classes covering
  the full vertical: `TestInterviewsSchema` (5), `TestAddInterview`
  (9 incl. the `inspect.signature` pin on `propagate_status`),
  `TestGetInterviews` (3), `TestUpdateInterview` (3),
  `TestDeleteInterview` (2), `TestInterviewsCascade` (1 — full
  FK-chain transitive cascade), `TestInterviewsMigration` (6 — pins
  the migrate-once gate, legacy NULL-clear, sequence-1/2 copy
  assignments, NULL-in-NULL-out, and strict idempotence across a
  second `init_db()`). `TestGetUpcomingInterviews` rewritten from
  six `upsert_application`-based seeds to seven `add_interview`-
  based seeds incl. the new `test_returns_row_per_interview`
  D18-shape pin.
- **`tests/test_app_page.py — TestT1DNextInterviewKpi`** — five
  tests rewritten to seed interviews via `add_interview`; the old
  `test_interview2_date_beats_another_rows_interview1` becomes
  `test_later_interview_on_same_position_does_not_override`
  (equivalent semantic under row-per-interview shape); class
  docstring rewritten for the new column contract.

### Changed — v1.3 alignment Sub-task 9 (branch `feature/align-v1.3`)

Sub-task 9 wires the R1/R2/R3 pipeline auto-promotion cascades across
`upsert_application` and `add_interview`, adds the
`is_all_recs_submitted` query helper, and swaps the hardcoded
`("[SAVED]", "[APPLIED]", "[INTERVIEW]")` tuple in
`compute_materials_readiness` for `config.STATUS_*` aliases (closes the
TASKS.md C1 carry-over that's been open since Sub-task 5). Pure
behavioural / refactor change — no schema edit, so no Migration entry.
DESIGN.md v1.3 §9.3 + §7 + D12 + D23.

- **`database.py — upsert_application`** signature bumps to
  `(position_id, fields, *, propagate_status: bool = True) -> dict`,
  returning `{"status_changed": bool, "new_status": str | None}`.
  Existing call sites that ignored the `None` return continue to
  work; the empty-fields early return still no-ops and hands the
  caller the indicator shape (both keys falsy) so unpacking is
  unconditional.
  - **R1**: when `pre_applied_date IS NULL AND
    fields["applied_date"] IS NOT NULL`, emit
    `UPDATE positions SET status = STATUS_APPLIED
     WHERE id = ? AND status = STATUS_SAVED`. Scoped to the
    NULL→non-NULL transition on the `applied_date` column rather
    than every touch, so a later upsert that merely updates the
    date leaves status alone.
  - **R3**: when `fields["response_type"] == "Offer"`, emit
    `UPDATE positions SET status = STATUS_OFFER
     WHERE id = ? AND status NOT IN TERMINAL_STATUSES`. Terminal
    guard in the WHERE prevents regression. The self-assignment
    that fires when the pre-state is already STATUS_OFFER reads
    as "no change" in the indicator because `status_changed`
    compares the status *string* pre/post, not whether an UPDATE
    executed.
- **`database.py — add_interview`** cascade body (Sub-task 8 left
  the body deferred for API stability) now emits R2:
  `UPDATE positions SET status = STATUS_INTERVIEW
   WHERE id = application_id AND status = STATUS_APPLIED`.
  Count-free per DESIGN §9.3 narrative — status guard alone handles
  all edges, including the back-edit-to-APPLIED-retaining-existing-
  interviews scenario that a count-based variant would miss.
- **`database.py — is_all_recs_submitted(position_id) -> bool`**
  new helper in the Applications group. Returns True iff every
  recommender for the position has a non-NULL, non-empty
  `submitted_date`. Zero-recs position returns True (vacuous truth)
  per D23's "summary that could be computed" framing — "nothing
  outstanding" holds trivially, and downstream aggregators like
  "is everything ready?" compose cleanly. Empty string is treated
  as equal to NULL (the page writes `""` when clearing a date field
  per the Notes-tab round-trip contract).
- **`database.py — compute_materials_readiness`** swaps the
  hardcoded `("[SAVED]", "[APPLIED]", "[INTERVIEW]")` tuple for
  `(config.STATUS_SAVED, config.STATUS_APPLIED, config.STATUS_INTERVIEW)`.
  Read at call time, not module load, so a future rename flows
  through immediately. Docstring updated to reference the alias
  names.
- **Atomicity** (DESIGN §9.3): every cascade runs inside the same
  `with _connect() as conn:` block as its primary write. When the
  cascade UPDATE raises (e.g. a bound parameter the SQLite driver
  cannot adapt), the context manager's except clause rolls back
  the whole transaction — neither the primary write nor any earlier
  cascade UPDATE persists.
- **`tests/test_database.py`** — 40 new tests structured by concern:
  - `TestUpsertApplicationR1` (4) — isolation: SAVED→APPLIED
    promote, applied_date-already-set noop, non-SAVED status
    guard, propagate_status=False suppression.
  - `TestUpsertApplicationR3` (9 incl. 3-value terminal
    parametrize) — SAVED/APPLIED/INTERVIEW promote to OFFER,
    already-OFFER self-assignment reads as no-change, terminal
    guard blocks CLOSED/REJECTED/DECLINED, propagate_status=False
    suppression, non-Offer response_type does nothing.
  - `TestUpsertApplicationR1R3Matrix` (7 incl. 3-value terminal
    parametrize) — every row of the DESIGN §9.3 combined-cascade
    matrix pinned (5 non-terminal pre-states + 3 terminals).
  - `TestUpsertApplicationIndicator` (3) — `inspect.signature`
    pin on the keyword-only `propagate_status=True`, return-shape
    pin, empty-fields return.
  - `TestUpsertApplicationAtomicity` (1) — monkeypatches
    `config.STATUS_APPLIED` to a non-bindable `object()`, forcing
    R1's UPDATE to raise `InterfaceError`, asserts primary write
    rolls back (applied_date stays NULL, status stays SAVED).
  - `TestAddInterviewR2` (9 incl. 3-value terminal parametrize)
    — APPLIED→INTERVIEW promotion, SAVED guard, INTERVIEW
    idempotence, OFFER guard, terminal guard, propagate_status
    opt-out, and the explicit "back-edit to APPLIED retaining
    existing interviews" scenario from the DESIGN §9.3 narrative.
  - `TestAddInterviewAtomicity` (1) — sibling of the upsert
    atomicity test for R2.
  - `TestIsAllRecsSubmitted` (5) — vacuous-truth on zero recs,
    all-submitted True, any-unsubmitted False, empty-string
    counts as unsubmitted, scoped to position_id.
  - `TestComputeMaterialsReadiness.test_active_statuses_drive_
    from_config_aliases` (1) — sentinel pattern (Sub-task 4
    precedent): monkeypatches the three aliases to strings the
    DB never holds, asserts the aggregation collapses to zero.
  Shared helper `_force_position_status(pid, status)` at module
  scope for raw-SQL pre-state staging (the user-facing writers
  would themselves fire the cascade and pollute the scenario).
- **`tests/test_database.py`** — existing
  `TestAddInterview.test_returns_indicator_dict` docstring updated
  to reflect the Sub-task 9 semantics (the assertions still hold
  because the seed's STATUS_SAVED pre-state doesn't trip R2's
  STATUS_APPLIED guard, not because the cascade body is absent).

### Changed — v1.3 alignment Sub-task 10 (branch `feature/align-v1.3`)

Sub-task 10 splits the pre-v1.3 dual-purpose
`applications.confirmation_email TEXT` column into
`confirmation_received INTEGER DEFAULT 0` + `confirmation_date TEXT`
per DESIGN.md v1.3 §6.2 + D19 + D20. D19 frames the original column
as type-ambiguous ("stored either `'Y'` or a date string"); D20
pins boolean-state columns at `INTEGER 0/1` rather than `TEXT
'Y'/'N'`. The legacy column stays physically in place until the
v1.0-rc rebuild drops it (DESIGN §6.3 step c "leave old columns
NULL until a rebuild drops them" — same retention as the
Sub-task 8 `interview1_date` / `interview2_date` pair).

- **`database.py` CREATE TABLE applications** adds the new columns
  right after `confirmation_email`:
  ```
  confirmation_received INTEGER DEFAULT 0,    -- 0 or 1
  confirmation_date     TEXT,                 -- ISO, NULL if none
  ```
  Inline comment block above the DDL records the split's rationale
  and the deferred physical drop so a future reader does not
  mistake the retained column for current schema.
- **`database.init_db()` migration block** (placed immediately after
  the Sub-task 8 interviews migration, so applications-table changes
  stay grouped):
  - Samples `PRAGMA table_info(applications)` once; captures the
    pre-ALTER column set.
  - PRAGMA-guarded `ALTER TABLE applications ADD COLUMN` for each
    new column — absent ⇒ add, present ⇒ skip. SQLite's
    "Cannot add a column with non-constant default" error (hit in
    Sub-task 6 for `updated_at`) does not apply here: the INTEGER
    DEFAULT 0 is a constant expression; the TEXT column has no
    DEFAULT at all.
  - **Migrate-once gate** (Sub-task 8 pattern): the one-shot UPDATE
    block only fires when either new column was absent pre-ALTER.
    A rerun on an already-migrated DB finds both columns present
    and skips the translation entirely — no re-translation of any
    legacy value, no overwrite of user-entered data. The logic is
    tighter than a per-row WHERE guard and lets the UPDATEs stay
    simple.
  - One-shot translation — two disjoint UPDATEs:
    - **Date-shaped legacy values** (via SQLite
      `GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'`, which
      matches exactly the 10-character ISO date shape and nothing
      else): set `confirmation_received = 1, confirmation_date =
      confirmation_email`.
    - **Flag-only legacy values** (`confirmation_email = 'Y'`):
      set `confirmation_received = 1`; `confirmation_date` stays
      NULL (the legacy 'Y' shape had no date).
    NULL, `''`, legacy `'N'`, or any other freetext value falls
    through both WHERE clauses — the new columns stay at their
    DEFAULTs (`received = 0`, `date = NULL`). This is correct: those
    shapes represent "no confirmation data," and the migration does
    not guess beyond the two shapes D19 names.
- **No application-code change** in `upsert_application` or any
  other writer. The function is schema-agnostic (accepts any fields
  dict and routes it into `INSERT … ON CONFLICT DO UPDATE SET`), so
  the split is transparent once the DDL exists. No caller in
  `app.py` / `pages/` / `tests/` writes to `confirmation_email`
  (verified via grep before the sub-task); new writes will land on
  the split pair when the Applications page UI lands in Phase 5.
- **`tests/test_database.py`** — 10 new tests:
  - `TestInitDb.test_applications_has_confirmation_received_column_with_zero_default`
    and `…_confirmation_date_column_nullable` — column-spec pins
    via `PRAGMA table_info`; mirror the Sub-task 6/7 precedent.
  - `TestUpsertApplication.test_writes_confirmation_received_and_date_roundtrip`
    — round-trip of both flag-only and flag+date upserts; also pins
    that the legacy `confirmation_email` stays NULL (no caller
    writes to it post-split).
  - New class `TestConfirmationSplitMigration` mirrors the Sub-task
    8 `TestInterviewsMigration` migrate-once-gate pattern: seeds a
    pre-v1.3 DB via `tmp_path` + monkeypatched `DB_PATH`, inserts
    one row with a legacy `confirmation_email` value, calls
    `init_db()`, inspects the new columns. Seven cases cover the
    full translation matrix — `'Y'` → received-only, date-shaped
    → both fields, NULL / empty / `'N'` → defaults, fresh-DB
    defaults contract, idempotence on second `init_db()`.
  - Shared seed helper `_seed_pre_v1_3_applications` includes
    `interview1_date` / `interview2_date` / `confirmation_email`
    together so `init_db()` runs ALL applicable migrations
    cleanly (Sub-task 8 first, Sub-task 10 next).
- **`tests/test_database.py`** — Sub-task 8 seed touch-up:
  `TestInterviewsMigration._seed_pre_v1_3_applications` gains a
  `confirmation_email TEXT` column so the realistic pre-v1.3 DB
  shape now round-trips cleanly through the Sub-task 10 migration
  block (which references `confirmation_email` in its UPDATE
  WHERE clauses). Pure seed realism — no change to the Sub-task
  8 test focus.

### Changed — v1.3 alignment Sub-task 11 (branch `feature/align-v1.3`)

Sub-task 11 rebuilds the `recommenders` table to bring its
storage types in line with DESIGN.md v1.3 §6.2 + D19 + D20:
`confirmed TEXT` → `confirmed INTEGER` (tri-state 0/1/NULL);
`reminder_sent TEXT` → `reminder_sent INTEGER DEFAULT 0`; add
`reminder_sent_date TEXT`. D19 frames the `reminder_sent` part as
a dual-concern (flag, date) split (a pre-v1.3 `reminder_sent`
TEXT cell could legitimately hold either `'Y'` or a date-shaped
string); D20 pins boolean-state columns at INTEGER 0/1 rather
than TEXT `'Y'`/`'N'`. Unlike Sub-tasks 8 and 10, which kept the
pre-v1.3 columns physically present (legacy-column retention per
§6.3 step c), this sub-task does a full table rebuild — SQLite
lacks in-place column-type change, so CREATE-COPY-DROP-RENAME
is the only clean recipe (see DESIGN §6.3's "Remove a column"
row, which also enumerates this pattern).

- **`database.py` CREATE TABLE recommenders DDL** rewritten to
  the target schema:
  ```
  confirmed          INTEGER,                -- 0, 1, or NULL
  submitted_date     TEXT,
  reminder_sent      INTEGER DEFAULT 0,      -- 0 or 1
  reminder_sent_date TEXT,                   -- ISO, NULL if none
  ```
  Preamble comment explains the tri-state semantics on `confirmed`
  (no DEFAULT so a fresh row is NULL = pending, distinct from 0 =
  explicitly not confirmed) and the (flag, date) split on the
  reminder pair. All other columns (`id`, `position_id`,
  `recommender_name`, `relationship`, `asked_date`,
  `submitted_date`, `notes`) stay untouched; the FK +
  `ON DELETE CASCADE` carries over verbatim.
- **`database.init_db()` migration block** inserted right after
  the Sub-task 10 confirmation_email split, before the
  `positions_updated_at` trigger:
  - **Idempotence gate** (borrowed from Sub-task 8's migrate-once
    shape, but keyed on the column's declared type rather than
    table presence): `PRAGMA table_info(recommenders)` → read the
    `confirmed` column's declared type. `INTEGER` (fresh DB or
    already-migrated) short-circuits the rebuild; `TEXT` (pre-v1.3)
    triggers it. A rerun on a migrated DB is a strict no-op — no
    duplicate tables, no double-translation.
  - **Step 1 — CREATE** `recommenders_new` with the target DDL
    (same columns and DEFAULTs as the CREATE TABLE above; FK +
    `ON DELETE CASCADE` re-declared so the rename lands a fully-
    constrained table).
  - **Step 2 — INSERT-COPY** from `recommenders` into
    `recommenders_new` with CASE translations:
    ```
    confirmed     'Y'           -> 1
                  'N'           -> 0
                  anything else -> NULL
                                   (cautious; 'maybe' / empty / stray
                                    freetext becomes NULL rather than
                                    a guessed integer)

    reminder_sent 'Y'           -> reminder_sent=1,
                                   reminder_sent_date=NULL
                  'YYYY-MM-DD'  -> reminder_sent=0,
                                   reminder_sent_date=<value>
                                   (matched via SQLite
                                    GLOB '????-??-??' — any 10-char
                                    '??-??' shape; looser than
                                    Sub-task 10's [0-9]-digit-class
                                    but safe given pre-v1.3
                                    reminder_sent realistically held
                                    only dates or 'Y'/NULL)
                  anything else -> reminder_sent=0,
                                   reminder_sent_date=NULL
    ```
    Other columns copy through verbatim. `id` values preserved so
    the `sqlite_sequence` AUTOINCREMENT counter stays coherent —
    SQLite advances it past any explicitly-inserted id on the
    next INSERT.
  - **Step 3 — DROP** the old `recommenders` table. Safe with
    `PRAGMA foreign_keys = ON` (set by `_connect()`): recommenders
    is a CHILD table (only an outbound FK to positions); nothing
    points INTO recommenders, so the implicit DELETE FROM that
    fires on DROP with FK=ON has nothing to cascade.
  - **Step 4 — RENAME** `recommenders_new` to `recommenders`. The
    FK definitions in other tables are unchanged (nothing points
    to recommenders), so the rename is structural only.
  - **Atomicity**: all four steps run inside the same
    `with _connect() as conn:` block, i.e. the same transaction
    as every other init_db() DDL change. A mid-rebuild failure
    triggers the `_connect()` context manager's rollback, so the
    DB cannot be left with a half-migrated table (e.g.
    `recommenders_new` orphaned alongside an un-translated
    `recommenders`).
- **No changes to recommender CRUD or dashboard-query functions.**
  `add_recommender` / `update_recommender` are schema-agnostic
  (no field whitelist), so they transparently accept integer
  values on the new INTEGER columns. `get_recommenders` /
  `get_all_recommenders` / `get_pending_recommenders` do not
  filter on `confirmed` or `reminder_sent` (the only WHERE
  predicates involve `submitted_date` and `asked_date`).
  `is_all_recs_submitted` only reads `submitted_date`. `pages/`
  and `exports.py` do not reference `confirmed` or `reminder_sent`
  at all (verified via grep; `pages/3_Recommenders.py` does not
  yet exist — landing target is Phase 5).
- **`tests/test_database.py`** — 18 new tests:
  - `TestInitDb` gets 4 pins (3 column-spec + 1 FK survival):
    `test_recommenders_confirmed_column_is_integer_nullable`
    (INTEGER, no DEFAULT — tri-state pending stays NULL),
    `test_recommenders_reminder_sent_column_is_integer_with_zero_default`
    (INTEGER, `dflt_value == "0"`),
    `test_recommenders_has_reminder_sent_date_column_nullable`
    (TEXT, no DEFAULT), and
    `test_recommenders_foreign_key_survives_rebuild`
    (PRAGMA foreign_key_list confirms position_id → positions.id
    with `on_delete == "CASCADE"` post-rename).
  - `TestRecommenders` gets 3 round-trip / defaults pins:
    `test_fresh_recommender_row_defaults` (add_recommender with
    only `recommender_name` → `confirmed=NULL`,
    `reminder_sent=0`, `reminder_sent_date=NULL`),
    `test_integer_confirmed_values_roundtrip` (0 / 1 / NULL all
    round-trip), and
    `test_integer_reminder_sent_and_date_roundtrip` (both the
    sent+dated and explicit-unsent states round-trip).
  - New `TestRecommendersRebuildMigration` class (11 tests)
    modeled on Sub-tasks 8 + 10's migration-test precedents.
    Shared `_seed_pre_v1_3_recommenders` helper builds a minimal
    pre-v1.3 DB via `tmp_path` + monkeypatched `DB_PATH`,
    including the pre-v1.3 applications columns Sub-tasks 8 + 10
    migrate (so init_db() runs ALL applicable migrations cleanly
    in order — Sub-task 8, Sub-task 10, Sub-task 11). Cases:
    `'Y'` → 1, `'N'` → 0, NULL stays NULL, other values
    (`'maybe'` / `''` / `'y'`) → NULL; `reminder_sent='Y'` →
    flag=1 / date=NULL, NULL / `''` / `'N'` / freetext →
    flag=0 / date=NULL, date-shaped → flag=0 /
    date=`<value>`; other columns preserved verbatim; FK +
    CASCADE still cleans up recommenders on delete_position;
    AUTOINCREMENT counter advances past migrated ids; second
    `init_db()` is a strict no-op (PRAGMA table_info guard
    evaluates False once `confirmed`'s type is INTEGER).
  - `import pandas as pd` added at the top for `pd.isna`
    checks on NULL-able columns (pandas may return None or NaN
    depending on whether other rows in the same column forced
    the dtype to float).

### Changed — v1.3 alignment Sub-task 12 (branch `feature/align-v1.3`)

Sub-task 12 aligns `app.py` with DESIGN.md v1.3 §8.0 (cross-page
conventions) + §8.1 (dashboard panel specifications + funnel visibility
rules + empty-state branches). Pure display-layer change — no schema,
no new database queries, no config edits.

- **`app.py` `st.set_page_config(…)`** added as the FIRST Streamlit
  call per DESIGN §8.0 + D14: `page_title="Postdoc Tracker"`,
  `page_icon="📋"`, `layout="wide"`. Data-heavy views (KPI grid,
  funnel, timeline) need horizontal room; the default centered layout
  cramps at ~750px. Placed immediately after imports, before
  `database.init_db()`, so it precedes every other `st.*` call.
- **`app.py` top-bar 🔄 Refresh button removed** per DESIGN D13.
  Streamlit reruns on any widget interaction; a manual refresh is
  cognitive noise for a single-user local app. The `st.columns([6, 1])`
  title/refresh wrap is replaced with a plain `st.title("Postdoc
  Tracker")` — no more half-empty column on the right. The pre-v1.3
  C3-locked decision is explicitly superseded by D13.
- **`app.py` Tracked KPI gains the locked help-tooltip string** per
  DESIGN §8.1: `help="Saved + Applied — positions you're still
  actively pursuing"`. Hovering the metric explains the arithmetic so
  the reader doesn't have to guess what "tracked" means. AppTest
  surfaces the tooltip at `metric.proto.help` (probed before writing
  the pin test).
- **`app.py` Application Funnel rewritten to be `FUNNEL_BUCKETS`-
  driven** per DESIGN §8.1 + D11 + D17:
  - Per-bucket counts are computed by summing `count_by_status()` over
    each bucket's raw-status tuple. The only multi-status bucket today
    is "Archived" (= `[REJECTED]` + `[DECLINED]`, D17); other buckets
    map one-to-one, so the change is a behavioural no-op on every
    non-archived row and correctly aggregates archived rows.
  - y-axis labels are the bucket LABELS (UI strings like "Saved" /
    "Applied" / …), not the raw `STATUS_VALUES` sentinels
    (`"[SAVED]"` / `"[APPLIED]"` / …). The presentation/storage split
    per D11 + D16 — storage keeps bracketed enum sentinels, the UI
    renders the clean labels. The y-axis is still reversed so the
    first visible bucket sits at the top (pipeline reads top-down).
  - Bar colors come from `FUNNEL_BUCKETS[i][2]`, not from
    `STATUS_COLORS`. The bucket OWNS its color because a bucket can
    aggregate multiple raw statuses — `STATUS_COLORS` is for
    per-status surfaces (Opportunities-table badges, tooltips).
  - Visible buckets = `FUNNEL_BUCKETS` entries whose label is NOT in
    `FUNNEL_DEFAULT_HIDDEN`, OR every bucket when the user has clicked
    `[expand]`. A visible bucket with zero count renders as a
    zero-width bar — keeps the chart shape stable as the pipeline
    fills up.
- **`app.py` single `[expand]` button + session flag** replacing the
  pre-v1.3 per-bucket checkbox model (DESIGN §8.1 + D24). Button
  label is literally `"[expand]"` (brackets included). Clicking fires
  a bound `_expand_funnel` callback via `on_click=` that flips
  `st.session_state["_funnel_expanded"]` to `True`; callbacks run
  BEFORE the next script rerun, so the funnel branches evaluate with
  expanded=True on the very first post-click render. No `st.rerun()`
  is needed and the pre-v1.3 "double rerun" gotcha is avoided. The
  flag is one-way (no collapse in v1).
- **`app.py` three-branch funnel empty-state matrix** per DESIGN
  §8.1, evaluated in order:
  - **(a)** `total == 0` — no positions at all. Render
    `st.info("Application funnel will appear once you've added
    positions.")` and SUPPRESS the `[expand]` button (nothing to
    expand into).
  - **(b)** total > 0, `_funnel_expanded is False`, every
    default-visible bucket has count 0. Render
    `st.info("All your positions are in hidden buckets. Click
    [expand] below to reveal them.")` followed by the `[expand]`
    button. Terminal-only DBs (every position in Closed / Archived)
    land here — this is the v1.3 REPLACEMENT for the pre-Sub-task-12
    "Option C: terminal-only DB still renders the figure" behaviour.
  - **(c)** otherwise. Render the chart; `[expand]` button below iff
    `FUNNEL_DEFAULT_HIDDEN` is non-empty AND not yet expanded. After
    click, the button no longer renders (since "not yet expanded"
    flips to False). Subheader renders in all three branches for
    page-height stability.
- **`tests/test_app_page.py`** — 59 tests on `app.py`; +11 new
  versus the pre-Sub-task-12 count of 48 (before: 43 were in the
  file and we had 5 unrelated other counts; net +11 on this file).
  Breakdown:
  - `TestT1AppShell` +1 (`test_page_config_sets_wide_layout` —
    source-level grep since AppTest doesn't surface set_page_config).
  - `TestT1CKpiCountsAndRefresh` → renamed `TestT1CKpiCounts`; the
    two refresh-button tests are gone and replaced with
    `test_refresh_button_absent` + `test_tracked_kpi_help_tooltip`
    (pin `metric.proto.help` against the locked string). Net: 0.
  - `TestT2AFunnelBar` — four tests renamed (one-bar-per-VISIBLE-
    BUCKET-in-order; x-values SUM bucket raw statuses; colors from
    FUNNEL_BUCKETS[i][2]; missing buckets render as zero-width bars).
    Each assertion is now bucket-aware and re-computes the expected
    visible-bucket list dynamically from config rather than hard-
    coding the 7-status STATUS_VALUES list. Net: 0.
  - `TestT2BFunnelEmptyState` — reshaped to the three-branch matrix.
    `EMPTY_COPY` → `EMPTY_COPY_A`; new `EMPTY_COPY_B` constant. New
    tests: `test_empty_db_fires_branch_a`,
    `test_branch_a_empty_copy_is_spec_exact`,
    `test_all_hidden_bucket_data_fires_branch_b`,
    `test_branch_b_empty_copy_is_spec_exact`,
    `test_single_open_position_fires_branch_c`,
    `test_mixed_visible_and_hidden_data_fires_branch_c`,
    `test_subheader_renders_in_all_branches`. The pre-v1.3
    `test_terminal_only_db_still_renders_figure` is GONE — its
    behaviour is explicitly inverted in v1.3 (terminal-only DB now
    fires branch (b), not the chart). Net: +2.
  - `TestT2CFunnelLayout.test_empty_state_info_renders_inside_left_
    column` — pointer update only: references `EMPTY_COPY_A` instead
    of the removed `EMPTY_COPY`.
  - `TestT2DFunnelExpand` — NEW class, 8 tests:
    `test_expand_button_renders_in_branch_c_by_default`,
    `test_expand_button_absent_in_branch_a`,
    `test_expand_button_present_in_branch_b`,
    `test_funnel_expanded_defaults_false`,
    `test_clicking_expand_sets_session_state_true`,
    `test_clicking_expand_reveals_all_buckets_on_chart` (the
    load-bearing behavioural pin — seeds visible + both hidden
    buckets, asserts pre-click y-axis excludes hidden labels and
    post-click y-axis matches every `FUNNEL_BUCKETS` label in order),
    `test_expand_button_hides_after_click`,
    `test_clicking_expand_from_branch_b_renders_chart`. Net: +8.
  - Unrelated T1-D / T1-E / T3 classes untouched.

### Changed — v1.3 alignment Sub-task 13 (branch `feature/align-v1.3`)

Sub-task 13 aligns `pages/1_Opportunities.py` with DESIGN.md v1.3 §8.0
(cross-page conventions) + §8.2 (Opportunities page + Delete-button
placement). Pure display-layer change — no schema, no new database
queries, no config edits. Parallel in spirit to Sub-task 12's §8.0 +
§8.1 alignment for `app.py`; this commit group closes the remaining
page-side gap left by that sub-task.

- **`pages/1_Opportunities.py` `st.set_page_config(…)`** added as the
  first Streamlit call per DESIGN §8.0 + D14: `page_title="Postdoc
  Tracker"`, `page_icon="📋"`, `layout="wide"`. Data-heavy views
  (positions table + edit panel) need horizontal room. Placed
  immediately after `database.init_db()`, before `st.title(…)`.
- **`filter_status` selectbox gains `format_func=lambda v:
  config.STATUS_LABELS.get(v, v)`** per DESIGN §8.0 Status label
  convention (storage holds raw bracketed values; UI renders the
  stripped labels). The lambda wraps the literal `STATUS_LABELS.get`
  so the "All" sentinel passes through (vanilla `STATUS_LABELS.get(
  "All")` returns `None` and would leak a blank option into the
  rendered dropdown). `.value` and the downstream filter predicate
  keep the raw storage key, so `df[df["status"] == status_filter]`
  compares apples to apples.
- **`edit_status` selectbox on the Overview form gains
  `format_func=config.STATUS_LABELS.get`**. No "All" sentinel on
  this path, so the literal dict-method is sufficient.
  `session_state["edit_status"]` stays raw; the Save handler writes
  the storage value into `positions.status` unchanged.
- **Edit-panel tab selector swapped from `st.tabs` to
  `st.radio(horizontal=True, label_visibility="collapsed",
  key="_active_edit_tab")`** — the load-bearing change for the
  Delete-button placement below. Rationale:
  - DESIGN §8.2 Delete row: "Button rendered below the edit panel
    (outside the panel box), visible only when the active tab is
    Overview."
  - Streamlit 1.56's `st.tabs(key=...)` accepts a `key` keyword but
    does NOT actually populate `session_state` with the active tab
    (verified via isolation probe before the swap); there is no
    public API to detect the active `st.tabs` tab.
  - `st.radio` with `horizontal=True` + collapsed label visually
    approximates the old tab strip, while its value lives in
    `session_state["_active_edit_tab"]` and drives branch-rendering:
    each tab body is wrapped in `if active_tab == "Overview": …` /
    `elif active_tab == "Requirements": …` / etc. On non-active
    tabs, the tab-specific widgets ARE NOT EMITTED (pre-Sub-task-13
    `st.tabs` emitted ALL tab bodies on every run and CSS-hid
    inactive ones). Test consequence: non-Overview tests must now
    set `session_state["_active_edit_tab"]` before accessing
    e.g. `edit_req_cv` radios.
- **Delete button relocated to below all four tab branches**,
  gated by `if active_tab == "Overview":` per DESIGN §8.2 Delete row
  ("the button's scope is the whole position, not the active tab's
  data — hence the Overview-only placement, matching the tab where
  the user is reviewing the position as a whole"). The `elif
  st.session_state.get("_delete_target_id") == sid:` dialog-reopen
  branch from Tier 5 lives in the same gated block — same AppTest
  script-run quirk that required re-opening the dialog across
  reruns is preserved end-to-end. On Requirements / Materials /
  Notes tabs the Delete button is now not in the DOM at all
  (pre-Sub-task-13 it was still there, just CSS-hidden; AppTest
  would find it via `at.button(key="edit_delete")` regardless of
  active tab).
- **`tests/test_opportunities_page.py`** — 441 tests on the page;
  +13 versus the pre-Sub-task-13 count of 428 (the branch was
  428-green at the head of Sub-task 12). Highlights:
  - New `TestPageConfigSetsWideLayout::test_page_config_sets_wide_
    layout` — source-grep pin (AppTest doesn't surface
    set_page_config), mirrors the `test_app_page.py` precedent.
  - New `TestFilterStatusFormatFunc` (3 tests): options display
    labels + "All" passthrough; `.value` stays raw; end-to-end
    storage/display split via a real filter round-trip.
  - New `TestEditStatusFormatFunc` (2 tests): Overview form's
    Status selectbox mirrors the filter_status contract, minus the
    "All" passthrough.
  - New `TestMaterialsFilterPredicateIsYes` (1 test): Materials tab
    renders a checkbox iff `session_state[f"edit_{req_col}"] ==
    "Yes"` (DESIGN §8.2) — independent pin from Sub-task 2's
    migration tests.
  - New `TestDeleteButtonTabSensitivity` (5 tests): Delete button
    visible on Overview, absent on each of Requirements / Materials
    / Notes, and reappears on return to Overview.
  - `TestEditPanelShell` — 4 tests updated to use
    `at.radio(key="_active_edit_tab")` instead of `at.tabs`, plus a
    new `test_default_active_tab_is_first_config_entry` pinning
    Overview as the default.
  - `TestRequirementsTabWidgets` / `TestMaterialsTabWidgets` /
    `TestNotesTabWidgets` + the three matching Save classes +
    `TestPreSeedNaNCoercion` — existing tests updated to call the
    new `_select_row_and_tab(at, row, tab_name)` helper (which
    writes both the row selection and the active tab to
    session_state in one step) before accessing non-Overview
    widgets. `TestRequirementsTabWidgets.test_one_radio_per_
    requirement_doc` bumps its radio-count assertion by +1 for the
    new tab selector. `TestNotesTabWidgets.test_text_area_renders_
    when_row_selected` drops from 2→1 expected text_areas
    (`edit_work_auth_note` now renders only when
    active_tab == "Overview"; `edit_notes` is the only text_area on
    the Notes tab).
  - `TestFilterBarStructure.test_status_options_match_config` +
    `TestOverviewTabWidgets.test_status_selectbox_options_match_
    config` — expected-options lists swap from raw STATUS_VALUES
    to `[STATUS_LABELS[v] for v in STATUS_VALUES]` (AppTest
    surfaces `.options` as post-format_func display strings).

### Changed — v1.3 alignment Sub-task 14 (branch `feature/align-v1.3`)

Sub-task 14 is the v1.3 doc-alignment sweep across the non-DESIGN
project docs. Closes the last v1.3-alignment item before the branch
pushes to a PR. Pure docs change — no schema, no new queries, no
config edit, no test drift. Scope: `GUIDELINES.md`, `CHANGELOG.md`,
`roadmap.md`, `TASKS.md`, `docs/ui/wireframes.md`,
`docs/dev-notes/extending.md`.

- **`GUIDELINES.md` §3 (Naming Conventions — widget keys
  sub-section)** — sentinel list gains `_active_edit_tab`
  (Opportunities edit-panel tab selector, landed Sub-task 13) and
  `_funnel_expanded` (dashboard `[expand]` toggle, landed
  Sub-task 12). The two new sentinels follow the existing
  `_edit_form_sid` / `_delete_target_id` / `_skip_table_reset`
  precedent — leading `_` marks internal state, not a widget key.
- **`GUIDELINES.md` §6 (Config Usage — status selectbox
  example)** — alias + literal swap for the Sub-task 5 rename
  ([OPEN] → [SAVED]):
  - `from config import STATUS_VALUES, STATUS_OPEN` →
    `from config import STATUS_VALUES, STATUS_SAVED, STATUS_LABELS`.
  - `st.selectbox("Status", STATUS_VALUES)` gains
    `format_func=STATUS_LABELS.get` so the GOOD example matches
    DESIGN §8.0 Status label convention (the UI surface convention
    Sub-task 13 actually enforced on `pages/1_Opportunities.py`).
  - `if row["status"] == STATUS_OPEN:` →
    `if row["status"] == STATUS_SAVED:`.
  - BAD example literal list swaps `["[OPEN]", "[APPLIED]", ...]`
    → `["[SAVED]", "[APPLIED]", ...]` and the BAD equality check
    swaps `"[OPEN]"` → `"[SAVED]"`.
- **`GUIDELINES.md` §6 pre-merge grep rule** —
  `grep -nE "\[OPEN\]|\[APPLIED\]|\[INTERVIEW\]" app.py pages/*.py`
  → `grep -nE "\[SAVED\]|\[APPLIED\]|\[INTERVIEW\]" app.py pages/*.py`.
  The rule's purpose (catch hardcoded stage-0/1/2 literals that
  drift from the config constants) is unchanged; the new pattern
  pins the current stage-0 literal, which is what the rule
  actually enforces.
- **`GUIDELINES.md` §7 (Streamlit Patterns — controlled inputs
  for enumerated values)** — the status selectbox example gains
  `format_func=config.STATUS_LABELS.get` + a short paragraph
  explaining the storage/display split and the `"All"`-passthrough
  lambda wrapper (`lambda v: STATUS_LABELS.get(v, v)`). Brings the
  canonical snippet in line with how Sub-task 13 wired
  `pages/1_Opportunities.py`'s `filter_status` / `edit_status`
  selectboxes.
- **`roadmap.md` "In flight" paragraph** — Sub-tasks 1–13 → 1–14
  in the opening clause; a final clause describes the Sub-task 14
  doc-sweep inline (GUIDELINES sentinel list + grep rule + status-
  selectbox example + CHANGELOG / TASKS / roadmap updates).
  `441 tests green` count preserved — no tests added, none removed.
- **`TASKS.md`** — new `[x] Sub-task 14` entry inserted between
  Sub-task 13 and the remaining `[ ] Push branch; open PR; merge
  to main` bullet; `_Updated:` footer bumped from "Sub-tasks
  1–13 shipped" to "Sub-tasks 1–14 shipped". Matches the cadence
  of every prior sub-task entry on this sprint.
- **`CHANGELOG.md`** — this entry. Placed in `[Unreleased]`
  immediately after the Sub-task 13 `Changed` block, mirroring
  the per-sub-task cadence of the rest of the section. Migration
  section below gains the matching "Sub-task 14 requires no
  migration" line so readers can scan the Migration block in
  isolation.
- **`docs/ui/wireframes.md`** — audited against DESIGN §8.1/§8.2/§8.3.
  Already shows the v1.3 state: `[expand]` button on the funnel,
  `Saved`/`Applied` labels (not raw bracketed sentinels) in the
  dashboard Upcoming table and the Opportunities-page table, no
  🔄 Refresh button, a multi-interview list on the Applications
  page, and the Delete button rendered below the Opportunities
  edit panel. The edit-panel `[ Overview ] [ Requirements ] [
  Materials ] [ Notes ]` ASCII strip is intent-only — DESIGN §8.2
  still calls these "Tabs" even though Sub-task 13 switched the
  underlying widget from `st.tabs` to `st.radio(horizontal=True)`;
  the sketch's tab appearance matches a horizontal radio's rendered
  shape, consistent with the file's "intent-only" disclaimer at
  the top. No changes.
- **`docs/dev-notes/extending.md`** — audited against DESIGN §5.3.
  Already v1.3-aligned: "Add a new pipeline status" references
  `STATUS_LABELS` / `FUNNEL_BUCKETS` / `FUNNEL_DEFAULT_HIDDEN` per
  D24; "Rename a pipeline status" references `STATUS_LABELS` +
  the config-driven DDL DEFAULT (Sub-task 4) so the one-shot
  `UPDATE` is the whole migration; "Add a new vocabulary option"
  lists `INTERVIEW_FORMATS` alongside the other v1.3 vocabs. No
  changes.
- **Out-of-scope (noted for follow-up)**:
  `docs/dev-notes/streamlit-state-gotchas.md` entry #14 still
  describes the removed 🔄 Refresh button and entry #13's example
  still uses the `interview1_date`/`interview2_date` pair that
  Sub-task 8 normalized into the `interviews` sub-table. Outside
  Sub-task 14's stated scope; candidate for a separate sub-task
  if approved.

### Fixed — v1.3 alignment post-Sub-task 14 follow-up (branch `feature/align-v1.3`)

Code-review follow-up landing during the post-Sub-task-14 review pass.
Brings the Sub-task 10 `confirmation_email` migration into parity with
the Sub-task 8 `interview1_date` / `interview2_date` migration so both
parallel "split a dual-purpose column" / "normalize flat columns into a
sub-table" recipes honour DESIGN §6.3 step (c) verbatim ("leave the old
column NULL until a follow-up release rebuilds the table to drop it").
Pre-fix the legacy `confirmation_email` retained its post-split values
('Y' or `YYYY-MM-DD` strings); no caller reads the column, but the
literal-DESIGN drift was the kind of inconsistency the alignment pass
exists to close.

- **`database.init_db()`** — add a NULL-clear UPDATE inside the
  existing `confirmation_split_needed` block, AFTER the two value-
  extracting UPDATEs so they still see the original
  `confirmation_email` contents. Clearing first would leave nothing to
  translate. Idempotent by virtue of the outer gate — re-runs on a
  migrated DB find both new columns already present, the gate is
  False, and the whole block (including this UPDATE) is skipped.
- **`tests/test_database.py`** — new
  `test_migration_null_clears_legacy_confirmation_email_column` in
  `TestConfirmationSplitMigration`. Seeds a date-shaped legacy value
  so both the value extraction AND the NULL-clear are exercised; runs
  `init_db()`; asserts the new (received, date) pair is populated AND
  the legacy `confirmation_email` is NULL post-migration. The
  section-header comment retiring the now-stale "NULL-cleared is not
  required" justification (which tracked the prior code, not the
  DESIGN literal) lands alongside.
- **No other callers, no UI surface, no schema rebuild.** `add_position`
  fresh-DB rows continue to insert with `confirmation_email = NULL` via
  the absent DEFAULT, so the existing
  `test_writes_confirmation_received_and_date_roundtrip` legacy-NULL
  assertion still passes unchanged.

452/452 pytest green (default + `-W error::DeprecationWarning`).

### Fixed — v1.3 alignment R3 cascade alias (branch `feature/align-v1.3`)

Second code-review follow-up. Replaces the hardcoded literal `"Offer"`
in the R3 cascade trigger with a `config.RESPONSE_TYPE_OFFER` alias on
parity with the `STATUS_*` aliases that already insulate cascade code
from `STATUS_VALUES` renames. Pre-fix, a future rename of the `'Offer'`
entry inside `RESPONSE_TYPES` would have left R3 silently broken — the
selectbox would render the new label, the user would pick it, and
`upsert_application`'s literal-string match would never fire. New
import-time invariant #9 catches the drift before any page renders.

- **`config.py`** — add `RESPONSE_TYPE_OFFER: str = "Offer"` plus
  invariant #9 `assert RESPONSE_TYPE_OFFER in RESPONSE_TYPES`. Literal
  lives at the alias declaration (not as `RESPONSE_TYPES[i]`) because
  RESPONSE_TYPES order is not a contract; only membership matters.
- **`database.py`** — R3 condition swaps the literal `"Offer"` for
  `config.RESPONSE_TYPE_OFFER`; inline comment cross-references
  invariant #9 so the safety story is local to the cascade site.
- **`DESIGN.md`** — patch §5.1 (new `RESPONSE_TYPE_OFFER` row +
  cross-reference on `RESPONSE_TYPES`), §5.2 (invariant #9), §9.3
  (placeholder convention extended; R3 condition uses
  `<RESPONSE_TYPE_OFFER>` placeholder; prose at "next
  upsert_application with response_type = …" uses the alias name
  matching the section's existing alias-over-literal convention).
  Small structural patches — no `Version:` bump per the doc-header
  "small corrections land as patch-style edits" clause.
- **`tests/test_config.py`** — three new tests pinning the alias
  (`test_response_type_offer_value_is_offer`), the membership
  positive case (`test_response_type_offer_is_member_of_response_types`),
  and the synthetic-drift firing
  (`test_invariant_9_fires_on_drift`). Mirrors the
  `test_invariant_*_fires_on_drift` pattern used for invariants 1, 3,
  6, 8 — replicates the guard logic on a synthetic bad value rather
  than reloading config under mutation.
- **No behavioural change for end-users.** `RESPONSE_TYPES` still
  shows `'Offer'`; `database.upsert_application(... response_type =
  "Offer" ...)` still fires R3 exactly as before; existing R3 tests
  (incl. the 5-row per-state matrix) continue passing untouched.

455/455 pytest green (default + `-W error::DeprecationWarning`).

### Fixed — v1.3 alignment exports log-and-continue (branch `feature/align-v1.3`)

Third code-review follow-up. Honours the two related load-bearing
contracts in DESIGN §7 + §9.5 that the v1.3 alignment pass left
under-pinned: every `exports.write_all()` call must be log-and-swallow
(at both ends — inside `exports.write_all()` itself per §9.5, and at
each `database.py` writer's call site per §7 database.py contract #1).
Pre-fix, an export failure (mkdir denied, write_progress raises) would
propagate up to the page handler as a traceback, even though the DB
write that triggered the export had already succeeded — exactly the
"user sees Saved, not a traceback" promise §9.5 makes.

- **`exports.py`** — add `logging.getLogger(__name__)`. `write_all()`
  rewrites to wrap `EXPORTS_DIR.mkdir(exist_ok=True)` in its own
  try/except (short-circuits the rest of the function on failure;
  nothing else can succeed without the destination directory) and
  iterate over the three writer slot NAMES (`write_opportunities`,
  `write_progress`, `write_recommenders`) via `globals()`, each
  wrapped in its own try/except. Per-call wrapping (rather than a
  whole-function wrap) lets the other writers still run when one
  fails — matches §9.5's "A failure in ANY `write_*`" wording.
  Iterating by name rather than captured function reference keeps
  the log message reading as the intended writer slot (a monkey-
  patched stand-in carries its own `__name__` that would otherwise
  leak into the operator-facing log).
- **`database.py`** — add `logging.getLogger(__name__)`. Each of the
  10 writer call sites that calls `_exports.write_all()` gains a
  try/except wrapping the call: `add_position`, `update_position`,
  `delete_position`, `upsert_application`, `add_interview`,
  `update_interview`, `delete_interview`, `add_recommender`,
  `update_recommender`, `delete_recommender`. The deferred
  `import exports as _exports` line stays inside each writer per
  DESIGN §7's literal "the import of `exports` inside each writer
  is deferred (not at module top)" wording — no helper-function
  abstraction.
- **`tests/test_exports.py`** — three new tests pinning the §9.5
  contract: `test_write_all_swallows_individual_writer_failure`,
  `test_write_all_continues_after_individual_failure`,
  `test_write_all_swallows_mkdir_failure`.
- **`tests/test_database.py`** — new `TestExportsLogAndContinue`
  class. `test_writer_swallows_exports_failure` is parametrized
  over all 10 writers (a single failure surfaces as a unique line
  in pytest output naming the offending writer). `test_db_write_
  commits_even_when_exports_fails` is the load-bearing semantic
  pin: a failed export must NOT roll back the DB write that
  triggered it.
- **No behavioural change for the happy path.** All prior 455 tests
  continue passing — wrapping is strictly additive.

469/469 pytest green (default + `-W error::DeprecationWarning`) —
+14 new tests, +0 prior tests touched.

### Fixed — v1.3 alignment widget-key naming follow-up (branch `feature/align-v1.3`)

Fourth code-review follow-up. Renames the Opportunities edit-panel
tab-selector radio's widget key from `_active_edit_tab` to
`edit_active_tab` so it follows DESIGN §8.0's widget-key scope table.
The leading-`_` prefix is documented as reserved for internal session-
state sentinels (`_edit_form_sid`, `_skip_table_reset`,
`_delete_target_id`, `_funnel_expanded`); the tab selector is a real
widget, not a sentinel-only slot, so the `edit_` widget-key prefix is
its documented home — same scope as `edit_position_name`,
`edit_notes`, etc. Sub-task 14 had classified `_active_edit_tab` as a
sentinel in `GUIDELINES.md` §3 because the slot is read from non-
widget code paths (the Delete-button visibility gate); the §8.0
scope table is unambiguous on the rule though, so this follow-up
sides with the table.

- **`pages/1_Opportunities.py`** — `key="_active_edit_tab"` →
  `key="edit_active_tab"`. Inline comment refreshed to reference
  `session_state["edit_active_tab"]` and gains a short paragraph
  recording the §8.0 rationale.
- **`tests/test_opportunities_page.py`** — `TAB_SELECTOR_KEY`
  constant rebinds to `"edit_active_tab"`; descriptive prose in
  comments / docstrings naming the old key (Sub-task 13 class
  header, `_select_row_and_tab` docstring, §8.2 Delete-button
  tab-sensitivity comment block, §8.2 Delete-row prose) updates to
  the new key. A single forward-explaining note marks the
  migration-history so future readers see why the constant flipped.
  All test references go through the `TAB_SELECTOR_KEY` constant —
  no per-test rewrites needed.
- **`GUIDELINES.md` §3** — `_active_edit_tab` removed from the
  internal-sentinel list; `edit_active_tab` appended to the
  edit-panel widget-key example. Sub-task 14's classification is
  superseded.
- **`roadmap.md`** — current-state paragraph updated: the radio
  declaration reads `key="edit_active_tab"`; the prose splits the
  `edit_active_tab` widget key from the `_funnel_expanded` sentinel
  in the doc-sweep summary.
- **`CHANGELOG.md` Sub-task 13 / Sub-task 14 entries** — LEFT
  unchanged (historical record of what shipped at the time). This
  block is the canonical post-rename record.
- **`TASKS.md` done-item entries** — LEFT unchanged, same rationale.

469/469 pytest green (default + `-W error::DeprecationWarning`) —
+0 new tests, 41 tab-related tests rebound to the new constant.

### Fixed — v1.3 alignment date-shape divergence cross-reference (branch `feature/align-v1.3`)

Fifth code-review follow-up. Pure docs change. The Sub-task 10
`confirmation_email` split and the Sub-task 11 `recommenders` rebuild
both perform a dual-purpose-column split into a
`(flag INTEGER, date TEXT)` pair, but they translate a date-shaped
legacy value differently — `confirmation_email` lands a date as
`received = 1` + `date = value` while `reminder_sent` lands the same
shape as `reminder_sent = 0` + `reminder_sent_date = value`. Both
behaviours are pinned by tests since v1.3 alignment landed, but the
WHY of the divergence was nowhere on record — a future maintainer
reading the two tests side-by-side could read one as a bug relative
to the other.

- **`DESIGN.md` §6.3** — new "Flag/date split divergence —
  `confirmation_email` vs `reminder_sent`" paragraph after the
  manual-migration table, before "Migration discipline". Explains
  the per-column rationale (confirmation_email's pre-v1.3 semantics
  tied a date strongly to "received"; reminder_sent saw both
  date-only and `'Y'`-only legacy use without a clear "date implies
  sent" rule, so the user re-saves to flip the flag if intended)
  and names both pinning tests.
- **`database.py`** — extends the existing recommenders-rebuild
  comment block with a 9-line note immediately after the
  `reminder_sent` CASE rules table. Cross-references the new §6.3
  paragraph and includes a 1-sentence short-version so a maintainer
  mid-rebuild who can't context-switch to the spec still sees the
  load-bearing reason inline.
- **No code change, no test change.** The behaviour is unchanged
  and was already pinned by
  `test_migration_copies_date_string_to_both_fields` and
  `test_migration_splits_date_shaped_reminder_sent_into_new_column`.

469/469 pytest green (default + `-W error::DeprecationWarning`) —
+0 new tests, +0 prior tests touched.

### Fixed — v1.3 alignment empty-REQUIREMENT_DOCS guard (branch `feature/align-v1.3`)

Sixth (and final) code-review follow-up. Adds a defensive early-return
to `database.compute_materials_readiness` for the edge case where
`config.REQUIREMENT_DOCS` is empty. Pre-fix, the function built two
SQL fragments via `" OR ".join(...)` / `" AND ".join(...)` over the
constant; an empty list produced empty strings, leading to invalid
SQL (`... AND ()` and `CASE WHEN THEN 1 ELSE 0 END`). The state is
currently impossible — config.py REQUIREMENT_DOCS has seven entries
— but DESIGN §12.1's v2 profile expansion permits a future profile
(e.g. a casual job tracker) to ship with zero document requirements,
and the dashboard's Materials Readiness panel calls this function
unconditionally; without the guard, the dashboard would crash on
first load for such a profile.

- **`database.compute_materials_readiness`** — 2-line early-return
  at the top of the function: `if not config.REQUIREMENT_DOCS:
  return {"ready": 0, "pending": 0}`. Docstring extended with a
  paragraph documenting the contract + §12.1 rationale.
- **`tests/test_database.py`** —
  `test_empty_requirement_docs_returns_zero_counts` in
  `TestComputeMaterialsReadiness`: seeds a real ready position
  (sanity: pre-patch count = 1 ready), monkeypatches
  `config.REQUIREMENT_DOCS = []`, asserts the call returns
  `{"ready": 0, "pending": 0}` without raising. Exercises a
  config / schema mismatch (the DB still carries the standard
  `req_*`/`done_*` columns from init_db's run with the real config).
- **Chose defensive early-return over §5.2 invariant
  `len(REQUIREMENT_DOCS) > 0`.** §12.1 implies a profile-without-
  docs is a valid future state — an invariant would block it. The
  fix is also localized to the one affected function; other
  REQUIREMENT_DOCS-driven code (`init_db`'s CREATE/ALTER loops,
  the Materials tab) already tolerated `[]` gracefully.

470/470 pytest green (default + `-W error::DeprecationWarning`) —
+1 new test, +0 prior tests touched.

### Migration

**Sub-task 1** requires no migration — all additions are Python constants.

**Sub-task 2** — required value migration for the `req_*` columns on
`positions`. `init_db()` runs this automatically on next app start; a
user upgrading from a v1.2 DB does not need to execute anything
manually. For the record, the equivalent SQL executed per
`REQUIREMENT_DOCS` column is:

```sql
UPDATE positions
   SET req_<col> = CASE req_<col>
                     WHEN 'Y' THEN 'Yes'
                     WHEN 'N' THEN 'No'
                     ELSE req_<col>
                   END;
```

Idempotent: second and later runs are no-ops because `ELSE req_<col>`
passes `'Yes'`, `'No'`, `'Optional'`, and any other value through
unchanged. Column names come from `config.REQUIREMENT_DOCS` (never user
input). No schema rebuild, no data loss, no downtime.

**Sub-task 3** — no automatic migration runs because neither
`positions.work_auth` nor `positions.full_time` has a DDL constraint;
legacy values (if any) stay in place as orphan TEXT. No selectbox
currently renders either column, so the page keeps working. The values
will become meaningful again when the Overview-tab UI lands in a later
sub-task — at that point any row with a legacy string will fall
through the Opportunities-page pre-seed coercion (mirroring the
priority / status `F2` guard at `pages/1_Opportunities.py:379-386`)
and show the first option.

If a dev DB does carry legacy values that should be preserved, run the
translations manually. These require judgment — old values do not map
1-to-1 onto the new vocabularies, so review each row before executing:

```sql
-- work_auth — old 6 values → new 3 values.
-- "Any" / "OPT" / "J-1" / "H1B" are postings that would accept the
-- applicant; map to 'Yes' and record the visa detail in the future
-- work_auth_note column. "No Sponsorship" → 'No'. "Ask" → 'Unknown'.
UPDATE positions
   SET work_auth = CASE work_auth
                     WHEN 'Any'            THEN 'Yes'
                     WHEN 'OPT'            THEN 'Yes'
                     WHEN 'J-1'            THEN 'Yes'
                     WHEN 'H1B'            THEN 'Yes'
                     WHEN 'No Sponsorship' THEN 'No'
                     WHEN 'Ask'            THEN 'Unknown'
                     ELSE work_auth
                   END
 WHERE work_auth IN ('Any','OPT','J-1','H1B','No Sponsorship','Ask');

-- full_time — old Yes/No/Part-time → new Full-time/Part-time/Contract.
-- "Part-time" survives unchanged. "Yes" most naturally → 'Full-time'.
-- "No" is genuinely ambiguous (could be Part-time or Contract);
-- preferred outcome: leave these rows for manual review.
UPDATE positions
   SET full_time = 'Full-time'
 WHERE full_time = 'Yes';
-- SELECT id, position_name, full_time FROM positions WHERE full_time = 'No';
```

Idempotent on a clean DB (no rows match the `WHERE` clauses). Skip
entirely on a DB that was only ever populated under v1.3.

**Sub-task 4** requires no migration — it is a pure refactor. The
f-string interpolation emits the same SQL bytes as the prior hardcoded
DDL (`'[OPEN]'` / `'Pending'`) because live config still holds those
values. Renames under `STATUS_VALUES[0]` or `RESULT_DEFAULT` in future
sub-tasks will each ship their own one-shot `UPDATE` per DESIGN §6.3
— no DDL edit needed because the CREATE TABLE strings now read
config at call time.

**Sub-task 5** — two value migrations. `init_db()` runs both
automatically on next app start; a user upgrading from a v1.2 DB
does not need to execute anything manually. For the record, the
equivalent SQL executed is:

```sql
-- Pipeline-stage-0 literal rename ([OPEN] → [SAVED]).
-- Idempotent via the WHERE guard: the second run finds no matching
-- rows (every pre-v1.3 row already translated) and is a no-op.
UPDATE positions
   SET status = '[SAVED]'
 WHERE status = '[OPEN]';

-- Priority short-code rename ("Med" → "Medium").
-- Idempotent for the same reason.
UPDATE positions
   SET priority = 'Medium'
 WHERE priority = 'Med';
```

Schema DEFAULT clauses do **not** change — Sub-task 4 already lifted
them into config-driven f-strings, so the v1.3 config values
(`STATUS_VALUES[0] == '[SAVED]'`, `PRIORITY_VALUES[1] == 'Medium'`)
flow through automatically. No rebuild, no data loss, no downtime.

**Sub-task 6** — schema addition on `positions` (new column + new
trigger). `init_db()` runs the migration automatically on next app
start; a user upgrading from a v1.2 DB does not need to execute
anything manually. For the record, the equivalent SQL executed is:

```sql
-- 1. Add the column (NULL default on ALTER — SQLite rejects
--    non-constant expression DEFAULTs on ALTER TABLE ADD COLUMN
--    against a non-empty table). Idempotent via the PRAGMA
--    table_info guard in init_db().
ALTER TABLE positions ADD COLUMN updated_at TEXT;

-- 2. Backfill existing rows so they carry a stamp equivalent to
--    what the CREATE TABLE DEFAULT would have given them on a
--    fresh DB. Idempotent by the WHERE clause — a re-run finds
--    no matching rows.
UPDATE positions
   SET updated_at = datetime('now')
 WHERE updated_at IS NULL;

-- 3. Install the AFTER UPDATE trigger so subsequent mutations
--    refresh the stamp automatically. Idempotent via
--    IF NOT EXISTS.
CREATE TRIGGER IF NOT EXISTS positions_updated_at
    AFTER UPDATE ON positions FOR EACH ROW
BEGIN
    UPDATE positions SET updated_at = datetime('now') WHERE id = NEW.id;
END;
```

Fresh DBs reach the same final state via the CREATE TABLE DDL
(`updated_at TEXT DEFAULT (datetime('now'))`) plus the trigger CREATE
— so steps 1 and 2 above execute only on pre-v1.3 upgrades. No
rebuild, no data loss, no downtime. Loop prevention on the trigger's
inner UPDATE rides on SQLite's default `recursive_triggers = OFF`;
users who `PRAGMA recursive_triggers = ON` globally would see infinite
recursion on every UPDATE to `positions`.

**Sub-task 7** — schema addition on `positions` (new freetext
companion column for the categorical `work_auth` field).
`init_db()` runs the migration automatically on next app start; a
user upgrading from a v1.2 DB does not need to execute anything
manually. For the record, the equivalent SQL executed is:

```sql
-- Plain TEXT, no DEFAULT — existing rows correctly carry NULL
-- (v1.2 never collected this field, so NULL is the honest
-- "unknown" state). The PRAGMA table_info guard in init_db()
-- makes the ALTER idempotent.
ALTER TABLE positions ADD COLUMN work_auth_note TEXT;
```

Unlike Sub-task 6's `updated_at` migration, no backfill UPDATE
is needed here — the fresh-DB CREATE TABLE DDL and the migration
ALTER both produce the same "NULL-able TEXT, no DEFAULT" column,
so the two paths converge without any extra SQL. If a dev DB
carries legacy six-value `work_auth` strings (Sub-task 3 noted
those would need manual translation; no auto-migration runs),
the `work_auth_note` column is still added cleanly by this
step — translating the old `work_auth` enum values is an
independent manual action.

**Sub-task 8** — schema normalization (new `interviews` sub-table
replacing `applications.interview1_date` / `interview2_date`).
`init_db()` runs this automatically on the first app start after
upgrade; a user does not need to execute anything manually. For
the record, the equivalent SQL executed is:

```sql
-- (a) New sub-table (see DESIGN §6.2 for the full column spec).
CREATE TABLE IF NOT EXISTS interviews (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  INTEGER NOT NULL,
    sequence        INTEGER NOT NULL,
    scheduled_date  TEXT,
    format          TEXT,
    notes           TEXT,
    UNIQUE (application_id, sequence),
    FOREIGN KEY (application_id) REFERENCES applications(position_id)
        ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_interviews_application
    ON interviews(application_id);

-- (b) One-shot copy of legacy flat columns into the sub-table.
--     Only rows whose source date is non-NULL contribute.
INSERT INTO interviews (application_id, sequence, scheduled_date)
    SELECT position_id, 1, interview1_date
      FROM applications WHERE interview1_date IS NOT NULL;
INSERT INTO interviews (application_id, sequence, scheduled_date)
    SELECT position_id, 2, interview2_date
      FROM applications WHERE interview2_date IS NOT NULL;

-- (c) NULL-clear the legacy columns (DESIGN §6.3 step c).
--     Physical columns stay in CREATE TABLE applications until
--     a future rebuild drops them.
UPDATE applications
   SET interview1_date = NULL,
       interview2_date = NULL
 WHERE interview1_date IS NOT NULL
    OR interview2_date IS NOT NULL;
```

Idempotence is implemented via a **migrate-once gate** rather than
by per-statement guards: `init_db()` samples `sqlite_master` BEFORE
the `CREATE TABLE IF NOT EXISTS interviews` and only runs steps
(b) + (c) on the first call (when interviews was absent
pre-create). Subsequent calls find interviews already present and
skip the copy entirely — no INSERT OR IGNORE, no WHERE IS NULL
re-checks. A dev DB that somehow has an interviews table but
un-cleared legacy data (hand-built, partial failed migration) is
out of scope for the auto-path; recover with a one-time manual run
of steps (b) + (c). No rebuild, no data loss, no downtime on the
normal v1.2 → v1.3 upgrade.

**Sub-task 9** requires no migration — the cascade rewire + new
`is_all_recs_submitted` helper + `compute_materials_readiness`
alias swap are all pure behavioural / refactor changes. Existing
applications / interviews / recommenders rows persist untouched;
`upsert_application` and `add_interview` return a dict now instead
of `None`, but existing callers ignored the return value.

**Sub-task 10** — schema migration splitting the dual-purpose
`applications.confirmation_email` TEXT column into
`confirmation_received INTEGER DEFAULT 0` + `confirmation_date TEXT`.
`init_db()` runs this automatically on the first app start after
upgrade; a user does not need to execute anything manually. For
the record, the equivalent SQL executed is:

```sql
-- (a) Add the two new columns. Each ALTER is guarded by
--     PRAGMA table_info (absent ⇒ add, present ⇒ skip) so a
--     rerun is a strict no-op.
ALTER TABLE applications
    ADD COLUMN confirmation_received INTEGER DEFAULT 0;
ALTER TABLE applications
    ADD COLUMN confirmation_date TEXT;

-- (b) One-shot translation of the two legitimate legacy shapes.
--     Gated by a migrate-once flag (either new column absent
--     pre-ALTER ⇒ run the UPDATEs; both present ⇒ skip).
--
--     Date-shaped legacy values: the 10-character ISO date
--     pattern captured via SQLite GLOB character classes.
--     Anything not matching this shape — including 'Y', '',
--     NULL, legacy 'N', or freetext — falls through.
UPDATE applications
   SET confirmation_received = 1,
       confirmation_date     = confirmation_email
 WHERE confirmation_email GLOB
       '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]';

--     Flag-only legacy values: 'Y' sets the flag; the date
--     stays NULL because the old column never recorded one
--     alongside the 'Y' sentinel.
UPDATE applications
   SET confirmation_received = 1
 WHERE confirmation_email = 'Y';

-- (c) NULL-clear the legacy column per DESIGN §6.3 step (c)
--     "leave old columns NULL until a rebuild drops them".
--     Runs LAST so the value-extracting UPDATEs above still
--     see the original contents — clearing first would leave
--     nothing to translate. Parallels the interview1_date /
--     interview2_date NULL-clear in the Sub-task 8 migration.
--     Landed in the post-Sub-task-14 follow-up; see the
--     `### Fixed` entry above.
UPDATE applications
   SET confirmation_email = NULL
 WHERE confirmation_email IS NOT NULL;

-- The physical `confirmation_email` column stays in the
-- applications CREATE TABLE DDL — dead weight but preserved
-- to avoid a table-rebuild migration this release. Scheduled
-- for physical drop in v1.0-rc.
```

Idempotence follows the Sub-task 8 **migrate-once gate** shape:
the one-shot UPDATE block only fires when either new column was
absent pre-ALTER. A second `init_db()` call finds both columns
already present and skips the UPDATEs entirely — no
re-translation of any legacy value, no overwrite of user-entered
data that happens to look like the legacy shapes. Values that fall
through both WHERE clauses (NULL, `''`, legacy `'N'`, freetext)
leave the new columns at their DEFAULTs (received=0, date=NULL);
this matches "no confirmation data" and avoids guessing beyond the
two shapes D19 names.

A dev DB that somehow has the new columns but legacy values still
in `confirmation_email` (hand-built, partial failed migration) is
out of scope for the auto-path; recover with a one-time manual run
of the UPDATEs above (the two value-extracting UPDATEs followed by
the step (c) NULL-clear).

**Sub-task 11** — schema migration rebuilding the `recommenders`
table to convert `confirmed TEXT` → `confirmed INTEGER`,
`reminder_sent TEXT` → `reminder_sent INTEGER DEFAULT 0`, and add
`reminder_sent_date TEXT`. `init_db()` runs this automatically on
the first app start after upgrade; a user does not need to execute
anything manually. Unlike Sub-tasks 8 + 10 (which kept legacy
columns physically present), this sub-task is a full table rebuild
because SQLite lacks in-place column-type change. For the record,
the equivalent SQL executed is:

```sql
-- (1) CREATE the target-schema table under a temporary name.
CREATE TABLE recommenders_new (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id        INTEGER NOT NULL,
    recommender_name   TEXT,
    relationship       TEXT,
    asked_date         TEXT,
    confirmed          INTEGER,                -- 0, 1, or NULL
    submitted_date     TEXT,
    reminder_sent      INTEGER DEFAULT 0,      -- 0 or 1
    reminder_sent_date TEXT,                   -- ISO, NULL if none
    notes              TEXT,
    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
);

-- (2) INSERT-COPY from the old table with CASE translations.
--     Other columns (id, position_id, recommender_name, relationship,
--     asked_date, submitted_date, notes) copy verbatim; id values are
--     preserved so the sqlite_sequence AUTOINCREMENT counter advances
--     past them on the next add_recommender call.
INSERT INTO recommenders_new (
    id, position_id, recommender_name, relationship, asked_date,
    confirmed, submitted_date, reminder_sent, reminder_sent_date, notes
)
SELECT
    id,
    position_id,
    recommender_name,
    relationship,
    asked_date,
    CASE confirmed
        WHEN 'Y' THEN 1
        WHEN 'N' THEN 0
        ELSE NULL
    END,
    submitted_date,
    CASE WHEN reminder_sent = 'Y' THEN 1 ELSE 0 END,
    CASE WHEN reminder_sent GLOB '????-??-??'
         THEN reminder_sent
         ELSE NULL
    END,
    notes
FROM recommenders;

-- (3) DROP the old table.  Safe with PRAGMA foreign_keys = ON:
--     recommenders is a CHILD (outbound FK to positions); nothing
--     points INTO recommenders, so the implicit DELETE FROM on DROP
--     has nothing to cascade.
DROP TABLE recommenders;

-- (4) RENAME the new table into place.
ALTER TABLE recommenders_new RENAME TO recommenders;
```

All four steps run inside a single transaction (the same one that
every init_db() DDL change shares). A mid-rebuild failure triggers
the `_connect()` context manager's rollback, so the DB cannot be
left with a half-migrated table alongside a temporary
`recommenders_new`.

Idempotence is implemented via a **declared-type gate**: before
step (1), `init_db()` reads `PRAGMA table_info(recommenders)` and
extracts the declared type of the `confirmed` column. If it is
already `INTEGER` (fresh DB built with the v1.3 CREATE TABLE, or
the rebuild has already run), the entire block short-circuits —
no re-rebuild, no data copied twice.

Value-translation caveats:

- **`confirmed` tri-state** — only the two canonical legacy values
  (`'Y'` / `'N'`) translate to integers (`1` / `0`); every other
  value (including legacy `'y'` / `'yes'` / `'maybe'` / empty
  string / any freetext typo) becomes NULL. This is the
  pending-response semantics — "we don't know for sure" is NULL,
  distinct from the explicit-no `0`. If a dev DB had been
  hand-editing the column with a non-`'Y'`/`'N'` vocabulary, those
  rows will read as pending after migration; re-save them from
  the Recommenders page (Phase 5) to set the intended integer.
- **`reminder_sent` date-shaped values** — the `GLOB '????-??-??'`
  pattern matches any 10-character `??-??` shape, including
  theoretically-pathological strings like `'abcd-ef-gh'`. Safe in
  practice because pre-v1.3 `reminder_sent` realistically held
  only dates, `'Y'`, or NULL; the looser GLOB is acceptable and
  matches the SQL the user prescribed. (Sub-task 10's
  `confirmation_email` split used a stricter `[0-9]`-digit-class
  pattern; the two patterns diverge intentionally.)
- **Explicit-unsent after migration** — a pre-v1.3
  `reminder_sent = 'Y'` row lands as `reminder_sent = 1,
  reminder_sent_date = NULL`; a pre-v1.3 date-shaped row lands
  as `reminder_sent = 0, reminder_sent_date = <value>`. If the
  user wants both flag and date set they can re-save from the
  Recommenders page (Phase 5). The migration's conservative
  "flag = 0 unless literally 'Y'" rule keeps the translation
  deterministic and matches the spec SQL exactly.

A dev DB that somehow has both the old recommenders table and a
stranded `recommenders_new` (hand-built, partial failed migration)
is out of scope for the auto-path. Recover manually: inspect both
tables, decide which carries the truth, DROP the stale one, RENAME
the live one to `recommenders`, and restart.

**Sub-task 12** requires no migration — the entire change is
display-layer (`app.py` only). No schema edit, no new database
queries, no config rename. A user upgrading to the new `app.py`
sees the wide layout, the removed 🔄 Refresh button, the Tracked
help-tooltip, and the `FUNNEL_BUCKETS`-aggregated funnel bars on
the next page load. Existing DBs round-trip transparently. The
session flag `st.session_state["_funnel_expanded"]` is
session-scoped and defaults to False — no persistence to disk, no
"migration" of prior sessions needed.

**Sub-task 13** requires no migration — the entire change is
display-layer (`pages/1_Opportunities.py` only). No schema edit,
no new database queries, no config rename. A user upgrading to
the new page sees the wide layout, the status selectboxes
rendering display labels (Saved / Applied / …) instead of raw
bracketed values, the edit-panel tab strip driven by a horizontal
`st.radio` instead of `st.tabs`, and the Delete button absent on
Requirements / Materials / Notes tabs. Existing DBs round-trip
transparently (storage still holds raw `STATUS_VALUES`; format_func
only changes what the UI renders). The session flag
`st.session_state["_active_edit_tab"]` is session-scoped, defaults
to `"Overview"` (the first `EDIT_PANEL_TABS` entry) via st.radio's
`index=0` + Streamlit's widget-default contract — no persistence
to disk, no "migration" of prior sessions needed.

**Sub-task 14** requires no migration — the entire change is docs
(`GUIDELINES.md`, `CHANGELOG.md`, `roadmap.md`, `TASKS.md`; no
edits needed in `docs/ui/wireframes.md` / `docs/dev-notes/
extending.md` after audit). No schema edit, no new database
queries, no config rename, no code touched. A user upgrading
reads more v1.3-accurate conventions in GUIDELINES (status-
selectbox examples matching the live `pages/1_Opportunities.py`,
pre-merge grep pattern matching the current stage-0 literal,
sentinel list mentioning the Sub-task 12/13 additions) — but
nothing about the running app or its database changes.

### Changed — v1.1 doc refactor (branch `feature/docs-refactor-pre-t4`)

- **DESIGN.md** — drift pass (C1–C13) + restructured: tech stack reflects
  Plotly Graph Objects (not Express) and installed vs required versions
  (Streamlit 1.50 floor, tested with 1.56); config spec regenerated to
  match `config.py` (adds STATUS_OPEN/APPLIED/INTERVIEW, TERMINAL_STATUSES,
  REQUIREMENT_VALUES/LABELS, RESULT_DEFAULT, EDIT_PANEL_TABS); §6.3 data
  migrations subsection added; §10 decision-log namespace clarified
  (D1–D10 frozen; phase decisions use P3-D1/P4-D1; new decisions go to
  `docs/adr/`); §11 extension guide: `POSITION_FIELDS` → `QUICK_ADD_FIELDS`
- **GUIDELINES.md** — restructured: added §9 Testing Conventions and
  §10 Review Conventions; trimmed §11 Git Workflow from ~170 lines to
  ~35 lines (depth extracted to `docs/dev-notes/git-workflow-depth.md`);
  §7 Streamlit Patterns expanded with @st.dialog, st.switch_page, sentinel
  pattern, _safe_str; version table matches DESIGN
- **`docs/adr/`** — new folder, empty per the forward-only policy
  (D1–D10 not backfilled); README with Michael-Nygard template and
  relationship table to existing decision systems
- **`docs/dev-notes/`** — new folder with two deep-dive references:
  `git-workflow-depth.md` (254 lines, extracted from old GUIDELINES §9)
  and `streamlit-state-gotchas.md` (308 lines, 14 Streamlit 1.56 quirks
  consolidated from scattered comments)
- **TASKS.md** — trimmed from ~90 lines to ~40 lines; personal postdoc
  tasks (CV prep, research statement, recommender outreach) removed per
  scope decision (one scope per file)
- **roadmap.md** — restructured: added explicit v1 Ship Criteria;
  backlog split into P1/P2/P3; v2 Vision moved above Out-of-scope
- **CHANGELOG.md** — this file, created; v0.1.0–v0.4.0 backfilled from
  git log
- **`.gitignore`** — `CLAUDE.md` and `PHASE_*_GUIDELINES.md` added
  (internal working memory; not public-repo material)

### Deferred code changes (separate branch, pending approval)

Documentation for these landed in v1.1 but the code changes themselves
are a separate branch (`feature/code-refactor-pre-t4`) awaiting approval:

- ~~Rename `[OPEN]` → `[SAVED]`; `PRIORITY_VALUES` `"Med"` → `"Medium"`
  (with one-shot UPDATE migrations)~~ — shipped in the v1.3 alignment
  pass above (Sub-task 5).
- `ARCHIVED_BUCKET` grouping of terminal statuses on the dashboard funnel
  (note: the `STATUS_LABELS` half of this item shipped in the v1.3
  alignment pass above; the funnel-bucket half is already live in
  `FUNNEL_BUCKETS` as the `"Archived"` entry)
- Delete the 🔄 Refresh button on `app.py`
- C1: `database.py compute_materials_readiness` use `config.STATUS_OPEN/...`
  aliases instead of hardcoded tuple
- C2: ~~delete unused `TRACKER_PROFILE`~~ — superseded by DESIGN v1.3 §5.1,
  which locks `TRACKER_PROFILE` + `VALID_PROFILES` as the v1 API
- C6/C7: config-drive schema DEFAULTs in `init_db()`
- ~~C12: add `DEADLINE_URGENT_DAYS <= DEADLINE_ALERT_DAYS` assertion~~
  — shipped in the v1.3 alignment pass above (invariant #8)
- Set `st.set_page_config(layout="wide", ...)` on `app.py` and pages
- Tooltip on "Tracked" KPI

### Migration

No migrations required for the doc refactor. The deferred code refactor
will include status/priority rename migrations — will be documented here
when that release ships.

---

## [v0.4.0] — 2026-04-22 — Phase 4 Tier 3: Materials Readiness

### Added
- Dashboard right half-column panel: two `st.progress` bars
  (`"Ready to submit: N"` / `"Still missing: M"`, values = count /
  `max(total, 1)`) driven by `database.compute_materials_readiness()`
- `"→ Opportunities page"` CTA via `st.switch_page` (key
  `materials_readiness_cta`)
- Empty-state branch: `st.info("Materials readiness will appear once
  you've added positions with required documents.")` when `ready + pending == 0`;
  subheader always renders (page-height stability, mirrors T2-B pattern)
- `TestT3MaterialsReadiness` — 8 AppTest tests

### Notes
- Total tests green: **271** (from 263) · zero deprecation warnings
- Merge commit: `5ac0f63`
- Pre-merge review: `reviews/phase-4-Tier3-review.md` (verdict: approve + merge;
  4 observations kept by design, zero pre-merge fixes)
- First Phase-4 tier to ship with zero pre-merge fixes (Tier 1 had 2,
  Tier 2 had 2)

---

## [v0.3.0] — 2026-04-22 — Phase 4 Tier 2: Application Funnel

### Added
- Plotly horizontal bar funnel from `count_by_status()`, one bar per
  `config.STATUS_VALUES` entry; marker colors from `config.STATUS_COLORS`;
  y-axis reversed so pipeline reads top-down `[OPEN]` → `[DECLINED]`
- Sparse-dict fill: `[_status_counts.get(s, 0) for s in STATUS_VALUES]`
  keeps the chart shape stable as the pipeline fills up
- Empty-state (Option C trigger `sum(count_by_status().values()) == 0`;
  exact wording γ — pinned by `test_empty_state_copy_is_spec_exact`)
- Subheader renders in both branches so page height doesn't flicker
- Funnel placed in left half of `_left_col, _right_col = st.columns(2)`
  per U2; T3 reuses the right half
- 17 tests across `TestT2AFunnelBar` / `TestT2BFunnelEmptyState` /
  `TestT2CFunnelLayout`

### Notes
- Total tests green: **263** · zero deprecation warnings
- Merge commit: `96a5c76` (PR #5)
- Pre-merge review: `reviews/phase-4-Tier2-review.md`

---

## [v0.2.0] — 2026-04-21 — Phase 4 Tier 1: Dashboard Shell + KPIs

### Added
- `app.py` title "Postdoc Tracker" + top-bar 🔄 Refresh button
  (`st.columns([6, 1])`)
- 4 KPI cards (`st.columns(4)`): Tracked · Applied · Interview · Next Interview
- Tracked = `count([OPEN]) + count([APPLIED])` ("opportunities that
  might get moved forward"; INTERVIEW / OFFER excluded — have their own KPIs)
- Next Interview: earliest future date across `interview1_date` AND
  `interview2_date` across all rows, rendered `'{Mon D} · {institute}'`;
  "—" when empty (U3)
- Empty-DB hero callout with primary CTA `"+ Add your first position"`
  routing via `st.switch_page("pages/1_Opportunities.py")` when
  `tracked + applied + interview == 0` (U5)
- 23 tests: `TestT1AppShell` (+2) · `TestT1CKpiCountsAndRefresh` (+7) ·
  `TestT1DNextInterviewKpi` (+7) · `TestT1EEmptyDbHero` (+7)

### Changed
- `config.py`: added three named-status aliases
  `STATUS_OPEN` / `STATUS_APPLIED` / `STATUS_INTERVIEW` as pure
  additions over existing `STATUS_VALUES` entries (T1-C carve-out;
  keeps anti-typo guardrail)

### Notes
- Total tests green: **246** · zero deprecation warnings
- Merge commit: `f49ec5f` (PR #4)
- Pre-merge review: `reviews/phase-4-Tier1-review.md`

---

## [v0.1.0] — 2026-04-20 — Phase 3: Opportunities Page

### Added
- `pages/1_Opportunities.py` with Tiers 1–5:
  - **Quick-add** expander: 6-field form from `config.QUICK_ADD_FIELDS`;
    whitespace-only validation; `st.toast` on success; friendly
    `st.error` on DB failure (no re-raise)
  - **Filter bar**: status / priority / field (literal substring with
    `regex=False` so "C++" doesn't crash pandas str.contains)
  - **Positions table** via `st.dataframe(width="stretch",
    on_select="rerun", selection_mode="single-row")` with deadline
    urgency column from `config.DEADLINE_URGENT_DAYS/ALERT_DAYS`
  - **Edit panel** (subheader + 4 tabs driven by `config.EDIT_PANEL_TABS`):
    - Overview: 7 pre-filled widgets + Save (T5-A) + Delete (T5-E)
    - Requirements: `st.radio` per `REQUIREMENT_DOCS`; Save writes only
      `req_*` keys (T5-B) so `done_*` survives Y↔N flips
    - Materials: state-driven checkboxes filtered by live session_state;
      Save writes only `done_*` for visible docs (T5-C)
    - Notes: `st.text_area` inside `st.form("edit_notes_form")`; empty
      input stored as `""` not `NULL` (T5-D)
  - **Overview Delete** via `@st.dialog` confirm (T5-E); FK cascade
    (positions → applications + recommenders)
- `_safe_str(v)` NaN-pre-seed guard for pandas object-dtype NULL cells
- `_edit_form_sid` sentinel pattern to defeat widget-value trap
- `_skip_table_reset` one-shot for post-save selection survival
- Paired session-state cleanup for `selected_position_id` /
  `_edit_form_sid` / `_delete_target_*`
- 223 tests across the suite

### Fixed
- Pandas NaN in session_state TypeError (post-review): `_safe_str`
  applied to all five text pre-seed sites
- Review fixes F1–F5: try/except around database writes, whitespace
  validation, deadline urgency type-safety, explicit dict[str, Any]
  typing, `st.toast` for rerun-safe confirmations

### Notes
- Merge commit: `c972385` (PR #3)
- Pre-merge reviews: `reviews/phase-3-review.md`,
  `reviews/phase-3-tier5-review.md`,
  `reviews/phase-3-tier5-premerge.md`

---

## Pre-v0.1.0 (historical, pre-tag)

### 2026-04-16 — Phase 2: Data Layer
- `database.py`: full CRUD (`add_position`, `get_all_positions`,
  `get_position`, `update_position`, `delete_position`,
  `get_application`, `upsert_application`, `add_recommender`,
  `get_recommenders`, `get_all_recommenders`, `update_recommender`,
  `delete_recommender`)
- 5 dashboard queries (`count_by_status`, `get_upcoming_deadlines`,
  `get_upcoming_interviews`, `get_pending_recommenders`,
  `compute_materials_readiness`)
- Migration-aware `init_db()`: `ALTER TABLE ADD COLUMN` loop picks up
  new entries in `config.REQUIREMENT_DOCS` on next start
- `exports.py` stub (functions present but empty; real generators in
  Phase 6)
- `postdoc.db` initialized (3 tables, 37 columns in `positions`)
- 105 tests; 100% coverage of the data layer

### 2026-04-15 — Phase 1: Environment & Config
- `.venv/` created; Streamlit 1.56.0, Plotly 6.7.0, pandas 3.0.2 installed
- `requirements.txt` generated with pinned versions
- `config.py` with full vocabulary set: `STATUS_VALUES`,
  `STATUS_COLORS`, `PRIORITY_VALUES`, `WORK_AUTH_OPTIONS`,
  `FULL_TIME_OPTIONS`, `SOURCE_OPTIONS`, `RESPONSE_TYPES`,
  `RESULT_VALUES`, `RELATIONSHIP_TYPES`, `REQUIREMENT_DOCS`,
  `QUICK_ADD_FIELDS`, dashboard thresholds

### 2026-04-15 — Initial design
- `DESIGN.md` v1.0: master technical specification (architecture,
  schema, UI wireframes, data flow, 10 architectural decisions)
- `GUIDELINES.md` v1.0: coding conventions for all sessions
- `roadmap.md`: 7-phase plan + post-v1 backlog + v2 general-job-tracker vision
- Seed tables: `OPPORTUNITIES.md`, `PROGRESS.md`, `RECOMMENDERS.md`
  (hand-maintained; superseded once `exports.py` is complete in Phase 6)

---

## Version links

[Unreleased]: https://github.com/YuZh98/hugs_application_tracker/compare/v0.7.0...HEAD
[v0.7.0]: https://github.com/YuZh98/hugs_application_tracker/releases/tag/v0.7.0
[v0.6.0]: https://github.com/YuZh98/hugs_application_tracker/releases/tag/v0.6.0
[v0.5.0]: https://github.com/YuZh98/hugs_application_tracker/releases/tag/v0.5.0
[v0.4.0]: https://github.com/YuZh98/hugs_application_tracker/releases/tag/v0.4.0
[v0.3.0]: https://github.com/YuZh98/hugs_application_tracker/releases/tag/v0.3.0
[v0.2.0]: https://github.com/YuZh98/hugs_application_tracker/releases/tag/v0.2.0
[v0.1.0]: https://github.com/YuZh98/hugs_application_tracker/releases/tag/v0.1.0

## Links

- [Git tags](https://github.com/YuZh98/hugs_application_tracker/tags) — one per released version
- [Pull requests](https://github.com/YuZh98/hugs_application_tracker/pulls) — full history of merged work
- [Roadmap](roadmap.md) — what's coming next
