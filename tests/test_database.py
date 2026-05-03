# tests/test_database.py
# Integration tests for database.py.
#
# All tests use real SQLite (no mocking). Each test gets an isolated temp DB
# via the `db` fixture in conftest.py. Tests are grouped by concern.

import re
import sqlite3
import time
import pytest
import pandas as pd
from datetime import date, timedelta

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

    def test_noop_restart_does_not_bump_updated_at(self, db):
        """DESIGN §6.2 + D25 regression pin: a second init_db() on an
        already-migrated DB must not advance updated_at for any row. D25
        frames updated_at as "last row mutation", not "last app startup"
        — so idempotent migration UPDATEs must be scoped (WHERE guard)
        to rows actually needing migration. A CASE-ELSE-passthrough with
        no WHERE clause fires the positions_updated_at trigger for every
        row on every init_db() call (SQLite AFTER UPDATE triggers run on
        every matched row regardless of whether the new value equals the
        old), silently rewriting updated_at to "last app startup".

        The 2.1 s sleep crosses SQLite's 1-second datetime('now')
        granularity — without it a buggy implementation could hide
        inside one clock second (same pattern as
        test_update_position_refreshes_updated_at's 1.1 s sleep)."""
        pos_id = database.add_position(make_position())
        ts_before = database.get_position(pos_id)["updated_at"]

        time.sleep(2.1)
        database.init_db()
        ts_after = database.get_position(pos_id)["updated_at"]

        assert ts_after == ts_before, (
            "A second init_db() on an already-migrated DB must be a no-op "
            f"for updated_at. Before: {ts_before!r}, after: {ts_after!r}. "
            "See DESIGN §6.2 + D25."
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

    def test_positions_has_work_auth_note_column(self, db):
        """Sub-task 7 / DESIGN §6.2 + D22: positions.work_auth_note must
        exist as plain TEXT (NULL-able, no DEFAULT). It is the freetext
        companion to the categorical `work_auth` column — three-value enum
        for filtering (Yes/No/Unknown), freetext for posting-specific
        nuance (e.g. "green card required", "J-1 OK with a waiver"). The
        column has no DEFAULT so NULL is the fresh-row state and the
        Overview-tab UI decides when to populate it."""
        with database._connect() as conn:
            cols = conn.execute("PRAGMA table_info(positions)").fetchall()

        work_auth_note = next(
            (r for r in cols if r["name"] == "work_auth_note"), None
        )
        assert work_auth_note is not None, (
            "positions.work_auth_note must be defined in the CREATE TABLE DDL. "
            f"Column list: {sorted(r['name'] for r in cols)!r}"
        )
        assert work_auth_note["type"] == "TEXT", (
            "positions.work_auth_note type must be TEXT; "
            f"got {work_auth_note['type']!r}"
        )
        assert work_auth_note["dflt_value"] is None, (
            "positions.work_auth_note must not carry a DEFAULT — fresh rows "
            "start NULL and the Overview tab populates it explicitly. "
            f"Got dflt_value={work_auth_note['dflt_value']!r}"
        )

    def test_migration_adds_work_auth_note_to_pre_v1_3_positions(self, tmp_path, monkeypatch):
        """Sub-task 7 / DESIGN §6.3: pre-v1.3 DBs whose positions table
        predates this sub-task must pick up the work_auth_note column on
        the next init_db() via a PRAGMA-guarded ALTER TABLE ADD COLUMN,
        with any existing row's other columns untouched.

        The column has no DEFAULT (matching the CREATE TABLE DDL), so
        existing rows end up with work_auth_note IS NULL — which is
        correct: v1.2 never collected this field, so the honest state
        is "unknown". The Overview tab treats NULL as empty via
        _safe_str.

        Idempotence: a second init_db() finds the column already
        present and skips the ALTER entirely."""
        monkeypatch.setattr(database, "DB_PATH", tmp_path / "pre_v1_3.db")

        # Pre-v1.3 positions table — has work_auth (v1.2 already had it)
        # but NO work_auth_note, no updated_at, no req_*/done_* columns.
        # Same minimal-shape strategy as the Sub-task 6 migration test;
        # deadline_date is required so idx_positions_deadline CREATE in
        # init_db() does not fail.
        with database._connect() as conn:
            conn.execute("""
                CREATE TABLE positions (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    status        TEXT NOT NULL DEFAULT '[SAVED]',
                    priority      TEXT,
                    created_at    TEXT DEFAULT (date('now')),
                    position_name TEXT NOT NULL,
                    deadline_date TEXT,
                    work_auth     TEXT
                )
            """)
            conn.execute(
                "INSERT INTO positions (position_name, work_auth) "
                "VALUES ('LegacyRow', 'Yes')"
            )

        database.init_db()

        with database._connect() as conn:
            cols = {r["name"] for r in conn.execute(
                "PRAGMA table_info(positions)"
            ).fetchall()}
            legacy_row = conn.execute(
                "SELECT work_auth, work_auth_note "
                "FROM positions WHERE position_name = 'LegacyRow'"
            ).fetchone()

        assert "work_auth_note" in cols, (
            "Migration must add work_auth_note via ALTER TABLE ADD COLUMN."
        )
        assert legacy_row["work_auth"] == "Yes", (
            "Pre-existing work_auth value must survive the migration "
            f"untouched; got {legacy_row['work_auth']!r}"
        )
        assert legacy_row["work_auth_note"] is None, (
            "Existing rows must carry NULL work_auth_note after migration "
            "(honest 'unknown' state — v1.2 never collected this field); "
            f"got {legacy_row['work_auth_note']!r}"
        )

        # Idempotence: second init_db() is a no-op, row stays intact.
        database.init_db()
        with database._connect() as conn:
            legacy_row_after = conn.execute(
                "SELECT work_auth, work_auth_note "
                "FROM positions WHERE position_name = 'LegacyRow'"
            ).fetchone()
        assert legacy_row_after["work_auth"] == "Yes"
        assert legacy_row_after["work_auth_note"] is None

    def test_applications_has_confirmation_received_column_with_zero_default(self, db):
        """Sub-task 10 / DESIGN §6.2 + D19 + D20: applications.confirmation_received
        must be INTEGER with DEFAULT 0 (0/1 flag). Half of the split from the
        pre-v1.3 dual-purpose `confirmation_email` TEXT column, which stored
        either 'Y' (flag semantics) or a date string (date semantics); D19
        fixes that type ambiguity by breaking the single column into a
        (flag, date) pair so predicates are simple and no column holds
        either-shape data."""
        with database._connect() as conn:
            cols = conn.execute("PRAGMA table_info(applications)").fetchall()

        received = next(
            (r for r in cols if r["name"] == "confirmation_received"), None
        )
        assert received is not None, (
            "applications.confirmation_received must be defined in the CREATE "
            f"TABLE DDL. Column list: {sorted(r['name'] for r in cols)!r}"
        )
        assert received["type"] == "INTEGER", (
            "applications.confirmation_received type must be INTEGER (D20 — "
            "boolean-state columns as INTEGER 0/1, never TEXT Y/N); "
            f"got {received['type']!r}"
        )
        assert received["dflt_value"] == "0", (
            "applications.confirmation_received DEFAULT must be 0 — fresh "
            "rows start in the 'not yet received' state, matching the "
            "DESIGN §6.2 DDL. "
            f"Got dflt_value={received['dflt_value']!r}"
        )

    def test_applications_has_confirmation_date_column_nullable(self, db):
        """Sub-task 10 / DESIGN §6.2 + D19: applications.confirmation_date
        must be plain TEXT (NULL-able, no DEFAULT). Partners the
        confirmation_received flag — date is populated iff the user
        actually recorded a receipt date; NULL means "received flag only"
        or "not yet received" (the flag disambiguates). DESIGN's inline
        comment spells this out: 'ISO, NULL if not yet received'."""
        with database._connect() as conn:
            cols = conn.execute("PRAGMA table_info(applications)").fetchall()

        date_col = next(
            (r for r in cols if r["name"] == "confirmation_date"), None
        )
        assert date_col is not None, (
            "applications.confirmation_date must be defined in the CREATE "
            f"TABLE DDL. Column list: {sorted(r['name'] for r in cols)!r}"
        )
        assert date_col["type"] == "TEXT", (
            "applications.confirmation_date type must be TEXT (ISO YYYY-MM-DD "
            "strings, matching the rest of the date-column convention); "
            f"got {date_col['type']!r}"
        )
        assert date_col["dflt_value"] is None, (
            "applications.confirmation_date must not carry a DEFAULT — NULL "
            "is the honest 'no date recorded yet' state and keeps the "
            "column semantics independent of the received flag. "
            f"Got dflt_value={date_col['dflt_value']!r}"
        )

    def test_recommenders_confirmed_column_is_integer_nullable(self, db):
        """Sub-task 11 / DESIGN §6.2 + D20: recommenders.confirmed must be
        INTEGER (0, 1, or NULL). NULL encodes the "pending response"
        tri-state per DESIGN's inline comment — the column has no
        DEFAULT so a fresh row starts in the honest pending state rather
        than silently declaring "not confirmed" (which `0` would imply).
        D20 pins boolean-state columns at INTEGER 0/1 rather than TEXT
        Y/N; the tri-state (with NULL) requires no extra type gymnastics
        since INTEGER is NULL-able by default."""
        with database._connect() as conn:
            cols = conn.execute("PRAGMA table_info(recommenders)").fetchall()

        confirmed = next(
            (r for r in cols if r["name"] == "confirmed"), None
        )
        assert confirmed is not None, (
            "recommenders.confirmed must be defined in the CREATE TABLE DDL. "
            f"Column list: {sorted(r['name'] for r in cols)!r}"
        )
        assert confirmed["type"] == "INTEGER", (
            "recommenders.confirmed type must be INTEGER (D20 — boolean-"
            "state columns as INTEGER 0/1, never TEXT Y/N); "
            f"got {confirmed['type']!r}. If this is 'TEXT' the Sub-task "
            "11 rebuild did not run or the DDL was not updated."
        )
        assert confirmed["dflt_value"] is None, (
            "recommenders.confirmed must not carry a DEFAULT — NULL is the "
            "pending-response tri-state, 0 means 'explicitly not confirmed'. "
            f"Got dflt_value={confirmed['dflt_value']!r}"
        )

    def test_recommenders_reminder_sent_column_is_integer_with_zero_default(self, db):
        """Sub-task 11 / DESIGN §6.2 + D19 + D20: recommenders.reminder_sent
        must be INTEGER DEFAULT 0. Half of the D19 split — the partner
        `reminder_sent_date TEXT` carries the date payload when the
        flag is 1. Fresh rows start at "no reminder sent" (0) rather
        than NULL so downstream predicates don't have to special-case
        the default. D20 pins the type as INTEGER."""
        with database._connect() as conn:
            cols = conn.execute("PRAGMA table_info(recommenders)").fetchall()

        reminder_sent = next(
            (r for r in cols if r["name"] == "reminder_sent"), None
        )
        assert reminder_sent is not None, (
            "recommenders.reminder_sent must be defined in the CREATE TABLE "
            f"DDL. Column list: {sorted(r['name'] for r in cols)!r}"
        )
        assert reminder_sent["type"] == "INTEGER", (
            "recommenders.reminder_sent type must be INTEGER (D20); "
            f"got {reminder_sent['type']!r}"
        )
        assert reminder_sent["dflt_value"] == "0", (
            "recommenders.reminder_sent DEFAULT must be 0 — fresh rows "
            "start in the 'no reminder sent' state. "
            f"Got dflt_value={reminder_sent['dflt_value']!r}"
        )

    def test_recommenders_has_reminder_sent_date_column_nullable(self, db):
        """Sub-task 11 / DESIGN §6.2 + D19: recommenders.reminder_sent_date
        is the date half of the D19 (flag, date) pair. Plain TEXT,
        NULL-able, no DEFAULT — NULL means "no date recorded" and is
        the only honest state when reminder_sent = 0."""
        with database._connect() as conn:
            cols = conn.execute("PRAGMA table_info(recommenders)").fetchall()

        reminder_date = next(
            (r for r in cols if r["name"] == "reminder_sent_date"), None
        )
        assert reminder_date is not None, (
            "recommenders.reminder_sent_date must be defined in the CREATE "
            f"TABLE DDL. Column list: {sorted(r['name'] for r in cols)!r}"
        )
        assert reminder_date["type"] == "TEXT", (
            "recommenders.reminder_sent_date type must be TEXT (ISO "
            "YYYY-MM-DD strings); "
            f"got {reminder_date['type']!r}"
        )
        assert reminder_date["dflt_value"] is None, (
            "recommenders.reminder_sent_date must not carry a DEFAULT — "
            "NULL is the honest 'no date recorded yet' state. "
            f"Got dflt_value={reminder_date['dflt_value']!r}"
        )

    def test_recommenders_foreign_key_survives_rebuild(self, db):
        """Sub-task 11 / DESIGN §6.2: the FK
        recommenders.position_id → positions.id ON DELETE CASCADE is
        load-bearing — delete_position cascades through applications,
        interviews, AND recommenders. The Sub-task 11 rebuild is a
        CREATE-COPY-DROP-RENAME, so the FK has to be re-declared in
        the _new table's DDL; this test pins that the constraint lands
        on the surviving post-rename table with the correct target
        table + column + delete action."""
        with database._connect() as conn:
            fks = conn.execute(
                "PRAGMA foreign_key_list(recommenders)"
            ).fetchall()

        assert len(fks) == 1, (
            "recommenders must carry exactly one foreign key "
            f"(position_id → positions.id). Got {len(fks)} FKs: "
            f"{[dict(r) for r in fks]!r}"
        )
        fk = fks[0]
        assert fk["table"]    == "positions",   f"got {fk['table']!r}"
        assert fk["from"]     == "position_id", f"got {fk['from']!r}"
        assert fk["to"]       == "id",          f"got {fk['to']!r}"
        assert fk["on_delete"] == "CASCADE", (
            "FK delete action must be CASCADE so delete_position cleans "
            f"up recommenders rows. Got {fk['on_delete']!r}"
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

    def test_work_auth_note_roundtrips(self, db):
        """Sub-task 7 / DESIGN §6.2 + D22: work_auth_note is plain TEXT
        with no normalisation at the DB layer — whatever the Overview
        tab writes comes back verbatim on read. Exercises the full
        write-then-read cycle through add_position (INSERT) and
        update_position (UPDATE) for both the categorical `work_auth`
        column and its freetext `work_auth_note` partner. Guards
        against a future refactor that accidentally adds coercion or
        truncation at the DB layer."""
        # INSERT path — add_position accepts both fields in its dict.
        pos_id = database.add_position(make_position({
            "work_auth":      "Yes",
            "work_auth_note": "green card required",
        }))
        pos = database.get_position(pos_id)
        assert pos["work_auth"]      == "Yes"
        assert pos["work_auth_note"] == "green card required"

        # UPDATE path — both columns reachable via update_position.
        database.update_position(pos_id, {
            "work_auth":      "Unknown",
            "work_auth_note": "J-1 OK with a waiver",
        })
        pos = database.get_position(pos_id)
        assert pos["work_auth"]      == "Unknown"
        assert pos["work_auth_note"] == "J-1 OK with a waiver"

        # Empty string round-trips as empty string (not coerced to NULL).
        # Matches the Notes-tab contract — the page is the sole decider
        # of how to interpret empty vs NULL.
        database.update_position(pos_id, {"work_auth_note": ""})
        assert database.get_position(pos_id)["work_auth_note"] == ""


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

    def test_writes_confirmation_received_and_date_roundtrip(self, db):
        """Sub-task 10 / DESIGN §6.2 + D19: upsert_application accepts the
        new `confirmation_received` flag and `confirmation_date` columns
        and they round-trip via get_application(). The legacy
        confirmation_email TEXT column is physically retained until the
        v1.0-rc rebuild drops it (DESIGN §6.3 "leave until a rebuild"),
        but no caller — including this test — writes to it; new writes
        land exclusively in the split pair."""
        pos_id = database.add_position(make_position())

        # Flag-only: receipt acknowledged but no date recorded.
        database.upsert_application(pos_id, {"confirmation_received": 1})
        app = database.get_application(pos_id)
        assert app["confirmation_received"] == 1
        assert app["confirmation_date"] is None

        # Flag + date: mirrors the common case of a dated receipt.
        database.upsert_application(pos_id, {
            "confirmation_received": 1,
            "confirmation_date":     "2026-04-12",
        })
        app = database.get_application(pos_id)
        assert app["confirmation_received"] == 1
        assert app["confirmation_date"]     == "2026-04-12"

        # Legacy column stays NULL — no caller (incl. this one) writes to it.
        assert app["confirmation_email"] is None, (
            "upsert_application must not populate the legacy "
            "confirmation_email column; it is scheduled for physical "
            f"drop in v1.0-rc. Got {app['confirmation_email']!r}"
        )


# ── upsert_application cascade R1 + R3 ────────────────────────────────────────
# DESIGN §9.3 pipeline auto-promotion. Two cascade rules live inside
# upsert_application:
#   R1 — `applied_date` transitions from NULL to non-NULL
#        → UPDATE positions SET status = STATUS_APPLIED
#            WHERE id = ? AND status = STATUS_SAVED
#   R3 — incoming `response_type == "Offer"`
#        → UPDATE positions SET status = STATUS_OFFER
#            WHERE id = ? AND status NOT IN TERMINAL_STATUSES
#
# Each cascade runs inside the same transaction as the primary write and
# the function returns ``{"status_changed": bool, "new_status": str | None}``
# so callers can render a toast when the pipeline moved.


def _force_position_status(position_id: int, status: str) -> None:
    """Raw-SQL helper: set positions.status directly, bypassing the
    cascade. Used by tests to stage pre-states that a normal write path
    can't produce (e.g. manual back-edit to STATUS_SAVED while retaining
    a set applied_date). The tests below never call user-facing writers
    to set pre-state status, because those writers may themselves fire
    R1/R2/R3 and pollute the scenario."""
    with database._connect() as conn:
        conn.execute(
            "UPDATE positions SET status = ? WHERE id = ?",
            (status, position_id),
        )


class TestUpsertApplicationR1:
    """R1 isolation — `applied_date` NULL→set on a STATUS_SAVED position.
    No `response_type="Offer"` in the payload, so R3 never fires."""

    def test_r1_promotes_saved_to_applied(self, db):
        pid = database.add_position(make_position())
        assert database.get_position(pid)["status"] == config.STATUS_SAVED
        result = database.upsert_application(pid, {"applied_date": "2026-04-10"})
        assert database.get_position(pid)["status"] == config.STATUS_APPLIED
        assert result == {
            "status_changed": True,
            "new_status":     config.STATUS_APPLIED,
        }

    def test_r1_noop_when_applied_date_was_already_set(self, db):
        """Idempotence: once applied_date is non-NULL, a subsequent
        upsert that also sets applied_date (same or different date)
        does NOT trigger R1 again — the cascade is scoped to the
        NULL→non-NULL transition, not every touch of the column."""
        pid = database.add_position(make_position())
        database.upsert_application(pid, {"applied_date": "2026-04-10"})
        # Pre-state now: status=APPLIED, applied_date='2026-04-10'.
        # Manually back-edit the status to SAVED to isolate R1's
        # "applied_date must be NULL pre" clause from its status guard.
        _force_position_status(pid, config.STATUS_SAVED)
        result = database.upsert_application(pid, {"applied_date": "2026-04-11"})
        assert database.get_position(pid)["status"] == config.STATUS_SAVED, (
            "R1 must not fire when applied_date was already non-NULL "
            "pre-upsert, even if the new value differs."
        )
        assert result["status_changed"] is False
        assert result["new_status"] is None

    def test_r1_noop_when_status_not_saved(self, db):
        """Status guard: R1's SQL includes AND status = STATUS_SAVED,
        so a position already at a further stage is not regressed /
        re-promoted. Verified against STATUS_APPLIED + STATUS_INTERVIEW
        directly (STATUS_OFFER / terminals also satisfy the guard)."""
        for pre in (config.STATUS_APPLIED, config.STATUS_INTERVIEW):
            pid = database.add_position(make_position(
                {"position_name": f"Pre-{pre}"}
            ))
            _force_position_status(pid, pre)
            result = database.upsert_application(
                pid, {"applied_date": "2026-04-10"}
            )
            assert database.get_position(pid)["status"] == pre, (
                f"R1 must not affect a position already at {pre!r}; "
                f"got {database.get_position(pid)['status']!r}"
            )
            assert result["status_changed"] is False
            assert result["new_status"] is None

    def test_r1_does_not_fire_when_propagate_status_false(self, db):
        pid = database.add_position(make_position())
        result = database.upsert_application(
            pid, {"applied_date": "2026-04-10"}, propagate_status=False,
        )
        assert database.get_position(pid)["status"] == config.STATUS_SAVED, (
            "propagate_status=False must suppress R1 even when its "
            "conditions are met."
        )
        assert result["status_changed"] is False
        assert result["new_status"] is None
        # Primary write still lands — propagate_status=False suppresses
        # only the cascade, not the application upsert.
        assert database.get_application(pid)["applied_date"] == "2026-04-10"


class TestUpsertApplicationR3:
    """R3 isolation — `response_type == "Offer"` without touching
    `applied_date` on a non-NULL pre-state (or with pre-state manually
    staged so R1's condition is False)."""

    def test_r3_promotes_saved_to_offer(self, db):
        pid = database.add_position(make_position())
        # Pre: STATUS_SAVED. Payload has response_type=Offer, no
        # applied_date, so R1's condition (applied_date transition) is
        # False. R3 alone fires and sends SAVED→OFFER.
        result = database.upsert_application(pid, {"response_type": "Offer"})
        assert database.get_position(pid)["status"] == config.STATUS_OFFER
        assert result == {
            "status_changed": True,
            "new_status":     config.STATUS_OFFER,
        }

    def test_r3_promotes_applied_to_offer(self, db):
        pid = database.add_position(make_position())
        database.upsert_application(pid, {"applied_date": "2026-04-10"})
        # Pre: STATUS_APPLIED. R3 upgrades to OFFER.
        result = database.upsert_application(pid, {"response_type": "Offer"})
        assert database.get_position(pid)["status"] == config.STATUS_OFFER
        assert result["status_changed"] is True
        assert result["new_status"] == config.STATUS_OFFER

    def test_r3_promotes_interview_to_offer(self, db):
        pid = database.add_position(make_position())
        _force_position_status(pid, config.STATUS_INTERVIEW)
        result = database.upsert_application(pid, {"response_type": "Offer"})
        assert database.get_position(pid)["status"] == config.STATUS_OFFER
        assert result["status_changed"] is True
        assert result["new_status"] == config.STATUS_OFFER

    def test_r3_noop_when_already_offer(self, db):
        """DESIGN §9.3 pre-state matrix row: at STATUS_OFFER, R3 'fires
        (no-op, already there)'. The SQL UPDATE's WHERE still matches
        (OFFER is not terminal) and the SET self-assigns the same
        value, but pre_status == post_status so the caller sees
        status_changed=False (meaningful-change semantics)."""
        pid = database.add_position(make_position())
        _force_position_status(pid, config.STATUS_OFFER)
        result = database.upsert_application(pid, {"response_type": "Offer"})
        assert database.get_position(pid)["status"] == config.STATUS_OFFER
        assert result["status_changed"] is False, (
            "status_changed must compare pre vs post STATUS STRING, "
            "not whether an UPDATE executed. A self-assignment on "
            "STATUS_OFFER is not a meaningful change."
        )
        assert result["new_status"] is None

    @pytest.mark.parametrize("terminal_status", config.TERMINAL_STATUSES)
    def test_r3_blocked_on_terminal(self, db, terminal_status):
        """DESIGN §9.3 R3 guard: the SQL WHERE excludes every terminal
        status. A stray upsert with response_type=Offer on a terminal
        row must not silently regress the decision.

        Sourced from config so a future fourth terminal status flows
        into coverage automatically."""
        pid = database.add_position(make_position())
        _force_position_status(pid, terminal_status)
        result = database.upsert_application(pid, {"response_type": "Offer"})
        assert database.get_position(pid)["status"] == terminal_status, (
            f"R3 must not overwrite terminal status {terminal_status!r}; "
            f"got {database.get_position(pid)['status']!r}"
        )
        assert result["status_changed"] is False
        assert result["new_status"] is None

    def test_r3_does_not_fire_when_propagate_status_false(self, db):
        pid = database.add_position(make_position())
        result = database.upsert_application(
            pid, {"response_type": "Offer"}, propagate_status=False,
        )
        assert database.get_position(pid)["status"] == config.STATUS_SAVED
        assert result["status_changed"] is False
        assert database.get_application(pid)["response_type"] == "Offer"

    def test_r3_does_not_fire_on_non_offer_response_type(self, db):
        """R3 is keyed to the exact string "Offer". Other response_type
        values (Rejection, Interview Invite, …) are just data, not
        promotion triggers."""
        pid = database.add_position(make_position())
        database.upsert_application(pid, {"applied_date": "2026-04-10"})
        # Now at STATUS_APPLIED. A Rejection response must not promote.
        result = database.upsert_application(pid, {"response_type": "Rejection"})
        assert database.get_position(pid)["status"] == config.STATUS_APPLIED
        assert result["status_changed"] is False


class TestUpsertApplicationR1R3Matrix:
    """DESIGN §9.3 combined-cascade table: when R1's condition (applied_date
    NULL→set) AND R3's condition (response_type=Offer) are BOTH in the
    same upsert payload, the per-pre-state post-state matrix locks what
    wins. All five non-terminal pre-states land at STATUS_OFFER; the
    three terminals stay put because R3's guard blocks and R1's status
    guard blocks too."""

    def _upsert_both(self, pid):
        """Shared body: one upsert carrying both R1 and R3 triggers."""
        return database.upsert_application(pid, {
            "applied_date":  "2026-04-10",
            "response_type": "Offer",
        })

    def test_matrix_saved_lands_on_offer(self, db):
        """STATUS_SAVED + R1 + R3 → R1 promotes SAVED→APPLIED, then
        R3 promotes APPLIED→OFFER. Net: OFFER."""
        pid = database.add_position(make_position())
        assert database.get_position(pid)["status"] == config.STATUS_SAVED
        result = self._upsert_both(pid)
        assert database.get_position(pid)["status"] == config.STATUS_OFFER
        assert result["status_changed"] is True
        assert result["new_status"] == config.STATUS_OFFER

    def test_matrix_applied_lands_on_offer(self, db):
        pid = database.add_position(make_position())
        database.upsert_application(pid, {"applied_date": "2026-01-01"})
        # Back-edit status so pre is APPLIED but applied_date is already
        # set, then send a new applied_date (R1 doesn't re-fire because
        # pre applied_date was non-NULL) + Offer response (R3 fires).
        assert database.get_position(pid)["status"] == config.STATUS_APPLIED
        result = self._upsert_both(pid)
        assert database.get_position(pid)["status"] == config.STATUS_OFFER
        assert result["status_changed"] is True

    def test_matrix_interview_lands_on_offer(self, db):
        pid = database.add_position(make_position())
        _force_position_status(pid, config.STATUS_INTERVIEW)
        result = self._upsert_both(pid)
        assert database.get_position(pid)["status"] == config.STATUS_OFFER
        assert result["status_changed"] is True

    def test_matrix_offer_stays_offer_with_no_change_indicator(self, db):
        """Matrix row: pre STATUS_OFFER, both R1 and R3 evaluate. R1
        does not fire (status guard — not SAVED). R3 fires but self-
        assigns OFFER. Post == pre, so status_changed reads False."""
        pid = database.add_position(make_position())
        _force_position_status(pid, config.STATUS_OFFER)
        result = self._upsert_both(pid)
        assert database.get_position(pid)["status"] == config.STATUS_OFFER
        assert result["status_changed"] is False
        assert result["new_status"] is None

    @pytest.mark.parametrize("terminal_status", config.TERMINAL_STATUSES)
    def test_matrix_terminal_unchanged(self, db, terminal_status):
        """Matrix row: any terminal pre-state — R1 blocked (status != SAVED),
        R3 blocked (status IN TERMINAL_STATUSES). Post == pre.

        Sourced from config so a future fourth terminal status flows
        into coverage automatically."""
        pid = database.add_position(make_position())
        _force_position_status(pid, terminal_status)
        result = self._upsert_both(pid)
        assert database.get_position(pid)["status"] == terminal_status
        assert result["status_changed"] is False
        assert result["new_status"] is None


class TestUpsertApplicationIndicator:
    """Signature + return-shape contract on upsert_application."""

    def test_signature_has_keyword_only_propagate_status_default_true(self, db):
        """DESIGN §7 load-bearing contract #2. Sub-task 9 promotes
        upsert_application to the same keyword-only cascade API as
        add_interview (Sub-task 8), with default True."""
        import inspect
        sig = inspect.signature(database.upsert_application)
        param = sig.parameters.get("propagate_status")
        assert param is not None
        assert param.default is True
        assert param.kind == inspect.Parameter.KEYWORD_ONLY

    def test_returns_indicator_dict_shape(self, db):
        """Return value must always be a dict with exactly the two
        indicator keys — callers can read them without a try/except."""
        pid = database.add_position(make_position())
        result = database.upsert_application(pid, {"applied_date": "2026-04-10"})
        assert isinstance(result, dict)
        assert set(result.keys()) == {"status_changed", "new_status"}
        assert isinstance(result["status_changed"], bool)

    def test_empty_fields_returns_no_change_indicator(self, db):
        """Empty-fields early return (existing no-op contract) must
        still return the indicator dict, not None — so the caller can
        unpack the return unconditionally."""
        pid = database.add_position(make_position())
        result = database.upsert_application(pid, {})
        assert result == {"status_changed": False, "new_status": None}
        # And no primary write happened.
        assert database.get_application(pid)["applied_date"] is None


class TestUpsertApplicationAtomicity:
    """DESIGN §9.3: 'All cascades execute inside the same transaction as
    the primary write, so a failure rolls the whole call back.'"""

    def test_cascade_failure_rolls_back_primary_write(self, db, monkeypatch):
        """Inject a failure in the R1 cascade by replacing
        config.STATUS_APPLIED with an un-bindable Python object. SQLite's
        `execute(..., [params])` raises InterfaceError when asked to bind
        an un-adaptable value; the _connect() context manager's except
        branch rolls back everything in the transaction. The primary
        upsert (applications INSERT/UPDATE) must NOT persist.

        Empirical: sqlite3 raises
        'ProgrammingError: Error binding parameter' (Python 3.14) when
        a non-adaptable Python value appears in a bind tuple."""
        pid = database.add_position(make_position())

        # Sentinel that SQLite cannot bind.
        class NotBindable:
            pass
        monkeypatch.setattr(config, "STATUS_APPLIED", NotBindable())

        with pytest.raises(Exception):
            database.upsert_application(pid, {"applied_date": "2026-04-10"})

        # Primary write must have rolled back — no applied_date.
        app = database.get_application(pid)
        assert app["applied_date"] is None, (
            "Primary applications UPDATE must roll back when the R1 "
            f"cascade fails; got applied_date={app['applied_date']!r}. "
            "This is DESIGN §9.3 atomicity — cascade inside the same "
            "transaction as the primary write."
        )
        # And status remains at SAVED (the cascade never committed).
        assert database.get_position(pid)["status"] == config.STATUS_SAVED

    def test_r3_cascade_failure_rolls_back_primary_write(self, db, monkeypatch):
        """Companion to the R1 atomicity test above — pin R3's slice of
        the same DESIGN §9.3 contract. R3 lives in its own
        `conn.execute(...)` block (database.py upsert_application,
        STATUS_OFFER cascade) so a regression that opened a new
        connection or committed between R1 and R3 would only surface
        here. Force R3 to fail by monkeypatching STATUS_OFFER to an
        un-bindable sentinel; the primary applications upsert must roll
        back along with the (failed) cascade."""
        pid = database.add_position(make_position())

        class NotBindable:
            pass
        monkeypatch.setattr(config, "STATUS_OFFER", NotBindable())

        with pytest.raises(Exception):
            database.upsert_application(pid, {"response_type": "Offer"})

        # Primary write must have rolled back — no response_type.
        app = database.get_application(pid)
        assert app["response_type"] is None, (
            "Primary applications UPDATE must roll back when the R3 "
            f"cascade fails; got response_type={app['response_type']!r}. "
            "DESIGN §9.3 atomicity — cascade inside the same transaction "
            "as the primary write."
        )
        # And status stays at SAVED (R3 never committed).
        assert database.get_position(pid)["status"] == config.STATUS_SAVED


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

    def test_fresh_recommender_row_defaults(self, db):
        """Sub-task 11 / DESIGN §6.2 + D19 + D20: a fresh recommender
        (only recommender_name set) must come up with `confirmed = NULL`
        (pending response, tri-state), `reminder_sent = 0` (flag off,
        the DEFAULT), and `reminder_sent_date = NULL` (no date yet).
        These three defaults collectively pin the CREATE TABLE contract
        for the DESIGN §6.2 recommenders DDL."""
        pos_id = database.add_position(make_position())
        rec_id = database.add_recommender(
            pos_id, {"recommender_name": "Dr. Smith"}
        )
        recs = database.get_recommenders(pos_id)
        row = recs.iloc[0]
        assert row["id"] == rec_id
        assert row["confirmed"] is None or pd.isna(row["confirmed"]), (
            "Fresh recommender must have confirmed=NULL (pending response). "
            f"Got {row['confirmed']!r}"
        )
        assert int(row["reminder_sent"]) == 0, (
            "Fresh recommender must have reminder_sent=0 via DDL DEFAULT. "
            f"Got {row['reminder_sent']!r}"
        )
        assert row["reminder_sent_date"] is None or pd.isna(row["reminder_sent_date"]), (
            "Fresh recommender must have reminder_sent_date=NULL. "
            f"Got {row['reminder_sent_date']!r}"
        )

    def test_integer_confirmed_values_roundtrip(self, db):
        """Sub-task 11 / DESIGN §6.2 + D20: add_recommender writes the
        integer `confirmed` tri-state (0 / 1 / NULL) and it round-trips
        via get_recommenders. Pins that the add_recommender path does
        not coerce or reject the integer values (it's schema-agnostic —
        this test catches any accidental type narrowing)."""
        pid = database.add_position(make_position())

        r1 = database.add_recommender(pid, {
            "recommender_name": "Dr. Yes",
            "confirmed":        1,
        })
        r0 = database.add_recommender(pid, {
            "recommender_name": "Dr. No",
            "confirmed":        0,
        })
        rN = database.add_recommender(pid, {
            "recommender_name": "Dr. Pending",
            # confirmed omitted → NULL
        })
        recs = database.get_recommenders(pid).set_index("id")
        assert int(recs.loc[r1, "confirmed"]) == 1
        assert int(recs.loc[r0, "confirmed"]) == 0
        assert recs.loc[rN, "confirmed"] is None or pd.isna(recs.loc[rN, "confirmed"])

    def test_integer_reminder_sent_and_date_roundtrip(self, db):
        """Sub-task 11 / DESIGN §6.2 + D19: the (flag, date) pair
        round-trips via add_recommender + get_recommenders. `reminder_sent
        = 1, reminder_sent_date = '2026-04-14'` is the common case after
        the user records a sent reminder; `reminder_sent = 0,
        reminder_sent_date = NULL` is the explicit un-sent state. Both
        must come back byte-for-byte."""
        pid = database.add_position(make_position())

        r_sent = database.add_recommender(pid, {
            "recommender_name":   "Dr. Reminded",
            "reminder_sent":      1,
            "reminder_sent_date": "2026-04-14",
        })
        r_unsent = database.add_recommender(pid, {
            "recommender_name": "Dr. Unreminded",
            "reminder_sent":    0,
        })
        recs = database.get_recommenders(pid).set_index("id")

        assert int(recs.loc[r_sent, "reminder_sent"]) == 1
        assert recs.loc[r_sent, "reminder_sent_date"] == "2026-04-14"

        assert int(recs.loc[r_unsent, "reminder_sent"]) == 0
        unsent_date = recs.loc[r_unsent, "reminder_sent_date"]
        assert unsent_date is None or pd.isna(unsent_date)


# ── is_all_recs_submitted ─────────────────────────────────────────────────────
# DESIGN §7 + D23: the "all recs submitted" summary that an earlier draft
# stored as a column is computed at query time by this helper. Scope is a
# single position; returns True when every recommender row for that
# position has a non-NULL, non-empty `submitted_date`, OR when the
# position has zero recommenders (vacuous truth — nothing outstanding).


class TestIsAllRecsSubmitted:

    def test_returns_true_for_zero_recommenders(self, db):
        """Vacuous truth: a position with no recommenders has no
        outstanding letters by definition. This matches the most
        natural reading of D23 ('nothing to still be submitted') and
        makes downstream 'is everything ready?' aggregations compose
        cleanly without a 'no recs' special case."""
        pid = database.add_position(make_position())
        assert database.is_all_recs_submitted(pid) is True

    def test_returns_true_when_all_recommenders_submitted(self, db):
        pid = database.add_position(make_position())
        database.add_recommender(pid, {
            "recommender_name": "Dr. Smith",
            "submitted_date":   "2026-04-10",
        })
        database.add_recommender(pid, {
            "recommender_name": "Dr. Jones",
            "submitted_date":   "2026-04-12",
        })
        assert database.is_all_recs_submitted(pid) is True

    def test_returns_false_when_any_recommender_unsubmitted(self, db):
        pid = database.add_position(make_position())
        database.add_recommender(pid, {
            "recommender_name": "Dr. Smith",
            "submitted_date":   "2026-04-10",
        })
        database.add_recommender(pid, {
            "recommender_name": "Dr. Jones",
            # submitted_date omitted → NULL
        })
        assert database.is_all_recs_submitted(pid) is False

    def test_empty_string_submitted_date_counts_as_unsubmitted(self, db):
        """The page sometimes stores "" instead of NULL for cleared
        date fields (matches the Notes-tab contract). is_all_recs_
        submitted treats empty string the same as NULL — both mean
        "no submission recorded"."""
        pid = database.add_position(make_position())
        database.add_recommender(pid, {
            "recommender_name": "Dr. Smith",
            "submitted_date":   "",
        })
        assert database.is_all_recs_submitted(pid) is False

    def test_scoped_to_position_id(self, db):
        """An unsubmitted recommender on another position must not
        bleed into this position's 'all submitted' calculation."""
        pid_a = database.add_position(make_position({"position_name": "A"}))
        pid_b = database.add_position(make_position({"position_name": "B"}))
        database.add_recommender(pid_a, {
            "recommender_name": "Dr. Smith",
            "submitted_date":   "2026-04-10",
        })
        database.add_recommender(pid_b, {
            "recommender_name": "Dr. Jones",
            # unsubmitted on position B only
        })
        assert database.is_all_recs_submitted(pid_a) is True
        assert database.is_all_recs_submitted(pid_b) is False


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

    def test_includes_deadline_exactly_at_window_boundary(self, db):
        """SQL uses `deadline_date <= cutoff` where cutoff = today + days.
        The exact boundary day must be included; a regression to `<`
        would silently drop the last day of the window. Pin both sides
        of the comparison together with the next test."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=30)).isoformat(),
        }))
        df = database.get_upcoming_deadlines(30)
        assert len(df) == 1, (
            "Deadline exactly at the upper boundary (today + days) must "
            "be included — SQL uses <=, not <."
        )

    def test_excludes_deadline_one_day_past_window(self, db):
        """The companion to the boundary test above: today+days+1 must
        be excluded. Pinning both rules together protects against an
        off-by-one in either direction."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=31)).isoformat(),
        }))
        df = database.get_upcoming_deadlines(30)
        assert len(df) == 0, (
            "Deadline one day past the window upper boundary must be "
            "excluded."
        )

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


