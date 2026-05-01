# Phase 4 — Tier 1 Code Review

**Branch:** `feature/phase-4-tier1` (12 commits ahead of `main`)
**Scope:** T1-A (test scaffold) + T1-B (app shell + KPI grid skeleton) + T1-C (refresh button + KPI count wiring) + T1-D (Next-Interview KPI wiring) + T1-E (empty-DB hero + CTA)
**Stats:** `app.py` 13 → 124 lines; `tests/test_app_page.py` new file, +407 lines, 23 tests across 4 classes; **246 total tests passing, 0 deprecation warnings**.
**Verdict:** T1 mergeable in isolation; locked plan packages T1–T5 into one PR at T6.
**Reviewer attitude:** Skeptical. Trust nothing. Question every implicit assumption. Verify every Streamlit / pandas API claim.

---

## Executive summary

Tier 1 stands up the dashboard's read-only top of page: title bar, manual refresh, four KPI cards (three count-driven, one date-driven) and a fully-empty-DB hero with a CTA into Opportunities. The work is well-tested (every code path has a pin, including the awkward symmetric two-column interview-date selection), the comments explain *why* rather than *what*, and the sub-tasks land cleanly through the locked TDD cadence (test → feat → chore × 5 sub-tasks).

The review surfaces **no bugs**, **two test-coverage hardening fixes** worth landing pre-merge, and **a handful of intentional-but-worth-naming design choices** that will need to be reconsidered (or pinned more tightly) once T2 / T3 land. The review also closes out two minor housekeeping items (a stale "in progress" comment block) that have aged into the file since the kickoff.

---

## Findings

| # | File · Line | Issue | Severity | Status |
|---|-------------|-------|----------|--------|
| 1 | `tests/test_app_page.py` : `_hero_heading_rendered` (~334) | Hero-presence heuristic is `len(at.subheader) >= 1`. Once T2/T3/T4/T5 lands a panel subheader, this becomes a permanent false positive — the hero could vanish and the test would still pass. | 🟡 Moderate | **Fix applied** (assert on the actual hero copy substring) |
| 2 | `app.py` : 4–11 | Top-of-file comment block still says "T1 — app shell + 4 KPI cards (in progress)". T1-A through T1-E have all shipped; the file's own header is the most-read piece of documentation in the project and should reflect reality. | 🟢 Minor | **Fix applied** (mark T1 done; tighten the tier roadmap to match `PHASE_4_GUIDELINES.md`) |
| 3 | `app.py` : 101 | Hero trigger condition `tracked == 0 and applied == 0 and interview == 0` is mathematically redundant — `tracked == 0` already implies `applied == 0` (since `tracked = open + applied`). | ℹ️ Observation | Kept by design (see Q3 below) |
| 4 | `app.py` : 74–75 | Refresh button calls `st.rerun()` inside `if st.button(...):`. A button click already triggers a Streamlit rerun on its own; the explicit call causes a second rerun (one wasted script execution per click). Behaviour is correct. | 🟢 Minor | Kept (see Q5 below) |
| 5 | `app.py` : 91 | `database.get_upcoming_interviews()` is invoked unconditionally — even on an empty DB where the SQL returns zero rows. Cheap, but technically wasteful and conceptually inconsistent with the empty-DB hero short-circuit. | ℹ️ Observation | Accepted (see Q6 below) |
| 6 | `app.py` : 28–64 | `_next_interview_display` ties on date are resolved by SQL ORDER BY (interview1 ASC NULLS LAST, interview2 ASC NULLS LAST) → first scanned wins. Deterministic and inherits the query's order; not pinned by a test. | ℹ️ Observation | Accepted; coverage gap noted (Q8) |
| 7 | `app.py` : 28–64 | `_next_interview_display` falls back to a date-only label (`'May 3'`) when `institute` is NULL/NaN/empty. Reasonable graceful degradation; not pinned by a test, so the behaviour is implicit rather than promised. | ℹ️ Observation | Accepted; coverage gap noted (Q9) |
| 8 | `app.py` : (no `st.set_page_config`) | Page uses Streamlit defaults (no custom title, icon, or wide layout). Phase 7 ("polish") is the documented home for this; flagging here so it isn't forgotten. | ℹ️ Observation | Deferred to Phase 7 |

