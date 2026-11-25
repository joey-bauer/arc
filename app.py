from pathlib import Path
import sqlite3
from datetime import datetime, timedelta, timezone

import streamlit as st

from database import (
    create_project,
    get_active_session,
    get_completed_sessions,
    get_projects,
    get_codewars_profile,
    get_last_codewars_username,
    get_github_repository,
    get_session_summary,
    get_project_session_summary,
    save_github_repository,
    save_codewars_profile,
    update_project_next_step,
    initialize_database,
    start_session,
    stop_session,
)

from codewars_api import fetch_codewars_profile
from github_api import fetch_github_repository

st.set_page_config(page_title="Arc", page_icon="⚡", layout="wide")

styles_path = Path(__file__).resolve().parent / "styles.css"
st.html(styles_path)

st.html("""
    <div class="arc-header">
        <h1>ARC<span class="arc-header-dot" aria-hidden="true"></span></h1>
    </div>
""")

try:
    initialize_database()
    active_session = get_active_session()
except sqlite3.Error:
    st.error("Arc could not open the session database.")
    st.stop()

completion_message = st.session_state.pop("completion_message", None)
if completion_message:
    st.success(completion_message)

@st.fragment(run_every=1)
def render_elapsed_timer(started_at_iso):
    started_at = datetime.fromisoformat(started_at_iso)

    elapsed_seconds = max(
        0,
        int((datetime.now(timezone.utc) - started_at).total_seconds()),
    )

    hours, remainder = divmod(elapsed_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    st.metric(
        "Elapsed Time",
        f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    )

resume_column, coding_column, progress_column = st.columns(
    [1, 1.5, 1],
    gap="medium",
)

projects_column, sessions_column = st.columns(2, gap="medium")
github_column, codewars_column = st.columns(2, gap="medium")

try:
    projects_by_id = {project["id"]: project for project in get_projects()}
except sqlite3.Error:
    projects_by_id = {}
    st.error("Could not load projects. Please refresh to try again.")

selected_project_id = None

with coding_column, st.container(border=True, key="coding_timer", height=460):
    st.subheader("Coding Session")

    if active_session is None:
        st.metric("Elapsed Time", "00:00:00")
        st.caption("No coding session active.")

        if projects_by_id:
            project_ids = list(projects_by_id)
            previous_project_id = st.session_state.get("selected_project_id")
            default_index = (
                project_ids.index(previous_project_id)
                if previous_project_id in projects_by_id
                else 0
            )
            selected_project_id = st.selectbox(
                "Project",
                options=project_ids,
                index=default_index,
                format_func=lambda project_id: projects_by_id[project_id]["name"],
                key="session_project",
            )
            st.session_state["selected_project_id"] = selected_project_id
            selected_project = projects_by_id[selected_project_id]

            if selected_project["next_step"]:
                st.info(selected_project["next_step"])
            else:
                st.caption("No next step saved for this project yet.")

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
            st.info("Add a project in Project Bays before starting a session.")

    else:
        selected_project_id = active_session["project_id"]
        render_elapsed_timer(active_session["started_at"])
        project_name = active_session["project_name"] or "Unassigned"
        st.caption(f"Coding session active: {project_name}")

        if active_session["next_step"]:
            st.info(active_session["next_step"])
        else:
            st.caption("No next step saved for this project yet.")

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


selected_project = projects_by_id.get(selected_project_id)

with sessions_column, st.container(
    border=True, key="session_log", height=420
):
    st.subheader("Session Log")
    st.caption("Your 14 most recent completed sessions. Start times are local.")

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
                    "Started": local_start.strftime("%Y-%m-%d %H:%M:%S"),
                    "Duration": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
                })

            st.dataframe(
                session_rows,
                hide_index=True,
                width="stretch",
                height=250,
                column_config={
                    "Started": st.column_config.TextColumn(width=170),
                },
            )

with progress_column, st.container(
    border=True, key="project_bays", height=460
):
    st.subheader("Project Bays")

    if selected_project is None:
        st.info("No project selected. Add a project below to get started.")
    else:
        st.dataframe(
            [{"Project": selected_project["name"]}],
            hide_index=True,
            width="stretch",
        )

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
            st.session_state["completion_message"] = "Project saved."
            st.rerun()

