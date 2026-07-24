import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GenerationLog(Base):
    """Lịch sử mỗi lần gọi AI sinh câu hỏi (PRD mục 10: provider/model/prompt
    version/tham số/thời gian/token/chi phí/nguồn).

    Chỉ lưu metadata + tham chiếu chunk nguồn (`source_chunk_ids`) — KHÔNG lưu
    nguyên văn prompt/response để tránh lưu lâu dài nội dung sách giáo khoa có
    bản quyền trong DB (quyết định chủ dự án 21/07/2026, xem
    docs/superpowers/specs/2026-07-21-llm-rag-integration-design.md).
    """

    __tablename__ = "generation_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    exam_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("exams.id", ondelete="SET NULL"), nullable=True)
    block_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("exam_blocks.id", ondelete="SET NULL"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), nullable=False)
    params: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    question_count_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    source_chunk_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
