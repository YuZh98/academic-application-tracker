# tests/conftest.py
# Shared pytest fixtures for the postdoc tracker test suite.

import pytest
from datetime import date, timedelta

import database


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Isolated SQLite database for each test.

    Redirects database.DB_PATH to a temp file so tests never touch postdoc.db.
    Tables are initialized fresh; the temp directory is cleaned up automatically."""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    yield


# ── Shared helpers ────────────────────────────────────────────────────────────

def make_position(overrides: dict | None = None) -> dict:
    """Return a minimal valid fields dict for add_position()."""
    base = {
        "position_name": "BioStats Postdoc",
        "institute": "Stanford",
        "field": "Statistics",
        "deadline_date": (date.today() + timedelta(days=20)).isoformat(),
        "priority": "High",
    }
    if overrides:
        base.update(overrides)
    return base
