USE placement_system;

-- Change the roll number below to view one student's profile.
SET @roll_no = '100';

SELECT
    c.name AS college,
    s.roll_no,
    s.full_name,
    s.email,
    s.phone,
    d.name AS department,
    b.name AS branch,
    sec.name AS section,
    s.current_semester,
    s.graduation_year,
    s.status AS student_status
FROM students s
JOIN colleges c ON c.id = s.college_id
LEFT JOIN sections sec ON sec.id = s.section_id
LEFT JOIN branches b ON b.id = sec.branch_id
LEFT JOIN departments d ON d.id = b.department_id
WHERE s.roll_no = @roll_no;

-- Semester-wise SGPA and CGPA for the same roll number.
SELECT s.roll_no, s.full_name, sem.number AS semester, sem.academic_year,
       sr.sgpa, sr.cgpa, sr.result_status
FROM semester_results sr
JOIN students s ON s.id = sr.student_id AND s.college_id = sr.college_id
JOIN semesters sem ON sem.id = sr.semester_id AND sem.college_id = sr.college_id
WHERE s.roll_no = @roll_no
ORDER BY sem.number;

-- Subject-wise marks, grades, and pass/fail status.
SELECT s.roll_no, sem.number AS semester, sub.code AS subject_code, sub.name AS subject,
       m.internal_marks, m.external_marks, m.total_marks, m.grade, m.result
FROM marks m
JOIN students s ON s.id = m.student_id AND s.college_id = m.college_id
JOIN subjects sub ON sub.id = m.subject_id AND sub.college_id = m.college_id
JOIN semesters sem ON sem.id = sub.semester_id AND sem.college_id = sub.college_id
WHERE s.roll_no = @roll_no
ORDER BY sem.number, sub.code;

-- Attendance percentage (present / all recorded sessions).
SELECT s.roll_no,
       COUNT(ar.id) AS recorded_sessions,
       SUM(CASE WHEN ar.status = 'present' THEN 1 ELSE 0 END) AS present_sessions,
       ROUND(100.0 * SUM(CASE WHEN ar.status = 'present' THEN 1 ELSE 0 END) / NULLIF(COUNT(ar.id), 0), 1) AS attendance_percentage
FROM students s
LEFT JOIN attendance_records ar ON ar.student_id = s.id AND ar.college_id = s.college_id
WHERE s.roll_no = @roll_no
GROUP BY s.roll_no;

-- Certifications for the same roll number.
SELECT s.roll_no, cert.course_name, cert.provider, cert.completion_date, cert.verification_status
FROM certifications cert
JOIN students s ON s.id = cert.student_id AND s.college_id = cert.college_id
WHERE s.roll_no = @roll_no
ORDER BY cert.completion_date DESC;

-- Passwords are NEVER readable from the database: only password_hash is stored.
-- Use setup/demo_credentials.csv for the fictional temporary demo login passwords.
