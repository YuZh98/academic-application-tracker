# tests/test_exports.py
# Smoke tests for exports.py stub + Phase 6 generator content tests.
#
# Smoke tests verify the stub API is callable and the exports/ directory
# is created. Generator-specific tests (Phase 6 T1+) verify rendered
# markdown content, sort order, NULL handling, etc.

from pathlib import Path

import pytest

import config
import database
import exports
from tests.conftest import make_position


@pytest.fixture
def isolated_exports_dir(tmp_path, monkeypatch):
    """Redirect EXPORTS_DIR + DB_PATH to a `tmp_path` subtree, then init
    a fresh DB. Tests using this fixture get full isolation from both
    the project's real ``exports/`` directory AND its real ``postdoc.db``.

    Why the DB leg of isolation matters (added 2026-05-04 post-mortem on
    PRs #32 / #33 / #34): post-Phase 6 the writers
    ``write_opportunities`` / ``write_progress``
    / ``write_recommenders`` all read the DB. Without ``DB_PATH``
    monkeypatching here, a smoke test calling a writer falls through
    to the project's real ``postdoc.db`` locally (passes silently
    against the developer's real data) and raises
    ``sqlite3.OperationalError: no such table: positions`` on CI
    runners (which have no ``postdoc.db``). Pinning the DB monkeypatch
    + ``init_db()`` inside this fixture closes the gap once for every
    consumer rather than per-test.

    Mirror of the conftest ``db`` fixture from Phase 6 T2 conftest lift,
    minus the yield value — this fixture returns the exports-dir path
    so consumers can read rendered output."""
    d = tmp_path / "exports"
    monkeypatch.setattr(exports, "EXPORTS_DIR", d)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    return d


def test_write_all_does_not_raise(isolated_exports_dir):
    exports.write_all()


def test_write_all_creates_exports_directory(isolated_exports_dir):
    exports.write_all()
    assert isolated_exports_dir.exists()
    assert isolated_exports_dir.is_dir()


def test_write_opportunities_does_not_raise(isolated_exports_dir):
    exports.write_opportunities()


def test_write_progress_does_not_raise(isolated_exports_dir):
    exports.write_progress()


def test_write_recommenders_does_not_raise(isolated_exports_dir):
    exports.write_recommenders()


def test_exports_dir_path_is_correct():
    """EXPORTS_DIR should be a sibling of exports.py, not somewhere else."""
    expected = Path(__file__).parent.parent / "exports"
    assert exports.EXPORTS_DIR == expected


# ── DESIGN §7 exports.py contract #1 + §9.5 log-and-continue ─────────────────
# A failure in any write_* must be caught at the write_all boundary, logged,
# and swallowed — the DB write that triggered the export has already
# succeeded, so callers must see "Saved", not a traceback. Per-call wrapping
# (rather than a whole-function wrap) lets the other writers still run —
# matches §9.5's literal "A failure in ANY write_*" wording.


def test_write_all_swallows_individual_writer_failure(
    isolated_exports_dir, monkeypatch, caplog,
):
    """DESIGN §9.5: a failure in any write_* is caught at the write_all
    boundary and logged. write_all() itself must not re-raise.

    Takes ``isolated_exports_dir`` so the real ``write_opportunities`` /
    ``write_recommenders`` calls (the non-monkeypatched ones) write into
    a tmp directory rather than the project's real ``exports/``.
    """

    def _boom():
        raise RuntimeError("simulated write_progress failure")

    monkeypatch.setattr(exports, "write_progress", _boom)

    with caplog.at_level("ERROR"):
        exports.write_all()  # must not re-raise

    # Log captured — message should reference the failing writer so
    # operators can find which file failed.
    assert any("write_progress" in (r.message or "") for r in caplog.records), (
        "Expected a log entry naming write_progress after its failure. "
        f"Got: {[r.message for r in caplog.records]}"
    )


def test_write_all_continues_after_individual_failure(
    isolated_exports_dir, monkeypatch,
):
    """Per-call wrapping: write_progress raising must NOT stop
    write_recommenders from running. Pin the §9.5 sequencing contract —
    a whole-function try/except wrap would skip the later writers.

    Takes ``isolated_exports_dir`` so ``EXPORTS_DIR.mkdir`` inside
    ``write_all`` doesn't create a stray ``exports/`` directory at the
    project root.
    """
    calls: list[str] = []

    def _track_opportunities():
        calls.append("opportunities")

    def _boom_progress():
        calls.append("progress")
        raise RuntimeError("simulated write_progress failure")

    def _track_recommenders():
        calls.append("recommenders")

    monkeypatch.setattr(exports, "write_opportunities", _track_opportunities)
    monkeypatch.setattr(exports, "write_progress", _boom_progress)
    monkeypatch.setattr(exports, "write_recommenders", _track_recommenders)

    exports.write_all()  # must not re-raise

    assert calls == ["opportunities", "progress", "recommenders"], (
        f"write_recommenders must run even after write_progress raised. Got call order: {calls}"
    )


def test_write_all_swallows_mkdir_failure(monkeypatch, caplog):
    """If EXPORTS_DIR.mkdir fails (perm denied, disk full, parent-path
    is a file, etc.) write_all must still return without re-raising —
    the DB write has already succeeded and the user must see "Saved",
    not a traceback. Replaces EXPORTS_DIR with a stand-in whose mkdir
    raises so the test does not depend on a real I/O failure shape."""

    class _BoomyPath:
        def mkdir(self, *args, **kwargs):
            raise OSError("simulated mkdir failure")

    monkeypatch.setattr(exports, "EXPORTS_DIR", _BoomyPath())

    with caplog.at_level("ERROR"):
        exports.write_all()  # must not re-raise

    # The catch should also log so operators see the failure.
    assert any(
        "mkdir" in (r.message or "").lower()
        or "exports_dir" in (r.message or "").lower()
        or "EXPORTS_DIR" in (r.message or "")
        for r in caplog.records
    ), (
        "Expected a log entry mentioning the EXPORTS_DIR mkdir failure. "
        f"Got: {[r.message for r in caplog.records]}"
    )


