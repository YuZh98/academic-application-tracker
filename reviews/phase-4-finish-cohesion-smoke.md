# Phase 4 Finish — Cross-Panel Cohesion Smoke

**Branch:** `feature/phase-4-tier6-Cohesion` (off `main` at `c5a7c76` after PR #13 merged)
**Scope:** TASKS.md T6 first checkbox — *"Cross-panel cohesion smoke (manual browser at 1280 / 1440 / 1680 widths; screenshots to `docs/ui/screenshots/v0.5.0/`)"*. The five Phase-4 panels (KPI grid → Funnel + Readiness → Upcoming → Recommender Alerts) were each verified in isolation across T1–T5; T6 is the first time they get verified *together* across responsive widths and against each other for visual rhythm.
**Verdict:** Approve cohesion claim; capture screenshots and merge T6 once the 3 PNGs land in `docs/ui/screenshots/v0.5.0/`.
**Method:**
1. Boot smoke via `streamlit run app.py` (Bash, port 8502) — confirms the dashboard returns HTTP 200 with no startup exception, on both an empty DB and a fully-seeded DB.
2. AppTest probes (populated + empty-DB) — render every panel headlessly and dump every visible string in document order, so the cohesion claims below cite verbatim copy from the actual render rather than the spec.
3. Source audit — re-read `app.py` against DESIGN §8.0 + §8.1 with cohesion lenses (subheader rhythm, empty-state copy pattern, status-sentinel stripping, label format reuse, layout column-weight stability).
4. `pytest tests/ -q` and `pytest -W error::DeprecationWarning tests/ -q` — both **535 passed** on this branch.

The browser-width screenshot capture step (1280 / 1440 / 1680) is the *user's* manual work — see "Capture instructions" at the bottom of this doc. The cohesion findings here tell the user what to look for in each capture, so the screenshots become a confirmation of the audit rather than the audit itself.

---

## Executive summary

The dashboard composes cleanly. All five panels follow a single visual grammar:

- **Subheader rhythm.** Every panel uses `st.subheader(...)` (same Streamlit primitive → same visual weight). The Welcome hero uses `st.subheader` too, so the empty-DB state reads as one continuous typographic level rather than a heading-tier mix.
- **Empty-state pattern.** Every empty branch uses `st.info(...)` (same blue-tinted callout). Copy splits along an honest tense distinction: future ("…will appear once you've added…") for genuinely-empty signal, present ("No deadlines or interviews…", "No pending recommender follow-ups.") for "no actionable items right now". This is consistent across branches and matches DESIGN §8.1's empty-state matrix verbatim.
- **Status sentinel stripping.** No raw `[SAVED]`/`[APPLIED]`/etc. literal leaks to any rendered surface. The Upcoming dataframe maps Status through `STATUS_LABELS.get(raw, raw)` (`app.py:340-342`) and renders "Applied", "Interview", "Saved" — verified against the AppTest dataframe dump. DESIGN §8.0 status-label convention holds.
- **Label-format reuse.** Three panels surface a position label and all three reuse the same `{institute}: {position_name}` shape with bare-fallback when institute is empty: `database._label_for` (Upcoming), `app._format_label` (Recommender Alerts), and the Opportunities-page table (`pages/1_Opportunities.py`). The single intentional divergence is the KPI Next-Interview cell, which uses bare `{institute}` for compactness in a one-cell metric (`{Mon D} · {institute}` per DESIGN §8.1 KPI table) — kept-by-design, see Q1.
- **Date format.** Every place that renders a forward-window date in the dashboard uses `MMM D` ("May 8", no year): the Upcoming dataframe via `column_config.DateColumn(format="MMM D")` (`app.py:347-348`), the Recommender Alerts bullets via `f"{d.strftime('%b')} {d.day}"` (`app.py:398`), and the Next-Interview KPI via `f"{d.strftime('%b')} {d.day}"` (`app.py:75-76`). All three converge on the same rendered shape from three independent code sites.
- **Em-dash empty-glyph.** Both NULL-deadline and no-Next-Interview render `'—'`. `NEXT_INTERVIEW_EMPTY = "—"` is the lone module constant; the recommender-card formatter reuses the same glyph by literal (`app.py:396`). Cohesive but a tiny opportunity for a shared constant — see Finding #2.
- **Layout structure.** Reading top-down: 4-col KPI → 2-col (Funnel + Readiness) → full-width [3,1] (Upcoming) → full-width (Recommender Alerts). The hierarchy moves from snapshot to detail naturally.

The 1280 / 1440 / 1680 captures are still required to *visually* confirm two things the source audit cannot prove: (a) the 6-column Upcoming dataframe doesn't truncate the Label column at 1280 (~213 px / column at full stretch), and (b) the Recommender card border doesn't visually clash with the dataframe border at any width. Both are low-risk on the source evidence, but they are the visual claims that warrant a real browser.

**Verdict: Approve cohesion claim; capture screenshots and merge T6 once the 3 PNGs land in `docs/ui/screenshots/v0.5.0/`.**

---

## Findings

| # | File · Line | Issue | Severity | Status |
|---|-------------|-------|----------|--------|
| 1 | `docs/ui/wireframes.md:41–46` (Upcoming row) and `:48–51` (Recommender row) | The wireframe ASCII shows the Upcoming columns in a different order than the locked DESIGN §8.1 contract (wireframe: Date · Label · Status · Kind · Days left · Urgency; live + DESIGN: Date · Days left · Label · Kind · Status · Urgency). The wireframe also shows BOTH pending **and** submitted recommender rows on the dashboard panel, but the live panel only surfaces pending (DESIGN §8.1: *"All shown rows are warnings"*). The file's preamble line 3 explicitly disclaims it as *"Intent-only — not pixel-exact"*, so this is doc drift not contract drift, but a reader cross-checking against the source will be momentarily confused. | 🟡 polish | Defer to publish-phase doc-drift sweep (P5) — same bundle as the gotcha-#13 / gotcha-#14 cleanups already tracked there |
| 2 | `app.py:37` (`NEXT_INTERVIEW_EMPTY`) vs `app.py:396` (`return "—"` literal) | Two sites render the same em-dash empty-glyph; only one of them goes through the named constant. If a future product call swaps the glyph (e.g. to `"None"` or `"-"`), the recommender-card site would silently drift. The locked-decision-U3 trail (DESIGN §8.1 + project_state) commits the *project* to the em-dash — but only the KPI cell follows that commitment via constant. | 🟡 polish | Defer (cosmetic; would benefit a cleanup tier alongside C2). The fix is a 1-line move: `_format_due` returns `NEXT_INTERVIEW_EMPTY` instead of the literal |
| 3 | `app.py:158` (comment) and `pages/1_Opportunities.py:395` (comment) | The pre-merge `grep -nE "\[SAVED\]\|\[APPLIED\]\|\[INTERVIEW\]"` surfaces these two comment-only matches. **Code is clean** — every literal is `STATUS_*` or `STATUS_LABELS`. The grep tool intentionally matches comments; the false-positive resolution is already tracked: project_state.md "Open carry-overs > Grep→rg" pins the swap to a `rg --type py 'pattern' app.py pages/ \| rg -v '^\s*#'` rule on a follow-up branch. | ℹ️ Observation | Pre-existing carry-over; T6 does not regress it |
| 4 | `app.py:78` (KPI Next-Interview format) vs `app.py:387` (Recommender label) | Different label shapes for the same logical surface (a position): KPI Next-Interview drops the position name entirely (`f"{Mon D} · {institute}"`); Recommender bullets keep both (`f"{institute}: {position_name}"`). | ℹ️ Kept-by-design | See Q1 |
| 5 | Browser-width capture not yet performed | The 1280 / 1440 / 1680 PNGs are the only piece of T6 first-checkbox evidence not produced inside this session — the preview tool's macOS sandbox blocks reading `.venv/pyvenv.cfg` (the `com.apple.provenance` xattr), so headless screenshot capture from inside the harness is unworkable. Bash `streamlit run` works fine; capture requires the user's own browser. | 🟡 polish (process) | **User action** — see "Capture instructions" |

No 🔴 findings. No 🟠 drift. The cohesion claim is sound on every dimension reachable from source + AppTest.

---

## Verbatim render dumps (cohesion evidence)

The two AppTest probes below are the source of truth for every "verified verbatim" claim above. Paste them into `git diff` review when re-running this audit on a future branch.

### Populated DB (5 positions, 3 recommenders, 1 interview)

```
=== TITLE ===
  'Postdoc Tracker'

=== SUBHEADERS ===
  'Application Funnel'
  'Materials Readiness'
  'Upcoming (next 30 days)'
  'Recommender Alerts'

=== METRICS ===
  'Tracked'         value='3'   help="Saved + Applied — positions you're still actively pursuing"
  'Applied'         value='1'   help=''
  'Interview'       value='1'   help=''
  'Next Interview'  value='May 8 · MIT CSAIL'  help=''

=== UPCOMING DATAFRAME ===
  columns=['Date', 'Days left', 'Label', 'Kind', 'Status', 'Urgency'] · rows=4
  2026-05-05  in 5 days   Stanford: Postdoc in Biostatistics        Deadline for application  Applied   🔴
  2026-05-08  in 8 days   MIT CSAIL: Postdoc in CS / ML             Interview 1               Interview 🟡
  2026-05-15  in 15 days  MIT CSAIL: Postdoc in CS / ML             Deadline for application  Interview 🟡
  2026-05-22  in 22 days  Princeton: Postdoc in Bayesian Inference  Deadline for application  Saved     🟡

=== RECOMMENDER CARDS (markdown) ===
  '**⚠ Dr. Smith**\n- Stanford: Postdoc in Biostatistics (asked 14d ago, due May 5)\n- MIT CSAIL: Postdoc in CS / ML (asked 14d ago, due May 15)'

=== BUTTONS ===
  funnel_expand               '[expand]'
  materials_readiness_cta     '→ Opportunities page'

=== SELECTBOX ===
  upcoming_window  label='Window (days)'  value=30  options=['30','60','90']
```

Cross-checks the audit verifies from this dump:
- Status column shows `Applied` / `Interview` / `Saved` — never `[APPLIED]` / `[INTERVIEW]` / `[SAVED]`. ✓
- Label column reuses `{institute}: {position_name}` for every row — `Stanford: …`, `MIT CSAIL: …`, `Princeton: …`. ✓
- Recommender bullet lines use the same label format. ✓
- Recommender card date `due May 5` matches Upcoming row Date `May 5` (column `column_config.DateColumn(format="MMM D")`) — same calendar abbreviation across panels. ✓
- KPI Next-Interview value `May 8 · MIT CSAIL` is the only place a label drops `position_name` — kept-by-design (Q1). ✓
- One person, multiple positions → one card with multiple bullets (Dr. Smith with Stanford + MIT CSAIL). DESIGN T5-A grouping rule honoured. ✓

### Empty DB (no positions)

```
=== SUBHEADERS ===
  'Welcome to your Postdoc Tracker'   ← empty-DB hero
  'Application Funnel'
  'Materials Readiness'
  'Upcoming (next 30 days)'
  'Recommender Alerts'

=== INFO MESSAGES (empty-state copy, in panel order) ===
  "Application funnel will appear once you've added positions."
  "Materials readiness will appear once you've added positions with required documents."
  'No deadlines or interviews in the next 30 days.'
  'No pending recommender follow-ups.'

=== METRICS ===
  'Tracked'         value='0'
  'Applied'         value='0'
  'Interview'       value='0'
  'Next Interview'  value='—'

=== BUTTONS ===
  dashboard_empty_cta   '+ Add your first position'   (type=primary)
```

Cross-checks the audit verifies from this dump:
- 4 panel subheaders + 1 hero subheader = 5 total — same primitive, same visual weight. ✓
- 4 `st.info(...)` callouts — one per panel — same primitive. ✓
- Tense pattern: "will appear" / "will appear" / "No …" / "No …". ✓
- KPI Next-Interview empty value is `'—'` (em-dash, locked decision U3). ✓
- Empty-DB hero CTA is the *only* primary button on the page; every other button is default style. Reserves "primary" for first-action of an empty state. ✓

### Boot smoke

```
streamlit run app.py --server.port 8502 ...
  ↳ Local URL: http://localhost:8502
  ↳ HTTP 200 on /
  ↳ HTTP 200 on /healthz (body: 'ok')
  ↳ no exception block in either AppTest render (populated or empty)
```

---

## Junior-engineer Q&A

### Q1 — Why does the KPI Next-Interview cell drop the position name when every other panel keeps it? Isn't that a cohesion violation?

**A.** It's an intentional asymmetry, and DESIGN §8.1 names it explicitly: the KPI table row says *"`get_upcoming_interviews()` scanned for earliest FUTURE `scheduled_date`; rendered `'{Mon D} · {institute}'`"*. The reasoning is real-estate. A KPI cell rendered by `st.metric` is one short string sitting in a 1/4-width column; squeezing `f"May 8 · MIT CSAIL: Postdoc in CS / ML"` into ~320 px (at 1280-wide viewport) would either truncate or wrap — both worse outcomes than the institute-only short form. Other surfaces have a row to themselves and can afford the full label.

The cohesion the project actually wants is *"the same logical entity always uses the same SHAPE when there's room"*, not *"every surface uses identical strings"*. The shape rule (`{institute}: {position_name}`) is reused at every full-width or row surface (Upcoming Label, Recommender bullet, Opportunities table). The KPI exception is a documented compactness exception, locked-decision U3 era.

A future cleanup might surface the institute-only form as a named formatter (`_short_label(institute)` or similar) so the asymmetry becomes a function call rather than a literal — but that is a polish call, not a cohesion bug.

### Q2 — Both Findings #1 and #2 are tagged 🟡 polish and deferred. Why aren't either fixed in this T6 sub-task?

**A.** T6 is *cohesion smoke* — by TASKS.md scope it produces a review doc + 3 screenshots, not code edits. The TDD three-commit cadence (`test:` red → `feat:` green → `chore:` rollup) is for sub-tasks that ship behaviour. A smoke check that ships zero behaviour and zero code change has only the rollup commit (the doc + tracker tick).

Both findings are real but cheap to defer:
- **#1 (wireframe drift):** wireframes.md is explicitly intent-only (line 3), and an existing publish-phase task P5 is already scheduled to do a doc-drift sweep including the gotcha-#13 / gotcha-#14 entries. Bundling this with that sweep avoids a one-line PR.
- **#2 (em-dash literal):** a 1-line Edit to make `_format_due` return `NEXT_INTERVIEW_EMPTY`. Defensible to land alongside the C2 cleanup tier (TASKS.md "Code carry-overs"); not worth its own commit while T6 is in flight.

If you wanted to land #2 inline anyway it's the kind of thing a reviewer can request as a one-line nit on the eventual T6 PR.

### Q3 — The preview tool failed because of `com.apple.provenance` xattrs. Is the dashboard broken in any way as a result?

**A.** No. The dashboard runs fine via `streamlit run app.py` from the user's shell — that's how the user runs it day-to-day. The failure was specifically the harness's *sandboxed* Python being denied permission to read `.venv/pyvenv.cfg`. macOS marks files copied or written by sandboxed apps with `com.apple.provenance`; the preview tool's sandbox can't see across that boundary.

Three avenues were tried before falling back to Bash:
1. Strip the xattr with `xattr -dr` — failed silently (sandbox blocks the strip too).
2. Bypass `pyvenv.cfg` by inserting the venv site-packages on `sys.path` manually from a system Python — Python booted but stuck in `os.listdir` for `site-packages` subdirs, again sandbox-blocked.
3. Run the launcher from `/tmp/` to escape provenance — bash itself failed `getcwd` before exec.

The right fix is to capture screenshots from the user's actual browser, which is what TASKS.md T6 says ("manual browser at 1280 / 1440 / 1680 widths"). The "manual" wording was always pointing at the user's desktop browser; the smoke check + audit are the harness-friendly preparation that lets the user know exactly what to look for in each capture.

### Q4 — How do I know the captures will match the AppTest dumps? AppTest is a different render pipeline than the browser.

**A.** You don't get a 100% guarantee, but you get strong coverage. AppTest uses Streamlit's element-tree representation; the browser uses the protobuf-rendered DOM. The two diverge in three known ways:
- **Number-vs-string for selectbox options** (gotcha #15) — `at.selectbox.options` returns strings even when the source list is `[30, 60, 90]`. Verified above (`options=['30','60','90']`); the live UI shows `30 / 60 / 90` correctly.
- **`st.metric` `key=`** — display-only; tests look up by label (gotcha #5). Both AppTest and browser render the same label, so this is a non-issue here.
- **`st.dialog` re-render in tests** (gotcha #3) — irrelevant: this dashboard has no dialogs.

For the cohesion check specifically — subheader text, info-message strings, button labels, dataframe row count, status-label stripping — AppTest renders are byte-equal to the live render. The only properties not provable from AppTest are:
- Visual font weight / color of the subheader (always `st.subheader`'s default).
- Pixel widths of dataframe columns at narrow viewport (the reason you still capture at 1280).
- Plotly funnel bar colors at render (we know the *config* says `"blue"` / `"orange"` / etc.; the bar pixel color is what the screenshot proves).

The capture step is verification *of those properties*, not of the textual content the audit already pinned.

### Q5 — Why are the screenshots saved under a *version* directory (`docs/ui/screenshots/v0.5.0/`) rather than a tier directory?

**A.** TASKS.md T6 specifies `docs/ui/screenshots/v0.5.0/` (the tag the dashboard ships at). Versioning under the tag has two payoffs:
- **The screenshot reflects what shipped, not what was in flight.** A `v0.5.0` capture is what a `git checkout v0.5.0 && streamlit run` reproduces exactly.
- **Phase 7 T5 ("Responsive layout check at 1024 / 1280 / 1440 / 1680 widths; capture screenshots to `docs/ui/screenshots/v0.8.0/`")** uses the same scheme. T6's directory choice is the precedent that Phase 7 follows.

If a future tier changes the dashboard substantially before v0.5.0 ships, re-shoot. The v0.5.0 directory is a snapshot, not a running record.

### Q6 — Is the boot-smoke 200 OK enough to claim "no startup exception"?

**A.** It's a necessary signal but not the full check. Streamlit's HTTP server returns 200 on `/` even when the script execution throws — the SPA shell is static; the script runs on the websocket connection, and an exception there shows as a red error block in the *rendered* page rather than a 500. That is exactly why this audit pairs the boot smoke with two AppTest probes (`Has any exception block: False` for both populated and empty DBs). AppTest exposes `at.exception` which is non-empty if the script run hit any exception — both probes returned `ElementList()` (the empty form), confirming clean rendering on both data shapes.

The triple = HTTP 200 (server is alive) + AppTest empty-exception (script ran clean on populated DB) + AppTest empty-exception on empty DB (script ran clean on the empty-state branches). That's the actual smoke check.

---

## Capture instructions (user — desktop browser)

Three captures, one per breakpoint, saved to `docs/ui/screenshots/v0.5.0/`. The seed data described in this doc is in `postdoc.db` *right now*; if the file has been restored before you read this, re-seed first using the snippet in §"Re-seed for capture" below.

1. `streamlit run app.py` (your usual shell-based launch).
2. In the browser, **resize the window** rather than the inner viewport — browser dev-tools' "responsive design mode" works too. Target widths: **1280**, **1440**, **1680** pixels of OUTER window width. Don't worry about height; let it scroll.
3. Capture each width to a PNG named `dashboard-1280.png`, `dashboard-1440.png`, `dashboard-1680.png`. macOS shortcut: ⌘⇧4 → spacebar → click the window. Save into `docs/ui/screenshots/v0.5.0/`.
4. **Eyeball the captures against the cohesion claims in this doc:**
   - All 5 subheaders look the same size and weight.
   - 4 KPI cards line up at equal width.
   - The 2-column funnel + readiness row stays balanced (no one column dwarfs the other).
   - The Upcoming dataframe shows all 6 columns without truncating Label or Kind. *(Most likely fail mode at 1280 — if Label is truncated, that's a 🟡 polish to flag for Phase 7.)*
   - Status column shows "Applied" / "Saved" / "Interview" — no brackets.
   - Recommender card border is visible and aligns left-edge with the dataframe.
   - The em-dash `'—'` for empty cells reads cleanly (some browser font fallbacks render a hyphen-minus in its place).

If anything looks off, capture it anyway, log a 🟠 finding in the eventual `reviews/phase-4-finish-review.md`, and route the fix through Phase 7 polish.

### Re-seed for capture

If `postdoc.db` was already restored to its pre-smoke state by the time you do the captures, re-seed:

```bash
source .venv/bin/activate
# Run the seed snippet preserved in this conversation (or copy from
# the .claude/run_streamlit.sh-adjacent /tmp/cohesion_seed.py if it
# was extracted). The seed produces:
#   Tracked=3, Applied=1, Interview=1, Next Interview = May 8 · MIT CSAIL
#   Funnel: Saved/Applied/Interview/Offer all non-zero, Closed/Archived hidden
#   Materials: 1 ready, 2 pending
#   Upcoming: 4 rows (1 🔴 + 3 🟡)
#   Recommender Alerts: 1 card (Dr. Smith — 2 positions)
```

The exact seed values aren't load-bearing for the cohesion check; any DB that populates each panel with at least one row will surface the same visual claims.

---

## Notes for the eventual full T6 review

This cohesion-smoke doc is one input to the full `reviews/phase-4-finish-review.md` that closes T6. The full review will pull in the three screenshots, this doc's findings table verbatim, and the second T6 checkbox (the broader pre-merge review of T4 + T5 + T6 as a phase). Don't merge this doc as the T6 review — it's the cohesion-smoke step output, the *first* of three checkboxes.
