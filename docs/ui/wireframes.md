# UI Wireframes

ASCII layout sketches, one per page. **Intent-only** — not pixel-exact.
Column widths, element sizes, and character-grid alignment are
representative of visual intent and will differ from Streamlit's
rendered output.

For the data sources, widget behaviour, and empty-state rules that
back each layout, see
[DESIGN §8 UI Design](../../DESIGN.md#8-ui-design--page-by-page).
Each section below cross-links its matching DESIGN sub-section.

---

## Dashboard

Page source: `app.py`. See
[DESIGN §8.1](../../DESIGN.md#81-apppy--dashboard-home).

```
╔════════════════════════════════════════════════════════════════╗
║  Academic Application Tracker                                  ║
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
║  Date     Days  Position   Institute  Kind       Status   Urgency ║
║  Apr 24    9d   BioStats   Stanford   deadline   Saved    🔴      ║
║  May 3    18d   BioStats   Stanford   Interview  Applied          ║
║  May 15   30d   CSAIL      MIT        deadline   Saved            ║
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
[DESIGN §8.2](../../DESIGN.md#82-pages1_opportunitiespy--positions).

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
║  Search [________________]  Status [All ▼]  Priority [All ▼]  Field [____]  ║
║                                                                ║
║  Position   Institute  Priority   Status    Due      Urgency  Link  ║
║  ──────────────────────────────────────────────────────────────────  ║
║  BioStats   Stanford   🟡 High   Applied   ——        🔴       🔗    ║
║  Postdoc    MIT        🟡 High   Saved     May 15             🔗    ║
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
[DESIGN §8.3](../../DESIGN.md#83-pages2_applicationspy--progress).

```
╔════════════════════════════════════════════════════════════════╗
║  Applications                                                  ║
║                                                                ║
║  Filter: Status [Active ▼]                                     ║
║                                                                ║
║  Position   Institute  Applied    Recs  Confirmation   Response   Result   ║
║  ───────────────────────────────────────────────────────────────────── ║
║  BioStats  Stanford    Apr 18     ✓     ✓ Apr 19       Interview  Pending ║
║  MIT       CSAIL      —          —      —                —        Pending ║
║                                                                ║
║  ┌──── Stanford BioStats Postdoc ──────────────────────────┐  ║
║  │  Applied: Apr 18       All recs submitted: ✓            │  ║
║  │  Confirmation: ✓  (received Apr 19)                     │  ║
║  │  Response type: Interview Invite ▼  Date: Apr 22        │  ║
║  │  Result notify date: 📅 ——  Result: Pending ▼           │  ║
║  │  Notes: ___________________________________  [ Save ]   │  ║
║  │  ──────  Interviews  ──────                             │  ║
║  │  **Interview 1**                                        │  ║
║  │  📅 May 3      Video ▼      notes______________         │  ║
║  │  [ Save ]                                               │  ║
║  │  [ 🗑️ Delete Interview 1 ]                              │  ║
║  │  ─────────────────────────────────────────────────────  │  ║
║  │  **Interview 2**                                        │  ║
║  │  📅 May 17     Onsite ▼     notes______________         │  ║
║  │  [ Save ]                                               │  ║
║  │  [ 🗑️ Delete Interview 2 ]                              │  ║
║  │  [ + Add another interview ]                            │  ║
║  └──────────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════════╝
```

---

## Recommenders

Page source: `pages/3_Recommenders.py`. See
[DESIGN §8.4](../../DESIGN.md#84-pages3_recommenderspy--recommenders).

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
[DESIGN §8.5](../../DESIGN.md#85-pages4_exportpy--export).

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
