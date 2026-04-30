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

**Last shipped tag:** `v0.4.0` (Phase 4 Tier 3 — Materials Readiness,
2026-04-22). Phase 4 T4 (Upcoming timeline) merged to `main` via
PR #12 (`483efa9`); Phase 4 T5 (Recommender Alerts) merged via
PR #13 (`c5a7c76`). `main` is currently at `c5a7c76`. The next tag
is `v0.5.0` once T6 closes.
See [`CHANGELOG.md`](CHANGELOG.md) for full version history.

**In flight:** Phase 4 T6 — pre-merge close-out for the dashboard —
on branch `feature/phase-4-tier6-Cohesion`. Three checkboxes: cross-
panel cohesion smoke ✅ (`reviews/phase-4-finish-cohesion-smoke.md`);
funnel disclosure-toggle polish ✅ (DESIGN §8.1 T6 amendment —
bidirectional, tertiary, subheader-row inline); full review doc +
PR + tag `v0.5.0` pending. 553 tests green under both pytest gates.

**Next up after `v0.5.0`:** Phase 5 — Applications page
(`pages/2_Applications.py`) per Q5 Option A from the 2026-04-27
v1 planning session, then Recommenders page, then Phase 6 Exports.

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
| 4 | Dashboard (`app.py`) — 5 panels | 🔄 T1-T5 ✅ · T6 in flight (cohesion smoke + toggle polish ✅; review + PR + tag `v0.5.0` pending) |
| 5 | Applications + Recommenders pages | ⏳ pending |
| 6 | Full exports + Export page | ⏳ pending |
| 7 | Polish (urgency colors, search, confirm dialogs, responsive) | ⏳ pending |

### Phase 4 — Dashboard (detail)

| Tier | Scope | Status |
|------|-------|--------|
| T1 | Shell + 4 KPI cards + empty-DB hero | ✅ v0.2.0 + v1.3 updates merged |
| T2 | Application funnel (FUNNEL_BUCKETS aggregation + bidirectional disclosure toggle + 3-branch empty-state) | ✅ v0.3.0 + v1.3 updates merged + T6 toggle polish |
| T3 | Materials readiness (two progress bars + CTA + empty state) | ✅ v0.4.0 (`5ac0f63`) |
| T4 | Upcoming timeline (merged deadlines + interviews; urgency column) | ✅ merged via PR #12 (`483efa9`) |
| T5 | Recommender alerts (grouped by person on dashboard; full mailto + LLM prompts on Phase 5 T6) | ✅ merged via PR #13 (`c5a7c76`) |
| T6 | Pre-merge review + PR + tag `v0.5.0` | 🔄 in flight — branch `feature/phase-4-tier6-Cohesion` (cohesion smoke ✅; funnel toggle polish ✅; full review + PR + tag pending) |

### Phase 5 — Applications + Recommenders (sketch)

Per **Q5 Option A**, build Applications page first.

- `pages/2_Applications.py` — submission/response/interview/result tracking
  per position; **inline interview list UI** per DESIGN §8.3 D-B
  (`apps_interview_{id}_*` keying, single Save form, `@st.dialog`-gated
  delete, R2-toast surfacing on add)
- `pages/3_Recommenders.py` — letter log; alerts grouped by recommender;
  reminder helpers per DESIGN §8.4 D-C (locked-body mailto + `LLM prompts
  (N tones)` expander)
- The R1/R2/R3 cross-table cascade is already wired in `database.py`
  (Sub-task 9, 2026-04-24). No ADR pending — pages call
  `upsert_application(propagate_status=True)` /
  `add_interview(propagate_status=True)` and surface a `st.toast` when
  the writer's return value indicates promotion.

### Phase 6 — Exports (sketch)

- Complete `exports.py` with three generators (`write_opportunities`,
  `write_progress`, `write_recommenders`)
- `pages/4_Export.py` with manual regenerate button + `st.download_button`
- `exports.write_all()` already wired into every `database.py` writer; turns on
  when the functions fill in

### Phase 7 — Polish (sketch)

- Urgency colors on the positions table
- Search bar on Opportunities (currently filter-only)
- ~~`st.set_page_config(layout="wide")` across the app~~ — `app.py`
  done as v1.3 alignment Sub-task 12; `pages/1_Opportunities.py`
  done as v1.3 alignment Sub-task 13; other `pages/*.py` follow when
  each page is built (DESIGN §8 specifies it on every page).
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
| ~~Presentation-layer `STATUS_LABELS` + Archived bucket~~ | Design critique | STATUS_LABELS shipped Sub-task 1; Archived bucket (`[REJECTED]`+`[DECLINED]`, D17) wired into `app.py` funnel as Sub-task 12 |
| ~~Delete 🔄 Refresh button~~ | Design critique (friend #2) | Shipped as v1.3 alignment Sub-task 12 (per DESIGN D13) |
| Soft-delete with undo toast | UX | Requires `archived_at` column + FK cascade adjustment |
| Interactive funnel (click → filtered Opportunities) | Friend #3 | Plotly click events + `st.session_state` filter handoff |
| Position search bar on Opportunities | UX | Substring search on `position_name` + `institute` |
| Clickable `link` column via `st.column_config.LinkColumn` | UX | 10-line change |
| ~~Tooltip on "Tracked" KPI explaining semantics~~ | UX | Shipped as v1.3 alignment Sub-task 12 — locked copy `"Saved + Applied — positions you're still actively pursuing"` |

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