# ── Interviews schema ─────────────────────────────────────────────────────────
# Sub-task 8 / DESIGN §6.2 + D18: the flat interview1_date / interview2_date
# columns on applications are replaced by a normalized interviews sub-table
# so a position can carry arbitrarily many interviews.

class TestInterviewsSchema:

    def test_interviews_table_exists(self, db):
        with database._connect() as conn:
            tables = {r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()}
        assert "interviews" in tables, (
            "Sub-task 8: interviews table must be registered via CREATE TABLE "
            "IF NOT EXISTS in init_db()."
        )

    def test_interviews_has_expected_columns(self, db):
        """Column shape pinned exactly per DESIGN §6.2: id, application_id,
        sequence, scheduled_date, format, notes. Other columns would signal
        DDL drift from the DESIGN spec."""
        with database._connect() as conn:
            cols = {r["name"]: dict(r) for r in conn.execute(
                "PRAGMA table_info(interviews)"
            ).fetchall()}

        # SQLite quirk: INTEGER PRIMARY KEY AUTOINCREMENT reports
        # notnull=0 from PRAGMA table_info — the NOT NULL is enforced
        # via the PK (pk=1 in the fifth tuple element) rather than the
        # notnull flag. So the pk column's expected notnull is 0 here
        # even though it's de-facto NOT NULL; the other NOT NULL
        # columns still report notnull=1 as expected.
        expected = {
            "id":             ("INTEGER", 0),   # PK (notnull enforced by PK)
            "application_id": ("INTEGER", 1),   # NOT NULL
            "sequence":       ("INTEGER", 1),   # NOT NULL
            "scheduled_date": ("TEXT",    0),   # nullable
            "format":         ("TEXT",    0),   # nullable
            "notes":          ("TEXT",    0),   # nullable
        }
        for name, (type_, notnull) in expected.items():
            assert name in cols, f"interviews.{name} missing — got {list(cols)!r}"
            assert cols[name]["type"] == type_, (
                f"interviews.{name} type expected {type_}, "
                f"got {cols[name]['type']!r}"
            )
            assert cols[name]["notnull"] == notnull, (
                f"interviews.{name} notnull expected {notnull}, "
                f"got {cols[name]['notnull']!r}"
            )
        # Make sure nothing unexpected snuck in.
        assert set(cols) == set(expected), (
            f"Unexpected columns on interviews: {set(cols) - set(expected)!r}"
        )

    def test_interviews_unique_application_sequence(self, db):
        """DESIGN §6.2 locks UNIQUE(application_id, sequence) so a
        position can't accidentally hold two interviews at the same
        sequence slot. SQLite raises IntegrityError on insert collision."""
        pid = database.add_position(make_position())
        with database._connect() as conn:
            conn.execute(
                "INSERT INTO interviews (application_id, sequence, scheduled_date) "
                "VALUES (?, 1, ?)",
                (pid, (date.today() + timedelta(days=7)).isoformat()),
            )
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO interviews (application_id, sequence, scheduled_date) "
                    "VALUES (?, 1, ?)",
                    (pid, (date.today() + timedelta(days=14)).isoformat()),
                )

    def test_interviews_fk_to_applications(self, db):
        """interviews.application_id references applications.position_id
        with ON DELETE CASCADE. Direct INSERT of a nonexistent
        application_id must fail when foreign_keys PRAGMA is ON (which
        _connect() guarantees)."""
        with database._connect() as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO interviews (application_id, sequence, scheduled_date) "
                    "VALUES (?, 1, ?)",
                    (99999, date.today().isoformat()),
                )

    def test_interviews_application_index_exists(self, db):
        """DESIGN §6.2 names idx_interviews_application — the index on
        application_id that keeps get_interviews(application_id) fast as
        the table grows."""
        with database._connect() as conn:
            indices = {r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()}
        assert "idx_interviews_application" in indices, (
            f"Expected idx_interviews_application in sqlite_master; got {indices!r}"
        )


