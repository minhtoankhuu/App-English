from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def record_audit_log(
    db: Session,
    *,
    actor: User,
    action: str,
    target: User,
    details: dict[str, object] | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_user_id=actor.id,
        actor_email=actor.email,
        action=action,
        target_type="teacher",
        target_id=target.id,
        target_label=target.email,
        details=details or {},
    )
    db.add(log)
    return log
