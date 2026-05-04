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
    """Redirect EXPORTS_DIR to a temp path so smoke tests never touch the
    real project exports/ directory. Each test gets its own clean subtree."""
    d = tmp_path / "exports"
    monkeypatch.setattr(exports, "EXPORTS_DIR", d)
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


def test_write_all_swallows_individual_writer_failure(monkeypatch, caplog):
    """DESIGN §9.5: a failure in any write_* is caught at the write_all
    boundary and logged. write_all() itself must not re-raise."""

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


def test_write_all_continues_after_individual_failure(monkeypatch):
    """Per-call wrapping: write_progress raising must NOT stop
    write_recommenders from running. Pin the §9.5 sequencing contract —
    a whole-function try/except wrap would skip the later writers."""
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
#   have a stable order across reruns. AGENTS.md "Immediate task" pins
#   this explicitly.


@pytest.fixture
def db_and_exports(tmp_path, monkeypatch):
    """Combined isolation fixture: redirects both `database.DB_PATH` and
    `exports.EXPORTS_DIR` into the same `tmp_path`, then runs `init_db`.

    Why a combined fixture rather than reusing the existing `db` (from
    conftest.py) + `isolated_exports_dir`: `database.add_position` calls
    `exports.write_all()` via deferred import, which writes into
    `exports.EXPORTS_DIR`. If only `db` is monkeypatched, the auto-fired
    `write_all` writes into the project's real `exports/` directory and
    pollutes it across test runs. Pinning both monkeypatches in one
    fixture eliminates that footgun and matches the precedent of
    `conftest.py::db` (which monkeypatches `database.DB_PATH`)."""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    exports_dir = tmp_path / "exports"
    monkeypatch.setattr(exports, "EXPORTS_DIR", exports_dir)
    database.init_db()
    return exports_dir


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

    # ── AGENTS.md spec'd six ──────────────────────────────────────────

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
