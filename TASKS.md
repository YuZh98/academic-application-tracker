# Tasks

## In Progress
- [ ] Phase 3 Tier 5: Save / Delete with confirm dialog
  - [x] T5-A: Overview Save (update_position + toast + error path + selection survival via _skip_table_reset)
  - [ ] T5-B: Requirements Save (preserve done_* across req flips Y↔N)
  - [ ] T5-C: Materials Save (writes done_* only for req_* == 'Y')
  - [ ] T5-D: Notes Save (empty → "")
  - [ ] T5-E: Delete with st.dialog confirm (Overview tab only; FK cascade)
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

_Updated: 2026-04-20 (Tier 4 merged; T5-A done; T5-B next — Requirements Save)_
