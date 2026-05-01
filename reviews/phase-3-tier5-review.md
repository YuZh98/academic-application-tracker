# Phase 3 — Tier 5 Code Review

**Branch:** `feature/phase-3-tier5` (14 commits ahead of `main`)
**Scope:** T5-A (Overview Save) + T5-B (Requirements Save) + T5-C (Materials Save) + T5-D (Notes Save) + T5-E (Overview Delete with `@st.dialog`)
**Stats:** `pages/1_Opportunities.py` +~300 lines; `tests/test_opportunities_page.py` +~1000 lines; 220 tests passing (was 147 at end of Tier 3); 0 deprecation warnings.
**Verdict:** Request changes → approved after Fix #1 and Fix #2 (both landed in this review).
**Reviewer attitude:** Skeptical. Trust nothing. Propose failure modes. Question the obvious.

---

## Executive summary

Tier 5 lands four write paths (one per edit-panel tab) plus a destructive delete dialog that honours the FK cascade contract. The work is well-tested (74 new AppTest cases), comments the rationale rigorously, and reuses the T4 patterns (paired session-state cleanup, `_edit_form_sid` sentinel, F2-style coercion, config-drive).

The review surfaces **two real bugs** (one user-harmful, one UX surprise) worth fixing before merge, a handful of design observations that look correct on second thought, and sets of follow-up test-coverage recommendations. No security, performance, or data-integrity defects were found.

---

## Findings

| # | File · Line | Issue | Severity | Status |
|---|-------------|-------|----------|--------|
| 1 | `pages/1_Opportunities.py` : 50, 66 | `_confirm_delete_dialog` passes `position_id=None` to `database.delete_position` when session-state key is missing — SQLite `WHERE id = NULL` matches no rows, but the success toast still fires. Not reachable via the current UI (the elif re-open requires `_delete_target_id == sid`), but cheap defensive insurance against future refactors. | 🟡 Moderate (downgraded after confirming unreachability; guard retained as defense-in-depth) | **Fix applied (guard + friendly error)** |
| 2 | `pages/1_Opportunities.py` : 475 | "Phantom dialog": if the user dismisses the dialog via the X / Escape (no `_delete_target_*` cleanup), then later re-selects the same row, the elif re-opens the dialog with no user action. | 🟡 Moderate | **Fix applied** (clears stale target on row-change; X-dismiss-then-same-row is a Streamlit-framework limitation documented below) |
| 3 | `pages/1_Opportunities.py` : 408–452 / 505–520 / 554–571 / 600–611 | The four Save handlers share a repeated `payload / try / update_position / toast / pop / flag / rerun / except` skeleton. DRY cleanup considered. | 🟢 Minor | Rejected — extraction hurts cohesion (see Q4 below) |
| 4 | `tests/test_opportunities_page.py` : `TestDeleteAction` | Missing: selection-change-while-dialog-pending clears state; rapid-re-click Delete resets target cleanly. | 🟡 Moderate | **Added regression tests** |
| 5 | `pages/1_Opportunities.py` : 63, 79 | `st.button(width="stretch")` — new in Streamlit 1.49, valid in our 1.56. | 🟢 Minor | Verified (no-op) |
| 6 | `database.py` : `delete_position` | Accepts `None` and silently no-ops. Informational — the fix in #1 happens at the call-site (page) but a defensive `TypeError` in the data layer would be cleaner. | ℹ️ Observation | Deferred — page-layer guard is sufficient for now; documented for a later hardening pass |
| 7 | `pages/1_Opportunities.py` : 527–560 | Materials Save payload = comprehension over live-visible docs. Looks race-prone on paper; is correct by design (mirrors the Y-only readiness definition in `database.py`). | ℹ️ Observation | Already pinned by `test_save_preserves_done_fields_hidden_by_req_n` |
| 8 | Overall | Error messages interpolate raw `exc` into `st.error("Could not save changes: {exc}")`. For a local single-user app this aids debugging; for a multi-user deploy it would leak internals. | ℹ️ Observation | Accepted for v1 |

---

## Fixes applied in this review

### Fix #1 — Guard against `None` position_id in the Delete confirm handler

**Why:** Reproduced in isolation:

```
>>> database.delete_position(None)
# no exception, no row deleted. Silent no-op.
```

Combined with the current handler, this produces:
1. `position_id = st.session_state.get("_delete_target_id")` → `None`
2. `database.delete_position(None)` → silent no-op
3. `st.toast('Deleted ""')` fires
4. `selected_position_id` + `_edit_form_sid` + `_delete_target_*` all cleared
5. User reads the toast and believes the row is gone — but it isn't.

