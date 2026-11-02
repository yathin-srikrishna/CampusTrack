# Student Academic & Placement Management System

Flask + MySQL demo project for multi-college student academic and placement management. Includes fictional demo records for 3 colleges and 30 students (roll numbers **100–129**), with individual temporary student passwords and one college-admin login per demo college, semesters 1–8, subjects, marks, SGPA/CGPA, attendance sessions and records, certifications, skills, projects, and sample placement data.

> **Demo-only warning:** All students, colleges, emails, phones, certificates and placement records are fictional. The `.example.test` email domain cannot receive mail. Do not use the bundled temporary passwords or seed data in production. Each demo account must change its password on first login. Do not publish either file in `setup/` containing demo credentials to a public repository.

## Requirements
- Python 3.11+
- MySQL 8+
- MySQL Workbench (optional, for running the SQL scripts)

## 1. Create the MySQL database
1. Open MySQL Workbench and connect to your local MySQL server.
2. Open and run `sql/01_create_database.sql`.
3. If you changed the database user's password in that SQL file, use the same password in `.env`.

## 2. Install the app (Windows)
You can double-click `setup_windows.bat` to create the Python environment and install dependencies, or run the commands below from PowerShell in the `placement_project` folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and replace `SECRET_KEY` with a long random secret and update `DATABASE_URL` with the actual MySQL username/password. URL-encode special characters in the password (for example `@` as `%40`, `#` as `%23`, and `%` as `%25`).

## 3. Create tables and seed demo records
```powershell
.\.venv\Scripts\python.exe -m flask --app run.py init-db
.\.venv\Scripts\python.exe seed_demo.py
```

The seed script loads `.env` even when run directly and connects through the same `DATABASE_URL` used by the website. It hashes each student and college-admin password using the app's password-hashing method and sets `must_change_password=true`. It copies credentials to `instance/demo_credentials.csv` and `instance/demo_admin_credentials.csv`, which are intended to remain private. The script intentionally refuses to run if one or more demo college codes already exist, to avoid duplicate or partial records. Back up the database before any reset.

## 4. Start the website
```powershell
.\.venv\Scripts\python.exe -m flask --app run.py run --debug
```
Open `http://127.0.0.1:5000`. Student login URL: `http://127.0.0.1:5000/auth/login`. Students can sign in with either their numeric roll number (100–129) or their registered demo email address; use the matching temporary password from `instance/demo_credentials.csv` after seeding. College admins use the username in `instance/demo_admin_credentials.csv`. Change each password after first login. The included emails use the reserved `.example.test` domain and cannot receive real email.

## 5. SQL files
- `sql/01_create_database.sql` — creates the database and database user.
- `sql/02_reporting_queries.sql` — useful queries for student lists, semester results, marks, attendance, certifications and placement applications.
- `sql/03_verify_demo_data.sql` — verifies seed counts and roll range.
- `sql/04_student_lookup.sql` — lookup query for one student by roll number.
- `initialize_demo_windows.bat` — creates tables and inserts the demo data after MySQL and `.env` are configured; run only once on a fresh demo database.
- `setup_windows.bat` — creates the virtual environment, installs dependencies, and prepares `.env`.
- `run_windows.bat` — starts the local Flask website after MySQL setup and seeding.

Run the verification SQL in MySQL Workbench after seeding. Expected key totals: 3 demo colleges, 30 demo students, 240 semester result rows (30 students × 8 semesters), and 1,200 marks rows (30 × 8 × 5 subjects). Attendance and certification totals vary only if you intentionally modify the seed script.

