# tests/test_seed_demo_db.py
# Tests for scripts/seed_demo_db.py — both the library entry seed(conn)
# used by the demo bootstrap AND the CLI workflow used for screenshot
# generation.

import os
import sqlite3
import sys

import pytest

import config
import database


class TestModuleImport:
    """The module must have no import-time side effects. db_session.py
    imports it at module load; we don't want AAT_DB_PATH mutated as a
    consequence."""

    def test_import_does_not_mutate_env(self, monkeypatch):
        monkeypatch.delenv("AAT_DB_PATH", raising=False)
        # Fresh import — clear any cached module first.
        sys.modules.pop("scripts.seed_demo_db", None)
        from scripts import seed_demo_db  # noqa: F401

        assert "AAT_DB_PATH" not in os.environ


class TestSeedLibraryEntry:
    """seed(conn) populates an open connection with the demo dataset.
    Uses the database public API so cascades + exports gate fire as
    they would from the UI."""

    @pytest.fixture
    def empty_demo_conn(self, monkeypatch):
        # Provider-backed in-memory DB. IS_DEMO=True so the exports gate
        # is exercised during seeding (no FS writes).
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        database.set_connection_provider(lambda: conn)
        database.init_db()
        monkeypatch.setattr(config, "IS_DEMO", True)
        yield conn
        conn.close()

    def test_seed_runs_against_empty_db(self, empty_demo_conn):
        from scripts import seed_demo_db

        seed_demo_db.seed(empty_demo_conn)
        for table in ("positions", "applications", "recommenders", "interviews"):
            cur = empty_demo_conn.execute(f"SELECT COUNT(*) AS n FROM {table}")
            assert cur.fetchone()["n"] > 0, f"{table} empty after seed"

    def test_seed_refuses_on_populated_db(self, empty_demo_conn):
        from scripts import seed_demo_db

        seed_demo_db.seed(empty_demo_conn)
        with pytest.raises(RuntimeError, match="not empty"):
            seed_demo_db.seed(empty_demo_conn)
