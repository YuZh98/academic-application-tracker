# Tasks

_Scope: software for this application tracker only. Older completions move to
`CHANGELOG.md` at the end of each sprint._

---

## Current sprint — Phase 4 finish (T4 + T5 + T6)

Branch: `feature/phase-4-finish` (to be created off `main` at `d7968e5`)

Per **Q1 Option B** from the 2026-04-27 v1 planning session, the
existing T4/T5/T6 roadmap structure is preserved (no re-tiering).
DESIGN.md §8.1 panel rows + empty-state matrix are the contract.

- [x] **T4** Upcoming timeline panel on `app.py` — DESIGN §8.1 (locked T4-0 + T4-0b)
  - [x] T4-0 + T4-0b: lock §8.1 panel column contract — six columns
        `(date, days_left, label, kind, status, urgency)`; date as
        `datetime.date` for chronological sort; `days_left` phrased
        `"today"` / `"in 1 day"` / `"in N days"`; Label as
        `"{institute}: {position_name}"`; Kind as
        `"Deadline for application"` / `f"Interview {sequence}"`;
        window selector via `st.selectbox(UPCOMING_WINDOW_OPTIONS)`
        with default `DEADLINE_ALERT_DAYS` and dynamic subheader
        `f"Upcoming (next {selected_window} days)"`. New config invariant
        #10: `DEADLINE_ALERT_DAYS in UPCOMING_WINDOW_OPTIONS`.
  - [x] T4-A `database.get_upcoming(days=DEADLINE_ALERT_DAYS)`: thin
        projection over `get_upcoming_deadlines(days)` +
        `get_upcoming_interviews()` returning the six-column shape
        above; both `days_left` and `urgency` derive from the same
        `days_away` int per row so the columns cannot drift; thresholds
        resolve at call time from config.
  - [x] T4-B `app.py` panel: full-width below the funnel/readiness
        `st.columns(2)` row; `st.columns([3, 1])` carries the dynamic
        subheader (left) + `upcoming_window` selectbox (right);
        `st.dataframe(width="stretch", hide_index=True)` with display
        headers `(Date, Days left, Label, Kind, Status, Urgency)` —
        Date rendered via `st.column_config.DateColumn(format="MMM D")`,
        Status mapped via `STATUS_LABELS.get(raw, raw)`; empty-state
        `f"No deadlines or interviews in the next {selected_window} days."`.
        Adds `config.UPCOMING_WINDOW_OPTIONS = [30, 60, 90]` + §5.2
        invariant #10.
  - Tests: `tests/test_app_page.py::TestT4UpcomingTimeline` (19) with
    class-level `SUBHEADER_DEFAULT` + `EMPTY_COPY_DEFAULT` +
    `DISPLAY_COLUMNS` + `WINDOW_KEY` constants per GUIDELINES §9, plus
    3 new `tests/test_config.py` invariant-#10 tests.
- [x] **T5** Recommender Alerts panel on `app.py` — DESIGN §8.1
  - [x] T5-A: group `get_pending_recommenders()` by `recommender_name`;
        emit one `st.container(border=True)` per person with `⚠ {Name}`
        header + bullet list of `{position} (asked {N}d ago, due {deadline})`
        lines; empty-state `st.info("No pending recommender follow-ups.")`.
        Position label uses T4 precedent `{institute}: {position_name}`
        (bare `position_name` when institute is empty); due-date renders
        in `Mon D` form (T4 DateColumn precedent), `—` em-dash for NULL
        deadline (mirrors `NEXT_INTERVIEW_EMPTY`). `groupby(sort=False)`
        relies on the SQL-side `ORDER BY recommender_name ASC,
        deadline_date ASC NULLS LAST` so within-group bullets are
        deadline-asc and across-group cards are alphabetical without
        any extra sort.
        **Note:** the `Compose reminder email` button + LLM-prompts
        expander (DESIGN §8.4 D-C) belong on the Recommenders **page**
        (Phase 5 T6), NOT on the dashboard. T5 only renders the alert
        cards.
  - Tests: `tests/test_app_page.py::TestT5RecommenderAlerts` (15) with
    class-level `SUBHEADER` + `EMPTY_COPY` + `BORDER_SOURCE` +
    `WARN_GLYPH` constants per GUIDELINES §9. Four groups: subheader /
    layout, empty / populated branches, card content, grouping by
    recommender_name.
