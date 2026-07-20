"""Validation Engine (PRD mục 11). Chạy trên từng câu hỏi vừa sinh, trả về danh
sách cảnh báo — theo đúng nguyên tắc "cảnh báo, không chặn cứng" đã chốt xuyên
suốt đặc tả. Kiểm tra trùng lặp dùng fuzzy text-match kết hợp cosine embedding
(PRD 11, Giai đoạn 1D — quyết định #15 trước đây chỉ tạm dùng fuzzy vì chưa có
embedding). Embedding do caller tính sẵn (không tự gọi OpenAI ở đây) — giữ module
này không phụ thuộc trực tiếp SDK AI, và cho phép caller embed theo batch."""

import difflib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import ProficiencyLevel
from app.models.ai_config import AIProviderConfig
from app.models.exam import Question
from app.models.exercise import ExerciseType, PassageLengthRule, SentenceLengthRule
from app.services.ai_provider import QuestionDraft

WORD_COUNT_EXERCISE_TYPES = {"multiple_choice", "word_form"}
DUPLICATE_FUZZY_THRESHOLD = 0.85
DEFAULT_DUPLICATE_SIMILARITY_THRESHOLD = 0.90


def _duplicate_similarity_threshold(db: Session) -> float:
    config = db.scalar(select(AIProviderConfig).where(AIProviderConfig.is_active.is_(True)))
    return config.duplicate_similarity_threshold if config else DEFAULT_DUPLICATE_SIMILARITY_THRESHOLD


def _word_count(text: str) -> int:
    return len(text.split())


def validate_draft(
    db: Session,
    draft: QuestionDraft,
    *,
    exercise_type: ExerciseType,
    grade_number: int,
    school_stage_id: uuid.UUID,
    exam_level_rank: int,
    draft_embedding: list[float] | None = None,
) -> list[str]:
    warnings: list[str] = []

    if exercise_type.code in WORD_COUNT_EXERCISE_TYPES:
        rule = db.scalar(select(SentenceLengthRule).where(SentenceLengthRule.school_stage_id == school_stage_id))
        if rule:
            wc = _word_count(draft.prompt_text)
            if not (rule.min_words <= wc <= rule.max_words):
                warnings.append(
                    f"Câu hỏi dài {wc} từ, ngoài khoảng {rule.min_words}-{rule.max_words} từ khuyến nghị."
                )

    if exercise_type.has_passage and draft.passage_text:
        rule = db.scalar(
            select(PassageLengthRule).where(
                PassageLengthRule.grade_min <= grade_number,
                PassageLengthRule.grade_max >= grade_number,
            )
        )
        if rule:
            wc = _word_count(draft.passage_text)
            if not (rule.min_words <= wc <= rule.max_words):
                warnings.append(
                    f"Bài đọc dài {wc} từ, ngoài khoảng {rule.min_words}-{rule.max_words} từ khuyến nghị."
                )

    level = db.scalar(select(ProficiencyLevel).where(ProficiencyLevel.code == draft.level_code))
    if level is not None and level.rank > exam_level_rank:
        warnings.append(f"Kiến thức ở trình độ {level.code}, vượt trình độ mục tiêu của đề.")

    bank_prompts = db.scalars(select(Question.prompt_text).where(Question.is_in_bank.is_(True))).all()
    for existing in bank_prompts:
        ratio = difflib.SequenceMatcher(None, draft.prompt_text, existing).ratio()
        if ratio >= DUPLICATE_FUZZY_THRESHOLD:
            warnings.append(f"Có thể trùng câu trong ngân hàng (khớp {ratio:.0%} theo văn bản).")
            break

    if draft_embedding is not None:
        closest = db.execute(
            select(Question.embedding.cosine_distance(draft_embedding).label("distance"))
            .where(Question.is_in_bank.is_(True), Question.embedding.isnot(None))
            .order_by("distance")
            .limit(1)
        ).first()
        if closest is not None:
            similarity = 1 - closest.distance
            threshold = _duplicate_similarity_threshold(db)
            if similarity >= threshold:
                warnings.append(f"Có thể trùng câu trong ngân hàng (khớp {similarity:.0%} theo embedding).")

    return warnings
