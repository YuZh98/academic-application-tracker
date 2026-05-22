# tests/test_planned_v0_16.py
# Pinning tests for v0.16.0 — Bulk operations (R1a) + In-UI settings
# (R1b) per UX_Improvement_Plan_2026-05-22.
#
# TDD red-phase contracts. Same conventions as test_planned_v0_15.py:
#   - xfail(strict=False) so the suite stays green today.
#   - hasattr() gate raises NotImplementedError if planned symbols
#     missing, so xfail catches one deterministic failure mode.
#   - getattr() indirection keeps pyright clean.
#
# R1a's cross-position recommender bulk depends on R0a's join table —
# its xfail also stays in place until R0a ships.

from datetime import date
from typing import Any

import pytest
from streamlit.testing.v1 import AppTest

import config
import database
from tests.conftest import make_position

# Planned symbol catalogue.
R1A_SYMBOLS = (
    "bulk_promote_to_applied",
    "bulk_set_requirement",
)
R1A_CROSS_SYMBOLS = R1A_SYMBOLS + (
    "bulk_mark_writer_submitted",
    "link_recommender_to_position",
    "add_global_recommender",
)
R1B_SYMBOLS = ("load_settings", "save_settings")
R1B_PAGE = "pages/5_Settings.py"


def _require(symbols: tuple[str, ...]) -> None:
    missing = [s for s in symbols if not hasattr(database, s)]
    if missing:
        raise NotImplementedError(
            f"Planned symbols not yet on database: {missing}."
        )


def _planned(name: str) -> Any:
    return getattr(database, name)


# ── R1a: bulk operations in Opportunities table ────────────────────────────────


