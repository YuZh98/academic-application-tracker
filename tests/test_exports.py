# tests/test_exports.py
# Smoke tests for exports.py stub.
#
# These verify the stub API is callable and the exports/ directory is created.
# Full content tests belong in Phase 6 once the generators are implemented.

from pathlib import Path
import exports


def test_write_all_does_not_raise():
    exports.write_all()


def test_write_all_creates_exports_directory():
    exports.write_all()
    assert exports.EXPORTS_DIR.exists()
    assert exports.EXPORTS_DIR.is_dir()


def test_write_opportunities_does_not_raise():
    exports.write_opportunities()


def test_write_progress_does_not_raise():
    exports.write_progress()


def test_write_recommenders_does_not_raise():
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
    assert any(
        "write_progress" in (r.message or "")
        for r in caplog.records
    ), (
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
    monkeypatch.setattr(exports, "write_progress",     _boom_progress)
    monkeypatch.setattr(exports, "write_recommenders", _track_recommenders)

    exports.write_all()  # must not re-raise

    assert calls == ["opportunities", "progress", "recommenders"], (
        "write_recommenders must run even after write_progress raised. "
        f"Got call order: {calls}"
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