# ── Phase 6 T1: write_opportunities() generator ──────────────────────────────
#
# DESIGN §7 names the generator and its output file (`exports/OPPORTUNITIES.md`,
# from the positions table) but does NOT enumerate the column set or the
# rendered cell shapes. This test class pins the column contract so future
# changes to the rendered format land alongside an explicit test diff (the
# DESIGN §7 contract #2 "stable markdown format" requirement holds at the
# test-pin level — a generator change without a matching test edit fails CI).
#
# Column contract (locked here):
#   Position · Institute · Field · Deadline · Priority · Status · Created · Updated
#
# Cell shapes:
#   - Empty/NULL TEXT cells → `—` (em-dash). Mirrors the in-app
#     `_safe_str_or_em` convention so users see a single missing-cell glyph
#     across UI tables and exported markdown.
#   - Date / datetime cells → pass-through ISO (`YYYY-MM-DD` or
#     `YYYY-MM-DD HH:MM:SS`); the schema already stores these as ISO TEXT
#     so no reformatting is needed for round-trip backups.
#   - Status → raw bracketed sentinel (`[SAVED]`, `[APPLIED]`, …) NOT
#     `STATUS_LABELS` translation. Rationale: markdown exports are "human-
#     readable DB backups" per the project description; round-trippable /
#     greppable raw form trumps UI-friendly translation. The pre-PR
#     status-literal grep in GUIDELINES §11 is scoped to `app.py pages/`,
#     not `exports/`, so bracketed sentinels in OPPORTUNITIES.md don't
#     trip the gate.
#
# Sort order:
#   `deadline_date ASC NULLS LAST, position_id ASC` — mirror of
#   `database.get_applications_table()` precedent so equal-deadline rows
#   have a stable order across reruns.


@pytest.fixture
def db_and_exports(db, tmp_path):
    """Thin wrapper around ``conftest.py::db`` exposing the exports
    directory path so the export-content tests can read the rendered
    markdown.

    Why a wrapper rather than a separate fixture: post-Phase 6 T2, the
    conftest ``db`` fixture already monkeypatches both
    ``database.DB_PATH`` and ``exports.EXPORTS_DIR`` (to ``tmp_path /
    'test.db'`` and ``tmp_path / 'exports'`` respectively). This wrapper
    exists ONLY to return the exports-dir path so consumers can read
    files; it adds no isolation logic of its own. The ``db`` parameter
    activates the conftest fixture (its yield is unused — the
    monkeypatch side effect is what matters); ``tmp_path`` recovers the
    same ``Path`` value that ``conftest.py::db`` used."""
    return tmp_path / "exports"


