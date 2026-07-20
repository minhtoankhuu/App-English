"""Chọn AIProvider đang hoạt động dựa trên cấu hình Admin (Giai đoạn 1D) — thay cho
singleton `MockAIProvider()` cứng trước đây trong `generation.py`. Chưa cấu hình AI
→ tự động dùng Mock (an toàn, không lỗi cứng khi Admin chưa nhập API key)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_config import AIProviderConfig
from app.services.ai_provider import AIProvider, MockAIProvider
from app.services.crypto import decrypt_api_key
from app.services.openai_provider import OpenAIProvider


def get_active_provider(db: Session) -> AIProvider:
    config = db.scalar(select(AIProviderConfig).where(AIProviderConfig.is_active.is_(True)))
    if config is None:
        return MockAIProvider()
    return OpenAIProvider(config, decrypt_api_key(config.api_key_encrypted), db)
