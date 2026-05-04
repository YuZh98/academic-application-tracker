**Branch:** `feature/phase-7-tier4-ConfirmDialogAudit`
**Scope:** Phase 7 T4 — confirm-dialog audit across the three destructive paths (position / interview / recommender delete). 11 new tests in `tests/test_pages_cohesion.py::TestConfirmDialogAudit` + one cascade-copy bug fix in `pages/1_Opportunities.py::_confirm_delete_dialog` (warning text added "interview" to the FK-cascade enumeration — was: "application and recommender rows"; now: "application, interview, and recommender rows").
**Stats:** 11 new tests (853 → 864 passed, 1 xfailed unchanged); +296 / −2 lines across 2 files; ruff clean; status-literal grep 0 lines; standing isolation gate empty; CI-mirror local check passes (864 + 1 xfailed); **`Tests + Lint (3.14)` CI conclusion: SUCCESS** (`mergeStateStatus: BLOCKED`, `mergeable: MERGEABLE`)
**Verdict:** Approve

---

## Executive Summary

T4 is **not** a no-op outcome — the audit surfaced a real bug. The
position-delete dialog body said "application and recommender rows"
but the FK cascade chain (`positions → applications → interviews`,
both edges with `ON DELETE CASCADE`; `positions → recommenders`,
also CASCADE) actually drops **three** child tables in one
transactional sweep. The user clicking "Delete this position" had
no warning that interview rows were about to disappear too.
Implementer's `feat:` commit fixed the copy:

```diff
-    f'Delete **"{position_name}"**? This also removes its application '
-    f'and recommender rows (FK cascade) and **cannot be undone**.'
+    f'Delete **"{position_name}"**? This also removes its '
+    f'application, interview, and recommender rows (FK cascade) '
+    f'and **cannot be undone**.'
```

Per-page `TestDeleteAction` had the same gap — it asserted
`"application"` + `"recommender"` + `"cannot be undone"` substrings
were present, didn't enumerate the full cascade chain. The cohesion
test caught it because `DESTRUCTIVE_PATHS` enumerates the FK chain
explicitly via `cascade_substrings: ["application", "interview",
"recommender"]` and the `test_dialog_body_lists_cascade_effects`
assertion fails fast on any missing entity. This is the value
proposition of cross-page cohesion tests — per-page tests check
contracts the page already knows about; cohesion tests check
contracts that span layers.

`TestConfirmDialogAudit` ships five test methods, four parametrized
over all three destructive paths + one cross-page AST walk:

1. **Title locked-shape** — verbatim source-grep for
   `@st.dialog("Delete this <noun>?")`. (3 tests)
2. **Irreversibility cue** — body contains `"cannot be undone"`. (3 tests)
3. **Cascade-effect copy** — body lists every FK-cascade child table.
   Parametrized only over paths with non-empty `cascade_substrings`,
   so today only position-delete is tested (interview + recommender
   are leaf deletes). (1 test today; auto-extends if future paths gain
   cascades.) ← **this is the test that surfaced the bug**.
4. **Every `database.delete_*` caller is inside a `@st.dialog`
   function** — AST walk across all 5 page files; ancestor chain
   check finds enclosing `FunctionDef` with `@st.dialog` decorator.
   Catches a future "quick delete" button that bypasses the dialog.
   (1 cross-page test.)
5. **Failure preserves the pending sentinel** — AST walk for
   `st.session_state.pop` calls inside `except` handlers;
   asserts none exist. The success-path pops (Confirm + Cancel
   button branches) live OUTSIDE the except handler and stay legal.
   Pins the documented contract (every dialog's docstring says
   "Sentinels survive so the dialog re-opens for retry") to source
   structure. (3 tests.)

