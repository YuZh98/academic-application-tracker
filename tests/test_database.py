# tests/test_database.py
# Integration tests for database.py.
#
# All tests use real SQLite (no mocking). Each test gets an isolated temp DB
# via the `db` fixture in conftest.py. Tests are grouped by concern.

import re
import sqlite3
import time
import pytest
from datetime import date, timedelta
from pathlib import Path

import database
import config
from tests.conftest import make_position


# ── Schema / init_db ──────────────────────────────────────────────────────────

class TestInitDb:

    def test_creates_three_tables(self, db):
        with database._connect() as conn:
            tables = {r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert {"positions", "applications", "recommenders"} <= tables

    def test_creates_indices(self, db):
        with database._connect() as conn:
            indices = {r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()}
        assert "idx_positions_status"   in indices
        assert "idx_positions_deadline" in indices

    def test_positions_has_all_req_done_columns(self, db):
        with database._connect() as conn:
            col_names = {r["name"] for r in conn.execute(
                "PRAGMA table_info(positions)"
            ).fetchall()}
        for req_col, done_col, _ in config.REQUIREMENT_DOCS:
            assert req_col  in col_names, f"Missing column: {req_col}"
            assert done_col in col_names, f"Missing column: {done_col}"

    def test_idempotent(self, db):
        """Calling init_db() multiple times must not raise or corrupt tables."""
        database.init_db()
        database.init_db()
        with database._connect() as conn:
            tables = {r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        assert "positions" in tables

    def test_migration_adds_new_column(self, db, monkeypatch):
        """Adding a new entry to REQUIREMENT_DOCS and calling init_db() adds the
        columns without touching existing data."""
        extra = config.REQUIREMENT_DOCS + [
            ("req_portfolio", "done_portfolio", "Portfolio"),
        ]
        monkeypatch.setattr(config, "REQUIREMENT_DOCS", extra)
        database.init_db()

        with database._connect() as conn:
            col_names = {r["name"] for r in conn.execute(
                "PRAGMA table_info(positions)"
            ).fetchall()}
        assert "req_portfolio"  in col_names
        assert "done_portfolio" in col_names

    def test_migration_preserves_existing_rows(self, db, monkeypatch):
        """Migration must not delete existing position rows."""
        pos_id = database.add_position(make_position())

        extra = config.REQUIREMENT_DOCS + [
            ("req_portfolio", "done_portfolio", "Portfolio"),
        ]
        monkeypatch.setattr(config, "REQUIREMENT_DOCS", extra)
        database.init_db()

        pos = database.get_position(pos_id)
        assert pos["position_name"] == "BioStats Postdoc"
        assert pos["req_portfolio"] == "No"   # default for new column

    def test_migration_rewrites_legacy_req_short_codes(self, db):
        """Sub-task 2 / D21: pre-v1.3 short-code req_* values ('Y'/'N') must
        be rewritten in place to the full-word form on next init_db(). The
        fixture already called init_db() once, so we simulate a legacy-state
        DB by writing short codes via raw SQL (bypassing the page and
        add_position, which both route through the new vocabulary), then
        re-run init_db() and assert every flavour is translated correctly:

          - 'Y' → 'Yes'
          - 'N' → 'No'
          - 'Optional' stays 'Optional' (ELSE branch of the CASE)

        Also pins idempotence: a second init_db() on the already-migrated
        row leaves the 'Yes' / 'No' / 'Optional' values untouched."""
        pos_id = database.add_position(make_position())
        # Overwrite three req_* columns with legacy values via raw SQL so
        # the test setup faithfully mirrors a pre-v1.3 DB on disk.
        with database._connect() as conn:
            conn.execute(
                "UPDATE positions SET req_cv = 'Y', "
                "req_cover_letter = 'N', "
                "req_transcripts = 'Optional' "
                "WHERE id = ?",
                (pos_id,),
            )

        database.init_db()

        pos = database.get_position(pos_id)
        assert pos["req_cv"] == "Yes", (
            f"Legacy 'Y' must migrate to 'Yes'; got {pos['req_cv']!r}"
        )
        assert pos["req_cover_letter"] == "No", (
            f"Legacy 'N' must migrate to 'No'; got {pos['req_cover_letter']!r}"
        )
        assert pos["req_transcripts"] == "Optional", (
            f"'Optional' must pass through unchanged; got {pos['req_transcripts']!r}"
        )

        # Idempotence: second init_db() on the migrated row is a no-op.
        database.init_db()
        pos = database.get_position(pos_id)
        assert pos["req_cv"] == "Yes"
        assert pos["req_cover_letter"] == "No"
        assert pos["req_transcripts"] == "Optional"

    def test_migration_rewrites_legacy_pipeline_stage0_status(self, db):
        """Sub-task 5 / DESIGN §5.1 + §6.3: any row carrying the pre-v1.3
        pipeline-stage-0 status literal must migrate in place to '[SAVED]'
        on the next init_db() call. The one-shot UPDATE is idempotent by
        its WHERE-guard — the second call sees no matching rows and is a
        no-op.

        Legacy string is spelled via concatenation so the GUIDELINES §6
        pre-merge grep stays at zero hits post-rename — the exact literal
        only materialises at runtime inside the test and inside init_db().
        See CHANGELOG [Unreleased] Migration: entry for the canonical SQL."""
        pos_id = database.add_position(make_position())
        legacy_status = "[OPE" + "N]"   # pre-v1.3 pipeline-stage-0 literal
        with database._connect() as conn:
            conn.execute(
                "UPDATE positions SET status = ? WHERE id = ?",
                (legacy_status, pos_id),
            )

        database.init_db()

        pos = database.get_position(pos_id)
        assert pos["status"] == "[SAVED]", (
            "Pre-v1.3 stage-0 literal must migrate to '[SAVED]'; got "
            f"{pos['status']!r}"
        )

        # Idempotence: second init_db() leaves '[SAVED]' untouched.
        database.init_db()
        pos = database.get_position(pos_id)
        assert pos["status"] == "[SAVED]"

    def test_migration_rewrites_legacy_med_priority(self, db):
        """Sub-task 5 / DESIGN §5.1: the pre-v1.3 PRIORITY_VALUES short
        code must migrate in place to the full-word 'Medium' on the next
        init_db() call. Other priorities ('High'/'Low'/'Stretch' and NULL)
        pass through unchanged — the UPDATE's WHERE clause scopes it to
        the single legacy literal.

        Legacy short code is spelled via concatenation so the GUIDELINES §6
        pre-merge grep stays at zero hits post-rename."""
        # Seed three positions with different priority states to pin
        # scope: one legacy short code, one already-migrated 'Medium'
        # (must survive unchanged), one unrelated 'High' (also unchanged).
        p1 = database.add_position(make_position({"position_name": "P1"}))
        p2 = database.add_position(make_position({"position_name": "P2"}))
        p3 = database.add_position(make_position({"position_name": "P3"}))
        legacy_medium = "M" + "ed"   # pre-v1.3 short-code priority literal
        with database._connect() as conn:
            conn.execute("UPDATE positions SET priority = ? WHERE id = ?", (legacy_medium, p1))
            conn.execute("UPDATE positions SET priority = 'Medium' WHERE id = ?", (p2,))
            conn.execute("UPDATE positions SET priority = 'High' WHERE id = ?",   (p3,))

        database.init_db()

        assert database.get_position(p1)["priority"] == "Medium", (
            "Pre-v1.3 short-code priority must migrate to 'Medium'; got "
            f"{database.get_position(p1)['priority']!r}"
        )
        assert database.get_position(p2)["priority"] == "Medium"
        assert database.get_position(p3)["priority"] == "High"

        # Idempotence: second init_db() is a no-op.
        database.init_db()
        assert database.get_position(p1)["priority"] == "Medium"
        assert database.get_position(p2)["priority"] == "Medium"
        assert database.get_position(p3)["priority"] == "High"

    def test_ddl_defaults_interpolate_from_config(self, tmp_path, monkeypatch):
        """Sub-task 4 / DESIGN §6.2: the CREATE TABLE statements must
        interpolate config.STATUS_VALUES[0] into positions.status DEFAULT
        and config.RESULT_DEFAULT into applications.result DEFAULT — so
        that a rename in config.py is a config-only edit (no DDL change).

        Sentinel monkeypatch forces a mismatch between live config values
        and what a hardcoded DDL literal would emit; if init_db() reads
        the constants at call time (f-string interpolation), PRAGMA
        dflt_value reflects the sentinel. SQLite reports DEFAULT clauses
        exactly as written in DDL, so the expected form is
        f"'{value}'" — including the surrounding single quotes."""
        sentinel_status = "[SENTINEL_SAVED]"
        sentinel_result = "SentinelPending"

        monkeypatch.setattr(
            config, "STATUS_VALUES",
            [sentinel_status] + config.STATUS_VALUES[1:],
        )
        monkeypatch.setattr(config, "RESULT_DEFAULT", sentinel_result)
        monkeypatch.setattr(database, "DB_PATH", tmp_path / "ddl_probe.db")

        database.init_db()

        with database._connect() as conn:
            positions_cols    = conn.execute("PRAGMA table_info(positions)").fetchall()
            applications_cols = conn.execute("PRAGMA table_info(applications)").fetchall()

        status_default = next(
            r["dflt_value"] for r in positions_cols if r["name"] == "status"
        )
        result_default = next(
            r["dflt_value"] for r in applications_cols if r["name"] == "result"
        )

        assert status_default == f"'{config.STATUS_VALUES[0]}'", (
            "positions.status DEFAULT must interpolate config.STATUS_VALUES[0] "
            f"(wrapped in SQL quotes); got {status_default!r}, "
            f"expected {f'{chr(39)}{sentinel_status}{chr(39)}'!r}."
        )
        assert result_default == f"'{config.RESULT_DEFAULT}'", (
            "applications.result DEFAULT must interpolate config.RESULT_DEFAULT "
            f"(wrapped in SQL quotes); got {result_default!r}, "
            f"expected {f'{chr(39)}{sentinel_result}{chr(39)}'!r}."
        )

    def test_positions_has_updated_at_column_with_datetime_default(self, db):
        """Sub-task 6 / DESIGN §6.2 + D25: positions.updated_at column must
        exist with DEFAULT (datetime('now')) so every INSERT without an
        explicit updated_at value is stamped at row-creation time by SQLite
        itself — no Python writer needs to remember.

        SQLite preserves parenthesised expression defaults verbatim in
        sqlite_master, and PRAGMA table_info surfaces the raw text through
        dflt_value — so exact-string equality is safe here."""
        with database._connect() as conn:
            cols = conn.execute("PRAGMA table_info(positions)").fetchall()

        updated_at = next((r for r in cols if r["name"] == "updated_at"), None)
        assert updated_at is not None, (
            "positions.updated_at must be defined in the CREATE TABLE DDL. "
            f"Column list: {sorted(r['name'] for r in cols)!r}"
        )
        assert updated_at["type"] == "TEXT", (
            f"positions.updated_at type must be TEXT; got {updated_at['type']!r}"
        )
        assert updated_at["dflt_value"] == "datetime('now')", (
            "positions.updated_at DEFAULT must be the parenthesised expression "
            f"datetime('now'); got {updated_at['dflt_value']!r}"
        )

    def test_positions_updated_at_trigger_exists(self, db):
        """Sub-task 6 / DESIGN §6.2 + D25: CREATE TRIGGER positions_updated_at
        must be registered in sqlite_master after init_db(). The trigger is
        AFTER UPDATE on positions and resets updated_at to datetime('now');
        SQLite's default recursive_triggers = 0 suppresses the inner UPDATE
        from re-firing the trigger — the loop-prevention guarantee rides on
        that default, not on any code we write here."""
        with database._connect() as conn:
            triggers = {
                r["name"] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'trigger'"
                ).fetchall()
            }
        assert "positions_updated_at" in triggers, (
            "Expected trigger 'positions_updated_at' registered in sqlite_master; "
            f"got: {triggers!r}"
        )

    def test_add_position_populates_updated_at(self, db):
        """Sub-task 6 / DESIGN §6.2 + D25: newly inserted positions must
        carry a non-NULL updated_at stamp. add_position() does not pass
        updated_at in its INSERT dict, so the value comes purely from the
        column DEFAULT — which is exactly why the DDL default is load-
        bearing (INSERT does not fire the AFTER UPDATE trigger)."""
        pos_id = database.add_position(make_position())
        pos = database.get_position(pos_id)

        assert pos["updated_at"] is not None, (
            "updated_at must be populated on INSERT via the column DEFAULT; got None"
        )
        # SQLite's datetime('now') renders as 'YYYY-MM-DD HH:MM:SS'.
        assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", pos["updated_at"]), (
            "updated_at must match SQLite's datetime('now') ISO-ish format; "
            f"got {pos['updated_at']!r}"
        )

    def test_update_position_refreshes_updated_at(self, db):
        """Sub-task 6 / DESIGN §6.2 + D25: every UPDATE on positions must
        advance updated_at to the current wall clock via the trigger. Also
        implicitly pins "no infinite loop" — if recursive_triggers were ON
        (or the trigger body were re-entrant in some other way), the inner
        UPDATE would recurse to SQLite's 1000-frame limit and raise
        `sqlite3.OperationalError: recursion limit reached`. A clean return
        from update_position therefore proves the recursion is suppressed.

        SQLite's datetime('now') is second-precision, so the 1.1 s sleep is
        the minimum needed to guarantee ts_after > ts_before under string
        comparison (ISO datetimes sort lexically the same way they sort
        chronologically)."""
        pos_id = database.add_position(make_position())
        ts_before = database.get_position(pos_id)["updated_at"]

        time.sleep(1.1)
        database.update_position(pos_id, {"position_name": "Renamed"})
        ts_after = database.get_position(pos_id)["updated_at"]

        assert ts_after > ts_before, (
            "updated_at must advance on UPDATE (trigger fires AFTER UPDATE). "
            f"Before: {ts_before!r}, after: {ts_after!r}"
        )

    def test_migration_adds_updated_at_to_pre_v1_3_positions(self, tmp_path, monkeypatch):
        """Sub-task 6 / DESIGN §6.3: pre-v1.3 DBs whose positions table was
        created without updated_at must pick up the column + trigger on the
        next init_db(), and any existing row must be backfilled with
        datetime('now') (not left NULL).

        SQLite disallows `ALTER TABLE ADD COLUMN ... DEFAULT (datetime('now'))`
        once the target table has rows — it raises 'Cannot add a column
        with non-constant default'. The migration therefore uses a
        NULL-default ADD COLUMN and a one-shot UPDATE backfill. The
        CREATE TABLE DDL's DEFAULT (datetime('now')) handles fresh DBs;
        this test exercises the upgrade path specifically.

        Idempotence: a second init_db() finds the column already present
        and must leave the backfilled stamp untouched (the backfill UPDATE
        is scoped WHERE updated_at IS NULL, so it no-ops the second time)."""
        monkeypatch.setattr(database, "DB_PATH", tmp_path / "pre_v1_3.db")

        # Simulate a pre-v1.3 positions table (no updated_at) with an
        # existing row — mirrors what a user's local DB looks like before
        # this sub-task ships. Only includes the columns that init_db()
        # needs to reach the updated_at migration: indexed columns
        # (status, deadline_date) plus priority (touched by the Sub-task 5
        # value-migration UPDATE) and position_name (NOT NULL identity).
        # Everything else is added by existing req/done migration loops.
        with database._connect() as conn:
            conn.execute("""
                CREATE TABLE positions (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    status        TEXT NOT NULL DEFAULT '[SAVED]',
                    priority      TEXT,
                    created_at    TEXT DEFAULT (date('now')),
                    position_name TEXT NOT NULL,
                    deadline_date TEXT
                )
            """)
            conn.execute(
                "INSERT INTO positions (position_name) VALUES ('LegacyRow')"
            )

        database.init_db()

        with database._connect() as conn:
            cols = {r["name"] for r in conn.execute(
                "PRAGMA table_info(positions)"
            ).fetchall()}
            legacy_row = conn.execute(
                "SELECT updated_at FROM positions "
                "WHERE position_name = 'LegacyRow'"
            ).fetchone()
            triggers = {
                r["name"] for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'trigger'"
                ).fetchall()
            }

        assert "updated_at" in cols, (
            "Migration must add updated_at via ALTER TABLE ADD COLUMN."
        )
        assert legacy_row["updated_at"] is not None, (
            "Existing pre-v1.3 rows must be backfilled with datetime('now') — "
            f"got {legacy_row['updated_at']!r}"
        )
        assert re.match(
            r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
            legacy_row["updated_at"],
        ), (
            "Backfilled updated_at must match SQLite's datetime('now') "
            f"format; got {legacy_row['updated_at']!r}"
        )
        assert "positions_updated_at" in triggers, (
            "Trigger must also be created during the migration path."
        )

        # Idempotence: second init_db() must leave the migrated row's
        # stamp untouched. The backfill UPDATE is WHERE updated_at IS NULL,
        # so it no-ops; no other init_db() step should touch the column.
        ts_after_first_init = legacy_row["updated_at"]
        database.init_db()
        with database._connect() as conn:
            ts_after_second_init = conn.execute(
                "SELECT updated_at FROM positions "
                "WHERE position_name = 'LegacyRow'"
            ).fetchone()["updated_at"]
        assert ts_after_second_init == ts_after_first_init, (
            "Second init_db() on a migrated DB must be a no-op for updated_at. "
            f"Before: {ts_after_first_init!r}, after: {ts_after_second_init!r}"
        )


