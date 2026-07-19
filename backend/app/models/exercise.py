import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ExerciseType(Base):
    """Thư viện dạng bài khởi đầu (PRD 7.2, Implementation Notes 1.5)."""

    __tablename__ = "exercise_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_instruction: Mapped[str] = mapped_column(Text, nullable=False)
    has_passage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)


class SentenceLengthRule(Base):
    """Độ dài câu hỏi (trắc nghiệm/word form) theo cấp học — PRD 7.6a.

    Áp dụng cho các ExerciseType có code trong ("multiple_choice", "word_form");
    chưa tách bảng liên kết riêng ở giai đoạn skeleton này.
    """

    __tablename__ = "sentence_length_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_stage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("school_stages.id"), unique=True, nullable=False)
    min_words: Mapped[int] = mapped_column(Integer, nullable=False)
    max_words: Mapped[int] = mapped_column(Integer, nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    school_stage = relationship("SchoolStage")


class PassageLengthRule(Base):
    """Độ dài bài đọc theo khoảng khối lớp — PRD 7.6b."""

    __tablename__ = "passage_length_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    grade_min: Mapped[int] = mapped_column(Integer, nullable=False)
    grade_max: Mapped[int] = mapped_column(Integer, nullable=False)
    min_words: Mapped[int] = mapped_column(Integer, nullable=False)
    max_words: Mapped[int] = mapped_column(Integer, nullable=False)
