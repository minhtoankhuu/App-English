from decimal import Decimal

from app.models.exam import Exam, ExamBlock


ROMAN_NUMERALS = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)


def to_roman(value: int) -> str:
    if value <= 0:
        raise ValueError("value must be positive")

    parts: list[str] = []
    for number, symbol in ROMAN_NUMERALS:
        while value >= number:
            parts.append(symbol)
            value -= number
    return "".join(parts)


def _preview_questions(block: ExamBlock, next_number: int) -> tuple[list[dict[str, object]], int]:
    actual = sorted(block.questions, key=lambda question: question.order_no)
    count = max(block.question_count, len(actual))
    items: list[dict[str, object]] = []

    for index in range(count):
        question = actual[index] if index < len(actual) else None
        items.append(
            {
                "question_number": next_number,
                "prompt_text": question.prompt_text if question else None,
                "passage_text": question.passage_text if question else None,
                "is_placeholder": question is None,
            }
        )
        next_number += 1

    return items, next_number


def build_preview(exam: Exam) -> dict[str, object]:
    blocks: list[dict[str, object]] = []
    next_number = 1
    total_points = Decimal("0.0")

    for index, block in enumerate(sorted(exam.blocks, key=lambda candidate: candidate.order_no), start=1):
        questions, next_number = _preview_questions(block, next_number)
        total_points += block.points
        blocks.append(
            {
                "section_label": to_roman(index),
                "title": block.title,
                "instruction": block.instruction,
                "points": block.points,
                "question_start": questions[0]["question_number"] if questions else None,
                "question_end": questions[-1]["question_number"] if questions else None,
                "questions": questions,
            }
        )

    return {
        "total_questions": next_number - 1,
        "total_points": total_points,
        "page_count": 1,
        "pages": [{"page_number": 1, "blocks": blocks}],
    }
