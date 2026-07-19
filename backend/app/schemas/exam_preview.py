import uuid
from decimal import Decimal

from pydantic import BaseModel


class PreviewQuestionOut(BaseModel):
    question_number: int
    prompt_text: str | None
    passage_text: str | None
    is_placeholder: bool


class PreviewBlockOut(BaseModel):
    block_id: uuid.UUID
    section_number: int
    section_label: str
    title: str
    instruction: str | None
    question_start: int | None
    question_end: int | None
    question_count: int
    points: Decimal
    continuation: bool
    questions: list[PreviewQuestionOut]


class PreviewPageOut(BaseModel):
    page_number: int
    blocks: list[PreviewBlockOut]


class ExamPreviewOut(BaseModel):
    exam_id: uuid.UUID
    title: str
    total_questions: int
    total_points: Decimal
    page_count: int
    pages: list[PreviewPageOut]
