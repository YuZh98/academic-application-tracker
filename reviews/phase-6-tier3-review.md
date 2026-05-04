**Branch:** `feature/phase-6-tier3-WriteRecommenders`
**Scope:** Phase 6 T3 — `exports.write_recommenders()` markdown generator + smoke-test fixture fix that closed the CI-red regression introduced by T1 + T2 (`exports.py`, `tests/test_exports.py`)
**Stats:** 14 new tests in `TestWriteRecommenders` (801 → 815 passed, 1 xfailed unchanged); +489 / −4 lines across 2 files; ruff clean; status-literal grep 0 lines; **standing isolation gate** empty post-pytest; **CI-mirror local check** passes (815 + 1 xfailed with `postdoc.db` moved aside); **`Tests + Lint (3.14)` CI conclusion: SUCCESS** (verified per the new `c284c20` procedure before admin-bypass)
**Verdict:** Approve

---

## Executive Summary

T3 ships in three commits — the standard `test:` + `feat:` pair plus
a `fix:` amendment that resolved the CI-red regression that had been
shipping silently since T1. The `write_recommenders()` generator
itself is straightforward (mirror of T1 + T2 architecture); the
load-bearing review work is the `fix:` commit on the same branch.

**Generator (commits `2a5e317` / `efecb3d`).** Reads
`database.get_all_recommenders()` and writes a single 8-column
markdown table to `exports/RECOMMENDERS.md`. Column contract is
locked by the `TestWriteRecommenders` class: Recommender ·
Relationship · Position · Institute · Asked · Confirmed · Submitted ·
Reminder. **`notes` deliberately omitted** — free-form prose is
awkward in a markdown table cell; if a future revision wants to fold
notes in, the natural shape is a per-recommender section with
bullets, not a table column. Two helper-reuse decisions land cleanly:
**Confirmed** uses a NEW local `_format_confirmed` helper (`—` /
`No` / `Yes` tri-state) per the DESIGN §2 layer rule (pages and
exports cannot share helpers; the page module imports streamlit
which `exports.py` is forbidden from transitively pulling in);
**Reminder** REUSES the existing `exports._format_confirmation`
helper because the `(reminder_sent, reminder_sent_date)` pair has
the same `(flag, date)` shape as the Applications-page Confirmation
pattern (DESIGN §8.3 D-A T1-C precedent). Reusing rather than
building a parallel "almost identical but subtly different" helper
keeps cell formats coherent. Sort: `recommender_name ASC,
deadline_date ASC NULLS LAST, id ASC` — primary groups one person's
owed letters together; secondary orders multiple positions for the
same recommender by upcoming-ness; tertiary is the deterministic
tiebreaker. `database.get_all_recommenders()` SQL covers keys 1 + 3
only; `deadline_date` is merged in pandas from
`database.get_all_positions()` here in the writer (mirror of T2's
"compose multiple reads in `exports.py`" precedent), then re-sorted
with `kind="stable"` so a future upstream change to either reader
doesn't silently break the export's row order.