class TestWriteOpportunities:
    """Phase 6 T1 — content tests for `exports.write_opportunities`.

    The function reads `database.get_all_positions()` and writes a
    single markdown table to `exports.EXPORTS_DIR / 'OPPORTUNITIES.md'`.
    See module-level comment for the locked column contract + cell
    shapes."""

    OUTPUT_FILENAME = "OPPORTUNITIES.md"

    EXPECTED_HEADER = (
        "| Position | Institute | Field | Deadline "
        "| Priority | Status | Created | Updated |"
    )

    EXPECTED_SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- | --- |"

    @classmethod
    def _read_output(cls, exports_dir: Path) -> str:
        """Return the full rendered markdown content. Failing this read
        means `write_opportunities` didn't create the file at all."""
        return (exports_dir / cls.OUTPUT_FILENAME).read_text(encoding="utf-8")

    @classmethod
    def _data_rows(cls, content: str) -> list[str]:
        """Return the markdown table's data rows — every line that
        starts with `|` minus the header (line 0) and separator (line 1).
        Robust to leading prose / trailing newline."""
        table_lines = [ln for ln in content.splitlines() if ln.startswith("|")]
        # First two lines are header + separator per the markdown table
        # spec; everything after is a data row.
        return table_lines[2:]

    # ── Six core writer contracts ─────────────────────────────────────

    def test_writes_file_at_expected_path(self, db_and_exports):
        """Call writer → file exists at `EXPORTS_DIR/OPPORTUNITIES.md`.
        DESIGN §7 pins the filename (uppercase + .md extension); pinning
        it here guards against a typo or directory-rename refactor."""
        database.add_position(make_position({"position_name": "P1"}))
        exports.write_opportunities()
        out = db_and_exports / self.OUTPUT_FILENAME
        assert out.exists(), f"Expected file at {out!s}; directory contents: {list(db_and_exports.iterdir()) if db_and_exports.exists() else '(missing)'}"

    def test_table_header_matches_contract(self, db_and_exports):
        """First markdown table row is the locked column header. Pinning
        the exact string catches any column rename / reorder."""
        database.add_position(make_position())
        exports.write_opportunities()
        content = self._read_output(db_and_exports)
        assert self.EXPECTED_HEADER in content, (
            f"Expected header {self.EXPECTED_HEADER!r} in output; "
            f"got content:\n{content!r}"
        )
        assert self.EXPECTED_SEPARATOR in content, (
            f"Expected separator {self.EXPECTED_SEPARATOR!r} below header; "
            f"got content:\n{content!r}"
        )

    def test_one_row_per_position(self, db_and_exports):
        """Three positions seeded → three data rows below the header.
        Catches a bug where the writer drops or duplicates rows."""
        for name in ("A", "B", "C"):
            database.add_position(make_position({"position_name": name}))
        exports.write_opportunities()
        content = self._read_output(db_and_exports)
        rows = self._data_rows(content)
        assert len(rows) == 3, (
            f"Expected 3 data rows (one per position); got {len(rows)}: {rows!r}"
        )

    def test_sort_order_by_deadline_asc_nulls_last(self, db_and_exports):
        """Mixed deadlines (NULL + two distinct dates) → render in
        deadline ASC NULLS LAST order. Mirrors
        `database.get_applications_table()` precedent so equal-deadline
        rows have a stable order across reruns."""
        # Insert in arbitrary order; expected order is Early → Late → NoDate.
        database.add_position(make_position({
            "position_name": "Late", "deadline_date": "2026-12-15",
        }))
        database.add_position(make_position({
            "position_name": "NoDate", "deadline_date": None,
        }))
        database.add_position(make_position({
            "position_name": "Early", "deadline_date": "2026-06-01",
        }))
        exports.write_opportunities()
        content = self._read_output(db_and_exports)
        early_idx = content.find("Early")
        late_idx = content.find("Late")
        nodate_idx = content.find("NoDate")
        assert 0 <= early_idx < late_idx < nodate_idx, (
            f"Expected Early < Late < NoDate by file offset; got "
            f"early={early_idx}, late={late_idx}, nodate={nodate_idx}.\n"
            f"Content:\n{content!r}"
        )

    def test_em_dash_for_missing_text_cells(self, db_and_exports):
        """NULL TEXT cells render as `—` (em-dash). Pinned for the Field
        column — the position is inserted with explicit None so the
        emptyness can't slip through as ``""``."""
        # add_position takes a dict; we pass None explicitly for the
        # nullable TEXT columns we want to surface as missing.
        database.add_position({
            "position_name": "BareName",
            "field": None,
            "institute": None,
            # deadline_date stays unset (None) too — secondary check.
        })
        exports.write_opportunities()
        content = self._read_output(db_and_exports)
        bare_lines = [ln for ln in content.splitlines() if "BareName" in ln]
        assert bare_lines, (
            f"Expected the BareName row in output; got content:\n{content!r}"
        )
        row = bare_lines[0]
        assert "—" in row, (
            f"Expected em-dash for missing TEXT cells; got row={row!r}"
        )

    def test_iso_format_for_date_cells(self, db_and_exports):
        """Deadline column renders as `YYYY-MM-DD` (passes the schema's
        ISO TEXT through verbatim)."""
        database.add_position(make_position({
            "position_name": "DatedPosition",
            "deadline_date": "2026-06-15",
        }))
        exports.write_opportunities()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "DatedPosition" in ln]
        assert rows, "Expected DatedPosition row in output"
        assert "2026-06-15" in rows[0], (
            f"Expected ISO deadline '2026-06-15' in row; got row={rows[0]!r}"
        )

    # ── Bonus pins ────────────────────────────────────────────────────

    def test_status_renders_as_raw_bracketed_sentinel(self, db_and_exports):
        """Markdown export captures DB-shape state for round-trip backup;
        Status is the raw bracketed sentinel (`[APPLIED]`) NOT the UI
        label form (`Applied`). Pins the deliberate divergence from the
        UI status-label convention — exports are a backup format, not a
        UI surface."""
        pid = database.add_position(make_position({"position_name": "AppliedRow"}))
        # Move off the default [SAVED] so the test exercises a non-default.
        database.update_position(pid, {"status": config.STATUS_APPLIED})
        exports.write_opportunities()
        content = self._read_output(db_and_exports)
        applied_rows = [ln for ln in content.splitlines() if "AppliedRow" in ln]
        assert applied_rows, "Expected AppliedRow in output"
        assert config.STATUS_APPLIED in applied_rows[0], (
            f"Expected raw bracketed status {config.STATUS_APPLIED!r} in row; "
            f"got row={applied_rows[0]!r}"
        )

    def test_idempotent_across_two_calls(self, db_and_exports):
        """Calling the writer twice with no DB change produces byte-
        identical output. Load-bearing for DESIGN §7 contract #2 ("stable
        markdown format committed to version control") — non-deterministic
        output (timestamps in the body, dict-ordering drift) would create
        spurious git diffs on every save."""
        database.add_position(make_position({"position_name": "Stable"}))
        exports.write_opportunities()
        first = self._read_output(db_and_exports)
        exports.write_opportunities()
        second = self._read_output(db_and_exports)
        assert first == second, (
            "write_opportunities must be deterministic — two calls with no "
            "DB change must produce byte-identical output."
        )

    def test_empty_db_writes_header_only(self, db_and_exports):
        """No positions seeded → file still written with just the header
        + separator (no data rows). The Export-page manual-trigger button
        in Phase 6 T4 must work on a fresh DB without raising."""
        # Don't seed anything.
        exports.write_opportunities()
        content = self._read_output(db_and_exports)
        assert self.EXPECTED_HEADER in content, (
            f"Header must render even on empty DB; got content:\n{content!r}"
        )
        rows = self._data_rows(content)
        assert rows == [], (
            f"Empty DB → zero data rows; got {len(rows)}: {rows!r}"
        )


