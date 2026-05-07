# Pre-publication Tests Code Review

**Branch:** `fix/kpi-nomenclature`
**Scope:** Pre-publication code review of every file under `tests/` (838 test functions across 12 files; 19,700 LOC) against GUIDELINES §9 testing conventions and DESIGN §2 layer rules.
**Stats:** 904 passed, 1 xfailed; ruff clean; pyright on `tests/` has 2 errors (see F3)
**Verdict:** Approve with findings

---

## Findings

| # | File | Line(s) | Severity | Finding |
|---|------|---------|----------|---------|
| 1 | tests/test_app_page.py | 4, 446, 962 | 🟡 | Three references to `PHASE_4_GUIDELINES.md`; the file does not exist anywhere in the repo. Public readers chase a dead link. **Fix:** delete the parenthetical references or replace with a link to `DESIGN §8.1`. |
| 2 | tests/conftest.py:21; tests/test_app_page.py:4; tests/test_export_page.py:38; tests/test_exports.py:25, 201, 256, 501, 832; tests/test_recommenders_page.py:34 | (11 total refs) | 🟡 | Comments reference `AGENTS.md` and `TASKS.md`, which were removed from the public repo in commit `a4a95c2 chore(repo): remove docs/internal/ from public repository`. Readers cloning the public repo see pointers to docs that don't ship. **Fix:** scrub these comments or replace with a public-doc anchor (`DESIGN.md` / `GUIDELINES.md`). |
| 3 | tests/test_opportunities_page.py | 3918 | 🟡 | `int(at.number_input(key=NUM_REC_LETTERS_KEY).value)` raises pyright errors because `.value` is typed `Number \| None` and `int(None)` would crash at runtime if the widget ever surfaces None. **Fix:** `int(at.number_input(key=NUM_REC_LETTERS_KEY).value or 0)`. |
| 4 | tests/test_app_page.py | 290 | 🟡 | Docstring says `"All three counted KPIs (Tracked / Applied / Interview)"` but the assertions below now check `"Interviews"` (plural — renamed in commit `a0b11bc`). **Fix:** `"Tracked / Applied / Interviews"` in the docstring. |
| 5 | tests/test_export_page.py | 509 | 🟡 | Comment says `"or via the _EXPORT_FILENAMES iteration variable"`, but that constant was deleted from `pages/4_Export.py` in commit `333ccf9` (review finding F8). **Fix:** drop the parenthetical — the loop now iterates `database.get_export_paths()`. |
| 6 | tests/test_database.py | 330, 357 | 🟡 | `time.sleep(1.1)` and `time.sleep(2.1)` are real wall-clock waits (3.2 s of suite latency across two tests) used to cross SQLite's 1-second `datetime('now')` granularity. Real sleeps in tests are flakiness vectors on slow CI and burn time. **Fix:** stub `database.datetime`/`date` via `monkeypatch` to advance fake clocks instead, or pin via direct UPDATE of `updated_at` between calls. |
| 7 | tests/test_app_page.py | 41, 97, 319, 443, 549, 754, 959, 1082, 1274, 1776, 2098, 2502; tests/test_recommenders_page.py:1397, 1567 | 🟡 | 14 test classes named after process-historical phase/tier IDs (`TestT1AppShell`, `TestT2AFunnelBar`, `TestT6ComposeButton`, …). GUIDELINES §9 example shape is `Test<TierOrFeature>` and the rest of the suite uses feature names (`TestApplicationsFilterBar`, `TestPendingAlertsPanel`). **Fix:** rename to feature names (e.g., `TestT1CKpiCounts` → `TestKpiCounts`); the class-level constants and method names already describe the feature. |
| 8 | tests/ (84 occurrences) | many | ⚪ | "Sub-task 4", "Sub-task 12", "v0.10.0", and similar internal-tracker references inside test docstrings have no value to a public reader and rot quickly as the project moves on. **Fix:** sweep them out alongside finding #2. Not a publication blocker. |
| 9 | tests/ (163 occurrences) | many | ⚪ | Phase/tier IDs in docstrings (`T1-A`, `T2-B`, `Phase 5 T6`, etc.) — same shape as #7 but in prose rather than class names. **Fix:** keep when they explain a non-obvious decision; delete when they're just timestamps. Not a publication blocker. |
| 10 | tests/test_exports.py | 18–43 | ⚪ | `isolated_exports_dir` fixture re-implements the DB + EXPORTS_DIR isolation already provided by `conftest.py::db`. `tests/test_export_page.py:52–62` shows the leaner pattern: a 4-line wrapper around `db` that exposes the exports-dir path. **Fix:** rewrite `isolated_exports_dir` as the same 4-line wrapper for parity. |
| 11 | tests/test_opportunities_page.py | 67–71 | ⚪ | `_force_set_position_field` opens a raw `sqlite3.connect(str(db_path))` instead of routing through `database._connect()`, which means the test escape hatch silently bypasses `PRAGMA foreign_keys = ON`. Harmless for the UPDATE statements it executes, but the docstring should call out the limitation so a future caller doesn't reach for it for an INSERT/DELETE that needs FK enforcement. |
| 12 | tests/conftest.py | 46–58 | ⚪ | `make_position` is defined alongside the `db` fixture in `conftest.py`. By convention `conftest.py` is for fixtures only; pure helpers live in `tests/helpers.py` (which already exists). The current import path `from tests.conftest import make_position` is unusual. **Fix:** move `make_position` to `tests/helpers.py` next to `link_buttons` / `decode_mailto` and update the seven import sites. |

