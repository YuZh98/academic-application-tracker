# Working Memory
_Single source of context for any Claude session in this project._

---

## Who I Am
PhD candidate / recent graduate actively applying to postdoc positions.
On OPT. Building a personal tracker to manage the full application lifecycle.

---

## Project State
**Phase:** Phase 4 **Tier 3 complete, T4 next** — T1 merged via PR #4 (`f49ec5f`), T2 merged via PR #5 (`96a5c76`). T3 shipped on `feature/phase-4-tier3-MaterialReadiness` as a single commit-triple (D4=κ — T3-A + T3-B merged into one sub-tier per conductor brief): two `st.progress` bars (`"Ready to submit: N"` / `"Still missing: M"`, values = count / `max(total, 1)`) inside the right half of T2-C's `st.columns(2)`, plus a `"→ Opportunities page"` CTA (`key="materials_readiness_cta"`) that `st.switch_page`s to `pages/1_Opportunities.py`. Empty-state (when `ready + pending == 0`, including terminal-only DBs because `compute_materials_readiness()` excludes terminal statuses) renders `st.info("Materials readiness will appear once you've added positions with required documents.")` — no bars, no CTA. Subheader `"Materials Readiness"` ALWAYS renders (page-height stability). Plan locked in `PHASE_4_GUIDELINES.md` (6 tiers, ~9 sessions, ~9.5 hr; critical path linear). 8 design decisions closed 2026-04-20; Tracked-bucket semantics + config.py carve-out locked 2026-04-21; Next-Interview format + selection rule locked 2026-04-21; empty-DB hero trigger operationalized as `tracked + applied + interview == 0` (2026-04-21); funnel empty-state trigger + copy locked 2026-04-21 (Option C + wording γ); T3 visual + CTA + empty-state + denominator guard locked 2026-04-22. **271 tests passing, zero deprecation warnings.** Next: **T4** (Upcoming timeline).
**Git:** on `feature/phase-4-tier3-MaterialReadiness` branched off `main` at `96a5c76`. Commits this branch: T3 test-red → T3 feat-green → T3 chore tracker rollup (this commit). Ready for T6-A pre-merge review once T4+ complete, or interim merge.
**Database:** `postdoc.db` created and initialized (3 tables, 37 columns in positions). All 5 dashboard queries exist and are Phase-2 tested.
**App:** `app.py` renders title + top-row `🔄 Refresh` button + empty-DB hero callout (bordered `st.container` with welcome subheader + primary CTA button `"+ Add your first position"` calling `st.switch_page("pages/1_Opportunities.py")`; fires when `tracked == 0 and applied == 0 and interview == 0`, per U5) + `st.columns(4)` × `st.metric` fully live (Tracked/Applied/Interview via `database.count_by_status()`; Next Interview via `database.get_upcoming_interviews()` + `_next_interview_display()` helper rendering `'{Mon D} · {institute}'` or `"—"`) + `_left_col, _right_col = st.columns(2)` where LEFT holds **Application Funnel** subheader (always visible) + EITHER `st.info("Application funnel will appear once you've added positions.")` when `sum(count_by_status().values()) == 0` (T2-B Option C) OR Plotly horizontal `go.Bar` (one bar per `config.STATUS_VALUES`, x from `count_by_status()` with sparse-dict fill to 0, `marker_color` from `config.STATUS_COLORS`, y-axis reversed for top-down reading, chart key `funnel_chart`); RIGHT holds **Materials Readiness** subheader (always visible) + EITHER `st.info("Materials readiness will appear once you've added positions with required documents.")` when `ready + pending == 0` OR two `st.progress` bars (`text=f"Ready to submit: {N}"` and `text=f"Still missing: {M}"`, values = count / `max(ready + pending, 1)` per D5) followed by `st.button("→ Opportunities page", key="materials_readiness_cta")` routing via `st.switch_page("pages/1_Opportunities.py")`. `pages/1_Opportunities.py` = Tiers 1–5 complete and frozen for Phase 4.

**Phase 4 deviation log (T1-B):** `PHASE_4_GUIDELINES.md` originally called for `st.metric(..., key=...)` keyed lookup in tests. Verified against live Streamlit 1.56 that `st.metric` has no `key=` parameter (`TypeError` on unexpected kwarg); `at.metric[i].key` is `None` because the base `Element.key` attr is only populated for stateful widgets. Tests use **label-based lookup** instead — matches DESIGN.md §app.py UI contract and is the idiomatic AppTest path for display-only elements. Guideline corrected in same `chore:` commit.

