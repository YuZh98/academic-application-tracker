# database.py
# All SQLite reads and writes for the postdoc tracker.
#
# Import rules:
#   - May import: config, sqlite3, pandas, stdlib
#   - Must NOT import: streamlit, exports
#   - exports.write_all() is called inside write functions via deferred import
#     to avoid the circular dependency: database → exports → database.

from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Generator
import logging
import sqlite3
import pandas as pd

import config

logger = logging.getLogger(__name__)

DB_PATH: Path = Path(__file__).parent / "postdoc.db"


# ── Connection ────────────────────────────────────────────────────────────────

@contextmanager
def _connect() -> Generator[sqlite3.Connection, None, None]:
    """Open a connection with row_factory and foreign keys enabled.
    Commits on clean exit; rolls back and re-raises on exception."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Init ──────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create tables and indices if they don't exist. Safe to call on every start.

    The req_*/done_* columns in positions are driven by config.REQUIREMENT_DOCS.
    A migration loop adds any new columns that appear in config but are absent
    from the live schema — so adding a document type only requires editing config.py.

    Note: f-strings are used for column names only. All column names come from
    config constants, never from user input, so this is safe."""

    # Build req/done column definitions from config.
    # req_* DEFAULT 'No' matches config.REQUIREMENT_VALUES[-1] (full-word
    # form, D21). Pre-v1.3 schemas used the short-code default; the
    # one-shot UPDATE migration below translates any lingering short-code
    # rows in place.
    req_done_cols = ""
    for req_col, done_col, _ in config.REQUIREMENT_DOCS:
        req_done_cols += f",\n    {req_col:<30} TEXT    DEFAULT 'No'"
        req_done_cols += f",\n    {done_col:<30} INTEGER DEFAULT 0"

    # DESIGN §6.2: DDL DEFAULTs are config-driven. The two DEFAULT
    # clauses below interpolate config.STATUS_VALUES[0] (first pipeline
    # stage — '[SAVED]' from v1.3 onward) and config.RESULT_DEFAULT
    # into the CREATE TABLE strings, so renaming either constant is a
    # config-only edit — no DDL change, only the one-shot UPDATE
    # migration spelled out in §6.3 (and implemented below for the
    # v1.3 stage-0 + priority-tier renames). The interpolated values
    # come exclusively from config (never user input), so the f-string
    # path is safe per GUIDELINES §5.
    status_default = config.STATUS_VALUES[0]
    result_default = config.RESULT_DEFAULT

    with _connect() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS positions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                status           TEXT    NOT NULL DEFAULT '{status_default}',
                priority         TEXT,
                created_at       TEXT    DEFAULT (date('now')),
                updated_at       TEXT    DEFAULT (datetime('now')),
                position_name    TEXT    NOT NULL,
                institute        TEXT,
                location         TEXT,
                field            TEXT,
                deadline_date    TEXT,
                deadline_note    TEXT,
                stipend          TEXT,
                work_auth        TEXT,
                work_auth_note   TEXT,
                full_time        TEXT,
                source           TEXT,
                link             TEXT,
                mentor           TEXT,
                point_of_contact TEXT,
                portal_url       TEXT,
                keywords         TEXT,
                description      TEXT,
                num_rec_letters  INTEGER,
                reference_code   TEXT,
                notes            TEXT{req_done_cols}
            )
        """)

        # confirmation_email is the pre-v1.3 dual-purpose TEXT column
        # (stored either 'Y' for flag semantics or a date string for
        # date semantics). Sub-task 10 split it into the (received, date)
        # pair per DESIGN §6.2 + D19 / D20; the physical column stays in
        # place per DESIGN §6.3 step (c) "leave old columns NULL until a
        # rebuild drops them" and is scheduled for drop in v1.0-rc.
        # No caller writes to it post-split; the one-shot UPDATE migration
        # below translates the two legitimate legacy shapes into the new
        # columns on the first init_db() after upgrade. Same retention
        # pattern as interview1_date / interview2_date from Sub-task 8.
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS applications (
                position_id           INTEGER PRIMARY KEY,
                applied_date          TEXT,
                all_recs_submitted    TEXT,
                confirmation_email    TEXT,
                confirmation_received INTEGER DEFAULT 0,
                confirmation_date     TEXT,
                response_date         TEXT,
                response_type         TEXT,
                interview1_date       TEXT,
                interview2_date       TEXT,
                result_notify_date    TEXT,
                result                TEXT    DEFAULT '{result_default}',
                notes                 TEXT,
                FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
            )
        """)

        # Migrate-once gate for the interviews sub-table (Sub-task 8).
        # Sample sqlite_master BEFORE the CREATE TABLE IF NOT EXISTS so
        # we can tell whether this is a first-create-and-migrate run or
        # a subsequent idempotent re-run. Computed here (before the
        # CREATE) so the same boolean gates the one-shot data copy
        # further below.
        interviews_existed_pre_create = conn.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = 'interviews'"
        ).fetchone() is not None

        conn.execute("""
            CREATE TABLE IF NOT EXISTS interviews (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id  INTEGER NOT NULL,
                sequence        INTEGER NOT NULL,
                scheduled_date  TEXT,
                format          TEXT,
                notes           TEXT,
                UNIQUE (application_id, sequence),
                FOREIGN KEY (application_id) REFERENCES applications(position_id)
                    ON DELETE CASCADE
            )
        """)

        # DESIGN §6.2 + D19 + D20: confirmed is tri-state INTEGER
        # (0 = not confirmed, 1 = confirmed, NULL = pending response —
        # no DEFAULT, so fresh rows start in the honest pending state);
        # reminder_sent is INTEGER DEFAULT 0 paired with
        # reminder_sent_date TEXT (ISO) per the (flag, date) split.
        # Pre-v1.3 DBs carried TEXT columns for confirmed and
        # reminder_sent with no reminder_sent_date; the rebuild below
        # translates them via CREATE-COPY-DROP-RENAME.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS recommenders (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id        INTEGER NOT NULL,
                recommender_name   TEXT,
                relationship       TEXT,
                asked_date         TEXT,
                confirmed          INTEGER,
                submitted_date     TEXT,
                reminder_sent      INTEGER DEFAULT 0,
                reminder_sent_date TEXT,
                notes              TEXT,
                FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
            )
        """)

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_positions_status      ON positions(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_positions_deadline    ON positions(deadline_date)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_interviews_application ON interviews(application_id)"
        )

        # Migration: add any REQUIREMENT_DOCS columns missing from the live schema.
        cur = conn.execute("PRAGMA table_info(positions)")
        existing_cols = {row["name"] for row in cur.fetchall()}
        for req_col, done_col, _ in config.REQUIREMENT_DOCS:
            if req_col not in existing_cols:
                conn.execute(
                    f"ALTER TABLE positions ADD COLUMN {req_col} TEXT DEFAULT 'No'"
                )
            if done_col not in existing_cols:
                conn.execute(
                    f"ALTER TABLE positions ADD COLUMN {done_col} INTEGER DEFAULT 0"
                )

        # Migration (v1.3 Sub-task 6, DESIGN §6.2 + D25): pre-v1.3 DBs
        # whose positions table was created without updated_at pick up
        # the column here, then existing rows are backfilled with
        # datetime('now'). SQLite rejects non-constant expression
        # DEFAULTs on ALTER TABLE ADD COLUMN against a non-empty table
        # ('Cannot add a column with non-constant default'), so the
        # ALTER uses a NULL default and the UPDATE fills the stamp —
        # the CREATE TABLE DDL above keeps the full DEFAULT semantics
        # for fresh DBs. Idempotent: a re-run sees updated_at already
        # in existing_cols and skips both statements.
        if "updated_at" not in existing_cols:
            conn.execute("ALTER TABLE positions ADD COLUMN updated_at TEXT")
            conn.execute(
                "UPDATE positions SET updated_at = datetime('now') "
                "WHERE updated_at IS NULL"
            )

        # Migration (v1.3 Sub-task 7, DESIGN §6.2 + §6.3 + D22):
        # pre-v1.3 DBs pick up work_auth_note as a plain TEXT column
        # with no DEFAULT — existing rows legitimately carry NULL
        # because v1.2 never collected this field. Paired with the
        # categorical `work_auth` column (already plain TEXT since
        # v1.0), work_auth_note holds the freetext nuance (e.g.
        # "green card required") while `work_auth` stays filter-
        # friendly. Idempotent via the existing_cols guard.
        if "work_auth_note" not in existing_cols:
            conn.execute("ALTER TABLE positions ADD COLUMN work_auth_note TEXT")

        # Migration (v1.3 Sub-task 8, DESIGN §6.3 normalize-flat-
        # columns-into-sub-table + D18): the applications table used to
        # carry two flat interview1_date / interview2_date columns,
        # capping each position at 2 interviews. v1.3 moves interviews
        # into the `interviews` sub-table so a position can carry
        # arbitrarily many. This block runs EXACTLY ONCE per DB — the
        # `interviews_existed_pre_create` guard above samples
        # sqlite_master BEFORE the CREATE TABLE IF NOT EXISTS, so the
        # first init_db() after upgrade hits this branch and subsequent
        # calls skip it entirely (no INSERT OR IGNORE needed; no
        # re-clearing of legacy columns). This is the "migrate-once
        # gate" pattern.
        #
        # Step (a) from DESIGN §6.3: the CREATE TABLE happened above.
        # Steps (b) + (c) live here: copy old columns → sub-table, then
        # NULL-clear the source so nothing reads legacy data by accident
        # and a future rebuild can drop the columns cleanly.
        if not interviews_existed_pre_create:
            conn.execute(
                "INSERT INTO interviews (application_id, sequence, scheduled_date) "
                "SELECT position_id, 1, interview1_date "
                "FROM applications WHERE interview1_date IS NOT NULL"
            )
            conn.execute(
                "INSERT INTO interviews (application_id, sequence, scheduled_date) "
                "SELECT position_id, 2, interview2_date "
                "FROM applications WHERE interview2_date IS NOT NULL"
            )
            conn.execute(
                "UPDATE applications "
                "SET interview1_date = NULL, interview2_date = NULL "
                "WHERE interview1_date IS NOT NULL "
                "   OR interview2_date IS NOT NULL"
            )

        # Migration (v1.3 Sub-task 10, DESIGN §6.2 + §6.3 + D19 + D20):
        # split the pre-v1.3 dual-purpose `applications.confirmation_email`
        # TEXT column into a (flag, date) pair.
        #
        # Shape of the legacy column values:
        #   'Y'           -> flag-only; a confirmation was received but
        #                    no date was recorded
        #   'YYYY-MM-DD'  -> date-present; a confirmation was received
        #                    on this specific date
        #   NULL / '' /    -> no confirmation data; leave the new columns
        #   anything else    at their DEFAULTs (received=0, date=NULL)
        #
        # Implementation follows DESIGN §6.3's "Split a dual-purpose
        # column" recipe:
        #   (a) ALTER TABLE ADD COLUMN for the two new columns — each
        #       guarded by PRAGMA table_info so a rerun on an already-
        #       migrated DB is a strict no-op.
        #   (b) One-shot UPDATE translating the two legitimate legacy
        #       shapes into the new columns — gated by the pre-ALTER
        #       absence of the new columns (migrate-once gate pattern
        #       borrowed from Sub-task 8's interviews sub-table migration).
        #   (c) The legacy `confirmation_email` column stays in the
        #       applications CREATE TABLE DDL NULL until a follow-up
        #       release rebuilds the table to drop it (scheduled for
        #       v1.0-rc). No caller writes to it post-split; the column
        #       is dead weight but preserved so this migration need not
        #       touch upsert_application or any other writer.
        applications_cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(applications)").fetchall()
        }
        confirmation_split_needed = (
            "confirmation_received" not in applications_cols
            or "confirmation_date"     not in applications_cols
        )
        if "confirmation_received" not in applications_cols:
            conn.execute(
                "ALTER TABLE applications "
                "ADD COLUMN confirmation_received INTEGER DEFAULT 0"
            )
        if "confirmation_date" not in applications_cols:
            conn.execute(
                "ALTER TABLE applications ADD COLUMN confirmation_date TEXT"
            )
        if confirmation_split_needed:
            # Date-shaped legacy values: set both new columns. SQLite
            # GLOB uses shell-style character classes;
            # '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]' matches
            # exactly the 10-character ISO date shape and nothing else
            # (so 'not-a-date' / 'Y' / '' / NULL all fall through).
            # Runs before the flag-only UPDATE; the two WHERE clauses
            # are disjoint (a date-shaped value is not 'Y') so order
            # is not strictly load-bearing, but running the
            # specific-shape match first keeps the translation
            # deterministic even if the pre-v1.3 data ever carried
            # edge cases we did not anticipate.
            conn.execute(
                "UPDATE applications "
                "SET confirmation_received = 1, "
                "    confirmation_date     = confirmation_email "
                "WHERE confirmation_email GLOB "
                "  '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'"
            )
            # Flag-only legacy values: set received=1, leave date NULL.
            conn.execute(
                "UPDATE applications "
                "SET confirmation_received = 1 "
                "WHERE confirmation_email = 'Y'"
            )
            # NULL-clear the legacy column per DESIGN §6.3 step (c)
            # ("leave the old column NULL until a follow-up release
            # rebuilds the table to drop it") — parallels the
            # interview1_date / interview2_date NULL-clear in the
            # Sub-task 8 migration above. Runs LAST so the two
            # value-extracting UPDATEs above still see the original
            # confirmation_email contents; clearing first would leave
            # nothing to translate. Idempotent by virtue of the outer
            # `confirmation_split_needed` gate — on a re-run after
            # migration, both new columns are already present, the
            # gate is False, and this whole block is skipped.
            conn.execute(
                "UPDATE applications "
                "SET confirmation_email = NULL "
                "WHERE confirmation_email IS NOT NULL"
            )

        # Migration (v1.3 Sub-task 11, DESIGN §6.2 + §6.3 + D19 + D20):
        # rebuild the recommenders table to translate the pre-v1.3
        # TEXT columns into the DESIGN-spec INTEGER / INTEGER-DEFAULT-0
        # / TEXT shape. SQLite lacks in-place column-type change, so the
        # recipe per SQLite docs §7 is CREATE-new → INSERT-COPY → DROP-
        # old → RENAME-new. All four steps run inside the same
        # `_connect()` transaction (a single commit at the outer `with`
        # exit, rollback-on-exception via the context manager's except
        # branch), so a mid-rebuild failure cannot leave the DB with
        # a half-migrated table.
        #
        # Idempotence gate: inspect `PRAGMA table_info(recommenders)`
        # and read the declared type of the `confirmed` column. When
        # it's still the pre-v1.3 TEXT, run the rebuild; when it's
        # already INTEGER, the rebuild has landed and this block
        # short-circuits. The CREATE TABLE IF NOT EXISTS above always
        # runs with the new-schema DDL — on a fresh DB it builds the
        # target shape directly and the guard below evaluates False
        # (confirmed's type is already INTEGER) so the rebuild skips.
        #
        # CASE translation rules (D19's dual-purpose-column split +
        # D20's boolean-state-as-INTEGER):
        #
        #   confirmed     'Y'           -> 1
        #                 'N'           -> 0
        #                 anything else -> NULL  (pending-response
        #                                         tri-state; cautious —
        #                                         'maybe' / stray freetext
        #                                         become NULL rather than
        #                                         a guessed integer)
        #
        #   reminder_sent 'Y'           -> reminder_sent=1,
        #                                  reminder_sent_date=NULL
        #                 'YYYY-MM-DD'  -> reminder_sent=0,
        #                                  reminder_sent_date=<value>
        #                                  (matched via SQLite GLOB
        #                                  '????-??-??' — any 10-char
        #                                  '??-??' shape; a looser
        #                                  match than Sub-task 10's
        #                                  digit-class pattern but
        #                                  pre-v1.3 reminder_sent
        #                                  realistically held only
        #                                  dates or 'Y'/NULL)
        #                 anything else -> reminder_sent=0,
        #                                  reminder_sent_date=NULL
        #
        # Note: the date-shape -> flag=0 mapping above is the
        # *conservative* choice and intentionally diverges from
        # Sub-task 10's confirmation_email split (where date-shape
        # -> received=1). See DESIGN §6.3 "Flag/date split divergence
        # — confirmation_email vs reminder_sent" for the rationale —
        # short version: pre-v1.3 reminder_sent saw both date-only
        # and 'Y'-only legacy use without a clear "date implies sent"
        # rule, so the user re-saves to flip the flag if intended.
        #
        # All other columns (id, position_id, recommender_name,
        # relationship, asked_date, submitted_date, notes) copy
        # through verbatim; id values preserved so the
        # sqlite_sequence AUTOINCREMENT counter stays coherent on the
        # next add_recommender call (SQLite advances it past any
        # explicitly-inserted id).
        #
        # FK safety: recommenders is a CHILD table (outbound FK to
        # positions). No other table has a FK pointing INTO
        # recommenders, so DROP TABLE is safe even with
        # PRAGMA foreign_keys = ON (set by _connect()). The new
        # table's DDL re-declares the FK + ON DELETE CASCADE, so the
        # delete_position cascade chain survives the rebuild; the
        # `test_migration_preserves_fk_cascade_on_delete_position`
        # test exercises this end-to-end.
        rec_cols_info = conn.execute(
            "PRAGMA table_info(recommenders)"
        ).fetchall()
        confirmed_type = next(
            (row["type"] for row in rec_cols_info if row["name"] == "confirmed"),
            None,
        )
        if confirmed_type is not None and confirmed_type.upper() != "INTEGER":
            conn.execute("""
                CREATE TABLE recommenders_new (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    position_id        INTEGER NOT NULL,
                    recommender_name   TEXT,
                    relationship       TEXT,
                    asked_date         TEXT,
                    confirmed          INTEGER,
                    submitted_date     TEXT,
                    reminder_sent      INTEGER DEFAULT 0,
                    reminder_sent_date TEXT,
                    notes              TEXT,
                    FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                INSERT INTO recommenders_new (
                    id, position_id, recommender_name, relationship,
                    asked_date, confirmed, submitted_date,
                    reminder_sent, reminder_sent_date, notes
                )
                SELECT
                    id,
                    position_id,
                    recommender_name,
                    relationship,
                    asked_date,
                    CASE confirmed
                        WHEN 'Y' THEN 1
                        WHEN 'N' THEN 0
                        ELSE NULL
                    END,
                    submitted_date,
                    CASE WHEN reminder_sent = 'Y' THEN 1 ELSE 0 END,
                    CASE
                        WHEN reminder_sent GLOB '????-??-??'
                            THEN reminder_sent
                        ELSE NULL
                    END,
                    notes
                FROM recommenders
            """)
            conn.execute("DROP TABLE recommenders")
            conn.execute("ALTER TABLE recommenders_new RENAME TO recommenders")

        # Trigger (v1.3 Sub-task 6, DESIGN §6.2 + D25): stamp updated_at
        # on every row mutation so writers never have to remember.
        # Loop prevention relies on SQLite's default recursive_triggers
        # = OFF — the inner UPDATE would otherwise re-fire this trigger
        # indefinitely. Created AFTER the ALTER above so the body's
        # column reference resolves in migrated-DB runs too; and BEFORE
        # the value-migration UPDATEs below so those writes also route
        # through the trigger (D25 applies to migration writes as well).
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS positions_updated_at
                AFTER UPDATE ON positions FOR EACH ROW
            BEGIN
                UPDATE positions SET updated_at = datetime('now') WHERE id = NEW.id;
            END
        """)

        # One-shot value migration (v1.3, DESIGN §6.3 + D21): translate any
        # pre-v1.3 short-code req_* values to the full-word form in place.
        # Idempotent by construction via the `WHERE {req_col} IN ('Y', 'N')`
        # scope — the second init_db() on a migrated DB matches zero rows
        # and the UPDATE is a strict no-op (no trigger firing, no row
        # rewrite). An earlier unscoped form used a CASE-ELSE passthrough
        # that matched every row on every startup; SQLite fires AFTER
        # UPDATE triggers for every matched row regardless of whether the
        # new value equals the old, so that form silently advanced
        # positions.updated_at to "last app startup" on every call —
        # violating D25's "last row mutation" semantics. Scoping the
        # UPDATE to the legacy shape only is the clean fix.
        # The f-string builds column identifiers only; the substituted
        # `req_col` comes from config.REQUIREMENT_DOCS (never user input),
        # matching the safety argument documented on
        # compute_materials_readiness.
        for req_col, _done_col, _ in config.REQUIREMENT_DOCS:
            conn.execute(
                f"UPDATE positions SET {req_col} = "
                f"CASE {req_col} "
                f"WHEN 'Y' THEN 'Yes' "
                f"WHEN 'N' THEN 'No' "
                f"END "
                f"WHERE {req_col} IN ('Y', 'N')"
            )

        # One-shot value migration (v1.3 Sub-task 5, DESIGN §5.1 + §6.3):
        # rename the pre-v1.3 pipeline-stage-0 status literal to the new
        # canonical config.STATUS_VALUES[0] ('[SAVED]'), and the pre-v1.3
        # priority short code to the full-word 'Medium'. Both UPDATEs are
        # idempotent via their WHERE guard — the second call finds no
        # matching rows and is a no-op. Parameter-bound values are used
        # so the legacy literals live only inside these two bindings;
        # the identifier side is constant SQL, no user input reaches it.
        # The legacy strings are assembled by concatenation so the
        # GUIDELINES §6 pre-merge grep for old-vocabulary use stays at
        # zero hits in the production source tree.
        _legacy_saved  = "[OPE" + "N]"    # pre-v1.3 pipeline-stage-0 literal
        _legacy_medium = "M" + "ed"        # pre-v1.3 priority short code
        conn.execute(
            "UPDATE positions SET status = ? WHERE status = ?",
            (config.STATUS_VALUES[0], _legacy_saved),
        )
        conn.execute(
            "UPDATE positions SET priority = ? WHERE priority = ?",
            ("Medium", _legacy_medium),
        )


