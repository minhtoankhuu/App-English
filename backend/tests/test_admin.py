import json

from sqlalchemy import func, select

from app.models.audit import AuditLog
from app.models.user import User, UserRole
from app.security import hash_password


def _login_as(client, db, *, email, password, role):
    user = User(email=email, password_hash=hash_password(password), full_name="Seed User", role=role)
    db.add(user)
    db.commit()
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return user


def _login_as_admin(client, db):
    return _login_as(client, db, email="admin@examcraft.dev", password="Secret123!", role=UserRole.ADMIN)


def _login_as_teacher(client, db):
    return _login_as(client, db, email="teacher@examcraft.dev", password="Secret123!", role=UserRole.TEACHER)


def test_teacher_cannot_access_admin_teacher_endpoints(client, db):
    _login_as_teacher(client, db)

    assert client.get("/admin/teachers").status_code == 403
    assert (
        client.post(
            "/admin/teachers",
            json={"email": "new@examcraft.dev", "full_name": "New", "password": "Secret123!"},
        ).status_code
        == 403
    )


def test_unauthenticated_cannot_access_admin_teacher_endpoints(client):
    assert client.get("/admin/teachers").status_code == 401


def test_admin_create_list_update_teacher(client, db):
    _login_as_admin(client, db)

    resp = client.post(
        "/admin/teachers",
        json={"email": "teacher2@examcraft.dev", "full_name": "Nguyễn An", "password": "Secret123!"},
    )
    assert resp.status_code == 201
    teacher = resp.json()
    assert teacher["is_active"] is True
    assert teacher["email"] == "teacher2@examcraft.dev"
    assert "password" not in teacher and "password_hash" not in teacher

    resp = client.get("/admin/teachers")
    assert resp.status_code == 200
    emails = [t["email"] for t in resp.json()]
    assert "teacher2@examcraft.dev" in emails

    resp = client.patch(f"/admin/teachers/{teacher['id']}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    resp = client.patch(f"/admin/teachers/{teacher['id']}", json={"full_name": "Trần Bình"})
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Trần Bình"
    assert resp.json()["is_active"] is False  # không bị ghi đè bởi update khác


def test_create_teacher_duplicate_email_returns_409(client, db):
    _login_as_admin(client, db)
    payload = {"email": "dup@examcraft.dev", "full_name": "A", "password": "Secret123!"}
    assert client.post("/admin/teachers", json=payload).status_code == 201
    resp = client.post("/admin/teachers", json=payload)
    assert resp.status_code == 409


def test_update_teacher_not_found_returns_404(client, db):
    _login_as_admin(client, db)
    resp = client.patch(
        "/admin/teachers/00000000-0000-0000-0000-000000000000", json={"is_active": False}
    )
    assert resp.status_code == 404


def test_deactivated_teacher_cannot_login(client, db):
    admin_client_user = _login_as_admin(client, db)
    resp = client.post(
        "/admin/teachers",
        json={"email": "deactivated@examcraft.dev", "full_name": "Bị khóa", "password": "Secret123!"},
    )
    teacher_id = resp.json()["id"]
    client.patch(f"/admin/teachers/{teacher_id}", json={"is_active": False})
    client.post("/auth/logout")

    resp = client.post(
        "/auth/login", json={"email": "deactivated@examcraft.dev", "password": "Secret123!"}
    )
    assert resp.status_code == 401
    _ = admin_client_user


def test_password_reset_lets_teacher_login_with_new_password(client, db):
    _login_as_admin(client, db)
    resp = client.post(
        "/admin/teachers",
        json={"email": "resetme@examcraft.dev", "full_name": "Reset", "password": "OldPass123!"},
    )
    teacher_id = resp.json()["id"]
    client.patch(f"/admin/teachers/{teacher_id}", json={"password": "NewPass456!"})
    client.post("/auth/logout")

    resp = client.post(
        "/auth/login", json={"email": "resetme@examcraft.dev", "password": "OldPass123!"}
    )
    assert resp.status_code == 401

    resp = client.post(
        "/auth/login", json={"email": "resetme@examcraft.dev", "password": "NewPass456!"}
    )
    assert resp.status_code == 200


def test_admin_cannot_manage_other_admins_via_teacher_endpoint(client, db):
    admin_user = _login_as_admin(client, db)
    resp = client.patch(f"/admin/teachers/{admin_user.id}", json={"is_active": False})
    assert resp.status_code == 404


def test_create_teacher_writes_audit_log(client, db):
    admin = _login_as_admin(client, db)

    response = client.post(
        "/admin/teachers",
        json={"email": "audit-create@examcraft.dev", "full_name": "Audit Create", "password": "Secret123!"},
    )

    assert response.status_code == 201
    teacher = response.json()
    log = db.scalar(select(AuditLog).where(AuditLog.target_id == teacher["id"]))
    assert log is not None
    assert log.actor_user_id == admin.id
    assert log.actor_email == admin.email
    assert log.action == "teacher.created"
    assert log.target_type == "teacher"
    assert log.target_label == teacher["email"]
    assert log.details == {}


def test_update_teacher_writes_safe_audit_actions(client, db):
    _login_as_admin(client, db)
    created = client.post(
        "/admin/teachers",
        json={"email": "audit-update@examcraft.dev", "full_name": "Before", "password": "Secret123!"},
    ).json()

    response = client.patch(
        f"/admin/teachers/{created['id']}",
        json={"full_name": "After", "is_active": False, "password": "NewSecret456!"},
    )

    assert response.status_code == 200
    logs = list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.target_id == created["id"], AuditLog.action != "teacher.created")
            .order_by(AuditLog.created_at, AuditLog.id)
        )
    )
    assert {log.action for log in logs} == {
        "teacher.updated",
        "teacher.deactivated",
        "teacher.password_reset",
    }
    update_log = next(log for log in logs if log.action == "teacher.updated")
    assert update_log.details == {"changed_fields": ["full_name"]}
    serialized = json.dumps([{"action": log.action, "details": log.details} for log in logs])
    assert "NewSecret456!" not in serialized
    assert "password_hash" not in serialized


def test_duplicate_teacher_does_not_write_extra_audit_log(client, db):
    _login_as_admin(client, db)
    payload = {"email": "audit-dup@examcraft.dev", "full_name": "Audit", "password": "Secret123!"}
    assert client.post("/admin/teachers", json=payload).status_code == 201
    count_before = db.scalar(select(func.count()).select_from(AuditLog))

    response = client.post("/admin/teachers", json=payload)

    assert response.status_code == 409
    assert db.scalar(select(func.count()).select_from(AuditLog)) == count_before
