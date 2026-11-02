from datetime import datetime, date
from enum import Enum
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db, login_manager


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    COLLEGE_ADMIN = "college_admin"
    FACULTY = "faculty"
    PLACEMENT_OFFICER = "placement_officer"
    STUDENT = "student"


class PlacementStatus(str, Enum):
    APPLIED = "applied"
    SHORTLISTED = "shortlisted"
    INTERVIEW = "interview"
    SELECTED = "selected"
    OFFER_ACCEPTED = "offer_accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    WAITLISTED = "waitlisted"


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class College(TimestampMixin, db.Model):
    __tablename__ = "colleges"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    official_email = db.Column(db.String(254), nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    departments = db.relationship("Department", backref="college", cascade="all, delete-orphan")
    users = db.relationship("User", backref="college", foreign_keys="User.college_id")


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True, index=True)
    username = db.Column(db.String(254), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default=Role.STUDENT.value, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    must_change_password = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_super_admin(self):
        return self.role == Role.SUPER_ADMIN.value


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


class Department(TimestampMixin, db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(30), nullable=False)
    __table_args__ = (db.UniqueConstraint("college_id", "code", name="uq_department_college_code"),)
    branches = db.relationship("Branch", backref="department", cascade="all, delete-orphan")


class Branch(TimestampMixin, db.Model):
    __tablename__ = "branches"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(30), nullable=False)
    __table_args__ = (db.UniqueConstraint("college_id", "code", name="uq_branch_college_code"),)
    sections = db.relationship("Section", backref="branch", cascade="all, delete-orphan")


class Section(TimestampMixin, db.Model):
    __tablename__ = "sections"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    name = db.Column(db.String(30), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    __table_args__ = (db.UniqueConstraint("college_id", "branch_id", "name", "academic_year", name="uq_section_scope"),)


class Student(TimestampMixin, db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    section_id = db.Column(db.Integer, db.ForeignKey("sections.id"), nullable=True, index=True)
    roll_no = db.Column(db.String(50), nullable=False)
    full_name = db.Column(db.String(160), nullable=False)
    email = db.Column(db.String(254), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    admission_year = db.Column(db.Integer, nullable=True)
    graduation_year = db.Column(db.Integer, nullable=True, index=True)
    current_semester = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default="active", nullable=False)
    __table_args__ = (db.UniqueConstraint("college_id", "roll_no", name="uq_student_college_roll"),)
    account = db.relationship("User", backref=db.backref("student_profile", uselist=False), foreign_keys=[user_id])
    section = db.relationship("Section", foreign_keys=[section_id])
    college = db.relationship("College", foreign_keys=[college_id])


class Semester(TimestampMixin, db.Model):
    __tablename__ = "semesters"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    number = db.Column(db.Integer, nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    __table_args__ = (db.UniqueConstraint("college_id", "number", "academic_year", name="uq_semester_scope"),)


class Subject(TimestampMixin, db.Model):
    __tablename__ = "subjects"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False, index=True)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    credits = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    max_internal = db.Column(db.Numeric(6, 2), nullable=False, default=30)
    max_external = db.Column(db.Numeric(6, 2), nullable=False, default=70)
    __table_args__ = (db.UniqueConstraint("college_id", "branch_id", "semester_id", "code", name="uq_subject_scope"),)


class Mark(TimestampMixin, db.Model):
    __tablename__ = "marks"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False, index=True)
    internal_marks = db.Column(db.Numeric(6, 2), nullable=False, default=0)
    external_marks = db.Column(db.Numeric(6, 2), nullable=False, default=0)
    total_marks = db.Column(db.Numeric(6, 2), nullable=False, default=0)
    grade = db.Column(db.String(5), nullable=True)
    grade_points = db.Column(db.Numeric(4, 2), nullable=True)
    result = db.Column(db.String(20), nullable=False, default="pending")
    attempt_number = db.Column(db.Integer, nullable=False, default=1)
    entered_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    subject = db.relationship("Subject")
    __table_args__ = (db.UniqueConstraint("college_id", "student_id", "subject_id", "attempt_number", name="uq_mark_attempt"),)


class SemesterResult(TimestampMixin, db.Model):
    __tablename__ = "semester_results"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    semester_id = db.Column(db.Integer, db.ForeignKey("semesters.id"), nullable=False, index=True)
    credits_counted = db.Column(db.Numeric(6, 2), nullable=False, default=0)
    sgpa = db.Column(db.Numeric(4, 2), nullable=True)
    cgpa = db.Column(db.Numeric(4, 2), nullable=True)
    result_status = db.Column(db.String(20), default="pending", nullable=False)
    semester = db.relationship("Semester")
    __table_args__ = (db.UniqueConstraint("college_id", "student_id", "semester_id", name="uq_sem_result"),)


class AttendanceSession(TimestampMixin, db.Model):
    __tablename__ = "attendance_sessions"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False, index=True)
    session_date = db.Column(db.Date, nullable=False, default=date.today)
    topic = db.Column(db.String(200), nullable=True)
    subject = db.relationship("Subject")