---

## Fixes applied in this review

### Fix #1 — Tighten hero-heading assertion (`tests/test_app_page.py`)

**Why:** The current heuristic is

```python
@staticmethod
def _hero_heading_rendered(at: AppTest) -> bool:
    return len(at.subheader) >= 1
```

with a comment that owns the trade-off ("we don't pin the exact copy ... but we do require *some* subheader — the KPI-only render has none"). The rationale was sound *while T1 was the only feature*: the page has zero subheaders in the non-empty case, so any subheader = hero. That guarantee dies the moment T2 (Application Funnel) or T3 (Materials Readiness) lands a panel header. From that point, the `test_empty_db_renders_hero_with_cta` assertion is a tautology — the hero could be removed without breaking it.

Pinning the exact copy string is also brittle (Phase 7 may polish it). The middle path is to pin a **substring** that survives reasonable polish but would not appear in a funnel/readiness/timeline header by accident.

**Fix:** Match `"Welcome"` (the load-bearing word in the current copy) inside any rendered subheader. Phase-7 polish that drops the word "Welcome" entirely will trip this test — exactly the regression signal we want.

```python
@staticmethod
def _hero_heading_rendered(at: AppTest) -> bool:
    return any("Welcome" in s.value for s in at.subheader)
```

The test still passes today (the hero subheader is `"Welcome to your Postdoc Tracker"`), and now it will start failing if the hero is removed *or* if the copy drifts so far that the user-facing welcome message disappears.

### Fix #2 — Update `app.py` header comment block

**Why:** The file's own opening comment is the project's most-read documentation. As of `065df72` (chore on T1-E rollup) it still reads:

```python
# Phase 4 build-out: answers "What do I do today?" at a glance. This file
# is layered in over several tiers (see PHASE_4_GUIDELINES.md):
#   T1 — app shell + 4 KPI cards   (in progress)
#   T2 — application funnel
#   T3 — materials readiness panel
#   T4 — upcoming timeline
#   T5 — recommender alerts
```

T1 is done — five sub-tasks have landed. Junior contributors reading the file head will be misled about state.

