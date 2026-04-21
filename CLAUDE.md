# Working Memory
_Single source of context for any Claude session in this project._

---

## Who I Am
PhD candidate / recent graduate actively applying to postdoc positions.
On OPT. Building a personal tracker to manage the full application lifecycle.

---

## Project State
**Phase:** Phase 4 **in progress** — T1-A + T1-B + T1-C + T1-D shipped on `feature/phase-4-tier1`. Plan locked in `PHASE_4_GUIDELINES.md` (6 tiers, ~9 sessions, ~9.5 hr; critical path linear). 8 design decisions closed 2026-04-20; Tracked-bucket semantics + config.py carve-out locked 2026-04-21; Next-Interview format + selection rule locked 2026-04-21. 239 tests passing, zero deprecation warnings. Next session: **T1-E** (fully-empty-DB hero callout + CTA `st.switch_page()` into Opportunities, per decision U5).
**Git:** on `feature/phase-4-tier1`. Commits since branching: `test(phase-4-t1)` (T1-A) → `feat(phase-4-t1)` (T1-B) → `chore(phase-4-t1)` (T1-A/B rollup) → `test(phase-4-t1c)` → `feat(phase-4-t1c)` → `chore(phase-4-t1c)` → `test(phase-4-t1d)` → `feat(phase-4-t1d)` → `chore:` pending on this session's rollup.
**Database:** `postdoc.db` created and initialized (3 tables, 37 columns in positions). All 5 dashboard queries exist and are Phase-2 tested.
**App:** `app.py` renders title + top-row `🔄 Refresh` button + `st.columns(4)` × `st.metric` fully live: Tracked/Applied/Interview via `database.count_by_status()`; Next Interview via `database.get_upcoming_interviews()` + `_next_interview_display()` helper rendering `'{Mon D} · {institute}'` (earliest future date across both interview columns) or `"—"` when none. `pages/1_Opportunities.py` = Tiers 1–5 complete and frozen for Phase 4.

**Phase 4 deviation log (T1-B):** `PHASE_4_GUIDELINES.md` originally called for `st.metric(..., key=...)` keyed lookup in tests. Verified against live Streamlit 1.56 that `st.metric` has no `key=` parameter (`TypeError` on unexpected kwarg); `at.metric[i].key` is `None` because the base `Element.key` attr is only populated for stateful widgets. Tests use **label-based lookup** instead — matches DESIGN.md §app.py UI contract and is the idiomatic AppTest path for display-only elements. Guideline corrected in same `chore:` commit.

**Phase 4 deviation log (T1-C):** PHASE_4_GUIDELINES.md §Scope lists `config.py` as out-of-scope for Phase 4, but the per-bucket KPI counts genuinely needed a way to name specific statuses without violating the anti-hardcode rule (pre-merge grep `\[OPEN\]|\[APPLIED\]|\[INTERVIEW\]` in `app.py` must return zero hits). User approved a **narrow carve-out** on 2026-04-21: add three named aliases (`STATUS_OPEN` / `STATUS_APPLIED` / `STATUS_INTERVIEW`) over existing `STATUS_VALUES` entries — pure additive, no schema drift, no behavior change. **Tracked-bucket semantics** (user decision 2026-04-21): Tracked = count([OPEN]) + count([APPLIED]); INTERVIEW and OFFER are excluded because they have their own KPIs.

**Phase 4 decisions log (T1-D):** Next-Interview KPI format and selection rule (user 2026-04-21):
- **Format:** `'{Mon D} · {institute}'` (short month + day, no year, with institute — e.g. `"May 3 · MIT"`). Matches DESIGN.md §app.py wireframe verbatim.
- **Selection:** earliest FUTURE date across BOTH `interview1_date` AND `interview2_date` across all rows returned by `get_upcoming_interviews()`. The paired institute belongs to whichever position owns that winning date. Columns are symmetric; past dates in the same row as a future-far date are ignored (a row is included when *either* date is future, so per-cell filtering is required — not row-level).
- **Empty:** `"—"` (locked decision U3).
Helper lives in `app.py` as `_next_interview_display(df)` — uses `pd.isna` to cover both Python `None` (raw NULL) and `pandas.NaN` (NULL in an object-dtype column — same concern as the Tier 5 `_safe_str` pre-seed guard).

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
