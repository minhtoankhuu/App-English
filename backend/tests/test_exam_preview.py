from decimal import Decimal

import pytest

import app.services.exam_preview as exam_preview
from app.models.exam import Exam, ExamBlock, Question
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


def test_to_roman_supports_more_than_twenty():
    assert to_roman(24) == "XXIV"


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