---

## Finding Details

### F1: References to non-existent `PHASE_4_GUIDELINES.md`

Three places in `tests/test_app_page.py` cite `PHASE_4_GUIDELINES.md` (the module-level docstring at line 4, plus two intra-class references at 446 and 962). The file does not exist on disk, in `git ls-files`, or anywhere reachable from a fresh clone. A reader who follows the citation hits nothing. Fix: delete the parenthetical or repoint to `DESIGN §8.1`, where the dashboard contract actually lives.

### F2: Internal-doc references that don't ship publicly

Five test files (`conftest.py`, `test_app_page.py`, `test_export_page.py`, `test_exports.py`, `test_recommenders_page.py`) cite `AGENTS.md`, `TASKS.md`, or `docs/internal/`. Commit `a4a95c2 chore(repo): remove docs/internal/ from public repository` deleted that whole directory from the published tree. Eleven references currently point at content that no longer ships. The references aren't load-bearing — each one explains *why* a test exists or where a contract was sourced — so a global scrub (or repoint to `DESIGN.md` / `GUIDELINES.md`) is safe.

### F3: pyright errors in test code

`pyright tests/` reports two errors at `test_opportunities_page.py:3918`:
```
Argument of type "Number | None" cannot be assigned to parameter "x" of type "ConvertibleToInt" in function "__new__"
```
The expression `int(at.number_input(key=NUM_REC_LETTERS_KEY).value)` works at runtime because the widget is pre-seeded from session_state, but the widget contract allows `value=None` for a cleared input. Add the `or 0` fallback to align the test with the type contract and prevent a future test from copy-pasting the unsafe form.

### F4: Stale docstring after the Interview → Interviews rename

`tests/test_app_page.py:290`'s docstring opens with `"All three counted KPIs (Tracked / Applied / Interview)"`. The KPI was renamed plural in commit `a0b11bc` and the actual assertion at line 310 now reads `helps["Interviews"]`. The class-level constant is `INTERVIEWS_HELP`. Mechanical drift left over from my own edit; one-word fix.

### F5: Reference to dead `_EXPORT_FILENAMES` constant

`tests/test_export_page.py:509` says `"or via the _EXPORT_FILENAMES iteration variable"`. That constant was deleted from `pages/4_Export.py` in commit `333ccf9` (pre-publish review F8 follow-up). The comment now describes a code path that doesn't exist; trim it.

### F6: Wall-clock `time.sleep` in test_database.py

