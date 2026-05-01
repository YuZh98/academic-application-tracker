# DESIGN.md Review — 2026-04-23

**Branch:** `feature/docs-refactor-pre-t4`
**Scope:** Read-only review of `DESIGN.md` v1.3 (2026-04-23, 1,291 lines).
**Verdict:** Approve with nits. Address 🔴 (F2/F4/F7/F8) before Phase 5; the rest can land in a single v1.4 clarity pass.
**Reviewer:** Senior UX/Engineering review pass
**Subject:** `DESIGN.md` v1.3 (2026-04-23), 1,291 lines
**Goal of review:** Improve DESIGN.md on **UX-experience, clarity, stability, extensibility, unambiguity, conciseness, structuredness**, while keeping v1 realizable and avoiding over-engineering.

---

## 0. Executive summary

DESIGN.md is **ambitious, structured, and senior-quality** as a mid-term
self-reflection. It covers architecture → schema → UI → data flows →
decisions → extensions → v2 notes in a logical sweep, and the invariant
block in §5.2 plus the migration taxonomy in §6.3 are genuinely
impressive artifacts for a single-author personal project.

That said, a skeptical pass surfaces **17 findings** worth acting on
before T4 starts. Most are internal to the spec itself (contradictions
between wireframes and column tables, ambiguous empty-state triggers,
over-restrictive state-machine rules). Two are **UX design flaws**
latent in the v1 target itself — not drift from code — and would
ship a worse experience unless caught. Another cluster is
conciseness/structure polish: the document has grown organically and
some concepts are now restated in four places.

**Verdict:** Approve with nits. None of the 17 findings block T4.
Address 🔴 items (F2, F4, F7, F8) before Phase 5 begins; the rest
can land as a single `docs(design): v1.4 clarity pass` commit.

**Method.** I read DESIGN.md top-to-bottom; cross-checked every
structural claim against `config.py`, `database.py`, `app.py`,
`GUIDELINES.md`, `PHASE_4_GUIDELINES.md`, `roadmap.md`,
`CHANGELOG.md`, and `docs/adr/README.md`. Per the user's note, I
treated code/doc drift as expected (the CHANGELOG already classes the
`[OPEN]`→`[SAVED]` rename and related edits as deferred), so drift
findings are flagged for awareness only and do not count against the
doc. The review targets **doc quality**, not code parity.

---

## 1. Findings table

Severity follows [GUIDELINES §10](../GUIDELINES.md) with a doc-review adaptation:

| Icon | Meaning | Scope |
|------|---------|-------|
| 🔴 | Contradiction or ambiguity that would actively **mislead an implementer** | Fix before Phase 5 |
| 🟠 | Drift the reader should be warned about, or missing information | Fix in v1.4 clarity pass |
| 🟡 | Clarity, conciseness, or structure polish | Fix if cheap |
| 🟢 | Forward-looking or v2 concern | Log; no action now |

### Findings

