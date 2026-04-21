# Tasks

## In Progress
**Phase 4 — Dashboard (`app.py`)** — plan locked in `PHASE_4_GUIDELINES.md`. 6 tiers, ~9 sessions, ~9.5 hr. Critical path: T1 → T2 → T3 → T4 → T5 → T6.

### Phase 4 — Dashboard (pending)
- [~] **T1** App shell + KPI cards (~1.5 hr, 3 sessions, branch `feature/phase-4-tier1`)
  - [x] T1-A: `tests/test_app_page.py` scaffold + empty-DB smoke test + 4-KPI-column shape test
  - [x] T1-B: `app.py` shell — title + `database.init_db()` + `st.columns(4)` with 4 `st.metric` placeholder cards (labels per DESIGN.md; values `"—"`)
  - [x] T1-C: top bar 🔄 refresh button (`st.rerun()`) + wire `count_by_status()` → Tracked / Applied / Interview
  - [ ] T1-D: wire `get_upcoming_interviews()` → Next Interview date (empty → `"—"`, per U3)
  - [ ] T1-E: fully-empty-DB hero callout + CTA to Opportunities (per U5)
- [ ] **T2** Application funnel (Plotly) (~2.0 hr, 2 sessions, branch `feature/phase-4-tier2`)
  - [ ] T2-A: Plotly horizontal bar from `count_by_status()`, colors via `config.STATUS_COLORS`
  - [ ] T2-B: empty-state render (no positions → descriptive text, not broken figure)
  - [ ] T2-C: place in left half of `st.columns(2)` (per U2)
- [ ] **T3** Materials Readiness (~1.0 hr, 1 session, branch `feature/phase-4-tier3`)
  - [ ] T3-A: render `compute_materials_readiness()` → "N ready / M pending" + mini bar
  - [ ] T3-B: place in right half of `st.columns(2)` (per U2)
- [ ] **T4** Upcoming timeline (~2.5 hr, 2 sessions, branch `feature/phase-4-tier4`)
  - [ ] T4-A: merge `get_upcoming_deadlines(30)` + `get_upcoming_interviews()` by date
  - [ ] T4-B: urgency column from `DEADLINE_URGENT_DAYS` / `DEADLINE_ALERT_DAYS`
  - [ ] T4-C: `st.dataframe(width="stretch")` with (date, label, kind, urgency)
  - [ ] T4-D: empty state
- [ ] **T5** Recommender alerts (~1.5 hr, 1 session, branch `feature/phase-4-tier5`)
  - [ ] T5-A: fetch `get_pending_recommenders(RECOMMENDER_ALERT_DAYS)`, group by recommender
  - [ ] T5-B: per-person card with `mailto:` prefilled (subject + position names)
  - [ ] T5-C: empty state
- [ ] **T6** Pre-merge review + PR (~1.0 hr, 2 sessions)
  - [ ] T6-A: `reviews/phase-4-premerge.md` with verified acceptance criteria
  - [ ] T6-B: open PR → merge → delete branch (mirror Tier 5-F)

**Tests:** one file, `tests/test_app_page.py` (per C8). Class per tier.
**Decisions locked:** C3 keep refresh, C4 skip caching, C5 sync GUIDELINES.md, C6 fix DESIGN §6 line 431, C8 one test file, U2 `st.columns(2)`, U3 "—" on empty, U5 empty-DB hero.

## Done in this phase
- [x] 2026-04-21 — Phase 4 T1-C: KPI count wiring + 🔄 refresh button. `app.py` now reads `database.count_by_status()` and renders live values in the first three KPI cards (Tracked = `count([OPEN]) + count([APPLIED])`, Applied = `count([APPLIED])`, Interview = `count([INTERVIEW])`); Next Interview stays `"—"` until T1-D. Top-bar `st.columns([6, 1])` places the title on the left and a `🔄 Refresh` button on the right that calls `st.rerun()` (decision C3). **Tracked-bucket decision** (new, locked with user 2026-04-21): "opportunities that might get moved forward" = OPEN + APPLIED; INTERVIEW and OFFER are excluded because they're tracked by their own KPIs. **Phase 4 scope deviation** (approved by user 2026-04-21): added three named-status aliases to `config.py` (`STATUS_OPEN` / `STATUS_APPLIED` / `STATUS_INTERVIEW`) so `app.py` can reference specific statuses without hardcoding the literal strings — keeps the anti-typo guardrail in place and satisfies the Phase 4 pre-merge grep rule (`grep -nE "\[OPEN\]|\[APPLIED\]|\[INTERVIEW\]" app.py` → zero hits). Tests: 7 new (`TestT1CKpiCountsAndRefresh`: empty-DB zeros, Tracked = OPEN+APPLIED, Applied bucket, Interview bucket, terminal statuses excluded, refresh button render, refresh-click rerender). 232 passing, 0 deprecation warnings.
- [x] 2026-04-20 — Phase 4 T1-A + T1-B: dashboard test scaffold + app shell. `tests/test_app_page.py` created (class `TestT1AppShell`, 2 tests) reusing the shared `db` fixture; `app.py` stub replaced with title + `database.init_db()` + `st.columns(4)` rendering four `st.metric` cards with labels "Tracked" / "Applied" / "Interview" / "Next Interview" and `"—"` placeholder values. **Deviation from plan**: PHASE_4_GUIDELINES.md §Test-conventions called for `st.metric(..., key=...)` lookup; verified against live Streamlit 1.56 that `st.metric` has no `key=` parameter (`TypeError` on unexpected kwarg); tests use label-based + positional lookup instead, which is the idiomatic AppTest path and doubles as a DESIGN.md contract check. Guideline corrected in same `chore:` commit. 225/225 passing, 0 deprecation warnings.

