# Handoff: Remove [INTERVIEW] and [OFFER] from the manual status edit selectbox

**Branch:** `fix/kpi-nomenclature`  
**Date:** 2026-05-07  
**Context:** The dashboard KPI nomenclature fix is in progress. This is a follow-up UX improvement.

## Problem

The Opportunities page edit panel (Overview tab) offers all 7 statuses in the "Status" selectbox, including `[INTERVIEW]` and `[OFFER]`. These two statuses are meant to be reached via auto-promotion:

- `[INTERVIEW]` is set automatically when the user logs an interview on the Applications page (`add_interview` with `propagate_status=True`)
- `[OFFER]` is set automatically when the user records an offer result

Exposing them in the manual picker is confusing — users might set "Interview" without logging an actual interview event, creating inconsistent data.

## Solution

Add a new constant in `config.py` that defines the statuses available for manual selection in the edit form:

```python
# Statuses the user can manually pick in the Opportunities edit panel.
# [INTERVIEW] and [OFFER] are auto-promoted and excluded from manual selection.
MANUAL_STATUS_VALUES: list[str] = [
    STATUS_SAVED,
    STATUS_APPLIED,
    STATUS_CLOSED,
    STATUS_REJECTED,
    STATUS_DECLINED,
]
```

Then in `pages/1_Opportunities.py` line ~417, change:

```python
# Before
config.STATUS_VALUES

# After
config.MANUAL_STATUS_VALUES
```

This applies ONLY to the edit form selectbox (`key="edit_status"`), NOT to:
- The filter selectbox on Opportunities page (`key="filter_status"`) — keep all statuses there
- The filter selectbox on Applications page (`key="apps_filter_status"`) — keep all statuses there
- Any other reference to `STATUS_VALUES`

## Edge cases handled

- User at `[INTERVIEW]` who deleted all interviews → can manually select `[APPLIED]` to revert
- User at `[OFFER]` who wants to undo → can select `[APPLIED]` (rare edge case, acceptable)
- Positions already at `[INTERVIEW]` or `[OFFER]` when loaded into the edit form → the selectbox won't contain their current status. Handle this by computing the index safely: if the current status isn't in `MANUAL_STATUS_VALUES`, default to index 0 (or keep the current status displayed read-only). The simplest approach: temporarily prepend the current status to the options list if it's not already in `MANUAL_STATUS_VALUES`, so the form loads correctly but the user can only move to a manual status.

## Display logic for current-status edge case

In `pages/1_Opportunities.py` around line 342–383 where `safe_status` is computed and passed as the selectbox default:

```python
# Build the options list for the status selectbox
_edit_status_options = config.MANUAL_STATUS_VALUES
if safe_status not in config.MANUAL_STATUS_VALUES:
    # Position is at an auto-promoted status (INTERVIEW/OFFER);
    # include it so the form loads with the correct current value,
    # but the user can move away from it (and can't move back).
    _edit_status_options = [safe_status] + config.MANUAL_STATUS_VALUES
```

Then use `_edit_status_options` instead of `config.STATUS_VALUES` in the selectbox.

## Tests

1. Update any test that asserts the edit form status selectbox options to expect `MANUAL_STATUS_VALUES` (or the augmented list when current status is INTERVIEW/OFFER)
2. Add a test: position at `[INTERVIEW]` → edit form shows `[INTERVIEW]` as current + manual statuses; saving with `[APPLIED]` works
3. Add a test: position at `[SAVED]` → edit form does NOT show `[INTERVIEW]` or `[OFFER]` in options
4. Existing filter selectbox tests should remain unchanged

## Files to modify

- `config.py` — add `MANUAL_STATUS_VALUES`
- `pages/1_Opportunities.py` — edit form selectbox logic (~lines 342–420)
- `tests/test_opportunities_page.py` — update/add tests for the edit selectbox options
- `tests/test_config.py` — add assertion that `MANUAL_STATUS_VALUES ⊂ STATUS_VALUES`
