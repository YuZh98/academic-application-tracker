# Streamlit State Gotchas — Reference

_Reproducible Streamlit quirks hit by this codebase (Symptom → Cause → Workaround), pinned by tests where possible. [GUIDELINES §7](../../GUIDELINES.md#7-streamlit-patterns) links here from the Streamlit-patterns section._

Things that are **not** obvious from the Streamlit docs but that this
codebase has hit in Phase 3/4. Each entry has the symptom, the cause, and
the workaround. `GUIDELINES §7` links here from the Streamlit-patterns
section.

All notes verified against **Streamlit 1.56.0** (2026-04-23).

---

## Index

Source comments and review docs cite gotchas by number — use this
index to jump to the right entry.

1. **NaN in `session_state`** crashes widget serialisation (use `_safe_str`)
2. **Widget-value trap on selection change** — the `_edit_form_sid` sentinel
3. **`@st.dialog`** does not auto-re-render across AppTest reruns
4. **Form id collision** — must not match any widget key inside the form
5. **`st.metric`** has no `key=` parameter (identify by label / position)
6. **`AppTest.session_state`** does not support `.get()`
7. **`KeyError` on conditional widgets** in AppTest — use try/except helpers
8. **`numpy.bool_`** is not `True` identity-wise (use `bool(...)` or `==`)
9. **`Button.type`** in AppTest reports widget-class name, not the `type=` param
10. **`use_container_width=True`** deprecated — use `width="stretch"`
11. **`st.dataframe` selection** doesn't persist across data-change reruns
12. **`get_all_positions()` ordering** shifts row indices on insert
13. **`pd.isna`** catches both `None` and `float('nan')` — truthy check misses NaN
14. **`if st.button(...): st.rerun()`** double-reruns (drop explicit rerun for plain buttons)
15. **`AppTest selectbox.options`** is protobuf string form, not original Python type
16. **`st.dataframe`** has no per-cell tooltip API in Streamlit 1.56

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

**Workaround:** identify metrics in tests by **label** (DESIGN §8 locks
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
# Example from app.py::_next_interview_display: each row carries a
# single scheduled_date from the interviews sub-table; the pd.isna
# guard catches NaN-from-NULL before the string comparison.
for _, row in upcoming.iterrows():
    v = row["scheduled_date"]
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

**Workaround:** drop the explicit `st.rerun()` after a plain `st.button`
click — Streamlit's automatic rerun is sufficient. The pattern survives
in the codebase only inside Save / Delete handlers wrapped in `st.form`
or `@st.dialog`, where the explicit rerun IS required: form-submission
and dialog Confirm events do not trigger a script rerun automatically,
so the handler must call `st.rerun()` explicitly to refresh the UI
after a write. Example sites: every Save handler in
`pages/1_Opportunities.py`'s `st.form` blocks, and every
`_confirm_*_delete_dialog` handler across the project's destructive
paths (position / interview / recommender deletes).

---

## 15. AppTest `selectbox.options` is the protobuf string form, not the original Python type

**Symptom:** a test that asserts
`list(at.selectbox(key="x").options) == [30, 60, 90]` fails with
`['30', '60', '90'] != [30, 60, 90]` even though the page passes the int
list to `st.selectbox(options=[30, 60, 90], ...)`. Confusing because
`at.selectbox(key="x").value` correctly returns the int `30`.

**Cause:** Streamlit serializes selectbox options into the page protobuf as
strings regardless of the original Python type. AppTest's `.options`
attribute exposes that protobuf-serialized form; `.value` runs the
round-trip back to the original type via the registered `format_func`,
which is why the two attributes disagree about types.

**Workaround:** compare against the stringified expected list, and cite the
original list in the failure message for debug clarity:

```python
expected_strs = [str(v) for v in config.UPCOMING_WINDOW_OPTIONS]
assert list(sb.options) == expected_strs, (
    f"AppTest exposes selectbox options as strings; expected "
    f"{expected_strs!r} (stringified config.UPCOMING_WINDOW_OPTIONS="
    f"{config.UPCOMING_WINDOW_OPTIONS!r}). Got {list(sb.options)!r}"
)
```

Trust `.value` for round-trip-correct type assertions
(`assert sb.value == 30`); use `.options` only with awareness it returns
strings. Discovered while writing
`TestT4UpcomingTimeline::test_window_selector_offers_config_window_options`
(Phase 4 T4-B, 2026-04-29).

---

## 16. `st.dataframe` does not support per-cell tooltips in Streamlit 1.56

**Symptom:** A spec calls for "the cell carries `<field>` as a tooltip"
or similar per-row hover text on a `st.dataframe`, and there's no
visible Streamlit API to attach it. `st.column_config.Column(help=...)`
shows up in the docs but only renders on the column header — every
row in that column shares the same hover string.

**Cause:** Streamlit's `st.dataframe` serializes the data through Arrow
protobuf to the React frontend. Per-cell metadata (style, tooltip,
custom click target) is not part of that protobuf. Two fallback paths
that look like they should work also don't:

- `pandas.io.formats.style.Styler.set_tooltips(...)` produces tooltip
  metadata for the *HTML* render path; `st.dataframe` consumes the
  Arrow representation, which strips Styler tooltips. Verified against
  Streamlit 1.56.0 source (2026-04-30).
- `st.column_config.TextColumn(help=...)` is column-header-only — same
  as `Column(help=...)`. Streamlit 1.56 has no `cell_help` / `row_help`
  parameter anywhere on the column-config types.

**Workaround:** Fold the tooltip text into inline cell content. For the
Applications-page Confirmation column (DESIGN §8.3 D-A amendment, T1-C):

```python
def _format_confirmation(received: Any, iso_str: Any) -> str:
    if pd.isna(received) or not bool(received):
        return EM_DASH                        # — (received = 0)
    formatted = _format_date_or_em(iso_str)
    if formatted == EM_DASH:
        return "✓ (no date)"                  # received = 1, no date
    return f"✓ {formatted}"                   # ✓ Apr 19
```

Three states cover what the original tooltip would have said. Reverse
the workaround if a future Streamlit release adds per-cell tooltip
support — the call site is one apply-call.

**Alternatives considered + rejected:** rendering the table as
`st.html(df.to_html(...))` with `<td title="...">` works but loses
sort / selection / copy interactivity. Wrapping each row in
`st.container(border=True)` (the T5 Recommender Alerts pattern)
works for ≤ 10 rows but doesn't scale to a tabular data view. Full
write-up + four-option comparison in
`reviews/phase-5-tier1-review.md` (Q3).

Discovered while implementing the Applications page Confirmation
column (Phase 5 T1-C, 2026-04-30) — DESIGN §8.3 D-A had originally
specified per-cell tooltip text; the amendment to inline-cell text is
recorded inline in DESIGN §8.3.

---

## When a new gotcha lands

1. Reproduce it with an isolation probe (small throwaway script in `/tmp/`).
2. Add an entry here with Symptom / Cause / Workaround.
3. Reference it in the source comment where the workaround lives.
4. Pin it with a test so a Streamlit version bump that changes the
   behaviour trips a specific test rather than a mysterious failure.
