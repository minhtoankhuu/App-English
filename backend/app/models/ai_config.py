import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AIProviderConfig(TimestampMixin, Base):
    """Cấu hình provider AI đang dùng để sinh đề (PRD mục 10, Giai đoạn 1D).

    Đúng 1 dòng `is_active=True` tại một thời điểm — hệ thống chỉ có 1 Admin, không
    cần khái niệm chọn provider theo từng lần sinh (PRD 22.1, giữ đơn giản).
    `api_key_encrypted` là Fernet token (app/services/crypto.py) — không bao giờ trả
    nguyên qua API, luôn mask khi trả về (xem app/schemas/ai_config.py).
    """

    __tablename__ = "ai_provider_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(64), nullable=False)
    api_key_encrypted: Mapped[bytes] = mapped_column(nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    duplicate_similarity_threshold: Mapped[float] = mapped_column(Float, default=0.90, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    updated_by = relationship("User")