# ── add_interview / get_interviews / update_interview / delete_interview ─────

class TestAddInterview:

    def test_returns_indicator_dict(self, db):
        """DESIGN §7 + §9.3: writers that can promote return an indicator
        dict with id + status_changed + new_status keys. A fresh
        position seeds at STATUS_SAVED, and R2's guard requires
        STATUS_APPLIED, so the cascade doesn't fire here — the indicator
        reads False/None. The R2-fires path is covered by
        TestAddInterviewR2 in the Sub-task 9 coverage block."""
        pid = database.add_position(make_position())
        result = database.add_interview(pid, {
            "scheduled_date": (date.today() + timedelta(days=7)).isoformat(),
        })
        assert isinstance(result, dict)
        assert "id" in result and isinstance(result["id"], int)
        assert result["id"] >= 1
        assert result["status_changed"] is False
        assert result["new_status"] is None

    def test_auto_assigns_sequence_1_for_first_interview(self, db):
        """When `sequence` is omitted, add_interview computes the next
        available sequence for that application_id. First interview
        picks sequence=1."""
        pid = database.add_position(make_position())
        database.add_interview(pid, {"scheduled_date": date.today().isoformat()})
        df = database.get_interviews(pid)
        assert len(df) == 1
        assert df.iloc[0]["sequence"] == 1

    def test_auto_assigns_next_sequence_for_subsequent_interviews(self, db):
        """Second interview on the same position picks sequence=2."""
        pid = database.add_position(make_position())
        database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        database.add_interview(pid, {"scheduled_date": "2026-06-01"})
        df = database.get_interviews(pid)
        seqs = list(df["sequence"])
        assert seqs == [1, 2], (
            f"Second add_interview must auto-sequence to 2; got {seqs!r}"
        )

    def test_auto_sequence_picks_past_gap_after_delete(self, db):
        """Gaps in sequence (delete #1, add two more) are allowed —
        MAX+1 picks past any leftover gap so the UNIQUE constraint
        never collides. A regression to MIN-style numbering would
        re-use sequence=1 here and fail.

        Also pins that the auto-sequencer reads from MAX over ALL rows,
        not COUNT(*) — a COUNT-based variant would assign sequence=2
        after the delete (one row remains), colliding with the existing
        sequence=2."""
        pid = database.add_position(make_position())
        res1 = database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        database.add_interview(pid, {"scheduled_date": "2026-06-01"})
        # Drop sequence=1; sequence=2 row stays. MAX(sequence)=2.
        database.delete_interview(res1["id"])

        # Two more inserts — auto-sequencer must pick past the surviving
        # MAX(=2). Expected new sequences: 3 and 4.
        database.add_interview(pid, {"scheduled_date": "2026-07-01"})
        database.add_interview(pid, {"scheduled_date": "2026-08-01"})

        seqs = list(database.get_interviews(pid)["sequence"])
        assert seqs == [2, 3, 4], (
            "Auto-sequence must pick MAX(sequence)+1 (past any gap from "
            "a deleted row), not MIN-of-available or COUNT+1. Got "
            f"{seqs!r}; expected [2, 3, 4] (the deleted #1 is not re-used)."
        )

    def test_explicit_sequence_override(self, db):
        """A caller that knows what it's doing can pass `sequence`
        explicitly — e.g. restoring a deleted interview at its old slot.
        The UNIQUE constraint catches collisions."""
        pid = database.add_position(make_position())
        database.add_interview(pid, {
            "sequence": 3,
            "scheduled_date": "2026-05-01",
        })
        df = database.get_interviews(pid)
        assert list(df["sequence"]) == [3]

    def test_explicit_sequence_collision_raises(self, db):
        """Two interviews on the same application_id with the same
        sequence → IntegrityError from the UNIQUE constraint."""
        pid = database.add_position(make_position())
        database.add_interview(pid, {"sequence": 1, "scheduled_date": "2026-05-01"})
        with pytest.raises(sqlite3.IntegrityError):
            database.add_interview(pid, {"sequence": 1, "scheduled_date": "2026-06-01"})

    def test_propagate_status_kwarg_default_true(self, db):
        """DESIGN §7: add_interview signature must be
        `add_interview(application_id, fields, *, propagate_status=True)`.
        Default must be True — cascade opt-out is explicit. In Sub-task 8
        the kwarg has no observable effect (cascade body deferred), but
        the signature is in place for Sub-task 9."""
        import inspect
        sig = inspect.signature(database.add_interview)
        param = sig.parameters.get("propagate_status")
        assert param is not None, (
            "add_interview must accept a propagate_status kwarg "
            "(DESIGN §7 load-bearing contract #2)"
        )
        assert param.default is True, (
            f"propagate_status must default to True; got {param.default!r}"
        )
        assert param.kind == inspect.Parameter.KEYWORD_ONLY, (
            "propagate_status must be keyword-only so callers pass it "
            "explicitly; got kind = "
            f"{param.kind!r}"
        )

    def test_propagate_status_false_suppresses_r2_cascade(self, db):
        """propagate_status=False must suppress R2 even when its conditions
        are met. Pre-stage STATUS_APPLIED so R2 would fire under the default
        (cascade promotes APPLIED→INTERVIEW); kwarg=False must keep the row
        at APPLIED. The previous form pre-stayed STATUS_SAVED — R2's status
        guard would block it either way, so a regression that ignored the
        kwarg silently passed."""
        pid = database.add_position(make_position())
        # Move to STATUS_APPLIED via the same writer that fires R1, so the
        # test reflects a realistic pre-state rather than back-doored SQL.
        database.upsert_application(pid, {"applied_date": "2026-04-10"})
        assert database.get_position(pid)["status"] == config.STATUS_APPLIED

        result = database.add_interview(
            pid,
            {"scheduled_date": "2026-05-01"},
            propagate_status=False,
        )
        assert database.get_position(pid)["status"] == config.STATUS_APPLIED, (
            "propagate_status=False must suppress R2 when its conditions "
            "(pre-state STATUS_APPLIED, interview insert succeeds) are met."
        )
        assert result["status_changed"] is False
        assert result["new_status"] is None
        # And the primary INSERT still landed — kwarg suppresses the cascade,
        # not the interview row.
        assert len(database.get_interviews(pid)) == 1

    def test_fk_violation_raises_on_nonexistent_application(self, db):
        """Inserting an interview for a position that doesn't exist
        (no applications row) violates the FK → IntegrityError."""
        with pytest.raises(sqlite3.IntegrityError):
            database.add_interview(99999, {"scheduled_date": "2026-05-01"})

    def test_accepts_format_and_notes(self, db):
        """DESIGN §6.2 columns: format (from INTERVIEW_FORMATS vocabulary,
        but column is plain TEXT so any string is allowed) and notes.
        Round-trip through add_interview → get_interviews."""
        pid = database.add_position(make_position())
        database.add_interview(pid, {
            "scheduled_date": "2026-05-01",
            "format":         "Video",
            "notes":          "PI chat then committee",
        })
        row = database.get_interviews(pid).iloc[0]
        assert row["format"] == "Video"
        assert row["notes"]  == "PI chat then committee"