# ── Phase 6 T2: write_progress() generator ───────────────────────────────────
#
# DESIGN §7 names the generator + output file (`exports/PROGRESS.md` from
# positions × applications × interviews) but does NOT enumerate the column
# set, the per-cell rendering rules, or the interviews-summary cell shape.
# This test class pins all three so a future generator change lands alongside
# an explicit test diff (DESIGN §7 contract #2 — stable markdown format
# committed to version control).
#
# Column contract (locked here):
#   Position · Institute · Status · Applied · Confirmation · Response · Result · Interviews
#
# Cell shapes — mirrors T1 OPPORTUNITIES.md conventions for cohesion across
# the three exports:
#   - Empty/NULL TEXT cells → '—' (em-dash) via `_safe_str_or_em`.
#   - Date cells → pass-through ISO TEXT (`YYYY-MM-DD`).
#   - Status → raw bracketed sentinel (`[SAVED]` / `[APPLIED]` / …) NOT
#     STATUS_LABELS translation. Markdown is a backup format, not a UI
#     surface (DESIGN §7 + Phase 6 T1 review Q1 precedent).
#   - Confirmation cell folds the (received, date) pair per the same shape
#     the Applications page uses (DESIGN §8.3 D-A T1-C amendment), but with
#     ISO dates instead of "Mon D" so the export round-trips cleanly:
#       received=0 → '—'
#       received=1 + date set → '✓ {YYYY-MM-DD}'
#       received=1 + date NULL → '✓ (no date)'
#
# Interviews-summary cell shape (the open T2 design question):
#
#   Format: '{count} (last: {YYYY-MM-DD})' where `last` = max
#           `scheduled_date` across the position's interviews.
#
#   Edge cases:
#     - 0 interviews → '—'
#     - ≥1 interviews with at least one non-NULL scheduled_date →
#         '{N} (last: {ISO})'
#     - ≥1 interviews but all NULL scheduled_date →
#         '{N} (no dates)' (rare in practice — interviews are typically
#         created with a scheduled_date — but pinned for completeness)
#
#   Rationale (didactic, since this is the only T2 design call):
#     1. Round-trippable + greppable. ISO date matches T1's date convention
#        so the three exports read coherently. The integer count gives a
#        quick "how much activity" signal that a date-only cell would lose.
#     2. Backup framing. Markdown exports are version-controlled backups,
#        not a working UI surface. "last" reads as max(scheduled_date) and
#        is unambiguous regardless of "today" or whether interviews are
#        future or past — both are useful info for review. The Applications
#        page in-app already shows full per-interview detail; the export
#        does not need to duplicate that, just summarize.
#     3. Deterministic. max-of-set is unique (idempotency-safe under
#        DESIGN §7 contract #2).
#
#   Considered + rejected: a count-only cell ('2'; loses chronological
#   info), a comma-joined date list ('2026-04-15, 2026-05-08, …'; can grow
#   unbounded — bad for markdown table cells), and a next-interview cell
#   ('next: 2026-05-08'; relies on "today" semantics that drift over time
#   and break idempotency).
#
# Sort order: same as T1 — `deadline_date ASC NULLS LAST, position_id ASC`.
# Inherited from `database.get_applications_table()` (which already sorts
# this way in SQL); the writer additionally re-applies the order via
# `pandas.sort_values(... kind='stable')` to insure against a future
# upstream change to that reader.