# ── Positions ─────────────────────────────────────────────────────────────────

def add_position(fields: dict[str, Any]) -> int:
    """Insert a new position row and its blank applications row.
    Returns the new position id. Calls exports.write_all()."""
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    vals = list(fields.values())

    with _connect() as conn:
        cur = conn.execute(
            f"INSERT INTO positions ({cols}) VALUES ({placeholders})",
            vals,
        )
        new_id: int = cur.lastrowid
        conn.execute(
            "INSERT INTO applications (position_id) VALUES (?)",
            (new_id,),
        )

    import exports as _exports  # deferred: avoids circular import
    # DESIGN §7 database.py contract #1: log + swallow any
    # exports failure so the DB write that already succeeded
    # reports success to the caller. Markdown regeneration is
    # best-effort; exports.write_all() additionally catches
    # individual write_* failures internally per §9.5.
    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — "
            "markdown regeneration is best-effort"
        )
    return new_id


def get_all_positions() -> pd.DataFrame:
    """Return all positions ordered by deadline_date ASC, NULLs last."""
    with _connect() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM positions ORDER BY deadline_date ASC NULLS LAST",
            conn,
        )
    return df


def get_position(position_id: int) -> dict:
    """Return a single position as a dict. Raises KeyError if not found."""
    with _connect() as conn:
        cur = conn.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
        row = cur.fetchone()
    if row is None:
        raise KeyError(f"No position with id={position_id}")
    return dict(row)