**Fix:** Mark T1 ✅, fold the empty-DB hero into the T1 line (it's part of the shipped tier, not a separate one), keep T2–T5 unchanged. The file body remains untouched.

---

## Junior-engineer Q&A

> "If I were reviewing this as a junior engineer on this team, what would I want explained?"

The standing rule: every `Q` is the kind of thing a thoughtful junior would actually ask. Every `A` answers it with the *why* — including the trade-offs that were considered and rejected.

---

### Q1. `database.init_db()` runs at the very top of `app.py`. Doesn't that mean it executes on every Streamlit rerun — every widget click, every refresh?

**Yes**, and that's fine. Streamlit's execution model is "rerun the script top-to-bottom on every interaction." `database.init_db()` is built around `CREATE TABLE IF NOT EXISTS` plus a column-migration loop (`ALTER TABLE ... ADD COLUMN` only when missing) — once the schema is in place, both calls are no-ops at the SQL level (one schema-info query each). The cost is dominated by the SQLite open-and-close, which on a local file is microseconds.

The alternative — wrapping in `@st.cache_resource` or guarding with a session-state flag — adds two failure modes (stale cache after schema migration in another process; a missed init when session_state is cleared) for negligible benefit. The current pattern is the idiomatic Streamlit one.

(`PHASE_4_GUIDELINES.md` C4 explicitly excludes `@st.cache_data` from Phase 4 for the same reason: optimize when measured, not before.)

---

### Q2. Why does `app.py` define `STATUS_OPEN` / `STATUS_APPLIED` / `STATUS_INTERVIEW` in `config.py`? GUIDELINES §6 says "no hardcoded vocab", but isn't naming them by alias still hardcoding?

The anti-hardcode rule is about **typo-driven drift**: if the page file says `"[OPEN]"` and someone renames the canonical value to `"[Open]"`, every page that hardcoded the old string silently breaks. The rule's enforcement mechanism is the pre-merge grep:

```bash
grep -nE "\[OPEN\]|\[APPLIED\]|\[INTERVIEW\]" app.py   # must return zero hits
```

To avoid the grep tripping, page code needs *some* way to refer to specific statuses without the literal string. Two options were on the table:

- **(A)** Add named aliases in `config.py` (`STATUS_OPEN = STATUS_VALUES[0]`, etc.).
- **(B)** Use positional indices into `STATUS_VALUES` (e.g. `STATUS_VALUES[0]`).

(B) survives the grep but **trades the typo problem for a worse one** — a reorder of `STATUS_VALUES` (which is the most plausible future change) silently re-binds every positional-index call site. (A) keeps the source-of-truth in one file *and* makes the page code self-documenting.

The user approved (A) on 2026-04-21 as a narrow carve-out — three additive aliases only, no other `config.py` edits permitted in Phase 4 (`PHASE_4_GUIDELINES.md` §Out of scope).

---

### Q3. The hero trigger is `tracked == 0 and applied == 0 and interview == 0`. But `tracked = open + applied`, so `tracked == 0` already implies `applied == 0`. Isn't the second condition dead?

Mathematically yes — today. The form is intentional **executable documentation**: the trigger semantics are "all three counted KPIs are zero" (logged in the deferred-decision log on 2026-04-21). The triple-zero AND mirrors that exact phrasing.

There is also a forward-looking reason. Phase 4 has an open question about whether `Tracked` should later include `INTERVIEW` (the current scope explicitly excludes it because INTERVIEW has its own KPI). If a future spec change moves to `tracked = open + applied + interview`, then `tracked == 0` alone would no longer cover `applied == 0` *and* `interview == 0`. The current form survives that change without behavioural drift; the simplified form would silently start firing the hero in new edge cases.

Cost of redundancy: two extra `int == 0` comparisons per render. Negligible. Net: keep.

---

### Q4. Why a manual `🔄 Refresh` button when Streamlit already reruns the script on every widget click?

Locked decision **C3** (`PHASE_4_GUIDELINES.md`). Streamlit's auto-rerun fires on widget interaction *within the current page*. It does **not** fire when data changes via another browser tab or terminal action — e.g. the user adds a position via Opportunities in tab B while the dashboard is open in tab A. The only way to refresh the dashboard's data without a full page reload is to take an action that triggers a rerun. The Refresh button is that action, plus it's discoverable.

(The same rationale will apply to Phases 5/6 when the Applications page can update statuses — the dashboard needs a way to pick those up without a hard reload that resets scroll position.)

---

### Q5. Inside the Refresh handler, the code calls `st.rerun()`. But the button click *already* triggers a rerun. Isn't that redundant?

Yes — strictly. The execution sequence on click is:

1. User clicks the button.
2. Streamlit reruns the script (the natural button-click rerun).
3. `if st.button(...):` evaluates to `True` (the click is replayed once).
4. `st.rerun()` runs → enqueues *another* rerun.
5. Script executes a third time. `if st.button(...):` is now `False` (button-click is one-shot). Page renders cleanly.

So one wasted execution per click. **Behaviour is correct** — just slightly inefficient. Two arguments for keeping it as-is:

- It's idiomatic and self-documenting ("yes, the intent here is to refresh"). A reader who removes it and checks the same test will assume nothing changed.
- The cost is one ~100ms script execution per manual refresh. The user clicks Refresh maybe a few times per session. Total: imperceptible.

Flagged as 🟢 Minor; left unchanged. If a future review wants leaner code, the `st.rerun()` line can be deleted without breaking any test (because the AppTest test calls `.run()` explicitly after `.click()`, which is the test-mode equivalent of the natural rerun).

---

### Q6. `_next_interview_display(database.get_upcoming_interviews())` runs even on an empty DB — even when the hero short-circuit just told us there's nothing to show. Couldn't we skip the query?

Could, yes. The short-circuit would be:

```python
if tracked == 0 and applied == 0 and interview == 0:
    next_interview = NEXT_INTERVIEW_EMPTY  # save one DB query
else:
    next_interview = _next_interview_display(database.get_upcoming_interviews())
```

The reason **not** to is the conceptual cost: it couples the Next Interview KPI to the hero trigger. Today the two share a "no data" semantic — but they don't have to. A future product call could decouple them (e.g. a DB with only terminal-status rows still has no Next Interview, but a product change might suppress the hero in that case). The current code keeps the two computations independent and lets each branch own its own state.

The query itself returns immediately on an empty DB (the SQL filter `interview1_date >= today` produces zero matches before pandas materializes any rows). Net cost: <1ms. Not worth the coupling.

---

### Q7. `_next_interview_display` walks rows with `iterrows()`. Isn't pandas-vectorized faster?

Yes, in big-O terms. In practice:

- The DataFrame is the result of `get_upcoming_interviews()`, which filters to rows where *either* interview date is today-or-later. For a single-user postdoc tracker this is realistically <10 rows ever. The `iterrows()` version executes in microseconds.
- The vectorized version would need to: (a) `pd.melt` the two date columns into a long format, (b) drop NaN/empty/past dates, (c) sort, (d) take `head(1)`, (e) read off the institute. That's five operations and three intermediate copies — more code, more mental overhead, no perceptible win at this data scale.

The iterative form also makes the **selection rule** explicit and reviewable line-by-line. The selection rule is the locked decision; readability beats performance here.

---

### Q8. `_next_interview_display` ties on date — what wins?

The first row scanned wins, where iteration order is whatever `get_upcoming_interviews()`'s `ORDER BY` returns. The SQL is:

```sql
ORDER BY a.interview1_date ASC NULLS LAST,
         a.interview2_date ASC NULLS LAST
```

So if two positions have an interview on the same earliest future date:

- The position whose `interview1_date` matches that date will be scanned before the position whose `interview2_date` matches it (because `interview1_date ASC` orders the first ahead of the latter).
- Within the same row, `interview1_date` is checked before `interview2_date` due to the inner loop's `for col in ("interview1_date", "interview2_date"):`.

The behaviour is deterministic and inherited from the SQL ORDER BY contract. It is **not** pinned by a test. A small AppTest with two positions tied on the same future date would be a useful coverage addition — flagged here for a future tier (T6 pre-merge, or T2 if the funnel test scaffold needs to seed interview data anyway). Not blocking for T1 merge.

---

### Q9. What if `institute` is NULL? `_next_interview_display` builds `'May 3 · {institute}'` — does it crash?

No. The relevant guard is:

```python
if best_institute and not pd.isna(best_institute):
    label += f" · {best_institute}"
```

Three failure modes for `institute` collapse here:

| Stored as | DB row → pandas | Caught by |
|-----------|-----------------|-----------|
| NULL (column-allows-NULL, value omitted) | `None` | `if best_institute` (None is falsy) |
| Empty string `""` | `""` | `if best_institute` ("" is falsy) |
| pandas NaN (object-dtype column with mixed NULL + string rows) | `float('nan')` | `not pd.isna(...)` (NaN is truthy — `bool(float('nan')) == True` — so the truthy-check alone wouldn't catch it) |

The output in any of these cases is a date-only label — `'May 3'` — which is graceful degradation rather than an error.

This isn't pinned by a test today. The `institute` column on `positions` is `TEXT NOT NULL` per the schema, so the NULL case is not reachable through `database.add_position()` (the test helper `make_position` always seeds it). But three things are worth knowing:

- The schema NOT NULL constraint is a runtime guard, not a static one — a hand-edited DB or a future schema relaxation could violate it.
- Empty string ("") is reachable: nothing in the schema or the page-layer Save handlers prevents `institute = ""`.
- The graceful-degradation behaviour is currently an **implementation detail**, not a documented contract.

A test would harden this. Not blocking for T1 merge; a strong T6-A pre-merge candidate.

---

### Q10. Why isn't `st.set_page_config()` called?

The page is using Streamlit's defaults: title from `st.title()`, no favicon, no wide layout. `st.set_page_config()` would let us pin a browser-tab title, a favicon, and (more usefully) a wider layout — the dashboard's eventual five-panel grid (KPI row + funnel/readiness + timeline + alerts) will be cramped at the default content width.

Phase 7 ("polish — urgency colors, search bar, responsive check") is the documented home for layout-level concerns. Adding `st.set_page_config(layout="wide")` now would be scope creep; flagging it here so it isn't forgotten when Phase 7 starts.

---

### Q11. The hero subheader copy is "Welcome to your Postdoc Tracker". Doesn't that duplicate the page title?

Yes. The hero exists *only* on the empty-DB state, so a returning user with even one position never sees both. The duplication is intentional emphasis: an empty dashboard with no greeting can read as "broken / loading"; the explicit Welcome subheader signals "this is the right page; you just haven't started yet."

Fixable by Phase 7 polish (e.g. swap to "Let's add your first position"). Not blocking.

---

### Q12. The hero CTA is `type="primary"`. The test says we can't verify primary styling via AppTest — so what *is* tested?

`AppTest.Button.type` reports the widget-class name (the Python class), **not** the Streamlit `type=` parameter that controls visual primary/secondary styling. (Documented in `memory/project_state.md` under "Observed Streamlit behaviours worth remembering".)

What the test actually pins:

- The CTA exists by **label** (`"+ Add your first position"`) — `test_empty_db_renders_hero_with_cta`.
- The CTA's target page is `pages/1_Opportunities.py` — `test_cta_targets_opportunities_page`, which reads `app.py` source for the literal string. Brittle, but the only option AppTest single-file mode leaves us — `st.switch_page` raises in single-file mode because sibling pages aren't registered.

Primary styling = source-level review only. This review confirms it: `app.py:112` explicitly passes `type="primary"`.

---

### Q13. `st.title("Postdoc Tracker")` is rendered inside `with title_col:`. I thought `st.title()` had to be the first call on the page?

It doesn't. `st.title()` is just a styled `st.markdown` underneath — it has no positioning constraint and works inside any container or column. The `at.title` AppTest selector finds it regardless of which container holds it (verified by `test_page_loads_on_empty_db` which asserts on `at.title[0].value`).

What *is* required to be first on the page is `st.set_page_config()` (which the page doesn't call — see Q10). That is enforced by Streamlit at runtime and would raise `StreamlitSetPageConfigMustBeFirstCommandError`.

---

### Q14. `st.switch_page("pages/1_Opportunities.py")` — what happens if that file is renamed or moved?

Streamlit raises `StreamlitAPIException` at click time. The AppTest single-file mode raises *immediately* on the call (sibling pages aren't registered in single-file mode), so a hand-test by clicking the CTA would surface the breakage instantly.

This is the entire reason `test_cta_targets_opportunities_page` reads `app.py` source for the literal `"pages/1_Opportunities.py"`: it's a regression-style assertion that the path string in the source matches the project's actual file. If the page is ever renamed (Phase 7?), the rename will need to update both the page file and the assertion in two places — annoying but not silently broken.

A more durable check would be to assert that the file exists on disk:

```python
assert pathlib.Path("pages/1_Opportunities.py").exists()
```

This wasn't added because the source-grep already catches the literal-string drift, and adding a filesystem assertion would couple the test to the project layout in a way that breaks if the test runner cwds elsewhere. Acceptable as-is.

---

### Q15. Why does the page import `pandas as pd` just to use `pd.isna`? Couldn't `math.isnan` plus an `is None` check do the same thing?

It could, with three downsides:

- `math.isnan(None)` raises `TypeError`, so we'd need `if v is None or math.isnan(v):` — verbose and easy to invert by accident.
- `math.isnan(v)` raises `TypeError` for non-numeric values — harmless here (we only feed it ISO-format strings or numerics) but a footgun if the function grows.
- We're already importing `pandas` for the `DataFrame` parameter type hint and the `iterrows()` call. Importing `pandas` *and* `math.isnan` is two imports doing one job.

`pd.isna` is the catch-all here: it accepts None, NaN, NaT, and arrays. Standard pandas idiom. Documented in F2 of the Phase 3 Tier 5 review for the same reason.

---

### Q16. The KPI labels (`"Tracked"`, `"Applied"`, `"Interview"`, `"Next Interview"`) are duplicated between `app.py` and `tests/test_app_page.py`. Isn't that a violation of DRY?

Intentional. The labels are the **UI contract** locked in `DESIGN §app.py` and `PHASE_4_GUIDELINES.md`. The test exists to **regression-detect drift** in either direction:

- If `app.py` renames `"Tracked"` → `"Active"`, the test fails.
- If `app.py` reorders the columns, the test fails (it asserts the full list `== KPI_LABELS`, not just set membership).

Importing the labels from a shared module (e.g. exposing them in `config.py` as `KPI_LABELS = [...]`) would defeat the purpose — a refactor that wrongly renames the constant on both sides simultaneously would be invisible. The duplication is the regression signal.

---

### Q17. Tests use a `db` fixture that monkeypatches `database.DB_PATH`. Does `app.py`'s `database.init_db()` call (which runs at the very top of the script) honour that monkeypatch?

Yes. `AppTest.from_file("app.py").run()` executes the page module in the same Python process as the test. `monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")` mutates the `database` module's attribute *before* `at.run()` invokes the page, so when `app.py` calls `database.init_db()`, the function reads the patched `database.DB_PATH`. After the `db` fixture yields, monkeypatch restores the original.

The test never touches `postdoc.db`. Verified by `tests/conftest.py:18` and re-verified across all 23 T1 tests (none mention `postdoc.db`).

---

## Pre-merge readiness for T6

Per `PHASE_4_GUIDELINES.md` pre-merge checklist (excerpt for T1 scope):

- [x] `pytest tests/ -q` — **246 passed** (was 223 at end of Phase 3; +23 new T1 tests)
- [x] `pytest -W error::DeprecationWarning tests/ -q` — **246 passed**, zero deprecation warnings
- [x] `git diff main..HEAD -- database.py exports.py pages/1_Opportunities.py` — **empty** (no scope creep into Phase 3 code)
- [x] `git diff main..HEAD -- config.py` — three additive lines only (`STATUS_OPEN`, `STATUS_APPLIED`, `STATUS_INTERVIEW` aliases), per the user-approved 2026-04-21 carve-out
- [x] `grep -nE "\[OPEN\]|\[APPLIED\]|\[INTERVIEW\]" app.py` — **zero hits** (all status references via `config.STATUS_*` aliases)
- [x] `grep -nE "^\s*[0-9]+\s*#\s*(days|urgent|alert)" app.py` — **zero hits** (no magic-number thresholds)
- [x] Empty-DB hero renders when `count_by_status()` returns all zeros — pinned by `test_empty_db_renders_hero_with_cta` and (after Fix #1) the Welcome-substring check
- [ ] PR body lists commit roster + acceptance criteria + delta vs. DESIGN §6 — **deferred to T6-A** (the dedicated pre-merge review pass at the end of Phase 4)

**Recommendation:** T1 is mergeable in isolation — but the locked plan keeps it on `feature/phase-4-tier1` until T2–T5 land, then T6 packages everything into one PR. No reason to deviate.

---

## Coverage gaps deliberately left open (to revisit at T6-A)

These are not Tier-1 defects; they are observations worth landing in the T6 pre-merge sweep when the test scaffold is touched anyway:

1. **Tied earliest dates** — pin a test where two positions have an interview on the same future date (Q8).
2. **NULL/empty institute → date-only label** — pin a test for the graceful-degradation path (Q9).
3. **Hero subheader exact copy vs. polish** — once Phase 7 polish lands, decide whether to replace the substring match with an exact-copy match.

---

_Initial draft: 2026-04-21, immediately after T1-E rollup._
