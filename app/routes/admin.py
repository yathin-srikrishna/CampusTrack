from io import BytesIO
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, send_file
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models import (Role, College, User, Department, Branch, Section, Student,
                      Semester, Subject, Mark, SemesterResult, AttendanceSession,
                      AttendanceRecord, Company, JobOpening, Application, PlacementOffer,
                      Skill, StudentSkill, Certification, StudentProject, StudentActivity, StudentDocument)
from ..security import roles_required, ensure_same_college
from ..services.audit import log_action
from ..services.analytics import (college_placement_summary, department_placement_rows,
    package_histogram_png, skill_demand, application_status_summary, application_status_chart_png,
    academic_performance_chart_png, attendance_status_chart_png)

admin_bp = Blueprint("admin", __name__)


def current_college_id():
    if current_user.role == Role.SUPER_ADMIN.value:
        raw = request.args.get("college_id") or request.form.get("college_id")
        if raw:
            try:
                return int(raw)
            except ValueError:
                abort(400)
        return None
    return current_user.college_id


def require_college(college_id=None):
    cid = college_id or current_college_id()
    if cid is None:
        return None
    college = db.session.get(College, cid)
    if not college:
        abort(404)
    ensure_same_college(college.id)
    return college


@admin_bp.get("/")
@roles_required(Role.SUPER_ADMIN, Role.COLLEGE_ADMIN, Role.FACULTY, Role.PLACEMENT_OFFICER)
def dashboard():
    if current_user.role == Role.SUPER_ADMIN.value:
        colleges = College.query.order_by(College.name).all()
        return render_template("admin/super_dashboard.html", colleges=colleges)
    college = require_college(current_user.college_id)
    summary = college_placement_summary(college.id)
    students_count = Student.query.filter_by(college_id=college.id).count()
    jobs_count = JobOpening.query.filter_by(college_id=college.id).count()
    applications_count = Application.query.filter_by(college_id=college.id).count()
    rejected_count = Application.query.filter_by(college_id=college.id, status="rejected").count()
    accepted_count = Application.query.filter(Application.college_id == college.id,
        Application.status.in_(["selected", "offer_accepted"])).count()
    return render_template("admin/dashboard.html", college=college, summary=summary,
        students_count=students_count, jobs_count=jobs_count, applications_count=applications_count,
        rejected_count=rejected_count, accepted_count=accepted_count)


@admin_bp.route("/colleges", methods=["GET", "POST"])
@roles_required(Role.SUPER_ADMIN)
def colleges():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        name = request.form.get("name", "").strip()
        email = request.form.get("official_email", "").strip().lower()
        if not code or not name or not email:
            flash("College code, name and official email are required.", "danger")
        else:
            college = College(code=code, name=name, official_email=email, status="active")
            db.session.add(college)
            try:
                db.session.flush()
                # Create a starter academic structure in the same transaction.
                department = Department(college_id=college.id, name="Computer Science and Engineering", code="CSE")
                db.session.add(department)
                db.session.flush()
                branch = Branch(college_id=college.id, department_id=department.id,
                                name="Artificial Intelligence and Machine Learning", code="AIML")
                db.session.add(branch)
                db.session.flush()
                for section_name in ("A", "B"):
                    db.session.add(Section(college_id=college.id, branch_id=branch.id,
                                           name=section_name, academic_year="2026-2027"))
                for sem_no in range(1, 9):
                    academic_start = 2026 + (sem_no - 1) // 2
                    academic_end = str(academic_start + 1)[-2:]
                    db.session.add(Semester(college_id=college.id, number=sem_no,
                                            academic_year=f"{academic_start}-{academic_end}"))
                db.session.commit()
                log_action("college_created", actor_user_id=current_user.id, entity_type="college", entity_id=college.id)
                flash("College and starter academic structure created in MySQL. Create its College Admin account next.", "success")
                return redirect(url_for("admin.colleges"))
            except IntegrityError:
                db.session.rollback()
                flash("That college code already exists. Choose another code.", "danger")
    return render_template("admin/colleges.html", colleges=College.query.order_by(College.name).all())


