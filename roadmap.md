# Roadmap

_Phase tracker, ship criteria, and backlog. Update the tier/phase status on completion;
push deep detail to `CHANGELOG.md`._

---

## Vision

A local, single-user postdoc application tracker that answers one question clearly:
**"What do I do today?"** — built in a way that extends to a general job tracker
without rewriting existing code.

---

## Current Status

**v0.4.0** — Phase 4 Tier 3 (Materials Readiness) shipped to `main` at commit `5ac0f63`.
v1.1 documentation refactor merged via PR #7 (`main @ cf45c09`).
See [`CHANGELOG.md`](CHANGELOG.md) for full version history.

**In flight:** DESIGN-to-codebase alignment on branch `feature/align-v1.3` —
Sub-tasks 1–6 shipped (config additions, `REQUIREMENT_VALUES` Y/N → Yes/No
migration, `WORK_AUTH_OPTIONS` / `FULL_TIME_OPTIONS` vocabulary swap, DDL
DEFAULT clauses f-string-interpolated from `config.STATUS_VALUES[0]` /
`config.RESULT_DEFAULT` per DESIGN §6.2, `[OPEN]→[SAVED]` +
`"Med"→"Medium"` renames with two idempotent `UPDATE positions` loops in
`init_db()`, and `positions.updated_at` column + `AFTER UPDATE` trigger
per §6.2 + D25 with `ALTER TABLE ADD COLUMN` + backfill for pre-v1.3
DBs). 310 tests green · zero deprecation warnings.

**Next up:** remaining v1.3 alignment items (schema overhauls
incl. `work_auth_note`, interviews sub-table, confirmation_* and
reminder_sent_* splits, `recommenders.confirmed` INTEGER, cascade
R1/R2/R3 rewire), then Phase 4 Tier 4 (Upcoming timeline).

---

## v1 Ship Criteria

v1.0 ships when **all three** are true:

1. **All phases complete** — Phase 4 T4–T6, Phase 5 (Applications + Recommenders
   pages), Phase 6 (exports), with Phase 7 polish bar to be set at T6 close.
2. **Publish scaffolding** — `README.md`, `LICENSE`, `CHANGELOG.md` committed at
   the repo root.