The key should always be present (the Delete button handler sets it before calling the dialog), but "always" in session-state systems is fragile: a rerun can fire between set and read; a stale entry can be orphaned; a future refactor may drop the assignment. The guard is cheap insurance.

**Fix:** Return early from the Confirm branch when `position_id is None`, surface `st.error("Delete target was lost — please re-open the dialog.")` so the user understands *why* nothing happened.

### Fix #2 — Clear stale delete target on row-change

**Why:** The elif-reopen pattern (`elif st.session_state.get("_delete_target_id") == sid: _confirm_delete_dialog()`) is the mechanism that lets Confirm/Cancel clicks reach their branches across reruns. It has a latent UX bug: if the user dismisses the dialog via the X or Escape (neither fires a button click, neither runs our Cancel handler), `_delete_target_id` stays in session-state. On the next rerun:

- If the user has moved to a **different row**, the elif's `== sid` check is False, the dialog does not re-open, state lingers silently. Then they come back to the **original row** — phantom dialog, no user action.
- If the user stays on the **same row**, the phantom dialog is immediate.

The X-dismiss-same-row case is unavoidable without a Streamlit `on_close` event (not exposed in 1.56). The **cross-row** case is the one we can fix: when the selected row changes, drop the delete target. This adds one session-state pop paired with the selection assignment — idempotent, cheap, and keeps the paired-cleanup pattern honest.

**Fix:** In the selection-resolution block, when a new `selected_position_id` is assigned that differs from the previous one, pop `_delete_target_id` / `_delete_target_name` as part of the same step.

**Known remaining limitation:** X-dismiss-then-same-row phantom. Documented below and in a comment at the elif-reopen site. Will revisit when Streamlit exposes a dialog-dismiss event.

### Fix #4 — Added one regression test; documented second fix as unreachable-via-UI

- `test_row_change_clears_pending_delete_target` — pins Fix #2. Intentionally fails without the fix (verified: without the row-change cleanup, the second `at.run()` after switching rows still has `_delete_target_id` in session_state).
- Fix #1 (the `None` guard) cannot be pinned via AppTest. Both entry points to the dialog body (the Delete-button click at line 471 and the `elif` re-open at line 475) *require* `_delete_target_id` to be set — the elif's guard clause is `st.session_state.get("_delete_target_id") == sid`. There is no reachable flow from the page UI that enters the dialog body with a `None` id. The guard is pure defense-in-depth for a future refactor that might pop the key prematurely, a URL-based session-state manipulation, or a cross-tab race in a future multi-user port. Documented at the test site and in this review; verified by code inspection.

Updated finding table below.

---

## Junior-engineer Q&A (didactic section)

> "If I were reviewing this as a junior engineer on this team, what would I want explained?"

### Q1 — Why is "Save" a `st.form_submit_button` instead of a regular `st.button`?

Because widgets inside `st.form(...)` do **not** rerun the script on every keystroke. The form batches changes and only submits when the submit button fires. Without a form, typing a character in "Position Name" would rerun the script, re-seed widget state, and make editing feel laggy (and race-prone — the session-state pre-seed could clobber an in-progress edit). `st.form_submit_button` is the only button type that Streamlit permits inside a form: a plain `st.button` inside a form raises at render.

### Q2 — Why is the Notes form's id `"edit_notes_form"` but the text_area's key `"edit_notes"`? Why the suffix?

Because `st.form` registers its id into the same session-state namespace widgets use, with `writes_allowed=False`. If the form's id collides with an existing session-state key (e.g., the pre-seeded `edit_notes` slot), Streamlit raises `StreamlitValueAssignmentNotAllowedError` at render. The suffix-by-convention (`_form`) guarantees no collision. A junior reader should assume "if in doubt, suffix with `_form`" — it costs nothing and prevents a confusing runtime error.

### Q3 — Why `st.toast(...)` instead of `st.success(...)` for save confirmation?

`st.success` is tied to the current script run — it disappears as soon as the next rerun starts. Every Tier-5 save path ends in `st.rerun()`, which would clobber a `st.success` instantly. `st.toast` is a notification that persists across reruns by design (~4 seconds) — which is exactly what a save-confirmation needs. Pinned by `test_save_toast_survives_rerun` in each Save class.

### Q4 — All four Save handlers repeat the same `payload / try / update_position / toast / pop / flag / rerun / except` block. Isn't that a DRY violation?

