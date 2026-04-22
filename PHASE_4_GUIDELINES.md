# Phase 4 — Dashboard (`app.py`) Guidelines
_Load at the start of every Phase 4 session. Supplements GUIDELINES.md — does not replace it. Specific to the dashboard build._

---

## Scope of Phase 4
**Goal:** Transform `app.py` from a 13-line stub into the project's home page — the one screen that answers *"what do I do today?"*

**In scope:**
1. **T1** — App shell + 4 KPI cards (Tracked / Applied / Interview / Next Interview)
   - **Tracked-bucket semantics (locked 2026-04-21):** Tracked = `count_by_status()["[OPEN]"] + count_by_status()["[APPLIED]"]`. Rationale: "opportunities that might get moved forward." `[INTERVIEW]` / `[OFFER]` have their own KPIs downstream; terminal statuses are excluded.
2. **T2** — Application funnel (Plotly horizontal bar, color-coded by status)
3. **T3** — Materials Readiness panel (ready vs. pending counts, grid-aligned with T2)
4. **T4** — Upcoming timeline (next 30 days: deadlines merged with interviews)
5. **T5** — Recommender alerts (grouped by recommender, with `mailto:` link)
6. **T6** — Pre-merge review + PR (mirrors Tier 5-F pattern)

**Out of scope (deliberately):**
- Any change to `database.py`, `config.py`, `exports.py`, `pages/1_Opportunities.py`
  - **Narrow carve-out (approved by user 2026-04-21, T1-C):** three additive named aliases in `config.py` — `STATUS_OPEN`, `STATUS_APPLIED`, `STATUS_INTERVIEW` (defined over existing `STATUS_VALUES` entries). Needed so `app.py`'s per-bucket KPI counts can name specific statuses without hardcoding literals (the anti-typo guardrail + Phase 4 pre-merge grep rule). Pure additive; no schema drift, no behavior change. **No other `config.py` edits are permitted without an equivalently explicit user decision.**
- Recommender alerts row-by-row (we group by person; row-wise is Phase 5)
- Edit affordances on the dashboard (dashboard is read-only — click-through lands on Opportunities)
- `@st.cache_data` wrapping (C4: skip caching in Phase 4; revisit post-merge if actual slowness measured)
- New DB columns, schema migration, or new dashboard query helpers — all 5 queries already exist in `database.py` and were 100%-tested in Phase 2

---

## Standing instructions block — pinned for Phase 4

Paste this verbatim at the top of each Phase 4 implementation prompt:

> Standing instructions & rules:
> - announce the plan + files touched before writing code
> - follow DESIGN.md + GUIDELINES.md + PHASE_4_GUIDELINES.md exactly
> - verify any Streamlit / Plotly API you use (no guessing signatures)
> - form id ≠ any widget key inside the form
> - `st.toast` for confirmations; `st.error` for failures (friendly, no traceback, no re-raise)
> - no hardcoded vocab — everything through `config.py`
> - ask before uncertain modifications
> - work on branch `feature/phase-4-tierN`
> - commit once per logical change with Conventional Commit prefix (test → feat → chore)

---

## Key user-approved design decisions (locked — do not re-litigate)

| Key | Decision | Source |
|----|----------|--------|
| **C3** | **Keep** the `[🔄 Refresh]` button in the top bar; don't rely solely on Streamlit's auto-rerun | user answer |
| **C4** | **Skip** all `@st.cache_data` work in Phase 4 | user answer |
| **C5** | Sync GUIDELINES.md §7 (`st.success` → `st.toast`) and §8 (drop the `raise`) during Phase 4 opening | user answer |
| **C6** | Fix DESIGN.md line 431: readiness scope is `[OPEN]` + `[APPLIED]` + `[INTERVIEW]` (not `[OPEN]` only) to match implementation | user answer |
| **C8** | **One** test file for the whole dashboard: `tests/test_app_page.py` (not per-tier) | user answer |
| **U2** | Funnel + Readiness side-by-side via `st.columns(2)` (stacking on narrow windows is acceptable) | user answer |
| **U3** | When no upcoming interview exists, Next-Interview KPI shows `"—"` for grid consistency | user answer |
| **U5** | Implement a fully-empty-DB hero callout at the top of `app.py` with a clear CTA into Opportunities | user answer |

These decisions are **closed**. If new evidence emerges mid-phase, raise it as a question *before* deviating.

---

## Tier list — difficulty, workload, session pairing

