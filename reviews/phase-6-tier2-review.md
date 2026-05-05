**Branch:** `feature/phase-6-tier2-WriteProgress`
**Scope:** Phase 6 T2 — `exports.write_progress()` markdown generator + the mandatory `db_and_exports` conftest fixture lift (`exports.py`, `tests/conftest.py`, `tests/test_exports.py`, `tests/test_database.py`)
**Stats:** 15 new tests in `TestWriteProgress` (786 → 801 passed, 1 xfailed unchanged); +581 / −27 lines across 4 files; ruff clean; status-literal grep 0 lines; **T2 isolation gate passes** (`git status --porcelain exports/` empty after a clean `pytest tests/ -q`)
**Verdict:** Approve

---

## Executive Summary

T2 lands two deliverables in one PR per the AGENTS.md "Mandatory
ride-along" pattern: (1) the long-flagged conftest fixture lift that
fixes T1's exposed test-isolation pollution and (2) the second
markdown-export generator, `exports.write_progress()`, against
positions × applications × interviews. Both are clean.

The conftest lift is structural — `tests/conftest.py::db` now
monkeypatches both `database.DB_PATH` and `exports.EXPORTS_DIR` in
one fixture, so every test that requests `db` gets DB + exports
isolation by default. The implementer correctly identified five
opt-out sites in `tests/test_database.py` (migration tests that
hand-roll `tmp_path` because they need pre-v1.3 DB shapes) and
applied paired EXPORTS_DIR monkeypatches at each — two of those
sites were T1's actual polluters (`delete_position` +
`add_recommender` in `TestRecommendersRebuildMigration`); the other
three pair the isolation for symmetry. Two `write_all` behaviour
tests in `test_exports.py` gain the existing
`isolated_exports_dir` fixture parameter to keep them off the real
`exports/` path. Verification: T2 isolation gate now reports an
empty `git status --porcelain exports/` after a clean pytest run —
the pollution is gone.

`write_progress()` mirrors T1's architecture (deferred `database`
import, `EXPORTS_DIR.mkdir(exist_ok=True)` inside the function body,
sort `deadline_date ASC NULLS LAST, position_id ASC` re-applied via
pandas with `kind="stable"`, cell-shape conventions on em-dash + ISO
pass-through + raw bracketed status sentinel + `_md_escape_cell`).
Two new tri-state helpers carry the joined-frame complexity:
`_format_confirmation(received, iso_date)` mirrors the Applications
page DESIGN §8.3 D-A T1-C inline-text shape but uses ISO dates
instead of "Mon D" so the export round-trips, and
`_format_interviews_summary(scheduled_dates)` carries the only T2
design call — `"{N} (last: {YYYY-MM-DD})"` with `last` = max
scheduled_date. Per-row interviews lookup via
`database.get_interviews(position_id)` is N+1 queries; documented as
deliberate ("fine here — low position counts, single-user app").

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `tests/conftest.py::db` `local import exports as _exports` | Implementer's docstring rationale: "to avoid loading exports at conftest import time, in case a future test wants to monkeypatch the module before the fixture activates." Mildly over-defensive — `tests/conftest.py` already imports `database` at module level, and `database` can transitively load `exports` via deferred import paths. The local import doesn't *prevent* that, just keeps the conftest module's own namespace clean. The cost is essentially zero (one extra `import` line inside the fixture body). Net: harmless. | ℹ️ | Observation |

*No 🔴 / 🟠 / 🟡 / 🟢 findings.*

*Three additional kept-by-design choices (no Deadline column in `PROGRESS.md`, per-row N+1 interviews lookup, defensive `EXPORTS_DIR` monkeypatch symmetry across the five migration-test sites in `test_database.py`) are addressed in the Q&A section per `GUIDELINES §10` ("`Kept by design` observations belong in the Q&A section, not in the Findings table — they are not defects"). See Q1 (no-Deadline rationale), Q3 (5-site monkeypatch symmetry), Q7 (N+1 revisit signals).*

---

## Junior-Engineer Q&A

**Q1. Why does `PROGRESS.md` exclude the `Deadline` column when `OPPORTUNITIES.md` includes it?**

