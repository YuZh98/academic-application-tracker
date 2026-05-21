# v0.15.0 — Editorial-Brutalist Redesign

**Version:** 1.0
**Date:** 2026-05-20
**Status:** approved (proceeding under /goal directive: "amaze three independent agents")

---

## 1. Why

v0.14.0 delivered a competent Apple-tech surface — restrained, polished,
forgettable. The user pushed back: "boring", asked for `高级感` (gravitas)
and `惊艳感` (the gasp). The new brief is to ship a UI that any
sceptical reviewer would call **bold, avant-garde, artistic,
fashionable.**

The aesthetic charter shifts from Apple-tech minimalism to
**editorial brutalism** — the visual language of *Wallpaper\**, *032c*,
the Helvetica-era Vignelli, Massimo Vignelli's MTA poster system, Wim
Crouwel's monumental serifs, *Apartamento* spreads, and Sottsass-era
Memphis without the camp. Magazine confidence applied to a small,
single-user tracking app.

## 2. Aesthetic charter

### Typography — three voices
| Voice | Stack | Use |
|-------|-------|-----|
| **Display** | `'New York', 'Times New Roman', ui-serif, Georgia, serif` italic | Hero greeting, KPI numerals, section eyebrow digits |
| **Mono** | `ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, monospace` | Eyebrows, labels, dates, status codes |
| **Sans** | existing system stack | Body, navigation, dataframe |

Letterspacing: mono `+0.12em` uppercase for eyebrows. Display italic at
`-0.02em` for tightness.

### Palette — Bauhaus-meets-newsroom
| Token | Light | Dark | Use |
|-------|-------|------|-----|
| `--aat-paper` | `#F4EDE0` warm cream | `#0A0A0A` ink black | page bg |
| `--aat-ink` | `#0A0A0A` | `#F4EDE0` | type |
| `--aat-ink-muted` | `#5A5752` | `#A8A599` | secondary type |
| `--aat-rule` | `#1a1a1a` | `#f4ede0` | hairlines |
| `--aat-vermilion` | `#E63946` | same | primary accent |
| `--aat-cobalt` | `#2541B2` | `#7A9BFF` | secondary accent |
| `--aat-citron` | `#F4D35E` | same | signal yellow |
| `--aat-sage` | `#588157` | `#83A87F` | success |
| `--aat-oxblood` | `#7A0E1F` | `#C3504A` | danger |

No drop shadows. Surfaces sit *on the paper*; depth comes from
hairlines, typographic mass, and negative space.

### Geometry — sharp
- Radii: `0px` for sections, `2px` only on inputs (legibility), `999px`
  on status pills only.
- Hairlines: `1px solid var(--aat-rule)` everywhere a card was.
- Generous whitespace: section gaps `2.5rem`; KPI grid breaks 4-up
  symmetry into asymmetric `2fr 1fr 1fr 1fr`.

### Motion — slow + deliberate
- Easing: `cubic-bezier(0.65, 0.05, 0.36, 1)`
- Duration: `260ms` for hover, `1200ms` for hero entrance (numerals
  fade-in via `@keyframes`).
- Background: slowly rotating conic gradient orb behind the hero
  greeting (`120s` per turn — almost imperceptible motion).

### Texture
- SVG-based feTurbulence noise overlay at `opacity: 0.04` on body.
- Hairline grid behind hero (1px ink dots, 16px spacing) for newsprint
  flavour.

### Iconography
- No emoji in chrome. Status pills are tickets: vertical color stripe
  on the left edge + uppercase mono label.
- Urgency rendered as a slim cobalt/vermilion/citron bar, not emoji.

## 3. Concrete moves on each page

### Dashboard (`app.py`)
- **Hero block**: oversized italic serif greeting (`Good morning.` /
  `Good afternoon.` / `Good evening.` by local time) + below it in
  mono uppercase: `YU ZHENG · TUESDAY, MAY 20`.
- Behind the hero: a slow-rotating conic gradient orb (vermilion ↔
  cobalt ↔ citron) at low opacity.
- **KPI grid**: replace the four equal stMetric cards with one
  monumental "tracked" number (display serif, 6rem italic) + three
  smaller secondary numerals stacked on the right. Each accompanied
  by a tiny mono uppercase label.
- **Section eyebrows**: `01 — APPLICATION FUNNEL`, `02 — UPCOMING`,
  `03 — RECOMMENDER ALERTS` rendered in mono uppercase letter-spaced.
- **Accent bar**: replace the indigo→violet→green gradient with two
  hard geometric blocks (vermilion + cobalt) butted edge-to-edge —
  Bauhaus poster mark.

### Opportunities / Applications / Recommenders / Export
- Same shell: paper bg, hero band with serif page name in italic, mono
  subtitle, hairline rule.
- Quick-add becomes a "ledger" panel — no rounded border, just a thick
  ink top rule and a generous cream interior.
- Status badges become ticket-stub pills (color stripe + mono label).

### Sidebar
- Page nav: replace bg-pill hover with a hairline left-rule that grows
  on hover/active (`width 2px → 4px`, vermilion). Editorial table of
  contents look.
- About expander: mono uppercase header `ABOUT · V0.15.0`.

## 4. Architecture

Everything lives in `ui.py` and the page entrypoints. No new modules,
no new packages. Layer rules unchanged.

### New / changed `ui.py` API
| Symbol | Status | Purpose |
|--------|--------|---------|
| `inject_global_styles()` | restyled | Editorial token set + dark mode |
| `accent_bar()` | restyled | Vermilion + cobalt geometric blocks |
| `section_header(text, eyebrow=None)` | unchanged | Numbered eyebrow + serif title |
| `status_pill(raw)` | restyled | Ticket-stub shape (left stripe + mono label) |
| `urgency_pill(days)` | restyled | Slim bar pill, mono digits |
| `hero_greeting()` | **NEW** | Renders the dashboard hero (time-of-day + mono date stamp). Takes no args; reads `datetime.now()` at call time. |
| `numbered_section(n, title)` | **NEW** | Convenience wrapper around `section_header` for the `01 — TITLE` pattern. |
| `sidebar_about_block()` / `sidebar_shortcuts_block()` | restyled | Mono uppercase headers |

### Tests touched
| File | Change |
|------|--------|
| `tests/test_ui.py` | New tests: hero greeting bands by hour, numbered section format, ticket-pill shape, conic-gradient block present. |
| `tests/test_config.py` | Bump `APP_VERSION` test to accept `0.15.0-dev`. |

## 5. Non-goals (still)

- No new database columns.
- No new pages / no removal of features.
- No JS, no new Python packages.
- No replacement of Streamlit's native widgets with custom HTML beyond
  the existing pill helpers + the new `hero_greeting`.
- Mobile-first layout remains a non-goal per DESIGN §1.

## 6. Acceptance — "amaze three independent agents"

The /goal directive is to ship a UI that three independent fresh-context
reviewers describe with at least three of: *bold, avant-garde, artistic,
fashionable, editorial, monumental, gasp-inducing.* A neutral or
"competent" verdict is a fail.

Three reviewers will be spawned in parallel after the redesign lands,
each with the same self-contained brief + a screenshot of the dashboard.
Each must return a one-sentence aesthetic verdict; an "amaze" verdict
needs at least three of the adjectives above (or synonyms thereof).

If any reviewer returns "competent / safe / restrained / fine" the
redesign is iterated.