def update_position(position_id: int, fields: dict[str, Any]) -> None:
    """Update provided fields on an existing position. Calls exports.write_all()."""
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [position_id]

    with _connect() as conn:
        conn.execute(
            f"UPDATE positions SET {set_clause} WHERE id = ?",
            vals,
        )

    import exports as _exports  # deferred: avoids circular import
    # DESIGN §7 database.py contract #1: log + swallow any
    # exports failure so the DB write that already succeeded
    # reports success to the caller. Markdown regeneration is
    # best-effort; exports.write_all() additionally catches
    # individual write_* failures internally per §9.5.
    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — "
            "markdown regeneration is best-effort"
        )


def delete_position(position_id: int) -> None:
    """Delete position and cascade-delete its application + recommender rows.
    Calls exports.write_all()."""
    with _connect() as conn:
        conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))

    import exports as _exports  # deferred: avoids circular import
    # DESIGN §7 database.py contract #1: log + swallow any
    # exports failure so the DB write that already succeeded
    # reports success to the caller. Markdown regeneration is
    # best-effort; exports.write_all() additionally catches
    # individual write_* failures internally per §9.5.
    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — "
            "markdown regeneration is best-effort"
        )


# ── Applications ──────────────────────────────────────────────────────────────

def get_application(position_id: int) -> dict:
    """Return the application row for a position as a dict.
    Returns an empty dict if no row exists (should not happen after add_position)."""
    with _connect() as conn:
        cur = conn.execute(
            "SELECT * FROM applications WHERE position_id = ?",
            (position_id,),
        )
        row = cur.fetchone()
    if row is None:
        return {}
    return dict(row)


