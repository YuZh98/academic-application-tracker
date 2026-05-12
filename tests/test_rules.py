"""Pinning tests for load-bearing rules from GUIDELINES.md.

Each rule is asserted via static analysis (AST inspection) of production code or
test code. A failing test means a rule was violated — fix the rule violation, do
not loosen the test, unless GUIDELINES is updated first.

References:
- GUIDELINES §5 (every writer ends with exports.write_all)
- GUIDELINES §7 (_skip_table_reset before st.rerun)
- GUIDELINES §9 (AppTest default_timeout=10)

Pragma exemption (G2 only):
  Add the inline comment ``# pragma: skip-table-reset-check`` on the same source
  line as the ``st.rerun()`` call to exempt it from the G2 check.  This is
  reserved for the two canonical delete-confirm paths where clearing the table
  selection is **intentional** — Confirm-Delete reruns that have already called
  ``session_state.pop("selected_*")`` before the rerun.  All other reruns inside
  save/delete handlers must set a ``*_skip_table_reset`` key first.

  Current exempted lines:
    - pages/1_Opportunities.py  ``_confirm_delete_dialog``   Confirm branch:
      position is deleted; selection is intentionally cleared before rerun.
    - pages/3_Recommenders.py   ``_confirm_delete_recommender_dialog``
      Confirm branch: recommender row is deleted; selection is intentionally
      cleared before rerun.
"""

import ast
from pathlib import Path
from typing import Iterator

import pytest

REPO_ROOT = Path(__file__).parent.parent

_PAGES_DIR = REPO_ROOT / "pages"
_DATABASE_PY = REPO_ROOT / "database.py"
_TESTS_DIR = REPO_ROOT / "tests"


# ── shared AST helpers ────────────────────────────────────────────────────────


def _set_parents(tree: ast.AST) -> None:
    """Annotate every node with a ``.parent`` attribute."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node  # type: ignore[attr-defined]


def _ancestors(node: ast.AST) -> Iterator[ast.AST]:
    """Yield every ancestor of ``node`` walking outward to the root."""
    cur: ast.AST = node
    while getattr(cur, "parent", None) is not None:
        cur = cur.parent  # type: ignore[attr-defined]
        yield cur


def _enclosing_function(node: ast.AST) -> ast.FunctionDef | None:
    """Return the innermost enclosing FunctionDef, or None."""
    for anc in _ancestors(node):
        if isinstance(anc, ast.FunctionDef):
            return anc
    return None


def _is_write_all_call(node: ast.AST) -> bool:
    """Return True if ``node`` is a Call to ``_exports.write_all()`` or
    ``exports.write_all()``."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr != "write_all":
        return False
    if not isinstance(func.value, ast.Name):
        return False
    return func.value.id in ("_exports", "exports")


def _pragma_lines(source: str) -> set[int]:
    """Return the set of line numbers carrying ``# pragma: skip-table-reset-check``."""
    lines: set[int] = set()
    for lineno, line in enumerate(source.splitlines(), start=1):
        if "# pragma: skip-table-reset-check" in line:
            lines.add(lineno)
    return lines


def _enclosing_stmts(node: ast.AST) -> list[ast.stmt]:
    """Return the list of statements in the innermost enclosing block that
    contains ``node``.  Walks outward through parent links until it finds a
    node whose ``body`` (or ``orelse`` / ``handlers``) contains ``node``'s
    immediate parent statement."""
    # Walk up to find the containing statement list.
    cur: ast.AST = node
    while getattr(cur, "parent", None) is not None:
        parent = cur.parent  # type: ignore[attr-defined]
        for attr in ("body", "orelse", "finalbody", "handlers"):
            block = getattr(parent, attr, None)
            if block and isinstance(block, list) and cur in block:
                return block  # type: ignore[return-value]
        cur = parent
    return []


def _stmts_before(node: ast.AST, block: list[ast.stmt]) -> list[ast.stmt]:
    """Return the statements in ``block`` that appear strictly before ``node``."""
    result: list[ast.stmt] = []
    for stmt in block:
        if stmt is node:
            break
        result.append(stmt)
    return result


def _is_skip_table_reset_assign(stmt: ast.AST) -> bool:
    """Return True if ``stmt`` assigns ``True`` to a session_state key whose
    string name contains ``_skip_table_reset``.

    Matches the pattern:
        st.session_state["<anything>_skip_table_reset<anything>"] = True

    The subscript key check is intentionally a substring match so that
    page-local prefixed variants (``_applications_skip_table_reset``,
    ``_recs_skip_table_reset``) are all accepted alongside the canonical
    ``_skip_table_reset``.
    """
    if not isinstance(stmt, ast.Assign):
        return False
    if len(stmt.targets) != 1:
        return False
    target = stmt.targets[0]
    # Must be a subscript: st.session_state["<key>"]
    if not isinstance(target, ast.Subscript):
        return False
    # Value side: st.session_state
    value_node = target.value
    if not (
        isinstance(value_node, ast.Attribute)
        and value_node.attr == "session_state"
        and isinstance(value_node.value, ast.Name)
        and value_node.value.id == "st"
    ):
        return False
    # Subscript key must be a string constant containing "_skip_table_reset"
    key_node = target.slice
    if not isinstance(key_node, ast.Constant):
        return False
    if not isinstance(key_node.value, str):
        return False
    if "_skip_table_reset" not in key_node.value:
        return False
    # Assigned value must be True (the boolean constant)
    rhs = stmt.value
    if not isinstance(rhs, ast.Constant):
        return False
    return rhs.value is True


