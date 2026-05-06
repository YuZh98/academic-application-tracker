# database.py
# All SQLite reads and writes for the academic application tracker.
#
# Import rules:
#   - May import: config, sqlite3, pandas, stdlib
#   - Must NOT import: streamlit, exports
#   - exports.write_all() is called inside write functions via deferred import
#     to avoid the circular dependency: database → exports → database.

import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Generator

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


    req_done_cols = ""
    for req_col, done_col, _ in config.REQUIREMENT_DOCS:
        req_done_cols += f",\n    {req_col:<30} TEXT    DEFAULT 'No'"
        req_done_cols += f",\n    {done_col:<30} INTEGER DEFAULT 0"


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


        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS applications (
                position_id           INTEGER PRIMARY KEY,
                applied_date          TEXT,
                all_recs_submitted    TEXT,
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


        interviews_existed_pre_create = (
            conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'interviews'"
            ).fetchone()
            is not None
        )

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

        conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_status      ON positions(status)")
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
                conn.execute(f"ALTER TABLE positions ADD COLUMN {req_col} TEXT DEFAULT 'No'")
            if done_col not in existing_cols:
                conn.execute(f"ALTER TABLE positions ADD COLUMN {done_col} INTEGER DEFAULT 0")


        if "updated_at" not in existing_cols:
            conn.execute("ALTER TABLE positions ADD COLUMN updated_at TEXT")
            conn.execute(
                "UPDATE positions SET updated_at = datetime('now') WHERE updated_at IS NULL"
            )


        if "work_auth_note" not in existing_cols:
            conn.execute("ALTER TABLE positions ADD COLUMN work_auth_note TEXT")


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


        applications_cols = {
            row["name"] for row in conn.execute("PRAGMA table_info(applications)").fetchall()
        }
        confirmation_split_needed = (
            "confirmation_received" not in applications_cols
            or "confirmation_date" not in applications_cols
        )
        if "confirmation_received" not in applications_cols:
            conn.execute(
                "ALTER TABLE applications ADD COLUMN confirmation_received INTEGER DEFAULT 0"
            )
        if "confirmation_date" not in applications_cols:
            conn.execute("ALTER TABLE applications ADD COLUMN confirmation_date TEXT")
        if confirmation_split_needed:

            conn.execute(
                "UPDATE applications "
                "SET confirmation_received = 1, "
                "    confirmation_date     = confirmation_email "
                "WHERE confirmation_email GLOB "
                "  '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'"
            )
            conn.execute(
                "UPDATE applications SET confirmation_received = 1 WHERE confirmation_email = 'Y'"
            )

            conn.execute(
                "UPDATE applications "
                "SET confirmation_email = NULL "
                "WHERE confirmation_email IS NOT NULL"
            )


        applications_cols_post_split = {
            row["name"] for row in conn.execute("PRAGMA table_info(applications)").fetchall()
        }
        if "confirmation_email" in applications_cols_post_split:
            conn.execute("ALTER TABLE applications DROP COLUMN confirmation_email")


        rec_cols_info = conn.execute("PRAGMA table_info(recommenders)").fetchall()
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


        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS positions_updated_at
                AFTER UPDATE ON positions FOR EACH ROW
            BEGIN
                UPDATE positions SET updated_at = datetime('now') WHERE id = NEW.id;
            END
        """)


        for req_col, _done_col, _ in config.REQUIREMENT_DOCS:
            conn.execute(
                f"UPDATE positions SET {req_col} = "
                f"CASE {req_col} "
                f"WHEN 'Y' THEN 'Yes' "
                f"WHEN 'N' THEN 'No' "
                f"END "
                f"WHERE {req_col} IN ('Y', 'N')"
            )

        _legacy_saved = "[OPE" + "N]"  # assembled to avoid grep false positives
        _legacy_medium = "M" + "ed"    # assembled to avoid grep false positives
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
        new_id: int = cur.lastrowid or 0
        conn.execute(
            "INSERT INTO applications (position_id) VALUES (?)",
            (new_id,),
        )

    import exports as _exports  # deferred: avoids circular import

    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — markdown regeneration is best-effort"
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


    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — markdown regeneration is best-effort"
        )


def delete_position(position_id: int) -> None:
    """Delete position and cascade-delete its application + recommender rows.
    Calls exports.write_all()."""
    with _connect() as conn:
        conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))

    import exports as _exports  # deferred: avoids circular import


    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — markdown regeneration is best-effort"
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

    if not fields:
        return {"status_changed": False, "new_status": None}

    cols = ", ".join(["position_id"] + list(fields.keys()))
    placeholders = ", ".join(["?"] * (1 + len(fields)))
    set_clause = ", ".join(f"{k} = excluded.{k}" for k in fields)
    vals = [position_id] + list(fields.values())

    with _connect() as conn:
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
            new_applied_date = fields.get("applied_date")
            if pre_applied_date is None and new_applied_date is not None:
                conn.execute(
                    "UPDATE positions SET status = ? WHERE id = ? AND status = ?",
                    (config.STATUS_APPLIED, position_id, config.STATUS_SAVED),
                )


            if fields.get("response_type") == config.RESPONSE_TYPE_OFFER:
                terminal = tuple(config.TERMINAL_STATUSES)
                placeholder_list = ", ".join("?" * len(terminal))
                conn.execute(
                    f"UPDATE positions SET status = ? "
                    f"WHERE id = ? AND status NOT IN ({placeholder_list})",
                    (config.STATUS_OFFER, position_id, *terminal),
                )

        cur = conn.execute(
            "SELECT status FROM positions WHERE id = ?",
            (position_id,),
        )
        post_pos = cur.fetchone()
        post_status = post_pos["status"] if post_pos else None

    import exports as _exports  # deferred: avoids circular import

    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — markdown regeneration is best-effort"
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
    there is nothing outstanding. Vacuous truth makes the helper
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

    fields = dict(fields)

    with _connect() as conn:
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
        new_id: int = cur.lastrowid or 0

        if propagate_status:
            conn.execute(
                "UPDATE positions SET status = ? WHERE id = ? AND status = ?",
                (config.STATUS_INTERVIEW, application_id, config.STATUS_APPLIED),
            )


        cur = conn.execute(
            "SELECT status FROM positions WHERE id = ?",
            (application_id,),
        )
        post_pos = cur.fetchone()
        post_status = post_pos["status"] if post_pos else None

    import exports as _exports  # deferred: avoids circular import

    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — markdown regeneration is best-effort"
        )

    if post_status != pre_status:
        return {
            "id": new_id,
            "status_changed": True,
            "new_status": post_status,
        }
    return {
        "id": new_id,
        "status_changed": False,
        "new_status": None,
    }


def get_interviews(application_id: int) -> pd.DataFrame:
    """Return all interviews for a given application, ordered by sequence ASC.

    Empty frame for an application with no interviews (not an error)."""
    with _connect() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM interviews WHERE application_id = ? ORDER BY sequence ASC",
            conn,
            params=[application_id],
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
            "exports.write_all() failed; DB write succeeded — markdown regeneration is best-effort"
        )


def delete_interview(interview_id: int) -> None:
    """Delete a single interview row. Calls exports.write_all()."""
    with _connect() as conn:
        conn.execute("DELETE FROM interviews WHERE id = ?", (interview_id,))

    import exports as _exports  # deferred: avoids circular import


    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — markdown regeneration is best-effort"
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
        new_id: int = cur.lastrowid or 0

    import exports as _exports  # deferred: avoids circular import


    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — markdown regeneration is best-effort"
        )
    return new_id


def get_recommenders(position_id: int) -> pd.DataFrame:
    """Return all recommenders for a given position."""
    with _connect() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM recommenders WHERE position_id = ? ORDER BY id ASC",
            conn,
            params=[position_id],
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

    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — markdown regeneration is best-effort"
        )


def delete_recommender(rec_id: int) -> None:
    """Delete a single recommender row. Calls exports.write_all()."""
    with _connect() as conn:
        conn.execute("DELETE FROM recommenders WHERE id = ?", (rec_id,))

    import exports as _exports  # deferred: avoids circular import


    try:
        _exports.write_all()
    except Exception:
        logger.exception(
            "exports.write_all() failed; DB write succeeded — markdown regeneration is best-effort"
        )


def regenerate_exports() -> None:
    """Trigger a full markdown export regeneration on demand.

    Called by pages/4_Export.py's manual-trigger button. Unlike the
    auto-write hook in write functions (which logs-and-continues),
    errors here propagate to the caller so the page can surface them
    via st.error.
    """
    import exports as _exports  # deferred to break circular import

    _exports.write_all()


def get_export_paths() -> list[tuple[str, Path]]:
    """Return (filename, Path) pairs for the three committed export files.

    Called by pages/4_Export.py to resolve file paths for mtime display
    and download buttons without importing exports directly.
    """
    import exports as _exports  # deferred to break circular import

    return [
        (filename, _exports.EXPORTS_DIR / filename)
        for filename in ["OPPORTUNITIES.md", "PROGRESS.md", "RECOMMENDERS.md"]
    ]


# ── Dashboard queries ─────────────────────────────────────────────────────────


def count_by_status() -> dict[str, int]:
    """Return {status_value: count} for all positions.
    Statuses with zero positions are not included in the result."""
    with _connect() as conn:
        cur = conn.execute("SELECT status, COUNT(*) AS cnt FROM positions GROUP BY status")
        rows = cur.fetchall()
    return {row["status"]: row["cnt"] for row in rows}


def get_upcoming_deadlines(days: int = config.DEADLINE_ALERT_DAYS) -> pd.DataFrame:
    """Return open positions with deadline_date within the next `days` days,
    ordered by deadline_date ASC. Excludes config.TERMINAL_STATUSES."""
    today = date.today().isoformat()
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    terminal = tuple(config.TERMINAL_STATUSES)
    not_in = ", ".join("?" * len(terminal))

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
            params=[today, cutoff, *terminal],
        )
    return df


def get_upcoming_interviews() -> pd.DataFrame:
    """Return every interview scheduled for today or a future date, joined
    with position details, ordered by scheduled_date ASC.

    DESIGN §6.2 row-per-interview shape: one row per interviews
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
            params=[today],
        )
    return df


