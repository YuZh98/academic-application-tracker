# BDD User Scenarios — UX Improvement Plan v0.14.0 → v0.16.0

**Source plan:** `UX_Improvement_Plan_2026-05-22.md`
**Status:** v1 — acceptance contracts for planned releases
**Format:** Gherkin (Given / When / Then). Each scenario maps to one
or more pytest tests under `tests/test_planned_v0_XX_*.py`.

The personas referenced here are the three from the field study report
(`UX_Field_Study_Report_2026-05-22.pdf` §3):
**P1 Aisha** (life-sci postdoc, ~40 positions, 4 recommenders),
**P2 James** (humanities TT, ~22 positions, 5 recommenders),
**P3 Wei** (CS mixed, ~51 positions, 3 recommenders).

---

## v0.14.0 — close-out

### Feature: Symmetric R2 cascade on `delete_interview` (B1)

> *Persona context:* P3 filed this as a GitHub issue on Nov 4 against
> `database.py:707–719`. Forward cascade exists at `database.py:629`;
> reverse path is missing.

**Scenario: Deleting the only interview row retracts `[INTERVIEW]` status**
- *Given* a position promoted to `[INTERVIEW]` by adding one interview row
- *When* that interview row is deleted via `delete_interview`
- *Then* the position status returns to `[APPLIED]`
- *And* the markdown export reflects the demotion

**Scenario: Deleting one of many interview rows does not retract status**
- *Given* a position with two interview rows in `[INTERVIEW]` status
- *When* one interview row is deleted
- *Then* the position status stays `[INTERVIEW]`
- *And* the surviving interview row is unaffected

**Scenario: Reverse cascade does not fire for non-INTERVIEW positions**
- *Given* a position in `[OFFER]` with one interview row
- *When* the interview row is deleted
- *Then* the position status stays `[OFFER]` — the cascade is symmetric
  only with respect to `[APPLIED]↔[INTERVIEW]`, matching the forward
  cascade's narrow precondition

### Feature: Schema-UI binding pin (B3, partial)

**Scenario: Every nullable `positions` column reachable from the UI**
- *Given* the live `positions` schema in `database.py`
- *When* the binding inspector enumerates non-housekeeping columns
  (i.e. excludes `id`, `created_at`, `updated_at`, `status`, plus the
  config-managed `req_*` / `done_*` families)
- *Then* every remaining column appears as a widget key in either
  Quick-Add (`pages/1_Opportunities.py`) or Edit panel
- *xfail until v0.15.0 R0b ships the wireup*

---

## v0.15.0 — recommender refactor

### Feature: Global recommender entity + `position_recommenders` join (R0a)

> *Persona context:* P1 (4 writers × 40 positions = 160 manual rows) and
> P2 (5 × 22 = 110) both abandoned the Recommenders page on Day 1. R0a
> makes recommenders a first-class entity so per-person state lives
> per-person.

**Scenario: Onboarding cost is additive, not multiplicative**
- *Given* a fresh database
- *When* P1 adds 4 letter writers globally and then 40 positions
- *And* assigns each writer to all 40 positions
- *Then* the **writer creation cost** is 4 form submissions
  (not 4 × 40 = 160)
- *And* the assignment matrix is reachable via a single multi-select
  control per position OR a single multi-select per writer

**Scenario: Editing one writer's email propagates everywhere**
- *Given* a writer with email `a@x.edu` linked to 3 positions
- *When* P2 updates the email to `b@x.edu` on the global "My letter
  writers" tab
- *Then* all 3 Compose-Reminder mailtos on the Assignments tab use
  `b@x.edu`
- *And* no per-position edit is required

**Scenario: Deleting a position preserves the global writer**
- *Given* a position with 2 assigned writers
- *When* the position is deleted
- *Then* both writers remain in the global table
- *And* the join rows for the deleted position are gone

**Scenario: Migration deduplicates case-folded recommender names**
- *Given* a legacy DB with rows
  `[("Smith", pos1), ("smith", pos2), ("Smith", pos3)]`
  in the per-position `recommenders` table
- *When* `init_db()` runs the v0.15.0 migration
- *Then* exactly one global `recommenders` row exists for "Smith"
- *And* three `position_recommenders` join rows reference it

**Scenario: Legacy table retained for one release as rollback surface**
- *Given* the v0.15.0 migration has run
- *When* the user inspects the schema
- *Then* both `recommenders_legacy` (renamed) and the new
  `recommenders` + `position_recommenders` exist
- *And* the legacy table is read-only (no writes after migration)
- *And* v0.16.0 will drop `recommenders_legacy` physically

**Scenario (negative): Deleting an assigned global writer is blocked**
- *Given* a global writer with 3 active assignments
- *When* the user clicks Delete on the global tab without a confirm
  dialog
- *Then* the delete is blocked with `st.error` naming the 3 positions
- *And* cascade-delete requires a separate `@st.dialog` confirm

**Scenario (negative): Mid-migration crash leaves no partial state**
- *Given* the migration fails between backfill and legacy-table rename
  (simulated `IOError`)
- *When* the app restarts and calls `init_db()` again
- *Then* either the legacy table holds every row and new tables are
  empty (retry-clean), or the new tables hold every row (success) —
  never a mixed state with some rows in both

