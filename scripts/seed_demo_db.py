"""Seed a throwaway SQLite database with fabricated demo data.

Two entry points:

- ``seed(conn)``: library entry used by ``db_session.py`` during demo
  bootstrap. Populates an already-open connection. Asserts the DB is
  empty before inserting.

- ``main()``: CLI entry used for screenshot generation. Resolves a
  file path via ``AAT_DB_PATH`` (default: ``./demo.db``), wipes +
  initializes + seeds against the file.

The module body has zero side effects — no path manipulation, no env
mutation, no module-level reloads. ``db_session.py`` imports this
module at load time and must not pay any of those costs.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

# Path-only setup so the module can be imported from anywhere (CLI from
# repo root, library import from db_session). NOT an env mutation — see
# the module docstring and tests/test_seed_demo_db.py::TestModuleImport.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import config  # noqa: E402
import database  # noqa: E402


def iso(days_offset: int) -> str:
    return (date.today() + timedelta(days=days_offset)).isoformat()


def seed(conn: sqlite3.Connection) -> None:
    """Populate the demo dataset.

    The ``conn`` argument is a lifetime witness — the caller must hold a
    reference to keep an in-memory DB alive. Every write inside this
    function routes through ``database.add_position`` etc., which use
    ``database._connect()``, which in demo mode (provider installed)
    returns the same ``conn`` back. In CLI mode the public API opens
    its own file connections per call; the passed ``conn`` is unused
    once the emptiness check returns.

    Raises ``RuntimeError`` if the positions table is not empty.
    """
    row = conn.execute("SELECT COUNT(*) AS n FROM positions").fetchone()
    if row["n"] != 0:
        raise RuntimeError("seed_demo_db.seed() refused: positions table is not empty")
    _seed_body()


def _seed_body() -> None:
    """The actual inserts. Extracted so ``seed(conn)`` can guard
    emptiness before mutating, and ``main()`` can call after its own
    wipe + init dance.

    Task 6 expands this dataset to 18 positions across 2 cycles
    covering all 7 statuses; the body here is the v0.13 baseline.
    """
    # 1. Stanford BioStats — APPLIED, materials all ready, urgent deadline.
    sid = database.add_position(
        {
            "position_name": "Postdoc in Biostatistics",
            "institute": "Stanford University",
            "field": "Biostatistics",
            "deadline_date": iso(5),
            "priority": "High",
            "link": "https://example.org/stanford-biostats",
            "location": "Stanford, CA",
            "source": "AcademicJobsOnline",
            "req_cv": "Yes",
            "done_cv": 1,
            "req_cover_letter": "Yes",
            "done_cover_letter": 1,
            "req_research_statement": "Yes",
            "done_research_statement": 1,
            "req_rec_letters": "Yes",
            "num_rec_letters": 3,
        }
    )
    database.upsert_application(
        sid,
        {"applied_date": iso(-12), "response_type": "Acknowledgement"},
        propagate_status=True,
    )
    database.add_recommender(
        sid,
        {
            "recommender_name": "Dr. Anna Park",
            "relationship": "PhD Advisor",
            "asked_date": iso(-18),
            "confirmed": 1,
            "submitted_date": iso(-5),
        },
    )
    database.add_recommender(
        sid,
        {
            "recommender_name": "Dr. Marcus Hale",
            "relationship": "Committee Member",
            "asked_date": iso(-18),
            "confirmed": 1,
            "submitted_date": iso(-3),
        },
    )
    database.add_recommender(
        sid,
        {
            "recommender_name": "Dr. Priya Patel",
            "relationship": "Committee Member",
            "asked_date": iso(-10),
            "confirmed": 1,
            "submitted_date": None,
        },
    )

    # 2. MIT CSAIL — INTERVIEW (auto-promoted via add_interview cascade).
    mid = database.add_position(
        {
            "position_name": "Postdoc in Machine Learning",
            "institute": "Massachusetts Institute of Technology",
            "field": "Machine Learning",
            "deadline_date": iso(15),
            "priority": "High",
            "link": "https://example.org/mit-csail",
            "location": "Cambridge, MA",
            "source": "Lab website",
            "req_cv": "Yes",
            "done_cv": 1,
            "req_research_statement": "Yes",
            "done_research_statement": 0,
            "req_teaching_statement": "Yes",
            "done_teaching_statement": 0,
        }
    )
    database.upsert_application(
        mid,
        {"applied_date": iso(-25), "response_type": "Interview Invite"},
        propagate_status=True,
    )
    database.add_interview(
        mid,
        {
            "sequence": 1,
            "scheduled_date": iso(8),
            "format": "Video",
            "notes": "First-round chat with the PI.",
        },
        propagate_status=True,
    )
    database.add_recommender(
        mid,
        {
            "recommender_name": "Dr. Anna Park",
            "relationship": "PhD Advisor",
            "asked_date": iso(-25),
            "confirmed": 1,
            "submitted_date": iso(-10),
        },
    )

    # 3. UC Berkeley — OFFER (R3 cascade).
    bid = database.add_position(
        {
            "position_name": "Postdoc in Statistical Genomics",
            "institute": "University of California, Berkeley",
            "field": "Statistical Genomics",
            "priority": "Medium",
            "location": "Berkeley, CA",
            "req_cv": "Yes",
            "done_cv": 1,
            "req_cover_letter": "Yes",
            "done_cover_letter": 1,
        }
    )
    database.upsert_application(
        bid,
        {"applied_date": iso(-40), "response_type": config.RESPONSE_TYPE_OFFER},
        propagate_status=True,
    )

    # 4. Princeton — SAVED, materials still pending, deadline 22 days out.
    database.add_position(
        {
            "position_name": "Postdoc in Bayesian Methods",
            "institute": "Princeton University",
            "field": "Bayesian Statistics",
            "deadline_date": iso(22),
            "priority": "Medium",
            "link": "https://example.org/princeton-stats",
            "location": "Princeton, NJ",
            "source": "HigherEdJobs",
            "req_cv": "Yes",
            "done_cv": 0,
            "req_research_statement": "Yes",
            "done_research_statement": 0,
        }
    )

    # 5. Harvard — SAVED, far deadline (only visible in the 60/90-day window).
    database.add_position(
        {
            "position_name": "Postdoc in Causal Inference",
            "institute": "Harvard University",
            "field": "Causal Inference",
            "deadline_date": iso(50),
            "priority": "Stretch",
            "source": "Listserv",
        }
    )


def wipe(path) -> None:
    """Delete all rows from the demo DB file. Existing behavior preserved."""
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return
    with sqlite3.connect(p) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        for table in ("recommenders", "interviews", "applications", "positions"):
            try:
                conn.execute(f"DELETE FROM {table}")
            except sqlite3.OperationalError:
                # Schema not yet present — init_db() will create it.
                pass
        conn.commit()


def main() -> None:
    """CLI entry — preserves the existing screenshot-generation workflow.

    Resolves AAT_DB_PATH at call time (no module-level mutation),
    reloads config + database so DB_PATH picks up the override, then
    wipes + inits + seeds against the resolved file path.
    """
    import importlib
    import os

    if "AAT_DB_PATH" not in os.environ:
        os.environ["AAT_DB_PATH"] = str((_REPO_ROOT / "demo.db").resolve())

    # Order matters: config first (database reads from config), then
    # database (so DB_PATH picks up the env override).
    importlib.reload(config)
    importlib.reload(database)

    db_path = database.DB_PATH
    print(f"Seeding demo database at {db_path}")
    wipe(Path(db_path))
    database.init_db()
    _seed_body()

    print()
    print("=== Demo DB summary ===")
    print(f"  Status counts:    {database.count_by_status()}")
    print(f"  Pending recs:     {len(database.get_pending_recommenders())} rows")
    print(f"  Upcoming (30d):   {len(database.get_upcoming(days=30))} rows")
    print(f"  Materials ready:  {database.compute_materials_readiness()}")
    print()
    print("Run the app against this DB with:")
    print(f"  AAT_DB_PATH={db_path} streamlit run app.py")


if __name__ == "__main__":
    main()
