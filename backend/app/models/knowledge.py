import enum
import uuid

from sqlalchemy import Boolean, Computed, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DocumentChunkType(str, enum.Enum):
    VOCABULARY = "vocabulary"
    WORD_FORM = "word_form"
    PHRASE = "phrase"
    GRAMMAR = "grammar"
    OTHER = "other"


class KnowledgeDocument(TimestampMixin, Base):
    """Tài liệu nguồn đã nhập từ Knowledge_Base (PRD mục 6 — Knowledge Base & RAG).

    `checksum` cho phép import lại idempotent: file không đổi thì bỏ qua,
    file đổi nội dung thì thay toàn bộ chunk cũ (xem app/import_knowledge.py).
    """

    __tablename__ = "knowledge_documents"
    __table_args__ = (UniqueConstraint("unit_id", "file_name", name="uq_knowledge_document_unit_file"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    unit = relationship("Unit")
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document", order_by="KnowledgeChunk.order_no", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base):
    """Một đoạn kiến thức trích từ tài liệu — đơn vị cho full-text search (PRD 9.2).

    `structured` chỉ chứa trường parse được best-effort (vd word/ipa/pos/meaning
    cho vocabulary); nhiều dòng trong sách không khớp regex nên có thể là None —
    `raw_text` luôn có và là nguồn full-text search chính.
    """

    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_documents.id"), nullable=False)
    order_no: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[DocumentChunkType] = mapped_column(
        Enum(DocumentChunkType, name="knowledge_chunk_type"), nullable=False
    )
    section_title: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    structured: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', raw_text)", persisted=True), nullable=True
    )

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")