- [ ] **T6** Phase 4 finish — pre-merge review + PR + tag `v0.5.0`
  - [x] Cross-panel cohesion smoke — audit doc at
        `reviews/phase-4-finish-cohesion-smoke.md`; verbatim AppTest
        renders for both populated + empty DB pin every subheader,
        KPI label, info-message, dataframe column, and recommender-
        card markdown; six cohesion dimensions verified (subheader
        rhythm, empty-state pattern, status-sentinel stripping,
        label-format reuse, date-format reuse, layout hierarchy);
        zero 🔴 / 🟠 + two 🟡 polish (wireframe ASCII drift; em-dash
        literal-vs-constant) deferred. 1280 / 1440 / 1680 PNG
        captures land in `docs/ui/screenshots/v0.5.0/` (with seed
        snippet at `docs/ui/screenshots/v0.5.0/.seed-snippet.py`)
        once the user runs them manually — preview-tool macOS
        sandbox blocks headless capture on this setup; boot smoke
        ran via Bash `streamlit run` (HTTP 200) + AppTest probes
        (no exception on populated or empty DB).
  - [x] Funnel disclosure-toggle polish — replace pre-T6
        unidirectional `[expand]` button with a bidirectional
        toggle (DESIGN §8.1 T6 amendment 2026-04-30): single
        `st.button(type="tertiary")` placed in the funnel
        subheader row via `st.columns([3, 1])` (mirror of T4
        Upcoming idiom); state-keyed labels in
        `config.FUNNEL_TOGGLE_LABELS`
        (`+ Show all stages` ↔ `− Show fewer stages`) following
        the project's `<symbol> <verb-phrase>` CTA convention;
        invariant #11 added to `config.py` + DESIGN §5.2; branch
        (b) info copy updated to reference the toggle by label
        rather than spatial direction. Three-commit TDD round
        (`test:` red → `feat:` green → `chore:` rollup); 535 →
        553 tests passing under both pytest gates. Solves the
        two user-reported issues (no collapse path; button too
        visually heavy for a chart control).
  - [ ] `reviews/phase-4-finish-review.md` (Exec summary → Findings →
        Junior-engineer Q&A → Verdict, per GUIDELINES §10)
  - [ ] PR; address review nits inline; merge; tag `v0.5.0`

## Prior sprint — v1.1 doc refactor (merged via PR #7)

- [x] Commit 1: DESIGN + GUIDELINES drift fixes (C1–C13)
- [x] Commit 2: DESIGN restructure + `docs/adr/` skeleton
- [x] Commit 3: GUIDELINES restructure + `docs/dev-notes/` extraction
- [x] Commit 4: TASKS + roadmap + CHANGELOG + .gitignore
- [x] Retroactive git tags: `v0.1.0` · `v0.2.0` · `v0.3.0` · `v0.4.0`
- [x] Push branch; open PR; merge to main

## Prior sprint — v1.3 alignment (merged via PR #8 + PR #9 + PR #10)

- [x] Sub-tasks 1–14 (config additions, vocab migrations, schema
      normalization, R1/R2/R3 cascade, confirmation_email split,
      recommenders rebuild, dashboard + Opportunities page DESIGN-§8
      alignment, doc sweep) — merged via PR #8 (`ace9acb`).
- [x] Test-reliability + completeness review — 9 hardening commits;
      merged via PR #9 (`0cb6f77`).
- [x] Sub-task 13 reverted (edit panel restored to `st.tabs` after the
      radio-based tab selector caused two user-reported widget-state-loss
      bugs); merged via PR #10 (`d7968e5`). 478 tests green.

---

## Up next (after Phase 4 finish)

### Code carry-overs (deferrable)

- [ ] **C2** Delete unused `TRACKER_PROFILE` from `config.py` — flagged
      by v1.1 doc refactor; one-line removal but config invariant #1
      (`TRACKER_PROFILE in VALID_PROFILES`) goes with it. Defer until a
      cleanup tier; not blocking v1.0.

### Phase 5 — Applications + Recommenders pages

Per **Q5 Option A**, build Applications page first.