def _any_skip_in_block(block: list[ast.stmt], before: list[ast.stmt]) -> bool:
    """Return True if any statement in ``before`` is a skip-table-reset assign,
    OR if any sub-statement reachable from ``before`` (via nested if/try bodies)
    contains such an assign.

    We do a full ``ast.walk`` over each preceding statement so that assigns
    nested inside a try-block or if-branch are counted.
    """
    for stmt in before:
        for subnode in ast.walk(stmt):
            if _is_skip_table_reset_assign(subnode):
                return True
    return False


# ── Rule R5 ───────────────────────────────────────────────────────────────────


class TestEveryWriterCallsExports:
    """R5 (GUIDELINES §5): every public write function in database.py must call
    ``exports.write_all()`` somewhere in its body.

    The test is explicit about which functions are considered "writers" rather
    than relying on heuristic discovery (INSERT/UPDATE/DELETE patterns) so that
    accidental omission of exports.write_all() in a new writer is caught the
    moment the function name is added to WRITERS below.

    To add a new writer: add its name to WRITERS, implement the function with
    the required ``_exports.write_all()`` call, and the test passes.
    """

    WRITERS = {
        "add_position",
        "update_position",
        "delete_position",
        "upsert_application",
        "add_interview",
        "update_interview",
        "delete_interview",
        "add_recommender",
        "update_recommender",
        "delete_recommender",
        "regenerate_exports",
    }

    def test_every_writer_calls_exports_write_all(self) -> None:
        """Assert that every function in WRITERS has at least one call to
        ``_exports.write_all()`` or ``exports.write_all()`` in its body.

        Violation message includes function name and file path for immediate
        fix target.  Rule reference: GUIDELINES §5.
        """
        src = _DATABASE_PY.read_text(encoding="utf-8")
        tree = ast.parse(src)

        # Collect module-level FunctionDef nodes by name.
        fn_map: dict[str, ast.FunctionDef] = {}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                fn_map[node.name] = node

        violations: list[str] = []

        for fn_name in sorted(self.WRITERS):
            fn = fn_map.get(fn_name)
            if fn is None:
                violations.append(
                    f"database.py: writer '{fn_name}' not found at module level "
                    f"(was it renamed or moved into a class?). "
                    f"Rule R5 (GUIDELINES §5) requires every named writer to call "
                    f"exports.write_all()."
                )
                continue

            found = any(_is_write_all_call(node) for node in ast.walk(fn))
            if not found:
                violations.append(
                    f"database.py:{fn.lineno}: '{fn_name}' does not call "
                    f"_exports.write_all() / exports.write_all(). "
                    f"Every writer must call exports.write_all() per GUIDELINES §5 (R5)."
                )

        assert not violations, (
            "R5 violation(s) — writers missing exports.write_all() call:\n"
            + "\n".join(f"  {v}" for v in violations)
        )


# ── Rule G2 ───────────────────────────────────────────────────────────────────