class TestR1aBulkOps:
    """Bulk multi-row actions on the Opportunities table. Table bulk
    ops (status flip, requirement-set) are R0a-independent; cross-
    position recommender bulk (mark-submitted-across-positions)
    depends on R0a's join table.

    Acceptance contracts: BDD UX_BDD_Scenarios_2026-05-22 §v0.16.0 R1a."""

    XFAIL_REASON = (
        "Planned v0.16.0 R1a: bulk operations not yet shipped. "
        "Functions bulk_promote_to_applied / bulk_set_requirement / "
        "bulk_mark_writer_submitted do not exist on database."
    )

    def test_bulk_status_flip_fires_one_r1_cascade_per_row(self, db):
        """Scenario: Bulk status flip fires one R1 cascade per selected
        row (BDD R1a)."""
        _require(R1A_SYMBOLS)

        ids = [database.add_position(make_position()) for _ in range(10)]
        # All start in [SAVED]; bulk-promote 5 to [APPLIED].
        selected = ids[:5]
        today = date.today().isoformat()

        _planned("bulk_promote_to_applied")(selected, applied_date=today)

        with database._connect() as conn:
            promoted = {
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM positions WHERE status = ?",
                    (config.STATUS_APPLIED,),
                ).fetchall()
            }
            applied_dates = {
                r["position_id"]: r["applied_date"]
                for r in conn.execute(
                    "SELECT position_id, applied_date FROM applications "
                    "WHERE position_id IN ({})".format(
                        ", ".join("?" * len(selected))
                    ),
                    selected,
                ).fetchall()
            }

        assert promoted == set(selected), (
            f"Expected exactly {selected!r} promoted to [APPLIED]; got {promoted!r}"
        )
        assert all(applied_dates[i] == today for i in selected), (
            "R1 cascade contract: every bulk-promoted position must have "
            "its applied_date set in the applications table (the R1 "
            "trigger that drives the [SAVED]→[APPLIED] promotion)."
        )

        # The other 5 must remain in [SAVED].
        unpromoted = set(ids[5:])
        with database._connect() as conn:
            still_saved = {
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM positions WHERE status = ? "
                    "AND id IN ({})".format(", ".join("?" * len(unpromoted))),
                    (config.STATUS_SAVED, *unpromoted),
                ).fetchall()
            }
        assert still_saved == unpromoted, (
            "R1a contract: unselected rows must remain in [SAVED]."
        )

    def test_bulk_set_requirement_rejects_unknown_column(self, db):
        """Scenario (negative): bulk_set_requirement rejects a column
        not in ``config.REQUIREMENT_DOCS`` (BDD R1a, response to
        engineer round-1 nit #2). Boundary-validates the column-name
        f-string substitution to prevent SQL injection through the
        requirement name (GUIDELINES §5)."""
        pid = database.add_position(make_position())
        with pytest.raises(ValueError) as exc:
            database.bulk_set_requirement(
                [pid], requirement="req_evil; DROP TABLE positions; --", value="Yes"
            )
        msg = str(exc.value)
        assert "req_evil" in msg or "Unknown requirement" in msg, (
            f"Error must name the offending column. Got: {msg!r}"
        )

    def test_bulk_promote_to_applied_tolerates_unknown_ids(self, db):
        """Scenario (DB-failure path): bulk_promote_to_applied called
        with a mix of valid + non-existent ids does not raise; the
        non-existent ones are no-ops (UPDATE...WHERE matches nothing),
        the valid ones still promote. Pins the GUIDELINES §9
        DB-failure-case bar without inventing an artificial constraint
        violation (response to engineer round-1 nit #3)."""
        real_pid = database.add_position(make_position())
        bogus_pid = real_pid + 99_999  # guaranteed absent
        today = date.today().isoformat()

        # Must not raise.
        database.bulk_promote_to_applied(
            [real_pid, bogus_pid], applied_date=today
        )

        df = database.get_all_positions()
        promoted = set(df[df["status"] == config.STATUS_APPLIED]["id"].tolist())
        assert promoted == {real_pid}, (
            "Bulk promote must succeed for real ids and silently ignore "
            f"bogus ones. Got promoted={promoted!r}."
        )

    def test_bulk_requirement_set_across_selected_rows(self, db):
        """Scenario: Bulk requirement-set across selected rows
        (BDD R1a)."""
        _require(R1A_SYMBOLS)

        ids = [database.add_position(make_position()) for _ in range(7)]
        _planned("bulk_set_requirement")(ids, requirement="req_cv", value="Yes")

        with database._connect() as conn:
            cv_values = [
                r["req_cv"]
                for r in conn.execute(
                    "SELECT req_cv FROM positions WHERE id IN ({})".format(
                        ", ".join("?" * len(ids))
                    ),
                    ids,
                ).fetchall()
            ]
        assert all(v == "Yes" for v in cv_values), (
            f"All 7 rows must have req_cv='Yes'; got {cv_values!r}"
        )

    @pytest.mark.xfail(strict=False, reason=XFAIL_REASON)
    def test_bulk_mark_writer_submitted_updates_all_assignments(self, db):
        """Scenario: Bulk mark-submitted across positions
        (BDD R1a, depends on R0a)."""
        _require(R1A_CROSS_SYMBOLS)

        wid = _planned("add_global_recommender")({"name": "Dr. Jones"})
        pids = [database.add_position(make_position()) for _ in range(3)]
        for pid in pids:
            _planned("link_recommender_to_position")(pid, wid)

        today = date.today().isoformat()
        _planned("bulk_mark_writer_submitted")(wid, submitted_date=today)

        with database._connect() as conn:
            rows = conn.execute(
                "SELECT submitted_date FROM position_recommenders "
                "WHERE recommender_id = ?",
                (wid,),
            ).fetchall()
        assert all(r["submitted_date"] == today for r in rows), (
            "R1a cross-position bulk: all 3 join rows for the writer "
            f"must share the same submitted_date. Got "
            f"{[r['submitted_date'] for r in rows]!r}"
        )

    def test_bulk_ui_button_drives_dispatcher_end_to_end(self, db):
        """Scenario: Bulk-action UI control is user-observable
        (BDD R1a, response to UX-mgr round-1 blocker #1). The
        Opportunities page must expose a multiselect + "Mark applied"
        button — clicking it through AppTest must fire the dispatcher
        and apply the R1 cascade to every selected row."""
        # Distinct names so the multiselect's labels are unambiguous —
        # Streamlit matches options by label, so identical labels would
        # collapse on the AppTest rerun (Day-1 debug finding).
        ids = [
            database.add_position(make_position(overrides={"position_name": f"Pos{i}"}))
            for i in range(4)
        ]
        at = AppTest.from_file(
            "pages/1_Opportunities.py", default_timeout=10
        )
        at.run()
        at.multiselect(key="opps_bulk_multiselect").set_value(ids[:2])
        at.button(key="opps_bulk_mark_applied").click().run()

        df = database.get_all_positions()
        promoted = set(df[df["status"] == config.STATUS_APPLIED]["id"].tolist())
        assert promoted == set(ids[:2]), (
            f"R1a UI contract: clicking 'Mark applied' on 2 selected rows "
            f"must promote exactly those 2 to [APPLIED]. Got {promoted!r}."
        )

    def test_bulk_action_preserves_table_selection(self, db):
        """Scenario (state preservation): Bulk action keeps table
        selection (BDD R1a, dev-notes gotcha #11).

        Contract: a bulk-action dispatch must NOT clobber the
        selection state and MUST trigger the documented R1 cascade
        for every selected row. The page wires ``_skip_table_reset``
        internally — the user-observable contract is that selected
        ids survive the dispatch rerun AND the data effect lands."""
        _require(R1A_SYMBOLS)

        ids = [database.add_position(make_position()) for _ in range(5)]
        at = AppTest.from_file(
            "pages/1_Opportunities.py", default_timeout=10
        )
        at.session_state["opps_bulk_selected_ids"] = set(ids[:3])
        at.session_state["opps_bulk_pending_action"] = "promote_to_applied"
        at.run()

        # Selection set survives the dispatch rerun.
        selected = (
            at.session_state["opps_bulk_selected_ids"]
            if "opps_bulk_selected_ids" in at.session_state
            else None
        )
        assert selected == set(ids[:3]), (
            "R1a contract: selected-row set must persist across the "
            f"bulk-action rerun. Got {selected!r}."
        )
        # Pending action sentinel is consumed (one-shot dispatch).
        assert "opps_bulk_pending_action" not in at.session_state, (
            "R1a contract: pending-action sentinel must be popped by "
            "the dispatcher so it does not re-fire on subsequent reruns."
        )
        # Data effect: the 3 selected rows are now in [APPLIED].
        df = database.get_all_positions()
        promoted = set(df[df["status"] == config.STATUS_APPLIED]["id"].tolist())
        assert promoted == set(ids[:3]), (
            f"R1a cascade contract: expected {set(ids[:3])!r} promoted "
            f"to [APPLIED]; got {promoted!r}"
        )