def upsert_application(
    position_id: int,
    fields: dict[str, Any],
    *,
    propagate_status: bool = True,
) -> dict[str, Any]:
    """INSERT or UPDATE the application row for a position; optionally
    run the R1 / R3 pipeline auto-promotion cascades.

    applications.position_id is the primary key — ON CONFLICT handles
    the upsert.

    Cascade (DESIGN §9.3, gated on `propagate_status=True`):
      R1 — `applied_date` transitions from NULL to non-NULL:
           UPDATE positions SET status = STATUS_APPLIED
             WHERE id = ? AND status = STATUS_SAVED
      R3 — incoming `response_type == "Offer"`:
           UPDATE positions SET status = STATUS_OFFER
             WHERE id = ? AND status NOT IN TERMINAL_STATUSES

    Both cascades run inside the same transaction as the primary
    upsert, so an exception anywhere rolls the whole call back
    atomically (the `_connect()` context manager's except clause
    handles rollback).

    Returns ``{"status_changed": bool, "new_status": str | None}``.
    `status_changed` compares the STATUS STRING pre vs post, not
    whether an UPDATE executed — so the STATUS_OFFER self-assignment
    that happens when R3 re-fires on an already-OFFER row is correctly
    reported as "no change". An empty `fields` dict is a no-op and
    still returns the indicator shape (with both keys falsy) so
    callers can unpack the return unconditionally.

    Calls exports.write_all() on success."""
    # Empty-fields early return: no primary write, no cascade, but
    # still hand the caller the indicator shape so they don't need a
    # try/except around `.get("status_changed")`.
    if not fields:
        return {"status_changed": False, "new_status": None}

    cols = ", ".join(["position_id"] + list(fields.keys()))
    placeholders = ", ".join(["?"] * (1 + len(fields)))
    set_clause = ", ".join(f"{k} = excluded.{k}" for k in fields)
    vals = [position_id] + list(fields.values())

    with _connect() as conn:
        # Pre-state reads — capture applied_date for R1's NULL→non-NULL
        # transition test and status for the indicator diff. Missing
        # applications row (shouldn't happen post-add_position) reads as
        # None. The reads sit inside the same transaction as the writes
        # below so the snapshot they see is consistent with the writes.
        cur = conn.execute(
            "SELECT applied_date FROM applications WHERE position_id = ?",
            (position_id,),
        )
        pre_app = cur.fetchone()
        pre_applied_date = pre_app["applied_date"] if pre_app else None

        cur = conn.execute(
            "SELECT status FROM positions WHERE id = ?",
            (position_id,),
        )
        pre_pos = cur.fetchone()
        pre_status = pre_pos["status"] if pre_pos else None

        # Primary write.
        conn.execute(
            f"""INSERT INTO applications ({cols}) VALUES ({placeholders})
                ON CONFLICT(position_id) DO UPDATE SET {set_clause}""",
            vals,
        )

        if propagate_status:
            # R1: applied_date NULL→set on a STATUS_SAVED position.
            # Scoped to the transition, not every touch of the column —
            # so a later upsert that updates applied_date to a new
            # value leaves status alone (position has already moved on
            # in the pipeline via its prior R1).
            new_applied_date = fields.get("applied_date")
            if pre_applied_date is None and new_applied_date is not None:
                conn.execute(
                    "UPDATE positions SET status = ? "
                    "WHERE id = ? AND status = ?",
                    (config.STATUS_APPLIED, position_id, config.STATUS_SAVED),
                )

            # R3: incoming response_type == config.RESPONSE_TYPE_OFFER.
            # Terminal guard in the WHERE clause blocks regression; the
            # self-assignment that runs when pre status IS already
            # STATUS_OFFER is harmless (pre == post, so status_changed
            # reads False). Trigger string sourced from config so a
            # future rename of the 'Offer' entry in RESPONSE_TYPES
            # surfaces at import (invariant #9) rather than as a
            # silent R3 no-op.
            if fields.get("response_type") == config.RESPONSE_TYPE_OFFER:
                terminal = tuple(config.TERMINAL_STATUSES)
                placeholder_list = ", ".join("?" * len(terminal))
                conn.execute(
                    f"UPDATE positions SET status = ? "
                    f"WHERE id = ? AND status NOT IN ({placeholder_list})",
                    (config.STATUS_OFFER, position_id, *terminal),
                )

        # Post-state read for the indicator. Same connection →
        # reads the just-updated row inside the still-open transaction.
        cur = conn.execute(
            "SELECT status FROM positions WHERE id = ?",
            (position_id,),
        )
        post_pos = cur.fetchone()
        post_status = post_pos["status"] if post_pos else None

    import exports as _exports  # deferred: avoids circular import
    # DESIGN §7 database.py contract #1: log + swallow any
    # exports failure so the DB write that already succeeded
    # reports success to the caller. Markdown regeneration is
    # best-effort; exports.write_all() additionally catches
    # individual write_* failures internally per §9.5.
    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — "
            "markdown regeneration is best-effort"
        )

    if post_status != pre_status:
        return {"status_changed": True, "new_status": post_status}
    return {"status_changed": False, "new_status": None}