**Scenario (state preservation): Tab switch keeps row selection**
- *Given* a row is selected on the Assignments tab
- *When* the user switches to "My letter writers" and back
- *Then* the selection persists (per `_skip_table_reset` contract,
  dev-notes gotcha #11)
- *And* no `pandas.NaN` leaks into widget state (`fillna("")` before
  any `groupby` on join queries, gotcha #13)

### Feature: Assignments tab visual contract (R0a UI)

**Scenario: Default grouping is per-recommender, not per-position grid**
- *Given* P2 with 5 writers × 22 positions
- *When* P2 opens the Assignments tab
- *Then* the default view shows **5 expandable cards** (one per
  writer), each listing their assigned positions
- *And* the visible row count is N (writers), not N×M (writers ×
  positions) — this is the visual lever, not just the data lever
- *And* a per-position view is reachable behind a toggle for users
  who prefer the old shape

### Feature: Schema-UI wireup (R0b)

**Scenario: All 10 orphan columns reachable from Edit panel**
- *Given* a position created via Quick-Add with `location="Stanford"`,
  `source="academic-jobs-online"`, `portal_url="https://x.edu/apply"`
- *When* the user opens the Edit panel
- *Then* all 10 previously-orphan columns (`location`, `field`,
  `deadline_note`, `stipend`, `work_auth`, `work_auth_note`,
  `full_time`, `source`, `mentor`, `point_of_contact`, `portal_url`,
  `keywords`, `description`, `num_rec_letters`, `reference_code`) are
  visible and editable
- *And* round-trip Save preserves every value

**Scenario: Quick-Add stays inside the 6-field discipline (S6)**
- *Given* R0b ships three short-string columns into Quick-Add
  (`location`, `source`, `portal_url`)
- *When* a five-line BDD walkthrough times the capture-a-new-posting
  task
- *Then* the median walkthrough completes in ≤30 seconds (S6 bar)
- *And* long free-text columns (`description`, `keywords`) stay in
  Edit only

---

## v0.16.0 — bulk + settings

### Feature: Bulk operations in Opportunities table (R1a)

**Scenario: Bulk status flip fires one R1 cascade per selected row**
- *Given* 10 positions in `[SAVED]`
- *When* P3 selects 5 of them and clicks "Mark applied"
- *Then* 5 R1 cascades fire in one batch (`applied_date` set,
  status promoted)
- *And* the markdown export reflects exactly those 5 transitions
- *And* the other 5 positions remain in `[SAVED]`

**Scenario: Bulk requirement-set across selected rows**
- *Given* 7 positions selected, each missing `req_cv`
- *When* the user picks "Set CV required" from the bulk-action menu
- *Then* all 7 rows have `req_cv="Yes"` in the next render
- *And* materials readiness recomputes for each

**Scenario: Bulk mark-submitted across positions (depends on R0a join)**
- *Given* a global writer with 3 active assignments where
  `submitted_date IS NULL`
- *When* the user marks the writer submitted from the global
  Recommenders tab
- *Then* all 3 join rows update with the same `submitted_date`
- *And* materials-readiness recomputes for each affected position

**Scenario (state preservation): Bulk action keeps table selection**
- *Given* 5 rows selected
- *When* a bulk action completes and the page reruns
- *Then* the same 5 rows remain selected (per `_skip_table_reset`,
  gotcha #11)
- *And* the table does not scroll to the top

### Feature: In-UI settings page (R1b)

**Scenario: Threshold change re-bands the Upcoming panel**
- *Given* `DEADLINE_ALERT_DAYS` defaults to 7
- *When* the user sets it to 3 in Settings and reloads the dashboard
- *Then* the Upcoming panel urgency banding uses 3 days, not 7
- *And* a JSON override file persists under the project data dir
- *And* `config.py` import-time invariants (S5) still hold

**Scenario: Vocabulary additions are append-only**
- *Given* the user opens the Settings page
- *When* the user tries to remove `[APPLIED]` from `STATUS_VALUES`
- *Then* the action is blocked with a clear message naming the rows
  that currently hold that status
- *And* appending a new status (e.g. `[GHOSTED]`) succeeds

**Scenario: Invalid threshold rejected at the boundary**
- *Given* the user enters `DEADLINE_ALERT_DAYS = -1`
- *When* Save is clicked
- *Then* `st.error("DEADLINE_ALERT_DAYS must be ≥ 1")` is shown
- *And* the override file is not written
- *And* the in-memory value is unchanged

---

## Coverage matrix

| Item | Scenarios | Test file |
|---|---|---|
| B1 reverse cascade | 3 | `tests/test_planned_v0_14.py::TestB1ReverseCascade` |
| B3 schema-UI pin | 1 | `tests/test_planned_v0_14.py::TestB3SchemaUiPin` |
| R0a recommender entity | 8 (5 positive + 2 negative + 1 state) | `tests/test_planned_v0_15.py::TestR0aRecommenderEntity` |
| R0a Assignments visual | 1 | `tests/test_planned_v0_15.py::TestR0aAssignmentsVisual` |
| R0b schema-UI wireup | 3 (Quick-Add round-trip + S6 cap + Edit-panel round-trip) | `tests/test_planned_v0_15.py::TestR0bSchemaUiWireup` |
| R1a bulk ops | 7 (status flip + req-set + writer-bulk[xfail R0a] + UI button E2E + state-pres + 2 negative paths) | `tests/test_planned_v0_16.py::TestR1aBulkOps` |
| R1b in-UI settings | 4 (threshold re-band + append-only + page UI E2E + invalid-threshold) | `tests/test_planned_v0_16.py::TestR1bSettings` |

Each test file pins these acceptance contracts via `@pytest.mark.xfail
(strict=False, reason=...)` so the suite stays green today; when the
implementation lands, the xfail marker is removed in the same PR that
makes the test pass.
