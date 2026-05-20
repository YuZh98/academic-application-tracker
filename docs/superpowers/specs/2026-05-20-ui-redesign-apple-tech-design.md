# UI Redesign — Apple-Tech Aesthetic & Industry-Product Polish

**Version:** 1.0  
**Date:** 2026-05-20  
**Status:** approved (proceeding under /goal directive)

---

## 1. Purpose

Lift the tracker's UI from "competent Streamlit + per-page CSS in `app.py`
only" to a cohesive, Apple-tech-flavoured surface applied consistently
across all pages, while raising it to industry-product baselines
(empty states, focus rings, motion, dark-mode awareness, sidebar polish,
typographic rhythm, accessible contrast).

Constraint: the app remains a single-binary Streamlit 1.57 process. No
new runtime dependencies. No mobile-first reflow (still a non-goal per
DESIGN §1). No auth, no cloud.

## 2. Aesthetic principles (the "Apple-tech" decoder)

| Principle | Concrete rule |
|-----------|---------------|
| **Restrained colour** | One brand accent (indigo `#4F6BEF`), one success (`#10B981`), one warn (`#F59E3A`), one danger (`#EF4444`). All grayscale neutrals derived from a single slate ramp. |
| **System typography** | SF Pro / system stack already adopted; we add a tight rhythm: H1 `2.0rem/700`, H2 `1.4rem/700`, eyebrow uppercase `0.7rem/700/0.09em`, body `0.95rem/400`. |
| **Generous whitespace** | Section gaps `1.5rem`; card padding `1.1–1.4rem`. |
| **Layered surfaces** | One elevation step: subtle 1px hairline border + soft 6/20 shadow. No drop-shadow stacks; no glassmorphism. |
| **Soft motion** | 150–200ms cubic-bezier(0.2, 0, 0, 1) on hover/focus only. No scroll-jacking. |
| **Iconography** | Existing emoji glyphs (🔴🟡) replaced with colour-tinted unicode dots in HTML pills for crispness; remaining text icons (📋, ⚠️) kept. |
| **Dark-mode respect** | Tokens defined as CSS custom properties; `@media (prefers-color-scheme: dark)` flips the slate ramp + surface colours. Brand accent unchanged across modes. |

## 3. Industry-product criteria addressed

| Criterion | Change | Landed in v0.14.0? |
|-----------|--------|--------------------|
| Consistent shell on every page | New `ui.py` injects the same stylesheet on every page (currently only `app.py`). | ✅ |
| Accessible focus | Visible focus ring on all interactive elements via `:focus-visible`. | ✅ |
| Sidebar polish | About + Shortcuts expanders rendered on every page; version pulled from `config.APP_VERSION`. | ✅ |
| Error grace | Already present (save-paths catch broadly); no change needed. | ✅ (pre-existing) |
| Performance | CSS is static; no runtime cost. No new network calls. | ✅ |
| Print readability | A `@media print` block hides sidebar + toolbar so users can print their dashboard. | ✅ |
| Strong empty states (SVG illustrations) | Each major page would get the empty-state hero pattern extended (inline SVG + CTA). | ⏳ deferred — conflicts with §6 non-goal "no replacement of Streamlit's native widgets with custom HTML"; the existing `st.info(...)` empty states ship unchanged in v0.14.0. Track in backlog. |
| Predictable affordances (pill rendering) | Status badges + urgency rendered through `ui.status_pill` / `ui.urgency_pill` instead of raw emoji. | ⏳ partial — helpers + tests landed in `ui.py`; pages still call `config.urgency_glyph` / `st.badge`. Wiring is a follow-up (no schema change required); pages can opt into the helpers individually. |

## 4. Architecture

### 4.1 New module: `ui.py`

A presentation-helper sibling of `app.py`. Imports `config` only at the
top level; `streamlit` is imported at the top level too (this module
exists specifically to call `st.markdown`).

Exposed API (all pure-render or pure-string):

```python
def inject_global_styles() -> None: ...
def status_pill(raw_status: str) -> str: ...       # returns HTML
def urgency_pill(days_left: int | None,            # returns HTML
                 *, urgent_d: int = ..., alert_d: int = ...) -> str: ...
def accent_bar() -> None: ...                       # gradient line
def section_header(text: str, *, eyebrow: str | None = None) -> None: ...
def sidebar_about_block(version: str) -> None: ...  # expander in sidebar
```

