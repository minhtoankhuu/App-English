import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SchoolStage(Base):
    """Primary / Secondary / High school — dùng để nhóm kiến thức và quy tắc độ dài (PRD 7.4, 7.6)."""

    __tablename__ = "school_stages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # primary|secondary|high_school
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)

    grades: Mapped[list["Grade"]] = relationship(back_populates="school_stage")


class ProficiencyLevel(Base):
    """Trục chuẩn CEFR A1-C1 (PRD 7.4). `rank` dùng để so sánh vượt trình độ."""

    __tablename__ = "proficiency_levels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)  # A1, A2, B1, B2, C1
    rank: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)


class CambridgeCertificate(Base):
    """Starters/Movers/Flyers/KET/PET — nhãn nguồn kiến thức, quy đổi CEFR theo giáo viên (PRD 7.4)."""

    __tablename__ = "cambridge_certificates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # Starters, Movers, ...
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    cefr_level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("proficiency_levels.id"), nullable=False)

    cefr_level: Mapped[ProficiencyLevel] = relationship()


class Grade(Base):
    """Khối lớp 1-12. `suggested_level_id` là gợi ý mặc định (PRD 7.4), giáo viên chỉnh tự do."""

    __tablename__ = "grades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    school_stage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("school_stages.id"), nullable=False)
    suggested_level_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("proficiency_levels.id"), nullable=False)

    school_stage: Mapped[SchoolStage] = relationship(back_populates="grades")
    suggested_level: Mapped[ProficiencyLevel] = relationship()
    units: Mapped[list["Unit"]] = relationship(back_populates="grade")


class BookSeries(Base):
    """Bộ sách, hiện chỉ Global Success (PRD 7.4 — chỉ dùng một bộ sách)."""

    __tablename__ = "book_series"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class Unit(Base):
    """Unit theo lớp. Chỉ seed cho lớp có danh mục đã xác nhận (6-12); lớp 1-5 chờ giáo viên duyệt."""

    __tablename__ = "units"
    __table_args__ = (UniqueConstraint("grade_id", "order_no", name="uq_units_grade_order"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_series_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("book_series.id"), nullable=False)
    grade_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("grades.id"), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    book_series: Mapped[BookSeries] = relationship()
    grade: Mapped[Grade] = relationship(back_populates="units")
