"""Render docs/ui/screenshots/v0.14.0/collage.png from scripts/collage.html.

Uses Playwright + the pinned-Chromium revision shipped with the playwright
version in requirements-dev.txt. Determinism guards: disable LCD subpixel
text, force prefers-reduced-motion, no font hinting.

Prerequisite: the four .collage-src PNGs must already exist (run Pass 2 of
the capture pipeline first). This script does not invoke Streamlit; it only
composites.

Usage:
    python3 scripts/build_collage.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
COLLAGE_HTML = REPO_ROOT / "scripts" / "collage.html"
SOURCE_DIR = REPO_ROOT / "docs" / "ui" / "screenshots" / "v0.14.0" / ".collage-src"
OUTPUT_PATH = REPO_ROOT / "docs" / "ui" / "screenshots" / "v0.14.0" / "collage.png"

REQUIRED_SOURCES = ("dashboard.png", "opportunities.png", "applications.png", "recommenders.png")

CANVAS_WIDTH = 2880
CANVAS_HEIGHT = 1620

CHROMIUM_FLAGS = [
    "--font-render-hinting=none",
    "--disable-lcd-text",
    "--force-prefers-reduced-motion",
    "--disable-features=PaintHolding",
]


def _verify_sources() -> None:
    missing = [name for name in REQUIRED_SOURCES if not (SOURCE_DIR / name).is_file()]
    if missing:
        sys.stderr.write(
            "ERROR: required collage source PNGs missing:\n"
            + "\n".join(f"  {SOURCE_DIR / m}" for m in missing)
            + "\n\nRun Pass 2 of the capture pipeline to regenerate them.\n"
        )
        sys.exit(2)


def render_collage() -> Path:
    _verify_sources()
    with sync_playwright() as p:
        browser = p.chromium.launch(args=CHROMIUM_FLAGS)
        context = browser.new_context(
            viewport={"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
            device_scale_factor=1,
            color_scheme="light",
            reduced_motion="reduce",
        )
        page = context.new_page()
        page.goto(f"file://{COLLAGE_HTML}")
        page.wait_for_function(
            "() => Array.from(document.images).every(img => img.complete && img.naturalWidth > 0)"
        )
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(
            path=str(OUTPUT_PATH),
            type="png",
            full_page=False,
            omit_background=False,
            clip={"x": 0, "y": 0, "width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
        )
        browser.close()
    return OUTPUT_PATH


if __name__ == "__main__":
    out = render_collage()
    print(f"Wrote {out} ({out.stat().st_size:,} bytes)")
