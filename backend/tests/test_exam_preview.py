from decimal import Decimal
import uuid

import pytest
from sqlalchemy import select

import app.services.exam_preview as exam_preview
from app.models.academic import Grade, ProficiencyLevel, Unit
from app.models.exam import Exam, ExamBlock, ExamBlockPart, Question
from app.models.exercise import ExerciseType
from app.models.user import User, UserRole
from app.security import hash_password
from app.services.exam_preview import build_preview, to_roman


@pytest.fixture
def exam():
    return Exam()


@pytest.fixture
def exam_with_blocks():
    first = ExamBlock(
        order_no=1,
        title="Vocabulary",
        instruction="Choose the best answer.",
        question_count=2,
        points=Decimal("1.0"),
    )
    second = ExamBlock(
        order_no=2,
        title="Grammar",
        instruction=None,
        question_count=3,
        points=Decimal("2.0"),
    )
    return Exam(blocks=[second, first])


@pytest.fixture
def block_with_one_of_three_questions():
    question = Question(
        order_no=1,
        prompt_text="Choose the correct answer.",
        passage_text=None,
    )
    block = ExamBlock(
        order_no=1,
        title="Grammar",
        instruction=None,
        question_count=3,
        points=Decimal("3.0"),
        questions=[question],
    )
    Exam(blocks=[block])
    return block


@pytest.fixture
def long_exam():
    block = ExamBlock(
        order_no=1,
        title="Long practice",
        instruction=None,
        question_count=30,
        points=Decimal("4.0"),
    )
    return Exam(blocks=[block])


@pytest.fixture
def oversized_question_exam():
    question = Question(
        order_no=1,
        prompt_text="x" * 4000,
        passage_text=None,
    )
    block = ExamBlock(
        order_no=1,
        title="Long reading question",
        instruction=None,
        question_count=1,
        points=Decimal("1.0"),
        questions=[question],
    )
    return Exam(blocks=[block])


@pytest.fixture
def exam_with_block_starting_on_new_page():
    first = ExamBlock(
        order_no=1,
        title="First section",
        instruction=None,
        question_count=16,
        points=Decimal("1.0"),
    )
    second = ExamBlock(
        order_no=2,
        title="Second section",
        instruction=None,
        question_count=1,
        points=Decimal("1.0"),
    )
    return Exam(blocks=[first, second])


def test_empty_exam_has_one_empty_page(exam):
    preview = build_preview(exam)
    assert preview["total_questions"] == 0
    assert preview["total_points"] == Decimal("0.0")
    assert preview["page_count"] == 1
    assert preview["pages"] == [{"page_number": 1, "blocks": []}]


def test_placeholders_are_numbered_across_blocks(exam_with_blocks):
    preview = build_preview(exam_with_blocks)
    first, second = preview["pages"][0]["blocks"]
    assert (first["section_label"], first["question_start"], first["question_end"]) == ("I", 1, 2)
    assert (second["section_label"], second["question_start"], second["question_end"]) == ("II", 3, 5)
    assert [question["question_number"] for question in second["questions"]] == [3, 4, 5]
    assert all(question["is_placeholder"] for question in first["questions"] + second["questions"])


def test_actual_questions_are_preserved_and_missing_questions_are_filled(block_with_one_of_three_questions):
    preview = build_preview(block_with_one_of_three_questions.exam)
    questions = preview["pages"][0]["blocks"][0]["questions"]
    assert questions[0]["prompt_text"] == "Choose the correct answer."
    assert [question["is_placeholder"] for question in questions] == [False, True, True]


def test_actual_questions_beyond_configured_count_are_preserved():
    block = ExamBlock(
        order_no=1,
        title="Stored questions",
        instruction=None,
        question_count=1,
        points=Decimal("1.0"),
        questions=[
            Question(order_no=2, prompt_text="Second stored question", passage_text=None),
            Question(order_no=1, prompt_text="First stored question", passage_text=None),
        ],
    )

    preview = build_preview(Exam(blocks=[block]))
    questions = preview["pages"][0]["blocks"][0]["questions"]

    assert preview["total_questions"] == 2
    assert [question["prompt_text"] for question in questions] == [
        "First stored question",
        "Second stored question",
    ]
    assert all(question["is_placeholder"] is False for question in questions)


def test_to_roman_supports_more_than_twenty():
    assert to_roman(24) == "XXIV"


def test_preview_carries_part_number_and_title_for_questions_in_a_part():
    part1 = ExamBlockPart(order_no=1, title="So sánh kép", instruction=None, question_count=1)
    part2 = ExamBlockPart(order_no=2, title="Cụm động từ", instruction="Rewrite using phrasal verbs.", question_count=1)
    block = ExamBlock(
        order_no=1,
        title="Transformation Patterns",
        instruction=None,
        question_count=2,
        points=Decimal("2.0"),
        questions=[
            Question(order_no=1, prompt_text="Q1", passage_text=None, part=part1),
            Question(order_no=2, prompt_text="Q2", passage_text=None, part=part2),
        ],
    )

    preview = build_preview(Exam(blocks=[block]))
    questions = preview["pages"][0]["blocks"][0]["questions"]

    assert questions[0]["part_number"] == 1
    assert questions[0]["part_title"] == "So sánh kép"
    assert questions[1]["part_number"] == 2
    assert questions[1]["part_title"] == "Cụm động từ"
    assert questions[1]["part_instruction"] == "Rewrite using phrasal verbs."