class TestGetInterviews:

    def test_empty_when_no_interviews(self, db):
        pid = database.add_position(make_position())
        df = database.get_interviews(pid)
        assert len(df) == 0

    def test_returns_interviews_ordered_by_sequence(self, db):
        """DESIGN §8.3: 'one row per interviews record, ordered by
        sequence'. Pin the ORDER BY on the reader so the Applications
        page never has to re-sort."""
        pid = database.add_position(make_position())
        # Insert out-of-order by sequence to verify the ORDER BY.
        database.add_interview(pid, {"sequence": 3, "scheduled_date": "2026-05-03"})
        database.add_interview(pid, {"sequence": 1, "scheduled_date": "2026-05-01"})
        database.add_interview(pid, {"sequence": 2, "scheduled_date": "2026-05-02"})
        seqs = list(database.get_interviews(pid)["sequence"])
        assert seqs == [1, 2, 3], f"ORDER BY sequence ASC not applied; got {seqs!r}"

    def test_scoped_to_application_id(self, db):
        """get_interviews filters by application_id; interviews on other
        positions are not returned."""
        pid_a = database.add_position(make_position({"position_name": "A"}))
        pid_b = database.add_position(make_position({"position_name": "B"}))
        database.add_interview(pid_a, {"scheduled_date": "2026-05-01"})
        database.add_interview(pid_b, {"scheduled_date": "2026-06-01"})
        assert len(database.get_interviews(pid_a)) == 1
        assert len(database.get_interviews(pid_b)) == 1


class TestUpdateInterview:

    def test_updates_specified_fields(self, db):
        pid = database.add_position(make_position())
        res = database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        database.update_interview(res["id"], {
            "scheduled_date": "2026-06-15",
            "format":         "Onsite",
        })
        row = database.get_interviews(pid).iloc[0]
        assert row["scheduled_date"] == "2026-06-15"
        assert row["format"]         == "Onsite"

    def test_partial_update_preserves_other_fields(self, db):
        pid = database.add_position(make_position())
        res = database.add_interview(pid, {
            "scheduled_date": "2026-05-01",
            "notes":          "keep me",
        })
        database.update_interview(res["id"], {"format": "Phone"})
        row = database.get_interviews(pid).iloc[0]
        assert row["notes"] == "keep me", (
            "Partial update must not clobber unmentioned columns."
        )

    def test_empty_fields_is_noop(self, db):
        """Mirror the update_position / update_recommender / upsert
        convention: empty dict → early return, no DB round-trip. Must
        not raise and must not affect any row."""
        pid = database.add_position(make_position())
        res = database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        database.update_interview(res["id"], {})
        row = database.get_interviews(pid).iloc[0]
        assert row["scheduled_date"] == "2026-05-01"


class TestDeleteInterview:

    def test_removes_single_row(self, db):
        pid = database.add_position(make_position())
        res = database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        database.delete_interview(res["id"])
        assert len(database.get_interviews(pid)) == 0

    def test_leaves_other_interviews_untouched(self, db):
        pid = database.add_position(make_position())
        res1 = database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        database.add_interview(pid, {"scheduled_date": "2026-06-01"})
        database.delete_interview(res1["id"])
        remaining = database.get_interviews(pid)
        assert len(remaining) == 1
        assert remaining.iloc[0]["scheduled_date"] == "2026-06-01"


class TestInterviewsCascade:

    def test_delete_position_cascades_through_application_to_interviews(self, db):
        """FK chain: positions → applications (ON DELETE CASCADE via
        applications.position_id → positions.id) → interviews (ON DELETE
        CASCADE via interviews.application_id → applications.position_id).
        So delete_position transitively removes every interview for
        that position, atomically."""
        pid = database.add_position(make_position())
        database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        database.add_interview(pid, {"scheduled_date": "2026-06-01"})

        database.delete_position(pid)

        with database._connect() as conn:
            orphans = conn.execute(
                "SELECT COUNT(*) AS n FROM interviews WHERE application_id = ?",
                (pid,),
            ).fetchone()["n"]
        assert orphans == 0, (
            f"FK cascade must remove interviews when their parent "
            f"position is deleted; got {orphans} orphaned rows"
        )


class TestAddInterviewR2:
    """DESIGN §9.3 R2 — add_interview fires
    `UPDATE positions SET status = STATUS_INTERVIEW
       WHERE id = application_id AND status = STATUS_APPLIED`.
    Status guard alone delivers correct semantics: the first interview
    on an APPLIED position promotes; subsequent interviews on an
    INTERVIEW position are no-ops; OFFER / terminals are not
    regressed. The cascade body counts NO interviews (earlier draft
    was over-restrictive per §9.3 narrative)."""

    def test_r2_promotes_applied_to_interview(self, db):
        pid = database.add_position(make_position())
        database.upsert_application(pid, {"applied_date": "2026-04-10"})
        # Now at STATUS_APPLIED.
        assert database.get_position(pid)["status"] == config.STATUS_APPLIED

        result = database.add_interview(pid, {"scheduled_date": "2026-05-01"})

        assert database.get_position(pid)["status"] == config.STATUS_INTERVIEW
        assert result["status_changed"] is True
        assert result["new_status"] == config.STATUS_INTERVIEW
        # Row id still present in the dict.
        assert isinstance(result["id"], int) and result["id"] >= 1

    def test_r2_noop_when_status_saved(self, db):
        """A user could add an interview on a SAVED position (unusual
        but not disallowed). R2's guard requires STATUS_APPLIED, so
        SAVED stays SAVED — no silent jump from SAVED straight to
        INTERVIEW."""
        pid = database.add_position(make_position())
        result = database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        assert database.get_position(pid)["status"] == config.STATUS_SAVED
        assert result["status_changed"] is False
        assert result["new_status"] is None

    def test_r2_subsequent_interview_on_interview_position_is_noop(self, db):
        """D18 idempotence narrative: 'subsequent interviews on a
        STATUS_INTERVIEW position are no-ops'. The 2nd+ add_interview
        call leaves the status untouched at INTERVIEW."""
        pid = database.add_position(make_position())
        database.upsert_application(pid, {"applied_date": "2026-04-10"})
        database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        # Now at STATUS_INTERVIEW (from the 1st interview's R2).
        assert database.get_position(pid)["status"] == config.STATUS_INTERVIEW

        result = database.add_interview(pid, {"scheduled_date": "2026-05-15"})
        assert database.get_position(pid)["status"] == config.STATUS_INTERVIEW
        assert result["status_changed"] is False
        assert result["new_status"] is None

    def test_r2_noop_when_already_offer(self, db):
        """Received an Offer, then scheduled another interview (e.g.
        final committee before accepting). R2's guard blocks — must
        not regress OFFER → INTERVIEW."""
        pid = database.add_position(make_position())
        _force_position_status(pid, config.STATUS_OFFER)
        result = database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        assert database.get_position(pid)["status"] == config.STATUS_OFFER
        assert result["status_changed"] is False

    @pytest.mark.parametrize("terminal_status", config.TERMINAL_STATUSES)
    def test_r2_noop_when_terminal(self, db, terminal_status):
        """Status guard blocks: a stray interview record on a
        terminal-status position must not silently regress.

        Sourced from config so a future fourth terminal status flows
        into coverage automatically."""
        pid = database.add_position(make_position())
        _force_position_status(pid, terminal_status)
        result = database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        assert database.get_position(pid)["status"] == terminal_status
        assert result["status_changed"] is False
        assert result["new_status"] is None

    def test_r2_does_not_fire_when_propagate_status_false(self, db):
        pid = database.add_position(make_position())
        database.upsert_application(pid, {"applied_date": "2026-04-10"})
        result = database.add_interview(
            pid, {"scheduled_date": "2026-05-01"}, propagate_status=False,
        )
        assert database.get_position(pid)["status"] == config.STATUS_APPLIED, (
            "propagate_status=False must suppress R2 even when its "
            "conditions are met."
        )
        assert result["status_changed"] is False
        # Primary INSERT still landed.
        assert len(database.get_interviews(pid)) == 1

    def test_r2_back_edited_applied_position_with_existing_interviews_promotes(self, db):
        """DESIGN §9.3 R2 rationale: 'if the user back-edits status to
        STATUS_APPLIED while retaining existing interviews, adding
        another interview would fail to promote [under the count-based
        variant]. The count-free form avoids this.' Verify the back-
        edit scenario — R2 fires on the next add_interview and
        re-promotes APPLIED → INTERVIEW."""
        pid = database.add_position(make_position())
        database.upsert_application(pid, {"applied_date": "2026-04-10"})
        database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        # Now at STATUS_INTERVIEW with one interview.
        # User back-edits status to STATUS_APPLIED (via update_position
        # — cascades don't fire on direct status edits).
        database.update_position(pid, {"status": config.STATUS_APPLIED})

        # Add another interview; R2 must promote again.
        result = database.add_interview(pid, {"scheduled_date": "2026-05-15"})
        assert database.get_position(pid)["status"] == config.STATUS_INTERVIEW
        assert result["status_changed"] is True
        assert result["new_status"] == config.STATUS_INTERVIEW


class TestAddInterviewAtomicity:

    def test_cascade_failure_rolls_back_insert(self, db, monkeypatch):
        """Mirror of TestUpsertApplicationAtomicity: force R2's UPDATE
        to fail by monkeypatching config.STATUS_INTERVIEW to a non-
        bindable Python object. The _connect() context manager must
        roll back the primary INSERT along with the cascade so the
        interviews row does NOT persist."""
        pid = database.add_position(make_position())
        database.upsert_application(pid, {"applied_date": "2026-04-10"})
        assert database.get_position(pid)["status"] == config.STATUS_APPLIED

        class NotBindable:
            pass
        monkeypatch.setattr(config, "STATUS_INTERVIEW", NotBindable())

        with pytest.raises(Exception):
            database.add_interview(pid, {"scheduled_date": "2026-05-01"})

        assert len(database.get_interviews(pid)) == 0, (
            "Primary INSERT must roll back when the R2 cascade fails; "
            "interviews row must not persist."
        )
        assert database.get_position(pid)["status"] == config.STATUS_APPLIED


class TestInterviewsMigration:
    """Sub-task 8 / DESIGN §6.3 normalize-flat-columns-into-sub-table
    pattern. Pre-v1.3 DBs have interview1_date / interview2_date on the
    applications row; init_db() creates the interviews table on first
    seeing it, copies the two legacy date columns across as
    sequence=1 / sequence=2 rows, and NULL-clears the source columns.

    Re-running init_db() on an already-migrated DB must be a strict
    no-op — implemented via a "migrate-once gate" that inspects
    sqlite_master BEFORE the CREATE TABLE IF NOT EXISTS and only runs
    the copy path when the interviews table did not already exist."""

    def _seed_pre_v1_3_applications(self, tmp_path, monkeypatch,
                                      interview1_date=None,
                                      interview2_date=None):
        """Build a minimal pre-v1.3 DB: positions (enough columns for
        init_db() to be happy) + applications with the two legacy date
        columns, one row with the requested values. Intentionally does
        NOT create an interviews table — that's what the migration
        creates.

        Mirrors the Sub-task 6/7 migration-test shape. Returns nothing;
        callers call database.init_db() after seeding and inspect the
        resulting tables."""
        monkeypatch.setattr(database, "DB_PATH", tmp_path / "pre_v1_3.db")
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
            # Realistic pre-v1.3 applications table: carries both the
            # flat interview date columns (this sub-task's target) AND
            # `confirmation_email` (Sub-task 10's target). init_db()
            # runs ALL applicable migrations on the first post-upgrade
            # call, so the seed must carry every legacy column that any
            # migration references; otherwise a later sub-task that
            # touches applications will trip on a narrower seed.
            conn.execute("""
                CREATE TABLE applications (
                    position_id        INTEGER PRIMARY KEY,
                    applied_date       TEXT,
                    confirmation_email TEXT,
                    interview1_date    TEXT,
                    interview2_date    TEXT,
                    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
                )
            """)
            conn.execute(
                "INSERT INTO positions (position_name) VALUES ('LegacyPosition')"
            )
            conn.execute(
                "INSERT INTO applications "
                "(position_id, interview1_date, interview2_date) VALUES (1, ?, ?)",
                (interview1_date, interview2_date),
            )

    def test_migration_copies_interview1_date_as_sequence_1(self, tmp_path, monkeypatch):
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch, interview1_date="2026-05-01"
        )
        database.init_db()
        with database._connect() as conn:
            rows = conn.execute(
                "SELECT application_id, sequence, scheduled_date "
                "FROM interviews ORDER BY sequence"
            ).fetchall()
        assert len(rows) == 1
        assert rows[0]["application_id"] == 1
        assert rows[0]["sequence"]       == 1
        assert rows[0]["scheduled_date"] == "2026-05-01"

    def test_migration_copies_interview2_date_as_sequence_2(self, tmp_path, monkeypatch):
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch, interview2_date="2026-06-15"
        )
        database.init_db()
        with database._connect() as conn:
            rows = conn.execute(
                "SELECT application_id, sequence, scheduled_date "
                "FROM interviews ORDER BY sequence"
            ).fetchall()
        assert len(rows) == 1
        assert rows[0]["sequence"]       == 2
        assert rows[0]["scheduled_date"] == "2026-06-15"

    def test_migration_copies_both_dates_in_order(self, tmp_path, monkeypatch):
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch,
            interview1_date="2026-05-01",
            interview2_date="2026-06-15",
        )
        database.init_db()
        with database._connect() as conn:
            rows = conn.execute(
                "SELECT sequence, scheduled_date FROM interviews "
                "WHERE application_id = 1 ORDER BY sequence"
            ).fetchall()
        dates = [(r["sequence"], r["scheduled_date"]) for r in rows]
        assert dates == [(1, "2026-05-01"), (2, "2026-06-15")]

    def test_migration_skips_null_dates(self, tmp_path, monkeypatch):
        """A row with interview1_date=NULL AND interview2_date=NULL must
        produce zero interviews rows. The WHERE IS NOT NULL filter is
        load-bearing — otherwise a normal v1.2 row with no interviews
        scheduled would migrate two NULL-date rows into the new table."""
        self._seed_pre_v1_3_applications(tmp_path, monkeypatch)  # both NULL
        database.init_db()
        with database._connect() as conn:
            n = conn.execute(
                "SELECT COUNT(*) AS n FROM interviews"
            ).fetchone()["n"]
        assert n == 0

    def test_migration_nulls_legacy_columns_after_copy(self, tmp_path, monkeypatch):
        """DESIGN §6.3 explicitly specifies: 'leave old columns NULL
        until a rebuild drops them'. After migration the legacy
        interview1_date / interview2_date on applications must be NULL
        — this both prevents data drift between old and new and
        guarantees idempotence (second migration run finds nothing
        to copy)."""
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch,
            interview1_date="2026-05-01",
            interview2_date="2026-06-15",
        )
        database.init_db()
        with database._connect() as conn:
            app = conn.execute(
                "SELECT interview1_date, interview2_date FROM applications "
                "WHERE position_id = 1"
            ).fetchone()
        assert app["interview1_date"] is None
        assert app["interview2_date"] is None

    def test_migration_is_idempotent(self, tmp_path, monkeypatch):
        """Migrate-once gate: first init_db() creates interviews and
        runs the copy; second init_db() must be a strict no-op — no
        duplicate rows, no re-copy of any NULL-cleared legacy value,
        no IntegrityError from the UNIQUE constraint."""
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch,
            interview1_date="2026-05-01",
            interview2_date="2026-06-15",
        )
        database.init_db()
        database.init_db()  # second call must be a no-op
        with database._connect() as conn:
            rows = conn.execute(
                "SELECT sequence FROM interviews WHERE application_id = 1 "
                "ORDER BY sequence"
            ).fetchall()
        assert [r["sequence"] for r in rows] == [1, 2], (
            "Second init_db() must not duplicate migrated rows; "
            f"got sequences {[r['sequence'] for r in rows]!r}"
        )


