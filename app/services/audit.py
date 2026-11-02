from ..extensions import db
from ..models import AuditLog

def log_action(action, college_id=None, actor_user_id=None, entity_type=None, entity_id=None, detail=None):
    """Keep audit details minimal. Never include passwords, tokens, or uploaded file contents."""
    try:
        entry = AuditLog(college_id=college_id, actor_user_id=actor_user_id, action=action,
                         entity_type=entity_type, entity_id=str(entity_id) if entity_id is not None else None,
                         detail=detail)
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