class TestSkipTableResetBeforeRerun:
    """G2 (GUIDELINES §7): every Save / Delete handler in ``pages/`` that calls
    ``st.rerun()`` must set a ``*_skip_table_reset`` session-state key to
    ``True`` before the rerun.

    Without this, ``st.dataframe`` row selection collapses on the next render
    (gotcha #11).

    Scope: the check is limited to ``st.rerun()`` calls inside functions whose
    name contains ``save``, ``delete``, or ``submit`` (case-insensitive).
    Module-level reruns (e.g. post-quick-add form submits) are not in scope
    because selection clearing is intentional there.

    Pragma exemption: add ``# pragma: skip-table-reset-check`` on the same
    source line as ``st.rerun()`` to exempt a rerun that intentionally clears
    selection.  This is used for the two Confirm-Delete paths that already
    call ``session_state.pop("selected_*")`` before the rerun.

    Exempted locations:
      - pages/1_Opportunities.py  ``_confirm_delete_dialog`` Confirm branch
        (line with st.rerun() carries the pragma).
      - pages/3_Recommenders.py   ``_confirm_delete_recommender_dialog``
        Confirm branch (line with st.rerun() carries the pragma).
    """

    _HANDLER_KEYWORDS = ("save", "delete", "submit")

    def _is_handler_function(self, fn: ast.FunctionDef) -> bool:
        name_lower = fn.name.lower()
        return any(kw in name_lower for kw in self._HANDLER_KEYWORDS)

    def test_skip_table_reset_set_before_rerun(self) -> None:
        """For every ``st.rerun()`` call inside a handler function in
        ``pages/*.py``, assert that a ``*_skip_table_reset = True`` assignment
        exists in the same block (or an enclosing statement) before the rerun.

        Reports file:line of each violation.  Rule reference: GUIDELINES §7 (G2).
        """
        page_files = sorted(_PAGES_DIR.glob("*.py"))
        violations: list[str] = []

        for page_path in page_files:
            src = page_path.read_text(encoding="utf-8")
            pragma_lines = _pragma_lines(src)
            tree = ast.parse(src)
            _set_parents(tree)

            for node in ast.walk(tree):
                # Only care about st.rerun() calls.
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "rerun"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "st"
                ):
                    continue

                # Exempted by pragma on the same source line.
                if node.lineno in pragma_lines:
                    continue

                # Only check reruns inside handler functions.
                fn = _enclosing_function(node)
                if fn is None or not self._is_handler_function(fn):
                    continue

                # Find the enclosing statement that directly contains the rerun
                # expression statement (the Expr node wrapping the Call).
                enclosing_expr: ast.AST = node
                # Walk up to the Expr statement level
                while getattr(enclosing_expr, "parent", None) is not None:
                    if isinstance(enclosing_expr, ast.Expr):
                        break
                    enclosing_expr = enclosing_expr.parent  # type: ignore[attr-defined]

                # Get the statement list that contains this Expr node.
                block = _enclosing_stmts(enclosing_expr)
                before = _stmts_before(enclosing_expr, block)

                if not _any_skip_in_block(block, before):
                    rel = page_path.relative_to(REPO_ROOT)
                    violations.append(
                        f"{rel}:{node.lineno}: st.rerun() in "
                        f"'{fn.name}' without a preceding "
                        f"*_skip_table_reset = True assignment in the "
                        f"same block. Per GUIDELINES §7 (G2), every Save/"
                        f"Delete handler rerun must preserve table selection."
                    )

        assert not violations, (
            "G2 violation(s) — st.rerun() without _skip_table_reset:\n"
            + "\n".join(f"  {v}" for v in violations)
        )


# ── Rule G14 ──────────────────────────────────────────────────────────────────


class TestAppTestDefaultTimeout:
    """G14 (GUIDELINES §9): every ``AppTest.from_file(...)`` call in ``tests/``
    must pass ``default_timeout=10`` (or higher).

    The AppTest default timeout of 3 s is too short for CI runners under load
    and causes flaky test failures.  This test scans every ``tests/test_*.py``
    to enforce the requirement.

    Violation message includes file:line so the fix is immediate.
    """

    MIN_TIMEOUT = 10

    @pytest.mark.xfail(
        strict=False,
        reason=(
            "102 pre-existing AppTest.from_file() calls predate the G14 rule "
            "(codified in PR #98). Bridge: xfail until follow-on codemod PR "
            "adds default_timeout=10 to all violating calls, then flip "
            "strict=True to enforce."
        ),
    )
    def test_apptest_from_file_uses_default_timeout(self) -> None:
        """Assert that every ``AppTest.from_file(...)`` call in the test suite
        has a ``default_timeout`` keyword argument with an integer value >= 10.

        Rule reference: GUIDELINES §9 (G14).
        """
        test_files = sorted(_TESTS_DIR.glob("test_*.py"))
        violations: list[str] = []

        for test_path in test_files:
            src = test_path.read_text(encoding="utf-8")
            tree = ast.parse(src)

            for node in ast.walk(tree):
                # Match AppTest.from_file(...)
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "from_file"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "AppTest"
                ):
                    continue

                # Find the default_timeout keyword argument.
                timeout_kw = next(
                    (kw for kw in node.keywords if kw.arg == "default_timeout"),
                    None,
                )

                rel = test_path.relative_to(REPO_ROOT)

                if timeout_kw is None:
                    violations.append(
                        f"{rel}:{node.lineno}: AppTest.from_file() missing "
                        f"default_timeout kwarg. Per GUIDELINES §9 (G14), "
                        f"use AppTest.from_file(..., default_timeout=10)."
                    )
                    continue

                val = timeout_kw.value
                # Accept int Constant or Name (e.g. a constant variable).
                if isinstance(val, ast.Constant) and isinstance(val.value, int):
                    if val.value < self.MIN_TIMEOUT:
                        violations.append(
                            f"{rel}:{node.lineno}: AppTest.from_file() has "
                            f"default_timeout={val.value} < {self.MIN_TIMEOUT}. "
                            f"Per GUIDELINES §9 (G14), minimum is {self.MIN_TIMEOUT}."
                        )
                else:
                    # Non-literal: cannot statically check the value, skip.
                    # If using a named constant, ensure its value is >= 10.
                    pass

        assert not violations, (
            f"G14 violation(s) — AppTest.from_file() without "
            f"default_timeout>={self.MIN_TIMEOUT}:\n"
            + "\n".join(f"  {v}" for v in violations)
        )
