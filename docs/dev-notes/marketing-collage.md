# Marketing-collage refresh ritual

The README hero at `docs/ui/screenshots/v0.14.0/collage.png` is composited from four screenshots of the running app via `scripts/build_collage.py`. The PNG, its SHA256 hash, and the four source captures must all land in the same commit; otherwise `tests/test_collage_integrity.py` fails.

This file documents the end-to-end refresh procedure. Run it when:

- Any of the four primary pages (Dashboard, Opportunities, Applications, Recommenders) gets a UI change that should be reflected in marketing material.
- `playwright` is bumped in `requirements-dev.txt` — Chromium ships with the package, so a version bump usually shifts pixels.
- The visual spec in `scripts/collage.html` is intentionally edited.

## Pre-flight

```bash
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
playwright install chromium            # separate from pip install
```

The Chromium binary is **not** pulled by `pip install`; it lives in `~/Library/Caches/ms-playwright/` (macOS) or `~/.cache/ms-playwright/` (Linux). Each `playwright` version maps to one Chromium revision, which is what gives the byte-integrity test its stable ground truth.

## Pass 1 — README screenshots (not the collage)

If only the per-page README PNGs need a refresh, follow the recipe in your shell memory entry `reference_streamlit_screenshot_stack.md`. That pass uses a thin 200-px sidebar override and writes directly to `docs/ui/screenshots/v0.14.0/{dashboard,opportunities,...}.png`.

## Pass 2 — collage source captures (4 PNGs)

The collage tiles need landscape-aspect captures with the sidebar hidden and alternating themes:

| Tile | Page | Theme | Viewport | Scroll |
|---|---|---|---|---|
| c1 | Dashboard | light (default) | 1280×580×2 | `stMain.scrollTop = 480` (skip "Good afternoon" hero) |
| c2 | Opportunities | dark (`emulate(colorScheme: "dark")`) | 1024×530×2 | `stMain.scrollTop = 280` |
| c3 | Applications | light | 1024×450×2 | `stMain.scrollTop = 240` |
| c4 | Recommenders | dark | 1024×450×2 | `stMain.scrollTop = 200` |

For each capture, inject this CSS after every `navigate_page` (Streamlit resets the DOM on nav):

```js
() => {
  let s = document.getElementById('aat-collage-css');
  if (!s) { s = document.createElement('style'); s.id = 'aat-collage-css'; document.head.appendChild(s); }
  s.textContent = `
    section[data-testid="stSidebar"] { display: none !important; }
    section[data-testid="stMain"]    { margin-left: 0 !important; padding-left: 0 !important; }
    [data-testid="stAppViewContainer"] > section:first-child { display: none !important; }
    [data-testid="stMainBlockContainer"] { padding-top: 1rem !important; }
  `;
  document.querySelector('section[data-testid="stMain"]').scrollTop = /* per-tile value */;
}
```

Then `take_screenshot` to `docs/ui/screenshots/v0.14.0/.collage-src/<page>.png`. That directory is gitignored — only the composed `collage.png` is tracked.

Driver: `chrome-devtools-mcp` (the running tool's MCP server) is the easiest interactive harness. Seed a throwaway DB first so no real applicant data leaks:

```bash
rm -f demo.db
AAT_DB_PATH=$PWD/demo.db python3 scripts/seed_demo_db.py
AAT_DB_PATH=$PWD/demo.db streamlit run app.py --server.port 8519 --server.headless true --client.toolbarMode minimal
```

## Pass 3 — composite + refresh the hash

```bash
python3 scripts/build_collage.py
shasum -a 256 docs/ui/screenshots/v0.14.0/collage.png | cut -d' ' -f1 > scripts/collage_hash.txt
pytest tests/test_collage_integrity.py -v
```

If the test passes, commit the four files together:

```bash
git add docs/ui/screenshots/v0.14.0/collage.png \
        scripts/collage_hash.txt
git commit -m "fix: refresh marketing collage"
```

Source PNGs in `.collage-src/` stay gitignored. Re-running the builder on the same source PNGs must produce a byte-identical output — `tests/test_collage_integrity.py` will catch any drift the next time CI runs.

## Cross-platform note

The committed hash is captured on whatever machine ran the refresh. Chromium font rendering is largely deterministic across macOS and Linux *for the same Chromium revision*, but minor pixel differences across OSes are possible. If CI starts failing the integrity test after a fresh refresh on a different OS than the original capture, regenerate the hash on the OS CI uses (Ubuntu) and commit that hash.

## Why a byte-integrity test, not a re-render determinism test?

The integrity test only proves `committed PNG ↔ committed hash`. It does **not** prove the renderer is deterministic — that's what the *manual* re-run step in Pass 3 verifies (run the builder twice, confirm the hash doesn't drift). Adding a Playwright-invoking test in CI would force the CI runner to install Chromium on every job, which isn't worth the cost for a marketing asset.
