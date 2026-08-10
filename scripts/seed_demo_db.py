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
    ``database._connect()``, which resolves the installed provider and
    returns the same ``conn`` back.

    Raises ``RuntimeError`` if no connection provider is installed, if
    the passed ``conn`` is not the same object the provider returns, or
    if the positions table is not empty.
    """
    # Fail-fast: the emptiness check below uses the passed conn, while
    # every write inside _seed_body() routes through database._connect()
    # → database._connection_provider(). If those two connections are
    # not the same object, the emptiness check would pass on one DB
    # while writes hit another. Refuse loudly instead of producing
    # silently-wrong state.
    if database._connection_provider is None:
        raise RuntimeError(
            "seed_demo_db.seed() requires database.set_connection_provider() "
            "to be installed first; writes route through database._connect() "
            "and need a provider to reach the same DB as the emptiness check."
        )
    provider_conn = database._connection_provider()
    if conn is not provider_conn:
        raise RuntimeError(
            "seed_demo_db.seed(conn): the conn argument must be the same "
            "object the installed provider returns. Got a different connection "
            "object — emptiness check would pass on one DB while writes hit "
            "another. Either pass the provider's connection or restructure "
            "the caller to install the provider with the same conn."
        )

    row = conn.execute("SELECT COUNT(*) AS n FROM positions").fetchone()
    if row["n"] != 0:
        raise RuntimeError("seed_demo_db.seed() refused: positions table is not empty")
    _seed_body()


def _seed_body() -> None:
    """Insert the 19-position multi-cycle demo dataset.

    Status mix (covers all 7 statuses): 4 SAVED, 4 APPLIED,
    3 INTERVIEW, 2 OFFER, 2 CLOSED, 3 REJECTED, 1 DECLINED = 19.

    Across two application cycles (2025-26 + 2026-27). Hits every
    alert panel — looming deadlines (7-day + 30-day), a far deadline
    visible only in the 60/90-day Upcoming windows, every priority
    value including Stretch, pending recommender letters past the
    asked-window, the NULL-recommender fallback, the R1/R2/R3 cascade
    trails (applied → interview → offer).

    All institutes are well-known public/private universities or
    research labs; every recommender name is fabricated.
    """
    # ── SAVED (3) — open opportunities not yet applied ────────────
    # 1 urgent (7-day vermilion band) — also carries the past-window recommender
    sid_saved_urgent = database.add_position(
        {
            "position_name": "Postdoc — Statistical Genomics",
            "institute": "Stanford University",
            "field": "Biostatistics",
            "deadline_date": iso(5),
            "priority": "High",
            "link": "https://example.org/stanford-genomics",
            "location": "Stanford, CA",
            "source": "AcademicJobsOnline",
            "status": config.STATUS_SAVED,
            "req_cv": "Yes",
            "done_cv": 1,
            "req_research_statement": "Yes",
            "done_research_statement": 0,
        }
    )

    # 2 in the 30-day cobalt band
    database.add_position(
        {
            "position_name": "Postdoc — Causal Inference",
            "institute": "University of Pennsylvania",
            "field": "Epidemiology",
            "deadline_date": iso(20),
            "priority": "High",
            "status": config.STATUS_SAVED,
            "req_cv": "Yes",
            "done_cv": 1,
            "req_cover_letter": "Yes",
            "done_cover_letter": 0,
        }
    )
    database.add_position(
        {
            "position_name": "Assistant Professor — Statistics",
            "institute": "University of Michigan",
            "field": "Statistics",
            "deadline_date": iso(28),
            "priority": "Medium",
            "status": config.STATUS_SAVED,
        }
    )

    # 1 far-out Stretch — deadline beyond the default 30-day window so
    # the Upcoming panel's 60/90-day selector visibly changes the list,
    # and the Stretch priority filter matches at least one row.
    database.add_position(
        {
            "position_name": "Postdoc — Machine Learning Theory",
            "institute": "ETH Zürich",
            "field": "Machine Learning",
            "deadline_date": iso(50),
            "priority": "Stretch",
            "link": "https://example.org/eth-ml-theory",
            "location": "Zürich, Switzerland",
            "source": "Lab website",
            "status": config.STATUS_SAVED,
        }
    )

    # ── APPLIED (4) — submitted, awaiting response ────────────────
    # 2 with applied_date set (R1 trail visible)
    sid_applied_a = database.add_position(
        {
            "position_name": "Postdoc — Bayesian Methods",
            "institute": "Harvard University",
            "field": "Biostatistics",
            "deadline_date": iso(-15),
            "priority": "High",
            "status": config.STATUS_APPLIED,
            "req_cv": "Yes",
            "done_cv": 1,
            "req_cover_letter": "Yes",
            "done_cover_letter": 1,
        }
    )
    database.upsert_application(
        sid_applied_a,
        {"applied_date": iso(-10), "response_type": "Acknowledgement"},
        propagate_status=False,
    )
    sid_applied_b = database.add_position(
        {
            "position_name": "Postdoc — Survival Analysis",
            "institute": "Johns Hopkins University",
            "field": "Biostatistics",
            "deadline_date": iso(-20),
            "priority": "Medium",
            "status": config.STATUS_APPLIED,
        }
    )
    database.upsert_application(
        sid_applied_b,
        {"applied_date": iso(-18)},
        propagate_status=False,
    )

    # 2 APPLIED without applied_date (in-flight, not yet stamped)
    for institute, field, deadline_off in [
        ("UC Berkeley", "Statistics", -30),
        ("Yale University", "Biostatistics", -25),
    ]:
        database.add_position(
            {
                "position_name": f"Postdoc — {field}",
                "institute": institute,
                "field": field,
                "deadline_date": iso(deadline_off),
                "priority": "Medium",
                "status": config.STATUS_APPLIED,
            }
        )

    # ── INTERVIEW (3) — each has 1+ interview row; 5 rows total ───
    sid_interview_a = database.add_position(
        {
            "position_name": "Faculty — Tenure-Track Assistant Professor",
            "institute": "Columbia University",
            "field": "Biostatistics",
            "deadline_date": iso(-60),
            "priority": "High",
            "status": config.STATUS_INTERVIEW,
        }
    )
    database.upsert_application(
        sid_interview_a,
        {"applied_date": iso(-55), "response_type": "Interview Invite"},
        propagate_status=False,
    )
    database.add_interview(
        sid_interview_a,
        {"scheduled_date": iso(7), "format": "Video"},
        propagate_status=False,
    )
    database.add_interview(
        sid_interview_a,
        {"scheduled_date": iso(14), "format": "On-site"},
        propagate_status=False,
    )

    sid_interview_b = database.add_position(
        {
            "position_name": "Postdoc — Network Science",
            "institute": "Northwestern University",
            "field": "Statistics",
            "deadline_date": iso(-70),
            "priority": "Medium",
            "status": config.STATUS_INTERVIEW,
        }
    )
    database.upsert_application(
        sid_interview_b,
        {"applied_date": iso(-65)},
        propagate_status=False,
    )
    database.add_interview(
        sid_interview_b,
        {"scheduled_date": iso(3), "format": "Video"},
        propagate_status=False,
    )
    database.add_interview(
        sid_interview_b,
        {"scheduled_date": iso(10), "format": "Video"},
        propagate_status=False,
    )

    sid_interview_c = database.add_position(
        {
            "position_name": "Research Scientist — Healthcare AI",
            "institute": "Memorial Sloan Kettering",
            "field": "Machine Learning",
            "deadline_date": iso(-80),
            "priority": "High",
            "status": config.STATUS_INTERVIEW,
        }
    )
    database.upsert_application(
        sid_interview_c,
        {"applied_date": iso(-75)},
        propagate_status=False,
    )
    database.add_interview(
        sid_interview_c,
        {"scheduled_date": iso(5), "format": "On-site"},
        propagate_status=False,
    )

    # ── OFFER (2) — 1 with response_date set (R3 trail visible) ───
    sid_offer_a = database.add_position(
        {
            "position_name": "Postdoc — Spatial Statistics",
            "institute": "University of Washington",
            "field": "Biostatistics",
            "deadline_date": iso(-100),
            "priority": "High",
            "status": config.STATUS_OFFER,
        }
    )
    database.upsert_application(
        sid_offer_a,
        {
            "applied_date": iso(-90),
            "response_date": iso(-10),
            "response_type": "Offer",
        },
        propagate_status=False,
    )
    database.add_position(
        {
            "position_name": "Assistant Professor — Statistics",
            "institute": "Carnegie Mellon University",
            "field": "Statistics",
            "deadline_date": iso(-95),
            "priority": "High",
            "status": config.STATUS_OFFER,
        }
    )

    # ── CLOSED (2) — search closed, no decision either way ────────
    database.add_position(
        {
            "position_name": "Postdoc — Computational Biology",
            "institute": "Broad Institute",
            "field": "Computational Biology",
            "deadline_date": iso(-150),
            "priority": "Medium",
            "status": config.STATUS_CLOSED,
        }
    )
    database.add_position(
        {
            "position_name": "Research Scientist — Population Health",
            "institute": "Kaiser Permanente Research",
            "field": "Public Health",
            "deadline_date": iso(-200),
            "priority": "Low",
            "status": config.STATUS_CLOSED,
        }
    )

    # ── REJECTED (3) — applied, response was no ───────────────────
    for institute, field, deadline_off, applied_off in [
        ("MIT", "Statistics", -120, -110),
        ("Cornell University", "Operations Research", -130, -125),
        ("New York University", "Statistics", -115, -100),
    ]:
        sid = database.add_position(
            {
                "position_name": f"Postdoc — {field}",
                "institute": institute,
                "field": field,
                "deadline_date": iso(deadline_off),
                "priority": "Medium",
                "status": config.STATUS_REJECTED,
            }
        )
        database.upsert_application(
            sid,
            {"applied_date": iso(applied_off), "response_type": "Rejection"},
            propagate_status=False,
        )

    # ── DECLINED (1) — accepted elsewhere, withdrew this one ──────
    sid_declined = database.add_position(
        {
            "position_name": "Postdoc — Theoretical Statistics",
            "institute": "Brown University",
            "field": "Statistics",
            "deadline_date": iso(-140),
            "priority": "Medium",
            "status": config.STATUS_DECLINED,
        }
    )
    database.upsert_application(
        sid_declined,
        {"applied_date": iso(-130)},
        propagate_status=False,
    )

    # ── Recommenders (5) ──────────────────────────────────────────
    # 1 on the urgent SAVED — past asked-window, no submission (triggers
    # the dashboard follow-up panel).
    database.add_recommender(
        sid_saved_urgent,
        {
            "recommender_name": "Dr. Alice Chen",
            "relationship": "PhD advisor",
            "asked_date": iso(-40),
            "submitted_date": None,
        },
    )

    # 1 confirmed but not yet submitted (within window).
    database.add_recommender(
        sid_applied_a,
        {
            "recommender_name": "Dr. Priya Iyer",
            "relationship": "Postdoc mentor",
            "asked_date": iso(-5),
            "confirmed": 1,
            "submitted_date": None,
        },
    )

    # 1 with letter fully submitted (positive trail).
    database.add_recommender(
        sid_interview_a,
        {
            "recommender_name": "Dr. Robert Park",
            "relationship": "Thesis committee",
            "asked_date": iso(-30),
            "confirmed": 1,
            "submitted_date": iso(-20),
        },
    )

    # 1 confirmed + submitted on a different position (variety).
    database.add_recommender(
        sid_interview_b,
        {
            "recommender_name": "Dr. Marcus Lee",
            "relationship": "Postdoc collaborator",
            "asked_date": iso(-25),
            "confirmed": 1,
            "submitted_date": iso(-18),
        },
    )

    # 1 with NULL recommender_name (exercises RECOMMENDER_NAME_FALLBACK).
    database.add_recommender(
        sid_applied_b,
        {
            "recommender_name": None,
            "relationship": "TBD",
            "asked_date": iso(-3),
            "submitted_date": None,
        },
    )


def wipe(path) -> None:
    """Delete all rows from the demo DB file."""
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
    """CLI entry for the screenshot-generation workflow.

    Resolves the target path (env ``AAT_DB_PATH`` override, else
    ``demo.db`` at the repo root) and points ``database.DB_PATH`` at it
    for the duration of the run only — restored on exit so in-process
    callers (tests) see no lingering global mutation.
    """
    import os

    env_path = os.environ.get("AAT_DB_PATH")
    db_path = (
        Path(env_path).expanduser().resolve()
        if env_path
        else (_REPO_ROOT / "demo.db").resolve()
    )

    prev_db_path = database.DB_PATH
    database.DB_PATH = db_path
    try:
        print(f"Seeding demo database at {db_path}")
        wipe(db_path)
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
    finally:
        database.DB_PATH = prev_db_path


if __name__ == "__main__":
    main()
