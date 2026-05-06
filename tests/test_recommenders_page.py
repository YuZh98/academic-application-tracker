# tests/test_recommenders_page.py
# Integration tests for pages/3_Recommenders.py using Streamlit AppTest.
#
# Phase 5 T4 coverage: page shell + Pending Alerts panel.
# Phase 5 T5 coverage: All Recommenders table + add form + inline edit.
# Phase 5 T6 coverage will be added in the next tier.
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

import pytest
from streamlit.testing.v1 import AppTest

import config
import database
from tests.conftest import make_position
from tests.helpers import decode_mailto, link_buttons

PAGE = "pages/3_Recommenders.py"

# T5 widget keys / sentinels — pinned in AGENTS.md "Immediate task" + DESIGN
# §8.4. Names follow the project's `recs_` widget-key prefix (GUIDELINES §13).
TABLE_KEY = "recs_table"
FILTER_POSITION_KEY = "recs_filter_position"
FILTER_RECOMMENDER_KEY = "recs_filter_recommender"

ADD_FORM_ID = "recs_add_form"
ADD_POSITION_KEY = "recs_add_position"
ADD_NAME_KEY = "recs_add_name"
ADD_RELATIONSHIP_KEY = "recs_add_relationship"
ADD_ASKED_DATE_KEY = "recs_add_asked_date"
ADD_SUBMIT_KEY = "recs_add_submit"

EDIT_FORM_ID = "recs_edit_form"
EDIT_ASKED_DATE_KEY = "recs_edit_asked_date"
EDIT_CONFIRMED_KEY = "recs_edit_confirmed"
EDIT_SUBMITTED_DATE_KEY = "recs_edit_submitted_date"
EDIT_REMINDER_SENT_KEY = "recs_edit_reminder_sent"
EDIT_REMINDER_DATE_KEY = "recs_edit_reminder_sent_date"
EDIT_NOTES_KEY = "recs_edit_notes"
EDIT_SUBMIT_KEY = "recs_edit_submit"

DELETE_BUTTON_KEY = "recs_edit_delete"
DELETE_CONFIRM_KEY = "recs_delete_confirm"
DELETE_CANCEL_KEY = "recs_delete_cancel"

# Internal sentinels — page-prefixed so they don't collide with the
# Opportunities / Applications page state machinery.
SELECTED_REC_ID_KEY = "recs_selected_id"
EDIT_FORM_SID_KEY = "_recs_edit_form_sid"
SKIP_TABLE_RESET_KEY = "_recs_skip_table_reset"
DELETE_TARGET_ID_KEY = "_recs_delete_target_id"
DELETE_TARGET_NAME_KEY = "_recs_delete_target_name"

EM_DASH = "—"


def _select_row(at: AppTest, row_index: int) -> None:
    """Inject single-row dataframe selection + rerun. AppTest's Dataframe
    element exposes no click-a-row API, so the test writes the protobuf-
    shaped selection state directly. Mirror of the helpers in
    test_opportunities_page.py / test_applications_page.py — the shape
    matches what Streamlit 1.56 produces for ``on_select='rerun'`` +
    ``selection_mode='single-row'``."""
    at.session_state[TABLE_KEY] = {"selection": {"rows": [row_index], "columns": []}}
    at.run()


def _keep_selection(at: AppTest, row_index: int) -> None:
    """Re-inject selection state WITHOUT rerunning.

    AppTest does not persist the dataframe event across reruns (gotcha
    #11). Multi-step flows that span an internal rerun (a Save handler
    that calls ``st.rerun()``, a button click followed by ``at.run()``)
    need this to mimic the browser-side selection persistence."""
    at.session_state[TABLE_KEY] = {"selection": {"rows": [row_index], "columns": []}}


def _ss_or_none(at: AppTest, key: str):
    """Read ``at.session_state[key]`` safely, returning None if absent.
    AppTest's session_state wrapper does NOT support ``.get()``."""
    return at.session_state[key] if key in at.session_state else None


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
    """Phase 5 T4: Recommender Alerts panel contract.

    Locked contract:
      - st.subheader("Recommender Alerts") renders in BOTH empty and populated
        branches for page-height stability (mirrors dashboard T5 precedent).
      - Empty branch: st.info(EMPTY_COPY) verbatim, no alert cards.
      - Populated branch: one st.container(border=True) per distinct
        recommender_name (source-level pin). Each card is a single
        st.markdown block whose body starts with ⚠️ **{name}** and
        optionally includes ({relationship}) when the field is non-NULL.
        Each position owed appears as a bullet:
          - {institute}: {position_name} (asked {N}d ago, due {Mon D})
        Bare position_name when institute is empty; '—' when deadline NULL.
      - Reminder helpers (mailto + LLM prompts) belong to Phase 5 T6, NOT
        here — T4 only renders the alert cards.
    """

    SUBHEADER = "Recommender Alerts"
    # Pin against the constant by name so a future wording edit in
    # config.py flows through here automatically — no test churn on
    # copy updates.
    EMPTY_COPY = config.EMPTY_PENDING_RECOMMENDERS
    BORDER_SOURCE = "st.container(border=True)"
    WARN_GLYPH = "⚠️"

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


# ── T5 helpers ────────────────────────────────────────────────────────────────


def _seed_position(name: str = "BioStats Postdoc", institute: str = "Stanford") -> int:
    """Add one position via the canonical add_position path. Returns its
    new id."""
    return database.add_position(make_position({"position_name": name, "institute": institute}))


def _seed_recommender(
    pos_id: int,
    *,
    recommender_name: str = "Dr. Smith",
    relationship: str | None = "PhD Advisor",
    asked_date: str | None = None,
    confirmed: int | None = None,
    submitted_date: str | None = None,
    reminder_sent: int = 0,
    reminder_sent_date: str | None = None,
    notes: str | None = None,
) -> int:
    """Insert a recommender row via the canonical add_recommender writer."""
    fields: dict = {
        "recommender_name": recommender_name,
        "relationship": relationship,
        "asked_date": asked_date,
        "confirmed": confirmed,
        "submitted_date": submitted_date,
        "reminder_sent": reminder_sent,
        "reminder_sent_date": reminder_sent_date,
        "notes": notes,
    }
    return database.add_recommender(pos_id, fields)


# ── T5-A: All Recommenders section header + filters ─────────────────────────


class TestAllRecommendersSection:
    """T5-A: the page renders an 'All Recommenders' subheader BELOW the
    Pending Alerts panel. Layout-stability anchor — the subheader exists
    even on an empty DB, mirroring T4's Pending-Alerts-stays-visible
    rule and the dashboard T5 / Applications T1-B precedents."""

    SUBHEADER = "All Recommenders"

    def test_subheader_renders_on_empty_db(self, db):
        at = _run_page()
        assert not at.exception, f"Page raised: {at.exception}"
        assert any(s.value == self.SUBHEADER for s in at.subheader), (
            f"Expected st.subheader({self.SUBHEADER!r}) on empty DB; "
            f"got {[s.value for s in at.subheader]}"
        )

    def test_subheader_renders_on_populated_db(self, db):
        pid = _seed_position()
        _seed_recommender(pid)
        at = _run_page()
        assert any(s.value == self.SUBHEADER for s in at.subheader), (
            f"Expected st.subheader({self.SUBHEADER!r}) on populated DB; "
            f"got {[s.value for s in at.subheader]}"
        )


