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

Branch (T3): T3-A + T3-B + T3 review (9 findings, 2 inline fixes) +
T3-rev (T3-rev-A column split + T3-rev-B per-row block refactor) +
pre-merge review addendum (Findings #10–#13, 2 inline fixes) all on
`feature/phase-5-tier3-InterviewManagementUI`; suite 638 → 683
green under both pytest gates. Merged via PR #19 (`f4db64c`); pre-merge
review at [`reviews/phase-5-Tier3-review.md`](reviews/phase-5-Tier3-review.md).

Branch (T4): on `feature/phase-5-tier4-RecommendersAlertPanel`; pre-merge
review at [`reviews/phase-5-tier4-review.md`](reviews/phase-5-tier4-review.md);
suite 682 → 700 green under both pytest gates. Merged via PR #28 (`a491be3`).

Branch (T5): on `feature/phase-5-tier5-RecommendersTableAddEdit`; pre-merge
review at [`reviews/phase-5-tier5-review.md`](reviews/phase-5-tier5-review.md);
suite 700 → 756 green under both pytest gates. Merged via PR #29 (`2293ebd`).

Branch (T6): on `feature/phase-5-tier6-RecommenderReminders`; pre-merge
review at [`reviews/phase-5-tier6-review.md`](reviews/phase-5-tier6-review.md);
suite 756 → 777 green under both pytest gates. Merged via PR #31 (`6993ea9`).

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
        wrapped in `st.container(border=True)` (architected to hold
        T3's per-row interview blocks); header reads
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
- [x] **T3** Inline interview list UI (per DESIGN §8.3 D-B) —
      per-row `apps_interview_{id}_form` blocks (T3-rev-B; retired
      the T3-A single-form `apps_interviews_form`), `@st.dialog`-
      gated delete, R2-toast surfacing on add when `add_interview`
      returns `status_changed=True`. T3-A + T3-B + T3-rev-A +
      T3-rev-B all shipped on branch
      `feature/phase-5-tier3-InterviewManagementUI`. Pre-merge
      review done (9+4 findings, 4 inline fixes across 2 passes);
      PR pending.
  - [x] T3-A Interview list + per-row edit form + Save + Add +
        R2 toast — `apps_interviews_form` with date/format/notes
        per row inside the existing T2 `st.container(border=True)`,
        `_safe_str`-normalized dirty-diff Save calling
        `database.update_interview` per dirty row only (clean rows
        skip), Add button outside the form (Streamlit 1.56 forbids
        `st.button` inside `st.form`) calling
        `database.add_interview(sid, {}, propagate_status=True)`
        with R2 promotion toast on `status_changed=True`. Format
        selectbox mirrors T2-A's `response_type` pattern:
        `[None, *INTERVIEW_FORMATS]` with `format_func` rendering
        `None` as the em-dash glyph — without the leading `None`,
        a freshly-Added row (`format=NULL`) would default to
        `INTERVIEW_FORMATS[0]` and silently dirty-write a value
        the user never chose (Sonnet plan-critique signal).
        Per-row pre-seed sentinel `_apps_interviews_seeded_ids`
        (frozenset of seeded ids; pruned via
        `saved_sentinel & current_ids` on every rerun) preserves
        sibling-row drafts across Add and prevents zombie ids
        after delete (Sonnet plan-critique signal). Save handler
        does NOT pop the sentinel after success (different from
        T2-A's pop pattern): `update_interview` is a direct write
        with no normalization, so the widget already reflects DB
        state — popping would re-seed sibling rows and clobber
        unsaved drafts. 25 new tests across 4 new classes
        (`TestApplicationsInterviewListRender`,
        `TestApplicationsInterviewSave`,
        `TestApplicationsInterviewAdd`,
        `TestApplicationsInterviewSentinelLifecycle`); suite
        638 → 663 under both pytest gates.
  - [x] T3-B Per-row Delete via `@st.dialog` confirm before
        `database.delete_interview(id)` — module-level
        `_confirm_interview_delete_dialog` helper at the page's
        helpers section; per-row Delete buttons render in a single
        horizontal `st.columns(N)` row BELOW `apps_interviews_form`
        (Streamlit 1.56 forbids `st.button` inside `st.form`), each
        keyed `apps_interview_{id}_delete` and labelled
        `🗑️ Delete Interview {seq}` so the per-row association
        stays unambiguous despite the vertical separation. Single
        dialog call site post-loop with a
        `pending_id in current_ids` guard provides automatic stale-
        target cleanup when the user navigates to a different
        position. Confirm path: `database.delete_interview(id)` +
        pop sentinels + `_applications_skip_table_reset=True`
        (gotcha #11 — preserves selection across the rerun) +
        `st.toast("Deleted interview {seq}.")` + `st.rerun()`.
        Cancel path: pop sentinels + `_applications_skip_table_reset
        =True` + `st.rerun()` (no DB write, no toast). Failure
        path: `st.error` per GUIDELINES §8 with sentinels
        SURVIVING so the dialog re-opens for retry — matches the
        Opportunities-page failure-preserves-state precedent.
        13 new tests across 2 new classes
        (`TestApplicationsInterviewDeleteButton`,
        `TestApplicationsInterviewDeleteDialog`); suite 663 → 676
        under both pytest gates.
  - [x] T3-rev-A Position / Institute column split per the post-T3
        truth-file alignment. DESIGN §8.3 amended (commit `ba7cd47`)
        with an explicit seven-column contract; wireframe updated
        in the same commit. Page table render now produces
        `Position` (bare `position_name`) + new `Institute` (bare
        institute, EM_DASH on empty) columns instead of a single
        `f"{institute}: {position_name}"` Position cell. Both go
        through `_safe_str_or_em` (NaN→EM_DASH per gotcha #1).
        Column widths: Position `large` (kept; bare `position_name`
        can still be long), Institute `medium` (full institute names
        like "Massachusetts Institute of Technology" don't fit
        `small`). The `_format_label` helper stays on the page —
        still used by the detail-card header. 4 net new test cases
        (3 from `test_institute_column_format` parametrize + 1
        `test_institute_column_is_medium`); suite 676 → 681 under
        both pytest gates.
  - [x] T3-rev-B Per-row interview block refactor — replaced the
        single page-level `apps_interviews_form` with per-row
        `apps_interview_{id}_form` (`border=False` so the parent
        `st.container(border=True)` stays the only visual frame).
        Each block carries `**Interview {seq}**` heading + 3-column
        detail row (date / format / notes) + per-row
        `st.form_submit_button("Save", key=f"apps_interview_{id}_save")`
        + per-row Delete button outside the form (Streamlit 1.56
        forbids `st.button` inside `st.form`). Blocks separated by
        `st.divider()`. Save handler (`if saves_clicked:`) processes
        the single (iid, seq) tuple from the click — Streamlit fires
        at most one form submit per rerun. Toast wording: `Saved
        interview {seq}.` (singular + sequence; side-effect closes
        T3 review Finding #6 wording asymmetry). Error wording:
        `Could not save interview {seq}: {e}`. Seeded-ids sentinel
        still NOT popped on Save success — load-bearing for the
        per-row architecture (popping would re-seed sibling rows and
        clobber drafts). 2 net new test cases (replaced
        `test_two_dirty_rows_call_update_interview_twice` with
        `test_clicking_one_row_save_does_not_persist_sibling_row`,
        added `test_save_one_row_preserves_sibling_row_draft` and
        `test_save_toast_includes_sequence_number`); suite 681 → 683
        under both pytest gates.
- [x] **T4** Recommenders alert panel (`pages/3_Recommenders.py`) —
      grouped by `recommender_name`
- [x] **T5** Recommenders table + add form + inline edit (`asked_date`,
      `confirmed`, `submitted_date`, `reminder_sent`+`reminder_sent_date`,
      `notes`) — three sub-areas shipped as one PR on
      `feature/phase-5-tier5-RecommendersTableAddEdit`. T5-A: read-only
      `st.dataframe` (`recs_table`) backed by `database.get_all_recommenders()`
      with the locked six-column display contract (Position · Recommender ·
      Relationship · Asked · Confirmed · Submitted) + two filter selectboxes
      (`recs_filter_position`, `recs_filter_recommender`) defaulting to
      `"All"`; recommender filter dedupes repeat names across positions.
      T5-B: `st.form("recs_add_form")` inside an "Add Recommender" expander
      (Opportunities Quick-Add precedent — keeps the table above the fold);
      position selectbox uses label-as-value with submit-time
      `_position_label_to_id` lookup so IDs never surface to the user
      (DESIGN §8.4); whitespace-only name → `st.error`; success →
      `st.toast(f"Added {name}.")`. T5-C: single-row selection captures
      `recs_selected_id`; inline edit card (`st.container(border=True)`)
      below the table with `st.form("recs_edit_form")` over asked_date /
      confirmed (`[None, 0, 1]` → `—`/`No`/`Yes`) / submitted_date /
      reminder_sent + reminder_sent_date / notes; Save computes a
      per-field dirty diff against the persisted row and writes ONLY
      changed fields via `database.update_recommender`; Delete button
      OUTSIDE the form opens an `@st.dialog` confirm gate
      (`recs_delete_confirm` / `recs_delete_cancel`) that cascades via
      `database.delete_recommender` on Confirm and preserves selection
      across the Cancel-driven rerun via the `_recs_skip_table_reset`
      one-shot. Mirrors the Opportunities-page dialog re-open trick
      (gotcha #3): single dialog call site post-loop guarded by
      `pending_id == _rec_id`, doubling as automatic stale-target cleanup
      on row-change. Ride-along constant rename
      `config.RELATIONSHIP_TYPES` → `config.RELATIONSHIP_VALUES`
      (project-wide `*_VALUES` naming convention) plus two prose
      references in `DESIGN.md` + `docs/dev-notes/extending.md`. 56 new
      tests; suite 700 → 756 under both pytest gates.
- [x] **T6** Recommender reminder helpers per DESIGN §8.4 (locked
      subject + body for primary mailto; `LLM prompts (N tones)`
      expander rendering pre-filled prompts as `st.code(...)` blocks)
      — wired into each Pending Alerts card on `pages/3_Recommenders.py`
      (T4 surface, NOT the T5-C inline edit card). T6-A:
      `st.link_button("Compose reminder email", url=mailto:?…)` per card
      with the verbatim DESIGN §8.4 subject (`Following up: letters for
      {N} postdoc applications`, `N` = card's owed-position count) +
      body (`Hi {recommender_name}, just a quick check-in on the letters
      of recommendation you offered. Thank you so much!`). No `to:`
      field — the recommenders schema doesn't store emails today; the
      OS-level mail client prompts for the recipient. Per-card unique
      key `recs_compose_{idx}` (`enumerate` over the groupby) prevents
      Streamlit `DuplicateWidgetID` across multi-card pages. T6-B:
      `st.expander(f"LLM prompts ({len(_REMINDER_TONES)} tones)")` per
      card holding one `st.code(prompt, language="text")` per locked
      tone — `_REMINDER_TONES = ("gentle", "urgent")` per DESIGN §8.4;
      expander label computes its count from `len(_REMINDER_TONES)` so a
      future tone addition flows through automatically. Each prompt
      embeds: recommender name + relationship (relationship omitted on
      NULL), every owed position (institute: position_name + deadline
      ISO or "no deadline"), days-since-asked (max wait across the
      card's positions — one summary integer per prompt), the target
      tone keyword, and an instruction asking the LLM to return BOTH
      subject and body. Two pure helpers carry the construction:
      `_build_compose_mailto(recommender_name, n_positions)` and
      `_build_llm_prompt(tone, recommender_name, relationship, group,
      days_ago)`; the existing T4 `_bullets`-building loop is extended
      by one line to collect each row's `days_ago`. 21 new tests
      across `TestT6ComposeButton` (9) + `TestT6LLMPromptsExpander`
      (12); suite 756 → 777 under both pytest gates.
- [x] **T7** Phase 5 review + PR + tag `v0.6.0` — close-out + cohesion
      sweep at [`reviews/phase-5-finish-cohesion-smoke.md`](reviews/phase-5-finish-cohesion-smoke.md)
      (verbatim AppTest renders for `pages/2_Applications.py` +
      `pages/3_Recommenders.py` populated + empty + populated-with-row-
      selected; six cohesion dimensions audited; 3 🟡 polish + 3 ℹ️
      observations; zero 🔴/🟠). Carry-overs disposed: **C4** closed
      (CHANGELOG `[v0.5.0]` split landed at `db383e3`); **C2** + **C3**
      + Phase 7 polish candidates (T5 Save-toast on no-dirty, T6
      subject-pluralization on N=1) all deferred to Phase 7 / v1.0-rc
      with explicit homes in TASKS.md. CHANGELOG split — `[Unreleased]`
      → `[v0.6.0]` (mirror of `db383e3` precedent for v0.5.0); empty
      `[Unreleased]` accumulates Phase 6 work. All four GUIDELINES §11
      pre-tag gates green at HEAD: ruff clean, `pytest tests/ -q`
      777 passed + 1 xfailed, `pytest -W error::DeprecationWarning
      tests/ -q` 777 passed + 1 xfailed, status-literal grep 0 lines.
      Tagged `v0.6.0` 2026-05-04.

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

Branch (T1): on `feature/phase-6-tier1-WriteOpportunities`; pre-merge
review at [`reviews/phase-6-tier1-review.md`](reviews/phase-6-tier1-review.md);
suite 777 → 786 green under both pytest gates. Merged via PR #32 (`e9a8a4a`).

Branch (T2): on `feature/phase-6-tier2-WriteProgress`; pre-merge
review at [`reviews/phase-6-tier2-review.md`](reviews/phase-6-tier2-review.md);
suite 786 → 801 green under both pytest gates. Mandatory conftest
fixture lift (`db_and_exports` → `tests/conftest.py::db`) closes T1's
exposed pollution; T2 isolation gate (`git status --porcelain
exports/` empty post-pytest) now part of the standing pre-PR
checklist. Merged via PR #33 (`911115a`).

Branch (T3): on `feature/phase-6-tier3-WriteRecommenders`; pre-merge
review at [`reviews/phase-6-tier3-review.md`](reviews/phase-6-tier3-review.md);
suite 801 → 815 green under both pytest gates. Three commits on
branch (`test:` → `feat:` → `fix:`) — the `fix:` augmented
`isolated_exports_dir` to also monkeypatch `DB_PATH` + run
`init_db()`, closing the CI-red regression that had been latent on
main since T1 (smoke tests `test_write_*_does_not_raise` fell
through to the developer's real `postdoc.db` locally + raised
`sqlite3.OperationalError` on CI). Process docs amended in
`c284c20` post-mortem (require CI-green-conclusion before
admin-bypass; CI-mirror local check `mv postdoc.db postdoc.db.bak
&& pytest tests/ -q && mv postdoc.db.bak postdoc.db` in standing
pre-PR checklist). Merged via PR #34 (`c11fde4`).

Branch (T4): on `feature/phase-6-tier4-ExportPage`; pre-merge review
at [`reviews/phase-6-tier4-review.md`](reviews/phase-6-tier4-review.md);
suite 815 → 827 green under both pytest gates. First PR in the
project's history to land with `mergeStateStatus: CLEAN` (rather
than `BLOCKED`); admin-bypass merge used anyway for procedure
consistency. Merged via PR #35 (`3235f60`).

Branch (T5): on `feature/phase-6-tier5-DownloadButtons`; pre-merge
review at [`reviews/phase-6-tier5-review.md`](reviews/phase-6-tier5-review.md);
suite 827 → 834 green under both pytest gates. Three design calls
flagged by implementer (stacked vs side-by-side layout — pragmatic
test-compatibility choice; `st.divider()` + `st.subheader("Download")`
vs literal Unicode dashes — the dashes don't render as a horizontal
rule; source-grep tests for `data` + `file_name` args because
AppTest 1.56's DownloadButton proto doesn't expose either field).
All defensible. Merged via PR #36 (`73a04c4`).

- [x] **T1** `write_opportunities()` generator — fills the existing
      `exports.py` stub with the first markdown export per DESIGN §7.
      Reads `database.get_all_positions()`, sorts `deadline_date ASC
      NULLS LAST, position_id ASC` (mirror of
      `database.get_applications_table()` precedent — the
      `position_id` tiebreaker is added via `pandas.sort_values(...
      kind="stable")` so equal-deadline rows have a stable order
      across rerenders), and writes a single markdown table to
      `exports/OPPORTUNITIES.md` (UPPERCASE per DESIGN §7 line 462 +
      the existing stub docstring). 8-column contract pinned by
      `TestWriteOpportunities.EXPECTED_HEADER`: Position · Institute ·
      Field · Deadline · Priority · Status · Created · Updated.
      Cell-shape rules: `_safe_str_or_em` coerces None / NaN / "" →
      em-dash (mirror of the in-app convention; helper duplicated
      because pages and exports must NOT share helpers — exports is
      forbidden from importing streamlit per DESIGN §2 layer rules).
      Date / datetime cells pass-through ISO TEXT verbatim. **Status
      renders the raw bracketed sentinel** (`[SAVED]`, `[APPLIED]`,
      …) NOT `STATUS_LABELS` — markdown is a backup format, not a UI
      surface, and round-trippable / greppable raw form trumps
      UI-friendly translation. The pre-PR status-literal grep in
      GUIDELINES §11 is scoped to `app.py + pages/`, not `exports/`,
      so this divergence stays grep-clean. Pinned by
      `test_status_renders_as_raw_bracketed_sentinel` so a future
      flip can't land silently. `_md_escape_cell` escapes `|` → `\|`
      and collapses `\n` / `\r` → ` ` — cheap safety net for future
      user-typed cells. Deferred `database` import inside the
      function body breaks the `database → exports → database`
      circular import (mirror of the pattern every `database.py`
      writer uses to call `exports.write_all`).
      `EXPORTS_DIR.mkdir(exist_ok=True)` inside the writer keeps it
      callable independently of `write_all`'s prior mkdir — required
      for the Phase 6 T4 manual-trigger button. Idempotent — two
      calls with the same DB state produce byte-identical output;
      load-bearing for DESIGN §7 contract #2 ("stable markdown
      format committed to version control"); pinned by
      `test_idempotent_across_two_calls`. Combined `db_and_exports`
      fixture monkeypatches both `database.DB_PATH` and
      `exports.EXPORTS_DIR` (because `add_position` triggers
      `exports.write_all()` via deferred import; without the second
      monkeypatch the test would pollute the project's real
      `exports/` directory). 9 new tests in `TestWriteOpportunities`;
      suite 777 → 786 under both pytest gates.
- [x] **T2** `write_progress()` generator (depends on Phase 5 T3 —
      reads `interviews` data) — fills the `exports.py` stub for the
      second markdown generator. Reads
      `database.get_applications_table()` (positions × applications
      LEFT JOIN, 10-column projection) and per-row
      `database.get_interviews(position_id)` for the interviews
      side; writes a single markdown table to `exports/PROGRESS.md`
      (UPPERCASE per DESIGN §7 line 463 + the T1 `OPPORTUNITIES.md`
      precedent). 8-column contract pinned by
      `TestWriteProgress.EXPECTED_HEADER`: Position · Institute ·
      Status · Applied · Confirmation · Response · Result ·
      Interviews. **No `Deadline` column** — the two exports answer
      different questions; OPPORTUNITIES.md owns the upstream window,
      PROGRESS.md owns the application progression. Cell shapes
      mirror T1 conventions (em-dash for missing TEXT via
      `_safe_str_or_em`, ISO TEXT pass-through for dates, raw
      bracketed status sentinel `[APPLIED]` etc., `_md_escape_cell`
      on every cell). Two new tri-state helpers for the
      joined-frame complexity: `_format_confirmation(received,
      iso_date)` mirrors the Applications page DESIGN §8.3 D-A
      T1-C inline-text shape (`—` / `✓ {ISO}` / `✓ (no date)`)
      using ISO instead of "Mon D" for round-trip cleanliness; pages
      and exports cannot share helpers (DESIGN §2 layer rules —
      pages import streamlit, exports cannot).
      `_format_interviews_summary(scheduled_dates: list[Any])`
      renders the only T2 design call: `"{N} (last: {YYYY-MM-DD})"`
      with `last` = max scheduled_date across the position's
      interviews. Edge cases pinned: 0 interviews → `—`; ≥1
      interviews + all-NULL `scheduled_date` → `{N} (no dates)`.
      Considered + rejected: count-only (loses chronology),
      comma-joined date list (unbounded length), next-interview
      cell (relies on "today" semantics that drift over time and
      break idempotency). Sort: `deadline_date ASC NULLS LAST,
      position_id ASC` inherited from
      `database.get_applications_table()` SQL ORDER BY; re-applied
      via `pandas.sort_values(... kind="stable")` to defend against
      upstream changes. Per-row N+1 interviews lookup is documented
      as kept-by-design (low position counts, single-user app;
      richer joined query would be premature optimization).
      Idempotent (DESIGN §7 contract #2). **Mandatory ride-along —
      conftest fixture lift**: `tests/conftest.py::db` now
      monkeypatches both `database.DB_PATH` AND `exports.EXPORTS_DIR`
      in one fixture; `tests/test_exports.py::db_and_exports`
      collapses to a thin wrapper returning the path; 5 migration
      sites in `test_database.py` get paired EXPORTS_DIR
      monkeypatches (2 actual polluters + 3 defensive symmetry); 2
      `write_all` behaviour tests in `test_exports.py` gain the
      `isolated_exports_dir` fixture parameter. T2 isolation gate
      (`git status --porcelain exports/` empty post-pytest) is now
      part of the standing pre-PR checklist. 15 new tests in
      `TestWriteProgress`; suite 786 → 801 under both pytest gates.
- [x] **T3** `write_recommenders()` generator — fills the third
      `exports.py` stub. Reads `database.get_all_recommenders()` (no
      new DB reader needed — the existing one returns recommenders ×
      positions LEFT JOIN ordered by `recommender_name ASC`) and
      writes a single 8-column markdown table to
      `exports/RECOMMENDERS.md` (UPPERCASE per DESIGN §7 line 464 +
      the T1 / T2 precedent). Locked column contract pinned by
      `TestWriteRecommenders.EXPECTED_HEADER`: Recommender ·
      Relationship · Position · Institute · Asked · Confirmed ·
      Submitted · Reminder. **`notes` deliberately omitted** —
      free-form prose is awkward in a markdown table cell; the
      in-app UI carries it, the export summarises. Two helper-reuse
      decisions: **Confirmed** uses a NEW local `_format_confirmed`
      (`—` / `No` / `Yes` tri-state — mirrors the
      `pages/3_Recommenders.py` helper of the same name; pages and
      exports cannot share helpers per DESIGN §2 layer rules);
      **Reminder** REUSES the existing `exports._format_confirmation`
      helper because the `(reminder_sent, reminder_sent_date)` pair
      has the same `(flag, date)` shape as the Applications-page
      Confirmation pattern (DESIGN §8.3 D-A T1-C precedent). Cell
      shapes mirror T1+T2 (em-dash for missing TEXT, ISO TEXT
      pass-through for dates, `_md_escape_cell` on every cell). Sort:
      `recommender_name ASC, deadline_date ASC NULLS LAST, id ASC`.
      `database.get_all_recommenders()` SQL covers keys 1 + 3 only;
      `deadline_date` is merged in pandas from
      `database.get_all_positions()` here in the writer (mirror of
      T2's "compose multiple reads in `exports.py`" precedent), then
      re-sorted via `pandas.sort_values(... kind="stable")` to
      defend against either upstream reader's ORDER BY changing.
      Idempotent (DESIGN §7 contract #2; pinned by
      `test_idempotent_across_two_calls`). 14 new tests in
      `TestWriteRecommenders`. **Three commits on branch (`test:` →
      `feat:` → `fix:`)** — the `fix:` augmented
      `isolated_exports_dir` to also monkeypatch `database.DB_PATH`
      + run `init_db()`, closing the CI-red regression that had
      been latent on main since T1 (three smoke tests
      `test_write_*_does_not_raise` used only `isolated_exports_dir`
      and never init'd a DB; locally they passed because `postdoc.db`
      sits at the project root + the unmonkeypatched `database.DB_PATH`
      fell through, but on CI runners with no `postdoc.db` the
      writers raised `sqlite3.OperationalError`). The fix is mirror
      of the conftest `db` fixture from Phase 6 T2 (single fixture,
      every consumer benefits) — closes the gap once for the three
      smoke tests AND the two `write_all` behaviour tests.
      **Process amendment in `c284c20` (post-mortem on PRs #32 +
      #33 + #34):** ORCHESTRATOR_HANDOFF.md now requires CI
      `conclusion: SUCCESS` (not IN_PROGRESS) before admin-bypass;
      AGENTS.md "Session bootstrap" adds the CI-mirror local check
      (`mv postdoc.db postdoc.db.bak && pytest tests/ -q && mv
      postdoc.db.bak postdoc.db`) to standing pre-PR checklist.
      Suite 801 → 815 under both pytest gates.
- [x] **T4** Export page — manual regenerate button + file mtimes —
      `pages/4_Export.py` created. Page shell (`set_page_config(layout=
      "wide")` first, `database.init_db()`, `st.title("Export")`,
      verbatim wireframe-pinned intro line via `st.markdown`).
      Regenerate button (`st.button("Regenerate all markdown files",
      key="export_regenerate", type="primary")`) wraps
      `exports.write_all()` in try/except per GUIDELINES §8 — friendly
      `st.error(f"Could not regenerate: {e}")` on failure with the
      button still rendered for retry, no re-raise; success path fires
      `st.toast("Markdown files regenerated.")`. Per DESIGN §7 contract
      #1, the inner per-writer calls already log-and-continue, so only
      the `EXPORTS_DIR.mkdir` leg can surface here. Mtimes panel below
      the button: one `st.markdown` line per locked filename
      (`OPPORTUNITIES.md`, `PROGRESS.md`, `RECOMMENDERS.md`, in
      wireframe order) — either `**{filename}** — last generated:
      {YYYY-MM-DD HH:MM:SS}` (file present, computed via
      `datetime.fromtimestamp(Path.stat().st_mtime).strftime(...)`) or
      `**{filename}** — not yet generated` (absent, via
      `Path.exists()` check). The "── Download ───" wireframe section
      header is deliberately omitted from T4 — that header scopes T5's
      download buttons, so adding it here with no buttons under it
      would read as a stray section header. 12 new tests in
      `tests/test_export_page.py` across 3 classes
      (`TestExportPageShell`, `TestExportPageRegenerateButton`,
      `TestExportPageMtimesPanel`) with all locked-copy strings
      centralized in module-level constants for one-edit drift
      surface; mtimes test uses `os.utime` to a deterministic epoch
      (`1700000000`) so timestamp assertions are exact rather than
      wall-clock-approximated. Local fixture `db_and_exports` (thin
      wrapper around the conftest `db` fixture) returns
      `tmp_path / "exports"` for the mtimes-panel tests. Suite 815 →
      827 under both pytest gates. Notable: PR #35 was the first PR
      to land with `mergeStateStatus: CLEAN` rather than `BLOCKED` —
      orchestrator-merged via standard admin-bypass for consistency
      with the `c284c20` procedure.
- [x] **T5** Export page — `st.download_button` per file — extends
      `pages/4_Export.py` (T4) with three `st.download_button`
      widgets keyed `export_download_<filename>` (one per locked
      filename in wireframe order: `OPPORTUNITIES.md`, `PROGRESS.md`,
      `RECOMMENDERS.md`) plus the wireframe-pinned "── Download ───"
      section header rendered as `st.divider()` +
      `st.subheader("Download")` (the Streamlit-idiomatic equivalent
      of the ASCII rule — Unicode dashes don't render as a horizontal
      rule in markdown). Each button's data arg: `Path.read_bytes()`
      when the file exists, `b""` + `disabled=True` when absent (the
      empty bytes are placeholder semantics; the disabled state
      blocks the click). A single `_file_present = _path.exists()`
      boolean now drives both the new download-button disabled
      state AND the existing T4 mtime-line branch — single
      filesystem call per file, no race between the two checks.
      Stacked layout (button above mtime line) rather than the
      wireframe's side-by-side `st.columns` rendering — the column
      layout would have moved the bold filename onto the button
      label and broken T4's substring assertions in
      `TestExportPageMtimesPanel`. 7 new tests in
      `TestExportPageDownloadButtons` plus two helper functions
      (`_download_buttons` wrapping `at.get('download_button')`,
      `_download_button` looking up by widget key via
      `proto.id.endswith(...)`); two source-grep tests pin the
      `data=read_bytes()` and `file_name=` contracts because AppTest
      1.56's DownloadButton proto stores both behind a mock media
      URL and doesn't expose them on the element tree. The integration
      test `test_download_button_enabled_when_file_present` is the
      belt-and-suspenders pin against the source-grep layer. Suite
      827 → 834 under both pytest gates.
- [x] **T6** Phase 6 review + PR + tag `v0.7.0` — close-out +
      cohesion-smoke at [`reviews/phase-6-finish-cohesion-smoke.md`](reviews/phase-6-finish-cohesion-smoke.md)
      (verbatim AppTest renders for `pages/4_Export.py` across four
      states: populated DB + no exports, populated + exports written,
      populated + post-click regenerate, empty DB + no exports; six
      cohesion dimensions audited; tier1-tier5 carry-overs all
      disposed; structural changes between v0.6.0 and v0.7.0
      catalogued — test-isolation lift `911115a`, CI procedure
      `c284c20`, privacy amendment `43b3f3c`). Carry-overs disposed:
      **C2** + **C3** continue to defer to v1.0-rc / cleanup tier;
      Phase 7 polish candidate (T4's `st.markdown` vs `st.write`
      cohesion) parked; remaining T2-T5 findings all kept-by-design.
      CHANGELOG split — `[Unreleased]` → `[v0.7.0]` (mirror of
      `6f936d7` precedent for v0.6.0); empty `[Unreleased]`
      accumulates Phase 7 work. All six pre-tag gates green at HEAD:
      ruff clean, `pytest tests/ -q` 834 passed + 1 xfailed,
      `pytest -W error::DeprecationWarning tests/ -q` 834 passed +
      1 xfailed, status-literal grep 0 lines, standing isolation
      gate empty, CI-mirror local check 834 + 1 xfailed. Tagged
      `v0.7.0` 2026-05-04.

### Phase 7 — Polish

- [x] **T1** Urgency colors on positions table (`st.column_config`)
      — `pages/1_Opportunities.py::_deadline_urgency` returns inline
      glyphs `🔴` (urgent: `days <= DEADLINE_URGENT_DAYS`), `🟡`
      (alert: `days <= DEADLINE_ALERT_DAYS`), `''` (distant), `—`
      (NULL / unparseable) instead of literal-string flags
      `'urgent'` / `'alert'` / `''`. Display column unchanged — just
      the value form. Same banding the dashboard's Upcoming panel
      uses (`database.py::_urgency_glyph`); shared via the
      `config.DEADLINE_URGENT_DAYS` / `DEADLINE_ALERT_DAYS`
      thresholds rather than via a shared helper (DESIGN §2 layer
      rule: pages cannot import `database.py` privates). New
      page-local `EM_DASH = "—"` module constant (mirror of the
      same literal in `app.py`, `pages/2_Applications.py`,
      `exports.py` — pages and layers cannot share helpers).
      Type-hint widening from `str | None` to `Any` because
      pandas' `.apply()` on object columns surfaces NULL TEXT
      cells as `float('nan')` (gotcha #1); explicit
      `isinstance + math.isnan` guard added on top of the existing
      not-falsy + try/except guards so every NULL-shaped input
      funnels to the em-dash branch consistently. New contract
      distinguishes "no deadline at all" (em-dash) from "deadline
      far enough away that no urgency is signaled" (empty cell);
      the old contract collapsed both into `''`. 7 existing
      urgency tests in `TestPositionsTable` updated in-place
      (renamed + assertions flipped); 2 new tests added
      (`test_today_deadline_renders_red_glyph` boundary +
      `test_invariant_check_urgent_le_alert` config invariant
      pin). Class-level constants `URGENT_GLYPH` / `ALERT_GLYPH` /
      `NO_GLYPH` / `EM_DASH` centralize the locked-copy strings.
      Suite 834 → 836 under both pytest gates. Merged via PR #37
      (`e5316fd`).
- [x] **T2** Position search bar on Opportunities (substring,
      `regex=False`) — `filter_search` text_input prepended to the
      filter row (`st.columns([3, 2, 2, 3])` reweighting; search
      column widest because user-typed queries are variable length).
      `df["position_name"].str.contains(query, regex=False,
      case=False, na=False)` row mask AND-combined with the existing
      status / priority / field filters via successive
      `df_filtered = df_filtered[mask]` narrowings. Search scope
      `position_name` only — institute / field deliberately excluded
      (field has its own filter; narrower scope keeps "what you type
      matches what's printed in the Position column" predictable).
      7 new tests across `TestPositionSearchStructure` (2: widget +
      label) + `TestPositionSearchBehaviour` (5: empty-search,
      substring case-insensitive, zero-match empty-state,
      regex-special-chars-as-literal `'++'`-in-`'C++ Postdoc'`,
      AND-combined with status filter). Every N=1 behaviour test
      includes row-identity assertion (not just count) — guards
      against swapped predicates that would coincidentally produce
      N=1 with the wrong row. Suite 836 → 843 under both pytest
      gates. Merged via PR #38 (`e67cfed`).
- [x] **T3** `set_page_config` sweep on remaining pages (verify
      GUIDELINES §13 step 2 holds for every page) — new
      `tests/test_pages_cohesion.py::TestSetPageConfigSweep` with 10
      parametrized tests across 5 pages × 2 invariants per page:
      (1) source-grep for the locked kwargs (`page_title="Postdoc
      Tracker"`, `page_icon="📋"`, `layout="wide"`); (2) AST-walk
      for the first module-level `st.<X>()` bare expression
      statement, asserting it is `set_page_config` (catches a future
      edit that adds `st.title("X")` above `set_page_config` —
      Streamlit warns + silently falls back to centered layout in
      that case). The AST helper deliberately skips decorators —
      `@st.dialog(...)` on `pages/1_Opportunities.py::_confirm_delete_dialog`
      sits ABOVE `set_page_config` legitimately because Streamlit's
      first-call gate is a render-call gate, not a module-load-time
      gate; decorators are factory-style higher-order calls that
      don't trip it. Audit outcome: all 5 pages already conform —
      **verification-only PR** (no production code touched, just
      the new test file). New `tests/test_pages_cohesion.py` is the
      home for cross-page cohesion contracts (T4 confirm-dialog
      audit + T5 responsive-layout check earmarked for the same
      file). Suite 843 → 853 under both pytest gates. Merged via
      PR #39 (`85968bb`).
- [x] **T4** Confirm-dialog audit (every destructive path wears
      `@st.dialog` with cascade-effect copy) — new
      `tests/test_pages_cohesion.py::TestConfirmDialogAudit` with
      11 tests across 3 destructive paths (position / interview /
      recommender delete). Five test methods, 4 parametrized + 1
      cross-page AST walk: (1) title locked-shape source-grep; (2)
      "cannot be undone" universal cue; (3) cascade-effect copy
      enumeration (positive enumeration via `cascade_substrings`
      list — auto-extends if new paths gain cascades); (4)
      `database.delete_*` callers all inside `@st.dialog`-decorated
      functions (cross-page AST walk for forward-defence against
      future quick-delete buttons that bypass dialogs); (5) failure-
      preserves-pending-sentinel (AST walk for
      `st.session_state.pop` calls inside `except` handlers —
      asserts none exist; pins the documented dialog re-open
      contract structurally). **Not a no-op outcome — surfaced and
      fixed a real bug**: position-delete dialog warning text said
      "application and recommender rows" but FK chain
      `positions → applications (CASCADE) → interviews (CASCADE)`
      + `positions → recommenders (CASCADE)` actually drops three
      child tables in one transactional sweep. Copy fixed inline
      to "application, interview, and recommender rows". Per-page
      `TestDeleteAction` had the same gap (asserted partial
      substrings, didn't enumerate the FK chain) — kept as-is
      because the cohesion test is now the single source of truth
      for "every child table in the FK chain is mentioned". AST
      helper `_set_parents` annotates parent links on the tree for
      ancestor-chain queries; `_has_dialog_decorator` /
      `_find_function` / `_ancestors` round out the toolkit. Suite
      853 → 864 under both pytest gates. Merged via PR #40
      (`952f0e9`).
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

- 2026-05-04 — **PR #40 merged** (`952f0e9`): Phase 7 T4 shipped —
  confirm-dialog audit + position cascade-copy fix. New
  `TestConfirmDialogAudit` (11 tests across 3 destructive paths)
  surfaced a real bug: position-delete dialog warning was missing
  "interview" from the FK cascade enumeration even though the
  schema's `positions → applications (CASCADE) → interviews
  (CASCADE)` chain drops interview rows too. Copy fixed inline.
  Cohesion-test pattern paid off — per-page `TestDeleteAction`
  passed because it asserted partial substrings; the cohesion
  test caught it via positive enumeration of the FK chain.
  Suite 853 → 864 under both pytest gates. Pre-merge review at
  [`reviews/phase-7-tier4-review.md`](reviews/phase-7-tier4-review.md).
- 2026-05-04 — **PR #39 merged** (`85968bb`): Phase 7 T3 shipped —
  verification-only `set_page_config` sweep across all 5 pages
  (`app.py` + 4 `pages/*.py`). New `tests/test_pages_cohesion.py`
  with `TestSetPageConfigSweep` (10 parametrized tests, 2
  invariants per page). Audit outcome: all 5 pages already conform
  to locked shape — no production code touched. AST helper
  deliberately skips decorators (load-bearing — `@st.dialog`
  doesn't trip Streamlit's first-call gate). Suite 843 → 853 under
  both pytest gates. Pre-merge review at
  [`reviews/phase-7-tier3-review.md`](reviews/phase-7-tier3-review.md).
- 2026-05-04 — **PR #38 merged** (`e67cfed`): Phase 7 T2 shipped —
  free-text "Search positions" `text_input` prepended to the
  Opportunities filter row; `position_name` substring match
  (case-insensitive, regex=False, NaN-safe) AND-combined with
  status / priority / field filters. Search scope `position_name`
  only (kept-by-design — field has its own filter widget). Filter
  row reweights `[2, 2, 3]` → `[3, 2, 2, 3]` with search widest.
  7 new tests; suite 836 → 843 under both pytest gates. CI procedure
  followed cleanly (third clean end-to-end run). Pre-merge review
  at [`reviews/phase-7-tier2-review.md`](reviews/phase-7-tier2-review.md).
- 2026-05-04 — **PR #37 merged** (`e5316fd`): Phase 7 T1 shipped —
  `pages/1_Opportunities.py::_deadline_urgency` returns inline
  glyphs (`🔴` / `🟡` / `''` / `—`) instead of literal-string
  flags. New em-dash branch distinguishes "no deadline at all"
  from "deadline far enough away" (the old contract collapsed
  both into `''`). Same banding the dashboard's Upcoming panel
  uses, shared via `config` thresholds rather than a shared helper
  (DESIGN §2 layer rule). Type hint widened to `Any` + explicit
  `math.isnan` guard added so every NULL-shaped input funnels to
  the em-dash branch. 7 existing urgency tests updated in-place +
  2 new tests (boundary at delta=0, config invariant pin). Suite
  834 → 836 under both pytest gates. CI procedure followed cleanly:
  `gh pr checks 37 --watch` blocked until conclusion landed,
  conclusion verified SUCCESS via `gh pr view --json
  statusCheckRollup`, then admin-bypass merge. Pre-merge review at
  [`reviews/phase-7-tier1-review.md`](reviews/phase-7-tier1-review.md).
- 2026-05-04 — **`v0.7.0` tagged** on `main` closing Phase 6 — three
  markdown generators (`write_opportunities` / `write_progress` /
  `write_recommenders`) backing `OPPORTUNITIES.md` / `PROGRESS.md` /
  `RECOMMENDERS.md` plus the new `pages/4_Export.py` (manual
  regenerate + per-file mtimes + per-file download buttons).
  Cohesion-smoke at
  [`reviews/phase-6-finish-cohesion-smoke.md`](reviews/phase-6-finish-cohesion-smoke.md);
  CHANGELOG `[Unreleased]` → `[v0.7.0]` split at the boundary commit
  (mirror of `6f936d7` precedent for v0.6.0). Three durable
  structural changes shipped during the phase too: the conftest
  fixture lift (`911115a`), the CI-green-conclusion-before-bypass
  procedure (`c284c20`), and the privacy amendment (`43b3f3c`).
  Suite 777 → 834 (+57 tests across the phase, 1 xfail unchanged).
- 2026-05-04 — **PR #36 merged** (`73a04c4`): Phase 6 T5 shipped —
  three `st.download_button` widgets + `st.divider()` +
  `st.subheader("Download")` section header on `pages/4_Export.py`.
  Each button's data arg: `Path.read_bytes()` when present,
  `b""` + `disabled=True` when absent. Stacked layout (button above
  mtime line) preserves T4's substring assertions; single
  `_file_present` boolean drives both download-disabled state AND
  T4 mtime branch. 7 new tests in `TestExportPageDownloadButtons`
  + two helper functions. Suite 827 → 834 under both pytest gates.
  Pre-merge review at [`reviews/phase-6-tier5-review.md`](reviews/phase-6-tier5-review.md).
  **Phase 6 generator-and-page group complete; T6 close-out next.**
- 2026-05-04 — **PR #35 merged** (`3235f60`): Phase 6 T4 shipped —
  `pages/4_Export.py` page shell + manual regenerate button +
  per-file mtimes panel. Regenerate button wraps
  `exports.write_all()` in try/except per GUIDELINES §8 (friendly
  `st.error`, no re-raise; success toast persists across rerun).
  Mtimes panel: one `st.markdown` line per locked filename via
  `Path.exists()` + `datetime.fromtimestamp` formatting; "── Download
  ───" wireframe section header deliberately omitted (scopes T5).
  12 new tests in `TestExportPageShell` + `TestExportPageRegenerateButton`
  + `TestExportPageMtimesPanel`; mtimes test uses `os.utime` to a
  deterministic epoch for exact-string assertions. Suite 815 → 827
  under both pytest gates. First project PR to land with
  `mergeStateStatus: CLEAN`. Pre-merge review at
  [`reviews/phase-6-tier4-review.md`](reviews/phase-6-tier4-review.md).
- 2026-05-04 — **PR #34 merged** (`c11fde4`): Phase 6 T3 shipped —
  `exports.write_recommenders()` filled with an 8-column markdown
  table writer to `exports/RECOMMENDERS.md`. Reuses
  `_format_confirmation` for the Reminder cell + new local
  `_format_confirmed` for the Confirmed cell; `notes` deliberately
  omitted; sort `recommender_name ASC, deadline_date ASC NULLS
  LAST, id ASC` with deadline merged in pandas from
  `get_all_positions()`. Three-commit branch (test → feat → fix);
  the fix augmented `isolated_exports_dir` with DB isolation,
  closing the CI-red regression latent since T1. Process amendment
  in `c284c20` requires CI-green-conclusion before admin-bypass +
  CI-mirror local check (`mv postdoc.db postdoc.db.bak && pytest
  && mv postdoc.db.bak postdoc.db`) in standing pre-PR checklist.
  14 new tests in `TestWriteRecommenders`; suite 801 → 815 under
  both pytest gates. Pre-merge review at
  [`reviews/phase-6-tier3-review.md`](reviews/phase-6-tier3-review.md).
- 2026-05-04 — **PR #33 merged** (`911115a`): Phase 6 T2 shipped —
  `exports.write_progress()` filled with an 8-column markdown table
  writer to `exports/PROGRESS.md` (positions × applications ×
  interviews; no Deadline column — different question from T1).
  Tri-state helpers `_format_confirmation` (`—` / `✓ {ISO}` / `✓ (no
  date)`) and `_format_interviews_summary` (`—` / `{N} (last: {ISO})`
  / `{N} (no dates)`); `last` = max(scheduled_date), round-trippable
  + idempotent + deterministic. Mandatory conftest fixture lift
  (`tests/conftest.py::db` monkeypatches both `DB_PATH` AND
  `EXPORTS_DIR`) closes T1's exposed test-isolation pollution; T2
  isolation gate added to standing pre-PR checklist. 15 new tests in
  `TestWriteProgress`; suite 786 → 801 under both pytest gates.
  Pre-merge review at [`reviews/phase-6-tier2-review.md`](reviews/phase-6-tier2-review.md).
- 2026-05-04 — **PR #32 merged** (`e9a8a4a`): Phase 6 T1 shipped —
  `exports.write_opportunities()` filled with an 8-column markdown
  table writer to `exports/OPPORTUNITIES.md`. Sort: `deadline_date
  ASC NULLS LAST, position_id ASC` via `pandas.sort_values(...
  kind="stable")`. Cell shapes: em-dash for NULL TEXT, ISO TEXT
  pass-through for dates, **raw bracketed sentinel** for Status
  (`[APPLIED]` not `Applied` — markdown is a backup format, not a
  UI surface; pinned by `test_status_renders_as_raw_bracketed_sentinel`).
  Idempotent (DESIGN §7 contract #2). 9 new tests in
  `TestWriteOpportunities`; suite 777 → 786 under both pytest gates.
  Pre-merge review at [`reviews/phase-6-tier1-review.md`](reviews/phase-6-tier1-review.md).
- 2026-05-04 — **`v0.6.0` tagged** on `main` closing Phase 5 — two
  pages complete (Applications + Recommenders) across six tiers
  (T1–T6); close-out cohesion-smoke at
  [`reviews/phase-5-finish-cohesion-smoke.md`](reviews/phase-5-finish-cohesion-smoke.md);
  CHANGELOG `[Unreleased]` → `[v0.6.0]` split at the boundary commit
  (mirror of `db383e3` precedent); suite at 777 / 1 xfailed under
  both pytest gates.
- 2026-05-04 — **PR #31 merged** (`6993ea9`): Phase 5 T6 (T6-A + T6-B)
  shipped — Compose-reminder-email `st.link_button` (locked DESIGN
  §8.4 mailto subject + body, no `to:` field) + `LLM prompts (2 tones)`
  expander with one `st.code(prompt, language="text")` per locked tone
  (`gentle`, `urgent`), wired into each Pending Alerts card on
  `pages/3_Recommenders.py`. Two pure helpers
  (`_build_compose_mailto`, `_build_llm_prompt`); existing T4
  `_bullets`-building loop extended by one line for `days_ago`
  collection. Suite 756 → 777 under both pytest gates. Pre-merge
  review at [`reviews/phase-5-tier6-review.md`](reviews/phase-5-tier6-review.md).
- 2026-05-03 — **PR #29 merged** (`2293ebd`): Phase 5 T5 (T5-A + T5-B
  + T5-C) shipped — All-Recommenders table + filters + Add form +
  inline edit card + dialog-gated Delete on `pages/3_Recommenders.py`
  with the `RELATIONSHIP_TYPES` → `RELATIONSHIP_VALUES` cohesion
  rename. Suite 700 → 756 under both pytest gates. Pre-merge review
  at [`reviews/phase-5-tier5-review.md`](reviews/phase-5-tier5-review.md).
- 2026-05-03 — **PR #28 merged** (`a491be3`): Phase 5 T4 shipped —
  `pages/3_Recommenders.py` page shell (`set_page_config`, title,
  `database.init_db()`) + Pending Alerts panel (`get_pending_recommenders()`
  grouped by `recommender_name`, one `st.container(border=True)` per
  person with relationship in header, em-dash on NULL deadlines).
  Suite 682 → 700 under both pytest gates. Pre-merge review at
  [`reviews/phase-5-tier4-review.md`](reviews/phase-5-tier4-review.md).
- 2026-05-01 — **Phase 5 T3-rev (T3-rev-A + T3-rev-B) shipped on
  branch** `feature/phase-5-tier3-InterviewManagementUI` —
  truth-file alignment for the Applications page. T3-rev-A: split
  the combined Position cell (`f"{institute}: {position_name}"`)
  into separate Position + Institute columns per the amended
  DESIGN §8.3 seven-column contract; both go through
  `_safe_str_or_em` (NaN→EM_DASH per gotcha #1); column widths
  Position=large / Institute=medium. T3-rev-B: replaced the single
  page-level `apps_interviews_form` with per-row
  `apps_interview_{id}_form` (`border=False`) blocks — each
  interview is now a self-contained block of {Interview number
  heading + Detail row + per-row Save submit + per-row Delete} per
  the user's directive. Streamlit fires at most one form submit
  per click rerun, so the per-row Save handler (`if saves_clicked:`)
  processes a single (iid, seq) tuple at a time — sibling rows'
  in-flight drafts survive the rerun via the per-row pre-seed
  sentinel `_apps_interviews_seeded_ids` (intersection-pruned
  frozenset; NOT popped on Save success). Toast / error wording
  switched to singular + sequence (`Saved interview {seq}.`,
  `Could not save interview {seq}: {e}`) — closes T3 review
  Finding #6 wording asymmetry by side-effect. 6 net new test
  cases (4 from T3-rev-A column tests + 2 from T3-rev-B per-row
  Save tests minus the retired
  `test_two_dirty_rows_call_update_interview_twice`); suite 676 →
  683 under both pytest gates.
- 2026-05-01 — **Phase 5 T3-rev-A shipped on branch**
  `feature/phase-5-tier3-InterviewManagementUI` — Position / Institute
  column split per the post-T3 truth-file alignment. DESIGN §8.3
  amended with an explicit seven-column contract for the Applications
  table (Position bare, Institute bare, Applied, Recs, Confirmation,
  Response, Result); wireframe already shows the same structure since
  `2bd20ab`. Page now uses `_safe_str_or_em` on both `position_name`
  and `institute` columns instead of a combined `f"{institute}:
  {position_name}"` Position cell. Position keeps `width="large"`
  (bare `position_name` can still be long); Institute is
  `width="medium"`. The `_format_label` helper stays — still used by
  the detail-card header. 4 net new test cases; suite 676 → 681
  under both pytest gates.
- 2026-05-01 — **Phase 5 T3 shipped on branch**
  `feature/phase-5-tier3-InterviewManagementUI` (T3-A + T3-B both
  green; pre-merge review + PR pending). T3-A: inline interview
  list under the existing T2 detail card with `apps_interviews_form`
  per-row edit form (date / format / notes widgets keyed
  `apps_interview_{id}_{date|format|notes}` per DESIGN §8.3 D-B),
  `_safe_str`-normalized dirty-diff Save calling
  `database.update_interview` per dirty row only, Add button outside
  the form calling
  `database.add_interview(sid, {}, propagate_status=True)` with R2
  promotion toast on `status_changed=True`; per-row pre-seed
  sentinel `_apps_interviews_seeded_ids` (frozenset, intersection-
  pruned per rerun) preserves sibling drafts across Add and stays
  zombie-id-free across delete. T3-B: per-row Delete buttons
  rendered in a single horizontal `st.columns(N)` row BELOW the
  form (Streamlit 1.56 forbids `st.button` inside `st.form`), each
  keyed `apps_interview_{id}_delete` and labelled
  `🗑️ Delete Interview {seq}`; module-level
  `@st.dialog`-decorated `_confirm_interview_delete_dialog` with the
  gotcha #3 re-open trick implemented via a single post-loop
  `pending_id in current_ids` guard (which doubles as automatic
  stale-target cleanup when the user navigates to a different
  position). Confirm path: `database.delete_interview(id)` +
  paired sentinel cleanup + selection preserved (gotcha #11) +
  `Deleted interview {seq}.` toast + rerun. Cancel path: silent
  cleanup + selection preserved + rerun. Failure path: `st.error`
  per GUIDELINES §8 with sentinels surviving so the dialog
  re-opens for retry (mirrors the Opportunities-page
  failure-preserves-state precedent). 38 new tests across 6 new
  classes (4 from T3-A + 2 from T3-B); suite 638 → 676 under
  both pytest gates.
- 2026-04-30 — **PR #16 merged** (`b9a2c82`): Phase 5 T2 (T2-A + T2-B)
  shipped — editable Application detail card behind row selection +
  cascade-promotion toast surfacing. Suite 586 → 638 under both pytest
  gates. Detailed forensic record in commit messages + the
  [`phase-5-Tier2-review.md`](reviews/phase-5-Tier2-review.md) review.
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

_Updated: 2026-05-04 (Phase 7 T4 merged via PR #40; main HEAD `952f0e9`; suite 864 / 1 xfailed; Phase 7 T5 — Responsive layout check next)_
