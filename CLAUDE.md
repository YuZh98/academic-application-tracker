# Working Memory
_Single source of context for any Claude session in this project._

---

## Who I Am
PhD candidate / recent graduate actively applying to postdoc positions.
On OPT. Building a personal tracker to manage the full application lifecycle.

---

## Project State
**Phase:** Phase 3 T4-A–C done — row selection + edit-panel shell + Overview tab (7 pre-filled widgets in st.form); 167 tests passing. Next: T4-D (Requirements tab — config-driven checkboxes).
**Git:** `feature/phase-3-tier4` branch active; T4-A–C commits local.
**Database:** `postdoc.db` created and initialized (3 tables, 37 columns in positions).
**App:** `app.py` stub exists (launches with placeholder). `pages/1_Opportunities.py` has quick-add form + filter bar + positions table (Tiers 1–3 done).

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
| `pages/1_Opportunities.py` | Quick-add + filter bar + table + row selection + edit-panel shell ✅ (T1–T3 + T4-A/B) — T4-C–T5 pending |
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
