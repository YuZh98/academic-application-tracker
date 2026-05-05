# Tasks

_Scope: software for this application tracker only. Older completions move to
`CHANGELOG.md` at the end of each sprint._

---

## Current sprint — Phase 5 — Applications + Recommenders pages

Per **Q5 Option A** from the 2026-04-27 v1 planning session, build
Applications page first.

Branch (T1): merged via PR #15 (`aebbb8b`); pre-merge review at
[`reviews/phase-5-tier1-review.md`](../../reviews/phase-5-tier1-review.md);
suite 553 → 586 green under both pytest gates.

Branch (T2): merged via PR #16 (`b9a2c82`); pre-merge review at
[`reviews/phase-5-Tier2-review.md`](../../reviews/phase-5-Tier2-review.md);
suite 586 → 638 green under both pytest gates.

Branch (T3): T3-A + T3-B + T3 review (9 findings, 2 inline fixes) +
T3-rev (T3-rev-A column split + T3-rev-B per-row block refactor) +
pre-merge review addendum (Findings #10–#13, 2 inline fixes) all on
`feature/phase-5-tier3-InterviewManagementUI`; suite 638 → 683
green under both pytest gates. Merged via PR #19 (`f4db64c`); pre-merge
review at [`reviews/phase-5-Tier3-review.md`](../../reviews/phase-5-Tier3-review.md).

Branch (T4): on `feature/phase-5-tier4-RecommendersAlertPanel`; pre-merge
review at [`reviews/phase-5-tier4-review.md`](../../reviews/phase-5-tier4-review.md);
suite 682 → 700 green under both pytest gates. Merged via PR #28 (`a491be3`).

Branch (T5): on `feature/phase-5-tier5-RecommendersTableAddEdit`; pre-merge
review at [`reviews/phase-5-tier5-review.md`](../../reviews/phase-5-tier5-review.md);
suite 700 → 756 green under both pytest gates. Merged via PR #29 (`2293ebd`).

Branch (T6): on `feature/phase-5-tier6-RecommenderReminders`; pre-merge
review at [`reviews/phase-5-tier6-review.md`](../../reviews/phase-5-tier6-review.md);
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
      sweep at [`reviews/phase-5-finish-cohesion-smoke.md`](../../reviews/phase-5-finish-cohesion-smoke.md)
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
      [`reviews/phase-4-finish-cohesion-smoke.md`](../../reviews/phase-4-finish-cohesion-smoke.md)
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
      finding 1 in [`reviews/phase-5-tier1-review.md`](../../reviews/phase-5-tier1-review.md).
- [ ] **C4** Split `CHANGELOG.md` `[Unreleased]` into a `[v0.5.0]`
      release section. Post-v0.4.0 work (v1.3 alignment + Phase 4
      T4/T5/T6 + this T1) accumulated under `[Unreleased]`; the
      `v0.5.0` tag now exists but no `[v0.5.0]` section sits between
      `[Unreleased]` and `[v0.4.0]`. Single housekeeping commit;
      logged as 🟢 finding 3 in
      [`reviews/phase-5-tier1-review.md`](../../reviews/phase-5-tier1-review.md).

### Phase 6 — Exports

Per **Q6 Option A**, plain markdown tables.

Branch (T1): on `feature/phase-6-tier1-WriteOpportunities`; pre-merge
review at [`reviews/phase-6-tier1-review.md`](../../reviews/phase-6-tier1-review.md);
suite 777 → 786 green under both pytest gates. Merged via PR #32 (`e9a8a4a`).

Branch (T2): on `feature/phase-6-tier2-WriteProgress`; pre-merge
review at [`reviews/phase-6-tier2-review.md`](../../reviews/phase-6-tier2-review.md);
suite 786 → 801 green under both pytest gates. Mandatory conftest
fixture lift (`db_and_exports` → `tests/conftest.py::db`) closes T1's
exposed pollution; T2 isolation gate (`git status --porcelain
exports/` empty post-pytest) now part of the standing pre-PR
checklist. Merged via PR #33 (`911115a`).

Branch (T3): on `feature/phase-6-tier3-WriteRecommenders`; pre-merge
review at [`reviews/phase-6-tier3-review.md`](../../reviews/phase-6-tier3-review.md);
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
at [`reviews/phase-6-tier4-review.md`](../../reviews/phase-6-tier4-review.md);
suite 815 → 827 green under both pytest gates. First PR in the
project's history to land with `mergeStateStatus: CLEAN` (rather
than `BLOCKED`); admin-bypass merge used anyway for procedure
consistency. Merged via PR #35 (`3235f60`).

