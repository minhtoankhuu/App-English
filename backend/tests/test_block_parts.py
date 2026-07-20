import io

from docx import Document
from sqlalchemy import select

from app.models.academic import Grade, ProficiencyLevel, Unit
from app.models.exercise import ExerciseType
from app.models.user import User, UserRole
from app.security import hash_password


def _login_as_teacher(client, db):
    user = User(
        email="teacher@examcraft.dev",
        password_hash=hash_password("Secret123!"),
        full_name="Teacher",
        role=UserRole.TEACHER,
    )
    db.add(user)
    db.commit()
    response = client.post("/auth/login", json={"email": "teacher@examcraft.dev", "password": "Secret123!"})
    assert response.status_code == 200
    return user


def _grade7_unit3(db):
    grade7 = db.scalar(select(Grade).where(Grade.number == 7))
    unit3 = db.scalar(select(Unit).where(Unit.grade_id == grade7.id, Unit.order_no == 3))
    return grade7, unit3


def _level(db, code):
    return db.scalar(select(ProficiencyLevel).where(ProficiencyLevel.code == code))


def _exercise_type(db, code):
    return db.scalar(select(ExerciseType).where(ExerciseType.code == code))


def _create_exam(client, db):
    grade7, unit3 = _grade7_unit3(db)
    level_a2 = _level(db, "A2")
    resp = client.post(
        "/exams",
        json={
            "title": "Unit 2 Revision",
            "grade_id": str(grade7.id),
            "level_id": str(level_a2.id),
            "source_type": "global_success",
            "unit_id": str(unit3.id),
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _create_block(client, db, exam_id, code="sentence_rewrite", title="IV. Transformation Patterns"):
    ex_type = _exercise_type(db, code)
    resp = client.post(
        f"/exams/{exam_id}/blocks",
        json={"exercise_type_id": str(ex_type.id), "title": title, "question_count": 1, "points": "3.0"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_add_part_syncs_block_question_count(client, seeded_db):
    _login_as_teacher(client, seeded_db)
    exam = _create_exam(client, seeded_db)
    block = _create_block(client, seeded_db, exam["id"])

    resp = client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts",
        json={"title": "So sánh kép", "question_count": 5},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert len(body["parts"]) == 1
    assert body["parts"][0]["order_no"] == 1
    assert body["question_count"] == 5

    resp = client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts",
        json={"title": "Cụm động từ", "question_count": 3},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body["parts"]) == 2
    assert body["parts"][1]["order_no"] == 2
    assert body["question_count"] == 8


def test_update_part_resyncs_question_count(client, seeded_db):
    _login_as_teacher(client, seeded_db)
    exam = _create_exam(client, seeded_db)
    block = _create_block(client, seeded_db, exam["id"])
    part = client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts",
        json={"title": "So sánh kép", "question_count": 5},
    ).json()["parts"][0]

    resp = client.patch(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts/{part['id']}",
        json={"question_count": 10},
    )
    assert resp.status_code == 200
    assert resp.json()["question_count"] == 10


def test_delete_part_resyncs_question_count_and_keeps_last_total(client, seeded_db):
    _login_as_teacher(client, seeded_db)
    exam = _create_exam(client, seeded_db)
    block = _create_block(client, seeded_db, exam["id"])
    p1 = client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts",
        json={"title": "Phần 1", "question_count": 5},
    ).json()["parts"][0]
    p2 = client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts",
        json={"title": "Phần 2", "question_count": 3},
    ).json()["parts"][1]

    resp = client.delete(f"/exams/{exam['id']}/blocks/{block['id']}/parts/{p1['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["parts"]) == 1
    assert body["parts"][0]["id"] == p2["id"]
    assert body["question_count"] == 3

    # xoá hết phần con -> question_count giữ nguyên giá trị cuối, không reset về 0
    resp = client.delete(f"/exams/{exam['id']}/blocks/{block['id']}/parts/{p2['id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["parts"] == []
    assert body["question_count"] == 3


def test_direct_question_count_update_ignored_when_block_has_parts(client, seeded_db):
    _login_as_teacher(client, seeded_db)
    exam = _create_exam(client, seeded_db)
    block = _create_block(client, seeded_db, exam["id"])
    client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts",
        json={"title": "Phần 1", "question_count": 5},
    )

    resp = client.patch(f"/exams/{exam['id']}/blocks/{block['id']}", json={"question_count": 40, "points": "4.0"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["question_count"] == 5
    assert body["points"] == "4.0"


def test_reorder_parts(client, seeded_db):
    _login_as_teacher(client, seeded_db)
    exam = _create_exam(client, seeded_db)
    block = _create_block(client, seeded_db, exam["id"])
    p1 = client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts", json={"title": "Phần 1", "question_count": 2}
    ).json()["parts"][0]
    p2 = client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts", json={"title": "Phần 2", "question_count": 2}
    ).json()["parts"][1]

    resp = client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts/reorder", json={"part_ids": [p2["id"], p1["id"]]}
    )
    assert resp.status_code == 200
    parts = sorted(resp.json()["parts"], key=lambda p: p["order_no"])
    assert parts[0]["id"] == p2["id"]
    assert parts[1]["id"] == p1["id"]


