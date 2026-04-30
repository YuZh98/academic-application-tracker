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
- [ ] **T5** Recommender Alerts panel on `app.py` — DESIGN §8.1
  - [ ] T5-A: group `get_pending_recommenders()` by `recommender_name`;
        emit one `st.container(border=True)` per person with `⚠ {Name}`
        header + bullet list of `{position} (asked {N}d ago, due {deadline})`
        lines; empty-state `st.info("No pending recommender follow-ups.")`.
        **Note:** the `Compose reminder email` button + LLM-prompts
        expander (DESIGN §8.4 D-C) belong on the Recommenders **page**
        (Phase 5 T6), NOT on the dashboard. T5 only renders the alert
        cards.
  - Tests: `tests/test_app_page.py::TestT5RecommenderAlerts` with the
    same class-constants pattern.
- [ ] **T6** Phase 4 finish — pre-merge review + PR + tag `v0.5.0`
  - [ ] Cross-panel cohesion smoke (manual browser at 1280 / 1440 /
        1680 widths; screenshots to `docs/ui/screenshots/v0.5.0/`)
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

_Updated: 2026-04-27 (v1 plan locked; Phase 4 T4 next on branch `feature/phase-4-finish`)_
