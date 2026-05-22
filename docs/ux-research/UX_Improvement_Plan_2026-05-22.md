# UX Improvement Plan — 2026-05-22

**Source:** `docs/ux-research/UX_Field_Study_Report_2026-05-22.pdf`
**Codebase ref:** `feat/ui-redesign-v0.14.0` @ `2ded3ba`
**Status:** v3 final — two iterations applied + UX-manager + teammate nits folded
**Author of record:** team lead (this session)

---

## 1. Reading of the report (what we believe and why)

The field study spans three synthesised personas over a 12-week cycle, with
file:line citations verified against current source (Appendix A). The
load-bearing claims we are acting on:

- **Churn is structural, not cosmetic.** Two of three personas operate at
  ~50% intended scope and maintain a parallel Google Sheet. The dashboard
  the user opens daily is silently incomplete because the data entry tax
  on the recommender model blocked them from completing it.
- **One root cause dominates.** `recommenders` is modelled per-position
  (`database.py:135–148`). N recommenders × M positions = N·M manual rows
  on Day 1. This single decision drove both near-quit moments in P1 and P2.
- **One real defect.** `delete_interview` (`database.py:707–719`) has no
  reverse cascade — orphan `[INTERVIEW]` status when the only interview
  row on a position is deleted. Verified, not just claimed.
- **Three feature-completion gaps.** 10 nullable `positions` columns
  unused in Quick-Add (`database.py:77–94`); no `email` column on
  `recommenders` so the Compose-Reminder mailto has an empty `To`;
  silent `[SAVED]→[APPLIED]` promotion has no toast on the Applications
  page.
- **What is working is non-trivial and worth defending.** Editorial
  identity, the Upcoming-deadlines panel + urgency banding, markdown
  exports on every write, the `config.py` import-time invariants, and
  the 6-field Quick-Add are the reasons all three personas stayed at all.
  Any redesign that risks degrading these is out of scope by default.

We are accepting the report's prioritisation (P0 / P1 / P2) and shipping
order. Where we diverge, it is in **batching** — see §3.

### 1.5 Persona-impact honesty

The v0.15.0–v0.16.0 sequence moves **P1 and P3** out of the 50% scope
plateau. **P2 only moves partially** — his Day-1 abandonment cause
(N×M recommender entry) is closed by R0a, but his Month-2 churn
drivers are the materials-versioning gap (R2a) and the Nov-22 manual
backup workaround (R2d), both currently logged for v0.17.0+. This is
a deliberate trade we are flagging now rather than discovering when
P2 stays at 50% after v0.16.0 ships. If reviewer pushback reorders
the queue, R2d (half-day) is the cheapest single concession.

## 2. What this plan is NOT

So we save reviewer time:

- We are **not** adding browser extension, AI cover-letter, mobile-first
  UX, multi-device sync, or cloud auth. Those are explicit non-goals in
  `DESIGN §1.3` and the report agrees.
- We are **not** rewriting the four-layer architecture (`config →
  database → ui → pages`). The architecture earned an upstream PR from
  P3; we extend it, we do not replace it.
- We are **not** chasing the grouped reminder mailto (R2e) — a
  five-second wall-clock win for a workflow already covered by R0a's
  per-recommender Assignments view. We **are** noting that the in-app
  backup button (R2d) is genuinely contested: the report rates it
  high-severity for P2, who manually copied `postdoc.db` on Nov 22
  after realising markdown export does not protect his full state.
  We currently keep R2d out of the planned releases because it is a
  half-day item the user can replicate with one shell command today —
  but if the v0.15.0 audit surfaces sustained P2-style trust shake,
  R2d slots into v0.16.0 with no plan disruption.
- We are **not** shipping responsive layout (R2b) inside this plan. The
  report classifies AAT as desktop-first by design; the mobile breakage
  is a P1 persona-specific friction, not a P0 churn-blocker. Logged for
  v0.17.0.

## 3. Plan — three shippable releases

Each entry: **WHAT** (one line), **WHY** (the churn lever it pulls or
the bug it closes), and **HOW** (one paragraph, surgical). BDD+TDD
cadence is `test:` (failing acceptance / unit) → `feat:` or `fix:`
(green) → `chore:` (rollup) per `GUIDELINES §11`.

**Two deviations from report §16 we are taking responsibility for:**

