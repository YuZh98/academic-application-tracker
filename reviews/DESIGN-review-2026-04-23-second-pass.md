# DESIGN.md Review — 2026-04-23 (Second Pass)

**Branch:** `feature/docs-refactor-pre-t4`
**Scope:** Read-only review of `DESIGN.md` v1.3 (1,026 lines post-extraction) plus its new satellites (`docs/ui/wireframes.md`, `docs/dev-notes/extending.md`, `docs/dev-notes/dev-setup.md`).
**Verdict:** Approve current state for Phase 5; address new 🔴/🟠 findings in a single `docs(design): v1.4 second-pass cleanup` commit; treat remaining prior 🟡 items as opportunistic cleanup.
**Reviewer:** Senior UX + Engineering review, follow-up pass
**Subject:** `DESIGN.md` v1.3 (currently 1,026 lines after recent extraction work)
**HEAD at review:** `b7d66df` — Phase 2 wireframe extraction
**Prior review:** [`DESIGN-review-2026-04-23.md`](DESIGN-review-2026-04-23.md) — 17 findings (F1–F17)
**Review criteria:** UX-experience · clarity · stability · extensibility · unambiguity · conciseness · structuredness. No over-engineering; keep v1 realizable.

---

## 0. Executive summary

DESIGN.md has **improved substantially** since the prior review. Of the four 🔴 findings, all four are fixed (F2, F4, F7, F8). The ~250-line reduction came from extracting UI wireframes, installation commands, and the full extension recipes to supplementary files with clean back-links — the remaining core reads tighter while the operational detail lives where it belongs.

That said, **a second-pass review still turns up 14 new findings** grouped in three buckets:

1. **Residual drift the prior review flagged and is still open** — 10 of 17 prior findings remain unaddressed (F1, F3, F6, F10, F11, F12, F13, F15, F16, F17). Most are 🟡 polish; two are 🟠 worth fixing before Phase 5.
2. **New findings introduced by the restructure** — the extraction moves (wireframes, recipes, placeholders) created their own integration seams. Most notable: the `<STATUS_SAVED>` placeholder convention (§6.2) is clever but has a copy-paste footgun.
3. **UX-design gaps in v1 itself** — two genuine product questions I believe need explicit decisions: **the Delete button's position-vs-tab scoping** and **KPI-card mutual-exclusivity semantics**.

**Verdict:** Approve the current state for Phase 5; address the 🔴/🟠 new findings in a single `docs(design): v1.4 second-pass cleanup` commit; treat the remaining prior 🟡 items as opportunistic cleanup.

**Method.** Read `DESIGN.md` top-to-bottom; read the three satellite files (`docs/ui/wireframes.md`, `docs/dev-notes/extending.md`, `docs/dev-notes/dev-setup.md`) as part of the scope since DESIGN.md now delegates to them; cross-checked section claims against `GUIDELINES.md`, `roadmap.md`, `CHANGELOG.md`, the prior review, and the commit log for this branch. Code/doc drift continues to be out-of-scope — DESIGN.md documents the v1 target.

---

## 1. Status of prior review (F1–F17)

A quick audit of which prior findings have shipped, organized by severity.

### 🔴 Prior findings — all resolved ✅

| # | Finding (prior) | Status | How / where |
|---|-----------------|--------|-------------|
| **F2** | Invariant #5 wording ambiguous ("no duplicates"…) | ✅ Fixed | §5.2 #5 now executable: `sorted(F) == sorted(STATUS_VALUES)` multiset equality |
| **F4** | Funnel empty-state misses "only terminal-status rows" case | ✅ Fixed | §8.1 Funnel empty-state now has three branches (a/b/c) — branch (b) explicitly handles "all non-zero buckets are hidden" |
| **F7** | R2 cascade condition over-restrictive ("exactly one interview") | ✅ Fixed | §9.3 R2 now reads "Any successful interview insert" with the `AND status = '<STATUS_APPLIED>'` guard carrying the full promotion logic |
| **F8** | R3 unconditional → terminal status regression risk | ✅ Fixed | §9.3 R3 now guards with `AND status NOT IN (<TERMINAL_STATUSES>)` |

### 🟠 Prior findings — still open

