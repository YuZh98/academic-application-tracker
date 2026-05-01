# Phase 4 — Tier 5 Code Review

**Branch:** `feature/phase-4-tier5-RecommenderAlerts` (3 commits ahead of `main`; T4 already merged via PR #12 → `483efa9`)
**Scope:** T5 — Recommender Alerts panel on `app.py`. A full-width section beneath the T4 Upcoming row that surfaces every recommender whose letter is past `RECOMMENDER_ALERT_DAYS` of being asked and still has no `submitted_date`, grouped so each person appears in one bordered card with a `**⚠ {Name}**` header and a bullet list of the letters they owe.
**Verdict:** Approve, merge after the inline polish + boundary test land.
**Stats:** `app.py` 351 → 416 (+68 lines, the new T5 panel and two private formatters); `tests/test_app_page.py` 1810 → 2154 (+344 lines, **15** new `TestT5RecommenderAlerts` cases across 4 groups); `CHANGELOG.md` +56; `TASKS.md` +30 (T5-A flipped to `[x]`, sprint footer date-stamp, "Recently done" entry). **519 → 534 tests passing under both `pytest -q` and `pytest -W error::DeprecationWarning -q`.**
**Cadence:** `test(app)` (red) → `feat(app)` (green) → `chore(tracker)` (rollup). Three commits, perfect TDD isolation. No new public `database.py` symbol — T5 is pure presentation reuse over `database.get_pending_recommenders()` (which has existed since Phase 2).
**Reviewer attitude:** Skeptical. Verify every Streamlit, pandas, and SQL claim. Cross-grep DESIGN against the source for every locked string. Pay special attention to **how the panel is testable when the Recommenders page UI does not exist yet** — the project's first opportunity to demonstrate that the `database.add_*` API is the testing seam, not the UI.

---

## Executive summary

Tier 5 is the smallest Phase-4 tier in code-line terms (≈ 68 lines of production code) but the most subtly load-bearing in *test approach*: there is no Recommenders page UI yet — Phase 5 owns that — and yet the panel's behaviour must be pinned end-to-end against a populated database. The worker's answer is the textbook one: seed via `database.add_position()` + `database.add_recommender()` (with `database.update_recommender()` for the submitted-letter case), then render the dashboard via AppTest, then assert on the rendered markdown. The seed step does not require any UI; the database API has been the public seam since Phase 2, and `tests/conftest.py::make_position` already exists to keep seeds short.

The 15 tests cover the full contract: subheader stability across empty↔seeded transitions; the `EMPTY_COPY` exact wording; the `**⚠ {Name}**` bold-warn header; the T4 Label precedent (`{institute}: {position_name}` with bare-name fallback when institute is empty); the `asked Nd ago` phrasing; the `Mon D` date format; the em-dash for null deadline; the GROUPING contract (two letters from one recommender → one card with two bullets; two recommenders → two cards); and the SQL-side filter (a submitted letter does not appear, an asked-today letter does not appear). The bordered-container CSS is pinned via a `count >= 2` source grep — the worker explicitly noted the empty-DB hero's existing `st.container(border=True)` would otherwise satisfy a `>= 1` count vacuously.

The review surfaces **zero bugs**, **two 🟡 polish observations** (one fixed inline; one kept-by-design), **two 🟢 future-work items**, and **one ℹ️ carried-forward observation** (the §6 grep miscount in `pages/1_Opportunities.py:395`, first noted in the Tier-3 review, still tripping). One 🟡 polish — drop the `str(_name)` defensive cast inside the card-body assembly — was applied inline; same anti-pattern as the `.astype(str)` removal in the T4 review (GUIDELINES §12: don't add code for impossible states). The other 🟡 — `_format_label` and `_format_due` defined inside the populated-branch `else:` block — is left as the worker chose, with rationale documented in Q&A. One additional test was added inline pinning the inclusive-boundary case at `RECOMMENDER_ALERT_DAYS` ago, mirroring T4's two-sided urgency-band tests.

**Verdict: approve, merge after the inline polish + boundary test land.**

---

## Findings

| # | File · Line | Issue | Severity | Status |
|---|-------------|-------|----------|--------|
| 1 | `app.py` : 414 (`else:` populated branch) | `_body = "**⚠ " + str(_name) + "**\n" + "\n".join(_bullets)` casts the groupby key through `str(...)` defensively. `_name` is the value of the `recommender_name` column, which is `TEXT` in the `recommenders` schema and arrives at the page as a Python `str` via `pd.read_sql_query`. Same anti-pattern flagged and removed in the T4 review (`.astype(str)` on `deadlines["status"]`). | 🟡 polish | **Fixed inline** (see Q1) |
| 2 | `app.py` : 367–386 | `_format_label` and `_format_due` are defined inside the `else:` populated branch instead of at module top-level alongside `_next_interview_display`. They re-define on every render, *and* they live in a place no reader looking for module helpers would find them. | 🟡 polish | Kept by design (see Q2) |
| 3 | `tests/test_app_page.py` : `TestT5RecommenderAlerts` | The boundary case `asked_date == today - RECOMMENDER_ALERT_DAYS` (the SQL inclusive cutoff `<=`) is not pinned — only the inside-the-window-doesn't-fire side is. T4's `TestGetUpcoming` pinned both inner and outer urgency boundaries; T5's coverage of the alert-day boundary is half. | 🟡 polish | **Fixed inline** — added `test_asked_at_alert_boundary_fires` (see Q3) |
| 4 | `database.py` : `get_pending_recommenders` line 1319 (pre-existing) | The filter is `submitted_date IS NULL` (NULL only). `is_all_recs_submitted` uses `submitted_date IS NULL OR submitted_date = ''`. A row with `submitted_date = ''` would be "not submitted" per the latter and "not pending" per the former — the two helpers disagree. Surfaces here because T5 is the first dashboard panel to consume the helper. Pre-existing; not introduced by T5. | 🟢 future | Backlog (see Q4) |
| 5 | `app.py` : 416 + DESIGN §8.4 D-C | The single `st.markdown(...)` card body is a static string; Phase 5 T6's "Compose reminder email" button + LLM-prompts expander cannot graft onto a static markdown block — the future structure must split the card into header + per-position rows with their own widgets. T5 hits the §8.1 spec exactly; it just locks in a shape that Phase 5 T6 will rework. | 🟢 future | Backlog (see Q5) |
| 6 | `pages/1_Opportunities.py` : 395 (pre-existing) | The pre-existing `'[APPLIED]'` literal in a docstring-style comment trips the GUIDELINES §6 pre-merge grep. Same shape carried forward from Tiers 3 and 4. | ℹ️ Observation | Carry-over (see Q6) |

---

## Fixes applied in this review

**Two fixes landed inline:**

1. **`app.py`** — drop the `str(_name)` cast in the card-body assembly. `_name` arrives from `pd.DataFrame.groupby("recommender_name", sort=False)` whose key dtype is the column dtype (`object`/`str` for SQLite `TEXT`); the cast was defensive against an impossible state (groupby keys cannot be a non-`str` value when the column is). Removing it shaves one call without changing observable behaviour. All 15 `TestT5RecommenderAlerts` tests stay green; the contract was always *"the header reads `**⚠ {Name}**`"*, not *"`_name` is forced through `str()`"*. Same reasoning that removed the no-op `.astype(str)` in the T4 review.

2. **`tests/test_app_page.py`** — add `test_asked_at_alert_boundary_fires` to `TestT5RecommenderAlerts` Group B. Pins that a recommender asked **exactly** `RECOMMENDER_ALERT_DAYS` ago produces a card (the SQL cutoff is inclusive `<=`). Mirrors T4's two-sided urgency-band coverage (`test_urgency_red_within_urgent_threshold` + `test_urgency_yellow_between_urgent_and_alert`, both with explicit boundary offsets).

The other findings — `_format_*` placement, the `submitted_date=''` divergence, the §6 carry-over, and the Phase-5-T6 structural concern — are documented and deferred. None blocks the merge.

---

## Junior-engineer Q&A

### Q1 — Why is `str(_name)` worth removing if it's harmless? Isn't this a pedantic nit?

**A.** It is a small change. The argument for removing it is the same as the T4 `.astype(str)` removal, with one project-specific twist:

GUIDELINES §12 lists *"Catching `Exception` and swallowing silently"* as an anti-pattern, and the project-level system rule generalises it: *"Don't add error handling, fallbacks, or validation for scenarios that can't happen."* The `str(_name)` cast lies about the contract — it implies *"`_name` might not be a `str`"* when in fact pandas's `groupby` on an object-dtype column produces `str` keys by construction. A reader landing on the line spends a moment thinking *"what case is this guarding?"* and the honest answer is none.

The project-specific twist: **the analogous T4 cast was the very first finding fixed in the previous review**. Leaving the same pattern in T5 a week later would set up a slow drift in code culture — *"defensive casts are tolerated"*. Cheap reversal now, costly to clean up later when the pattern is everywhere.

The fix is one line:

```python
# before
_body = "**⚠ " + str(_name) + "**\n" + "\n".join(_bullets)
# after
_body = f"**⚠ {_name}**\n" + "\n".join(_bullets)
```

The f-string substitution does the same job as the cast for the only data shape that actually arises (`_name` is already `str`), and reads as the natural Python idiom. None of the 15 T5 tests depended on the cast.

(There is one degenerate case worth naming: if `recommender_name` were `NULL` in the DB, pandas would surface it as `None`, and `groupby` with the default `dropna=True` would silently drop the group — neither the cast nor the f-string would render a `"None"` card. So the cast was never doing the work its presence implied. See Q7 for the broader NULL-name discussion.)

### Q2 — Why leave `_format_label` and `_format_due` inside the `else:` block instead of moving them to module top-level next to `_next_interview_display`?

**A.** Three readings, weighed:

1. **Reuse breadth.** `_next_interview_display` lives at module level because it serves a `st.metric` two screens above its caller; the function exists in its own logical layer (the helpers section between page setup and panel rendering). The T5 helpers are private to the Recommender-Alerts panel — they are not used by any other panel and never will be (the bullet-line phrasing is panel-specific). Module-level placement would advertise reuse breadth that doesn't exist.

2. **Lexical proximity.** The bullet-line construction is the only place the formatters are called. Lifting them three screens up to the module's helper section would force a future reader debugging the panel to scroll between the call site and the definition — exactly the friction the worker avoided by inlining.

3. **Re-definition cost.** A common knee-jerk objection to inline `def`s is *"they redefine on every render!"* For a Streamlit script that re-runs the whole file on every interaction, *every* `def` redefines on every render — `_next_interview_display`'s module-level placement gives it no special exemption. The runtime cost is identical.

The trade-off is real but mild. A maximally-consistent codebase would move them to module level so all helpers cluster. A maximally-readable panel keeps them near their call site. The worker chose readability; this review respects that choice.

What I would *not* tolerate is a half-and-half world where some panels inline and some don't. If Phase 5 / 6 / 7 keep adopting inline panel-helpers, formalise the convention in GUIDELINES §3. If module-level wins, rewrite this panel during T6's pre-merge cohesion sweep. Current state: the pattern is established by *one* panel, so naming the convention is premature.

### Q3 — Why does the boundary test matter? The other tests already exercise the panel.

**A.** Because the SQL contract is *inclusive*, and inclusive boundaries are the most-mistaken half of every range filter.

Looking at `database.get_pending_recommenders`:

```sql
WHERE r.submitted_date IS NULL
  AND r.asked_date IS NOT NULL
  AND r.asked_date <= ?
```

The `<=` says: *if today is `2026-04-29` and `RECOMMENDER_ALERT_DAYS = 7`, then `cutoff = '2026-04-22'`, and `asked_date = '2026-04-22'` matches*. The existing `test_unsubmitted_but_recent_ask_does_not_fire` pins the OTHER side (`asked_date = today` does NOT match — `today > cutoff`). What was missing: pinning the cutoff itself.

Three ways the boundary can break silently:

- A future tightening to `<` would drop the at-the-boundary case — exactly seven days ago becomes invisible. No existing test would catch this.
- A timezone-sensitive change to `cutoff` computation could nudge it by a day either way. No existing test would catch this either.
- A pandas-side filter reading `asked_date < cutoff` after the SQL had already done its inclusive cut would produce a spurious-looking "asked-today" panel. Not a test failure, but a design contract violation.

The new test seeds at `days_ago=config.RECOMMENDER_ALERT_DAYS` exactly and asserts at least one card. T4's `TestGetUpcoming` has the precedent: `test_urgency_red_within_urgent_threshold` (offset = 0 and `DEADLINE_URGENT_DAYS`, both inclusive); `test_urgency_yellow_between_urgent_and_alert` (offset = `DEADLINE_URGENT_DAYS + 1` and `DEADLINE_ALERT_DAYS`, both inclusive). Same instinct: explicit boundaries on every range filter.

### Q4 — `is_all_recs_submitted` and `get_pending_recommenders` disagree on `submitted_date = ''`. Is that a bug?

**A.** It's a latent inconsistency, not a bug for v1. Resolving it requires a decision on representation that has not been made yet.

Looking at the two helpers:

- `is_all_recs_submitted`: `WHERE position_id = ? AND (submitted_date IS NULL OR submitted_date = '')`. *"All non-NULL non-empty submitted_date values are submitted."*
- `get_pending_recommenders`: `WHERE submitted_date IS NULL ...`. *"Only NULL is pending."*

A row with `submitted_date = ''` is therefore:
- Counted as **not submitted** by `is_all_recs_submitted` (so the position's *all-recs-submitted* flag stays `False`).
- Counted as **submitted** by `get_pending_recommenders` (so the row does *not* surface in the alerts).

The user gets contradictory signals: the Applications page would say the position is missing recs, the dashboard alerts panel would say it's not pending. Whether this is reachable depends on the writer:

- The Recommenders page (Phase 5 T5) does not exist yet. When it does, its `st.date_input(...)` will produce `None` on a cleared field, never `''`.
- `database.add_recommender()` with no `submitted_date` field leaves it `NULL`.
- `database.update_recommender()` will write whatever the caller passes. A caller writing `''` is the only path to the divergent state.

So in practice, `submitted_date = ''` is unreachable in v1's UI. But the divergent SQL is a smell — the two helpers should agree on the *meaning* of "submitted." Two acceptable resolutions, both Phase-5-or-later work:

- **Tighten `get_pending_recommenders`** to `submitted_date IS NULL OR submitted_date = ''` — match `is_all_recs_submitted`. Simple; preserves the *"empty string means not submitted"* convention.
- **Loosen `is_all_recs_submitted`** to drop the `OR submitted_date = ''` clause, AND add a `CHECK(submitted_date IS NULL OR length(submitted_date) > 0)` constraint to the schema — enforce the *"NULL is the only empty"* contract at the storage layer.

Either is fine; both touch `database.py` and are out-of-scope for T5 (a presentation tier). This finding is logged for the Phase-5-T5 / T7-polish window.

### Q5 — Why won't the static `st.markdown(...)` card body extend to Phase 5 T6's reminder email button?

**A.** Because Streamlit widgets cannot live inside a `st.markdown` string. They are sibling elements, not embedded children.

The current T5 card body is *one* `st.markdown` call per recommender:

```python
_body = "**⚠ Dr. Smith**\n- Stanford: Pos-A (asked 14d ago, due Apr 24)\n- MIT: Pos-B (asked 14d ago, due May 5)"
st.markdown(_body)
```

That string is interpreted client-side by Streamlit's markdown renderer. There is no way to inject a `st.button(...)` into the middle of it — buttons are top-level Streamlit elements that get their own protobuf in the page tree, not markdown spans.

Phase 5 T6 (DESIGN §8.4 D-C) calls for a *primary* `Compose reminder email` button per recommender + a secondary `LLM prompts (N tones)` expander, both per-recommender. The current shape will need to refactor to:

```python
with st.container(border=True):
    st.markdown(f"**⚠ {name}**")
    for row in group:
        st.markdown(f"- {label} (asked {N}d ago, due {due})")
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Compose reminder email", key=f"recs_email_{name}"):
            ...
    with col2:
        with st.expander("LLM prompts (N tones)"):
            st.code(...)
```

This is a real refactor — the markdown stops being one big string and the buttons get explicit `key=` prefixes for AppTest to find them (`recs_` per GUIDELINES §13's prefix table).

The point of flagging this as 🟢 future is *not* to second-guess T5's choices. T5 is on the **dashboard**, where DESIGN §8.1 explicitly says the alerts row carries no interactive elements (the email-compose button lives on the Recommenders page). The T5 single-string shape is correct for the dashboard. But when Phase 5 T6 builds the Recommenders page, **the structure cannot be copy-pasted**; the page will need its own card-rendering loop with widgets per recommender, and the test class will need new patterns. Naming this here so the Phase-5 worker doesn't start by literally porting the dashboard panel and discovering the dead-end mid-implementation.

### Q6 — Why is the §6 grep still tripping in `pages/1_Opportunities.py`? Wasn't this flagged in T3 and T4?

**A.** Yes; same hit, third tier in a row. It will keep tripping until either the grep is tightened or the comment is rephrased.

The hit:

```python
# pages/1_Opportunities.py:395
# ('Applied'), never the raw bracketed storage value ('[APPLIED]').
```

The comment exists *to document* the literal it forbids; it is therefore a literal under the §6 grep. Two acceptable resolutions, repeated from the T3 + T4 review docs:

- **Tighten the grep** to exclude comment lines: `grep -nE "^[^#]*(\[SAVED\]|\[APPLIED\]|\[INTERVIEW\])" app.py pages/*.py`. One-line change in the GUIDELINES §11 pre-commit checklist; matches the T2-C `st\.columns\(2\)` analogue's resolution path.
- **Hash-out the literal in the comment** via concatenation: `'[' + 'APPLIED' + ']'`. Same readability; the grep lands at zero hits. Single-line edit to `pages/1_Opportunities.py`.

Neither is in scope for T5. The right place to land it: **Phase 4 T6's pre-merge cohesion sweep**, alongside the analogous T2-C grep refinement. By that point the grep will have logged three identical false-positives in three review documents; the cost-benefit is decisive.

### Q7 — How did the worker test the panel when there is no UI to add recommenders?

**A.** This is the question the user explicitly flagged, and the answer is the cleanest demonstration so far in this codebase that the **database API is the testing seam, not the UI**.

The seed helper inside the test class:

```python
@staticmethod
def _seed_pending(
    days_ago: int = 14,
    position_name: str = "BioStats Postdoc",
    institute: str = "Stanford",
    recommender_name: str = "Dr. Smith",
    deadline_offset: int | None = 10,
) -> int:
    pos_id = database.add_position(make_position({...}))
    return database.add_recommender(pos_id, {
        "recommender_name": recommender_name,
        "asked_date": (date.today() - timedelta(days=days_ago)).isoformat(),
    })
```

This pattern relies on three guarantees the project has carried since Phase 2:

1. **`database.add_position` and `database.add_recommender` are public API** (DESIGN §7), not test-only helpers. They are called by `pages/1_Opportunities.py` (which exists) and will be called by `pages/3_Recommenders.py` (which does not exist yet), and they are the same function in both worlds. Tests do not need a UI; they need the API, and the API is stable.
2. **GUIDELINES §9 forbids raw SQL in tests.** `Seed data via database.add_position() / upsert_application() — never raw SQL in tests.` This rule pre-empts the pattern many test suites land in: writing SQL fixtures that drift from the production write path. Here, the seed goes through the same `_connect()` context manager, the same `INSERT` statement, the same `exports.write_all()` call as a real user creating the row. A bug in `add_recommender` would surface in the panel test, which is exactly what we want.
3. **`tests/conftest.py::make_position`** keeps the seed terse. Without it, every test would have to assemble a 5-or-6-key fields dict; with it, only the fields that matter to *this* test get overridden.

The decoupling of *how data gets into the DB* from *how the panel renders* is the property that makes T5 testable today. When Phase 5 T5 ships the Recommenders page, those page tests will *also* call `database.add_recommender` for seeding (by GUIDELINES §9), then exercise the page's Save / Edit / Delete buttons on top. The same API serves both the production page and the test seed.

What this **doesn't** test: end-to-end UI flow from "user fills the recommenders form" → "card appears on the dashboard." That is left for the Phase 5 T5 review, where the seed-the-page-form path becomes testable. Until then, the dashboard panel's behaviour against a populated database is the only contract that exists, and it is the contract these 15 tests pin.

The didactic takeaway: **a UI gap is not a test gap when the database API is public**. The two surfaces share a write path; testing through the API tests the same code the future UI will exercise.

### Q8 — Why is grouping by `recommender_name` (a string) the right granularity? What about same-named recommenders at different organisations?

**A.** It is the right granularity for v1 — and it does collide on same-named different-people. This is a deliberate trade-off named in DESIGN §8.4.

The collision case: two unrelated postdoc applicants both have a recommender named "Dr. Smith" — but one is at Stanford and the other is at MIT. Today, both Smiths share one card. The user's mental model on a postdoc tracker is *"I have a recommender named Dr. Smith"*; the alert tells them they owe Dr. Smith reminders for letters across multiple positions. A two-Smiths case would aggregate *both* people's letters under one card, which is semantically incorrect.

Why ship it anyway:

- The product is a **personal** postdoc tracker. The realistic recommender pool is ≤ 5 people, almost certainly all distinguishable by name. Same-named different-recommenders is a v2 problem.
- Distinguishing by name + email is the standard fix, but `recommenders` has no `email` column today. Adding one is a schema change with its own migration, not a T5 polish.
- The test `test_two_recommenders_render_two_cards` pins the standard case (Dr. Smith vs Dr. Jones → two cards). The pathological collision is unpinned (no test asserts that two different "Dr. Smith"s would or wouldn't merge).

Forward-looking notes:

- DESIGN §12.x's v2 design notes already flag the *"recommender as a first-class entity"* shape: a separate `people` table with stable IDs, and `recommenders` becoming a join table between `positions` and `people`. Once that lands, group-by becomes group-by-`people.id` and the collision disappears.
- Until then, GUIDELINES does not require disambiguation. The existing comment in `app.py` documents *"groupby aggregates a person's multiple-letter cases into one card"* — explicit enough that a future maintainer hitting the same-name collision can find the right place to fix it.

The v1 contract is: *one row per (recommender_name, position) in the SQL projection; one card per `recommender_name` in the UI*. T5 implements that contract correctly. The collision is a **product limitation**, not a code bug.

---

## Observations for Tier 6+ design

Forward-looking, not blocking T5:

1. **The dashboard now has five panels** (KPI grid, Funnel + Readiness `st.columns(2)` row, Upcoming, Recommender Alerts). Phase 4 T6's cross-panel cohesion smoke (TASKS.md: 1280 / 1440 / 1680 widths) needs to confirm the vertical stack reads top-to-bottom in the priority order DESIGN §8.1 prescribes, and that the absence of any one panel (e.g., empty Recommender Alerts on a fresh DB) does not collapse the layout.

2. **Three panels now share the *"subheader stable across both branches"* invariant** (T2 funnel, T3 readiness, T4 Upcoming, T5 alerts). The pattern is now established enough to formalise as a class-level constant or a shared helper. Today each tier defines `SUBHEADER` / `SUBHEADER_DEFAULT` at the test class. A T6 refactor pulling these into `tests/test_app_page.py`'s top-level `KPI_LABELS`-style constants would shave ≈ 8 lines and lock the cohesion at one place.

3. **The `**⚠ Name**` warn-glyph header is a new UI element** that may want to land in `config.py` as `RECOMMENDER_ALERT_GLYPH = "⚠"` for the same reason `NEXT_INTERVIEW_EMPTY = "—"` lives in `app.py`. Today it is a magic literal in two places: the source (`"**⚠ "` concatenation) and the test (`WARN_GLYPH = "⚠"`). A glyph rename would require both — a single-source constant in `config.py` would catch it.

4. **The two formatters (`_format_label`, `_format_due`) duplicate concepts already encoded in `database._label_for` and `st.column_config.DateColumn(format="MMM D")`** at the database layer. An open question for T6 / Phase 7 polish: do the *page-side* formatters belong in a `display_helpers.py` module shared with `pages/1_Opportunities.py` (which has its own `_safe_str`)? For v1 the duplication is small enough to ignore; for v2 / general-tracker profiles, a centralised display layer would prevent drift.

---

## Verdict

**Approve, merge.**

- All pre-merge checks pass: `pytest tests/ -q` (535 green after the boundary test added in this review); `pytest -W error::DeprecationWarning -q` (535 green); GUIDELINES §6 status-literal grep clean modulo the carried-forward comment hit (Q6); pinned-version floors honoured (Streamlit 1.56, pandas 3.0.2 per GUIDELINES §1).
- One 🟡 polish landed inline (`str(_name)` cast removal — same anti-pattern as the T4 `.astype(str)` finding); one new test landed inline (`test_asked_at_alert_boundary_fires`, T4 boundary-coverage precedent); one 🟡 polish kept-by-design with rationale (helpers placement); two 🟢 future items logged for Phase 5 T5 / T6 / v1.0-rc; one ℹ️ observation deferred to T6 sweep.
- The work directly answers the reviewer's testability question: the panel is testable through `database.add_position` + `database.add_recommender` + `database.update_recommender` (no UI required) precisely because the project has held the *"public DB API is the testing seam"* contract since Phase 2 and GUIDELINES §9 forbids raw SQL in tests. T5 is the cleanest demonstration so far.
- TDD cadence textbook (red → green → tracker rollup); CHANGELOG entry comprehensive; TASKS.md tickmark + sprint footer updated. No DESIGN.md / GUIDELINES.md / DB / migration impact.

**Merge sequence:** push branch → open PR → reviewer scan → squash-merge → continue to Phase 4 T6 (cross-panel cohesion smoke + `phase-4-finish-review.md` + tag `v0.5.0`).

---

_Review by skeptical-reviewer session, 2026-04-29._