A. The two exports answer different questions and the column sets follow that split. `OPPORTUNITIES.md` is the upstream snapshot — *what positions exist + when are their deadlines*; `Deadline` is the central column there because it's the column users sort by when planning the next two weeks. `PROGRESS.md` is the application-progression backup — *how far along am I on each application I've started*; the columns are the steps in that pipeline (Applied · Confirmation · Response · Result · Interviews). Putting `Deadline` in both would create a redundancy between the two files that DESIGN §7 contract #2 ("stable markdown format committed to version control") would lock in for the lifetime of the project — three exports each duplicating the same upstream window doesn't add information; it adds three places to update if the upstream representation ever changes. The Position cell is the join key between exports if a reader wants to cross-reference. The same logic applies to T3's eventual `RECOMMENDERS.md` — recommenders own their own progression columns (asked / confirmed / submitted) and don't need to re-state the upstream Deadline.

**Q2. The interviews-summary cell is `"{N} (last: {YYYY-MM-DD})"`. Why use `max(scheduled_date)` rather than a more pandas-y "latest" via `idxmax` on the DataFrame?**

A. Three reasons, in priority order. (1) ISO `YYYY-MM-DD` strings sort lexicographically the same as chronologically — `max(['2026-04-15', '2026-05-01', '2026-06-20']) == '2026-06-20'`. The naive `max()` over a Python list of strings is correct without any datetime parsing. (2) The helper signature is `_format_interviews_summary(scheduled_dates: list[Any])` rather than `(interviews_df: pd.DataFrame)` — the writer pulls just the `scheduled_date` column from `get_interviews(pid)` and passes a flat list. Narrowing the helper's input means the helper is reusable from a different SQL query shape in the future (e.g. a joined query that returns just the dates). (3) `max()` on an empty list raises `ValueError`, which is a useful regression signal — the implementer guards with `if not iso_dates: return f"{n} (no dates)"` first, so empty + all-NULL cases land before `max()` runs. A pandas `idxmax` would silently return NaN on empty input — error-friendly here means stdlib `max()`.

The `test_interviews_summary_uses_max_scheduled_date_as_last` test is the regression bait: it inserts dates in non-monotonic order (`2026-09-01` then `2026-04-01`) so a bug that picks `iloc[-1]` (last-inserted) or `iloc[0]` (lowest-sequence) would fail with a wrong "last" date.

**Q3. The conftest `db` fixture now monkeypatches both `DB_PATH` and `EXPORTS_DIR`. The five migration-test sites in `test_database.py` opt out of `db` and hand-roll their own `tmp_path` setup. Why pair the EXPORTS_DIR monkeypatch at all five sites when only two of them call writers that fire `exports.write_all`?**

A. Defensive symmetry — three reasons. First, those five sites are doing pre-v1.3 schema seeds that need to bypass `init_db`'s schema setup; they're an exception to the conftest rule, and exceptions to fixtures should be obvious. The "for symmetry" comment at each site signals "this isn't because the test calls a writer right now; this is because the test escapes the conftest's isolation contract and that contract has two legs". Second, a future maintainer adding a writer call inside one of those test bodies would silently re-pollute `exports/`, and the `git status --porcelain exports/` gate (now part of the pre-PR checklist) would catch it post-hoc — the paired monkeypatch makes the gate a forward-prevent rather than a regression catcher. Third, the "for symmetry" comment is identical across all five sites, so a `grep` for it locates every opt-out path in one shot for a future audit. The cost is one `monkeypatch.setattr` line per site; the upside is that the isolation contract has one shape ("DB + EXPORTS together") rather than two ("DB + EXPORTS for writers; DB-only for migration tests").

**Q4. Why does the `db_and_exports` wrapper in `test_exports.py` take both `db` and `tmp_path` as parameters even though it doesn't use the `db` value?**

A. `db` is requested for its **side effect** — pytest's fixture resolution activates the `db` fixture and runs its `monkeypatch.setattr` lines before the wrapper's body executes. Without the `db` parameter, `tmp_path / "exports"` would be a path string that nothing has bound to `exports.EXPORTS_DIR`, and `write_progress` would write to the project's real `exports/` directory. The `tmp_path` parameter recovers the same `Path` value the conftest `db` fixture used to bind `EXPORTS_DIR`, so the wrapper can return it for the consumer to read. Pytest fixtures activate in declaration order; `db` first, then `tmp_path` reuses pytest's tmp_path mechanism that conftest already activated. The unused `db` value is the standard pytest pattern for "I need this fixture's side effects but not its return value" — the alternative (`db, _: db, tmp_path` etc.) is uglier without a payoff.