with resume_column, st.container(border=True, key="project_notes", height=460):
    st.subheader("Project Notes")
    st.caption("Leave yourself a next step for each project.")

    if selected_project is None:
        st.info("Add a project in Project Bays to leave a next step.")
    else:
        st.write(selected_project["name"])

        with st.form(key=f"next_step_form_{selected_project_id}"):
            next_step = st.text_area(
                "Notes:",
                value=selected_project["next_step"],
                key=f"next_step_{selected_project_id}",
            )

            save_next_step = st.form_submit_button("Save")

        if save_next_step:
            try:
                update_project_next_step(selected_project_id, next_step)
            except ValueError as error:
                st.warning(str(error))
            except sqlite3.Error:
                st.error("Could not save the next step. Please try again.")
            else:
                st.session_state["completion_message"] = "Next step saved."
                st.rerun()


with codewars_column, st.container(border=True, key="codewars"):
    st.subheader("Codewars")
    st.caption("Sync your public profile to track your kata progress.")

    try:
        default_codewars_username = get_last_codewars_username()
    except sqlite3.Error:
        st.error("Could not load your saved Codewars username.")
        default_codewars_username = ""

    with st.form(key="codewars_sync_form"):
        codewars_username = st.text_input(
            "Codewars username",
            value=default_codewars_username,
            key="codewars_username"
        )
        sync_codewars = st.form_submit_button("Sync Codewars")

    if sync_codewars:
        try:
            with st.spinner("Syncing Codewars profile..."):
                profile = fetch_codewars_profile(codewars_username)

                honor = profile["honor"]
                overall_rank = profile["ranks"]["overall"]["name"]
                completed_kata = profile["codeChallenges"]["totalCompleted"]

                if overall_rank is not None and not isinstance(overall_rank, str):
                    raise ValueError("Codewars returned an unexpected rank.")

                save_codewars_profile(
                    username=codewars_username,
                    honor=honor,
                    overall_rank=overall_rank,
                    completed_kata=completed_kata,
                )
        except (KeyError, TypeError):
            st.warning("Codewars returned incomplete or unexpected profile data.")
        except ValueError as error:
            st.warning(str(error))
        except sqlite3.Error:
            st.error("Could not save your Codewars profile. Please try again.")
        else:
            st.success("Codewars profile synced.")

    if codewars_username.strip():
        try:
            saved_profile = get_codewars_profile(codewars_username)
        except sqlite3.Error:
            st.error("Could Sync Codewars to save your profile.")
        else: 
            if saved_profile is None:
                st.info("Click Sync Codewars to save your profile.")
            else:
                honor_column, rank_column, kata_column = st.columns(3)

                honor_column.metric("Honor", saved_profile["honor"])
                rank_column.metric(
                    "Overall rank",
                    saved_profile["overall_rank"] or "Unranked",
                )
                kata_column.metric(
                    "Completed kata",
                    saved_profile["completed_kata"],
                )

                last_synced = datetime.fromisoformat(
                    saved_profile["last_synced_at"]
                ).astimezone()
                st.caption(
                    f"Last successful sync: "
                    f"{last_synced:%Y-%m-%d %H:%M:%S %Z}"
                )

