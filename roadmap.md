# Project Roadmap
_Big-picture tracker. Update the status column as phases complete._

---

## Vision
A local, personal postdoc application tracker that answers one question clearly: **"What do I do today?"** — built in a way that can be extended to a general job tracker without rewriting existing code.

---

## Current State
| Layer | Status |
|-------|--------|
| Design | Complete |
| Markdown data files | Created and committed |
| Git repository | Initialized |
| Virtual environment | ✅ Created (.venv/) |
| Data layer | ✅ database.py + exports.py stub |
| SQLite database | ✅ postdoc.db initialized |
| Python app | 🔄 Phase 3 merged to main via PR #3 (`c972385`). Phase 4 **in progress** on `feature/phase-4-tier1`: T1-A + T1-B shipped (dashboard test scaffold + `app.py` shell with 4-column KPI skeleton); 225 tests green. Next: T1-C (top bar refresh + wire `count_by_status()`). |

---

## Implementation Phases

### Phase 1 — Environment & Configuration ✅
**Goal:** Clean, reproducible Python environment. All constants in one place.

| Task | Status |
|------|--------|
| Create `.venv` and install packages | ✅ Done (2026-04-15) |
| Generate `requirements.txt` with pinned versions | ✅ Done (2026-04-15) |
| Write `config.py` with all constants | ✅ Done (2026-04-15) |

**Installed versions:** `streamlit==1.56.0`, `plotly==6.7.0`, `pandas==3.0.2`
**Commit:** `chore: set up venv and config.py`

---

### Phase 2 — Data Layer ✅
**Goal:** SQLite schema live; data readable and writable from Python.

| Task | Status |
|------|--------|
| Write `database.py` with `init_db()` and all CRUD functions | ✅ Done (2026-04-16) |
| Write `exports.py` stub (called after every write) | ✅ Done (2026-04-16) |
| Create and initialise `postdoc.db` | ✅ Done (2026-04-16) |
| Verify queries return correct DataFrames in isolation | ✅ 88/88 checks passed |

**Commit message:** `feat: add database.py — SQLite schema and CRUD`

---

### Phase 3 — Opportunities Page
**Goal:** First working UI. Can add and view positions.

| Task | Status |
|------|--------|
| Stub `app.py` so Streamlit doesn't error on launch | ✅ Done (2026-04-17) |
| `pages/1_Opportunities.py` skeleton with section markers | ✅ Done (2026-04-17) |
| Quick-add form (6 fields, saves immediately) | ✅ Done (2026-04-17) |
| Filter bar (status, priority, field) | ✅ Done (2026-04-18) — reviewed |
| Positions table display (st.dataframe + deadline urgency) | ✅ Done (2026-04-18) — reviewed |
| Row selection on positions table (T4-A) | ✅ Done (2026-04-19) |
| Edit-panel shell — subheader + 4 tabs (T4-B) | ✅ Done (2026-04-19) |
| Overview tab — 7 pre-filled edit widgets (T4-C) | ✅ Done (2026-04-19) |
| Requirements tab — config-driven 3-way radios (T4-D) | ✅ Done (2026-04-19) |
| Materials tab — state-driven checkboxes (T4-E) | ✅ Done (2026-04-19) |
| Notes tab — text_area (T4-F) | ✅ Done (2026-04-19) |
| Overview Save — update_position + toast + error + selection survival (T5-A) | ✅ Done (2026-04-20) |
| Requirements Save (T5-B) | ✅ Done (2026-04-20) |
| Materials Save (T5-C) | ✅ Done (2026-04-20) |
| Notes Save (T5-D) | ✅ Done (2026-04-20) |
| Delete with st.dialog confirm (T5-E) | ✅ Done (2026-04-20) |
| Tier 5 pre-merge review + PR (T5-F) | ✅ Done (2026-04-20) — `reviews/phase-3-tier5-premerge.md` |

**Commit message:** `feat: add Opportunities page with quick-add and full edit`

---

### Phase 4 — Dashboard
**Goal:** Home page answers "What do I do today?" at a glance.
**Plan locked:** `PHASE_4_GUIDELINES.md` (6 tiers, ~9 sessions, ~9.5 hr; critical path linear).
**Test file:** single `tests/test_app_page.py` (per decision C8).

| Tier | Sub-task | Status |
|------|----------|--------|
| T1 | T1-A: `tests/test_app_page.py` scaffold + empty-DB smoke + 4-KPI shape test | ✅ Done (2026-04-20) |
| T1 | T1-B: `app.py` shell — title + `init_db()` + `st.columns(4)` × `st.metric` placeholders | ✅ Done (2026-04-20) |
| T1 | T1-C: top bar 🔄 refresh button + wire `count_by_status()` → 3 KPI values | Pending |
| T1 | T1-D: wire `get_upcoming_interviews()` → Next Interview (empty → `"—"`, per U3) | Pending |
| T1 | T1-E: fully-empty-DB hero callout + CTA (per U5) | Pending |
| T2 | T2-A: Plotly funnel from `count_by_status()` + `config.STATUS_COLORS` | Pending |
| T2 | T2-B: funnel empty-state render | Pending |
| T2 | T2-C: `st.columns(2)` left half (per U2) | Pending |
| T3 | T3-A: render `compute_materials_readiness()` | Pending |
| T3 | T3-B: `st.columns(2)` right half (per U2) | Pending |
| T4 | T4-A: merge deadlines + interviews DataFrame | Pending |
| T4 | T4-B: urgency column from config thresholds | Pending |
| T4 | T4-C: `st.dataframe(width="stretch")` render | Pending |
| T4 | T4-D: timeline empty state | Pending |
| T5 | T5-A: group `get_pending_recommenders` by recommender | Pending |
| T5 | T5-B: per-person card + `mailto:` link | Pending |
| T5 | T5-C: alerts empty state | Pending |
| T6 | T6-A: pre-merge review doc | Pending |
| T6 | T6-B: PR + merge + delete branch | Pending |