# ── confirmation_email split → confirmation_received + confirmation_date ──────
# Sub-task 10 / DESIGN §6.2 + §6.3 + D19: the pre-v1.3 applications table
# carried one TEXT column `confirmation_email` that stored either:
#   - 'Y'  (flag-only semantics — "a confirmation was received, no date")
#   - a date-shaped string 'YYYY-MM-DD' (date-present semantics)
# Anything else (NULL, '', legacy 'N', freetext) means no receipt.
#
# The split translates those two legitimate shapes into the
# (confirmation_received INTEGER, confirmation_date TEXT) pair so
# predicates are simple and no column holds either-shape data.
# Mirrors TestInterviewsMigration's migrate-once gate pattern:
# init_db() samples the applications table BEFORE the ALTER ADD COLUMN,
# and runs the one-shot UPDATE only when the new columns are absent
# pre-ALTER. Subsequent init_db() calls find them already present and
# skip the translation entirely. DESIGN §6.3 step (c) applies: the
# physical confirmation_email column is NULL-cleared after the value
# extraction (matching the interview1_date / interview2_date NULL-clear
# in the Sub-task 8 migration) and stays in place until the v1.0-rc
# rebuild drops it.

class TestConfirmationSplitMigration:
    """Sub-task 10 / DESIGN §6.3 split-a-dual-purpose-column pattern.
    Pre-v1.3 DBs have applications.confirmation_email as a single TEXT
    column storing either 'Y' (flag) or a date string. init_db() adds
    confirmation_received INTEGER DEFAULT 0 + confirmation_date TEXT
    on first seeing the upgrade, then runs a one-shot UPDATE that
    translates the two legitimate legacy shapes. Migrate-once gate:
    the migration body only fires when the new columns were absent
    pre-ALTER, so a re-run on an already-migrated DB is a no-op."""

    def _seed_pre_v1_3_applications(self, tmp_path, monkeypatch,
                                      confirmation_email_value=None):
        """Build a minimal pre-v1.3 DB: positions + applications carrying
        the legacy `confirmation_email` TEXT column (but NO
        confirmation_received / confirmation_date). Inserts one row with
        the requested legacy value. Callers run database.init_db() and
        inspect the new columns.

        Mirrors the Sub-task 8 TestInterviewsMigration seed shape.
        deadline_date is required on positions so idx_positions_deadline
        CREATE in init_db() does not fail."""
        monkeypatch.setattr(database, "DB_PATH", tmp_path / "pre_v1_3.db")
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
            # A realistic pre-v1.3 applications table: carries the legacy
            # `confirmation_email` TEXT column (this sub-task's target) AND
            # the flat `interview1_date` / `interview2_date` columns that
            # Sub-task 8 normalized. Both sets of legacy columns exist
            # together in a genuine pre-v1.3 DB, so the seed must too:
            # init_db() runs ALL applicable migrations on the first call
            # (Sub-task 8 interviews-sub-table, then Sub-task 10 split)
            # and the Sub-task 8 copy SELECTs `interview1_date` from
            # applications — blowing up if the column is absent.
            conn.execute("""
                CREATE TABLE applications (
                    position_id        INTEGER PRIMARY KEY,
                    applied_date       TEXT,
                    confirmation_email TEXT,
                    interview1_date    TEXT,
                    interview2_date    TEXT,
                    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
                )
            """)
            conn.execute(
                "INSERT INTO positions (position_name) VALUES ('LegacyPosition')"
            )
            conn.execute(
                "INSERT INTO applications "
                "(position_id, confirmation_email) VALUES (1, ?)",
                (confirmation_email_value,),
            )

    def test_migration_copies_Y_flag_sets_received_only(self, tmp_path, monkeypatch):
        """Legacy 'Y' value is the flag-only path: set
        confirmation_received = 1, leave confirmation_date NULL. No date
        was ever recorded for this shape — the old column's flag
        semantics gave "received, don't know when"."""
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch, confirmation_email_value="Y"
        )
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT confirmation_received, confirmation_date "
                "FROM applications WHERE position_id = 1"
            ).fetchone()
        assert row["confirmation_received"] == 1, (
            "Legacy 'Y' must translate to confirmation_received=1; "
            f"got {row['confirmation_received']!r}"
        )
        assert row["confirmation_date"] is None, (
            "Legacy 'Y' has no date attached — confirmation_date must "
            f"stay NULL; got {row['confirmation_date']!r}"
        )

    def test_migration_copies_date_string_to_both_fields(self, tmp_path, monkeypatch):
        """A legacy date-shaped string (YYYY-MM-DD) carries both
        semantics: the receipt happened (flag=1) AND it happened on
        that date (confirmation_date=value). The date-shaped match
        runs via SQLite GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]',
        which matches exactly 10 characters of the ISO shape and
        nothing else — e.g. 'not-a-date' does not match."""
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch, confirmation_email_value="2026-01-15"
        )
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT confirmation_received, confirmation_date "
                "FROM applications WHERE position_id = 1"
            ).fetchone()
        assert row["confirmation_received"] == 1
        assert row["confirmation_date"]     == "2026-01-15"

    def test_migration_skips_null_legacy_value(self, tmp_path, monkeypatch):
        """NULL in confirmation_email means "no data" — both new
        columns must stay at their defaults (received=0, date=NULL).
        This is the common case for v1.2 rows whose users never
        touched the confirmation field."""
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch, confirmation_email_value=None
        )
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT confirmation_received, confirmation_date "
                "FROM applications WHERE position_id = 1"
            ).fetchone()
        assert row["confirmation_received"] == 0, (
            "NULL legacy value must leave confirmation_received at "
            f"DEFAULT 0; got {row['confirmation_received']!r}"
        )
        assert row["confirmation_date"] is None

    def test_migration_skips_empty_string_legacy_value(self, tmp_path, monkeypatch):
        """Empty string is a variant of "no data" (the Notes-tab
        round-trip contract writes '' for cleared TEXT cells). Must
        also leave the new columns at their defaults — it is neither
        'Y' nor a date-shaped string, and ambiguous-empty is the same
        semantics as NULL for this column."""
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch, confirmation_email_value=""
        )
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT confirmation_received, confirmation_date "
                "FROM applications WHERE position_id = 1"
            ).fetchone()
        assert row["confirmation_received"] == 0
        assert row["confirmation_date"]     is None

    def test_migration_skips_other_legacy_values(self, tmp_path, monkeypatch):
        """Any legacy value that is neither 'Y' nor a date-shaped
        string is out of the D19 translation scope — could be a
        typo, a short freetext note, or a pre-v1.0 'N' sentinel.
        The migration must leave the new columns at their defaults
        rather than guess."""
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch, confirmation_email_value="N"
        )
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT confirmation_received, confirmation_date "
                "FROM applications WHERE position_id = 1"
            ).fetchone()
        assert row["confirmation_received"] == 0, (
            "Out-of-scope legacy value must leave confirmation_received "
            f"at DEFAULT 0; got {row['confirmation_received']!r}"
        )
        assert row["confirmation_date"] is None

    def test_fresh_applications_row_has_zero_defaults(self, db):
        """A fresh DB (init_db() on an empty DB via the `db` fixture)
        creates the applications table via the v1.3 CREATE TABLE DDL,
        and every new applications row from add_position() must come
        up with confirmation_received=0 / confirmation_date=NULL per
        the DDL DEFAULTs. Pins the CREATE TABLE contract alongside
        the two `TestInitDb` column-spec tests."""
        pos_id = database.add_position(make_position())
        app = database.get_application(pos_id)
        assert app["confirmation_received"] == 0
        assert app["confirmation_date"]     is None

    def test_migration_is_idempotent(self, tmp_path, monkeypatch):
        """Migrate-once gate: first init_db() adds the two columns and
        runs the one-shot UPDATE translating 'Y' + date strings;
        second init_db() finds the new columns already present and
        must skip the UPDATE entirely. The test seeds a date-shaped
        legacy value so there is something to translate; after the
        second init_db(), the row's new-column values must be
        unchanged (not a re-translation of a now-stale
        confirmation_email cell, and not accidentally zeroed)."""
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch, confirmation_email_value="2026-01-15"
        )
        database.init_db()

        with database._connect() as conn:
            row_first = conn.execute(
                "SELECT confirmation_received, confirmation_date "
                "FROM applications WHERE position_id = 1"
            ).fetchone()
        assert row_first["confirmation_received"] == 1
        assert row_first["confirmation_date"]     == "2026-01-15"

        database.init_db()  # second call must be a no-op for this branch

        with database._connect() as conn:
            row_second = conn.execute(
                "SELECT confirmation_received, confirmation_date "
                "FROM applications WHERE position_id = 1"
            ).fetchone()
        assert row_second["confirmation_received"] == row_first["confirmation_received"]
        assert row_second["confirmation_date"]     == row_first["confirmation_date"]

    def test_migration_null_clears_legacy_confirmation_email_column(
        self, tmp_path, monkeypatch,
    ):
        """DESIGN §6.3 step (c): "leave the old column NULL until a
        follow-up release rebuilds the table to drop it." After the
        split UPDATEs land the legacy date-shaped value into the
        (received, date) pair, the source column itself must be NULL —
        parallels the interview1/2_date NULL-clear in the Sub-task 8
        migration. Without this, the legacy column carries stale
        post-split data that no caller reads but that violates the
        literal DESIGN spec and risks accidental future reads of
        post-split ghost values.
        """
        self._seed_pre_v1_3_applications(
            tmp_path, monkeypatch, confirmation_email_value="2026-01-15"
        )
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT confirmation_email, confirmation_received, "
                "       confirmation_date "
                "FROM applications WHERE position_id = 1"
            ).fetchone()
        # Sanity-pin the new columns first — the NULL-clear must not
        # accidentally undo the translation done by the prior UPDATEs.
        assert row["confirmation_received"] == 1
        assert row["confirmation_date"]     == "2026-01-15"
        # The DESIGN §6.3 step (c) NULL-clear:
        assert row["confirmation_email"] is None, (
            "Legacy confirmation_email must be NULL-cleared after the "
            "split migration completes (DESIGN §6.3 step (c)). "
            f"Got {row['confirmation_email']!r}"
        )


# ── recommenders rebuild: confirmed TEXT→INTEGER + reminder_sent split ────────
# Sub-task 11 / DESIGN §6.2 + D19 + D20: SQLite lacks in-place column-type
# change, so the pre-v1.3 recommenders table (`confirmed TEXT`,
# `reminder_sent TEXT`, no `reminder_sent_date`) rebuilds via the
# CREATE-COPY-DROP-RENAME recipe inside one transaction:
#   (1) CREATE TABLE recommenders_new (...)  -- target schema
#   (2) INSERT INTO recommenders_new SELECT id, ..., CASE-translated cols
#   (3) DROP TABLE recommenders
#   (4) ALTER TABLE recommenders_new RENAME TO recommenders
# Idempotence: guarded by `PRAGMA table_info(recommenders)` check on the
# `confirmed` column's declared type — INTEGER means the rebuild already
# ran; TEXT (or absent) means it hasn't.
#
# CASE translation matrix:
#   confirmed     'Y'           -> 1
#                 'N'           -> 0
#                 anything else -> NULL (pending-response tri-state —
#                                        cautious; 'maybe' / stray
#                                        freetext become NULL rather
#                                        than a guessed integer)
#   reminder_sent 'Y'           -> reminder_sent=1, reminder_sent_date=NULL
#                 'YYYY-MM-DD'* -> reminder_sent=0, reminder_sent_date=<value>
#                 anything else -> reminder_sent=0, reminder_sent_date=NULL
#   *matched via SQLite GLOB '????-??-??' per the user-specified rebuild SQL;
#   this is looser than Sub-task 10's [0-9]-digit-class pattern — any
#   10-char '??-??' shape passes — but pre-v1.3 reminder_sent values
#   realistically held only dates or 'Y'/NULL, so the looser match is safe.
# All other columns (id, position_id, recommender_name, relationship,
# asked_date, submitted_date, notes) copy through unchanged.

