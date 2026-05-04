# Phase 5 Finish — Cross-Page Cohesion Smoke + Close-out

**Branch:** _(direct-to-main; orchestrator close-out doc)_
**Scope:** TASKS.md T7 — Phase 5 close-out. Combines the cohesion-smoke audit (mirror of `reviews/phase-4-finish-cohesion-smoke.md`) with the tier1–tier6 carry-over triage that gates the `v0.6.0` tag. The two Phase 5 surfaces — `pages/2_Applications.py` (T1–T3) and `pages/3_Recommenders.py` (T4–T6) — were each verified in isolation across their own tiers; T7 is the first time they get verified *together* and against the dashboard for visual rhythm.
**Verdict:** Approve `v0.6.0` tag. Three 🟡 polish findings deferred to Phase 7. No 🔴 / 🟠 blockers.
**Method:**
1. AppTest probes (populated + empty + populated-with-row-selected) — render every Phase 5 surface headlessly and dump every visible string in document order, so the cohesion claims below cite verbatim copy from the actual render rather than the spec. Probe script: `/tmp/phase5_cohesion_probe.py`; raw output: `/tmp/phase5_cohesion_probe.out`. Both are session-local and not committed.
2. Source audit — re-read `pages/2_Applications.py` and `pages/3_Recommenders.py` against DESIGN §8.3 + §8.4 with the six cohesion lenses (status labels, empty-state copy, date format, toast/error wording, NaN coercion, widget-key prefixes).
3. Tier-review carry-over triage — read `reviews/phase-5-tier1-review.md` … `reviews/phase-5-tier6-review.md` end-to-end and aggregate every open carry-over.
4. `pytest tests/ -q` and `pytest -W error::DeprecationWarning tests/ -q` — both **777 passed + 1 xfailed** at `main` HEAD `60789e6`. `ruff check .` clean. Status-literal grep returns 0 lines.

The browser-width capture step that Phase 4 owned (1280 / 1440 / 1680 PNGs) is **not** part of T7's contract — `TASKS.md` Phase 7 T5 owns the responsive-layout sweep and explicitly captures to `docs/ui/screenshots/v0.8.0/`. Phase 5 close-out is harness-driven only.

---

## Executive summary

Phase 5 composes cleanly across pages. Both Phase 5 pages follow a single visual grammar that is consistent within each page and coherent with the Phase 4 dashboard:

