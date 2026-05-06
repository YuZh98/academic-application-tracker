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
from typing import Iterator

import pytest

# All five pages on the Academic Application Tracker. Order matches the sidebar.
# Add new pages here; the parametrize decorators pick them up
# automatically.
PAGE_FILES = [
    "app.py",
    "pages/1_Opportunities.py",
    "pages/2_Applications.py",
    "pages/3_Recommenders.py",
    "pages/4_Export.py",
]


# Phase 7 T4 — every destructive path in the app. Each entry is one
# delete dialog wired up by the page that owns it. The fields drive
# parametrize-driven assertions in TestConfirmDialogAudit below.
#
# `cascade_substrings` is the list of entity nouns the dialog body
# MUST mention so the user knows what they're about to lose. Empty
# list = leaf delete (no FK cascade — the row drops alone).
#
# Cascade chain (database.py schema):
#   positions  → applications (FK: position_id, ON DELETE CASCADE)
#                → interviews (FK: application_id, ON DELETE CASCADE)
#   positions  → recommenders (FK: position_id, ON DELETE CASCADE)
# So deleting a position drops applications + interviews +
# recommenders in one transactional sweep — the dialog must say so.
DESTRUCTIVE_PATHS: list[dict] = [
    {
        "page": "pages/1_Opportunities.py",
        "dialog_fn": "_confirm_delete_dialog",
        "title": "Delete this position?",
        "delete_call": "delete_position",
        "cascade_substrings": ["application", "interview", "recommender"],
    },
    {
        "page": "pages/2_Applications.py",
        "dialog_fn": "_confirm_interview_delete_dialog",
        "title": "Delete this interview?",
        "delete_call": "delete_interview",
        "cascade_substrings": [],
    },
    {
        "page": "pages/3_Recommenders.py",
        "dialog_fn": "_confirm_delete_recommender_dialog",
        "title": "Delete this recommender?",
        "delete_call": "delete_recommender",
        "cascade_substrings": [],
    },
]


def _has_dialog_decorator(func: ast.FunctionDef) -> bool:
    """Return True if ``func`` is decorated with ``@st.dialog(...)``."""
    for dec in func.decorator_list:
        if (
            isinstance(dec, ast.Call)
            and isinstance(dec.func, ast.Attribute)
            and isinstance(dec.func.value, ast.Name)
            and dec.func.value.id == "st"
            and dec.func.attr == "dialog"
        ):
            return True
    return False


def _set_parents(tree: ast.AST) -> None:
    """Annotate every node in ``tree`` with a ``.parent`` attribute.

    ``ast`` doesn't ship parent links by default, but several of T4's
    invariants are "find an enclosing X" questions (is this call inside
    a dialog function? inside an except handler?). Walking the tree
    once to set parents is the cleanest pattern for those queries.
    """
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node  # type: ignore[attr-defined]


