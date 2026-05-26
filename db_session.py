# db_session.py
# Per-session in-memory SQLite for the Streamlit Cloud demo deploy.
#
# Bridge layer between Streamlit and database.py. This is the ONLY new
# module allowed to import both ``streamlit`` and ``database`` — the layer
# rule (DESIGN §2) keeps database.py free of UI-framework dependencies;
# db_session.py is the dependency-injection wiring that puts a per-session
# connection behind database._connect() without making database.py aware
# of it.
#
# Lifecycle:
#   - ``bind()`` runs on every page bootstrap; on the first call per
#     session it opens ``:memory:``, caches the connection in
#     ``st.session_state``, installs the provider, runs schema + seed.
#     Idempotent thereafter via the ``_BOUND_KEY`` sentinel.
#   - ``_provider()`` is a pure read of ``st.session_state[_CONN_KEY]``.
#   - ``reset()`` wipes the cache + sentinel so the next ``bind()``
#     opens a fresh in-memory DB and re-seeds.
#
# Failure boundary is all-or-nothing: any exception inside the setup
# block pops the cache, clears the provider, and closes the connection
# before re-raising, so the next page render starts the setup over from
# scratch against a clean state.

from __future__ import annotations

import contextlib
import logging
import os
import sqlite3

import streamlit as st

import config
import database
from scripts import seed_demo_db

logger = logging.getLogger(__name__)

_BOUND_KEY = "_aat_demo_bound"
_CONN_KEY = "_aat_demo_conn"


def bind() -> None:
    """One-shot per-session demo setup. Safe to call on every bootstrap.

    No-op when ``config.IS_DEMO`` is False (local dev path: file-based
    SQLite, no provider installed). In demo mode: opens ``:memory:``,
    caches the connection in ``st.session_state``, installs the
    provider, runs schema + seed. On any setup failure: closes the
    conn, clears all state, re-raises so the next render retries from
    scratch.
    """
    if not config.IS_DEMO:
        return
    if st.session_state.get(_BOUND_KEY):
        return

    if os.environ.get("AAT_DB_PATH"):
        logger.warning(
            "AAT_DEMO=1 takes precedence over AAT_DB_PATH; the file-path "
            "override is ignored for this session."
        )

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    st.session_state[_CONN_KEY] = conn
    database.set_connection_provider(_provider)

    try:
        database.init_db()
        seed_demo_db.seed(conn)
    except Exception:
        # Roll back so the next render re-attempts a fresh bind. The
        # in-memory DB has no recoverable partial state — "all or
        # nothing per session" is the failure boundary.
        st.session_state.pop(_CONN_KEY, None)
        database.set_connection_provider(None)
        # conn.close() can itself raise on a corrupted :memory: after a
        # mid-DDL failure — suppress so the ORIGINAL setup exception
        # propagates via the bare ``raise`` below.
        with contextlib.suppress(Exception):
            conn.close()
        raise

    st.session_state[_BOUND_KEY] = True


def _provider() -> sqlite3.Connection:
    """Provider callable installed by ``bind()``. Pure read of session_state.

    Raises if ``st.session_state[_CONN_KEY]`` is missing — only reachable
    if external code popped the cache AFTER ``bind()`` succeeded (e.g.,
    a buggy widget calling ``st.session_state.clear()``). The "bind()
    never ran" case takes a different path: the provider was never
    installed, so ``database._connect()`` falls back to file mode
    without ever calling here.
    """
    conn = st.session_state.get(_CONN_KEY)
    if conn is None:
        raise RuntimeError(
            "db_session._provider() found no cached connection. "
            "Session state was cleared after bind() succeeded."
        )
    return conn


def reset() -> None:
    """Wipe the cached connection. Next render re-runs ``bind()`` and re-seeds."""
    conn = st.session_state.pop(_CONN_KEY, None)
    st.session_state.pop(_BOUND_KEY, None)
    if conn is not None:
        with contextlib.suppress(Exception):
            conn.close()
