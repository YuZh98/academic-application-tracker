# tests/test_planned_v0_14.py
# Pinning tests for v0.14.0 close-out items per UX_Improvement_Plan_2026-05-22.
#
# All tests in this file are TDD red-phase contracts: they capture the
# acceptance criteria from UX_BDD_Scenarios_2026-05-22.md *before* the
# implementation lands. Every test is marked xfail(strict=False) with a
# reason linking the release that will make it pass. When the
# implementation merges, the xfail decorator comes off in the SAME PR
# that makes the test green — per universal CLAUDE.md §7 "no rule
# without enforcement".
#
# These are pinning contracts, not aspirational comments. They run on
# every CI build today; they just XFAIL until the listed PR lands.

from datetime import date

import config
import database
from tests.conftest import make_position

# ── B1: symmetric reverse cascade on delete_interview ──────────────────────────


class TestB1ReverseCascade:
    """Reverse R2 cascade on delete_interview — symmetric to the
    forward cascade at database.py:629.

    Forward (today): add_interview promotes [APPLIED] → [INTERVIEW]
    when propagate_status=True and the position is in [APPLIED].

    Reverse (planned v0.14.0 B1): delete_interview must retract
    [INTERVIEW] → [APPLIED] when the deleted row was the last
    interview AND the position is currently in [INTERVIEW]. Other
    statuses (e.g. [OFFER]) are untouched — the cascade is symmetric
    only with respect to [APPLIED] ↔ [INTERVIEW].

    Source defect: database.py:707–719 deletes the row but never
    inspects status. Verified against feat/ui-redesign-v0.14.0 @
    2ded3ba (Appendix A of UX field study)."""

    def test_deleting_only_interview_retracts_interview_status(self, db):
        """Scenario: Deleting the only interview row retracts
        [INTERVIEW] status (BDD §v0.14.0 / R0c)."""
        pid = database.add_position(make_position())
        database.upsert_application(
            pid, {"applied_date": date.today().isoformat()}
        )
        res = database.add_interview(pid, {"scheduled_date": "2026-05-01"})

        # Precondition: forward cascade fired.
        with database._connect() as conn:
            pre = conn.execute(
                "SELECT status FROM positions WHERE id = ?", (pid,)
            ).fetchone()["status"]
        assert pre == config.STATUS_INTERVIEW, (
            "Setup invariant: forward cascade should have promoted to "
            f"{config.STATUS_INTERVIEW}; got {pre!r}"
        )

        database.delete_interview(res["id"])

        with database._connect() as conn:
            post = conn.execute(
                "SELECT status FROM positions WHERE id = ?", (pid,)
            ).fetchone()["status"]
        assert post == config.STATUS_APPLIED, (
            "B1 contract: deleting the only interview row must retract "
            f"status from {config.STATUS_INTERVIEW} to "
            f"{config.STATUS_APPLIED}. Got {post!r}."
        )

    def test_deleting_one_of_many_interviews_keeps_interview_status(self, db):
        """Scenario: Deleting one of many interview rows does not
        retract (BDD §v0.14.0).

        Passes today (delete_interview never touches status, so a 2-row
        position trivially keeps [INTERVIEW] after one delete). Pinned
        here as a *regression* contract: when B1 lands, the narrow
        precondition (zero remaining interviews) must still hold so
        this test stays green."""
        pid = database.add_position(make_position())
        database.upsert_application(
            pid, {"applied_date": date.today().isoformat()}
        )
        res1 = database.add_interview(pid, {"scheduled_date": "2026-05-01"})
        database.add_interview(pid, {"scheduled_date": "2026-06-01"})

        database.delete_interview(res1["id"])

        with database._connect() as conn:
            post = conn.execute(
                "SELECT status FROM positions WHERE id = ?", (pid,)
            ).fetchone()["status"]
        assert post == config.STATUS_INTERVIEW, (
            "B1 narrow precondition: cascade only fires when zero "
            f"interviews remain. One row survives — status must stay "
            f"{config.STATUS_INTERVIEW}. Got {post!r}."
        )

    def test_reverse_cascade_does_not_fire_for_terminal_status(self, db):
        """Scenario: Reverse cascade does not fire for non-INTERVIEW
        positions (BDD §v0.14.0). Symmetric with the forward cascade's
        narrow precondition at database.py:629 — guard on current
        status, not just on row count.

        Passes today (delete_interview never touches status). Pinned
        as a regression contract: B1's implementation must guard on
        ``current_status == STATUS_INTERVIEW`` before retracting, or
        this test will start failing once the cascade lands."""
        pid = database.add_position(make_position())
        database.upsert_application(
            pid, {"applied_date": date.today().isoformat()}
        )
        res = database.add_interview(pid, {"scheduled_date": "2026-05-01"})

        # Promote past [INTERVIEW] to [OFFER] via the forward path.
        database.upsert_application(
            pid, {"response_type": config.RESPONSE_TYPE_OFFER}
        )
        with database._connect() as conn:
            mid = conn.execute(
                "SELECT status FROM positions WHERE id = ?", (pid,)
            ).fetchone()["status"]
        assert mid == config.STATUS_OFFER, (
            f"Setup invariant: position should be in {config.STATUS_OFFER}; "
            f"got {mid!r}"
        )

        database.delete_interview(res["id"])

        with database._connect() as conn:
            post = conn.execute(
                "SELECT status FROM positions WHERE id = ?", (pid,)
            ).fetchone()["status"]
        assert post == config.STATUS_OFFER, (
            "B1 narrow precondition: reverse cascade must not fire when "
            f"position has moved past [INTERVIEW]. Expected "
            f"{config.STATUS_OFFER}; got {post!r}."
        )