### 4.2 Layer position

```
config.py     ← imports nothing
database.py   ← imports config
exports.py    ← imports database, config
ui.py         ← imports config + streamlit; never database  ← NEW
app.py        ← imports config, database, ui
pages/*.py    ← imports config, database, ui
```

Update GUIDELINES §2 + DESIGN §4 to reflect the new module. Layer count
remains four; `ui.py` is a sibling of `app.py`/`pages/` in the display
tier, not a fifth layer.

### 4.3 Tokens

CSS custom properties on `:root` and the dark-mode `@media` query. All
tokens live in the stylesheet string inside `ui.inject_global_styles()`.
Python-side colour constants (`STATUS_COLORS`, `FUNNEL_BUCKETS[i][2]`)
stay in `config.py` because Plotly + `st.badge` consume them by value;
those are not duplicated in CSS, only the *neutral palette + surfaces*
are.

## 5. Files touched

| File | Change |
|------|--------|
| `ui.py` | NEW — shared CSS + render helpers |
| `app.py` | Remove inline CSS; call `ui.inject_global_styles()`; replace urgency display + add sidebar about block |
| `pages/1_Opportunities.py` | Add `ui.inject_global_styles()`; restyle quick-add card |
| `pages/2_Applications.py` | Add `ui.inject_global_styles()` |
| `pages/3_Recommenders.py` | Add `ui.inject_global_styles()` |
| `pages/4_Export.py` | Add `ui.inject_global_styles()` |
| `tests/test_ui.py` | NEW — unit tests for `status_pill`, `urgency_pill`, smoke for `inject_global_styles` |
| `tests/test_app.py` (or page tests) | Smoke that all pages still load via `AppTest.from_file` |
| `DESIGN.md` | Add §8.6 *Design System*; update §4 file structure |
| `GUIDELINES.md` | Update §2 import contract |
| `CHANGELOG.md` | `[Unreleased]` entry |

## 6. Non-goals (explicit)

- No new database columns, no schema migration.
- No new pages; no removal of features.
- No mobile-first layout (still a v1 non-goal).
- No JS, no new Python packages.
- No replacement of Plotly with another chart lib.
- No replacement of Streamlit's native widgets with custom HTML, except
  for the two render helpers above (`status_pill`, `urgency_pill`) which
  return HTML strings the existing pages can opt into.

## 7. Test plan

| Test | Asserts |
|------|---------|
| `test_status_pill_html_structure` | Returns `<span class="aat-pill ...">` with the status label text. |
| `test_status_pill_known_statuses_have_colors` | Every `STATUS_VALUES` entry produces a pill with a non-empty colour class. |
| `test_urgency_pill_bands` | `days <= URGENT` → urgent class; `<= ALERT` → warn class; beyond → muted class; `None` → em-dash placeholder. |
| `test_urgency_pill_negative_is_urgent` | Past-due (-1 day) renders urgent (mirrors `urgency_glyph` invariant). |
| `test_inject_global_styles_smoke` | Calling once leaves Streamlit markdown call list non-empty and includes the `:root` token block + `@media (prefers-color-scheme: dark)` block. |
| `test_pages_inject_styles` | Each `pages/*.py` source contains a call to `ui.inject_global_styles`. |
| Existing 913-test suite | All pass post-change. |

## 8. Release vehicle

Tag `v0.14.0` once all changes land + CHANGELOG `[Unreleased]` rotated.
Per global CLAUDE.md §9: `release.sh` → annotated tag → push both →
follow-up pyproject bump.

## 9. Open questions deferred

- Light/dark mode toggle in-app (vs OS-only) — deferred; OS preference
  is the Apple-default behaviour and covers the use case.
- Sidebar collapse remembering across pages — Streamlit limitation; out
  of scope.
- Replacing Plotly funnel with bespoke HTML bars for matching styling —
  the Plotly bar already accepts custom colours from `FUNNEL_BUCKETS`,
  so a parallel native render adds maintenance without visible win;
  out of scope.