It **is** duplicated. The review weighed extracting a `_do_save(sid, payload, label)` helper. Conclusion: rejected.

- Each tab's payload logic is **domain-specific** (the Overview payload validates name; the Materials payload casts `bool → int 0/1` over a filtered subset; the Requirements payload is config-driven over `REQUIREMENT_DOCS`; the Notes payload coerces `None → ""`).
- A generic helper would need callbacks or payload-builder lambdas — more plumbing than the duplication it removes.
- Cohesion wins: a junior reader can read any one tab end-to-end without jumping to a helper file.
- The duplication is bounded at four instances and will not grow (no fifth tab is planned).

The DRY principle exists to reduce change-friction, not to win a code-golf contest. If and when the save pattern gains shared behaviour that *must* stay in sync across tabs (e.g., optimistic locking), revisit.

### Q5 — What is `_edit_form_sid` and why pop it on save?

It is a **sentinel** used to work around Streamlit's "once session_state[key] is set, `value=` is ignored" behaviour. When the user selects a new row, the pre-seed block writes every widget's session-state slot from the fresh DB row — but this only runs if `_edit_form_sid != sid`. On save, the DB row has new values; popping the sentinel forces the next render to re-seed widgets from the freshly-persisted DB values. Without this, the form would "stick" on the old text until the user clicks a different row and comes back.

### Q6 — `_skip_table_reset` is set before `st.rerun()` and consumed on the next run. Why is it "one-shot"?

`st.dataframe(on_select="rerun", key="positions_table")` stores its selection event in a per-render slot. On a **data-change rerun** (which our `update_position` triggers indirectly), the widget resets the slot to `{'selection': {'rows': []}}`. The selection-resolution block's else branch would then pop `selected_position_id`, collapsing the edit panel right after the user clicked Save — terrible UX.

`_skip_table_reset = True` is an out-of-band "hey, skip the reset for exactly one rerun" flag. It is popped-with-default-False when consumed, so it self-expires. If it leaked beyond one rerun, any subsequent legitimate deselection (e.g., user clicks blank space) would be ignored — which is why it's one-shot.

### Q7 — Why is the Delete button OUTSIDE `st.form("edit_overview")`?

Because `st.form` accepts **only** `st.form_submit_button` as a trigger. A plain `st.button` inside the form raises at render. Delete needs its own click handler (not tied to the Save form's submission batching), so it must live outside. Same reason the Save submit is *inside* the form (to batch widget edits) but the post-submit handler lives *outside* (so `st.error` / `st.toast` render in the page body, not inside the form's re-rendering scope).

### Q8 — Why does the Overview tab re-invoke `_confirm_delete_dialog()` via an elif on every rerun? Isn't that redundant with Streamlit's own dialog re-render?

Two reasons, one practical, one test-level:

1. **AppTest compatibility.** A 2026-04-20 isolation probe confirmed that `@st.dialog` does not auto-re-render across reruns under `AppTest`. Streamlit's browser runtime re-opens the dialog automatically while its internal "open" flag is set; `AppTest` does not carry that flag across runs. Without the elif, the Confirm click fires on a rerun where the dialog body is never re-executed, and the click handler is swallowed. We drive the dialog re-open ourselves via an explicit session-state key (`_delete_target_id`).

2. **State-driven design.** Using session-state keys as the single source of "is the dialog open for this row?" means the dialog lifecycle is fully inspectable and testable — there is no hidden Streamlit state driving visibility.

Cost: a minor UX limitation (see Q10 below — X-dismiss phantom on the same row).

### Q9 — Why does the pre-seed use `r["position_name"] or ""` instead of trusting the DB value?

Because `positions.position_name` is TEXT NOT NULL with a sanity default of `''` at the schema level — but other nullable text fields in the row (`institute`, `field`, `link`, `notes`) may be `None`. `st.text_input` expects `str`, not `None`. The `or ""` coerces `None → ""` at the widget boundary, pinning the widget-type contract. Same idea as the `datetime.date.fromisoformat` in a try/except: one bad row should not crash the page.

### Q10 — The Materials payload only contains `done_*` for currently visible docs. Is that a bug — don't hidden docs stay stale in the DB?

It is **intentional**, and the *opposite* behaviour would be the bug. The contract is:

- A `done_*` value is "this document is prepared." Prepared-ness is a user fact, independent of whether any given position currently *requires* the doc.
- If the user sets `req_cv = 'N'` for a position, they are saying "this position does not need a CV" — not "I have un-prepared my CV." Re-writing `done_cv = 0` would destroy information.
- The Materials Save path therefore writes only what the user can currently *see and toggle*. Everything hidden survives.

