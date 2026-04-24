# Streamlit State Gotchas — Reference

Things that are **not** obvious from the Streamlit docs but that this
codebase has hit in Phase 3/4. Each entry has the symptom, the cause, and
the workaround. `GUIDELINES.md §7` links here from the Streamlit-patterns
section.

All notes verified against **Streamlit 1.56.0** (2026-04-23).

---

## 1. `pandas.NaN` in `session_state` breaks widget serialisation

**Symptom:** `TypeError: bad argument type for built-in operation` with no
traceback context; the whole edit panel replaced by a red error block.

**Cause:** pandas upgrades a TEXT column's dtype to `object` once **any**
row has a real string, and returns `float('nan')` for the NULL cells on
rows that never had a value. The obvious idiom `r[col] or ""` mis-fires
because `bool(float('nan')) is True` — so `nan or ""` evaluates to `nan`.
That NaN ends up in `session_state`, and Streamlit's widget-value protobuf
serialisation fails a C-level `str` type-check with the TypeError above.

**Workaround:** the `_safe_str(v)` helper in `pages/1_Opportunities.py`:

```python
def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v)
```

Apply it to every text pre-seed site. Anywhere you would have written
`st.session_state["edit_x"] = r["x"] or ""`, write `_safe_str(r["x"])`.

---

## 2. Widget-value trap on selection change (`_edit_form_sid` sentinel)

**Symptom:** The edit form "sticks" on the first-selected row. Selecting a
different row still shows the first row's values; only changing a widget
manually picks up the new row.

**Cause:** Once `session_state[key]` is set, Streamlit ignores the `value=`
argument on later reruns for that key. The pre-seed block runs every rerun
and *looks* like it's re-seeding, but Streamlit uses the stale
session_state value anyway.

**Workaround:** gate pre-seed on a sentinel key that tracks the currently-
seeded selection id. Pseudo-pattern:

```python
if st.session_state.get("_edit_form_sid") != sid:
    st.session_state["edit_field_a"] = r["field_a"]
    st.session_state["edit_field_b"] = r["field_b"]
    # ... re-seed every widget state ...
    st.session_state["_edit_form_sid"] = sid
```

Pop the sentinel on save so the widgets re-seed from freshly-persisted
values on the next render.

---

## 3. `@st.dialog` does not auto-re-render across AppTest reruns

**Symptom:** in a live browser, a dialog stays open until confirmed/cancelled.
In AppTest, a button click *inside* the dialog fires an internal rerun that
closes the dialog — the click's handler never runs, tests fail.

**Cause:** Streamlit has internal magic to re-open a dialog on rerun when
it was open on the previous run. That magic does **not** carry through
AppTest's script-run model (verified by isolation probe 2026-04-20).

**Workaround:** the outer script must re-invoke the dialog itself while a
pending flag is set in session_state:

```python
if st.button("Delete", key="edit_delete"):
    st.session_state["_delete_target_id"] = sid
    _confirm_delete_dialog()   # opens
elif st.session_state.get("_delete_target_id") == sid:
    _confirm_delete_dialog()   # re-open on every rerun while pending
```

Confirm/Cancel handlers clear `_delete_target_*` before `st.rerun()` so the
dialog closes naturally on the next run.

---

## 4. Form id must not collide with any widget key inside the form

**Symptom:** `StreamlitValueAssignmentNotAllowedError` at render time.

**Cause:** `st.form(key)` registers the key with `writes_allowed=False`. If
any widget inside the form shares that key, assignment via session_state
fails.

**Workaround:** suffix form ids with `_form` when there's any risk of
collision:

```python
with st.form("edit_notes_form"):              # form id
    st.text_area("Notes", key="edit_notes")   # widget key — different
```

The convention: **form id = `<scope>_form`**, widget keys are `<scope>_<field>`.
A grep rule at merge time catches collisions.

---

## 5. `st.metric` has no `key=` parameter

**Symptom:** `TypeError: st.metric() got an unexpected keyword argument 'key'`.

**Cause:** `st.metric` is a display-only primitive. Only stateful widgets
accept `key=`. `at.metric[i].key` is also always `None` for the same reason.

**Workaround:** identify metrics in tests by **label** (DESIGN.md §8 locks
the four strings "Tracked" / "Applied" / "Interview" / "Next Interview")
or by **positional order** within `st.columns(4)`. Both double as
regression checks against the UI contract.

---

## 6. `AppTest.session_state` does not support `.get()`

**Symptom:** `AttributeError: 'AppSessionState' object has no attribute 'get'`.

**Cause:** AppTest's session_state wrapper mimics a subset of the dict API,
but not `.get()`.

**Workaround:** use `in` + subscript:

```python
# GOOD
if "selected_position_id" in at.session_state:
    sid = at.session_state["selected_position_id"]

# BAD — raises AttributeError
sid = at.session_state.get("selected_position_id")
```

---

## 7. `at.checkbox(key=...)` and `at.text_area(key=...)` raise `KeyError` if the widget didn't render

**Symptom:** the widget is conditionally shown (e.g. Materials tab filters
its checkboxes by live req_* values); the test queries by key and hits a
`KeyError` when the widget isn't on the current render.