with github_column, st.container(border=True, key="github"):
    st.subheader("GitHub")
    st.caption("Connect a public repository to an Arc project.")

    if selected_project is None:
        st.info("Add a project in Project Bays before syncing GitHub.")
    else:
        st.write(selected_project["name"])

        try:
            connected_repository = get_github_repository(
                selected_project_id
            )
        except sqlite3.Error:
            st.error("Could not load the saved repository.")
            connected_repository = None

        default_owner = ""
        default_repository_name = ""

        if connected_repository is not None:
            default_owner, default_repository_name = (
                connected_repository["full_name"].split("/", 1)
            )

        with st.form(key=f"github_sync_form_{selected_project_id}"):
            github_owner = st.text_input(
                "GitHub owner",
                value=default_owner,
                help="The username or organization that owns the repository.",
                key=f"github_owner_{selected_project_id}",
            )
            github_repository_name = st.text_input(
                "Repository name",
                value=default_repository_name,
                help="Enter the repository name, rather than its full URL.",
                key=f"github_repository_name_{selected_project_id}",
            )
            sync_github = st.form_submit_button("Sync GitHub")

        if sync_github:
            try:
                with st.spinner("Syncing GitHub repository..."):
                    repository = fetch_github_repository(github_owner, github_repository_name,)
                    save_github_repository(selected_project_id, repository,)
            except ValueError as error:
                st.warning(str(error))
            except sqlite3.Error:
                st.error("Could not save the repository. Please try again.")
            else:
                st.success("GitHub repository synced.")

        try:
            saved_repository = get_github_repository(selected_project_id)
        except sqlite3.Error:
            st.error("Could not load the saved repository.")
        else:
            if saved_repository is None:
                st.info("Sync a public repository to save its information.")
            else:
                st.write(saved_repository["full_name"])
                st.link_button("Open Repository", saved_repository["html_url"],)
                st.write(saved_repository["description"] or "No description provided")
                st.caption(
                    f"Main language: "
                    f"{saved_repository['language'] or 'Not specified'}"
                )

                if saved_repository["pushed_at"]:
                    last_pushed = datetime.fromisoformat(
                        saved_repository["pushed_at"].replace("Z", "+00:00")
                    ).astimezone()
                    st.caption(
                        f"Last repository push: "
                        f"{last_pushed:%Y-%m-%d %H:%M:%S %Z}"
                    )
                else:
                    st.caption("Last repository push: Not available")

                github_last_synced = datetime.fromisoformat(
                    saved_repository["last_synced_at"]
                ).astimezone()
                st.caption(
                    f"Last successful sync: "
                    f"{github_last_synced:%Y-%m-%d %H:%M:%S %Z}"
                )


with projects_column, st.container(border=True, key="weekly_debrief", height=420):
    st.subheader("Weekly Progress")

    today = datetime.now().astimezone().date()
    monday = today - timedelta(days=today.weekday())
    next_monday = monday + timedelta(days=7)
    sunday = next_monday - timedelta(days=1)

    # Convert each local midnight separately to respect timezone changes.
    week_start = datetime.combine(
        monday, datetime.min.time()
    ).astimezone()
    week_end = datetime.combine(
        next_monday, datetime.min.time()
    ).astimezone()

    st.caption(
        f"{monday:%b %d, %Y} - {sunday:%b %d, %Y} "
        "(local time)"
    )

    try:
        summary = get_session_summary(week_start, week_end)
    except sqlite3.Error:
        st.error("Could not load the weekly summary. Please try again.")
    else:
        hours, remainder = divmod(summary["total_seconds"], 3600)
        minutes, seconds = divmod(remainder, 60)

        session_count_column, coding_time_column = st.columns(2)

        session_count_column.metric(
            "Completed sessions",
            summary["session_count"],
        )
        coding_time_column.metric(
            "Coding time",
            f"{hours:02d}:{minutes:02d}:{seconds:02d}",
        )

        st.caption(
            "Coding time is shown as HH:MM:SS. "
            "Completed sessions count toward the week they started."
        )

        if summary["session_count"] == 0:
            st.info(
                "No completed sessions this week. "
                "Start and finish a coding session to see your progress."
            )

        else:
            try:
                project_summary = get_project_session_summary(
                    week_start, week_end
                )
            except sqlite3.Error:
                st.error("Could not load the project breakdown.")
            else:
                project_rows = []

                for project in project_summary:
                    hours, remainder = divmod(
                        project["total_seconds"], 3600
                    )
                    minutes, seconds = divmod(remainder, 60)

                    project_rows.append({
                        "Project": project["project_name"],
                        "Completed sessions": project["session_count"],
                        "Coding time (HH:MM:SS)": (
                            f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        ),
                    })

                st.dataframe(
                    project_rows,
                    hide_index=True,
                    width="stretch",
                )
