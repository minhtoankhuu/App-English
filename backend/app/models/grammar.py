import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.academic import ProficiencyLevel
from app.models.base import Base


class GrammarTopic(Base):
    """Chuyên đề trong mục 'Kiến thức chung': Tense, Các dạng cấu trúc câu (PRD 7.4)."""

    __tablename__ = "grammar_topics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # tense | sentence_structure
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    groups: Mapped[list["GrammarGroup"]] = relationship(back_populates="topic", order_by="GrammarGroup.order_no")


class GrammarGroup(Base):
    """Nhóm hiển thị: Hiện tại/Quá khứ/Tương lai hoặc Nền tảng/Trọng tâm THCS/Nâng cao THPT."""

    __tablename__ = "grammar_groups"
    __table_args__ = (UniqueConstraint("topic_id", "order_no", name="uq_grammar_groups_topic_order"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grammar_topics.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)

    topic: Mapped[GrammarTopic] = relationship(back_populates="groups")
    points: Mapped[list["GrammarPoint"]] = relationship(back_populates="group", order_by="GrammarPoint.order_no")


class GrammarPoint(Base):
    """Một thì hoặc một cấu trúc câu cụ thể, kèm trình độ tối thiểu (PRD 7.4 / Implementation Notes 1.2-1.3)."""

    __tablename__ = "grammar_points"
    __table_args__ = (UniqueConstraint("group_id", "order_no", name="uq_grammar_points_group_order"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grammar_groups.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    min_level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("proficiency_levels.id"), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)

    group: Mapped[GrammarGroup] = relationship(back_populates="points")
    min_level: Mapped[ProficiencyLevel] = relationship()
