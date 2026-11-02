from functools import wraps
from flask import abort
from flask_login import current_user, login_required
from .models import Role


def roles_required(*roles):
    allowed = {r.value if isinstance(r, Role) else str(r) for r in roles}
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in allowed:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def ensure_same_college(college_id):
    """Fail closed: only Super Admin may cross tenant boundaries."""
    if not current_user.is_authenticated:
        abort(403)
    if current_user.role == Role.SUPER_ADMIN.value:
        return
    if current_user.college_id is None or current_user.college_id != college_id:
        abort(403)
