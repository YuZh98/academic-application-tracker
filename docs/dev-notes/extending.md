# Extending the Tracker — Step-by-Step Recipes

Each recipe below is a concrete walkthrough for a common extension.
For the **concise summary** of what editing each `config.py` constant
affects (architectural "what → where"), see
[DESIGN.md §5.3 Extension recipes](../../DESIGN.md#53-extension-recipes).
This file is the **step-by-step companion** — how to actually do it.

The tracker is designed so most extensions touch only `config.py`;
`init_db()` auto-migrates the schema on next app start for additive
changes. If a recipe asks you to touch more than one file, that's a
sign the extension is architectural, not a routine config change.

---

## Add a new requirement document

1. Open `config.py`.
2. Append one tuple to `REQUIREMENT_DOCS`:
   ```python
   ("req_portfolio", "done_portfolio", "Portfolio"),
   ```
3. Restart the app. `init_db()` adds the two columns via `ALTER TABLE`.
4. The Requirements tab, Materials tab, materials readiness query, and markdown export pick it up without further code changes.

---

## Add a new vocabulary option

1. Append to the relevant list (`WORK_AUTH_OPTIONS`, `SOURCE_OPTIONS`, `RESPONSE_TYPES`, `RESULT_VALUES`, `RELATIONSHIP_TYPES`, `INTERVIEW_FORMATS`, etc.).
2. Selectboxes pick the new value up on next render.
3. No DB change — column is plain TEXT.

---

## Add a new pipeline status

1. Append to `STATUS_VALUES` and add the matching `STATUS_<name>` alias.
2. Add one entry each to `STATUS_COLORS` and `STATUS_LABELS`.
3. Decide which `FUNNEL_BUCKETS` entry it belongs in — extend an existing bucket's tuple or add a new `(label, (raw,...), color)` 3-tuple in the right display position.
4. If the new status should be hidden by default on the funnel, add its bucket label to `FUNNEL_DEFAULT_HIDDEN`.
5. If terminal (no downstream pipeline stage), append to `TERMINAL_STATUSES`.
6. No DB change; status column is TEXT.

---

## Rename a pipeline status

1. Edit `STATUS_VALUES[i]`, the matching `STATUS_<name>` alias, and the keys in `STATUS_COLORS` / `STATUS_LABELS` / `FUNNEL_BUCKETS` / `TERMINAL_STATUSES`.
2. Write a `Migration:` note in `CHANGELOG.md` with the one-shot SQL:
   ```sql
   UPDATE positions SET status = '<new>' WHERE status = '<old>';
   ```
3. Schema DDL is config-driven (`DEFAULT` reads `config.STATUS_VALUES[0]`), so renaming the first status value propagates without DDL edits.

---

## Add a new interview format

1. Append to `INTERVIEW_FORMATS`.
2. The Applications page's interview-row dropdown picks it up on next render.

---

## Switch the tracker profile

See [DESIGN.md §12.1](../../DESIGN.md#121-general-job-tracker--profile-expansion). v1 supports `"postdoc"` only; the hook to add another is in place but not wired.

---

## Change a dashboard threshold

Edit `DEADLINE_ALERT_DAYS` / `DEADLINE_URGENT_DAYS` / `RECOMMENDER_ALERT_DAYS` in `config.py`. The import-time invariants catch inverted thresholds on next import.
