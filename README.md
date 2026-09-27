# Uni System

A Flask-based university management system with separate student and staff portals, multi-semester course tracking, weighted grading, and prerequisite enforcement.

## Features

### Student portal
- **Account registration & login** — students sign up with an email/password (password must be 8+ characters with an uppercase letter and a number) and are placed into a program.
- **Course registration** — students can only register for courses that belong to their program, have open capacity, and whose prerequisites they've already passed. Registration is blocked once a course is passed or already taken in the current semester.
- **Retakes** — a failed course can be retaken in a later semester; a passed course cannot be re-registered.
- **Dashboard** — shows upcoming exams/assignments, items awaiting grades, and already-graded items for the active semester.
- **My courses** — lists in-progress and completed courses with pass/fail status.
- **Results** — full grade history grouped by semester.
- **Profile** — basic student info and program name.

### Staff/admin portal
- Separate password-protected staff login, independent of student accounts.
- **Course management** — add courses, assign them to a program, and set an optional enrollment capacity.
- **Program management** — create academic programs.
- **Prerequisite management** — define which courses require which other courses (self-requirement is blocked).
- **Semester management** — create semesters and set the single currently-active semester; most student-facing actions (registration, grading, dashboards) are scoped to whichever semester is active.
- **Exams & assignments** — add exams/assignments to a course for the active semester, each with its own weight; the system prevents weights for a course from exceeding 100%.
- **Grading** — a grading page per course lists the enrolled roster and every exam/assignment, letting staff enter grades per student per item.
- **Courses overview** — see, at a glance, which courses have complete (100%) grading weight for the active semester and which don't.

### Core mechanics
- **Multi-semester model** — enrollment, grades, exams, and assignments are all scoped to a specific semester, so history persists across terms and a course can be retaken cleanly.
- **Weighted grading** — a student's final grade for a course is computed automatically once every exam and assignment for that course/semester has a grade, using each item's weight; a 100-mark cutoff (`PASS_MARK`) determines pass/fail.
- **Cross-semester prerequisites** — prerequisite checks look across a student's entire history, not just the current semester, so a prerequisite passed in an earlier term still counts.
- **Enrollment caps** — courses can have a maximum capacity that blocks registration once full.

## Tech stack
- Python / Flask
- Flask-SQLAlchemy (SQLite by default)
- Server-side sessions for auth (students and staff are separate session-based roles)
- Passwords hashed with Werkzeug's `generate_password_hash` / `check_password_hash`

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Create a `.env` file in the project root with:
   ```
   SECRET_KEY=<a random secret key for Flask sessions>
   STAFF_PASSWORD_HASH=<output of werkzeug.security.generate_password_hash("your-staff-password")>
   ```
3. Run the app:
   ```bash
   python app.py
   ```
   This creates a local `instance/test.db` SQLite database on first run.

The app will be available at `http://127.0.0.1:5000/`. New students can sign up from the landing page; staff log in separately via `/staff-login`.