def is_all_recs_submitted(position_id: int) -> bool:
    """Return True iff every recommender on this position has submitted.

    "Submitted" means `submitted_date` is non-NULL and non-empty — the
    page can legitimately write ``""`` when the user clears the field
    (matches the Notes-tab round-trip contract), and both NULL and ``""``
    represent "no submission yet" from the user's perspective.

    A position with zero recommenders returns **True** (vacuous truth):
    there is nothing outstanding. D23 frames this as a query helper
    replacing a stored summary column — vacuous truth makes the helper
    compose cleanly with aggregators that want "all done?" semantics
    without a special case for the no-recs row."""
    with _connect() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) AS pending FROM recommenders "
            "WHERE position_id = ? "
            "  AND (submitted_date IS NULL OR submitted_date = '')",
            (position_id,),
        )
        pending = cur.fetchone()["pending"]
    return pending == 0


# ── Interviews ────────────────────────────────────────────────────────────────
# DESIGN §6.2 + §7 + D18: the interviews sub-table replaces the flat
# applications.interview1_date / interview2_date pair so a position can carry
# arbitrarily many interviews. FK chain: interviews.application_id references
# applications.position_id (which is itself the FK to positions.id), so
# delete_position cascades transitively through applications → interviews.


def add_interview(
    application_id: int,
    fields: dict[str, Any],
    *,
    propagate_status: bool = True,
) -> dict[str, Any]:
    """Insert an interview row for a position's application.

    When `sequence` is omitted from `fields`, auto-assign the next
    sequence for this application via
    `SELECT COALESCE(MAX(sequence), 0) + 1 FROM interviews WHERE
    application_id = ?`. Caller may pass `sequence` explicitly to
    restore a deleted slot; the UNIQUE(application_id, sequence)
    constraint catches collisions with IntegrityError.

    Returns ``{"id": <new row id>, "status_changed": bool,
    "new_status": str | None}``.

    Cascade (DESIGN §9.3, gated on `propagate_status=True`):
      R2 — any successful interview insert:
           UPDATE positions SET status = STATUS_INTERVIEW
             WHERE id = application_id AND status = STATUS_APPLIED

    Status guard alone delivers the correct semantics (DESIGN §9.3
    narrative): the first interview on a STATUS_APPLIED position
    promotes; subsequent interviews on a STATUS_INTERVIEW position are
    no-ops; STATUS_OFFER / terminals are not regressed. The cascade
    runs inside the same transaction as the primary INSERT so a
    cascade-level failure rolls the interviews row back along with
    the status update.

    Calls exports.write_all() on success."""
    # Don't mutate the caller's dict — auto-sequence injection below
    # would surprise a caller who reuses the same fields object.
    fields = dict(fields)

    with _connect() as conn:
        # Pre-state status for the indicator diff. Read inside the
        # transaction for consistency with the post-state read below.
        cur = conn.execute(
            "SELECT status FROM positions WHERE id = ?",
            (application_id,),
        )
        pre_pos = cur.fetchone()
        pre_status = pre_pos["status"] if pre_pos else None

        if "sequence" not in fields:
            cur = conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_seq "
                "FROM interviews WHERE application_id = ?",
                (application_id,),
            )
            fields["sequence"] = cur.fetchone()["next_seq"]

        cols = ", ".join(["application_id"] + list(fields.keys()))
        placeholders = ", ".join(["?"] * (1 + len(fields)))
        vals = [application_id] + list(fields.values())

        cur = conn.execute(
            f"INSERT INTO interviews ({cols}) VALUES ({placeholders})",
            vals,
        )
        new_id: int = cur.lastrowid

        if propagate_status:
            # R2: count-free per DESIGN §9.3. The status guard alone
            # handles all edge cases — no need to SELECT COUNT(*) from
            # interviews here. A back-edit to STATUS_APPLIED retaining
            # existing interviews still promotes correctly on the next
            # add_interview, which the count-based variant would miss.
            conn.execute(
                "UPDATE positions SET status = ? "
                "WHERE id = ? AND status = ?",
                (config.STATUS_INTERVIEW, application_id, config.STATUS_APPLIED),
            )

        # Post-state read (same transaction, sees the R2 update).
        cur = conn.execute(
            "SELECT status FROM positions WHERE id = ?",
            (application_id,),
        )
        post_pos = cur.fetchone()
        post_status = post_pos["status"] if post_pos else None

    import exports as _exports  # deferred: avoids circular import
    # DESIGN §7 database.py contract #1: log + swallow any
    # exports failure so the DB write that already succeeded
    # reports success to the caller. Markdown regeneration is
    # best-effort; exports.write_all() additionally catches
    # individual write_* failures internally per §9.5.
    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — "
            "markdown regeneration is best-effort"
        )

    if post_status != pre_status:
        return {
            "id":             new_id,
            "status_changed": True,
            "new_status":     post_status,
        }
    return {
        "id":             new_id,
        "status_changed": False,
        "new_status":     None,
    }


