import uuid

from sqlalchemy import select

from app.models.audit import AuditLog


def test_audit_log_model_persists_safe_metadata(db):
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()
    log = AuditLog(
        actor_user_id=actor_id,
        actor_email="admin@examcraft.dev",
        action="teacher.updated",
        target_type="teacher",
        target_id=target_id,
        target_label="teacher@examcraft.dev",
        details={"changed_fields": ["full_name"]},
    )
    db.add(log)
    db.commit()

    saved = db.scalar(select(AuditLog).where(AuditLog.id == log.id))

    assert saved is not None
    assert saved.actor_user_id == actor_id
    assert saved.target_id == target_id
    assert saved.action == "teacher.updated"
    assert saved.details == {"changed_fields": ["full_name"]}