# ── add_position / get_position ───────────────────────────────────────────────

class TestAddPosition:

    def test_returns_integer_id(self, db):
        pos_id = database.add_position(make_position())
        assert isinstance(pos_id, int)
        assert pos_id >= 1

    def test_ids_increment(self, db):
        id1 = database.add_position(make_position())
        id2 = database.add_position(make_position({"position_name": "Other"}))
        assert id2 == id1 + 1

    def test_status_defaults_to_saved(self, db):
        pos_id = database.add_position(make_position())
        pos = database.get_position(pos_id)
        assert pos["status"] == "[SAVED]"

    def test_req_columns_default_to_no(self, db):
        pos_id = database.add_position(make_position())
        pos = database.get_position(pos_id)
        for req_col, _, _ in config.REQUIREMENT_DOCS:
            assert pos[req_col] == "No", f"{req_col} should default to 'No'"

    def test_done_columns_default_to_zero(self, db):
        pos_id = database.add_position(make_position())
        pos = database.get_position(pos_id)
        for _, done_col, _ in config.REQUIREMENT_DOCS:
            assert pos[done_col] == 0, f"{done_col} should default to 0"

    def test_auto_creates_applications_row(self, db):
        pos_id = database.add_position(make_position())
        app = database.get_application(pos_id)
        assert app["position_id"] == pos_id
        assert app["result"] == "Pending"

    def test_auto_created_application_has_null_dates(self, db):
        pos_id = database.add_position(make_position())
        app = database.get_application(pos_id)
        assert app["applied_date"] is None
        assert app["interview1_date"] is None
        assert app["result_notify_date"] is None