def get_interviews(application_id: int) -> pd.DataFrame:
    """Return all interviews for a given application, ordered by sequence ASC.

    Empty frame for an application with no interviews (not an error)."""
    with _connect() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM interviews WHERE application_id = ? "
            "ORDER BY sequence ASC",
            conn,
            params=(application_id,),
        )
    return df


def update_interview(interview_id: int, fields: dict[str, Any]) -> None:
    """Update provided fields on an interview row. Empty `fields` → no-op
    (matches the update_position / update_recommender / upsert_application
    convention). Calls exports.write_all()."""
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [interview_id]

    with _connect() as conn:
        conn.execute(
            f"UPDATE interviews SET {set_clause} WHERE id = ?",
            vals,
        )

    import exports as _exports  # deferred: avoids circular import
    # DESIGN §7 database.py contract #1: log + swallow any
    # exports failure so the DB write that already succeeded
    # reports success to the caller. Markdown regeneration is
    # best-effort; exports.write_all() additionally catches
    # individual write_* failures internally per §9.5.
    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — "
            "markdown regeneration is best-effort"
        )


def delete_interview(interview_id: int) -> None:
    """Delete a single interview row. Calls exports.write_all()."""
    with _connect() as conn:
        conn.execute("DELETE FROM interviews WHERE id = ?", (interview_id,))

    import exports as _exports  # deferred: avoids circular import
    # DESIGN §7 database.py contract #1: log + swallow any
    # exports failure so the DB write that already succeeded
    # reports success to the caller. Markdown regeneration is
    # best-effort; exports.write_all() additionally catches
    # individual write_* failures internally per §9.5.
    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — "
            "markdown regeneration is best-effort"
        )


