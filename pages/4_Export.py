# pages/4_Export.py
# Streamlit page — Export.
#
# Phase 6 T4: page shell + manual regenerate button + per-file mtimes
# panel (DESIGN §8.5; docs/ui/wireframes.md#export).
#   - set_page_config(layout="wide"), database.init_db(), st.title("Export")
#   - One-line intro (wireframe-pinned).
#   - st.button("Regenerate all markdown files", key="export_regenerate",
#     type="primary") wraps exports.write_all() in try/except per
#     GUIDELINES §8 (friendly error, no re-raise) — the inner per-writer
#     log-and-continue (DESIGN §7 contract #1) means only EXPORTS_DIR.mkdir
#     failures should reach the handler.
#   - Per-file mtimes block: one st.markdown line per locked filename,
#     either "**FILENAME.md** — last generated: {YYYY-MM-DD HH:MM:SS}"
#     or "**FILENAME.md** — not yet generated" when the file is absent.
# Phase 6 T5: download_button per file + "── Download ───" wireframe
# section header (rendered as st.divider() + st.subheader("Download")).
# Each per-file row now carries (download_button, mtime line) stacked
# vertically; the button is enabled when the file exists with
# data=Path.read_bytes(), disabled with data=b"" when absent.

from datetime import datetime
from pathlib import Path

import streamlit as st

import database
import exports

# DESIGN §8.0 + D14: every page's FIRST Streamlit call is set_page_config
# with wide layout. Must precede any other st.* call.
st.set_page_config(
    page_title="Postdoc Tracker",
    page_icon="📋",
    layout="wide",
)

# Idempotent — picks up any pending REQUIREMENT_DOCS / vocabulary
# migrations when this page is opened first in a session, and is the
# pattern matched by app.py + every other page.
database.init_db()

st.title("Export")

# Wireframe-pinned intro (docs/ui/wireframes.md#export).
st.markdown(
    "Markdown files are auto-exported after every data change. "
    "Use this page to trigger a manual export or download files."
)

# ── Regenerate button ────────────────────────────────────────────────────────
#
# Calls `exports.write_all()`. Per DESIGN §7 contract #1, write_all
# log-and-continues on individual writer failure (each `write_*` runs
# inside its own try/except), so only the EXPORTS_DIR.mkdir leg of
# write_all can surface an exception to this handler. GUIDELINES §8
# wraps the call so the user sees a friendly st.error rather than a
# traceback, and the click handler does NOT re-raise — the button is
# still rendered after a failure so the user can retry.

if st.button(
    "Regenerate all markdown files",
    key="export_regenerate",
    type="primary",
):
    try:
        exports.write_all()
        st.toast("Markdown files regenerated.")
    except Exception as e:
        # GUIDELINES §8: friendly error, no re-raise. Mirror of every
        # other page's save / delete handler shape.
        st.error(f"Could not regenerate: {e}")


# ── Download section ────────────────────────────────────────────────────────
#
# T5 deliverable: per-file download buttons + the wireframe-pinned
# "── Download ───" section header (rendered as st.divider() +
# st.subheader("Download") — the Streamlit-idiomatic equivalent of the
# ASCII rule in docs/ui/wireframes.md#export).
#
# T4 deliverable interleaved per file: the existing
# "**{filename}** — last generated: ..." / "not yet generated" mtime
# line still renders below each download button. Two stacked elements
# per file rather than a side-by-side st.columns layout — the column
# rendering would have moved the bold filename onto the button label
# and broken T4's substring assertions in TestExportPageMtimesPanel.
#
# The three filenames mirror the three exports.write_* generators
# (Phase 6 T1 / T2 / T3); the order here matches the wireframe.
#
# `Path.exists()` check first rather than `try / except FileNotFoundError`
# on `.stat()` / `.read_bytes()` — both are idiomatic, but exists()
# reads cleaner for a pure-read panel and lets the same boolean drive
# both the download-button disabled state AND the mtime-line branch.
# The race (file deleted between exists() and stat()) is irrelevant on
# a single-user local app.

st.divider()
st.subheader("Download")

_EXPORT_FILENAMES = ("OPPORTUNITIES.md", "PROGRESS.md", "RECOMMENDERS.md")

for _filename in _EXPORT_FILENAMES:
    _path: Path = exports.EXPORTS_DIR / _filename
    _file_present = _path.exists()

    # T5 download button — enabled when the file exists with the file
    # bytes as data, disabled with empty data when absent. Locked
    # widget key per AGENTS.md (`export_download_<filename>`).
    if _file_present:
        st.download_button(
            label=f"⬇ {_filename}",
            data=_path.read_bytes(),
            file_name=_filename,
            mime="text/markdown",
            key=f"export_download_{_filename}",
        )
    else:
        st.download_button(
            label=f"⬇ {_filename}",
            data=b"",
            file_name=_filename,
            mime="text/markdown",
            key=f"export_download_{_filename}",
            disabled=True,
        )

    # T4 mtime line, unchanged — the "**{filename}** — ..." prose stays
    # the load-bearing substring that T4 tests pin against.
    if _file_present:
        _ts = datetime.fromtimestamp(_path.stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        st.markdown(f"**{_filename}** — last generated: {_ts}")
    else:
        st.markdown(f"**{_filename}** — not yet generated")
