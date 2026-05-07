# pages/4_Export.py
# Export page

from datetime import datetime

import streamlit as st

import database

st.set_page_config(
    page_title="Export — Academic Application Tracker",
    page_icon="📋",
    layout="wide",
)


database.init_db()

st.title("Export & Download")

st.markdown(
    "Markdown files are auto-exported after every data change and saved to the "
    "`exports/` folder in your project directory. Use **Regenerate** if a file "
    "looks stale, or **Download** to save a copy elsewhere."
)

# ── Regenerate button ────────────────────────────────────────────────────────

if st.button(
    "Regenerate all markdown files",
    key="export_regenerate",
    type="primary",
):
    try:
        database.regenerate_exports()
        st.toast("All markdown files regenerated.")
    except Exception as e:
        st.error(f"Could not regenerate: {e}")


# ── Download section ────────────────────────────────────────────────────────

st.divider()
st.subheader("Download Files")

for _filename, _path in database.get_export_paths():
    _file_present = _path.exists()

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
