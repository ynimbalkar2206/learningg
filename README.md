# Raisoni Learn — Full College E-Learning MVP

Responsive college LMS built with Flask, SQLite, Jinja templates, HTML/CSS and Lucide icons. The public starting page is `templates/index.html` and is served at `/`.

## Starting page
Visit `/` to open the public landing page (`templates/index.html`). Students can choose Create Account or Sign In. Once signed in, they are redirected to the dashboard.

## Features implemented
- Registration and sign-in with Werkzeug password hashing
- Student, teacher and administrator roles
- Responsive desktop/mobile interface
- Course catalogue, student enrollment, course detail pages
- Assignment creation and student submissions with optional file uploads
- Exam scheduling and result entry
- Attendance marking and records
- Notes/resources uploads or external URLs
- College announcements
- Admin user-role management and course creation
- Seeded demo data on first run

## Run locally (Windows / macOS / Linux)
1. Install Python 3.10 or newer.
2. Extract this ZIP.
3. Open a terminal in the extracted folder:
   ```bash
   python -m venv .venv
   ```
4. Activate it:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`
5. Install dependencies and run:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
6. Open `http://127.0.0.1:5000`.

## Demo logins
- Admin: `admin@raisonilearn.local` / `ChangeMe123!`
- Teacher: `teacher@raisonilearn.local` / `Teacher123!`
- Student: `student@raisonilearn.local` / `Student123!`

Change these passwords before deployment. The app seeds demo accounts and demo course data into `college.db` on first run.

## Android phone
The simplest path is to upload the extracted project to a Python hosting service or use a cloud coding workspace that supports Flask. Running `frontend/index.html` alone is not the full application: this version uses Flask templates and needs the Python server.

## Deploy
For a production WSGI server, install `gunicorn` (included in typical hosting build settings) and start with `gunicorn app:app`. Set a strong random `SECRET_KEY` environment variable. Configure persistent storage for SQLite and uploaded files, or migrate to PostgreSQL plus object storage. Some hosts have ephemeral filesystems, so local SQLite and uploads may otherwise disappear after redeploy.

## Production security checklist — do not skip
This is a functional MVP, not a finished institutional deployment. Before real students use it:
- Set `SECRET_KEY` to a long random secret and change all demo passwords.
- Add CSRF protection to all POST forms.
- Add rate limiting and account recovery.
- Enforce course-level access on uploaded files and secure media streaming.
- Review all authorization policies, especially teacher course assignment and admin role management.
- Add audit logs, database backups, HTTPS, monitoring, retention policies and privacy notices.
- Use PostgreSQL and durable file/object storage for multi-user production.
- Add a real exam engine with question authoring, timing, autosave and attempt rules if required.
- Configure institutional SSO/email and confirm compliance with college policies.
