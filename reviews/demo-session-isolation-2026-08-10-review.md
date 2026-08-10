# Pre-merge Review — Demo Session Isolation (2026-08-10)

**Branch:** `fix/demo-session-isolation` (6 commits)
**Scope:** Correctness pass over the unreleased demo-mode work (`#111`–`#117`) ahead of the `v0.15.0` cut. Touches `db_session.py`, `database.py`, `config.py`, `scripts/seed_demo_db.py`, four test modules, and the specs.
**Stats:** 14 files, +236 / −120. Suite 1084 → 1089 passed, 11 xfailed. Coverage 95.27% (floor 95).
**Verdict:** Approve.

## Executive Summary

Six defects in the unreleased demo-mode feature, one of them a
cross-visitor data leak on the public deploy. All are fixed, each in its
own commit with a regression test. The remaining four findings are
hygiene: a stale docstring, a spec gap, an order-dependent test, and a
working-directory-dependent test. Nothing here changes released
behaviour — every fix lands inside the `[Unreleased]` demo feature, so
the CHANGELOG folds rather than grows.

The headline defect: `db_session.bind()`'s failure path cleared the
process-global connection provider. Because that provider is shared by
every live demo session, one visitor's failed bind silently rerouted
*other* visitors' `database._connect()` calls to the on-disk database —
their seeded sandbox appeared to vanish and their subsequent edits
landed in a file shared with every other affected visitor. That is the
exact isolation failure demo mode exists to prevent.

## Findings

| # | Sev | Location | Finding | Status |
|---|-----|----------|---------|--------|
| 1 | 🔴 | `db_session.py:106` | Failed `bind()` cleared the process-global provider, dropping every other live session into shared file-DB mode. | Fixed inline |
| 2 | 🔴 | `database.py:75` | `_connect()`'s provider branch skipped `row_factory` and `PRAGMA foreign_keys`, so an injected connection could silently disable `ON DELETE CASCADE`. | Fixed inline |
| 3 | 🔴 | `database.py:1453` | `save_settings()` returned before validating in demo mode, dropping the boundary-validate guarantee where input is least trusted. | Fixed inline |
| 4 | 🔴 | `config.py:29` | `IS_DEMO` accepted only `"1"`; `AAT_DEMO=true` disabled per-session sandboxes on a public deploy with no signal. | Fixed inline |
| 5 | 🟠 | `scripts/seed_demo_db.py:139` | No seeded deadline beyond 30 days — the dashboard's 60/90-day window selector matched nothing. | Fixed inline |
| 6 | 🟠 | `scripts/seed_demo_db.py:140` | No seeded `Stretch` position — the priority filter offered an option matching nothing. | Fixed inline |
| 7 | 🟠 | `scripts/seed_demo_db.py:459` | `main()` exported `AAT_DB_PATH` and reloaded modules, permanently repointing `database.DB_PATH` for any in-process caller. | Fixed inline |
| 8 | 🟠 | `tests/test_config.py:867` | Reloading config under `AAT_DEMO=1` without reloading back left `IS_DEMO` True, demo-gating every later export writer. | Fixed inline |
| 9 | 🟠 | `tests/structure/test_bootstrap_order.py:27` | Page sources read via cwd-relative paths; the bootstrap-order guard errored out when pytest ran from anywhere but the repo root. | Fixed inline |
| 10 | 🟠 | `scripts/seed_demo_db.py:47` | `seed()`'s docstring described a provider-less CLI mode its own fail-fast guard makes unreachable. | Fixed inline |
| 11 | 🟠 | `db_session.py:121` | `_provider()`'s docstring and raised message named only one of the two routes to an empty cache; finding 1 makes the other primary. | Fixed inline |
| 12 | 🟠 | `DESIGN §5.2` | The new `AAT_DEMO` guard was documented in the §5.1 symbol table but absent from the import-time invariants list that enumerates exactly this class of check. | Fixed inline |
| 13 | 🟡 | `database.py:59` | `set_connection_provider()`'s docstring singled out `reset()` as the path leaving the provider installed; after finding 1 no path clears it. | Fixed inline |
| 14 | 🟡 | `config.py:9`, `GUIDELINES §2`, `DESIGN §5` | All three described config.py as merely *reading* `AAT_DEMO`; importing it can now abort the process. | Fixed inline |
| 15 | 🟡 | `tests/test_seed_demo_db.py:125` | Class docstring cited a `spec §4.7` that does not exist and narrated errata history. | Fixed inline |
| 16 | ℹ️ | `scripts/seed_demo_db.py:456` | The removed `importlib.reload(database)` also reset `_connection_provider`; the try/finally does not. Unreachable today — `main()` is CLI-only and the autouse fixture clears the provider after every test. | Kept by design |
| 17 | ℹ️ | `scripts/seed_demo_db.py:152` | The new row hardcodes `"priority": "Stretch"`, matching the 15 pre-existing priority literals in the file. `config` exposes only `PRIORITY_VALUES`, no per-priority constant. | Carry-over |
| 18 | ℹ️ | `config.py:33` | The new `raise` is exercised only in a subprocess, so it is uncovered in-process. Coverage headroom is now 0.27 points. | Kept by design |

