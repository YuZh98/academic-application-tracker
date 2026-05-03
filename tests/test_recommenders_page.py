# tests/test_recommenders_page.py
# Integration tests for pages/3_Recommenders.py using Streamlit AppTest.
#
# Phase 5 T4 coverage: page shell + Pending Alerts panel.
# Phase 5 T5/T6 coverage will be added in subsequent tiers.
#
# Uses the shared `db` fixture from tests/conftest.py so each test runs
# against a fresh temp SQLite DB. Never touches postdoc.db.
#
# AppTest access patterns (verified against Streamlit 1.56):
#   - `at.markdown[i].value` returns the raw markdown source string passed
#     to st.markdown(...) — multi-line card bodies come back as one element.
#   - `st.container(border=True)` is a CSS-styled wrapper; AppTest does not
#     surface a distinct element for it, so the bordered contract is pinned
#     via a source-level grep (same precedent as test_app_page.py T5).
#   - set_page_config is consumed before widgets render and does not appear
#     in the AppTest element tree — pinned via source grep (same precedent
#     as test_opportunities_page.py and test_applications_page.py).

import datetime
import pathlib

from streamlit.testing.v1 import AppTest

import database
from tests.conftest import make_position

PAGE = "pages/3_Recommenders.py"


def _run_page() -> AppTest:
    """Return a freshly-run AppTest for the Recommenders page."""
    at = AppTest.from_file(PAGE)
    at.run()
    return at


# ── Page config ───────────────────────────────────────────────────────────────