def test_part_not_found_returns_404(client, seeded_db):
    _login_as_teacher(client, seeded_db)
    exam = _create_exam(client, seeded_db)
    block = _create_block(client, seeded_db, exam["id"])

    resp = client.patch(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts/00000000-0000-0000-0000-000000000000",
        json={"title": "x"},
    )
    assert resp.status_code == 404


def test_other_teacher_cannot_manage_parts(client, seeded_db):
    _login_as_teacher(client, seeded_db)
    exam = _create_exam(client, seeded_db)
    block = _create_block(client, seeded_db, exam["id"])

    other = User(
        email="other-parts@examcraft.dev",
        password_hash=hash_password("Secret123!"),
        full_name="Other",
        role=UserRole.TEACHER,
    )
    seeded_db.add(other)
    seeded_db.commit()
    client.post("/auth/logout")
    client.post("/auth/login", json={"email": "other-parts@examcraft.dev", "password": "Secret123!"})

    resp = client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts", json={"title": "Phần 1", "question_count": 2}
    )
    assert resp.status_code == 403


def test_generate_assigns_questions_to_correct_part(client, seeded_db):
    _login_as_teacher(client, seeded_db)
    exam = _create_exam(client, seeded_db)
    block = _create_block(client, seeded_db, exam["id"])
    p1 = client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts",
        json={"title": "So sánh kép", "question_count": 2},
    ).json()["parts"][0]
    p2 = client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts",
        json={"title": "Cụm động từ", "question_count": 3},
    ).json()["parts"][1]

    resp = client.post(f"/exams/{exam['id']}/generate")
    assert resp.status_code == 200
    detail = resp.json()
    block_detail = next(b for b in detail["blocks"] if b["id"] == block["id"])
    questions = block_detail["questions"]
    assert len(questions) == 5

    part1_questions = [q for q in questions if q["part_id"] == p1["id"]]
    part2_questions = [q for q in questions if q["part_id"] == p2["id"]]
    assert len(part1_questions) == 2
    assert len(part2_questions) == 3


def test_generate_block_without_parts_leaves_part_id_null(client, seeded_db):
    _login_as_teacher(client, seeded_db)
    exam = _create_exam(client, seeded_db)
    block = _create_block(client, seeded_db, exam["id"], code="multiple_choice", title="II")
    client.patch(f"/exams/{exam['id']}/blocks/{block['id']}", json={"question_count": 3})

    resp = client.post(f"/exams/{exam['id']}/generate")
    assert resp.status_code == 200
    detail = resp.json()
    block_detail = next(b for b in detail["blocks"] if b["id"] == block["id"])
    assert all(q["part_id"] is None for q in block_detail["questions"])


def test_docx_export_prints_part_headings(client, seeded_db):
    _login_as_teacher(client, seeded_db)
    exam = _create_exam(client, seeded_db)
    block = _create_block(client, seeded_db, exam["id"])
    client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts",
        json={"title": "So sánh kép", "question_count": 1},
    )
    client.post(
        f"/exams/{exam['id']}/blocks/{block['id']}/parts",
        json={"title": "Cụm động từ", "question_count": 1, "instruction": "Rewrite using phrasal verbs."},
    )
    client.post(f"/exams/{exam['id']}/generate")
    resp = client.post(f"/exams/{exam['id']}/complete-review")
    assert resp.status_code in (200, 409)
    if resp.status_code == 409:
        detail = client.get(f"/exams/{exam['id']}").json()
        for b in detail["blocks"]:
            for q in b["questions"]:
                client.patch(f"/exams/{exam['id']}/questions/{q['id']}", json={"is_approved": True})
        resp = client.post(f"/exams/{exam['id']}/complete-review")
        assert resp.status_code == 200

    resp = client.post(f"/exams/{exam['id']}/export-config", json={"export_mode": "plain", "variant_count": 1})
    assert resp.status_code == 200

    resp = client.get(f"/exams/{exam['id']}/export.docx", params={"variant": "A"})
    assert resp.status_code == 200
    doc = Document(io.BytesIO(resp.content))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "1. So sánh kép" in full_text
    assert "2. Cụm động từ" in full_text
    assert "Rewrite using phrasal verbs." in full_text
