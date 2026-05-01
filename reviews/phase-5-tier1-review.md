# Phase 5 Tier 1 — Applications page shell — Pre-merge review

**Branch:** `feature/phase-5-tier1-ApplicationsPageShell`
**Scope:** Phase 5 T1 — Applications page shell (`pages/2_Applications.py`); 3 sub-tasks (T1-A reader `database.get_applications_table()`; T1-B page + status-filter selectbox; T1-C read-only six-column table).
**Verdict:** Approve. (Two 🟡 polish items + two 🟢 future items are deferred — see Findings.)
**Date:** 2026-04-30
**Spec authority:** `DESIGN §8.3` + `docs/ui/wireframes.md#applications`
**Test gates:** `pytest tests/ -q` and `pytest -W error::DeprecationWarning tests/ -q` — both green at **586 passed** (553 baseline + 33 new).

---

## 1 · Executive summary

Phase 5 T1 lands the **Applications page shell**: a new `pages/2_Applications.py` with `set_page_config(layout="wide")`, `st.title("Applications")`, a status filter selectbox keyed `apps_filter_status`, and a read-only six-column table sorted by deadline. The work was split into three sub-tasks (T1-A reader, T1-B page+filter, T1-C table) and shipped via the project's TDD three-commit cadence — 9 commits, each with a clear RED → GREEN → chore boundary.

**One DESIGN amendment** lands inline in this work: the original DESIGN §8.3 D-A spec called for a per-cell tooltip on the Confirmation column. Streamlit 1.56's `st.dataframe` does not expose a per-cell tooltip API, so the amendment folds the tooltip text into inline cell content (three states: `—` / `✓ {Mon D}` / `✓ (no date)`). This trade-off is the only contract change in the tier; alternatives considered are documented in the Q&A below.

**Verdict:** Approve. (Two 🟡 polish items + two 🟢 future items are deferred — see Findings.)

---

## 2 · Findings

| # | Severity | Location | Description | Status |
|---|----------|----------|-------------|--------|
| 1 | 🟡 polish | `pages/2_Applications.py:51` | `_FILTER_ALL = "All"` is a page-local magic literal. Parity with `pages/1_Opportunities.py`'s "All" usage; the user's Q3 directive moved only "Active" to config. | Deferred — promoting "All" to config is a project-wide refactor (touches Opportunities filter too). |
| 2 | 🟡 drift | DESIGN.md §8.3 D-A | The original D-A wording specified a per-cell tooltip; that API doesn't exist in Streamlit 1.56's `st.dataframe`. Resolution = inline cell text. | Fixed inline — DESIGN.md amended in the T1-C GREEN commit (`8a07db1`); this review doc is the canonical resolution record. |
| 3 | 🟢 future | CHANGELOG.md `[Unreleased]` | Post-v0.4.0 work (v1.3 alignment + Phase 4 T4 + T5 + T6 + this T1) has accumulated under `[Unreleased]`. The `v0.5.0` tag now exists but no `[v0.5.0]` release section sits between `[Unreleased]` and `[v0.4.0]`. | Logged — separate housekeeping commit. Not blocking T1 merge. |
| 4 | 🟢 future | `pages/2_Applications.py` Confirmation column | If a future Streamlit release adds per-cell tooltips for `st.dataframe`, the inline-text workaround can be reverted to honor the original DESIGN §8.3 D-A wording. | Logged in DESIGN amendment block + this review's Q&A. |

No 🔴 (bug) or 🟠 (drift requiring blocking fix) findings.

### Test coverage

| Surface | Test class | Methods | Runs (parametrize-aware) |
|---------|-----------|---------|--------------------------|
| Database reader | `tests/test_database.py::TestGetApplicationsTable` | 8 | 8 |
| Config sentinel + invariant #12 | `tests/test_config.py` (7 standalone tests) | 7 | 7 |
| Page set_page_config | `tests/test_applications_page.py::TestPageConfigSetsWideLayout` | 1 | 1 |
| Page shell (title) | `tests/test_applications_page.py::TestApplicationsPageShell` | 2 | 2 |
| Filter bar | `tests/test_applications_page.py::TestApplicationsFilterBar` | 3 | 3 |
| Table render | `tests/test_applications_page.py::TestApplicationsPageTable` | 8 | 12 (4 standalone + 6 parametrize rows) |
| **Total** | | **29 methods** | **33 runs** |