class TestWriteProgress:
    """Phase 6 T2 — content tests for `exports.write_progress`.

    The function reads positions × applications × interviews and writes
    a single markdown table to ``exports.EXPORTS_DIR / 'PROGRESS.md'``.
    See module-level comment for the locked column contract, cell
    shapes, and the interviews-summary design choice rationale."""

    OUTPUT_FILENAME = "PROGRESS.md"

    EXPECTED_HEADER = (
        "| Position | Institute | Status | Applied "
        "| Confirmation | Response | Result | Interviews |"
    )

    EXPECTED_SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- | --- |"

    @classmethod
    def _read_output(cls, exports_dir: Path) -> str:
        return (exports_dir / cls.OUTPUT_FILENAME).read_text(encoding="utf-8")

    @classmethod
    def _data_rows(cls, content: str) -> list[str]:
        table_lines = [ln for ln in content.splitlines() if ln.startswith("|")]
        return table_lines[2:]

    # ── Nine core writer contracts ────────────────────────────────────

    def test_writes_file_at_expected_path(self, db_and_exports):
        database.add_position(make_position({"position_name": "P1"}))
        exports.write_progress()
        out = db_and_exports / self.OUTPUT_FILENAME
        assert out.exists(), (
            f"Expected file at {out!s}; "
            f"directory contents: {list(db_and_exports.iterdir()) if db_and_exports.exists() else '(missing)'}"
        )

    def test_table_header_matches_contract(self, db_and_exports):
        database.add_position(make_position())
        exports.write_progress()
        content = self._read_output(db_and_exports)
        assert self.EXPECTED_HEADER in content, (
            f"Expected header {self.EXPECTED_HEADER!r}; got content:\n{content!r}"
        )
        assert self.EXPECTED_SEPARATOR in content, (
            f"Expected separator {self.EXPECTED_SEPARATOR!r}; got content:\n{content!r}"
        )

    def test_one_row_per_position(self, db_and_exports):
        """add_position auto-creates an applications row in the same
        transaction (database.add_position contract), so every position
        contributes exactly one row to the joined view."""
        for name in ("A", "B", "C"):
            database.add_position(make_position({"position_name": name}))
        exports.write_progress()
        content = self._read_output(db_and_exports)
        rows = self._data_rows(content)
        assert len(rows) == 3, (
            f"Expected 3 data rows (one per position); got {len(rows)}: {rows!r}"
        )

    def test_sort_order_by_deadline_asc_nulls_last(self, db_and_exports):
        database.add_position(make_position({
            "position_name": "Late", "deadline_date": "2026-12-15",
        }))
        database.add_position(make_position({
            "position_name": "NoDate", "deadline_date": None,
        }))
        database.add_position(make_position({
            "position_name": "Early", "deadline_date": "2026-06-01",
        }))
        exports.write_progress()
        content = self._read_output(db_and_exports)
        early_idx = content.find("Early")
        late_idx = content.find("Late")
        nodate_idx = content.find("NoDate")
        assert 0 <= early_idx < late_idx < nodate_idx, (
            f"Expected Early < Late < NoDate by file offset; "
            f"got early={early_idx}, late={late_idx}, nodate={nodate_idx}"
        )

    def test_em_dash_for_missing_text_cells(self, db_and_exports):
        """A row with no Applied date / no Response / no Result-set
        renders all three as em-dash. Status defaults to [SAVED] +
        result defaults to 'Pending' so those cells are non-empty."""
        # Fresh add_position → applied_date NULL, response_type NULL,
        # institute also NULL here (passed as None).
        database.add_position({
            "position_name": "BareName",
            "institute": None,
        })
        exports.write_progress()
        content = self._read_output(db_and_exports)
        bare_lines = [ln for ln in content.splitlines() if "BareName" in ln]
        assert bare_lines, "Expected the BareName row in output"
        row = bare_lines[0]
        assert "—" in row, (
            f"Expected em-dash for missing cells; got row={row!r}"
        )

    def test_iso_format_for_date_cells(self, db_and_exports):
        """Applied column renders as `YYYY-MM-DD` — pass-through of the
        schema's ISO TEXT."""
        pid = database.add_position(make_position({
            "position_name": "DatedRow",
        }))
        database.upsert_application(
            pid, {"applied_date": "2026-06-15"}, propagate_status=False,
        )
        exports.write_progress()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "DatedRow" in ln]
        assert rows, "Expected DatedRow in output"
        assert "2026-06-15" in rows[0], (
            f"Expected ISO Applied date in row; got row={rows[0]!r}"
        )

    def test_status_renders_as_raw_bracketed_sentinel(self, db_and_exports):
        """Backup format → raw bracketed status sentinel ([APPLIED]),
        NOT STATUS_LABELS translation ('Applied'). Same backup-vs-UI
        rationale as T1 OPPORTUNITIES.md."""
        pid = database.add_position(make_position({"position_name": "AppliedRow"}))
        database.update_position(pid, {"status": config.STATUS_APPLIED})
        exports.write_progress()
        content = self._read_output(db_and_exports)
        applied_rows = [ln for ln in content.splitlines() if "AppliedRow" in ln]
        assert applied_rows, "Expected AppliedRow in output"
        assert config.STATUS_APPLIED in applied_rows[0], (
            f"Expected raw bracketed status {config.STATUS_APPLIED!r} in row; "
            f"got row={applied_rows[0]!r}"
        )

    def test_idempotent_across_two_calls(self, db_and_exports):
        """DESIGN §7 contract #2: byte-identical output across two calls
        with no DB change. No timestamps in body, no dict-ordering drift."""
        database.add_position(make_position({"position_name": "Stable"}))
        exports.write_progress()
        first = self._read_output(db_and_exports)
        exports.write_progress()
        second = self._read_output(db_and_exports)
        assert first == second, (
            "write_progress must be deterministic — two calls with no DB "
            "change must produce byte-identical output."
        )

    def test_empty_db_writes_header_only(self, db_and_exports):
        """Phase 6 T4 manual-trigger button must work on a fresh DB —
        empty input → header + separator + zero data rows."""
        # Don't seed anything.
        exports.write_progress()
        content = self._read_output(db_and_exports)
        assert self.EXPECTED_HEADER in content
        rows = self._data_rows(content)
        assert rows == [], (
            f"Empty DB → zero data rows; got {len(rows)}: {rows!r}"
        )

    # ── Confirmation-cell tri-state pin (DESIGN §8.3 D-A T1-C precedent) ──

    def test_confirmation_em_dash_when_not_received(self, db_and_exports):
        """``confirmation_received == 0`` → cell text is just '—'.
        Mirrors the Applications page T1-C convention but renders into
        the exported markdown rather than the dashboard table."""
        pid = database.add_position(make_position({"position_name": "NotConfirmed"}))
        database.upsert_application(
            pid,
            {"confirmation_received": 0, "confirmation_date": None},
            propagate_status=False,
        )
        exports.write_progress()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "NotConfirmed" in ln]
        assert rows
        assert "✓" not in rows[0], (
            f"Confirmation cell must NOT contain ✓ when received=0; got {rows[0]!r}"
        )
        # The em-dash is present somewhere in the row (multiple cells could
        # be empty); we only need to verify ✓ is absent here.

    def test_confirmation_check_with_iso_date(self, db_and_exports):
        """``received=1, confirmation_date set`` → ``✓ {YYYY-MM-DD}``."""
        pid = database.add_position(make_position({"position_name": "DatedConfirm"}))
        database.upsert_application(
            pid,
            {"confirmation_received": 1, "confirmation_date": "2026-04-19"},
            propagate_status=False,
        )
        exports.write_progress()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "DatedConfirm" in ln]
        assert rows
        assert "✓ 2026-04-19" in rows[0], (
            f"Expected '✓ 2026-04-19' in Confirmation cell; got row={rows[0]!r}"
        )

    def test_confirmation_check_no_date_when_date_null(self, db_and_exports):
        """``received=1, confirmation_date NULL`` → ``✓ (no date)``."""
        pid = database.add_position(make_position({"position_name": "NoDateConfirm"}))
        database.upsert_application(
            pid,
            {"confirmation_received": 1, "confirmation_date": None},
            propagate_status=False,
        )
        exports.write_progress()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "NoDateConfirm" in ln]
        assert rows
        assert "✓ (no date)" in rows[0], (
            f"Expected '✓ (no date)' in Confirmation cell; got row={rows[0]!r}"
        )

    # ── Interviews-summary tri-state pin ──────────────────────────────

    def test_interviews_summary_em_dash_for_zero_interviews(self, db_and_exports):
        """No interviews seeded → cell is '—'."""
        database.add_position(make_position({"position_name": "NoInterviews"}))
        exports.write_progress()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "NoInterviews" in ln]
        assert rows
        assert "—" in rows[0], (
            f"Zero-interviews row must contain em-dash; got row={rows[0]!r}"
        )
        # Sanity: the row must NOT carry a digit-then-space-(last pattern.
        # Defensive check against a regression that always renders count.
        assert "(last:" not in rows[0], (
            f"Zero-interviews row must NOT carry '(last:' fragment; got row={rows[0]!r}"
        )

    def test_interviews_summary_count_and_last_date(self, db_and_exports):
        """≥1 interviews → ``{N} (last: {YYYY-MM-DD})`` where `last`
        is the max scheduled_date."""
        pid = database.add_position(make_position({"position_name": "ThreeIvws"}))
        # Seed three interviews with different scheduled_dates, latest
        # last so the sort isn't trivial.
        database.add_interview(
            pid, {"scheduled_date": "2026-04-15"}, propagate_status=False,
        )
        database.add_interview(
            pid, {"scheduled_date": "2026-05-01"}, propagate_status=False,
        )
        database.add_interview(
            pid, {"scheduled_date": "2026-06-20"}, propagate_status=False,
        )
        exports.write_progress()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "ThreeIvws" in ln]
        assert rows
        # Pin the exact summary substring — count + last ISO date.
        assert "3 (last: 2026-06-20)" in rows[0], (
            f"Expected '3 (last: 2026-06-20)' in Interviews cell; "
            f"got row={rows[0]!r}"
        )

    def test_interviews_summary_uses_max_scheduled_date_as_last(self, db_and_exports):
        """`last` is the MAX scheduled_date — not the most-recently-added,
        not the lowest-sequence. Inserts in non-monotonic order to catch a
        bug that uses last() / -1 indexing instead of max()."""
        pid = database.add_position(make_position({"position_name": "OutOfOrder"}))
        # Insert latest first so a bug that picks .iloc[-1] would surface.
        database.add_interview(
            pid, {"scheduled_date": "2026-09-01"}, propagate_status=False,
        )
        database.add_interview(
            pid, {"scheduled_date": "2026-04-01"}, propagate_status=False,
        )
        exports.write_progress()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "OutOfOrder" in ln]
        assert rows
        assert "(last: 2026-09-01)" in rows[0], (
            f"Expected (last: 2026-09-01) — max of seeded scheduled_dates — "
            f"in Interviews cell; got row={rows[0]!r}"
        )