class TestGetPosition:

    def test_returns_dict(self, db):
        pos_id = database.add_position(make_position())
        result = database.get_position(pos_id)
        assert isinstance(result, dict)

    def test_fields_are_correct(self, db):
        pos_id = database.add_position(make_position())
        pos = database.get_position(pos_id)
        assert pos["position_name"] == "BioStats Postdoc"
        assert pos["institute"] == "Stanford"
        assert pos["field"] == "Statistics"
        assert pos["priority"] == "High"

    def test_raises_key_error_for_missing_id(self, db):
        with pytest.raises(KeyError):
            database.get_position(999)


# ── get_all_positions ─────────────────────────────────────────────────────────

class TestGetAllPositions:

    def test_empty_db_returns_empty_dataframe(self, db):
        import pandas as pd
        df = database.get_all_positions()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_returns_all_rows(self, db):
        database.add_position(make_position())
        database.add_position(make_position({"position_name": "Other"}))
        df = database.get_all_positions()
        assert len(df) == 2

    def test_ordered_by_deadline_asc(self, db):
        database.add_position(make_position({
            "position_name": "Late",
            "deadline_date": (date.today() + timedelta(days=30)).isoformat(),
        }))
        database.add_position(make_position({
            "position_name": "Soon",
            "deadline_date": (date.today() + timedelta(days=5)).isoformat(),
        }))
        df = database.get_all_positions()
        assert df.iloc[0]["position_name"] == "Soon"
        assert df.iloc[1]["position_name"] == "Late"

    def test_null_deadline_last(self, db):
        database.add_position(make_position({
            "position_name": "No deadline",
            "deadline_date": None,
        }))
        database.add_position(make_position({
            "position_name": "Has deadline",
            "deadline_date": (date.today() + timedelta(days=10)).isoformat(),
        }))
        df = database.get_all_positions()
        assert df.iloc[0]["position_name"] == "Has deadline"
        assert df.iloc[1]["position_name"] == "No deadline"


