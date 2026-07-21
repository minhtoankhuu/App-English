import pytest
from pydantic import ValidationError

from app.config import Settings
from app.models.user import User, UserRole
from app.security import hash_password
from app.services.usage import get_usage_status, reserve_usage


BANGKOK_NOON = __import__("datetime").datetime(2026, 7, 19, 12, 0, tzinfo=__import__("zoneinfo").ZoneInfo("Asia/Bangkok"))


def _create_user(db, role=UserRole.TEACHER, email="usage-teacher@examcraft.dev"):
    user = User(email=email, password_hash=hash_password("Secret123!"), full_name="Usage User", role=role)
    db.add(user)
    db.commit()
    return user


def test_daily_generation_limit_defaults_to_ten():
    assert Settings(_env_file=None).daily_generation_limit == 10


def test_daily_generation_limit_must_be_positive():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, daily_generation_limit=0)


def test_teacher_usage_starts_at_zero_and_reserves_amount(db):
    teacher = _create_user(db)

    status = get_usage_status(db, teacher, now=BANGKOK_NOON)
    reserved = reserve_usage(db, teacher, 3, now=BANGKOK_NOON)

    assert (status.used, status.remaining) == (0, 10)
    assert (reserved.used, reserved.remaining) == (3, 7)


def test_reserve_never_blocks_even_past_configured_limit(db):
    """Không giới hạn số lượt sinh đề (quyết định chủ dự án 21/07/2026, sau khi nối
    OpenAI thật) — used_count vẫn cộng dồn để theo dõi chi phí, chỉ không còn chặn."""
    teacher = _create_user(db)
    reserve_usage(db, teacher, 8, now=BANGKOK_NOON)

    reserved = reserve_usage(db, teacher, 3, now=BANGKOK_NOON)

    assert reserved.used == 11
    assert reserved.is_unlimited is True
    assert get_usage_status(db, teacher, now=BANGKOK_NOON).used == 11


def test_usage_resets_on_next_bangkok_day(db):
    teacher = _create_user(db)
    reserve_usage(db, teacher, 4, now=BANGKOK_NOON)
    tomorrow = BANGKOK_NOON.replace(day=20)

    assert get_usage_status(db, teacher, now=tomorrow).used == 0


def test_admin_is_unlimited(db):
    admin = _create_user(db, role=UserRole.ADMIN, email="usage-admin@examcraft.dev")

    status = reserve_usage(db, admin, 99, now=BANGKOK_NOON)

    assert status.is_unlimited is True


def test_usage_me_requires_login(client):
    assert client.get("/usage/me").status_code == 401


def test_usage_me_returns_teacher_status(client, db):
    _create_user(db)
    assert client.post(
        "/auth/login", json={"email": "usage-teacher@examcraft.dev", "password": "Secret123!"}
    ).status_code == 200

    response = client.get("/usage/me")

    assert response.status_code == 200
    assert response.json()["is_unlimited"] is True