# ── Phase 6 T3: write_recommenders() generator ───────────────────────────────
#
# DESIGN §7 names the generator + output file (`exports/RECOMMENDERS.md` from
# recommenders JOIN positions). This test class pins the column contract,
# cell shapes, and sort order so any future generator change lands alongside
# an explicit test diff (DESIGN §7 contract #2 — stable markdown format).
#
# Column contract (locked here):
#   Recommender · Relationship · Position · Institute · Asked · Confirmed · Submitted · Reminder
#
# `notes` is intentionally NOT exported. Recommender notes are typically free-
# form prose (e.g. "preferred contact method: email; usually responds within
# a week") that's awkward in a markdown table cell — the in-app UI carries
# them; the export summarises. If a future revision wants to fold notes in,
# the natural shape is a per-recommender section with bullets, not a table
# column.
#
# Cell shapes — mirror T1 + T2 conventions for cross-export cohesion:
#   - Empty/NULL TEXT cells → '—' (em-dash) via `_safe_str_or_em`.
#   - Date cells → pass-through ISO TEXT.
#   - `_md_escape_cell` on every cell.
#   - No status sentinel here — recommenders don't carry pipeline status.
#
# Confirmed cell tri-state (mirrors `pages/3_Recommenders.py::_format_confirmed`
# but lives locally in `exports.py` per the DESIGN §2 layer rule that pages
# and exports cannot share helpers):
#     confirmed=NULL → '—'
#     confirmed=0    → 'No'
#     confirmed=1    → 'Yes'
#
# Reminder cell tri-state — REUSES `exports._format_confirmation` because
# the (flag, date) shape is identical to the Applications-page Confirmation
# pattern (DESIGN §8.3 D-A T1-C precedent):
#     reminder_sent=0 / NULL → '—'
#     reminder_sent=1 + reminder_sent_date set → '✓ {YYYY-MM-DD}'
#     reminder_sent=1 + reminder_sent_date NULL → '✓ (no date)'
# Reusing the helper rather than building a parallel one keeps the cell
# format coherent across exports and avoids an "almost identical but
# subtly different" drift trap.
#
# Sort order: `recommender_name ASC, deadline_date ASC NULLS LAST, id ASC`.
#   Primary `recommender_name` groups one person's owed letters together
#   (the natural reading mode for the file).
#   Secondary `deadline_date` orders multiple positions for the same
#   recommender by upcoming-ness (ASC NULLS LAST mirrors T1/T2).
#   Tertiary `id` is the deterministic tiebreaker.
#   `database.get_all_recommenders()` SQL only includes the first + third
#   keys; deadline_date comes from `database.get_all_positions()` and is
#   merged in pandas in the writer (T2 "compose multiple reads in
#   exports.py" precedent), then re-sorted with `kind="stable"`.