**Phase 4 deviation log (T1-C):** PHASE_4_GUIDELINES.md §Scope lists `config.py` as out-of-scope for Phase 4, but the per-bucket KPI counts genuinely needed a way to name specific statuses without violating the anti-hardcode rule (pre-merge grep `\[OPEN\]|\[APPLIED\]|\[INTERVIEW\]` in `app.py` must return zero hits). User approved a **narrow carve-out** on 2026-04-21: add three named aliases (`STATUS_OPEN` / `STATUS_APPLIED` / `STATUS_INTERVIEW`) over existing `STATUS_VALUES` entries — pure additive, no schema drift, no behavior change. **Tracked-bucket semantics** (user decision 2026-04-21): Tracked = count([OPEN]) + count([APPLIED]); INTERVIEW and OFFER are excluded because they have their own KPIs.

**Phase 4 decisions log (T1-D):** Next-Interview KPI format and selection rule (user 2026-04-21):
- **Format:** `'{Mon D} · {institute}'` (short month + day, no year, with institute — e.g. `"May 3 · MIT"`). Matches DESIGN.md §app.py wireframe verbatim.
- **Selection:** earliest FUTURE date across BOTH `interview1_date` AND `interview2_date` across all rows returned by `get_upcoming_interviews()`. The paired institute belongs to whichever position owns that winning date. Columns are symmetric; past dates in the same row as a future-far date are ignored (a row is included when *either* date is future, so per-cell filtering is required — not row-level).
- **Empty:** `"—"` (locked decision U3).
Helper lives in `app.py` as `_next_interview_display(df)` — uses `pd.isna` to cover both Python `None` (raw NULL) and `pandas.NaN` (NULL in an object-dtype column — same concern as the Tier 5 `_safe_str` pre-seed guard).

**Phase 4 notes log (T2-A):** AppTest access pattern for Plotly — `at.get("plotly_chart")[i].proto.spec` is JSON (figure `{data: [...], layout: {...}}`); `.value` triggers `session_state KeyError` for stateless charts, so the proto-spec path is the stable one. `count_by_status()` returns a SPARSE dict (zero-count statuses omitted), so `app.py` expands with `[_status_counts.get(s, 0) for s in STATUS_VALUES]` to keep the chart shape stable as the pipeline fills up. `marker_color` list is built with `[config.STATUS_COLORS[s] for s in STATUS_VALUES]` — same anti-typo guardrail as the status literals. **Y-axis fix:** Plotly renders horizontal bars bottom-to-top by default; `fig.update_yaxes(autorange="reversed")` flips the rendering so `[OPEN]` sits at the top and `[DECLINED]` at the bottom, matching `STATUS_VALUES` reading order.

**Phase 4 decisions log (T2-B, locked 2026-04-21):**
- **Trigger (Option C):** funnel empty-state fires iff `sum(count_by_status().values()) == 0` — strictly no rows in the positions table. A DB with only terminal-status rows ([CLOSED]/[REJECTED]/[DECLINED]) still renders the figure; the T1-E hero separately covers "no active pipeline," so the funnel's job remains purely visualizing whatever pipeline state exists. Pinned by `test_terminal_only_db_still_renders_figure`. Swapping to Option A later is a single-test change.
- **Copy (wording γ):** `"Application funnel will appear once you've added positions."` (exact match, pinned by `test_empty_state_copy_is_spec_exact`).
- **Render:** `st.info(...)` in the empty-state branch; subheader `"Application Funnel"` renders in BOTH branches so page height doesn't flicker when the first position lands.