| Tier | Title | Est. workload | Difficulty | Sessions | Branch |
|------|-------|--------------|------------|----------|--------|
| T1 | App shell + 4 KPI cards (+ refresh button + empty-DB hero) | ~1.5 hr | 🟢 easy (🟡 on T1-E empty-DB hero) | 3 | `feature/phase-4-tier1` |
| T2 | Application funnel (Plotly) | ~2.0 hr | 🟡 medium (first Plotly integration) | 2 | `feature/phase-4-tier2` |
| T3 | Materials Readiness panel | ~1.0 hr | 🟢 easy | 1 | `feature/phase-4-tier3` |
| T4 | Upcoming timeline (deadlines + interviews merged) | ~2.5 hr | 🟠 medium-hard (2-source merge + urgency logic) | 2 | `feature/phase-4-tier4` |
| T5 | Recommender alerts panel (grouped by person) | ~1.5 hr | 🟡 medium (grouping logic + `mailto:`) | 1 | `feature/phase-4-tier5` |
| T6 | Pre-merge review + PR | ~1.0 hr | 🟢–🟡 easy-medium | 2 | same branch(es) |
| **Total** | | **~9.5 hr** | | **~9 sessions** | |

**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 (linear; each depends only on T1's shell).

**Parallelisable:** T2 / T3 / T4 / T5 are mutually independent once T1 ships — but prefer sequential to keep git log linear.

---

## Sub-task breakdown & session pairing

### T1 — App shell + KPI cards  (~1.5 hr, 3 sessions)
- **T1-A** `test:` — `tests/test_app_page.py` scaffold (per C8) with empty-DB smoke test and 4-KPI-column shape test ✅ done 2026-04-20
- **T1-B** `test:` + `feat:` — `app.py` shell: title "Postdoc Tracker" + `database.init_db()` + `st.columns(4)` with four `st.metric` cards (labels "Tracked" / "Applied" / "Interview" / "Next Interview"; values `"—"` placeholders until C/D wire the real queries) ✅ done 2026-04-20
- **T1-C** `test:` + `feat:` — top bar 🔄 refresh button (calls `st.rerun()`) + wire `count_by_status()` into Tracked / Applied / Interview KPI values ✅ done 2026-04-21 (see Deferred-Decision Log entry 2026-04-21 for the narrow `config.py` carve-out and Tracked-bucket semantics)
- **T1-D** `test:` + `feat:` — wire `get_upcoming_interviews()` → Next Interview date (empty → `"—"` per U3) ✅ done 2026-04-21 (format + selection rule locked in Deferred-Decision Log)
- **T1-E** `test:` + `feat:` — fully-empty-DB hero callout (per U5): when all three counts = 0, render a hero panel above the KPI grid with a CTA button that `st.switch_page()`s to Opportunities ✅ done 2026-04-21 (trigger = `tracked + applied + interview == 0`; terminal-only DB edge case pinned by `test_terminal_only_db_still_shows_hero`; source-level assertion on `st.switch_page("pages/1_Opportunities.py")` target since AppTest single-file mode can't navigate)
- `chore:` — one commit per sub-task, rolling up tracker updates

**Session pairing:** one session covers T1-A+B (test scaffold + shell); one session T1-C+D (refresh button + KPI wiring); one session T1-E (empty-DB hero). Each session = 1 branch push; all stay on `feature/phase-4-tier1` until T1 reviewed.

### T2 — Application funnel  (~2.0 hr, 2 sessions)
- **T2-A** `test:` + `feat:` — Plotly horizontal bar built from `count_by_status()`, one bar per STATUS_VALUE, colors from `config.STATUS_COLORS`
- **T2-B** `test:` + `feat:` — empty-state render (no positions → descriptive text, no broken figure)
- **T2-C** `test:` + `feat:` — place figure inside left half of an `st.columns(2)` (per U2)

### T3 — Materials Readiness  (~1.0 hr, 1 session)
- **T3-A** `test:` + `feat:` — render `compute_materials_readiness()` → `"N ready / M pending"` plus a mini bar
- **T3-B** `test:` + `feat:` — place in right half of T2's `st.columns(2)`

**Deviation log (T3, D4 = κ, 2026-04-22):** PHASE_4_GUIDELINES originally split T3 into T3-A (render the counts + mini bar) and T3-B (place in the right half of `st.columns(2)`), each as its own `test:` + `feat:` pair. Conductor brief collapsed them into a **single commit-triple** (`test:` → `feat:` → `chore:`) on `feature/phase-4-tier3-MaterialReadiness` — T3 is small (~1 session), both pieces touch the same `with _right_col:` block in `app.py`, and the right-half column already exists from T2-C so there is no "new layout" to land separately. Mirrors the T1-B metric-key deviation entry in style: documented inline, no plan rewrite. Visual swapped from "N ready / M pending + mini bar" to **two stacked `st.progress` bars** (Ready / Missing) with a `"→ Opportunities page"` CTA — locked design decisions D1–D5 from the conductor brief (2026-04-22). `st.progress` signature on Streamlit 1.56 verified as `progress(value, text=None, width="stretch")`; AppTest exposes each bar via `at.get("progress")` as an `UnknownElement` with `proto.value` (0-100 int) and `proto.text` (label). Denominator is `max(ready + pending, 1)` per D5; strictly unnecessary inside the else-branch, but kept explicit so a future reader sees the contract next to the math.

### T4 — Upcoming timeline  (~2.5 hr, 2 sessions)
- **T4-A** `test:` + `feat:` — fetch deadlines via `get_upcoming_deadlines(30)` and interviews via `get_upcoming_interviews()`, merge into a single DataFrame keyed by date
- **T4-B** `test:` + `feat:` — urgency column using `DEADLINE_URGENT_DAYS` / `DEADLINE_ALERT_DAYS` from config (no hardcoded thresholds)
- **T4-C** `test:` + `feat:` — display via `st.dataframe(width="stretch")` with `(date, label, kind, urgency)` columns; `kind ∈ {"deadline", "interview"}` — label comes from positions/applications joins
- **T4-D** `test:` + `feat:` — empty state ("No deadlines or interviews in the next 30 days")

### T5 — Recommender alerts  (~1.5 hr, 1 session)
- **T5-A** `test:` + `feat:` — fetch via `get_pending_recommenders(RECOMMENDER_ALERT_DAYS)`, group by `recommender_name`, count affected positions per person
- **T5-B** `test:` + `feat:` — per-person card: name + "N overdue" + `mailto:` link prefilled with subject + position names
- **T5-C** `test:` + `feat:` — empty state ("No pending recommender follow-ups")

### T6 — Pre-merge review + PR  (~1.0 hr, 2 sessions)
- **T6-A** `review(phase-4):` — `reviews/phase-4-premerge.md` covering commit roster, acceptance criteria (pytest green, 0 deprecation warnings, no source-file scope creep outside `app.py` + `tests/test_app_page.py`, every threshold driven by config)
- **T6-B** — open PR, await merge; mirror Tier 5-F hand-off pattern

---

## Dependency map (verified)

```
           ┌──────────────┐
           │   T1 shell   │  (columns grid + refresh button + empty-DB hero)
           └──────┬───────┘
                  │  everything below needs the shell
    ┌─────┬───────┼───────┬─────┐
    ▼     ▼       ▼       ▼     ▼
   T2    T3      T4      T5    (T6 reviews all of them together)
  funnel readiness timeline alerts
```

- **T1-E is independent of T1-C+D** — all three depend only on the `st.columns(4)` from T1-B.
- **T2 / T3 / T4 / T5 are mutually independent** after T1 merges; can run in any order (recommended: T2 before T3 because T3 sits in T2's right column via `st.columns(2)`, but code-wise either can land first since `st.columns` is created once in a T2/T3 combined session).
- **T5 alerts share NO helpers with T4 timeline** — by design. `get_pending_recommenders(days)` is already separate from `get_upcoming_deadlines(days)` / `get_upcoming_interviews()`; no grouping helper is reused.

---

## Test conventions — Phase 4 specifics

**Per C8: one test file, `tests/test_app_page.py`.**

- Test classes named `Test<Tier>` (`TestT1KpiCards`, `TestT2Funnel`, `TestT3Readiness`, `TestT4Upcoming`, `TestT5Alerts`)
- `AppTest.from_file("app.py", default_timeout=10)` at the top of each test
- **Seed data via `database.add_position()` + `database.upsert_application()`** — never raw SQL in tests
- Reset DB between tests via a `conftest.py`-style fixture if needed (or wipe rows in setUp); do NOT replace `database.DB_PATH` at runtime (Phase 3 pattern remains valid)
- Plotly assertions: retrieve the figure via `at.get("plotly_chart")` (verify the Streamlit API before using — Plotly element selector may differ); compare data arrays to expected, not pixel output
- KPI card value assertions: walk `at.metric` elements and identify them by **label** (the spec'd strings in DESIGN.md §app.py: "Tracked", "Applied", "Interview", "Next Interview") or by positional order within the fixed `st.columns(4)` render. **`st.metric` in Streamlit 1.56 has no `key=` parameter** (verified against the installed API); display-only primitives don't expose one. Label-based lookup is the idiomatic AppTest path and doubles as a regression check against the DESIGN contract.

**Minimum coverage bar:** every KPI card, every chart, every empty-state branch pinned by at least one test.

---

## Cross-session continuity checklist

Before starting any Phase 4 session, re-read:
1. **PHASE_4_GUIDELINES.md** (this file) — locked decisions + sub-task list
2. **CLAUDE.md Project State** — current tier & next sub-task
3. **TASKS.md Phase 4 section** — what's checked off, what's next
4. **roadmap.md Phase 4 row** — global state

At session end, update all four + `memory/project_state.md` in the `chore:` commit.

If a new design question emerges that needs a user decision:
- Log it in the **Deferred-Decision Log** below
- Do not guess; ask before acting

---

## Pre-merge review checklist (T6-A)

Mirror `reviews/phase-3-tier5-premerge.md`. For each assertion, include the verifying command:

- [ ] `pytest tests/ -q` — all tests green (include count)
- [ ] `pytest -W error::DeprecationWarning tests/ -q` — zero deprecation warnings
- [ ] `git diff main..HEAD -- database.py config.py exports.py pages/1_Opportunities.py` — empty (no scope creep into Phase 3 code)
- [ ] `grep -nE "\\[OPEN\\]|\\[APPLIED\\]|\\[INTERVIEW\\]" app.py` — zero hits (all via `config.STATUS_VALUES`)
- [ ] `grep -nE "^\\s*[0-9]+\\s*#\\s*(days|urgent|alert)" app.py` — zero hits (all thresholds via `config`)
- [ ] Every `st.form` id ≠ any widget key inside
- [ ] Every save path uses `st.toast` on success + `st.error` on failure (no re-raise)
- [ ] Empty-DB hero renders when `count_by_status()` returns all zeros (verified by smoke test)
- [ ] PR body lists commit roster + acceptance criteria + delta vs. DESIGN §6

---

## Deferred-Decision Log

Any ambiguity encountered mid-phase that needs a user call, logged here with proposed option A/B.

| Date | Question | Option A | Option B | Recommendation | Status |
|------|----------|----------|----------|----------------|--------|
| 2026-04-21 | T1-C: what does "Tracked" KPI count? | Sum of all positions (incl. terminal) | Non-terminal only | User chose: **OPEN + APPLIED** ("opportunities that might get moved forward"); INTERVIEW/OFFER are excluded because they have their own KPIs. | ✅ Closed (locked in §Scope) |
| 2026-04-21 | T1-C: how to name specific statuses in `app.py` without hardcoding literals, given `config.py` is out-of-scope? | Edit `config.py` to add three named aliases | Positional-index access into `STATUS_VALUES` | User chose A; narrow carve-out — three additive aliases only, no other `config.py` edits permitted in Phase 4. | ✅ Closed (logged in §Out of scope) |
| 2026-04-21 | T1-D: what should the Next Interview KPI value show? | Exactly as wireframe: `'{Mon D} · {institute}'` (no year) | With year, or date only, or with `position_name` instead | User chose A; matches DESIGN.md §app.py wireframe verbatim. Renders e.g. `"May 3 · MIT"`. | ✅ Closed |
| 2026-04-21 | T1-D: which row/column becomes "next"? | Earliest future date across BOTH `interview1_date` AND `interview2_date` across all rows; paired institute belongs to whichever position owns that date | First row's `interview1_date` only | User chose A. Columns are symmetric; past dates on the same row as a future-far date are ignored (row-level filter is not enough — `get_upcoming_interviews()` includes a row when *either* date is future). | ✅ Closed |

---

## Known deferred DX items (carry-over from Phase 3)

- **`pytest.ini` fix**: add `pythonpath = .` so `pytest` alone (without `PYTHONPATH=.`) works. User deferred the one-line edit at Phase 3 close; revisit when user green-lights.

---

_Initial draft: 2026-04-20, immediately before Phase 4 T1 kickoff._
