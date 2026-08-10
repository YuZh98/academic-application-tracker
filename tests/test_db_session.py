# tests/test_db_session.py
# Tests for db_session.py — the streamlit-aware bridge module that wires
# per-session in-memory SQLite into database.py's connection provider.

import sqlite3

import pytest

import config
import database


class _FakeSessionState(dict):
    """Plain dict + attribute access — minimal stand-in for st.session_state."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def __setattr__(self, name, value):
        self[name] = value


@pytest.fixture
def fake_st(monkeypatch):
    """Replace streamlit.session_state with a plain dict so unit tests
    don't need a running Streamlit. Returns the dict for assertions."""
    import streamlit as st

    state = _FakeSessionState()
    monkeypatch.setattr(st, "session_state", state)
    return state


class TestBind:
    def test_bind_noop_when_not_demo(self, fake_st, monkeypatch):
        monkeypatch.setattr(config, "IS_DEMO", False)
        import db_session

        db_session.bind()
        assert database._connection_provider is None
        assert "_aat_demo_bound" not in fake_st

    def test_bind_installs_provider_when_demo(self, fake_st, monkeypatch):
        monkeypatch.setattr(config, "IS_DEMO", True)
        import db_session

        db_session.bind()
        assert database._connection_provider is db_session._provider
        assert fake_st["_aat_demo_bound"] is True
        assert isinstance(fake_st["_aat_demo_conn"], sqlite3.Connection)

    def test_bind_idempotent_within_session(self, fake_st, monkeypatch):
        monkeypatch.setattr(config, "IS_DEMO", True)
        import db_session

        db_session.bind()
        first_conn = fake_st["_aat_demo_conn"]
        db_session.bind()
        # Second bind() must short-circuit; same connection identity.
        assert fake_st["_aat_demo_conn"] is first_conn

    def test_bind_seeds_the_db(self, fake_st, monkeypatch):
        monkeypatch.setattr(config, "IS_DEMO", True)
        import db_session

        db_session.bind()
        conn = fake_st["_aat_demo_conn"]
        n = conn.execute("SELECT COUNT(*) AS n FROM positions").fetchone()["n"]
        assert n == 19

    def test_bind_warns_when_aat_db_path_also_set(self, fake_st, monkeypatch, caplog):
        monkeypatch.setattr(config, "IS_DEMO", True)
        monkeypatch.setenv("AAT_DB_PATH", "/tmp/should-be-ignored.db")
        import db_session

        with caplog.at_level("WARNING"):
            db_session.bind()
        assert any("AAT_DB_PATH" in r.message for r in caplog.records)

    def test_bind_cleans_up_on_seed_failure(self, fake_st, monkeypatch):
        monkeypatch.setattr(config, "IS_DEMO", True)
        import db_session
        from scripts import seed_demo_db

        def _raise(_conn):
            raise RuntimeError("simulated seed crash")

        monkeypatch.setattr(seed_demo_db, "seed", _raise)
        with pytest.raises(RuntimeError, match="simulated seed crash"):
            db_session.bind()
        # Session-local state cleaned up; the process-global provider
        # stays installed — other live sessions depend on it, and with
        # the cache popped _provider() fails loudly instead of letting
        # database._connect() fall back to the shared file DB.
        assert "_aat_demo_conn" not in fake_st
        assert "_aat_demo_bound" not in fake_st
        assert database._connection_provider is db_session._provider
        with pytest.raises(RuntimeError, match="no cached connection"):
            db_session._provider()

    def test_bind_recoverable_after_failure(self, fake_st, monkeypatch):
        monkeypatch.setattr(config, "IS_DEMO", True)
        import db_session
        from scripts import seed_demo_db

        original_seed = seed_demo_db.seed

        def _raise(_conn):
            raise RuntimeError("crash")

        monkeypatch.setattr(seed_demo_db, "seed", _raise)
        with pytest.raises(RuntimeError):
            db_session.bind()

        # Restore + retry — next bind() must succeed.
        monkeypatch.setattr(seed_demo_db, "seed", original_seed)
        db_session.bind()
        assert fake_st["_aat_demo_bound"] is True


class TestProvider:
    def test_provider_raises_when_cache_missing(self, fake_st):
        import db_session

        with pytest.raises(RuntimeError, match="no cached connection"):
            db_session._provider()

    def test_provider_returns_cached_conn(self, fake_st):
        import db_session

        sentinel = sqlite3.connect(":memory:")
        fake_st["_aat_demo_conn"] = sentinel
        try:
            assert db_session._provider() is sentinel
        finally:
            sentinel.close()


class TestReset:
    def test_reset_clears_cache_and_sentinel(self, fake_st, monkeypatch):
        monkeypatch.setattr(config, "IS_DEMO", True)
        import db_session

        db_session.bind()
        assert "_aat_demo_bound" in fake_st

        db_session.reset()
        assert "_aat_demo_conn" not in fake_st
        assert "_aat_demo_bound" not in fake_st

    def test_reset_followed_by_bind_reseeds(self, fake_st, monkeypatch):
        monkeypatch.setattr(config, "IS_DEMO", True)
        import db_session

        db_session.bind()
        first_conn = fake_st["_aat_demo_conn"]

        db_session.reset()
        db_session.bind()
        second_conn = fake_st["_aat_demo_conn"]
        assert second_conn is not first_conn
        n = second_conn.execute("SELECT COUNT(*) AS n FROM positions").fetchone()["n"]
        assert n == 19