| # | Finding (prior) | Status | Recommendation |
|---|-----------------|--------|----------------|
| **F3** | `STATUS_COLORS` palette constraint is prose-only | Open | Add either an enforced assertion in `config.py` (allowed-color set) or label the constraint explicitly as advisory-only in §5.1. Picking either moves it from "lurking bug" to "documented stance." |
| **F10** | Upcoming-panel wireframe (5 columns) vs spec table (4 columns) | Partially open | Spec now mentions "Status shown via `STATUS_LABELS[raw]`" but doesn't list it as a column; wireframe shows it. Still reconcile. |
| **F15** | §12.1 "schema is additive" claim is unscoped | Open | Narrow the claim: "**Column schema** is additive; vocabulary values require a one-shot `UPDATE` per profile pair, documented as a `Migration:` entry." |
| **F16** | §8.0 missing layout/loading/narrow-window conventions | Open | Add three items: layout-ratio table (the `[6,1]` split convention is scattered prose), a loading-state convention, and a narrow-window breakpoint note. |

### 🟡 Prior findings — still open

| # | Finding (prior) | Status |
|---|-----------------|--------|
| **F1** | §1 Solution bullets don't point at §8.1 (the actual answer to "what do I do today?") | Open |
| **F5** | Zero-count visible-bucket behaviour unspecified | ✅ Fixed — spec now says "a visible bucket with zero count renders as a zero-width bar (category preserved for axis stability)" |
| **F6** | Empty-DB hero trigger calls `count_by_status()` three times | Open |
| **F9** | R1+R3 co-firing narrative → table | ✅ Fixed — §9.3 now has a "Pre-state / R1 / R3 / Post-state" table |
| **F11** | `max(ready + pending, 1)` denominator — unreachable `max` obscures intent | Open |
| **F12** | Trigger `recursive_triggers = OFF` wording confusing ("fires … suppressed") | Open |
| **F13** | §10 decision table mixes architecture / schema / UX at one flat level | Open |
| **F14** | §6.4 ↔ §10 duplication | ✅ Fixed — §6.4 is now a pointer to §10 |
| **F17** | Missing "Architectural non-goals for v1" section | Open |

**Overall prior-review ship rate:** 7 of 17 addressed (F2, F4, F5, F7, F8, F9, F14). The four 🔴 items are in; most open ones are 🟡. Open 🟠 items are: F3, F10 (partially), F15, F16.

---

## 2. New findings (this pass)

Numbered **G1–G14** to avoid collision with the prior review's F-series. Same severity scale.

### Findings table

