import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def record_audit_log(
    db: Session,
    *,
    actor: User,
    action: str,
    target_type: str,
    target_id: uuid.UUID,
    target_label: str,
    details: dict[str, object] | None = None,
) -> AuditLog:
    log = AuditLog(
        actor_user_id=actor.id,
        actor_email=actor.email,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_label=target_label,
        details=details or {},
    )
    db.add(log)
    return log


def record_teacher_audit_log(
    db: Session, *, actor: User, action: str, target: User, details: dict[str, object] | None = None
) -> AuditLog:
    return record_audit_log(
        db, actor=actor, action=action, target_type="teacher", target_id=target.id, target_label=target.email,
        details=details,
    )
