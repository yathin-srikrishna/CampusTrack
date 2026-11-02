from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models import College, User, Role, Department, Branch, Section, Semester
from ..services.audit import log_action

main_bp = Blueprint("main", __name__)

@main_bp.get("/")
def home():
    if current_user.is_authenticated:
        if current_user.role == Role.STUDENT.value:
            return redirect(url_for("student.dashboard"))
        return redirect(url_for("admin.dashboard"))
    return render_template("home.html")

@main_bp.route("/register-college", methods=["GET", "POST"])
def register_college():
    """Public college onboarding: create tenant, starter structure and first admin atomically."""
    if current_user.is_authenticated:
        flash("Sign out before registering a new college.", "info")
        return redirect(url_for("main.home"))
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        name = request.form.get("name", "").strip()
        official_email = request.form.get("official_email", "").strip().lower()
        admin_username = request.form.get("admin_username", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        try:
            if not all([code, name, official_email, admin_username, password]):
                raise ValueError("Complete all required fields.")
            if len(code) > 30 or len(name) > 200 or len(official_email) > 254:
                raise ValueError("One or more fields exceed the allowed length.")
            if len(password) < 12:
                raise ValueError("College admin password must contain at least 12 characters.")
            if password != confirm:
                raise ValueError("Passwords do not match.")
            if College.query.filter_by(code=code).first():
                raise ValueError("That college code is already registered.")
            if User.query.filter_by(username=admin_username).first():
                raise ValueError("That administrator username is already registered.")

            college = College(code=code, name=name, official_email=official_email, status="active")
            db.session.add(college)
            db.session.flush()
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
                year = 2026 + (sem_no - 1) // 2
                db.session.add(Semester(college_id=college.id, number=sem_no,
                                        academic_year=f"{year}-{str(year + 1)[-2:]}"))
            admin = User(username=admin_username, college_id=college.id,
                         role=Role.COLLEGE_ADMIN.value, is_active=True,
                         must_change_password=False)
            admin.set_password(password)
            db.session.add(admin)
            db.session.flush()
            log_action("college_self_registered", college_id=college.id,
                       actor_user_id=admin.id, entity_type="college", entity_id=college.id)
            db.session.commit()
            flash("College registered successfully. You can now sign in with your College Admin username and password.", "success")
            return redirect(url_for("auth.login"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        except IntegrityError:
            db.session.rollback()
            flash("College code or admin username already exists. Nothing was saved; please use unique values.", "danger")
    return render_template("register_college.html")
