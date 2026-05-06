# tests/test_export_page.py
# Integration tests for pages/4_Export.py using Streamlit AppTest.
#
# Phase 6 T4 coverage: page shell + manual regenerate button + mtimes panel.
# Phase 6 T5 will add download_button per file (separate test class).
#
# Uses the shared `db` fixture from tests/conftest.py — post-Phase 6 T2 lift,
# `db` monkeypatches BOTH database.DB_PATH AND exports.EXPORTS_DIR into the
# test's tmp_path subtree, so AppTest renders that don't seed the DB still
# get full isolation. Tests that need the exports-dir path back wrap `db`
# in a thin `db_and_exports` fixture (mirror of tests/test_exports.py).
#
# AppTest access patterns (verified against Streamlit 1.56):
#   - `at.title[0].value` → page title string.
#   - `at.markdown[i].value` → raw markdown source. `st.write(str)` routes
#     to `st.markdown` so prose / mtime lines land here.
#   - `at.button(key=...)` → button accessor; `at.button(key="X").click()`
#     queues a click that fires on the next `at.run()`.
#   - `at.toast[i].value` → toast body (survives the post-click rerun).
#   - `at.error[i].value` → st.error body.
#   - `set_page_config` is consumed before widgets render and does NOT
#     surface in the AppTest element tree — pinned via source-grep, same
#     precedent as test_opportunities_page.py / test_recommenders_page.py.

import datetime
import os
import pathlib

import pytest
from streamlit.testing.v1 import AppTest

import database
import exports
from tests.helpers import download_button, download_buttons

PAGE = "pages/4_Export.py"

# Locked-copy strings — pinning the verbatim text catches any drift from
# the AGENTS.md / wireframe contract.
EXPECTED_TITLE = "Export"
EXPECTED_INTRO = (
    "Markdown files are auto-exported after every data change. "
    "Use this page to trigger a manual export or download files."
)
REGENERATE_KEY = "export_regenerate"
REGENERATE_LABEL = "Regenerate all markdown files"
SUCCESS_TOAST = "Markdown files regenerated."

EXPORT_FILENAMES = ("OPPORTUNITIES.md", "PROGRESS.md", "RECOMMENDERS.md")


@pytest.fixture
def db_and_exports(db, tmp_path):
    """Thin wrapper around ``conftest.py::db`` exposing the exports-dir
    path so the mtimes-panel tests can pre-populate / read files.

    The ``db`` parameter activates the conftest fixture (its yield is
    None — the side effect is the monkeypatching of DB_PATH +
    EXPORTS_DIR + init_db()); ``tmp_path`` recovers the same Path
    value the conftest fixture used for EXPORTS_DIR. Mirror of
    tests/test_exports.py::db_and_exports."""
    return tmp_path / "exports"


def _run_page() -> AppTest:
    """Return a freshly-run AppTest for the Export page."""
    at = AppTest.from_file(PAGE)
    at.run()
    return at


# ── Page shell ────────────────────────────────────────────────────────────────