3. **Working demo path** — either a live [Streamlit Cloud](https://streamlit.io/cloud)
   instance or a recorded walkthrough GIF in `docs/`.

### Nice-to-have (not binding)
- Pre-commit (ruff) + GitHub Actions CI green on main
- 300+ tests on main; zero deprecation warnings
- Cold-clone to running app in ≤ 3 commands

---

## Phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Environment & config | ✅ shipped (see CHANGELOG) |
| 2 | Data layer (`database.py`, `exports.py` stub, `postdoc.db`) | ✅ shipped |
| 3 | Opportunities page (quick-add, filter, table, edit, delete) | ✅ shipped @ v0.1.0 |
| 4 | Dashboard (`app.py`) — 5 panels | 🔄 T1-T3 ✅ · T4-T6 pending |
| 5 | Applications + Recommenders pages | ⏳ pending |
| 6 | Full exports + Export page | ⏳ pending |
| 7 | Polish (urgency colors, search, confirm dialogs, responsive) | ⏳ pending |

### Phase 4 — Dashboard (detail)

| Tier | Scope | Status |
|------|-------|--------|
| T1 | Shell + 4 KPI cards + 🔄 refresh + empty-DB hero | ✅ v0.2.0 (`f49ec5f`) |
| T2 | Application funnel (Plotly + empty state + left half-column) | ✅ v0.3.0 (`96a5c76`) |
| T3 | Materials readiness (two progress bars + CTA + empty state) | ✅ v0.4.0 (`5ac0f63`) |
| T4 | Upcoming timeline (merged deadlines + interviews; urgency column) | 🟠 next |
| T5 | Recommender alerts (grouped by person; `mailto:` link) | ⏳ pending |
| T6 | Pre-merge review + PR | ⏳ pending |

### Phase 5 — Applications + Recommenders (sketch)

- `pages/2_Applications.py` — submission/response/interview/result tracking per position
- `pages/3_Recommenders.py` — letter log; alerts grouped by recommender; `mailto:`
- **Design TBD (C13):** cross-table cascade "response_type='Offer' → positions.status"
  moves into `database.py` as a `propagate_status=True` kwarg on
  `upsert_application`. An ADR will land when the decision is finalized.

### Phase 6 — Exports (sketch)

- Complete `exports.py` with three generators (`write_opportunities`,
  `write_progress`, `write_recommenders`)
- `pages/4_Export.py` with manual regenerate button + `st.download_button`
- `exports.write_all()` already wired into every `database.py` writer; turns on
  when the functions fill in

### Phase 7 — Polish (sketch)

- Urgency colors on the positions table
- Search bar on Opportunities (currently filter-only)
- `st.set_page_config(layout="wide")` across the app
- Confirm dialogs audit
- Responsive layout check

---

## Post-v1 Backlog

Prioritized. Items land here when deferred from a phase; a P-tier is a rough
ordering, not a commitment.

### P1 — soon after v1

| Item | Source | Notes |
|------|--------|-------|
| ~~Rename `[OPEN]` → `[SAVED]` + `"Med"` → `"Medium"`~~ | Design critique (friend #1) | Shipped as v1.3 alignment Sub-task 5 on `feature/align-v1.3` |
| Presentation-layer `STATUS_LABELS` + `ARCHIVED_BUCKET` | Design critique | Same batch as rename |
| Delete 🔄 Refresh button | Design critique (friend #2) | Same batch |
| Soft-delete with undo toast | UX | Requires `archived_at` column + FK cascade adjustment |
| Interactive funnel (click → filtered Opportunities) | Friend #3 | Plotly click events + `st.session_state` filter handoff |
| Position search bar on Opportunities | UX | Substring search on `position_name` + `institute` |
| Clickable `link` column via `st.column_config.LinkColumn` | UX | 10-line change |
| Tooltip on "Tracked" KPI explaining semantics | UX | `st.metric(..., help=...)` |

### P2 — medium term

| Item | Source | Notes |
|------|--------|-------|
| AI-populate quick-add from listing URL | Friend #4 | New **Phase 8**; new dep (anthropic / openai SDK); `prefill: dict` hook in quick-add keeps v1 forward-compatible |
| Cloud backup of `postdoc.db` (periodic upload to S3 / iCloud / Dropbox) | Friend #6 | Simplest today: drop the project folder into an iCloud/Dropbox-synced location |
| File attachments on Materials panel (PDF/MD/TeX) | DESIGN.md §11 | Full sketch already in DESIGN; new `attachments` table + FK cascade + `shutil.rmtree` on delete |
| Recommender edit inline within Opportunities edit panel | UX | Rather than only on separate Recommenders page |
| Urgency colored badge / emoji prefix | Phase 7 | Column_config conditional formatting |
| Offer details sub-table (start date, salary notes, decision deadline) | ADR-001 legacy | New `offers` table linked from `applications` |
| Funding source field | ADR-001 legacy | Append to `QUICK_ADD_FIELDS` + schema |
| Interview prep notes (format, interviewer, retrospective) | ADR-001 legacy | Extend `applications` table |

### P3 — eventually

| Item | Source | Notes |
|------|--------|-------|
| Application goal setting + progress bar on dashboard | ADR-001 legacy | New `settings` table |
| Source effectiveness chart (sources → interviews conversion) | ADR-001 legacy | Derived; no new columns |
| Application timeline chart (cluster around deadlines) | ADR-001 legacy | Derived from `applied_date` |
| Keyboard shortcuts (N = new, / = search) | UX | Streamlit keyboard support limited |
| Markdown rendering in notes | UX | `st.markdown` alongside `st.text_area` |

---

## v2 Vision — General Job Tracker

The tracker is designed so that reskinning to a different job context requires
**editing `config.py` only** — no changes to `database.py`, `exports.py`, or page files.

| Step | What changes |
|------|-------------|
| Set `TRACKER_PROFILE = "software_eng"` | One line (pending C2 wire-up) |
| Add `salary_range`, `equity`, `remote_ok` to the schema via new columns | `REQUIREMENT_DOCS`-style additions or a parallel `JOB_FIELDS` block |
| Add `req_coding_challenge` to `REQUIREMENT_DOCS` | One tuple; `init_db()` migrates |
| Replace pipeline statuses if needed | Edit `STATUS_VALUES` + `STATUS_COLORS` + `TERMINAL_STATUSES` |

A future profile-aware `init_db()` could conditionally include/exclude columns.
v1 leaves postdoc-specific columns in place (NULL for non-postdoc rows) and
hides them from the UI.

**Backward compatibility:** users upgrading from the postdoc build to the
generalized v2 keep their existing data. Schema is additive.

---

## Explicitly Out of Scope (for v1)

- User authentication (single user, local only)
- Cloud deployment (local-only app; backup is optional)
- Mobile-first layout
- Email integration (the `mailto:` link covers 90% of the need)
- Calendar sync
- AI-assisted position discovery or matching (P2 backlog handles ingestion, not discovery)

---

## Design Reference

Architectural decisions, technical specification, and coding conventions:

- [`DESIGN.md`](DESIGN.md) — master technical specification (architecture,
  schema, UI contracts, extension points)
- [`GUIDELINES.md`](GUIDELINES.md) — coding conventions (read at every session start)
- [`docs/adr/`](docs/adr/README.md) — architectural decision records (v1.1+)
- [`docs/dev-notes/`](docs/dev-notes/) — Git workflow depth, Streamlit state gotchas
- [`CHANGELOG.md`](CHANGELOG.md) — release history
- [`reviews/`](reviews/) — pre-merge review docs, one per tier