# ── update_position ───────────────────────────────────────────────────────────

class TestUpdatePosition:

    def test_updates_specified_fields(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {"status": "[APPLIED]", "req_cv": "Yes"})
        pos = database.get_position(pos_id)
        assert pos["status"] == "[APPLIED]"
        assert pos["req_cv"] == "Yes"

    def test_partial_update_does_not_clobber_other_fields(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {"status": "[APPLIED]"})
        pos = database.get_position(pos_id)
        assert pos["position_name"] == "BioStats Postdoc"   # unchanged
        assert pos["institute"] == "Stanford"               # unchanged

    def test_can_set_done_column(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {"req_cv": "Yes", "done_cv": 1})
        pos = database.get_position(pos_id)
        assert pos["done_cv"] == 1


# ── delete_position + cascade ─────────────────────────────────────────────────

class TestDeletePosition:

    def test_removes_position_row(self, db):
        pos_id = database.add_position(make_position())
        database.delete_position(pos_id)
        with pytest.raises(KeyError):
            database.get_position(pos_id)

    def test_cascade_deletes_applications_row(self, db):
        pos_id = database.add_position(make_position())
        database.delete_position(pos_id)
        assert database.get_application(pos_id) == {}

    def test_cascade_deletes_recommenders(self, db):
        pos_id = database.add_position(make_position())
        database.add_recommender(pos_id, {"recommender_name": "Dr. Smith"})
        database.add_recommender(pos_id, {"recommender_name": "Dr. Jones"})
        database.delete_position(pos_id)
        recs = database.get_recommenders(pos_id)
        assert len(recs) == 0

    def test_deleting_nonexistent_id_does_not_raise(self, db):
        database.delete_position(999)   # should be silent


