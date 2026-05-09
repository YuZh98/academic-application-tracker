# Roadmap

_Phase tracker, ship criteria, and backlog. Update phase status on completion;
push deep detail to `CHANGELOG.md`._

---

## Vision

A local, single-user academic application tracker that answers one question
clearly: **"What do I do today?"** — built in a way that extends to a general
job tracker without rewriting existing code.

---

## Current Status

**Last shipped tag:** `v0.11.0` (screenshot refresh + README rewrite,
2026-05-06). Updates dashboard screenshots to v0.11.0 across four widths
(1024–1680 px) and rewrites README with a screenshot-first layout,
problem-driven pitch, and engineering notes in a collapsible section.
Suite at 889 collected; pyright fence holds 0/0; coverage 97%.

See [`CHANGELOG.md`](CHANGELOG.md) for full version history.

**Next step:** user-driven repo visibility flip — `gh repo edit
--visibility public` whenever the user is ready. Not part of any tag;
the codebase is stable at `v0.11.0`.

**v1.0.0 explicitly NOT planned.** The pre-1.0 SemVer convention (each
minor = one phase) maps cleanly to the project's release cadence.
Stopping at `v0.10.0` keeps the user free to break things post-public
without committing to a major-version bump promise.

---

## Public-launch Ship Criteria — all met @ `v0.11.0`

1. ✅ **All phases complete** — Phase 4 (Dashboard) at `v0.5.0`; Phase 5
   (Applications + Recommenders) at `v0.6.0`; Phase 6 (Exports) at
   `v0.7.0`; Phase 7 (Polish) at `v0.8.0`.
2. ✅ **Publish scaffolding** — `README.md`, `LICENSE`, `CHANGELOG.md`,
   `SECURITY.md` at repo root.
3. ✅ **Working demo path** — Phase 7 T5 responsive screenshots × 20 PNGs
   in `docs/ui/screenshots/v0.10.0/` + Dashboard hero embedded in README.
4. ✅ **Schema cleanup** — physical drop of legacy `confirmation_email`
   column per DESIGN §6.3 (PR #47, `v0.9.0`).

### Engineering polish — all met @ `v0.11.0`
- ✅ Pre-commit (ruff) + GitHub Actions CI green on main
- ✅ 800+ tests on main; zero deprecation warnings (suite at 883 + 1 xfailed)
- ✅ Cold-clone to running app in ≤ 3 commands (verified by README quick start)
- ✅ pytest-cov coverage report (97% in README badge)
- ✅ CI matrix runs declared floor (3.11) through tested-with (3.14)

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

| Item | Notes |
|------|-------|
| Soft-delete with undo toast | Requires `archived_at` column + FK cascade adjustment |
| Interactive funnel (click → filtered Opportunities) | Plotly click events + `st.session_state` filter handoff |
| Pyright `strict` mode (incremental, module-by-module) | `config.py` first; widens to `database.py`, `exports.py`, then pages |

### P2 — medium term

| Item | Notes |
|------|-------|
| AI-populate quick-add from listing URL | New **Phase 8**; new dep (anthropic / openai SDK); `prefill: dict` hook in quick-add keeps v1 forward-compatible |
| Cloud backup of `postdoc.db` (periodic upload to S3 / iCloud / Dropbox) | Simplest today: drop the project folder into an iCloud/Dropbox-synced location |
| File attachments on Materials panel (PDF/MD/TeX) | New `attachments` table + FK cascade + `shutil.rmtree` on delete |
| Recommender edit inline within Opportunities edit panel | Rather than only on separate Recommenders page |
| Offer details sub-table (start date, salary notes, decision deadline) | New `offers` table linked from `applications` |
| Funding source field | Append to `QUICK_ADD_FIELDS` + schema |
| Interview prep notes (format, interviewer, retrospective) | Extend `applications` table |

### P3 — eventually

| Item | Notes |
|------|-------|
| Application goal setting + progress bar on dashboard | New `settings` table |
| Source effectiveness chart (sources → interviews conversion) | Derived; no new columns |
| Application timeline chart (cluster around deadlines) | Derived from `applied_date` |
| Keyboard shortcuts (N = new, / = search) | Streamlit keyboard support limited |
| Markdown rendering in notes | `st.markdown` alongside `st.text_area` |

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