@admin_bp.route("/colleges/<int:college_id>/create-admin", methods=["GET", "POST"])
@roles_required(Role.SUPER_ADMIN)
def create_college_admin(college_id):
    college = db.session.get(College, college_id) or abort(404)
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if not username or len(password) < 12:
            flash("Username is required and password must be at least 12 characters.", "danger")
        elif User.query.filter_by(username=username).first():
            flash("That username is already in use.", "danger")
        else:
            user = User(username=username, college_id=college.id, role=Role.COLLEGE_ADMIN.value, is_active=True, must_change_password=True)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
                log_action("college_admin_created", college_id=college.id, actor_user_id=current_user.id,
                           entity_type="user", entity_id=user.id)
                flash("College Admin account created. Share credentials securely and require a change before production use.", "success")
                return redirect(url_for("admin.colleges"))
            except IntegrityError:
                db.session.rollback()
                flash("Could not create the account. Check the username and try again.", "danger")
    return render_template("admin/create_admin.html", college=college)


@admin_bp.route("/structure", methods=["GET", "POST"])
@roles_required(Role.COLLEGE_ADMIN)
def structure():
    college = require_college(current_user.college_id)
    if request.method == "POST":
        kind = request.form.get("kind")
        name = request.form.get("name", "").strip()
        code = request.form.get("code", "").strip().upper()
        try:
            if kind == "department":
                db.session.add(Department(college_id=college.id, name=name, code=code))
            elif kind == "branch":
                department_id = int(request.form.get("department_id", "0"))
                department = Department.query.filter_by(id=department_id, college_id=college.id).first_or_404()
                db.session.add(Branch(college_id=college.id, department_id=department.id, name=name, code=code))
            elif kind == "section":
                branch_id = int(request.form.get("branch_id", "0"))
                branch = Branch.query.filter_by(id=branch_id, college_id=college.id).first_or_404()
                db.session.add(Section(college_id=college.id, branch_id=branch.id, name=name,
                                        academic_year=request.form.get("academic_year", "").strip()))
            else:
                abort(400)
            db.session.commit()
            log_action(f"{kind}_created", college_id=college.id, actor_user_id=current_user.id)
            flash(f"{kind.title()} added.", "success")
            return redirect(url_for("admin.structure"))
        except (ValueError, IntegrityError):
            db.session.rollback()
            flash("Invalid information or duplicate code. Please check and try again.", "danger")
    departments = Department.query.filter_by(college_id=college.id).order_by(Department.name).all()
    branches = Branch.query.filter_by(college_id=college.id).order_by(Branch.name).all()
    sections = Section.query.filter_by(college_id=college.id).order_by(Section.name).all()
    return render_template("admin/structure.html", college=college, departments=departments, branches=branches, sections=sections)