class TestExportPageShell:
    """Phase 6 T4 — page shell contract.

    Locked:
      - st.set_page_config(layout="wide") as first executable statement
        (DESIGN §8.0 + D14; pinned via source-grep — set_page_config is
        consumed before widgets render and doesn't surface in AppTest).
      - st.title("Export").
      - One-line intro per the wireframe (verbatim string).
      - st.button("Regenerate all markdown files",
        key="export_regenerate", type="primary").
      - database.init_db() runs at top of the page (mirror of every
        other page; pinned via source-grep — the call has no
        AppTest-observable effect on a populated DB but must be
        present for empty-DB renders to not raise).
    """

    def test_page_config_sets_wide_layout(self, db):
        """DESIGN §8.0 + D14: every page calls
        ``st.set_page_config(layout='wide', ...)`` as its first
        executable statement. AppTest consumes the call before any
        widget renders, so the contract is pinned at the source level
        (same precedent as the other page-shell tests)."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert "st.set_page_config(" in src, (
            f"{PAGE} must call st.set_page_config(...) per DESIGN §8.0."
        )
        assert 'layout="wide"' in src, (
            f"{PAGE} must pass layout='wide' to set_page_config per DESIGN §8.0 / D14."
        )
        assert 'page_title="Academic Application Tracker"' in src, (
            "Mirror of every other page: set_page_config must bind "
            'page_title="Academic Application Tracker".'
        )
        assert 'page_icon="📋"' in src, (
            'Mirror of every other page: set_page_config must bind page_icon="📋".'
        )

    def test_init_db_called(self, db):
        """Every page calls ``database.init_db()`` near the top so a
        fresh-clone / fresh-db user lands on a working app on first
        visit. Pinned via source-grep — the call's effect on a
        populated DB is invisible to AppTest."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert "database.init_db()" in src, (
            f"{PAGE} must call database.init_db() near the top (mirror of every other page)."
        )

    def test_page_runs_without_exception_on_empty_db(self, db):
        """Foundational sanity: AppTest renders the page on a fresh
        (init'd, but empty) DB without raising. Catches import errors,
        widget-key collisions, or unguarded reads against missing
        files (the mtimes panel is the most likely site for the
        last)."""
        at = _run_page()
        assert not at.exception, f"Page raised on empty DB: {at.exception!r}"

    def test_page_title_is_export(self, db):
        """st.title must read 'Export' verbatim."""
        at = _run_page()
        titles = [t.value for t in at.title]
        assert titles == [EXPECTED_TITLE], (
            f"Expected single st.title({EXPECTED_TITLE!r}); got {titles!r}"
        )

    def test_intro_line_present(self, db):
        """Verbatim wireframe-pinned intro line under the title.
        st.write(str) routes to st.markdown so the value lands in
        ``at.markdown``; locating by substring is robust to any future
        rewrite that splits the intro into multiple paragraphs."""
        at = _run_page()
        markdown_bodies = [m.value for m in at.markdown]
        assert any(EXPECTED_INTRO in body for body in markdown_bodies), (
            f"Expected the wireframe-pinned intro line in some "
            f"st.markdown / st.write body; got bodies={markdown_bodies!r}"
        )

    def test_regenerate_button_renders(self, db):
        """st.button with key='export_regenerate' must render with the
        verbatim wireframe-pinned label."""
        at = _run_page()
        # at.button(key=...) raises KeyError for missing keys — the
        # access itself pins existence.
        btn = at.button(key=REGENERATE_KEY)
        assert btn is not None, f"Expected button with key={REGENERATE_KEY!r}"
        assert btn.label == REGENERATE_LABEL, (
            f"Expected button label {REGENERATE_LABEL!r}; got {btn.label!r}"
        )


# ── Regenerate button behaviour ──────────────────────────────────────────────


class TestExportPageRegenerateButton:
    """Phase 6 T4 — manual regenerate button calls
    ``exports.write_all()``. Per DESIGN §7 contract #1, ``write_all``
    log-and-continues on per-writer failure, so the button itself
    rarely sees an exception — but the ``EXPORTS_DIR.mkdir`` call
    inside ``write_all`` CAN raise (permissions, disk full); the
    handler wraps the call in ``try/except`` and surfaces the
    failure as ``st.error`` per GUIDELINES §8 (friendly message, no
    re-raise)."""

    def test_click_calls_write_all(self, db, monkeypatch):
        """Click → ``database.regenerate_exports()`` is called exactly once."""
        calls: list[None] = []

        def _track():
            calls.append(None)

        monkeypatch.setattr(database, "regenerate_exports", _track)

        at = _run_page()
        at.button(key=REGENERATE_KEY).click()
        at.run()

        assert not at.exception, f"Click raised: {at.exception!r}"
        assert len(calls) == 1, (
            f"Expected exactly one call to database.regenerate_exports; got {len(calls)}"
        )

    def test_click_emits_toast_on_success(self, db, monkeypatch):
        """Successful click → st.toast(SUCCESS_TOAST). Toasts persist
        across the post-click rerun. Monkeypatch write_all to a no-op
        so the test doesn't depend on actual file-system behaviour."""
        monkeypatch.setattr(database, "regenerate_exports", lambda: None)

        at = _run_page()
        at.button(key=REGENERATE_KEY).click()
        at.run()

        assert not at.exception, f"Click raised: {at.exception!r}"
        toast_values = [t.value for t in at.toast]
        assert SUCCESS_TOAST in toast_values, (
            f"Expected toast {SUCCESS_TOAST!r} after successful click; got toasts={toast_values!r}"
        )

    def test_click_emits_error_on_write_all_failure(self, db, monkeypatch):
        """Failure-path: write_all raises (e.g. EXPORTS_DIR.mkdir
        permission denied) → st.error surfaces the message verbatim;
        the handler does NOT re-raise (GUIDELINES §8) and the button
        is still rendered for retry."""

        def _boom():
            raise OSError("simulated mkdir failure")

        monkeypatch.setattr(database, "regenerate_exports", _boom)

        at = _run_page()
        at.button(key=REGENERATE_KEY).click()
        at.run()

        assert not at.exception, (
            f"Failure path must be caught + surfaced via st.error per "
            f"GUIDELINES §8; got uncaught exception={at.exception!r}"
        )
        error_values = [e.value for e in at.error]
        assert any("simulated mkdir failure" in v for v in error_values), (
            f"Expected st.error containing the underlying OSError "
            f"message; got errors={error_values!r}"
        )
        # Button still renders post-error — user can retry.
        retry_btn = at.button(key=REGENERATE_KEY)
        assert retry_btn is not None, (
            "Regenerate button must still render after a failed click so the user can retry."
        )
        # No success toast on the failure path.
        toast_values = [t.value for t in at.toast]
        assert SUCCESS_TOAST not in toast_values, (
            f"Failed click must NOT fire the success toast; got toasts={toast_values!r}"
        )


