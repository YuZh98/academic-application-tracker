# tests/conftest.py
# Shared pytest fixtures for the academic application tracker test suite.

from datetime import date, timedelta

import pytest

import database


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Isolated SQLite database + exports directory for each test.

    Redirects ``database.DB_PATH`` AND ``exports.EXPORTS_DIR`` into the
    test's temp directory so tests never touch ``postdoc.db`` OR the
    project's real ``exports/`` directory. Tables are initialized fresh
    via ``init_db()``; the temp tree is cleaned up automatically by
    pytest's ``tmp_path`` fixture.

    Why both monkeypatches in one fixture (Phase 6 T2 "Mandatory ride-
    along" lift): every ``database.add_position`` /
    ``update_position`` / ``add_recommender`` etc. fires
    ``exports.write_all()`` via deferred import, which now (post-Phase
    6 T1) writes a real markdown file at ``EXPORTS_DIR / 'OPPORTUNITIES.md'``.
    Without the second ``monkeypatch.setattr`` line below, every test
    in the suite that calls a ``database.py`` writer leaks a markdown
    file into the project's real ``exports/`` directory — `git status`
    after `pytest tests/ -q` shows the pollution. The lift here pulls
    both isolation legs into a single fixture so every test that
    requests ``db`` gets DB + exports isolation by default; consumers
    that need the exports-dir path back (the Phase 6 generator content
    tests) wrap this fixture in a thin shim that returns the path."""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    # Local import — avoids loading exports at conftest import time, in
    # case a future test wants to monkeypatch the module before the
    # fixture activates. Same shape as the deferred imports inside
    # database.py writers.
    import exports as _exports

    monkeypatch.setattr(_exports, "EXPORTS_DIR", tmp_path / "exports")
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


@pytest.fixture(autouse=True)
def _reset_demo_state(monkeypatch):
    """Clear demo state before AND after every test.

    - Removes AAT_DEMO and AAT_DB_PATH from the env so tests cannot
      bleed env values into each other (importlib.reload(config) tests
      in particular are order-sensitive without this).
    - Clears database._connection_provider after the test in case a
      test installed one and forgot to clean up. Provider state is
      process-global; a forgotten provider would silently affect later
      tests.
    """
    monkeypatch.delenv("AAT_DEMO", raising=False)
    monkeypatch.delenv("AAT_DB_PATH", raising=False)
    yield
    if hasattr(database, "set_connection_provider"):
        database.set_connection_provider(None)
        assert getattr(database, "_connection_provider", None) is None
