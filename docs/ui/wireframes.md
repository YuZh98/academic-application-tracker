# UI Wireframes

ASCII layout sketches, one per page. **Intent-only** — not pixel-exact.
Column widths, element sizes, and character-grid alignment are
representative of visual intent and will differ from Streamlit's
rendered output.

For the data sources, widget behaviour, and empty-state rules that
back each layout, see
[DESIGN.md §8 UI Design](../../DESIGN.md#8-ui-design--page-by-page).
Each section below cross-links its matching DESIGN sub-section.

---

## Dashboard

Page source: `app.py`. See
[DESIGN.md §8.1](../../DESIGN.md#81-apppy--dashboard-home).

```
╔════════════════════════════════════════════════════════════════╗
║  Postdoc Tracker                                               ║
╠══════════════╦══════════════╦══════════════╦═══════════════════╣
║  12          ║  4           ║  2           ║  May 3 · MIT      ║
║  Tracked ⓘ  ║  Applied     ║  Interview   ║  Next Interview   ║
║              ║              ║              ║                   ║
╠══════════════╩══════════════╩══════════════╩═══════════════════╣
║                             ║                                  ║
║  Application Funnel         ║   Materials Readiness            ║
║                             ║                                  ║
║  Saved       ████████  8    ║                                  ║
║  Applied     ██████    4    ║  Ready to submit:  3             ║
║  Interview   ████      2    ║  ███                             ║
║  Offer       ██        1    ║                                  ║
║  [+ Show all stages]        ║  Still missing:    5             ║
║                             ║  █████                           ║
║                             ║                                  ║
║                             ║  [→ Opportunities page]          ║
║                             ║                                  ║
╠═════════════════════════════╩══════════════════════════════════╣
║  Upcoming (next 30 days)                                       ║
║                                                                ║
║  Apr 24  Stanford BioStats   Saved      deadline    9d  🔴     ║
║  May 3   Stanford BioStats   Applied    Interview  18d         ║
║  May 15  MIT CSAIL           Saved      deadline   30d         ║
║                                                                ║
╠════════════════════════════════════════════════════════════════╣
║  Recommender Alerts                                            ║
║                                                                ║
║  ⚠  Dr. Smith  →  Stanford, MIT CSAIL  (asked 14 days ago)     ║
║  ✓  Dr. Jones  →  Stanford             (submitted Apr 20)      ║
╚════════════════════════════════════════════════════════════════╝
```

---

## Opportunities

Page source: `pages/1_Opportunities.py`. See
[DESIGN.md §8.2](../../DESIGN.md#82-pages1_opportunitiespy--positions).

```
╔════════════════════════════════════════════════════════════════╗
║  Opportunities                                                 ║
║                                                                ║
║  ▼ Quick Add  ──────────────────────────────────────────────  ║
║  │ Position Name*  │ Institute  │ Field  │ Deadline  │Priority║
║  │ ______________ │ __________ │ ______ │ 📅 date   │ High ▼ ║
║  │ Link: ___________________________ [ + Add Position ]       ║
║  └─────────────────────────────────────────────────────────── ║
║                                                                ║
║  Filter: Status [All ▼]  Priority [All ▼]  Field [________]   ║
║                                                                ║
║  Position Name        Institute  Priority   Status    Due      ║
║  ────────────────────────────────────────────────────────────  ║
║  Stanford BioStats    Stanford   🟡 High   Applied   ——        ║
║  MIT CSAIL Postdoc    MIT        🟡 High   Saved     May 15    ║
║  ··· (click row to expand) ···                                 ║
║                                                                ║
║  ┌──── Stanford BioStats Postdoc  ·  Applied  ─────────────┐   ║
║  │  [ Overview ] [ Requirements ] [ Materials ] [ Notes ]   │  ║
║  │  ─────────────────────────────────────────────────────── │  ║
║  │  (tab content — full edit form fields)                   │  ║
║  │  [ Save Changes ]                                        │  ║
║  └──────────────────────────────────────────────────────────┘  ║
║  [ Delete ]                                                    ║
╚════════════════════════════════════════════════════════════════╝
```

---

## Applications

Page source: `pages/2_Applications.py`. See
[DESIGN.md §8.3](../../DESIGN.md#83-pages2_applicationspy--progress).

```
╔════════════════════════════════════════════════════════════════╗
║  Applications                                                  ║
║                                                                ║
║  Filter: Status [Active ▼]                                     ║
║                                                                ║
║  Position           Applied    Recs  Confirmation   Response   Result   ║
║  ───────────────────────────────────────────────────────────────────── ║
║  Stanford BioStats  Apr 18     ✓     ✓ Apr 19       Interview  Pending ║
║  MIT CSAIL          —          —     —              —          Pending ║
║                                                                ║
║  ┌──── Stanford BioStats Postdoc ──────────────────────────┐  ║
║  │  Applied: Apr 18       All recs submitted: ✓            │  ║
║  │  Confirmation: ✓  (received Apr 19)                     │  ║
║  │  Response type: Interview Invite ▼  Date: Apr 22        │  ║
║  │  ──────  Interviews  ──────                             │  ║
║  │  1.  📅 May 3    Video    (notes)         [ Edit ]      │  ║
║  │  2.  📅 May 17   Onsite   (notes)         [ Edit ]      │  ║
║  │  [ + Add another interview ]                            │  ║
║  │  ──────                                                  │  ║
║  │  Result notify date: 📅 ——  Result: Pending ▼           │  ║
║  │  Notes: ___________________________________  [ Save ]   │  ║
║  └──────────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════════╝
```

**Filter selectbox (Phase 5 T1-B).** The `Status` filter offers, in
display order: `Active` (default — excludes `STATUS_FILTER_ACTIVE_EXCLUDED
= {STATUS_SAVED, STATUS_CLOSED}`), `All`, then each `STATUS_VALUES`
entry rendered via `STATUS_LABELS`. Sentinel labels (`Active`, `All`)
fall through `format_func=STATUS_LABELS.get(v, v)` because they aren't
in `STATUS_LABELS`.

**Confirmation column inline cell text (Phase 5 T1-C, DESIGN §8.3 D-A
amendment).** Streamlit 1.56's `st.dataframe` does not expose a
per-cell tooltip API; the column folds the original `Received {ISO date}`
tooltip into inline cell content. Three states:

| `confirmation_received` | `confirmation_date` | Cell text |
|---|---|---|
| `0` | — | `—` |
| `1` | `2026-04-19` | `✓ Apr 19` |
| `1` | NULL | `✓ (no date)` |

Full resolution + four-option comparison in
[`reviews/phase-5-tier1-review.md`](../../reviews/phase-5-tier1-review.md)
Q3 + new gotcha #16 in
[`docs/dev-notes/streamlit-state-gotchas.md`](../dev-notes/streamlit-state-gotchas.md).

**Phase 5 status (2026-04-30).** T1 ships the **page shell** only —
`set_page_config(layout="wide")`, title, status filter, and the
read-only six-column table sorted `deadline_date ASC NULLS LAST,
position_id ASC`. The detail card (T2) and inline interview list (T3)
are pending; their wireframe appearance below remains the contract
for those tiers.

---

## Recommenders

Page source: `pages/3_Recommenders.py`. See
[DESIGN.md §8.4](../../DESIGN.md#84-pages3_recommenderspy--recommenders).

```
╔════════════════════════════════════════════════════════════════╗
║  Recommenders                                                  ║
║                                                                ║
║  ── Pending Alerts ─────────────────────────────────────────  ║
║  ⚠  Dr. Smith  (PhD Advisor)  ·  asked 14 days ago            ║
║     → Stanford BioStats (due May 1)                           ║
║     → MIT CSAIL Postdoc (due May 15)                          ║
║     [ Compose reminder email ]                                 ║
║                                                                ║
║  ── All Recommenders ───────────────────────────────────────  ║
║  Filter by position: [All ▼]   Filter by recommender: [All ▼] ║
║                                                                ║
║  Position         Recommender   Asked    Confirmed  Submitted  ║
║  ──────────────────────────────────────────────────────────── ║
║  Stanford Bio     Dr. Smith     Apr 10   ✓          ——         ║
║  Stanford Bio     Dr. Jones     Apr 10   ✓          Apr 20 ✓   ║
║  MIT CSAIL        Dr. Smith     Apr 12   ✓          ——         ║
║                                                                ║
║  [ + Add recommender for position ▼ ]                         ║
╚════════════════════════════════════════════════════════════════╝
```

---

## Export

Page source: `pages/4_Export.py`. See
[DESIGN.md §8.5](../../DESIGN.md#85-pages4_exportpy--export).

```
╔════════════════════════════════════════════════════════════════╗
║  Export                                                        ║
║                                                                ║
║  Markdown files are auto-exported after every data change.     ║
║  Use this page to trigger a manual export or download files.   ║
║                                                                ║
║  [ Regenerate all markdown files ]                             ║
║                                                                ║
║  ── Download ───────────────────────────────────────────────  ║
║  [ ⬇ OPPORTUNITIES.md ]   Last generated: <file mtime>         ║
║  [ ⬇ PROGRESS.md ]        Last generated: <file mtime>         ║
║  [ ⬇ RECOMMENDERS.md ]    Last generated: <file mtime>         ║
╚════════════════════════════════════════════════════════════════╝
```