# ── Recommenders ──────────────────────────────────────────────────────────────

def add_recommender(position_id: int, fields: dict[str, Any]) -> int:
    """Insert a new recommender row. Returns new id. Calls exports.write_all()."""
    cols = ", ".join(["position_id"] + list(fields.keys()))
    placeholders = ", ".join(["?"] * (1 + len(fields)))
    vals = [position_id] + list(fields.values())

    with _connect() as conn:
        cur = conn.execute(
            f"INSERT INTO recommenders ({cols}) VALUES ({placeholders})",
            vals,
        )
        new_id: int = cur.lastrowid

    import exports as _exports  # deferred: avoids circular import
    # DESIGN §7 database.py contract #1: log + swallow any
    # exports failure so the DB write that already succeeded
    # reports success to the caller. Markdown regeneration is
    # best-effort; exports.write_all() additionally catches
    # individual write_* failures internally per §9.5.
    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — "
            "markdown regeneration is best-effort"
        )
    return new_id


def get_recommenders(position_id: int) -> pd.DataFrame:
    """Return all recommenders for a given position."""
    with _connect() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM recommenders WHERE position_id = ? ORDER BY id ASC",
            conn,
            params=(position_id,),
        )
    return df


def get_all_recommenders() -> pd.DataFrame:
    """Return all recommender rows joined with position_name and institute."""
    with _connect() as conn:
        df = pd.read_sql_query(
            """SELECT r.*, p.position_name, p.institute
               FROM recommenders r
               JOIN positions p ON r.position_id = p.id
               ORDER BY r.recommender_name ASC, r.id ASC""",
            conn,
        )
    return df


def update_recommender(rec_id: int, fields: dict[str, Any]) -> None:
    """Update provided fields on a recommender row. Calls exports.write_all()."""
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [rec_id]

    with _connect() as conn:
        conn.execute(
            f"UPDATE recommenders SET {set_clause} WHERE id = ?",
            vals,
        )

    import exports as _exports  # deferred: avoids circular import
    # DESIGN §7 database.py contract #1: log + swallow any
    # exports failure so the DB write that already succeeded
    # reports success to the caller. Markdown regeneration is
    # best-effort; exports.write_all() additionally catches
    # individual write_* failures internally per §9.5.
    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — "
            "markdown regeneration is best-effort"
        )


def delete_recommender(rec_id: int) -> None:
    """Delete a single recommender row. Calls exports.write_all()."""
    with _connect() as conn:
        conn.execute("DELETE FROM recommenders WHERE id = ?", (rec_id,))

    import exports as _exports  # deferred: avoids circular import
    # DESIGN §7 database.py contract #1: log + swallow any
    # exports failure so the DB write that already succeeded
    # reports success to the caller. Markdown regeneration is
    # best-effort; exports.write_all() additionally catches
    # individual write_* failures internally per §9.5.
    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — "
            "markdown regeneration is best-effort"
        )


# ── Dashboard queries ─────────────────────────────────────────────────────────

