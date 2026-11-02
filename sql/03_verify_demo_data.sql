USE placement_system;
SELECT COUNT(*) AS demo_colleges FROM colleges WHERE code IN ('DEMO01','DEMO02','DEMO03');
SELECT COUNT(*) AS demo_students FROM students s JOIN colleges c ON c.id=s.college_id WHERE c.code IN ('DEMO01','DEMO02','DEMO03');
SELECT MIN(CAST(s.roll_no AS UNSIGNED)) AS first_roll, MAX(CAST(s.roll_no AS UNSIGNED)) AS last_roll,
       COUNT(DISTINCT s.roll_no) AS distinct_rolls
FROM students s JOIN colleges c ON c.id=s.college_id WHERE c.code IN ('DEMO01','DEMO02','DEMO03');
SELECT COUNT(*) AS semester_results FROM semester_results sr JOIN colleges c ON c.id=sr.college_id WHERE c.code IN ('DEMO01','DEMO02','DEMO03');
SELECT COUNT(*) AS marks_rows FROM marks m JOIN colleges c ON c.id=m.college_id WHERE c.code IN ('DEMO01','DEMO02','DEMO03');
SELECT COUNT(*) AS attendance_rows FROM attendance_records ar JOIN colleges c ON c.id=ar.college_id WHERE c.code IN ('DEMO01','DEMO02','DEMO03');
SELECT COUNT(*) AS certification_rows FROM certifications ce JOIN colleges c ON c.id=ce.college_id WHERE c.code IN ('DEMO01','DEMO02','DEMO03');