## Backlog

### App build (in order)
- [ ] Phase 5: write `pages/2_Applications.py` and `pages/3_Recommenders.py`
- [ ] Phase 6: complete `exports.py` and `pages/4_Export.py`
- [ ] Phase 7: polish — urgency colors, empty states, search, confirm dialogs
- [ ] DX: add `pythonpath = .` to `pytest.ini` (one-line fix; user deferred at Phase 3 close)

### Application tasks
- [ ] Draft research statement
- [ ] Prepare CV (postdoc version)
- [ ] Identify target positions and add to tracker
- [ ] Request recommendation letters from advisors

## Completed
- [x] 2026-04-20 — Phase 3 **merged to main** via PR #3 (merge commit `c972385`); branch `feature/phase-3-tier5` deleted on origin; 223 tests passing on `main`, zero deprecation warnings.
- [x] 2026-04-20 — Phase 4 planning + `PHASE_4_GUIDELINES.md` drafted (6 tiers, ~15 sub-tasks, critical path mapped, 8 design decisions closed); DESIGN.md line 431 readiness scope synced with implementation; GUIDELINES.md §7 (`st.toast` over `st.success`) and §8 (no re-raise in user-facing paths) synced.
- [x] 2026-04-20 — Phase 3 Tier 5-F: pre-merge review — commit-by-commit walkthrough + release-notes doc (`reviews/phase-3-tier5-premerge.md`); verified acceptance criteria (`pytest -q` = 223 passed; `pytest -W error::DeprecationWarning` = 223 passed; `git diff main..HEAD -- database.py config.py exports.py app.py` = empty; no hardcoded vocab via grep; form id ≠ widget key via smoke test; all save/delete paths use `st.toast` on success + `st.error` on failure uniformly); updated `CLAUDE.md`, `TASKS.md`, `roadmap.md`, `memory/project_state.md` to reflect Tier-5 complete; staled header comment in `pages/1_Opportunities.py` updated (Tier 5 moved from Pending → Shipped); branch pushed to origin; PR opened against main
- [x] 2026-04-20 — Phase 3 Tier 5 post-review fix: pandas-NaN-in-pre-seed TypeError (user-reported) — adding 3 positions via Quick Add + Saving row 0 + selecting row 1 raised `TypeError: bad argument type for built-in operation` under every edit-panel tab (Notes area replaced entirely by the red error). Root cause: pandas returns `float('nan')` for NULL TEXT cells once any row has a real string (column dtype upgraded to `object`); the pre-seed idiom `r[col] or ""` mis-fires because NaN is truthy — `nan or ""` evaluates to `nan`, and NaN in `session_state` blows up Streamlit's widget protobuf str type-check. Fix: module-level `_safe_str(v)` helper (`None` or `math.isnan(float(v))` → `""`) applied to all five text pre-seed sites (position_name / institute / field / link / notes). Regression pinned by `TestPreSeedNaNCoercion` (end-to-end reproduction + helper-contract unit). 223 total passing, 0 deprecation warnings
- [x] 2026-04-20 — Phase 3 Tier 5-E: Overview Delete — `@st.dialog("Delete this position?")` opened by a primary-styled `st.button(key='edit_delete')` on the Overview tab **outside** `st.form('edit_overview')` (form only allows `form_submit_button`); target sid/name are passed via `session_state["_delete_target_id"/"_delete_target_name"]` and the Overview tab re-invokes `_confirm_delete_dialog()` on every rerun while the pending flag is set — Streamlit's built-in dialog-re-render magic does NOT carry through AppTest's script-run model (verified with an isolation probe `/tmp/dialog_probe.py`). **Confirm** → `database.delete_position(sid)` → `st.toast` → clear all four session_state keys (paired `_delete_target_*` + `selected_position_id` / `_edit_form_sid`) → `st.rerun()`. **Cancel** → clear only `_delete_target_*`, set `_skip_table_reset=True` so selection survives → `st.rerun()`. FK cascade via existing schema (`PRAGMA foreign_keys=ON` + `ON DELETE CASCADE` on applications.position_id and recommenders.position_id). Extended the selection-resolution `elif` to also preserve selection while `_delete_target_id in session_state`, otherwise the Confirm/Cancel click's internal rerun would collapse the edit panel before the dialog could re-open and the click would be lost. Failure mode mirrors Tier-5 save paths: raising `delete_position` → friendly `st.error("Could not delete: ...")`, no re-raise, `_delete_target_*` and selection preserved so the user can retry. 7 new AppTest tests in `TestDeleteAction` (render, confirm deletes, FK cascade pin, paired cleanup, toast w/ name, cancel is a no-op, DB-failure error path). AppTest caveats worth noting: `Button.type` reports widget-class not the Streamlit `type=` param (primary styling verified by code review, not automated); `AppTest.session_state` has no `.get()` — use `"key" in at.session_state` + subscript. **220 total passing, 0 deprecation warnings**.
- [x] 2026-04-20 — Phase 3 Tier 5-D: Notes Save — `st.form_submit_button('Save Changes', key='edit_notes_submit')` inside `st.form('edit_notes_form')` wired to `database.update_position`; payload `{'notes': <text or ''>}`; empty input is stored as `""` not NULL (pinned by `test_save_empty_stored_as_empty_string`) so round-trips through pre-seed (NULL→"") + no-op save leave DB stable at `""`; reuses all Tier-5 patterns (toast, friendly `st.error` without re-raise, `_edit_form_sid` pop, `_skip_table_reset` one-shot); 5 new AppTest tests in `TestNotesSave`; 213 total passing, 0 deprecation warnings
- [x] 2026-04-20 — Phase 3 Tier 5-C: Materials Save — `st.form_submit_button('Save Changes', key='edit_materials_submit')` inside `st.form('edit_materials')` wired to `database.update_position`; payload built from a comprehension over the **visible** subset of `config.REQUIREMENT_DOCS` (req_* == 'Y' on live session_state) containing ONLY `done_*` keys cast `int(bool(...))` — hidden `done_*` columns are never written, so prior prepared-doc state survives any `req_*` Y↔N flip (critical contract pinned by `test_save_preserves_done_fields_hidden_by_req_n`, mirrors T5-B from the opposite side); empty-state path unchanged (info hint, no form); reuses all Tier-5 patterns; 5 new AppTest tests in `TestMaterialsSave`; relaxed `test_unwired_save_buttons_still_disabled` count assertion (tooltip check preserved); 208 total passing at T5-C; 213 after T5-D
- [x] 2026-04-20 — Phase 3 Tier 5-B: Requirements Save — `st.form_submit_button('Save Changes', key='edit_requirements_submit')` wired to `database.update_position`; payload built from `config.REQUIREMENT_DOCS` comprehension containing ONLY `req_*` keys (critical contract: `done_*` columns untouched, so `done_cv` etc. survive `req_cv` Y→N→Y flips — pinned with `test_save_preserves_done_fields_on_req_flip`); reuses T5-A patterns (`_skip_table_reset` one-shot, `_edit_form_sid` pop-on-save, `st.toast` success, `st.error` on DB failure, no re-raise); `_keep_selection(at, row_index)` test helper reused; 5 new AppTest tests in `TestRequirementsSave`; 203 total passing, 0 deprecation warnings
- [x] 2026-04-20 — Phase 3 Tier 5-A: Overview Save — `st.form_submit_button('Save Changes', key='edit_overview_submit')` wired to `database.update_position`; whitespace-only `position_name` blocked with `st.error`; friendly `st.error` on DB failure (no re-raise, mirrors quick-add F1); `st.toast` on success; `_skip_table_reset` one-shot flag preserves `selected_position_id` across the post-save rerun (st.dataframe resets its event on data-change rerun per T4 behaviour note); `_edit_form_sid` popped on save so widgets re-seed from fresh DB values; tests use new `_keep_selection` helper to re-inject `positions_table` (AppTest doesn't persist widget event state across reruns; browser does); 6 new AppTest tests + 1 renamed disabled-count test; 198 total passing, 0 deprecation warnings
- [x] 2026-04-20 — Phase 3 Tier 4 merged to main (PR #2)
- [x] 2026-04-20 — Docs: DESIGN.md §11 adds "Adding file attachments to the Materials panel" extension sketch (config keys, attachments table DDL, three new database.py functions, filesystem-not-BLOB rationale, explicit non-goals); roadmap backlog row P2
- [x] 2026-04-19 — Phase 3 Tier 4-F: Notes tab — single `st.text_area(key='edit_notes')` inside `st.form('edit_notes_form')`; pre-seed copies `positions.notes` with NULL→'' coercion; form id intentionally ≠ widget key to avoid `StreamlitValueAssignmentNotAllowedError` (form registers with `writes_allowed=False`); disabled Tier-5 save placeholder mirrors T4-C/D/E; 6 AppTest tests; 190 total passing
- [x] 2026-04-19 — Phase 3 Tier 4-E: Materials tab — state-driven checkboxes filtered by `session_state[edit_{req_col}] == 'Y'` (Y-only matches database.py readiness def); empty-state hint when nothing required; pre-seed extended with `done_*` loop so req_* flip N→Y mid-edit shows DB value; `_checkbox_rendered` test helper via try/except KeyError; `bool(...)` normalization for numpy.bool_; 7 AppTest tests; 184 total passing
- [x] 2026-04-19 — Phase 3 Tier 4-D: Requirements tab — one st.radio per REQUIREMENT_DOCS entry, options = REQUIREMENT_VALUES ('Y'|'Optional'|'N'), display via REQUIREMENT_LABELS; F2-style coercion; 7 AppTest tests incl. monkeypatch config-drive proof; 177 total passing
- [x] 2026-04-19 — Phase 3 Tier 4-C: Overview tab — 7 pre-filled edit widgets in st.form('edit_overview'); _edit_form_sid sentinel defeats Streamlit's widget-value trap on selection change; 8 AppTest tests; 167 total passing
- [x] 2026-04-19 — Phase 3 Tier 4-B: edit-panel shell (subheader + st.tabs from config.EDIT_PANEL_TABS); selected row looked up in unfiltered df; 6 AppTest tests; 159 total passing
- [x] 2026-04-19 — Phase 3 Tier 4-A: single-row selection on positions table via st.dataframe(on_select='rerun'); 6 AppTest tests; 153 total passing
- [x] 2026-04-19 — Phase 3 Tier 2 & 3 code review (F1–F5): regex=False field filter, TypeError catch in _deadline_urgency, boundary + past-deadline + special-char tests; 147 tests passing
- [x] 2026-04-18 — Phase 3 Tier 3: positions table (st.dataframe + deadline urgency flag); 8 AppTest tests; 143 total passing
- [x] 2026-04-18 — Phase 3 Tier 2: filter bar (status, priority, field); 13 AppTest tests; 135 total passing
- [x] 2026-04-17 — Phase 3 Tier 1: quick-add form (6 fields) + empty state; 16 AppTest tests written + passing (121 total)
- [x] 2026-04-17 — Phase 3 Tier 1 code review (F1–F5): try/except, strip(), explicit keys, expander scope, dict[str,Any], st.toast fix; 122 tests passing
- [x] 2026-04-17 — Phase 3 Tier 0: stub app.py + pages/1_Opportunities.py skeleton; Streamlit APIs verified
- [x] 2026-04-16 — Phase 2 code review + 5 fixes applied; 105 tests, 100% coverage
- [x] 2026-04-16 — Phase 2: database.py (CRUD + dashboard queries) + exports.py stub + postdoc.db
- [x] 2026-04-15 — Design postdoc tracker system architecture
- [x] 2026-04-15 — Create markdown tracking files (OPPORTUNITIES, PROGRESS, RECOMMENDERS)
- [x] 2026-04-15 — Apply ADR-001 improvements (quick-add, materials readiness, recommender log)
- [x] 2026-04-15 — Initialize git repository
- [x] 2026-04-15 — Write CLAUDE.md, GUIDELINES.md, roadmap.md
- [x] 2026-04-15 — Phase 1: create .venv, install packages, write config.py

---

_Updated: 2026-04-21 (Phase 4 T1-C shipped on `feature/phase-4-tier1`; 232 tests green; next action: T1-D — wire `get_upcoming_interviews()` into the Next Interview KPI, "—" on empty per U3)_
