from pathlib import Path
from uuid import uuid4
from flask import Blueprint, current_app, request, redirect, url_for, flash, abort, send_file
from flask_login import current_user
from werkzeug.utils import secure_filename
from ..extensions import db
from ..models import Role, Student, StudentDocument, AuditLog
from ..security import roles_required
from ..services.audit import log_action

files_bp = Blueprint("files", __name__)


def _student_for_current_user():
    return Student.query.filter_by(user_id=current_user.id, college_id=current_user.college_id).first()


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]


@files_bp.post("/upload")
@roles_required(Role.STUDENT)
def upload():
    student = _student_for_current_user()
    if not student:
        abort(403)
    file = request.files.get("file")
    document_type = request.form.get("document_type", "resume").strip().lower()
    if document_type not in {"resume", "cv", "certificate", "other"}:
        abort(400)
    if not file or not file.filename or not _allowed(file.filename):
        flash("Upload a PDF, PNG or JPG file.", "danger")
        return redirect(url_for("student.dashboard"))
    original = secure_filename(file.filename)[:255] or "document"
    extension = original.rsplit(".", 1)[1].lower()
    stored = f"{uuid4().hex}.{extension}"
    folder_name = "certificates" if document_type == "certificate" else "resumes"
    folder = Path(current_app.config["UPLOAD_ROOT"]) / folder_name / str(student.college_id) / str(student.id)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / stored
    file.save(destination)
    # Basic signature check for common types; production deployments should also malware-scan files.
    with destination.open("rb") as stream:
        header = stream.read(8)
    valid = (extension == "pdf" and header.startswith(b"%PDF-")) or \
            (extension in {"jpg", "jpeg"} and header.startswith(b"\xff\xd8\xff")) or \
            (extension == "png" and header.startswith(b"\x89PNG\r\n\x1a\n"))
    if not valid:
        destination.unlink(missing_ok=True)
        flash("The uploaded file does not match its file extension.", "danger")
        return redirect(url_for("student.dashboard"))
    if document_type in {"resume", "cv"}:
        StudentDocument.query.filter_by(college_id=student.college_id, student_id=student.id,
                                         document_type=document_type, is_current=True).update({"is_current": False})
    doc = StudentDocument(college_id=student.college_id, student_id=student.id,
                          document_type=document_type, original_filename=original,
                          stored_filename=f"{student.college_id}/{student.id}/{stored}",
                          mime_type=file.mimetype, uploaded_by=current_user.id, is_current=True)
    db.session.add(doc)
    db.session.commit()
    log_action("document_uploaded", college_id=student.college_id, actor_user_id=current_user.id,
               entity_type="student_document", entity_id=doc.id)
    flash("Document uploaded privately.", "success")
    return redirect(url_for("student.dashboard"))


@files_bp.get("/<int:document_id>")
def download(document_id):
    from flask_login import login_required
    # Apply login_required manually so the endpoint never serves a file anonymously.
    if not current_user.is_authenticated:
        return current_app.login_manager.unauthorized()
    doc = db.session.get(StudentDocument, document_id) or abort(404)
    if current_user.role == Role.SUPER_ADMIN.value:
        pass  # Platform-level access should be explicitly governed by production policy.
    elif current_user.college_id != doc.college_id:
        abort(404)
    elif current_user.role == Role.STUDENT.value:
        student = _student_for_current_user()
        if not student or student.id != doc.student_id:
            abort(404)
    elif current_user.role not in {Role.COLLEGE_ADMIN.value, Role.FACULTY.value, Role.PLACEMENT_OFFICER.value}:
        abort(404)
    # stored_filename contains only generated IDs and fixed path segments; resolve under upload root.
    root = Path(current_app.config["UPLOAD_ROOT"]).resolve()
    folder_name = "certificates" if doc.document_type == "certificate" else "resumes"
    path = (root / folder_name / doc.stored_filename).resolve()
    if root not in path.parents or not path.is_file():
        abort(404)
    log_action("document_downloaded", college_id=doc.college_id, actor_user_id=current_user.id,
               entity_type="student_document", entity_id=doc.id)
    return send_file(path, as_attachment=True, download_name=doc.original_filename)
