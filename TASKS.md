# Tasks

_Scope: software for this application tracker only. Older completions move to
`CHANGELOG.md` at the end of each sprint._

---

## Current sprint — Phase 5 — Applications + Recommenders pages

Per **Q5 Option A** from the 2026-04-27 v1 planning session, build
Applications page first.

Branch (T1): merged via PR #15 (`aebbb8b`); pre-merge review at
[`reviews/phase-5-tier1-review.md`](reviews/phase-5-tier1-review.md);
suite 553 → 586 green under both pytest gates.

Branch (T2): merged via PR #16 (`b9a2c82`); pre-merge review at
[`reviews/phase-5-Tier2-review.md`](reviews/phase-5-Tier2-review.md);
suite 586 → 638 green under both pytest gates.

Branch (T3): not yet started — next functional work after the
`docs/guidelineupdate` doc-cleanup branch merges. T3 implements the
inline interview list UI per DESIGN §8.3 D-B
(`apps_interview_{id}_*` keying, single Save form, `@st.dialog`-gated
delete, R2-toast surfacing on add).

- [x] **T1** Applications page shell (`pages/2_Applications.py`) —
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
        `reviews/phase-5-tier1-review.md` + new gotcha #16 in
        `docs/dev-notes/streamlit-state-gotchas.md`. 12 new tests
        in `TestApplicationsPageTable` (parametrize counts each
        row as a separate test); suite 574 → 586 under both pytest
        gates.