class TestPageConfig:
    def test_page_config_sets_wide_layout(self, db):
        """set_page_config must be called with layout='wide' per DESIGN §8.0
        / D14. Source-grep because AppTest consumes set_page_config before
        any widget renders."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert "st.set_page_config(" in src, f"{PAGE} must call st.set_page_config(...)."
        assert 'layout="wide"' in src, (
            f"{PAGE} must pass layout='wide' to set_page_config per DESIGN §8.0."
        )

    def test_page_title_is_recommenders(self, db):
        """st.title must read 'Recommenders'."""
        at = _run_page()
        assert not at.exception, f"Page raised: {at.exception}"
        assert any(t.value == "Recommenders" for t in at.title), (
            f"Expected st.title('Recommenders'); got {[t.value for t in at.title]}"
        )


# ── Pending Alerts panel ──────────────────────────────────────────────────────


class TestPendingAlertsPanel:
    """Phase 5 T4: Pending Alerts panel contract.

    Locked contract:
      - st.subheader("Pending Alerts") renders in BOTH empty and populated
        branches for page-height stability (mirrors dashboard T5 precedent).
      - Empty branch: st.info(EMPTY_COPY) verbatim, no alert cards.
      - Populated branch: one st.container(border=True) per distinct
        recommender_name (source-level pin). Each card is a single
        st.markdown block whose body starts with **⚠ {name}** and
        optionally includes ({relationship}) when the field is non-NULL.
        Each position owed appears as a bullet:
          - {institute}: {position_name} (asked {N}d ago, due {Mon D})
        Bare position_name when institute is empty; '—' when deadline NULL.
      - Reminder helpers (mailto + LLM prompts) belong to Phase 5 T6, NOT
        here — T4 only renders the alert cards.
    """

    SUBHEADER = "Pending Alerts"
    EMPTY_COPY = "No pending recommenders."
    BORDER_SOURCE = "st.container(border=True)"
    WARN_GLYPH = "⚠"

    @classmethod
    def _alert_markdowns(cls, at: AppTest) -> list[str]:
        """Markdown bodies that look like a Pending-Alert card.

        Identified by the warn-glyph — robust against any future
        st.markdown calls elsewhere on the page."""
        return [m.value for m in at.markdown if cls.WARN_GLYPH in m.value]

    @staticmethod
    def _seed_pending(
        days_ago: int = 14,
        position_name: str = "BioStats Postdoc",
        institute: str = "Stanford",
        recommender_name: str = "Dr. Smith",
        relationship: str | None = "PhD Advisor",
        deadline_offset: int | None = 10,
    ) -> None:
        """Seed one pending recommender (asked >= RECOMMENDER_ALERT_DAYS
        ago, submitted_date NULL) so the alert panel fires."""
        pos_id = database.add_position(
            make_position(
                {
                    "position_name": position_name,
                    "institute": institute,
                    "deadline_date": (
                        (
                            datetime.date.today() + datetime.timedelta(days=deadline_offset)
                        ).isoformat()
                        if deadline_offset is not None
                        else None
                    ),
                }
            )
        )
        database.add_recommender(
            pos_id,
            {
                "recommender_name": recommender_name,
                "relationship": relationship,
                "asked_date": (
                    datetime.date.today() - datetime.timedelta(days=days_ago)
                ).isoformat(),
            },
        )

    # ── Group A: subheader stability ─────────────────────────────────────────

    def test_subheader_renders_on_empty_db(self, db):
        """Layout stability: subheader renders even with no pending
        recommenders so the panel anchor is always visible."""
        at = _run_page()
        assert not at.exception, f"Page raised: {at.exception}"
        assert any(s.value == self.SUBHEADER for s in at.subheader), (
            f"Expected st.subheader({self.SUBHEADER!r}) on empty DB; "
            f"got {[s.value for s in at.subheader]}"
        )

    def test_subheader_renders_on_populated_db(self, db):
        """Same layout-stability invariant on the populated path."""
        self._seed_pending()
        at = _run_page()
        assert any(s.value == self.SUBHEADER for s in at.subheader), (
            f"Expected st.subheader({self.SUBHEADER!r}) on populated DB; "
            f"got {[s.value for s in at.subheader]}"
        )

    # ── Group B: empty branch ────────────────────────────────────────────────

    def test_empty_state_shows_info_message(self, db):
        """Empty DB: exactly one st.info matching EMPTY_COPY verbatim."""
        at = _run_page()
        matching = [i for i in at.info if i.value == self.EMPTY_COPY]
        assert len(matching) == 1, (
            f"Expected exactly one st.info({self.EMPTY_COPY!r}); "
            f"got info bodies: {[i.value for i in at.info]}"
        )

    def test_empty_state_has_no_alert_cards(self, db):
        """Empty DB: no markdown cards with the warn glyph."""
        at = _run_page()
        assert self._alert_markdowns(at) == [], (
            f"Empty DB: no alert cards should render. Got: {self._alert_markdowns(at)}"
        )

    # ── Group C: populated branch ────────────────────────────────────────────

    def test_populated_suppresses_empty_info(self, db):
        """Populated DB: the empty-state info must NOT appear
        (branches are mutually exclusive)."""
        self._seed_pending()
        at = _run_page()
        assert all(i.value != self.EMPTY_COPY for i in at.info), (
            f"Populated DB: empty-state info must not render. "
            f"Got info bodies: {[i.value for i in at.info]}"
        )

    def test_pending_recommender_renders_one_card(self, db):
        """One pending recommender → exactly one alert card."""
        self._seed_pending()
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert len(bodies) == 1, f"Expected 1 alert card; got {len(bodies)}: {bodies}"

    def test_uses_bordered_containers(self, db):
        """Each card wraps in st.container(border=True). Pinned at the
        source level — AppTest does not surface container styling."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert self.BORDER_SOURCE in src, (
            f"{PAGE} must call {self.BORDER_SOURCE!r} for alert cards."
        )

    # ── Group D: card content ────────────────────────────────────────────────

    def test_recommender_name_in_card_header(self, db):
        """The recommender's name must appear in the card body."""
        self._seed_pending(recommender_name="Dr. Jones")
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert any("Dr. Jones" in b for b in bodies), (
            f"Expected 'Dr. Jones' in a card body; got {bodies}"
        )

    def test_relationship_shown_when_present(self, db):
        """A non-NULL relationship must appear in the card body."""
        self._seed_pending(relationship="Committee Member")
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert any("Committee Member" in b for b in bodies), (
            f"Expected 'Committee Member' in a card body; got {bodies}"
        )

    def test_relationship_absent_when_null(self, db):
        """A NULL relationship must not produce a literal 'None' string."""
        self._seed_pending(relationship=None)
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert len(bodies) == 1
        assert "None" not in bodies[0], (
            f"NULL relationship must not render as 'None'; got {bodies[0]!r}"
        )

    def test_position_label_includes_institute(self, db):
        """When institute is non-empty the label reads '{institute}: {name}'."""
        self._seed_pending(position_name="CSAIL Postdoc", institute="MIT")
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert any("MIT" in b and "CSAIL Postdoc" in b for b in bodies), (
            f"Expected 'MIT' and 'CSAIL Postdoc' in card bodies; got {bodies}"
        )

    def test_position_label_bare_when_no_institute(self, db):
        """When institute is empty the label is bare position_name,
        no colon prefix."""
        self._seed_pending(position_name="Solo Postdoc", institute="")
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert any("Solo Postdoc" in b for b in bodies), (
            f"Expected 'Solo Postdoc' in card bodies; got {bodies}"
        )
        assert all(": Solo Postdoc" not in b for b in bodies), (
            f"Empty institute must not produce a colon prefix; got {bodies}"
        )

    def test_due_date_formatted_as_mon_d(self, db):
        """Deadline renders as 'Mon D' (e.g. 'Jun 5'), no year."""
        self._seed_pending(deadline_offset=5)
        expected = datetime.date.today() + datetime.timedelta(days=5)
        expected_str = f"{expected.strftime('%b')} {expected.day}"
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert any(expected_str in b for b in bodies), (
            f"Expected due-date '{expected_str}' in card bodies; got {bodies}"
        )

    def test_null_deadline_shows_em_dash(self, db):
        """NULL deadline_date renders as '—' (em-dash), not 'None' or ''."""
        self._seed_pending(deadline_offset=None)
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert any("—" in b for b in bodies), (
            f"Expected em-dash for NULL deadline in card bodies; got {bodies}"
        )

    # ── Group E: grouping ────────────────────────────────────────────────────

    def test_multiple_positions_same_recommender_one_card(self, db):
        """One recommender owing letters for two positions → single card
        listing both positions (groupby aggregation contract)."""
        pos_a = database.add_position(make_position({"position_name": "Pos A"}))
        pos_b = database.add_position(make_position({"position_name": "Pos B"}))
        asked = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
        for pos_id in (pos_a, pos_b):
            database.add_recommender(
                pos_id,
                {
                    "recommender_name": "Dr. Smith",
                    "asked_date": asked,
                },
            )
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert len(bodies) == 1, (
            f"One recommender + two positions must produce 1 card; got {len(bodies)}: {bodies}"
        )
        assert "Pos A" in bodies[0] and "Pos B" in bodies[0], (
            f"Both positions must appear in the single card; got {bodies[0]!r}"
        )

    def test_multiple_recommenders_multiple_cards(self, db):
        """Two distinct recommenders → two separate cards."""
        self._seed_pending(recommender_name="Dr. Alpha", position_name="Alpha Postdoc")
        self._seed_pending(recommender_name="Dr. Beta", position_name="Beta Postdoc")
        at = _run_page()
        bodies = self._alert_markdowns(at)
        assert len(bodies) == 2, (
            f"Two recommenders must produce 2 cards; got {len(bodies)}: {bodies}"
        )