**Workaround:** try/except helpers:

```python
def _checkbox_rendered(at, key):
    try:
        at.checkbox(key=key)
        return True
    except KeyError:
        return False
```

Used in `TestT4EMaterialsTab` to verify that N→Y mid-edit brings a
checkbox onto the page without crashing the assertion.

---

## 8. `numpy.bool_` is not `True` identity-wise

**Symptom:** a test comparing `row[col] is True` fails; the value is clearly
`True` in print output.

**Cause:** pandas returns `numpy.bool_` when reading a SQLite INTEGER 0/1
column into a boolean-ish context. `numpy.True_ is True` evaluates to
`False`.

**Workaround:** normalise with `bool(...)` before identity comparison:

```python
assert bool(row["done_cv"]) is True   # works
assert row["done_cv"] is True          # FAILS silently
```

Or use `==` instead of `is` for value comparison.

---

## 9. `Button.type` in AppTest reports widget-class name, not the Streamlit `type=` param

**Symptom:** test asserts `at.button[i].type == "primary"`, fails because
`type` reads `"Button"` (the class name).

**Cause:** AppTest's element wrapping exposes the widget's internal type
name, not the user-facing `type=` keyword.

**Workaround:** if the styling test matters (destructive-action red button,
etc.), verify by code review rather than automation — document in a Tier
review doc that "primary styling of the Delete button is enforced by
source inspection."

---

## 10. `use_container_width=True` is deprecated; use `width="stretch"`

**Symptom:** ~60 `DeprecationWarning` lines per test run; `pytest -W error::DeprecationWarning` fails.

**Cause:** Streamlit 1.50+ deprecated `use_container_width` in favour of
the more general `width=` parameter (accepting `"stretch"`, `"content"`,
or a number). Removal scheduled after 2025-12-31.

**Workaround:** global find-replace across the codebase:
```python
# OLD
st.dataframe(df, use_container_width=True)
# NEW
st.dataframe(df, width="stretch")
```

Verified migrated as of Phase 3 Tier 4.

---

## 11. `st.dataframe` event state does not persist across data-change reruns

**Symptom:** user selects a row, saves a change, the rerun clears the
selection — edit panel collapses right after Save.

**Cause:** `st.dataframe` with `on_select="rerun"` treats a data-change
rerun as a new render; its selection event is reset to `{"rows": []}`.
Documented Streamlit protective behaviour.

**Workaround:** one-shot `_skip_table_reset` flag set before `st.rerun()`
in every Save path. The selection-resolution block consumes the flag:

```python
selected_rows = list(event.selection.rows) if event is not None else []
if selected_rows and 0 <= selected_rows[0] < len(df_display):
    st.session_state["selected_position_id"] = ...
elif st.session_state.pop("_skip_table_reset", False) \
     or "_delete_target_id" in st.session_state:
    pass                                          # keep current selection
else:
    st.session_state.pop("selected_position_id", None)
    st.session_state.pop("_edit_form_sid", None)
```

AppTest also does not persist the `positions_table` event across reruns
(a real browser does). Tests use a `_keep_selection(at, row_index)` helper
to re-inject the selection before the final `at.run()`.

---

## 12. `get_all_positions()` ordering changes the selected row's positional index

**Symptom:** user adds a new position, the new position lands somewhere
in the table based on its deadline, the previously-selected row's index
shifts, the edit panel silently re-binds to a different position.

**Cause:** `get_all_positions()` orders `deadline_date ASC NULLS LAST`.
Any insert can shift every other row's positional index.

**Workaround:** clear selection keys after any insert/delete. The quick-add
handler pops `positions_table`, `selected_position_id`, and
`_edit_form_sid` together before `st.rerun()`. Pinned by
`test_quick_add_clears_stale_selection`.

---

## 13. `pd.isna` catches both `None` and `float('nan')` — unlike truthy checks

NaN is truthy (`bool(float('nan')) is True`). A plain truthy check misses
NaN-from-NULL columns. `pd.isna` is the load-bearing guard anywhere a
DataFrame cell feeds into session_state or string formatting.

```python
for col in ("interview1_date", "interview2_date"):
    v = row[col]
    if pd.isna(v) or v == "" or v < today_iso:
        continue
    # safe to use v as a string / date
```

---

## 14. `if st.button(...): st.rerun()` double-reruns

**Symptom:** clicking a button triggers two reruns instead of one. No user-
visible bug but a slight performance cost.

**Cause:** `st.button` already triggers a rerun on click; the explicit
`st.rerun()` fires a second one.

**Workaround:** leave it if the double-rerun is negligible. The 🔄 Refresh
button in `app.py` keeps the explicit `st.rerun()` as a self-documenting
intent marker — future contributors reading the code see "this is here to
refresh" immediately.

---

## When a new gotcha lands

1. Reproduce it with an isolation probe (small throwaway script in `/tmp/`).
2. Add an entry here with Symptom / Cause / Workaround.
3. Reference it in the source comment where the workaround lives.
4. Pin it with a test so a Streamlit version bump that changes the
   behaviour trips a specific test rather than a mysterious failure.
