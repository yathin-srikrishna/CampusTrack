USE placement_system;

-- 1) Count students by college
SELECT c.code, c.name, COUNT(s.id) AS student_count
FROM colleges c LEFT JOIN students s ON s.college_id = c.id
GROUP BY c.id, c.code, c.name ORDER BY c.code;

-- 2) Student login usernames and roll numbers (NEVER select password_hash)
SELECT c.code AS college_code, s.roll_no, s.full_name, u.username, u.must_change_password
FROM students s JOIN users u ON u.id = s.user_id JOIN colleges c ON c.id = s.college_id
ORDER BY CAST(s.roll_no AS UNSIGNED);

-- 3) Semester-wise SGPA/CGPA
SELECT c.code AS college_code, s.roll_no, s.full_name, sem.number AS semester, sr.sgpa, sr.cgpa, sr.result_status
FROM semester_results sr JOIN students s ON s.id = sr.student_id
JOIN colleges c ON c.id = sr.college_id JOIN semesters sem ON sem.id = sr.semester_id
ORDER BY c.code, CAST(s.roll_no AS UNSIGNED), sem.number;

-- 4) Marks by student and semester
SELECT c.code AS college_code, s.roll_no, s.full_name, sem.number AS semester,
       sub.code AS subject_code, sub.name AS subject, m.internal_marks, m.external_marks,
       m.total_marks, m.grade, m.grade_points, m.result
FROM marks m JOIN students s ON s.id=m.student_id JOIN colleges c ON c.id=m.college_id
JOIN subjects sub ON sub.id=m.subject_id JOIN semesters sem ON sem.id=sub.semester_id
ORDER BY c.code, CAST(s.roll_no AS UNSIGNED), sem.number, sub.code;

-- 5) Attendance percentage by student
SELECT c.code AS college_code, s.roll_no, s.full_name,
       ROUND(100 * SUM(ar.status='present') / NULLIF(COUNT(ar.id),0), 2) AS attendance_percent,
       COUNT(ar.id) AS recorded_sessions
FROM attendance_records ar JOIN students s ON s.id=ar.student_id
JOIN colleges c ON c.id=s.college_id
GROUP BY c.code, s.id, s.roll_no, s.full_name
ORDER BY c.code, CAST(s.roll_no AS UNSIGNED);

-- 6) Certifications per student
SELECT c.code AS college_code, s.roll_no, s.full_name, cert.course_name, cert.provider,
       cert.completion_date, cert.verification_status
FROM certifications cert JOIN students s ON s.id=cert.student_id JOIN colleges c ON c.id=cert.college_id
ORDER BY c.code, CAST(s.roll_no AS UNSIGNED), cert.completion_date;

-- 7) Placement applications
SELECT c.code AS college_code, s.roll_no, s.full_name, co.name AS company, j.title AS role, a.status
FROM applications a JOIN students s ON s.id=a.student_id JOIN colleges c ON c.id=a.college_id
JOIN job_openings j ON j.id=a.job_id JOIN companies co ON co.id=j.company_id
ORDER BY c.code, CAST(s.roll_no AS UNSIGNED);
