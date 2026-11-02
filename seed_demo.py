r"""Seed the local MySQL database with fictional, linked demo academic/placement data.

Run after `flask --app run.py init-db`:
    .venv\Scripts\python.exe seed_demo.py

Only use these fictional records for testing. Temporary demo passwords are in
setup/demo_credentials.csv and copied to instance/demo_credentials.csv on seed.
"""
from __future__ import annotations
import csv, random, shutil
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from flask import current_app
from app import create_app
from app.extensions import db
from app.models import (College, User, Role, Department, Branch, Section, Student,
    Semester, Subject, Mark, SemesterResult, AttendanceSession, AttendanceRecord,
    Skill, StudentSkill, Certification, StudentProject, StudentActivity,
    Company, JobOpening, Application, InterviewRound, InterviewResult, PlacementOffer, StudentDocument)

ROOT = Path(__file__).resolve().parent
CREDENTIALS = ROOT / "setup" / "demo_credentials.csv"
ADMIN_CREDENTIALS = ROOT / "setup" / "demo_admin_credentials.csv"
DEMO_CODES = {"DEMO01", "DEMO02", "DEMO03"}
RNG = random.Random(20261028)

SUBJECT_NAMES = [
    ("MAT", "Engineering Mathematics", 4), ("PRG", "Programming Fundamentals", 4),
    ("DS", "Data Structures", 4), ("DBMS", "Database Management Systems", 4),
    ("OS", "Operating Systems", 3), ("CN", "Computer Networks", 3),
    ("AI", "Artificial Intelligence", 4), ("ML", "Machine Learning", 4),
    ("WEB", "Web Technologies", 3), ("SE", "Software Engineering", 3),
    ("STAT", "Probability and Statistics", 4), ("CLOUD", "Cloud Computing", 3),
]
SKILLS = [("Python", "Programming"), ("Java", "Programming"), ("SQL", "Database"),
          ("HTML/CSS", "Web"), ("JavaScript", "Web"), ("Machine Learning", "AI/ML"),
          ("Communication", "Professional"), ("Problem Solving", "Professional")]


def grade_for(total):
    if total >= 90: return "A+", 10
    if total >= 80: return "A", 9
    if total >= 70: return "B", 8
    if total >= 60: return "C", 7
    if total >= 50: return "D", 6
    if total >= 40: return "E", 5
    return "F", 0


