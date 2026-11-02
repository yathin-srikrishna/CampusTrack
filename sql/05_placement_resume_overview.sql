USE placement_system;

-- Replace DEMO01 with your college code to inspect only that college.
SET @college_code = 'DEMO01';

-- Job openings and company details.
SELECT c.code AS college_code, co.name AS company, j.title AS job_role,
       j.package_lpa, j.minimum_cgpa, j.status AS job_status
FROM job_openings j
JOIN colleges c ON c.id = j.college_id
JOIN companies co ON co.id = j.company_id
WHERE c.code = @college_code
ORDER BY co.name, j.title;

-- Application status counts: applied, shortlisted, interview, selected,
-- offer_accepted, rejected, withdrawn and waitlisted.
SELECT a.status, COUNT(*) AS application_count
FROM applications a
JOIN colleges c ON c.id = a.college_id
WHERE c.code = @college_code
GROUP BY a.status
ORDER BY a.status;

-- Student-wise applications and linked resume filename.
SELECT s.roll_no, s.full_name, s.email, co.name AS company, j.title AS job_role,
       a.status AS application_status, d.original_filename AS attached_resume,
       a.applied_at
FROM applications a
JOIN colleges c ON c.id = a.college_id
JOIN students s ON s.id = a.student_id
JOIN job_openings j ON j.id = a.job_id
JOIN companies co ON co.id = j.company_id
LEFT JOIN student_documents d ON d.id = a.resume_document_id
WHERE c.code = @college_code
ORDER BY a.applied_at DESC;

-- Resumes and certificates stored privately for each student.
SELECT s.roll_no, s.full_name, d.document_type, d.original_filename,
       d.mime_type, d.is_current, d.created_at
FROM student_documents d
JOIN students s ON s.id = d.student_id
JOIN colleges c ON c.id = d.college_id
WHERE c.code = @college_code
ORDER BY s.roll_no, d.document_type;

-- Semester-wise SGPA and CGPA.
SELECT s.roll_no, s.full_name, sem.number AS semester,
       sem.academic_year, sr.sgpa, sr.cgpa, sr.result_status
FROM semester_results sr
JOIN students s ON s.id = sr.student_id
JOIN semesters sem ON sem.id = sr.semester_id
JOIN colleges c ON c.id = sr.college_id
WHERE c.code = @college_code
ORDER BY s.roll_no, sem.number;
