import os
from pathlib import Path
import click
from flask import Flask, render_template
from flask.cli import with_appcontext
from .config import Config
from .extensions import db, login_manager, csrf, migrate


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_ROOT"]).mkdir(parents=True, exist_ok=True)
    for folder in ("resumes", "certificates", "other"):
        (Path(app.config["UPLOAD_ROOT"]) / folder).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from . import models  # noqa: F401
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.admin import admin_bp
    from .routes.student import student_bp
    from .routes.files import files_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(files_bp, url_prefix="/files")

    @app.cli.command("init-db")
    @with_appcontext
    def init_db_command():
        """Create tables for local development. Prefer migrations for production."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("create-super-admin")
    @with_appcontext
    def create_super_admin_command():
        """Create a Super Admin interactively without hard-coded credentials."""
        from .models import User, Role
        from getpass import getpass
        email = click.prompt("Super Admin email").strip().lower()
        if User.query.filter_by(username=email).first():
            raise click.ClickException("That username already exists.")
        password = getpass("Password (12+ characters): ")
        confirm = getpass("Confirm password: ")
        if password != confirm or len(password) < 12:
            raise click.ClickException("Passwords must match and be at least 12 characters.")
        user = User(username=email, role=Role.SUPER_ADMIN, is_active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo("Super Admin created. Sign in and create your first college.")

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(_error):
        return "File is too large. Maximum upload size is 10 MB.", 413

    return app
