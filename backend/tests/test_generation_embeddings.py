from unittest.mock import MagicMock, patch

from sqlalchemy import select

from app.models.academic import Grade, ProficiencyLevel
from app.models.ai_config import AIProviderConfig
from app.models.exam import Exam, ExamBlock, Question, SourceType
from app.models.exercise import ExerciseType
from app.models.knowledge import EMBEDDING_DIM
from app.models.user import User, UserRole
from app.security import hash_password
from app.services.crypto import encrypt_api_key
from app.services.generation import embed_questions_for_bank


def _setup_question(db) -> Question:
    teacher = User(
        email="embed-teacher@examcraft.dev", password_hash=hash_password("Secret123!"),
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
    exercise_type = db.scalar(select(ExerciseType).where(ExerciseType.code == "multiple_choice"))
    block = ExamBlock(
        exam_id=exam.id, exercise_type_id=exercise_type.id, order_no=1, title="Block", question_count=1, points=1
    )
    db.add(block)
    db.flush()
    question = Question(
        block_id=block.id, order_no=1, prompt_text="A question", answer_text="A", explanation="x",
        target_knowledge="x", level_id=level.id, source_ref="x",
    )
    db.add(question)
    db.flush()
    return question


def test_embed_questions_for_bank_noop_without_ai_config(seeded_db):
    question = _setup_question(seeded_db)
    embed_questions_for_bank(seeded_db, [question])
    assert question.embedding is None


def test_embed_questions_for_bank_populates_embedding_when_configured(seeded_db):
    question = _setup_question(seeded_db)
    config = AIProviderConfig(
        provider="openai", model="gpt-4o-mini", embedding_model="text-embedding-3-small",
        api_key_encrypted=encrypt_api_key("sk-test"), is_active=True,
    )
    seeded_db.add(config)
    seeded_db.flush()

    fake_vector = [1.0] * EMBEDDING_DIM
    with patch("app.services.generation.OpenAIEmbeddingClient") as mock_client_cls:
        mock_client_cls.return_value.embed_batch.return_value = [fake_vector]
        embed_questions_for_bank(seeded_db, [question])

    assert question.embedding is not None
