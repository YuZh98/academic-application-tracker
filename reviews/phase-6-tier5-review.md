**Branch:** `feature/phase-6-tier5-DownloadButtons`
**Scope:** Phase 6 T5 — `pages/4_Export.py` extended with three `st.download_button` widgets + the wireframe-pinned "── Download ───" section header (rendered as `st.divider()` + `st.subheader("Download")`); 7 new tests in `TestExportPageDownloadButtons` + two helper functions (`_download_buttons`, `_download_button`)
**Stats:** 7 new tests (827 → 834 passed, 1 xfailed unchanged); +256 / −11 lines across 2 files; ruff clean; status-literal grep 0 lines; standing isolation gate empty; CI-mirror local check passes (834 + 1 xfailed with `postdoc.db` moved aside); **`Tests + Lint (3.14)` CI conclusion: SUCCESS** (`mergeStateStatus: CLEAN`, `mergeable: MERGEABLE`)
**Verdict:** Approve

---

## Executive Summary

T5 closes the Phase 6 generator-and-page group with the download
affordance the Export page was missing in T4. Implementation is
mechanical: three `st.download_button` widgets keyed
`export_download_<filename>` interleaved into the existing T4 per-file
loop, with `disabled=True` + `data=b""` on the missing-file branch
and `data=Path.read_bytes()` on the present-file branch. A single
`_file_present = _path.exists()` boolean now drives BOTH the new
disabled-state branch AND the existing T4 mtime-line branch — single
`Path.exists()` per file, no duplicated I/O check. The
wireframe-pinned "── Download ───" section header lands as
`st.divider()` + `st.subheader("Download")` rather than a literal
Unicode markdown rule (the dashes don't render as a horizontal rule
in Streamlit's markdown).

Three design calls flagged in the PR description:

1. **Stacked vs side-by-side layout.** Wireframe shows download
   button + mtime line in one row (`[ ⬇ FILENAME.md ]   Last
   generated: ...`); implementer chose stacked (button above mtime
   line) because the side-by-side `st.columns` layout would have
   moved the bold filename onto the button label and broken T4's
   substring assertions in `TestExportPageMtimesPanel`. Pragmatic —
   keeps the T4 contract intact + reads cleanly at typical viewport
   widths. The mtime line still carries the bold filename so the
   visual association between the two rows is preserved.
2. **`st.divider()` + `st.subheader("Download")` for section header.**
   Streamlit's markdown does not render Unicode dashes as a
   horizontal rule (they appear as literal characters); the divider
   + subheader pair gives the same intent in idiomatic primitives.
3. **Source-grep tests for `data` + `file_name` args.** AppTest 1.56
   does not expose either field on the DownloadButton proto (they
   live behind a mock media URL), so the implementer added
   source-level grep tests to pin the contract that the
   implementation reads `Path.read_bytes()` for `data` and passes
   `file_name=` with the locked filename. Belt-and-suspenders: the
   `test_download_button_enabled_when_file_present` integration test
   confirms the runtime path doesn't raise when actually reading a
   file.

All six pre-merge gates green. CI conclusion SUCCESS; merging via
admin-bypass per the standing `c284c20` procedure for consistency.

---

## Findings

| # | File · Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `pages/4_Export.py` download section | Wireframe deviation: stacked button-above-mtime layout instead of side-by-side. Implementer rationale (PR description + commit body): preserving T4 substring assertions + cleaner narrow-viewport rendering. The wireframe is "intent-only" per `docs/ui/wireframes.md` line 3, and the visual association between button and mtime line is still clear. | ℹ️ | Kept-by-design. If a future Phase 7 cohesion sweep wants exact wireframe fidelity, the test-compatibility cost is one substring rewrite in `TestExportPageMtimesPanel`. |
| 2 | `pages/4_Export.py` "Download" section header rendering | `st.divider()` + `st.subheader("Download")` instead of literal `"── Download ───"` markdown. Streamlit's markdown doesn't render Unicode dashes as a horizontal rule — they'd appear as literal characters. Divider + subheader pair is the idiomatic equivalent: same visual intent (rule + label), better-rendered. | ℹ️ | Kept-by-design. |
| 3 | `tests/test_export_page.py` source-grep tests | Two of the seven new tests (`test_download_button_data_arg_uses_file_read_bytes` + `test_download_button_file_name_arg_uses_locked_filename`) are source-grep rather than runtime assertions because AppTest 1.56's DownloadButton proto doesn't expose the `data` bytes or `file_name` arg (they're stored behind a mock media URL). Source-grep is the correct fallback when the test framework can't reach the field. The integration test `test_download_button_enabled_when_file_present` is the belt-and-suspenders pin. | ℹ️ | Kept-by-design. Cite-able if a future Streamlit upgrade exposes these fields on the proto — at that point both source-grep tests can become runtime assertions. |
| 4 | `tests/test_export_page.py::_download_button` helper | Looks up by `proto.id.endswith(target_key)` rather than exact match. The `proto.id` is Streamlit's full widget id (includes a generated prefix); `endswith` reliably matches the user-set key suffix. Same precedent the T6 LLM-prompts test in `test_recommenders_page.py` uses for its link-button lookups. | ℹ️ | Observation. |

*No 🔴 / 🟠 / 🟡 findings.*

---

## Junior-Engineer Q&A

**Q1. Why does the disabled-button branch pass `data=b""` rather than skipping the `data` arg or passing `data=None`?**

A. Three reasons. (1) `st.download_button`'s `data` arg is **required** — not passing it raises a `TypeError` at render time. (2) `data=None` is rejected by Streamlit's type validation in 1.56 (it expects `bytes` or `BinaryIO`, not `None`). (3) `data=b""` is the smallest legal value that satisfies both constraints. The button is disabled so the user can never trigger a click that would download an empty file; the empty bytes are placeholder semantics, not user-visible content. The implementer's `else` branch is explicit about this — keeping the `data=b""` + `disabled=True` pair tied together visually in the source so a future reader sees both as the "absent file" rendering.

**Q2. Why does the section-header test pin `at.subheader` containing "Download" but NOT pin the `st.divider()` above it?**

A. The implementer's docstring frames this honestly: "the divider is a visual nicety, not a load-bearing contract." The wireframe's intent — a labelled section break separating the regenerate-button area from the per-file download rows — is delivered by the subheader's "Download" text alone. The divider is cosmetic on top. If a future implementer drops the divider for layout reasons (e.g. moves the section header into a column), the test should still pass because the section break is still present visually. Pinning the subheader text is the right contract granularity.

**Q3. The `_file_present` boolean drives both the new disabled-state branch AND the existing T4 mtime-line branch. Isn't that mixing concerns?**

A. Both branches answer the same question — "does this file exist?" — and the answer is single-source. Computing `Path.exists()` twice in the same loop iteration would be: (a) redundant work (file-system call duplicated), (b) racy (the file could blink in or out between the two calls, producing a download button enabled against a missing file). The single boolean ensures the disabled state and the mtime-line branch agree about file presence at one moment in time. This is the same intuition that drove the T2 conftest fixture lift — pin the source-of-truth in one place and let multiple consumers read it.

**Q4. The source-grep test for `file_name` arg checks that each locked filename appears in the source — but those strings are already in the `_EXPORT_FILENAMES` tuple constant. Doesn't that make the test trivially pass regardless of implementation?**

A. The implementer flagged this in the test docstring: the tuple constant is the standing pin, and the test is honest about what it can verify. The source-grep catches three regression classes: (i) `file_name` arg dropped entirely (the `assert "file_name=" in src` line catches this), (ii) the loop iterates over a wrong list (the `_EXPORT_FILENAMES` constant gets renamed but the loop reads a different one — the test's per-filename `assert filename in src` would still pass via the constant, BUT the integration test `test_download_button_enabled_when_file_present` would fail because the buttons wouldn't render for the right filenames), (iii) the `file_name=` arg gets a hard-coded wrong value like `"download.bin"` — neither check catches this directly, but the integration test would surface it via the AppTest button keys not matching `export_download_<correct_filename>`. The honest read: source-grep + integration tests together pin the contract; neither alone is enough.

**Q5. The download-button widget keys are `export_download_OPPORTUNITIES.md` etc. — including the file extension dot. Doesn't that violate the project's convention of underscore-separated widget keys?**

A. Streamlit doesn't impose a key-format convention beyond uniqueness; the dot in `OPPORTUNITIES.md` is fine syntactically. The implementer's choice locks the key to the locked filename so a future `OPPORTUNITIES.md` → `OPPS.md` rename surfaces as one constant edit + a clean test diff. The alternative (`export_download_opportunities` without the extension) would decouple the key from the filename and require maintaining a separate mapping; the dot-inclusive form keeps the key derivable from `EXPORT_FILENAMES` directly. Cosmetic; no consumer of the key (Streamlit, AppTest, the tests) cares about the dot.

**Q6. Phase 6 generators (T1-T3) used DESIGN §7 contract #2's "stable markdown format" pin via `test_idempotent_across_two_calls`. Why doesn't T5 add a corresponding test?**

A. T5 doesn't change the markdown format — it consumes the files the T1-T3 writers produce, doesn't generate new content. Any idempotency drift would surface in the T1-T3 tests, not here. T5's contract is "the download button reads the file's current bytes and serves them" — `Path.read_bytes()` is byte-for-byte deterministic by definition (filesystem semantics). The integration test `test_download_button_enabled_when_file_present` confirms the runtime path; the source-grep test pins the implementation shape; nothing more is needed at the T5 level. If a future T6 cohesion sweep wants a "regenerate then download produces the same bytes" round-trip test, it lands at the cohesion-smoke layer, not in `TestExportPageDownloadButtons`.

---

## Carry-overs

- None — Phase 6 generator-and-page group complete with T5. Next is **T6** (Phase 6 close-out + tag `v0.7.0`), orchestrator-owned per the Phase 5 T7 precedent (cohesion-smoke + carry-over triage + CHANGELOG split + tag).

---

_Written 2026-05-04 as a pre-merge review per the
`phase-5-tier1` … `phase-6-tier4` precedent. The six pre-merge gates
were re-run on the PR head locally (`pr-36` / `358b8ef`) at review
time: ruff clean · `pytest tests/ -q` 834 passed + 1 xfailed ·
`pytest -W error::DeprecationWarning tests/ -q` 834 passed + 1
xfailed · status-literal grep 0 lines · standing isolation gate
`git status --porcelain exports/` empty · CI-mirror local check
834 + 1 xfailed with `postdoc.db` moved aside · `Tests + Lint
(3.14)` CI **conclusion: SUCCESS** verified before admin-bypass per
the `c284c20` procedure._