- [x] **T2** Application detail card (Applied, Confirmation per DESIGN
      §8.3 D-A glyph + tooltip rules, Response, Result, Notes — all
      editable via `st.form`) — T2-A + T2-B both shipped on branch
      `feature/phase-5-tier2-ApplicationDetailCard`. Pre-merge
      review + PR pending (separate steps; not part of T2-B's
      three TDD commits per the user's pause-for-review boundary).
  - [x] T2-A Selection plumbing + editable detail card. Convert
        `apps_table` to selectable (`on_select="rerun"`,
        `selection_mode="single-row"`); add `column_config` widths
        (Position large, Confirmation medium, others small —
        AppTest-invisible per gotcha #15, source-grep pinned).
        Selection-resolution block mirrors Opportunities §8.2 with
        page-prefixed sentinels per user direction (2026-04-30):
        `applications_selected_position_id`,
        `_applications_edit_form_sid`,
        `_applications_skip_table_reset` — long-form `applications`
        prefix avoids confusion with `app.py` / dashboard sentinels.
        **Asymmetry vs. Opportunities §8.2** at `df_filtered.empty`:
        Applications does NOT pop selection on filter narrowing —
        the detail card resolves against the unfiltered `df` so an
        in-progress edit survives a filter change. Detail card
        wrapped in `st.container(border=True)` (architected for
        T3's sibling `apps_interviews_form`); header reads
        `f"{institute}: {position_name} · {STATUS_LABELS[raw]}"`;
        inline "All recs submitted: ✓ / —" via
        `is_all_recs_submitted` (vacuous-true for zero recs, D23).
        `st.form("apps_detail_form")` with 8 widgets:
        `apps_applied_date`, `apps_confirmation_received` (checkbox),
        `apps_confirmation_date`, `apps_response_type`
        (`[None, *RESPONSE_TYPES]` + `format_func` rendering None
        as `—`), `apps_response_date`, `apps_result` over
        `RESULT_VALUES`, `apps_result_notify_date`, `apps_notes`.
        Pre-seed gates on the form-id sentinel (gotcha #2); `r`
        from `get_applications_table` covers the position-side
        header fields, and a separate `database.get_application(sid)`
        read covers the application form fields not in T1-A's
        10-column projection (`response_date`,
        `result_notify_date`, `notes`). Save handler builds the
        upsert payload (date inputs round-trip via `.isoformat() if
        d else None`), calls
        `database.upsert_application(propagate_status=True)`, sets
        `_applications_skip_table_reset=True` (defense vs. gotcha
        #11 in real-browser reruns), pops the form-id sentinel,
        `st.toast(f'Saved "<name>".')`, `st.rerun()`. Failure path
        → `st.error(...)`, no re-raise (GUIDELINES §8); sentinel
        survives so the user's dirty form input is preserved for
        retry. Cascade-promotion toast (R1/R3 surfacing on
        `status_changed=True`) is T2-B's territory. New helper
        `_coerce_iso_to_date(v)` mirrors Opportunities-page F5
        defensive ISO parse. 43 new tests across five new classes
        in `test_applications_page.py` (`TestApplicationsTableColumnConfig`,
        `TestApplicationsTableSelection`,
        `TestApplicationsDetailCardRender`,
        `TestApplicationsDetailCardForm`,
        `TestApplicationsDetailCardSave`); suite 586 → 629 under
        both pytest gates.
  - [x] T2-B Cascade-promotion toast + cohesion sweep — Save
        handler now reads the upsert return value and fires a
        SECOND `st.toast(f"Promoted to {STATUS_LABELS[new_status]}.")`
        after the Saved toast whenever
        `result["status_changed"]=True`. Two toasts kept SEPARATE
        (semantically distinct events: persistence vs. pipeline
        state change); order is Saved-then-Promoted (chronological).
        Trust the upsert contract — no defensive
        `and result.get("new_status")` guard, per the 2026-04-30
        Sonnet plan critique (a guard would silently skip the
        toast on a contract violation rather than raising
        `KeyError` where the bug actually lives).
        `STATUS_LABELS.get(..., raw)` passthrough is the project
        status-display convention; the fallback is unreachable in
        practice given config invariant #3. All four R1/R3 paths
        pinned (R1-only on SAVED, R3-only on APPLIED, R1+R3
        chained from SAVED → OFFER with a DB-state probe to
        confirm R3 ran AFTER R1, terminal-guard no-op on CLOSED
        where Save still succeeds + DB still updates the
        application row but no promotion toast fires). Cohesion
        sweep: NaN-safe pre-seed parametrized over all 4 date
        widgets (closes the cohesion gap on response_date and
        result_notify_date that T2-A only individually pinned for
        applied_date and confirmation_date); save-error preserves
        form FIELD values across text_area + date_input +
        selectbox (extends T2-A's sentinel-only check). The
        filter-narrowing-keeps-form-values combination test was
        DROPPED per Sonnet — pre-seed gates on (sid changed OR
        key missing); filter narrowing alone changes neither, so
        the test would exercise Streamlit's session_state, not
        page code. 9 new tests across 2 classes
        (`TestApplicationsCascadePromotionToast`,
        `TestApplicationsCohesionSweep`); suite 629 → 638 under
        both pytest gates.
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

## Prior sprint — Phase 4 finish (PR #12 + #13 + #14, tag `v0.5.0`)

Per **Q1 Option B** from the 2026-04-27 v1 planning session, the
existing T4/T5/T6 roadmap structure was preserved (no re-tiering).
DESIGN §8.1 panel rows + empty-state matrix were the contract.

- [x] **T4** Upcoming timeline panel on `app.py` — DESIGN §8.1
      (T4-0/T4-0b column contract + T4-A `database.get_upcoming(days)`
      six-column projection + T4-B `app.py` panel render with
      `st.columns([3, 1])` subheader + window selector (default
      `DEADLINE_ALERT_DAYS`)). New config constant
      `UPCOMING_WINDOW_OPTIONS = [30, 60, 90]` + invariant #10.
      Pinned by `tests/test_app_page.py::TestT4UpcomingTimeline` (19)
      + 3 `test_config.py` invariant-#10 tests. Merged via PR #12
      (`483efa9`).
- [x] **T5** Recommender Alerts panel on `app.py` — DESIGN §8.1.
      `get_pending_recommenders()` grouped by `recommender_name` with
      one `st.container(border=True)` per person carrying a
      `⚠ {Name}` header + bullet list of `{institute}: {position_name}
      (asked {N}d ago, due {Mon D})` lines; empty-state info message.
      Position label and date format reuse the T4 precedent for
      cohesion. Pinned by `TestT5RecommenderAlerts` (15). Merged via
      PR #13 (`c5a7c76`).
- [x] **T6** Phase 4 finish — pre-merge close-out for the dashboard.
      Cohesion-smoke audit at
      [`reviews/phase-4-finish-cohesion-smoke.md`](reviews/phase-4-finish-cohesion-smoke.md)
      (six cohesion dimensions, verbatim AppTest renders for
      populated + empty DB, zero 🔴/🟠) + 7-findings review
      (`01dc7b6`) — together satisfy the GUIDELINES §10 review
      structure (no separate `phase-4-finish-review.md` file was
      written; the work was distributed across the cohesion-smoke
      audit + the inline 7-findings review). Funnel
      disclosure-toggle polish (DESIGN §8.1 T6 amendment):
      bidirectional `st.button(type="tertiary")` placed in the
      subheader row via `st.columns([3, 1])` with state-keyed
      labels in `config.FUNNEL_TOGGLE_LABELS` (`+ Show all stages`
      ↔ `− Show fewer stages`) — invariant #11 added. Three-commit
      TDD round (535 → 553 tests). Merged via PR #14 (`c93dec0`);
      tagged `v0.5.0` 2026-04-30.

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

## Up next (after Phase 5)

### Code carry-overs (deferrable)

- [ ] **C2** Delete unused `TRACKER_PROFILE` from `config.py` — flagged
      by v1.1 doc refactor; one-line removal but config invariant #1
      (`TRACKER_PROFILE in VALID_PROFILES`) goes with it. Defer until a
      cleanup tier; not blocking v1.0.
- [ ] **C3** Promote `"All"` filter sentinel to `config.py` — currently
      a magic literal in `pages/1_Opportunities.py` and
      `pages/2_Applications.py`. Asymmetric with `STATUS_FILTER_ACTIVE`
      (in config). Project-wide refactor; not blocking. Logged as 🟡
      finding 1 in [`reviews/phase-5-tier1-review.md`](reviews/phase-5-tier1-review.md).
- [ ] **C4** Split `CHANGELOG.md` `[Unreleased]` into a `[v0.5.0]`
      release section. Post-v0.4.0 work (v1.3 alignment + Phase 4
      T4/T5/T6 + this T1) accumulated under `[Unreleased]`; the
      `v0.5.0` tag now exists but no `[v0.5.0]` section sits between
      `[Unreleased]` and `[v0.4.0]`. Single housekeeping commit;
      logged as 🟢 finding 3 in
      [`reviews/phase-5-tier1-review.md`](reviews/phase-5-tier1-review.md).

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

- 2026-04-30 — **PR #16 merged** (`b9a2c82`): Phase 5 T2 (T2-A + T2-B)
  shipped — editable Application detail card behind row selection +
  cascade-promotion toast surfacing. Suite 586 → 638 under both pytest
  gates. Detailed forensic record in commit messages + the
  [`phase-5-Tier2-review.md`](reviews/phase-5-Tier2-review.md) review.
- 2026-04-30 — **Phase 5 T2-A green** on branch
  `feature/phase-5-tier2-ApplicationDetailCard`: editable
  Application detail card behind row selection. `apps_table` made
  selectable (`on_select="rerun"`, `selection_mode="single-row"`,
  `column_config` widths source-grep-pinned per gotcha #15);
  selection-resolution block resolves to
  `applications_selected_position_id` (page-prefixed sentinels
  `_applications_edit_form_sid`, `_applications_skip_table_reset`
  per user direction — long-form `applications` avoids confusion
  with `app.py`). **Asymmetry vs. Opportunities §8.2**: filter
  narrowing that excludes the selected row keeps the card open
  (the page resolves against the unfiltered `df`). Detail card
  in `st.container(border=True)` (architected for T3's sibling
  `apps_interviews_form`); header
  `f"{institute}: {position_name} · {STATUS_LABELS[raw]}"`; inline
  "All recs submitted: ✓ / —". `st.form("apps_detail_form")` with
  8 widgets; pre-seed gates on form-id sentinel; Save handler
  calls `database.upsert_application(propagate_status=True)`,
  fires `st.toast`, sets the skip-flag + pops the sentinel + reruns;
  failure path → `st.error`, sentinel survives. New helper
  `_coerce_iso_to_date(v)` mirrors Opportunities F5. R1/R3
  cascade-promotion toast lands in T2-B. 43 new tests across five
  classes in `test_applications_page.py`; suite 586 → 629 under
  both pytest gates. Three commits: `test:` red,
  `feat(applications):` green, `chore(tracker):` rollup. Multi-agent
  plan critique (Sonnet, 2026-04-30) reshaped the original
  3-sub-task split into 2 sub-tasks (T2-A includes both selection
  plumbing AND form/save) since the plumbing-only sub-task would
  have shipped a placeholder UI surface deleted by the next commit.
- 2026-04-30 — **Phase 5 T1 Applications page shell complete** on
  branch `feature/phase-5-tier1-ApplicationsPageShell`. Three
  sub-tasks shipped via TDD three-commit cadence per sub-task
  (9 commits total): T1-A `database.get_applications_table()`
  joined reader (10-column projection over positions × applications;
  sort `deadline_date ASC NULLS LAST, position_id ASC` with the
  `position_id` tiebreaker pinned for selection survival across
  reruns); T1-B page shell + filter (`set_page_config(layout="wide")`,
  `st.title("Applications")`, status filter selectbox keyed
  `apps_filter_status` with options
  `[STATUS_FILTER_ACTIVE, "All", *STATUS_VALUES]` and default
  `STATUS_FILTER_ACTIVE`); T1-C read-only table render with the
  six wireframe columns (Position / Applied / Recs / Confirmation
  / Response / Result), per-row `is_all_recs_submitted` glyph,
  and an empty-state info message. New config constants +
  invariant #12: `STATUS_FILTER_ACTIVE = "Active"`,
  `STATUS_FILTER_ACTIVE_EXCLUDED = frozenset({STATUS_SAVED,
  STATUS_CLOSED})`. **DESIGN §8.3 D-A amendment**: Confirmation
  column folds the per-cell tooltip into inline cell text
  (`—` / `✓ Mon D` / `✓ (no date)`) because Streamlit 1.56's
  `st.dataframe` has no per-cell tooltip API; full resolution +
  alternatives considered in `reviews/phase-5-tier1-review.md`.
  33 new tests across `test_database.py` (8),
  `test_config.py` (7), and `test_applications_page.py` (18 —
  parametrize counts each row as a separate test); suite 553 →
  586 green under both pytest gates. Boot smoke via Bash
  `streamlit run` returned HTTP 200 on root + `/Applications`.
- 2026-04-30 — **`v0.5.0` tagged** on `main` HEAD `c93dec0`
  closing Phase 4 (Dashboard). Tag annotation lists the cohesion
  smoke audit + bidirectional funnel disclosure toggle (T6
  amendment) as the headline T6 deliverables.

_Per GUIDELINES §14.5, the section caps at the 10 most-recent items
and trims anything older than the last shipped tag. **v0.5.0**
(2026-04-30) is the current boundary; pre-v0.5.0 entries — Phase 4
T5-A green, T6 cohesion-smoke + funnel-toggle polish, the 2026-04-27
v1 plan-locking commit, PRs #8/#9/#10, and the v0.2.0/v0.3.0/v0.4.0
tag entries — are archived in `CHANGELOG.md` under their respective
version blocks._

For earlier completions see [`CHANGELOG.md`](CHANGELOG.md).

---

_Updated: 2026-04-30 (Phase 5 T2 merged via PR #16 (`b9a2c82`); doc-cleanup branch `docs/guidelineupdate` in flight; Phase 5 T3 next functional work after that branch merges)_
