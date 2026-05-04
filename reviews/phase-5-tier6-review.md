**Branch:** `feature/phase-5-tier6-RecommenderReminders`
**Scope:** Phase 5 T6 — Recommender reminder helpers on `pages/3_Recommenders.py` Pending Alerts cards (T6-A Compose mailto link button + T6-B LLM-prompts expander)
**Stats:** 21 new tests (756 → 777 passed, 1 xfailed unchanged); +561 / −7 lines across 2 files; ruff clean; status-literal grep 0 lines
**Verdict:** Approve

---

## Executive Summary

T6 wires the two reminder affordances DESIGN §8.4 has been pinning since
v1.4 onto each Pending Alerts card: a `Compose reminder email`
`st.link_button` opening the user's default mail client with the locked
DESIGN subject + body, and an `LLM prompts (2 tones)` expander holding
one `st.code(prompt, language="text")` block per locked tone (gentle /
urgent). Both render INSIDE the existing T4 `st.container(border=True)`,
so each card stays one bordered visual unit. Two pure helpers
(`_build_compose_mailto`, `_build_llm_prompt`) carry the construction;
the existing T4 `_bullets`-building loop is extended by one line to
collect each row's `days_ago` so the prompt's "Days since I asked"
summary needs no additional date parsing or DB read. All four
GUIDELINES §11 pre-merge gates are green; suite climbs 756 → 777 (1
xfailed unchanged). The DESIGN §8.4 verbatim strings — subject
`"Following up: letters for {N} postdoc applications"`, body
`"Hi {recommender_name}, just a quick check-in on the letters of
recommendation you offered. Thank you so much!"` — match the spec
character-for-character; locked tone vocabulary `("gentle", "urgent")`
likewise matches.

---

## Findings

| # | File | Location | Description | Severity | Status |
|---|------|----------|-------------|----------|--------|
| 1 | `pages/3_Recommenders.py` | `_REMINDER_TONES` (line 144) | Module-level UI vocabulary at the page top rather than `config.py`. The project's pattern is split — `STATUS_VALUES` / `RELATIONSHIP_VALUES` / `RESULT_VALUES` live in `config.py` (multi-page), `STATUS_FILTER_ACTIVE` in `config.py` (cross-page) but `_FILTER_ALL` page-local on each page (carry-over C3). Tones are page-local UI vocabulary today; if T7 / Phase 7 promotes them to a user-editable surface, lift to `config.py` then. Acceptable as-is. | ℹ️ | Observation |
| 2 | `pages/3_Recommenders.py` | `_build_compose_mailto` subject | Subject is verbatim DESIGN §8.4 — `"Following up: letters for {N} postdoc applications"`. The N=1 case reads as `"letters for 1 postdoc applications"` (grammatically awkward singular/plural disagreement). Implementer correctly held the spec; if the awkwardness wants fixing, it's a DESIGN-amendment ask, not an implementation bug. Note for the Phase 7 polish pass. | ℹ️ | Observation |
| 3 | `pages/3_Recommenders.py` | `_max_days = max(_per_row_days)` (line 290) | DESIGN §8.4 says "days since recommender was asked" without specifying single-value vs per-position. Implementer chose the **max** across the card's positions ("longest wait") with a comment explaining the choice — keeps each prompt to one summary integer rather than per-row repetition. Defensible; alternatives (min, list-of-ints, average) are all valid; the design wasn't precise enough to call this a deviation. | ℹ️ | Observation |
| 4 | `tests/test_recommenders_page.py` | `_decode_mailto` (line 1396) | `urlparse` and `parse_qs` are imported inside the helper rather than at module top. Cosmetic — call frequency is per-test, the import cost is negligible, and inlining keeps the helper self-contained for an eventual move to a shared `tests/helpers.py`. Not a defect. | ℹ️ | Observation |

*No 🔴 / 🟠 / 🟡 findings.*

---

## Junior-Engineer Q&A

**Q1. Why does the Compose URL omit the `to:` field instead of using a dummy placeholder like `mailto:recommender@example.com?...`?**

A. The recommenders schema (`DESIGN §6` recommenders table) doesn't carry an email column today — that was a deliberate scoping choice during the v1.3 rebuild because the recommender's email lives in the user's address book / mail client, not in this app. With no real address to put in the field, three options existed: (a) omit it (`mailto:?subject=...`), (b) hard-code a placeholder string, (c) leave a literal token like `<recommender@email>` for the user to fill in. Option (a) is cleanest because most mail clients open with the cursor on the To: field and the user types or address-book-completes from there; (b) and (c) both put junk in front of the user that they have to delete. The compose-URL contract here matches this no-recipient default. If a future schema migration adds a `recommenders.email` column, the line in `_build_compose_mailto` becomes `f"mailto:{quote(email)}?subject=..."` — single-line change.

**Q2. The Compose button uses `key=f"recs_compose_{_idx}"`, where `_idx` comes from `enumerate(...)` over a `groupby`. Isn't the recommender_name a more semantically meaningful key?**