class TestWriteRecommenders:
    """Phase 6 T3 — content tests for `exports.write_recommenders`.

    The function reads `database.get_all_recommenders()` (recommenders ×
    positions LEFT JOIN), merges `deadline_date` from
    `database.get_all_positions()` for the secondary sort key, and
    writes a single markdown table to ``exports.EXPORTS_DIR /
    'RECOMMENDERS.md'``. See module-level comment for the locked
    column contract, cell shapes, sort order, and helper-reuse
    decisions."""

    OUTPUT_FILENAME = "RECOMMENDERS.md"

    EXPECTED_HEADER = (
        "| Recommender | Relationship | Position | Institute "
        "| Asked | Confirmed | Submitted | Reminder |"
    )

    EXPECTED_SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- | --- |"

    @classmethod
    def _read_output(cls, exports_dir: Path) -> str:
        return (exports_dir / cls.OUTPUT_FILENAME).read_text(encoding="utf-8")

    @classmethod
    def _data_rows(cls, content: str) -> list[str]:
        table_lines = [ln for ln in content.splitlines() if ln.startswith("|")]
        return table_lines[2:]

    # ── Nine core writer contracts ────────────────────────────────────

    def test_writes_file_at_expected_path(self, db_and_exports):
        pid = database.add_position(make_position())
        database.add_recommender(pid, {"recommender_name": "Dr. Smith"})
        exports.write_recommenders()
        out = db_and_exports / self.OUTPUT_FILENAME
        assert out.exists(), (
            f"Expected file at {out!s}; "
            f"directory contents: {list(db_and_exports.iterdir()) if db_and_exports.exists() else '(missing)'}"
        )

    def test_table_header_matches_contract(self, db_and_exports):
        pid = database.add_position(make_position())
        database.add_recommender(pid, {"recommender_name": "Dr. Smith"})
        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        assert self.EXPECTED_HEADER in content, (
            f"Expected header {self.EXPECTED_HEADER!r}; got content:\n{content!r}"
        )
        assert self.EXPECTED_SEPARATOR in content, (
            f"Expected separator {self.EXPECTED_SEPARATOR!r}; got content:\n{content!r}"
        )

    def test_one_row_per_recommender_position_pair(self, db_and_exports):
        """A recommender owing letters for N positions surfaces as N
        rows (matches `get_all_recommenders()`'s row shape — one row
        per (recommender, position) pair)."""
        pid_a = database.add_position(make_position({"position_name": "Pos A"}))
        pid_b = database.add_position(make_position({"position_name": "Pos B"}))
        pid_c = database.add_position(make_position({"position_name": "Pos C"}))
        # Dr. Smith owes letters for two positions; Dr. Jones owes one.
        database.add_recommender(pid_a, {"recommender_name": "Dr. Smith"})
        database.add_recommender(pid_b, {"recommender_name": "Dr. Smith"})
        database.add_recommender(pid_c, {"recommender_name": "Dr. Jones"})
        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        rows = self._data_rows(content)
        assert len(rows) == 3, (
            f"Expected 3 rows (2 for Dr. Smith + 1 for Dr. Jones); "
            f"got {len(rows)}: {rows!r}"
        )

    def test_sort_order_groups_by_recommender_then_deadline(self, db_and_exports):
        """Two recommenders with overlapping positions render with all
        of person A's rows before any of person B's; within each
        recommender, rows order by deadline ASC NULLS LAST."""
        pid_early = database.add_position(make_position({
            "position_name": "Early Pos", "deadline_date": "2026-06-01",
        }))
        pid_late = database.add_position(make_position({
            "position_name": "Late Pos", "deadline_date": "2026-12-15",
        }))
        pid_nodate = database.add_position(make_position({
            "position_name": "NoDate Pos", "deadline_date": None,
        }))
        # Insert recommenders in non-sorted order — Dr. Beta first, then
        # Dr. Alpha — so any sort bug that relies on insertion order
        # surfaces.
        database.add_recommender(pid_late, {"recommender_name": "Dr. Beta"})
        database.add_recommender(pid_nodate, {"recommender_name": "Dr. Alpha"})
        database.add_recommender(pid_early, {"recommender_name": "Dr. Beta"})
        database.add_recommender(pid_early, {"recommender_name": "Dr. Alpha"})

        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        rows = self._data_rows(content)
        # Expected order:
        #   Dr. Alpha + Early Pos     (deadline 2026-06-01)
        #   Dr. Alpha + NoDate Pos    (NULL deadline, sorts last within Alpha)
        #   Dr. Beta  + Early Pos     (deadline 2026-06-01)
        #   Dr. Beta  + Late Pos      (deadline 2026-12-15)
        assert len(rows) == 4, f"Expected 4 rows; got {len(rows)}: {rows!r}"
        # Pin every row position rather than substring-search — the
        # "groupby recommender, then sort within" guarantee can be
        # subtly broken by a sort bug that intermixes recommenders.
        assert "Dr. Alpha" in rows[0] and "Early Pos" in rows[0], (
            f"Row 0 must be Dr. Alpha + Early Pos; got {rows[0]!r}"
        )
        assert "Dr. Alpha" in rows[1] and "NoDate Pos" in rows[1], (
            f"Row 1 must be Dr. Alpha + NoDate Pos (NULL deadline last "
            f"within Alpha); got {rows[1]!r}"
        )
        assert "Dr. Beta" in rows[2] and "Early Pos" in rows[2], (
            f"Row 2 must be Dr. Beta + Early Pos; got {rows[2]!r}"
        )
        assert "Dr. Beta" in rows[3] and "Late Pos" in rows[3], (
            f"Row 3 must be Dr. Beta + Late Pos; got {rows[3]!r}"
        )

    def test_em_dash_for_missing_text_cells(self, db_and_exports):
        """NULL relationship / NULL asked_date / etc. surface as '—'."""
        pid = database.add_position(make_position({
            "position_name": "BarePos", "institute": None,
        }))
        # Insert a recommender with NULL relationship + NULL asked_date.
        database.add_recommender(pid, {
            "recommender_name": "Dr. Bare",
            "relationship": None,
            "asked_date": None,
        })
        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        bare_lines = [ln for ln in content.splitlines() if "Dr. Bare" in ln]
        assert bare_lines, f"Expected the Dr. Bare row; got content:\n{content!r}"
        row = bare_lines[0]
        assert "—" in row, (
            f"Expected em-dash for missing TEXT cells; got row={row!r}"
        )

    def test_iso_format_for_date_cells(self, db_and_exports):
        """Asked + Submitted columns render as `YYYY-MM-DD`."""
        pid = database.add_position(make_position())
        database.add_recommender(pid, {
            "recommender_name": "Dr. Dated",
            "asked_date": "2026-04-15",
            "submitted_date": "2026-05-01",
        })
        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "Dr. Dated" in ln]
        assert rows
        assert "2026-04-15" in rows[0], (
            f"Expected ISO Asked date in row; got {rows[0]!r}"
        )
        assert "2026-05-01" in rows[0], (
            f"Expected ISO Submitted date in row; got {rows[0]!r}"
        )

    def test_idempotent_across_two_calls(self, db_and_exports):
        """DESIGN §7 contract #2: byte-identical output across two calls
        with no DB change."""
        pid = database.add_position(make_position())
        database.add_recommender(pid, {"recommender_name": "Dr. Stable"})
        exports.write_recommenders()
        first = self._read_output(db_and_exports)
        exports.write_recommenders()
        second = self._read_output(db_and_exports)
        assert first == second, (
            "write_recommenders must be deterministic — two calls with no "
            "DB change must produce byte-identical output."
        )

    def test_empty_db_writes_header_only(self, db_and_exports):
        """No recommenders seeded → header + separator + zero data rows.
        The Phase 6 T4 manual-trigger button must work on a fresh DB."""
        # Don't seed anything.
        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        assert self.EXPECTED_HEADER in content
        rows = self._data_rows(content)
        assert rows == [], (
            f"Empty DB → zero data rows; got {len(rows)}: {rows!r}"
        )

    # ── Confirmed-cell tri-state pin (Yes/No/em-dash) ─────────────────

    def test_confirmed_em_dash_when_null(self, db_and_exports):
        """`confirmed=NULL` → '—'. Mirror of the Recommenders page
        `_format_confirmed` convention but rendered into the export."""
        pid = database.add_position(make_position())
        # Default add → confirmed NULL.
        database.add_recommender(pid, {
            "recommender_name": "Dr. NullConf",
            "confirmed": None,
        })
        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "Dr. NullConf" in ln]
        assert rows
        # The Confirmed cell is the 6th '|'-separated cell. Find it by
        # splitting; first/last entries are empty strings from leading /
        # trailing pipes, so the 6th cell is index 6.
        cells = [c.strip() for c in rows[0].split("|")]
        # cells: ['', Recommender, Relationship, Position, Institute,
        #         Asked, Confirmed, Submitted, Reminder, '']
        assert cells[6] == "—", (
            f"Confirmed cell must be '—' for NULL; got cells[6]={cells[6]!r} "
            f"(full row: {rows[0]!r})"
        )

    def test_confirmed_renders_no_when_zero(self, db_and_exports):
        """`confirmed=0` → 'No'."""
        pid = database.add_position(make_position())
        database.add_recommender(pid, {
            "recommender_name": "Dr. NoConf",
            "confirmed": 0,
        })
        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "Dr. NoConf" in ln]
        assert rows
        cells = [c.strip() for c in rows[0].split("|")]
        assert cells[6] == "No", (
            f"Confirmed cell must be 'No' for confirmed=0; got cells[6]={cells[6]!r} "
            f"(full row: {rows[0]!r})"
        )

    def test_confirmed_renders_yes_when_one(self, db_and_exports):
        """`confirmed=1` → 'Yes'."""
        pid = database.add_position(make_position())
        database.add_recommender(pid, {
            "recommender_name": "Dr. YesConf",
            "confirmed": 1,
        })
        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "Dr. YesConf" in ln]
        assert rows
        cells = [c.strip() for c in rows[0].split("|")]
        assert cells[6] == "Yes", (
            f"Confirmed cell must be 'Yes' for confirmed=1; got cells[6]={cells[6]!r} "
            f"(full row: {rows[0]!r})"
        )

    # ── Reminder-cell tri-state pin (em-dash / ✓ ISO / ✓ no date) ─────

    def test_reminder_em_dash_when_not_sent(self, db_and_exports):
        """`reminder_sent=0` (default) → '—'. The cell reuses
        `_format_confirmation` because the (flag, date) shape is
        identical to the Applications-page Confirmation pattern."""
        pid = database.add_position(make_position())
        database.add_recommender(pid, {
            "recommender_name": "Dr. NoReminder",
            "reminder_sent": 0,
            "reminder_sent_date": None,
        })
        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "Dr. NoReminder" in ln]
        assert rows
        cells = [c.strip() for c in rows[0].split("|")]
        # cells[8] is Reminder (index 8 with leading-pipe ghost).
        assert cells[8] == "—", (
            f"Reminder cell must be '—' for reminder_sent=0; "
            f"got cells[8]={cells[8]!r} (full row: {rows[0]!r})"
        )

    def test_reminder_check_with_iso_date(self, db_and_exports):
        """`reminder_sent=1, reminder_sent_date set` → '✓ {YYYY-MM-DD}'."""
        pid = database.add_position(make_position())
        database.add_recommender(pid, {
            "recommender_name": "Dr. DatedReminder",
            "reminder_sent": 1,
            "reminder_sent_date": "2026-04-19",
        })
        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "Dr. DatedReminder" in ln]
        assert rows
        cells = [c.strip() for c in rows[0].split("|")]
        assert cells[8] == "✓ 2026-04-19", (
            f"Reminder cell must be '✓ 2026-04-19'; got cells[8]={cells[8]!r} "
            f"(full row: {rows[0]!r})"
        )

    def test_reminder_check_no_date_when_date_null(self, db_and_exports):
        """`reminder_sent=1, reminder_sent_date NULL` → '✓ (no date)'."""
        pid = database.add_position(make_position())
        database.add_recommender(pid, {
            "recommender_name": "Dr. NoDateReminder",
            "reminder_sent": 1,
            "reminder_sent_date": None,
        })
        exports.write_recommenders()
        content = self._read_output(db_and_exports)
        rows = [ln for ln in content.splitlines() if "Dr. NoDateReminder" in ln]
        assert rows
        cells = [c.strip() for c in rows[0].split("|")]
        assert cells[8] == "✓ (no date)", (
            f"Reminder cell must be '✓ (no date)'; got cells[8]={cells[8]!r} "
            f"(full row: {rows[0]!r})"
        )