## Common errors and fixes
- **`Access denied for user`**: verify MySQL is running, the user/password match `sql/01_create_database.sql`, and `DATABASE_URL` is correct.
- **`Can't connect to MySQL server`**: start the MySQL service and confirm host/port (default `localhost:3306`).
- **`No module named flask_login`**: install packages using `.venv\Scripts\python.exe -m pip install -r requirements.txt` and choose `.venv\Scripts\python.exe` in VS Code → Python: Select Interpreter.
- **`Access denied` / database connection error**: check MySQL is running and that `.env` uses the exact same database username/password configured in `sql/01_create_database.sql`.
- **Email login fails**: use the email exactly as listed for that student in the credentials CSV and the corresponding temporary password; student roll-number login is also supported.
- **`Unknown database placement_system`**: run `sql/01_create_database.sql` first.
- **`Demo colleges already exist`**: the seed has already run or partially ran. Do not blindly delete records. Back up the database, inspect `sql/03_verify_demo_data.sql`, and only reset a disposable demo database if you are sure it contains no real data.
- **Special characters in DB password**: URL-encode reserved characters in `DATABASE_URL`.

## Security / production notes
This is a development/demo foundation, not a production-certified system. Review authorization checks, password reset/invitation workflow, migrations, backups, HTTPS, secure cookies, rate limiting, logging and institutional SGPA/CGPA rules before using real student data. Do not commit `.env`, `instance/demo_credentials.csv`, or real uploaded files.


## Automatic student registration (college admin)

College Admin or Faculty users can open **Admin → Students** and submit a student's full name, roll number, email, phone, section, admission year, graduation year, and current semester. The application creates the `users` login row and `students` profile row together in one MySQL transaction. If either insert fails, the transaction is rolled back, so a half-created student account is not left behind.

The roll number becomes the student's login username. A random 20-character temporary password is generated automatically; only its password hash is stored in MySQL. The temporary password is displayed once on the creation confirmation screen. Share it privately. Students must change it at first login. Students can subsequently sign in with their roll number or registered email. Duplicate roll numbers/usernames and duplicate email addresses are rejected.

**Note:** Adding a student creates their identity, login account, and profile record. Semester marks, SGPA/CGPA, attendance, certifications, and placement history should be entered through their respective academic/attendance/placement workflows; the application does not invent real academic results for newly registered students.


## New in this build
- Registering a college creates a starter CSE/AIML department, sections A/B and eight semester records in the same database transaction. A Super Admin still creates the college admin account separately.
- Student registration creates the login user and student profile in one transaction. Roll number is the username; a random temporary password is generated and must be changed on first login.
- Student resume/CV uploads are private and stored outside static web assets. Applying to a job automatically attaches the student's latest current resume/CV when one exists.
- Recruitment page lists applications, linked student/job/resume details, and supports status changes including rejected, shortlisted, selected and offer accepted.
- Analytics includes package distribution and job-application status charts. All queries are scoped to the signed-in college.
- Demo records are fictional. Do not treat sample grades, applications, resumes, companies or package data as real student outcomes.


## New college registration and automatic database records

The public landing page now has an **Add College** button beside Login. College registration creates the college, a starter CSE department, AIML branch, sections A/B, semester rows 1–8 and the first College Admin account in a single SQLAlchemy transaction. If validation or a uniqueness constraint fails, the transaction is rolled back.

After signing in, a College Admin can add student records from **Admin → Students**. The application creates the student profile and matching login account in the same database transaction. The roll number is the student's login username, a random temporary password is generated, and only its password hash is stored. The password is displayed once to the admin after creation. Students must change temporary passwords at first login.

Recruitment includes company/job creation, student job applications with resume attachment references, and application status updates including accepted and rejected. College analytics shows placement/package graphs and application-status graphs and counts. The demo seed creates fictional resumes and sample applications for the three demo colleges; newly registered colleges do not receive fabricated student records.

### Placement reports and SQL checks

Use `sql/05_placement_resume_overview.sql` to inspect job openings, student application outcomes (including accepted/rejected), linked resume filenames and semester-wise SGPA/CGPA. The admin Analytics page now includes package, application status, subject average-mark and attendance status graphs. When a placement officer changes an application to `selected` or `offer_accepted`, the application and corresponding placement offer are updated together; moving an offered application to `rejected` marks its offer as declined.

When a student applies to a job, the currently active resume is linked to the application automatically if the student has uploaded one. If no resume is on file, the application is still accepted without an attachment.
#   C a m p u s T r a c k  
 