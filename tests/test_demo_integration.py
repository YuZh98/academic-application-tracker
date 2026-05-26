# tests/test_demo_integration.py
# Integration test for the demo deploy. AppTest is synchronous; we run
# two sessions sequentially in the same process and confirm:
#   - Each session has its own cached connection identity in its
#     session_state.
#   - A write in session A is invisible to session B.
#
# The provider callable is process-global and stable across runs;
# what's session-scoped is the connection object behind
# st.session_state.

import importlib

import pytest
from streamlit.testing.v1 import AppTest

import config
import database


@pytest.fixture
def demo_env(monkeypatch):
    """Set AAT_DEMO=1 and reload config + db_session so IS_DEMO sees
    the env var at import time. Tears down after the test."""
    monkeypatch.setenv("AAT_DEMO", "1")
    importlib.reload(config)
    import db_session

    importlib.reload(db_session)
    yield
    monkeypatch.delenv("AAT_DEMO", raising=False)
    importlib.reload(config)


def test_two_sessions_get_distinct_cached_connections(demo_env):
    """Each AppTest instance is its own session — distinct connection
    identities in their respective session_state dicts."""
    at1 = AppTest.from_file("app.py", default_timeout=15)
    at1.run()
    assert "_aat_demo_conn" in at1.session_state
    conn1 = at1.session_state["_aat_demo_conn"]

    at2 = AppTest.from_file("app.py", default_timeout=15)
    at2.run()
    assert "_aat_demo_conn" in at2.session_state
    conn2 = at2.session_state["_aat_demo_conn"]

    assert id(conn1) != id(conn2), "Sessions must have distinct connections"

    # Provider identity is process-global — both runs see the same callable.
    import db_session

    assert database._connection_provider is db_session._provider


def test_write_in_session_a_invisible_to_session_b(demo_env):
    """Writes in session A's in-memory DB must not surface in session B."""
    at1 = AppTest.from_file("app.py", default_timeout=15)
    at1.run()
    conn_a = at1.session_state["_aat_demo_conn"]
    conn_a.execute(
        "INSERT INTO positions (position_name, status) VALUES (?, ?)",
        ("ISOLATION-CANARY-A", config.STATUS_SAVED),
    )
    conn_a.commit()

    # Fresh session.
    at2 = AppTest.from_file("app.py", default_timeout=15)
    at2.run()
    conn_b = at2.session_state["_aat_demo_conn"]
    n = conn_b.execute(
        "SELECT COUNT(*) AS n FROM positions WHERE position_name = ?",
        ("ISOLATION-CANARY-A",),
    ).fetchone()["n"]
    assert n == 0, "Session B saw a write from session A — isolation broken"


def test_exports_dir_stays_empty_in_demo(demo_env, tmp_path, monkeypatch):
    """Privacy invariant from spec §2.2: no FS write under EXPORTS_DIR
    happens during a demo session, even though seed() calls every
    database writer that has a deferred exports.write_all() in its
    success path."""
    import exports

    monkeypatch.setattr(exports, "EXPORTS_DIR", tmp_path / "exports")

    at = AppTest.from_file("app.py", default_timeout=15)
    at.run()
    assert "_aat_demo_conn" in at.session_state

    # The seed runs against the in-mem DB and calls add_position +
    # upsert_application + add_interview + add_recommender (each of
    # which would normally trigger exports.write_all). The gate must
    # keep EXPORTS_DIR untouched.
    exports_dir = tmp_path / "exports"
    assert not exports_dir.exists() or not any(exports_dir.rglob("*")), (
        f"EXPORTS_DIR not empty after demo session: "
        f"{list(exports_dir.rglob('*')) if exports_dir.exists() else []}"
    )