**Decisions log (locked 2026-04-20):**
- C3: keep `[🔄 Refresh]` button
- C4: skip `@st.cache_data` in Phase 4 (revisit post-merge only if slowness measured)
- C5: sync GUIDELINES.md §7 (`st.toast`) + §8 (no re-raise) — applied
- C6: DESIGN.md §6 line 431 readiness scope fix — applied
- C8: one test file `tests/test_app_page.py` for the whole dashboard
- U2: Funnel + Readiness via `st.columns(2)`; stacking on narrow windows OK
- U3: Next-Interview KPI shows `"—"` when empty
- U5: fully-empty-DB hero callout at top of `app.py`

**Commit message:** `feat: add dashboard home page`

---

### Phase 5 — Applications & Recommenders Pages
**Goal:** Full lifecycle tracking in the UI.

| Task | Status |
|------|--------|
| Write `pages/2_Applications.py` | Pending |
| Write `pages/3_Recommenders.py` | Pending |
| Recommender alert grouping (one row per person across all positions) | Pending |
| `mailto:` reminder link for overdue recommenders | Pending |

**Commit message:** `feat: add Applications and Recommenders pages`

---

### Phase 6 — Exports
**Goal:** Markdown files always in sync; downloadable from the app.

| Task | Status |
|------|--------|
| Complete `exports.py` (all three markdown generators) | Pending |
| Wire `exports.write_all()` into every `database.py` write function | Pending |
| Write `pages/4_Export.py` with manual trigger and `st.download_button` | Pending |
| Verify exported markdown matches current DB state | Pending |

**Commit message:** `feat: add exports.py and Export page`

---

### Phase 7 — Polish
**Goal:** Feels like a real app; no rough edges.

| Task | Status |
|------|--------|
| Deadline urgency colors (red ≤ 7 days, yellow ≤ 14 days) | Pending |
| Empty states ("No positions yet — use Quick Add above") | ✅ Done (2026-04-17) |
| Search bar on Opportunities table | Pending |
| Confirm dialog before delete | Pending |
| Responsive layout check | Pending |

**Commit message:** `feat: polish — colors, empty states, search, confirm dialog`

---

## Backlog (Post-v1, Prioritized)

These are accepted design decisions from ADR-001 that are intentionally deferred:

| Item | Priority | Notes |
|------|----------|-------|
| Offer details sub-table (start date, salary notes, decision deadline) | P2 | Add `offers` table; link from `applications` |
| Funding source field on positions | P2 | Add to `config.POSITION_FIELDS` and schema |
| Interview prep notes (format, interviewer, how it went) | P2 | Extend `applications` table |
| Application goal setting (target N applications) and progress bar | P2 | Store in a `settings` table; show on dashboard |
| Source effectiveness chart (which source yields most interviews) | P3 | Derived from existing `source` + `status` fields |
| Application timeline chart (when applications cluster around deadlines) | P3 | Derived from `applied_date` |
| File attachments on Materials panel (PDF / Markdown / TeX upload, open, replace, remove) | P2 | New `attachments` table + `attachments/` folder on disk; checkbox auto-flips on upload; FK cascade + `rmtree` on delete. Full design in DESIGN.md §11 "Adding file attachments to the Materials panel". |

---

## Future: General Job Tracker (v2)

The tracker is designed so this requires **editing `config.py` only** — no changes to `database.py`, `exports.py`, or page files.

| Step | What changes |
|------|-------------|
| Set `TRACKER_PROFILE = "software_eng"` | One line in `config.py` |
| Add `salary_range`, `equity`, `remote_ok` to `POSITION_FIELDS` | Three lines in `config.py` |
| Add `req_coding_challenge` to `REQUIREMENT_DOCS` | One line in `config.py` |
| Replace postdoc-specific status pipeline if needed | Edit `STATUS_VALUES` in `config.py` |

The DB schema is generated from `config.py` at `init_db()` time — new fields appear automatically.

---

## Out of Scope for v1
- User authentication (single user, local only)
- Cloud deployment
- Mobile-optimised layout
- Email integration (the `mailto:` link covers 90% of the need)
- Calendar sync
- AI-assisted position discovery or matching

---

## Design Reference
All architectural decisions, rationale, and critiques are recorded in this session's conversation history. Key documents committed to the repo:
- `DESIGN.md` — master technical specification (schema, UI wireframes, data flow)
- `GUIDELINES.md` — coding conventions (all sessions)
- `PHASE_4_GUIDELINES.md` — Phase-4-specific rules, locked decisions, sub-tasks
- `CLAUDE.md` — session memory
- `roadmap.md` — this file