class TestAllRecommendersFilters:
    """T5-A: two filter selectboxes — by position (`recs_filter_position`)
    and by recommender name (`recs_filter_recommender`). Both default to
    'All'; selecting a specific value narrows the table to matching rows."""

    ALL = "All"

    def test_position_filter_renders(self, db):
        at = _run_page()
        sb = at.selectbox(key=FILTER_POSITION_KEY)
        assert sb is not None, (
            f"Page must render a selectbox with key={FILTER_POSITION_KEY!r} "
            f"for the position filter."
        )

    def test_recommender_filter_renders(self, db):
        at = _run_page()
        sb = at.selectbox(key=FILTER_RECOMMENDER_KEY)
        assert sb is not None, (
            f"Page must render a selectbox with key={FILTER_RECOMMENDER_KEY!r} "
            f"for the recommender-name filter."
        )

    def test_position_filter_default_is_all(self, db):
        _seed_position()
        at = _run_page()
        assert at.selectbox(key=FILTER_POSITION_KEY).value == self.ALL, (
            f"Position filter default must be {self.ALL!r}; got "
            f"{at.selectbox(key=FILTER_POSITION_KEY).value!r}"
        )

    def test_recommender_filter_default_is_all(self, db):
        pid = _seed_position()
        _seed_recommender(pid)
        at = _run_page()
        assert at.selectbox(key=FILTER_RECOMMENDER_KEY).value == self.ALL, (
            f"Recommender filter default must be {self.ALL!r}; got "
            f"{at.selectbox(key=FILTER_RECOMMENDER_KEY).value!r}"
        )

    def test_position_filter_options_include_seeded_positions(self, db):
        _seed_position(name="Alpha", institute="MIT")
        _seed_position(name="Beta", institute="Stanford")
        at = _run_page()
        opts = list(at.selectbox(key=FILTER_POSITION_KEY).options)
        # The page must offer a sentinel + every seeded position. Exact
        # label format isn't pinned — what matters is the user can find
        # the position by something they recognise (institute or name).
        assert opts[0] == self.ALL, (
            f"Position filter first option must be {self.ALL!r} sentinel; got {opts!r}"
        )
        joined = " ".join(opts)
        for token in ("Alpha", "Beta", "MIT", "Stanford"):
            assert token in joined, (
                f"Position filter must surface {token!r} in its option labels; got options={opts!r}"
            )

    def test_recommender_filter_options_include_seeded_names(self, db):
        pid_a = _seed_position(name="Alpha")
        pid_b = _seed_position(name="Beta")
        _seed_recommender(pid_a, recommender_name="Dr. Foo")
        _seed_recommender(pid_b, recommender_name="Dr. Bar")
        at = _run_page()
        opts = list(at.selectbox(key=FILTER_RECOMMENDER_KEY).options)
        assert opts[0] == self.ALL, (
            f"Recommender filter first option must be {self.ALL!r}; got {opts!r}"
        )
        for name in ("Dr. Foo", "Dr. Bar"):
            assert name in opts, f"Recommender filter options must include {name!r}; got {opts!r}"

    def test_recommender_filter_dedupes_repeated_names(self, db):
        """Two recommender rows for the same person across different
        positions must surface as ONE option in the filter — duplicates
        in the dropdown are noise."""
        pid_a = _seed_position(name="Alpha")
        pid_b = _seed_position(name="Beta")
        _seed_recommender(pid_a, recommender_name="Dr. Smith")
        _seed_recommender(pid_b, recommender_name="Dr. Smith")
        at = _run_page()
        opts = list(at.selectbox(key=FILTER_RECOMMENDER_KEY).options)
        # 'Dr. Smith' must appear at most once.
        assert opts.count("Dr. Smith") == 1, (
            f"Recommender filter must dedupe repeated names; got {opts!r}"
        )


# ── T5-A: All Recommenders table ─────────────────────────────────────────────


class TestAllRecommendersTable:
    """T5-A: read-only ``st.dataframe`` of all recommenders joined with
    position name. Columns (in order): Position · Recommender ·
    Relationship · Asked · Confirmed · Submitted. Driven by
    ``database.get_all_recommenders()``."""

    DISPLAY_COLUMNS = [
        "Position",
        "Recommender",
        "Relationship",
        "Asked",
        "Confirmed",
        "Submitted",
    ]

    def _table_df(self, at: AppTest):
        """Return the All-Recommenders dataframe value from the AppTest
        element tree.

        The page renders the dataframe with key ``recs_table`` for T5-A;
        AppTest exposes dataframes positionally via ``at.dataframe``.
        Indexing the last element here ducks any future addition of a
        sibling dataframe earlier in the page (e.g. a per-position
        summary block) that would otherwise shift positional indices."""
        return at.dataframe[-1].value

    def test_table_renders_with_six_display_columns(self, db):
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith")
        at = _run_page()
        df = self._table_df(at)
        assert list(df.columns) == self.DISPLAY_COLUMNS, (
            f"Table columns must be {self.DISPLAY_COLUMNS!r} in this order; "
            f"got {list(df.columns)!r}"
        )

    def test_table_lists_seeded_recommender(self, db):
        pid = _seed_position(name="Alpha", institute="MIT")
        _seed_recommender(
            pid,
            recommender_name="Dr. Smith",
            relationship="PhD Advisor",
            asked_date="2026-04-01",
        )
        at = _run_page()
        df = self._table_df(at)
        assert len(df) == 1, f"One recommender → one row; got {len(df)}"
        recs = list(df["Recommender"])
        assert any("Dr. Smith" in str(v) for v in recs), (
            f"Expected 'Dr. Smith' in Recommender column; got {recs!r}"
        )

    def test_position_filter_narrows_table(self, db):
        pid_a = _seed_position(name="Alpha")
        pid_b = _seed_position(name="Beta")
        _seed_recommender(pid_a, recommender_name="Dr. Foo")
        _seed_recommender(pid_b, recommender_name="Dr. Bar")

        at = _run_page()
        # Pick whichever option carries the 'Alpha' token (label format
        # isn't pinned by spec — the option is whatever the page renders
        # for pid_a). Mirror of the Applications-page filter pattern.
        sb = at.selectbox(key=FILTER_POSITION_KEY)
        alpha_opt = next(o for o in sb.options if "Alpha" in str(o))
        sb.select(alpha_opt)
        at.run()

        df = self._table_df(at)
        recs = [str(v) for v in df["Recommender"]]
        assert any("Dr. Foo" in v for v in recs), (
            f"Filtering to position 'Alpha' must keep its recommender; got Recommender={recs!r}"
        )
        assert not any("Dr. Bar" in v for v in recs), (
            f"Filtering to position 'Alpha' must hide other positions' "
            f"recommenders; got Recommender={recs!r}"
        )

    def test_recommender_filter_narrows_table(self, db):
        pid_a = _seed_position(name="Alpha")
        pid_b = _seed_position(name="Beta")
        _seed_recommender(pid_a, recommender_name="Dr. Foo")
        _seed_recommender(pid_b, recommender_name="Dr. Bar")

        at = _run_page()
        at.selectbox(key=FILTER_RECOMMENDER_KEY).select("Dr. Foo")
        at.run()

        df = self._table_df(at)
        recs = [str(v) for v in df["Recommender"]]
        assert recs == ["Dr. Foo"] or all("Dr. Foo" in v for v in recs), (
            f"Filtering to recommender 'Dr. Foo' must surface only its "
            f"rows; got Recommender={recs!r}"
        )

    def test_position_label_includes_institute(self, db):
        """Locked label format (DESIGN §8.4 + AGENTS §T5-B): position
        cells render as ``f'{institute}: {position_name}'`` when the
        institute is non-empty, bare ``position_name`` otherwise.
        Mirror of the Pending-Alerts-card label format from T4."""
        pid = _seed_position(name="Postdoc Slot", institute="MIT")
        _seed_recommender(pid)
        at = _run_page()
        df = self._table_df(at)
        positions = [str(v) for v in df["Position"]]
        assert any("MIT" in v and "Postdoc Slot" in v for v in positions), (
            f"Position cell must include institute + position_name; got {positions!r}"
        )

    def test_position_label_bare_when_no_institute(self, db):
        pid = _seed_position(name="Solo Postdoc", institute="")
        _seed_recommender(pid)
        at = _run_page()
        df = self._table_df(at)
        positions = [str(v) for v in df["Position"]]
        assert any("Solo Postdoc" in v for v in positions), (
            f"Bare position_name must appear in Position column; got {positions!r}"
        )
        assert all(": Solo Postdoc" not in v for v in positions), (
            f"Empty institute must not produce a colon prefix; got {positions!r}"
        )

    def test_confirmed_renders_yes_no_em_dash(self, db):
        """Confirmed is INTEGER tri-state (0/1/NULL). The column renders
        humans-friendly: NULL→'—', 0→'No', 1→'Yes'. The em-dash mirrors
        the same NULL placeholder used by the inline edit selectbox."""
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="A NULL", confirmed=None)
        _seed_recommender(pid, recommender_name="B No", confirmed=0)
        _seed_recommender(pid, recommender_name="C Yes", confirmed=1)

        at = _run_page()
        df = self._table_df(at)
        # Build a {recommender_name: confirmed_cell} map; the table
        # ordering is name-ASC per database.get_all_recommenders contract.
        cells = {str(name): str(conf) for name, conf in zip(df["Recommender"], df["Confirmed"])}
        assert cells["A NULL"] == EM_DASH, (
            f"Confirmed=NULL must render as {EM_DASH!r}; got {cells['A NULL']!r}"
        )
        assert cells["B No"] == "No", f"Confirmed=0 must render as 'No'; got {cells['B No']!r}"
        assert cells["C Yes"] == "Yes", f"Confirmed=1 must render as 'Yes'; got {cells['C Yes']!r}"

    def test_table_uses_get_all_recommenders(self, db, monkeypatch):
        """Source-of-truth pin: the table reads from
        ``database.get_all_recommenders``. Monkeypatching the function
        makes its rows appear (or disappear) from the page —
        confirming the page's read goes through the documented helper
        rather than reaching into SQL directly."""
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Real")

        # Patch get_all_recommenders to return an empty frame; the
        # table must reflect the empty view.
        import pandas as pd

        empty = pd.DataFrame(
            columns=[
                "id",
                "position_id",
                "recommender_name",
                "relationship",
                "asked_date",
                "confirmed",
                "submitted_date",
                "reminder_sent",
                "reminder_sent_date",
                "notes",
                "position_name",
                "institute",
            ]
        )
        monkeypatch.setattr(database, "get_all_recommenders", lambda: empty)
        at = _run_page()
        # The page may render an empty st.dataframe OR an empty-state
        # info; either way 'Dr. Real' must NOT appear (since the patched
        # reader returns nothing).
        for el in at.dataframe:
            try:
                cells = " ".join(str(v) for v in el.value.values.flatten())
            except Exception:
                continue
            assert "Dr. Real" not in cells, (
                f"Page must read recommender rows via get_all_recommenders "
                f"— monkeypatched empty result still surfaced 'Dr. Real'; "
                f"cells={cells!r}"
            )
        # pid is referenced for documentation only.
        assert pid > 0


