# tests/structure/test_bootstrap_order.py
# Grep-grade test: every Streamlit page must call db_session.bind()
# before any database.* reference. Cheap insurance against new pages
# forgetting the demo bootstrap and silently breaking on Cloud.

import pathlib

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

# All entry points. Order matches the sidebar nav.
PAGES = [
    "app.py",
    "pages/1_Opportunities.py",
    "pages/2_Applications.py",
    "pages/3_Recommenders.py",
    "pages/4_Export.py",
    "pages/5_Settings.py",
]


@pytest.mark.parametrize("page", PAGES)
def test_page_calls_db_session_bind_before_database(page):
    """Bootstrap-order discipline: db_session.bind() must appear in the
    page source BEFORE any reference to ``database.`` (excluding the
    import line itself). A page that misses bind() silently falls back
    to file-DB mode on Streamlit Cloud — visitors share state."""
    src = (_REPO_ROOT / page).read_text()
    bind_idx = src.find("db_session.bind()")
    assert bind_idx != -1, (
        f"{page}: missing db_session.bind() call — demo bootstrap will "
        f"silently fall back to file-DB mode on Streamlit Cloud."
    )

    # First non-import ``database.`` reference. Skip lines that start
    # with ``import database`` or ``from database import``.
    db_idx = None
    offset = 0
    for line in src.splitlines(keepends=True):
        stripped = line.lstrip()
        if not (
            stripped.startswith("import database")
            or stripped.startswith("from database import")
        ):
            line_db_idx = line.find("database.")
            if line_db_idx != -1:
                db_idx = offset + line_db_idx
                break
        offset += len(line)

    if db_idx is not None:
        assert bind_idx < db_idx, (
            f"{page}: db_session.bind() appears AFTER first database.* "
            f"reference. Bind must come first or demo bootstrap fails."
        )


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_demo_banner(page):
    """Every page must call ui.demo_banner() so the visitor sees the
    banner regardless of which page they land on first."""
    src = (_REPO_ROOT / page).read_text()
    assert "ui.demo_banner()" in src, (
        f"{page}: missing ui.demo_banner() — visitor lands here without "
        f"seeing the demo banner."
    )


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_sidebar_demo_reset_block(page):
    """Every page must wire the sidebar reset block."""
    src = (_REPO_ROOT / page).read_text()
    assert "ui.sidebar_demo_reset_block" in src, (
        f"{page}: missing ui.sidebar_demo_reset_block — sidebar reset "
        f"button missing on this page."
    )
