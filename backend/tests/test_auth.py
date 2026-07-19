import json

from itsdangerous import TimestampSigner
from itsdangerous.encoding import base64_encode

from app.config import get_settings
from app.models.user import User, UserRole
from app.security import hash_password


def _create_user(db, email="teacher@examcraft.dev", password="Secret123!", role=UserRole.TEACHER):
    user = User(email=email, password_hash=hash_password(password), full_name="Test User", role=role)
    db.add(user)
    db.commit()
    return user


def test_login_success_sets_session(client, db):
    _create_user(db, email="teacher@examcraft.dev", password="Secret123!")

    response = client.post("/auth/login", json={"email": "teacher@examcraft.dev", "password": "Secret123!"})

    assert response.status_code == 200
    assert response.json()["email"] == "teacher@examcraft.dev"

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "teacher"


def test_login_wrong_password_rejected(client, db):
    _create_user(db, email="teacher@examcraft.dev", password="Secret123!")

    response = client.post("/auth/login", json={"email": "teacher@examcraft.dev", "password": "WrongPass"})

    assert response.status_code == 401


def test_login_unknown_email_rejected(client):
    response = client.post("/auth/login", json={"email": "nobody@examcraft.dev", "password": "whatever"})
    assert response.status_code == 401


def test_inactive_user_cannot_login(client, db):
    user = _create_user(db, email="disabled@examcraft.dev", password="Secret123!")
    user.is_active = False
    db.commit()

    response = client.post("/auth/login", json={"email": "disabled@examcraft.dev", "password": "Secret123!"})
    assert response.status_code == 401


def test_protected_endpoint_requires_login(client):
    response = client.get("/catalog/grades")
    assert response.status_code == 401


def test_malformed_session_user_id_returns_401_not_500(client):
    """Cookie ký hợp lệ (đúng secret) nhưng user_id không phải UUID phải trả 401, không phải 500."""
    settings = get_settings()
    signer = TimestampSigner(settings.session_secret, salt="starlette.sessions")
    payload = base64_encode(json.dumps({"user_id": "not-a-valid-uuid"}).encode("utf-8"))
    signed_value = signer.sign(payload).decode("utf-8")
    client.cookies.set(settings.session_cookie_name, signed_value)

    response = client.get("/auth/me")

    assert response.status_code == 401


def test_logout_clears_session(client, db):
    _create_user(db, email="teacher@examcraft.dev", password="Secret123!")
    client.post("/auth/login", json={"email": "teacher@examcraft.dev", "password": "Secret123!"})
    assert client.get("/auth/me").status_code == 200

    logout = client.post("/auth/logout")
    assert logout.status_code == 200

    assert client.get("/auth/me").status_code == 401