Branch (T5): on `feature/phase-6-tier5-DownloadButtons`; pre-merge
review at [`reviews/phase-6-tier5-review.md`](../../reviews/phase-6-tier5-review.md);
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
      cohesion-smoke at [`reviews/phase-6-finish-cohesion-smoke.md`](../../reviews/phase-6-finish-cohesion-smoke.md)
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
**Cleanup + polish sub-tier (between T4 and T5; CL1-CL6 closed in full 2026-05-05; T5 deferred to v1.0-rc):**

- [x] **CL1** Pyright/mypy in CI fence + drift cleanup —
      `pyright==1.1.409` pinned in `requirements-dev.txt`,
      `[tool.pyright]` basic-mode block in `pyproject.toml` with
      explicit include/exclude lists, new "Pyright type-check" CI
      step in `.github/workflows/ci.yml` between Ruff lint and
      Pytest, `pyright .` row added to AGENTS.md + GUIDELINES.md
      pre-commit checklists. **45 type-drift errors → 0** across 5
      files (`tests/test_app_page.py`, `exports.py`,
      `pages/1_Opportunities.py`, `pages/2_Applications.py`,
      `pages/3_Recommenders.py`). All fixes follow PR #22's
      precedent patterns: `Any`-typed locals for `iterrows` cells
      (pandas-stubs `Series | ndarray | Any` union),
      `# type: ignore[call-overload]` for pandas `rename`
      overload-resolution churn, `is not None` guards for AppTest
      `Button | None` returns, `cast(pd.DataFrame, ...)` for
      mask-narrowing where the runtime guarantee is "always
      DataFrame here". All 45 fixes are runtime no-ops (864 → 864
      passed). Six commits on branch (1 chore + 5 file-scoped
      fixes — per-file commit split gives per-line `git blame`
      attribution that survives the cleanup). Suite stable at 864
      / 1 xfailed under all seven gates. Branch auto-deleted on
      merge via `gh pr merge --delete-branch`. Merged via PR #41
      (`eac75c3`).
- [x] **CL2** `config.py` lifts — closed carry-overs **C2** + **C3**
      in one PR. Four lifts to `config.py`: `EM_DASH = "—"` (was
      duplicated in 5 modules — `app.py` as `NEXT_INTERVIEW_EMPTY`,
      three `pages/*.py`, `exports.py` as `_EM_DASH`); new
      `urgency_glyph(days_away: int | None) -> str` function (was
      duplicated as `database.py::_urgency_glyph(int)` and
      `pages/1_Opportunities.py::_deadline_urgency(Any)` — the
      lifted form takes the canonical `int | None`; the
      page-layer wrapper retains the date-string parsing concern +
      delegates; `database.py::_urgency_glyph` deleted entirely
      with its two `get_upcoming` call sites now passing
      `config.urgency_glyph` directly into `Series.apply`);
      `FILTER_ALL = "All"` (was magic literal in 3 pages, lives
      next to `STATUS_FILTER_ACTIVE` in config); `REMINDER_TONES:
      tuple[str, ...] = ("gentle", "urgent")` (was page-local
      `_REMINDER_TONES` in Recommenders). One drop:
      `TRACKER_PROFILE` + `VALID_PROFILES` + import-time assert +
      4 `TestTrackerProfile` tests (carry-over **C2** — never read
      by any module since v1.1 doc refactor). All four lifts are
      behaviour-preserving refactors; 6 net new tests pin the new
      contracts at the lift surface; existing per-page urgency /
      filter / reminder tests pass without modification.
      **Pyright fence held through the lift** — `pyright .`
      returns 0/0 post-CL2, confirming no type-shape drift in any
      of the 6 consumer modules. Suite 864 → 870 under all seven
      gates. Five commits on branch (1 test red + 4 refactor
      commits, one per lift/drop) for clean per-line `git blame`
      attribution. Branch auto-deleted on merge via
      `--delete-branch`. Merged via PR #42 (`bd76d29`).