# ── R1b: in-UI settings page ───────────────────────────────────────────────────


class TestR1bSettings:
    """In-UI page for tunable thresholds + append-only vocabulary.
    Writes to a JSON override file the import-time loader picks up so
    S5 (config.py invariants) holds.

    Acceptance contracts: BDD UX_BDD_Scenarios_2026-05-22 §v0.16.0 R1b."""

    XFAIL_REASON = (
        "Planned v0.16.0 R1b: in-UI settings page not yet shipped. "
        "pages/5_Settings.py does not exist; load_settings / "
        "save_settings are not on database (or wherever the loader lives)."
    )

    def test_threshold_change_re_bands_upcoming_panel(self, db, tmp_path, monkeypatch):
        """Scenario: Threshold change re-bands the Upcoming panel
        (BDD R1b). Picks an override value that exists in
        ``UPCOMING_WINDOW_OPTIONS`` so the segmented control snaps to
        it exactly — verifying the dashboard actually consumes the
        override, not just stores it (response to UX-mgr round-1
        blocker #3)."""
        _require(R1B_SYMBOLS)

        override = config.UPCOMING_WINDOW_OPTIONS[-1]  # e.g. 90
        config_default = config.DEADLINE_ALERT_DAYS  # e.g. 30
        assert override != config_default, (
            "Test fixture invariant: pick an override that differs from "
            "the config default so a passing assert proves the override "
            "actually propagates."
        )

        _planned("save_settings")({"DEADLINE_ALERT_DAYS": override})

        loaded = _planned("load_settings")()
        assert loaded["DEADLINE_ALERT_DAYS"] == override, (
            "R1b contract: save_settings → load_settings must round-trip "
            f"DEADLINE_ALERT_DAYS={override}. Got {loaded!r}."
        )

        at = AppTest.from_file("app.py", default_timeout=10).run()

        effective = (
            at.session_state["effective_deadline_alert_days"]
            if "effective_deadline_alert_days" in at.session_state
            else None
        )
        assert effective == override, (
            "R1b: dashboard must read the override value, not the "
            f"config.py default. session_state marker: {effective!r}"
        )
        # User-observable contract: the Upcoming-panel segmented control
        # default reflects the override, not the config default.
        seg = at.segmented_control(key="upcoming_window")
        rendered_default = seg.value if seg is not None else None
        assert rendered_default == override, (
            "R1b user-observable contract: with the override set to "
            f"{override}, the Upcoming-panel segmented control must "
            f"render with default={override}, not the config default "
            f"({config_default}). Got rendered_default={rendered_default!r}."
        )

    def test_vocabulary_additions_are_append_only(self, db):
        """Scenario: Vocabulary additions are append-only (BDD R1b).
        Removing an in-use status must be blocked; appending succeeds."""
        _require(R1B_SYMBOLS + ("update_status_vocabulary",))

        pid = database.add_position(make_position())
        database.upsert_application(
            pid, {"applied_date": date.today().isoformat()}
        )

        # Removing [APPLIED] while a row holds it must be blocked.
        with pytest.raises(ValueError) as exc:
            _planned("update_status_vocabulary")(
                remove=[config.STATUS_APPLIED]
            )
        assert config.STATUS_APPLIED in str(exc.value)

        # Appending a new status must succeed.
        _planned("update_status_vocabulary")(append=["[GHOSTED]"])
        loaded = _planned("load_settings")()
        assert "[GHOSTED]" in loaded.get("STATUS_VALUES", []), (
            "R1b append-only contract: new [GHOSTED] must land in the "
            f"persisted STATUS_VALUES. Got {loaded.get('STATUS_VALUES')!r}."
        )

    def test_settings_page_ui_drives_persistence_end_to_end(self, db):
        """Scenario: Settings page is user-observable (BDD R1b,
        response to UX-mgr round-1 blocker #2). The page at
        pages/5_Settings.py must expose number inputs + a Save
        button — driving them via AppTest must round-trip through
        save_settings → load_settings."""
        at = AppTest.from_file("pages/5_Settings.py", default_timeout=10).run()
        at.number_input(key="settings_deadline_alert_days").set_value(3)
        at.button(key="settings_thresholds_submit").click().run()

        loaded = database.load_settings()
        assert loaded["DEADLINE_ALERT_DAYS"] == 3, (
            "R1b UI contract: clicking 'Save thresholds' with "
            "DEADLINE_ALERT_DAYS=3 must persist via save_settings. "
            f"Got loaded={loaded!r}."
        )

    def test_invalid_threshold_rejected_at_boundary(self, db):
        """Scenario: Invalid threshold rejected at the boundary
        (BDD R1b). DEADLINE_ALERT_DAYS = -1 must error, leave the
        override file unwritten, and not change the in-memory value."""
        _require(R1B_SYMBOLS)

        before = _planned("load_settings")().get("DEADLINE_ALERT_DAYS")

        with pytest.raises(ValueError) as exc:
            _planned("save_settings")({"DEADLINE_ALERT_DAYS": -1})
        assert "DEADLINE_ALERT_DAYS" in str(exc.value)

        after = _planned("load_settings")().get("DEADLINE_ALERT_DAYS")
        assert after == before, (
            f"R1b: failed save must not partially mutate state. "
            f"before={before!r} after={after!r}"
        )
