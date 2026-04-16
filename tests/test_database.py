# tests/test_database.py
# Integration tests for database.py.
#
# All tests use real SQLite (no mocking). Each test gets an isolated temp DB
# via the `db` fixture in conftest.py. Tests are grouped by concern.

import sqlite3
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
        assert pos["req_portfolio"] == "N"   # default for new column


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

    def test_status_defaults_to_open(self, db):
        pos_id = database.add_position(make_position())
        pos = database.get_position(pos_id)
        assert pos["status"] == "[OPEN]"

    def test_req_columns_default_to_n(self, db):
        pos_id = database.add_position(make_position())
        pos = database.get_position(pos_id)
        for req_col, _, _ in config.REQUIREMENT_DOCS:
            assert pos[req_col] == "N", f"{req_col} should default to 'N'"

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
        database.update_position(pos_id, {"status": "[APPLIED]", "req_cv": "Y"})
        pos = database.get_position(pos_id)
        assert pos["status"] == "[APPLIED]"
        assert pos["req_cv"] == "Y"

    def test_partial_update_does_not_clobber_other_fields(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {"status": "[APPLIED]"})
        pos = database.get_position(pos_id)
        assert pos["position_name"] == "BioStats Postdoc"   # unchanged
        assert pos["institute"] == "Stanford"               # unchanged

    def test_can_set_done_column(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {"req_cv": "Y", "done_cv": 1})
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
        assert counts["[OPEN]"]    == 2
        assert counts["[APPLIED]"] == 1

    def test_closed_status_counted_separately(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {"status": "[CLOSED]"})
        counts = database.count_by_status()
        assert "[OPEN]"   not in counts
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
        """req_* all default to 'N' — position has no requirements, excluded from count."""
        database.add_position(make_position())
        result = database.compute_materials_readiness()
        assert result == {"ready": 0, "pending": 0}

    def test_ready_when_all_required_docs_done(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {"req_cv": "Y", "done_cv": 1})
        result = database.compute_materials_readiness()
        assert result["ready"] == 1
        assert result["pending"] == 0

    def test_pending_when_required_doc_not_done(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {"req_cv": "Y", "done_cv": 0})
        result = database.compute_materials_readiness()
        assert result["ready"] == 0
        assert result["pending"] == 1

    def test_pending_when_one_of_many_required_docs_not_done(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {
            "req_cv": "Y", "done_cv": 1,
            "req_cover_letter": "Y", "done_cover_letter": 0,   # not done
        })
        result = database.compute_materials_readiness()
        assert result["ready"] == 0
        assert result["pending"] == 1

    def test_optional_docs_not_required_for_ready(self, db):
        """req_* = 'Optional' means the doc exists but is not required for readiness."""
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {
            "req_cv": "Y", "done_cv": 1,
            "req_transcripts": "Optional", "done_transcripts": 0,  # Optional, not done
        })
        result = database.compute_materials_readiness()
        # 'Optional' != 'Y', so done_transcripts=0 does not make it pending
        assert result["ready"] == 1
        assert result["pending"] == 0

    def test_excludes_closed_positions(self, db):
        pos_id = database.add_position(make_position())
        database.update_position(pos_id, {
            "status": "[CLOSED]",
            "req_cv": "Y", "done_cv": 0,
        })
        result = database.compute_materials_readiness()
        assert result == {"ready": 0, "pending": 0}

    def test_counts_multiple_positions_correctly(self, db):
        # Position 1: cv required and done → ready
        p1 = database.add_position(make_position({"position_name": "P1"}))
        database.update_position(p1, {"req_cv": "Y", "done_cv": 1})

        # Position 2: cv required but not done → pending
        p2 = database.add_position(make_position({"position_name": "P2"}))
        database.update_position(p2, {"req_cv": "Y", "done_cv": 0})

        # Position 3: no requirements → excluded
        database.add_position(make_position({"position_name": "P3"}))

        result = database.compute_materials_readiness()
        assert result["ready"]   == 1
        assert result["pending"] == 1


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
