"""Điều phối sinh câu hỏi: gọi AIProvider rồi chạy Validation Engine trên từng câu,
lưu kết quả vào DB. Tách khỏi router để router chỉ lo HTTP, còn logic nghiệp vụ
nằm ở đây và test được độc lập."""

import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import Grade, ProficiencyLevel, Unit
from app.models.exam import Exam, ExamBlock, Question
from app.models.exercise import ExerciseType
from app.services.ai_provider import AIProvider, BlockSpec, GenerationContext, MockAIProvider
from app.services.validation import validate_draft

_provider: AIProvider = MockAIProvider()


def _build_context(db: Session, exam: Exam, grade: Grade) -> GenerationContext:
    unit_title = None
    unit_order_no = None
    if exam.unit_id:
        unit = db.get(Unit, exam.unit_id)
        if unit:
            unit_title = unit.title
            unit_order_no = unit.order_no
    exam_level = db.get(ProficiencyLevel, exam.level_id)
    return GenerationContext(
        grade_number=grade.number,
        school_stage_code=grade.school_stage.code if grade.school_stage else "",
        exam_level_code=exam_level.code if exam_level else "",
        unit_title=unit_title,
        unit_order_no=unit_order_no,
    )


def _effective_level(db: Session, exam: Exam, block: ExamBlock) -> ProficiencyLevel:
    if block.level_override_id:
        override = db.get(ProficiencyLevel, block.level_override_id)
        if override:
            return override
    return db.get(ProficiencyLevel, exam.level_id)


def generate_block_questions(db: Session, exam: Exam, block: ExamBlock) -> list[Question]:
    """Xoá toàn bộ câu chưa khóa của block rồi sinh mới đủ question_count."""
    exercise_type = db.get(ExerciseType, block.exercise_type_id)
    grade = db.get(Grade, exam.grade_id)
    exam_level = db.get(ProficiencyLevel, exam.level_id)
    effective_level = _effective_level(db, exam, block)
    context = _build_context(db, exam, grade)

    for existing in list(block.questions):
        if not existing.is_locked:
            db.delete(existing)
    db.flush()

    spec = BlockSpec(
        exercise_type_code=exercise_type.code,
        question_count=block.question_count,
        level_code=effective_level.code,
        passage_word_target=block.passage_word_target,
        prompt_override=block.prompt_override,
    )
    drafts = _provider.generate(spec, context)

    locked_orders = {q.order_no for q in block.questions if q.is_locked}
    order_no = 0
    created: list[Question] = []
    for draft in drafts:
        order_no += 1
        while order_no in locked_orders:
            order_no += 1
        level = db.scalar(select(ProficiencyLevel).where(ProficiencyLevel.code == draft.level_code)) or exam_level
        warnings = validate_draft(
            db,
            draft,
            exercise_type=exercise_type,
            grade_number=grade.number,
            school_stage_id=grade.school_stage_id,
            exam_level_rank=exam_level.rank,
        )
        question = Question(
            block_id=block.id,
            order_no=order_no,
            prompt_text=draft.prompt_text,
            passage_text=draft.passage_text,
            options=draft.options,
            answer_text=draft.answer_text,
            explanation=draft.explanation,
            target_knowledge=draft.target_knowledge,
            level_id=level.id,
            source_ref=draft.source_ref,
            warnings=warnings,
        )
        db.add(question)
        created.append(question)
    return created


def regenerate_question(db: Session, exam: Exam, block: ExamBlock, question: Question) -> None:
    exercise_type = db.get(ExerciseType, block.exercise_type_id)
    grade = db.get(Grade, exam.grade_id)
    exam_level = db.get(ProficiencyLevel, exam.level_id)
    effective_level = _effective_level(db, exam, block)
    context = _build_context(db, exam, grade)
    spec = BlockSpec(
        exercise_type_code=exercise_type.code,
        question_count=1,
        level_code=effective_level.code,
        passage_word_target=block.passage_word_target,
        prompt_override=block.prompt_override,
    )
    draft = _provider.regenerate_one(spec, context, exclude_prompt=question.prompt_text)
    level = db.scalar(select(ProficiencyLevel).where(ProficiencyLevel.code == draft.level_code)) or exam_level
    warnings = validate_draft(
        db,
        draft,
        exercise_type=exercise_type,
        grade_number=grade.number,
        school_stage_id=grade.school_stage_id,
        exam_level_rank=exam_level.rank,
    )

    question.prompt_text = draft.prompt_text
    question.passage_text = draft.passage_text
    question.options = draft.options
    question.answer_text = draft.answer_text
    question.explanation = draft.explanation
    question.target_knowledge = draft.target_knowledge
    question.level_id = level.id
    question.source_ref = draft.source_ref
    question.warnings = warnings
    question.is_approved = False


def shuffle_variant(exam: Exam, seed: int) -> dict:
    """Đảo thứ tự câu trong mỗi block theo shuffle_questions của block.
    Không tách nhóm câu dùng chung ngữ cảnh (đoạn đọc) — đảo trong phạm vi 1 block (PRD 13)."""
    rng = random.Random(seed)
    order: dict[str, list[str]] = {}
    for block in exam.blocks:
        question_ids = [str(q.id) for q in sorted(block.questions, key=lambda q: q.order_no)]
        if block.shuffle_questions:
            rng.shuffle(question_ids)
        order[str(block.id)] = question_ids
    return order