- [ ] **T1** Applications page shell (`pages/2_Applications.py`) —
      `set_page_config`, title, default filter excluding
      `STATUS_SAVED + STATUS_CLOSED`, table view sorted by deadline
  - [x] T1-A `database.get_applications_table()` joined reader:
        10-column projection over positions × applications LEFT JOIN
        (`position_id, position_name, institute, deadline_date,
        status, applied_date, confirmation_received,
        confirmation_date, response_type, result`); sort
        `deadline_date ASC NULLS LAST, position_id ASC` with the
        `position_id` tiebreaker pinned by
        `test_position_id_breaks_deadline_ties` so equal-deadline
        rows stay stable across reruns (selection-survival
        invariant, streamlit-state-gotchas #12). Filter-agnostic:
        terminal-status rows are present; the page applies the
        default `STATUS_FILTER_ACTIVE_EXCLUDED` filter on top
        (T1-B). 8 new tests in `TestGetApplicationsTable`; suite
        553 → 561 under both pytest gates.
  - [x] T1-B Page shell + filter — `set_page_config(layout="wide")`,
        `database.init_db()`, `st.title("Applications")`, and a
        status filter selectbox keyed `apps_filter_status` whose
        options are `[STATUS_FILTER_ACTIVE, "All", *STATUS_VALUES]`
        (default = `STATUS_FILTER_ACTIVE`, `format_func` =
        `STATUS_LABELS.get(v, v)` for sentinel-safe identity
        fallthrough). New config constants + invariant #12:
        `STATUS_FILTER_ACTIVE = "Active"` and
        `STATUS_FILTER_ACTIVE_EXCLUDED = frozenset({STATUS_SAVED,
        STATUS_CLOSED})`; DESIGN §5.1 + §5.2 + §8.3 cross-referenced.
        13 new tests (7 in `test_config.py` + 6 in new
        `test_applications_page.py`); suite 561 → 574 under both
        pytest gates.
  - [x] T1-C Table render — read-only `st.dataframe(width="stretch",
        hide_index=True, key="apps_table")` with the six wireframe
        columns `Position / Applied / Recs / Confirmation /
        Response / Result` in display order; sort inherited from
        `get_applications_table` (page does NOT re-sort). Filter
        resolved at render time (Active → exclude
        `STATUS_FILTER_ACTIVE_EXCLUDED`; All → no exclusion;
        specific status → narrow). Per-row `is_all_recs_submitted`
        glyph for the Recs column. Empty post-filter →
        `st.info("No applications match the current filter.")`,
        table suppressed. **DESIGN §8.3 D-A amendment**:
        Confirmation column folds the per-cell tooltip into inline
        cell text — three states (`—` / `✓ Mon D` / `✓ (no date)`)
        — because Streamlit 1.56's `st.dataframe` has no per-cell
        tooltip API; full resolution in
        `reviews/phase-5-tier1-review.md`. 12 new tests in
        `TestApplicationsPageTable` (parametrize counts each row
        as a separate test); suite 574 → 586 under both pytest
        gates.
- [ ] **T2** Application detail card (Applied, Confirmation per DESIGN
      §8.3 D-A glyph + tooltip rules, Response, Result, Notes — all
      editable via `st.form`)
- [ ] **T3** Inline interview list UI (per DESIGN §8.3 D-B) —
      `apps_interview_{id}_*` keying, single Save form
      `apps_interviews_form`, `@st.dialog`-gated delete, R2-toast
      surfacing on add when `add_interview` returns `status_changed=True`
- [ ] **T4** Recommenders alert panel (`pages/3_Recommenders.py`) —
      grouped by `recommender_name`
- [ ] **T5** Recommenders table + add form + inline edit (`asked_date`,
      `confirmed`, `submitted_date`, `reminder_sent`+`reminder_sent_date`,
      `notes`)
- [ ] **T6** Recommender reminder helpers per DESIGN §8.4 D-C (locked
      subject + body for primary mailto; `LLM prompts (N tones)`
      expander rendering pre-filled prompts as `st.code(...)` blocks)
- [ ] **T7** Phase 5 review + PR + tag `v0.6.0`

### Phase 6 — Exports

Per **Q6 Option A**, plain markdown tables.

- [ ] **T1** `write_opportunities()` generator
- [ ] **T2** `write_progress()` generator (depends on Phase 5 T3 —
      reads `interviews` data)
- [ ] **T3** `write_recommenders()` generator
- [ ] **T4** Export page — manual regenerate button + file mtimes
- [ ] **T5** Export page — `st.download_button` per file
- [ ] **T6** Phase 6 review + PR + tag `v0.7.0`

### Phase 7 — Polish

- [ ] **T1** Urgency colors on positions table (`st.column_config`)
- [ ] **T2** Position search bar on Opportunities (substring,
      `regex=False`)
- [ ] **T3** `set_page_config` sweep on remaining pages (verify
      GUIDELINES §13 step 2 holds for every page)
- [ ] **T4** Confirm-dialog audit (every destructive path wears
      `@st.dialog` with cascade-effect copy)
- [ ] **T5** Responsive layout check at 1024 / 1280 / 1440 / 1680
      widths; capture screenshots to `docs/ui/screenshots/v0.8.0/`
- [ ] **T6** Phase 7 review + PR + tag `v0.8.0`

### v1.0-rc — schema cleanup

- [ ] Physical drop of `applications.confirmation_email` per DESIGN §6.3
      "Pending column drops" — single-commit table rebuild via
      CREATE-COPY-DROP-RENAME inside one transaction; idempotent via
      `PRAGMA table_info(applications)` check on `confirmation_email`
      presence.

### Publish scaffolding (per Q7 Option C — both live + recorded GIF)

- [ ] **P1** `README.md` at repo root — what it is, the one daily
      question it answers, install/run, screenshot, link to DESIGN.md
- [ ] **P2** `LICENSE` (MIT, per DESIGN §4)
- [ ] **P3** `requirements.txt` audit + freeze (`pip freeze`, prune
      unused deps)
- [ ] **P4a** Live demo: deploy to Streamlit Cloud (note: SQLite
      ephemeral storage on Cloud — verify behavior or arrange
      persistence)
- [ ] **P4b** Recorded GIF / short walkthrough committed to `docs/`
- [ ] **P5** Doc-drift sweep — `streamlit-state-gotchas.md` gotcha #14
      (mentions deleted Refresh button) and #13 (mentions
      `interview1_date`/`interview2_date`); cross-doc link verification
