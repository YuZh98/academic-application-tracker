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
#
# Concurrency invariants:
#   The Streamlit Cloud demo serves many visitors from a single Python
#   process. Two invariants make that safe; both are load-bearing and
#   easy to break by accident.
#
#   1. The ``_provider()`` callable is process-global / singleton.
#      It is installed exactly once via
#      ``database.set_connection_provider(_provider)`` inside ``bind()``
#      and is never replaced or cleared during normal operation. Every
#      concurrent demo session shares the *same* provider object.
#
#   2. Per-session isolation comes from ``st.session_state``, not from
#      per-session providers. Streamlit gives each session its own
#      ``st.session_state`` mapping, so when ``_provider()`` executes
#      in session A's thread it reads session A's cached connection,
#      and when it executes in session B's thread it reads session B's.
#      The provider is shared; the connection it returns is not.
#
#   Corollary — do NOT clear the provider in ``reset()``. The provider
#   is shared across every live demo session in the process; clearing
#   it would break the *next* ``database._connect()`` call in OTHER
#   concurrent visitors. ``reset()`` only wipes the calling session's
#   own cache + sentinel. This is intentionally asymmetric with the
#   teardown path inside ``bind()``'s except block, which only fires
#   when the provider was just installed for this session and no other
#   session can yet depend on it.

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

    The per-call read of ``st.session_state`` is what makes this
    process-global singleton callable safe for concurrent sessions:
    each invocation resolves the connection in the *calling* session's
    state, so a shared provider returns per-session connections.
    """
    conn = st.session_state.get(_CONN_KEY)
    if conn is None:
        raise RuntimeError(
            "db_session._provider() found no cached connection. "
            "Session state was cleared after bind() succeeded."
        )
    return conn


def reset() -> None:
    """Wipe the cached connection. Next render re-runs ``bind()`` and re-seeds.

    The provider is left installed by design (cross-session safety):
    it is shared across every live demo session in the process, so
    clearing it here would break the next ``database._connect()`` call
    in other concurrent visitors. See the module docstring's
    "Concurrency invariants" section for the full rationale.

    Only the calling session's own ``_CONN_KEY`` cache and ``_BOUND_KEY``
    sentinel are popped, so the next render in *this* session runs
    ``bind()`` again, which re-opens ``:memory:`` and re-seeds. The
    connection closed below is the calling session's own; closing it
    does not affect connections held by other sessions.
    """
    conn = st.session_state.pop(_CONN_KEY, None)
    st.session_state.pop(_BOUND_KEY, None)
    if conn is not None:
        with contextlib.suppress(Exception):
            conn.close()