**Phase 4 decisions log (T2-C, locked by U2 + implemented 2026-04-21):** Funnel + Readiness sit side-by-side in a single `_left_col, _right_col = st.columns(2)` block in `app.py`. The split is created ONCE (not re-split in T3) — T3-B will reuse `_right_col`. AppTest detects the pair via `col.proto.weight == 0.5` (distinct from the dashboard's other splits: `st.columns([6,1])` title row weights ≈0.857/0.143, KPI grid `st.columns(4)` weight 0.25 each). Any future 2-column split on the dashboard will trip `TestT2CFunnelLayout::test_exactly_two_half_width_columns_exist` — intentional guard.

**Phase 4 T6-A carry-over (resolved in T2-C `feat:`):** The doc comment previously referenced `[OPEN]` / `[DECLINED]` to explain the y-axis reversal. Reworded in the T2-C `feat:` commit to reference "first/last STATUS_VALUES entry" instead. `grep -nE "\[OPEN\]|\[APPLIED\]|\[INTERVIEW\]" app.py` now returns zero hits in both code AND comments — pre-merge grep rule fully clean.

**Phase 4 decisions log (T1-E):** Empty-DB hero trigger operationalized as `tracked == 0 and applied == 0 and interview == 0` (2026-04-21). Two readings of U5 ("fully-empty-DB") were possible — strictly zero positions vs. all-three-counted-KPIs zero. Picked the latter because Phase 4 is scoped to `app.py` + tests only (no new `database.py` helper allowed). Consequence: a DB with only terminal-status rows ([CLOSED]/[REJECTED]/[DECLINED]) still fires the hero. This edge case is pinned by `test_terminal_only_db_still_shows_hero` so any future narrowing (e.g. once a `count_all_positions()` helper exists) is a visible one-test change. CTA route (`st.switch_page("pages/1_Opportunities.py")`) asserted at the source level because AppTest single-file mode has no sibling-page registry — an actual button click would raise rather than navigate.

**To run:**
```
source .venv/bin/activate
streamlit run app.py
```

---

## What This System Is
A local, single-user Streamlit web app backed by SQLite.
Three layers: `postdoc.db` (data) → `database.py` (logic) → Streamlit pages (UI).
Markdown files in `exports/` are auto-generated backups, not the source of truth.

---

## Key Files

### Source code
| File | Role |
|------|------|
| `config.py` | ALL constants: status values, priority options, document types, thresholds ✅ |
| `database.py` | All SQLite reads/writes; no Streamlit imports ✅ |
| `exports.py` | Regenerates markdown files; stub until Phase 6 ✅ |
| `app.py` | Dashboard home page stub ✅ (Phase 4 = full dashboard) |
| `pages/1_Opportunities.py` | Quick-add + filter bar + table + row selection + edit panel with all four tabs' Save + Overview Delete ✅ (T1–T5 complete) |
| `pages/2_Applications.py` | Progress tracking + status updates |
| `pages/3_Recommenders.py` | Recommender log + pending alerts |
| `pages/4_Export.py` | Manual export trigger + file download |

### Data files
| File | Role |
|------|------|
| `postdoc.db` | SQLite database — **authoritative source of truth** (gitignored) |
| `exports/OPPORTUNITIES.md` | Auto-generated from positions table |
| `exports/PROGRESS.md` | Auto-generated from applications table |
| `exports/RECOMMENDERS.md` | Auto-generated from recommenders table |

### Design documents (human-maintained, committed)
| File | Role |
|------|------|
| `DESIGN.md` | Master technical specification — architecture, schema, UI wireframes, data flow |
| `GUIDELINES.md` | Coding conventions for all sessions |
| `PHASE_4_GUIDELINES.md` | Phase-4-specific rules, locked decisions, sub-task breakdown (load each Phase 4 session) |
| `roadmap.md` | Phases, status, backlog, future plans |
| `OPPORTUNITIES.md` | Original hand-maintained table (superseded by DB once app is built) |
| `PROGRESS.md` | Original hand-maintained table (superseded by DB) |
| `RECOMMENDERS.md` | Original hand-maintained table (superseded by DB) |

---

## Database Tables (3)
- `positions` — one row per position; holds all overview + requirements + materials done state
- `applications` — one row per position; holds submission dates, response, interview, result
- `recommenders` — many rows per position; holds per-recommender asked/confirmed/submitted

**Foreign keys:** `applications` and `recommenders` reference `positions.id` with `ON DELETE CASCADE`.

---

## Status Pipeline (ordered)
| Value | Meaning |
|-------|---------|
| `[OPEN]` | Found; not yet applied |
| `[APPLIED]` | Application submitted |
| `[INTERVIEW]` | Reached interview stage |
| `[OFFER]` | Offer received |
| `[CLOSED]` | Deadline passed; did not apply |
| `[REJECTED]` | Rejection received |
| `[DECLINED]` | Offer turned down |

**These values live in `config.STATUS_VALUES`. Never hardcode them in page files.**

---

## Key Design Decisions (do not undo without reason)

| Decision | Rationale |
|----------|-----------|
| All field/status/vocab definitions in `config.py` | Open/Closed Principle — add new field types by editing one file |
| `deadline_date` is an ISO date string, not freetext | All "X days away" computations require a real date |
| `done_*` fields are `INTEGER 0/1` in positions table | Materials readiness is computed at query time, not stored |
| `database.py` calls `exports.write_all()` after every write | Markdown backups are always current; no manual export needed |
| IDs are internal; UI shows `position_name + institute` | Users should never need to know or manage database IDs |
| Quick-add form has exactly 6 fields | Capture friction must be minimal at discovery time |
| Status set via `st.selectbox` from `config.STATUS_VALUES` | Prevents typos that silently corrupt pipeline queries |
| All date fields use `st.date_input()` | Enforces `YYYY-MM-DD` format without custom validation |

---

## People
| Who | Role |
|-----|------|
|     |      |
_(Fill in recommenders and collaborators as they appear)_

---

## Vocabulary
| Term | Meaning |
|------|---------|
| Quick-add | 6-field capture form; saves immediately with defaults |
| Materials readiness | Computed score: how many required docs have `done_* = 1` |
| Recommender alert | Recommender asked > 7 days ago with no `submitted_date` |
| Tracker profile | Config switch: `"postdoc"` today; `"software_eng"` or `"faculty"` later |
