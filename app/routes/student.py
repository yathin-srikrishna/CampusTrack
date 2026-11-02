from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from ..extensions import db
from ..models import (Role, Student, Mark, SemesterResult, AttendanceRecord,
                      AttendanceSession, StudentSkill, Certification, StudentProject,
                      StudentActivity, StudentDocument, JobOpening, Application, PlacementOffer)
from ..security import roles_required
from ..services.audit import log_action

student_bp = Blueprint("student", __name__)


def own_student():
    # Never trust student_id from a query parameter for student self-service.
    student = Student.query.filter_by(user_id=current_user.id, college_id=current_user.college_id).first()
    return student


@student_bp.get("/")
@roles_required(Role.STUDENT)
def dashboard():
    student = own_student()
    if not student:
        flash("Your student profile has not been configured. Contact your college administrator.", "warning")
        return render_template("student/dashboard.html", student=None, marks=[], results=[], attendance=[], skills=[], certifications=[], projects=[], activities=[], documents=[], applications=[], offers=[])
    marks = Mark.query.filter_by(college_id=student.college_id, student_id=student.id).order_by(Mark.created_at.desc()).limit(50).all()
    results = SemesterResult.query.filter_by(college_id=student.college_id, student_id=student.id).order_by(SemesterResult.semester_id).all()
    attendance_query = db.session.query(AttendanceRecord, AttendanceSession).join(
        AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id
    ).filter(AttendanceRecord.college_id == student.college_id,
             AttendanceRecord.student_id == student.id)
    attendance_total = attendance_query.count()
    attendance_present = attendance_query.filter(AttendanceRecord.status == "present").count()
    attendance_percentage = round((attendance_present / attendance_total) * 100, 1) if attendance_total else None
    attendance_rows = attendance_query.order_by(AttendanceSession.session_date.desc()).limit(50).all()
    skills = StudentSkill.query.filter_by(college_id=student.college_id, student_id=student.id).all()
    certifications = Certification.query.filter_by(college_id=student.college_id, student_id=student.id).all()
    projects = StudentProject.query.filter_by(college_id=student.college_id, student_id=student.id).all()
    activities = StudentActivity.query.filter_by(college_id=student.college_id, student_id=student.id).all()
    documents = StudentDocument.query.filter_by(college_id=student.college_id, student_id=student.id).order_by(StudentDocument.created_at.desc()).all()
    applications = Application.query.filter_by(college_id=student.college_id, student_id=student.id).all()
    offers = PlacementOffer.query.filter_by(college_id=student.college_id, student_id=student.id).all()
    return render_template("student/dashboard.html", student=student, marks=marks, results=results,
                           attendance=attendance_rows, attendance_percentage=attendance_percentage, skills=skills, certifications=certifications,
                           projects=projects, activities=activities, documents=documents,
                           applications=applications, offers=offers)


@student_bp.route("/profile", methods=["GET", "POST"])
@roles_required(Role.STUDENT)
def profile():
    student = own_student()
    if not student:
        flash("Your profile is not configured yet.", "warning")
        return redirect(url_for("student.dashboard"))
    if request.method == "POST":
        # Students may edit contact details only; roll number, college and academic fields are admin-controlled.
        student.email = request.form.get("email", "").strip().lower() or None
        student.phone = request.form.get("phone", "").strip() or None
        db.session.commit()
        log_action("student_contact_updated", college_id=student.college_id, actor_user_id=current_user.id,
                   entity_type="student", entity_id=student.id)
        flash("Contact details updated.", "success")
        return redirect(url_for("student.profile"))
    return render_template("student/profile.html", student=student)


@student_bp.get("/jobs")
@roles_required(Role.STUDENT)
def jobs():
    student = own_student()
    if not student:
        return render_template("student/jobs.html", jobs=[], applications=[])
    jobs = JobOpening.query.filter_by(college_id=student.college_id, status="open").order_by(JobOpening.created_at.desc()).all()
    applications = Application.query.filter_by(college_id=student.college_id, student_id=student.id).all()
    applied_ids = {a.job_id for a in applications}
    return render_template("student/jobs.html", jobs=jobs, applications=applications, applied_ids=applied_ids)


@student_bp.post("/jobs/<int:job_id>/apply")
@roles_required(Role.STUDENT)
def apply_job(job_id):
    student = own_student()
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("student.jobs"))
    job = JobOpening.query.filter_by(id=job_id, college_id=student.college_id, status="open").first_or_404()
    if Application.query.filter_by(college_id=student.college_id, job_id=job.id, student_id=student.id).first():
        flash("You have already applied for this opening.", "info")
    else:
        current_resume = StudentDocument.query.filter_by(
            college_id=student.college_id, student_id=student.id,
            document_type="resume", is_current=True
        ).order_by(StudentDocument.created_at.desc()).first()
        application = Application(
            college_id=student.college_id, job_id=job.id, student_id=student.id,
            resume_document_id=current_resume.id if current_resume else None,
        )
        db.session.add(application)
        db.session.commit()
        log_action("job_applied", college_id=student.college_id, actor_user_id=current_user.id,
                   entity_type="application", entity_id=application.id)
        flash("Application submitted.", "success")
    return redirect(url_for("student.jobs"))
