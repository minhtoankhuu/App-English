from unittest.mock import MagicMock, patch

import openai

from app.models.ai_config import AIProviderConfig
from app.models.user import User, UserRole
from app.security import hash_password
from app.services.crypto import decrypt_api_key


def _login(client, db, *, email: str = "ai-admin@examcraft.dev") -> User:
    user = User(email=email, password_hash=hash_password("Secret123!"), full_name="Admin User", role=UserRole.ADMIN)
    db.add(user)
    db.commit()
    response = client.post("/auth/login", json={"email": email, "password": "Secret123!"})
    assert response.status_code == 200
    return user


VALID_PAYLOAD = {
    "model": "gpt-4o-mini",
    "embedding_model": "text-embedding-3-small",
    "temperature": 0.7,
    "duplicate_similarity_threshold": 0.9,
    "api_key": "sk-test-1234567890",
}


def test_get_config_returns_null_when_not_configured(client, seeded_db):
    _login(client, seeded_db)
    response = client.get("/admin/ai-config")
    assert response.status_code == 200
    assert response.json() is None


def test_put_creates_config_and_masks_key(client, seeded_db):
    _login(client, seeded_db)
    response = client.put("/admin/ai-config", json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "gpt-4o-mini"
    assert body["api_key_masked"] == "sk-...7890"
    assert "api_key" not in body


def test_put_rejects_unlisted_model(client, seeded_db):
    _login(client, seeded_db)
    payload = {**VALID_PAYLOAD, "model": "gpt-3.5-turbo"}
    response = client.put("/admin/ai-config", json=payload)
    assert response.status_code == 422


def test_put_without_api_key_fails_when_no_existing_config(client, seeded_db):
    _login(client, seeded_db)
    payload = {**VALID_PAYLOAD, "api_key": None}
    response = client.put("/admin/ai-config", json=payload)
    assert response.status_code == 400


def test_put_empty_api_key_keeps_existing_key(client, seeded_db):
    _login(client, seeded_db)
    client.put("/admin/ai-config", json=VALID_PAYLOAD)

    update_payload = {**VALID_PAYLOAD, "temperature": 0.3, "api_key": None}
    response = client.put("/admin/ai-config", json=update_payload)
    assert response.status_code == 200
    assert response.json()["temperature"] == 0.3
    assert response.json()["api_key_masked"] == "sk-...7890"

    config = seeded_db.query(AIProviderConfig).filter(AIProviderConfig.is_active.is_(True)).one()
    assert decrypt_api_key(config.api_key_encrypted) == "sk-test-1234567890"


def test_put_new_api_key_replaces_old_one(client, seeded_db):
    _login(client, seeded_db)
    client.put("/admin/ai-config", json=VALID_PAYLOAD)

    update_payload = {**VALID_PAYLOAD, "api_key": "sk-new-key-000"}
    response = client.put("/admin/ai-config", json=update_payload)
    assert response.status_code == 200
    assert response.json()["api_key_masked"] == "sk-...-000"

    config = seeded_db.query(AIProviderConfig).filter(AIProviderConfig.is_active.is_(True)).one()
    assert decrypt_api_key(config.api_key_encrypted) == "sk-new-key-000"


def test_test_connection_success(client, seeded_db):
    _login(client, seeded_db)
    with patch("app.routers.admin_ai_config.openai.OpenAI") as mock_openai:
        mock_openai.return_value.models.list.return_value = MagicMock()
        response = client.post("/admin/ai-config/test", json={"api_key": "sk-test"})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "message": "Kết nối thành công."}


def test_test_connection_invalid_key(client, seeded_db):
    _login(client, seeded_db)
    with patch("app.routers.admin_ai_config.openai.OpenAI") as mock_openai:
        mock_openai.return_value.models.list.side_effect = openai.AuthenticationError(
            message="invalid", response=MagicMock(), body=None
        )
        response = client.post("/admin/ai-config/test", json={"api_key": "sk-bad"})
    assert response.status_code == 200
    assert response.json()["ok"] is False


def test_non_admin_cannot_access(client, seeded_db):
    teacher = User(
        email="teacher-ai@examcraft.dev",
        password_hash=hash_password("Secret123!"),
        full_name="Teacher",
        role=UserRole.TEACHER,
    )
    seeded_db.add(teacher)
    seeded_db.commit()
    client.post("/auth/login", json={"email": "teacher-ai@examcraft.dev", "password": "Secret123!"})
    response = client.get("/admin/ai-config")
    assert response.status_code == 403
