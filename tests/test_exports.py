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