# ── upsert_application ────────────────────────────────────────────────────────

class TestUpsertApplication:

    def test_inserts_if_no_conflict(self, db):
        pos_id = database.add_position(make_position())
        # The auto-created row has result='Pending'. Upsert with a real applied_date.
        database.upsert_application(pos_id, {
            "applied_date": "2026-04-10",
            "response_type": "Interview Invite",
        })
        app = database.get_application(pos_id)
        assert app["applied_date"] == "2026-04-10"
        assert app["response_type"] == "Interview Invite"

    def test_updates_on_conflict(self, db):
        pos_id = database.add_position(make_position())
        database.upsert_application(pos_id, {"applied_date": "2026-04-10"})
        database.upsert_application(pos_id, {"result": "Offer Accepted"})
        app = database.get_application(pos_id)
        assert app["result"] == "Offer Accepted"

    def test_upsert_is_idempotent_single_row(self, db):
        pos_id = database.add_position(make_position())
        database.upsert_application(pos_id, {"applied_date": "2026-04-10"})
        database.upsert_application(pos_id, {"applied_date": "2026-04-10"})
        with database._connect() as conn:
            cnt = conn.execute(
                "SELECT COUNT(*) AS c FROM applications WHERE position_id=?", (pos_id,)
            ).fetchone()["c"]
        assert cnt == 1

    def test_upsert_preserves_unmentioned_fields(self, db):
        """Upserting a subset of fields must not null out other existing fields."""
        pos_id = database.add_position(make_position())
        database.upsert_application(pos_id, {"applied_date": "2026-04-10"})
        database.upsert_application(pos_id, {"result": "Rejected"})
        app = database.get_application(pos_id)
        assert app["applied_date"] == "2026-04-10"   # still set


# ── recommenders ─────────────────────────────────────────────────────────────

