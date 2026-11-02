from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from . import main  # noqa: F401
from ..extensions import db
from ..models import User, Role, Student
from ..services.audit import log_action

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        # Student accounts can sign in with either their roll-number username or
        # their registered email address. College admins continue to use usernames.
        user = User.query.filter(db.func.lower(User.username) == username).first()
        if user is None and "@" in username:
            student = Student.query.filter(db.func.lower(Student.email) == username).first()
            if student is not None:
                user = db.session.get(User, student.user_id)
        if user and user.is_active and user.check_password(password):
            login_user(user, remember=False, fresh=True)
            log_action("login", college_id=user.college_id, actor_user_id=user.id)
            flash("Welcome back.", "success")
            if user.must_change_password:
                return redirect(url_for("auth.change_password"))
            if user.role == Role.STUDENT.value:
                return redirect(url_for("student.dashboard"))
            return redirect(url_for("admin.dashboard"))
        flash("Invalid username or password, or the account is inactive.", "danger")
    return render_template("auth/login.html")

@auth_bp.post("/logout")
def logout():
    if current_user.is_authenticated:
        log_action("logout", college_id=current_user.college_id, actor_user_id=current_user.id)
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
def change_password():
    from flask_login import login_required
    from functools import wraps
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not current_user.check_password(current_password):
            flash("Current password is incorrect.", "danger")
        elif len(new_password) < 12:
            flash("Use a password with at least 12 characters.", "danger")
        elif new_password != confirm_password:
            flash("New passwords do not match.", "danger")
        elif new_password == current_password:
            flash("Choose a new password different from the current one.", "danger")
        else:
            current_user.set_password(new_password)
            current_user.must_change_password = False
            db.session.commit()
            log_action("password_changed", college_id=current_user.college_id, actor_user_id=current_user.id)
            flash("Password updated successfully.", "success")
            if current_user.role == Role.STUDENT.value:
                return redirect(url_for("student.dashboard"))
            return redirect(url_for("admin.dashboard"))
    return render_template("auth/change_password.html")