Pinned by `test_save_preserves_done_fields_hidden_by_req_n`. Mirrored contract from the opposite side in T5-B: Requirements Save writes only `req_*` keys, so `done_*` columns survive any `Y↔N` flip.

### Q11 — The Requirements payload writes only `req_*` keys. But `update_position` could overwrite every column — how are `done_*` survived?

`database.update_position(position_id, fields: dict)` does `UPDATE positions SET {comma-joined keys} = ?, ... WHERE id = ?`. It **only touches columns that appear as keys in the payload dict**. The Save handler builds the payload via a comprehension over `REQUIREMENT_DOCS` that includes only the `req_col` keys — never the `done_col` keys — so the SQL never touches `done_*`. The contract is enforced in the payload comprehension, not in `update_position` itself.

Pinned by `test_save_preserves_done_fields_on_req_flip`: the test pre-sets `done_cv=1`, flips `req_cv` Y → N → Y via two saves, and asserts `done_cv == 1` still.

### Q12 — What's the difference between `st.session_state.pop(key, None)` and `del st.session_state[key]`?

`pop(key, None)` is **idempotent**: it removes the key if present, returns `None` if not, never raises. `del` raises `KeyError` if the key is missing. Every Tier-5 handler uses `pop(..., None)` for state cleanup because we cannot always be sure a given key was set (e.g., `_edit_form_sid` is only set after the first row selection; the delete path may run on the first-ever delete with no prior select-then-save). Using `del` would require a prior `if key in session_state` guard, which is more lines and more surface for copy-paste error. `pop(..., None)` is the one-line equivalent of the whole `if … del` block.

### Q13 — Why `int(bool(x))` instead of just `int(x)`?

Two reasons.

1. **numpy bool propagation.** `pandas` reads `positions.done_cv` (SQLite INTEGER 0/1) as `numpy.int64`. `numpy.int64(0)` is falsy, `numpy.int64(1)` is truthy, but `int(numpy.int64(0))` is `0`, `int(numpy.int64(1))` is `1` — so `int()` directly would work. **However**, the widget's session-state slot holds Python `bool` (checkbox value), not numpy. The seed path assigns `st.session_state[key] = (d == 1)` (a Python bool). On save, we read `st.session_state.get(f"edit_{done_col}")` and may get `None` (if the key was never set — unlikely given the pre-seed, but defensive). `bool(None)` is `False`; `int(False)` is `0`. So `int(bool(x))` normalises `None | bool | numpy.bool_ → 0 | 1` safely.
2. **Self-documenting domain intent.** The schema says `done_* INTEGER 0/1`. `int(bool(...))` reads as "this is a bool being stored as an int" — the two-step cast is a contract, not ceremony. Reviewer-friendly > one-char shorter.

### Q14 — Why does `AppTest` need `_keep_selection(at, 0)` but a real browser doesn't?

`st.dataframe(on_select="rerun", key="positions_table")` uses the key slot as a **single-run event buffer**. In the browser, the user's click on a row is persisted into `window.streamlit.componentState` client-side; the next render's websocket frame re-injects it into the session — the selection feels "sticky." `AppTest` does not simulate this client-side persistence: it executes one script run per `at.run()`, and the `positions_table` slot is **not** automatically re-populated from the prior run. Tests that span multiple `at.run()` calls must re-inject the selection state themselves; otherwise the else branch of the selection-resolution block runs and drops `selected_position_id`.

This is one of the few places where AppTest diverges meaningfully from the browser — documented in `CLAUDE.md` "Observed Streamlit behaviours worth remembering."

### Q15 — What prevents SQL injection in `update_position`?

All queries in `database.py` are **parameterised** (`?` placeholders) — `sqlite3.Connection.execute(sql, params)` passes `params` as a bound argument list, never as string interpolation. The only dynamic string in `update_position` is the column-name list (`", ".join(f"{k} = ?" for k in payload.keys())`), and those keys come from code-internal comprehensions over `config.REQUIREMENT_DOCS` / a fixed Overview field list — not from user input. If a future refactor let user-supplied keys into the payload dict, they would become a SQL injection vector, and we would need a column-name allow-list. Today: safe.

### Q16 — Why `monkeypatch.setattr(database, "delete_position", _boom)` instead of mocking the whole module?

Two reasons:

