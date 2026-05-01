# Phase 5 — Tier 2 Code Review

**Branch:** `feature/phase-5-tier2-ApplicationDetailCard` (6 commits ahead of `main`; T1 merged via PR #15 → `aebbb8b`)
**Verdict:** Approve, merge after the inline test-logic fix lands.
**Scope:** T2 — Application detail card on `pages/2_Applications.py`. Two sub-tasks:
  1. **T2-A** (3 commits) — Selection plumbing + bordered detail-card container + `apps_detail_form` (8 widgets) + Save handler that calls `database.upsert_application(propagate_status=True)`. Mirrors Opportunities §8.2 with a deliberate asymmetry at the empty-filter site (selection survives a filter narrowing because the card resolves against the unfiltered `df`).
  2. **T2-B** (3 commits) — Cascade-promotion toast surfacing. Save handler reads `result["status_changed"]` and fires a second `st.toast(f"Promoted to {STATUS_LABELS[new_status]}.")` after the Saved toast whenever R1 / R3 actually fired. Cohesion sweep covers the remaining date-widget NaN-pre-seed and the cross-widget-type save-error preserve-values gap.
**Stats:** `pages/2_Applications.py` +331 / -12 (the detail card + helpers + comments — file 168 → 517 lines, ≈3× growth on T1's shell). `tests/test_applications_page.py` +1 208 (file went from 466 to 1 598 lines). 7 new test classes (`TestApplicationsTableColumnConfig`, `TestApplicationsTableSelection`, `TestApplicationsDetailCardRender`, `TestApplicationsDetailCardForm`, `TestApplicationsDetailCardSave`, `TestApplicationsCascadePromotionToast`, `TestApplicationsCohesionSweep`) carrying ≈ 52 cases (43 in T2-A + 9 in T2-B). `CHANGELOG.md` +229; `TASKS.md` +164. **586 → 638 tests passing under both `pytest -q` and `pytest -W error::DeprecationWarning -q`** (+52 net).
**Cadence:** Two TDD rounds, three commits each — `test:` red → `feat:` green → `chore:` rollup. T2-A and T2-B each shipped as one logical unit. Six commits total; no spec drift between sub-tasks; the Sonnet plan critique reshaped the original 3-sub-task split (selection plumbing alone) into 2 sub-tasks (plumbing + form bundled).
**Reviewer attitude:** Skeptical. Verify every cascade claim against `database.upsert_application`'s contract; cross-check that the page never renders a raw `[APPLIED]` sentinel; verify that the asymmetry-vs-Opportunities §8.2 contract at the empty-filter site is locked at three layers (DESIGN §8.3 prose, page comment, dedicated test).

---

## Executive summary

T2 is the densest Phase-5 surface so far — the editable Application detail card with R1/R3 cascade-promotion surfacing — and the test class is in step: 52 cases pin every editable widget (per-widget round-trip), every pre-seed branch (NULL / value / NaN), every cascade path (R1-only, R3-only, R1+R3 chained, terminal-guard no-op), every empty-state, every selection life-cycle event (select, deselect, skip-table-reset one-shot, filter narrowing), and every Save-error preservation invariant. The page mirrors Opportunities §8.2's edit-panel architecture without the recommendations from Sub-task 13's reverted radio-tab experiment (no conditional widget rendering; the form lives in one container; the pre-seed gate is the same `_<page>_edit_form_sid` sentinel pattern that survives gotcha #2).

The deliberate asymmetry-vs-Opportunities §8.2 — Applications keeps selection on `df_filtered.empty`, Opportunities pops it — is locked at three layers (DESIGN §8.3 prose, an inline comment at the empty-filter site, a dedicated `test_filter_narrowing_does_not_clear_selection` test) so a future maintainer cannot copy-paste the Opportunities pop-on-empty branch into the Applications page without tripping a test. The cascade-promotion contract trusts `database.upsert_application`'s `(status_changed, new_status)` invariant — no defensive `and result.get("new_status")` guard, per the Sonnet plan critique recorded in the CHANGELOG; a contract violation would surface as a `KeyError` exactly where the bug lives, rather than being silently swallowed.

The review surfaces **one 🟠 test-logic bug fixed inline** (a `any(...not in...)` tautology that doesn't actually catch the failure mode it claims to guard against), **two 🟡 polish kept-by-design** (a redundant `or 0` defensive branch on the confirmation-received bool coercion; a `pd.isna(received)` guard on an INTEGER-typed column that the schema migration prevents from going NULL), **two 🟢 future-work items** (per-render `database.get_application(sid)` query without sid-keyed caching; stale-selection if the selected position is deleted by another tab), and **one ℹ️ carried-forward observation** (the §6 grep miscount at `pages/1_Opportunities.py:395`, fifth tier in a row).

**Verdict: approve, merge after the inline test-logic fix lands.**

---

## Findings

| # | File · Line | Issue | Severity | Status |
|---|-------------|-------|----------|--------|
| 1 | `tests/test_applications_page.py` lines 1437–1443 (`test_r1_plus_r3_chained_promotes_saved_to_offer`) | The assertion `assert any(self._promo_toast_text(config.STATUS_APPLIED) not in v for v in toast_values)` is a tautology — `any(... not in ...)` evaluates True whenever ANY single toast doesn't contain the substring, which is satisfied vacuously by the Saved toast and the final OFFER toast even when an intermediate "Promoted to Applied" toast IS present. The test would pass under exactly the regression it's meant to catch (a page that fires multiple promotion toasts during R1+R3 chained cascades). The intended logic is `all(... not in ...)` or equivalently `not any(... in ...)`. | 🟠 drift | **Fixed inline** (see Q1) |
| 2 | `pages/2_Applications.py` line 381 (pre-seed) | `bool(app_row.get("confirmation_received") or 0)` includes a redundant `or 0` — `bool(None)` is already `False`, `bool(0)` is `False`, `bool(1)` is `True`. The `or 0` defends against an impossible state (the schema's `confirmation_received INTEGER DEFAULT 0` plus the ALTER-with-DEFAULT migration in Sub-task 10 prevents NULL from arising), and falls under the GUIDELINES §12 anti-pattern *"don't add fallbacks for scenarios that can't happen"* — same shape as the T4 `.astype(str)` and T5 `str(_name)` removed in earlier reviews. | 🟡 polish | Kept by design (see Q2) |
| 3 | `pages/2_Applications.py` line 122 (`_format_confirmation`) | `pd.isna(received)` in the table-render formatter defends against a NaN value that the schema migration explicitly prevents. INTEGER columns with `DEFAULT 0` and ALTER-with-DEFAULT migrations cannot produce NaN unless a legacy DB write inserted NULL directly; pandas reads INTEGER as int64 (no NaN possible) when every row has a value, falling back to float64 only when at least one row is NULL. Defensive against a near-impossible state. | 🟡 polish | Kept by design (see Q3) |
| 4 | `pages/2_Applications.py` line 322 + line 339 | `database.get_application(sid)` runs on every render the user has a selection — including renders where `sid` hasn't changed (filter changes, in-flight typing). The pre-seed gate skips re-seeding on same-sid renders, but the SQL query itself is unconditional. For the v1 single-user local SQLite path the cost is negligible; for any future multi-user / remote-DB path this becomes a per-render N+1 in disguise. | 🟢 future | Backlog (see Q4) |
| 5 | `pages/2_Applications.py` lines 309–322 (selection resolution) | If the user has a position selected and that position is deleted via the Opportunities page (in a parallel browser tab), the next Applications-page render keeps `applications_selected_position_id` in session_state, the page hits `selected_row.empty == True`, and the detail card silently does not render. The selection key is left dangling. Rare in practice (the project ships single-tab) but worth a sentinel pop on `selected_row.empty`. | 🟢 future | Backlog (see Q5) |
| 6 | `pages/1_Opportunities.py:395` (pre-existing) | The pre-existing `'[APPLIED]'` literal in a comment trips the GUIDELINES §6 status-literal grep. Same shape as T3 / T4 / T5 / T6 reviews — fifth tier in a row. The Phase 4 finish review committed to landing the `rg -v '^\s*#'` grep amendment; that commit hasn't shipped yet. Carry-over, not introduced by T2. | ℹ️ Observation | Carry-over (see Q6) |

---

## Fixes applied in this review

**One fix landed inline:**

`tests/test_applications_page.py` — fix the `test_r1_plus_r3_chained_promotes_saved_to_offer` assertion logic from `any(... not in ...)` (tautology) to `all(... not in ...)` (catches the regression). Empirically verified the existing form is broken: under `toast_values = ["Saved …", "Promoted to Applied", "Promoted to Offer"]`, `any(intermediate not in v for v in toast_values)` returns `True` (the Saved toast doesn't contain "Promoted to Applied", so the existential is satisfied), even though the test should fail because the intermediate toast IS present. The corrected `all(intermediate not in v for v in toast_values)` returns `False` in the same scenario, which fails the assertion as intended.

The other 🟡 / 🟢 / ℹ️ findings are documented and deferred. Two of them (#2 and #3) follow the pattern that prior reviews removed inline (T4's `.astype(str)`, T5's `str(_name)`) but the cost-benefit here is closer than those cases — the `or 0` and `pd.isna` patterns each guard a specific failure shape that, while currently unreachable, is one schema migration away from being possible. Documented for the eventual cleanup tier (TASKS.md C2 family).

---

## Junior-engineer Q&A

### Q1 — How can a test that "passes" actually be broken? Doesn't a green build mean the test works?

**A.** Green means the test's *current expression* evaluates True against the current code. It does not mean the expression catches the regressions the test's *docstring* claims it catches. Tautologies are the most common form of this mismatch.

The specific bug:

```python
# Original (broken):
assert any(
    self._promo_toast_text(config.STATUS_APPLIED) not in v
    for v in toast_values
), (
    "Chained cascade must NOT surface an intermediate "
    "'Promoted to Applied' toast — only the post-state."
)
```

Read the predicate carefully: `any(intermediate_text not in v for v in toast_values)` evaluates True if **at least one** toast doesn't contain the intermediate text. Three cases on a populated chain:

| Toasts | `any(NOT IN)` | Test |
|--------|---------------|------|
| `["Saved", "Promoted to Offer"]` (correct case) | True (both don't contain it) | passes (intended) |
| `["Saved", "Promoted to Applied", "Promoted to Offer"]` (regression: intermediate present) | True (Saved + Offer toasts both don't contain it) | **passes (BUG)** |
| `["Promoted to Applied", "Promoted to Applied"]` (every toast contains it) | False | fails |

The third row is the only failure mode the broken expression actually catches — and it's a degenerate case the page can't produce. The intended-failure-mode (row 2) sails through.

The fix:

```python
# Corrected:
assert all(
    self._promo_toast_text(config.STATUS_APPLIED) not in v
    for v in toast_values
), (
    "Chained cascade must NOT surface an intermediate "
    "'Promoted to Applied' toast — only the post-state."
)
```

`all(intermediate_text not in v for v in toast_values)` evaluates True only when **every** toast lacks the substring — which is exactly the contract the docstring promises.

The same bug pattern exists in many real-world test suites, almost always in *negation tests* (assertions of the form "X must not happen"). The mental model that catches them at code-review time: when you see `assert not X` or `assert any(... not in ...)`, mentally rewrite the condition to its positive form (`all(... not in ...)` or `not any(... in ...)`) and ask if those mean the same thing. They usually don't.

This finding does not invalidate the test's other assertions (the OFFER toast presence + DB probe at the end both work correctly), and the DB probe (`post_status == config.STATUS_OFFER`) provides independent coverage of the chain's correctness. So the test wasn't *useless* — just over-claiming. With the fix, it now catches what it advertises.

### Q2 — Should the redundant `or 0` defensive branch be removed inline like the T4 `.astype(str)` and T5 `str(_name)` were?

**A.** Tempting, but the cost-benefit is closer here than in the prior cases.

The expression:

```python
"apps_confirmation_received": bool(app_row.get("confirmation_received") or 0),
```

Three values can land at this line:
- `0` (default, fresh row): `0 or 0` = `0` → `bool(0)` = `False`. ✓
- `1` (confirmed): `1 or 0` = `1` → `bool(1)` = `True`. ✓
- `None` (impossible-by-schema, but theoretically possible if a row pre-dates the Sub-task 10 migration with no DEFAULT applied): `None or 0` = `0` → `bool(0)` = `False`. ✓

The `or 0` only matters in the third case. Without it: `bool(None)` = `False` — same outcome. So the `or 0` is mechanically redundant.

Now compare to the T4 `.astype(str)` removal:

| | T4 `.astype(str)` | T2 `or 0` |
|---|---|---|
| Failure shape it defends against | Pandas dtype churn (impossible in pinned pandas 3.0.2) | NULL in `confirmation_received` (impossible by schema DEFAULT + migration) |
| Cost of being wrong | Status column shows literal `"nan"` | Checkbox shows `False` (correct value!) |
| Anti-pattern signal | Strong — defended against impossible | Mild — same outcome with or without |
| Self-documenting value | Low — cast doesn't hint at WHY | Low — same |

The key asymmetry: removing T4's `.astype(str)` *changed the failure mode* from "silent literal nan" to "loud NaN" if the JOIN ever weakened. Removing T2's `or 0` doesn't change anything — `bool(None)` is `False` regardless of the path.

So the change here would be cosmetic, not structural. GUIDELINES §12 *"don't add fallbacks for scenarios that can't happen"* applies, but the cost (one-line edit, churn in a tier already at 638 tests) doesn't pay for itself when removal doesn't strengthen the failure-mode story. Documented for the cleanup tier; deferred.

(Same reasoning applies to Finding #3, the `pd.isna(received)` guard. The migration prevents NaN; pandas dtype handling for INTEGER columns prevents NaN; removal doesn't change observable behaviour. Documented; deferred.)

### Q3 — Why does the page issue a SECOND `database.get_application(sid)` query when it already has the row from `get_applications_table()`?

**A.** Because `get_applications_table()` is a 10-column projection contract (per T1-A) and the form needs three columns it doesn't expose: `response_date`, `result_notify_date`, `notes`.

The two readers:

| Reader | Purpose | Columns |
|---|---|---|
| `get_applications_table()` (T1-A) | Drives the table | `position_id, position_name, institute, deadline_date, status, applied_date, confirmation_received, confirmation_date, response_type, result` (10 cols) |
| `get_application(pid)` (Phase-2 helper) | Single-application read | `SELECT * FROM applications WHERE position_id = ?` (full applications row including the three the table doesn't surface) |

Three options for the form pre-seed:

1. **Widen `get_applications_table()` to 13 columns.** The T1-A 10-column contract is pinned by `TestApplicationsPageTable` (at least 200 lines of tests) and DESIGN §8.3 + the merged review doc. Widening would force re-pinning every test that asserts column count, plus a DESIGN amendment. High blast radius.
2. **Issue a per-render second query** (current choice). One extra SELECT per render with a selection. For local SQLite + 10–100 rows, sub-millisecond cost; 0 lines of contract churn.
3. **Cache the second query in session_state keyed by sid.** Adds a sentinel + invalidation logic; 5–10 lines of code; saves the second query when the user types into the form (selectbox is unchanged). Premature for v1.

Option 2 is the right choice for v1. Option 3 is the right choice if the dataset ever grows or the dashboard adds a real-time refresh poll. The 🟢 future entry in the findings table marks the moment the cost-benefit will flip.

(There's a small variant of (3) worth naming: cache `app_row` *only* across the same-sid pre-seed window, then drop on row change. The pre-seed gate already keys on sid, so the cache could ride the same gate. Defer to the cleanup tier.)

### Q4 — Why is the asymmetry vs. Opportunities §8.2 (filter narrowing keeps selection on Applications, drops it on Opportunities) the right design?

**A.** Because the *user mental model* differs between the two pages.

Opportunities is a list-of-positions page where the user comes to add / edit / delete positions. The filter bar is a way to find the right row to edit; if the user filters, then narrows past their current selection, the user has signalled "I'm done with that one — show me others." Popping selection matches that signal.

Applications is a workflow-progress page where the user comes to update an application's status. The user might select a position, start typing into the Notes text_area, then narrow the filter to "only Interview-stage" to glance at the bigger picture, then return to the original row. Popping selection on filter narrowing would *destroy in-flight work* — the form would collapse, the user would have to re-select, and the typed-but-not-saved Notes text would vanish (because the post-collapse re-render would re-seed from DB).

The DESIGN amendment locks the asymmetry at three layers:

1. **DESIGN §8.3 prose**: *"the detail card resolves against the unfiltered df, so a filter narrowing that excludes the selected row keeps the in-progress edit visible."*
2. **Page comment** at the empty-filter site (lines 218–223): *"Asymmetry vs. Opportunities §8.2: do NOT pop applications_selected_position_id here."*
3. **Dedicated test** (`test_filter_narrowing_does_not_clear_selection`): seeds a Visible/APPLIED row, narrows filter to STATUS_INTERVIEW (no rows match), and asserts the selection key survives.

A future maintainer copy-pasting the Opportunities `pop_on_empty` branch will trip the test before they read the comment.

There's a subtler reason this asymmetry is *load-bearing for T3*. T3 plans an `apps_interviews_form` as a sibling to the detail-card form inside the same `st.container(border=True)`. The interview list will track `interview_id` in widget keys (`apps_interview_{id}_*`), so the form is even *more* fragile to a filter-narrowing-induced re-render than the detail card alone. T2-A locks the asymmetry now so T3 inherits a stable contract.

### Q5 — Why isn't the stale-selection edge case (selected position deleted by another tab) a 🟠 drift instead of 🟢 future?

**A.** Three reasons that align it with backlog rather than block-merge:

1. **The product's deployment model is single-user, single-tab.** The README + DESIGN explicitly position the tracker as a desktop-local Streamlit run; multi-tab Streamlit is unusual on this app because the cross-tab sync story is fundamentally a Streamlit limitation (Streamlit reruns are isolated per session; cross-tab shared state requires the database to be the single source of truth, which it already is, but session_state isn't reactive across tabs). A user who opens two tabs and deletes from one is exercising a use case the product doesn't promise.

2. **The failure mode is silent-empty, not silent-wrong.** When the selected position is deleted, `selected_row = df[df["position_id"] == sid]` returns an empty DataFrame, and the `if not selected_row.empty:` guard suppresses the entire detail-card render. The user sees the table without a card — which is the same UI state as "no row selected." There's no data corruption, no stale write, no incorrect cascade — just a missing card.

3. **The cleanup is straightforward when needed.** A single `else: st.session_state.pop("applications_selected_position_id", None)` after the if-not-empty block clears the dangling selection on the next render. Sub-3-line change; could land alongside any other deletion-aware affordance (e.g., a Delete button on the Applications detail card, which is currently missing — Phase 5's plan defers Delete to Opportunities only).

The 🟢 categorisation matches the project's pattern for *"latent UX edge case in a single-user product, fix when it surfaces"*. If the project ever adds multi-user mode (post-v1.0), this finding promotes to 🟠 alongside several other multi-tab assumptions.

### Q6 — Why is the §6 grep carry-over still tripping in five reviews?

**A.** Because the grep itself over-matches; the source code is clean.

The hit:

```python
# pages/1_Opportunities.py:395
# ('Applied'), never the raw bracketed storage value ('[APPLIED]').
```

This is a comment that documents the rule it's flagging — the `'[APPLIED]'` literal exists only as a description of what NOT to do. The pre-merge grep is `grep -nE "\[SAVED\]|\[APPLIED\]|\[INTERVIEW\]" app.py pages/*.py` per GUIDELINES §11; it doesn't distinguish code from comments.

The Phase 4 finish review committed to landing the resolution alongside the close-out work. The current state: the toggle polish + cohesion smoke landed on the Phase 4 T6 branch; the grep amendment (`rg -v '^\s*#'` on the pre-merge checklist) is the third T6 sub-task, which merged before this T2 work. Why the hit still surfaces here:

- The amendment lives in GUIDELINES §11 (the pre-commit checklist) but the grep is also inline-documented on the project_state.md *"Open carry-overs > Grep→rg"* line.
- The actual command in CI (if/when CI exists) hasn't been retrofitted yet.
- The hit serves as a recurring conversation prompt for landing the amendment.

This T2 review is the fifth tier review to flag it (T3 / T4 / T5 / T6 / T2). The right action remains: tighten the grep (one-line edit to GUIDELINES §11 + any CI script), or rephrase the comment to use string concatenation (`'[' + 'APPLIED' + ']'`). Neither has shipped. Defer to the eventual `reviews/phase-5-finish-review.md` or the closer of any cleanup tier.

### Q7 — The R1+R3 chained test asserts BOTH the toast AND a DB probe. Why both? Won't the toast text suffice?

**A.** Because the toast text proves the *endpoint* of the cascade chain, not the *path* taken to reach it.

`upsert_application(propagate_status=True)` returns `{"status_changed": bool, "new_status": str | None}`. The page reads `result["new_status"]` and renders a toast for that value. So a toast saying "Promoted to Offer" tells you the FINAL state was OFFER — but it doesn't tell you whether R1 actually fired (taking SAVED → APPLIED) before R3 took it the rest of the way (APPLIED → OFFER).

Three ways the chain could be broken:

| Failure mode | Final state | Toast | Endpoint test passes? | DB probe catches? |
|---|---|---|---|---|
| Correct: R1 then R3 | OFFER | "Promoted to Offer" | ✓ | ✓ (status == OFFER) |
| Hypothetical: R3 stalls because pre-state SAVED ∉ TERMINAL_STATUSES check fails | APPLIED | "Promoted to Applied" | fails (toast diff) | ✓ (status != OFFER) |
| Hypothetical: R1 stalls; R3 fires from SAVED directly | OFFER | "Promoted to Offer" | passes (toast match) | ? |
| Hypothetical: R3 doesn't fire; R1 stops at APPLIED | APPLIED | "Promoted to Applied" | fails | fails |

The interesting row is the third — a regression where R1 silently doesn't fire but R3 picks up SAVED → OFFER directly. The toast assertion would pass (the endpoint is correct). The DB probe would also pass (the endpoint is OFFER). But the chain didn't actually run as designed: R1's transitional behaviour is broken.

In practice, today's `upsert_application` doesn't allow this — R1 is gated on `pre_status == STATUS_SAVED` and updates to STATUS_APPLIED, then R3 is gated on `pre_status NOT IN TERMINAL` (STATUS_APPLIED is not terminal) and updates to STATUS_OFFER. They run in lexical order inside the transaction. So row-3 is structurally impossible.

But the test pair (toast + DB probe) is *defensive* against future refactors that might rearrange the cascade order or change the gates. The Sonnet plan-review signal recorded in the CHANGELOG explicitly called for this: *"the toast alone proves the endpoint, not the chain; only the DB probe disambiguates 'R3 stalled' from 'R3 chained correctly'."* The DB probe is the witness that the *path* through the cascade was R1 → R3, not "R3 alone." The fixed `all(...)` assertion (per Finding #1) closes the related "no intermediate Applied toast" check that was previously a tautology.

### Q8 — The detail-card subheader uses `f"{label} · {status_label}"` (with the `·` separator). Why not the same status-label idiom as Opportunities' table cell (where status is its own column)?

**A.** Because the two surfaces are answering different reader questions.

The Opportunities table is a *list view* — the user is scanning across rows. Status is a per-row attribute and gets its own column so the user can sort / filter / compare across rows. Each cell shows just the label (`"Applied"`, `"Saved"`, etc.).

The Applications detail card is a *single-row view* — the user has selected one position and is now examining it in detail. The status is metadata about *this one position*, and presenting it as a separate column would split the reader's attention. The midpoint dot (`·`) is the project's idiomatic "subordinate metadata" separator (also used by the Next-Interview KPI: `f"{Mon D} · {institute}"`); putting `status_label` after the dot is the visual grammar for "additional context about this entity."

The header `"MIT: Postdoc Slot · Applied"` reads in one mental sweep: this is the MIT Postdoc Slot, which is in the Applied stage. Splitting it into two lines (subheader + caption, or two subheaders) would imply a hierarchy the data doesn't have.

The choice is locked by tests (`test_card_header_includes_position_and_status`, `test_card_header_uses_label_not_raw_status`) so a future maintainer can't reformat to a different shape without explicit intent. The tests pin the *components* (institute / position_name / STATUS_LABELS[raw]) but not the separator — a maintainer who wants to swap `·` for `—` only has to convince themselves and a test reviewer; the spec stays at the component level.

### Q9 — Why does the page trust `database.upsert_application`'s `(status_changed, new_status)` contract without a defensive guard?

**A.** Because the contract is the contract, and a defensive guard would *hide* future violations rather than surface them.

The contract (from `database.upsert_application`'s docstring + the implementation):

```
Returns {"status_changed": bool, "new_status": str | None}.
status_changed compares the STATUS STRING pre vs post, not whether an
UPDATE executed — so the STATUS_OFFER self-assignment that happens when
R3 re-fires on an already-OFFER row is correctly reported as "no change".
```

Translation: when `status_changed=True`, `new_status` is the post-state status STRING — non-None and a valid `STATUS_VALUES` member. When `status_changed=False`, `new_status` is `None`.

The page reads:

```python
if result["status_changed"]:
    promo_label = config.STATUS_LABELS.get(
        result["new_status"], result["new_status"]
    )
    st.toast(f"Promoted to {promo_label}.")
```

A defensive variant might guard: `if result["status_changed"] and result.get("new_status"):`. This is exactly the anti-pattern GUIDELINES §12 names. Three problems:

1. **It hides contract violations.** If a future refactor accidentally returns `{"status_changed": True, "new_status": None}` (e.g., a refactor that moves the post-state read but forgets to update the indicator), the defensive guard silently swallows the toast — the user sees a Saved toast, the cascade *did* fire (DB row promoted), but no promotion toast surfaces. A bug that should fire loudly hides as a missing toast.

2. **It blurs which side of the contract the reader trusts.** The page already `STATUS_LABELS.get(..., raw)` passthrough as a defensive *display* fallback (so an unmapped status renders as the raw value rather than crashing). That's defense at the rendering layer. Adding another defense at the contract layer would imply *neither* layer is authoritative — a maintainer reading the code would have to figure out which check is the "real" one.

3. **The fallback is unreachable in practice.** Config invariant #3 (`set(STATUS_VALUES) == set(STATUS_LABELS)`) plus the upsert contract together guarantee the `STATUS_LABELS.get(...)` lookup never falls through to its default. The `.get` is for legacy DBs that might carry an unmigrated status; the contract guarantees `new_status` is a current-vocabulary member.

The Sonnet plan-review signal recorded in the CHANGELOG made this explicit: *"trust the upsert contract; a violation surfaces loudly via KeyError rather than silently skipping the toast."* The CHANGELOG also notes the inline comment near the fields-dict construction reminds future maintainers of the 8-key invariant — *every editable widget contributes a key, so the empty-fields early-return path is unreachable*. The whole stack is designed to fail loud, not fail silent.

### Q10 — The "All recs submitted" line uses `database.is_all_recs_submitted(sid)` for the second time on each render. Why not pass the value through from the table?

**A.** Because the table renders `df_filtered` (which may exclude the selected row) and the detail card resolves against `df` (the unfiltered set). Passing through would force re-introducing a filter-aware lookup at the card.

The flow:

1. **Table render** (line 238): `df_filtered["position_id"].apply(lambda pid: ...)`. Computes `is_all_recs_submitted` per visible row.
2. **Detail card resolution** (line 311): `df[df["position_id"] == sid]` — uses the *unfiltered* df so the asymmetry from Q4 holds.
3. **Detail card recs glyph** (line 339): `database.is_all_recs_submitted(sid)` — runs the helper a second time.

If we wanted to avoid the second SQL call, the choices are:

- **Cache it on the row passed through.** But the row comes from `df` (unfiltered), and `df` doesn't carry `is_all_recs_submitted` (the table render computes it on `df_filtered` post-filter). Threading the value through would require widening `get_applications_table()` to include the boolean — same blast radius as Q3.
- **Cache it in session_state keyed by sid.** Same shape as Q3's caching proposal; same trade-off.
- **Inline the COUNT(*) query at the page layer.** Bypasses the helper; violates GUIDELINES §1 *"page files have no raw SQL."*

For v1's local single-user SQLite path, two `is_all_recs_submitted` calls per render is sub-millisecond; it's the right cost for the right contract. The cleanup tier could land an `is_all_recs_submitted_bulk(position_ids: list[int])` reader that returns a dict-keyed subset, and both call sites would consume from it — but that's a Phase 5 / 6 polish.

---

## Observations for Tier 3+ design

Forward-looking, not blocking T2:

1. **The `st.container(border=True)` wraps both the form AND the inline "All recs submitted" line.** T3's `apps_interviews_form` will be a sibling form INSIDE the same container, above the detail form (DESIGN §8.3 D-B). T2's structure is architected for this — but a future maintainer adding a third widget directly inside the container (e.g., a position-summary panel) without making it a form will create a layout where the order of children implicitly matters but isn't documented. Recommend a comment block at the container open declaring the child order contract before T3 lands.

2. **The 8-widget invariant** is documented in a single comment near the Save handler. T3 will introduce two more interaction surfaces (the inline interview list + the Add-another-interview button) that need their own invariants. The pattern of *"one comment block per form, naming the editable-widget count and what changes when fields change"* should generalise — perhaps a section header above each form scoping the contract.

3. **The cohesion sweep parametrize** (`test_null_date_field_preseeds_to_none` over 4 widgets) is the right shape for the date-input subset. T3 will introduce per-row date inputs (`apps_interview_{id}_date`) where the row identity is dynamic — the parametrize pattern needs a row-keyed seed helper. Recommend adapting the T6 `_chart_bucket_count` helper precedent (a test-class method rather than module-level fixture) so each row's pre-seed assertion has its own assertion message including the interview_id.

4. **The `_keep_selection` / `_select_row` / `_deselect_row` helpers** at the top of `tests/test_applications_page.py` are duplicates of the same helpers in `tests/test_opportunities_page.py`. The two pages both use selectable dataframes with `apps_table` / `positions_table` keys. T3 will introduce a third selectable surface (the per-interview selection state, scoped by interview_id rather than position_id). At three call sites, promoting the helpers to a shared `tests/helpers/_selection.py` module is the right cleanup. Defer to T3 entry.

5. **The CHANGELOG entry's "8-key invariant" inline note** is the kind of cross-cutting contract that benefits from a pin in DESIGN §8.3. Currently the contract lives in a comment + the fields-dict shape; a future maintainer who renames a widget or adds a ninth would not know the implicit contract. Recommend a sentence in DESIGN §8.3: *"The detail-card form's `fields` dict carries exactly N keys, where N equals the number of editable widgets in the form. Adding a widget without adding a key (or vice versa) silently breaks the upsert contract's `status_changed` semantics."*

---

## Verdict

**Approve, merge.**

- All pre-merge checks pass: `pytest tests/ -q` (638 green); `pytest -W error::DeprecationWarning -q` (638 green); pinned-version floors per GUIDELINES §1 honoured; the 6-commit TDD cadence preserved across both T2-A and T2-B sub-tasks.
- One 🟠 test-logic bug fixed inline (the `any(...not in...)` tautology in `test_r1_plus_r3_chained_promotes_saved_to_offer`); two 🟡 polish kept-by-design with rationale (defensive `or 0` and `pd.isna` patterns that don't strengthen failure-mode story when removed); two 🟢 future items logged for the cleanup tier or post-v1; one ℹ️ observation — the §6 grep carry-over now on its fifth review — to land in the publish-phase doc-drift sweep.
- The work resolves Phase 5 T2's full DESIGN §8.3 contract — Applied / Confirmation (per D-A glyph + tooltip rules) / Response / Result / Notes — and surfaces R1 / R3 cascade promotions (DESIGN §9.3) without any new database.py surface; the page is a pure presentation reuse of helpers shipping since Phase 2. The 52-test class pins every editable widget, every cascade path, every empty-state branch, and every selection life-cycle event.
- The deliberate asymmetry-vs-Opportunities §8.2 at the empty-filter site is locked at three layers (DESIGN §8.3 prose + page comment + dedicated test) so a future Streamlit / Phase rework cannot regress to a uniform pop-on-empty behaviour without explicit intent.

**Merge sequence:** push branch → open PR → reviewer scan → squash-merge → continue to T3 (inline interview list UI) on a fresh branch.

---

_Review by skeptical-reviewer session, 2026-04-30._