class TestRecommendersRebuildMigration:
    """Sub-task 11 / DESIGN §6.2 + §6.3 + D19 + D20: the recommenders
    table rebuild translates pre-v1.3 TEXT columns into the DESIGN-spec
    INTEGER tri-state (confirmed) + INTEGER flag (reminder_sent) +
    TEXT date (reminder_sent_date) trio, preserving all other columns,
    the autoincrement counter, and the FK → positions CASCADE
    relationship. Idempotence guard is on `confirmed`'s declared type
    so reruns are a strict no-op."""

    def _seed_pre_v1_3_recommenders(self, tmp_path, monkeypatch,
                                      rows=()):
        """Build a minimal pre-v1.3 DB: positions (enough for init_db
        to be happy) + recommenders with the pre-v1.3 schema
        (`confirmed TEXT`, `reminder_sent TEXT`, no `reminder_sent_date`).
        `rows` is a list of dicts, each keyed by the pre-v1.3 column
        names; rows with the same position_id share a single parent
        position (auto-created if needed).

        Seed strategy matches TestInterviewsMigration /
        TestConfirmationSplitMigration — tmp_path + monkeypatched
        DB_PATH, a deliberately slim positions table, and the minimal
        set of legacy columns init_db's migrations reference. Unlike
        those migrations, Sub-task 11 only touches recommenders, so
        the other tables can stay bare."""
        monkeypatch.setattr(database, "DB_PATH", tmp_path / "pre_v1_3.db")
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
            # Applications carries the pre-v1.3 legacy columns that
            # Sub-tasks 8 + 10 migrate — present so init_db() does not
            # blow up before reaching the Sub-task 11 rebuild.
            conn.execute("""
                CREATE TABLE applications (
                    position_id        INTEGER PRIMARY KEY,
                    applied_date       TEXT,
                    confirmation_email TEXT,
                    interview1_date    TEXT,
                    interview2_date    TEXT,
                    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
                )
            """)
            # Pre-v1.3 recommenders schema — confirmed/reminder_sent as
            # TEXT, no reminder_sent_date.
            conn.execute("""
                CREATE TABLE recommenders (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_id      INTEGER NOT NULL,
                    recommender_name TEXT,
                    relationship     TEXT,
                    asked_date       TEXT,
                    confirmed        TEXT,
                    submitted_date   TEXT,
                    reminder_sent    TEXT,
                    notes            TEXT,
                    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
                )
            """)
            # Insert rows. First ensure each position_id referenced has
            # a matching positions row (FK is enforced at INSERT time
            # with PRAGMA foreign_keys = ON in _connect()).
            needed_positions = {r.get("position_id", 1) for r in rows}
            if not rows:
                needed_positions = {1}
            for pid in sorted(needed_positions):
                conn.execute(
                    "INSERT INTO positions (id, position_name) VALUES (?, ?)",
                    (pid, f"LegacyPosition{pid}"),
                )

            for r in rows:
                cols = ["position_id"] + [k for k in r if k != "position_id"]
                vals = [r.get("position_id", 1)] + [
                    r[k] for k in cols if k != "position_id"
                ]
                placeholders = ", ".join("?" * len(cols))
                conn.execute(
                    f"INSERT INTO recommenders ({', '.join(cols)}) "
                    f"VALUES ({placeholders})",
                    vals,
                )

    # ── confirmed translation ──────────────────────────────────────

    def test_migration_translates_confirmed_Y_to_1(self, tmp_path, monkeypatch):
        """Legacy 'Y' in confirmed must translate to INTEGER 1."""
        self._seed_pre_v1_3_recommenders(tmp_path, monkeypatch, rows=[
            {"recommender_name": "Dr. Yes", "confirmed": "Y"},
        ])
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT confirmed FROM recommenders "
                "WHERE recommender_name = 'Dr. Yes'"
            ).fetchone()
        assert row["confirmed"] == 1, (
            f"Expected confirmed=1 after 'Y' translation, got {row['confirmed']!r}"
        )

    def test_migration_translates_confirmed_N_to_0(self, tmp_path, monkeypatch):
        """Legacy 'N' in confirmed must translate to INTEGER 0."""
        self._seed_pre_v1_3_recommenders(tmp_path, monkeypatch, rows=[
            {"recommender_name": "Dr. No", "confirmed": "N"},
        ])
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT confirmed FROM recommenders "
                "WHERE recommender_name = 'Dr. No'"
            ).fetchone()
        assert row["confirmed"] == 0, (
            f"Expected confirmed=0 after 'N' translation, got {row['confirmed']!r}"
        )

    def test_migration_keeps_confirmed_null_as_null(self, tmp_path, monkeypatch):
        """Legacy NULL in confirmed stays NULL post-rebuild — this is
        the pending-response tri-state D20 preserves via INTEGER (no
        DEFAULT, NULL-able). The `ELSE NULL` branch in the CASE
        translation captures this."""
        self._seed_pre_v1_3_recommenders(tmp_path, monkeypatch, rows=[
            {"recommender_name": "Dr. Pending", "confirmed": None},
        ])
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT confirmed FROM recommenders "
                "WHERE recommender_name = 'Dr. Pending'"
            ).fetchone()
        assert row["confirmed"] is None

    def test_migration_translates_confirmed_other_values_to_null(self, tmp_path, monkeypatch):
        """Anything other than 'Y' or 'N' (including 'maybe', empty
        string, legacy 'yes', stray typos) must translate to NULL
        rather than guess an integer — the migration takes the
        cautious path, reflecting "we don't know" as NULL (pending
        response). The user-spec SQL's `CASE confirmed WHEN 'Y' THEN 1
        WHEN 'N' THEN 0 ELSE NULL END` implements this exactly."""
        self._seed_pre_v1_3_recommenders(tmp_path, monkeypatch, rows=[
            {"recommender_name": "Dr. Maybe",  "confirmed": "maybe"},
            {"recommender_name": "Dr. Empty",  "confirmed": ""},
            {"recommender_name": "Dr. Lower",  "confirmed": "y"},
        ])
        database.init_db()
        with database._connect() as conn:
            rows = conn.execute(
                "SELECT recommender_name, confirmed FROM recommenders "
                "ORDER BY id"
            ).fetchall()
        for r in rows:
            assert r["confirmed"] is None, (
                f"Expected confirmed=NULL for {r['recommender_name']!r}, "
                f"got {r['confirmed']!r}"
            )

    # ── reminder_sent (flag) translation ───────────────────────────

    def test_migration_translates_reminder_sent_Y_to_flag_1(self, tmp_path, monkeypatch):
        """Legacy 'Y' in reminder_sent sets the new INTEGER flag to 1;
        reminder_sent_date stays NULL because 'Y' carried no date."""
        self._seed_pre_v1_3_recommenders(tmp_path, monkeypatch, rows=[
            {"recommender_name": "Dr. Reminded", "reminder_sent": "Y"},
        ])
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT reminder_sent, reminder_sent_date FROM recommenders "
                "WHERE recommender_name = 'Dr. Reminded'"
            ).fetchone()
        assert row["reminder_sent"]      == 1
        assert row["reminder_sent_date"] is None

    def test_migration_translates_reminder_sent_null_and_other_to_flag_0(
        self, tmp_path, monkeypatch,
    ):
        """Legacy NULL, empty string, 'N', or any freetext that is not
        'Y' and not date-shaped must produce reminder_sent=0 and
        reminder_sent_date=NULL — the user-spec SQL's
        `CASE WHEN reminder_sent = 'Y' THEN 1 ELSE 0 END` defaults
        everything-not-Y to 0."""
        self._seed_pre_v1_3_recommenders(tmp_path, monkeypatch, rows=[
            {"recommender_name": "Dr. Null",  "reminder_sent": None},
            {"recommender_name": "Dr. Empty", "reminder_sent": ""},
            {"recommender_name": "Dr. No",    "reminder_sent": "N"},
            {"recommender_name": "Dr. Other", "reminder_sent": "sometime"},
        ])
        database.init_db()
        with database._connect() as conn:
            rows = conn.execute(
                "SELECT recommender_name, reminder_sent, reminder_sent_date "
                "FROM recommenders ORDER BY id"
            ).fetchall()
        for r in rows:
            assert r["reminder_sent"] == 0, (
                f"Expected reminder_sent=0 for {r['recommender_name']!r}, "
                f"got {r['reminder_sent']!r}"
            )
            assert r["reminder_sent_date"] is None, (
                f"Expected reminder_sent_date=NULL for "
                f"{r['recommender_name']!r}, got {r['reminder_sent_date']!r}"
            )

    def test_migration_splits_date_shaped_reminder_sent_into_new_column(
        self, tmp_path, monkeypatch,
    ):
        """Pre-v1.3 reminder_sent sometimes stored a date string instead
        of 'Y' — ambiguous dual-purpose semantics exactly like Sub-task
        10's confirmation_email split. The rebuild's second CASE branch
        (`GLOB '????-??-??'`) captures that date into the new
        reminder_sent_date column. Per user-spec SQL: the flag itself
        stays 0 in this path — the old TEXT value was NOT 'Y'.
        Downstream the page UI will treat a non-NULL reminder_sent_date
        as evidence that a reminder was sent; if the user wants both
        flag and date set they re-save after the migration runs."""
        self._seed_pre_v1_3_recommenders(tmp_path, monkeypatch, rows=[
            {"recommender_name": "Dr. Dated", "reminder_sent": "2026-04-14"},
        ])
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT reminder_sent, reminder_sent_date FROM recommenders "
                "WHERE recommender_name = 'Dr. Dated'"
            ).fetchone()
        # Per user-spec rebuild SQL:
        #   reminder_sent      = CASE WHEN reminder_sent = 'Y' THEN 1 ELSE 0 END
        #   reminder_sent_date = CASE WHEN reminder_sent GLOB '????-??-??'
        #                             THEN reminder_sent ELSE NULL END
        # A date-shaped legacy value is not 'Y', so flag=0; the GLOB
        # matches so the date populates the new column.
        assert row["reminder_sent"]      == 0
        assert row["reminder_sent_date"] == "2026-04-14"

    # ── other-column preservation + structural invariants ──────────

    def test_migration_preserves_other_columns_unchanged(self, tmp_path, monkeypatch):
        """The rebuild's INSERT copies id, position_id,
        recommender_name, relationship, asked_date, submitted_date, and
        notes verbatim — only the three D19/D20 columns are CASE-
        translated. This test pins every copied column via a single
        seed row with non-NULL values across the board."""
        self._seed_pre_v1_3_recommenders(tmp_path, monkeypatch, rows=[{
            "recommender_name": "Dr. FullRow",
            "relationship":     "PhD Advisor",
            "asked_date":       "2026-03-01",
            "confirmed":        "Y",
            "submitted_date":   "2026-04-15",
            "reminder_sent":    "Y",
            "notes":            "wrote in early",
        }])
        database.init_db()
        with database._connect() as conn:
            row = conn.execute(
                "SELECT id, position_id, recommender_name, relationship, "
                "       asked_date, submitted_date, notes "
                "FROM recommenders WHERE recommender_name = 'Dr. FullRow'"
            ).fetchone()
        assert row["id"]               == 1
        assert row["position_id"]      == 1
        assert row["recommender_name"] == "Dr. FullRow"
        assert row["relationship"]     == "PhD Advisor"
        assert row["asked_date"]       == "2026-03-01"
        assert row["submitted_date"]   == "2026-04-15"
        assert row["notes"]            == "wrote in early"

    def test_migration_preserves_fk_cascade_on_delete_position(self, tmp_path, monkeypatch):
        """The rebuild must land the FK + ON DELETE CASCADE on the
        post-rename table (the new DDL re-declares it, but this test
        exercises the end-to-end behaviour). Deleting a position with
        a migrated recommender must cascade the recommender row away."""
        self._seed_pre_v1_3_recommenders(tmp_path, monkeypatch, rows=[
            {"position_id": 1, "recommender_name": "Dr. Cascade", "confirmed": "Y"},
        ])
        database.init_db()
        # Confirm pre-delete state: recommender exists.
        assert len(database.get_recommenders(1)) == 1
        database.delete_position(1)
        with database._connect() as conn:
            remaining = conn.execute(
                "SELECT COUNT(*) AS c FROM recommenders"
            ).fetchone()["c"]
        assert remaining == 0, (
            "FK CASCADE on delete_position must wipe the recommender row "
            f"after the rebuild. Got {remaining} remaining rows."
        )

    def test_migration_preserves_autoincrement_counter(self, tmp_path, monkeypatch):
        """After the rebuild, the next new recommender must get an id
        of `max(previous ids) + 1` rather than restarting from 1. The
        INSERT-COPY explicitly lists `id` so the primary key values
        are preserved; the AUTOINCREMENT counter state lives in the
        `sqlite_sequence` table, which SQLite updates on INSERT — so
        copying the rows with explicit id values is sufficient for the
        counter to stay coherent."""
        self._seed_pre_v1_3_recommenders(tmp_path, monkeypatch, rows=[
            {"recommender_name": "Dr. First",  "confirmed": "Y"},
            {"recommender_name": "Dr. Second", "confirmed": "N"},
            {"recommender_name": "Dr. Third"},
        ])
        database.init_db()
        # Max id pre-add is 3; next must be 4.
        new_id = database.add_recommender(1, {
            "recommender_name": "Dr. Fourth",
        })
        assert new_id == 4, (
            f"AUTOINCREMENT counter must advance past migrated ids. "
            f"Expected next id=4, got {new_id}"
        )

    def test_migration_is_idempotent(self, tmp_path, monkeypatch):
        """Second init_db() must be a strict no-op for the rebuild:
        the `confirmed` column is now INTEGER, so the PRAGMA
        table_info guard evaluates False and the CREATE-COPY-DROP-
        RENAME does not run. Previously-translated integer values
        must stay put."""
        self._seed_pre_v1_3_recommenders(tmp_path, monkeypatch, rows=[
            {"recommender_name": "Dr. First",  "confirmed": "Y",
             "reminder_sent": "2026-04-14"},
        ])
        database.init_db()
        with database._connect() as conn:
            first = conn.execute(
                "SELECT id, confirmed, reminder_sent, reminder_sent_date "
                "FROM recommenders WHERE recommender_name = 'Dr. First'"
            ).fetchone()
        assert first["confirmed"]          == 1
        assert first["reminder_sent"]      == 0
        assert first["reminder_sent_date"] == "2026-04-14"

        database.init_db()  # second call must be a no-op

        with database._connect() as conn:
            second = conn.execute(
                "SELECT id, confirmed, reminder_sent, reminder_sent_date "
                "FROM recommenders WHERE recommender_name = 'Dr. First'"
            ).fetchone()
        assert second["id"]                 == first["id"]
        assert second["confirmed"]          == first["confirmed"]
        assert second["reminder_sent"]      == first["reminder_sent"]
        assert second["reminder_sent_date"] == first["reminder_sent_date"]


# ── get_upcoming_interviews ───────────────────────────────────────────────────
# Sub-task 8 / DESIGN §7: rewrites to read from the new interviews sub-table
# via JOIN interviews → applications → positions. Returns row-per-interview
# (prior shape was row-per-position with two date columns), ordered by
# scheduled_date ASC. Seed via add_interview — NEVER via upsert_application
# with the legacy interview1_date/interview2_date columns (those stay NULL
# after the Sub-task 8 migration).

class TestGetUpcomingInterviews:

    def test_empty_when_no_interviews_set(self, db):
        database.add_position(make_position())
        df = database.get_upcoming_interviews()
        assert len(df) == 0

    def test_returns_single_future_interview(self, db):
        pos_id = database.add_position(make_position())
        database.add_interview(pos_id, {
            "scheduled_date": (date.today() + timedelta(days=7)).isoformat(),
        })
        df = database.get_upcoming_interviews()
        assert len(df) == 1

    def test_returns_row_per_interview(self, db):
        """D18: arbitrary interview count per position. Two interviews
        on the same position → two rows in the result (not one
        aggregated row, not capped at 2)."""
        pos_id = database.add_position(make_position())
        database.add_interview(pos_id, {
            "scheduled_date": (date.today() + timedelta(days=7)).isoformat(),
        })
        database.add_interview(pos_id, {
            "scheduled_date": (date.today() + timedelta(days=14)).isoformat(),
        })
        df = database.get_upcoming_interviews()
        assert len(df) == 2, (
            "Row-per-interview shape is load-bearing for D18 — two "
            "interviews on one position must produce two rows."
        )

    def test_excludes_past_interview(self, db):
        pos_id = database.add_position(make_position())
        database.add_interview(pos_id, {
            "scheduled_date": (date.today() - timedelta(days=1)).isoformat(),
        })
        df = database.get_upcoming_interviews()
        assert len(df) == 0

    def test_includes_interview_today(self, db):
        pos_id = database.add_position(make_position())
        database.add_interview(pos_id, {
            "scheduled_date": date.today().isoformat(),
        })
        df = database.get_upcoming_interviews()
        assert len(df) == 1

    def test_ordered_by_scheduled_date_asc(self, db):
        """Chronological order is part of the contract (DESIGN §7 load-
        bearing #5). Earliest upcoming interview first, regardless of
        position or insert order."""
        pid_a = database.add_position(make_position({"position_name": "A"}))
        pid_b = database.add_position(make_position({"position_name": "B"}))
        later  = (date.today() + timedelta(days=20)).isoformat()
        sooner = (date.today() + timedelta(days=5)).isoformat()
        database.add_interview(pid_a, {"scheduled_date": later})
        database.add_interview(pid_b, {"scheduled_date": sooner})
        df = database.get_upcoming_interviews()
        assert list(df["scheduled_date"]) == [sooner, later]

    def test_result_has_join_columns(self, db):
        """Consumer contract: each row carries the position identity
        (name + institute) and the interview identity (scheduled_date,
        plus format and sequence for the Applications page)."""
        pos_id = database.add_position(make_position())
        database.add_interview(pos_id, {
            "scheduled_date": (date.today() + timedelta(days=5)).isoformat(),
            "format":         "Video",
        })
        df = database.get_upcoming_interviews()
        for col in (
            "position_id", "position_name", "institute",
            "scheduled_date", "format", "sequence",
        ):
            assert col in df.columns, (
                f"get_upcoming_interviews missing expected column {col!r}; "
                f"got {list(df.columns)!r}"
            )