- **Status sentinel stripping.** No raw `[SAVED]` / `[APPLIED]` / `[INTERVIEW]` literal leaks anywhere reachable. Applications page filter selectbox shows `['Active', 'All', 'Saved', 'Applied', 'Interview', 'Offer', 'Closed', 'Rejected', 'Declined']` (sentinels mapped via `STATUS_LABELS.get(v, v)` with the `STATUS_FILTER_ACTIVE` identity-fallback per invariant #12). Detail-card subheader: `'MIT CSAIL: Postdoc in CS / ML · Interview'` — three-part `{institute}: {position_name} · {STATUS_LABELS[raw]}` with the status name unwrapped. The status-literal grep gate (GUIDELINES §11) returns 0 lines and is enforced by CI.

- **Empty-state pattern.** Applications page on empty DB shows `"No applications match the current filter."` (`st.info`); Recommenders Pending Alerts panel shows `"No pending recommenders."` (`st.info`). Both are the same primitive Phase 4 settled on (`st.info(...)`) and both follow the same present-tense "No X" phrasing. The All-Recommenders panel below is the lone exception — see Finding #1.

- **Label format reuse.** Both pages reuse the dashboard-precedent `{institute}: {position_name}` shape with bare-fallback when institute is empty. Applications detail-card header: `'MIT CSAIL: Postdoc in CS / ML · Interview'`. Recommenders Pending Alerts bullet: `'Stanford: Postdoc in Biostatistics (asked 14d ago, due May 18)'`. Recommenders All-Recommenders Position cell: `'MIT CSAIL: Postdoc in CS / ML'`. Same three code sites, three independent `_format_label` helpers (one on each page, one in the database layer for the dashboard); all converge on the same rendered shape.

- **Date format — Pending Alerts and Applications agree on `Mon D`.** `'asked 14d ago, due May 18'` (Recommender Pending Alerts), `'Apr 13'` (Applications Applied column), `'✓ Apr 15'` (Applications Confirmation column). The asymmetry is the All-Recommenders table — see Finding #2.

- **Toast / error wording.** Every Save / Add / Delete handler across both pages uses `st.toast(...)` for confirmations (`'Saved "..."'.`, `'Added ...'`, `'Deleted "..."'`) and `st.error(str(e))` for handler failures with the page sentinels surviving for retry (Opportunities-page failure-preserves-state precedent). No `st.success` anywhere — verified by source grep.

- **NaN coercion.** Both pages define `_safe_str(v)` and `_safe_str_or_em(v)` with identical bodies (mirror of `pages/1_Opportunities.py::_safe_str`). Every TEXT cell pre-seed for `st.text_input` / `st.text_area` runs through `_safe_str`. Em-dash `'—'` for NULL is consistent across all surfaces (Applications Recs column, Applications Confirmation column, Recommenders Confirmed/Submitted/Asked columns).

- **Widget-key prefix discipline.** Applications page: `apps_filter_status`, `apps_table`, `apps_detail_form`, `apps_applied_date`, `apps_confirmation_*`, `apps_response_*`, `apps_result_*`, `apps_notes`, `apps_interview_{id}_*`, `apps_add_interview`. Recommenders page: `recs_filter_position`, `recs_filter_recommender`, `recs_table`, `recs_add_*`, `recs_compose_{idx}`, `recs_edit_*`, `recs_delete_*`. Zero cross-prefix bleed; sentinel keys (`_applications_*`, `_recs_*`) follow the leading-underscore convention from gotcha #2.

- **Layout structure.** Applications: `set_page_config(layout="wide")` → title → filter → table → (selection-driven) detail card with interview list. Recommenders: `set_page_config(layout="wide")` → title → `Pending Alerts` subheader → cards → `All Recommenders` subheader → Add expander → filters → table → (selection-driven) edit card. Reading top-down on Recommenders: alerts (urgent / what to act on) → working surface (search / inspect / edit). Hierarchy is sound.

The three 🟡 findings below are all Phase 7 polish candidates — none gate the `v0.6.0` tag.

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `pages/3_Recommenders.py` All-Recommenders section | When `_filtered_df.empty` (genuinely empty DB OR filter narrows to zero), only an empty six-column `st.dataframe` renders below the "All Recommenders" subheader — no `st.info(...)` callout. Pending Alerts directly above DOES carry an empty-state info message, and the Phase 4 cohesion convention says every panel-with-data has an empty-state info branch. The empty 6-col frame is structurally correct (locked column contract, gotcha #16) but visually impoverished — a user with a wiped DB or a heavily-narrowed filter sees a header followed by white space. | 🟡 polish | Defer to Phase 7. One-line addition in the `if _filtered_df.empty` branch: `st.info("No recommenders match the current filter.")` (filter case) or `st.info("Add a recommender to see it here.")` (empty DB case). Pick wording per the present-tense Phase 4 pattern. |
| 2 | `pages/3_Recommenders.py` All-Recommenders table — `Asked` / `Submitted` columns | `Asked` renders as raw ISO `'2026-05-01'`; the Applications page Applied / Confirmation columns render as `Mon D` (`'Apr 13'`, `'✓ Apr 15'`); the Pending Alerts panel renders as `'due May 18'` (`Mon D`). Same logical surface ("date a thing happened"), three different formats. The ISO form on All-Recommenders is *defensible* — All-Recommenders is the page's working data table, and a sortable / unambiguous YYYY-MM-DD makes sense for that role — but cohesion would suggest converging on one format unless the divergence is design-locked. | 🟡 polish | Defer to Phase 7. Two paths: (a) align All-Recommenders to `Mon D` via a 4-line `_format_date_short(iso)` helper applied in the column-projection step; (b) amend DESIGN §8.4 to lock the ISO form on All-Recommenders as the kept-by-design exception (mirror of the dashboard's KPI Next-Interview kept-by-design exception in Phase 4 cohesion-smoke Q1). User picks. |
| 3 | `pages/3_Recommenders.py` Add-Recommender form on empty DB | When the DB has no positions, the Position selectbox renders with `options=[]` and `value=None`. The user can still submit, and the handler defensively surfaces `st.error("Pick a position before adding a recommender.")`. The `st.error` is correct but the form is presented as if it were usable — better UX would be either (a) hiding the expander when `not _position_label_to_id` or (b) replacing the form with a prompt: `st.info("Add a position on the Opportunities page first.")`. | 🟡 polish | Defer to Phase 7. ~5-line guard in the expander block. Phase 7 T4 ("Confirm-dialog audit") is the natural home — adjacent UX-pre-condition gates. |
| 4 | `pages/2_Applications.py` (no subheaders) vs `pages/3_Recommenders.py` (`Pending Alerts` + `All Recommenders` subheaders) | Applications has zero `st.subheader` calls — the table is the primary surface and there are no distinct sections to label. Recommenders has two sections (alerts + working table) and so carries two subheaders. Cohesion-of-shape WITHIN each page holds; the cross-page asymmetry is by-design (different information architecture). | ℹ️ Kept-by-design | No action. Cohesion the project actually wants is "the same logical entity always uses the same SHAPE when there's room", not "every page uses identical primitives" — same justification as the Phase 4 cohesion-smoke Q1. |
| 5 | `pages/2_Applications.py` detail-card header (`st.subheader`) vs `pages/3_Recommenders.py` edit-card header (`st.markdown('**Editing: ...**')`) | Same logical slot ("Editing this row"), different Streamlit primitive. Applications uses `st.subheader(f"{institute}: {position_name} · {STATUS_LABELS[raw]}")`; Recommenders uses `st.markdown(f"**Editing: {_rec_name or EM_DASH}**")`. Visual weight is similar (subheader and bold-markdown read close at default font sizes), but the primitive divergence makes future styling sweeps more work. | ℹ️ Observation | Defer. If Phase 7 T1 ("Urgency colors on positions table") rolls into a broader column-styling pass, fold the primitive convergence in then; not worth its own commit. |
| 6 | `database.is_all_recs_submitted(pid)` returns vacuous-true for zero recs | A position with zero recommenders rendered into the Applications table's `Recs` column shows `'✓'` ("all submitted") — the same glyph as a position with N recommenders all of whose letters arrived. Locked decision per DESIGN D23 (vacuous-true is the mathematically honest reading). The current data dump shows `'—'` for both seeded positions because the seed has at least one un-submitted recommender on each. The vacuous-true case isn't reachable in the current cohesion seed — see Q4. | ℹ️ Kept-by-design | DESIGN D23 commits the project to the vacuous-true reading; no action. The Q4 entry below pins the rationale for future readers. |

*No 🔴 / 🟠 findings. The `v0.6.0` tag is clear.*

---

## Carry-over triage (tier1 → tier6)

The five Phase 5 tier reviews accumulated the following carry-overs. T7 disposes of each before tagging:

| Carry-over | Source | Status before T7 | Disposition |
|---|---|---|---|
| **C2** Drop unused `TRACKER_PROFILE` from `config.py` | v1.1 doc-refactor leftover (`TASKS.md` "Code carry-overs") | Open since v1.1 | **Defer to v1.0-rc** — single-line removal but the schema-cleanup tier is the natural bundle. Not blocking v0.6.0. |
| **C3** Promote `"All"` filter sentinel to `config.py` | `reviews/phase-5-tier1-review.md` Finding 1; extends through T5 (`pages/3_Recommenders.py::_FILTER_ALL`) and arguably to T6 (`_REMINDER_TONES` page-local) | Open; surface count grew tier-over-tier | **Defer to a cleanup tier between Phase 6 and Phase 7.** Project-wide refactor (3 page files); not blocking v0.6.0. Filed under "Code carry-overs" in `TASKS.md`. |
| **C4** Split `CHANGELOG.md` `[Unreleased]` → `[v0.5.0]` | `reviews/phase-5-tier1-review.md` Finding 3 | **Resolved** — split landed at commit `db383e3` (CHANGELOG line 79 currently shows `## [v0.5.0] — 2026-04-30 — ...`); `[Unreleased]` now contains only post-v0.5.0 work | **Closed.** No further action. The same machinery (manual section split at the boundary commit) will run again at v0.6.0 — see "v0.6.0 tag preparation" below. |
| **T5 Save toast wording when `_dirty` is empty** | `reviews/phase-5-tier5-review.md` Finding #2 | Open ℹ️ | **Defer to Phase 7.** Save's contract is "no error" → the current "Saved" toast is honest under that contract; the polish ask is to either suppress on no-op or change wording to "No changes to save." Phase 7 T4 (confirm-dialog audit) is the natural home. |
| **T6 Subject pluralization on `N=1`** | `reviews/phase-5-tier6-review.md` Finding #2 | Open ℹ️ | **Defer to Phase 7.** Current subject is verbatim DESIGN §8.4 (`"Following up: letters for 1 postdoc applications"` for N=1). Fix lives in `_build_compose_mailto` + a DESIGN amendment; Phase 7 polish-pass scope. |
| **T6 `_REMINDER_TONES` module-local vs `config.py`** | `reviews/phase-5-tier6-review.md` Finding #1 | Open ℹ️ | **Track under C3** (same shape — page-local UI vocabulary that *might* belong in `config.py`). No separate carry-over. |
| **T6 days-since-asked = max-across-group** | `reviews/phase-5-tier6-review.md` Finding #3 | Open ℹ️ | **Resolved by-design.** DESIGN §8.4 line 638 was silent on per-position vs single-summary; the implementer's max-across-group choice is documented in the code comment and accepted by the T6 review. No action. |
| **T6 `urlparse`/`parse_qs` imported inside `_decode_mailto`** | `reviews/phase-5-tier6-review.md` Finding #4 | Open ℹ️ | **Test-helper cosmetic.** No action; folds into a future `tests/helpers.py` extraction if it ever lands. |

---

## Verbatim render dumps (cohesion evidence)

The four AppTest probes below are the source of truth for every "verified verbatim" claim above. The probe script is `/tmp/phase5_cohesion_probe.py`; the raw output is `/tmp/phase5_cohesion_probe.out`. Both are session-local; the dumps below are the load-bearing slices.

### Applications page · POPULATED DB · no selection

```
=== TITLE ===
  'Applications'

=== DATAFRAMES ===
  columns=['Position', 'Institute', 'Applied', 'Recs', 'Confirmation', 'Response', 'Result']  rows=2
    {'Position': 'Postdoc in CS / ML',         'Institute': 'MIT CSAIL', 'Applied': 'Apr 13', 'Recs': '—', 'Confirmation': '✓ Apr 15', 'Response': '—', 'Result': 'Pending'}
    {'Position': 'Postdoc in Biostatistics',   'Institute': 'Stanford',  'Applied': 'Apr 23', 'Recs': '—', 'Confirmation': '✓ Apr 24', 'Response': '—', 'Result': 'Pending'}

=== SELECTBOXES ===
  key='apps_filter_status'  label='Status'  value='Active'
  options=['Active', 'All', 'Saved', 'Applied', 'Interview', 'Offer', 'Closed', 'Rejected', 'Declined']

=== EXCEPTION ===
  has_exception=False
```

Cross-checks: 7-column table per DESIGN §8.3 ✓ · `Mon D` date format ✓ · em-dash NULL glyph ✓ · status filter shows bare labels (sentinel-stripped) ✓ · script ran clean.

### Applications page · POPULATED DB · row 0 selected

```
=== SUBHEADERS ===
  'MIT CSAIL: Postdoc in CS / ML · Interview'

=== MARKDOWN ===
  'All recs submitted: —'
  '**Interviews**'
  '**Interview 1**'

=== BUTTONS ===
  apps_detail_submit            'Save'
  apps_interview_1_save         'Save'
  apps_interview_1_delete       '🗑️ Delete Interview 1'
  apps_add_interview            'Add another interview'

=== SELECTBOXES (detail card) ===
  apps_response_type   options=['—', 'Acknowledgement', 'Screening Call', 'Interview Invite', 'Rejection', 'Offer', 'Other']
  apps_result          options=['Pending', 'Offer Accepted', 'Offer Declined', 'Rejected', 'Withdrawn']
  apps_interview_1_format  options=['—', 'Phone', 'Video', 'Onsite', 'Other']

=== DATE INPUTS (detail card) ===
  apps_applied_date           value=2026-04-13
  apps_confirmation_date      value=2026-04-15
  apps_response_date          value=None
  apps_result_notify_date     value=None
  apps_interview_1_date       value=2026-05-11

=== CHECKBOX ===
  apps_confirmation_received  value=True

=== TEXT AREAS ===
  apps_interview_1_notes      value='Faculty panel'
  apps_notes                  value=''

=== EXCEPTION ===
  has_exception=False
```

Cross-checks: detail-card header reuses `{institute}: {position_name} · {STATUS_LABELS[raw]}` shape ✓ · `STATUS_LABELS['INTERVIEW'] == 'Interview'` (sentinel-stripped) ✓ · all `*_*_date` widgets pre-seeded from DB via `_coerce_iso_to_date` ✓ · response_type / interview_format selectboxes lead with `—` per the `[None, *VALUES]` + em-dash `format_func` precedent ✓ · per-row interview block render with Save + Delete (T3-rev-B per-row architecture).

### Recommenders page · POPULATED DB · no selection

```
=== TITLE ===           'Recommenders'

=== SUBHEADERS ===
  'Pending Alerts'
  'All Recommenders'

=== MARKDOWN (Pending Alerts cards) ===
  '**⚠ Dr. Smith** (PhD Advisor)
   - Stanford: Postdoc in Biostatistics (asked 14d ago, due May 18)
   - Princeton: Postdoc in Bayesian Inference (asked 14d ago, due May 25)'

=== EXPANDERS ===
  'LLM prompts (2 tones)'
  'Add Recommender'

=== CODE BLOCKS ===
  language='text'  first_line='Please draft a gentle reminder email to my recommender about pending letters of recommendation.'  total=420 chars
  language='text'  first_line='Please draft a urgent reminder email to my recommender about pending letters of recommendation.'  total=420 chars

=== LINK BUTTONS ===
  'Compose reminder email'  url='mailto:?subject=Following%20up%3A%20letters%20for%202%20postdoc%20applications&body=...'

=== DATAFRAMES (All Recommenders) ===
  columns=['Position', 'Recommender', 'Relationship', 'Asked', 'Confirmed', 'Submitted']  rows=3
    {'Position': 'MIT CSAIL: Postdoc in CS / ML',         'Recommender': 'Dr. Jones', 'Relationship': 'Committee Member',  'Asked': '2026-05-01', 'Confirmed': '—', 'Submitted': '—'}
    {'Position': 'Stanford: Postdoc in Biostatistics',    'Recommender': 'Dr. Smith', 'Relationship': 'PhD Advisor',       'Asked': '2026-04-19', 'Confirmed': '—', 'Submitted': '—'}
    {'Position': 'Princeton: Postdoc in Bayesian Inference','Recommender': 'Dr. Smith', 'Relationship': 'PhD Advisor',     'Asked': '2026-04-19', 'Confirmed': '—', 'Submitted': '—'}

=== SELECTBOXES ===
  recs_add_position        options=['MIT CSAIL: Postdoc in CS / ML', 'Stanford: Postdoc in Biostatistics', 'Princeton: Postdoc in Bayesian Inference']
  recs_add_relationship    options=['PhD Advisor', 'Committee Member', 'Collaborator', 'Postdoc Supervisor', 'Department Faculty', 'Other']
  recs_filter_position     options=['All', ...]
  recs_filter_recommender  options=['All', 'Dr. Jones', 'Dr. Smith']

=== EXCEPTION ===
  has_exception=False
```

Cross-checks: Pending Alerts groupby produces ONE card for Dr. Smith (2 positions); Dr. Jones is below the 7-day `RECOMMENDER_ALERT_DAYS` threshold and correctly does NOT surface a card (only Dr. Smith's data feeds the Compose URL: `subject=...for 2 postdoc applications` matches the 2 owed positions) ✓ · LLM-prompts expander label `LLM prompts (2 tones)` ties to `len(_REMINDER_TONES)` ✓ · 2 code blocks per the locked tones (gentle, urgent) ✓ · All Recommenders shows all 3 rows (Dr. Jones surfaces in this surface even though he's not in alerts — by-design, the working table is filter-agnostic) ✓ · recommender filter dedupes Dr. Smith to one option ✓ · Confirmed / Submitted columns render `'—'` for NULL via `_format_confirmed` / `_safe_str_or_em` ✓ · script ran clean.

### Recommenders page · POPULATED DB · row 0 selected (Dr. Jones)

```
=== MARKDOWN ===
  '**Editing: Dr. Jones**'

=== BUTTONS ===
  recs_edit_submit   'Save Changes'
  recs_edit_delete   'Delete'

=== SELECTBOXES ===
  recs_edit_confirmed   options=['—', 'No', 'Yes']

=== DATE INPUTS ===
  recs_edit_asked_date         value=2026-05-01
  recs_edit_submitted_date     value=None
  recs_edit_reminder_sent_date value=None

=== CHECKBOX ===
  recs_edit_reminder_sent  value=False

=== TEXT AREAS ===
  recs_edit_notes  value=''

=== EXCEPTION ===
  has_exception=False
```

Cross-checks: edit-card header `'**Editing: Dr. Jones**'` renders via `st.markdown` (Finding #5 — primitive divergence vs Applications detail-card header which uses `st.subheader`); `recs_edit_confirmed` selectbox uses the locked `[None, 0, 1]` options rendered as `[—, No, Yes]` via `format_func` (same em-dash-leading idiom as the Applications-page selectboxes for `response_type` / `interview_format`); date pre-seed via `_coerce_iso_to_date` round-trips correctly; Reminder-sent checkbox pre-seeded `False` per `bool(_rec_row.get("reminder_sent") or 0)`.

### Applications page · EMPTY DB

```
=== TITLE ===           'Applications'
=== INFO MESSAGES ===   'No applications match the current filter.'
=== SELECTBOXES ===     apps_filter_status='Active' (full options preserved)
=== EXCEPTION ===       has_exception=False
```

Cross-checks: empty-state `st.info` with present-tense "No X match" copy ✓ · filter widget survives empty data (so the user can switch to "All" to confirm the DB really is empty) ✓ · script clean.

### Recommenders page · EMPTY DB

```
=== TITLE ===           'Recommenders'
=== SUBHEADERS ===      'Pending Alerts'  ·  'All Recommenders'
=== INFO MESSAGES ===   'No pending recommenders.'
=== DATAFRAMES ===      columns=['Position', 'Recommender', 'Relationship', 'Asked', 'Confirmed', 'Submitted']  rows=0
=== EXPANDERS ===       'Add Recommender'
=== BUTTONS ===         recs_add_submit='+ Add Recommender'
=== SELECTBOXES ===
  recs_add_position        options=[]   value=None    ← empty positions list
  recs_filter_position     options=['All']
  recs_filter_recommender  options=['All']
=== EXCEPTION ===       has_exception=False
```

Cross-checks: Pending Alerts empty-state `st.info("No pending recommenders.")` ✓ · All Recommenders empty 6-col dataframe (locked column contract holds, gotcha #16) — but **NO empty-state info callout** under the All Recommenders subheader (Finding #1) · Add Recommender expander still renders (Finding #3 — could detect empty positions and surface a helpful message instead) · script clean.

---

## Junior-engineer Q&A

### Q1 — Why is the All-Recommenders empty-state finding 🟡 polish rather than 🟠 must-fix?

**A.** Three reasons hold the severity below 🟠. First, the locked column contract (six columns, gotcha #16) is preserved on empty — the table renders structurally, just with zero rows; the user is not seeing a broken UI, they are seeing an empty UI. Second, the directly-adjacent Pending Alerts panel DOES carry the empty-state info message, so a user staring at a wiped DB sees `"No pending recommenders."` two-thirds up the screen and can infer the All-Recommenders blank below is the same story. Third, the cohesion gap is asymmetric in only one direction — every panel-with-data SHOULD have an empty branch, and one panel doesn't. Phase 7 polish-tier is the right home: the fix is one-line, but it lands cleanest as part of a systematic empty-state sweep across all pages rather than a one-off. If a user hits this in the meantime they get correct (if visually thin) UI, not broken UI.

### Q2 — The All-Recommenders table renders Asked dates as ISO `2026-05-01` while everywhere else in the project uses `Mon D` (`May 1`). Is the ISO form a bug, a kept-by-design choice, or an oversight?

**A.** It is most likely an oversight that has now hardened into a defensible kept-by-design choice. The T5 implementation projected the joined frame's TEXT cells through `_safe_str_or_em` directly without a `Mon D` formatter pass, and no T5 review caught it. The defensibility argument: All-Recommenders is the page's *working data table*, not a presentation surface. ISO `YYYY-MM-DD` is sortable lexicographically, machine-readable, and unambiguous about year — useful properties for a working table that the user might paste into a spreadsheet. The Pending Alerts panel above is presentation-only and the brevity of `Mon D` reads better there. If we lock this asymmetry in, it should be DESIGN-amended; if we want cohesion, a `_format_date_short` helper applied to the All-Recommenders projection is a 4-line fix. Phase 7 picks. Either way, the v0.6.0 tag is not blocked: the data is correct, the dates are unambiguous, and no test pins the format either way.

### Q3 — The `recs_add_position` selectbox renders `options=[]` and `value=None` when the DB has no positions. Couldn't the user submit and trip an error?

**A.** They can submit, and the handler is built to handle it — `_pos_label not in _position_label_to_id` triggers `st.error("Pick a position before adding a recommender.")`, no DB write, sentinels survive for retry. The fix in Finding #3 is purely UX: a user shouldn't be presented with a form they can't complete. The cheapest gate is `if not _position_label_to_id: st.info("Add a position on the Opportunities page first."); else: <render expander>`. The defensive `st.error` then becomes belt-and-suspenders for the "user opened the page in two tabs and deleted the last position in tab 1" race, which is exactly the kind of edge case `st.error` is designed for. Two-layer defence is right; the current implementation just skips the first layer.

### Q4 — `is_all_recs_submitted(pid)` returns vacuous-true for zero recs. Why does the cohesion-smoke seed never expose this?

**A.** The seed has at least one un-submitted recommender on every position that's far enough along to surface in the Active filter (Stanford has Dr. Smith asked-not-submitted, MIT CSAIL has Dr. Jones asked-not-submitted), so the Recs column shows `'—'` for both seeded rows. The vacuous-true case fires when a position has zero recommender rows AND is in the Active filter band (i.e. status = APPLIED or INTERVIEW or OFFER) — a scenario where the user has applied without any letters tracked, which the database layer correctly reads as "all the letters that were tracked are submitted (which is none of them)". DESIGN D23 commits the project to this reading because the alternative ("show ✗ for zero recs") would mis-fire on positions where letters truly aren't required (some industry post-doc fellowships skip them). The Phase 4 cohesion-smoke explicitly accepted the same vacuous-true reading on the dashboard's KPI; Phase 5 inherits the contract. If Phase 7's polish pass wants a third state (`✓` / `—` / `?`) it would need both schema + DESIGN backing.

### Q5 — Three carry-overs (C2, C3, T6 polish) deferred to Phase 7. Don't deferrals accumulate into a debt heap?

**A.** Two checks against the heap. First, every deferral here is logged in `TASKS.md` "Code carry-overs" / "Phase 7 / v1.0-rc" with a specific home — none of them are floating. Second, the deferred items are all genuinely cosmetic or scope-creep; the alternative to deferring would be either expanding the v0.6.0 scope (and pushing the tag) or shipping a one-off fix-PR that bundles unrelated edits. Both are worse than letting Phase 7 batch the polish into a single coherent pass. The signal to revisit is when Phase 7 starts: at that point the deferred list becomes the input checklist.

### Q6 — Why is Phase 5 close-out a single doc instead of the three-deliverable structure Phase 4 used (cohesion smoke + screenshots + 7-findings review)?

**A.** Phase 4 had three deliverables because it had three distinct outputs to coordinate — the cohesion-smoke audit was harness-only, the responsive-width PNGs needed the user's browser, and the 7-findings inline review captured per-tier polish that didn't fit the cohesion-smoke schema. Phase 5 has none of those splits: no responsive-width capture is in scope (Phase 7 T5 owns that, deferred to v0.8.0), and the per-tier polish is already captured in the six tier-review docs (`phase-5-tier1-review.md` … `phase-5-tier6-review.md`) — T7 just triages the carry-overs they each filed. Folding into one doc keeps the orchestrator's load light and reduces the cross-doc cite churn.

---

## v0.6.0 tag preparation (orchestrator checklist)

The remaining T7 mechanics — once this doc lands — are pure mechanical close-out:

1. **CHANGELOG.md split** — `[Unreleased]` → `[v0.6.0] — 2026-05-04 — Phase 5: Applications + Recommenders pages` at the boundary commit `6993ea9` (T6 merge), mirroring the precedent commit `db383e3` that did the same split for v0.5.0. Phase 5 entries (T1 / T2-A / T2-B / T3-A / T3-B / T3-rev-A / T3-rev-B / T4 / T5 / T6 / RELATIONSHIP-rename) collapse to one-line bullets pointing at commit hashes + review docs (per GUIDELINES §14.4 short-form). Pre-Phase-5 essays in `[Unreleased]` (the GUIDELINES §14 / docs/adr / wireframes-drift cleanup work) move under `[v0.6.0]` Changed.
2. **Pre-tag gates** — re-run `ruff check .`, `pytest tests/ -q`, `pytest -W error::DeprecationWarning tests/ -q`, status-literal grep. All four must be green at the tag commit.
3. **Tag** — `git tag -a v0.6.0 -m "Phase 5 — Applications + Recommenders pages"` with the annotation listing the six headline tier deliverables. Push.
4. **TASKS.md / AGENTS.md final flip** — T7 ✅; main HEAD line bumped; Immediate-task block replaced with the next phase's task (Phase 6 T1 — `write_opportunities()` exports generator).
5. **Recently-done entry** — one bullet for the v0.6.0 tag close-out.

---

_Written 2026-05-04 as the Phase 5 close-out doc per the
`reviews/phase-4-finish-cohesion-smoke.md` precedent. Verbatim renders
captured via `/tmp/phase5_cohesion_probe.py` against `main` HEAD
`60789e6`. Suite green at 777 passed + 1 xfailed under both pytest
gates. Verdict: Approve `v0.6.0` tag._
