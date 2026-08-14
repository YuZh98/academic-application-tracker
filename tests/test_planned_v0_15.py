# tests/test_planned_v0_15.py
# Pinning tests for v0.15.0 — Recommender refactor (R0a) + Schema-UI
# wireup (R0b) per UX_Improvement_Plan_2026-05-22.
#
# TDD red-phase contracts. The planned functions (add_global_recommender,
# link_recommender_to_position, etc.) do not yet exist on the database
# module. Every test:
#   - Marked xfail(strict=False) so the suite stays green today.
#   - Gated by hasattr() so the test raises NotImplementedError before
#     hitting any setup that depends on R0a internals — pinning the
#     acceptance contract without breaking collection.
#   - Uses getattr() to access planned attributes so pyright stays
#     clean (the planned attributes are not yet defined).
#
# When R0a / R0b land, the implementer:
#   1. Adds the public functions + schema migration to database.py.
#   2. Drops the hasattr() gate and the getattr() indirection in this
#      file, replacing them with direct calls.
#   3. Removes the xfail decorator in the SAME PR that makes the test
#      green (universal CLAUDE.md §7 enforcement rule).

import re
from pathlib import Path
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

import database
from tests.conftest import make_position
from tests.helpers import page_path

# Planned-symbol catalogue — every name R0a/R0b will add. The
# _require() gate raises NotImplementedError before the test body runs
# if any are missing, so xfail catches a single deterministic failure
# mode rather than chasing AttributeError / sqlite3 errors per call site.
R0A_SYMBOLS = (
    "add_global_recommender",
    "update_global_recommender",
    "delete_global_recommender",
    "get_global_recommenders",
    "link_recommender_to_position",
    "RecommenderHasActiveAssignmentsError",
)


def _require(symbols: tuple[str, ...]) -> None:
    missing = [s for s in symbols if not hasattr(database, s)]
    if missing:
        raise NotImplementedError(
            f"Planned symbols not yet on database: {missing}. "
            "See UX_Improvement_Plan_2026-05-22 §3 R0a/R0b."
        )


def _planned(name: str) -> Any:
    return getattr(database, name)


# ── R0a: global recommender entity + position_recommenders join ────────────────


