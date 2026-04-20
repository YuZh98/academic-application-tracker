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
| Python app | 🔄 Phase 3 T4-A–D complete — Overview + Requirements tabs live; T4-E (Materials, state-driven) next |

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
| Materials / Notes tab bodies (T4-E–F) | Pending (Tier 4) |
| State-driven Materials tab (shows only required docs) | Pending (Tier 4) |
| Save / Delete with confirm dialog | Pending (Tier 5) |

**Commit message:** `feat: add Opportunities page with quick-add and full edit`

---

### Phase 4 — Dashboard
**Goal:** Home page answers "What do I do today?" at a glance.

| Task | Status |
|------|--------|
| Write full `app.py` | Pending |
| KPI cards: Tracked / Applied / Interview Stage / Next Interview date | Pending |
| Application funnel chart (Plotly horizontal bar, color-coded by status) | Pending |
| Materials Readiness panel (ready vs. missing count) | Pending |
| Upcoming deadlines + events timeline (next 30 days, red if ≤ 7 days) | Pending |
| Recommender alerts panel (asked > 7 days, not yet submitted) | Pending |

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
- `GUIDELINES.md` — coding conventions
- `CLAUDE.md` — session memory
- `roadmap.md` — this file
