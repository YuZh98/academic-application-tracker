# pages/4_Export.py
# Export page — manual regenerate trigger and per-file download buttons.

from datetime import datetime

import streamlit as st

import database

# DESIGN §8.0 + D14: every page's FIRST Streamlit call is set_page_config
# with wide layout. Must precede any other st.* call.
st.set_page_config(
    page_title="Export — Academic Application Tracker",
    page_icon="📋",
    layout="wide",
)

# Idempotent — picks up any pending REQUIREMENT_DOCS / vocabulary
# migrations when this page is opened first in a session, and is the
# pattern matched by app.py + every other page.
database.init_db()

st.title("Export & Download")

# Wireframe-pinned intro (docs/ui/wireframes.md#export).
st.markdown(
    "Markdown files are auto-exported after every data change and saved to the "
    "`exports/` folder in your project directory. Use **Regenerate** if a file "
    "looks stale, or **Download** to save a copy elsewhere."
)

# ── Regenerate button ────────────────────────────────────────────────────────
#
# Calls database.regenerate_exports() — the thin wrapper in database.py
# that imports exports lazily (deferred import to break circular
# dependency) and calls write_all(). Errors propagate here so the page
# can surface them via st.error. GUIDELINES §8: no re-raise, button
# still rendered after failure so user can retry.

if st.button(
    "Regenerate all markdown files",
    key="export_regenerate",
    type="primary",
):
    try:
        database.regenerate_exports()
        st.toast("All markdown files regenerated.")
    except Exception as e:
        # GUIDELINES §8: friendly error, no re-raise. Mirror of every
        # other page's save / delete handler shape.
        st.error(f"Could not regenerate: {e}")


# ── Download section ────────────────────────────────────────────────────────
#
# T5 deliverable: per-file download buttons + the wireframe-pinned
# "── Download ───" section header (rendered as st.divider() +
# st.subheader("Download") — the Streamlit-idiomatic equivalent of the
# section header (rendered as st.divider() + st.subheader("Download Files") —
# the Streamlit-idiomatic equivalent of the ASCII rule in
# docs/ui/wireframes.md#export).
#
# T4 deliverable interleaved per file: the
# "**{filename}** — last generated: ..." / "not yet generated ..." mtime
# line still renders below each download button, followed by a caption
# describing the file's contents. Two stacked elements per file rather
# than a side-by-side st.columns layout — the column rendering would have
# moved the bold filename onto the button label and broken T4's substring
# assertions in TestExportPageMtimesPanel.
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
st.subheader("Download Files")

_EXPORT_FILENAMES = ("OPPORTUNITIES.md", "PROGRESS.md", "RECOMMENDERS.md")

for _filename, _path in database.get_export_paths():
    _file_present = _path.exists()

    # T5 download button — enabled when the file exists with the file
    # bytes as data, disabled with empty data when absent. Locked
    # widget key per AGENTS.md (`export_download_<filename>`).
    if _file_present:
        st.download_button(
            label=f"⬇️ {_filename.lower()}",
            data=_path.read_bytes(),
            file_name=_filename,
            mime="text/markdown",
            key=f"export_download_{_filename}",
        )
    else:
        st.download_button(
            label=f"⬇️ {_filename.lower()}",
            data=b"",
            file_name=_filename,
            mime="text/markdown",
            key=f"export_download_{_filename}",
            disabled=True,
        )

    # T4 mtime line — human-readable timestamp or guidance when not yet
    # generated. The "**{filename}** — ..." prose is the load-bearing
    # substring that T4 tests pin against.
    if _file_present:
        _dt = datetime.fromtimestamp(_path.stat().st_mtime)
        _ts = _dt.strftime(f"%b {_dt.day}, %Y at %I:%M %p").replace(" 0", " ")
        st.markdown(f"**{_filename}** — last generated: {_ts}")
    else:
        st.markdown(f"**{_filename}** — not yet generated. Use **Regenerate** above to create it.")

    # Per-file caption describing the file's contents.
    if _filename == "OPPORTUNITIES.md":
        st.caption("All tracked positions with deadlines, status, and requirements.")
    elif _filename == "PROGRESS.md":
        st.caption("Application submission status, responses, and interview records.")
    elif _filename == "RECOMMENDERS.md":
        st.caption("Recommendation letter requests, confirmations, and submission dates.")