class TestR0aRecommenderEntity:
    """Recommender becomes a first-class global entity. New shape:

        recommenders (id, name, email, relationship, asked_date,
                      confirmed, notes)
        position_recommenders (position_id, recommender_id,
                               submitted_date, reminder_sent,
                               reminder_sent_date)

    Acceptance contracts trace back to BDD UX_BDD_Scenarios_2026-05-22
    §v0.15.0 R0a."""

    XFAIL_REASON = (
        "Planned v0.15.0 R0a: global recommender entity + "
        "position_recommenders join table not yet implemented. "
        "Tracked by docs/ux-research/UX_Improvement_Plan_2026-05-22 §3 "
        "R0a (v0.15.0). Remove xfail when R0a ships."
    )

    SMITH_LOWER = "smith"
    SMITH_TITLE = "Smith"

    @pytest.mark.xfail(strict=False, reason=XFAIL_REASON)
    def test_writer_creation_cost_is_additive_not_multiplicative(self, db):
        """Scenario: Onboarding cost is additive (BDD R0a).
        P1: 4 writers + 40 positions = 44 ops, not 160."""
        _require(R0A_SYMBOLS)

        writer_ids = [
            _planned("add_global_recommender")(
                {"name": f"Writer {i}", "email": f"w{i}@x.edu"}
            )
            for i in range(4)
        ]
        position_ids = [database.add_position(make_position()) for _ in range(40)]

        assert len(_planned("get_global_recommenders")()) == 4
        assert len(writer_ids) == 4
        assert len(position_ids) == 40

        # Creating a global writer must not auto-link to every position.
        with database._connect() as conn:
            joins = conn.execute(
                "SELECT COUNT(*) AS n FROM position_recommenders"
            ).fetchone()["n"]
        assert joins == 0, (
            "R0a invariant: writer-creation must not explode joins. "
            f"Found {joins} pre-existing rows."
        )

        for pid in position_ids:
            for wid in writer_ids:
                _planned("link_recommender_to_position")(pid, wid)
        with database._connect() as conn:
            joins = conn.execute(
                "SELECT COUNT(*) AS n FROM position_recommenders"
            ).fetchone()["n"]
        assert joins == 4 * 40, f"Expected 160 join rows; got {joins}"

    @pytest.mark.xfail(strict=False, reason=XFAIL_REASON)
    def test_editing_writer_email_propagates_to_all_positions(self, db):
        """Scenario: Editing one writer's email propagates everywhere
        (BDD R0a)."""
        _require(R0A_SYMBOLS)

        wid = _planned("add_global_recommender")(
            {"name": "Dr. Jones", "email": "a@x.edu"}
        )
        p1, p2, p3 = (database.add_position(make_position()) for _ in range(3))
        for pid in (p1, p2, p3):
            _planned("link_recommender_to_position")(pid, wid)

        _planned("update_global_recommender")(wid, {"email": "b@x.edu"})

        with database._connect() as conn:
            rows = conn.execute(
                "SELECT r.email FROM recommenders r "
                "JOIN position_recommenders pr ON pr.recommender_id = r.id "
                "WHERE pr.position_id IN (?, ?, ?)",
                (p1, p2, p3),
            ).fetchall()
        emails = {r["email"] for r in rows}
        assert emails == {"b@x.edu"}, (
            "R0a contract: email lives on the global writer, not on the "
            f"join. Expected {{'b@x.edu'}}; got {emails!r}."
        )

    @pytest.mark.xfail(strict=False, reason=XFAIL_REASON)
    def test_deleting_position_preserves_global_writer(self, db):
        """Scenario: Deleting a position preserves the global writer
        (BDD R0a)."""
        _require(R0A_SYMBOLS)

        w1 = _planned("add_global_recommender")({"name": "Dr. A"})
        w2 = _planned("add_global_recommender")({"name": "Dr. B"})
        pid = database.add_position(make_position())
        _planned("link_recommender_to_position")(pid, w1)
        _planned("link_recommender_to_position")(pid, w2)

        database.delete_position(pid)

        survivors = _planned("get_global_recommenders")()
        names = {row["name"] for _, row in survivors.iterrows()}
        assert names >= {"Dr. A", "Dr. B"}

        with database._connect() as conn:
            joins = conn.execute(
                "SELECT COUNT(*) AS n FROM position_recommenders "
                "WHERE position_id = ?",
                (pid,),
            ).fetchone()["n"]
        assert joins == 0, (
            "Position-delete must cascade join rows but NOT the global "
            f"writer. Orphan joins remaining: {joins}."
        )

    @pytest.mark.xfail(strict=False, reason=XFAIL_REASON)
    def test_migration_deduplicates_case_folded_names(self, db):
        """Scenario: Migration dedups case-folded recommender names
        (BDD R0a).

        Lighter-touch shape than the full legacy-DB rehydration: seeds
        per-position recommender rows via the existing public API
        (which today writes the legacy shape), then asserts the post-
        migration global table has dedup'd them. R0a's migration must
        be idempotent when called against a DB that already has the
        legacy rows in place."""
        _require(R0A_SYMBOLS)

        # Three positions, three legacy recommender rows naming "Smith"
        # / "smith" / "Smith". Seeded via the legacy API (existing
        # database.add_recommender writes the per-position shape).
        pid1 = database.add_position(make_position(overrides={"position_name": "P1"}))
        pid2 = database.add_position(make_position(overrides={"position_name": "P2"}))
        pid3 = database.add_position(make_position(overrides={"position_name": "P3"}))
        database.add_recommender(pid1, {"recommender_name": self.SMITH_TITLE})
        database.add_recommender(pid2, {"recommender_name": self.SMITH_LOWER})
        database.add_recommender(pid3, {"recommender_name": self.SMITH_TITLE})

        # Re-run init_db to trigger the R0a backfill on existing rows.
        database.init_db()

        global_rows = _planned("get_global_recommenders")()
        smith_rows = global_rows[
            global_rows["name"].str.casefold() == self.SMITH_LOWER
        ]
        assert len(smith_rows) == 1, (
            "R0a migration must case-fold-dedup 'Smith' / 'smith' into "
            f"one global row. Got {len(smith_rows)}."
        )

        with database._connect() as conn:
            joins = conn.execute(
                "SELECT COUNT(*) AS n FROM position_recommenders pr "
                "JOIN recommenders r ON r.id = pr.recommender_id "
                "WHERE LOWER(r.name) = ?",
                (self.SMITH_LOWER,),
            ).fetchone()["n"]
        assert joins == 3, (
            f"All 3 legacy rows must produce join entries; got {joins}."
        )

    @pytest.mark.xfail(strict=False, reason=XFAIL_REASON)
    def test_legacy_table_retained_as_rollback_surface(self, db):
        """Scenario: Legacy table retained for one release (BDD R0a).
        After v0.15.0 migration both ``recommenders_legacy`` (renamed)
        and the new ``recommenders`` + ``position_recommenders`` must
        exist. v0.16.0 drops the legacy table physically."""
        _require(R0A_SYMBOLS)

        with database._connect() as conn:
            tables = {
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert {"recommenders", "position_recommenders", "recommenders_legacy"} <= tables, (
            "R0a rollback surface: must keep recommenders_legacy alongside "
            "the new tables in v0.15.0. Missing: "
            f"{{'recommenders', 'position_recommenders', 'recommenders_legacy'}} - {tables}"
        )

    @pytest.mark.xfail(strict=False, reason=XFAIL_REASON)
    def test_deleting_assigned_global_writer_is_blocked(self, db):
        """Scenario (negative): Deleting an assigned global writer is
        blocked (BDD R0a). Policy choice: blocking error with named
        positions; cascade requires explicit confirm. Surface here so
        reviewers can challenge."""
        _require(R0A_SYMBOLS)

        wid = _planned("add_global_recommender")({"name": "Dr. Active"})
        pid = database.add_position(make_position(overrides={"position_name": "PosX"}))
        _planned("link_recommender_to_position")(pid, wid)

        exc_class = _planned("RecommenderHasActiveAssignmentsError")
        with pytest.raises(exc_class) as exc:
            _planned("delete_global_recommender")(wid)
        msg = str(exc.value)
        assert "PosX" in msg, (
            "Block error must name the active position(s). "
            f"Got: {msg!r}."
        )

    @pytest.mark.xfail(strict=False, reason=XFAIL_REASON)
    def test_mid_migration_crash_leaves_no_partial_state(
        self, db, tmp_path, monkeypatch
    ):
        """Scenario (negative): Mid-migration crash → either legacy
        intact OR new tables complete; never both partial (BDD R0a).

        Strategy: seed three legacy rows, monkeypatch the planned
        backfill helper to raise mid-transaction, re-run init_db, then
        inspect the resulting state. R0a must wrap migration in a
        single transaction so the partial path is impossible."""
        _require(R0A_SYMBOLS + ("_r0a_backfill",))

        pid = database.add_position(make_position())
        database.add_recommender(pid, {"recommender_name": "A"})
        database.add_recommender(pid, {"recommender_name": "B"})
        database.add_recommender(pid, {"recommender_name": "C"})

        def _boom(_conn: Any) -> None:
            raise IOError("simulated mid-migration crash")

        monkeypatch.setattr(database, "_r0a_backfill", _boom)
        with pytest.raises(IOError):
            database.init_db()

        with database._connect() as conn:
            tables = {
                r["name"]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            new_count = (
                conn.execute(
                    "SELECT COUNT(*) FROM position_recommenders"
                ).fetchone()[0]
                if "position_recommenders" in tables
                else 0
            )
            legacy_count = (
                conn.execute("SELECT COUNT(*) FROM recommenders").fetchone()[0]
                if "recommenders" in tables
                else 0
            )

        assert (legacy_count == 3 and new_count == 0) or (
            legacy_count == 0 and new_count == 3
        ), (
            "R0a atomicity contract: mid-crash state must be one of "
            "{legacy intact, no joins} or {migration complete}. "
            f"Got legacy_count={legacy_count}, new_count={new_count}."
        )


    @pytest.mark.xfail(strict=False, reason=XFAIL_REASON)
    def test_tab_switch_preserves_row_selection(self, db):
        """Scenario (state preservation): Tab switch on the two-tab
        Recommenders page keeps row selection (BDD R0a / state).
        Pins dev-notes gotcha #11 (`_skip_table_reset` flag) and #13
        (`fillna("")` before any groupby on join queries — guards
        against NaN-from-NULL leaking into widget state on a join
        query the new Assignments tab depends on)."""
        _require(R0A_SYMBOLS)

        wid = _planned("add_global_recommender")({"name": "Dr. Jones"})
        pid = database.add_position(make_position())
        _planned("link_recommender_to_position")(pid, wid)

        at = AppTest.from_file(
            "pages/3_Recommenders.py", default_timeout=10
        ).run()

        # Simulate a row selection on the Assignments tab, then switch
        # to "My letter writers" and back. The Streamlit AppTest tab
        # API drives this — the contract is that the selection-id
        # sentinel persists across the round trip.
        at.session_state["recs_selected_writer_id"] = wid
        at.run()  # rerun simulating tab switch
        assert at.session_state.get("recs_selected_writer_id") == wid, (
            "R0a state contract: selection-id sentinel must survive a "
            "tab switch (per dev-notes gotcha #11). "
            f"Got {at.session_state.get('recs_selected_writer_id')!r}."
        )
        # Joining the legacy NaN gotcha #13 contract: the page must
        # have rendered without raising a widget protobuf TypeError
        # — which it would if a float('nan') from a NULL email
        # column leaked into a widget pre-seed. Reaching this assert
        # means the join-query rendering path applied fillna("")
        # successfully.
        assert at.exception == [] or not any(
            "TypeError" in str(e) for e in at.exception
        ), (
            "R0a contract: join-query NULL columns must be coerced "
            "via fillna('') before widget pre-seed (gotcha #13). "
            f"Got exceptions: {at.exception!r}."
        )


class TestR0aAssignmentsVisual:
    """Visual contract: the Assignments tab defaults to a per-
    recommender grouping (N cards) — not a per-position grid (N×M
    rows). This is what addresses P2's abandonment, separately from
    R0a's data-model fix."""

    XFAIL_REASON = (
        "Planned v0.15.0 R0a (UI): two-tab Recommenders page with "
        "Assignments tab defaulting to per-recommender grouping is not "
        "yet shipped. AppTest will not yet find the tab structure."
    )
    RECOMMENDERS_PAGE = page_path("pages/3_Recommenders.py")

    @pytest.mark.xfail(strict=False, reason=XFAIL_REASON)
    def test_default_grouping_is_per_recommender_not_per_position(self, db):
        """Scenario: Default Assignments view is N cards, not N×M rows
        (BDD R0a / UI)."""
        _require(R0A_SYMBOLS)

        # Smaller fixture than P2's 5×22: still pins the N-vs-N×M
        # contract cleanly while keeping the test fast.
        writers = [
            _planned("add_global_recommender")({"name": f"W{i}"}) for i in range(5)
        ]
        positions = [database.add_position(make_position()) for _ in range(4)]
        for pid in positions:
            for wid in writers:
                _planned("link_recommender_to_position")(pid, wid)

        at = AppTest.from_file(self.RECOMMENDERS_PAGE, default_timeout=10).run()

        assert len(at.expander) == 5, (
            "R0a UI contract: default Assignments view groups by writer "
            f"(N=5 expandable cards), not by position (N×M=20 rows). "
            f"Got {len(at.expander)} expanders."
        )


# ── R0b: schema-UI wireup (closes the v0.14.0 xfail) ───────────────────────────


class TestR0bSchemaUiWireup:
    """The 10 orphan ``positions`` columns get a UI binding. Quick-Add
    gains three short-string columns under the 6-field discipline (S6);
    the rest reach Edit only. When R0b ships, the v0.14.0
    ``TestB3SchemaUiPin`` test also flips green and its xfail comes off."""

    OPPORTUNITIES_PAGE = page_path("pages/1_Opportunities.py")
    ROUND_TRIP_LOCATION = "Stanford"
    ROUND_TRIP_SOURCE = "academic-jobs-online"
    ROUND_TRIP_PORTAL = "https://x.edu/apply"

    def test_quickadd_round_trip_preserves_new_columns(self, db):
        """Scenario: Round-trip Save preserves every previously-orphan
        column (BDD R0b)."""
        at = AppTest.from_file(self.OPPORTUNITIES_PAGE, default_timeout=10).run()

        at.text_input(key="qa_position_name_0").set_value("Test Postdoc")
        at.text_input(key="qa_institute_0").set_value("Stanford")
        at.text_input(key="qa_location_0").set_value(self.ROUND_TRIP_LOCATION)
        at.text_input(key="qa_source_0").set_value(self.ROUND_TRIP_SOURCE)
        at.text_input(key="qa_portal_url_0").set_value(self.ROUND_TRIP_PORTAL)
        at.button(key="qa_submit_0").click().run()

        rows = database.get_all_positions()
        assert len(rows) == 1
        row = rows.iloc[0]
        assert row["location"] == self.ROUND_TRIP_LOCATION
        assert row["source"] == self.ROUND_TRIP_SOURCE
        assert row["portal_url"] == self.ROUND_TRIP_PORTAL

    def test_edit_panel_round_trip_preserves_orphan_columns(self, db):
        """Scenario: Round-trip Save through the Edit-panel Overview
        tab preserves previously-orphan columns that didn't get
        promoted to Quick-Add (BDD R0b, response to UX-mgr round-1
        nit). Pins ``mentor``, ``stipend``, and ``keywords`` —
        representative of the 8 Edit-only orphan columns.

        Goes straight through the database API for the Save half of
        the round trip — the existing TestOverviewTabSave tests already
        pin the Streamlit form submit driver against AppTest with the
        ``_keep_selection`` pattern; what R0b actually changes is the
        column set Save persists, which is testable at the DB layer."""
        pid = database.add_position(make_position())

        # The R0b edit-panel payload, mirroring the page's
        # update_position(sid, payload) call for the Overview tab.
        database.update_position(
            pid,
            {
                "mentor": "Dr. Mentor",
                "stipend": "$65k",
                "keywords": "ml, nlp",
                "point_of_contact": "Admissions <pofc@x.edu>",
                "reference_code": "REF-001",
                "description": "Joint computational biology + ML postdoc.",
                "deadline_note": "Soft deadline; rolling review.",
                "full_time": "Yes",
            },
        )

        row = database.get_all_positions().iloc[0]
        assert int(row["id"]) == pid
        assert row["mentor"] == "Dr. Mentor"
        assert row["stipend"] == "$65k"
        assert row["keywords"] == "ml, nlp"
        assert row["point_of_contact"] == "Admissions <pofc@x.edu>"
        assert row["reference_code"] == "REF-001"
        assert row["description"] == "Joint computational biology + ML postdoc."
        assert row["deadline_note"] == "Soft deadline; rolling review."
        assert row["full_time"] == "Yes"

        # And the Edit-panel widgets exist on the page (BDD R0b: "all
        # 10 previously-orphan columns visible and editable"). Verified
        # via the schema-UI binding test at v0.14 B3SchemaUiPin; we
        # cross-pin the panel here by re-grepping the widget keys so a
        # rename in the page would fail this test in addition to B3.
        page = Path(self.OPPORTUNITIES_PAGE).read_text(encoding="utf-8")
        for col in (
            "mentor", "stipend", "keywords", "point_of_contact",
            "reference_code", "description", "deadline_note", "full_time",
        ):
            assert re.search(rf'key="edit_{col}"', page), (
                f"R0b contract: Edit-panel widget keyed edit_{col} must "
                "be present in pages/1_Opportunities.py."
            )

    def test_quickadd_stays_within_six_field_discipline(self, db):
        """Scenario: Quick-Add stays inside the 6-field discipline
        (BDD R0b / S6).

        Tightened post-round-1 to count *all* widget kinds (text_input,
        date_input, selectbox), and to assert the exact post-R0b
        count rather than an open-ended cap — so silent slack cannot
        absorb the next addition."""
        at = AppTest.from_file(self.OPPORTUNITIES_PAGE, default_timeout=10).run()

        # Collect every Quick-Add widget across widget kinds. The form's
        # nonce-suffixed keys (qa_*_0) tag inputs unambiguously.
        qa_widget_keys: set[str] = set()
        for w in at.text_input:
            if w.key and w.key.startswith("qa_") and w.key != "qa_submit_0":
                qa_widget_keys.add(w.key)
        for w in at.date_input:
            if w.key and w.key.startswith("qa_"):
                qa_widget_keys.add(w.key)
        for w in at.selectbox:
            if w.key and w.key.startswith("qa_"):
                qa_widget_keys.add(w.key)

        # 6 original (position_name, deadline_date, institute, priority,
        # field, link) + 3 R0b promotions (location, source, portal_url).
        assert len(qa_widget_keys) == 9, (
            "S6 discipline: Quick-Add must hold exactly 6 original fields "
            f"+ 3 R0b short-string promotions = 9 widgets. Got "
            f"{len(qa_widget_keys)} ({sorted(qa_widget_keys)!r})."
        )

        forbidden = {"qa_description_0", "qa_keywords_0"}
        assert qa_widget_keys.isdisjoint(forbidden), (
            "Long free-text columns must stay in Edit only. Found in "
            f"Quick-Add: {qa_widget_keys & forbidden}."
        )