A. Three reasons for the index. (1) Streamlit widget keys must be DOM-safe — `recommender_name` may contain spaces, slashes, accents, or quotes that would need slugification first; the index is always an int. (2) Two recommenders with the same name (rare but possible — `Dr. Smith` from two different institutions, both pending) would produce a `DuplicateWidgetID` if name-keyed; index-keyed they are distinct. (3) The groupby ordering is stable per the upstream `database.get_pending_recommenders()` sort (`recommender_name ASC, deadline_date ASC NULLS LAST`), so the index is deterministic across reruns — same recommender lands on the same index unless the user adds/removes pending rows between renders, in which case Streamlit's widget-state reset is the right behaviour anyway (no in-flight state on a link button to preserve).

**Q3. The expander uses no `key=` parameter. With two cards each rendering a `LLM prompts (2 tones)` expander, doesn't Streamlit raise `DuplicateWidgetID`?**

A. `st.expander` in Streamlit 1.56 doesn't accept `key=` and Streamlit handles duplicate-label expanders by content-hash internally — verified empirically by `test_two_recommenders_two_expanders` which seeds two cards and asserts both `not at.exception` AND `len(matching) == 2`. The same is true for `st.code` blocks — they have no `key=` and Streamlit disambiguates by their position in the page tree. The two regression tests (`test_two_recommenders_two_buttons` + `test_two_recommenders_two_expanders`) explicitly pin the no-collision invariant by checking `not at.exception` first, so a future Streamlit version that tightens the rule would surface as a test failure, not a silent runtime crash for the user.

**Q4. `_build_llm_prompt` uses keyword-only arguments via the leading `*`. Why not allow positional?**

A. Five-argument calls are the danger zone — positional confusion at the call site (`_build_llm_prompt("gentle", name, rel, group, days)` vs `_build_llm_prompt(name, "gentle", ...)` — both type-check) is the canonical positional-args footgun. Keyword-only forces every call to spell out which argument is which, making the call site self-documenting AND making refactor-by-rename safe (renaming `group` → `pending_rows` doesn't break callers, where positional ordering changes would). The cost is one `*` token. The same pattern would be worth applying to `_build_compose_mailto` for consistency — it's a 2-arg function so the risk is lower, but the form is identical.

**Q5. Why does the LLM prompt summarise days-since-asked as a single integer (max across the group) rather than per-position?**

A. Two reasons cohabit. (1) Readability — a multi-position recommender's prompt would otherwise carry "asked 14d ago for Pos A, 21d ago for Pos B, 7d ago for Pos C" inline, which clutters the prose the LLM is meant to draft from. (2) Behavioural — the user's mental model when sending a reminder is "the longest-overdue letter", not "the average wait"; the max captures the most urgent deadline, which is what the email should anchor on. The per-position deadlines still surface in the prompt's `Positions still owed:` block, so the LLM has full per-position context if it wants to vary the urgency by position; the days-since-asked summary just sets the headline tone.

**Q6. The `language="text"` argument to `st.code` is pinned by both a source-grep test AND a runtime test (`test_code_blocks_use_text_language` + `test_code_blocks_render_with_text_language`). Why both?**

A. Belt-and-suspenders for a regression class that is easy to introduce silently. The source-grep test catches a future implementer who copy-pastes the call and changes `language="text"` to `language="python"` (the Streamlit default for `st.code` when omitted is now `"python"` in 1.56 — verified by manual smoke during T6 development). The runtime test catches a Streamlit upgrade that changes the default-language semantics or breaks the proto field. Either failure would surface as the user's prose getting Python-syntax-coloured (variable names highlighted, em-dashes treated as operators) — visually obvious in the browser but invisible in headless tests without an explicit pin. The dual-pin pattern is the right defence for a UI invariant that has no functional consequence beyond visual correctness.

**Q7. The Compose body interpolates `recommender_name` per card via the loop variable `_name`. The `test_body_per_card_uses_correct_recommender_name` test seeds two recommenders and asserts each body references its own card's name. What bug class does that test catch?**

A. Closure-capture errors. A naive implementation would compute `_body_template = f"Hi {_name}, ..."` once outside the groupby loop and re-use it across cards — every card's button would carry the FIRST recommender's name. Or the implementation would lift `_build_compose_mailto(_name, len(_group))` outside the loop body, computing the URL once. The test catches both shapes by seeding two distinct recommenders ("Dr. Alpha" + "Dr. Beta"), pulling every Compose button's URL, and asserting the bodies collectively reference both names. A single-recommender test would not distinguish "name interpolated correctly" from "name happens to be the only one in the loop" — pinning per-card uniqueness needs ≥ 2 cards.

---

## Carry-overs

- **C3** ("All" / locked-vocabulary sentinels in pages vs. `config.py`) extends to `_REMINDER_TONES` if T7 / Phase 7 promotes tones to user-editable. Track on the existing C3 line; do not split.
- **Phase 7 polish candidate** — Subject pluralization (`"applications"` regardless of N=1 vs N>1) per Finding #2. Park here; if the user wants `"application"` for N=1, the change lives in `_build_compose_mailto` and on a new DESIGN §8.4 amendment.

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` / `phase-5-Tier2` / `phase-5-Tier3` / `phase-5-tier4`
/ `phase-5-tier5` precedent. The four pre-merge gates were re-run on
the PR head locally (`pr-31` / `d719e1d`) at review time:
ruff clean · `pytest tests/ -q` 777 passed + 1 xfailed · `pytest -W
error::DeprecationWarning tests/ -q` 777 passed + 1 xfailed ·
status-literal grep 0 lines._