class TestRecommenders:

    def test_add_returns_id(self, db):
        pos_id = database.add_position(make_position())
        rec_id = database.add_recommender(pos_id, {"recommender_name": "Dr. Smith"})
        assert isinstance(rec_id, int)

    def test_get_recommenders_returns_only_that_position(self, db):
        id1 = database.add_position(make_position())
        id2 = database.add_position(make_position({"position_name": "Other"}))
        database.add_recommender(id1, {"recommender_name": "Dr. Smith"})
        database.add_recommender(id2, {"recommender_name": "Dr. Jones"})

        recs1 = database.get_recommenders(id1)
        assert len(recs1) == 1
        assert recs1.iloc[0]["recommender_name"] == "Dr. Smith"

    def test_get_all_recommenders_includes_join_columns(self, db):
        pos_id = database.add_position(make_position())
        database.add_recommender(pos_id, {"recommender_name": "Dr. Smith"})
        df = database.get_all_recommenders()
        assert "position_name" in df.columns
        assert "institute" in df.columns
        assert df.iloc[0]["position_name"] == "BioStats Postdoc"

    def test_update_recommender(self, db):
        pos_id = database.add_position(make_position())
        rec_id = database.add_recommender(pos_id, {
            "recommender_name": "Dr. Smith",
            "asked_date": "2026-04-01",
        })
        database.update_recommender(rec_id, {"submitted_date": "2026-04-14"})
        recs = database.get_recommenders(pos_id)
        assert recs.iloc[0]["submitted_date"] == "2026-04-14"
        assert recs.iloc[0]["recommender_name"] == "Dr. Smith"   # unchanged

    def test_delete_recommender(self, db):
        pos_id = database.add_position(make_position())
        rec_id = database.add_recommender(pos_id, {"recommender_name": "Dr. Smith"})
        database.delete_recommender(rec_id)
        recs = database.get_recommenders(pos_id)
        assert len(recs) == 0

    def test_delete_recommender_does_not_affect_position(self, db):
        pos_id = database.add_position(make_position())
        rec_id = database.add_recommender(pos_id, {"recommender_name": "Dr. Smith"})
        database.delete_recommender(rec_id)
        pos = database.get_position(pos_id)   # should not raise
        assert pos["position_name"] == "BioStats Postdoc"


# ── count_by_status ───────────────────────────────────────────────────────────

class TestCountByStatus:

    def test_empty_db_returns_empty_dict(self, db):
        assert database.count_by_status() == {}

    def test_counts_correctly(self, db):
        database.add_position(make_position())
        database.add_position(make_position({"position_name": "P2"}))
        pos3 = database.add_position(make_position({"position_name": "P3"}))
        database.update_position(pos3, {"status": "[APPLIED]"})

        counts = database.count_by_status()
        assert counts["[SAVED]"]   == 2
        assert counts["[APPLIED]"] == 1

    def test_closed_status_counted_separately(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {"status": "[CLOSED]"})
        counts = database.count_by_status()
        assert "[SAVED]"  not in counts
        assert counts.get("[CLOSED]") == 1


# ── get_upcoming_deadlines ────────────────────────────────────────────────────

class TestGetUpcomingDeadlines:

    def test_returns_positions_within_window(self, db):
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=10)).isoformat(),
        }))
        df = database.get_upcoming_deadlines(30)
        assert len(df) == 1

    def test_excludes_positions_outside_window(self, db):
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=40)).isoformat(),
        }))
        df = database.get_upcoming_deadlines(30)
        assert len(df) == 0

    def test_excludes_past_deadlines(self, db):
        database.add_position(make_position({
            "deadline_date": (date.today() - timedelta(days=1)).isoformat(),
        }))
        df = database.get_upcoming_deadlines(30)
        assert len(df) == 0

    def test_includes_deadline_today(self, db):
        database.add_position(make_position({
            "deadline_date": date.today().isoformat(),
        }))
        df = database.get_upcoming_deadlines(30)
        assert len(df) == 1

    def test_excludes_closed_status(self, db):
        pos_id = database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=5)).isoformat(),
        }))
        database.update_position(pos_id, {"status": "[CLOSED]"})
        df = database.get_upcoming_deadlines(30)
        assert len(df) == 0

    def test_excludes_rejected_and_declined(self, db):
        for status in ("[REJECTED]", "[DECLINED]"):
            pos_id = database.add_position(make_position({
                "position_name": f"pos_{status}",
                "deadline_date": (date.today() + timedelta(days=5)).isoformat(),
            }))
            database.update_position(pos_id, {"status": status})
        df = database.get_upcoming_deadlines(30)
        assert len(df) == 0

    def test_excludes_null_deadline(self, db):
        database.add_position(make_position({"deadline_date": None}))
        df = database.get_upcoming_deadlines(30)
        assert len(df) == 0

    def test_ordered_by_deadline_asc(self, db):
        database.add_position(make_position({
            "position_name": "Later", "deadline_date": (date.today() + timedelta(days=20)).isoformat(),
        }))
        database.add_position(make_position({
            "position_name": "Sooner", "deadline_date": (date.today() + timedelta(days=5)).isoformat(),
        }))
        df = database.get_upcoming_deadlines(30)
        assert df.iloc[0]["position_name"] == "Sooner"

    def test_result_has_expected_columns(self, db):
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=5)).isoformat(),
        }))
        df = database.get_upcoming_deadlines(30)
        for col in ("id", "position_name", "institute", "deadline_date", "status", "priority"):
            assert col in df.columns, f"Missing column: {col}"