def make_demo_resume_pdf(student_name, roll_no, college_name):
    """Create a tiny valid, fictional one-page PDF without external PDF dependencies."""
    def esc(value):
        return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lines = [f"DEMO RESUME - NOT FOR OFFICIAL USE", f"Name: {student_name}",
             f"Roll number: {roll_no}", f"College: {college_name}",
             "Skills: Python, SQL, communication", "Project: Student Academic Dashboard",
             "This is fictional sample data created for software testing."]
    stream = "BT /F1 12 Tf 50 780 Td 16 TL " + " ".join(
        f"({esc(line)}) Tj T*" for line in lines) + " ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream".encode("latin-1"),
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, 1):
        offsets.append(len(pdf)); pdf.extend(f"{idx} 0 obj\n".encode()); pdf.extend(obj); pdf.extend(b"\nendobj\n")
    xref = len(pdf); pdf.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]: pdf.extend(f"{off:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)


def seed():
    if not CREDENTIALS.exists() or not ADMIN_CREDENTIALS.exists():
        raise RuntimeError("Missing setup/demo_credentials.csv or setup/demo_admin_credentials.csv; restore both demo credential files.")
    with CREDENTIALS.open(newline="", encoding="utf-8") as handle:
        students_input = list(csv.DictReader(handle))
    with ADMIN_CREDENTIALS.open(newline="", encoding="utf-8") as handle:
        admins_input = list(csv.DictReader(handle))
    if len(admins_input) != 3 or {r["college_code"] for r in admins_input} != DEMO_CODES:
        raise RuntimeError("Demo admin credentials must contain exactly DEMO01, DEMO02 and DEMO03.")
    if len(students_input) != 30 or {r["roll_no"] for r in students_input} != {str(n) for n in range(100, 130)}:
        raise RuntimeError("Demo credentials must contain exactly rolls 100 through 129.")
    existing = {c.code for c in College.query.filter(College.code.in_(DEMO_CODES)).all()}
    if existing:
        raise RuntimeError("Demo colleges already exist (or seed is partial): " + ", ".join(sorted(existing)) + ". Back up data and reset only the demo database before reseeding.")

    # Copy credential sheet to instance folder, outside public/static paths.
    private_credential_path = Path(current_app.instance_path) / "demo_credentials.csv"
    private_admin_path = Path(current_app.instance_path) / "demo_admin_credentials.csv"
    private_credential_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CREDENTIALS, private_credential_path)
    shutil.copy2(ADMIN_CREDENTIALS, private_admin_path)

    college_rows = [
        ("DEMO01", "Demo Institute of Technology", "office@demo01.example.test"),
        ("DEMO02", "Demo Valley Engineering College", "office@demo02.example.test"),
        ("DEMO03", "Demo Coastal University", "office@demo03.example.test"),
    ]
    colleges = {}
    for code, name, email in college_rows:
        c = College(code=code, name=name, official_email=email, status="active")
        db.session.add(c); db.session.flush(); colleges[code] = c

    # One isolated College Admin per demo college, each with an individual temporary password.
    for admin_row in admins_input:
        college = colleges[admin_row["college_code"]]
        admin_user = User(college_id=college.id, username=admin_row["username"],
            role=Role.COLLEGE_ADMIN.value, is_active=True, must_change_password=True)
        admin_user.set_password(admin_row["temporary_password"])
        db.session.add(admin_user)

    skills = {}
    for name, category in SKILLS:
        skill = Skill(name=name, category=category); db.session.add(skill); db.session.flush(); skills[name] = skill

    for college_code, college in colleges.items():
        dept = Department(college_id=college.id, name="Computer Science and Engineering", code="CSE")
        db.session.add(dept); db.session.flush()
        branch = Branch(college_id=college.id, department_id=dept.id, name="Artificial Intelligence and Machine Learning", code="AIML")
        db.session.add(branch); db.session.flush()
        section_a = Section(college_id=college.id, branch_id=branch.id, name="A", academic_year="2026-2027")
        section_b = Section(college_id=college.id, branch_id=branch.id, name="B", academic_year="2026-2027")
        db.session.add_all([section_a, section_b]); db.session.flush()
        semester_map = {}
        for sem_num in range(1, 9):
            sem = Semester(college_id=college.id, number=sem_num, academic_year=f"{2023 + (sem_num-1)//2}-{str(2024 + (sem_num-1)//2)[-2:]}")
            db.session.add(sem); db.session.flush(); semester_map[sem_num] = sem
        subject_map = {}
        for sem_num, sem in semester_map.items():
            # Five subjects per semester, with semester-specific subject codes.
            offset = ((sem_num - 1) * 5) % len(SUBJECT_NAMES)
            for j in range(5):
                code, subject_name, credits = SUBJECT_NAMES[(offset + j) % len(SUBJECT_NAMES)]
                subj = Subject(college_id=college.id, branch_id=branch.id, semester_id=sem.id,
                    code=f"S{sem_num}-{code}", name=subject_name, credits=Decimal(str(credits)),
                    max_internal=Decimal("30"), max_external=Decimal("70"))
                db.session.add(subj); db.session.flush(); subject_map[(sem_num, subj.id)] = subj

        # Attendance sessions are shared by every student enrolled in the college,
        # rather than creating a separate class session for each individual student.
        sessions_by_subject = {}
        for subj in subject_map.values():
            sessions = []
            sem_num = next(sn for (sn, subject_id), _subject in subject_map.items() if subject_id == subj.id)
            for sess_index in range(3):
                sess_date = date(2023, 8, 1) + timedelta(days=(sem_num-1)*100 + sess_index*12 + (subj.id % 7))
                session = AttendanceSession(college_id=college.id, subject_id=subj.id,
                    session_date=sess_date, topic=f"Demo class {sess_index+1}: {subj.name}")
                db.session.add(session); db.session.flush(); sessions.append(session)
            sessions_by_subject[subj.id] = sessions

        for row in students_input:
            if row["college_code"] != college_code: continue
            username = row["username"]
            user = User(college_id=college.id, username=username, role=Role.STUDENT.value,
                        is_active=True, must_change_password=True)
            user.set_password(row["temporary_password"])
            db.session.add(user); db.session.flush()
            roll = int(row["roll_no"])
            section = section_a if roll % 2 == 0 else section_b
            student = Student(college_id=college.id, user_id=user.id, section_id=section.id,
                roll_no=row["roll_no"], full_name=row["full_name"], email=row["email"],
                phone=f"90000{roll:05d}"[-10:], admission_year=2023, graduation_year=2027,
                current_semester=8, status="active")
            db.session.add(student); db.session.flush()
            # A private, fictional resume PDF is included for demo students only.
            resume_rel = f"{college.id}/{student.id}/demo-resume-{roll}.pdf"
            resume_path = Path(current_app.config["UPLOAD_ROOT"]) / "resumes" / resume_rel
            resume_path.parent.mkdir(parents=True, exist_ok=True)
            resume_path.write_bytes(make_demo_resume_pdf(student.full_name, student.roll_no, college.name))
            resume_doc = StudentDocument(college_id=college.id, student_id=student.id,
                document_type="resume", original_filename=f"{student.roll_no}_Demo_Resume.pdf",
                stored_filename=resume_rel, mime_type="application/pdf", uploaded_by=user.id,
                is_current=True)
            db.session.add(resume_doc); db.session.flush()
            for skill_name, skill in skills.items():
                if RNG.random() < 0.65:
                    db.session.add(StudentSkill(college_id=college.id, student_id=student.id,
                        skill_id=skill.id, proficiency=RNG.choice(["Beginner", "Intermediate", "Advanced"]),
                        verification_status="verified"))
            for k in range(RNG.randint(1, 3)):
                db.session.add(Certification(college_id=college.id, student_id=student.id,
                    course_name=RNG.choice(["Python Programming", "SQL Fundamentals", "AI Foundations", "Web Development", "Cloud Essentials"]),
                    provider=RNG.choice(["Demo Learning Lab", "Open Skills Academy", "Campus Training Cell"]),
                    completion_date=date(2024, 1, 1) + timedelta(days=RNG.randint(0, 950)),
                    verification_status=RNG.choice(["verified", "pending"])))
            db.session.add(StudentProject(college_id=college.id, student_id=student.id,
                title=RNG.choice(["Student Performance Dashboard", "Smart Attendance Tracker", "Campus Placement Portal", "AI Study Assistant"]),
                description="Fictional demonstration project record for testing the student profile.",
                technologies=RNG.choice(["Python, Flask, MySQL", "HTML, CSS, JavaScript", "Python, Pandas, Matplotlib"]),
                verification_status="verified"))
            db.session.add(StudentActivity(college_id=college.id, student_id=student.id,
                title="Technical Workshop", category="workshop", activity_date=date(2025, 2, 1) + timedelta(days=RNG.randint(0, 300)),
                role_or_achievement="Participant", verification_status="verified"))

            # Semester-wise marks and credit-weighted SGPA / cumulative CGPA.
            cumulative_weighted = 0.0; cumulative_credits = 0.0
            for sem_num, sem in semester_map.items():
                sem_weighted = 0.0; sem_credits = 0.0; failed = False
                sem_subjects = [s for (sn, _), s in subject_map.items() if sn == sem_num]
                for subj in sem_subjects:
                    internal = RNG.randint(12, 30)
                    external = RNG.randint(25, 70)
                    total = internal + external
                    grade, points = grade_for(total)
                    result = "pass" if total >= 40 else "fail"
                    if result == "fail": failed = True
                    credits = float(subj.credits)
                    sem_weighted += points * credits; sem_credits += credits
                    db.session.add(Mark(college_id=college.id, student_id=student.id, subject_id=subj.id,
                        internal_marks=Decimal(internal), external_marks=Decimal(external), total_marks=Decimal(total),
                        grade=grade, grade_points=Decimal(points), result=result, attempt_number=1))
                    # Record each student's attendance in the shared class sessions.
                    for session in sessions_by_subject[subj.id]:
                        status = RNG.choices(["present", "absent", "excused"], weights=[84, 12, 4], k=1)[0]
                        db.session.add(AttendanceRecord(college_id=college.id, session_id=session.id,
                            student_id=student.id, status=status))
                sgpa = round(sem_weighted / sem_credits, 2) if sem_credits else 0.0
                cumulative_weighted += sem_weighted; cumulative_credits += sem_credits
                cgpa = round(cumulative_weighted / cumulative_credits, 2) if cumulative_credits else 0.0
                db.session.add(SemesterResult(college_id=college.id, student_id=student.id, semester_id=sem.id,
                    credits_counted=Decimal(str(sem_credits)), sgpa=Decimal(str(sgpa)), cgpa=Decimal(str(cgpa)),
                    result_status="fail" if failed else "pass"))

    # Fictional companies/jobs and a few placement records per college.
    company_names = ["Demo Analytics Labs", "Sample Cloud Systems", "Practice Software Works"]
    for college in colleges.values():
        company_map = {}
        for idx, company_name in enumerate(company_names):
            company = Company(college_id=college.id, name=company_name,
                industry=["Analytics", "Cloud Computing", "Software Development"][idx],
                website="https://example.test", contact_email=f"careers{idx+1}@example.test")
            db.session.add(company); db.session.flush(); company_map[company_name] = company
            job = JobOpening(college_id=college.id, company_id=company.id,
                title=["Junior Data Analyst", "Graduate Cloud Associate", "Software Engineer Trainee"][idx],
                description="Fictional placement listing for local demonstration only.",
                required_skills="Python, SQL, communication", minimum_cgpa=Decimal("6.00"),
                max_active_backlogs=0, package_lpa=Decimal(str([4.5, 5.2, 6.0][idx])),
                graduation_year=2027, deadline=date(2027, 3, 31), status="open")
            db.session.add(job); db.session.flush()
            round1 = InterviewRound(college_id=college.id, job_id=job.id, name="Technical Interview", round_number=1,
                scheduled_at=datetime(2026, 11, 15, 10, 0))
            db.session.add(round1); db.session.flush()
            students = Student.query.filter_by(college_id=college.id).order_by(Student.roll_no).all()
            demo_statuses = ["applied", "shortlisted", "interview", "selected",
                             "offer_accepted", "rejected", "waitlisted", "withdrawn"]
            for student_index, student in enumerate(students[:8]):
                status = demo_statuses[(student_index + idx) % len(demo_statuses)]
                resume = StudentDocument.query.filter_by(college_id=college.id, student_id=student.id,
                    document_type="resume", is_current=True).first()
                app = Application(college_id=college.id, job_id=job.id, student_id=student.id,
                    resume_document_id=resume.id if resume else None, status=status)
                db.session.add(app); db.session.flush()
                if status in {"shortlisted", "interview", "selected", "offer_accepted"}:
                    db.session.add(InterviewResult(college_id=college.id, application_id=app.id, round_id=round1.id,
                        attendance_status="attended" if status in {"selected", "offer_accepted"} else "scheduled",
                        result="passed" if status in {"selected", "offer_accepted"} else "pending",
                        notes="Fictional demonstration interview record"))
                if status in {"selected", "offer_accepted"}:
                    db.session.add(PlacementOffer(college_id=college.id, application_id=app.id,
                        student_id=student.id, company_id=company.id, role_title=job.title,
                        annual_package_lpa=job.package_lpa, offer_date=date(2026, 10, 15),
                        acceptance_status="accepted" if status == "offer_accepted" else "pending"))
    db.session.commit()
    print("Demo data seeded successfully.")
    print("Colleges: 3 | Students: 30 | Roll numbers: 100-129")
    print("Demo resumes: 30 private PDF files | Job applications: status examples include applied, shortlisted, interview, selected, offer accepted, rejected, waitlisted and withdrawn.")
    print(f"Private student credentials copied to: {private_credential_path}")
    print(f"Private college-admin credentials copied to: {private_admin_path}")
    print("All demo accounts require a password change on first login.")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        try:
            seed()
        except Exception:
            db.session.rollback()
            raise
