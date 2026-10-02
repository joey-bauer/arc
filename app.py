from pathlib import Path
import sqlite3
from datetime import datetime, timezone

import streamlit as st

from database import (
    get_active_session,
    initialize_database,
    start_session,
    stop_session,
)

st.set_page_config(page_title="Arc", page_icon="⚡", layout="centered")

styles_path = Path(__file__).resolve().parent / "styles.css"
st.html(styles_path)

st.title("Arc")

try:
    initialize_database()
    active_session = get_active_session()
except sqlite3.Error:
    st.error("Arc could not open the session database.")
    st.stop()

completion_message = st.session_state.pop("completion_message", None)
if completion_message:
    st.success(completion_message)

with st.container(border=True, key="coding_timer"):
    st.subheader("Coding Session")

    if active_session is None:
        st.metric("Elapsed Time", "00:00:00")
        st.caption("No coding session is active.")

        if st.button(
            "Start Coding Session",
            key="start_session",
            type="primary",
        ):
            try:
                start_session()
            except sqlite3.IntegrityError:
                st.warning(
                    "A session is already active. Refresh to see it."
                )
            except sqlite3.Error:
                st.error("Could not start the session. Please try again.")
            else:
                st.rerun()

    else:
        started_at = datetime.fromisoformat(active_session["started_at"])
        elapsed_seconds = max(
            0,
            int((datetime.now(timezone.utc) - started_at).total_seconds()),
        )

        hours, remainder = divmod(elapsed_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        st.metric(
            "Elapsed Time",
            f"{hours:02d}:{minutes:02d:{seconds:02d}}",
        )
        st.caption("Coding session active.")

        if st.button(
            "Stop Coding Session",
            key="stop_session",
            type="primary",
        ):
            try:
                duration = stop_session(active_session["id"])
            except ValueError as error:
                st.warning(str(error))
            except sqlite3.Error:
                st.error("Could not stop the session. Please try again.")
            else:
                st.session_state["completion_message"] = (
                    f"Session saved: {duration} seconds of coding."
                )
                st.rerun()