- [x] **CL3** `tests/helpers.py` extraction — 4 AppTest helpers
      lifted verbatim from per-page test files into shared
      `tests/helpers.py` module: `link_buttons` + `decode_mailto`
      (was page-local in `test_recommenders_page.py`),
      `download_buttons` + `download_button` (was page-local in
      `test_export_page.py`). Leading-underscore dropped on lift
      (helpers go from page-test-private to test-module-public).
      **Paren-anchored rename strategy** (`_helper(` → `helper(`)
      preserved test method substring matches like
      `test_three_download_buttons_render` (which contains
      `download_buttons` as a substring of the test method name) —
      a naive substring rename would have corrupted the test
      method name into a mangled form, breaking pytest collection.
      Worth recording as precedent for future rename-on-lift
      refactors. New `tests/test_helpers.py` with 5 smoke tests:
      import-compat (callable check on all 4 names) +
      `decode_mailto` round-trip + URL-decoding + missing-fields
      defaulting + non-`mailto:` scheme rejection. The three
      AppTest-dependent helpers (`link_buttons`,
      `download_buttons`, `download_button`) get only the
      import-compat smoke check — their behavioural coverage is
      the 114 existing tests in the consumer files. **Pyright
      fence held through the lift** — 0/0 post-CL3, confirming no
      type drift. Suite 870 → 875 under all seven gates. Two
      commits on branch (refactor + smoke tests). Branch
      auto-deleted on merge via `--delete-branch`. Merged via
      PR #43 (`479aa15`).