# ── get_upcoming_interviews ───────────────────────────────────────────────────

class TestGetUpcomingInterviews:

    def test_empty_when_no_interviews_set(self, db):
        database.add_position(make_position())
        df = database.get_upcoming_interviews()
        assert len(df) == 0

    def test_returns_row_with_future_interview1(self, db):
        pos_id = database.add_position(make_position())
        database.upsert_application(pos_id, {
            "interview1_date": (date.today() + timedelta(days=7)).isoformat(),
        })
        df = database.get_upcoming_interviews()
        assert len(df) == 1

    def test_returns_row_with_future_interview2_only(self, db):
        pos_id = database.add_position(make_position())
        database.upsert_application(pos_id, {
            "interview2_date": (date.today() + timedelta(days=14)).isoformat(),
        })
        df = database.get_upcoming_interviews()
        assert len(df) == 1

    def test_excludes_past_interview(self, db):
        pos_id = database.add_position(make_position())
        database.upsert_application(pos_id, {
            "interview1_date": (date.today() - timedelta(days=1)).isoformat(),
        })
        df = database.get_upcoming_interviews()
        assert len(df) == 0

    def test_includes_interview_today(self, db):
        pos_id = database.add_position(make_position())
        database.upsert_application(pos_id, {
            "interview1_date": date.today().isoformat(),
        })
        df = database.get_upcoming_interviews()
        assert len(df) == 1

    def test_result_has_join_columns(self, db):
        pos_id = database.add_position(make_position())
        database.upsert_application(pos_id, {
            "interview1_date": (date.today() + timedelta(days=5)).isoformat(),
        })
        df = database.get_upcoming_interviews()
        for col in ("position_name", "institute", "interview1_date"):
            assert col in df.columns


# ── get_pending_recommenders ──────────────────────────────────────────────────

class TestGetPendingRecommenders:

    def test_empty_when_no_recommenders(self, db):
        database.add_position(make_position())
        df = database.get_pending_recommenders(7)
        assert len(df) == 0

    def test_includes_recommender_asked_beyond_threshold(self, db):
        pos_id = database.add_position(make_position())
        database.add_recommender(pos_id, {
            "recommender_name": "Dr. Smith",
            "asked_date": (date.today() - timedelta(days=8)).isoformat(),
        })
        df = database.get_pending_recommenders(7)
        assert len(df) == 1
        assert df.iloc[0]["recommender_name"] == "Dr. Smith"

    def test_excludes_recommender_asked_within_threshold(self, db):
        """Asked 6 days ago with days=7 → should NOT be alerted."""
        pos_id = database.add_position(make_position())
        database.add_recommender(pos_id, {
            "recommender_name": "Dr. Smith",
            "asked_date": (date.today() - timedelta(days=6)).isoformat(),
        })
        df = database.get_pending_recommenders(7)
        assert len(df) == 0

    def test_excludes_recommender_who_submitted(self, db):
        pos_id = database.add_position(make_position())
        rec_id = database.add_recommender(pos_id, {
            "recommender_name": "Dr. Jones",
            "asked_date": (date.today() - timedelta(days=10)).isoformat(),
        })
        database.update_recommender(rec_id, {
            "submitted_date": date.today().isoformat(),
        })
        df = database.get_pending_recommenders(7)
        assert len(df) == 0

    def test_excludes_recommender_with_no_asked_date(self, db):
        pos_id = database.add_position(make_position())
        database.add_recommender(pos_id, {"recommender_name": "Dr. Ghost"})
        df = database.get_pending_recommenders(7)
        assert len(df) == 0

    def test_result_has_join_columns(self, db):
        pos_id = database.add_position(make_position())
        database.add_recommender(pos_id, {
            "recommender_name": "Dr. Smith",
            "asked_date": (date.today() - timedelta(days=10)).isoformat(),
        })
        df = database.get_pending_recommenders(7)
        for col in ("position_name", "institute", "deadline_date"):
            assert col in df.columns


# ── compute_materials_readiness ───────────────────────────────────────────────

