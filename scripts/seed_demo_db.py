"""Seed a throwaway SQLite database with fabricated demo data for screenshots.

Usage
-----
    source .venv/bin/activate
    AAT_DB_PATH=$PWD/demo.db python3 scripts/seed_demo_db.py
    AAT_DB_PATH=$PWD/demo.db streamlit run app.py

The script wipes whatever lives at ``AAT_DB_PATH`` (or ``demo.db`` in the
repo root if the env var is unset), reinitializes the schema, and fills
it with five fictional positions plus a small recommender roster — enough
to populate every panel on Dashboard, Opportunities, Applications, and
Recommenders without using a single real datum.

All institute names are well-known public universities; every recommender
name is fabricated. ``demo.db`` is gitignored so it never reaches origin.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# AAT_DB_PATH must be set BEFORE importing database so its module-level
# DB_PATH resolution picks up the override on the first import.
if "AAT_DB_PATH" not in os.environ:
    os.environ["AAT_DB_PATH"] = str((_REPO_ROOT / "demo.db").resolve())

import config  # noqa: E402
import database  # noqa: E402


def iso(days_offset: int) -> str:
    return (date.today() + timedelta(days=days_offset)).isoformat()


def wipe(path: Path) -> None:
    if not path.exists():
        return
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        for table in ("recommenders", "interviews", "applications", "positions"):
            try:
                conn.execute(f"DELETE FROM {table}")
            except sqlite3.OperationalError:
                # Schema not yet present — init_db() will create it.
                pass
        conn.commit()


def seed() -> None:
    db_path = database.DB_PATH
    print(f"Seeding demo database at {db_path}")
    wipe(db_path)
    database.init_db()

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
    seed()
