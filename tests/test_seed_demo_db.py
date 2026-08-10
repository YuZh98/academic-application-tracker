# tests/test_seed_demo_db.py
# Tests for scripts/seed_demo_db.py — both the library entry seed(conn)
# used by the demo bootstrap AND the CLI workflow used for screenshot
# generation.

import os
import sqlite3
import sys
from datetime import date, timedelta

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


class TestSeedFailFastGuards:
    """seed(conn) must reject mismatches between the passed conn and the
    installed connection provider. Without this guard, the emptiness
    check (which uses the passed conn) can pass against DB A while the
    actual writes — which route through database._connect() →
    _connection_provider() — hit DB B. The result is silently-wrong
    state; these tests pin the loud-failure contract instead."""

    def test_seed_raises_when_no_provider_installed(self):
        # autouse fixture clears the provider after each test, so by
        # default no provider is installed. Calling seed() must fail
        # loudly rather than route writes to the file-based DB_PATH.
        from scripts import seed_demo_db

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        # Create the positions table directly on the in-memory conn so
        # the emptiness check would otherwise pass — proves the guard
        # fires BEFORE that check. Hermetic: does not touch DB_PATH.
        conn.execute(
            "CREATE TABLE positions (id INTEGER PRIMARY KEY, status TEXT)"
        )
        try:
            with pytest.raises(
                RuntimeError, match="requires database.set_connection_provider"
            ):
                seed_demo_db.seed(conn)
        finally:
            conn.close()

    def test_seed_raises_on_conn_provider_mismatch(self, monkeypatch):
        # Provider returns connection A; caller passes connection B.
        # The emptiness check would pass against B while writes would
        # hit A. Guard must reject this.
        from scripts import seed_demo_db

        conn_a = sqlite3.connect(":memory:")
        conn_a.row_factory = sqlite3.Row
        conn_a.execute("PRAGMA foreign_keys = ON")
        conn_b = sqlite3.connect(":memory:")
        conn_b.row_factory = sqlite3.Row
        conn_b.execute("PRAGMA foreign_keys = ON")

        database.set_connection_provider(lambda: conn_a)
        # Initialize positions table on B so the emptiness check would
        # otherwise pass — the guard must fire first.
        conn_b.execute(
            "CREATE TABLE positions (id INTEGER PRIMARY KEY, status TEXT)"
        )

        try:
            with pytest.raises(RuntimeError, match="different connection"):
                seed_demo_db.seed(conn_b)
        finally:
            conn_a.close()
            conn_b.close()