Two tests in `test_database.py` (`test_update_position_refreshes_updated_at` at 330 and `test_noop_restart_does_not_bump_updated_at` at 357) sleep for 1.1 s and 2.1 s respectively to step past SQLite's `datetime('now')` 1-second granularity. The reason is documented in the docstrings, but real-time sleeps in a 50-second suite are 6 % of total runtime, are vulnerable to slow CI runners, and are the wrong tool for testing trigger logic. A monkeypatch on `database.datetime` (or a stub that returns explicit timestamps) gives the same coverage without the wall-clock dependency.

### F7: Test classes named after phase/tier IDs

GUIDELINES §9 prescribes `Test<TierOrFeature>` with examples `TestT3MaterialsReadiness`, `TestQuickAddFormBehaviour`. Most of the suite follows the latter (`TestApplicationsFilterBar`, `TestPendingAlertsPanel`, `TestMaterialsTabLorRendering`), but 14 classes still carry phase IDs: `TestT1AppShell`, `TestT1CKpiCounts`, `TestT1DNextInterviewKpi`, `TestT1EEmptyDbHero`, `TestT2AFunnelBar`, `TestT2BFunnelEmptyState`, `TestT2CFunnelLayout`, `TestT2DFunnelExpand`, `TestT3MaterialsReadiness`, `TestT4UpcomingTimeline`, `TestT5RecommenderAlerts`, `TestT6FunnelToggle`, `TestT6ComposeButton`, `TestT6LLMPromptsExpander`. Once the project ships, "T1C" and "T2D" mean nothing; the class-level constants and method names already describe the feature. Rename to feature-only names.

### F8 / F9: Process-historical comments

Across the test suite there are ~84 occurrences of internal-tracker references like `Sub-task 4`, `v0.10.0`, `Phase 6 T2 lift`, plus another ~163 mentions of phase/tier IDs in docstrings. They were useful when the repo lived on a private branch with a sprint tracker; for a public release they're just archaeological clutter. Not blockers — sweep when convenient.

### F10: Duplicate isolation fixture

`tests/test_exports.py:18–43` defines `isolated_exports_dir`, which monkeypatches `EXPORTS_DIR`, monkeypatches `DB_PATH`, and runs `init_db()` — the same three things the conftest `db` fixture already does. The fixture exists because consumers want the exports-dir `Path` back. `tests/test_export_page.py:52–62` shows the leaner pattern: depend on `db` + `tmp_path`, return `tmp_path / "exports"`. Refactor `isolated_exports_dir` to match for one fewer setup path to maintain.

### F11: `_force_set_position_field` bypasses `_connect()`

The escape hatch at `tests/test_opportunities_page.py:67–71` opens `sqlite3.connect(str(db_path))` directly, which means it doesn't run `PRAGMA foreign_keys = ON`. Fine for the UPDATEs it currently issues, but the docstring should warn future callers not to reach for it for INSERT/DELETE statements that depend on FK enforcement.

### F12: `make_position` lives in conftest.py

Convention treats `conftest.py` as fixture-only; pure helpers belong in `tests/helpers.py` (which exists for `link_buttons` / `decode_mailto` / `download_button`). `make_position` is a pure helper but lives in conftest, forcing the unusual `from tests.conftest import make_position` import in seven test files. Move to `tests/helpers.py` for cleaner separation.

---

## Verdict Rationale

No 🔴 findings — the test suite is structurally sound, layer-clean (no `streamlit` imports outside page-test files, no raw SQL outside the documented migration-test escape hatches and the `_force_*` helpers), uses `db`-fixture isolation across the board, and has no `assert True` / `pytest.skip` / debug `print` rot. The 🟡 cluster is dominated by **dangling references to internal documents that no longer ship** (F1, F2, F5) plus **stale comments and one drifting docstring** from recent edits (F3, F4) and a **wall-clock flakiness pattern** (F6). F7 is the only convention-shape finding (phase-ID class names) and the existing feature-named classes show the cleanup is mechanical. None block publication, but F1, F2, and F3 are visible to anyone who clones the repo and runs `pyright tests/` or follows a `PHASE_4_GUIDELINES.md` link, so they should land before the public push. The ⚪ findings (F8–F12) are housekeeping that can wait.
