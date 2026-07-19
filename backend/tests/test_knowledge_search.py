import shutil
from pathlib import Path

from sqlalchemy import select

from app.import_knowledge import import_global_success
from app.models.academic import Grade, Unit
from app.models.user import User, UserRole
from app.security import hash_password

KB_ROOT = Path(__file__).resolve().parents[2] / "Knowledge_Base" / "Global Success"


def _login_as(client, db, email, role):
    user = User(email=email, password_hash=hash_password("Secret123!"), full_name="Knowledge Test", role=role)
    db.add(user)
    db.commit()
    response = client.post("/auth/login", json={"email": email, "password": "Secret123!"})
    assert response.status_code == 200
    return user


def _import_unit3_grade7(db, tmp_path):
    dest_dir = tmp_path / "G7"
    dest_dir.mkdir(parents=True)
    shutil.copyfile(KB_ROOT / "G7" / "GS7 - UNIT 3 - LESSON.docx", dest_dir / "GS7 - UNIT 3 - LESSON.docx")

    stats = import_global_success(db, tmp_path)
    db.commit()
    assert stats.chunks_written > 0
    return db.scalar(select(Unit).join(Grade).where(Grade.number == 7, Unit.order_no == 3))


def test_unauthenticated_cannot_search(client):
    response = client.get("/knowledge/search")

    assert response.status_code == 401


def test_teacher_can_search_by_unit(client, seeded_db, tmp_path):
    unit3 = _import_unit3_grade7(seeded_db, tmp_path)
    _login_as(client, seeded_db, "teacher-kb@examcraft.dev", UserRole.TEACHER)

    response = client.get("/knowledge/search", params={"unit_id": str(unit3.id), "limit": 100})

    assert response.status_code == 200
    chunks = response.json()
    assert len(chunks) > 0
    assert all(c["document"]["unit_id"] == str(unit3.id) for c in chunks)


def test_admin_can_search_too(client, seeded_db, tmp_path):
    unit3 = _import_unit3_grade7(seeded_db, tmp_path)
    _login_as(client, seeded_db, "admin-kb@examcraft.dev", UserRole.ADMIN)

    response = client.get("/knowledge/search", params={"unit_id": str(unit3.id)})

    assert response.status_code == 200


def test_search_by_query_finds_golden_reference_word(client, seeded_db, tmp_path):
    unit3 = _import_unit3_grade7(seeded_db, tmp_path)
    _login_as(client, seeded_db, "teacher-kb-search@examcraft.dev", UserRole.TEACHER)

    response = client.get("/knowledge/search", params={"unit_id": str(unit3.id), "q": "volunteer"})

    assert response.status_code == 200
    chunks = response.json()
    assert len(chunks) > 0
    assert any(c["structured"] and c["structured"].get("word") == "volunteer" for c in chunks)


def test_search_filters_by_chunk_type(client, seeded_db, tmp_path):
    unit3 = _import_unit3_grade7(seeded_db, tmp_path)
    _login_as(client, seeded_db, "teacher-kb-type@examcraft.dev", UserRole.TEACHER)

    response = client.get(
        "/knowledge/search", params={"unit_id": str(unit3.id), "chunk_type": "grammar", "limit": 100}
    )

    assert response.status_code == 200
    chunks = response.json()
    assert len(chunks) > 0
    assert all(c["chunk_type"] == "grammar" for c in chunks)