**Q5. The Confirmation cell helper duplicates logic that exists in `pages/2_Applications.py` (the DESIGN §8.3 D-A T1-C inline-text shape). Why duplicate rather than import from a shared utility?**

A. DESIGN §2 layer rules: pages import streamlit, exports cannot. A shared `ui_helpers.py` would either need to be streamlit-free (and then it stops being a UI helper) or stay streamlit-bound (and then exports can't import it). The honest split is two helpers — same semantic shape, different output flavor (Mon D for the page, ISO for the export) — and the cost is ~25 lines duplicated. The `_format_confirmation` here uses ISO dates because exports are version-controlled backups; "Mon D" loses the year and would be ambiguous five years from now when grep-ing through historical PROGRESS.md commits. The same split applies to `_safe_str_or_em` (the page layer's version is in `pages/2_Applications.py`; the export layer's version is in `exports.py`), and was already accepted at T1 review time.

**Q6. The `test_write_all_swallows_individual_writer_failure` test gains an `isolated_exports_dir` fixture parameter, but `test_write_all_swallows_mkdir_failure` does NOT. Why the asymmetry?**

A. The third test (`test_write_all_swallows_mkdir_failure`) explicitly *makes* `EXPORTS_DIR.mkdir` fail by monkeypatching `Path.mkdir` to raise — it never reaches the per-writer call sites that would write a file. Adding `isolated_exports_dir` would be cosmetic since the test's whole premise is that no directory ever gets created. The first two tests, by contrast, exercise the *non-failing* writers (`write_opportunities` succeeds even when `write_progress` is monkeypatched to raise), so they need the real `write_opportunities` body to execute against an isolated `EXPORTS_DIR`. The implementer's per-test reasoning is in the docstrings — a clean signal that the author thought about each test individually rather than blanket-applying the fixture.

**Q7. The N+1 query pattern in the per-row interviews lookup is documented as "premature optimization" to fix. When would a future implementer want to revisit?**

A. Three signals. (1) The user reports a noticeable Export-page button latency on a populated DB (Phase 6 T4 ships the manual-trigger button). At ≤50 positions the latency is microseconds; at 500 the user might notice a second of delay. (2) A real benchmark — `pytest --duration=10 tests/ | grep test_one_row_per_position` — shows `write_progress` blowing past 100ms on a small seed. (3) A future Phase adds a "rebuild every export every save" loop that fans out across every database write (post-v1.0); at that point the cumulative N+1 across `write_progress` × every writer call adds up. The right fix at that point is a `database.get_progress_table()` reader that does the join in SQL, returns one row per position with a pre-aggregated interviews-summary cell, and replaces both the `get_applications_table` call AND the per-row `get_interviews` lookup. The migration is mechanical: the new reader's contract goes into a `test_database.py::TestGetProgressTable` class first, then `write_progress` switches to it. Today, none of those three signals exist — so the ergonomics of "two readers + one summary helper" wins over "one custom SQL query + a writer that knows the join shape".

---

## Carry-overs

- **Phase 6 / Phase 7 performance signal:** Per-row N+1 interviews lookup in `write_progress` (kept-by-design per Q7). Track only if user-visible latency surfaces; not blocking.
- **T3 column-contract precedent:** The "no Deadline column" choice in `PROGRESS.md` (kept-by-design per Q1) sets the precedent that each export answers a different question with a non-overlapping column set. T3 (`write_recommenders`) should follow — its columns should be the recommender-progression set (Position · Recommender · Relationship · Asked · Confirmed · Submitted · Reminders) without re-stating the upstream Deadline.

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-6-tier1` precedent. The five pre-merge gates
were re-run on the PR head locally (`pr-33` / `2b82453`) at review
time: ruff clean · `pytest tests/ -q` 801 passed + 1 xfailed ·
`pytest -W error::DeprecationWarning tests/ -q` 801 passed + 1
xfailed · status-literal grep 0 lines · **T2 isolation gate
`git status --porcelain exports/` empty**._