# ── B3 (partial): schema-UI binding pinning test ───────────────────────────────


class TestB3SchemaUiPin:
    """Asserts every nullable `positions` column has a UI binding in
    either Quick-Add or the Edit panel — i.e. no column exists on disk
    that the user cannot read or write through the UI.

    Source motivation: UX field study P1 quote — "They built half the
    schema and then forgot to wire it up." Verified 10 nullable columns
    previously unused by the UI at database.py:77–94.

    Plan §3 deviation #2 staged this as a v0.14.0 xfail with R0b
    closing it in v0.15.0; in practice R0b shipped on the same branch
    so the test landed green from the first push (recorded as
    "stronger than promised" in the round-2 review)."""

    # Columns the binding rule excludes by design — housekeeping or
    # config-managed families. The rule applies to everything else in
    # the live schema.
    HOUSEKEEPING = frozenset(
        {"id", "created_at", "updated_at", "status", "priority", "position_name"}
    )

    @staticmethod
    def _live_schema_columns() -> set[str]:
        with database._connect() as conn:
            return {row["name"] for row in conn.execute("PRAGMA table_info(positions)").fetchall()}

    @staticmethod
    def _config_managed_columns() -> set[str]:
        cols: set[str] = set()
        for req_col, done_col, _label in config.REQUIREMENT_DOCS:
            cols.add(req_col)
            cols.add(done_col)
        return cols

    @staticmethod
    def _ui_referenced_columns() -> set[str]:
        """Scan Quick-Add + Edit-panel source for column references.

        Approximation, not perfect: matches `qa_<col>` and `edit_<col>`
        widget keys and explicit `"<col>":` fields-dict literals in
        pages/1_Opportunities.py. False negatives are conservative —
        if the test reports a column missing, the wireup really is
        missing or the widget key does not follow the convention from
        GUIDELINES §3."""
        import re
        from pathlib import Path

        page = Path("pages/1_Opportunities.py").read_text(encoding="utf-8")
        # qa_<name>_ or edit_<name>_ or edit_<name> at line-end / form-end.
        widget_keys = set(re.findall(r"\b(?:qa|edit)_([a-z_]+?)(?:_\d+|_nonce|\b)", page))
        # Plain fields-dict literals: "<col>": <expr>
        dict_keys = set(re.findall(r'"([a-z_]+)":', page))
        return widget_keys | dict_keys

    def test_every_nullable_positions_column_has_ui_binding(self, db):
        """Scenario: Every nullable positions column reachable from
        UI (BDD §v0.14.0 / B3)."""
        schema_cols = self._live_schema_columns()
        excluded = self.HOUSEKEEPING | self._config_managed_columns()
        candidate_cols = schema_cols - excluded

        ui_cols = self._ui_referenced_columns()
        orphaned = candidate_cols - ui_cols

        assert orphaned == set(), (
            "B3 binding contract: every nullable positions column must "
            "appear as a widget key (qa_* or edit_*) or as a fields-dict "
            "key in pages/1_Opportunities.py. Orphan columns found:\n"
            f"  {sorted(orphaned)!r}\n"
            "Fix: ship R0b wireup (add to Edit panel; promote short-"
            "string ones to Quick-Add) and remove the xfail."
        )
