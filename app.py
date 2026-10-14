from pathlib import Path
import sqlite3
from datetime import datetime, timezone

import streamlit as st

from database import (
    create_project,
    get_active_session,
    get_completed_sessions,
    get_projects,
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
        st.caption("No coding session active.")

        try:
            projects = get_projects()
        except sqlite3.Error:
            st.error("Could not load projects. Please refresh to try again.")
        else:
            if not projects:
                st.info("Add a project in Project Bays before starting a session.")
            else:
                project_names = {
                    project["id"]: project["name"]
                    for project in projects
                }

                selected_project_id = st.selectbox(
                    "Project",
                    options=list(project_names),
                    format_func=lambda project_id: project_names[project_id],
                    key="session_project"
                )

                if st.button(
                    "Start Coding Session",
                    key="start_session",
                    type="primary",
                ):
                    try:
                        start_session(selected_project_id)
                    except ValueError as error:
                        st.warning(str(error))
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
            f"{hours:02d}:{minutes:02d}:{seconds:02d}",
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


with st.container(border=True, key="session_log"):
    st.subheader("Session Log")
    st.caption("Your ten most recent completed sessions. Start times are local.")

    try:
        completed_sessions = get_completed_sessions()
    except sqlite3.Error:
        st.error("Could not load the session log. Please refresh to try again.")
    else:
        if not completed_sessions:
            st.info("No completed sessions yet. Start a coding session and stop it to see it here.")
        else:
            session_rows = []
            for session in completed_sessions:
                # Keep UTC in storage and convert only for display.
                local_start = datetime.fromisoformat(session["started_at"]).astimezone()
                hours, remainder = divmod(session["duration_seconds"], 3600)
                minutes, seconds = divmod(remainder, 60)
                session_rows.append({
                    "Project": session["project_name"] or "Unassigned",
                    "Started": local_start.strftime("%Y-%m-%d %H:%M:%S %Z"),
                    "Duration (HH:MM:SS)": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
                })

            st.dataframe(session_rows, hide_index=True, width="stretch")

with st.container(border=True, key="project_bays"):
    st.subheader("Project Bays")

    with st.form(key="add_project_form"):
        project_name = st.text_input(
            "Project name",
            key="new_project_name",
        )
        submitted = st.form_submit_button("Add Project")

    if submitted:
        try:
            create_project(project_name)
        except ValueError as error:
            st.warning(str(error))
        except sqlite3.Error:
            st.error("Could not save the project. Please try again.")
        else:
            st.success("Project saved.")

    try:
        projects = get_projects()
    except sqlite3.Error:
        st.error("Could not load projects. Please refresh to try again.")
    else:
        if not projects:
            st.info("No projects yet. Add your first project above.")
        else:
            project_rows = []
            for project in projects:
                project_rows.append({
                    "Project": project["name"],
                })

            st.dataframe(
                project_rows,
                hide_index=True,
                width="stretch",
            )