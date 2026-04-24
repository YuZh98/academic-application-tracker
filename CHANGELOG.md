# Changelog

All notable changes to the Postdoc Tracker are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(with the pre-1.0 convention that each minor bump marks one completed phase
or tier — see `GUIDELINES.md §11` for the version scheme).

Versions use the format `v<major>.<minor>.<patch>`. The `[Unreleased]` section
at the top collects changes on feature branches before they ship.

Each release entry may include a `Migration:` note with the exact SQL or
manual steps to run against a pre-existing database.

---

## [Unreleased]

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

- Rename `[OPEN]` → `[SAVED]`; `PRIORITY_VALUES` `"Med"` → `"Medium"`
  (with one-shot UPDATE migrations)
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

## Links

- [Git tags](https://github.com/YuZh98/hugs_application_tracker/tags) — one per released version
- [Pull requests](https://github.com/YuZh98/hugs_application_tracker/pulls) — full history of merged work
- [Roadmap](roadmap.md) — what's coming next
