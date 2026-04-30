# Phase 4 — Tier 4 Code Review

**Branch:** `feature/phase-4-tier4-UpcomingDeadline` (9 commits ahead of `main`)
**Scope:** T4 — full-width Upcoming timeline panel on `app.py`. T4-0 + T4-0b lock `DESIGN §8.1`'s six-column contract; T4-A adds `database.get_upcoming(days)` as a thin projection over the existing deadlines + interviews helpers; T4-B wires the panel beneath the funnel/readiness `st.columns(2)` row with a window selectbox driving subheader, empty copy, and data fetch in lockstep.
**Stats:** `database.py` +127 (new `get_upcoming` + 3 private helpers + `_UPCOMING_COLUMNS`); `app.py` +69 (selectbox + subheader + dataframe + column-rename + status-label map); `config.py` +23 (`UPCOMING_WINDOW_OPTIONS` + invariant #10); `tests/test_database.py` +326 (`TestGetUpcoming`, 19 cases); `tests/test_app_page.py` +357 (`TestT4UpcomingTimeline`, 19 cases); `tests/test_config.py` +52 (3 invariant-#10 cases). `DESIGN.md` +48; `CHANGELOG.md` +150; `TASKS.md` +47/-23; `docs/dev-notes/streamlit-state-gotchas.md` +34 (gotcha #15). **497 → 519 tests passing (`pytest -q` and `pytest -W error::DeprecationWarning -q`); also clean under `-W error::FutureWarning` on the `TestGetUpcoming` block.**
**Cadence:** `docs(design)` (T4-0) → `docs(design)` (T4-0b) → `test(database)` (red) → `feat(database)` (green) → `chore(tracker)` (T4-A roll-up) → `test(app/config)` (red) → `feat(app/config)` (green) → `chore(tracker)` (T4-B roll-up) → `docs(dev-notes)` (gotcha #15). Spec-then-test-then-feat for both A and B; no spec drift mid-implementation.
**Reviewer attitude:** Skeptical. Verify every Streamlit, pandas, and SQLite behaviour claim. Trust `git diff` and the tests, not commit prose. Cross-grep DESIGN against the source for every locked string.

---

## Executive summary

Tier 4 is the largest Phase-4 tier so far (≈1 200 line-deltas, 22 new tests) and arguably the cleanest. The work walks through five interlocking surfaces — DESIGN §5.1 / §5.2 / §8.1, `config.UPCOMING_WINDOW_OPTIONS`, `database.get_upcoming`, the dashboard panel, and gotcha #15 — and at every layer the contract is one unambiguous sentence away. The tests pin the contract row-by-row: every Days-left phrasing branch, every urgency-band boundary (inclusive at both ends), the date-as-`datetime.date` round-trip, the institute-prefix fallback (None *and* empty-string), the sequence-aware Kind cell, the call-time threshold resolution under monkeypatch, and the selectbox→subheader→empty-copy→data-fetch chain via a single AppTest `set_value(60).run()`.

The window-selector mechanic is interesting: the right column defines `selected_window` first, the left column interpolates it into the subheader on the same render. Streamlit's column placement is determined by index, not by execution order, so this works — and the layout test pins it via `proto.weight == 0.5` exclusion to guarantee the panel sits BELOW the funnel/readiness pair, not inside either half.

The review surfaces **zero bugs**, **two 🟡 polish observations**, **two 🟢 future-work items**, and **one ℹ️ carried-forward observation** (the §6 grep miscount in `pages/1_Opportunities.py` first noted in the Tier-3 review). One polish observation cleared inline per GUIDELINES §10's "fix if cheap"; the other documented and deferred as a deliberate stylistic choice.

**Verdict: approve, merge after the inline polish lands.**

---

## Findings

| # | File · Line | Issue | Severity | Status |
|---|-------------|-------|----------|--------|
| 1 | `database.py` : 1265, 1296 | Two `astype(str)` calls on `deadlines["status"]` and `merged["status"]` are no-op casts on object-dtype columns whose values are already `str` — the SQL JOINs + `NOT NULL` `positions.status` + FK CASCADE chain guarantee a non-NaN `str` in every row. Reads as defensive against a state that can't happen. GUIDELINES §12 anti-pattern: *"Catching `Exception` and swallowing silently"* generalised: don't write code for impossible states. | 🟡 polish | Fixed inline (see Q1) |
| 2 | `database.py` : 1244 + 1303 | Tie-break ordering when a deadline and an interview share the same date is documented as *"deadlines before interviews — implicit, not pinned by tests"*. The current behaviour (`pd.concat([deadlines, interviews])` → `sort_values(kind="stable")`) is deterministic by construction, but a future refactor that swaps the concat order would silently flip the order. | 🟡 polish | Kept by design (see Q2) |
| 3 | `database.py` : 1251 / 1272 / 1282 | `get_upcoming` opens **three** separate `_connect()` contexts per call — `get_upcoming_deadlines` → `get_upcoming_interviews` → `get_all_positions` — instead of one. Negligible for the single-user local-SQLite v1; would matter under load or against a remote DB. | 🟢 future | Backlog (see Q3) |
| 4 | `database.py` : 1255 / 1286 | `pd.to_datetime(deadlines["deadline_date"]).dt.date` and the `merged["scheduled_date"]` analog will raise `ValueError` on a non-ISO string. Writers go through `st.date_input.isoformat()`, so non-ISO is unreachable via the UI; a manual SQL edit could trip it. | 🟢 future | Backlog (see Q4) |
| 5 | `pages/1_Opportunities.py` : 395 | The pre-existing `'[APPLIED]'` literal in a docstring-style comment trips the GUIDELINES §6 pre-merge grep. Carried forward from Tier 3; not introduced by Tier 4. The pre-merge grep is a lower-bound check (live calls + comments that document them); the *invariant* (no live status-literal use) holds. | ℹ️ Observation | Carry-over (see Q5) |

---

## Fixes applied in this review

**One fix landed inline:** removed the two no-op `.astype(str)` calls in `database.get_upcoming` (lines 1265 and 1296). Pandas' `pd.read_sql_query` against SQLite TEXT columns produces an object-dtype Series of `str` — the cast was a no-op preserved as defensive belt-and-suspenders. Removing it aligns with GUIDELINES §12 *"Don't add error handling, fallbacks, or validation for scenarios that can't happen"* (also called out in the project-level system prompt) and shaves two lines without changing observable behaviour. All 519 tests still green; no test depended on the cast.

The other 🟡 polish (sort tie-break) is left as-is because the DESIGN comment explicitly accepts the "implicit, not pinned by tests" stance — pinning it now would *narrow* the contract, not maintain it. The 🟢 backlog items and the 🟢 ℹ️ carry-over are out-of-scope for this tier.

---

## Junior-engineer Q&A

### Q1 — The `astype(str)` calls "look defensive" — what's the harm in keeping them?

**A.** Two costs, both small but real.

1. **They lie about the contract.** A reader sees `merged["status"].astype(str)` and reasonably asks: *"What case does this guard?"* The honest answer is: *"None — the JOIN already guarantees `str`."* GUIDELINES §12 names this an anti-pattern for a reason: defensive code that doesn't defend anything teaches future readers to distrust the surrounding invariants. *"If the cast is here, maybe the JOIN doesn't always hit?"* — and now we have to re-derive the FK chain in our heads to convince ourselves it does.

2. **They'd hide a real bug if one ever appeared.** Suppose a future refactor weakens the JOIN (`LEFT JOIN positions` instead of `INNER JOIN`). The merge could then leak NaN. With `astype(str)` in place, the leak shows up to the user as the literal string `"nan"` in the Status column — silently ugly. Without the cast, pandas leaves NaN in place and the page either crashes loudly (good — caught in dev) or `.map(STATUS_LABELS.get)` returns NaN (also caught: the existing `test_status_column_shows_ui_labels_not_raw_sentinels` would flag a NaN cell). Loud failure beats silent garbage.

The fix is the smallest defensible diff:

```python
# before
"status":    deadlines["status"].astype(str),
# after
"status":    deadlines["status"],
```

The same change at line 1296. Two mechanically-equivalent edits. The `TestGetUpcoming` and `TestT4UpcomingTimeline` classes both pass unchanged — the contract was always *"the column carries str values"*, and the JOINs deliver that without help.

(There is one situation where `.astype(str)` would actually do something: if `pd.read_sql_query` ever started returning `numpy.bytes_` on a SQLite TEXT column. It doesn't — verified against pandas 3.0.2 + sqlite3 stdlib, our pinned versions per GUIDELINES §1. If the pinned versions ever drift, the Status-label test would catch it via the `s.startswith("[")` guard.)

### Q2 — Why isn't the deadline-vs-interview tie-break pinned by a test?

**A.** Three readings, weighed:

1. **Strict spec-fidelity.** DESIGN §8.1 says only *"Sort: by date ascending (stable)."* It does not say "deadlines before interviews on tied dates." The implementation chooses one ordering by construction (`pd.concat([deadlines_proj, interviews_proj])` puts deadlines first; `sort_values(kind="stable")` preserves it on ties). A test that pins this would *narrow* the spec — it would assert a behaviour the spec doesn't guarantee.

2. **Future-flexibility.** Imagine a v2 product call: *"on a tied date, show interviews first because they're more time-sensitive."* The right shape of that change is a single-line swap in the `pd.concat` argument order. A pinned tie-break test would force a test edit alongside, but the test's intent is muddier than the spec's: the test would say *"deadlines first"* with no reason recorded.

3. **Defence-in-depth.** A subtle bug class — *"a future refactor swaps the concat order and nobody notices"* — is mitigated by inline source comments at line 1244 (the docstring of `get_upcoming`) and line 1303 (the `kind="stable"` argument), both naming the assumption. A reader stumbling on either spot has the contract on screen.

The carrying weight here is (1). Pinning a behaviour the spec deliberately leaves implicit moves the line of contract. Better to leave the `# implicit, not pinned by tests` comment as the truth and let a future reviewer make a deliberate choice if a v2 ask lands.

### Q3 — Three `_connect()` opens per dashboard render — isn't that wasteful?

**A.** It is. It also doesn't matter today.

The cost in absolute terms: each `_connect()` opens a SQLite handle, runs a `PRAGMA foreign_keys = ON`, runs the query, commits, closes. On a local file with a small (≤ 1 000-row) table, the round-trip is sub-millisecond — call it 0.5 ms each, total ≈ 1.5 ms per dashboard render. The dashboard renders once per Streamlit interaction (any widget change → full script re-run), so this cost lands many times per session, but never on the user's critical path.

The alternative — a single SQL query that `UNION ALL`s the deadline and interview shapes, joins both sides to `positions`, and produces the six-column projection in one round-trip — would shave ≈ 1 ms and cost two things:

1. **A bigger, gnarlier SQL string.** The deadline side selects from `positions`; the interview side selects from `interviews` and joins through `applications` to `positions`. A `UNION ALL` between them needs hand-aligned columns (NULLs padded on either side) and the per-row `kind` literal switches between `'Deadline for application'` and `f'Interview {sequence}'` via a `CASE` expression. Concretely, ≈ 30-line SQL versus the current 6-line + 6-line + 6-line tri-helper composition.

2. **Loss of compositional reuse.** `get_upcoming_deadlines` is also called by `pages/1_Opportunities.py` for the table view (sort by `deadline_date`); `get_upcoming_interviews` is reused for the Next-Interview KPI. Inlining their SQL into a unified query forks the codebase: now there are three near-identical queries with subtly different filter shapes.

For v1 — single-user, local SQLite, ≤ 200 rows realistic — the composition wins on maintainability. For a hypothetical v2 with a remote DB, the unified query is the right move; that's where this finding lives in the backlog.

### Q4 — `pd.to_datetime(...).dt.date` raises on non-ISO. Is that a real risk?

**A.** Not in production paths. Two layers prevent it:

1. **Every UI write path goes through `st.date_input(...)`.** The Quick-add expander, the Overview-tab edit form, and the Applications-page interview list all call `st.date_input(...)`, take `.isoformat()`, and store the result. There is no `st.text_input` storing into a `*_date` column.

2. **Test coverage on the date-shape contract.** `TestGetUpcoming.test_date_column_holds_datetime_date_objects` pins the dtype: every Date cell is a `datetime.date`. A regression that wrote a non-ISO string to `deadline_date` via the API would trip this test on the next CI run.

The risk surface that remains: **a manual SQL edit** (someone opens the SQLite CLI and writes `'04/24/2026'` instead of `'2026-04-24'`). For a personal tracker, this is the user's own foot, the user's own gun.

The safer-but-uglier form would be `pd.to_datetime(..., errors='coerce').dt.date` followed by a `.dropna(subset=['date'])`. The cost: silent row-drops the user can't explain. The benefit: the dashboard doesn't crash on a manually-corrupted DB. For v1 the trade is wrong: a loud crash points the user at a real problem they can fix in a `sqlite3` shell. The current behaviour is correct *for this product*. If we ever expose the tracker to non-author users, this finding promotes from 🟢 to 🟠 and the `errors='coerce'` shape lands.

### Q5 — Why did the §6 grep find a hit in `pages/1_Opportunities.py` if T4 doesn't touch that file?

**A.** It's a carry-over, identical in shape to the Tier-3 finding logged at `reviews/phase-4-Tier3-review.md` Q2.

The grep `grep -nE "\[SAVED\]|\[APPLIED\]|\[INTERVIEW\]" app.py pages/*.py` is a **lower-bound** invariant check. It hits any literal occurrence — code, comment, or docstring. Line 395 of `pages/1_Opportunities.py` reads (as a comment):

```
# ('Applied'), never the raw bracketed storage value ('[APPLIED]').
```

The comment exists *to document* that `'[APPLIED]'` must never appear in a live call — the comment itself is therefore the literal it forbids. Two acceptable resolutions, both also flagged in the Tier-3 review:

- **Tighten the grep** to exclude comment-prefixed lines: `grep -nE "^[^#]*(\[SAVED\]|\[APPLIED\]|\[INTERVIEW\])"`. Drops in cleanly; refines the pre-merge checklist.
- **Hash-out the literal in the comment** via concatenation: `'[' + 'APPLIED' + ']'`. Same readability; the grep lands at zero hits.

Neither is in scope for T4 — the right place to land it is Phase 4 T6's pre-merge sweep, alongside the analogous T2-C `st\.columns\(2\)` grep refinement.

### Q6 — Why does the right column (selectbox) render BEFORE the left column (subheader) in the source order?

**A.** Because the subheader needs `selected_window`, and the only place to get `selected_window` is from the selectbox return value. If the source put the left column first, we'd need either:

- A two-pass dance: render a placeholder subheader, run the selectbox, then go back and update the subheader. Streamlit doesn't natively support post-hoc widget updates without `st.empty()` placeholders.
- A pre-read of `st.session_state["upcoming_window"]` with a default fallback. This works on the second render onward, but on the very first render the key isn't set yet, so we'd need the same `config.UPCOMING_WINDOW_OPTIONS.index(config.DEADLINE_ALERT_DAYS)` fallback duplicated outside the selectbox call.

The current shape sidesteps both: Streamlit's `st.columns([3, 1])` reserves visual slots by index, but `with` blocks execute in source order. So the right column's `with` runs first, defines `selected_window`, and the left column's `with` runs second and reads it. The visual placement is left-to-right (subheader on the left), the execution placement is right-to-left, and they don't have to agree.

A reader landing on this for the first time will be briefly confused — the in-source comment at lines 291–294 of `app.py` names the trick explicitly, which is the right amount of explanation given the unusual idiom.

### Q7 — Why `STATUS_LABELS.get(raw, raw)` (with default) when invariant #3 already guarantees coverage?

**A.** Two complementary defences for the same surface, each catching a different failure class:

- **Invariant #3** (`set(STATUS_VALUES) == set(STATUS_LABELS)`): catches a config-time drift. If a developer adds a new status to `STATUS_VALUES` without adding it to `STATUS_LABELS`, the module fails to import. Static, deterministic, fired at startup.
- **`.get(raw, raw)` default**: catches a runtime-data drift. If a DB row carries a *legacy* status string that is no longer in `STATUS_VALUES` (e.g. the pre-v1.3 `'[OPEN]'` rows that didn't get migrated, perhaps because `init_db()` wasn't run on this DB instance), `STATUS_LABELS[raw]` raises `KeyError` whereas `.get(raw, raw)` shows the raw bracket form to the user — ugly but not crashing.

GUIDELINES §7 endorses this exact pattern by example: *"Selectboxes with an `'All'` passthrough wrap the getter in a lambda so the sentinel renders unchanged: `lambda v: STATUS_LABELS.get(v, v)`."* The dashboard's defensive default has the same flavour: *"never crash on stale data; degrade gracefully to the raw form."*

This is the legitimate counter-example to Q1's "remove defensive casts." The difference: `astype(str)` is no-op for the data shape `pd.read_sql_query` produces, whereas `STATUS_LABELS.get` defends against *user-data* whose shape `init_db()` migrates but doesn't *enforce* (no FK, no check constraint on `status` values).

### Q8 — Gotcha #15 was discovered late in T4-B. Should it have been an A-side discovery?

**A.** No — it's authentic to the wiring step. T4-A's tests run against `database.get_upcoming` directly, returning a real pandas DataFrame; the protobuf serialisation that surprised AppTest never enters the picture. The gotcha is specific to AppTest's view of `st.selectbox.options`, which is a B-side (page-render) concern.

What's worth naming: the discovery cycle was textbook. The test failed once, the worker isolated the cause to AppTest's `.options` exposing the protobuf string form (versus `.value`'s round-trip), patched the assertion to compare against the stringified expected list, and committed the gotcha as `docs(dev-notes)` immediately. The gotcha file's "When a new gotcha lands" footer is followed step-for-step:

1. *Reproduce with an isolation probe* — implicit in the failing assertion's traceback.
2. *Add an entry here with Symptom / Cause / Workaround* — `streamlit-state-gotchas.md` §15.
3. *Reference it in the source comment where the workaround lives* — `test_window_selector_offers_config_window_options` carries the inline note pointing readers at the gotcha for the *why*.
4. *Pin it with a test* — the same test is the pin.

This is the kind of small operational discipline that keeps the project's "discovered but not documented" surface at zero. It's also a good signal for Tier 5 / Tier 6 reviewers: if a Streamlit-version bump in v1.x flips `selectbox.options` back to native types, this test fails specifically and points at gotcha #15 instead of dying in a soup of unrelated AppTest queries.

---

## Observations for Tier 5+ design

Forward-looking, not blocking T4:

1. **`get_upcoming` is the dashboard's single I/O surface for two different domains.** Tier 5's Recommender Alerts panel will follow the same shape: a dedicated `get_pending_recommenders`-derived helper with the same column-renamed-at-page-boundary pattern. The class-constant-driven test style (`SUBHEADER_DEFAULT`, `EMPTY_COPY_DEFAULT`, `DISPLAY_COLUMNS`, `WINDOW_KEY`) sets the template.

2. **The §5.2 invariant pattern (`positive case + drift fires` per invariant) is now template-quality.** Invariant #10 lands the test trio (`test_invariant_10_default_window_in_options`, `test_invariant_10_fires_on_drift`, plus the non-empty/positive-int shape test). Phase 5 / 6 invariants should adopt the same triple.

3. **The window selectbox lives on `st.session_state["upcoming_window"]` for the session.** No test pins persistence across a full reload-from-disk, but Streamlit doesn't promise that anyway — refresh = new session = back to default. If Phase 7 polish ever wants per-user persistence, this is the constant to thread through `st.experimental_user` or a config-side preference store.

4. **The gotcha-#15 quirk hits `selectbox.options` everywhere — including `pages/1_Opportunities.py`'s status filter, which already uses `format_func=STATUS_LABELS.get`.** Existing tests for that filter use `.value` (correct), not `.options` (would fail today). Worth a one-line footnote in the gotchas file pointing future testers at *both* sites.

---

## Verdict

**Approve, merge.**

- All pre-merge checks pass: `pytest tests/ -q` (519 green); `pytest -W error::DeprecationWarning -q` (519 green); GUIDELINES §6 grep clean modulo the one carried-forward comment (Q5); GUIDELINES §1 pin levels honoured (Streamlit 1.56, pandas 3.0.2, plotly 6.7); TDD cadence textbook across both T4-A and T4-B (red → green → tracker).
- One 🟡 polish landed inline (the no-op `.astype(str)` removal); one 🟡 polish kept-by-design with a documented rationale; two 🟢 future items logged for the v2 design notes; one ℹ️ observation deferred to the Phase 4 T6 pre-merge sweep.
- The work demonstrably benefits from the conductor pattern's *spec-first* ordering: T4-0 + T4-0b locked the §8.1 column contract before any test ran, so T4-A's tests and T4-B's tests bound to the same unambiguous specification — no "what does the spec actually mean here?" cycles mid-implementation. This is the lesson the prior T4 attempt pre-empted.
- Gotcha #15 captured in real time and pinned with a regression test. The gotcha-file workflow is now self-perpetuating.

**Merge sequence:** push branch → open PR → reviewer scan → squash-merge → tag `v0.4.1` (or roll into `v0.5.0` after T5 + T6 ship per the TASKS.md sprint plan) → update `memory/project_state.md` to reflect Phase 4 T4 shipped.

---

_Review by skeptical-reviewer session, 2026-04-29._
