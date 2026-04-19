# Tasks

## In Progress
- [ ] Phase 3 Tier 4: row-click inline edit
  - [x] T4-A: row-selection on positions table (session_state['selected_position_id'])
  - [x] T4-B: edit-panel shell — subheader + 4 empty tabs driven by config.EDIT_PANEL_TABS
  - [x] T4-C: Overview tab fields (7 pre-filled widgets in st.form + _edit_form_sid seed)
  - [ ] T4-D: Requirements tab (config-driven checkboxes)
  - [ ] T4-E: Materials tab (state-driven — shows only required docs)
  - [ ] T4-F: Notes tab (text_area)
  - [ ] T4-G: review + apply fixes + open PR

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

_Updated: 2026-04-19 (T4-A + T4-B + T4-C complete; T4-D next)_
