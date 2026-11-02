# Implementation notes and next steps

## College Admin provisioning
The Super Admin can create a college and then create a College Admin account from the college list. This starter version accepts a temporary password to make local testing straightforward. For production, replace that form with a single-use, expiring invitation token emailed to the administrator. Do not distribute permanent credentials over chat or email.

## Academic record entry
The schema includes `Semester`, `Subject`, `Mark`, and `SemesterResult`. Add staff-only forms/API endpoints for entering marks, validating marks against each subject's maximum values, computing grade points according to each college's approved grading policy, and calculating SGPA/CGPA. The starter scaffold intentionally does not assume that one grading scale applies to every college.

## Attendance
Create one `AttendanceSession` per conducted class, then one `AttendanceRecord` per student/session. Attendance percent = present sessions / applicable conducted sessions * 100. Define how excused classes and practical sessions count before generating official reports.

## Multi-tenant authorization checklist
- Determine tenant from the authenticated user's server-side session, not a form field or query parameter.
- Apply `college_id` filters to every query involving tenant-owned data.
- Validate parent-child ownership (e.g. branch belongs to the same college as department; section belongs to the same college as branch).
- Add automated tests attempting to read and mutate College B records while signed in as College A admin/student.
- Audit privileged actions without logging secrets.
- Consider MySQL constraints and, where appropriate, composite foreign keys to strengthen tenant consistency.

## Analytics definitions
- Placement denominator: currently active student records in the college. Before official reporting, refine this to the eligible graduation cohort using an explicit eligibility rule.
- Placed student: a distinct student with an accepted or pending offer in this starter implementation. For official placement rate, usually count accepted offers (or the institution's documented definition), and report pending separately.
- Package unit: annual LPA (lakhs per annum), stored as a numeric value.
- The package summary is offer-level. For student-level package summaries, select one consistent offer per student (for example, highest accepted offer).
- The initial section summary is illustrative scaffolding and should be replaced with validated distinct-student aggregation joined through sections, branches, and departments.

## Production deployment
- Set `SESSION_COOKIE_SECURE=true` behind HTTPS.
- Use a strong randomly generated `SECRET_KEY` from a secret manager.
- Use Flask-Migrate migrations; do not rely on `db.create_all()` for production schema changes.
- Add rate limiting for login, password reset, and file upload endpoints.
- Add invitation and password-reset emails with one-time expiring tokens.
- Scan uploaded files for malware; validate file signatures; consider object storage with private access policies.
- Configure backups, restore tests, monitoring, audit retention, and data deletion/retention policies.
- Run tests and a security review before importing real student records.
