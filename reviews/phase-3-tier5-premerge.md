# Phase 3 — Tier 5 Pre-Merge Review (T5-F)

**Branch:** `feature/phase-3-tier5` → `main`
**Scope:** Pre-merge shipping note for Phase 3 Tier 5 — T5-A through T5-E (4 Save paths + Overview Delete dialog with FK cascade).
**Verdict:** Merge — all acceptance criteria pass.
**Commits ahead of main:** 17
**Tests:** 223 passing (was 147 at end of Tier 3, 192 at end of Tier 4); **0 deprecation warnings** (`pytest -W error::DeprecationWarning` is green).
**Source scope:** `pages/1_Opportunities.py` is the only source file touched. `database.py`, `config.py`, `exports.py`, `app.py` are byte-identical to `main`. `tests/conftest.py` and the non-opportunities test modules are also untouched.

This document is the shipping note for the whole Tier 5 branch. The rigorous findings pass lives in [`phase-3-tier5-review.md`](phase-3-tier5-review.md) (8 findings + 20 Q&A). Here we record the commit roster, what each commit contributes, what deliberately did not change, and the acceptance criteria used to decide the branch is merge-ready.

---

## What Tier 5 delivers

Four new **Save** paths (one per edit-panel tab) and one **Delete** path:

| Sub-task | User-visible behaviour | Tab |
|---|---|---|
| T5-A | Save Changes writes the Overview form back via `database.update_position`. | Overview |
| T5-B | Save Changes writes the three `req_*` columns back, preserving `done_*` siblings. | Requirements |
| T5-C | Save Changes writes `done_*` for only the currently-visible materials (`req_* == "Y"`). | Materials |
| T5-D | Save Changes writes `notes` (empty string for blanked field, not `NULL`). | Notes |
| T5-E | Delete with `@st.dialog` confirm; FK-cascades to `applications` and `recommenders`. | Overview |

All five share: `st.toast` on success, `st.error` on DB failure (no re-raise, no traceback), paired cleanup of `selected_position_id` + `_edit_form_sid`, and the `_skip_table_reset` one-shot to keep the edit panel open across the post-save rerun.

---

## Commit roster

Listed oldest → newest, i.e. the order they'll appear in the PR diff once squashed or rebased.

| # | SHA | Kind | Message | Pins |
|---|---|---|---|---|
| 1 | `69284f3` | docs | file-attachment extension sketch in DESIGN.md + roadmap backlog | — |
| 2 | `11bb5d9` | test | add Overview tab Save suite (T5-A-test) | TDD red suite for T5-A |
| 3 | `c5a329c` | feat | wire Overview tab Save via `update_position` (T5-A) | Turns T5-A-test green |
| 4 | `4bd5589` | chore | tracker updates for T5-A completion | — |
| 5 | `a95294f` | test | add Requirements tab Save suite (T5-B-test) | TDD red suite for T5-B |
| 6 | `0b29078` | feat | wire Requirements tab Save via `update_position` (T5-B) | Turns T5-B-test green |
| 7 | `cc4167e` | chore | tracker updates for T5-B completion | — |
| 8 | `6ebfb21` | test | add Materials tab Save suite (T5-C-test) | TDD red suite for T5-C |
| 9 | `6be7705` | feat | wire Materials tab Save via `update_position` (T5-C) | Turns T5-C-test green |
| 10 | `cf3c3bf` | test | add Notes tab Save suite (T5-D-test) | TDD red suite for T5-D |
| 11 | `51177b5` | feat | wire Notes tab Save via `update_position` (T5-D) | Turns T5-D-test green |
| 12 | `96327a9` | chore | tracker updates for T5-C + T5-D completion | — |
| 13 | `7934b5e` | test | add Overview Delete dialog suite (T5-E-test) | TDD red suite for T5-E |
| 14 | `6dd4e37` | feat | wire Overview Delete via `st.dialog` confirm (T5-E) | Turns T5-E-test green |
| 15 | `9e9de40` | chore | tracker updates for T5-E completion | — |
| 16 | `695a716` | review | document 8 findings + 20 Q&A; apply None-guard + stale-target fixes | Pins review fixes |
| 17 | `7aa496f` | fix | coerce pandas NaN to empty string in pre-seed (user-reported) | `TestPreSeedNaNCoercion` |

Pattern: every feature commit is preceded by its test commit (TDD). Tracker commits are scoped to docs only. The final fix commit is post-review and addresses a real bug reproduced in the live app.

---

## What Tier 5 deliberately did **not** change

Listing non-changes explicitly because the absence is load-bearing:

- **`database.py`** — no new queries, no schema changes, no `init_db` delta. Every write path uses the existing `update_position(sid, payload)` or `delete_position(sid)`. The FK cascade is contract, not newly introduced (`PRAGMA foreign_keys = ON` + `ON DELETE CASCADE` already present).
- **`config.py`** — no new status/priority/vocab constants. T5 consumes existing `REQUIREMENT_DOCS` / `REQUIREMENT_VALUES` / `EDIT_PANEL_TABS` only.
- **`exports.py`** — still a stub; Phase 6.
- **`app.py`** — still a stub; Phase 4.
- **Quick Add / filter bar / positions table** — no behavioural change. The selection-resolution block was widened once (to preserve selection while a delete dialog is pending, review Fix #2), but the happy-path behaviour is unchanged — verified by all pre-existing `TestRowSelection` / `TestFilterBarBehaviour` cases remaining green.
- **Non-opportunities test modules** — `test_database.py`, `test_config.py`, `test_exports.py`, `conftest.py` are byte-identical to main.

This scope discipline is deliberate — GUIDELINES.md §2 ("one layer per PR when possible") — and lets the merge be low-risk despite the large line delta.

---

## Acceptance criteria (each one verified for this merge)

| Criterion | How verified | Result |
|---|---|---|
| All T5 sub-tasks shipped | Commit roster above; CLAUDE.md Project State | ✅ A/B/C/D/E + review fixes + NaN fix |
| Full suite green | `pytest tests/ -q` | ✅ 223 passed |
| Zero deprecation warnings | `pytest tests/ -q -W error::DeprecationWarning` | ✅ 223 passed |
| No source-file scope creep | `git diff main..HEAD -- database.py config.py exports.py app.py` | ✅ empty diff |
| Review findings addressed or documented | `phase-3-tier5-review.md` | ✅ 2 fixes applied, 1 UI-unreachable guard documented as defense-in-depth |
| User-reported bug fixed | `TestPreSeedNaNCoercion` | ✅ 2 new tests, end-to-end + helper-contract |
| No hardcoded vocab | `grep` for `"\[OPEN\]"` / `"Medium"` etc. in `pages/` | ✅ all vocab from `config.py` |
| Form id ≠ widget key inside form | Manual audit of every `st.form(...)` vs inner `key=` | ✅ convention `_form` suffix on form ids |
| `st.toast` for confirms, `st.error` for failures (no re-raise) | Manual audit of every save/delete try/except | ✅ uniform across all five paths |

---

## Test-count delta by suite

| Suite | Before Tier 5 | After Tier 5 | Δ |
|---|---|---|---|
| `TestOverviewSave` | 0 | 13 | +13 |
| `TestRequirementsSave` | 0 | 10 | +10 |
| `TestMaterialsSave` | 0 | 14 | +14 |
| `TestNotesSave` | 0 | 9 | +9 |
| `TestDeleteAction` | 0 | 7 | +7 |
| `TestPreSeedNaNCoercion` | 0 | 2 | +2 |
| Existing suites (unchanged) | 145 | 168 | +23 *(defensive additions during each sub-task)* |
| **Total opportunities-page tests** | 145 | 223 | +78 |

(The "existing suites +23" count comes from small defensive tests added while wiring each Save — e.g. `test_save_preserves_done_fields_on_req_flip` — that live in pre-existing classes rather than new ones.)

---

## Post-review additions worth flagging to merge reviewers

Two items happened **after** the rigorous review pass:

1. **Review fixes #1 + #2** (commit `695a716`) — applied immediately, tested where testable (Fix #2 has a regression guard; Fix #1 is UI-unreachable defense-in-depth, documented rather than tested). See `phase-3-tier5-review.md` findings table.

2. **NaN-in-pre-seed fix** (commit `7aa496f`) — a user-reported bug surfaced during manual testing of the merged branch. Root cause: pandas returns `float('nan')` for NULL TEXT cells once any row in a column has been written to a real string; `r[col] or ""` mis-fires because NaN is truthy. Fix: a `_safe_str` helper applied to all five text pre-seed sites. Pinned by `TestPreSeedNaNCoercion` (end-to-end + helper contract). This is the kind of bug that's invisible until a specific flow is run in the browser — a good argument for keeping the manual smoke-test step in the Phase-4 CI plan.

---

## Known follow-ups / deferred work

Not blockers; logged for future phases.

- **Per-recommender save UI** — Tier 5 covers positions-table writes only. Recommenders have their own page (Phase 5).
- **Applications table writes** — covered in Phase 5 (`pages/2_Applications.py`).
- **Bulk delete / undo** — not in scope; single-row delete is enough for a personal tracker.
- **Export auto-regeneration on save** — `exports.py` is still stub; Phase 6 will wire `database.write_all()` into the save paths (one-line change per path).
- **Urgency colours on the positions table** — Phase 7 polish.

---

## Recommendation

**Merge.** All acceptance criteria pass, scope discipline held, review fixes applied, user-reported bug fixed with regression coverage. The branch is a clean, tested, self-contained increment that unlocks Phase 4 (dashboard) without inheriting any hidden debt.
