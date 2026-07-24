import math

from sqlalchemy import select

from app.models.academic import Grade, ProficiencyLevel
from app.models.ai_config import AIProviderConfig
from app.models.exam import Exam, ExamBlock, Question, SourceType
from app.models.exercise import ExerciseType
from app.models.knowledge import EMBEDDING_DIM
from app.models.user import User, UserRole
from app.security import hash_password
from app.services.ai_provider import QuestionDraft
from app.services.crypto import encrypt_api_key
from app.services.validation import validate_draft


def _exercise_type(db, code="multiple_choice") -> ExerciseType:
    return db.scalar(select(ExerciseType).where(ExerciseType.code == code))


def _vector(first_dim: float) -> list[float]:
    return [first_dim] + [0.0] * (EMBEDDING_DIM - 1)


def _base_vector() -> list[float]:
    return [1.0] + [0.0] * (EMBEDDING_DIM - 1)


def _vector_with_cosine_similarity(cosine_sim: float) -> list[float]:
    """Vector (đã chuẩn hóa) có cosine similarity đúng bằng `cosine_sim` so với
    `_base_vector()` — cosine similarity không đổi theo độ dài vector, chỉ theo góc,
    nên cần dựng vector lệch góc thật thay vì chỉ đổi độ lớn."""
    sin_component = math.sqrt(max(0.0, 1 - cosine_sim**2))
    return [cosine_sim, sin_component] + [0.0] * (EMBEDDING_DIM - 2)


def _make_draft(prompt_text="Sample question text here") -> QuestionDraft:
    return QuestionDraft(
        prompt_text=prompt_text,
        answer_text="A",
        explanation="because",
        target_knowledge="Present Simple",
        level_code="A2",
        source_ref="test",
    )


def _make_bank_question(db, *, prompt_text, embedding) -> Question:
    teacher = User(
        email="val-teacher@examcraft.dev", password_hash=hash_password("Secret123!"),
        full_name="Teacher", role=UserRole.TEACHER,
    )
    db.add(teacher)
    db.flush()
    grade = db.scalar(select(Grade).where(Grade.number == 7))
    level = db.scalar(select(ProficiencyLevel).where(ProficiencyLevel.code == "A2"))
    exam = Exam(
        teacher_id=teacher.id, title="t", grade_id=grade.id, level_id=level.id, source_type=SourceType.GLOBAL_SUCCESS
    )
    db.add(exam)
    db.flush()
    exercise_type = _exercise_type(db)
    block = ExamBlock(
        exam_id=exam.id, exercise_type_id=exercise_type.id, order_no=1, title="Block", question_count=1, points=1
    )
    db.add(block)
    db.flush()
    question = Question(
        block_id=block.id, order_no=1, prompt_text=prompt_text, answer_text="A", explanation="x",
        target_knowledge="x", level_id=level.id, source_ref="x", is_in_bank=True, embedding=embedding,
    )
    db.add(question)
    db.flush()
    return question


def test_no_warning_when_bank_is_empty(seeded_db):
    exercise_type = _exercise_type(seeded_db)
    grade = seeded_db.scalar(select(Grade).where(Grade.number == 7))
    warnings = validate_draft(
        seeded_db, _make_draft(), exercise_type=exercise_type, grade_number=7,
        school_stage_id=grade.school_stage_id, exam_level_rank=2, draft_embedding=_vector(1.0),
    )
    assert not any("embedding" in w for w in warnings)


def test_warns_when_cosine_similarity_above_threshold(seeded_db):
    _make_bank_question(seeded_db, prompt_text="existing bank question", embedding=_vector(1.0))
    exercise_type = _exercise_type(seeded_db)
    grade = seeded_db.scalar(select(Grade).where(Grade.number == 7))

    warnings = validate_draft(
        seeded_db, _make_draft(), exercise_type=exercise_type, grade_number=7,
        school_stage_id=grade.school_stage_id, exam_level_rank=2, draft_embedding=_vector(1.0),
    )
    assert any("embedding" in w for w in warnings)


def test_no_warning_when_cosine_similarity_below_threshold(seeded_db):
    _make_bank_question(seeded_db, prompt_text="existing bank question", embedding=_vector(-1.0))
    exercise_type = _exercise_type(seeded_db)
    grade = seeded_db.scalar(select(Grade).where(Grade.number == 7))

    warnings = validate_draft(
        seeded_db, _make_draft(), exercise_type=exercise_type, grade_number=7,
        school_stage_id=grade.school_stage_id, exam_level_rank=2, draft_embedding=_vector(1.0),
    )
    assert not any("embedding" in w for w in warnings)


def test_skips_cosine_check_when_no_draft_embedding_given(seeded_db):
    _make_bank_question(seeded_db, prompt_text="existing bank question", embedding=_vector(1.0))
    exercise_type = _exercise_type(seeded_db)
    grade = seeded_db.scalar(select(Grade).where(Grade.number == 7))

    warnings = validate_draft(
        seeded_db, _make_draft(), exercise_type=exercise_type, grade_number=7,
        school_stage_id=grade.school_stage_id, exam_level_rank=2, draft_embedding=None,
    )
    assert not any("embedding" in w for w in warnings)


def test_uses_configured_similarity_threshold(seeded_db):
    _make_bank_question(seeded_db, prompt_text="existing bank question", embedding=_base_vector())
    config = AIProviderConfig(
        provider="openai", model="gpt-4o-mini", embedding_model="text-embedding-3-small",
        api_key_encrypted=encrypt_api_key("sk-test"), duplicate_similarity_threshold=0.99, is_active=True,
    )
    seeded_db.add(config)
    seeded_db.flush()
    exercise_type = _exercise_type(seeded_db)
    grade = seeded_db.scalar(select(Grade).where(Grade.number == 7))

    # ~0.95 similarity: vượt ngưỡng mặc định 0.90 nhưng dưới ngưỡng cấu hình 0.99
    warnings = validate_draft(
        seeded_db, _make_draft(), exercise_type=exercise_type, grade_number=7,
        school_stage_id=grade.school_stage_id, exam_level_rank=2,
        draft_embedding=_vector_with_cosine_similarity(0.95),
    )
    assert not any("embedding" in w for w in warnings)