# ── Mtimes panel ─────────────────────────────────────────────────────────────


class TestExportPageMtimesPanel:
    """Phase 6 T4 — per-file mtimes display below the regenerate
    button. For each of OPPORTUNITIES.md / PROGRESS.md /
    RECOMMENDERS.md the page renders either:
      ``**{filename}** — last generated: {YYYY-MM-DD HH:MM:SS}`` (file
        present), or
      ``**{filename}** — not yet generated`` (file absent).
    """

    @staticmethod
    def _all_text(at: AppTest) -> str:
        """Concatenate every markdown / write body so substring
        assertions don't depend on which element each line landed in.
        st.write(str) routes to st.markdown, so checking
        at.markdown alone is sufficient post-Streamlit-1.27."""
        return "\n".join(m.value for m in at.markdown)

    def test_mtimes_show_not_yet_generated_when_files_absent(
        self,
        db_and_exports,
    ):
        """Fresh DB, no files in EXPORTS_DIR → each filename surfaces
        with the ``not yet generated`` placeholder. Pre-condition:
        the conftest db fixture monkeypatches EXPORTS_DIR to
        tmp_path/exports but does NOT create the directory or any
        files inside it."""
        # Defensive: confirm no files exist at fixture entry.
        if db_and_exports.exists():
            for f in EXPORT_FILENAMES:
                assert not (db_and_exports / f).exists(), (
                    f"precondition: {f} must not exist on a fresh DB"
                )

        at = _run_page()
        text = self._all_text(at)
        for filename in EXPORT_FILENAMES:
            assert filename in text, f"Expected {filename!r} in rendered page; got text={text!r}"
            # The "not yet generated" placeholder appears next to each
            # missing filename. Substring check on the whole page text
            # is enough to pin the per-file rendering — a regression
            # that omitted the placeholder for one file would surface
            # as "OPPORTUNITIES.md" present without the matching
            # "not yet generated" near it. Tighter: count occurrences
            # of the placeholder.
        placeholder = "not yet generated"
        # Three filenames, three "not yet generated" placeholders.
        assert text.count(placeholder) == len(EXPORT_FILENAMES), (
            f"Expected {len(EXPORT_FILENAMES)} occurrences of "
            f"{placeholder!r} (one per missing file); got "
            f"{text.count(placeholder)} in text:\n{text!r}"
        )

    def test_mtimes_show_timestamps_when_files_present(self, db_and_exports):
        """Pre-populate each export file with a known mtime → page
        renders the formatted YYYY-MM-DD HH:MM:SS timestamp for each.

        Uses os.utime to set a deterministic mtime so the assertion
        can pin the exact rendered string rather than approximating
        against wall-clock time. Epoch 1700000000 = 2023-11-14
        22:13:20 UTC (local-time conversion via fromtimestamp matches
        whatever the page uses)."""
        db_and_exports.mkdir(parents=True, exist_ok=True)
        epoch = 1700000000  # arbitrary but deterministic
        expected_ts = datetime.datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")
        for filename in EXPORT_FILENAMES:
            path = db_and_exports / filename
            path.write_text("# placeholder\n", encoding="utf-8")
            os.utime(path, (epoch, epoch))

        at = _run_page()
        text = self._all_text(at)
        for filename in EXPORT_FILENAMES:
            assert filename in text, f"Expected {filename!r} in rendered page; got text={text!r}"
        # Three filenames, three timestamps. Single substring check
        # pins the format; counting catches a regression that uses
        # the same mtime for one file and "not yet generated" for
        # the others.
        assert text.count(expected_ts) == len(EXPORT_FILENAMES), (
            f"Expected {len(EXPORT_FILENAMES)} occurrences of "
            f"timestamp {expected_ts!r} (one per file); got "
            f"{text.count(expected_ts)} in text:\n{text!r}"
        )
        # And the not-yet-generated placeholder must NOT appear when
        # all three files are present.
        assert "not yet generated" not in text, (
            f"All three files exist on disk; 'not yet generated' must "
            f"not appear; got text:\n{text!r}"
        )

    def test_regenerate_then_mtimes_update(self, db_and_exports):
        """Click Regenerate on a fresh DB → exports.write_all renders
        all three header-only files → the mtimes panel re-renders
        with timestamps (no longer 'not yet generated').

        Cohesion-of-state pin: the post-click rerun must reflect the
        just-written files. A bug where the mtimes panel was rendered
        before write_all (or where st.rerun isn't called after a
        successful regenerate) would surface here."""
        # Pre-condition: no files yet; pre-render confirms the
        # "not yet generated" branch fires.
        if db_and_exports.exists():
            for f in EXPORT_FILENAMES:
                assert not (db_and_exports / f).exists()
        at = _run_page()
        pre_text = self._all_text(at)
        assert "not yet generated" in pre_text, (
            "precondition: pre-click page must show 'not yet generated' for the missing files"
        )

        at.button(key=REGENERATE_KEY).click()
        at.run()

        assert not at.exception, f"Click raised: {at.exception!r}"
        # Post-click: all three files exist on disk (write_all created
        # them via the now-real generators), so the mtimes panel must
        # render timestamps for all three.
        for filename in EXPORT_FILENAMES:
            assert (db_and_exports / filename).exists(), (
                f"After regenerate, {filename!r} must exist in EXPORTS_DIR"
            )
        post_text = self._all_text(at)
        # The exact timestamps depend on wall-clock time at write_all
        # call; we can't pin them. But the placeholder must be gone
        # for all three filenames, and a YYYY-MM-DD prefix should
        # appear at least three times (one per file).
        assert "not yet generated" not in post_text, (
            f"After regenerate, 'not yet generated' must not appear; got text:\n{post_text!r}"
        )
        # Today's date prefix is present at least three times. Use the
        # local-time date so the test doesn't drift around UTC midnight.
        today_prefix = datetime.date.today().strftime("%Y-%m-%d")
        assert post_text.count(today_prefix) >= len(EXPORT_FILENAMES), (
            f"Expected at least {len(EXPORT_FILENAMES)} occurrences of "
            f"today's date prefix {today_prefix!r} (one per just-written "
            f"file); got {post_text.count(today_prefix)} in text:\n"
            f"{post_text!r}"
        )