def _ancestors(node: ast.AST) -> Iterator[ast.AST]:
    """Yield every ancestor of ``node`` in the AST, walking outward."""
    cur: ast.AST = node
    while getattr(cur, "parent", None) is not None:
        cur = cur.parent  # type: ignore[attr-defined]
        yield cur


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    """Return the first ``FunctionDef`` named ``name`` (or None)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


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
             page_title="Academic Application Tracker",
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
    def test_page_calls_set_page_config_with_locked_kwargs(self, page: str) -> None:
        src = pathlib.Path(page).read_text(encoding="utf-8")
        assert "st.set_page_config(" in src, (
            f"{page} must call st.set_page_config(...) per DESIGN §8.0."
        )
        assert 'page_title="Academic Application Tracker"' in src, (
            f'{page} must bind page_title="Academic Application Tracker" '
            f"(locked across every page per DESIGN §8.0 / D14)."
        )
        assert 'page_icon="📋"' in src, (
            f'{page} must bind page_icon="📋" (locked across every page per DESIGN §8.0 / D14).'
        )
        assert 'layout="wide"' in src, f'{page} must bind layout="wide" per DESIGN §8.0 / D14.'

    @pytest.mark.parametrize("page", PAGE_FILES)
    def test_set_page_config_is_first_streamlit_statement(self, page: str) -> None:
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


class TestConfirmDialogAudit:
    """Phase 7 T4 — cross-page confirm-dialog cohesion.

    Every destructive path (delete that hits the DB) must wear an
    ``@st.dialog`` confirm gate per GUIDELINES §8 ("Irreversible
    actions: ``@st.dialog`` confirm gate"). This class pins the
    structural invariants that hold across all three destructive
    paths in the app:

      1. **Title locked-shape** —
         ``@st.dialog("Delete this <noun>?")``.
      2. **Irreversibility cue** — body warning contains "cannot be
         undone".
      3. **Cascade-effect copy** — for paths whose FK cascade drops
         child rows, the body must spell out each cascade-affected
         entity (so the user knows what's about to disappear).
      4. **Every database.delete_* caller is inside a dialog
         function** — no bare button → delete (would break GUIDELINES
         §8).
      5. **Failure preserves the pending sentinel** — except handlers
         in the dialog must NOT pop the pending sentinel, so the
         dialog re-opens for retry on the next rerun (gotcha #3 +
         Opportunities precedent).

    Per-page behavioural tests (click → dialog opens → Confirm/Cancel
    paths, plus the FK-cascade DB assertions) live in:

      • tests/test_opportunities_page.py::TestDeleteAction
      • tests/test_applications_page.py::TestApplicationsInterviewDeleteDialog
      • tests/test_recommenders_page.py::TestRecommenderEditDelete

    This class is a thin structural pin on top of those — it's
    checking the *audit invariants* (what every delete path looks
    like at the source level), not duplicating each page's
    end-to-end click flows.
    """

    @pytest.mark.parametrize("path", DESTRUCTIVE_PATHS, ids=lambda p: p["page"])
    def test_dialog_decorator_locked_shape(self, path: dict) -> None:
        """Each destructive path's dialog function is decorated with
        the verbatim ``@st.dialog("Delete this <noun>?")`` line. The
        verbatim source-grep catches drift in either the decorator
        attribute (e.g., a future Streamlit rename to ``st.modal``)
        or the title string (which is what the user reads when the
        dialog opens — locked across pages for consistency)."""
        src = pathlib.Path(path["page"]).read_text(encoding="utf-8")
        expected = f'@st.dialog("{path["title"]}")'
        assert expected in src, (
            f"{path['page']} must wear {expected!r} on its dialog function per GUIDELINES §8."
        )

    @pytest.mark.parametrize("path", DESTRUCTIVE_PATHS, ids=lambda p: p["page"])
    def test_dialog_body_says_cannot_be_undone(self, path: dict) -> None:
        """Every dialog body must contain the irreversibility cue
        "cannot be undone" — the universal minimum so the user
        understands the click is destructive. Cascading deletes get
        this AS WELL AS the cascade-effect copy (next test);
        leaf deletes (interview, recommender) get only this cue."""
        src = pathlib.Path(path["page"]).read_text(encoding="utf-8")
        tree = ast.parse(src)
        fn = _find_function(tree, path["dialog_fn"])
        assert fn is not None, (
            f"{path['page']} is missing function {path['dialog_fn']} — "
            f"was the dialog function renamed?"
        )
        body_src = (ast.get_source_segment(src, fn) or "").lower()
        assert "cannot be undone" in body_src, (
            f"{path['page']}::{path['dialog_fn']} body must contain "
            f"'cannot be undone' as the universal irreversibility "
            f"cue (GUIDELINES §8)."
        )

    @pytest.mark.parametrize(
        "path",
        [p for p in DESTRUCTIVE_PATHS if p["cascade_substrings"]],
        ids=lambda p: p["page"],
    )
    def test_dialog_body_lists_cascade_effects(self, path: dict) -> None:
        """Cascading-delete dialogs must spell out each
        cascade-affected entity in the warning copy. The user
        clicking "Delete this position" needs to know they're also
        about to lose every application, every interview tied to
        those applications, and every recommender — the FK chain
        does this transparently in SQLite, but the UI has to
        surface it.

        Schema: positions → applications (CASCADE) → interviews
        (CASCADE); positions → recommenders (CASCADE). All four
        rows / four child tables drop together.

        Substring match (lowercased) so the test isn't tied to
        singular/plural choice in the prose."""
        src = pathlib.Path(path["page"]).read_text(encoding="utf-8")
        tree = ast.parse(src)
        fn = _find_function(tree, path["dialog_fn"])
        assert fn is not None
        body_src = (ast.get_source_segment(src, fn) or "").lower()
        missing = [s for s in path["cascade_substrings"] if s not in body_src]
        assert not missing, (
            f"{path['page']}::{path['dialog_fn']} body is missing "
            f"cascade-effect mention(s) of {missing}. Per spec the "
            f"position-delete warning must list applications + "
            f"interviews + recommenders (the three child tables that "
            f"drop on FK cascade)."
        )

    def test_every_database_delete_caller_inside_dialog(self) -> None:
        """No bare ``database.delete_*`` call may sit at module level
        or inside a non-``@st.dialog``-decorated function.

        AST-walks every page (and ``app.py``); for each
        ``database.delete_*`` call node, walks the ancestor chain to
        find an enclosing ``FunctionDef`` with ``@st.dialog`` on it.
        Failing example: a future "quick delete" button that calls
        ``database.delete_position`` directly from the click handler
        (no dialog) would slip past per-page tests but get caught
        here.

        Comments containing the substring ``database.delete_*`` are
        ignored automatically — ``ast.parse`` skips comment text."""
        violations: list[tuple[str, int, str]] = []
        for page in PAGE_FILES:
            src = pathlib.Path(page).read_text(encoding="utf-8")
            tree = ast.parse(src)
            _set_parents(tree)
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "database"
                    and node.func.attr.startswith("delete_")
                ):
                    continue
                inside_dialog = any(
                    isinstance(anc, ast.FunctionDef) and _has_dialog_decorator(anc)
                    for anc in _ancestors(node)
                )
                if not inside_dialog:
                    violations.append((page, node.lineno, node.func.attr))
        assert not violations, (
            f"database.delete_* calls outside @st.dialog functions: "
            f"{violations}. Per GUIDELINES §8, every irreversible "
            f"action must be gated by a confirm dialog."
        )

    @pytest.mark.parametrize("path", DESTRUCTIVE_PATHS, ids=lambda p: p["page"])
    def test_dialog_failure_preserves_pending_sentinel(self, path: dict) -> None:
        """Failure path of every dialog must NOT pop the pending
        sentinel — so when ``database.delete_*`` raises, the user
        sees ``st.error`` and the dialog re-opens for retry on the
        next rerun (no data loss, no stuck-modal state).

        Implementation: AST-walk the dialog function, find every
        ``st.session_state.pop`` call, walk up its ancestor chain,
        and fail if any ancestor is an ``ast.ExceptHandler``. The
        success-path pops (Confirm-button branch, Cancel-button
        branch) live OUTSIDE the except handler and stay legal.

        This pins the contract documented at every dialog's
        docstring ("Sentinels survive so the dialog re-opens for
        retry") to source structure rather than relying on each
        page's behavioural test alone."""
        src = pathlib.Path(path["page"]).read_text(encoding="utf-8")
        tree = ast.parse(src)
        fn = _find_function(tree, path["dialog_fn"])
        assert fn is not None
        _set_parents(tree)
        for node in ast.walk(fn):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "pop"
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "session_state"
            ):
                continue
            inside_except = any(isinstance(anc, ast.ExceptHandler) for anc in _ancestors(node))
            assert not inside_except, (
                f"{path['page']}::{path['dialog_fn']}: "
                f"st.session_state.pop at line {node.lineno} sits "
                f"inside an except handler. Failure must preserve the "
                f"pending sentinel so the dialog re-opens for retry "
                f"per GUIDELINES §8 + the dialog's own docstring."
            )


class TestImportContractSweep:
    """DESIGN §2 layer-rule enforcement.

    Each test source-greps one architectural invariant that must hold
    across all page files and database.py. These mirror the contract
    stated in GUIDELINES §2 Module Import Contract.
    """

    PAGE_FILES = [
        "app.py",
        "pages/1_Opportunities.py",
        "pages/2_Applications.py",
        "pages/3_Recommenders.py",
        "pages/4_Export.py",
    ]

    def test_database_never_imports_streamlit(self):
        """database.py must never import streamlit at module top-level."""
        src = pathlib.Path("database.py").read_text()
        # Module-top imports only — deferred imports inside functions are allowed.
        top_level = "\n".join(
            line
            for line in src.splitlines()
            if not line.startswith(" ") and not line.startswith("\t")
        )
        assert "import streamlit" not in top_level, (
            "database.py has a module-top 'import streamlit' — DESIGN §2 forbids this."
        )

    def test_pages_never_import_exports(self):
        """pages/*.py and app.py must never directly import exports.py."""
        for page in self.PAGE_FILES:
            src = pathlib.Path(page).read_text()
            top_level = "\n".join(
                line
                for line in src.splitlines()
                if not line.startswith(" ") and not line.startswith("\t")
            )
            assert "import exports" not in top_level, (
                f"{page} has a top-level 'import exports' — "
                "DESIGN §2 forbids pages from importing exports directly."
            )

    def test_pages_no_raw_sql(self):
        """pages/*.py and app.py must never contain raw SQL (.execute() calls or sqlite3 imports)."""
        for page in self.PAGE_FILES:
            src = pathlib.Path(page).read_text()
            # Only scan non-comment lines so documentation comments that
            # mention sqlite3 by name don't trip the rule.  We care about
            # actual imports / usage, not incidental prose references.
            for line in src.splitlines():
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                assert "sqlite3" not in stripped, (
                    f"{page}: found 'sqlite3' outside a comment — "
                    "pages must use database.* helpers only."
                )
                # .execute( is a strong signal of raw SQL; exclude HTML/JS contexts
                assert ".execute(" not in stripped, (
                    f"{page}: found '.execute(' — raw SQL in page files is forbidden."
                )