All six pre-merge gates green. CI conclusion SUCCESS verified per
the standing `c284c20` procedure.

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `pages/1_Opportunities.py::_confirm_delete_dialog` body | Position-delete dialog warning text omitted "interview" from the FK-cascade enumeration. Schema: `positions → applications (CASCADE) → interviews (CASCADE)` + `positions → recommenders (CASCADE)` — three child tables drop together; the warning listed only two ("application and recommender rows"). User clicking "Delete this position" had no signal that interview rows were about to disappear too. Pre-existing bug; T4's `test_dialog_body_lists_cascade_effects` surfaced it. **Fixed inline** in PR #40's `feat:` commit (`6efb709`). | 🔴 Bug | Fixed inline |
| 2 | `tests/test_opportunities_page.py::TestDeleteAction` (existing — not modified by this PR) | The per-page test asserted `"application"` + `"recommender"` + `"cannot be undone"` substrings in the dialog body — didn't enumerate the FK-cascade chain. So when the dialog copy was missing "interview", the per-page test passed. Surfaced as a finding, not a fix: T4's cross-page cohesion test (`test_dialog_body_lists_cascade_effects`) is the right home for the chain-enumeration check; tightening the per-page test would duplicate that contract. | ℹ️ | Observation — kept as-is. The cohesion test is now the single source of truth for "every child table in the FK chain is mentioned". |

*No 🟠 / 🟡 / 🟢 findings.*

*Two architectural choices live in the Q&A section per `GUIDELINES §10`: AST helper `_set_parents` annotation pattern; cascade-substring list shape (positive enumeration vs FK-introspection).*

---

## Junior-Engineer Q&A

**Q1. Why was the bug latent? The per-page test (`TestDeleteAction`) explicitly checked dialog-body content — what did it miss?**

A. The per-page test asserted **partial substring presence**: `"application"` is in the body? Yes. `"recommender"` is in the body? Yes. `"cannot be undone"` is in the body? Yes. Done. It didn't enumerate the full FK cascade chain because the test author at write-time was thinking "name a few entities the user should recognize", not "every CASCADE edge from this table". The cohesion test (`test_dialog_body_lists_cascade_effects`) inverts this: it parametrizes over the `cascade_substrings` list which is a positive enumeration of every FK-affected entity, and asserts every entry is present. Missing one entity in the list = missing one entry in the dialog copy — direct correspondence. The structural difference is "test the contract you happen to remember" (per-page) vs "test the contract derived from the schema" (cohesion). T4's value-add is exactly this kind of audit-via-derivation that a per-page test naturally wouldn't surface.

**Q2. The implementer used positive enumeration (`cascade_substrings: ["application", "interview", "recommender"]`) instead of introspecting the FK chain from the database schema. Why?**

A. Three reasons. (1) The schema is in `database.py::init_db()` as a `CREATE TABLE` string, not in a programmatic structure that's easy to AST-walk for `REFERENCES ... ON DELETE CASCADE` clauses. Parsing SQL DDL to extract the FK chain is non-trivial (regex against multi-line SQL, handling triggers + indices, edge cases like composite FKs). (2) The user-facing copy isn't 1:1 with the schema entity names — `applications` (table) → `application` (singular noun in copy); `recommenders` → `recommender`. A schema-introspection approach would need a noun-mapping layer that defeats the simplicity it was supposed to provide. (3) Positive enumeration in the test fixture is a documented contract — a future engineer reading `DESTRUCTIVE_PATHS` sees explicitly which child tables the position-delete affects, and can update both the schema CASCADE clause and the dialog copy in lockstep. The cost is a small list maintained by hand; the benefit is the test reads at the contract level the user actually cares about. If the project ever grows a fourth child table on `positions`, adding it to the list + the dialog copy is one PR; introspection would have to keep pace via different machinery.

**Q3. The `_set_parents` helper annotates every AST node with a `.parent` attribute. Isn't that a side effect on borrowed data?**

A. It is — and the implementer's docstring is honest about it. `ast.AST` nodes are mutable and the trees are constructed fresh by every `ast.parse()` call (no shared cache between tests), so the side effect doesn't leak across tests. The pattern is the standard answer to "find an enclosing X" queries in Python AST work because `ast.walk` is direction-agnostic — it yields nodes in a flat sequence without parent links. The alternatives (manually plumbing the parent through a recursive walk, or using `ast.NodeVisitor` with a parent stack) are significantly more code for the same outcome. The `# type: ignore[attr-defined]` annotation in the implementation is the only honest acknowledgement that we're tagging on a non-standard attribute; mypy / pyright would otherwise flag the access. For test-internal use, this is the cleanest pattern.