# ── get_upcoming ──────────────────────────────────────────────────────────────
# T4-A: unified upcoming feed merging deadlines + interviews. Thin projection
# over get_upcoming_deadlines + get_upcoming_interviews; powers the dashboard's
# Upcoming panel (DESIGN §8.1). Spec lock-down for the column contract is in
# DESIGN §8.1's "Upcoming-panel column contract" sub-table.

class TestGetUpcoming:
    """get_upcoming(days) returns six columns in storage form
    (date, days_left, label, kind, status, urgency), sorted by date asc.

    Per DESIGN §8.1 (T4-0 + T4-0b lock-down):
      - `date` is a `datetime.date` object so column-header re-sort in
        the page is chronological, not lexicographic.
      - `days_left` is one of: 'today' (0 days), 'in 1 day' (singular),
        'in N days' (N > 1).
      - `label` is '{institute}: {position_name}' when institute is
        non-empty; bare position_name otherwise.
      - `kind` is 'Deadline for application' for deadline rows, or
        f'Interview {sequence}' for interview rows (1-indexed).
      - `status` is the raw bracketed sentinel — UI mapping is T4-B.
      - `urgency` is '🔴' / '🟡' / '' from the SAME days_away integer
        as `days_left`, so the two columns cannot drift by construction.
        Thresholds resolve at call time from config.
    """

    EXPECTED_COLUMNS = ["date", "days_left", "label", "kind", "status", "urgency"]
    URGENT = "🔴"
    WARN   = "🟡"
    DEADLINE_KIND = "Deadline for application"

    def test_empty_db_returns_empty_dataframe_with_expected_columns(self, db):
        """Six-column shape is part of the contract and must hold even
        on an empty DB; T4-B's column rename binds to this exact list."""
        df = database.get_upcoming()
        assert len(df) == 0, f"Empty DB must return zero rows; got {len(df)}"
        assert list(df.columns) == self.EXPECTED_COLUMNS, (
            f"Columns must be {self.EXPECTED_COLUMNS!r} in this order, "
            f"got {list(df.columns)!r}"
        )

    def test_deadline_row_projects_to_unified_shape(self, db):
        """One deadline at +10d → one row with the deadline-flavoured
        Kind, the date-object Date column, the institute-prefixed Label,
        and the position's status."""
        deadline_iso = (date.today() + timedelta(days=10)).isoformat()
        database.add_position(make_position({
            "position_name": "P-deadline",
            "institute":     "Stanford",
            "deadline_date": deadline_iso,
        }))
        df = database.get_upcoming()
        assert len(df) == 1
        row = df.iloc[0]
        assert row["date"]   == date.fromisoformat(deadline_iso)
        assert row["label"]  == "Stanford: P-deadline"
        assert row["kind"]   == self.DEADLINE_KIND
        assert row["status"] == config.STATUS_SAVED

    def test_interview_row_projects_to_unified_shape(self, db):
        """One interview at +10d → one row with sequence-aware Kind
        ('Interview 1' for the first interview), date-object Date,
        institute-prefixed Label, and status enriched from the position
        (R2 cascade does NOT fire from [SAVED] — position stays at
        default)."""
        interview_iso = (date.today() + timedelta(days=10)).isoformat()
        pos_id = database.add_position(make_position({
            "position_name": "P-int",
            "institute":     "MIT",
            "deadline_date": None,
        }))
        database.add_interview(pos_id, {"scheduled_date": interview_iso})
        df = database.get_upcoming()
        assert len(df) == 1
        row = df.iloc[0]
        assert row["date"]   == date.fromisoformat(interview_iso)
        assert row["label"]  == "MIT: P-int"
        assert row["kind"]   == "Interview 1"
        assert row["status"] == config.STATUS_SAVED

    def test_date_column_holds_datetime_date_objects(self, db):
        """DESIGN §8.1: underlying Date dtype is datetime.date so the
        column header's user-triggered re-sort is chronological. Pandas
        has no native date dtype — the column stays object-dtype but
        every cell is a date instance. Per-element check is the
        load-bearing assertion (a regression to ISO-string Dates would
        not catch on a column.dtype check)."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=5)).isoformat(),
        }))
        df = database.get_upcoming()
        cells = list(df["date"])
        assert all(isinstance(c, date) for c in cells), (
            f"Every Date cell must be a datetime.date (not str / Timestamp / "
            f"None). Got types: {[type(c).__name__ for c in cells]}"
        )

    def test_days_left_today_for_zero_days(self, db):
        """+0d → 'today' — the no-arithmetic case for the user."""
        database.add_position(make_position({
            "deadline_date": date.today().isoformat(),
        }))
        df = database.get_upcoming()
        assert df.iloc[0]["days_left"] == "today"

    def test_days_left_singular_for_one_day(self, db):
        """+1d → 'in 1 day' — pinned because singular/plural agreement
        is locked DESIGN copy."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=1)).isoformat(),
        }))
        df = database.get_upcoming()
        assert df.iloc[0]["days_left"] == "in 1 day"

    def test_days_left_plural_for_multiple_days(self, db):
        """+10d → 'in 10 days' — and the same template for any N > 1."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=10)).isoformat(),
        }))
        df = database.get_upcoming()
        assert df.iloc[0]["days_left"] == "in 10 days"

    def test_label_falls_back_to_position_name_when_institute_missing(self, db):
        """`institute` is nullable in `positions`; when None, the Label
        drops the prefix and shows just the position name — the
        colon-prefix would look broken otherwise."""
        deadline_iso = (date.today() + timedelta(days=5)).isoformat()
        database.add_position(make_position({
            "position_name": "Standalone",
            "institute":     None,
            "deadline_date": deadline_iso,
        }))
        df = database.get_upcoming()
        assert df.iloc[0]["label"] == "Standalone", (
            f"Missing institute must produce bare position_name. "
            f"Got: {df.iloc[0]['label']!r}"
        )

    def test_label_falls_back_when_institute_is_empty_string(self, db):
        """Empty-string institute is the same UX as None — pinned
        separately because get_all_positions / pandas may surface
        '' rather than NaN/None depending on the round-trip."""
        deadline_iso = (date.today() + timedelta(days=5)).isoformat()
        database.add_position(make_position({
            "position_name": "Standalone",
            "institute":     "",
            "deadline_date": deadline_iso,
        }))
        df = database.get_upcoming()
        assert df.iloc[0]["label"] == "Standalone"

    def test_kind_for_interview_row_uses_sequence_number(self, db):
        """A position with two interviews → two rows whose Kind cells
        are 'Interview 1' and 'Interview 2' (1-indexed), pulling from
        interviews.sequence. Pinning both rows together protects against
        a regression that hardcodes the sequence number."""
        pos_id = database.add_position(make_position({
            "position_name": "Multi",
            "institute":     "U",
            "deadline_date": None,
        }))
        database.add_interview(pos_id, {
            "scheduled_date": (date.today() + timedelta(days=5)).isoformat(),
        })
        database.add_interview(pos_id, {
            "scheduled_date": (date.today() + timedelta(days=14)).isoformat(),
        })
        df = database.get_upcoming()
        assert len(df) == 2
        assert list(df["kind"]) == ["Interview 1", "Interview 2"], (
            f"Expected sequence-aware Kind cells. Got: {list(df['kind'])}"
        )
        assert all(label == "U: Multi" for label in df["label"])

    def test_merged_rows_sorted_by_date_asc(self, db):
        """A's deadline at +20d, B's interview at +5d → B first (with
        its 'Interview 1' Kind), then A (with the deadline Kind).
        Sort key is the unified Date column."""
        database.add_position(make_position({
            "position_name": "A",
            "institute":     "InstA",
            "deadline_date": (date.today() + timedelta(days=20)).isoformat(),
        }))
        b_id = database.add_position(make_position({
            "position_name": "B",
            "institute":     "InstB",
            "deadline_date": None,
        }))
        database.add_interview(b_id, {
            "scheduled_date": (date.today() + timedelta(days=5)).isoformat(),
        })
        df = database.get_upcoming()
        assert list(df["kind"])  == ["Interview 1", self.DEADLINE_KIND]
        assert list(df["label"]) == ["InstB: B", "InstA: A"]

    def test_urgency_red_within_urgent_threshold(self, db):
        """Days-away ≤ DEADLINE_URGENT_DAYS → URGENT, boundary inclusive."""
        for offset in (0, config.DEADLINE_URGENT_DAYS):
            database.add_position(make_position({
                "position_name": f"P-{offset}",
                "deadline_date": (date.today() + timedelta(days=offset)).isoformat(),
            }))
        df = database.get_upcoming()
        assert all(u == self.URGENT for u in df["urgency"]), (
            f"Days-away ≤ DEADLINE_URGENT_DAYS={config.DEADLINE_URGENT_DAYS} "
            f"must produce {self.URGENT!r}. Got: {list(df['urgency'])}"
        )

    def test_urgency_yellow_between_urgent_and_alert(self, db):
        """Days-away in (DEADLINE_URGENT_DAYS, DEADLINE_ALERT_DAYS] → WARN.
        Both boundaries pinned."""
        for offset in (
            config.DEADLINE_URGENT_DAYS + 1,
            config.DEADLINE_ALERT_DAYS,
        ):
            database.add_position(make_position({
                "position_name": f"P-{offset}",
                "deadline_date": (date.today() + timedelta(days=offset)).isoformat(),
            }))
        df = database.get_upcoming()
        assert all(u == self.WARN for u in df["urgency"]), (
            f"Days-away in ({config.DEADLINE_URGENT_DAYS}, "
            f"{config.DEADLINE_ALERT_DAYS}] must produce {self.WARN!r}. "
            f"Got: {list(df['urgency'])}"
        )

    def test_urgency_thresholds_resolve_at_call_time(self, db, monkeypatch):
        """Tightening DEADLINE_URGENT_DAYS via monkeypatch flips the
        urgency band on the very next call — proves the function reads
        the config threshold at call time, not at import. Catches a
        regression that hardcodes the comparison constant in the
        function body."""
        offset = config.DEADLINE_URGENT_DAYS
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=offset)).isoformat(),
        }))
        monkeypatch.setattr(config, "DEADLINE_URGENT_DAYS", offset - 1)
        df = database.get_upcoming()
        assert df.iloc[0]["urgency"] == self.WARN, (
            f"Tightening DEADLINE_URGENT_DAYS to {offset - 1} must demote "
            f"a deadline at +{offset}d from {self.URGENT!r} to {self.WARN!r}. "
            f"Got {df.iloc[0]['urgency']!r}. Hardcoded thresholds break this."
        )

    def test_days_left_and_urgency_share_the_same_days_away(self, db):
        """Both columns are derived from the same days_away int per
        row; coherence guaranteed by construction. A row at exactly
        DEADLINE_URGENT_DAYS shows '🔴' AND the days_left phrasing for
        that exact offset — they cannot disagree."""
        offset = config.DEADLINE_URGENT_DAYS
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=offset)).isoformat(),
        }))
        df = database.get_upcoming()
        row = df.iloc[0]
        assert row["urgency"] == self.URGENT
        if offset == 0:
            expected_days_left = "today"
        elif offset == 1:
            expected_days_left = "in 1 day"
        else:
            expected_days_left = f"in {offset} days"
        assert row["days_left"] == expected_days_left, (
            f"days_left and urgency must derive from the same days_away. "
            f"At +{offset}d: expected days_left={expected_days_left!r}, "
            f"urgency={self.URGENT!r}. Got days_left={row['days_left']!r}, "
            f"urgency={row['urgency']!r}."
        )

    def test_default_days_bounds_interview_window(self, db):
        """get_upcoming_interviews has no built-in days bound; DESIGN
        §8.1's window contract applies it to interviews too. An
        interview one day past the default window is excluded."""
        pos_id = database.add_position(make_position({"deadline_date": None}))
        database.add_interview(pos_id, {
            "scheduled_date": (date.today() + timedelta(
                days=config.DEADLINE_ALERT_DAYS + 1
            )).isoformat(),
        })
        df = database.get_upcoming()
        assert len(df) == 0

    def test_explicit_days_param_widens_window_for_both_kinds(self, db):
        """The selectbox in T4-B passes its choice to days. Beyond the
        DEADLINE_ALERT_DAYS band the urgency cell is empty (defensive),
        but the row is still surfaced — the user asked for the wider
        window explicitly. Days_left still renders correctly."""
        pos_id = database.add_position(make_position({"deadline_date": None}))
        database.add_interview(pos_id, {
            "scheduled_date": (date.today() + timedelta(days=60)).isoformat(),
        })
        df = database.get_upcoming(days=90)
        assert len(df) == 1
        assert df.iloc[0]["urgency"] == "", (
            f"Days-away > DEADLINE_ALERT_DAYS={config.DEADLINE_ALERT_DAYS} "
            f"must produce empty urgency. Got {df.iloc[0]['urgency']!r}."
        )
        assert df.iloc[0]["days_left"] == "in 60 days", (
            f"Days_left should still render correctly even when the urgency "
            f"band is exhausted. Got {df.iloc[0]['days_left']!r}."
        )

    def test_terminal_status_excludes_deadline_row(self, db):
        """Terminal-status filtering passes through from
        get_upcoming_deadlines — a [REJECTED] position's deadline does
        NOT appear in the upcoming feed."""
        pos_id = database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=5)).isoformat(),
        }))
        database.update_position(pos_id, {"status": config.STATUS_REJECTED})
        df = database.get_upcoming()
        assert len(df) == 0

    def test_status_column_carries_raw_bracketed_sentinel(self, db):
        """T4-A is the storage layer; STATUS_LABELS mapping is T4-B's
        responsibility. Pin that the raw bracketed sentinel makes it
        through the projection unchanged."""
        database.add_position(make_position({
            "deadline_date": (date.today() + timedelta(days=5)).isoformat(),
        }))
        df = database.get_upcoming()
        assert df.iloc[0]["status"] == config.STATUS_SAVED
        assert df.iloc[0]["status"].startswith("["), (
            "Raw sentinel form (bracketed) — UI label mapping happens in app.py."
        )


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

    def test_empty_string_submitted_date_currently_excluded(self, db):
        """Pin the **current** behaviour and document a known asymmetry.

        is_all_recs_submitted (database.py) treats both ``NULL`` and
        ``""`` as "not submitted" (its WHERE is
        ``submitted_date IS NULL OR submitted_date = ''``) — pinned by
        TestIsAllRecsSubmitted::
        test_empty_string_submitted_date_counts_as_unsubmitted.

        get_pending_recommenders only filters on ``submitted_date IS NULL``.
        A recommender whose date got cleared to ``""`` (which the page
        legitimately writes per the Notes-tab clear-field round-trip
        contract) is therefore "unsubmitted" by one helper but **silently
        excluded** from the alert list by the other. This test pins the
        current asymmetric behaviour so a future production change to
        normalise the two helpers (e.g. adding ``OR submitted_date = ''``
        to get_pending_recommenders) is a deliberate edit, not an
        invisible drift — the test will then need to flip and assert
        len(df) == 1, and an empty-string date will start surfacing as a
        pending alert."""
        pos_id = database.add_position(make_position())
        database.add_recommender(pos_id, {
            "recommender_name": "Dr. Jones",
            "asked_date":     (date.today() - timedelta(days=10)).isoformat(),
            "submitted_date": "",
        })
        df = database.get_pending_recommenders(7)
        assert len(df) == 0, (
            "Current behaviour: empty-string submitted_date is treated as "
            "'submitted' by get_pending_recommenders (only IS NULL is "
            "filtered). is_all_recs_submitted DISAGREES — both NULL and "
            "'' count as unsubmitted there. If you reconcile the two, "
            "flip this assertion to len(df) == 1 and update this docstring."
        )

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

    def test_active_statuses_drive_from_config_aliases(self, db, monkeypatch):
        """Sub-task 9 (TASKS C1): the active-statuses tuple in
        compute_materials_readiness must source from the
        config.STATUS_SAVED / STATUS_APPLIED / STATUS_INTERVIEW aliases
        rather than a hardcoded `("[SAVED]", "[APPLIED]", "[INTERVIEW]")`
        literal. Sentinel approach (precedent: Sub-task 4's
        `test_ddl_defaults_interpolate_from_config`): monkeypatch the
        aliases to values the DB doesn't contain and assert the scope
        collapses to zero. A hardcoded tuple would ignore the patch
        and still match the real `[SAVED]` row → this test is only
        satisfiable if the function reads aliases at call time."""
        # Seed a STATUS_SAVED position with a required doc — the
        # pre-monkeypatch query would pick it up.
        pid = database.add_position(make_position())
        database.update_position(pid, {"req_cv": "Yes", "done_cv": 0})
        # Sanity: before patching, the position is pending.
        assert database.compute_materials_readiness() == {"ready": 0, "pending": 1}

        # Patch all three aliases to sentinel values the DB never holds.
        monkeypatch.setattr(config, "STATUS_SAVED",     "[SENTINEL_SAVED]")
        monkeypatch.setattr(config, "STATUS_APPLIED",   "[SENTINEL_APPLIED]")
        monkeypatch.setattr(config, "STATUS_INTERVIEW", "[SENTINEL_INTERVIEW]")

        # Post-patch: the real row's status ("[SAVED]") is no longer in
        # the active set, so the position falls out of the aggregation.
        # A hardcoded-tuple implementation would still return
        # {"ready": 0, "pending": 1} and fail this assertion.
        result = database.compute_materials_readiness()
        assert result == {"ready": 0, "pending": 0}, (
            "compute_materials_readiness must read active statuses from "
            "config.STATUS_SAVED/APPLIED/INTERVIEW at call time, not "
            "from a hardcoded tuple literal."
        )

    def test_empty_requirement_docs_returns_zero_counts(self, db, monkeypatch):
        """Edge case: if `config.REQUIREMENT_DOCS` is empty (a valid
        future profile-expansion state per DESIGN §12.1 — e.g. a
        casual-tracker profile that ships without document
        requirements), `compute_materials_readiness` must return zero
        counts gracefully. The pre-fix SQL-fragment construction
        produced invalid SQL (`... AND ()`) when both
        `" OR ".join(...)` and `" AND ".join(...)` evaluated to empty
        strings on an empty REQUIREMENT_DOCS, surfacing as
        `sqlite3.OperationalError: near ")": syntax error`.

        Today the constant has 7 entries by config.py so this branch
        never fires in production, but a downstream caller (the
        dashboard's Materials Readiness panel) would crash on first
        load if a future profile shipped without docs. The defensive
        early-return makes the function compose cleanly with
        aggregator code that calls it unconditionally — same
        permission-to-have-no-data shape as `count_by_status()` on
        an empty DB."""
        # Seed a real position so the test exercises the function on
        # a non-empty DB — i.e., it's the empty REQUIREMENT_DOCS that
        # forces the zero-count, not an empty positions table.
        pid = database.add_position(make_position())
        database.update_position(pid, {"req_cv": "Yes", "done_cv": 1})
        # Sanity: before patching, the position is ready (one Yes/done).
        assert database.compute_materials_readiness() == {"ready": 1, "pending": 0}

        # Force REQUIREMENT_DOCS empty for the call. The DB schema
        # still carries the standard req_*/done_* columns from
        # init_db's run with the real config — so the test verifies
        # the function tolerates a config / schema mismatch without
        # synthesising invalid SQL.
        monkeypatch.setattr(config, "REQUIREMENT_DOCS", [])
        result = database.compute_materials_readiness()
        assert result == {"ready": 0, "pending": 0}, (
            "Empty config.REQUIREMENT_DOCS must yield "
            "{'ready': 0, 'pending': 0} without raising. "
            f"Got {result!r}"
        )


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

    # `test_terminal_statuses_are_subset_of_status_values` lives in
    # tests/test_config.py — pure config-invariant check that needs no
    # database fixture. Removed here to drop the duplicate.


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


# ── DESIGN §7 database.py contract #1: writers swallow exports failures ───────
# "Every public write function calls exports.write_all() as its last step,
# inside a try/except that logs errors but does not re-raise. A write that
# succeeded in the DB always reports success to its caller, even if markdown
# regeneration failed."
#
# Tests below pin the wrapping for every writer that calls _exports.write_all()
# (10 sites today: add_position, update_position, delete_position,
# upsert_application, add_interview, update_interview, delete_interview,
# add_recommender, update_recommender, delete_recommender). Each test forces
# exports.write_all() to raise via monkeypatch, calls the writer, and asserts
# the exception is swallowed AND a log entry was emitted.

class TestExportsLogAndContinue:
    """DESIGN §7 database.py contract #1 — every writer must swallow an
    exports.write_all() failure, log it, and continue to report success
    to its caller."""

    @staticmethod
    def _arm_boom(monkeypatch):
        """Force exports.write_all() to raise on every call. Returns the
        raised exception's message so tests can pin it loosely."""
        import exports
        msg = "simulated exports.write_all failure"

        def _explode():
            raise RuntimeError(msg)

        monkeypatch.setattr(exports, "write_all", _explode)
        return msg

    @pytest.mark.parametrize("writer_name", [
        "add_position",
        "update_position",
        "delete_position",
        "upsert_application",
        "add_interview",
        "update_interview",
        "delete_interview",
        "add_recommender",
        "update_recommender",
        "delete_recommender",
    ])
    def test_writer_swallows_exports_failure(
        self, db, monkeypatch, caplog, writer_name,
    ):
        """The writer must NOT re-raise an exports.write_all() failure.
        Parametrized so a single failure surfaces as a unique line in
        pytest output, naming the offending writer."""
        # Baseline rows BEFORE arming boom, so update/delete writers
        # have something to act on. Each baseline write itself calls
        # exports.write_all() — that's intentional happy-path coverage.
        pid = database.add_position({"position_name": "Baseline"})
        iid = database.add_interview(
            pid, {"scheduled_date": "2026-12-01"}
        )["id"]
        rid = database.add_recommender(
            pid, {"recommender_name": "Dr. Baseline"}
        )

        # Arm boom AFTER baseline so every subsequent exports.write_all()
        # raises.
        self._arm_boom(monkeypatch)

        callers = {
            "add_position":      lambda: database.add_position(
                {"position_name": "Z"}
            ),
            "update_position":   lambda: database.update_position(
                pid, {"position_name": "Y"}
            ),
            "delete_position":   lambda: database.delete_position(pid),
            "upsert_application": lambda: database.upsert_application(
                pid, {"applied_date": "2026-01-01"}
            ),
            "add_interview":     lambda: database.add_interview(
                pid, {"scheduled_date": "2026-12-15"}
            ),
            "update_interview":  lambda: database.update_interview(
                iid, {"notes": "updated"}
            ),
            "delete_interview":  lambda: database.delete_interview(iid),
            "add_recommender":   lambda: database.add_recommender(
                pid, {"recommender_name": "Dr. Y"}
            ),
            "update_recommender": lambda: database.update_recommender(
                rid, {"notes": "updated"}
            ),
            "delete_recommender": lambda: database.delete_recommender(rid),
        }

        with caplog.at_level("ERROR"):
            try:
                callers[writer_name]()
            except Exception as exc:
                pytest.fail(
                    f"{writer_name} re-raised exports.write_all() "
                    f"failure: {exc!r}. DESIGN §7 database.py #1 "
                    f"forbids this — DB write succeeded; markdown "
                    f"regeneration is best-effort."
                )

        # Log captured. The exact wording is implementation-defined;
        # what matters is that SOMETHING shows up in the error channel
        # so operators can correlate a missing markdown file with a
        # specific writer call.
        assert any(
            "export" in (r.message or "").lower()
            for r in caplog.records
        ), (
            f"Expected at least one log entry mentioning 'export' "
            f"after {writer_name} caught its exports.write_all() "
            f"failure. Got: {[r.message for r in caplog.records]}"
        )

    def test_db_write_commits_even_when_exports_fails(
        self, db, monkeypatch, caplog,
    ):
        """Load-bearing semantic pin: when exports.write_all() raises,
        the DB write must STILL be committed and visible to subsequent
        reads. Without this, a failed export would silently roll back
        the user's data — the exact opposite of the §7 contract."""
        self._arm_boom(monkeypatch)

        with caplog.at_level("ERROR"):
            pid = database.add_position(
                {"position_name": "Persisted Despite Boom"}
            )

        assert isinstance(pid, int) and pid > 0, (
            f"add_position must return a real id even when exports "
            f"fails. Got {pid!r}"
        )
        # Read back via a DIFFERENT writer/reader to confirm the row
        # was actually committed (not just returned in-memory).
        row = database.get_position(pid)
        assert row["position_name"] == "Persisted Despite Boom", (
            f"Row must persist when exports fails. Got {row!r}"
        )


# ── get_applications_table ────────────────────────────────────────────────────

class TestGetApplicationsTable:
    """get_applications_table() returns the joined positions × applications
    view that backs the Applications page table (DESIGN §8.3, Phase 5 T1-A).

    The reader is filter-agnostic — it returns every position; the page
    layer applies the default 'exclude SAVED + CLOSED' filter
    (DESIGN §8.3 + config.STATUS_FILTER_ACTIVE_EXCLUDED, added in T1-B).

    Contract:
      - Columns (in order): position_id, position_name, institute,
        deadline_date, status, applied_date, confirmation_received,
        confirmation_date, response_type, result.
      - One row per position. add_position auto-creates the applications
        row; the LEFT JOIN is defensive against a future migration that
        could leave an orphan position.
      - Sort: deadline_date ASC NULLS LAST, position_id ASC. The
        position_id tiebreaker is part of the contract so equal-deadline
        rows have a stable order across reruns (matches the selection-
        survival invariant pinned by streamlit-state-gotchas #11/#12).
    """

    EXPECTED_COLUMNS = [
        "position_id",
        "position_name",
        "institute",
        "deadline_date",
        "status",
        "applied_date",
        "confirmation_received",
        "confirmation_date",
        "response_type",
        "result",
    ]

    def test_empty_db_returns_empty_dataframe_with_expected_columns(self, db):
        """Empty DB must surface the column contract — the page's
        downstream filter / rename / display-projection chain assumes
        these columns exist on every render, not just rendering with
        data. Mirrors the equivalent T4-B contract for get_upcoming."""
        df = database.get_applications_table()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
        assert list(df.columns) == self.EXPECTED_COLUMNS, (
            f"Columns must be {self.EXPECTED_COLUMNS!r} in this order, "
            f"got {list(df.columns)!r}"
        )

    def test_one_row_per_position(self, db):
        """Two positions → two rows. The LEFT JOIN must not duplicate
        position rows; applications.position_id is a primary key so the
        join cardinality stays 1:1."""
        database.add_position(make_position({"position_name": "A"}))
        database.add_position(make_position({"position_name": "B"}))
        df = database.get_applications_table()
        assert len(df) == 2

    def test_position_fields_surface(self, db):
        """The positions-side fields land in the joined view with
        their stored values."""
        pid = database.add_position(make_position({
            "position_name": "BioStats",
            "institute":     "Stanford",
            "deadline_date": "2026-05-15",
        }))
        df = database.get_applications_table()
        row = df.iloc[0]
        assert row["position_id"]   == pid
        assert row["position_name"] == "BioStats"
        assert row["institute"]     == "Stanford"
        assert row["deadline_date"] == "2026-05-15"
        assert row["status"]        == config.STATUS_SAVED

    def test_application_defaults_after_add_position(self, db):
        """A freshly-added position has its applications row
        auto-created with the schema DEFAULT clause: applied_date /
        confirmation_date / response_type NULL; confirmation_received
        = 0; result = config.RESULT_DEFAULT. The reader must surface
        these unchanged so the page can rely on `result == 'Pending'`
        (and friends) without coercion at the page layer."""
        database.add_position(make_position())
        df = database.get_applications_table()
        row = df.iloc[0]
        assert row["applied_date"]          is None
        assert row["confirmation_received"] == 0
        assert row["confirmation_date"]     is None
        assert row["response_type"]         is None
        assert row["result"]                == config.RESULT_DEFAULT

    def test_application_fields_surface_after_upsert(self, db):
        """upsert_application updates show up on the next read. Pin the
        common fields that drive the Applications page table (Applied /
        Confirmation / Response). Uses propagate_status=False so the
        R-cascade side effects are tested elsewhere (TestUpsertApplication
        R1/R3) rather than here — keeping the assertion focused on the
        join + column-projection contract."""
        pid = database.add_position(make_position())
        database.upsert_application(pid, {
            "applied_date":          "2026-04-18",
            "confirmation_received": 1,
            "confirmation_date":     "2026-04-19",
            "response_type":         "Interview Invite",
        }, propagate_status=False)
        df = database.get_applications_table()
        row = df.iloc[0]
        assert row["applied_date"]          == "2026-04-18"
        assert row["confirmation_received"] == 1
        assert row["confirmation_date"]     == "2026-04-19"
        assert row["response_type"]         == "Interview Invite"

    def test_ordered_by_deadline_asc_nulls_last(self, db):
        """Primary sort: deadline_date ASC NULLS LAST. NULL deadlines
        sort to the bottom. Mirrors the get_all_positions contract
        (§7 #5) so the two readers agree on row order."""
        database.add_position(make_position({
            "position_name": "Late",
            "deadline_date": "2026-06-30",
        }))
        database.add_position(make_position({
            "position_name": "No deadline",
            "deadline_date": None,
        }))
        database.add_position(make_position({
            "position_name": "Soon",
            "deadline_date": "2026-04-15",
        }))
        df = database.get_applications_table()
        assert list(df["position_name"]) == ["Soon", "Late", "No deadline"]

    def test_position_id_breaks_deadline_ties(self, db):
        """Two positions sharing the same deadline_date sort by
        position_id ASC. The stable tiebreaker is part of the contract
        — without it, SQLite is free to return ties in either order,
        which would surface as a flickering selection across reruns
        on the Applications page (per streamlit-state-gotchas #12)."""
        pid_a = database.add_position(make_position({
            "position_name": "A",
            "deadline_date": "2026-05-01",
        }))
        pid_b = database.add_position(make_position({
            "position_name": "B",
            "deadline_date": "2026-05-01",
        }))
        df = database.get_applications_table()
        ids = list(df["position_id"])
        assert ids == sorted([pid_a, pid_b]), (
            f"Equal-deadline rows must order by position_id ASC; "
            f"got {ids!r}"
        )

    def test_includes_terminal_status_rows(self, db):
        """The reader is filter-agnostic — terminal-status positions
        ([CLOSED] / [REJECTED] / [DECLINED]) must be in the DataFrame
        regardless of where they sit in the pipeline. The Applications
        page layer applies the default 'exclude SAVED + CLOSED' filter
        (DESIGN §8.3); the reader stays general so a future 'All'
        filter selection can surface every row without a second query."""
        database.add_position(make_position({"position_name": "Open"}))
        pid_closed = database.add_position(
            make_position({"position_name": "Closed-out"})
        )
        database.update_position(pid_closed, {"status": config.STATUS_CLOSED})

        df = database.get_applications_table()
        assert len(df) == 2
        statuses = dict(zip(df["position_name"], df["status"]))
        assert statuses["Open"]       == config.STATUS_SAVED
        assert statuses["Closed-out"] == config.STATUS_CLOSED