class TestSeedDataShape:
    """After seed(), the DB must contain the alert-panel-exercising
    shape: all 7 statuses, every priority value, and deadlines in each
    Upcoming window. Each test pins one slice of the contract."""

    # Distribution: 4 SAVED, 4 APPLIED, 3 INTERVIEW, 2 OFFER, 2 CLOSED,
    # 3 REJECTED, 1 DECLINED = 19.
    EXPECTED_DISTRIBUTION = {
        config.STATUS_SAVED: 4,
        config.STATUS_APPLIED: 4,
        config.STATUS_INTERVIEW: 3,
        config.STATUS_OFFER: 2,
        config.STATUS_CLOSED: 2,
        config.STATUS_REJECTED: 3,
        config.STATUS_DECLINED: 1,
    }

    @pytest.fixture
    def seeded(self, monkeypatch):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        database.set_connection_provider(lambda: conn)
        database.init_db()
        monkeypatch.setattr(config, "IS_DEMO", True)
        from scripts import seed_demo_db

        seed_demo_db.seed(conn)
        yield conn
        conn.close()

    def test_nineteen_positions(self, seeded):
        n = seeded.execute("SELECT COUNT(*) AS n FROM positions").fetchone()["n"]
        assert n == 19, f"expected 19 positions, got {n}"

    def test_far_deadline_beyond_default_window(self, seeded):
        # The 60/90-day Upcoming selector must visibly change the list:
        # at least one SAVED deadline past the default 30-day window.
        n = seeded.execute(
            "SELECT COUNT(*) AS n FROM positions "
            "WHERE status = ? AND deadline_date > date('now', '+30 days')",
            (config.STATUS_SAVED,),
        ).fetchone()["n"]
        assert n >= 1, "no deadline beyond 30 days — 60/90 window selector inert"

    def test_every_priority_value_present(self, seeded):
        present = {
            r["priority"]
            for r in seeded.execute(
                "SELECT DISTINCT priority FROM positions WHERE priority IS NOT NULL"
            ).fetchall()
        }
        missing = set(config.PRIORITY_VALUES) - present
        assert not missing, f"priority filter options with no matching row: {missing}"

    def test_status_distribution_covers_all_seven(self, seeded):
        counts = {
            r["status"]: r["n"]
            for r in seeded.execute(
                "SELECT status, COUNT(*) AS n FROM positions GROUP BY status"
            ).fetchall()
        }
        for status, expected in self.EXPECTED_DISTRIBUTION.items():
            assert counts.get(status, 0) == expected, (
                f"{status}: expected {expected}, got {counts.get(status, 0)} "
                f"(full distribution: {counts})"
            )

    def test_at_least_two_applied_have_applied_date(self, seeded):
        # R1 trail visible.
        n = seeded.execute(
            "SELECT COUNT(*) AS n FROM applications a "
            "JOIN positions p ON p.id = a.position_id "
            "WHERE p.status = ? AND a.applied_date IS NOT NULL",
            (config.STATUS_APPLIED,),
        ).fetchone()["n"]
        assert n >= 2

    def test_interview_positions_have_interview_rows(self, seeded):
        # R2 trail visible — 3 INTERVIEW positions, 5+ interview rows total.
        total = seeded.execute("SELECT COUNT(*) AS n FROM interviews").fetchone()["n"]
        assert total >= 5
        n_with = seeded.execute(
            "SELECT COUNT(DISTINCT p.id) AS n "
            "FROM positions p JOIN applications a ON a.position_id = p.id "
            "JOIN interviews i ON i.application_id = a.position_id "
            "WHERE p.status = ?",
            (config.STATUS_INTERVIEW,),
        ).fetchone()["n"]
        assert n_with == 3

    def test_offer_with_response_date(self, seeded):
        # R3 trail visible — at least 1 OFFER with response_date set.
        n = seeded.execute(
            "SELECT COUNT(*) AS n FROM applications a "
            "JOIN positions p ON p.id = a.position_id "
            "WHERE p.status = ? AND a.response_date IS NOT NULL",
            (config.STATUS_OFFER,),
        ).fetchone()["n"]
        assert n >= 1

    def test_deadline_in_seven_day_window(self, seeded):
        # Vermilion urgency band.
        today = date.today().isoformat()
        cutoff_7 = (date.today() + timedelta(days=7)).isoformat()
        n = seeded.execute(
            "SELECT COUNT(*) AS n FROM positions "
            "WHERE deadline_date BETWEEN ? AND ?",
            (today, cutoff_7),
        ).fetchone()["n"]
        assert n >= 1

    def test_deadline_in_thirty_day_window(self, seeded):
        # Cobalt urgency band (within 30 days but outside 7).
        cutoff_8 = (date.today() + timedelta(days=8)).isoformat()
        cutoff_30 = (date.today() + timedelta(days=30)).isoformat()
        n = seeded.execute(
            "SELECT COUNT(*) AS n FROM positions "
            "WHERE deadline_date BETWEEN ? AND ?",
            (cutoff_8, cutoff_30),
        ).fetchone()["n"]
        assert n >= 2

    def test_null_recommender_present(self, seeded):
        n = seeded.execute(
            "SELECT COUNT(*) AS n FROM recommenders WHERE recommender_name IS NULL"
        ).fetchone()["n"]
        assert n == 1

    def test_recommender_past_asked_window(self, seeded):
        # At least one recommender with asked_date older than the alert
        # threshold AND no submitted_date — triggers the follow-up panel.
        cutoff = (
            date.today() - timedelta(days=config.RECOMMENDER_ALERT_DAYS + 1)
        ).isoformat()
        n = seeded.execute(
            "SELECT COUNT(*) AS n FROM recommenders "
            "WHERE asked_date IS NOT NULL "
            "AND asked_date <= ? "
            "AND submitted_date IS NULL",
            (cutoff,),
        ).fetchone()["n"]
        assert n >= 1


class TestSeedCli:
    """The CLI workflow (main + wipe) is what the screenshot-generation
    pipeline calls. These tests pin the file-mode path so a future
    refactor cannot silently break the local screenshot workflow."""

    def test_wipe_on_missing_path_is_noop(self, tmp_path):
        from scripts import seed_demo_db

        missing = tmp_path / "does_not_exist.db"
        # No exception raised.
        seed_demo_db.wipe(missing)
        assert not missing.exists()

    def test_wipe_clears_rows_when_present(self, tmp_path):
        from scripts import seed_demo_db

        db_path = tmp_path / "demo.db"
        # Create a DB with one table + one row.
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE positions (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO positions (name) VALUES ('placeholder')")
        conn.commit()
        conn.close()

        seed_demo_db.wipe(db_path)

        conn = sqlite3.connect(db_path)
        n = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        conn.close()
        assert n == 0, f"wipe() must clear rows; positions still has {n}"

    def test_main_produces_a_seeded_demo_db(self, tmp_path, monkeypatch, capsys):
        from scripts import seed_demo_db

        db_path = tmp_path / "demo.db"
        monkeypatch.setenv("AAT_DB_PATH", str(db_path))

        seed_demo_db.main()

        # Output mentions the path.
        captured = capsys.readouterr().out
        assert "Seeding demo database" in captured
        assert "Status counts" in captured

        # DB file exists + carries the 19-position dataset.
        assert db_path.exists()
        conn = sqlite3.connect(db_path)
        try:
            n = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
            assert n == 19
        finally:
            conn.close()

    def test_main_on_repeat_invocation_reseeds(self, tmp_path, monkeypatch):
        # main() calls wipe + init + seed every run, so calling it twice
        # against the same file must produce 19 positions on the second
        # run (not 38, not a RuntimeError).
        from scripts import seed_demo_db

        db_path = tmp_path / "demo.db"
        monkeypatch.setenv("AAT_DB_PATH", str(db_path))

        seed_demo_db.main()
        seed_demo_db.main()

        conn = sqlite3.connect(db_path)
        try:
            n = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
            assert n == 19
        finally:
            conn.close()
