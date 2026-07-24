import enum
import uuid
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.knowledge import EMBEDDING_DIM


class SourceType(str, enum.Enum):
    GLOBAL_SUCCESS = "global_success"
    COMMON_KNOWLEDGE = "common_knowledge"
    CAMBRIDGE = "cambridge"


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    READY = "ready"


class ExportMode(str, enum.Enum):
    PLAIN = "plain"
    ANSWER_KEY = "answer_key"


class Difficulty(str, enum.Enum):
    NHAN_BIET = "nhan_biet"
    THONG_HIEU = "thong_hieu"
    VAN_DUNG = "van_dung"
    HON_HOP = "hon_hop"


class Exam(TimestampMixin, Base):
    """Đề thi. Đúng một trong unit_id/grammar_topic_id/cambridge_certificate_id được set,
    tương ứng source_type — ràng buộc kiểm tra ở tầng service, chưa dùng CHECK constraint
    (giữ đơn giản cho giai đoạn skeleton, xem PRD 22.1)."""

    __tablename__ = "exams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    grade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grades.id"), nullable=False)
    level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("proficiency_levels.id"), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="exam_source_type"), nullable=False)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("units.id"), nullable=True)
    grammar_topic_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("grammar_topics.id"), nullable=True)
    cambridge_certificate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cambridge_certificates.id"), nullable=True
    )
    extra_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ExamStatus] = mapped_column(
        Enum(ExamStatus, name="exam_status"), default=ExamStatus.DRAFT, nullable=False
    )
    export_mode: Mapped[ExportMode | None] = mapped_column(Enum(ExportMode, name="exam_export_mode"), nullable=True)
    variant_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    grade = relationship("Grade")
    level = relationship("ProficiencyLevel")
    unit = relationship("Unit")
    grammar_topic = relationship("GrammarTopic")
    cambridge_certificate = relationship("CambridgeCertificate")
    blocks: Mapped[list["ExamBlock"]] = relationship(
        back_populates="exam", order_by="ExamBlock.order_no", cascade="all, delete-orphan"
    )
    grammar_selections: Mapped[list["ExamGrammarSelection"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan"
    )
    variants: Mapped[list["ExamVariant"]] = relationship(back_populates="exam", cascade="all, delete-orphan")


class ExamGrammarSelection(Base):
    """Thì/cấu trúc câu được tick khi nguồn kiến thức là 'Kiến thức chung' (PRD 7.5/7.6)."""

    __tablename__ = "exam_grammar_selections"
    __table_args__ = (UniqueConstraint("exam_id", "grammar_point_id", name="uq_exam_grammar_point"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id"), nullable=False)
    grammar_point_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grammar_points.id"), nullable=False)

    exam = relationship("Exam", back_populates="grammar_selections")
    grammar_point = relationship("GrammarPoint")


class ExamBlock(Base):
    """Một phần của đề (I, II, III...). Trường khớp đúng dialog chỉnh block trong prototype."""

    __tablename__ = "exam_blocks"
    __table_args__ = (UniqueConstraint("exam_id", "order_no", name="uq_exam_block_order"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id"), nullable=False)
    exercise_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exercise_types.id"), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    difficulty: Mapped[Difficulty] = mapped_column(
        Enum(Difficulty, name="exam_block_difficulty"), default=Difficulty.HON_HOP, nullable=False
    )
    level_override_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("proficiency_levels.id"), nullable=True)
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    shuffle_answers: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    prompt_override: Mapped[str | None] = mapped_column(Text, nullable=True)
    passage_word_target: Mapped[int | None] = mapped_column(Integer, nullable=True)

    exam = relationship("Exam", back_populates="blocks")
    exercise_type = relationship("ExerciseType")
    level_override = relationship("ProficiencyLevel")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="block", order_by="Question.order_no", cascade="all, delete-orphan"
    )
    parts: Mapped[list["ExamBlockPart"]] = relationship(
        back_populates="block", order_by="ExamBlockPart.order_no", cascade="all, delete-orphan"
    )


class ExamBlockPart(Base):
    """Phần con đánh số 1./2./3. bên trong một block (ví dụ IV. TRANSFORMATION PATTERNS
    chia thành 1. So sánh kép, 2. So sánh hơn/kém/nhất, 3. Cụm động từ — mẫu đề thật GS9
    Unit 2). Dùng chung exercise_type/points/difficulty của block cha; chỉ tách tiêu đề,
    hướng dẫn, số câu và prompt bổ sung. Block không có phần con nào hoạt động như trước
    (tương thích ngược, xem docs/superpowers/specs/2026-07-20-block-sub-parts-design.md)."""

    __tablename__ = "exam_block_parts"
    __table_args__ = (UniqueConstraint("block_id", "order_no", name="uq_block_part_order"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    block_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exam_blocks.id"), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_override: Mapped[str | None] = mapped_column(Text, nullable=True)

    block = relationship("ExamBlock", back_populates="parts")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="part", order_by="Question.order_no", cascade="all, delete-orphan"
    )


class Question(TimestampMixin, Base):
    """Câu hỏi trong một block. `source_ref` là placeholder "Mock" cho tới khi có RAG thật."""

    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("block_id", "order_no", name="uq_question_block_order"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    block_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exam_blocks.id"), nullable=False)
    part_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exam_block_parts.id"), nullable=True)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    passage_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    options: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    target_knowledge: Mapped[str] = mapped_column(String(255), nullable=False)
    level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("proficiency_levels.id"), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    warnings: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_in_bank: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)

    block = relationship("ExamBlock", back_populates="questions")
    part = relationship("ExamBlockPart", back_populates="questions")
    level = relationship("ProficiencyLevel")


class ExamVariant(Base):
    """Mã đề A/B/C/D: seed + ánh xạ thứ tự câu để tái tạo chính xác (PRD 13)."""

    __tablename__ = "exam_variants"
    __table_args__ = (UniqueConstraint("exam_id", "code", name="uq_exam_variant_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("exams.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(5), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    question_order: Mapped[dict] = mapped_column(JSONB, nullable=False)

    exam = relationship("Exam", back_populates="variants")
