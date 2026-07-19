import uuid

from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.security import hash_password


def _login(client, db, *, email: str, role: UserRole) -> User:
    user = User(
        email=email,
        password_hash=hash_password("Secret123!"),
        full_name="Audit User",
        role=role,
    )
    db.add(user)
    db.commit()
    response = client.post("/auth/login", json={"email": email, "password": "Secret123!"})
    assert response.status_code == 200
    return user


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


def test_audit_log_api_requires_admin(client, db):
    assert client.get("/admin/audit-logs").status_code == 401

    _login(client, db, email="audit-teacher@examcraft.dev", role=UserRole.TEACHER)

    assert client.get("/admin/audit-logs").status_code == 403


def test_audit_log_api_returns_newest_page(client, db):
    _login(client, db, email="audit-admin@examcraft.dev", role=UserRole.ADMIN)
    for index in range(3):
        response = client.post(
            "/admin/teachers",
            json={
                "email": f"audit-page-{index}@examcraft.dev",
                "full_name": f"Teacher {index}",
                "password": "Secret123!",
            },
        )
        assert response.status_code == 201

    response = client.get("/admin/audit-logs?limit=1&offset=1")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert len(body["items"]) == 1
    expected = list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())))[1]
    assert body["items"][0]["id"] == str(expected.id)


def test_audit_log_api_validates_pagination(client, db):
    _login(client, db, email="audit-validation@examcraft.dev", role=UserRole.ADMIN)

    assert client.get("/admin/audit-logs?limit=0").status_code == 422
    assert client.get("/admin/audit-logs?limit=101").status_code == 422
    assert client.get("/admin/audit-logs?offset=-1").status_code == 422
