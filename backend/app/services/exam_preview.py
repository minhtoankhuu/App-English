import math
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

PAGE_LINES = 42
FOOTER_LINES = 2
FIRST_PAGE_HEADER_LINES = 5
CONTINUED_PAGE_HEADER_LINES = 2


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


def _question_lines(question: dict[str, object], previous_passage: str | None) -> int:
    if question["is_placeholder"]:
        return 2

    prompt = str(question["prompt_text"] or "")
    passage = question["passage_text"]
    lines = 2 + math.ceil(len(prompt) / 90)
    if passage and passage != previous_passage:
        lines += math.ceil(len(str(passage)) / 90)
    return lines


def _block_header_lines(block: dict[str, object]) -> int:
    return 2 + int(bool(block["instruction"]))


def _paginate(blocks: list[dict[str, object]]) -> list[dict[str, object]]:
    content_capacity = PAGE_LINES - FOOTER_LINES
    pages: list[dict[str, object]] = [{"page_number": 1, "blocks": []}]
    used_lines = FIRST_PAGE_HEADER_LINES

    def start_page() -> dict[str, object]:
        nonlocal used_lines
        page = {"page_number": len(pages) + 1, "blocks": []}
        pages.append(page)
        used_lines = CONTINUED_PAGE_HEADER_LINES
        return page

    page = pages[0]
    for block in blocks:
        questions = list(block["questions"])
        block_header = _block_header_lines(block)

        if not questions:
            if page["blocks"] and used_lines + block_header > content_capacity:
                page = start_page()
            page["blocks"].append(
                {
                    **block,
                    "continuation": False,
                    "question_start": None,
                    "question_end": None,
                    "questions": [],
                }
            )
            used_lines += block_header
            continue

        question_index = 0
        continuation = False
        while question_index < len(questions):
            first_question = questions[question_index]
            first_question_lines = _question_lines(first_question, previous_passage=None)
            if page["blocks"] and used_lines + block_header + first_question_lines > content_capacity:
                page = start_page()

            piece: dict[str, object] = {
                **block,
                "continuation": continuation,
                "question_start": None,
                "question_end": None,
                "questions": [],
            }
            page["blocks"].append(piece)
            used_lines += block_header
            previous_passage: str | None = None

            while question_index < len(questions):
                question = questions[question_index]
                question_lines = _question_lines(question, previous_passage)
                piece_questions = piece["questions"]
                if used_lines + question_lines > content_capacity and piece_questions:
                    page = start_page()
                    continuation = True
                    break

                piece_questions.append(question)
                question_number = question["question_number"]
                if piece["question_start"] is None:
                    piece["question_start"] = question_number
                piece["question_end"] = question_number
                used_lines += question_lines
                previous_passage = question["passage_text"]
                question_index += 1

    return pages


def build_preview(exam: Exam) -> dict[str, object]:
    blocks: list[dict[str, object]] = []
    next_number = 1
    total_points = Decimal("0.0")

    for index, block in enumerate(sorted(exam.blocks, key=lambda candidate: candidate.order_no), start=1):
        questions, next_number = _preview_questions(block, next_number)
        total_points += block.points
        blocks.append(
            {
                "block_id": block.id,
                "section_number": index,
                "section_label": to_roman(index),
                "title": block.title,
                "instruction": block.instruction,
                "points": block.points,
                "question_start": questions[0]["question_number"] if questions else None,
                "question_end": questions[-1]["question_number"] if questions else None,
                "question_count": block.question_count,
                "questions": questions,
            }
        )

    pages = _paginate(blocks)
    return {
        "total_questions": next_number - 1,
        "total_points": total_points,
        "page_count": len(pages),
        "pages": pages,
    }
