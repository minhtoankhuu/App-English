import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.exam import Difficulty, ExamStatus, ExportMode, SourceType


class ExamCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    grade_id: uuid.UUID
    level_id: uuid.UUID
    source_type: SourceType
    unit_id: uuid.UUID | None = None
    grammar_topic_id: uuid.UUID | None = None
    cambridge_certificate_id: uuid.UUID | None = None
    extra_prompt: str | None = None


class ExamUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    grade_id: uuid.UUID | None = None
    level_id: uuid.UUID | None = None
    source_type: SourceType | None = None
    unit_id: uuid.UUID | None = None
    grammar_topic_id: uuid.UUID | None = None
    cambridge_certificate_id: uuid.UUID | None = None
    extra_prompt: str | None = None


class GrammarSelectionRequest(BaseModel):
    grammar_point_ids: list[uuid.UUID]


class BlockCreateRequest(BaseModel):
    exercise_type_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    instruction: str | None = None
    question_count: int = Field(ge=1, le=50)
    points: Decimal = Field(ge=0, le=10)
    difficulty: Difficulty = Difficulty.HON_HOP
    level_override_id: uuid.UUID | None = None
    shuffle_questions: bool = True
    shuffle_answers: bool = True
    prompt_override: str | None = None
    passage_word_target: int | None = Field(default=None, ge=10, le=500)


class BlockUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    instruction: str | None = None
    question_count: int | None = Field(default=None, ge=1, le=50)
    points: Decimal | None = Field(default=None, ge=0, le=10)
    difficulty: Difficulty | None = None
    level_override_id: uuid.UUID | None = None
    shuffle_questions: bool | None = None
    shuffle_answers: bool | None = None
    prompt_override: str | None = None
    passage_word_target: int | None = Field(default=None, ge=10, le=500)


class BlockReorderRequest(BaseModel):
    block_ids: list[uuid.UUID]


class BlockPartCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    instruction: str | None = None
    question_count: int = Field(ge=1, le=50)
    prompt_override: str | None = None


class BlockPartUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    instruction: str | None = None
    question_count: int | None = Field(default=None, ge=1, le=50)
    prompt_override: str | None = None


class BlockPartReorderRequest(BaseModel):
    part_ids: list[uuid.UUID]


class QuestionFlagsUpdateRequest(BaseModel):
    is_approved: bool | None = None
    is_locked: bool | None = None


class ExportConfigRequest(BaseModel):
    export_mode: ExportMode
    variant_count: int = Field(ge=1, le=4)


class RefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_no: int
    prompt_text: str
    passage_text: str | None
    options: list[dict[str, Any]] | None
    answer_text: str
    explanation: str
    target_knowledge: str
    level: RefOut
    source_ref: str
    warnings: list[str]
    is_approved: bool
    is_locked: bool
    part_id: uuid.UUID | None


class ExerciseTypeRefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    has_passage: bool


class BlockPartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_no: int
    title: str
    instruction: str | None
    question_count: int
    prompt_override: str | None


class BlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_no: int
    exercise_type: ExerciseTypeRefOut
    title: str
    instruction: str | None
    question_count: int
    points: Decimal
    difficulty: Difficulty
    level_override: RefOut | None
    shuffle_questions: bool
    shuffle_answers: bool
    prompt_override: str | None
    passage_word_target: int | None
    questions: list[QuestionOut]
    parts: list[BlockPartOut]


class ExamSummaryOut(BaseModel):
    id: uuid.UUID
    title: str
    status: ExamStatus
    grade_number: int
    level_code: str
    total_questions: int
    total_points: Decimal
    export_mode: ExportMode | None
    variant_count: int
    updated_at: Any


class ExamDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: ExamStatus
    source_type: SourceType
    grade_id: uuid.UUID
    level: RefOut
    unit_id: uuid.UUID | None
    grammar_topic_id: uuid.UUID | None
    cambridge_certificate_id: uuid.UUID | None
    extra_prompt: str | None
    export_mode: ExportMode | None
    variant_count: int
    grammar_point_ids: list[uuid.UUID]
    blocks: list[BlockOut]


class VariantOut(BaseModel):
    code: str
    seed: int