| # | §/Line | Finding | Severity | Recommendation |
|---|--------|---------|----------|----------------|
| **F1** | §1 Purpose | "Markdown files alone cannot answer the key daily question" — but the **Solution** bullets don't include answering it either. `app.py` §8.1 is where the answer lives. | 🟡 | Add "See §8.1 — the dashboard *is* the answer" as a one-line forward-pointer. |
| **F2** | §5.2 invariant #5 | "The raw statuses across all FUNNEL_BUCKETS tuples, flattened, equal set(STATUS_VALUES) with no duplicates" is English-ambiguous — does "no duplicates" modify the flattened list or the equality? | 🔴 | Rewrite as executable prose: *"Let `F = [raw for (_, raws, _) in FUNNEL_BUCKETS for raw in raws]`. Require `sorted(F) == sorted(STATUS_VALUES)` (element-wise equality as multisets; each raw status appears in exactly one bucket)."* |
| **F3** | §5.1 STATUS_COLORS docstring | "Values are from the overlap of the st.badge palette and Plotly marker_color CSS-color vocabulary." This invariant has **no assertion** in §5.2. If a future editor replaces `"orange"` with `"#ff7f0e"`, `st.badge()` silently breaks (flagged in T2 review finding #7, kept by design). | 🟠 | Either add an assertion (allowed-color set, validated at import) or acknowledge explicitly in §5.1 that this is a **prose-only invariant** with no enforcement, so the reader knows to grep before editing. |
| **F4** | §8.1 Funnel panel + §8.1 Funnel empty-state | **Inconsistency: when a DB has only terminal-status rows AND terminal buckets are default-hidden, the figure renders with zero visible bars** — but the empty-state trigger (`sum(count_by_status().values()) == 0`) does not fire, because the sum is > 0. User sees a subheader + toggles + blank plot area. | 🔴 | Either: (a) broaden the empty-state trigger to "no visible bars" — `sum(count for bucket in FUNNEL_BUCKETS if bucket.label not in hidden_set) == 0`; or (b) explicitly document this edge case as acceptable UX and rely on the toggle row above the chart to cue "there are hidden rows." My vote: (a); (b) leaves a bad first impression for a user who has only archived applications from a past cycle. |
| **F5** | §8.1 Funnel panel row | `FUNNEL_BUCKETS[i][2]` spec doesn't say what happens to zero-count buckets that **are** visible — does the chart render a zero-width bar (transparent) or skip the bucket? `app.py` today renders zero-width bars for stability; the target spec is silent. | 🟠 | State explicitly: "Zero-count visible buckets render as zero-width bars so the y-axis category set is stable as the pipeline fills." (This mirrors the sparse-dict fill rationale already explained for `count_by_status()`.) |
| **F6** | §8.1 Empty-DB hero trigger | The trigger formula calls `count_by_status()` three times: `count_by_status().get(STATUS_SAVED, 0) + count_by_status().get(STATUS_APPLIED, 0) + count_by_status().get(STATUS_INTERVIEW, 0) == 0`. A reader implementing this literally would issue three DB round-trips per render. | 🟡 | Render as pseudocode with a single call: `c = count_by_status(); if c.get(STATUS_SAVED,0) + c.get(STATUS_APPLIED,0) + c.get(STATUS_INTERVIEW,0) == 0:`. The live `app.py` already does this correctly; DESIGN is the one misleading the reader. |
| **F7** | §9.3 R2 auto-promotion | **"After the insert, this application has exactly one interview row"** is over-restrictive. Scenario: position is at `[APPLIED]` with 2 existing interviews (because the user back-edited the status from `[INTERVIEW]` → `[APPLIED]`). User adds a 3rd interview. "Exactly one" is false → no promotion. The pipeline silently stays at `[APPLIED]` despite 3 scheduled interviews. | 🔴 | Relax the condition: "R2 fires whenever `add_interview` is called for a position where `status = '[APPLIED]'`." The "exactly one" is a red herring — the `AND status = '[APPLIED]'` guard already prevents double-promotion. Alternative: add a complementary R2' in `delete_interview` that regresses to `[APPLIED]` only if `status = '[INTERVIEW]'` and zero interviews remain; but that doubles the complexity. Pick one. |
| **F8** | §9.3 R3 auto-promotion | **Unconditional `UPDATE positions SET status = '[OFFER]' WHERE id = ?`** means a stray edit that sets `response_type = 'Offer'` on a `[REJECTED]` position would regress the terminal status to `[OFFER]`. That's not a recoverable UX state; the user has to manually re-reject. | 🔴 | Add terminal guard: `WHERE id = ? AND status NOT IN TERMINAL_STATUSES`. The spec's "R3 unconditional" philosophy is fine for SAVED→OFFER in one transaction, but terminal statuses are terminal. |
| **F9** | §9.3 R1+R3 co-firing paragraph | The paragraph says "If R1 and R3 fire from the same upsert_application call, R3 wins (evaluated last, unconditional). The combined effect equals `[SAVED] → [OFFER]` in one transaction." This is true but non-obvious — a reader has to trace: R1 promotes SAVED→APPLIED, R3 promotes anything→OFFER, so end state is OFFER. | 🟡 | Replace the sentence with a 3-row micro-table showing {before, R1 fires?, R3 fires?, after}: `[SAVED], Y, Y, [OFFER]`; `[APPLIED], N, Y, [OFFER]`; `[REJECTED], N, Y (currently) / N (F8-fixed), [REJECTED]`. |
| **F10** | §8.1 Upcoming panel | **Wireframe vs. spec-table drift.** The wireframe shows 5 columns (`Date, Label, Status, Kind, Urgency+emoji`); the spec table lists 4 (`Date, Label, Kind, Urgency`). The wireframe shows `Saved` / `Applied` under a status-like column. | 🟠 | Reconcile. Users skimming Upcoming want to see status to distinguish "I need to apply by this date" vs "I have an interview." My recommendation: add a fifth column `Status` (via `STATUS_LABELS[raw]`) to the spec table, or fold status into `Label` as `"Stanford BioStats · Saved"`. |
| **F11** | §8.1 Materials Readiness | Denominator formula `count / max(ready + pending, 1)` is mathematically correct but obscures the UX intent. The `max(..., 1)` is unreachable in the else-branch (both zero → if-branch handles it), per CLAUDE.md notes. | 🟡 | Either simplify to `count / (ready + pending)` and note "unreachable zero-div case is gated by the empty-state branch above," or keep `max(1)` and say so inline: "Defensive against zero-div if the branch guard is ever removed." |
| **F12** | §6.2 TRIGGER positions_updated_at note | "Relies on SQLite's default recursive_triggers = OFF — the inner UPDATE fires the trigger again in principle, but is suppressed by the default setting, preventing an infinite loop." The phrasing "fires the trigger again in principle, but is suppressed" is confusing. With `recursive_triggers = OFF`, the inner UPDATE **does not fire** the trigger at all — there is no firing-then-suppression. | 🟡 | Rewrite: "With SQLite's default `recursive_triggers = OFF`, nested UPDATE statements from inside a trigger do not re-enter the trigger. If a future runtime changes this PRAGMA globally, the trigger loops infinitely on update — pin this at the connection level if concerned." |
| **F13** | §10 decision table organization | D1–D25 mixes architectural (D1, D12), schema (D16–D22), UX (D13, D14, D24), and ops (D4, D25) decisions at one flat granularity. Scanning is hard. | 🟡 | Introduce three sub-headers: **§10.1 Architecture** (D1, D4, D9, D10, D12, D15), **§10.2 Schema & Storage** (D2, D3, D5, D8, D11, D16, D18, D19, D20, D21, D22, D23, D25), **§10.3 UX & Presentation** (D6, D7, D13, D14, D17, D24). Preserves numbering. |
| **F14** | §6.4 vs §10 duplication | §6.4 schema-design-decisions table repeats D19/D20/D21/D22 verbatim from §10. | 🟡 | Keep §10 as the canonical decision ledger; §6.4 becomes a pointer table: "Storage decisions affecting this schema: D2, D3, D11, D16, D18, D19, D20, D21, D22, D23, D25 (see §10)." Saves ~15 lines and removes the second-update hazard. |
| **F15** | §12.1 profile expansion | Claim: "Users keep existing data through a profile switch — the schema is additive." This is only true for **columns**. If `software_eng` replaces `STATUS_VALUES` entirely (`[BACKLOG, APPLIED, PHONE, ONSITE, OFFER, ...]`), existing `[SAVED]`/`[INTERVIEW]` rows become orphan values with no UI affordance. | 🟠 | Scope the claim: "Columns are additive; vocabulary values require a manual one-shot `UPDATE` per profile pair, documented as a `Migration:` entry in CHANGELOG." Also add a profile-expansion recipe for `FUNNEL_BUCKETS` (the current recipe covers `PROFILE_REQUIREMENT_DOCS` but not bucket definitions). |
| **F16** | §8.0 Cross-page conventions | Covers page_config, widget-key prefixes, status labels, toast/error patterns. **Missing:** layout conventions (column width ratios like `[6,1]` title row are repeated prose-style in §8.1 — pull them up), loading states (none specified — what renders during a slow query?), and narrow-window behavior (U2 accepts stacking "on narrow windows" but the breakpoint is unspecified). | 🟡 | Add three items to §8.0: a layout-ratio table, a loading-state convention (default: block render; no spinner for queries under ~100ms), and a narrow-window note ("Streamlit's default breakpoint applies; no custom media queries in v1"). |
| **F17** | §1.3 vs missing "Architectural non-goals" | §1.3 covers product non-goals (no auth, no cloud). No section covers **architectural non-goals**: no CI, no type-checker enforcement, no multi-threading, no performance tuning, no i18n. A new contributor would either ask about these or silently add them. | 🟡 | Add §1.4 "Architectural non-goals for v1" listing: (a) No CI / pre-commit — tests run manually (GUIDELINES §11 pre-commit checklist), (b) No performance budget — 10²–10³ positions fit in memory, (c) No static type checking at CI — type hints are advisory, (d) No i18n — English-only, American date formats, (e) No accessibility audit — basic Streamlit defaults only. |

---

## 2. Pitfalls junior UX designers and engineers are subject to

These are grounded in what I observed reviewing DESIGN.md, not generic advice.

### P1. Treating the wireframe and the spec table as independent sources of truth

**Seen in:** F10 (Upcoming panel has a Status column in the wireframe, not in the spec table).

ASCII wireframes age out fast — someone edits a column and forgets the
mirror table, or vice versa. The junior reader then either: (a) copies
from the wireframe, misses a column, and fields a bug report ("Where's
the status shown?"), or (b) copies from the spec table, and the QA tester
compares to the wireframe and files a mismatch.

**Lesson.** Wireframes are schematic — they show *shape*. The spec
table is normative — it says *what to render*. Commit an explicit
sentence under each wireframe: "The spec table below is the contract;
the ASCII above is for orientation only."

### P2. Empty-state triggers that track data, not the visible presentation

**Seen in:** F4 (funnel empty-state fires on "zero rows anywhere" — but
a user with only archived applications from a past cycle sees an empty
chart area without the helpful empty-state copy).

Junior heuristic: "if no data, hide." Mature heuristic: "if no
**visible** content, hide." A panel with filters, toggles, or
default-hidden buckets has two empty states: the data-level one
(`rows == 0`) and the presentation-level one (`visible_rows == 0`).
Mixing them shows a broken-looking UI to a user whose data is
legitimately present but filtered out of view.

**Lesson.** For any panel with default-hidden subsets, write the
empty-state trigger against the rendered output, not the raw count.

### P3. Over-promising "additive" or "safe" behaviors

**Seen in:** F15 (profile expansion's "schema is additive" is true for
columns, false for vocabulary values — but the claim is unscoped).

Junior writing a forward-looking section wants to reassure the future
reader: "Don't worry, it's compatible." Senior reality: compatibility
claims are only as safe as their narrowest axis. "Additive" is a
precise term and requires scoping when used.

**Lesson.** Any word like "additive," "idempotent," "atomic," "safe,"
or "compatible" should carry the scope next to it — *what* is additive,
under *what conditions*, breaks *when*. A sentence like "additive
across schema columns; vocabulary values require migration" is two
seconds slower to write and saves an hour of debugging.

### P4. State-machine rules that treat a count as a proxy for an event

**Seen in:** F7 (R2 cascade fires when "after insert, exactly one
interview" — conflating "this is the first interview ever" with "there
is currently one interview").

Junior: "the natural way to detect 'first interview' is to count — if
count == 1 after insert, it was the first." Senior: "counts change
under deletes; events are the better trigger." The spec's `AND status =
'[APPLIED]'` guard already encodes the promotion condition — the count
is redundant and actively wrong after a delete.

**Lesson.** In a state-machine cascade, trigger on the **event**
(a write that moves forward one stage) and guard on the **current
state** (`status = '[APPLIED]'`). Never trigger on a count that can
reset.

### P5. Unguarded terminal-state writes

**Seen in:** F8 (R3 promotes to `[OFFER]` unconditionally — including
from `[REJECTED]`).

Junior reasoning: "the happy path is linear, and this is a side
effect of a save; the user wouldn't enter `response_type = 'Offer'`
on a rejected position." This is the classic "bug-free on the paths
I imagined" trap. Terminal states exist precisely to reject
out-of-order edits.

**Lesson.** Any state-change rule should enumerate both the
intended transitions AND the `AND status NOT IN TERMINAL_STATUSES`
guard. Write the guard even if the happy path never hits it; the cost
is one SQL clause, the benefit is durability against weird sequences
(undo, manual SQL, import from backup).

### P6. Invariant assertions in prose instead of code

**Seen in:** F3 (STATUS_COLORS docstring says colors are "from the
overlap of st.badge palette and Plotly CSS vocabulary" but nothing
enforces it).

Junior reads the invariant, feels informed, moves on. Six months later
a new contributor opens `config.py`, sees `"blue"`, thinks "I'll use
`#4287f5` — more modern," and `st.badge()` silently falls back to
default styling in half the UI. No test catches it because the
invariant is in a markdown file, not an `assert`.

**Lesson.** Every invariant named "must" or "always" in DESIGN.md
should have a counterpart `assert` at the top of `config.py` or a
`test_config.py` test. If it's genuinely too expensive to enforce (e.g.,
"bar color must be perceptually distinct from adjacent bar"), label
the invariant **advisory-only** in the doc so the reader doesn't
expect runtime enforcement.

### P7. Load-bearing contracts restated in four places

**Seen in:** Con1 in my mental findings — "exports after writes" is
stated in §6.2 (schema notes), §7 (module contracts),
§9.1 (add flow), §9.5 (export pipeline), and §10 D4 (decision).

Junior reader follows a reference, lands in one of the four, and
assumes they've seen the whole contract. Three of the four are
summaries; only one (§7 or §9.5) has the full detail. Which one? Not
marked.

**Lesson.** For cross-cutting contracts, pick **one canonical home**
— typically §7 Module Contracts. Every other mention says "See §7.X"
and stops. Restating invites drift.

---

## 3. Junior-engineer Q&A

Questions a reader new to this project would ask, answered didactically.

### Q1. "DESIGN.md says `STATUS_VALUES` starts with `[SAVED]`, but `config.py` has `[OPEN]`. Which do I code against?"

**Answer.** Code against `config.py` — it's the live module. DESIGN.md
documents the **v1 target**; the `[OPEN]`→`[SAVED]` rename is a
deferred refactor (see [CHANGELOG.md](../CHANGELOG.md) "Deferred code
changes"). The rename will land with a one-shot `UPDATE positions SET
status = '[SAVED]' WHERE status = '[OPEN]'` migration on a separate
branch.

**Lesson.** In a doc-before-code refactor window, always ground
**tests** in the live module. If a test asserts against DESIGN's
target, it lies until the migration lands. If it asserts against the
current module, it remains truthful and the migration just updates
the test's expected value.

### Q2. "Why does `count_by_status()` return a sparse dict instead of a dense one?"

**Answer.** `SELECT status, COUNT(*) FROM positions GROUP BY status`
simply doesn't emit rows for groups with no members. The function is
honest to its SQL. The cost is on the consumer side: every caller has
to do `.get(status, 0)`.

**Lesson on the trade-off.** Two API shapes:
- **Sparse + consumer-fills:** truthful to SQL, burdens every caller,
  requires a test like `test_funnel_missing_statuses_render_as_zero_bars`
  to pin the behavior. One bug per consumer who forgets.
- **Dense + source-fills:** lies a tiny bit (it says "0 applications"
  as if it queried zero, but really it patched zero in), ergonomic for
  consumers, zero forgettable boilerplate.

DESIGN picks sparse-and-document. I'd pick dense-and-encode-in-type
(return a `Counter` or a `dict[Status, int]` where every status is a
key). But given the current tests pin sparse behavior, changing it is
a breaking refactor for Phase 5+, not a doc fix.

### Q3. "Why are R1, R2, R3 auto-promotion rules in `database.py` instead of `pages/2_Applications.py`?"

**Answer.** Four reasons, in increasing order of importance:

1. **Atomicity.** The promotion + the primary write share a single
   transaction. If the promotion fails, the write rolls back too.
2. **Testability.** Tests can hit `database.upsert_application()`
   without spinning up an AppTest harness.
3. **Uniform firing.** If you later add a CLI, a background job, or a
   data-import script, they all get the cascade for free — they're
   calling the same writer.
4. **Layer hygiene.** Page files are display-only (GUIDELINES §2).
   Business rules in pages mean the same rule gets re-implemented per
   page, differently each time.

This is D12 in §10.

**Lesson.** State-machine cascades belong in the layer that owns
state. Pages describe intent ("save this"); the data layer translates
intent into state transitions.

### Q4. "Why is the 🔄 Refresh button kept if Streamlit reruns on interaction?"

**Answer.** Two reasons:

1. **Passive view case:** if the user is on the dashboard and adds a
   position in another tab (Opportunities), nothing on the dashboard
   has triggered a rerun. Refresh is the manual override.
2. **One button is cheap.** The cost is one element of visual noise;
   the benefit is a recoverable user when Streamlit's auto-rerun
   hasn't fired.

That said, friend critique pushed to remove it (roadmap.md P1
backlog). `DESIGN §10 D13` — the *target* — already says "No 🔄
Refresh button on the dashboard top bar." The current code still has
one. Expect the deferred code refactor to delete it.

**Lesson.** UX decisions with soft benefits (override) and measurable
costs (visual noise) don't have one right answer. Document the
reasoning inline; revisit when real users hit the friction.

### Q5. "The Upcoming panel wireframe shows a Status column; the spec table lists 4 columns without it. Which is right?"

**Answer.** This is a doc drift (F10 in my findings). The wireframe
has 5 columns (Date, Label, Status, Kind, Urgency+emoji); the spec
table has 4 (Date, Label, Kind, Urgency). A user skimming Upcoming
almost certainly wants status — it's the difference between "I need
to apply by this date" and "I have an interview scheduled." I'd add
Status as the 5th column, or fold it into Label as
`"Stanford BioStats · Saved"`.

**Lesson.** When a wireframe and spec table conflict, don't silently
pick one — raise it. Spec tables are normative; wireframes are
orientational. A reconciliation PR is 10 lines; a silent-pick bug
is debugging at 2am three months later.

### Q6. "§12.1 says the schema is 'additive' across profile switches. Is this accurate?"

**Answer.** Partially. Columns are additive — adding a new profile's
columns via `ALTER TABLE ADD COLUMN` is safe, and existing rows keep
NULL in the new columns. But **vocabulary values are not additive**. If
`software_eng` replaces `STATUS_VALUES` entirely with `[BACKLOG,
APPLIED, PHONE, ONSITE, OFFER]`, then existing `[SAVED]` and
`[INTERVIEW]` rows become orphan values with no UI affordance.

The honest claim: **"Column schema is additive; vocabulary values
require a migration per profile pair."** Any profile switch
accompanied by a one-shot `UPDATE positions SET status = '<new>'
WHERE status = '<old>'` is fine. An unplanned switch is not.

**Lesson.** Reassurance words ("additive," "atomic," "safe") demand
a scope next to them. The unscoped claim invites a failure mode you
didn't think about.

### Q7. "§10 has D1–D25, but the ADR README says 'decisions in DESIGN §10 (D1–D10) — those are the original v1.0 decisions.' Is D11–D25 also frozen, or not?"

**Answer.** This is a contradiction between
[`docs/adr/README.md`](../docs/adr/README.md) and DESIGN §10. The
ADR README was drafted when §10 had ten rows; the refactor added D11–D25
(or those ranges were always there and the README writer miscounted).
Either way, the ADR README needs a one-line fix: change "D1–D10" to
"D1–D25 (frozen v1.0 decisions) — subsequent decisions land here as
ADR-NNNN."

**Lesson.** Documentation-about-documentation is a common drift site.
When you write "X is frozen at line Y," that claim dies as soon as
line Y changes. Prefer identifier-based references ("the D-numbered
rows in §10, inclusive of the current range") over numeric ranges.

### Q8. "Why does DESIGN.md define `STATUS_LABELS` and `FUNNEL_BUCKETS` in §5 but the live `config.py` has neither?"

**Answer.** DESIGN.md is the **v1 target spec** — it describes what
`config.py` will look like at v1.0.0 release. The live `config.py`
is mid-refactor (T1 carve-out added `STATUS_OPEN/APPLIED/INTERVIEW`
aliases; the `STATUS_LABELS` and `FUNNEL_BUCKETS` additions are
deferred per CHANGELOG "Deferred code changes"). The top of DESIGN.md
explicitly flags this: *"This document is the authoritative design
specification. It describes the target design for v1."*

**Lesson.** When reading a spec labeled "target," your first question
should be "which parts are live and which are deferred?" The CHANGELOG
"Unreleased" section is the answer. DESIGN.md could help by adding a
**status badge per major block** (e.g., `[Live]` or `[Target v1.0]`)
so a reader gets that signal without cross-referencing — but this is
polish, not a blocker.

---

## 4. What DESIGN.md does well (so the user knows which patterns to keep)

Not every review paragraph should be a correction. These are the things I'd
not want an editor to remove:

1. **The import-time invariants block (§5.2).** Eight runtime-enforced
   assertions that catch drift at `config.py` import, not at page render. Most
   docs describe invariants in prose and hope. This one compiles them down to
   `assert` statements. Keep this pattern and extend it (see F3, F6).
2. **The migration taxonomy (§6.3).** Splitting schema evolution into
   "auto-migrated / manual / breaking" with a concrete SQL recipe per row is
   senior-level work. A junior would either say "we'll figure it out at
   migration time" or list everything as manual. The three-tier table tells a
   future developer exactly which category their change falls into.
3. **The decision log (§10) as a reference artifact.** Even with the
   granularity critique (F13), the habit of writing D-numbered decisions with
   `Decision | Rationale | Alternative rejected` is golden. The "alternative
   rejected" column is particularly valuable — it stops the next person from
   reopening the same question.
4. **The Extension Guide (§11) as a recipe book.** Most design docs describe
   the state; this one tells you how to *change* the state. "Add a new
   requirement document" → three concrete steps → done. This is the correct
   unit of documentation for a project where config.py is the extension
   surface.
5. **The v2 forward notes (§12) with explicit "this informs v1"
   callouts.** §12.4 saying "v1's quick-add should accept a `prefill: dict`
   parameter shape (a two-line change today) so the v2 AI module wires in
   without restructuring the page" — *that's* the right way to forward-engineer.
   Not "we'll build this later," but "v1 should expose this hook so v2 doesn't
   cost a refactor."

---

## 5. Summary of recommended edits (priority-ordered)

| Priority | Item | Effort | Finding |
|----------|------|--------|---------|
| 1 (before Phase 5) | Rewrite R2 auto-promotion rule without "exactly one" count | ~5 min | F7 |
| 1 (before Phase 5) | Add terminal-status guard to R3 | ~5 min | F8 |
| 1 (before Phase 5) | Broaden funnel empty-state trigger to cover "no visible bars" OR explicitly accept the terminal-only-DB UX | ~10 min | F4 |
| 1 (before Phase 5) | Rewrite §5.2 invariant #5 as executable pseudocode | ~5 min | F2 |
| 2 (v1.4 clarity pass) | Fix hero-trigger triple-call in §8.1 | ~2 min | F6 |
| 2 (v1.4 clarity pass) | Reconcile Upcoming wireframe vs. spec table | ~10 min | F10 |
| 2 (v1.4 clarity pass) | Scope §12.1 additivity claim; add FUNNEL_BUCKETS expansion recipe | ~15 min | F15 |
| 2 (v1.4 clarity pass) | Fix §6.2 trigger recursive_triggers phrasing | ~5 min | F12 |
| 2 (v1.4 clarity pass) | Update ADR README from "D1–D10" to current range | ~2 min | (crosses F8 boundary — not in DESIGN itself but affects reader) |
| 3 (polish) | Group §10 into 10.1/10.2/10.3 sub-headers | ~15 min | F13 |
| 3 (polish) | Replace §6.4 with pointer table to §10 | ~10 min | F14 |
| 3 (polish) | Add §1.4 Architectural non-goals | ~10 min | F17 |
| 3 (polish) | Expand §8.0 with layout/loading/narrow conventions | ~15 min | F16 |
| 3 (polish) | Document STATUS_COLORS invariant as advisory or add assertion | ~5 min | F3 |
| 3 (polish) | Materials Readiness denominator: clarify intent | ~2 min | F11 |
| 3 (polish) | Funnel zero-count visible-bucket semantics | ~2 min | F5 |
| 3 (polish) | R1+R3 co-firing micro-table | ~5 min | F9 |
| 3 (polish) | §1 Solution forward-pointer to §8.1 | ~1 min | F1 |

Total effort for priorities 1–2: **~90 min** (one focused session).
Total for priorities 1–3: **~2.5 hr**.

---

## 6. Closing note

DESIGN.md v1.3 is a document I'd be happy to hand to a new contributor
tomorrow. The findings above are refinements on a genuinely strong base,
not corrections to a flawed one. Treat the 🔴 priority items as
**Phase 5 unblockers** (the auto-promotion rules will be exercised for
the first time when `pages/2_Applications.py` ships), and the rest as
optional polish for a v1.4 clarity pass.

The **most important** lessons to internalize — those that generalize
beyond this project — are:

- **Write invariants as code, not prose** (P6). If `assert` can catch it,
  don't rely on a human reader to remember the rule.
- **Empty-states track presentation, not data** (P2). The user sees
  what's rendered, not what's in the DB.
- **Scope reassurance words** (P3). "Additive" is precise; scope it
  explicitly or drop it.
- **Cascades guard on state, trigger on events** (P4). Never count.
- **Terminal states are terminal** (P5). Always guard against them in
  forward-promotion rules.

Verdict: **Approve with nits.** Four 🔴 priority items before Phase 5;
the rest can land in a single v1.4 clarity pass.

---
_End of review._
