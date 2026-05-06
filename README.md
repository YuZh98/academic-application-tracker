# Academic Application Tracker

[![CI](https://github.com/YuZh98/academic-application-tracker/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/YuZh98/academic-application-tracker/actions/workflows/ci.yml) [![Python](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue)](pyproject.toml) [![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen)](pyproject.toml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

![Dashboard — empty state on first run](docs/ui/screenshots/v0.11.0/dashboard-1280.png)

A local Streamlit dashboard that answers one question every morning: **"What do I do today?"**

---

## What a spreadsheet can't do

**Surface urgency automatically.** The dashboard computes what's due, flags it red or yellow by proximity, and surfaces it every session — no manual sorting, no missed deadlines.

**Track recommenders across positions.** One recommender writing letters for seven positions means seven independent asked / confirmed / submitted states. The Recommenders page flags everyone asked more than 7 days ago who hasn't submitted, groups alerts by recommender, and offers a one-click mailto to draft a follow-up.

**Keep materials readiness co-located with status.** Each position carries its own checklist (CV, cover letter, research statement, teaching portfolio, …). The Materials Readiness panel shows how many active applications are ready to submit and how many are still missing something — without opening each position manually.

---

## Pages

**Dashboard** — KPI grid (Tracked / Applied / Interview / Next Interview), application funnel, materials readiness panel, upcoming deadlines, recommender alerts. One screen; one daily answer.

**Opportunities** — Quick-add a position in under 30 seconds. Full edit panel with four tabs (Overview / Requirements / Materials / Notes). Filter bar: status, priority, field, full-text search. Urgency-banded deadline column.

**Applications** — Per-position card: applied date, confirmation, response, result, outcome. Inline multi-round interview log. Pipeline cascades automatically: save → applied → interview → offer.

**Recommenders** — Pending-alert cards with mailto and LLM-prompt helpers to draft a follow-up. Full (position × recommender) table with inline edit and delete.

**Export** — Manual regenerate + per-file download for `OPPORTUNITIES.md`, `PROGRESS.md`, `RECOMMENDERS.md`. Every database write also auto-regenerates these — the `exports/` folder is always a fresh plaintext backup of your entire job-search state.

---

## Quick start

```bash
git clone https://github.com/YuZh98/academic-application-tracker.git
cd academic-application-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Python ≥ 3.11. Open the URL Streamlit prints (default `http://localhost:8501`). The SQLite database is created on first run; the empty-state hero walks you through adding your first position.

**Stack:** Python · Streamlit 1.57 · SQLite · pandas · Plotly  
**Dev tooling:** pytest · ruff · pyright

---

<details>
<summary>Engineering notes</summary>

Built like a small production system, not a personal script.

**Architecture — four strict layers:**
```
config.py     constants, vocabularies, import-time invariants
database.py   SQL only — never imports streamlit
exports.py    markdown writers — called by database, never by pages
pages/*.py    display only — no raw SQL, no direct exports import
```
Layer contracts are enforced by cohesion tests that fail CI if any rule drifts.

**889 tests, 97% coverage.** Integration tests use the official `streamlit.testing.v1.AppTest` harness against real page files; unit tests run against per-test temp SQLite files via a `db` fixture. A second test pass with `-W error::DeprecationWarning` catches Streamlit-API drift before it surfaces on upgrades.

**CI on every PR:** ruff lint · pyright strict-basic (zero errors required) · pytest (two passes) · status-literal grep (no hardcoded `[SAVED]` / `[APPLIED]` / `[INTERVIEW]` strings in page code — all vocabulary routed through `config.py`).

**Config-driven schema.** Adding a new required document type (e.g. "Portfolio") = one tuple appended to `config.REQUIREMENT_DOCS`. `init_db()` adds the `req_*` / `done_*` columns automatically on next start. No other file changes needed.

**Import-time invariants.** `config.py` asserts structural integrity at module load — every status has a color and a label, urgency thresholds are ordered, funnel buckets cover all statuses exactly once. Misconfiguration aborts startup with a clear traceback before any page renders.

**Spec-first.** [`DESIGN.md`](DESIGN.md) is the authoritative spec for the schema, page contracts, cascade rules, and export format. Implementation tracks the spec; deviations land as spec amendments with commit references.

</details>

---

## Project structure

```
app.py                 Dashboard home page
config.py              Constants — statuses, thresholds, vocabularies
database.py            SQL reads/writes; calls exports.write_all() on every write
exports.py             Markdown generators (OPPORTUNITIES / PROGRESS / RECOMMENDERS)
pages/
  1_Opportunities.py   Position CRUD
  2_Applications.py    Application + interview tracking
  3_Recommenders.py    Recommender tracker + reminder helpers
  4_Export.py          Manual export trigger + per-file download buttons
tests/                 879-test suite (AppTest + unit + cohesion)
docs/
  adr/                 Architecture decision records
  dev-notes/           Streamlit gotchas, dev setup, git workflow notes
  ui/                  Wireframes + screenshots
DESIGN.md              Authoritative spec
GUIDELINES.md          Coding conventions
CHANGELOG.md           Per-release narrative log
```

---

## Documentation

- [`DESIGN.md`](DESIGN.md) — schema, page contracts, cascade rules, export format. Start here for "how does this work?"
- [`GUIDELINES.md`](GUIDELINES.md) — coding conventions, TDD cadence, doc tiering. Start here for "how is this codebase organized?"
- [`CHANGELOG.md`](CHANGELOG.md) — per-release development log
- [`docs/dev-notes/`](docs/dev-notes/) — Streamlit-specific gotchas, dev setup, git workflow depth

---

## Status

`v0.11.0`. Daily-usage flows stable. Schema may evolve before `v1.0`.

## License

[MIT](LICENSE)

## Acknowledgments

Built with [Claude Code](https://claude.com/claude-code) using an orchestrator + implementer agent pipeline. Architectural decisions, review judgment, and merge calls remain the author's; the agent pipeline ships the code.
