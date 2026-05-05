# Roadmap

_Phase tracker, ship criteria, and backlog. Update phase status on completion;
push deep detail to `CHANGELOG.md`. Live sprint tracker is `docs/internal/TASKS.md`._

---

## Vision

A local, single-user academic application tracker that answers one question
clearly: **"What do I do today?"** — built in a way that extends to a general
job tracker without rewriting existing code.

---

## Current Status

**Last shipped tag:** `v0.9.0` (v1.0-rc schema cleanup + publish-readiness
scaffolding, 2026-05-05). Schema cleanup (PR #47) physically dropped the
legacy `applications.confirmation_email` column via SQLite 3.35+
`ALTER TABLE DROP COLUMN`, closing the v1.3 Sub-task 10 split migration.
Publish-readiness (PR #46) added MIT `LICENSE` + public-facing
`README.md` + repo rename to `academic-application-tracker` + doc-tier
reorg moving dev-process artifacts to `docs/internal/` + Python
`>=3.11` floor declaration. Suite at 883 passed + 1 xfailed; pyright
fence holds 0/0.

See [`CHANGELOG.md`](CHANGELOG.md) for full version history.

**In flight:** the rest of v1.0-rc / v1.0.0:

1. **P4a Live demo** — Streamlit Cloud deploy (verify SQLite ephemeral-
   storage behavior or arrange persistence). User-driven.
2. **P4b Walkthrough GIF** — recorded short walkthrough committed to
   `docs/`. Bundles with **Phase 7 T5** (responsive layout at 1024 /
   1280 / 1440 / 1680 widths — screenshots to
   `docs/ui/screenshots/v1.0.0/`).
3. **P6** — `v1.0.0` PR + tag + GitHub release notes once P4a or P4b
   lands.

(P3 dep audit + P5 cross-doc link verify closed 2026-05-05.)

---

## v1 Ship Criteria

v1.0 ships when **all four** are true:

1. ✅ **All phases complete** — Phase 4 (Dashboard) at `v0.5.0`; Phase 5
   (Applications + Recommenders) at `v0.6.0`; Phase 6 (Exports) at
   `v0.7.0`; Phase 7 (Polish) at `v0.8.0`.
2. ✅ **Publish scaffolding** — `README.md`, `LICENSE`, `CHANGELOG.md`
   committed at the repo root (PR #46).
3. ⏳ **Working demo path** — either a live [Streamlit
   Cloud](https://streamlit.io/cloud) instance or a recorded walkthrough
   GIF in `docs/`.
4. ✅ **Schema cleanup** — physical drop of legacy `confirmation_email`
   column per DESIGN §6.3 (PR #47, `v0.9.0`) closed the v1.3 split
   migration loop.

### Nice-to-have (not binding)
- ✅ Pre-commit (ruff) + GitHub Actions CI green on main
- ✅ 800+ tests on main; zero deprecation warnings (suite at 879)
- ✅ Cold-clone to running app in ≤ 3 commands (verified by README quick start)
- ⏳ pytest-cov coverage report (number for the README)
- ⏳ CI matrix runs declared floor (3.11) through tested-with (3.14)

---

## Phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Environment & config | ✅ shipped |
| 2 | Data layer (`database.py`, `exports.py` stub, `postdoc.db`) | ✅ shipped |
| 3 | Opportunities page (quick-add, filter, table, edit, delete) | ✅ shipped @ `v0.1.0` |
| 4 | Dashboard (`app.py`) — 5 panels | ✅ shipped @ `v0.5.0` |
| 5 | Applications + Recommenders pages | ✅ shipped @ `v0.6.0` |
| 6 | Full exports + Export page | ✅ shipped @ `v0.7.0` |
| 7 | Polish (urgency colors, search, confirm dialogs, cleanup sub-tier) | ✅ shipped @ `v0.8.0` |
| v1.0-rc | Schema cleanup + publish-readiness scaffolding | ✅ shipped @ `v0.9.0` |
| v1.0 | Demo path (Cloud deploy or walkthrough GIF) + T5 responsive + tag + GitHub release | ⏳ in flight |

Per-tier detail lives in `CHANGELOG.md` version blocks (forensic record from
when each tier shipped) and in `reviews/<phase>-finish-cohesion-smoke.md`
close-out docs.

---

## Post-v1 Backlog

Prioritized. Items land here when deferred from a phase; a P-tier is a rough
ordering, not a commitment.

### P1 — soon after v1

| Item | Source | Notes |
|------|--------|-------|
| Soft-delete with undo toast | UX | Requires `archived_at` column + FK cascade adjustment |
| Interactive funnel (click → filtered Opportunities) | Friend #3 | Plotly click events + `st.session_state` filter handoff |
| Clickable `link` column via `st.column_config.LinkColumn` | UX | 10-line change |
| Pyright `strict` mode (incremental, module-by-module) | Engineering polish | `config.py` first; widens to `database.py`, `exports.py`, then pages |
| Coverage report in README | Engineering polish | `pytest-cov` + badge; surfaces real gaps |

### P2 — medium term

| Item | Source | Notes |
|------|--------|-------|
| AI-populate quick-add from listing URL | Friend #4 | New **Phase 8**; new dep (anthropic / openai SDK); `prefill: dict` hook in quick-add keeps v1 forward-compatible |
| Cloud backup of `postdoc.db` (periodic upload to S3 / iCloud / Dropbox) | Friend #6 | Simplest today: drop the project folder into an iCloud/Dropbox-synced location |
| File attachments on Materials panel (PDF/MD/TeX) | DESIGN §11 | New `attachments` table + FK cascade + `shutil.rmtree` on delete |
| Recommender edit inline within Opportunities edit panel | UX | Rather than only on separate Recommenders page |
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

The tracker is designed so reskinning to a different job context requires
**editing `config.py` only** — no changes to `database.py`, `exports.py`, or
page files.

| Step | What changes |
|------|-------------|
| Add `salary_range`, `equity`, `remote_ok` to the schema via new columns | `REQUIREMENT_DOCS`-style additions or a parallel `JOB_FIELDS` block |
| Add `req_coding_challenge` to `REQUIREMENT_DOCS` | One tuple; `init_db()` migrates |
| Replace pipeline statuses if needed | Edit `STATUS_VALUES` + `STATUS_COLORS` + `TERMINAL_STATUSES` |

A future profile-aware `init_db()` could conditionally include/exclude
columns. v1 leaves postdoc-specific columns in place (NULL for non-postdoc
rows) and hides them from the UI.

**Backward compatibility:** users upgrading from the academic build to the
generalized v2 keep their existing data. Schema is additive.

---

## Explicitly Out of Scope (for v1)

- User authentication (single user, local only)
- Cloud deployment as the primary path (local-only app; Streamlit Cloud is
  an optional demo target, not a deployment target)
- Mobile-first layout
- Email integration (the `mailto:` link covers 90% of the need)
- Calendar sync
- AI-assisted position discovery or matching (P2 backlog handles ingestion,
  not discovery)

---

## Design Reference

Architectural decisions, technical specification, and coding conventions:

- [`DESIGN.md`](DESIGN.md) — master technical specification (architecture,
  schema, UI contracts, extension points)
- [`GUIDELINES.md`](GUIDELINES.md) — coding conventions (read at every
  session start)
- [`docs/adr/`](docs/adr/README.md) — architectural decision records
- [`docs/dev-notes/`](docs/dev-notes/) — Git workflow depth, Streamlit
  state gotchas
- [`CHANGELOG.md`](CHANGELOG.md) — release history
- [`reviews/`](reviews/) — pre-merge review docs, one per tier
- [`docs/internal/TASKS.md`](docs/internal/TASKS.md) — live sprint tracker
