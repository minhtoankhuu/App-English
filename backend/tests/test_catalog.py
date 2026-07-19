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


def test_grades_seeded_and_suggest_correct_level(client, seeded_db):
    _login_as_teacher(client, seeded_db)

    response = client.get("/catalog/grades")

    assert response.status_code == 200
    grades = {g["number"]: g for g in response.json()}
    assert len(grades) == 12
    assert grades[7]["school_stage"]["code"] == "secondary"
    assert grades[7]["suggested_level"]["code"] == "A2"
    assert grades[10]["suggested_level"]["code"] == "B2"


def test_units_for_grade_ordered_and_matches_golden_reference(client, seeded_db):
    _login_as_teacher(client, seeded_db)
    grade7_id = next(g["id"] for g in client.get("/catalog/grades").json() if g["number"] == 7)

    response = client.get(f"/catalog/grades/{grade7_id}/units")

    assert response.status_code == 200
    units = response.json()
    assert len(units) == 12
    assert units[0] == {"id": units[0]["id"], "order_no": 1, "title": "Hobbies"}
    assert units[2]["title"] == "Community Service"  # golden test reference (PRD)


def test_units_for_unknown_grade_returns_404(client, seeded_db):
    _login_as_teacher(client, seeded_db)

    response = client.get("/catalog/grades/00000000-0000-0000-0000-000000000000/units")

    assert response.status_code == 404


def test_grammar_topics_counts(client, seeded_db):
    _login_as_teacher(client, seeded_db)

    response = client.get("/catalog/grammar-topics")

    assert response.status_code == 200
    topics = {t["code"]: t for t in response.json()}
    assert sum(len(g["points"]) for g in topics["tense"]["groups"]) == 12
    assert sum(len(g["points"]) for g in topics["sentence_structure"]["groups"]) == 20


def test_exercise_types_flag_passage(client, seeded_db):
    _login_as_teacher(client, seeded_db)

    response = client.get("/catalog/exercise-types")

    assert response.status_code == 200
    by_code = {e["code"]: e for e in response.json()}
    assert len(by_code) == 10
    assert by_code["cloze_test"]["has_passage"] is True
    assert by_code["reading_true_false"]["has_passage"] is True
    assert by_code["multiple_choice"]["has_passage"] is False


def test_sentence_length_rules(client, seeded_db):
    _login_as_teacher(client, seeded_db)

    response = client.get("/catalog/sentence-length-rules")

    assert response.status_code == 200
    by_stage = {r["school_stage"]["code"]: r for r in response.json()}
    assert by_stage["secondary"]["min_words"] == 12
    assert by_stage["secondary"]["max_words"] == 14
    assert by_stage["secondary"]["is_confirmed"] is True
    assert by_stage["primary"]["is_confirmed"] is False


def test_passage_length_rules(client, seeded_db):
    _login_as_teacher(client, seeded_db)

    response = client.get("/catalog/passage-length-rules")

    assert response.status_code == 200
    rules = response.json()
    assert len(rules) == 5
    match = next(r for r in rules if r["grade_min"] == 6 and r["grade_max"] == 7)
    assert (match["min_words"], match["max_words"]) == (80, 150)


def test_cambridge_certificates_map_to_cefr(client, seeded_db):
    _login_as_teacher(client, seeded_db)

    response = client.get("/catalog/cambridge-certificates")

    assert response.status_code == 200
    by_code = {c["code"]: c["cefr_level"]["code"] for c in response.json()}
    assert by_code == {"Starters": "A1", "Movers": "A1", "Flyers": "A2", "KET": "B1", "PET": "B2"}
