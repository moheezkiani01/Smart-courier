import json
from datetime import datetime
from flask_login import current_user
from app.extensions import db
from app.models.support import AuditLog

def log_audit(action: str, entity_type: str, entity_id: int, before: dict = None, after: dict = None, branch_id: int = None, user_id: int = None):
    """
    Append-only security and data mutation audit logging.
    Redacts sensitive keys (passwords, tokens).
    """
    if user_id is None and current_user and current_user.is_authenticated:
        user_id = current_user.id

    def sanitize(data):
        if not data or not isinstance(data, dict):
            return None
        cleaned = {}
        for k, v in data.items():
            if any(s in k.lower() for s in ["password", "secret", "csrf", "token"]):
                cleaned[k] = "[REDACTED]"
            elif isinstance(v, (datetime,)):
                cleaned[k] = v.isoformat()
            else:
                cleaned[k] = v
        return json.dumps(cleaned)

    entry = AuditLog(
        actor_user_id=user_id,
        branch_id=branch_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=sanitize(before),
        after_json=sanitize(after),
        occurred_at=datetime.utcnow(),
    )
    db.session.add(entry)
