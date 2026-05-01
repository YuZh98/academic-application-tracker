# Architectural Decision Records

This folder holds **Architectural Decision Records** (ADRs) — one file per decision —
documenting *why* the Postdoc Tracker is built the way it is.

---

## What an ADR is (and what it isn't)

An ADR captures a **single architectural decision** at the moment it is made.
It is **not** a specification, a bug report, or a tutorial. The format is
deliberately short so that writing one is cheap.

Every ADR answers three questions:

| Section | Answers |
|---------|---------|
| **Context** | What problem are we solving? What forces are in play? |
| **Decision** | What did we choose, and what did we reject? |
| **Consequences** | What becomes easier? What becomes harder? What do we accept as trade-offs? |

ADRs are **immutable once accepted** — if the decision later reverses, you write a
**new** ADR that supersedes the old one. The original stays in git history as a
record of *why* the project once believed something different.

---

## When to write an ADR

Write an ADR when the decision is:
- **Architectural** — affects the shape of modules, data flow, or dependencies.
- **Hard to reverse** — changing it later would require migration or refactoring.
- **Contested** — at least one reasonable alternative exists.

If the answer to "would a future contributor ask *why* was this chosen?" is yes,
write an ADR.

**Don't** write an ADR for:
- Implementation details that could go either way (variable naming, file layout
  within a module).
- Decisions already captured in `DESIGN §10` D1–D10 — those are the original
  v1.0 decisions, frozen for historical continuity. (`DESIGN §10` D11–D25
  are post-v1.1 additions to the same section that pre-date the ADR ledger;
  see "Status of post-v1.1 architectural decisions" below.)
- Phase-local decisions (P3-D1, P4-D1, etc.) — those live in phase review docs
  under `reviews/`.

---

## Numbering and naming

Files use the pattern `ADR-NNNN-short-kebab-title.md`, where `NNNN` is a
zero-padded monotonic integer starting at `0001`. Use the next free number;
never reuse numbers.

Examples:
- `ADR-0001-presentation-storage-split-for-statuses.md`
- `ADR-0002-soft-delete-for-positions.md`
- `ADR-0003-ai-ingestion-boundary.md`

Keep titles under 7 words and descriptive — a reader scanning the folder should
understand the decision from the filename alone.

---

## Status lifecycle

Every ADR carries a `Status:` line at the top. Valid values:

| Status | Meaning |
|--------|---------|
| **Proposed** | Drafted; awaiting discussion / approval. |
| **Accepted** | In force. The codebase reflects this decision. |
| **Deprecated** | No longer followed but not replaced by a new decision. |
| **Superseded by ADR-NNNN** | Explicitly replaced. The new ADR links back. |

Move from Proposed → Accepted in the same commit that ships the code realizing
the decision (or the doc refactor that codifies it).

---

## Template

Copy the block below into a new file. Fill each section; leave no placeholder text.

```markdown
# ADR-NNNN: <Short noun-phrase title>

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-MMMM
**Date:** YYYY-MM-DD
**Deciders:** <names or roles>

## Context

<2-5 sentences. What is the situation? What forces are at play?
Describe the problem honestly; do not argue for the conclusion yet.>

## Decision

<1-3 sentences stating the chosen option in the imperative present tense.
"We will X." "Status labels are stripped at the presentation layer.">

## Options Considered

### Option A — <name>  (chosen | rejected)
Pros: <list>
Cons: <list>

### Option B — <name>  (chosen | rejected)
Pros: <list>
Cons: <list>

<add more as needed>

## Consequences

- What becomes easier:
- What becomes harder:
- What we accept as a trade-off:
- What we'll need to revisit:
```

---

## How ADRs relate to other decision records in this repo

| System | Scope | Lives in |
|--------|-------|----------|
| **`DESIGN §10` D1–D10** | Original v1.0 architectural decisions (frozen v1.0 batch) | `DESIGN.md` |
| **`DESIGN §10` D11–D25** | Post-v1.1 decisions made before the ADR ledger was active (candidate ADR backfills) | `DESIGN.md` (see ADR backfill note below) |
| **Phase decisions (P3-D1, P4-D1, ...)** | Phase-local implementation choices | `reviews/phase-*.md`, `CLAUDE.md` (internal) |
| **ADR-NNNN (this folder)** | All architectural decisions **from v1.1 forward** | `docs/adr/` |

A decision belongs in exactly one place. If uncertain: ADR wins for anything
architectural; phase review wins for anything implementation-local.

---

## Current ADRs

_(empty — this folder was created at v1.1 refactor per the "empty + forward-only"
policy; existing D1–D10 decisions (and the post-v1.1 D11–D25 additions to
`DESIGN §10`) were not backfilled. New ADRs land here as decisions are made.)_

## Status of post-v1.1 architectural decisions (note 2026-04-30)

Several post-v1.1 decisions whose scope qualifies them as ADRs (cross-cutting
architectural choices, hard to reverse, with viable alternatives) currently
live elsewhere — `DESIGN §10` (D11–D25), `CHANGELOG.md` `[Unreleased]`, and
review docs. Some examples (not exhaustive):

- The `st.tabs` mandate post-Sub-task-13 reversal (`DESIGN §8.2`)
- The R1/R2/R3 cascade-in-database design (`DESIGN §9.3`, was C13 deferred from v1.1)
- The `DESIGN §8.3` D-A amendment (Confirmation column inline-text vs per-cell tooltip; recorded in `reviews/phase-5-tier1-review.md` and dev-note gotcha #16)

The project owner will backfill these as ADRs in a future cleanup tier
(post-v1.0). The forward-only policy still applies: new cross-cutting
architectural decisions from this point on should land in `docs/adr/`
(using the template above) rather than only in `DESIGN §10` or review docs.
