"""Byte-integrity check for the marketing collage.

This test does NOT re-render the collage — it only verifies that the
committed `docs/ui/screenshots/v0.14.0/collage.png` matches the SHA256
committed at `scripts/collage_hash.txt`. The pair must always land in the
same commit; a mismatch means someone updated one without the other.

For an actual re-render determinism check (across Playwright bumps /
Chromium revs), run `scripts/build_collage.py` locally and confirm the
fresh hash equals the committed hash; the script's docstring documents
the refresh ritual.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLAGE_PATH = REPO_ROOT / "docs" / "ui" / "screenshots" / "v0.14.0" / "collage.png"
HASH_PATH = REPO_ROOT / "scripts" / "collage_hash.txt"


def test_collage_image_exists() -> None:
    assert COLLAGE_PATH.is_file(), (
        f"Marketing collage missing at {COLLAGE_PATH}. "
        f"Run: python3 scripts/build_collage.py"
    )


def test_collage_hash_file_exists() -> None:
    assert HASH_PATH.is_file(), (
        f"Golden hash file missing at {HASH_PATH}. "
        f"Generate it after running scripts/build_collage.py."
    )


def test_collage_hash_matches_committed_value() -> None:
    if not COLLAGE_PATH.is_file() or not HASH_PATH.is_file():
        pytest.skip("collage.png or collage_hash.txt missing; sibling tests will fail.")

    expected_hash = HASH_PATH.read_text().strip()
    actual_hash = hashlib.sha256(COLLAGE_PATH.read_bytes()).hexdigest()

    assert actual_hash == expected_hash, (
        f"collage.png / collage_hash.txt out of sync — one was updated without the other.\n"
        f"  expected: {expected_hash}\n"
        f"  actual:   {actual_hash}\n"
        f"Refresh both together — see scripts/build_collage.py for the ritual."
    )
