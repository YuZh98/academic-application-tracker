# pages/5_Settings.py
# R1b in-UI settings page — tunable thresholds + append-only vocabulary
# editor. Writes to a JSON overlay next to the DB so the import-time
# invariants in config.py stay authoritative for defaults.

import streamlit as st

import config
import database
import db_session
import ui

st.set_page_config(
    page_title="Settings — Academic Application Tracker",
    page_icon="📋",
    layout="wide",
)

db_session.bind()
database.init_db()
ui.inject_global_styles()
ui.demo_banner()
ui.sidebar_about_block()
ui.sidebar_shortcuts_block()
ui.sidebar_demo_reset_block(db_session.reset)

ui.colophon("Settings")
ui.page_mark("¶")
st.title("Settings")
ui.accent_bar()
st.markdown(
    "<p class='aat-tagline'>Threshold tuning and vocabulary management without leaving the app.</p>",
    unsafe_allow_html=True,
)

if config.IS_DEMO:
    st.info(
        "Settings changes do not persist in the public demo — every "
        "session starts fresh from the defaults. Self-host the app to "
        f"tune thresholds and vocabulary against your real data ([setup "
        f"guide]({config.DEMO_SELF_HOST_URL}))."
    )

settings = database.load_settings()

# ── Thresholds ───────────────────────────────────────────────────────────────

st.subheader("Alert thresholds")
st.caption(
    "Each value is bounded; out-of-range entries are rejected at save time. "
    "Defaults come from config.py."
)

with st.form("settings_thresholds_form"):
    deadline_days = st.number_input(
        "Deadline alert window (days)",
        min_value=1,
        max_value=365,
        value=int(settings["DEADLINE_ALERT_DAYS"]),
        step=1,
        key="settings_deadline_alert_days",
        help="Upcoming panel banding threshold — positions within N days are highlighted.",
    )
    recommender_days = st.number_input(
        "Recommender follow-up window (days)",
        min_value=1,
        max_value=90,
        value=int(settings["RECOMMENDER_ALERT_DAYS"]),
        step=1,
        key="settings_recommender_alert_days",
        help="Days after an ask date before a recommender shows as pending.",
    )
    upcoming_days = st.number_input(
        "Upcoming-window default (days)",
        min_value=1,
        max_value=90,
        value=int(settings["UPCOMING_WINDOW_DAYS"]),
        step=1,
        key="settings_upcoming_window_days",
        help="Default value of the dashboard's deadline-window selectbox.",
    )
    thresholds_submitted = st.form_submit_button(
        "Save thresholds",
        key="settings_thresholds_submit",
        disabled=config.IS_DEMO,
    )

if thresholds_submitted:
    try:
        database.save_settings(
            {
                "DEADLINE_ALERT_DAYS": int(deadline_days),
                "RECOMMENDER_ALERT_DAYS": int(recommender_days),
                "UPCOMING_WINDOW_DAYS": int(upcoming_days),
            }
        )
        st.toast("Thresholds saved.")
        st.rerun()
    except ValueError as e:
        st.error(f"Could not save: {e}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")

# ── Vocabulary ───────────────────────────────────────────────────────────────

st.subheader("Status vocabulary (append-only)")
st.caption(
    "Add new pipeline statuses here. Removal is blocked while any position "
    "currently holds the status — clear those rows first via the Edit panel."
)

current_statuses = list(settings.get("STATUS_VALUES", config.STATUS_VALUES))
st.write("Current order:", ", ".join(current_statuses))

with st.form("settings_vocab_form"):
    new_status = st.text_input(
        "New status (must be a bracketed sentinel, e.g. [GHOSTED])",
        key="settings_new_status",
        placeholder="[GHOSTED]",
    )
    vocab_submitted = st.form_submit_button(
        "Append",
        key="settings_vocab_submit",
        disabled=config.IS_DEMO,
    )

if vocab_submitted:
    candidate = (new_status or "").strip()
    if not candidate.startswith("[") or not candidate.endswith("]"):
        st.error("New status must be a bracketed sentinel, e.g. [GHOSTED].")
    else:
        try:
            database.update_status_vocabulary(append=[candidate])
            st.toast(f"Appended {candidate}.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not append: {e}")