1. **B2 (recommender email) moves out of v0.14.0 into v0.15.0 R0a.**
   The report puts B2 in the v0.14.0 fix batch. We move it because
   the email column architecturally belongs on the new global
   `recommenders` table, not on the soon-to-be-replaced per-position
   one. Shipping it in v0.14.0 means writing a migration we throw away
   four weeks later. Cost of waiting: one more release with an empty
   mailto `To` field — the same state we have today.
2. **B3 (schema-UI wireup) splits across v0.14.0 and v0.15.0.** The
   pinning test (which asserts every nullable column has a UI binding)
   lands in v0.14.0 as `xfail`; the actual wireup ships in v0.15.0
   R0b. This is the §7 "no rule without enforcement" pattern from
   `~/.claude/CLAUDE.md` — codifies the rule now so the wireup PR
   simply removes the xfail.

Net effect: v0.14.0 is no longer a strict B1+B2+B3 batch; it's a
B1+B3-pin batch. Both deviations are visible above so the audit gate
can challenge them rather than discovering them in the diff.

### v0.14.0 close-out — two items, ~half-day implementation

The current branch is the right place for the verified bug that does
not require a schema migration, plus the enforcement-only pinning
test. Ship before opening the v0.14.0 PR for merge.

- **B1 — Reverse cascade on `delete_interview` (R0c).**
  *Why:* Real defect. After deleting the only interview row, the position
  keeps `[INTERVIEW]` status — the dashboard funnel lies. P3 filed a
  GitHub issue for this himself.
  *How:* Inside the existing `_connect()` block at `database.py:707–719`,
  after the `DELETE`, check whether any interviews remain for that
  `application_id`; if zero **and** current status is
  `config.STATUS_INTERVIEW`, demote to `config.STATUS_APPLIED`. New
  acceptance test in `tests/test_database.py` pins the symmetry against
  the existing `add_interview` cascade test.

- **B3 (partial) — Pinning test for "every nullable positions column
  has a UI binding".**
  *Why:* The wireup itself (R0b) ships in v0.15.0, but the *pinning*
  test belongs here so we cannot regress.
  *How:* Add `tests/test_rules.py::test_positions_schema_ui_binding`
  that inspects `database.py` schema and asserts every non-`_at` column
  is referenced in either Quick-Add or the Edit panel. Mark `xfail`
  (`strict=False`) with reason linking the **v0.15.0 R0b follow-on
  issue** (tracked id placeholder — must be filled before the v0.14.0
  PR opens, per the universal §7 anti-pattern guard against untracked
  xfails). The same PR that ships R0b removes the xfail.

*Dropped from this plan as trivial — will land in v0.14.0 hygiene
without a line item:* B4 toast on `[SAVED]→[APPLIED]` promotion
(one-line addition mirroring the existing R2 toast pattern at
`pages/2_Applications.py:645`).

**B2 is deferred** to v0.15.0 where it belongs — the email column ships
together with the recommender entity refactor (R0a) since both touch
the same migration.

### v0.15.0 — the recommender refactor (the big one)

This is the single highest-leverage release in the backlog. It is also
the only entry in this plan that requires real architectural care: it
changes the schema shape, the data model the user reasons about, and
the join behaviour of the dashboard alert panel. Multi-week, not
multi-day.

