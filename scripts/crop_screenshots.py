"""Auto-crop README screenshots.

Removes Streamlit Cloud top chrome (white "Deploy" bar) and trims trailing
uniform cream/white margins. Idempotent: re-running on already-tight images
is a near no-op.

Usage: python scripts/crop_screenshots.py [path ...]
Defaults to docs/ui/screenshots/v0.14.0/*.png.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

PAD = 16
CONTENT_GRAY_MAX = 220.0
ROW_DARK_MIN = 30
COL_DARK_MIN = 1
# Probe deep enough to cover the Streamlit chrome strip at any reasonable
# devicePixelRatio (the strip is ~50 CSS px so 400 native rows is safe for
# DPR up to 4×; was 200 at 1× DPR which let a sliver leak through at 2×).
CHROME_PROBE_ROWS = 400
CHROME_CREAM_CUTOFF = 242.0
# Fallback when the detector finds no white→cream transition in the probe
# window. Streamlit always renders a top chrome strip in headless mode, so
# we trim a safe minimum from every capture and let the body-content scan
# tighten the rest.
CHROME_FALLBACK_ROWS = 160
DEFAULT_DIR = Path("docs/ui/screenshots/v0.14.0")


def find_chrome_bottom(arr: np.ndarray) -> int:
    """First row where the page transitions from the Streamlit chrome
    (white-ish "Deploy" badge strip) into the cream app body.

    Detects against the rightmost 200 columns only — the chrome strip's
    pure-white badge area — because averaging across the full row pulls
    the mean down with cream sidebar pixels and silently disables chrome
    trimming. At 2× DPR the full-row mean fell below the cream cutoff on
    the very first chrome row, so the old logic returned 0 and let the
    "Deploy" sliver leak into the final crop.

    Falls through to ``CHROME_FALLBACK_ROWS`` when no transition is found
    in the probe window: Streamlit always renders a top chrome strip in
    headless mode, so an empty detection is itself a signal that the
    detector missed (not that there's no chrome).
    """
    right_cols = arr[:CHROME_PROBE_ROWS, -200:]
    row_mean = right_cols.mean(axis=(1, 2))
    below = np.where(row_mean < CHROME_CREAM_CUTOFF)[0]
    if below.size:
        return int(below[0])
    return CHROME_FALLBACK_ROWS


def crop_one(path: Path) -> tuple[tuple[int, int], tuple[int, int]]:
    img = Image.open(path).convert("RGB")
    arr = np.array(img)
    H, W = arr.shape[:2]

    chrome_bottom = find_chrome_bottom(arr)
    body = arr[chrome_bottom:]
    gray = body.mean(axis=2)
    content = gray < CONTENT_GRAY_MAX

    row_count = content.sum(axis=1)
    col_count = content.sum(axis=0)
    rows = np.where(row_count >= ROW_DARK_MIN)[0]
    cols = np.where(col_count >= COL_DARK_MIN)[0]
    if rows.size == 0 or cols.size == 0:
        return (W, H), (W, H)

    left = max(0, int(cols[0]) - PAD)
    right = min(body.shape[1], int(cols[-1]) + 1 + PAD)
    top = max(0, int(rows[0]) - PAD)
    bottom = min(body.shape[0], int(rows[-1]) + 1 + PAD)

    cropped = body[top:bottom, left:right]
    Image.fromarray(cropped).save(path, optimize=True)
    return (W, H), (cropped.shape[1], cropped.shape[0])


def main(argv: list[str]) -> int:
    if argv:
        paths = [Path(p) for p in argv]
    else:
        paths = sorted(DEFAULT_DIR.glob("*.png"))
    if not paths:
        print("no images found", file=sys.stderr)
        return 1
    for p in paths:
        before, after = crop_one(p)
        print(f"{p.name}: {before[0]}x{before[1]} -> {after[0]}x{after[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
