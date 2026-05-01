# Phase 4 — Tier 6 Code Review

**Branch:** `feature/phase-4-tier6-Cohesion` (5 commits ahead of `main`; T4 + T5 already merged via PR #12 / PR #13 → `c5a7c76`)
**Verdict:** Approve, merge after the inline footnote lands and the user supplies the 1280 / 1440 / 1680 PNGs.
**Scope:** T6 — the dashboard's pre-merge close-out, with three checkboxes per `TASKS.md`. Two are addressed on this branch:
  1. **Cross-panel cohesion smoke** (✅) — `reviews/phase-4-finish-cohesion-smoke.md` audits the five panels (KPI grid → Funnel + Readiness → Upcoming → Recommender Alerts) for shared visual grammar across populated and empty-DB renders. PNG captures at 1280 / 1440 / 1680 are user-pending (preview-tool sandbox limitation documented inline).
  2. **Funnel disclosure-toggle polish** (✅) — `[expand]` (one-way) → bidirectional `+ Show all stages` ↔ `− Show fewer stages`, `type="tertiary"`, docked in the funnel subheader row via `st.columns([3, 1])` (mirror of the T4 Upcoming-panel idiom). DESIGN §8.1 amendment locks the new contract; new config invariant #11 pins the dict shape.
  3. **`reviews/phase-4-finish-review.md` + PR + tag `v0.5.0`** (pending) — this per-tier review is one input for that final review; the user's PR + tag work follow.
**Stats:** `app.py` +104/-? (the funnel-toggle rewrite, comment refresh); `config.py` +48 (`FUNNEL_TOGGLE_LABELS` + invariant #11); `tests/test_app_page.py` +611/-? (new 15-test `TestT6FunnelToggle` class + edits to T2B / T2D under the new contract); `tests/test_config.py` +62 (4 invariant-#11 cases); `DESIGN.md` +31 (§5.1 symbol row, §5.2 invariant, §5.3 recipe, §8.1 panel-spec rewrite + visibility-rules rewrite + empty-state-matrix rewrite); `GUIDELINES.md` +2 (§3 sentinels list comment refresh); `TASKS.md` +58 (T6 checkboxes + Recently-done entries + sprint footer); `CHANGELOG.md` +194 (the toggle-polish + cohesion-smoke entries); `roadmap.md` +42 (T4/T5 ship statuses); `docs/ui/wireframes.md` +2 (toggle representation); `docs/ui/screenshots/v0.5.0/.seed-snippet.py` +113 (NEW — re-seed scratch script preserving the cohesion-smoke fixture); `reviews/phase-4-finish-cohesion-smoke.md` +241 (NEW — the cohesion-smoke audit doc itself). **519 → 553 tests passing under both `pytest -q` and `pytest -W error::DeprecationWarning -q`** (+34 net; +15 `TestT6FunnelToggle` + 4 invariant-#11 + edits to existing tier classes − 1 deleted `test_expand_button_hides_after_click`).
**Cadence:** `review` (cohesion smoke) → `test` (red) → `feat` (green) → `chore` (tracker rollup + DESIGN amendment) → `chore` (post-rename doc scrub). Five commits across two T6 sub-tasks; perfect TDD isolation on the toggle replacement; the cohesion smoke is doc-only with no code change.
**Reviewer attitude:** Skeptical. Verify every Streamlit, config, and test claim. Cross-grep DESIGN against the source for every locked string. Pay special attention to the **bidirectional contract** — pre-T6 the toggle was unidirectional and the user reported being trapped in the expanded state; post-T6 the round-trip must be exact (involution under two clicks).

---

## Executive summary

T6 is the largest Phase-4 tier in line-deltas (≈ 1 400 lines across 11 files) and the only tier that **changes behaviour the user explicitly reported as broken**: pre-T6, the funnel `[expand]` button vanished after one click and there was no companion `[collapse]` to return to the focused view. The replacement is a single bidirectional disclosure toggle whose label flips with state (`config.FUNNEL_TOGGLE_LABELS[True/False]`), styled `type="tertiary"` so it reads as a chart control rather than a primary CTA, and docked in the funnel subheader row via `st.columns([3, 1])` — establishing a third use of the *"chart with a control on the right"* idiom (T2 funnel, T4 Upcoming, now T6 funnel-toggle).

The contract is locked at four layers — DESIGN §5.1 symbol row, §5.2 invariant #11, §8.1 panel-specs row, and §8.1 empty-state matrix — with each layer pinning a different facet (label vocabulary, dict shape, placement, branch behaviour). The 15-test `TestT6FunnelToggle` class spans five groups: label correctness in each state (A), bidirectional state + round-trip + branch-(b)↔(c) round-trip (B), source-grep for `st.columns([3, 1])` and `type="tertiary"` (C), empty-state matrix re-pinned under the new contract (D), and CTA-convention symbol cohesion (E). The `test_round_trip_through_branch_b` test is the explicit pin for the user-reported bug fix — pre-T6 no second click was possible.

The cohesion-smoke audit (committed first, before the toggle replacement) verifies cross-panel visual grammar from verbatim AppTest dumps and surfaces a clean cohesion claim across six dimensions. Two 🟡 polish were filed there (wireframe ASCII drift; em-dash literal vs constant); both deferred per the doc's own GUIDELINES §10 defer-if-costly reasoning.

The review surfaces **zero bugs**, **one 🟡 polish fixed inline** (cohesion-smoke render dumps are stale post-toggle-replacement and need a temporal-context footnote), **two 🟡 polish kept-by-design** (test consistency on comment-stripping; class-scope literal duplication), **two 🟢 future-work items** (PNG captures user-pending; phase-name "T6" collision risk with Phase 5 T6), and **one ℹ️ carried-forward observation** (the §6 grep miscount at `pages/1_Opportunities.py:395`, fourth tier in a row).

**Verdict: approve, merge after the inline footnote lands and the user supplies the 1280 / 1440 / 1680 PNGs.**

---

## Findings

| # | File · Line | Issue | Severity | Status |
|---|-------------|-------|----------|--------|
| 1 | `reviews/phase-4-finish-cohesion-smoke.md` lines 79–84 (BUTTONS dump) | The verbatim AppTest dump shows `funnel_expand '[expand]'`, captured before commits 7e5e2f4 / 9221cd8 / bed2904 / 7c68b1c replaced the unidirectional `[expand]` button with the bidirectional toggle. The doc-scrub commit (`7c68b1c`, *"scrub stale [expand]/_expand_funnel refs post-T6 rename"*) updated `app.py` comments, `DESIGN.md`, `GUIDELINES.md`, `TASKS.md`, and `wireframes.md` but did not touch the smoke doc's render dumps. A reader landing on the doc post-merge sees evidence labels that do not match what `streamlit run app.py` will actually render today. | 🟡 polish | **Fixed inline** — added a temporal-context footnote (see Q1) |
| 2 | `tests/test_app_page.py` `TestT6FunnelToggle.test_no_hardcoded_label_literal_in_app_source` (Group A.3) | The test does NOT strip comment lines before grepping — sibling `test_subheader_row_uses_columns_3_1` (C.1) and `test_toggle_uses_tertiary_type` (C.2) both DO. A future maintainer who adds an explanatory comment quoting either label as a string literal would trip A.3 even though the source is structurally fine. The inconsistency is real but the choice is defensible — see Q2. | 🟡 polish | Kept by design (see Q2) |
| 3 | `tests/test_app_page.py` `TestT6FunnelToggle` class scope | `EXPAND_LABEL` / `COLLAPSE_LABEL` literals duplicate `config.FUNNEL_TOGGLE_LABELS[False / True]` rather than referencing them. Drift caught by `test_class_literals_match_config` (A.3a). The duplication is deliberate (collection-time stability) but adds two lines of literal vocabulary the next reader has to mentally unify. | 🟡 polish | Kept by design (see Q3) |
| 4 | `docs/ui/screenshots/v0.5.0/` | The directory exists with `.seed-snippet.py` but the three PNGs (`dashboard-1280.png`, `dashboard-1440.png`, `dashboard-1680.png`) are user-pending. Smoke doc explains why (preview-tool sandbox blocks `.venv/pyvenv.cfg`); user manual capture still required. | 🟢 future | User action — see Q4 |
| 5 | DESIGN §8.4 D-C (Phase 5 T6) and DESIGN §8.1 (Phase 4 T6 amendment) | Both sub-tiers are called "T6" within their respective phases. Comments and CHANGELOG entries say "Phase 5 T6" / "Phase 4 T6" explicitly, but a junior reader skimming a single doc will conflate them. Process risk, not a code defect. | 🟢 future | Naming convention; surface in Phase 5 entry recap |
| 6 | `pages/1_Opportunities.py` : 395 (pre-existing) | The pre-existing `'[APPLIED]'` literal in a docstring-style comment trips the GUIDELINES §6 pre-merge grep. Same hit fourth tier in a row (T3 / T4 / T5 reviews all flagged it). The cohesion-smoke audit also calls it out at Finding #3. | ℹ️ Observation | Carry-over (see Q5) |

---

## Fixes applied in this review

**One fix landed inline:**

`reviews/phase-4-finish-cohesion-smoke.md` — added a one-paragraph footnote at the head of the "Verbatim render dumps" section noting that the dumps were captured at the close of the smoke audit (T6 first checkbox) before the disclosure-toggle replacement landed (T6 second checkbox), and pointing the reader at the post-T6 button label / key. The cohesion claim itself is unaffected by the toggle replacement (cohesion is about cross-panel visual grammar, not the toggle's specific shape) — the footnote preserves the historical narrative without re-running the AppTest probes from a now-different code state.

**Other findings:** all four are documented and deferred. The kept-by-design pair has rationale in Q&A; the 🟢 future items are tracked at the Phase 5 / publish boundary; the §6 grep carry-over is bundled with the same project_state.md "Open carry-overs > Grep→rg" line that has logged it for the prior three tiers.

---

## Junior-engineer Q&A

### Q1 — Why footnote the smoke-doc dumps instead of re-running them?

**A.** Two reasons, both about preserving evidence integrity.

1. **The dumps document a moment in time, not a continuously-fresh state.** When the cohesion-smoke commit landed, the dashboard had `funnel_expand '[expand]'` — that is not stale; that is *what was true* on the branch tip when the audit ran. Mutating the dumps to reflect a later branch state turns the audit from *"this is what we observed"* into *"this is what's true today,"* and the next reader has no way to distinguish historical evidence from forward claims without timestamps.

2. **The cohesion claim is independent of the toggle's specific shape.** The smoke doc verifies six dimensions: subheader rhythm, empty-state pattern, status-sentinel stripping, label-format reuse, date-format reuse, layout hierarchy. None of those six is affected by the `[expand]` → bidirectional-toggle replacement. The toggle's button label is not a cohesion claim — it appears in the BUTTONS dump only as a side-effect of dumping every visible widget. Re-running the probes would produce a fresher dump that reads *exactly the same way* under the cohesion claim, so the test would pass and the audit would still hold. The cost (re-running) and the benefit (a fresher dump that doesn't change the conclusion) are mismatched.

The footnote does the cheaper thing: tells the reader *"this dump is from T6 first-checkbox state; the post-toggle state is described in `reviews/phase-4-Tier6-review.md` Q1 and the CHANGELOG `Changed — Funnel disclosure toggle …` entry."* Forward pointer instead of revisionism.

If a future change *does* break a cohesion dimension (e.g., one panel switches to `st.title` while the others keep `st.subheader`), THAT is when re-running the probes makes sense — the audit is no longer a record but a regression target.

### Q2 — Why doesn't `test_no_hardcoded_label_literal_in_app_source` strip comments like the other source-grep tests do?

**A.** Because it's catching a different failure mode than C.1 / C.2.

C.1 (`test_subheader_row_uses_columns_3_1`) and C.2 (`test_toggle_uses_tertiary_type`) are *count* tests — they assert *"this idiom appears N times in executable code."* Comment lines that *describe* an idiom (e.g., the comment block in `app.py` mentioning `st.columns([3, 1])` to explain the layout) would cause a count overshoot, so stripping comments is necessary for the tests to be precise.

A.3 (`test_no_hardcoded_label_literal_in_app_source`) is a *forbidden-substring* test — it asserts *"this string literal does NOT appear in `app.py` source at all."* The forbidden list contains *quoted* forms like `'"+ Show all stages"'` (with surrounding double-quotes) — i.e., the literal *as it would appear in source code as a string literal*. A casual mention in a comment like `# the label is + Show all stages when collapsed` (no quotes) does NOT match the forbidden substring, because the comment doesn't include the quote characters. So the test already filters out the most likely casual-comment case by virtue of grepping for *quoted* forms.

What the test *would* catch:
- A future maintainer who pastes the literal as a backup string in a defensive `getattr(config, "FUNNEL_TOGGLE_LABELS", {True: "− Show fewer stages"})` — yes, fail. Correct: that defeats the config-as-source-of-truth contract.
- A docstring containing the verbatim string literal `"+ Show all stages"` for documentation — yes, fail. Defensible: the same vocabulary should be one-sourced; a docstring referencing the label by *meaning* (no quotes around the literal) is fine.
- An explanatory comment that quotes the label as a string in backticks: `` # See FUNNEL_TOGGLE_LABELS for the canonical values, e.g. ``"+ Show all stages"`` `` — yes, fail. The test is over-strict here. But the cost of over-strictness is one-line: replace the docstring backtick quote with a value reference.

Stripping comments would weaken the test's "no hardcoded label" guarantee for a marginal convenience. The current shape draws the line at *"the literal must not appear inside source-code quote characters,"* which is the cleanest precise rule. A reviewer can flip the rule with a one-line change if the use-case ever justifies it; today, it doesn't.

### Q3 — Why duplicate `EXPAND_LABEL` / `COLLAPSE_LABEL` at class scope instead of just reading from config?

**A.** Because pytest collection runs class bodies at import time, and config import order is not guaranteed across the suite.

Concretely: `tests/test_app_page.py` imports `config` at module top. When pytest collects the file, every class body executes immediately — including assignments like:

```python
class TestT6FunnelToggle:
    EXPAND_LABEL = config.FUNNEL_TOGGLE_LABELS[False]   # ← runs at collection time
```

If a test ordering / fixture pattern *anywhere else* in the suite mutates `config.FUNNEL_TOGGLE_LABELS` via `monkeypatch.setattr` (the project does this in `TestGetUpcoming.test_urgency_thresholds_resolve_at_call_time` for `DEADLINE_URGENT_DAYS`), the class-scope binding gets the patched value. Subsequent tests using `cls.EXPAND_LABEL` would assert against the *patched* value, not the real one — silently wrong assertions.

Static literals at class scope avoid that trap entirely:

```python
class TestT6FunnelToggle:
    EXPAND_LABEL = "+ Show all stages"   # static; no config dependency at collection
```

The cost is the drift risk — class literal vs config could disagree. That's exactly what `test_class_literals_match_config` (A.3a) catches:

```python
assert config.FUNNEL_TOGGLE_LABELS[False] == self.EXPAND_LABEL, ...
assert config.FUNNEL_TOGGLE_LABELS[True]  == self.COLLAPSE_LABEL, ...
```

A maintainer changing config without updating the test class trips A.3a immediately. The test pair (literal-at-class-scope + drift-pin) is strictly better than the alternative (read-config-at-collection-time, trust nothing patches it) — it's robust under the project's existing monkeypatch pattern *and* it surfaces drift loudly.

This is the same pattern `TestT2BFunnelEmptyState` uses for `EXPAND_LABEL`, with the same reasoning documented inline.

### Q4 — Why are the PNG captures user-pending? Can the harness do anything to help?

**A.** The harness preview tool's macOS sandbox cannot read `.venv/pyvenv.cfg` due to the `com.apple.provenance` extended attribute the sandbox-aware Python runtime checks. Three workarounds were tried and documented in `reviews/phase-4-finish-cohesion-smoke.md` Q3:

1. `xattr -dr com.apple.provenance .venv` — fails silently (sandbox blocks the strip).
2. Bypass `pyvenv.cfg` by inserting `.venv/lib/.../site-packages` on `sys.path` from a system Python — Python boots but `os.listdir` on a sandboxed `site-packages` subdir blocks.
3. Run from `/tmp/` to escape provenance — bash's own `getcwd` fails before exec.

The user's daily flow (`source .venv/bin/activate && streamlit run app.py`) works fine because the user's shell is not sandboxed. So the right path is exactly what `TASKS.md` T6 has always called for: *"manual browser at 1280 / 1440 / 1680 widths"*. The harness has done the cohesion audit and the AppTest verbatim dumps; the user does the visual capture.

The smoke doc's "Capture instructions" section walks through the macOS-specific shortcut (⌘⇧4 → spacebar → click) and lists six visual claims to eyeball against each PNG. The new `.seed-snippet.py` re-creates the canonical fixture data so the user can re-seed before capturing — important if the user has been live-using the tracker since the smoke run and the DB no longer matches the dumps.

### Q5 — Why is `pages/1_Opportunities.py:395` still tripping the §6 grep four reviews in a row?

**A.** Because the grep itself over-matches; the source is clean.

The comment in question:

```python
# pages/1_Opportunities.py:395
# ('Applied'), never the raw bracketed storage value ('[APPLIED]').
```

This comment exists *to document* the rule that `'[APPLIED]'` must never appear in a live call. The comment is therefore a literal under a `grep -nE "\[APPLIED\]"` rule. Two acceptable resolutions, both pre-existing in the project's open carry-overs:

1. **Tighten the grep to skip comment lines** — the canonical fix is `rg --type py 'pattern' app.py pages/ | rg -v '^\s*#'`, tracked at `project_state.md` *"Open carry-overs > Grep→rg"*. A one-line GUIDELINES §11 amendment.
2. **Rephrase the comment** — `'[' + 'APPLIED' + ']'` reads identically to a human and lands at zero hits under the current grep. A one-line edit to `pages/1_Opportunities.py`.

Neither has shipped through three Phase-4 reviews. The right time to land it: the eventual `reviews/phase-4-finish-review.md` (the third T6 checkbox), which will close out Phase 4 with a comprehensive cleanup pass before tagging `v0.5.0`. By that point the carry-over has trip-reported in four reviews; the cost-benefit is decisive.

### Q6 — Why is `type="tertiary"` the right styling, not `type="secondary"`?

**A.** Streamlit's `st.button` accepts three values for `type=`: `"primary"` (filled, accent color, bold weight), `"secondary"` (outlined, default text), and `"tertiary"` (plain text, no border, near-background — the lightest of the three).

The dashboard already uses two of the three:

- `"primary"`: `+ Add your first position` (empty-DB hero CTA). The strongest visual call: *"this is the one thing you should do right now."*
- Default (= `"secondary"`): `→ Opportunities page` (Materials Readiness CTA). A cross-page navigation CTA — important but not dominant.
- `"tertiary"`: `+ Show all stages` / `− Show fewer stages` (post-T6 funnel disclosure toggle). A chart control — modifies the current view without leaving the page.

The visual weight matches the role weight. Mixing them would muddle the affordance:
- A `"primary"` toggle would compete visually with the empty-DB hero CTA — the user trying to do *the most important thing* would see two equally-loud buttons.
- A `"secondary"` toggle would read as another navigation CTA, not as a chart control. The user might expect it to take them somewhere else.

The `tertiary` choice is the visual encoding of *"this changes what you're looking at; it doesn't take you anywhere."* The C.2 source-grep test (`test_toggle_uses_tertiary_type`) pins `count == 1` for this very reason — the funnel toggle is the *only* tertiary button on the dashboard, and a future tertiary elsewhere would dilute the affordance.

### Q7 — The bidirectional toggle is a textbook involution. Why is the round-trip test (B.3) needed alongside B.1 + B.2?

**A.** Because B.1 and B.2 each pin one *direction* of the round trip; B.3 pins the *composition* — that the two clicks compose to identity.

This sounds redundant in the abstract — *if click-A flips state True→False and click-B flips state False→True, surely click-A∘click-B is identity?* — but Streamlit's render pipeline is the kind of place where compositions can fail in surprising ways:

- The `on_click` callback runs *before* the next render, so any side effect on `st.session_state` is committed before the page redraws. Two clicks in succession trigger two callbacks in sequence; each callback reads the current state and flips it. If the callback ever read a stale value (e.g., from a closure captured at first render), the second click would mis-flip.
- The visible-bucket count (`_chart_bucket_count`) is computed from `at.get("plotly_chart")[0].proto.spec`, which is rebuilt from the script's render output. A subtle sort/filter regression could leave the bar count *equal* but the *bars themselves* different — the involution would pass the count check but fail the actual rendering. (B.3 doesn't pin the bar identity directly, but the project explicitly accepts that compromise — DESIGN §8.1 deliberately leaves the per-bucket order as "list order", not "user-controlled".)
- Streamlit's widget keys persist across reruns; if the toggle's `key=` changed mid-flow (e.g., a refactor renames `funnel_toggle` → `funnel_disclosure_toggle`), the second click could land on a stale widget instance. B.3's involution check would catch this — the post-second-click render would produce a different button identity, breaking the label / state / count triple.

The three checks together (label, state flag, visible-bucket count) form a redundant proof: any one of them returning wrong narrows the failure mode to a specific layer (label drift = config issue; state flag drift = callback issue; count drift = rendering issue). B.1 + B.2 alone don't compose to that proof, because each tests one direction in isolation against an artificially-set initial state.

This is the same instinct behind `test_round_trip_through_branch_b` (B.4) — if branch (b) → click → branch (c) and branch (c) → click → branch (b) each work in isolation, the *round-trip* through both branches still needs its own pin because the branch transition itself adds a class of failure mode (chart presence/absence) the simpler tests don't cover.

### Q8 — Why does branch (a) degrade to a bare subheader instead of the `st.columns([3, 1])` split?

**A.** Because `st.columns([3, 1])` reserves visual space for the right column even when the right `with` block emits no widget — and an empty right column at 25% width is a visual hole, not a neutral element.

In branch (a) (no positions at all), the toggle is suppressed: there is nothing to disclose into. Three options for the subheader-row layout in this branch:

1. **Render the `[3, 1]` split anyway, leave the right column empty.** Streamlit fills the right column slot with a blank box at 25% page width. The subheader text is left-pushed by an invisible column the user can't interact with. Visually awkward — the layout suggests something *was* there.

2. **Render the `[3, 1]` split, fill the right column with a placeholder (e.g., an `st.empty()`).** Same visual outcome as (1), with one extra Streamlit element. No win.

3. **Branch on `_show_funnel_toggle`: when False, use a bare `st.subheader`; when True, use the `[3, 1]` split.** The subheader uses the full page width when there's no right-column content. Visually clean.

The implementation chose (3). The branch-on-layout pattern echoes the project's existing instinct: page-height stability is preserved by the subheader rendering in *both* the empty and populated states (T2 / T3 / T4 / T5 precedent), but page *width* decisions are made per-branch when the alternative is a dead column. The three Q&A pins this reasoning at the source comment line ~245-247.

A pedant might argue the bare-subheader branch is a special case the layout matrix has to track — yes. The cost of *not* having the special case (an unfilled 25% column on the empty-DB hero state, exactly when the user is seeing the dashboard for the first time) is higher than the cost of one extra `if` branch.

### Q9 — Why is invariant #11 needed when `FUNNEL_TOGGLE_LABELS` only has two keys?

**A.** Because *"only has two keys"* is the contract the page reads, and contracts that aren't enforced erode.

The page indexes the dict at render time:

```python
config.FUNNEL_TOGGLE_LABELS[st.session_state["_funnel_expanded"]]
```

`_funnel_expanded` is a bool. So the index can only ever be `True` or `False`. If `FUNNEL_TOGGLE_LABELS` is missing one of those keys, the line raises `KeyError` on the first render that hits the missing state — but only when the user *clicks* the toggle and `_funnel_expanded` flips into the missing key's value. A QA pass that never clicks the toggle would never trip the missing key. A test suite that mocks `_funnel_expanded` would, but the test suite is the *target* of the invariant, not the only line of defence.

Three alternative mitigations were considered and rejected:

- **`FUNNEL_TOGGLE_LABELS.get(state, "<missing label>")`**: silently substitutes a default. Hides the bug. The user sees an unhelpful generic label and the dashboard works *almost*. GUIDELINES §12 anti-pattern: silent fallbacks for impossible states.
- **Exhaustive type hint**: `dict[Literal[True, False], str]`. Python doesn't enforce `Literal` types at runtime; a maintainer adding a third key (say, an `Optional` tri-state) would breeze past the type hint without static-checker help (`mypy --strict` is not part of the project's CI).
- **Test-only assertion**: pin in `tests/test_config.py` only, not `config.py`. Tests catch the drift but can be skipped under `-k 'not invariant'`. The import-time `assert` in `config.py` runs *every* time anyone imports config, including production page loads.

Invariant #11 is the cheapest enforcement: one assertion at import time, runs everywhere, fires *before* any page render. The `test_invariant_11_fires_on_drift` test exercises the failure mode synthetically so the guard's correctness is itself pinned.

### Q10 — DESIGN §5.3 lists `<symbol> <verb-phrase>` as the project's CTA convention. Is the `+`/`−` pair really following that convention?

**A.** Mostly yes, with one small wrinkle worth naming.

The convention as exhibited in the project today:

| CTA | Symbol | Verb phrase |
|-----|--------|-------------|
| `+ Add your first position` (empty-DB hero) | `+` | "Add your first position" |
| `→ Opportunities page` (Materials Readiness CTA) | `→` | "Opportunities page" |
| `+ Show all stages` (toggle, collapsed) | `+` | "Show all stages" |
| `− Show fewer stages` (toggle, expanded) | `−` | "Show fewer stages" |

The shape is consistent: a single character symbol, a space, then a short verb phrase. The wrinkle: the `→ Opportunities page` CTA's "verb phrase" is technically a noun phrase. The convention as written in DESIGN §5.3 is *"`<symbol> <verb-phrase>`"* but the existing CTAs treat the verb phrase loosely (any short phrase that names the action). The toggle's `+ Show all stages` / `− Show fewer stages` pair adheres strictly: both start with imperative verbs.

Two ways to read this:

1. **Strict** — the convention is *literally* a verb phrase, the toggle complies, and the Materials Readiness CTA is a pre-existing exception worth tightening on Phase 7 polish.
2. **Loose** — the convention is *"a symbol-prefix CTA"* with the verb-phrase as a strong recommendation, and all four CTAs comply.

DESIGN §5.3's recipe row (newly added in T6) says: *"the `+` / `−` pairing is recommended — the symbol encodes the click's effect direction — but invariant #11 only enforces dict shape, not symbol choice. Tests in `TestT6FunnelToggle` (`test_label_symbols_match_cta_convention`) pin the current `+` / `−` pair; relax that test if you adopt a different symbol pair."* Reading that paragraph, the project leans *loose* on the verb-phrase rule (any short clear text) and *strict* on the symbol-pairing rule for *bidirectional* CTAs (the `+ / −` reversibility cue).

The Phase 7 polish call would either tighten DESIGN §5.3 to formally relax the "verb-phrase" wording, or rephrase `→ Opportunities page` to lead with a verb (e.g., `→ Open Opportunities`). Either is fine; neither is in scope for T6.

---

## Observations for the eventual full T6 review

The third T6 checkbox is `reviews/phase-4-finish-review.md` — the comprehensive close-out review covering T4 + T5 + T6 as a phase. This per-tier review and the cohesion-smoke audit are two of its inputs. Notes for whoever writes the finish review:

1. **Pull this Findings table verbatim into the finish review** — its five entries already have severity, status, and forward references. Avoid re-deriving them.

2. **The cohesion-smoke audit's six dimensions are the cohesion-claim spine.** The finish review can name them as the cohesion contract and observe whether T6 (the toggle replacement) introduced any new cross-panel rhythm — short answer: it doesn't. The toggle styling (tertiary) actually *strengthens* the rhythm (now three buttons live at three distinct visual weights, matching three distinct roles).

3. **The §6 grep carry-over is on its fourth review.** Either land the `rg -v '^\s*#'` GUIDELINES amendment in the finish review's pre-merge fixes, or accept the comment-rephrase one-liner. Picking neither for a fifth tier would be a process smell.

4. **The PNG captures gate the cohesion-smoke checkbox close.** TASKS.md T6 first checkbox cannot be considered fully done until all three PNGs land. The smoke doc's verdict is conditional: *"capture screenshots and merge T6 once the 3 PNGs land in `docs/ui/screenshots/v0.5.0/`."* The finish review should not declare T6 complete without the captures.

5. **Two 🟡 polish from the cohesion-smoke audit are still deferred** — wireframe ASCII drift (Finding #1) and em-dash literal-vs-constant (Finding #2). The publish-phase doc-drift sweep (P5) and a future cleanup tier are the right homes; do not relitigate in the finish review.

6. **The `v0.5.0` tag is the next gate after the finish review.** TASKS.md sequence: review doc → PR → squash-merge → tag. The `roadmap.md` Status row already reflects "T6 in flight" — flip it to "✅ shipped" when `v0.5.0` lands.

---

## Verdict

**Approve, merge.**

- All pre-merge checks pass: `pytest tests/ -q` (553 green); `pytest -W error::DeprecationWarning -q` (553 green); pinned-version floors per GUIDELINES §1 honoured; `_run_page` smoke clean on populated and empty DB.
- One 🟡 polish landed inline (cohesion-smoke temporal-context footnote); two 🟡 polish kept-by-design with rationale (test consistency on comment-stripping; class-scope literal duplication); two 🟢 future items logged for the finish review / Phase 5; one ℹ️ observation deferred to the pre-merge cleanup pass at the finish review.
- The work directly resolves both user-reported pain points on the funnel toggle (no collapse path; button too visually heavy) in one widget rework, with the bidirectional contract pinned at four DESIGN layers and 19 new tests (15 in `TestT6FunnelToggle` + 4 invariant-#11). Round-trip involution explicitly tested; branch (b) ↔ (c) round-trip explicitly tested.
- The cohesion-smoke audit verifies cross-panel visual grammar is intact at this stopping point: subheader rhythm, empty-state pattern, status-sentinel stripping, label-format reuse, date format, layout hierarchy — all six dimensions clear with verbatim AppTest evidence. Two 🟡 polish surfaced and deferred per GUIDELINES §10's defer-if-costly rule. PNG captures user-pending.
- TDD cadence textbook on the toggle replacement (red → green → tracker → doc-scrub); CHANGELOG comprehensive with an explicit "Migration: none" callout and a verbatim live-AppTest probe of the round trip.

**Merge sequence:** capture PNGs (user manual) → push branch → finish review (third T6 checkbox) → PR → squash-merge → tag `v0.5.0` → close Phase 4. Then Phase 5 begins on a fresh branch off `v0.5.0`.

---

_Review by skeptical-reviewer session, 2026-04-30._


YuZh98: The first fix is reverted. The file `reviews/phase-4-finish-cohesion-smoke.md` should be frozen so no change is allowed.