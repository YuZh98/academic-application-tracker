"""Golden-image hash check for the marketing collage.

The collage is rendered by scripts/build_collage.py from a pinned Chromium
revision. A SHA256 hash of the rendered PNG lives in scripts/collage_hash.txt.
This test verifies that the file currently committed at
docs/ui/screenshots/v0.14.0/collage.png matches that hash byte-for-byte.

If the hash drifts (e.g. someone bumped playwright without regenerating),
this test fails loudly. Refresh path: re-run scripts/build_collage.py and
manually update scripts/collage_hash.txt in a documented commit.
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
        f"collage.png hash drift detected.\n"
        f"  expected: {expected_hash}\n"
        f"  actual:   {actual_hash}\n"
        f"If this drift is intentional (e.g. playwright bumped), regenerate "
        f"the hash via:  sha256sum {COLLAGE_PATH} | cut -d' ' -f1 > {HASH_PATH}"
    )