class AttendanceRecord(TimestampMixin, db.Model):
    __tablename__ = "attendance_records"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    session_id = db.Column(db.Integer, db.ForeignKey("attendance_sessions.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)  # present, absent, excused
    __table_args__ = (db.UniqueConstraint("college_id", "session_id", "student_id", name="uq_attendance_record"),)


class Skill(TimestampMixin, db.Model):
    __tablename__ = "skills"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    category = db.Column(db.String(50), nullable=True)


class StudentSkill(TimestampMixin, db.Model):
    __tablename__ = "student_skills"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=False, index=True)
    proficiency = db.Column(db.String(30), nullable=True)
    verification_status = db.Column(db.String(20), default="pending", nullable=False)
    skill = db.relationship("Skill")
    __table_args__ = (db.UniqueConstraint("college_id", "student_id", "skill_id", name="uq_student_skill"),)


class Certification(TimestampMixin, db.Model):
    __tablename__ = "certifications"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    course_name = db.Column(db.String(180), nullable=False)
    provider = db.Column(db.String(160), nullable=True)
    completion_date = db.Column(db.Date, nullable=True)
    certificate_document_id = db.Column(db.Integer, nullable=True)
    verification_status = db.Column(db.String(20), default="pending", nullable=False)


class StudentProject(TimestampMixin, db.Model):
    __tablename__ = "student_projects"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=True)
    technologies = db.Column(db.String(500), nullable=True)
    project_url = db.Column(db.String(500), nullable=True)
    verification_status = db.Column(db.String(20), default="pending", nullable=False)


class StudentActivity(TimestampMixin, db.Model):
    __tablename__ = "student_activities"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    activity_date = db.Column(db.Date, nullable=True)
    role_or_achievement = db.Column(db.String(250), nullable=True)
    verification_status = db.Column(db.String(20), default="pending", nullable=False)


class StudentDocument(TimestampMixin, db.Model):
    __tablename__ = "student_documents"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    document_type = db.Column(db.String(30), nullable=False)  # resume, cv, certificate, other
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    mime_type = db.Column(db.String(100), nullable=True)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_current = db.Column(db.Boolean, default=True, nullable=False)


class Company(TimestampMixin, db.Model):
    __tablename__ = "companies"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    name = db.Column(db.String(180), nullable=False)
    industry = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    contact_email = db.Column(db.String(254), nullable=True)
    __table_args__ = (db.UniqueConstraint("college_id", "name", name="uq_company_college_name"),)


class JobOpening(TimestampMixin, db.Model):
    __tablename__ = "job_openings"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=True)
    required_skills = db.Column(db.String(1000), nullable=True)
    minimum_cgpa = db.Column(db.Numeric(4, 2), nullable=True)
    max_active_backlogs = db.Column(db.Integer, nullable=True)
    package_lpa = db.Column(db.Numeric(10, 2), nullable=True)
    graduation_year = db.Column(db.Integer, nullable=True)
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="open", nullable=False)
    company = db.relationship("Company")


class Application(TimestampMixin, db.Model):
    __tablename__ = "applications"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job_openings.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    resume_document_id = db.Column(db.Integer, db.ForeignKey("student_documents.id"), nullable=True)
    status = db.Column(db.String(30), default=PlacementStatus.APPLIED.value, nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    student = db.relationship("Student")
    job = db.relationship("JobOpening")
    resume_document = db.relationship("StudentDocument", foreign_keys=[resume_document_id])
    __table_args__ = (db.UniqueConstraint("college_id", "job_id", "student_id", name="uq_application_once"),)


class InterviewRound(TimestampMixin, db.Model):
    __tablename__ = "interview_rounds"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job_openings.id"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    round_number = db.Column(db.Integer, nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=True)


class InterviewResult(TimestampMixin, db.Model):
    __tablename__ = "interview_results"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True)
    round_id = db.Column(db.Integer, db.ForeignKey("interview_rounds.id"), nullable=False, index=True)
    attendance_status = db.Column(db.String(20), default="scheduled", nullable=False)
    result = db.Column(db.String(30), default="pending", nullable=False)
    notes = db.Column(db.Text, nullable=True)
    __table_args__ = (db.UniqueConstraint("college_id", "application_id", "round_id", name="uq_interview_result"),)


class PlacementOffer(TimestampMixin, db.Model):
    __tablename__ = "placement_offers"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=False, index=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    role_title = db.Column(db.String(180), nullable=False)
    annual_package_lpa = db.Column(db.Numeric(10, 2), nullable=False)
    offer_date = db.Column(db.Date, nullable=True)
    acceptance_status = db.Column(db.String(20), default="pending", nullable=False)
    joining_date = db.Column(db.Date, nullable=True)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey("colleges.id"), nullable=True, index=True)
    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(100), nullable=True)
    entity_id = db.Column(db.String(80), nullable=True)
    detail = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