# ── Phase 6 T5: Download buttons ─────────────────────────────────────────────
#
# `download_buttons` + `download_button` helpers live in tests/helpers.py
# (lifted in Phase 7 cleanup CL3 — same pattern as tests/test_recommenders_
# page.py's `link_buttons` / `decode_mailto` lift). Imported above.


class TestExportPageDownloadButtons:
    """Phase 6 T5 — three st.download_button widgets per
    EXPORT_FILENAMES with the wireframe-pinned "── Download ───"
    section header above them.

    Locked contracts:
      - One widget per locked filename (OPPORTUNITIES.md /
        PROGRESS.md / RECOMMENDERS.md), in wireframe order.
      - Widget key: ``f"export_download_{filename}"``.
      - Widget label: ``f"⬇ {filename}"`` (download glyph + name).
      - File present → button enabled, data = file bytes.
      - File absent → button disabled, data = b"".
      - Section header ("Download") rendered above the buttons.

    AppTest API caveats:
      - `at.get('download_button')` returns UnknownElement instances;
        `.proto.disabled` exposes the disabled state.
      - The download button's bytes payload (`data` arg) and
        `file_name` arg are NOT on the proto. Source-grep tests pin
        those two contracts at the implementation level.
    """

    DOWNLOAD_HEADER_TEXT = "Download"

    def test_three_download_buttons_render(self, db):
        """Three widgets rendered in wireframe order with the locked
        keys + labels."""
        at = _run_page()
        buttons = download_buttons(at)
        assert len(buttons) == len(EXPORT_FILENAMES), (
            f"Expected {len(EXPORT_FILENAMES)} download buttons (one per file); got {len(buttons)}"
        )
        for filename in EXPORT_FILENAMES:
            btn = download_button(at, filename)
            expected_label = f"⬇ {filename}"
            assert btn.proto.label == expected_label, (
                f"Expected label {expected_label!r} on the {filename!r} "
                f"download button; got {btn.proto.label!r}"
            )

    def test_download_button_disabled_when_file_absent(self, db_and_exports):
        """Fresh DB, no files in EXPORTS_DIR → every download button
        is disabled. The user gets the 'click Regenerate first'
        affordance from the existing T4 mtimes panel ('not yet
        generated' placeholder); the disabled button is the visual
        signal that the file isn't downloadable yet."""
        # Defensive: confirm no files exist at fixture entry.
        if db_and_exports.exists():
            for f in EXPORT_FILENAMES:
                assert not (db_and_exports / f).exists(), (
                    f"precondition: {f} must not exist on a fresh DB"
                )
        at = _run_page()
        for filename in EXPORT_FILENAMES:
            btn = download_button(at, filename)
            assert btn.proto.disabled, (
                f"{filename!r} download button must be disabled when "
                f"the file is absent; got disabled={btn.proto.disabled}"
            )

    def test_download_button_enabled_when_file_present(self, db_and_exports):
        """Pre-populate each export file → every download button
        renders enabled (disabled=False)."""
        db_and_exports.mkdir(parents=True, exist_ok=True)
        for filename in EXPORT_FILENAMES:
            (db_and_exports / filename).write_text("# placeholder\n", encoding="utf-8")
        at = _run_page()
        for filename in EXPORT_FILENAMES:
            btn = download_button(at, filename)
            assert not btn.proto.disabled, (
                f"{filename!r} download button must be enabled when "
                f"the file exists; got disabled={btn.proto.disabled}"
            )

    def test_download_button_data_arg_uses_file_read_bytes(self):
        """The `data` arg passes the file's raw bytes (so the
        downloaded file matches disk content). The bytes payload is
        NOT on the AppTest proto (it's stored behind a mock media
        URL), so this contract is pinned at source level: the
        implementation must read the file bytes via `read_bytes()` to
        feed `data`. A regression that hard-codes a string or fails
        to read the file would fail this grep.

        Belt-and-suspenders: the
        `test_download_button_enabled_when_file_present` integration
        test confirms the runtime path doesn't raise on a real file
        read; this test pins the implementation shape."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert "read_bytes()" in src, (
            f"{PAGE} must read the export file via Path.read_bytes() "
            f"to populate the download button's `data` arg. Without "
            f"this, the AppTest enabled/disabled contract holds but "
            f"the runtime download data would be wrong."
        )

    def test_download_button_file_name_arg_uses_locked_filename(self):
        """The `file_name` arg locks the user's saved-file name to
        the export filename (so it lands as ``OPPORTUNITIES.md``, not
        the page's internal slug or `download.bin`). The arg is NOT
        on the AppTest proto — pinned at source level.

        After the DESIGN §2 architecture fix, filenames are no longer
        hardcoded in the page source — they are returned by
        database.get_export_paths(). The page source must reference
        that call; the locked filename strings must live in database.py."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        # The spec calls for `file_name=filename` (or equivalent
        # variable). Look for the `file_name=` token.
        assert "file_name=" in src, (
            f"{PAGE} must pass file_name=... to st.download_button so "
            f"the saved file lands with the locked export filename."
        )
        # The page must delegate path resolution to database.get_export_paths()
        # rather than constructing paths from exports.EXPORTS_DIR directly
        # (DESIGN §2: pages must never import exports).
        assert "database.get_export_paths()" in src, (
            f"{PAGE} must call database.get_export_paths() to resolve "
            f"export file paths (DESIGN §2: pages must never import exports)."
        )
        # Each locked filename must appear in database.py (the new home
        # of the filename constants after the architecture fix).
        db_src = pathlib.Path("database.py").read_text(encoding="utf-8")
        for filename in EXPORT_FILENAMES:
            assert filename in db_src, (
                f"database.py source must reference {filename!r} so "
                f"database.get_export_paths() resolves to the locked "
                f"export filename. (Moved from pages/4_Export.py per "
                f"DESIGN §2.)"
            )

    def test_download_section_header_rendered(self, db):
        """The wireframe pins a "── Download ───" section header above
        the download buttons. Implementation rendering choice:
        st.divider() + st.subheader("Download") (Streamlit-idiomatic
        equivalent of the ASCII header). This test pins the visible
        "Download" subheader; the divider is a visual nicety, not a
        load-bearing contract."""
        at = _run_page()
        subheaders = [s.value for s in at.subheader]
        assert self.DOWNLOAD_HEADER_TEXT in subheaders, (
            f"Expected an st.subheader({self.DOWNLOAD_HEADER_TEXT!r}) "
            f"above the download buttons (wireframe-pinned section "
            f"header); got subheaders={subheaders!r}"
        )

    def test_regenerate_then_download_buttons_enable(self, db_and_exports):
        """Cohesion-of-state across the click + post-rerun: fresh DB
        → buttons disabled → click regenerate → re-rendered buttons
        all enabled. Catches a bug where the disabled state is cached
        across the rerun (e.g. a stale `Path.exists()` snapshot or
        widget state holding the old value)."""
        if db_and_exports.exists():
            for f in EXPORT_FILENAMES:
                assert not (db_and_exports / f).exists()
        at = _run_page()
        # Pre-state: all three buttons disabled.
        for filename in EXPORT_FILENAMES:
            btn = download_button(at, filename)
            assert btn.proto.disabled, (
                f"precondition: {filename!r} button must be disabled pre-click"
            )
        # Click regenerate → write_all creates the three header-only files.
        at.button(key=REGENERATE_KEY).click()
        at.run()
        assert not at.exception, f"Click raised: {at.exception!r}"
        # Post-state: all three buttons enabled.
        for filename in EXPORT_FILENAMES:
            assert (db_and_exports / filename).exists(), (
                f"After regenerate, {filename!r} must exist on disk"
            )
            btn = download_button(at, filename)
            assert not btn.proto.disabled, (
                f"After regenerate, {filename!r} download button must "
                f"be enabled; got disabled={btn.proto.disabled}"
            )


# ── Database export-helper unit tests ─────────────────────────────────────────
#
# Thin unit tests for the two new database.py wrappers that route the
# Export page through the database layer (DESIGN §2 fix).


class TestDatabaseExportHelpers:
    """Unit tests for database.regenerate_exports() and
    database.get_export_paths() — the two thin wrapper functions added
    to database.py so that pages/4_Export.py never needs to import
    exports directly (DESIGN §2)."""

    def test_regenerate_exports_calls_write_all(self, db, monkeypatch):
        """database.regenerate_exports() must delegate to
        exports.write_all() exactly once."""
        calls: list[None] = []
        monkeypatch.setattr(exports, "write_all", lambda: calls.append(None))
        database.regenerate_exports()
        assert len(calls) == 1, (
            f"Expected exactly one call to exports.write_all() from "
            f"database.regenerate_exports(); got {len(calls)}"
        )

    def test_regenerate_exports_propagates_exceptions(self, db, monkeypatch):
        """Unlike the log-and-swallow auto-write hooks, regenerate_exports
        must propagate exceptions so the page can surface them via
        st.error (GUIDELINES §8 / DESIGN §7 contract distinction)."""

        def _boom() -> None:
            raise OSError("simulated mkdir failure")

        monkeypatch.setattr(exports, "write_all", _boom)
        with pytest.raises(OSError, match="simulated mkdir failure"):
            database.regenerate_exports()

    def test_get_export_paths_returns_three_files(self, db):
        """get_export_paths() must return exactly three (filename, Path)
        pairs covering the three committed export files in wireframe order."""
        result = database.get_export_paths()
        assert len(result) == 3, f"Expected 3 export paths; got {len(result)}: {result!r}"
        filenames = [name for name, _ in result]
        assert filenames == list(EXPORT_FILENAMES), (
            f"Expected locked filenames {list(EXPORT_FILENAMES)!r} in "
            f"wireframe order; got {filenames!r}"
        )

    def test_get_export_paths_resolves_under_exports_dir(self, db_and_exports):
        """Paths returned by get_export_paths() must resolve under
        EXPORTS_DIR (monkeypatched to tmp_path/exports by the db fixture)."""
        result = database.get_export_paths()
        for filename, path in result:
            assert path.parent == db_and_exports, (
                f"{filename!r} path {path!r} must be inside EXPORTS_DIR {db_and_exports!r}"
            )
            assert path.name == filename, (
                f"path.name {path.name!r} must match filename {filename!r}"
            )
