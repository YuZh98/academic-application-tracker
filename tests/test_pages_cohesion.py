# tests/test_pages_cohesion.py
# Phase 7 cross-page cohesion tests.
#
# Phase 7 introduces a thin layer of tests that hold across the entire
# page surface rather than any single page. T3 ships the
# set_page_config sweep below; T4 (confirm-dialog audit) and T5
# (responsive-layout check) will accrete onto this file when they ship.
#
# Pinning approach: set_page_config is consumed by Streamlit before
# widgets render, so the call doesn't surface in AppTest's element
# tree. Source-level grep + ast-walk is the standard precedent on this
# project for "this contract must hold in the source file" — see
# tests/test_export_page.py::TestExportPageShell::
# test_page_config_sets_wide_layout for the single-page version this
# sweep generalises.

import ast
import pathlib

import pytest


# All five pages on the Postdoc Tracker. Order matches the sidebar.
# Add new pages here; the parametrize decorators pick them up
# automatically.
PAGE_FILES = [
    "app.py",
    "pages/1_Opportunities.py",
    "pages/2_Applications.py",
    "pages/3_Recommenders.py",
    "pages/4_Export.py",
]


def _first_module_level_st_call(source: str) -> tuple[str, int] | None:
    """Return ``(attribute_name, line_number)`` of the first bare
    ``st.<X>(...)`` expression statement at module level in ``source``,
    or ``None`` if none exist.

    "Bare expression statement" is the AST shape for a top-level call
    that is NOT inside a def/class body, NOT inside an assignment RHS,
    and NOT a decorator. Concretely:

      ✓ counted: ``st.title("X")``, ``st.set_page_config(...)``
      ✗ skipped: ``@st.dialog("...")`` on a FunctionDef
      ✗ skipped: ``EM_DASH = st.something(...)``  (assignment)
      ✗ skipped: ``def f(): st.title("X")``        (function body)
      ✗ skipped: ``import streamlit as st``        (import)

    The contract this helper supports: "the first executable Streamlit
    *rendering* statement on a page must be set_page_config" (DESIGN
    §8.0 + D14). Decorators like ``@st.dialog(...)`` execute at module
    load but Streamlit's "set_page_config must be first" guard does
    NOT trip on them — they are factory-style higher-order calls, not
    render calls. ``pages/1_Opportunities.py`` legitimately uses
    ``@st.dialog`` on ``_confirm_delete_dialog`` ABOVE its
    set_page_config; the page renders fine. So the AST check must
    skip decorators to match Streamlit's actual gate, otherwise the
    test would force a refactor for no real-world bug.
    """
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Expr):
            call = node.value
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == "st"
            ):
                return call.func.attr, node.lineno
    return None


class TestSetPageConfigSweep:
    """Phase 7 T3 — cross-page set_page_config cohesion.

    Locked shape (DESIGN §8.0 + D14, GUIDELINES §13 step 2):

      .. code-block:: python

         st.set_page_config(
             page_title="Postdoc Tracker",
             page_icon="📋",
             layout="wide",
         )

    Two invariants per page:

      1. **Locked kwargs (source grep).** All three kwargs present
         and bound to their locked values. Mirror of
         ``test_export_page.py::TestExportPageShell::
         test_page_config_sets_wide_layout``, applied to every page.
      2. **First Streamlit statement (ast walk).** No
         ``st.<X>()`` bare expression statement at module level may
         precede ``set_page_config``. Catches a future edit that adds
         ``st.title("X")`` above the ``set_page_config`` line —
         Streamlit emits a runtime warning and silently falls back
         to centered layout in that case.
    """

    @pytest.mark.parametrize("page", PAGE_FILES)
    def test_page_calls_set_page_config_with_locked_kwargs(
        self, page: str
    ) -> None:
        src = pathlib.Path(page).read_text(encoding="utf-8")
        assert "st.set_page_config(" in src, (
            f"{page} must call st.set_page_config(...) per DESIGN §8.0."
        )
        assert 'page_title="Postdoc Tracker"' in src, (
            f"{page} must bind page_title=\"Postdoc Tracker\" "
            f"(locked across every page per DESIGN §8.0 / D14)."
        )
        assert 'page_icon="📋"' in src, (
            f"{page} must bind page_icon=\"📋\" "
            f"(locked across every page per DESIGN §8.0 / D14)."
        )
        assert 'layout="wide"' in src, (
            f"{page} must bind layout=\"wide\" per DESIGN §8.0 / D14."
        )

    @pytest.mark.parametrize("page", PAGE_FILES)
    def test_set_page_config_is_first_streamlit_statement(
        self, page: str
    ) -> None:
        src = pathlib.Path(page).read_text(encoding="utf-8")
        first = _first_module_level_st_call(src)
        assert first is not None, (
            f"{page} has no module-level st.<X>() bare expression "
            f"statement — was set_page_config removed or moved into a "
            f"function body?"
        )
        name, lineno = first
        assert name == "set_page_config", (
            f"{page}: first module-level st.<X>() bare expression is "
            f"st.{name}() at line {lineno}; must be "
            f"st.set_page_config(...) per DESIGN §8.0 / D14 / "
            f"GUIDELINES §13. Streamlit warns + silently falls back to "
            f"centered layout when any other st.* render call precedes "
            f"set_page_config."
        )
