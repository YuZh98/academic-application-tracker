# Pre-publication Code Review

**Branch:** `main`
**Scope:** Pre-publication code review — final audit of all source files against GUIDELINES.md conventions before making the repo public.
**Stats:** 909 passed, 1 xfailed; ruff clean; pyright 0/0
**Verdict:** Approve with findings

---

## Findings

| # | File | Line(s) | Severity | Finding |
|---|------|---------|----------|---------|
| 1 | database.py | 105 | 🟡 | `all_recs_submitted TEXT` is declared in the applications DDL but never written or read anywhere — stored summary of a computed value that violates DESIGN D23 / GUIDELINES §12. **Delete this line.** |
| 2 | database.py | 110–111 | 🟡 | `interview1_date` / `interview2_date` are flat-column relics replaced by the `interviews` sub-table per DESIGN D18; new DBs receive the dead columns on every fresh init. **Delete these two lines** from the CREATE TABLE (the migration block at 195–211 still works because it's gated by `interviews_existed_pre_create`). |
| 3 | database.py | 315–323 | 🟡 | The `Y`→`Yes` / `N`→`No` UPDATE loop runs on **every** `init_db()` call (i.e. every page load), scanning the positions table N times — guard it the way the schema-shape migrations are guarded (e.g. only run when a `req_*` column was just ALTER-added at 169–173). |
| 4 | database.py | 327–334 | 🟡 | The `[OPEN]`→`STATUS_SAVED` and `Med`→`Medium` legacy UPDATEs also fire on every page load with no schema-shape guard — wrap both in a one-shot guard so they don't scan the table forever. |
| 5 | database.py | 325–326 | ⚪ | `_legacy_saved = "[OPE" + "N]"` and `_legacy_medium = "M" + "ed"` are split with the comment "to avoid the CI lint check," but the `.pre-commit-config.yaml` regex only matches `[SAVED]/[APPLIED]/[INTERVIEW]` and only in `app.py` / `pages/`, so the workaround is unnecessary; **replace with `_legacy_saved = "[OPEN]"` and `_legacy_medium = "Med"`** and drop the misleading comments. |
| 6 | pages/2_Applications.py | 251, 284–289 | 🟡 | The "Letters" CheckboxColumn renders ✓ for any position with zero recommenders (vacuous truth from `is_all_recs_submitted`), so a row that doesn't need letters looks identical to "all letters in" — switch to a tri-state TextColumn that returns `EM_DASH` when there are no recommenders. |
| 7 | pages/2_Applications.py | 251 | ⚪ | `database.is_all_recs_submitted` is invoked once per displayed row via `.apply`, opening a fresh connection each call (N+1 pattern); replace with a single grouped query (e.g. add `database.get_recs_submitted_map()`). |
| 8 | pages/4_Export.py | 46 | 🟡 | `_EXPORT_FILENAMES = ("OPPORTUNITIES.md", "PROGRESS.md", "RECOMMENDERS.md")` is defined but never referenced — the loop uses `database.get_export_paths()`. **Delete this line.** |
| 9 | app.py | 269 | ⚪ | `st.info("...Click 'Show all stages' to reveal them.")` hardcodes the string from `config.FUNNEL_TOGGLE_LABELS[False]`; a config rename would silently desync — interpolate `config.FUNNEL_TOGGLE_LABELS[False]` (with the leading `+ ` stripped) instead. |
| 10 | pages/3_Recommenders.py | 545, 613 | ⚪ | `bool(_rec_row.get("reminder_sent") or 0)` and `int(_rec_row["reminder_sent"] or 0)` use the `r[col] or X` idiom GUIDELINES §12 explicitly bans (NaN is truthy, so `nan or 0` → `nan` which crashes `int(...)`); use a `_safe_str`-style NaN-aware coercion. |

---

## Finding Details

### F1: Vestigial `all_recs_submitted` column in applications DDL

The applications CREATE TABLE declares `all_recs_submitted TEXT`, but no writer or reader anywhere in the codebase touches that column — only the function `is_all_recs_submitted()` exists, which is a query helper that derives the result on demand. DESIGN D23 explicitly chose "summary flags that could be computed are computed, never stored," and GUIDELINES §12 lists "storing computed values in the DB" as an anti-pattern. Fix: delete line 105 from the CREATE TABLE; no migration needed since nothing depends on the column.

### F2: Vestigial `interview1_date` / `interview2_date` columns in applications DDL

DESIGN D18 replaced the two flat interview-date columns with the `interviews` sub-table; the migration loop at 195–211 already moves data out of those columns and the rest of the codebase reads exclusively from the sub-table. Yet a fresh DB still gets these columns spawned on every `init_db()` because they're declared in the canonical DDL. Fix: delete lines 110–111. The migration block at 195–211 stays as-is — it's gated by `interviews_existed_pre_create`, so it only runs against pre-D18 databases that still have the columns.

### F3: Idempotent-init migration UPDATEs scan positions on every page load

The loop at 315–323 issues a CASE-WHEN UPDATE for every `req_*` column on every `init_db()` call, which fires on every page load (Opportunities/Applications/Recommenders/Export all call it at top of file). After the first run the WHERE clause matches nothing, so the rows aren't rewritten — but each query still scans the `positions` table without an index on those columns. Fix: track which columns were just ALTER-added at 169–173 and only run the corresponding UPDATE for those columns; or wrap the whole loop in a one-shot sentinel (e.g. a `schema_version` row) so it runs at most once per DB.

### F4: Legacy status/priority migration UPDATEs also scan on every init

Same shape as F3: the `[OPEN]`→`STATUS_SAVED` and `Med`→`Medium` UPDATEs at 327–334 run on every `init_db()` invocation. The `idx_positions_status` index covers the status query but the priority one is unindexed. Fix: pair this block with the same one-shot guard from F3.

### F5: Misleading "split to avoid CI lint" comments

The `_legacy_saved = "[OPE" + "N]"` and `_legacy_medium = "M" + "ed"` runtime concatenations claim they're avoiding the CI status-literal lint check, but `.pre-commit-config.yaml`'s regex is `\[SAVED\]|\[APPLIED\]|\[INTERVIEW\]` (none of these matches `[OPEN]` or `Med`) and the rule only applies to `app.py` and `pages/` — `database.py` is unscanned. Fix: replace with the obvious string literals and delete the comments.

### F6: "Letters" CheckboxColumn shows ✓ for zero-recommender positions

The Applications-page table calls `database.is_all_recs_submitted` per row; that function returns `True` (vacuous truth) for any position with zero recommenders, which renders as a checked box — visually identical to "all letters submitted." A user looking at a position they haven't asked anyone about yet sees the same glyph as one where every letter is in, which is actively misleading. Fix: switch to `st.column_config.TextColumn` and return `EM_DASH` when the recommenders count is 0, `"✓"` only when count > 0 and all submitted, `"—"` otherwise.

### F7: N+1 query pattern on the Applications table render

Line 251 invokes `is_all_recs_submitted` once per filtered row via `df.apply`, and each call opens a new SQLite connection. At the documented scale ceiling (10²–10³ positions, DESIGN §3.1) this is hundreds of round-trips on every page render. Fix: add a `database.get_recs_submitted_map() -> dict[int, bool]` helper that returns the per-position summary in one query, and replace the per-row `apply` with a `.map(...)` against that dict.

### F8: Unused `_EXPORT_FILENAMES` constant

The constant at pages/4_Export.py:46 is defined but never referenced in production code (a test mentions the variable name as documentation, not as an import). The for-loop uses `database.get_export_paths()` instead. Dead code shouldn't ship in a public release. Fix: delete line 46.

### F9: Hardcoded toggle label in dashboard info message

The empty-state info message at app.py:269 quotes `'Show all stages'`, which is the visible portion of `config.FUNNEL_TOGGLE_LABELS[False]` (= `"+ Show all stages"`). If the config string is renamed for any reason — translation, copy iteration — this hint will silently say something different from the actual button. Fix: build the message via `config.FUNNEL_TOGGLE_LABELS[False].lstrip("+ ").strip()` (or interpolate the full label and accept the `+`).

### F10: `r[col] or 0` idiom on the Recommenders edit form

`bool(_rec_row.get("reminder_sent") or 0)` (line 545) and `int(_rec_row["reminder_sent"] or 0)` (line 613) repeat the exact NaN-truthy pitfall GUIDELINES §12 calls out (`bool(float('nan')) is True`, so `nan or 0 → nan`, which crashes `int(...)`). The column is declared `INTEGER DEFAULT 0` so NaN shouldn't surface in practice, but the idiom is the banned one. Fix: route through a NaN-aware helper, e.g. `int(_safe_str(_rec_row["reminder_sent"]) or 0)`, or `0 if pd.isna(v) else int(v)`.

---

## Verdict Rationale

No 🔴 findings; the codebase is functionally correct, layer-clean (no `streamlit` import in `database.py` / `exports.py`, no `exports` import in pages or `app.py`), uses parameterised SQL with the documented column-name f-string exception, has no `TODO`/`FIXME`/`HACK`/debug `print` left, and `.gitignore` properly excludes `postdoc.db` and `exports/`. The 🟡 findings are dead schema (F1, F2, F8), an init-time performance footgun on a hot path (F3, F4), and one user-visible UX confusion (F6). None block publication, but F1, F2, F6, and F8 are the kind of thing readers will notice within minutes of opening the repo. F3+F4 are invisible to a casual reader but make every page load do strictly more work than it should. Recommend addressing the 🟡s before going public; the ⚪s can land in a follow-up.