| # | §/Location | Finding | Severity |
|---|-----------|---------|----------|
| **G1** | §6.2 DDL (lines 333, 392) | `'<STATUS_SAVED>'` and `'<RESULT_DEFAULT>'` **quoted placeholder** convention looks exactly like a valid SQL string literal. A reader running this DDL verbatim in a SQLite shell creates a column whose default is the literal 11-character string `<STATUS_SAVED>`. The "these are placeholders" paragraph is 40 lines below; if a reader scrolls to the DDL, scans, and copy-pastes, they get broken data. | 🔴 |
| **G2** | §8.2 Opportunities Delete row (line 707) | Delete button placement is **inconsistent across its own justification**. The row says it's "rendered below the edit panel (outside the panel box), visible only when the active tab is Overview." If the button is *outside* the panel box, why is it tab-sensitive? Tabs are a property of the panel's internal state — a button outside the panel should not know about them. The user gets a ghost button that appears/disappears without a visible anchor to what changed. | 🔴 |
| **G3** | §8.1 KPI panel specs | KPI cards are **not mutually exclusive** but this is never documented. "Tracked" = `STATUS_SAVED + STATUS_APPLIED`. "Applied" = `STATUS_APPLIED`. An APPLIED position counts in **both**. A user doing a mental `12 + 4 + 2 + 1 = 19 ≠ total` will think the dashboard is buggy. | 🟠 |
| **G4** | §11 Extension Guide (lines 928–935) | §11 is now **just a 7-line pointer** to `§5.3` and `docs/dev-notes/extending.md`. With no content of its own, it exists only to appear in the ToC. Either (a) inline a 2-3 sentence "when to use which" to justify its presence, or (b) drop §11 entirely and link from the ToC directly to the two destinations. Current form is a speed bump. | 🟡 |
| **G5** | §5.1 symbol-index tables | The conversion from "commented code listing" to "symbol-index tables" wins for reference lookup but **loses the shape-at-a-glance** of the old code block. A newcomer wanting "what groups of constants does `config.py` have?" gets ten separate tables with no narrative. Add a 1-sentence intro per group explaining what the group as a whole is for. | 🟡 |
| **G6** | §8.0 Status label convention (line 617) | The convention says "Pages never render a raw status value to the user" — but §8.1 Upcoming panel cell shows `"Saved"` (correct) while the §8.1 KPI Next Interview panel spec shows raw cell access. Consistent rule, subtle gap in enforcement guidance. Add: "The corollary — every selectbox uses `format_func=config.STATUS_LABELS.get` — applies across pages; no exceptions in v1." | 🟡 |
| **G7** | §6.2 `interviews.application_id` | Column is named `application_id` but its FK is `REFERENCES applications(position_id)`. A reader with DB intuition expects `application_id` to reference `applications.id` — which does not exist. The pattern is valid (the `applications` table uses `position_id` as its PK per D10), but the naming invites confusion. Either rename to `position_id` (accepting that interviews transitively depend on applications) or add an inline comment: `-- application_id aliases applications.position_id (applications.PK = position_id, per D10)`. | 🟡 |
| **G8** | §9.3 `response_type = "Offer"` ambiguity | R3 trigger reads `response_type transitions to "Offer"` — the string literal `"Offer"` here is a **RESPONSE_TYPE value**, not the **pipeline status** `[OFFER]`. The spec conflates them because they share the word. Disambiguate: `response_type = RESPONSE_TYPES[4]` (if the index is stable), OR document inline: "note: `"Offer"` here is the response-type category (`RESPONSE_TYPES`); the pipeline stage it promotes to is `STATUS_OFFER`." | 🟡 |
| **G9** | §9.3 post-cascade return dict | `{"status_changed": bool, "new_status": str \| None}` — what is `old_status`? If the UI wants to toast `"Promoted from Applied to Interview"`, it needs both. The current shape forces the caller to do a pre-read. Widen to `{"status_changed": bool, "old_status": str \| None, "new_status": str \| None}`. | 🟡 |
| **G10** | §6.2 `recommenders.confirmed` | Column is `INTEGER` tri-state: `0`/`1`/`NULL` for "declined"/"accepted"/"pending". Using `NULL` as a meaningful third state is a **common bug source** — every consumer must remember that `confirmed = 1 OR confirmed = 0` misses `NULL`. Three options: (a) add an explicit D-numbered decision justifying the tri-state; (b) split into `confirmed INTEGER` + `confirmed_date TEXT` with `NULL` meaning "no response yet" (unambiguous); (c) use a three-value TEXT like `REQUIREMENT_VALUES`. Option (b) is cheap and matches D19's dual-column philosophy. | 🟠 |
| **G11** | §8.1 Dashboard wireframe (in `docs/ui/wireframes.md`) vs §8.1 spec | Wireframe shows `[expand]` button inline with the Funnel column ("Saved / Applied / Interview / Offer / [expand]") — as if it's a 5th funnel row. DESIGN.md spec says `[expand]` is a separate button below the chart. Reader of the wireframe will assume it's a row; reader of the spec will build it as a button. Reconcile. | 🟠 |
| **G12** | §5.1 `STATUS_OFFER` alias | Seven `STATUS_*` aliases defined — `STATUS_SAVED`, `STATUS_APPLIED`, `STATUS_INTERVIEW`, `STATUS_OFFER`, `STATUS_CLOSED`, `STATUS_REJECTED`, `STATUS_DECLINED`. The spec text uses them for R1/R2/R3 cascades. But §8.1 Tracked KPI reference uses `STATUS_SAVED + STATUS_APPLIED` (two aliases), §9.3 R3 uses `STATUS_OFFER` (one alias), and nothing uses `STATUS_CLOSED`/`REJECTED`/`DECLINED`. If these three aliases have no documented consumer in v1, they exist for symmetry only. Either find a use (e.g., R3's terminal guard could enumerate them) or note in §5.1: "The three terminal aliases are for symmetry and future-use; current v1 code references `TERMINAL_STATUSES` for terminal checks." | 🟢 |
| **G13** | §8.1 `Materials Readiness` progress bars | Spec says `values = count / max(ready + pending, 1)`. The `max(..., 1)` is unreachable (per F11, still open). But also: the pair is `(ready, pending)` where `ready + pending ≥ 1` in the non-empty branch; so both progress bars **sum to exactly 1.0 — they partition a total of 1**. Is this the right visual? Two bars summing to a visual 100% might read as "3 out of 8 are ready, 5 out of 8 are missing" — which is correct — but could also read "5 out of 8" = 62.5% missing as one bar filling 62.5% of some abstract whole. A single stacked-segment bar would be unambiguous; two parallel bars invite confusion. UX review deferred — but flag as a choice worth documenting in §10 if it stays. | 🟢 |
| **G14** | §9.3 R2 "pre-application interview" gap | If a user adds an interview to a `[SAVED]` position (they forgot to mark it applied first), R2's `AND status = '<STATUS_APPLIED>'` guard makes the cascade a no-op. The position stays `[SAVED]`, but the Upcoming panel shows an interview for it — a dashboard inconsistency. Intentional? The spec doesn't say. Either document ("R2 respects pipeline order; out-of-order interviews don't retro-promote the status") or add an R2-prime that handles SAVED→INTERVIEW. My take: **document it** — the user-intervention path (manually change status) is fine; retro-promoting would hide a workflow mistake. | 🟢 |

---

## 3. Cross-cutting pitfalls (this pass)

Grounded in what I observed, not generic advice. Continues the prior review's `P`-series.

### P8. Pretend-literal placeholders in code blocks

**Seen in:** G1 (`'<STATUS_SAVED>'` in SQL DDL).

The convention "surround a substitution target in angle brackets and keep the quotes for visual coherence" is clever — but the resulting string is syntactically valid in SQLite. A reader who types `sqlite3 postdoc.db < schema.sql` with the DDL copy-pasted gets a column whose default is the literal string `<STATUS_SAVED>`. No error. Data is silently wrong.

**Lesson.** If a code block is meant to be partially pseudo, make the substitution **syntactically impossible to mis-copy**. Three options:

1. Non-SQL-valid marker: `DEFAULT {{STATUS_SAVED}}` (double braces are not SQL; error if copied).
2. Comment-only reference: `DEFAULT '[SAVED]' -- = config.STATUS_VALUES[0]`; accept that a rename means a doc edit.
3. Explicit sentinel: `DEFAULT NULL -- interpolated at init_db() time from config.STATUS_VALUES[0]`.

Option 2 is my recommendation for a spec: stable-enough (DESIGN.md updates on architectural change), no footgun.

### P9. Section-with-no-content anti-pattern

**Seen in:** G4 (§11 is a 7-line pointer).

When a section exists only to point at two other places, it's a ToC entry pretending to be content. Readers who click "11. Extension Guide" expect either (a) a recipe, (b) a rationale, or (c) a choice ("use this for X, that for Y"). A bare pointer gives none of the three.

**Lesson.** Section stubs should **earn their ToC slot**. If a section is one link, fold the link into the parent or a neighboring section. If it's genuinely necessary as a landing — because the ToC is a public-facing navigation contract — make it **explain the choice** it delegates.

### P10. Reference-style prose that loses narrative

**Seen in:** G5 (§5.1 symbol-index tables).

The old code-block version of §5.1 was discursive — a reader learned `config.py`'s shape by reading Python with comments. The new table version is reference-grade — faster to look up "what does `TERMINAL_STATUSES` do?" — but slower to learn "how is `config.py` organized?"

This is a classic **reference vs tutorial** tension. Good specs serve both. The current one serves reference well; tutorial poorly.

**Lesson.** A reference table gains a new reader when you place a 1-2 sentence "what this group of rows is about" block above each table. The cost is 10 minutes of writing; the benefit is first-time readability.

### P11. Shared vocabulary across layers

**Seen in:** G8 (`"Offer"` the response type vs `STATUS_OFFER` the pipeline state).

Two concepts sharing a word is fine in speech; in code and spec it's ambiguity waiting to land. DESIGN.md uses `"Offer"` in §9.3 R3 and `[OFFER]` in STATUS_VALUES — both appear in the same transition rule. A reader has to parse "which Offer do you mean?" each time.

**Lesson.** Whenever two closely-related concepts share a word, **pick different words in the spec** even if the code has the same string. Here: "R3 fires when `response_type` takes the value `RESPONSE_TYPE_OFFER`" — a pseudo-alias that signals "this is not the status."

### P12. Tri-state columns without a framework

**Seen in:** G10 (`recommenders.confirmed` as INTEGER NULL).

Three-state boolean-ish fields (`True` / `False` / `Unknown`) are common in real systems but come in two forms:

1. **One tri-state column** (INTEGER NULL, TEXT enum). Pro: compact. Con: every query needs `IS NULL` branches; easy to forget.
2. **Two columns** (boolean flag + metadata). Pro: unambiguous, matches D19. Con: more columns.

The schema picks form 1 for `confirmed` and form 2 (D19) for `confirmation_received` / `confirmation_date`. **The split is inconsistent.** Both fields are conceptually the same shape (a positive event that may not have happened yet).

**Lesson.** Pick a project-wide stance on tri-states and apply it uniformly. For this project, D19 is the cleaner path; `confirmed` should follow.

### P13. "Outside the box" UI elements reacting to inside-the-box state

**Seen in:** G2 (Delete button outside edit panel but tab-sensitive).

When a UI element lives *outside* a container, users assume it's scoped to the container-wide state (i.e., "Delete this position"). When it reacts to *inside* state (the active tab), the mental model breaks. Either the button should be inside (and tab-local) or outside (and tab-agnostic).

**Lesson.** A UI element's spatial scope should match its behavioural scope. If Delete is scoped to the position-as-a-whole (which it is — it cascades to applications, interviews, recommenders), it should be **always visible** when a position is selected, from any tab. Alternatively: put it inside the Overview tab form as an explicit "Delete this position" action, matching the tab that represents the position's identity.

---

## 4. UX-specific risks (senior UX hat)

Four product questions that DESIGN.md leaves under-specified. None are blockers for v1 ship but each has a real user-impact cost.

### UX1. Dashboard KPI mutual-exclusivity

**Issue (G3):** KPI cards overlap in their counting logic. A position at `[APPLIED]` appears in both Tracked and Applied. The dashboard doesn't surface this.

**User impact:** A power user who treats the four KPIs as a dashboard integrity check (do the numbers sum to the total?) will conclude the app is buggy. A casual user may make decisions based on a wrong mental model ("Applied is small, I should apply more" when in fact Applied is a subset of a larger Tracked).

**Fix:** Update the `help=` tooltip on Tracked to say "Saved + Applied — these overlap with the other KPIs by design (Applied is a subset of Tracked)." Or: change Tracked to "Saved" = `STATUS_SAVED` only, so the four KPI cards partition the active pipeline.

### UX2. Interview KPI semantic

**Issue:** "Interview" KPI counts **positions** at `[INTERVIEW]` status, not **interview events**. With the normalized `interviews` sub-table, a user with two scheduled interviews for the same position sees KPI = 1, not 2.

**User impact:** Mismatch between intuition ("I have 3 upcoming interviews") and display ("Interview: 1").

**Fix:** `help="Positions currently at the Interview stage (not total scheduled interviews — see Upcoming panel for those)"`.

### UX3. Unsaved-changes indicator on edit panel tabs

**Issue:** Each tab has its own Save button. Nothing indicates "this tab has unsaved changes." A user can edit the Requirements tab, switch to Materials, make changes, switch back to Requirements, and *wonder* if they ever hit Save.

**User impact:** Double-saving is harmless (idempotent); missing a save is data loss. The current design biases toward data loss.

**Fix (deferrable to Phase 7 polish):** add a dirty-state marker (dot next to the tab label) when session_state diverges from the DB. Streamlit supports this via `st.tabs` with an emoji prefix that can be conditionally rendered.

### UX4. Delete button targeting after selection change

**Issue (related to G2):** If the Delete button is rendered "below the edit panel" (outside the panel box per the wireframe), it's spatially associated with *whichever position is currently selected*. If the user changes selection, the button continues to point at the new selection — but visually, it hasn't moved. A user whose mental model is "I was looking at position X, I'm about to delete it" can click Delete and find they've deleted position Y.

**User impact:** Data loss. Irreversible in v1 (no soft delete until §12.2).

**Fix:** Two options. (a) Put Delete inside the Overview tab form so it always travels with the position body. (b) Add the position name to the Delete button label: `[ Delete "Stanford BioStats Postdoc" ]` — the button reads its own target, eliminating mental-model drift.

---

## 5. Satellite file review

The extraction moves created three new files that DESIGN.md now depends on. Quick audit.

### `docs/ui/wireframes.md` (174 lines)

**Verdict:** Clean. The "Intent-only" disclaimer at top is senior-level defensive writing. Each wireframe back-links to the matching DESIGN.md sub-section — good bidirectional nav.

**Drift with DESIGN:**
- G11 above: `[expand]` button placement.
- F10 (prior): Upcoming panel has a Status column.

**Suggested:** consider adding a second wireframe variant showing "funnel expanded" state, so a reader understands what clicking `[expand]` does.

### `docs/dev-notes/extending.md` (73 lines)

**Verdict:** Clean complement to §5.3. The step-by-step recipes are the right genre for a dev-notes file.

**Minor:** the "Switch the tracker profile" section is one sentence ("See DESIGN §12.1") — consider either (a) removing it from this file and linking from §5.3 directly to §12.1, or (b) expanding to actual steps. Currently it's the same G4 pattern: a stub earning a section header.

### `docs/dev-notes/dev-setup.md` (48 lines)

**Verdict:** Clean. The "why here vs GUIDELINES" disambiguation at the top is thoughtful. No issues.

---

## 6. Recommendations (priority-ordered)

### Ship before Phase 5 (🔴)

1. **Fix G1 — placeholder convention** — pick Option 2 from P8: keep literal `DEFAULT '[SAVED]'` with a `-- config.STATUS_VALUES[0]` comment. Accept the small stability cost.
2. **Fix G2 / UX4 — Delete button scoping** — either move inside the Overview tab form, or make it always-visible with the position name embedded in the button label.

### Ship in v1.4 clarity pass (🟠)

3. **Fix G3 / UX1 — KPI mutual-exclusivity** — update `help=` tooltips on all four KPI cards to disambiguate.
4. **Fix G10 — `recommenders.confirmed` tri-state** — split into `confirmed INTEGER 0/1` + `confirmation_date TEXT` per D19, for schema consistency.
5. **Fix G11 — wireframe/spec drift on `[expand]`** — reconcile per the spec (separate button below chart).
6. **Fix F15 (prior)** — scope the §12.1 "additive" claim; add the per-profile migration recipe.
7. **Fix F16 (prior)** — add layout-ratio table, loading-state convention, and narrow-window note to §8.0.
8. **Fix F3 (prior)** — either enforce the `STATUS_COLORS` palette invariant or label it advisory-only.
9. **Fix F10 (prior) + G6** — reconcile Status column in the Upcoming wireframe/spec.

### Opportunistic polish (🟡)

10. **G4** — drop §11 or earn it by inlining "when to use which" language.
11. **G5** — add 1-sentence intros per symbol-index sub-group in §5.1.
12. **G7** — clarify `interviews.application_id` naming or rename.
13. **G8** — disambiguate "Offer" the response type vs the status.
14. **G9** — widen the cascade return dict to include `old_status`.
15. **UX3** — add dirty-state indicator on edit panel tabs (can defer to Phase 7).
16. **F1, F6, F11, F12, F13, F17** — prior 🟡 items still open.

### Log only (🟢)

17. **G12** — document the three terminal aliases as forward-use only (or find v1 consumers).
18. **G13** — document the progress-bar pair visual pattern in §10 if it stays.
19. **G14** — document that R2 does not retro-promote out-of-order interviews.

---

## 7. Verdict

### Objective scores (my calibration, not absolute)

| Criterion | Score | Notes |
|-----------|-------|-------|
| **UX-experience** | B+ | §8 panels are thoroughly spec'd; UX1/UX2/UX4 are real holes; satellite wireframes cleanly scoped. |
| **Clarity** | A- | Invariants are crisp; §9.3 cascade table is exemplary. §5.1 symbol-index trades narrative for lookup — net neutral. Placeholder convention in §6.2 is an active clarity hazard. |
| **Stability** | A- | Version discipline locked, substantive content is v1-target. `<STATUS_SAVED>` placeholder protects against rename drift; F13 (flat decision table) is a scanning cost, not stability. |
| **Extensibility** | A | §5.3 extension recipes + `docs/dev-notes/extending.md` step-by-step is an excellent two-layer system. |
| **Unambiguity** | B+ | F2/F4/F7/F8 resolved (big wins). G1/G8/G10 are the remaining ambiguity surface. |
| **Conciseness** | A- | Wireframe + recipe + install-command extractions were the right move. §11 is a leftover stub (G4). |
| **Structuredness** | A- | 12 sections follow the canonical sequence; ToC is accurate; F13 flat-table remains the one organisational blemish. |

**Overall: A-** — solid, review-ready v1 spec. The two 🔴 findings (G1, G2/UX4) are worth fixing before Phase 5 starts because they're both footgun-class: silent broken data (G1) and silent destructive action (G2/UX4). Everything else is either polish or real-but-deferrable.

**Approve for Phase 5 after G1 + G2/UX4 fixes land.**

---

## 8. What a junior engineer would ask

Four questions specific to this iteration.

### Q1. "Why is `TERMINAL_STATUSES` a `list`, not a `set`?"

**Observation.** §5.1 types it `list[str]`. The values are unordered (membership is the only semantic operation). Compare with `VALID_PROFILES: set[str]`.

**Answer.** Either (a) display order matters somewhere (e.g., an error message that lists terminal statuses in order); (b) it was typed as `list` by convention and never reconsidered. The spec doesn't say. The `<= set(...)` invariant in §5.2 #4 does a set conversion, so the type doesn't affect that check. If no display-order consumer exists, `set[str]` is more honest.

**Lesson.** Collection-type choice is a signal. `list` says "order matters." `set` says "only membership." `tuple` says "immutable sequence." When none of those matches, the reader suspects a missed refactor.

### Q2. "If `applications.position_id` is both PK and FK, how do I write a query to find an application by its own ID?"

**Observation.** §6.2 applications table: `position_id INTEGER PRIMARY KEY`. No separate `id` column. To look up an application, you query by `position_id`.

**Answer.** That's the design (D10): every position has exactly one application, and the FK relationship is 1:1. The PK *is* the FK. So `SELECT * FROM applications WHERE position_id = ?` is both "find by application id" and "find by position id" — they're the same column.

**Lesson.** When a FK serves as the PK, the joining table loses independent identity — there's no `application.id` distinct from `position.id`. Usually this is fine for 1:1 relationships; it becomes awkward if you later need a 1:N (one position, multiple applications over time — e.g. reapplying next cycle).

### Q3. "The `<STATUS_SAVED>` placeholders in §6.2 DDL — are they literal SQL or templates?"

**Observation (G1, P8).** Syntactically they're valid SQL string literals. Semantically they're templates interpolated at runtime.

**Answer.** Templates. The paragraph under the DDL (lines ~441) explains this. But the DDL looks runnable.

**Lesson.** Pseudo-code inside a real code block is an anti-pattern when the fake syntax happens to also be valid real syntax. Separate them visually (comments, different brace style, or explicit prose) so no reader can mistake one for the other.

### Q4. "Why is the Delete button on the Opportunities page placed outside the edit panel?"

**Observation (G2, UX4).** §8.2 spec says "rendered below the edit panel (outside the panel box), visible only when the active tab is Overview."

**Answer.** The stated reason ("the Delete button's scope is the whole position, not the active tab's data — hence the Overview-only placement, matching the tab where the user is reviewing the position as a whole") is internally inconsistent. Outside-the-box spatial scope does not match tab-sensitive behaviour.

**Lesson.** UI placement decisions should have a single-sentence rationale that covers all the behaviour's axes. "Delete is scoped to the position → Delete lives inside the Overview tab form OR travels with the position via an always-visible button." Both are defensible; the current hybrid is not.

---

## 9. Method

1. Read `DESIGN.md` v1.3 end-to-end against the seven review criteria (UX, clarity, stability, extensibility, unambiguity, conciseness, structuredness).
2. Read the three satellite files (`docs/ui/wireframes.md`, `docs/dev-notes/extending.md`, `docs/dev-notes/dev-setup.md`) as part of the scope; cross-checked each claim against DESIGN.md.
3. Read the prior review (`reviews/DESIGN-review-2026-04-23.md`) and checked each F1–F17 finding against the current DESIGN.md. Status table in §1 above.
4. Examined the git log on `feature/docs-refactor-pre-t4` (commits since the prior review) to understand the restructuring moves.
5. Read `GUIDELINES.md`, `CHANGELOG.md`, and `roadmap.md` briefly to ground cross-doc claims.
6. Applied a senior-UX hat specifically on §8 (UX1–UX4); otherwise reviewed as a generalist senior engineer.
7. No code or markdown files edited. No source code read beyond what DESIGN.md references by name.

**Out of scope by instruction:** drift between DESIGN.md and the current codebase (expected per the user's context note — the file is a mid-term self-reflection). No comparison with `config.py` / `database.py` / `app.py` was performed for drift; only for cross-referencing concepts.

**Next step if approved:** address the two 🔴 items (G1, G2/UX4) in one commit; roll the 🟠 fixes into a `docs(design): v1.4 clarity pass` commit alongside the open prior-review items (F3, F10, F15, F16).