# ── T5-B: Add recommender form ────────────────────────────────────────────────


class TestAddRecommenderFormRender:
    """T5-B: ``st.form('recs_add_form')`` with four widgets — position
    selectbox, name text input, relationship selectbox, asked-date date
    input. Submit fires ``database.add_recommender(pos_id, fields)``."""

    def test_add_form_position_widget_renders(self, db):
        _seed_position()
        at = _run_page()
        sb = at.selectbox(key=ADD_POSITION_KEY)
        assert sb is not None, (
            f"Add form must render a position selectbox with key={ADD_POSITION_KEY!r}"
        )

    def test_add_form_name_widget_renders(self, db):
        at = _run_page()
        ti = at.text_input(key=ADD_NAME_KEY)
        assert ti is not None, f"Add form must render a name text_input with key={ADD_NAME_KEY!r}"

    def test_add_form_relationship_widget_renders(self, db):
        at = _run_page()
        sb = at.selectbox(key=ADD_RELATIONSHIP_KEY)
        assert sb is not None, (
            f"Add form must render a relationship selectbox with key={ADD_RELATIONSHIP_KEY!r}"
        )

    def test_add_form_asked_date_widget_renders(self, db):
        at = _run_page()
        di = at.date_input(key=ADD_ASKED_DATE_KEY)
        assert di is not None, (
            f"Add form must render an asked_date date_input with key={ADD_ASKED_DATE_KEY!r}"
        )

    def test_add_form_submit_button_renders(self, db):
        _seed_position()
        at = _run_page()
        # at.button(key=...) raises KeyError for missing keys.
        btn = at.button(key=ADD_SUBMIT_KEY)
        assert btn is not None, f"Add form must render a submit button with key={ADD_SUBMIT_KEY!r}"

    def test_position_options_come_from_get_all_positions(self, db):
        _seed_position(name="Alpha", institute="MIT")
        _seed_position(name="Beta", institute="Stanford")
        at = _run_page()
        sb = at.selectbox(key=ADD_POSITION_KEY)
        joined = " ".join(str(o) for o in sb.options)
        assert "Alpha" in joined and "Beta" in joined, (
            f"Position selectbox options must reflect get_all_positions(); "
            f"got options={list(sb.options)!r}"
        )

    def test_relationship_options_come_from_config_relationship_values(self, db):
        at = _run_page()
        sb = at.selectbox(key=ADD_RELATIONSHIP_KEY)
        opts = list(sb.options)
        for v in config.RELATIONSHIP_VALUES:
            assert v in opts, (
                f"Relationship selectbox must offer every "
                f"config.RELATIONSHIP_VALUES entry; missing {v!r} from {opts!r}"
            )

    def test_form_id_is_recs_add_form(self):
        """Source-grep pin: the form id is ``recs_add_form`` per AGENTS
        §T5-B. Form ids aren't surfaced through AppTest's element tree
        — pinning at the source level catches a rename that would break
        any future test that reaches into the form by id."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert f'st.form("{ADD_FORM_ID}"' in src or f"st.form('{ADD_FORM_ID}'" in src, (
            f"Page must call st.form({ADD_FORM_ID!r}, ...) per AGENTS §T5-B"
        )


class TestAddRecommenderSubmit:
    """T5-B: submit handler calls ``database.add_recommender(pos_id,
    fields)``. Success → ``st.toast(f'Added {name}.')``; failure →
    ``st.error(str(e))``. Mirrors the quick-add pattern on the
    Opportunities page (whitespace-only name rejected, friendly errors,
    no re-raise)."""

    def test_submit_persists_recommender(self, db):
        pid = _seed_position(name="Alpha", institute="MIT")
        at = _run_page()

        # Pick the position that maps to pid (label format isn't pinned).
        sb = at.selectbox(key=ADD_POSITION_KEY)
        alpha_opt = next(o for o in sb.options if "Alpha" in str(o))
        sb.select(alpha_opt)

        at.text_input(key=ADD_NAME_KEY).set_value("Dr. New")
        at.selectbox(key=ADD_RELATIONSHIP_KEY).select("PhD Advisor")
        at.date_input(key=ADD_ASKED_DATE_KEY).set_value(datetime.date(2026, 4, 1))
        at.button(key=ADD_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Add raised: {at.exception!r}"
        recs = database.get_recommenders(pid)
        assert len(recs) == 1, f"Submit must INSERT one recommender for pid={pid}; got {len(recs)}"
        row = recs.iloc[0]
        assert row["recommender_name"] == "Dr. New"
        assert row["relationship"] == "PhD Advisor"
        assert row["asked_date"] == "2026-04-01"

    def test_submit_fires_added_toast(self, db):
        pid = _seed_position(name="Alpha")
        at = _run_page()
        sb = at.selectbox(key=ADD_POSITION_KEY)
        sb.select(next(o for o in sb.options if "Alpha" in str(o)))
        at.text_input(key=ADD_NAME_KEY).set_value("Dr. Toast")
        at.selectbox(key=ADD_RELATIONSHIP_KEY).select("PhD Advisor")
        at.date_input(key=ADD_ASKED_DATE_KEY).set_value(datetime.date(2026, 4, 1))
        at.button(key=ADD_SUBMIT_KEY).click()
        at.run()

        toasts = [el.value for el in at.toast]
        assert any('Added "Dr. Toast"' in v for v in toasts), (
            f"Successful add must fire st.toast('Added \"Dr. Toast\".')); got toasts={toasts!r}"
        )
        # Sanity: pid was used (suppresses unused-variable warning).
        assert pid > 0

    def test_empty_name_rejected_with_st_error(self, db):
        """Mirror Opportunities §8.2 quick-add F3: whitespace-only name
        is treated as empty — no DB write, no toast, friendly st.error
        prompts the user to retry."""
        _seed_position(name="Alpha")
        at = _run_page()
        sb = at.selectbox(key=ADD_POSITION_KEY)
        sb.select(next(o for o in sb.options if "Alpha" in str(o)))
        at.text_input(key=ADD_NAME_KEY).set_value("   ")  # whitespace only
        at.selectbox(key=ADD_RELATIONSHIP_KEY).select("PhD Advisor")
        at.date_input(key=ADD_ASKED_DATE_KEY).set_value(datetime.date(2026, 4, 1))
        at.button(key=ADD_SUBMIT_KEY).click()
        at.run()

        # No DB write.
        recs = database.get_all_recommenders()
        assert len(recs) == 0, f"Whitespace-only name must NOT be persisted; got {len(recs)} rows"
        # Friendly st.error.
        errors = [el.value for el in at.error]
        assert errors, f"Whitespace-only name must surface an st.error; got errors={errors!r}"
        # No success toast.
        toasts = [el.value for el in at.toast]
        assert not any("Added" in v for v in toasts), (
            f"Failed add must NOT fire an Added toast; got toasts={toasts!r}"
        )

    def test_db_failure_surfaces_st_error_no_re_raise(self, db, monkeypatch):
        """``database.add_recommender`` raises → page surfaces a friendly
        st.error containing the underlying message and does NOT re-raise.
        Mirrors GUIDELINES §8."""
        _seed_position(name="Alpha")

        def _boom(*args, **kwargs):
            raise RuntimeError("disk on fire")

        monkeypatch.setattr(database, "add_recommender", _boom)

        at = _run_page()
        sb = at.selectbox(key=ADD_POSITION_KEY)
        sb.select(next(o for o in sb.options if "Alpha" in str(o)))
        at.text_input(key=ADD_NAME_KEY).set_value("Dr. Smith")
        at.selectbox(key=ADD_RELATIONSHIP_KEY).select("PhD Advisor")
        at.date_input(key=ADD_ASKED_DATE_KEY).set_value(datetime.date(2026, 4, 1))
        at.button(key=ADD_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, (
            f"add_recommender failure must be caught + surfaced via "
            f"st.error per GUIDELINES §8; got exception={at.exception!r}"
        )
        errors = [el.value for el in at.error]
        assert any("disk on fire" in v for v in errors), (
            f"Failure must surface the underlying message; got errors={errors!r}"
        )
        toasts = [el.value for el in at.toast]
        assert not any("Added" in v for v in toasts), (
            f"Failed add must NOT fire an Added toast; got toasts={toasts!r}"
        )


# ── T5-C: Row selection + inline edit ────────────────────────────────────────


class TestRecommendersTableSelection:
    """T5-C: the All-Recommenders table is selectable (``on_select=
    'rerun'``, ``selection_mode='single-row'``). Selecting a row stores
    the recommender's primary-key id under ``recs_selected_id`` so the
    inline edit card below can resolve which row to render."""

    def test_table_is_selectable_source_grep(self):
        """AppTest cannot directly observe a dataframe's selection
        configuration; pin the on_select+selection_mode kwargs at the
        source level. Mirror of the Opportunities / Applications source-
        grep pin."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert 'on_select="rerun"' in src or "on_select='rerun'" in src, (
            f"{PAGE} must pass on_select='rerun' on the recs table"
        )
        assert 'selection_mode="single-row"' in src or "selection_mode='single-row'" in src, (
            f"{PAGE} must pass selection_mode='single-row' on the recs table"
        )

    def test_selecting_row_captures_recommender_id(self, db):
        pid = _seed_position(name="Alpha")
        rec_id = _seed_recommender(pid, recommender_name="Dr. Smith")

        at = _run_page()
        _select_row(at, 0)

        assert SELECTED_REC_ID_KEY in at.session_state, (
            f"Selecting row 0 must populate {SELECTED_REC_ID_KEY!r}"
        )
        assert at.session_state[SELECTED_REC_ID_KEY] == rec_id, (
            f"Expected selected rec_id={rec_id!r}; got {at.session_state[SELECTED_REC_ID_KEY]!r}"
        )

    def test_no_selection_no_edit_card(self, db):
        """Without a selection, the inline edit card / edit form must
        not render. Otherwise a ghost form would surface against an
        unselected row."""
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith")

        at = _run_page()
        # Don't select. The edit form's submit button only exists if
        # the form was rendered — its absence pins "no card".
        with pytest.raises(KeyError):
            at.button(key=EDIT_SUBMIT_KEY)


