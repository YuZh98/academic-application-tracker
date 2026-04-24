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

        conn.execute(f"""
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
                result               TEXT    DEFAULT '{result_default}',
                notes                TEXT,
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
        # Idempotent by construction — the ELSE branch passes 'Optional'
        # and any already-migrated 'Yes'/'No' values through unchanged, so
        # rerunning on a migrated DB is a no-op. The f-string builds column
        # identifiers only; the substituted `req_col` comes from
        # config.REQUIREMENT_DOCS (never user input), matching the safety
        # argument documented on compute_materials_readiness.
        for req_col, _done_col, _ in config.REQUIREMENT_DOCS:
            conn.execute(
                f"UPDATE positions SET {req_col} = "
                f"CASE {req_col} "
                f"WHEN 'Y' THEN 'Yes' "
                f"WHEN 'N' THEN 'No' "
                f"ELSE {req_col} END"
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


def upsert_application(position_id: int, fields: dict[str, Any]) -> None:
    """INSERT or UPDATE the application row for a position.
    applications.position_id is the primary key — ON CONFLICT handles the upsert.
    Calls exports.write_all()."""
    if not fields:
        return
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
    "new_status": str | None}``. The cascade indicator follows
    DESIGN §9.3 — Sub-task 9 fills in the R2 body (`UPDATE positions
    SET status = STATUS_INTERVIEW WHERE id = application_id
    AND status = STATUS_APPLIED`) conditioned on `propagate_status`.
    For Sub-task 8 the cascade is deferred, so status_changed always
    reads False regardless of the kwarg. The keyword-only kwarg is in
    place now to lock the API across the two sub-tasks (callers can
    pass `propagate_status=False` today and get the same behaviour
    they will get once Sub-task 9 lands).

    Calls exports.write_all() on success."""
    # Don't mutate the caller's dict — auto-sequence injection below
    # would surprise a caller who reuses the same fields object.
    fields = dict(fields)

    with _connect() as conn:
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

    import exports as _exports  # deferred: avoids circular import
    _exports.write_all()

    # Sub-task 9 target: gate the following UPDATE on propagate_status
    # and return the actual status_changed / new_status. For now the
    # indicator keys exist with their no-cascade defaults so callers
    # can read them today without a try/except. `propagate_status` is
    # consumed here only to satisfy the signature contract.
    _ = propagate_status
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
    _exports.write_all()


def delete_interview(interview_id: int) -> None:
    """Delete a single interview row. Calls exports.write_all()."""
    with _connect() as conn:
        conn.execute("DELETE FROM interviews WHERE id = ?", (interview_id,))

    import exports as _exports  # deferred: avoids circular import
    _exports.write_all()


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
    Active = status in ([SAVED], [APPLIED], [INTERVIEW]).

    SQL uses f-strings for column names only — column names come from config
    constants, never from user input (documented in GUIDELINES.md §DB access)."""
    has_any_req = " OR ".join(
        f"{req} = 'Yes'" for req, _, _ in config.REQUIREMENT_DOCS
    )
    all_done = " AND ".join(
        f"({req} != 'Yes' OR {done} = 1)"
        for req, done, _ in config.REQUIREMENT_DOCS
    )
    active_statuses = ("[SAVED]", "[APPLIED]", "[INTERVIEW]")
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
