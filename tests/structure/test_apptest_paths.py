# tests/structure/test_apptest_paths.py
# Grep-grade test: AppTest entry-point paths must be absolute.
# Streamlit >= 1.61 resolves a relative from_file() path against the
# calling test file, not the working directory, so a relative literal
# silently becomes tests/<path> and every AppTest in the file errors.

import pathlib
import re

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_TESTS_DIR = _REPO_ROOT / "tests"

# AppTest.from_file("...") with a bare string literal — the failing shape.
_RELATIVE_LITERAL = re.compile(r'AppTest\.from_file\(\s*["\']')

TEST_MODULES = sorted(p for p in _TESTS_DIR.rglob("test_*.py"))


@pytest.mark.parametrize("module", TEST_MODULES, ids=lambda p: p.name)
def test_no_relative_apptest_path_literals(module):
    """Entry-point paths reach AppTest via helpers.page_path(), never as a
    bare relative string. This module is exempt: it matches on the pattern."""
    if module.name == pathlib.Path(__file__).name:
        pytest.skip("this module contains the pattern it searches for")

    hits = [
        f"{module.relative_to(_REPO_ROOT)}:{n}: {line.strip()}"
        for n, line in enumerate(module.read_text().splitlines(), start=1)
        if _RELATIVE_LITERAL.search(line)
    ]
    assert not hits, (
        "AppTest.from_file() called with a relative string literal — wrap it in "
        "tests.helpers.page_path(...) so the path resolves from the repo root:\n"
        + "\n".join(hits)
    )
