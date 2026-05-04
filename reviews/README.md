# Reviews

Pre-merge review docs, one per tier (with occasional one-off bug-fix and
DESIGN review docs). Maintained per `GUIDELINES §10` (review structure)
and `GUIDELINES §14.7` (this index, naming convention).

**Naming.** Tier reviews follow `phase-<N>-tier<M>-review.md` (lowercase
`tier`); date-stamped one-offs follow `<topic>-YYYY-MM-DD-review.md`.
Mixed casing in legacy filenames is left alone — new files conform.

**Front-matter.** Every review opens with `**Branch:**` · `**Scope:**` ·
`**Stats:**` (optional) · `**Verdict:**` per `GUIDELINES §14.1`.
Pre-existing extras (Reviewer attitude, Cadence, Method, Date, etc.)
follow.

---

## Index (reverse chronological)

| Date | Scope | Branch | Verdict | Link |
|---|---|---|---|---|
| 2026-05-04 | Phase 6 finish — cohesion smoke + close-out (T6 — `v0.7.0` tag) | _(direct-to-main; orchestrator close-out doc)_ | Approve `v0.7.0` tag | [phase-6-finish-cohesion-smoke.md](phase-6-finish-cohesion-smoke.md) |
| 2026-05-04 | Phase 6 T5 — Export page download buttons + Download section header | `feature/phase-6-tier5-DownloadButtons` | Approve | [phase-6-tier5-review.md](phase-6-tier5-review.md) |
| 2026-05-04 | Phase 6 T4 — Export page shell + manual regenerate button + mtimes panel | `feature/phase-6-tier4-ExportPage` | Approve | [phase-6-tier4-review.md](phase-6-tier4-review.md) |
| 2026-05-04 | Phase 6 T3 — `write_recommenders()` markdown generator + smoke-test fixture fix that closed CI-red regression | `feature/phase-6-tier3-WriteRecommenders` | Approve | [phase-6-tier3-review.md](phase-6-tier3-review.md) |
| 2026-05-04 | Phase 6 T2 — `write_progress()` markdown generator + conftest fixture lift | `feature/phase-6-tier2-WriteProgress` | Approve | [phase-6-tier2-review.md](phase-6-tier2-review.md) |
| 2026-05-04 | Phase 6 T1 — `write_opportunities()` markdown generator | `feature/phase-6-tier1-WriteOpportunities` | Approve | [phase-6-tier1-review.md](phase-6-tier1-review.md) |
| 2026-05-04 | Phase 5 finish — cohesion smoke + close-out (T7 — `v0.6.0` tag) | _(direct-to-main; orchestrator close-out doc)_ | Approve `v0.6.0` tag | [phase-5-finish-cohesion-smoke.md](phase-5-finish-cohesion-smoke.md) |
| 2026-05-04 | Phase 5 T6 — Recommender reminder helpers (Compose mailto + LLM prompts expander) | `feature/phase-5-tier6-RecommenderReminders` | Approve | [phase-5-tier6-review.md](phase-5-tier6-review.md) |
| 2026-05-03 | Phase 5 T5 — Recommenders table + filters + Add form + inline edit + dialog Delete | `feature/phase-5-tier5-RecommendersTableAddEdit` | Approve (post-merge) | [phase-5-tier5-review.md](phase-5-tier5-review.md) |
| 2026-04-30 | Phase 5 T4 — Recommenders page shell + Pending Alerts panel | `feature/phase-5-tier4-RecommendersAlertPanel` | Approve | [phase-5-tier4-review.md](phase-5-tier4-review.md) |
| 2026-04-30 | Phase 5 T3 — Inline interview list UI (T3-A + T3-B + T3-rev) | `feature/phase-5-tier3-InterviewManagementUI` | Approve | [phase-5-Tier3-review.md](phase-5-Tier3-review.md) |
| 2026-04-30 | Phase 5 T2 — Application detail card (T2-A + T2-B) | `feature/phase-5-tier2-ApplicationDetailCard` | Approve, merge after the inline test-logic fix lands | [phase-5-Tier2-review.md](phase-5-Tier2-review.md) |
| 2026-04-30 | Phase 5 T1 — Applications page shell | `feature/phase-5-tier1-ApplicationsPageShell` | Approve | [phase-5-tier1-review.md](phase-5-tier1-review.md) |
| 2026-04-30 | Phase 4 T6 — Cross-panel cohesion smoke (audit doc) | `feature/phase-4-tier6-Cohesion` | Approve cohesion claim; capture screenshots | [phase-4-finish-cohesion-smoke.md](phase-4-finish-cohesion-smoke.md) |
| 2026-04-30 | Phase 4 T6 — Dashboard close-out (review doc) | `feature/phase-4-tier6-Cohesion` | Approve, merge after inline footnote + PNGs | [phase-4-Tier6-review.md](phase-4-Tier6-review.md) |
| 2026-04-30 | Phase 4 T5 — Recommender Alerts panel | `feature/phase-4-tier5-RecommenderAlerts` | Approve, merge after inline polish + boundary test | [phase-4-Tier5-review.md](phase-4-Tier5-review.md) |
| 2026-04-29 | Phase 4 T4 — Upcoming timeline panel | `feature/phase-4-tier4-UpcomingDeadline` | Approve, merge after inline polish | [phase-4-Tier4-review.md](phase-4-Tier4-review.md) |
| 2026-04-25 | Opportunities-page bug-fix round (Sub-task 13 revert) | `review/test-reliability-2026-04-25` | Approve with two doc-drift nits (fixed in review) | [opportunities-page-bug-fix-2026-04-25-review.md](opportunities-page-bug-fix-2026-04-25-review.md) |
| 2026-04-23 | DESIGN v1.3 — second pass | `feature/docs-refactor-pre-t4` | Approve current state; address 🔴/🟠 in v1.4 cleanup | [DESIGN-review-2026-04-23-second-pass.md](DESIGN-review-2026-04-23-second-pass.md) |
| 2026-04-23 | DESIGN v1.3 — first pass | `feature/docs-refactor-pre-t4` | Approve with nits; address 🔴 (F2/F4/F7/F8) before Phase 5 | [DESIGN-review-2026-04-23.md](DESIGN-review-2026-04-23.md) |
| 2026-04-22 | Phase 4 T3 — Materials Readiness panel | `feature/phase-4-tier3-MaterialReadiness` | Approve, merge | [phase-4-Tier3-review.md](phase-4-Tier3-review.md) |
| 2026-04-22 | Phase 4 T2 — Application Funnel panel | `feature/phase-4-Tier2-ApplicationFunnel` | Acceptance gate met; findings #1 + #2 applied | [phase-4-Tier2-review.md](phase-4-Tier2-review.md) |
| 2026-04-21 | Phase 4 T1 — Dashboard shell + KPI grid | `feature/phase-4-tier1` | T1 mergeable in isolation; packaged at T6 | [phase-4-Tier1-review.md](phase-4-Tier1-review.md) |
| 2026-04-20 | Phase 3 T5 — Pre-merge shipping note (T5-A → T5-E) | `feature/phase-3-tier5` → `main` | Merge | [phase-3-tier5-premerge.md](phase-3-tier5-premerge.md) |
| 2026-04-20 | Phase 3 T5 — Code review (T5-A → T5-E) | `feature/phase-3-tier5` | Request changes → approved after Fix #1 + #2 | [phase-3-tier5-review.md](phase-3-tier5-review.md) |
| 2026-04-19 | Phase 3 T4 — Full review (T4-A → T4-F) | `feature/phase-3-tier4` | Approve with F1–F3 applied + F7 pinned; F4–F6 accepted | [phase-3-Tier4-full-review.md](phase-3-Tier4-full-review.md) |
| 2026-04-19 | Phase 3 T4-A/B/C — Row selection + edit-panel + Overview tab | `feature/phase-3-tier4` | Approve with fixes F1–F6 applied | [phase-3-Tier4-ABC-review.md](phase-3-Tier4-ABC-review.md) |
| 2026-04-18 | Phase 3 T2 + T3 — Filter bar + positions table | _(direct-to-main; pre-branch-workflow)_ | Request Changes (5 findings, all fixed) | [phase-3-Tier2&3-review.md](phase-3-Tier2&3-review.md) |
| 2026-04-17 | Phase 3 T1 — Quick-Add form + empty state | _(direct-to-main; pre-branch-workflow)_ | Request Changes (5 findings, all fixed) | [phase-3-review.md](phase-3-review.md) |
| 2026-04-16 | Phase 2 — `database.py` + `exports.py` | _(direct-to-main; pre-branch-workflow)_ | Approved with fixes applied | [phase-2-review.md](phase-2-review.md) |
| 2026-04-16 | Phase 1 — environment + `config.py` + `requirements.txt` | _(direct-to-main; pre-branch-workflow)_ | Approved with fixes applied | [phase-1-review.md](phase-1-review.md) |

---

## How to add a new entry

When a new review doc lands:

1. Make sure the review file's front-matter conforms to `GUIDELINES §14.1` (Branch · Scope · Stats opt · Verdict).
2. Prepend a row to the table above with the date, scope, branch, verdict (one-line summary), and a link to the file.
3. Commit alongside the review itself — the index update is part of the same logical change.