Boot smoke (per project_state precedent — preview tool's macOS sandbox blocks `.venv` access):

```
$ streamlit run app.py --server.port 8502 --server.headless true ...
ROOT_STATUS=200
APPS_STATUS=200    (path: /Applications)
```

No errors in the streamlit log.

### Commits in the tier (9, oldest first)

| SHA | Type | Sub-task |
|-----|------|----------|
| `097f1ae` | `test` | T1-A RED |
| `a8ed04f` | `feat` | T1-A GREEN |
| `c295ace` | `chore` | T1-A tracker |
| `a3c9c5a` | `test` | T1-B RED |
| `325de05` | `feat` | T1-B GREEN |
| `34dbcb0` | `chore` | T1-B tracker |
| `3061e5d` | `test` | T1-C RED |
| `8a07db1` | `feat` | T1-C GREEN (also DESIGN §8.3 D-A amendment) |
| `3adb5a9` | `chore` | T1-C tracker |
| `b7badca` | `chore` | T1-D parent rollup + CHANGELOG |

(Plus the `v0.5.0` tag operation done as pre-flight before T1-A — that closes Phase 4 T6, not T1.)

---

## 3 · Junior-engineer Q&A

The questions below are the kind a code-reviewer new to the project might ask. The answers connect the design choice to the constraint that motivated it.

### Q1 · Why a brand-new `database.get_applications_table()` reader instead of looping over `get_all_positions()` and calling `get_application(pid)` per row?

Two reasons:

1. **Layer rule (GUIDELINES §2 / DESIGN §7).** Pages are SQL-free. The page can call `get_all_positions()` and `get_application(pid)`, but composing them via per-row calls means the page is doing a manual join — that's database-layer logic leaking into the page. Pushing the join into a single reader keeps each layer's responsibility honest.

2. **Per-row N+1.** With ~100 positions in a power-user's DB, the manual-join approach fires ~100 small SQL queries on every page render and every filter change. A single `LEFT JOIN` is one query. Both approaches return correct data; the reader approach is the one that scales.

The reader's API surface is tiny (one function, one call site for now) so the cost is low. T2 and T3 will reuse it.

### Q2 · Why is `"Active"` in `config.py` but `"All"` is still a magic literal in the page?

Asymmetric, but deliberate.

- **`"Active"` is a sentinel that encodes a domain decision** (which statuses count as "actionable" — `STATUS_VALUES \ STATUS_FILTER_ACTIVE_EXCLUDED`). That decision is part of the spec; it could be reused on the dashboard (e.g. a "Tracked: Active" KPI variant). Putting it in config makes the contract one click from the spec and gives invariant #12 something to guard.
- **`"All"` is a UI primitive.** It just means "no filter applied." Every selectbox-with-an-All-pass option in the project uses the literal `"All"` directly (`pages/1_Opportunities.py` has it too). Promoting `"All"` to config would be a project-wide refactor — and the user's Q3 directive specifically named "Active" only.

This drift is logged as 🟡 finding 1 above. It's a one-line addition + one-line edit per page, but it's larger than T1's contract. Worth doing in a future cleanup tier; not blocking now.

### Q3 · Streamlit 1.56's `st.dataframe` doesn't support per-cell tooltips. What alternatives did you consider, and why is "inline cell text" the chosen workaround?

Four options were on the table:

| Option | What it looks like | Why not chosen |
|--------|--------------------|----------------|
| **A — Inline cell text** (chosen) | `"✓ Apr 19"` / `"✓ (no date)"` / `"—"` directly in the cell. | Works in Streamlit 1.56. Every piece of D-A's information is visible at-a-glance. Matches the T4 Upcoming Date-column format precedent. |
| B — Column-header help only | `st.column_config.Column(help="✓ = received; — = pending. Hover row for date.")` — header tooltip only; no per-row date. | Information loss: the date itself disappears from the view. |
| C — pandas `Styler.set_tooltips(...)` | Render `df.style.set_tooltips(...)` HTML. | `st.dataframe` sends data through Arrow/protobuf; Styler tooltips don't transfer. Verified in 1.56 source. |
| D — Replace `st.dataframe` with HTML | Render the table as `st.html(df.to_html(...))` with `<td title="...">`. | Loses sort/selection/copy interactivity. Significantly worse UX. |

The D-A amendment (DESIGN §8.3) records option A as the resolution. If a future Streamlit release adds per-cell tooltips, the workaround is one apply-call to revert.

### Q4 · The Confirmation tests use `@pytest.mark.parametrize` with three rows. Why parametrize instead of three separate `test_*` methods?

Both shapes work and the test count is the same (3 either way). Parametrize wins on two counts here:

- **Failure messages name the case.** When run-1 fails, the failure ID reads `test_confirmation_column_inline_format[1-2026-04-19-✓ Apr 19]` — the failing case is in the test name. With three separate methods, you'd need to pattern-match on the method name to know which state broke.
- **Single source for the "what cells are valid" decision.** The three (received, date, expected) tuples sit at the top of the test body; future maintainers see the contract in one place. Three methods would split the contract across three docstrings.

Use separate methods when the test bodies need different SETUP. Here all three cases share the seed code (add_position + upsert_application + update_position) — the only thing that changes is the parameter triple.

### Q5 · `is_all_recs_submitted(pid)` returns `True` when the position has zero recommenders. Why? Doesn't that show a `✓` for a position that has no letters at all?

Yes — and that's deliberate. From `tests/test_database.py::TestIsAllRecsSubmitted::test_returns_true_for_zero_recommenders`:

> "Vacuous truth: a position with no recommenders has no outstanding letters by definition."

This matches the most natural reading of D23 ("nothing to still be submitted") and lets downstream "is everything ready?" aggregations compose without a "no recs" special case. It also means a user who hasn't yet entered any recommenders for a position won't see a misleading `—` in the Recs column — there's nothing pending, so the column shouldn't suggest there is.

If a future tier wants to differentiate "has zero recs" from "has all recs submitted" visually, that's an enrichment of the column display rule, not a change to the database semantic.

### Q6 · The SQL has `ORDER BY p.deadline_date ASC NULLS LAST, p.id ASC`. Why the `p.id ASC` tiebreaker?

Without it, SQLite is free to return rows with equal `deadline_date` in any order. Two positions with the same deadline could swap positions on consecutive page renders. That breaks two contracts:

1. **Selection survival across reruns** (per `streamlit-state-gotchas #11/#12`). The Opportunities page relies on the row's positional index to identify which row the user selected. If the index shifts under the user, the edit panel re-binds to a different row.
2. **AppTest stability.** `at.dataframe[0].value.iloc[0]["Position"]` is meaningless if `iloc[0]` could be either row.

The `p.id ASC` tiebreaker is monotonic in insertion order, so it's a stable, unambiguous secondary sort. T1-A's `test_position_id_breaks_deadline_ties` pins it.

### Q7 · The page module defines `EM_DASH = "—"` (U+2014, em-dash). Why a constant instead of inlining the literal?

Three reasons:

1. **Visibility.** A bare `"—"` in source code is easy to miss (it looks like a hyphen at small font sizes). Naming it `EM_DASH` makes it grep-able and makes intent clear at the call site.
2. **Cohesion.** Five call sites use it (`_format_date_or_em`, `_format_confirmation`, `_safe_str_or_em`, the Recs column lambda, the empty-cell fallback). One source of truth means a future "use a different placeholder glyph" change is a one-line edit.
3. **Dashboard precedent.** `app.py`'s T4 Upcoming panel and T5 Recommender Alerts already use `—` as the empty-cell glyph. Naming it here makes the convention visible without committing to promote it to `config.py`.

Inlining would also have worked. The constant is cheap and the readability win is real.

### Q8 · Why does the filter selectbox use `format_func=lambda v: STATUS_LABELS.get(v, v)` instead of branching on the sentinels in the page logic?

A `format_func` is a **display-only mapping** — it controls what the user sees in the dropdown, not what value flows back to `st.session_state[key]`. Using `STATUS_LABELS.get(v, v)`:

- For an unknown key like `"Active"` or `"All"`, the second arg of `.get(...)` falls back to identity, so the sentinels render as themselves.
- For a known `STATUS_VALUES` entry like `"[SAVED]"`, returns `"Saved"` (the user-facing label).

This is the cleanest one-liner that satisfies both the "display labels for real statuses" and "display sentinels as themselves" requirements without writing a dedicated helper. Branching in the page would also work (`if v in (STATUS_FILTER_ACTIVE, "All"): return v else: return STATUS_LABELS[v]`), but the lambda is shorter and the identity-fallback is idiomatic for `dict.get` in the project.

The filter logic itself (which statuses pass) is in the page body — the `format_func` only controls cosmetics.

### Q9 · The page uses `frozenset` for `STATUS_FILTER_ACTIVE_EXCLUDED`. Why frozen?

Two layered reasons:

- **Mutation guard.** A regular `set` could be mutated via `STATUS_FILTER_ACTIVE_EXCLUDED.add(...)` from any module that imports it. Pages run on a long-lived Streamlit process; a single accidental mutation could broaden the page's default filter for the rest of the session — a silent, hard-to-debug bug.
- **Hashable.** Frozensets are hashable; pages can put them in `set` operations or use them as dict keys without copying. Not used yet, but a free property.

Tests pin both the type (`isinstance(..., frozenset)`) and the membership (`== frozenset({STATUS_SAVED, STATUS_CLOSED})`).

### Q10 · The boot smoke is a Bash `streamlit run` + `curl`. Why not the preview tool that other Phase-4 tiers used?

The project_state memory documents this:

> "preview-tool macOS sandbox blocks headless capture on this setup; boot smoke ran via Bash `streamlit run` (HTTP 200)"

Reproduced 2026-04-30 — the preview tool fails on `Operation not permitted: '/Users/zhengyu/.../.venv/pyvenv.cfg'`. The macOS sandbox restricts the tool's process from reading `.venv/`. The Bash + curl path bypasses the sandbox entirely (the user's shell session has full access).

For the Phase 5 demo deliverable (Q7 from the v1 plan: live Streamlit Cloud demo + recorded GIF), this constraint will need a different solution — but for in-CI-feeling boot smokes during development, Bash + curl is fine.

---

## 4 · Verdict

**Approve.** Suite green, contract pinned, one DESIGN amendment in scope and recorded. Two 🟡 polish items + two 🟢 future items deferred per the table above.

Recommended next: open PR → merge T1 → start T2 (Application detail card per DESIGN §8.3 D-A glyph + tooltip rules, Response, Result, Notes — all editable via `st.form`). The detail card is where the Confirmation column's full information surfaces editably; the inline-text shortcut from T1-C does NOT need to propagate to the editor.