**Smoke-test fix (commit `2439b4f`).** The orchestrator's CI review
caught three smoke tests at the top of `tests/test_exports.py`
(`test_write_*_does_not_raise`) failing on CI with `sqlite3.Operational
Error: no such table: positions` / `recommenders`. Root cause: the
`isolated_exports_dir` fixture monkeypatched only `exports.EXPORTS_DIR`,
not `database.DB_PATH`. Post-Phase 6 the writers all read the DB;
without DB isolation the unpatched `database.DB_PATH` fell through to
the developer's real `postdoc.db` locally (silent pass) but hit a
fresh empty sqlite on CI (where there is no `postdoc.db`). The
implementer's fix moves the DB monkeypatch + `init_db()` into
`isolated_exports_dir` itself — five consumers (three smoke tests +
two `write_all` behaviour tests) get full DB + exports isolation by
default, mirror of the Phase 6 T2 conftest `db` lift. Cleaner than
the "delete the redundant smoke tests" recommendation in the
orchestrator's hand-back message because it preserves the smoke tests
as a coverage layer above the per-class `TestWriteX::test_empty_db_*`
tests AND fixes the gap once for every consumer.

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `exports.py` `write_recommenders` `notes` column omission | The recommenders schema carries a `notes` TEXT column that the in-app UI exposes as an editable text-area, but the export does not surface it. Implementer's reasoning (commit body): "Recommender notes are typically free-form prose that's awkward in a markdown table cell; the in-app UI carries them, the export summarises." Defensible — markdown tables cap cell width naturally and a multi-paragraph notes field would either truncate or wrap badly. The fold-in alternative (per-recommender section with bullets) is acknowledged as the future shape if the user wants notes in the export. | ℹ️ | Kept-by-design. Cite-able if a future Phase 7 polish wants to expose notes in a non-table form. |
| 2 | `exports.py` `write_recommenders` deadline merge | `database.get_all_recommenders()` SQL ORDER BY only covers `recommender_name ASC, id ASC`; the secondary `deadline_date` sort key is not in the upstream reader. Implementer merges `deadline_date` from `database.get_all_positions()` (trimmed to `(id, deadline_date)`) inside the writer rather than amending the SQL. Defensible — adds one line of pandas in the writer vs touching the DB layer for a single sort-key need; mirror of T2's precedent. The pandas re-sort with `kind="stable"` defends against either upstream reader's ORDER BY changing in the future. | ℹ️ | Kept-by-design. |
| 3 | `tests/test_exports.py::isolated_exports_dir` post-fix shape | Post-fix, `isolated_exports_dir` is functionally equivalent to the conftest `db` fixture except for its return value (the `tmp_path / "exports"` path that smoke tests need). Two paths to the same isolation pattern in the same suite is a minor non-DRY signal. Lifting `isolated_exports_dir` into conftest as a thin wrapper around `db` (the same shape `db_and_exports` already uses) would consolidate; today the implementer's choice keeps it page-local because consumers are all within `test_exports.py`. | ℹ️ | Defer. If Phase 6 T4 / T5 (Export page tests) want the fixture, lift then; today single-file consumer = local. |
| 4 | Process | The CI-mirror local check (`mv postdoc.db postdoc.db.bak && pytest && mv postdoc.db.bak postdoc.db`) — codified in `c284c20` — would have caught this gap pre-push if the gate had been in `AGENTS.md` before T1 started. Implementer's `fix:` commit confirms the gate now does its job: the local check passes 815 + 1 xfailed with no `postdoc.db` at the project root, matching CI. | ℹ️ | The gate is now standing for every future PR. |

*No 🔴 / 🟠 / 🟡 findings.*

---

## Junior-Engineer Q&A

**Q1. Why does `write_recommenders` exclude the `notes` column when the in-app UI exposes notes for editing?**

A. Markdown tables impose visual constraints that work poorly for free-form prose. The notes cell is typed by the user with no length limit — multi-sentence reflections about a recommender are common ("met at SfN 2024, recommended me to her old advisor"). In a fixed-pitch markdown table, that cell either (a) wraps awkwardly across multiple lines (breaking the table grid), or (b) gets truncated by every renderer that auto-formats cell widths. Both outcomes degrade the export's "version-controlled human-readable backup" purpose. The implementer's reasoning in the commit body — "the in-app UI carries them, the export summarises" — acknowledges this honestly: the export is a snapshot of the structured fields (dates, statuses, names) where markdown tables shine, and the UI is the working surface for free-form text. If a future user wants notes in the backup, the natural reshape is a per-recommender section with the table row + the notes as a bulleted paragraph below — which would land alongside a DESIGN §7 amendment.

**Q2. Why merge `deadline_date` from a second SQL reader (`get_all_positions()`) in the writer rather than amending `get_all_recommenders()` to include it?**

A. Three reasons. (1) `get_all_recommenders()` is consumed by `pages/3_Recommenders.py` (the All Recommenders table) which already has an explicit column contract — adding `deadline_date` to its projection means amending the page's display logic, the page tests, and the database tests, all for one sort-key need in the writer. (2) The "compose in `exports.py`" precedent was set by T2's `write_progress`, which similarly does its own per-row `get_interviews(pid)` lookup rather than a richer joined query in the database layer. (3) The writer's pandas re-sort uses `kind="stable"` so even if a future change adds `deadline_date` to the upstream SQL ORDER BY, the writer's behaviour stays deterministic — the merge becomes redundant but not broken. Net: the implementer chose the lower-impact path, pinned the result via `test_sort_order_groups_by_recommender_then_deadline`, and left a comment explaining the choice.

**Q3. The fix commit augments `isolated_exports_dir` to monkeypatch `DB_PATH` AND run `init_db()`. Why not just delete the three redundant smoke tests as the orchestrator's hand-back message recommended?**