def test_question_line_estimate_adds_lines_when_part_changes():
    question = {
        "is_placeholder": False,
        "prompt_text": "x" * 10,
        "passage_text": None,
        "part_number": 2,
        "part_title": "Cụm động từ",
        "part_instruction": None,
    }
    without_part_change = exam_preview._question_lines(question, previous_passage=None, previous_part_number=2)
    with_part_change = exam_preview._question_lines(question, previous_passage=None, previous_part_number=1)
    assert with_part_change == without_part_change + 2


def test_long_block_splits_between_questions(long_exam):
    preview = build_preview(long_exam)
    assert preview["page_count"] >= 2
    first_piece = preview["pages"][0]["blocks"][0]
    second_piece = preview["pages"][1]["blocks"][0]
    assert first_piece["continuation"] is False
    assert second_piece["continuation"] is True
    assert second_piece["question_start"] == first_piece["question_end"] + 1


def test_single_oversized_question_terminates(oversized_question_exam):
    preview = build_preview(oversized_question_exam)
    assert preview["page_count"] <= 2
    assert sum(len(piece["questions"]) for page in preview["pages"] for piece in page["blocks"]) == 1


def test_block_that_starts_on_a_new_page_is_not_a_continuation(exam_with_block_starting_on_new_page):
    preview = build_preview(exam_with_block_starting_on_new_page)
    assert preview["pages"][1]["blocks"][0]["continuation"] is False


def test_question_line_estimate_counts_a_repeated_passage_once():
    question = {
        "is_placeholder": False,
        "prompt_text": "x" * 91,
        "passage_text": "p" * 91,
    }
    assert hasattr(exam_preview, "_question_lines")
    assert exam_preview._question_lines(question, previous_passage=None) == 6
    assert exam_preview._question_lines(question, previous_passage="p" * 91) == 4


def test_preview_preserves_decimal_total_points_when_paginated(long_exam):
    preview = build_preview(long_exam)
    assert preview["total_points"] == Decimal("4.0")


def _login(client, db, email):
    user = User(
        email=email,
        password_hash=hash_password("Secret123!"),
        full_name=email,
        role=UserRole.TEACHER,
    )
    db.add(user)
    db.commit()
    assert client.post("/auth/login", json={"email": email, "password": "Secret123!"}).status_code == 200
    return user


def _create_exam_with_blocks(client, db):
    grade = db.scalar(select(Grade).where(Grade.number == 7))
    level = db.scalar(select(ProficiencyLevel).where(ProficiencyLevel.code == "A2"))
    unit = db.scalar(select(Unit).where(Unit.grade_id == grade.id, Unit.order_no == 3))
    exam = client.post(
        "/exams",
        json={
            "title": "Preview exam",
            "grade_id": str(grade.id),
            "level_id": str(level.id),
            "source_type": "global_success",
            "unit_id": str(unit.id),
        },
    ).json()
    exercise_type = db.scalar(select(ExerciseType).where(ExerciseType.code == "multiple_choice"))
    assert (
        client.post(
            f"/exams/{exam['id']}/blocks",
            json={
                "exercise_type_id": str(exercise_type.id),
                "title": "Grammar",
                "question_count": 3,
                "points": "2.0",
            },
        ).status_code
        == 201
    )
    return exam


def test_preview_endpoint_returns_typed_payload(client, seeded_db):
    _login(client, seeded_db, "preview-owner@examcraft.dev")
    exam = _create_exam_with_blocks(client, seeded_db)

    response = client.get(f"/exams/{exam['id']}/preview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["exam_id"] == exam["id"]
    assert payload["title"] == "Preview exam"
    assert payload["total_questions"] == 3
    assert payload["total_points"] == "2.0"
    assert payload["page_count"] == len(payload["pages"])
    assert payload["pages"] == [
        {
            "page_number": 1,
            "blocks": [
                {
                    "block_id": payload["pages"][0]["blocks"][0]["block_id"],
                    "section_number": 1,
                    "section_label": "I",
                    "title": "Grammar",
                    "instruction": None,
                    "question_start": 1,
                    "question_end": 3,
                    "question_count": 3,
                    "points": "2.0",
                    "continuation": False,
                    "questions": [
                        {
                            "question_number": number,
                            "prompt_text": None,
                            "passage_text": None,
                            "is_placeholder": True,
                            "part_number": None,
                            "part_title": None,
                            "part_instruction": None,
                        }
                        for number in range(1, 4)
                    ],
                }
            ],
        }
    ]
    assert uuid.UUID(payload["pages"][0]["blocks"][0]["block_id"])


def test_preview_requires_owner(client, seeded_db):
    _login(client, seeded_db, "preview-owner@examcraft.dev")
    exam = _create_exam_with_blocks(client, seeded_db)
    client.post("/auth/logout")
    _login(client, seeded_db, "preview-other@examcraft.dev")

    assert client.get(f"/exams/{exam['id']}/preview").status_code == 403


def test_preview_requires_login(client, seeded_db):
    assert client.get(f"/exams/{uuid.uuid4()}/preview").status_code == 401


def test_preview_returns_not_found_for_missing_exam(client, seeded_db):
    _login(client, seeded_db, "preview-owner@examcraft.dev")

    assert client.get(f"/exams/{uuid.uuid4()}/preview").status_code == 404