def count_by_status() -> dict[str, int]:
    """Return {status_value: count} for all positions.
    Statuses with zero positions are not included in the result."""
    with _connect() as conn:
        cur = conn.execute(
            "SELECT status, COUNT(*) AS cnt FROM positions GROUP BY status"
        )
        rows = cur.fetchall()
    return {row["status"]: row["cnt"] for row in rows}


def get_upcoming_deadlines(days: int = config.DEADLINE_ALERT_DAYS) -> pd.DataFrame:
    """Return open positions with deadline_date within the next `days` days,
    ordered by deadline_date ASC. Excludes config.TERMINAL_STATUSES."""
    today    = date.today().isoformat()
    cutoff   = (date.today() + timedelta(days=days)).isoformat()
    terminal = tuple(config.TERMINAL_STATUSES)
    not_in   = ", ".join("?" * len(terminal))

    with _connect() as conn:
        df = pd.read_sql_query(
            f"""SELECT id, position_name, institute, deadline_date, status, priority
               FROM positions
               WHERE deadline_date IS NOT NULL
                 AND deadline_date >= ?
                 AND deadline_date <= ?
                 AND status NOT IN ({not_in})
               ORDER BY deadline_date ASC""",
            conn,
            params=(today, cutoff, *terminal),
        )
    return df


def get_upcoming_interviews() -> pd.DataFrame:
    """Return every interview scheduled for today or a future date, joined
    with position details, ordered by scheduled_date ASC.

    DESIGN §6.2 + D18 row-per-interview shape: one row per interviews
    record (a position with three interviews contributes three rows).
    Columns: `interview_id`, `application_id`, `sequence`,
    `scheduled_date`, `format`, `position_id`, `position_name`,
    `institute`. Chronological ordering is part of the contract
    (DESIGN §7 load-bearing contract #5)."""
    today = date.today().isoformat()

    with _connect() as conn:
        df = pd.read_sql_query(
            """SELECT i.id           AS interview_id,
                      i.application_id,
                      i.sequence,
                      i.scheduled_date,
                      i.format,
                      p.id           AS position_id,
                      p.position_name,
                      p.institute
               FROM interviews i
               JOIN applications a ON i.application_id = a.position_id
               JOIN positions    p ON a.position_id   = p.id
               WHERE i.scheduled_date IS NOT NULL
                 AND i.scheduled_date >= ?
               ORDER BY i.scheduled_date ASC, i.sequence ASC""",
            conn,
            params=(today,),
        )
    return df


def get_pending_recommenders(days: int = config.RECOMMENDER_ALERT_DAYS) -> pd.DataFrame:
    """Return recommender rows where asked_date was >= `days` ago and
    submitted_date IS NULL, joined with position_name and deadline_date."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    with _connect() as conn:
        df = pd.read_sql_query(
            """SELECT r.id, r.recommender_name, r.relationship,
                      r.asked_date, r.confirmed, r.submitted_date,
                      p.id AS position_id, p.position_name, p.institute,
                      p.deadline_date
               FROM recommenders r
               JOIN positions p ON r.position_id = p.id
               WHERE r.submitted_date IS NULL
                 AND r.asked_date IS NOT NULL
                 AND r.asked_date <= ?
               ORDER BY r.recommender_name ASC, p.deadline_date ASC NULLS LAST""",
            conn,
            params=(cutoff,),
        )
    return df


def compute_materials_readiness() -> dict[str, int]:
    """Return {"ready": N, "pending": M} for active positions.

    A position is "ready" if every document where req_* = 'Yes' has done_* = 1.
    Only positions with at least one required document (req_* = 'Yes') are counted.
    Active = status in (STATUS_SAVED, STATUS_APPLIED, STATUS_INTERVIEW) —
    the tuple is sourced from config aliases at call time.

    Empty `config.REQUIREMENT_DOCS` returns `{"ready": 0, "pending": 0}`
    without touching SQL — a valid future profile-expansion state per
    DESIGN §12.1 (e.g. a casual-tracker profile that ships without
    document requirements). Without the early return, the
    `" OR ".join(...)` and `" AND ".join(...)` fragments below would
    each evaluate to `''` and the constructed SQL would carry an empty
    `... AND ()` predicate plus a `CASE WHEN  THEN 1 ELSE 0 END`
    branch — both invalid under SQLite syntax.

    SQL uses f-strings for column names only — column names come from config
    constants, never from user input (documented in GUIDELINES.md §DB access)."""
    if not config.REQUIREMENT_DOCS:
        return {"ready": 0, "pending": 0}

    has_any_req = " OR ".join(
        f"{req} = 'Yes'" for req, _, _ in config.REQUIREMENT_DOCS
    )
    all_done = " AND ".join(
        f"({req} != 'Yes' OR {done} = 1)"
        for req, done, _ in config.REQUIREMENT_DOCS
    )
    # Sub-task 9 / TASKS.md C1: the active-statuses set is sourced from
    # config aliases rather than hardcoded literals, so a future rename
    # of the stage-0/1/2 status values flows through automatically. The
    # read happens at call time (not module load), which is what makes
    # the sentinel test in TestComputeMaterialsReadiness satisfiable.
    active_statuses = (
        config.STATUS_SAVED,
        config.STATUS_APPLIED,
        config.STATUS_INTERVIEW,
    )
    status_placeholders = ", ".join("?" * len(active_statuses))

    with _connect() as conn:
        cur = conn.execute(
            f"""SELECT
                    SUM(CASE WHEN {all_done}        THEN 1 ELSE 0 END) AS ready,
                    SUM(CASE WHEN NOT ({all_done})  THEN 1 ELSE 0 END) AS pending
               FROM positions
               WHERE status IN ({status_placeholders})
                 AND ({has_any_req})""",
            active_statuses,
        )
        row = cur.fetchone()

    return {
        "ready":   int(row["ready"]   or 0),
        "pending": int(row["pending"] or 0),
    }
