**Branch:** `feature/phase-6-tier1-WriteOpportunities`
**Scope:** Phase 6 T1 — `exports.write_opportunities()` markdown generator (`exports.py` + `tests/test_exports.py`)
**Stats:** 9 new tests (777 → 786 passed, 1 xfailed unchanged); +359 / −7 lines across 2 files; ruff clean; status-literal grep 0 lines
**Verdict:** Approve

---

## Executive Summary

T1 fills the existing `exports.py` stub with the first of three Phase 6
markdown generators per DESIGN §7. The function reads
`database.get_all_positions()`, sorts deadline ASC NULLS LAST with a
`position_id` tiebreaker (mirror of
`database.get_applications_table()`), and writes a single markdown
table to `exports/OPPORTUNITIES.md`. Three architectural pillars are
sound: deferred `database` import inside the function body breaks the
`database → exports → database` circular import; the function calls
`EXPORTS_DIR.mkdir(exist_ok=True)` itself so it works independently of
`write_all`'s prior mkdir (load-bearing for the Phase 6 T4
manual-trigger button); idempotency is pinned by
`test_idempotent_across_two_calls` so DESIGN §7 contract #2 ("stable
markdown format committed to version control") holds at the test
level. Two implementer-driven scope choices land cleanly: status
renders as the **raw bracketed sentinel** (`[APPLIED]`, not
`Applied`) because markdown is a backup format, not a UI surface, and
the column set is **pinned by the test class** since DESIGN §7 names
the file but doesn't enumerate columns. All four GUIDELINES §11
pre-merge gates are green; suite climbs 777 → 786.

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `AGENTS.md` "Immediate task — Phase 6 T1" block | The orchestrator-written T1 spec lowercased the output filename (`exports/opportunities.md`); DESIGN §7 line 462 + the existing `exports.py` stub docstring + the project's three markdown filenames in `exports/` are all **UPPERCASE** (`OPPORTUNITIES.md`, `PROGRESS.md`, `RECOMMENDERS.md`). Implementer correctly followed DESIGN over AGENTS and flagged the typo in the PR description. | 🟢 Doc-drift | Fix in the T1 chore rollup — sweep AGENTS.md so subsequent tier handoffs don't repeat the mistake. |
| 2 | `exports.py` `write_opportunities` | Status column renders the **raw bracketed sentinel** (`[SAVED]`, `[APPLIED]`, …) rather than the UI-friendly `STATUS_LABELS` translation. This is a deliberate divergence from the UI convention. Implementer's reasoning (in commit body + test class docstring): markdown is a backup format, round-trippable / greppable raw form trumps display-friendly translation. The pre-PR status-literal grep in GUIDELINES §11 is scoped to `app.py + pages/`, not `exports/`, so this divergence stays grep-clean. Pinned by `test_status_renders_as_raw_bracketed_sentinel` so a future implementer can't silently flip it. | ℹ️ | Kept-by-design. Cite-able in a future Phase 6 T2 / T3 review when the same question recurs for `write_progress` and `write_recommenders`. |
| 3 | `exports.py` `write_opportunities` column contract | DESIGN §7 names the file + role but does NOT enumerate columns. Implementer pinned `Position · Institute · Field · Deadline · Priority · Status · Created · Updated` via `TestWriteOpportunities`. The `Created` + `Updated` audit columns add temporal cells to a "human-readable backup" — defensible (they ARE valid backup data; round-trip needs them) but the markdown becomes less scannable. Idempotency holds because the timestamps don't change between consecutive `write_opportunities()` calls without an intervening DB write. | ℹ️ | Kept-by-design. Cite-able if Phase 6 T6 close-out audits the markdown for human-readability. The 8-column shape is now the locked contract; future column edits land alongside an explicit test diff. |
| 4 | `tests/test_exports.py` `db_and_exports` fixture | Combined isolation fixture monkeypatches both `database.DB_PATH` and `exports.EXPORTS_DIR` because `database.add_position` triggers `exports.write_all()` via deferred import. Without monkeypatching `EXPORTS_DIR` alongside `DB_PATH`, the auto-fired `write_all` would land in the project's real `exports/` directory and pollute it across test runs. Implementer suggested lifting to `conftest.py` if Phase 6 T2 / T3 tests need the same combined isolation. | ℹ️ | Defer to T2 — if T2's `write_progress` tests want the same shape, lift then. Premature lifting now (one consumer) is over-abstraction. |

*No 🔴 / 🟠 / 🟡 findings.*

---

## Junior-Engineer Q&A

**Q1. Why does the export render `[APPLIED]` (raw bracketed sentinel) when every UI surface renders `Applied` (translated label)?**

A. Markdown exports are a *backup format*, not a UI surface. The project description in `AGENTS.md` calls them "automated deadline alerts and markdown exports as portable backups" — the user opens `OPPORTUNITIES.md` to recover state if the SQLite file gets corrupted, to grep across positions on the command line, or to review history in a `git log -p`. All three of those use cases want the literal DB value: a future `INSERT INTO positions ... status='[APPLIED]'` can be reconstructed from the markdown by hand without first reverse-mapping `Applied → [APPLIED]`. The UI convention exists to hide the bracket noise from a human reading a Streamlit page; the backup convention exists to round-trip cleanly. Two different audiences, two different conventions. The implementer's `test_status_renders_as_raw_bracketed_sentinel` pin makes the divergence explicit: a future PR that "fixes" the export to use `STATUS_LABELS` would fail CI with a clear test-class docstring explaining why.

**Q2. The `Created` and `Updated` columns surface every row's audit timestamps in a human-readable backup file. Doesn't that read as noise?**