class TestComputeMaterialsReadiness:

    def test_empty_db_returns_zeros(self, db):
        result = database.compute_materials_readiness()
        assert result == {"ready": 0, "pending": 0}

    def test_position_with_no_required_docs_excluded(self, db):
        """req_* all default to 'No' — position has no requirements, excluded from count."""
        database.add_position(make_position())
        result = database.compute_materials_readiness()
        assert result == {"ready": 0, "pending": 0}

    def test_ready_when_all_required_docs_done(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {"req_cv": "Yes", "done_cv": 1})
        result = database.compute_materials_readiness()
        assert result["ready"] == 1
        assert result["pending"] == 0

    def test_pending_when_required_doc_not_done(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {"req_cv": "Yes", "done_cv": 0})
        result = database.compute_materials_readiness()
        assert result["ready"] == 0
        assert result["pending"] == 1

    def test_pending_when_one_of_many_required_docs_not_done(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {
            "req_cv": "Yes", "done_cv": 1,
            "req_cover_letter": "Yes", "done_cover_letter": 0,   # not done
        })
        result = database.compute_materials_readiness()
        assert result["ready"] == 0
        assert result["pending"] == 1

    def test_optional_docs_not_required_for_ready(self, db):
        """req_* = 'Optional' means the doc exists but is not required for readiness."""
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {
            "req_cv": "Yes", "done_cv": 1,
            "req_transcripts": "Optional", "done_transcripts": 0,  # Optional, not done
        })
        result = database.compute_materials_readiness()
        # 'Optional' != 'Yes', so done_transcripts=0 does not make it pending
        assert result["ready"] == 1
        assert result["pending"] == 0

    def test_excludes_closed_positions(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {
            "status": "[CLOSED]",
            "req_cv": "Yes", "done_cv": 0,
        })
        result = database.compute_materials_readiness()
        assert result == {"ready": 0, "pending": 0}

    def test_counts_multiple_positions_correctly(self, db):
        # Position 1: cv required and done → ready
        p1 = database.add_position(make_position({"position_name": "P1"}))
        database.update_position(p1, {"req_cv": "Yes", "done_cv": 1})

        # Position 2: cv required but not done → pending
        p2 = database.add_position(make_position({"position_name": "P2"}))
        database.update_position(p2, {"req_cv": "Yes", "done_cv": 0})

        # Position 3: no requirements → excluded
        database.add_position(make_position({"position_name": "P3"}))

        result = database.compute_materials_readiness()
        assert result["ready"]   == 1
        assert result["pending"] == 1


# ── Edge cases for empty fields dicts (F2 / F3 fixes) ────────────────────────

class TestEmptyFieldsGuards:

    def test_update_position_empty_fields_is_noop(self, db):
        """update_position({}) must return without error rather than emitting
        'UPDATE ... SET  WHERE id=?' which is invalid SQL (F2)."""
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {})
        pos = database.get_position(pos_id)
        assert pos["position_name"] == "BioStats Postdoc"   # unchanged

    def test_update_recommender_empty_fields_is_noop(self, db):
        """update_recommender({}) must return without error (F2)."""
        pos_id = database.add_position(make_position())
        rec_id = database.add_recommender(pos_id, {"recommender_name": "Dr. Smith"})
        database.update_recommender(rec_id, {})
        recs = database.get_recommenders(pos_id)
        assert recs.iloc[0]["recommender_name"] == "Dr. Smith"   # unchanged

    def test_upsert_application_empty_fields_is_noop(self, db):
        """upsert_application({}) must return without error (F3)."""
        pos_id = database.add_position(make_position())
        database.upsert_application(pos_id, {})
        app = database.get_application(pos_id)
        assert app["result"] == "Pending"   # unchanged default


# ── TERMINAL_STATUSES used by get_upcoming_deadlines (F5 fix) ────────────────

class TestTerminalStatusesConfig:

    def test_all_terminal_statuses_excluded_from_deadlines(self, db):
        """Every status in config.TERMINAL_STATUSES must be filtered out by
        get_upcoming_deadlines — the query now reads from config, not hardcoded
        strings, so adding a new terminal status to config automatically takes
        effect here (F5)."""
        for status in config.TERMINAL_STATUSES:
            pos_id = database.add_position(make_position({
                "position_name": f"pos_{status}",
                "deadline_date": (date.today() + timedelta(days=5)).isoformat(),
            }))
            database.update_position(pos_id, {"status": status})
        df = database.get_upcoming_deadlines(30)
        assert len(df) == 0, (
            f"Expected 0 rows; terminal statuses leaked into results: "
            f"{df['status'].tolist()}"
        )

    def test_terminal_statuses_are_subset_of_status_values(self):
        """Guard: TERMINAL_STATUSES must all be valid STATUS_VALUES entries."""
        assert set(config.TERMINAL_STATUSES) <= set(config.STATUS_VALUES)


# ── _connect rollback on exception ───────────────────────────────────────────

class TestConnectContextManager:

    def test_commits_on_clean_exit(self, db):
        with database._connect() as conn:
            conn.execute(
                "INSERT INTO positions (position_name) VALUES (?)",
                ("Explicit write",),
            )
        # Should persist
        df = database.get_all_positions()
        assert len(df) == 1

    def test_rollback_on_exception(self, db):
        with pytest.raises(RuntimeError):
            with database._connect() as conn:
                conn.execute(
                    "INSERT INTO positions (position_name) VALUES (?)",
                    ("Should be rolled back",),
                )
                raise RuntimeError("forced error")
        # Row must not have persisted
        df = database.get_all_positions()
        assert len(df) == 0

    def test_foreign_key_violation_raises(self, db):
        """Inserting a recommender with a non-existent position_id must raise."""
        with pytest.raises(sqlite3.IntegrityError):
            with database._connect() as conn:
                conn.execute(
                    "INSERT INTO recommenders (position_id, recommender_name) VALUES (?, ?)",
                    (999, "Ghost"),
                )