1. **Scope.** We want one function to raise, not to rebuild `database` wholesale. The other calls (`add_position`, `init_db`, `get_all_positions`) must still use the real SQLite fixture — the page calls them in the same run.
2. **Import semantics.** The page file has `import database` at the top. Python imports by reference — the page's `database` is the same module object pytest monkeypatches. Rebinding one attribute on that module is visible to the page immediately. If we had used `import database as db` plus a module-local alias, or `from database import delete_position`, the rebinding would not reach the page's local name, and the patch would silently miss. The page uses `database.delete_position(...)` (not `from database import ...`), so monkeypatch hits the right name.

Pinned by the failure tests in every Tier-5 save class.

### Q17 — In the failure tests, why `assert not at.exception`? Isn't the whole point that an exception happened?

The exception happens **inside the `try/except`**. `at.exception` reports uncaught exceptions that bubbled out of the script. The failure contract is:

- Raise inside `database.delete_position` → caught by the handler → `st.error("Could not delete: ...")` → script continues → rerun.
- `at.exception` stays empty. The error is reported via `at.error` (a friendly `st.error` element), not via a stack trace.

The assertion `not at.exception` pins "no traceback leaked to the user" — the whole reason the try/except exists (GUIDELINES §8 / F1). Complementary assertion `at.error` pins "the failure is surfaced gracefully." Both together pin the contract.

### Q18 — Why is the payload built inside `if submitted:` rather than unconditionally?

Building the payload unconditionally would read session-state slots that only exist when a row is selected, raising `KeyError` on the first page load. More importantly: it would be wasted work — the payload is only needed when the user clicked Save. The `if submitted:` gate keeps all the save-specific logic scoped to the save flow, which makes the handler easy to read and skip.

### Q19 — Why not just re-read the DB on every rerun instead of using session-state sentinels?

We **do** re-read the DB on every rerun (`df = database.get_all_positions()` at line ~196). The session-state sentinels are not about *reading* — they are about *what widget state to display* when the DB and the form disagree. Example flow:

1. User selects row A. DB has `position_name = "Alpha"`. Pre-seed sets `edit_position_name = "Alpha"`. Form renders "Alpha."
2. User edits the form field to "Beta" (not saved). Session-state now has `edit_position_name = "Beta"`.
3. User reruns (say, by editing a filter). DB still has "Alpha," form still shows "Beta" (because `session_state[key]` overrides `value=`).

The sentinel `_edit_form_sid` says *"widgets are currently seeded for this sid."* When the user saves, we pop the sentinel, and the next render re-seeds widgets from the fresh DB. When the user selects a different row, the sentinel-mismatch triggers a re-seed. Without the sentinel we could not distinguish "user's in-flight edit I must preserve" from "stale form state I must refresh."

### Q20 — How does FK cascade work and why do we rely on it rather than explicitly deleting applications/recommenders first?

Two schema declarations do the work:

1. `PRAGMA foreign_keys = ON;` — SQLite's FK enforcement is **off by default** per connection. `database._connect()` enables it explicitly.
2. `ON DELETE CASCADE` on `applications.position_id` and `recommenders.position_id` (see `database.py` schema). When a `positions` row is deleted, SQLite auto-deletes every dependent row in the same transaction.

Relying on the schema (vs. manual `DELETE FROM applications WHERE position_id = ?`) has three wins:

- **Atomic.** The parent + children go in one transaction; a crash mid-way leaves the DB consistent.
- **Complete.** If someone adds a new child table that FKs to positions, the cascade applies automatically — no page-code changes.
- **Testable.** We pin the contract with `test_confirm_cascades_applications_and_recommenders` so a future refactor that drops `PRAGMA foreign_keys = ON` is caught in CI.

The trade-off: the cascade is invisible in the page code. Every reader needs to know about it. Comment at the Confirm handler + the test fixture + `CLAUDE.md` Key Design Decisions all document this.

---

## Verdict

**Request changes → approved after fixes.**

Apply Fix #1 and Fix #2 (both landed in this review). Add the two regression tests (landed). After fixes, the branch is merge-ready.

### Pre-merge checklist

- [x] Fix #1 applied: `None` guard in Confirm handler with friendly error (defense-in-depth; no reachable failure mode via page UI).
- [x] Fix #2 applied: stale delete target cleared on row-change.
- [x] Regression test added: `test_row_change_clears_pending_delete_target` (pins Fix #2).
- [x] Full suite green: **221 passing, 0 deprecation warnings**.
- [x] Known limitation documented: X-dismiss-then-same-row phantom dialog (pending a Streamlit dialog-close event).

---

_Review completed 2026-04-20 on branch `feature/phase-3-tier5`, immediately before the pre-merge PR for T5-F._