- [ ] **P6** v1.0.0 PR + tag `v1.0.0` + GitHub release notes

---

## Blocked / awaiting input

_(none)_

---

## Recently done

- 2026-04-30 — **Phase 4 T6 funnel disclosure-toggle polish complete**
  on branch `feature/phase-4-tier6-Cohesion`: replaced the pre-T6
  unidirectional `[expand]` button with a bidirectional disclosure
  toggle (DESIGN §8.1 T6 amendment); `st.button(type="tertiary")`
  placed in the funnel subheader row via `st.columns([3, 1])`
  (mirror of T4 Upcoming idiom); state-keyed labels in
  `config.FUNNEL_TOGGLE_LABELS` following the project's
  `<symbol> <verb-phrase>` CTA convention. Solves two user-reported
  issues — no collapse path + button too heavy for a chart control —
  in one widget rework. Three-commit TDD round
  (`test:` red → `feat:` green → `chore:` rollup); 535 → 553 tests
  passing under both pytest gates. Live AppTest probe confirms the
  round-trip (False → True → False) with zero exceptions.
- 2026-04-30 — **Phase 4 T6 cohesion-smoke audit complete** on branch
  `feature/phase-4-tier6-Cohesion`: `reviews/phase-4-finish-cohesion-smoke.md`
  pins six cohesion dimensions across the dashboard's five panels with
  verbatim AppTest renders (populated + empty DB) as evidence; 535 tests
  green under both pytest gates. Zero 🔴 / 🟠 + two 🟡 polish deferred.
  Browser captures at 1280 / 1440 / 1680 land in
  `docs/ui/screenshots/v0.5.0/` once the user runs them manually
  (harness's macOS sandbox blocks headless screenshot via the preview
  tool). T6 second + third checkboxes (full review doc + PR + tag
  `v0.5.0`) still pending.
- 2026-04-29 — **Phase 4 T5-A green** on branch
  `feature/phase-4-tier5-RecommenderAlerts`: Recommender Alerts panel
  wired below the Upcoming row. Subheader stable in both branches;
  empty `st.info("No pending recommender follow-ups.")`; populated
  branch groups `get_pending_recommenders()` by `recommender_name`
  and emits one `st.container(border=True)` per person carrying a
  `**⚠ {Name}**` header + bullet list of `{institute}: {position_name}
  (asked {N}d ago, due {Mon D})` lines. 15 new `TestT5RecommenderAlerts`
  tests green; suite total 519 → 534 under both pytest gates.
- 2026-04-27 — **v1 plan locked** on branch `docs/v1-planning-pins`:
  GUIDELINES.md G1/G3/G4 (sentinels list, pre-commit grep, new §13
  page-authoring procedure); DESIGN.md D-A/D-B (§8.3 confirmation
  column + inline interview list UI), D-C (§8.4 mailto + LLM-prompts
  pattern), D-D (§6.3 confirmation_email v1.0-rc drop). Q1–Q8
  decisions locked.
- 2026-04-25 — **PR #10 merged** (`d7968e5`): Sub-task 13 reverted —
  edit panel restored to `st.tabs` after the radio-based tab selector
  caused two user-reported widget-state-loss bugs. 478 tests green.
- 2026-04-25 — **PR #9 merged** (`0cb6f77`): skeptical test-reliability
  + completeness review; 9 hardening commits.
- 2026-04-25 — **PR #8 merged** (`ace9acb`): v1.3 alignment Sub-tasks
  1–14 + 6 review follow-ups. Full DESIGN-to-codebase alignment.
- 2026-04-22 — **v0.4.0** Phase 4 T3 Materials Readiness merged to main (`5ac0f63`)
- 2026-04-22 — **v0.3.0** Phase 4 T2 Application Funnel merged (`96a5c76`)
- 2026-04-21 — **v0.2.0** Phase 4 T1 App shell + KPI cards merged (`f49ec5f`)

For earlier completions see [`CHANGELOG.md`](CHANGELOG.md).

---

_Updated: 2026-04-30 (Phase 4 T6 cohesion-smoke audit + funnel disclosure-toggle polish complete on branch `feature/phase-4-tier6-Cohesion`; full review doc + PR + tag `v0.5.0` next)_
