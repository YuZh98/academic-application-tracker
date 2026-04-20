# Tasks

## In Progress
- [ ] Phase 3 Tier 5: Save / Delete with confirm dialog
  - [x] T5-A: Overview Save (update_position + toast + error path + selection survival via _skip_table_reset)
  - [x] T5-B: Requirements Save (preserve done_* across req flips Y↔N)
  - [x] T5-C: Materials Save (writes done_* only for req_* == 'Y')
  - [x] T5-D: Notes Save (empty → "")
  - [x] T5-E: Delete with st.dialog confirm (Overview tab only; FK cascade)
  - [ ] T5-F: pre-merge review + open PR

## Done in this phase
- [x] Phase 3 Tier 4 merged to main (T4-A through T4-G)
  - T4-A row-selection, T4-B edit-panel shell, T4-C Overview widgets,
    T4-D Requirements radios, T4-E Materials state-driven checkboxes,
    T4-F Notes text_area, T4-G pre-merge review + PR #2

## Backlog

### App build (in order)
- [ ] Phase 4: write full `app.py` dashboard
- [ ] Phase 5: write `pages/2_Applications.py` and `pages/3_Recommenders.py`
- [ ] Phase 6: complete `exports.py` and `pages/4_Export.py`
- [ ] Phase 7: polish — urgency colors, empty states, search, confirm dialogs

### Application tasks
- [ ] Draft research statement
- [ ] Prepare CV (postdoc version)
- [ ] Identify target positions and add to tracker
- [ ] Request recommendation letters from advisors

## Completed
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

_Updated: 2026-04-20 (Tier 4 merged; T5-A/B/C/D/E all done — all four tabs' Save wired + Overview Delete via st.dialog; T5-F next — pre-merge review + PR)_