A. Both paths work, but the implementer's choice is strictly better. (1) The smoke tests serve a different purpose than the per-class `TestWriteX::test_empty_db_writes_header_only` tests — the smokes assert "the writer doesn't raise" as a quick sanity check that lives at the top of the file, the per-class tests assert the rendered file's structure. Deleting the smokes loses the "quickly notice if a writer crashes" layer above the structural tests. (2) Augmenting the fixture closes the gap **once** for every consumer (the three smokes plus the two `write_all` behaviour tests) rather than per-test. The diff is +21 / −2; deleting all three smokes would be roughly the same line count but would leave the two `write_all` tests still needing DB isolation. (3) The fix shape mirrors the conftest `db` fixture's lift from T2 — same idiom, same architectural intuition. Future T4 / T5 export-page tests will recognize the pattern.

**Q4. Why does the Reminder cell REUSE `exports._format_confirmation` while the Confirmed cell needs a NEW local `_format_confirmed`?**

A. The two cells answer the same kind of question (a flag plus an optional date) but with different rendering conventions because their underlying columns store different shapes. **Reminder** is `(reminder_sent INTEGER, reminder_sent_date TEXT)` — exactly the `(flag, date)` shape of Applications-page Confirmation, so `_format_confirmation` already handles it (`—` / `✓ {ISO}` / `✓ (no date)`). **Confirmed** is `(confirmed INTEGER)` only — a tri-state column with no companion date — so it renders `—` / `No` / `Yes` (no check glyph, no date). Different shape needs a different renderer. The implementer's commit body cites the DESIGN §2 layer rule for why `_format_confirmed` lives locally in `exports.py` rather than being imported from `pages/3_Recommenders.py` (which has the same-named helper for the same tri-state) — pages import streamlit, exports cannot. The reuse-where-possible / duplicate-where-the-layer-rule-mandates split is the project's standing pattern.

**Q5. The `fix:` commit makes T3's branch carry three commits (test → feat → fix). Doesn't that violate the TDD-three-commit cadence (`test:` → `feat:` → `chore:`)?**

A. The cadence is a guideline for *what shape the branch ships in*, not a hard cap on commit count. The T3 branch ships in two commits in normal flow (`test:` red → `feat:` green); the `fix:` is an amendment landing on the same branch because the `feat:` exposed a latent regression that had already shipped to main on T1 + T2 (a CI gap, not a code bug introduced by T3). The implementer's commit message correctly frames this: "TDD cadence reads: test → feat → fix → orchestrator's chore post-merge." If the regression had been introduced by T3 itself, a `fix:` would have been the wrong shape — the right shape would have been amending the `feat:` (since the `feat:` would have been incomplete). Here, T3's `feat:` was structurally correct AND consistent with how T1 + T2 shipped; the regression was a pre-existing gap that the implementer surfaced and closed, which is what `fix:` is for.

**Q6. CI was IN_PROGRESS on PR #32 and #33 when the orchestrator admin-bypassed; both eventually went FAILURE and main shipped red. What changed for PR #34?**

A. Three changes. (1) The `c284c20` process commit codified "do NOT admin-bypass while CI is IN_PROGRESS" as a blocking rule in `ORCHESTRATOR_HANDOFF.md`, with the explicit `gh pr view <N> --json statusCheckRollup --jq '...'` verification step. (2) The same commit added the CI-mirror local check (`mv postdoc.db postdoc.db.bak && pytest && mv postdoc.db.bak postdoc.db`) to `AGENTS.md` Session bootstrap, so the implementer can catch the same class of regression locally before pushing. (3) The orchestrator ran the full six-gate set — including the CI-mirror check — locally on the PR head before merging this time, instead of just the four GUIDELINES §11 gates. The CI-mirror gate is what would have caught PR #32 + #33 pre-merge if it had existed then.

---

## Carry-overs

- **Phase 6 T4 / T5 (Export page UI tests):** if those tests want exports-dir isolation, lift `isolated_exports_dir` into `tests/conftest.py` then. Today single-file consumer = local; multi-file consumer = lift.
- **Phase 7 polish candidate:** Recommender `notes` could be folded into the export as a per-recommender bullet section if the user wants. Park here; revisit during the Phase 7 cohesion sweep.

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-6-tier2` precedent. The six pre-merge gates
were re-run on the PR head locally (`pr-34-fixed` / `2439b4f`) at
review time: ruff clean · `pytest tests/ -q` 815 passed + 1 xfailed
· `pytest -W error::DeprecationWarning tests/ -q` 815 passed + 1
xfailed · status-literal grep 0 lines · standing isolation gate
`git status --porcelain exports/` empty · CI-mirror local check
815 + 1 xfailed with `postdoc.db` moved aside · `Tests + Lint (3.14)`
CI **conclusion: SUCCESS** verified before admin-bypass per the new
`c284c20` procedure._
