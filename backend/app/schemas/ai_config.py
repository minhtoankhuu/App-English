import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Whitelist thay vì free-text — model không hợp lệ sẽ lỗi lúc gọi OpenAI (Structured
# Outputs chỉ vài model hỗ trợ), khó hiểu với Admin hơn nhiều so với chặn ngay ở đây.
ALLOWED_CHAT_MODELS = {"gpt-4o", "gpt-4o-mini"}
ALLOWED_EMBEDDING_MODELS = {"text-embedding-3-small", "text-embedding-3-large"}


class AIProviderConfigUpdateRequest(BaseModel):
    model: str
    embedding_model: str
    temperature: float = Field(ge=0, le=2)
    duplicate_similarity_threshold: float = Field(ge=0, le=1)
    api_key: str | None = Field(default=None, min_length=1)

    @field_validator("model")
    @classmethod
    def _validate_model(cls, value: str) -> str:
        if value not in ALLOWED_CHAT_MODELS:
            raise ValueError(f"Model không hợp lệ, chỉ chấp nhận: {', '.join(sorted(ALLOWED_CHAT_MODELS))}")
        return value

    @field_validator("embedding_model")
    @classmethod
    def _validate_embedding_model(cls, value: str) -> str:
        if value not in ALLOWED_EMBEDDING_MODELS:
            raise ValueError(
                f"Embedding model không hợp lệ, chỉ chấp nhận: {', '.join(sorted(ALLOWED_EMBEDDING_MODELS))}"
            )
        return value


class AIProviderConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    model: str
    embedding_model: str
    temperature: float
    duplicate_similarity_threshold: float
    is_active: bool
    api_key_masked: str
    updated_at: datetime