class TestRecommenderEditFormRender:
    """T5-C: inline edit card (``st.container(border=True)``) below the
    table when a row is selected, holding ``st.form('recs_edit_form')``
    with editable widgets for asked_date, confirmed, submitted_date,
    reminder_sent + reminder_sent_date, notes."""

    @pytest.mark.parametrize(
        "widget_key",
        [
            EDIT_ASKED_DATE_KEY,
            EDIT_CONFIRMED_KEY,
            EDIT_SUBMITTED_DATE_KEY,
            EDIT_REMINDER_SENT_KEY,
            EDIT_REMINDER_DATE_KEY,
            EDIT_NOTES_KEY,
        ],
    )
    def test_edit_widget_present(self, db, widget_key):
        """Each editable field must render in the edit form once a row
        is selected. Membership in session_state is the cleanest pin —
        AppTest writes session_state for every rendered widget on first
        render, so the key being present means the widget rendered."""
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith")
        at = _run_page()
        _select_row(at, 0)
        assert widget_key in at.session_state, (
            f"Edit form must render widget with key={widget_key!r} once a row is selected"
        )

    def test_form_id_is_recs_edit_form(self):
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        assert f'st.form("{EDIT_FORM_ID}"' in src or f"st.form('{EDIT_FORM_ID}'" in src, (
            f"Page must call st.form({EDIT_FORM_ID!r}, ...) per AGENTS §T5-C"
        )

    def test_edit_card_uses_bordered_container(self):
        """T5-C: inline edit card wraps in ``st.container(border=True)``.
        AppTest does not surface container styling — pinned at the
        source level (mirror of the T4 Pending-Alerts test).

        Count the actual ``with st.container(border=True):`` form so
        comments / docstrings that mention the API don't pad the
        count. The T4 Pending-Alerts panel already uses one such
        block; T5-C adds a second for the inline edit card."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        count = src.count("with st.container(border=True):")
        assert count >= 2, (
            f"{PAGE} must use 'with st.container(border=True):' for both "
            f"the T4 alert cards AND the T5-C edit card; got count={count}"
        )

    def test_pre_seed_asked_date(self, db):
        """Editing a recommender row pre-seeds its existing values so
        the form opens on the persisted state, not blank defaults.
        Same widget-value-trap pattern as Opportunities / Applications."""
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith", asked_date="2026-04-15")
        at = _run_page()
        _select_row(at, 0)
        assert at.session_state[EDIT_ASKED_DATE_KEY] == datetime.date(2026, 4, 15), (
            f"asked_date pre-seed must convert ISO → datetime.date; "
            f"got {at.session_state[EDIT_ASKED_DATE_KEY]!r}"
        )

    def test_pre_seed_confirmed_tri_state(self, db):
        """``confirmed`` is INTEGER tri-state (None/0/1) — pre-seed must
        carry the literal value (matching how the selectbox renders
        None as 'Not yet / unknown', 0 as 'No', 1 as 'Yes')."""
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith", confirmed=1)
        at = _run_page()
        _select_row(at, 0)
        assert at.session_state[EDIT_CONFIRMED_KEY] == 1, (
            f"confirmed pre-seed must reflect DB value; got "
            f"{at.session_state[EDIT_CONFIRMED_KEY]!r}"
        )

    def test_pre_seed_notes_handles_null(self, db):
        """NULL notes must pre-seed as '' (the widget-safe coercion that
        prevents the NaN-truthiness trap on st.text_area). Mirror of the
        Opportunities / Applications _safe_str invariant."""
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith", notes=None)
        at = _run_page()
        _select_row(at, 0)
        assert at.session_state[EDIT_NOTES_KEY] == "", (
            f"NULL notes must pre-seed as ''; got {at.session_state[EDIT_NOTES_KEY]!r}"
        )


class TestRecommenderEditFormSave:
    """T5-C: Save calls ``database.update_recommender(rec_id,
    dirty_fields_only)``. Toast on success; ``st.error`` on failure."""

    def test_save_persists_asked_date(self, db):
        pid = _seed_position(name="Alpha")
        rec_id = _seed_recommender(
            pid,
            recommender_name="Dr. Smith",
            asked_date="2026-04-01",
        )
        at = _run_page()
        _select_row(at, 0)

        at.date_input(key=EDIT_ASKED_DATE_KEY).set_value(datetime.date(2026, 4, 20))
        _keep_selection(at, 0)
        at.button(key=EDIT_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        row = database.get_recommenders(pid).iloc[0]
        assert int(row["id"]) == rec_id
        assert row["asked_date"] == "2026-04-20", (
            f"Save must persist asked_date; got {row['asked_date']!r}"
        )

    def test_save_persists_confirmed(self, db):
        pid = _seed_position(name="Alpha")
        rec_id = _seed_recommender(
            pid,
            recommender_name="Dr. Smith",
            confirmed=None,
        )
        at = _run_page()
        _select_row(at, 0)

        at.selectbox(key=EDIT_CONFIRMED_KEY).select(1)
        _keep_selection(at, 0)
        at.button(key=EDIT_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        row = database.get_recommenders(pid).iloc[0]
        assert int(row["id"]) == rec_id
        assert int(row["confirmed"]) == 1, (
            f"Save must persist confirmed=1; got {row['confirmed']!r}"
        )

    def test_save_persists_notes(self, db):
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith", notes=None)
        at = _run_page()
        _select_row(at, 0)

        at.text_area(key=EDIT_NOTES_KEY).set_value("follow up next week")
        _keep_selection(at, 0)
        at.button(key=EDIT_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        row = database.get_recommenders(pid).iloc[0]
        assert row["notes"] == "follow up next week", (
            f"Save must persist notes; got {row['notes']!r}"
        )

    def test_save_writes_only_dirty_fields(self, db, monkeypatch):
        """Spec ('dirty_fields_only'): the Save handler must compute the
        per-field diff against the persisted row and pass ONLY changed
        fields to update_recommender. Untouched widgets must NOT
        appear in the payload — this preserves any concurrent write
        semantics and matches the per-row Save pattern from T3-rev-B
        on the Applications page."""
        pid = _seed_position(name="Alpha")
        _seed_recommender(
            pid,
            recommender_name="Dr. Smith",
            asked_date="2026-04-01",
            confirmed=None,
            notes="orig notes",
        )

        captured: list[dict] = []
        orig = database.update_recommender

        def _spy(rec_id, fields):
            captured.append(dict(fields))
            return orig(rec_id, fields)

        monkeypatch.setattr(database, "update_recommender", _spy)

        at = _run_page()
        _select_row(at, 0)

        # Change only the notes field.
        at.text_area(key=EDIT_NOTES_KEY).set_value("updated notes")
        _keep_selection(at, 0)
        at.button(key=EDIT_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        assert captured, (
            "Save must call database.update_recommender at least once; captured nothing"
        )
        # The handler may or may not call update_recommender on a no-op;
        # but on a real change it must include 'notes'. Untouched
        # asked_date / confirmed must NOT appear.
        last = captured[-1]
        assert "notes" in last, f"Save payload must include the changed 'notes' field; got {last!r}"
        assert "asked_date" not in last, (
            f"Save payload must NOT include unchanged 'asked_date'; got {last!r}"
        )
        assert "confirmed" not in last, (
            f"Save payload must NOT include unchanged 'confirmed'; got {last!r}"
        )

    def test_save_fires_toast(self, db):
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith")
        at = _run_page()
        _select_row(at, 0)

        at.text_area(key=EDIT_NOTES_KEY).set_value("change")
        _keep_selection(at, 0)
        at.button(key=EDIT_SUBMIT_KEY).click()
        at.run()

        toasts = [el.value for el in at.toast]
        assert any("Saved" in v or "Dr. Smith" in v for v in toasts), (
            f'Successful Save must fire st.toast("Saved …"); got toasts={toasts!r}'
        )
        # Use pid to suppress unused-variable warnings — the variable
        # documents the scope of the seeded row.
        assert pid > 0

    def test_save_with_no_changes_fires_no_changes_toast(self, db):
        """Clicking Save when the form has no dirty diff against the
        persisted recommender row fires
        ``st.toast("No changes to save.")`` — the
        ``Saved "<name>"`` toast is reserved for branches with a
        non-empty dirty diff (signal honesty)."""
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith")
        at = _run_page()
        _select_row(at, 0)

        # Click Save without touching any widget.
        _keep_selection(at, 0)
        at.button(key=EDIT_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, f"Save raised: {at.exception!r}"
        toasts = [el.value for el in at.toast]
        assert any("No changes to save." in v for v in toasts), (
            f'No-op Save must fire st.toast("No changes to save."); got toasts={toasts!r}'
        )
        assert not any("Saved" in v for v in toasts), (
            f"No-op Save must NOT fire the Saved toast (dishonest when "
            f"nothing changed); got toasts={toasts!r}"
        )

    def test_save_db_failure_shows_error_no_toast(self, db, monkeypatch):
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith")

        def _boom(*args, **kwargs):
            raise RuntimeError("write failed")

        monkeypatch.setattr(database, "update_recommender", _boom)

        at = _run_page()
        _select_row(at, 0)

        at.text_area(key=EDIT_NOTES_KEY).set_value("won't land")
        _keep_selection(at, 0)
        at.button(key=EDIT_SUBMIT_KEY).click()
        at.run()

        assert not at.exception, (
            f"Save failure must be caught (GUIDELINES §8); got exception={at.exception!r}"
        )
        errors = [el.value for el in at.error]
        assert any("write failed" in v for v in errors), (
            f"Save failure must surface the underlying message; got {errors!r}"
        )
        toasts = [el.value for el in at.toast]
        assert not any("Saved" in v for v in toasts), (
            f"Failed save must NOT fire a Saved toast; got {toasts!r}"
        )
        # pid documents which row was targeted.
        assert pid > 0


class TestRecommenderEditDelete:
    """T5-C: ``st.button`` outside the form opens an ``@st.dialog``
    confirm gate; on Confirm, ``database.delete_recommender(rec_id)``
    cascades. Pattern mirrors the Opportunities-page delete dialog
    (``_confirm_delete_dialog``)."""

    def test_delete_button_renders_when_selected(self, db):
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith")
        at = _run_page()
        _select_row(at, 0)
        # Direct AppTest accessor — KeyError if absent.
        btn = at.button(key=DELETE_BUTTON_KEY)
        assert btn is not None, (
            f"Edit card must render a Delete button with key={DELETE_BUTTON_KEY!r}"
        )
        assert pid > 0

    def test_delete_dialog_warning_mentions_irreversibility(self, db):
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith")
        at = _run_page()
        _select_row(at, 0)

        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()

        warnings = " ".join(el.value for el in at.warning)
        assert "Dr. Smith" in warnings, (
            f"Dialog warning must reference the recommender name; got {warnings!r}"
        )
        assert "cannot be undone" in warnings.lower(), (
            f"Dialog warning must signal irreversibility; got {warnings!r}"
        )
        assert pid > 0

    def test_confirm_deletes_recommender(self, db):
        pid = _seed_position(name="Alpha")
        rec_id = _seed_recommender(pid, recommender_name="Dr. Smith")
        at = _run_page()
        _select_row(at, 0)

        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        at.button(key=DELETE_CONFIRM_KEY).click()
        at.run()

        assert not at.exception, f"Confirm raised: {at.exception!r}"
        recs = database.get_recommenders(pid)
        ids = list(recs["id"]) if not recs.empty else []
        assert rec_id not in ids, (
            f"Recommender id={rec_id} must be deleted after Confirm; got {ids!r}"
        )

    def test_confirm_clears_selection_state(self, db):
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Smith")
        at = _run_page()
        _select_row(at, 0)
        assert SELECTED_REC_ID_KEY in at.session_state  # precondition

        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        at.button(key=DELETE_CONFIRM_KEY).click()
        at.run()

        assert SELECTED_REC_ID_KEY not in at.session_state, (
            f"Confirm-delete must pop {SELECTED_REC_ID_KEY!r}"
        )
        assert EDIT_FORM_SID_KEY not in at.session_state, (
            f"Confirm-delete must pop {EDIT_FORM_SID_KEY!r} alongside "
            f"{SELECTED_REC_ID_KEY!r} (paired-cleanup contract)"
        )
        assert pid > 0

    def test_confirm_fires_toast(self, db):
        pid = _seed_position(name="Alpha")
        _seed_recommender(pid, recommender_name="Dr. Toast")
        at = _run_page()
        _select_row(at, 0)
        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        at.button(key=DELETE_CONFIRM_KEY).click()
        at.run()

        toasts = [el.value for el in at.toast]
        assert any("Dr. Toast" in v for v in toasts), (
            f"Confirm-delete must fire a toast referencing the deleted recommender; got {toasts!r}"
        )
        assert pid > 0

    def test_cancel_does_not_delete(self, db):
        pid = _seed_position(name="Alpha")
        rec_id = _seed_recommender(pid, recommender_name="Dr. Smith")
        at = _run_page()
        _select_row(at, 0)

        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        at.button(key=DELETE_CANCEL_KEY).click()
        _keep_selection(at, 0)
        at.run()

        assert not at.exception, f"Cancel raised: {at.exception!r}"
        recs = database.get_recommenders(pid)
        assert rec_id in list(recs["id"]), (
            f"Cancel must NOT delete the recommender; rec_id={rec_id} "
            f"missing from {list(recs['id'])!r}"
        )
        # No toast on cancel.
        toasts = [el.value for el in at.toast]
        assert not toasts, f"Cancel must NOT fire a toast; got {toasts!r}"

    def test_delete_db_failure_shows_error_no_re_raise(self, db, monkeypatch):
        pid = _seed_position(name="Alpha")
        rec_id = _seed_recommender(pid, recommender_name="Dr. Smith")

        def _boom(_rec_id):
            raise RuntimeError("delete failed")

        monkeypatch.setattr(database, "delete_recommender", _boom)

        at = _run_page()
        _select_row(at, 0)
        at.button(key=DELETE_BUTTON_KEY).click()
        _keep_selection(at, 0)
        at.run()
        at.button(key=DELETE_CONFIRM_KEY).click()
        at.run()

        assert not at.exception, (
            f"Delete failure must be caught + surfaced via st.error; got exception={at.exception!r}"
        )
        errors = [el.value for el in at.error]
        assert any("delete failed" in v for v in errors), (
            f"Delete failure must surface the underlying message; got {errors!r}"
        )
        # Recommender row still present (defensive).
        recs = database.get_recommenders(pid)
        assert rec_id in list(recs["id"]), (
            f"Failed delete must leave the row in DB; rec_id={rec_id} "
            f"missing from {list(recs['id'])!r}"
        )


# ── T6 helpers ────────────────────────────────────────────────────────────────
#
# T6 wires reminder helpers into each Pending Alerts card from T4. AppTest
# 1.56 has no typed `at.link_button` accessor — link buttons surface as
# `UnknownElement` instances accessible via `at.get('link_button')` whose
# `.proto` carries the LinkButton protobuf with `.label`, `.url`, `.id`
# fields. Phase 7 cleanup CL3 lifted `link_buttons` and `decode_mailto`
# into the shared `tests/helpers.py` module so test_export_page.py +
# future tests reach for one place.


# ── T6-A: Compose reminder email button (mailto link) ────────────────────────


class TestT6ComposeButton:
    """Phase 5 T6-A: per-Pending-Alert-card ``st.link_button`` opening a
    locked-copy ``mailto:`` URL.

    Locked contract (DESIGN §8.4 + AGENTS §T6-A):
      - Label: ``📧 Compose Reminder Email`` verbatim.
      - URL scheme: ``mailto:`` with empty path (no ``to:`` field — the
        recommenders schema doesn't store emails today).
      - Subject: ``Following up: letters for {N} <APPLICATION_LABEL>s``
        (label sourced from ``config.APPLICATION_LABEL``)
        where ``N`` is the count of positions that recommender owes
        letters for.
      - Body: ``Hi {recommender_name}, just a quick check-in on the
        letters of recommendation you offered. Thank you so much!``
      - One button per alert card — same cardinality as the cards
        themselves (groupby on recommender_name).
    """

    LABEL = "📧 Compose Reminder Email"

    def test_no_buttons_on_empty_db(self, db):
        """Empty DB → no alert cards → no compose buttons. The page
        still renders the Pending-Alerts subheader + empty-state info,
        but no link buttons."""
        at = _run_page()
        assert not at.exception, f"Page raised: {at.exception}"
        compose = [b for b in link_buttons(at) if b.proto.label == self.LABEL]
        assert compose == [], (
            f"Empty DB must not render any Compose buttons; got "
            f"{len(compose)}: labels={[b.proto.label for b in compose]!r}"
        )

    def test_single_pending_recommender_renders_one_button(self, db):
        """One pending recommender → exactly one Compose button."""
        TestPendingAlertsPanel._seed_pending()
        at = _run_page()
        compose = [b for b in link_buttons(at) if b.proto.label == self.LABEL]
        assert len(compose) == 1, (
            f"One pending recommender must produce exactly one Compose "
            f"button; got {len(compose)}: {[b.proto.label for b in link_buttons(at)]!r}"
        )

    def test_button_label_is_verbatim(self, db):
        """Label is ``Compose reminder email`` verbatim — pinned because
        DESIGN §8.4 spells the string out."""
        TestPendingAlertsPanel._seed_pending()
        at = _run_page()
        compose = [b for b in link_buttons(at) if b.proto.label == self.LABEL]
        assert compose, (
            f"Expected a link button labelled {self.LABEL!r}; got "
            f"{[b.proto.label for b in link_buttons(at)]!r}"
        )

    def test_button_url_uses_mailto_with_no_recipient(self, db):
        """URL is ``mailto:?subject=…&body=…`` — no ``to:`` because the
        recommenders schema doesn't store emails."""
        TestPendingAlertsPanel._seed_pending()
        at = _run_page()
        compose = [b for b in link_buttons(at) if b.proto.label == self.LABEL]
        assert compose, "precondition: compose button must render"
        url = compose[0].proto.url
        assert url.startswith("mailto:?"), (
            f"Compose URL must start with 'mailto:?' (no recipient); got {url!r}"
        )

    def test_subject_uses_locked_string_with_position_count(self, db):
        """At N=1 the subject uses singular ``letter`` and singular
        ``application`` per DESIGN §8.4 — the spec follows English
        pluralization rules across the N=1 / N≥2 split."""
        TestPendingAlertsPanel._seed_pending()
        at = _run_page()
        compose = [b for b in link_buttons(at) if b.proto.label == self.LABEL]
        decoded = decode_mailto(compose[0].proto.url)
        expected = f"Following up: letter for 1 {config.APPLICATION_LABEL}"
        assert decoded["subject"] == expected, (
            f"Subject must be {expected!r}; got {decoded['subject']!r}"
        )

    def test_subject_position_count_matches_card(self, db):
        """Multi-position case: a recommender owing two letters → ``N=2``
        in the subject. Coupled to the groupby cardinality, so a future
        bug that miscounts (e.g. uses len(unfiltered df) instead of len
        of the group) would surface here."""
        # Two positions, same recommender — one card, two bullets.
        pos_a = database.add_position(make_position({"position_name": "Pos A"}))
        pos_b = database.add_position(make_position({"position_name": "Pos B"}))
        asked = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
        for pid in (pos_a, pos_b):
            database.add_recommender(
                pid,
                {
                    "recommender_name": "Dr. Smith",
                    "asked_date": asked,
                },
            )

        at = _run_page()
        compose = [b for b in link_buttons(at) if b.proto.label == self.LABEL]
        assert len(compose) == 1, (
            f"Two-position single-recommender → one Compose button; got {len(compose)}"
        )
        decoded = decode_mailto(compose[0].proto.url)
        expected = f"Following up: letters for 2 {config.APPLICATION_LABEL}s"
        assert decoded["subject"] == expected, (
            f"Subject N must equal owed-position count; expected {expected!r}, "
            f"got {decoded['subject']!r}"
        )

    def test_body_uses_locked_string_with_recommender_name(self, db):
        """Body is the verbatim DESIGN §8.4 string with the recommender's
        name interpolated."""
        TestPendingAlertsPanel._seed_pending(recommender_name="Dr. Jones")
        at = _run_page()
        compose = [b for b in link_buttons(at) if b.proto.label == self.LABEL]
        decoded = decode_mailto(compose[0].proto.url)
        expected = (
            "Hi Dr. Jones, just a quick check-in on the letters of "
            "recommendation you offered. Thank you so much!"
        )
        assert decoded["body"] == expected, (
            f"Body must be the locked DESIGN §8.4 string with the recommender's "
            f"name interpolated; expected {expected!r}, got {decoded['body']!r}"
        )

    def test_two_recommenders_two_buttons(self, db):
        """One Compose button per alert card — two distinct recommenders
        → two buttons. Per-card uniqueness of widget keys is implied
        (Streamlit raises DuplicateWidgetID otherwise)."""
        TestPendingAlertsPanel._seed_pending(
            recommender_name="Dr. Alpha",
            position_name="Alpha Postdoc",
        )
        TestPendingAlertsPanel._seed_pending(
            recommender_name="Dr. Beta",
            position_name="Beta Postdoc",
        )
        at = _run_page()
        assert not at.exception, (
            f"Page raised on two-card render — likely a DuplicateWidgetID from "
            f"non-unique compose-button keys: {at.exception!r}"
        )
        compose = [b for b in link_buttons(at) if b.proto.label == self.LABEL]
        assert len(compose) == 2, f"Two recommenders → two Compose buttons; got {len(compose)}"

    def test_body_per_card_uses_correct_recommender_name(self, db):
        """Multi-card: each Compose button's body must use ITS recommender's
        name, not a shared / first-card name. Catches a bug where the body
        is computed once outside the groupby loop."""
        TestPendingAlertsPanel._seed_pending(
            recommender_name="Dr. Alpha",
            position_name="Alpha Postdoc",
        )
        TestPendingAlertsPanel._seed_pending(
            recommender_name="Dr. Beta",
            position_name="Beta Postdoc",
        )
        at = _run_page()
        compose = [b for b in link_buttons(at) if b.proto.label == self.LABEL]
        bodies = [decode_mailto(b.proto.url)["body"] for b in compose]
        assert any("Dr. Alpha" in b for b in bodies), (
            f"One Compose body must reference Dr. Alpha; got {bodies!r}"
        )
        assert any("Dr. Beta" in b for b in bodies), (
            f"One Compose body must reference Dr. Beta; got {bodies!r}"
        )


# ── T6-B: LLM prompts expander ───────────────────────────────────────────────


class TestT6LLMPromptsExpander:
    """Phase 5 T6-B: per-card ``st.expander`` revealing N pre-filled LLM
    prompts (one per style). DESIGN §8.4 + AGENTS §T6-B fix N=2 with tones
    ``gentle`` and ``urgent``, so the expander label reads
    ``Draft email with AI (2 styles)``.

    Each prompt block is rendered via ``st.code(text, language='text')``
    so Streamlit's built-in copy-on-hover affordance works. Required
    prompt content:
      - recommender name + relationship,
      - every owed position (name, institute, deadline),
      - days-since-asked,
      - target tone keyword (``gentle`` / ``urgent``),
      - explicit instruction asking the LLM to return BOTH subject and body.
    """

    EXPANDER_LABEL = "Draft email with AI (2 styles)"
    TONES = ("gentle", "urgent")

    def test_no_expander_on_empty_db(self, db):
        """Empty DB → no alert cards → no LLM-prompts expanders."""
        at = _run_page()
        labels = [e.label for e in at.expander]
        assert self.EXPANDER_LABEL not in labels, (
            f"Empty DB must not render the LLM-prompts expander; got expander labels={labels!r}"
        )

    def test_single_pending_renders_one_expander(self, db):
        TestPendingAlertsPanel._seed_pending()
        at = _run_page()
        matching = [e for e in at.expander if e.label == self.EXPANDER_LABEL]
        assert len(matching) == 1, (
            f"One pending recommender → one expander labelled "
            f"{self.EXPANDER_LABEL!r}; got {len(matching)} (all labels: "
            f"{[e.label for e in at.expander]!r})"
        )

    def test_expander_label_includes_tone_count(self, db):
        """Label format is ``LLM prompts ({N} tones)`` where N is the
        live tone count. DESIGN §8.4: 'Expander label includes prompt
        count, e.g. LLM prompts (2 tones)'."""
        TestPendingAlertsPanel._seed_pending()
        at = _run_page()
        labels = [e.label for e in at.expander]
        assert any(self.EXPANDER_LABEL in label for label in labels), (
            f"Expected an expander labelled {self.EXPANDER_LABEL!r}; got labels={labels!r}"
        )

    def test_expander_holds_two_code_blocks(self, db):
        """One pending recommender → two ``st.code`` blocks (one per
        tone). ``at.code`` collects every code block on the page; with
        only one alert card, the count equals the per-card tone count."""
        TestPendingAlertsPanel._seed_pending()
        at = _run_page()
        codes = list(at.code)
        assert len(codes) == 2, (
            f"One alert card → two code blocks (one per tone); got "
            f"{len(codes)}: {[c.value[:60] for c in codes]!r}"
        )

    def test_two_recommenders_two_expanders(self, db):
        """Two distinct recommenders → two expanders + 4 code blocks
        total (2 tones × 2 cards). Pins both the per-card cardinality
        and that the same widget keys aren't reused (Streamlit raises
        DuplicateWidgetID otherwise)."""
        TestPendingAlertsPanel._seed_pending(
            recommender_name="Dr. Alpha",
            position_name="Alpha Postdoc",
        )
        TestPendingAlertsPanel._seed_pending(
            recommender_name="Dr. Beta",
            position_name="Beta Postdoc",
        )
        at = _run_page()
        assert not at.exception, (
            f"Page raised on two-card render — likely a duplicate-widget "
            f"issue from the expander keys: {at.exception!r}"
        )
        matching = [e for e in at.expander if e.label == self.EXPANDER_LABEL]
        assert len(matching) == 2, f"Two recommenders → two expanders; got {len(matching)}"
        codes = list(at.code)
        assert len(codes) == 4, f"Two cards × two tones each → 4 code blocks; got {len(codes)}"

    def test_each_prompt_includes_recommender_name_and_relationship(self, db):
        TestPendingAlertsPanel._seed_pending(
            recommender_name="Dr. Jones",
            relationship="Committee Member",
        )
        at = _run_page()
        codes = list(at.code)
        assert codes, "precondition: pending recommender must produce prompt code blocks"
        for c in codes:
            assert "Dr. Jones" in c.value, (
                f"Every prompt must reference the recommender name; got prompt={c.value!r}"
            )
            assert "Committee Member" in c.value, (
                f"Every prompt must reference the recommender's "
                f"relationship; got prompt={c.value!r}"
            )

    def test_each_prompt_includes_owed_position_details(self, db):
        """Owed positions surface in the prompt with their name, institute,
        and deadline — matches DESIGN §8.4 'positions owed (position name,
        institute, deadline)'."""
        TestPendingAlertsPanel._seed_pending(
            position_name="CSAIL Postdoc",
            institute="MIT",
            deadline_offset=10,
        )
        deadline_iso = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
        at = _run_page()
        codes = list(at.code)
        assert codes, "precondition: pending recommender must produce prompt code blocks"
        for c in codes:
            assert "CSAIL Postdoc" in c.value, (
                f"Every prompt must include the position name; got prompt={c.value!r}"
            )
            assert "MIT" in c.value, (
                f"Every prompt must include the institute; got prompt={c.value!r}"
            )
            assert deadline_iso in c.value, (
                f"Every prompt must include the deadline (ISO date); got prompt={c.value!r}"
            )

    def test_each_prompt_includes_days_since_asked(self, db):
        """Days-since-asked is the integer count surfaced on the alert card
        bullet too — keep the prompts coherent with the bullet text."""
        TestPendingAlertsPanel._seed_pending(days_ago=14)
        at = _run_page()
        codes = list(at.code)
        assert codes, "precondition: pending recommender must produce prompt code blocks"
        for c in codes:
            assert "14" in c.value, (
                f"Every prompt must include the days-since-asked count (14); got prompt={c.value!r}"
            )

    def test_each_prompt_carries_a_target_tone_keyword(self, db):
        """Two prompts, two tones — across the pair every locked-tone
        keyword (``gentle``, ``urgent``) appears at least once."""
        TestPendingAlertsPanel._seed_pending()
        at = _run_page()
        codes = list(at.code)
        joined = "\n\n".join(c.value.lower() for c in codes)
        for tone in self.TONES:
            assert tone in joined, (
                f"Locked tone keyword {tone!r} must appear in some prompt; "
                f"got code-bodies={[c.value[:80] for c in codes]!r}"
            )

    def test_each_prompt_asks_for_subject_and_body(self, db):
        """DESIGN §8.4: 'Prompts ask LLM to return both subject and body
        so user can paste either / both into mail client.'"""
        TestPendingAlertsPanel._seed_pending()
        at = _run_page()
        codes = list(at.code)
        assert codes, "precondition: pending recommender must produce prompt code blocks"
        for c in codes:
            v = c.value.lower()
            assert "subject" in v, (
                f"Every prompt must instruct the LLM to return a subject; got prompt={c.value!r}"
            )
            assert "body" in v, (
                f"Every prompt must instruct the LLM to return a body; got prompt={c.value!r}"
            )

    def test_code_blocks_use_text_language(self):
        """``st.code(prompt_text, language='text')`` per AGENTS §T6-B —
        keeps Streamlit from syntax-highlighting prose. Pinned at the
        source level because the proto's ``language`` field on the Code
        element is exposed to AppTest and we want to avoid a regression
        to ``language='python'`` (which would highlight the prose as
        Python and look wrong)."""
        src = pathlib.Path(PAGE).read_text(encoding="utf-8")
        # Mostly a sanity grep; combined with the runtime test below
        # we have both source-level and runtime coverage.
        assert 'language="text"' in src or "language='text'" in src, (
            f"{PAGE} must call st.code(..., language='text') for the "
            f"LLM-prompt blocks per AGENTS §T6-B"
        )

    def test_code_blocks_render_with_text_language(self, db):
        TestPendingAlertsPanel._seed_pending()
        at = _run_page()
        codes = list(at.code)
        assert codes, "precondition: pending recommender must produce prompt code blocks"
        for c in codes:
            assert c.language == "text", (
                f"Every prompt code block must render with language='text'; "
                f"got language={c.language!r} on body={c.value[:60]!r}"
            )