@admin_bp.route("/students", methods=["GET", "POST"])
@roles_required(Role.COLLEGE_ADMIN, Role.FACULTY)
def students():
    """Create a student profile and login account in one database transaction."""
    import secrets
    import string

    college = require_college(current_user.college_id)
    created_credentials = None

    if request.method == "POST":
        roll_no = request.form.get("roll_no", "").strip().upper()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower() or None
        phone = request.form.get("phone", "").strip() or None
        section_raw = request.form.get("section_id", "").strip()
        graduation_raw = request.form.get("graduation_year", "").strip()
        admission_raw = request.form.get("admission_year", "").strip()
        semester_raw = request.form.get("current_semester", "").strip()

        try:
            section_id = int(section_raw) if section_raw else None
            graduation_year = int(graduation_raw) if graduation_raw else None
            admission_year = int(admission_raw) if admission_raw else None
            current_semester = int(semester_raw) if semester_raw else None
            if not roll_no or not full_name:
                raise ValueError("Roll number and full name are required.")
            if len(roll_no) > 50 or len(full_name) > 160:
                raise ValueError("Roll number or name is too long.")
            if current_semester is not None and not 1 <= current_semester <= 12:
                raise ValueError("Semester must be between 1 and 12.")
            if graduation_year is not None and not 2000 <= graduation_year <= 2100:
                raise ValueError("Enter a valid graduation year.")
            if admission_year is not None and not 2000 <= admission_year <= 2100:
                raise ValueError("Enter a valid admission year.")
            if section_id:
                Section.query.filter_by(id=section_id, college_id=college.id).first_or_404()

            # The roll number is also the student's login username.
            login_username = roll_no.lower()
            if User.query.filter_by(username=login_username).first():
                raise ValueError("This roll number is already used as a login username.")
            if Student.query.filter_by(college_id=college.id, roll_no=roll_no).first():
                raise ValueError("This roll number already exists in this college.")
            if email and Student.query.filter(db.func.lower(Student.email) == email).first():
                raise ValueError("This email address is already registered.")

            alphabet = string.ascii_letters + string.digits + "!@#$%*-_"
            temporary_password = "".join(secrets.choice(alphabet) for _ in range(20))
            user = User(username=login_username, college_id=college.id,
                        role=Role.STUDENT.value, is_active=True,
                        must_change_password=True)
            user.set_password(temporary_password)
            db.session.add(user)
            db.session.flush()

            student = Student(
                college_id=college.id, user_id=user.id, section_id=section_id,
                roll_no=roll_no, full_name=full_name, email=email, phone=phone,
                admission_year=admission_year, graduation_year=graduation_year,
                current_semester=current_semester, status="active")
            db.session.add(student)
            db.session.flush()
            log_action("student_created", college_id=college.id,
                       actor_user_id=current_user.id, entity_type="student",
                       entity_id=student.id)
            db.session.commit()
            created_credentials = {"roll_no": roll_no, "email": email,
                                   "temporary_password": temporary_password}
            flash("Student profile and login account were saved to MySQL successfully.", "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        except IntegrityError:
            db.session.rollback()
            flash("A duplicate roll number, username, or email was detected. No records were saved.", "danger")

    student_rows = Student.query.filter_by(college_id=college.id).order_by(Student.roll_no).all()
    sections = Section.query.filter_by(college_id=college.id).order_by(Section.name).all()
    return render_template("admin/students.html", college=college,
                           students=student_rows, sections=sections,
                           created_credentials=created_credentials)


@admin_bp.get("/analytics")
@roles_required(Role.COLLEGE_ADMIN, Role.PLACEMENT_OFFICER)
def analytics():
    college = require_college(current_user.college_id)
    accepted_count = Application.query.filter_by(college_id=college.id, status="offer_accepted").count()
    rejected_count = Application.query.filter_by(college_id=college.id, status="rejected").count()
    pending_count = Application.query.filter(Application.college_id == college.id,
        Application.status.in_(["applied", "shortlisted", "interview", "waitlisted"])).count()
    return render_template("admin/analytics.html", college=college,
                           summary=college_placement_summary(college.id),
                           section_rows=department_placement_rows(college.id),
                           skills=skill_demand(college.id),
                           application_statuses=application_status_summary(college.id),
                           accepted_count=accepted_count, rejected_count=rejected_count,
                           pending_count=pending_count)


@admin_bp.get("/analytics/package-chart.png")
@roles_required(Role.COLLEGE_ADMIN, Role.PLACEMENT_OFFICER)
def package_chart():
    college = require_college(current_user.college_id)
    chart = package_histogram_png(college.id)
    return send_file(chart, mimetype="image/png", download_name="package-distribution.png")




@admin_bp.get("/analytics/application-chart.png")
@roles_required(Role.COLLEGE_ADMIN, Role.PLACEMENT_OFFICER)
def application_chart():
    college = require_college(current_user.college_id)
    return send_file(application_status_chart_png(college.id), mimetype="image/png",
                     download_name="application-status-overview.png")


@admin_bp.get("/analytics/academic-chart.png")
@roles_required(Role.COLLEGE_ADMIN, Role.PLACEMENT_OFFICER)
def academic_chart():
    college = require_college(current_user.college_id)
    return send_file(academic_performance_chart_png(college.id), mimetype="image/png",
                     download_name="academic-performance.png")


@admin_bp.get("/analytics/attendance-chart.png")
@roles_required(Role.COLLEGE_ADMIN, Role.PLACEMENT_OFFICER)
def attendance_chart():
    college = require_college(current_user.college_id)
    return send_file(attendance_status_chart_png(college.id), mimetype="image/png",
                     download_name="attendance-overview.png")


@admin_bp.route("/recruitment", methods=["GET", "POST"])
@roles_required(Role.COLLEGE_ADMIN, Role.PLACEMENT_OFFICER)
def recruitment():
    college = require_college(current_user.college_id)
    if request.method == "POST":
        name = request.form.get("company", "").strip()
        title = request.form.get("title", "").strip()
        try:
            package = float(request.form.get("package_lpa", "0"))
            minimum_cgpa = float(request.form.get("minimum_cgpa", "0")) if request.form.get("minimum_cgpa") else None
            if not name or not title or package < 0 or (minimum_cgpa is not None and not 0 <= minimum_cgpa <= 10):
                raise ValueError
            company = Company.query.filter_by(college_id=college.id, name=name).first()
            if not company:
                company = Company(college_id=college.id, name=name)
                db.session.add(company)
                db.session.flush()
            job = JobOpening(college_id=college.id, company_id=company.id, title=title,
                             required_skills=request.form.get("required_skills", "").strip(),
                             minimum_cgpa=minimum_cgpa, package_lpa=package,
                             status="open")
            db.session.add(job)
            db.session.commit()
            log_action("job_opening_created", college_id=college.id, actor_user_id=current_user.id,
                       entity_type="job_opening", entity_id=job.id)
            flash("Company and job opening saved.", "success")
            return redirect(url_for("admin.recruitment"))
        except (ValueError, IntegrityError):
            db.session.rollback()
            flash("Enter valid company, role, package and CGPA criteria.", "danger")
    jobs = JobOpening.query.filter_by(college_id=college.id).order_by(JobOpening.created_at.desc()).all()
    applications = Application.query.filter_by(college_id=college.id).order_by(Application.applied_at.desc()).all()
    return render_template("admin/recruitment.html", college=college, jobs=jobs, applications=applications)

@admin_bp.route("/academics", methods=["GET", "POST"])
@roles_required(Role.COLLEGE_ADMIN, Role.FACULTY)
def academics():
    college = require_college(current_user.college_id)
    action = request.form.get("action") if request.method == "POST" else None
    if request.method == "POST":
        try:
            if action == "semester":
                semester = Semester(college_id=college.id, number=int(request.form["number"]),
                                    academic_year=request.form["academic_year"].strip())
                db.session.add(semester)
            elif action == "subject":
                branch = Branch.query.filter_by(id=int(request.form["branch_id"]), college_id=college.id).first_or_404()
                semester = Semester.query.filter_by(id=int(request.form["semester_id"]), college_id=college.id).first_or_404()
                subject = Subject(college_id=college.id, branch_id=branch.id, semester_id=semester.id,
                                  code=request.form["code"].strip().upper(), name=request.form["name"].strip(),
                                  credits=float(request.form["credits"]), max_internal=float(request.form["max_internal"]),
                                  max_external=float(request.form["max_external"]))
                db.session.add(subject)
            elif action == "mark":
                student = Student.query.filter_by(id=int(request.form["student_id"]), college_id=college.id).first_or_404()
                subject = Subject.query.filter_by(id=int(request.form["subject_id"]), college_id=college.id).first_or_404()
                internal = float(request.form["internal_marks"])
                external = float(request.form["external_marks"])
                if internal < 0 or internal > float(subject.max_internal) or external < 0 or external > float(subject.max_external):
                    raise ValueError("Marks outside allowed range")
                total = internal + external
                result = "pass" if total >= 40 else "fail"  # Replace with the institution's official rules.
                mark = Mark(college_id=college.id, student_id=student.id, subject_id=subject.id,
                            internal_marks=internal, external_marks=external, total_marks=total,
                            result=result, attempt_number=int(request.form.get("attempt_number", "1")),
                            entered_by=current_user.id)
                db.session.add(mark)
            else:
                abort(400)
            db.session.commit()
            log_action(f"academic_{action}_created", college_id=college.id, actor_user_id=current_user.id)
            flash("Academic record saved. Review the official grading rules before using results.", "success")
            return redirect(url_for("admin.academics"))
        except (ValueError, KeyError, IntegrityError):
            db.session.rollback()
            flash("Invalid data, out-of-range marks, or duplicate record. Please check the form.", "danger")
    semesters = Semester.query.filter_by(college_id=college.id).order_by(Semester.number).all()
    branches = Branch.query.filter_by(college_id=college.id).order_by(Branch.name).all()
    subjects = Subject.query.filter_by(college_id=college.id).order_by(Subject.name).all()
    student_rows = Student.query.filter_by(college_id=college.id, status="active").order_by(Student.roll_no).all()
    marks = Mark.query.filter_by(college_id=college.id).order_by(Mark.created_at.desc()).limit(100).all()
    return render_template("admin/academics.html", college=college, semesters=semesters, branches=branches,
                           subjects=subjects, students=student_rows, marks=marks)


@admin_bp.route("/attendance", methods=["GET", "POST"])
@roles_required(Role.COLLEGE_ADMIN, Role.FACULTY)
def attendance():
    college = require_college(current_user.college_id)
    if request.method == "POST":
        try:
            subject = Subject.query.filter_by(id=int(request.form["subject_id"]), college_id=college.id).first_or_404()
            student = Student.query.filter_by(id=int(request.form["student_id"]), college_id=college.id).first_or_404()
            from datetime import date as date_type
            session_date = date_type.fromisoformat(request.form["session_date"])
            topic = request.form.get("topic", "").strip()
            session = AttendanceSession.query.filter_by(college_id=college.id, subject_id=subject.id,
                                                        session_date=session_date, topic=topic or None).first()
            if not session:
                session = AttendanceSession(college_id=college.id, subject_id=subject.id,
                                            session_date=session_date, topic=topic or None)
                db.session.add(session)
                db.session.flush()
            record = AttendanceRecord(college_id=college.id, session_id=session.id, student_id=student.id,
                                      status=request.form["status"])
            if record.status not in {"present", "absent", "excused"}:
                raise ValueError
            db.session.add(record)
            db.session.commit()
            log_action("attendance_record_created", college_id=college.id, actor_user_id=current_user.id)
            flash("Attendance record saved.", "success")
            return redirect(url_for("admin.attendance"))
        except (ValueError, KeyError, IntegrityError):
            db.session.rollback()
            flash("Invalid attendance entry or duplicate record.", "danger")
    subjects = Subject.query.filter_by(college_id=college.id).order_by(Subject.name).all()
    student_rows = Student.query.filter_by(college_id=college.id, status="active").order_by(Student.roll_no).all()
    recent = db.session.query(AttendanceRecord, AttendanceSession).join(
        AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id
    ).filter(AttendanceRecord.college_id == college.id).order_by(AttendanceSession.session_date.desc()).limit(100).all()
    return render_template("admin/attendance.html", college=college, subjects=subjects, students=student_rows, recent=recent)


@admin_bp.route("/applications/<int:application_id>/status", methods=["POST"])
@roles_required(Role.COLLEGE_ADMIN, Role.PLACEMENT_OFFICER)
def update_application_status(application_id):
    college = require_college(current_user.college_id)
    application = Application.query.filter_by(id=application_id, college_id=college.id).first_or_404()
    allowed = {s.value for s in PlacementStatus}
    status = request.form.get("status", "")
    if status not in allowed:
        abort(400)
    application.status = status
    offer = PlacementOffer.query.filter_by(college_id=college.id, application_id=application.id).first()
    if status in {PlacementStatus.SELECTED.value, PlacementStatus.OFFER_ACCEPTED.value}:
        if offer is None:
            offer = PlacementOffer(
                college_id=college.id,
                application_id=application.id,
                student_id=application.student_id,
                company_id=application.job.company_id,
                role_title=application.job.title,
                annual_package_lpa=application.job.package_lpa or 0,
                offer_date=date.today(),
                acceptance_status="accepted" if status == PlacementStatus.OFFER_ACCEPTED.value else "pending",
            )
            db.session.add(offer)
        else:
            offer.acceptance_status = "accepted" if status == PlacementStatus.OFFER_ACCEPTED.value else "pending"
    elif status == PlacementStatus.REJECTED.value and offer is not None:
        offer.acceptance_status = "declined"
    db.session.commit()
    log_action("application_status_updated", college_id=college.id, actor_user_id=current_user.id,
               entity_type="application", entity_id=application.id, detail=f"status={status}")
    flash("Application status updated.", "success")
    return redirect(url_for("admin.recruitment"))
