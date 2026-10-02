# Arc - Project Instructions

## Project Purpose
Arc is a personal command center style dashboard that helps me organize coding projects, track progress, and record learning milestones.
It is initially a local application for one user.

## Technology
- Python
- Streamlit
- SQLite
- Custom CSS in a separate stylesheet
- Codewars and GitHub APIs in later stages

## How to work with me
I am learning Python. Help me build the app while understanding the important decisions.

- Work on one manageable feature at a time
- Proceed with reasonable implementation choices.
- Do not make any changes to code without my permission.
- Before making changes, briefly explain what you will add, why it is useful, and which files will change.
- When dsicussing specific lines of code, give me the line numbers to help me locate the referenced code.

## Keep the architecture understandable
- Separate UI code, database operations, and API integrations.
- Follow existing project conventions.
- Prefer straightforward functions and descriptive names.
- Avoid unnecessary dependencies, abstractions, and rewrites.
- Keep changes focused on the requested feature.
- Explain any new dependency before adding it.
- Use comments to explain non-obvious decisions.

## Database and persistence
- Use stable database IDs to connect projects and sessions.
- Use parameterized SQL queries.
- Make database initialization safe to run repeatedly.
- Store timestamps consistently and document the convention.
- Persist active coding sessions in SQLite so refreshes and
  Streamlit reruns do not lose them.
- Calculate elapsed time from timestamps; do not use a
  constantly running loop.
- Preserve existing records when changing the schema.
- Do not delete or reset my database without explicit permission.

## Streamlit behavior
- Handle session state and reruns deliberately.
- Use stable, unique widget keys when needed.
- Validate input before saving.
- Give clear feedback when an action succeeds or fails.
- Include helpful empty states when no records exist.

## Design direction
Use a restrained JARVIS-inspired appearance:
- Dark backgrounds
- Cyan or teal accents
- Clean cards and subtle borders
- Readable typography and clear spacing
Prioritize clarity and ease of use.
Use mission-themed labels only when their meaning is obvious.
Keep custom CSS in a separate file.
Avoid excessive animation and visual clutter.

## API integrations
- Verify official API documentation before implementation.
- Explain what information the API actually provides.
- Use explicit Sync buttons and store results locally.
- Keep API calls out of normal dashboard rerenders.
- Show the last successful sync time.
- Preserve previously synced data when a sync fails.
- Handle timeouts, missing data, and rate limits clearly.
- Never put tokens or secrets in source code or commit them.
- Keep session time, commits, and kata completions labeled
  as separate measures.

  ## Verification and reporting
- Run checks appropriate to the change.
- Never claim a check passed unless you actually ran it.
- Explain any checks you could not run.
- Mention important limitations or unfinished behavior.
- Do not commit or push changes unless I ask.

## Build order
1. Dashboard, Project Bays, and Session Log
2. Resume Mission
3. Codewars integration
4. GitHub integration
5. Weekly Debrief
6. Detailed visual polish and authenticated API practice

Use basic cohesive styling from the beginning.
Follow my current request if I explicitly change this order.