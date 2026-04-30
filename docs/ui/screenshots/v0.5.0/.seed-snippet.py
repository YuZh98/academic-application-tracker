"""
Re-seed postdoc.db with the cohesion-smoke fixture data.

Save as a scratch script and run from the repo root with the venv active:
    source .venv/bin/activate
    python3 docs/ui/screenshots/v0.5.0/.seed-snippet.py

Wipes the existing DB and re-fills it so the dashboard exercises every
panel for the v0.5.0 cohesion-smoke captures (1280 / 1440 / 1680).
The fixture is the same one that produced the verbatim renders cited in
reviews/phase-4-finish-cohesion-smoke.md.

WARNING: this WIPES postdoc.db. Run only when capturing screenshots,
and only in a working tree where you have a backup or no production data.
"""
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB = Path("postdoc.db")

# Wipe so the seed lands on a clean schema. (CREATE TABLE IF NOT EXISTS
# preserves the existing DDL — including any pre-v1.3 DEFAULTs — so if
# you suspect schema drift, delete the file entirely and let
# database.init_db() recreate from scratch.)
with sqlite3.connect(DB) as conn:
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DELETE FROM recommenders")
    conn.execute("DELETE FROM interviews")
    conn.execute("DELETE FROM applications")
    conn.execute("DELETE FROM positions")
    conn.commit()

import database
import config

database.init_db()

today = date.today()
def iso(days_offset):
    return (today + timedelta(days=days_offset)).isoformat()

# 1. Stanford BioStats — APPLIED, all req docs ready (Materials Readiness "ready")
sid = database.add_position({
    "position_name": "Postdoc in Biostatistics",
    "institute": "Stanford",
    "field": "Biostatistics",
    "deadline_date": iso(5),  # 🔴 within 7 days
    "priority": "High",
    "link": "https://example.org/stanford",
    "req_cv": "Yes", "done_cv": 1,
    "req_cover_letter": "Yes", "done_cover_letter": 1,
    "req_research_statement": "Yes", "done_research_statement": 1,
})
database.upsert_application(sid, {"applied_date": iso(-12), "response_type": "Acknowledgement"}, propagate_status=True)
database.add_recommender(sid, {"recommender_name": "Dr. Smith", "relationship": "PhD Advisor",
                                "asked_date": iso(-14), "confirmed": 1, "submitted_date": None})
database.add_recommender(sid, {"recommender_name": "Dr. Jones", "relationship": "Committee Member",
                                "asked_date": iso(-14), "confirmed": 1, "submitted_date": iso(-3)})

# 2. MIT CSAIL — INTERVIEW, has upcoming interview, materials still pending
mid = database.add_position({
    "position_name": "Postdoc in CS / ML",
    "institute": "MIT CSAIL",
    "field": "Machine Learning",
    "deadline_date": iso(15),
    "priority": "High",
    "link": "https://example.org/mit",
    "req_cv": "Yes", "done_cv": 1,
    "req_research_statement": "Yes", "done_research_statement": 0,
    "req_teaching_statement": "Yes", "done_teaching_statement": 0,
})
database.upsert_application(mid, {"applied_date": iso(-25), "response_type": "Interview Invite"}, propagate_status=True)
database.add_interview(mid, {"sequence": 1, "scheduled_date": iso(8), "format": "Video",
                              "notes": "Initial chat with PI"}, propagate_status=True)
database.add_recommender(mid, {"recommender_name": "Dr. Smith", "relationship": "PhD Advisor",
                                "asked_date": iso(-14), "confirmed": 1, "submitted_date": None})

# 3. UC Berkeley Stats — OFFER (R3 fires)
bid = database.add_position({
    "position_name": "Postdoc in Statistics",
    "institute": "UC Berkeley",
    "field": "Statistics",
    "priority": "Medium",
    "req_cv": "Yes", "done_cv": 1,
})
database.upsert_application(bid, {"applied_date": iso(-40), "response_type": config.RESPONSE_TYPE_OFFER}, propagate_status=True)

# 4. Princeton — SAVED with future deadline
database.add_position({
    "position_name": "Postdoc in Bayesian Inference",
    "institute": "Princeton",
    "field": "Bayesian Statistics",
    "deadline_date": iso(22),
    "priority": "Medium",
    "link": "https://example.org/princeton",
    "req_cv": "Yes", "done_cv": 0,
})

# 5. Harvard — SAVED, deadline 50 days out (only visible at 60/90-day windows)
database.add_position({
    "position_name": "Postdoc in Causal Inference",
    "institute": "Harvard T.H. Chan",
    "field": "Causal Inference",
    "deadline_date": iso(50),
    "priority": "Stretch",
})

print("=== Seeded DB state ===")
print(f"Status counts:    {database.count_by_status()}")
print(f"Pending recs:     {len(database.get_pending_recommenders())} rows (expect 2)")
print(f"Upcoming (30d):   {len(database.get_upcoming(days=30))} rows")
print(f"Materials ready:  {database.compute_materials_readiness()}")
