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
from typing import Generator
import sqlite3
import pandas as pd

import config

DB_PATH: Path = Path(__file__).parent / "postdoc.db"


# ── Connection ────────────────────────────────────────────────────────────────

@contextmanager
def _connect() -> Generator[sqlite3.Connection, None, None]:
    """Open a connection with row_factory and foreign keys enabled.
    Commits on clean exit; rolls back and re-raises on exception."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
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
    req_done_cols = ""
    for req_col, done_col, _ in config.REQUIREMENT_DOCS:
        req_done_cols += f",\n    {req_col:<30} TEXT    DEFAULT 'N'"
        req_done_cols += f",\n    {done_col:<30} INTEGER DEFAULT 0"

    with _connect() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS positions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                status           TEXT    NOT NULL DEFAULT '[OPEN]',
                priority         TEXT,
                created_at       TEXT    DEFAULT (date('now')),
                position_name    TEXT    NOT NULL,
                institute        TEXT,
                location         TEXT,
                field            TEXT,
                deadline_date    TEXT,
                deadline_note    TEXT,
                stipend          TEXT,
                work_auth        TEXT,
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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                position_id          INTEGER PRIMARY KEY,
                applied_date         TEXT,
                all_recs_submitted   TEXT,
                confirmation_email   TEXT,
                response_date        TEXT,
                response_type        TEXT,
                interview1_date      TEXT,
                interview2_date      TEXT,
                result_notify_date   TEXT,
                result               TEXT    DEFAULT 'Pending',
                notes                TEXT,
                FOREIGN KEY (position_id) REFERENCES positions(id) ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS recommenders (
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

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_positions_status   ON positions(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_positions_deadline ON positions(deadline_date)"
        )

        # Migration: add any REQUIREMENT_DOCS columns missing from the live schema.
        cur = conn.execute("PRAGMA table_info(positions)")
        existing_cols = {row["name"] for row in cur.fetchall()}
        for req_col, done_col, _ in config.REQUIREMENT_DOCS:
            if req_col not in existing_cols:
                conn.execute(
                    f"ALTER TABLE positions ADD COLUMN {req_col} TEXT DEFAULT 'N'"
                )
            if done_col not in existing_cols:
                conn.execute(
                    f"ALTER TABLE positions ADD COLUMN {done_col} INTEGER DEFAULT 0"
                )


# ── Positions ─────────────────────────────────────────────────────────────────

def add_position(fields: dict) -> int:
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
    _exports.write_all()
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


def update_position(position_id: int, fields: dict) -> None:
    """Update provided fields on an existing position. Calls exports.write_all()."""
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [position_id]

    with _connect() as conn:
        conn.execute(
            f"UPDATE positions SET {set_clause} WHERE id = ?",
            vals,
        )

    import exports as _exports  # deferred: avoids circular import
    _exports.write_all()


def delete_position(position_id: int) -> None:
    """Delete position and cascade-delete its application + recommender rows.
    Calls exports.write_all()."""
    with _connect() as conn:
        conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))

    import exports as _exports  # deferred: avoids circular import
    _exports.write_all()


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


def upsert_application(position_id: int, fields: dict) -> None:
    """INSERT or UPDATE the application row for a position.
    applications.position_id is the primary key — ON CONFLICT handles the upsert.
    Calls exports.write_all()."""
    cols = ", ".join(["position_id"] + list(fields.keys()))
    placeholders = ", ".join(["?"] * (1 + len(fields)))
    set_clause = ", ".join(f"{k} = excluded.{k}" for k in fields)
    vals = [position_id] + list(fields.values())

    with _connect() as conn:
        conn.execute(
            f"""INSERT INTO applications ({cols}) VALUES ({placeholders})
                ON CONFLICT(position_id) DO UPDATE SET {set_clause}""",
            vals,
        )

    import exports as _exports  # deferred: avoids circular import
    _exports.write_all()


# ── Recommenders ──────────────────────────────────────────────────────────────

def add_recommender(position_id: int, fields: dict) -> int:
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
    _exports.write_all()
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


def update_recommender(rec_id: int, fields: dict) -> None:
    """Update provided fields on a recommender row. Calls exports.write_all()."""
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [rec_id]

    with _connect() as conn:
        conn.execute(
            f"UPDATE recommenders SET {set_clause} WHERE id = ?",
            vals,
        )

    import exports as _exports  # deferred: avoids circular import
    _exports.write_all()


def delete_recommender(rec_id: int) -> None:
    """Delete a single recommender row. Calls exports.write_all()."""
    with _connect() as conn:
        conn.execute("DELETE FROM recommenders WHERE id = ?", (rec_id,))

    import exports as _exports  # deferred: avoids circular import
    _exports.write_all()


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
    ordered by deadline_date ASC. Excludes CLOSED, REJECTED, DECLINED."""
    today  = date.today().isoformat()
    cutoff = (date.today() + timedelta(days=days)).isoformat()

    with _connect() as conn:
        df = pd.read_sql_query(
            """SELECT id, position_name, institute, deadline_date, status, priority
               FROM positions
               WHERE deadline_date IS NOT NULL
                 AND deadline_date >= ?
                 AND deadline_date <= ?
                 AND status NOT IN (?, ?, ?)
               ORDER BY deadline_date ASC""",
            conn,
            params=(today, cutoff, "[CLOSED]", "[REJECTED]", "[DECLINED]"),
        )
    return df


def get_upcoming_interviews() -> pd.DataFrame:
    """Return rows where interview1_date or interview2_date is today or future,
    joined with position details, ordered by interview1_date ASC."""
    today = date.today().isoformat()

    with _connect() as conn:
        df = pd.read_sql_query(
            """SELECT p.id, p.position_name, p.institute,
                      a.interview1_date, a.interview2_date
               FROM applications a
               JOIN positions p ON a.position_id = p.id
               WHERE (a.interview1_date IS NOT NULL AND a.interview1_date >= ?)
                  OR (a.interview2_date IS NOT NULL AND a.interview2_date >= ?)
               ORDER BY a.interview1_date ASC NULLS LAST,
                        a.interview2_date ASC NULLS LAST""",
            conn,
            params=(today, today),
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

    A position is "ready" if every document where req_* = 'Y' has done_* = 1.
    Only positions with at least one required document (req_* = 'Y') are counted.
    Active = status in ([OPEN], [APPLIED], [INTERVIEW]).

    SQL uses f-strings for column names only — column names come from config
    constants, never from user input (documented in GUIDELINES.md §DB access)."""
    has_any_req = " OR ".join(
        f"{req} = 'Y'" for req, _, _ in config.REQUIREMENT_DOCS
    )
    all_done = " AND ".join(
        f"({req} != 'Y' OR {done} = 1)"
        for req, done, _ in config.REQUIREMENT_DOCS
    )
    active_statuses = ("[OPEN]", "[APPLIED]", "[INTERVIEW]")
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