A. It does add cells the user is unlikely to read on a casual scan, but it is the right call for a backup. Three reasons. First, audit timestamps are part of the round-trip — restoring from `OPPORTUNITIES.md` without `created_at` would lose the chronological signal the project's "what's new this week" workflow depends on. Second, DESIGN §6 schema commits the project to keeping these columns; omitting them from the export would break the DESIGN §7 contract #2 "stable markdown format" (the backup must reflect the DB shape). Third, the column count (8) is locked by `TestWriteOpportunities.EXPECTED_HEADER` — if a future Phase 7 polish wants to drop them for readability, that change lands alongside an explicit DESIGN amendment + test edit, not as a silent generator change.

**Q3. Why does the writer use `pandas.sort_values(by=['deadline_date', 'id'], na_position='last', kind='stable')` instead of relying on the upstream `get_all_positions()` SQL `ORDER BY`?**

A. Two reasons. First, `database.get_all_positions()` orders by `deadline_date ASC NULLS LAST` only — it does **not** add a `position_id` tiebreaker (the SQL `ORDER BY deadline_date NULLS LAST` is non-deterministic for equal-deadline rows). The `applications` table query (`get_applications_table`) added the tiebreaker to keep selection survival working across reruns (Phase 5 T1 invariant); the positions query never inherited that fix. Adding the tiebreaker in the writer is the cheaper option than amending the database query and re-pinning every Opportunities-page test. Second, `kind='stable'` is the explicit guarantee that pandas-side sort doesn't disturb existing relative order on the secondary key — `pandas.sort_values` defaults to `kind='quicksort'` which is unstable; stable is what idempotency needs.

**Q4. The fixture `db_and_exports` monkeypatches BOTH `database.DB_PATH` AND `exports.EXPORTS_DIR`. Couldn't a test stack `db` (from `conftest.py`) + `isolated_exports_dir` (already in this file)?**

A. It could, but stacking two fixtures from two files spreads the isolation contract across two `monkeypatch.setattr` calls in two different scopes, and a test author who omits either one would silently pollute the project's real `exports/` directory. The reason is `database.add_position`'s side effect: it calls `exports.write_all()` via deferred import, and `write_all` writes to whatever `exports.EXPORTS_DIR` is set to at function-call time. If only `database.DB_PATH` is monkeypatched, the side-effect write lands in the project root's real `exports/`. The combined fixture eliminates the footgun by binding both monkeypatches to a single `tmp_path`, and the docstring spells out the rationale so future tests see the precedent. Implementer suggested lifting to `conftest.py` if Phase 6 T2 / T3 want the same shape; deferring that lift to T2 keeps the abstraction honest (one consumer = page-local; two consumers = lift it).

**Q5. The `_md_escape_cell` helper escapes `|` and collapses `\n` / `\r`. Why escape rather than reject these characters at write time?**

A. Reject would surface as a runtime exception during a save handler — and the user already lost the foreground UI affordance because writing happens **after** the DB commit, inside the deferred `exports.write_all()` call. A user who types `Postdoc | Bayes / ML` into a position name should not see their save succeed in the DB but fail with a stack trace in the exports backup; that violates DESIGN §7 contract #1 "log-and-continue on failure". Escaping is the lossless option: pipes round-trip via `\|` (still readable as a pipe in markdown rendered output via the standard escape rule); newlines collapse to a single space (visibly readable, only a minor information loss). The cost is two `.replace(...)` calls per cell — negligible. The cheap safety net stays cheap because realistic position names rarely contain pipes or newlines, but the writer is hardened against the cell that does.

**Q6. Why does the file-existence test (`test_writes_file_at_expected_path`) include the directory's contents in its `assert` failure message?**

A. Defensive test ergonomics. If `write_opportunities` writes to the wrong path (e.g. lowercase `opportunities.md`, or to the project-root `exports/` when isolation didn't bind), the test's failure message is the user's first signal of WHY. A bare `assert out.exists()` would say "expected True, got False" — true but unhelpful. Including the directory listing in the message tells the reader "I expected `OPPORTUNITIES.md` here; instead I see `[…]`". The directory-existence guard (`if db_and_exports.exists() else '(missing)'`) handles the case where the writer didn't create the directory at all — that signal too is useful debugging when the test fails in CI without local reproduction.

**Q7. The empty-DB test (`test_empty_db_writes_header_only`) seems redundant — if positions is empty, who cares what the markdown looks like?**

A. The Export-page manual-trigger button (Phase 6 T4) calls `write_all()` on user click, which fans out to all three generators including `write_opportunities`. A user who opens the app for the first time, navigates to the Export page, and clicks "Regenerate exports" must NOT see a stack trace just because they haven't added a position yet. The empty-DB test pins exactly that — the writer produces a valid markdown file (header + separator only) without raising, even when `df.empty` is True. The implementer's `if not df.empty: df.sort_values(...)` guard is what makes this work; without it, `pandas.sort_values` on an empty DataFrame is fine in current pandas but the `if` adds a small future-proofing margin against pandas API changes. The test is the contract gate.

---

## Carry-overs

- **Doc-drift:** AGENTS.md "Immediate task" block lowercases `exports/opportunities.md`; DESIGN + the existing stub use UPPERCASE. Sweep in the T1 chore rollup so the next tier handoff (Phase 6 T2) doesn't repeat the typo.
- **Phase 6 T2 / T3:** if the `db_and_exports` combined-isolation fixture is needed for `write_progress` / `write_recommenders` content tests, lift to `conftest.py` then. Single consumer today = local; two consumers = lift.

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-5-tier6` precedent. The four pre-merge gates
were re-run on the PR head locally (`pr-32` / `989e48b`) at review
time: ruff clean · `pytest tests/ -q` 786 passed + 1 xfailed ·
`pytest -W error::DeprecationWarning tests/ -q` 786 passed + 1
xfailed · status-literal grep 0 lines._