- [x] **CL4** Phase 7 polish batched (4 UX fixes) — four UX
      polish items shipped in one PR with four commits (one per
      fix) for clean per-line `git blame`. **Fix 1
      (`feat(phase-7-CL4)`):** save-toast wording branched on
      dirty diff across three save handlers — `apps_detail_form`
      (gained per-field dirty diff vs. persisted `app_row`; was
      previously an unconditional `upsert_application` with full
      8-field payload + `Saved` toast), per-row
      `apps_interview_{id}_form` (dirty diff already gated the
      DB write — only the toast wording was previously
      dishonest), `recs_edit_form` (same shape — `_dirty` already
      gated). No-op clicks now fire
      `st.toast("No changes to save.")` instead of the misleading
      `Saved "<name>".` Cascade safety: the `apps_detail_form`
      no-op short-circuit skips both the DB write AND the R1/R3
      cascade — there's no transition to fire against — pinned by
      `test_save_with_no_changes_skips_upsert` (spy on
      `database.upsert_application`). `pages/1_Opportunities.py`
      save handlers (overview / requirements / materials / notes)
      deliberately out of CL4 scope: they don't currently compute
      a dirty diff (always rewrite full payload), and adding the
      infrastructure to four more save paths would balloon CL4's
      "small UX fixes" mandate. Logged as follow-up. **Fix 2
      (`feat(phase-7-CL4)` + DESIGN amend):**
      `_build_compose_mailto` subject branches on `n_positions` —
      N=1 → `"Following up: letter for 1 postdoc application"`
      (singular both nouns); N≥2 → `"Following up: letters for
      {n} postdoc applications"` (unchanged plural shape).
      `DESIGN.md §8.4` line 631 amended in the same commit so
      spec and implementation stay in lockstep. Test
      `test_subject_uses_locked_string_with_position_count`
      updated to assert the new singular form; multi-position pin
      `test_subject_position_count_matches_card` unchanged. **Fix
      3 (`refactor(phase-7-CL4)`):** `app.py` empty-DB hero copy
      `st.write` → `st.markdown` — single outlier in a codebase
      that otherwise standardizes on `st.markdown` for prose
      (Pending Alerts cards on `app.py` + `pages/3_Recommenders.py`,
      Interviews subheader + per-row interview headings on
      `pages/2_Applications.py`, intro + per-file mtime lines on
      `pages/4_Export.py`). Convention picked per AGENTS.md spec:
      `st.markdown` for prose (with or without formatting),
      `st.write` for ambiguous-type renders (DataFrame, dict).
      Behaviour identical (`st.write(str)` routes to `st.markdown`
      internally — `at.markdown[i].value` lookups continue to
      work). Cohesion-only refactor; no test changes needed.
      **Fix 4 (`refactor(phase-7-CL4)`):** five `st.info(...)`
      empty-state strings lifted to per-surface constants in
      `config.py` — `EMPTY_FILTERED_POSITIONS`,
      `EMPTY_NO_POSITIONS` (Opportunities); `EMPTY_FILTERED_APPLICATIONS`
      (Applications); `EMPTY_PENDING_RECOMMENDERS` (Recommenders);
      `EMPTY_PENDING_RECOMMENDER_FOLLOWUPS` (dashboard). Per-surface
      naming (option a per spec) chosen over single-template
      (option b) because the wording is intentionally
      surface-specific: "filters" plural for Opportunities matches
      its multi-filter bar, "filter" singular for Applications
      matches its single-filter bar; "recommenders" on the page
      vs. "recommender follow-ups" on the dashboard distinguishes
      page-level vs. alert-panel framing. Tests in
      `test_opportunities_page.py`, `test_applications_page.py`,
      `test_recommenders_page.py`, `test_app_page.py` updated to
      assert against the constants by name (mirror of CL2's
      `EM_DASH` / `FILTER_ALL` test-update pattern) so a future
      copy edit lands once in `config.py` and flows through to
      assertions automatically. **Pyright fence held through all
      four fixes** — `pyright .` returns 0/0 post-CL4. Suite 875 →
      879 (+4 new tests, all in Fix 1 — three no-op-toast pins +
      one no-op-skips-upsert spy) under all seven gates. Three
      🟡 doc-drift findings surfaced in pre-merge review and
      deferred to **CL5** for the trim sweep: history-as-guidance
      anti-pattern in `DESIGN.md` line 631 (back-references
      "previously-locked verbatim plural-only form" + "Phase 7
      CL4 Fix 2 amended this line"), same anti-pattern in the
      `_build_compose_mailto` docstring, and noisy "Phase 7 CL4
      Fix N: ..." comment blocks repeated across consumer sites.
      Branch auto-deleted on merge via `--delete-branch`. Merged
      via PR #44 (`9a5eded`).
- [x] **CL5** CL4 doc-drift carry-overs (code-area) — three
      trims shipped (DESIGN §8.4 line 631 back-reference clause
      drop + `pages/3_Recommenders.py::_build_compose_mailto`
      docstring rewrite to forward-looking rule + ~17-site sweep
      across 4 source + 4 test files + `config.py` section
      header). Full-sweep outcome — `grep -rn "Phase 7 CL4 Fix"`
      returns 0 matches post-CL5. Forward-looking invariants kept
      (cascade-safety note on apps_detail_form save handler +
      dirty-diff design rationale + "pin against constant by
      name" reasoning); change-log noise dropped (5 verbatim
      "lifted to config" comments + 2 toast-wording-branch
      blocks + config.py section-header CL4 attribution). Test
      docstrings dropped `Phase 7 CL4 Fix N:` prefix; contract-
      pinning prose stays. Net 0 test count change (879 → 879);
      net −50 lines (−97 / +47, mostly comment deletions).
      **Pyright fence held** through the doc-trim (0/0 post-CL5)
      — fourth consecutive refactor PR confirming CL1's value.
      Three commits on branch (one per trim) for clean per-line
      `git blame`. Branch auto-deleted on merge via
      `--delete-branch`. Merged via PR #45 (`9dd87d3`).
- [x] **CL6** Process amendment + retroactive doc drift
      (orchestrator-only, ran direct on main as two split commits
      `04fa7a3` + `bc1017e`). CL6a codified
      `gh pr merge --delete-branch` in `ORCHESTRATOR_HANDOFF.md`
      "Recurring post-merge ritual" (5 consecutive proven uses
      CL1-CL5). CL6b stripped `Kept by design` rows from Phase 6
      T2/T3/T4 review-doc Findings tables (per GUIDELINES §10
      those belong in Q&A; T2: 4→1, T3: 4→2, T4: 4→2; T4 added
      Q7 covering `── Download ───` section-header omission) +
      added forensic-preservation framing paragraphs to
      CHANGELOG `[v0.4.0]` / `[v0.3.0]` / `[v0.2.0]` / `[v0.1.0]`
      matching the existing `[v0.7.0]` / `[v0.6.0]` / `[v0.5.0]`
      pattern (pre-§14.4 entries explicitly preserved as
      forensic record; content untouched).

- [⏭️] **T5** Responsive layout check at 1024 / 1280 / 1440 / 1680
      widths — **deferred to v1.0-rc.** No Chrome DevTools MCP
      available in the current environment; bundles naturally
      with publish-scaffolding tier (`README.md` screenshots +
      Streamlit Cloud deploy verification + recorded demo GIF).
      Folder target renamed to `docs/ui/screenshots/v1.0.0/`.
      Documented in [`reviews/phase-7-finish-cohesion-smoke.md`](../../reviews/phase-7-finish-cohesion-smoke.md).
- [x] **T6** Phase 7 close-out + tag `v0.8.0` — cohesion-smoke
      doc at [`reviews/phase-7-finish-cohesion-smoke.md`](../../reviews/phase-7-finish-cohesion-smoke.md);
      CHANGELOG `[Unreleased]` → `[v0.8.0]` split; tag annotation
      lists T1-T4 + CL1-CL6 + the three structural changes
      (pyright fence, cohesion-pinning tests, `--delete-branch`
      codification). Suite 879 + 1 xfailed. Pyright 0/0.

### v1.0-rc — schema cleanup

- [x] Physical drop of `applications.confirmation_email` per DESIGN §6.3
      "Remove a col" — `ALTER TABLE applications DROP COLUMN
      confirmation_email` (SQLite 3.35+, replaces the originally-spec'd
      CREATE-COPY-DROP-RENAME rebuild because the column carries no
      PK / UNIQUE / INDEX / FK-ref / CHECK / generated constraint).
      Idempotent via `PRAGMA table_info(applications)` gate. DESIGN §6.3
      amended with two-shape guidance in the same PR. Merged via PR #47
      (`bf73bdd`); suite 879 → 883 under all seven gates; tagged `v0.9.0`.

### Publish scaffolding (per Q7 Option C — both live + recorded GIF)

- [x] **P1** `README.md` at repo root — what it is, the one daily
      question it answers, install/run, screenshot, link to DESIGN.md
      _(PR #46, screenshot deferred — see P4b)_
- [x] **P2** `LICENSE` (MIT, per DESIGN §4) _(PR #46)_
- [~] **P3** `requirements.txt` audit + freeze (`pip freeze`, prune
      unused deps) _(PR #46 declared `requires-python>=3.11` floor + lowered
      ruff/pyright targets; transitive-dep prune still pending — low-impact follow-up)_
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

- 2026-05-05 — **`v0.9.0` tagged** (close-out commit + annotated tag):
  v1.0-rc schema cleanup + publish-readiness scaffolding shipped.
  CHANGELOG `[Unreleased]` → `[v0.9.0]` split (boundary covers both
  PR #46 publish-readiness + PR #47 schema cleanup); CHANGELOG
  version-link table + Links section repo URLs bumped
  `hugs_application_tracker` → `academic-application-tracker`
  (post-`gh repo rename` cleanup; old URLs auto-redirect forever but
  canonical form is the new name). Tag annotation lists the two PR
  scopes + the migration shape + the path-to-v1.0.0 (P3 / P4a / P4b /
  P5 / P6 / Phase 7 T5 still pending). All seven pre-tag gates green
  at HEAD: ruff · pyright 0/0 · pytest 883+1xf · `-W
  error::DeprecationWarning` · status-literal grep · `git status
  --porcelain exports/` · CI-mirror.
- 2026-05-05 — **PR #47 merged** (`bf73bdd`, admin-bypass + `--delete-branch`):
  v1.0-rc schema cleanup landed. Branch
  `feature/v1-rc-schema-cleanup-confirmation-email` carried 4 commits
  (`test:` → `feat:` → `chore:` → `review:`) implementing the
  long-running v1.3 Sub-task 10 split migration's final step:
  `applications.confirmation_email` TEXT column physically dropped via
  SQLite 3.35+ `ALTER TABLE ... DROP COLUMN` (idempotent via PRAGMA
  table_info gate; data-safe — column NULL-only since v1.3). DESIGN
  §6.3 "Remove a col" amended in same PR with two-shape guidance
  (DROP COLUMN preferred when constraint-eligible; CREATE-COPY-DROP-
  RENAME rebuild fallback when not — and the rebuild needs `PRAGMA
  foreign_keys=OFF` outside the transaction when other tables FK in).
  Test class `TestV1RcConfirmationEmailDrop` pins 5 properties
  (column drop · data preservation · PK preservation · idempotency ·
  E2E pre-v1.3 → split → drop in one `init_db()`); 1 obsolete NULL-
  clear test + 1 obsolete in-row assertion dropped (rebuild
  supersedes them). Pre-merge audit surfaced one 🟡 finding (stale
  "rebuild" naming in test class + comments), fixed inline in `4f3e70d`
  before merge. Suite 879 → 883 under all seven gates; pyright fence
  held 0/0.
- 2026-05-05 — **PR #46 merged** (`3915536`): publish-readiness
  must-haves landed as a single 7-commit PR ahead of the public
  flip. Drove the resume-use launch sequence: privacy redact
  (drop personal email + visa detail from
  `docs/internal/ORCHESTRATOR_HANDOFF.md`); doc-tier reorg moving
  `AGENTS.md` / `ORCHESTRATOR_HANDOFF.md` / `TASKS.md` to
  `docs/internal/` (DESIGN/GUIDELINES/CHANGELOG/roadmap stay at
  root as public-readable engineering signal); Python floor
  `>=3.11` declared in `pyproject.toml [project]` + ruff/pyright
  targets lowered to match; MIT `LICENSE` added; public-facing
  `README.md` written (engineering-practices section is the
  resume-signal carrier — names the 879-test suite, pyright
  fence, ruff, deprecation-strict gate, cohesion tests,
  atomic-commit cadence, spec-first design); root cleanup
  (delete `dashboard.html` + `.coverage`, gitignore `.coverage*`/
  `htmlcov/`); seed-template archive (move `OPPORTUNITIES.md`/
  `PROGRESS.md`/`RECOMMENDERS.md` to `docs/seed-templates/` with
  brief directory README — kept as design-history artifacts per
  user request); rebrand `Postdoc Tracker` →
  `Academic Application Tracker` across 18 files (atomic — every
  user-visible string + spec pin + test assertion flips in one
  commit). Suite stays 879 + 1 xfailed under all seven gates.
  Post-merge admin: `gh repo rename hugs_application_tracker →
  academic-application-tracker` (auto-redirects old URL forever);
  `gh repo edit` set description + 8 topics (`streamlit`,
  `python`, `sqlite`, `job-tracker`, `application-tracker`,
  `phd`, `postdoc`, `academic`); local clone remote URL bumped
  to new name. Public-flip itself NOT yet executed — paused on
  user confirmation per "one-way door" rule. Versioning
  decoupled from public flip per user direction (resume-use
  launch can land at v0.x; v1.0.0 follows the schema cleanup +
  Streamlit Cloud demo on the `v1.0-rc` branch).
- 2026-05-05 — **`v0.8.0` tagged** (close-out commit + annotated
  tag): Phase 7 closed. T6 cohesion-smoke at
  [`reviews/phase-7-finish-cohesion-smoke.md`](../../reviews/phase-7-finish-cohesion-smoke.md);
  CHANGELOG `[Unreleased]` → `[v0.8.0]` split (boundary at the
  T6 close-out commit); tag annotation lists T1-T4 + CL1-CL6 +
  the three structural changes (pyright fence in CI · cohesion-
  pinning tests in `tests/test_pages_cohesion.py` · `gh pr merge
  --delete-branch` codified in post-merge ritual). T5 (responsive
  layout) explicitly deferred to v1.0-rc (no Chrome DevTools MCP
  available; bundles with publish scaffolding). All seven pre-tag
  gates green at HEAD. Phase 7 spans 24 commits across 9 PRs +
  3 orchestrator-direct commits, suite 834 → 879 (+45 tests),
  pyright fence held 0/0 across 4 consecutive refactor PRs.
- 2026-05-05 — **CL6c closed** (`079564b`): pre-tag drift trim.
  Pre-`v0.8.0` comprehensive audit (8 parallel Explore agents)
  surfaced 5 minor nits — DESIGN history-as-guidance × 2 (line
  355 DDL comment "Replaces the earlier flat ..." + line 470
  contract #2 amendment preamble), GUIDELINES line 399 pre-commit
  checklist parenthetical, TASKS footer HEAD hash one commit
  stale, CHANGELOG bare `[drift audit]` placard. All 5 fixed in
  single commit. All seven gates green.
- 2026-05-05 — **CL6 closed** (`04fa7a3` + `bc1017e`): Phase 7
  cleanup CL6 shipped as two split commits direct on main
  (orchestrator-only, no PR). CL6a (`04fa7a3`) codified
  `gh pr merge --delete-branch` in `ORCHESTRATOR_HANDOFF.md`
  "Recurring post-merge ritual" — 5 consecutive proven uses
  CL1-CL5 (PRs #41 / #42 / #43 / #44 / #45). CL6b (`bc1017e`)
  retroactive doc-drift trim: Phase 6 T2/T3/T4 review-doc
  Findings tables stripped of `Kept by design` rows per
  `GUIDELINES §10` (T2: 4→1, T3: 4→2, T4: 4→2) with kept-by-
  design coverage routed to existing Q&A entries; T4 gained Q7
  covering wireframe-pinned `── Download ───` section-header
  omission rationale (header ships with T5 download buttons).
  CHANGELOG `[v0.4.0]` / `[v0.3.0]` / `[v0.2.0]` / `[v0.1.0]`
  gained forensic-preservation framing paragraphs matching the
  existing `[v0.7.0]` / `[v0.6.0]` / `[v0.5.0]` pattern (pre-
  §14.4 entries preserved as forensic record; content
  untouched). All seven gates green at HEAD. Phase 7 cleanup
  sub-tier (CL1-CL6) closed in full.
- 2026-05-05 — **PR #45 merged** (`9dd87d3`): Phase 7 cleanup CL5
  shipped — 3 trims closing the CL4 doc-drift carry-overs. Full
  sweep — `grep -rn "Phase 7 CL4 Fix"` returns 0 matches post-CL5.
  Forward-looking invariants kept; change-log noise dropped.
  Pyright fence held (0/0; 4th consecutive refactor PR
  confirming CL1's value). Suite stable at 879 / 1 xfailed under
  all seven gates. Net −50 lines (mostly comment deletions).
  Three commits on branch (one per trim) for clean per-line
  `git blame`. Pre-merge review at
  [`reviews/phase-7-CL5-review.md`](../../reviews/phase-7-CL5-review.md).
- 2026-05-05 — **PR #44 merged** (`9a5eded`): Phase 7 cleanup CL4
  shipped — 4 batched UX fixes. (1) Save-toast wording branched
  on dirty diff in apps_detail_form + per-row interview save +
  recs_edit_form (apps_detail_form gained dirty-diff
  infrastructure — no-op skips DB write AND R1/R3 cascade,
  pinned by spy test). (2) `_build_compose_mailto` subject
  branches on `n_positions` (N=1 → singular; N≥2 → plural);
  DESIGN §8.4 line 631 amended. (3) `app.py` empty-DB hero
  `st.write` → `st.markdown` (lone outlier in cross-page
  convention). (4) 5 empty-state strings lifted to per-surface
  `config.py` constants. Suite 875 → 879 under all seven gates.
  Pyright fence held (0/0). 3 🟡 doc-drift findings deferred to
  CL5 (closed in PR #45 above). Pre-merge review at
  [`reviews/phase-7-CL4-review.md`](../../reviews/phase-7-CL4-review.md).
- 2026-05-04 — **PR #43 merged** (`479aa15`): Phase 7 cleanup CL3
  shipped — 4 AppTest helpers extracted to `tests/helpers.py`
  (link_buttons + decode_mailto + download_buttons + download_button).
  Paren-anchored rename strategy (`_helper(` → `helper(`)
  preserved test method substring matches. New `tests/test_helpers.py`
  with 5 smoke tests. Pyright fence held (0/0). Suite 870 → 875
  under all seven gates. Pre-merge review at
  [`reviews/phase-7-CL3-review.md`](../../reviews/phase-7-CL3-review.md).
- 2026-05-04 — **PR #42 merged** (`bd76d29`): Phase 7 cleanup CL2
  shipped — 4 lifts to `config.py` (EM_DASH, urgency_glyph,
  FILTER_ALL, REMINDER_TONES) + drop of TRACKER_PROFILE block.
  Closes carry-overs **C2** + **C3** in one PR. Pyright fence
  held through the lift (0/0). Five commits on branch for clean
  per-line `git blame`. Suite 864 → 870 under all seven gates.
  Pre-merge review at [`reviews/phase-7-CL2-review.md`](../../reviews/phase-7-CL2-review.md).
- 2026-05-04 — **PR #41 merged** (`eac75c3`): Phase 7 cleanup CL1
  shipped — pyright type-check fence in CI + 45 drift errors → 0.
  `pyright==1.1.409` pinned, `[tool.pyright]` basic mode in
  `pyproject.toml`, new CI step + checklist rows. All 45 fixes
  follow PR #22's precedent patterns (Any-typed locals for
  iterrows, `# type: ignore[call-overload]` for pandas rename,
  `is not None` guards for AppTest helpers, `cast(pd.DataFrame,
  ...)`). Suite 864 → 864 (no behavioural change; runtime no-ops).
  Six commits on branch (1 chore + 5 file-scoped fixes for clean
  per-line `git blame`). First PR merged with
  `--delete-branch` flag (testing branch-cleanup-on-merge ritual).
  Pre-merge review at [`reviews/phase-7-CL1-review.md`](../../reviews/phase-7-CL1-review.md).
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
  [`reviews/phase-7-tier4-review.md`](../../reviews/phase-7-tier4-review.md).
- 2026-05-04 — **PR #39 merged** (`85968bb`): Phase 7 T3 shipped —
  verification-only `set_page_config` sweep across all 5 pages
  (`app.py` + 4 `pages/*.py`). New `tests/test_pages_cohesion.py`
  with `TestSetPageConfigSweep` (10 parametrized tests, 2
  invariants per page). Audit outcome: all 5 pages already conform
  to locked shape — no production code touched. AST helper
  deliberately skips decorators (load-bearing — `@st.dialog`
  doesn't trip Streamlit's first-call gate). Suite 843 → 853 under
  both pytest gates. Pre-merge review at
  [`reviews/phase-7-tier3-review.md`](../../reviews/phase-7-tier3-review.md).
- 2026-05-04 — **PR #38 merged** (`e67cfed`): Phase 7 T2 shipped —
  free-text "Search positions" `text_input` prepended to the
  Opportunities filter row; `position_name` substring match
  (case-insensitive, regex=False, NaN-safe) AND-combined with
  status / priority / field filters. Search scope `position_name`
  only (kept-by-design — field has its own filter widget). Filter
  row reweights `[2, 2, 3]` → `[3, 2, 2, 3]` with search widest.
  7 new tests; suite 836 → 843 under both pytest gates. CI procedure
  followed cleanly (third clean end-to-end run). Pre-merge review
  at [`reviews/phase-7-tier2-review.md`](../../reviews/phase-7-tier2-review.md).
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
  [`reviews/phase-7-tier1-review.md`](../../reviews/phase-7-tier1-review.md).
- 2026-05-04 — **`v0.7.0` tagged** on `main` closing Phase 6 — three
  markdown generators (`write_opportunities` / `write_progress` /
  `write_recommenders`) backing `OPPORTUNITIES.md` / `PROGRESS.md` /
  `RECOMMENDERS.md` plus the new `pages/4_Export.py` (manual
  regenerate + per-file mtimes + per-file download buttons).
  Cohesion-smoke at
  [`reviews/phase-6-finish-cohesion-smoke.md`](../../reviews/phase-6-finish-cohesion-smoke.md);
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
  Pre-merge review at [`reviews/phase-6-tier5-review.md`](../../reviews/phase-6-tier5-review.md).
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
  [`reviews/phase-6-tier4-review.md`](../../reviews/phase-6-tier4-review.md).
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
  [`reviews/phase-6-tier3-review.md`](../../reviews/phase-6-tier3-review.md).
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
  Pre-merge review at [`reviews/phase-6-tier2-review.md`](../../reviews/phase-6-tier2-review.md).
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
  Pre-merge review at [`reviews/phase-6-tier1-review.md`](../../reviews/phase-6-tier1-review.md).
- 2026-05-04 — **`v0.6.0` tagged** on `main` closing Phase 5 — two
  pages complete (Applications + Recommenders) across six tiers
  (T1–T6); close-out cohesion-smoke at
  [`reviews/phase-5-finish-cohesion-smoke.md`](../../reviews/phase-5-finish-cohesion-smoke.md);
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
  review at [`reviews/phase-5-tier6-review.md`](../../reviews/phase-5-tier6-review.md).
- 2026-05-03 — **PR #29 merged** (`2293ebd`): Phase 5 T5 (T5-A + T5-B
  + T5-C) shipped — All-Recommenders table + filters + Add form +
  inline edit card + dialog-gated Delete on `pages/3_Recommenders.py`
  with the `RELATIONSHIP_TYPES` → `RELATIONSHIP_VALUES` cohesion
  rename. Suite 700 → 756 under both pytest gates. Pre-merge review
  at [`reviews/phase-5-tier5-review.md`](../../reviews/phase-5-tier5-review.md).
- 2026-05-03 — **PR #28 merged** (`a491be3`): Phase 5 T4 shipped —
  `pages/3_Recommenders.py` page shell (`set_page_config`, title,
  `database.init_db()`) + Pending Alerts panel (`get_pending_recommenders()`
  grouped by `recommender_name`, one `st.container(border=True)` per
  person with relationship in header, em-dash on NULL deadlines).
  Suite 682 → 700 under both pytest gates. Pre-merge review at
  [`reviews/phase-5-tier4-review.md`](../../reviews/phase-5-tier4-review.md).
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
  [`phase-5-Tier2-review.md`](../../reviews/phase-5-Tier2-review.md) review.
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

For earlier completions see [`CHANGELOG.md`](../../CHANGELOG.md).

---

_Updated: 2026-05-05 (v1.0-rc schema cleanup + publish-readiness shipped at `v0.9.0`; main HEAD post-rollup; suite 883 / 1 xfailed; pyright 0/0; remaining v1.0-rc deliverables before `v1.0.0`: P3 dep prune · P4a Streamlit Cloud deploy · P4b walkthrough GIF · P5 cross-doc link verify · P6 v1.0.0 PR + tag · Phase 7 T5 responsive layout check)_