## Junior-engineer Q&A

**Q1. Why is leaving a global installed safer than clearing it, when the session that owned it just failed?**
Because the provider is not the session's — it is the *process's*. It is
a pure function of `st.session_state`, so the same object serves every
visitor and resolves each caller's own connection. Clearing it is a
global action taken on local evidence. Popping the session cache is the
local action: the failed session now has no connection, and its next
`database` call raises inside `_provider()` instead of silently opening
the shared file. Loud local failure beats silent global degradation.

**Q2. `_connect()` now runs `PRAGMA foreign_keys = ON` on every provider call. Isn't that wasted work, and doesn't SQLite ignore that pragma inside a transaction?**
Both concerns are real and both are answered by the call graph. An AST
walk over `database.py` confirms no `with _connect()` block calls
another function that opens `_connect()` — the four intra-block calls go
to `_sync_rec_letters_done`, which takes the open connection as a
parameter. Every block therefore ends in `commit()` or `rollback()`
before the next begins, so the pragma always executes outside a
transaction and takes effect. Cost is one C-level statement per block.
The alternative — trusting each provider to configure its connection —
is what let the contract drift in the first place.

**Q3. Why validate in demo mode when the Save button is disabled there anyway?**
`disabled=` is client-side. It shapes the UI; it does not defend the
function. `save_settings()` documents "if any value fails validation, no
write happens" — a boundary guarantee, and a boundary that only holds in
some modes is not a boundary. The fix keeps the demo write suppressed
and moves only the `return`, so validation runs everywhere and the demo
path still touches no disk.

**Q4. Aborting the whole app because an environment variable is misspelled seems harsh. Why not warn?**
Because the failure is silent, remote, and irreversible in effect. An
operator typing `AAT_DEMO=true` gets a running app that looks correct
and hands every visitor the same on-disk database. A warning lands in a
log nobody reads on a Cloud deploy. This matches the module's existing
posture: `config.py` already aborts startup on a bad `FUNNEL_BUCKETS` or
inverted threshold. A misconfigured privacy flag deserves at least the
treatment a misconfigured chart bucket gets.

**Q5. The conftest fixture now repairs a leaked `IS_DEMO`. Doesn't a self-healing fixture hide the next leak?**
That was the review's objection, and it is why the offending test was
also fixed at the source: it now reloads config in a `finally`. The
fixture change stays as a backstop, not as the cure. The distinction
matters — a backstop that fires silently on an already-fixed problem is
insurance; a backstop used *instead* of a fix is a leak detector wired
to nothing.

**Q6. Why rewrite the branch history instead of adding a follow-up commit?**
One commit body had been corrupted with heredoc markers and a verbatim
copy of a different commit's message describing files it did not touch.
A follow-up commit cannot fix a message; only a rewrite can, and a
rewrite is free before a branch has been reviewed or merged. Folding the
review corrections into their originating commits at the same time cost
nothing extra and leaves each commit describing exactly what it does.
Every rebuilt commit was re-verified green individually.

**Q7. How do we know the seed additions didn't disturb the other pinned expectations?**
The new row is `[SAVED]` with a 50-day deadline and no application,
interview, recommender, or materials rows, so it cannot move the
upcoming-panel counts, pending-recommender counts, or the R1/R2/R3
cascade trails. Every count assertion in the suite was audited: the
exact ones were updated (19 positions, SAVED 3→4), and the rest are
lower bounds or exact counts on slices the new row does not enter. The
full suite is green in both passes, and two new tests now pin the
coverage properties themselves rather than the row count.

## Verdict

**Approve.** Four correctness defects and one privacy-relevant
configuration trap are fixed with regression tests; the remaining
findings were doc and test hygiene, all resolved. Every commit is
independently green (`1086 → 1089` as each commit's tests land), ruff and
pyright are clean, the status-literal grep is clean, and both pytest
passes are green at HEAD.