**Q4. The `test_every_database_delete_caller_inside_dialog` test walks every `database.delete_*` call in every page and verifies enclosing `@st.dialog` decoration. Doesn't a per-page test already pin this?**

A. It pins the EXISTING three call sites — Q1's per-page tests verify the position / interview / recommender delete paths each have their own dialog. The cross-page test is forward-defence against a NEW destructive path that someone adds without going through the dialog pattern. Concrete scenario: a future Phase 7 / v1.0 polish adds a "Quick close" button on the dashboard that calls `database.delete_position` directly because the implementer thought "it's a one-click action, no big deal". The per-page test for `pages/1_Opportunities.py` doesn't fire because the new caller is on `app.py`. The cross-page test fires because it walks ALL page files. Cost is a single AST walk per test run (~milliseconds); benefit is a cohesion guarantee that scales as the project grows. Same intuition as the `set_page_config` sweep in T3 — sweeps catch the regressions that per-page tests don't see.

**Q5. The `test_dialog_failure_preserves_pending_sentinel` test asserts `st.session_state.pop` does NOT appear inside `except` handlers. Why source-AST instead of behavioural?**

A. Behavioural would mean: monkeypatch `database.delete_*` to raise → click Confirm → assert the dialog re-opens on the next AppTest run + pending sentinel survives in `st.session_state`. That works, but the source-AST check is **strictly stronger**. Behavioural tests verify "the contract holds for the inputs we tested"; the AST check verifies "the contract holds STRUCTURALLY" — for any input that triggers an exception in the try-block. A future code path that handles a different exception type might pop the sentinel in a way the behavioural test doesn't exercise (e.g. catches `OSError` separately). The AST check has zero false-negatives because it's invariant to the specific exception inputs. The cost is one ancestor-chain walk per `pop` call; the false-positive risk is also zero because `st.session_state.pop` outside the except handler (in the success-path Confirm/Cancel branches) sits in a sibling block, not an ancestor. Source-AST is the right granularity for "this code shape must hold structurally".

**Q6. The implementer caught a real bug instead of finding the no-op-PR outcome that T3 had. What changed?**

A. T3 (`set_page_config` sweep) was a **shape contract** — every page had the same call with the same kwargs from project inception. Phase 7 T3 just turned an unenforced convention into a structural test. T4 is a **content contract** — what does the dialog body actually say? — and content is much more drift-prone over time. The position-delete dialog was written when the schema had `positions → applications` + `positions → recommenders` (no `applications → interviews` cascade yet); the interview-cascade edge was added in v1.3 (Sub-task 8) but the dialog copy didn't get updated. Six months of project work between then and T4. Cohesion tests are valuable specifically for this shape of drift — the per-page test was written once in Phase 3 and never revisited; the cohesion test enforces a contract that has to track every schema change. T4's positive find is structural evidence the audit pattern works.

---

## Carry-overs

- **No new carry-overs introduced.** The fix landed inline; the cohesion test enforces the contract going forward; future schema changes that add CASCADE edges to `positions` (or add destructive paths anywhere else) will surface as failing tests in `TestConfirmDialogAudit`.

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-7-tier3` precedent. The six pre-merge
gates were re-run on the PR head locally (`pr-40` / `6efb709`) at
review time: ruff clean · `pytest tests/ -q` 864 passed + 1
xfailed · `pytest -W error::DeprecationWarning tests/ -q` 864
passed + 1 xfailed · status-literal grep 0 lines · standing
isolation gate `git status --porcelain exports/` empty · CI-mirror
local check 864 + 1 xfailed with `postdoc.db` moved aside ·
`Tests + Lint (3.14)` CI **conclusion: SUCCESS** verified via
`gh pr checks 40 --watch` + `gh pr view 40 --json
statusCheckRollup --jq '...'` per the standing `c284c20`
procedure._