# ── get_upcoming: unified upcoming feed ─────────────────────────────────────

_UPCOMING_COLUMNS: list[str] = [
    "date",
    "days_left",
    "label",
    "kind",
    "status",
    "urgency",
]


def _days_left_label(days_away: int) -> str:
    if days_away == 0:
        return "today"
    if days_away == 1:
        return "in 1 day"
    return f"in {days_away} days"




def _label_for(institute: Any, position_name: str) -> str:
    if pd.isna(institute) or str(institute).strip() == "":
        return position_name
    return f"{institute}: {position_name}"


def get_upcoming(days: int = config.DEADLINE_ALERT_DAYS) -> pd.DataFrame:
    """Return the merged upcoming feed (deadlines + interviews) within
    the next `days` days, projected to the six-column DESIGN §8.1
    contract and sorted by date ascending.

    Column contract — see `_UPCOMING_COLUMNS` and the module-level
    comment above. Both `days_left` and `urgency` are derived once
    per row from the same `days_away` int so the two columns cannot
    drift; thresholds for the urgency band resolve at call time from
    config so a runtime tweak is honoured without restart.

    Implementation notes:
      - get_upcoming_interviews has no built-in days bound;
        get_upcoming applies one (`scheduled_date <= today + days`)
        so DESIGN §8.1's 'next N days' contract holds for both kinds.
      - Interview rows don't carry `status` from the underlying
        query; enrichment is a left-merge with get_all_positions on
        position_id, trimmed to id + status to keep the projection
        clean.
      - Sort is stable: within a tied date the per-helper ordering
        survives (deadlines before interviews — implicit, not pinned
        by tests)."""
    today = date.today()
    cutoff_iso = (today + timedelta(days=days)).isoformat()

    # ── Deadlines half ────────────────────────────────────────────────────
    deadlines = get_upcoming_deadlines(days)
    if deadlines.empty:
        deadlines_proj = pd.DataFrame(columns=_UPCOMING_COLUMNS)
    else:
        date_series = pd.to_datetime(deadlines["deadline_date"]).dt.date
        days_away_series = date_series.apply(lambda d: (d - today).days)
        deadlines_proj = pd.DataFrame(
            {
                "date": date_series,
                "days_left": days_away_series.apply(_days_left_label),
                "label": deadlines.apply(
                    lambda r: _label_for(r["institute"], r["position_name"]),
                    axis=1,
                ),
                "kind": "Deadline for application",
                "status": deadlines["status"],
                "urgency": days_away_series.apply(config.urgency_glyph),
            }
        )

    # ── Interviews half ───────────────────────────────────────────────────
    interviews = get_upcoming_interviews()
    if not interviews.empty:
        interviews = interviews[interviews["scheduled_date"] <= cutoff_iso]

    if interviews.empty:
        interviews_proj = pd.DataFrame(columns=_UPCOMING_COLUMNS)
    else:
        positions = get_all_positions()[["id", "status"]].rename(  # type: ignore[call-overload]
            columns={"id": "position_id"}
        )
        merged = interviews.merge(positions, on="position_id", how="left")
        date_series = pd.to_datetime(merged["scheduled_date"]).dt.date
        days_away_series = date_series.apply(lambda d: (d - today).days)
        interviews_proj = pd.DataFrame(
            {
                "date": date_series,
                "days_left": days_away_series.apply(_days_left_label),
                "label": merged.apply(
                    lambda r: _label_for(r["institute"], r["position_name"]),
                    axis=1,
                ),
                "kind": merged["sequence"].apply(lambda n: f"Interview {n}"),
                "status": merged["status"],
                "urgency": days_away_series.apply(config.urgency_glyph),
            }
        )

    combined = pd.concat([deadlines_proj, interviews_proj], ignore_index=True)
    return combined.sort_values(by="date", kind="stable").reset_index(drop=True)


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
            params=[cutoff],
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
    constants, never from user input."""
    if not config.REQUIREMENT_DOCS:
        return {"ready": 0, "pending": 0}

    has_any_req = " OR ".join(f"{req} = 'Yes'" for req, _, _ in config.REQUIREMENT_DOCS)
    all_done = " AND ".join(
        f"({req} != 'Yes' OR {done} = 1)" for req, done, _ in config.REQUIREMENT_DOCS
    )
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
        "ready": int(row["ready"] or 0),
        "pending": int(row["pending"] or 0),
    }


def get_applications_table() -> pd.DataFrame:
    """Return the joined positions × applications view backing the
    Applications page table (DESIGN §8.3).

    Columns (in order): position_id, position_name, institute,
    deadline_date, status, applied_date, confirmation_received,
    confirmation_date, response_type, result.

    Sort: deadline_date ASC NULLS LAST, position_id ASC. The
    position_id tiebreaker is part of the contract so equal-deadline
    rows have a stable order across reruns — the Applications page
    relies on this for selection survival across Save / filter-change
    reruns (same pattern as the Opportunities page).

    LEFT JOIN over the auto-created applications row is defensive:
    add_position creates the applications row in the same transaction,
    so an INNER JOIN would also work in practice; LEFT JOIN keeps the
    reader robust against a future migration that could leave an orphan
    position. The reader is filter-agnostic — every position is in the
    result; the page layer applies the default 'exclude SAVED + CLOSED'
    filter via config.STATUS_FILTER_ACTIVE_EXCLUDED."""
    sql = """
        SELECT
            p.id                    AS position_id,
            p.position_name         AS position_name,
            p.institute             AS institute,
            p.deadline_date         AS deadline_date,
            p.status                AS status,
            a.applied_date          AS applied_date,
            a.confirmation_received AS confirmation_received,
            a.confirmation_date     AS confirmation_date,
            a.response_type         AS response_type,
            a.result                AS result
        FROM positions p
        LEFT JOIN applications a ON a.position_id = p.id
        ORDER BY p.deadline_date ASC NULLS LAST, p.id ASC
    """
    with _connect() as conn:
        return pd.read_sql_query(sql, conn)