- **R0a — Recommenders as a global first-class entity.**
  *Why:* The 4 × 40 = 160 / 5 × 22 = 110 manual entries on Day 1 are
  *the* churn driver. Promote `recommenders` to a global table with
  `(id, name, email, relationship, asked_date, confirmed, notes)`, and
  add a join table `position_recommenders(position_id, recommender_id,
  submitted_date, reminder_sent, reminder_sent_date)` — per-position
  state stays per-position, per-person state becomes per-person.
  *How:* `config.py` invariants extend to cover the new join table on
  Day 1 (per Appendix A, S5 is what made P3 contribute upstream — we
  preserve the property). Migration outline, in the same shape as the
  existing `interviews_existed_pre_create` pattern at `database.py:113`:
  (1) detect legacy schema, (2) create new global + join tables,
  (3) backfill — case-folded dedup of `recommender_name` into global,
  per-position rows become join entries with their existing
  `submitted_date` / `reminder_*` columns, (4) keep the legacy
  `recommenders` table intact for **one release** as a rollback
  surface; drop it physically in v0.16.0. Every recommender + join
  write site must call `exports.write_all()` to preserve S3 (markdown
  export as recovery surface) — `exports/RECOMMENDERS.md` itself needs
  a schema-aware rewrite to render per-writer rather than per-position. Recommenders page becomes
  two tabs: **My letter writers** (global CRUD) + **Assignments**. The
  **Assignments tab defaults to a per-recommender grouping** — for P1
  that is 4 expandable cards, each listing their N assigned positions
  — *not* a per-position grid. This is the visual contract that
  matters: P2 abandoned the page because of the N×M visual tax, not
  just the data tax; the new default reduces the visible row count
  from N×M to N. A per-position view remains available behind a
  toggle for users who prefer the old shape.
  *BDD acceptance scenarios:*
  - *Given* a fresh DB, *when* I add 4 letter writers and then 40
    positions, *then* I have performed exactly 4 + 40 = 44 writer-
    assignment clicks (not 160).
  - *Given* a writer with email `a@x` linked to 3 positions, *when*
    I update the email to `b@x` on the global tab, *then* all 3
    positions' Compose-Reminder mailtos use `b@x`.
  - *Given* a position with 2 assigned writers, *when* I delete the
    position, *then* both writers remain in the global table.
  - *Given* a legacy DB with `[("Smith", pos1), ("smith", pos2),
    ("Smith", pos3)]`, *when* migration runs, *then* one global
    "Smith" row exists with three join entries.

  *Negative + state-preservation scenarios (per GUIDELINES §9):*
  - *Given* a global recommender with 3 active assignments, *when* I
    try to delete them from the global tab, *then* the delete is
    blocked with a clear error naming the 3 positions; cascade-delete
    is a separate explicit confirm dialog. (Policy choice surfaced
    here so reviewers can challenge.)
  - *Given* a mid-migration crash (e.g. simulated IOError between
    backfill and legacy-table rename), *when* the app restarts,
    *then* either the legacy table is intact and migration retries
    cleanly, or the new tables hold every legacy row — never both
    partial.
  - *Given* the two-tab Recommenders page with a selected row,
    *when* I switch tabs and back, *then* the selection and
    `_skip_table_reset` contract holds (dev-notes gotcha #11) and
    no row collapses. Pandas `fillna("")` is applied before any
    `groupby` on join-query nullable columns (gotcha #13).

- **R0d — Recommender `email` column + populated mailto (subsumed).**
  *Why:* B2 in the report, but architecturally part of R0a — the email
  belongs on the global recommender, not the per-position row.
  *How:* Falls out of R0a's new schema. The mailto code in
  `pages/3_Recommenders.py:142` reads `recommender.email` directly
  after the refactor. Tests: pinning test that asserts mailto `To`
  field is non-empty when any letter writer has an email.

- **R0b — Wire the 10 unused `positions` columns into Quick-Add and
  Edit.**
  *Why:* Half the schema exists only on disk; P1 said it explicitly
  ("They built half the schema and then forgot to wire it up"). The
  cost of fixing this is small once we are already touching the
  Opportunities page, and it closes the `xfail` pinning test from
  v0.14.0.
  *How:* Audit the 6-field Quick-Add against the schema. Add the 10
  missing columns to the **Edit panel** by default; promote three to
  Quick-Add only if they are short-string ones that do not bloat the
  form (`location`, `source`, `portal_url`). The 6-field discipline (S6
  in the report) is a strength we are explicitly defending — long
  free-text fields (`description`, `keywords`) stay in Edit only.
  *BDD acceptance scenario:* *Given* a position created via Quick-Add
  with `location="Stanford"`, *when* I open the Edit panel, *then* the
  `location` field shows `"Stanford"` and a round-trip Save preserves
  every previously-orphan schema column. Removes the v0.14.0 `xfail`.

### v0.16.0 — settings and bulk

These are the P1-tier "frequent friction" items that became newly
shippable once R0a unblocks scale. Both are real engineering work but
neither is multi-week.

- **R1a — Bulk operations in the Opportunities table.**
  *Why:* P3 has 51 positions and one row per status flip. Bulk status
  flip and bulk requirement-set are independent of R0a; the cross-
  position **mark-submitted-across-positions** sub-op is the only
  piece that needs R0a's join (an inherently per-recommender action).
  We split R1a into two scopes accordingly: the table bulk ops do not
  depend on R0a and could in principle ship earlier — but we keep them
  in v0.16.0 to avoid churn on the Opportunities page mid-R0a.
  *How:* `st.data_editor` multi-row selection backed by a
  session-state set.
  *BDD acceptance scenarios:*
  - *Given* 10 positions in `[SAVED]`, *when* I select 5 and click
    "Mark applied", *then* 5 R1 cascades fire in one batch and the
    markdown export reflects exactly those 5 transitions.
  - *Given* a writer assigned to 3 positions and not yet submitted,
    *when* I mark them submitted from the global Recommenders tab,
    *then* all 3 join rows update with the same `submitted_date` and
    materials-readiness recomputes for each position.

- **R1b — In-UI settings page.**
  *Why:* `DEADLINE_ALERT_DAYS`, `RECOMMENDER_ALERT_DAYS`,
  `UPCOMING_WINDOW_DAYS`, and `STATUS_VALUES` ordering are tuned via
  Python edit today (P2 cannot do it; P3 will but resents it). The
  `config.py` import-time invariants are a strength we keep — settings
  page writes to a JSON file the import-time loader picks up, so
  invariants stay enforced at import.
  *How:* New `pages/5_Settings.py`. Vocabulary additions
  (`STATUS_VALUES`, `INTERVIEW_FORMATS`, `RESPONSE_TYPES`) are
  append-only in the UI to keep migrations sane. Threshold fields are
  number inputs with bounds from `config.py`.
  *BDD acceptance scenario:* *Given* `DEADLINE_ALERT_DAYS` defaults to
  7, *when* I set it to 3 in the Settings page and reload, *then* the
  dashboard Upcoming panel banding uses 3 days, not 7, and the JSON
  override file is persisted under the project data dir.

### v0.17.0+ — backlog (logged, not planned in detail)

The items below stay in the backlog. They are non-trivial but lower
leverage than the v0.14.0–v0.16.0 sequence. Re-evaluate after v0.16.0
ships and we see whether persona-style friction reports converge or
diverge.

- **R1c TRACKER_PROFILE switch** (postdoc / faculty / industry). The
  report's strongest "big bet" call. Worth doing only after R0a +
  R1b prove the architecture absorbs vocabulary extension cleanly.
- **R2a File attachments + per-document version metadata.** P2's
  materials-versioning gap. Multi-week. Real value but only one
  persona currently affected.
- **R2b Responsive layout** for tablet use. Persona-specific to P1.
- **R2c Keyboard shortcuts** under the hotkey shield post-v0.14.0.

## 4. Team orchestration (if I had a team)

I am the team lead. Concretely I would split four roles. In our actual
solo-dev reality these collapse to one person wearing four hats with
agent assistance — but the *handoffs* below are what I would defend
against compression even then, because they are where bias hides.

- **Planner (this doc).** Owns the contract with the reviewer team.
  Once approved, does not touch implementation until the implementer
  asks for a scope-call.
- **Implementer.** Owns BDD+TDD per item. Writes the failing test
  first, then the green commit, then the rollup. Cannot self-approve a
  PR (per the universal `CLAUDE.md` audit-gating rule).
- **Independent auditor.** Fresh-context agent, has not seen
  implementer reasoning. Runs against the diff and the project's
  GUIDELINES + DESIGN. Verdict: Approve / Approve-with-nits / Request
  changes. This is the audit gate from `~/.claude/CLAUDE.md §3`.
- **UX-manager reviewer.** Owns persona-impact sign-off. Reads the
  diff against the field-study report and answers one question:
  "does this PR move a verified persona out of the 50% scope
  plateau, or is it neutral/regressive?" Lives in the PR description,
  not a separate doc.

Sequencing across the v0.14.0 → v0.15.0 → v0.16.0 arc:

1. **v0.14.0 close-out batch (B1 + B4 + B3-pin)** runs as three
   independent commits on the existing branch. Implementer drives;
   auditor reviews the batch as one diff. UX-manager confirms the
   three fixes do not regress S1–S6.
2. **v0.15.0 R0a + R0d + R0b** opens a new branch. R0a's schema
   migration is the load-bearing piece — implementer writes the
   migration test first against a synthetic legacy DB before any
   schema change lands. R0d and R0b follow on the same branch but as
   separate commits to keep the diff legible. Auditor reviews the
   branch as a whole; UX-manager checks that the new two-tab
   Recommenders page does not break the S2 / S4 strengths.
3. **v0.16.0 R1a + R1b** can parallelise across two branches if we had
   two implementers. With one, R1b ships first (it is a smaller risk
   surface and unblocks the settings-tuning persona feedback loop) and
   R1a follows.

**Two distinct iteration cycles, kept separate:**

- *Plan-iteration cycle (this document).* The goal contract says
  "iterate twice to fix wrong claims and bad plans". That budget is
  for this plan, before any code is written. v1 → v2 → v3 spends it
  here and ends at reviewer dispatch. If reviewers request changes,
  that is escalation, not extension of the iteration budget.
- *Implementation-audit cycle (per PR).* Once code starts, each PR
  goes through the standard audit gate from `~/.claude/CLAUDE.md §3`.
  Audit "Request changes" verdicts are PR-level work, not consumed
  against the plan's iteration budget. Conflating the two would let
  a noisy audit cycle hide a structurally wrong plan.

## 5. Risks we accept and watch for

- **R0a migration risk.** Schema migrations are the most likely place
  to lose user data. The migration test against a synthetic legacy DB
  is non-optional. We also keep the markdown exports (`S3`) as a
  recovery surface — if the migration ever loses a row, the markdown
  archive still has it.
- **Scope-creep risk on R0a.** The temptation to also fix R1c
  (TRACKER_PROFILE) inside R0a is strong because both touch
  vocabulary. We resist. R1c lands only after R0a stabilises.
- **Strengths-defended block (S1–S6 named).** S1 editorial identity,
  S2 Upcoming + urgency panel, S3 markdown export (preserved by the
  R0a `exports.write_all` fan-out + `RECOMMENDERS.md` schema rewrite),
  S4 auto-promotion cascade (strengthened by B1's reverse-cascade fix,
  not just preserved), S5 `config.py` import-time invariants (extended
  to join table on Day 1), and S6 6-field Quick-Add discipline. Any
  PR that arguably regresses one of these must call it out in the
  description and get an explicit waiver from the UX-manager reviewer.
- **Six-field Quick-Add discipline.** R0b risks bloating it. Strength
  S6 ("under 30 seconds to capture a new posting") is the bar; if any
  Quick-Add column addition pushes capture time above ~30s for a
  five-line BDD walkthrough, that column moves to Edit-only.
- **Effort-padding honesty.** "Multi-week" for R0a is a lower bound
  of 3 weeks given migration test + two-tab UI + ~33
  `exports.write_all()` call sites + per-recommender grouping toggle.
  R1a is closer to 1.5–2 weeks once the cross-position recommender
  bulk variant is in scope. We label these conservatively rather
  than padding the per-release version count.
- **Two iterations is the budget, not the floor.** If after two
  audit-driven revisions the plan still does not have UX-manager
  approval, the right move is to escalate the scope question (split
  into smaller releases, defer R0a's join-table piece, etc.) rather
  than push a third revision through.
- **Effort-impact misclassification risk on R0d.** Report Figure 6
  places R0d (email + mailto) in the "quick wins" quadrant at effort
  ~1.5. Our plan moves it into the multi-week R0a refactor (§3
  deviation #1). We accept the optical hit of delaying a quick-win
  because the alternative is a throwaway migration. If reviewer
  pushback is strong, the fallback is to add `email` to the existing
  per-position `recommenders` table in v0.14.0 and carry it through
  the R0a migration — strictly more work, but defensible if the
  v0.15.0 timeline slips materially.

---

## Approval

- [x] **UX-manager agent — Approve with nits** (2026-05-22). Confirmed
  R0a addresses P1+P2 Day-1 cause and per-recommender Assignments
  view collapses visible row count; flagged P2's Month-2 churn drivers
  (R2a/R2d) as deferred trade — now explicit in §1.5. Requested S4
  in defended-strengths block — now in §5.
- [x] **Teammate (engineering) agent — Approve with nits** (2026-05-22).
  Spot-checked 5 file:line citations, all verified. Requested:
  explicit `exports.write_all()` fan-out + markdown schema rewrite
  (now in R0a HOW); migration outline mirroring the existing
  `interviews_existed_pre_create` pattern (now in R0a HOW); negative
  + state-preservation BDD scenarios per GUIDELINES §9 (now in R0a);
  xfail tracker-id placeholder (now in B3-pin); R0a 3-week lower
  bound + R1a 1.5–2 week realism (now in §5).
- [x] **Team lead (this session)** — Approve.

All blocking nits folded. Non-blocking citation wording nit (R2 cascade
phrasing) acknowledged; current draft already distinguishes the
forward cascade at `database.py:629` from the documented gap at
`707–719`. Plan is approved.
