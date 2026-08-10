# Changelog

All notable changes to the Academic Application Tracker are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

## [v0.15.0] — 2026-08-10 — Public demo mode

### Added
- Public demo at [`academic-application-tracker.streamlit.app`](https://academic-application-tracker.streamlit.app) — try the full app without installing; each visitor gets an isolated sandbox that resets on tab close (#111)
- Demo banner + sidebar "Reset demo data" button on every page when running in demo mode (#111)
- 19-position seed dataset covering all 7 statuses, every priority value, and all three Upcoming windows so every dashboard panel, filter, and alert fires on first render (#111)
- "Live demo" badge in the README (#111)

### Changed
- Export writers no-op in demo mode — the shared filesystem cannot be safely written from concurrent visitor sessions (#111)
- Settings page disables Save/Append buttons in demo mode; info banner explains why edits do not persist (#112, #115)
- Vermilion accent extracted to `config.ACCENT_VERMILION` — single Python source-of-truth for all accent references (#112)
- `scripts/seed_demo_db.py` refactored: zero import-time side effects; new `seed(conn)` library entry for the demo bootstrap (#111, #114)

### Fixed
- Form-submit and link buttons now render in the editorial theme under both color schemes — previously fell through to Streamlit defaults in dark mode (#116)
- Button text no longer vanishes on hover — inner elements inherit the parent's color transition (#117)

## [v0.14.0] — 2026-05-25 — Editorial-brutalist UI redesign

### Added
- Settings page — tune alert thresholds and manage the status vocabulary without editing config files (#103)
- Bulk-action panel on Opportunities — multi-select rows, flip status or set requirements in one batch (#103)
- Edit-panel coverage for 11 previously-orphan position fields; three also appear in Quick Add (#103)
- Editorial-brutalist visual identity — warm-cream paper, italic-serif headlines, vermilion/cobalt/citron accents, hairline rules
- Print-friendly layout — sidebar and toolbar drop out when printing

### Changed
- Dashboard Upcoming window honors the Settings override (#103)
- Dashboard warning indicator is ▲ (U+25B2) instead of emoji

### Fixed
- Deleting the last interview retracts the position from Interview back to Applied (#103)
- README screenshots refreshed against fabricated demo data (no real PII)

## [v0.13.0] — 2026-05-12 — Self-host setup guide

### Added
- Self-host setup guide — covers install, data persistence, backup/restore, updates, and troubleshooting; linked from README quick start (#97)

### Fixed
- Stale annotations in DESIGN.md file tree corrected (#97)

## [v0.12.0] — 2026-05-09 — LOR integration + public launch

### Added
- Letters of recommendation integrated into the materials/requirements system — LOR status derived from recommender data (#88)
- Coverage gate in CI — 95% minimum line coverage (#93)

### Changed
- Dashboard KPIs use cumulative semantics (e.g., "Applied" counts applied + interview + offer)
- Hide auto-promoted statuses from the manual status picker
- Repo flipped to public visibility

### Fixed
- Quick Add form fields now clear visually after successful save (#89, #90)
- Drop misleading "Active" filter from Applications page

## [v0.11.0] — 2026-05-06 — Pre-launch polish

### Added
- Community scaffolding — CODE_OF_CONDUCT, CONTRIBUTING, PR/issue templates, pre-commit hooks
- Cohesion tests enforcing layer-rule imports in CI
- Link column on Opportunities table; urgency progress bar with color-coded days
- Responsive screenshots (5 pages × 4 widths)

### Changed
- Dashboard visual overhaul — elevated cards, hex palette, segmented window control, consistent Plotly charts
- UX copy pass across all four pages — labels, glyphs, dialog text, date formatting
- README rewrite with screenshot-first layout and engineering notes

### Fixed
- Widget key collisions causing spurious reruns on Opportunities page
- Export page routed through database layer instead of direct filesystem calls
- Material Icons font restored after CSS refactor

## [v0.10.0] — 2026-05-06 — Public launch

### Added
- CI matrix (Python 3.11–3.14) + coverage gate (95%)
- SECURITY.md, README badges (CI / Python / license)
- Responsive screenshots across 5 pages

## [v0.9.0] — 2026-05-05 — Schema cleanup + publish readiness

### Added
- MIT LICENSE + public-facing README

### Changed
- Repo renamed to `academic-application-tracker`
- Brand: "Postdoc Tracker" → "Academic Application Tracker"

### Removed
- Legacy `applications.confirmation_email` column physically dropped (auto-migrated)

## [v0.8.0] — 2026-05-05 — UX polish

### Added
- Urgency glyphs (🔴/🟡/—) on Opportunities deadline column
- Position search bar on Opportunities filter row
- Pyright type-check fence in CI

### Changed
- Config lifts: EM_DASH, urgency_glyph, FILTER_ALL, REMINDER_TONES
- UX copy pass: save-toast wording, mailto subject, empty-state strings

### Fixed
- Confirm-dialog audit + position cascade-copy fix

## [v0.7.0] — 2026-05-04 — Exports

### Added
- Three markdown generators (OPPORTUNITIES.md, PROGRESS.md, RECOMMENDERS.md) — auto-regenerated on every database write
- Export page with manual regenerate + per-file download buttons
- `exports/` gitignored for privacy

## [v0.6.0] — 2026-05-04 — Applications + Recommenders pages

### Added
- Applications page — status filter, detail card with dirty-diff save, cascade-promotion toasts, inline interview list
- Recommenders page — pending-alert cards, full matrix table, add/edit/delete, mailto compose + LLM prompt helpers

## [v0.5.0] — 2026-04-30 — Dashboard complete

### Added
- Upcoming timeline panel with selectable window (30/60/90 days)
- Recommender Alerts panel — surfaces overdue follow-ups grouped by person
- Funnel disclosure toggle (bidirectional, inline in subheader)

### Changed
- v1.3 schema alignment: requirement values normalized, status renames, interviews sub-table, pipeline cascades (R1/R2/R3), confirmation split, recommenders rebuild

## [v0.4.0] — 2026-04-22 — Materials readiness

### Added
- Materials Readiness panel on the dashboard — progress bars for ready vs pending documents

## [v0.3.0] — 2026-04-22 — Application funnel

### Added
- Plotly horizontal-bar application funnel on the dashboard
- Empty-state handling + expand button for hidden pipeline stages

## [v0.2.0] — 2026-04-21 — Dashboard shell + KPIs

### Added
- Dashboard home page with 4-KPI grid (Tracked / Applied / Interview / Next Interview)
- Empty-DB hero CTA

## [v0.1.0] — 2026-04-20 — Opportunities page

### Added
- Opportunities page — Quick-Add, filter bar, positions table, 4-tab edit panel (Overview / Requirements / Materials / Notes)
- Delete position via confirmation dialog
