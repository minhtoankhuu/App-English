"""Admin cấu hình provider AI (PRD mục 10, Giai đoạn 1D — xem
docs/superpowers/specs/2026-07-21-llm-rag-integration-design.md).

Đúng 1 dòng cấu hình `is_active=True` tại một thời điểm — PUT là upsert dòng đó.
API key luôn mã hóa trước khi lưu, không bao giờ trả nguyên qua bất kỳ response
nào (chỉ trả dạng che `sk-...ab12`).
"""

import openai
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.ai_config import AIProviderConfig
from app.models.user import User
from app.schemas.ai_config import AIProviderConfigOut, AIProviderConfigUpdateRequest
from app.services.audit import record_audit_log
from app.services.crypto import decrypt_api_key, encrypt_api_key, mask_api_key

router = APIRouter(prefix="/admin/ai-config", tags=["admin"], dependencies=[Depends(require_admin)])


class TestConnectionRequest(BaseModel):
    api_key: str = Field(min_length=1)


class TestConnectionResult(BaseModel):
    ok: bool
    message: str


def _get_active_config(db: Session) -> AIProviderConfig | None:
    return db.scalar(select(AIProviderConfig).where(AIProviderConfig.is_active.is_(True)))


def _config_out(config: AIProviderConfig) -> dict:
    return {
        "id": config.id,
        "provider": config.provider,
        "model": config.model,
        "embedding_model": config.embedding_model,
        "temperature": config.temperature,
        "duplicate_similarity_threshold": config.duplicate_similarity_threshold,
        "is_active": config.is_active,
        "api_key_masked": mask_api_key(decrypt_api_key(config.api_key_encrypted)),
        "updated_at": config.updated_at,
    }


@router.get("", response_model=AIProviderConfigOut | None)
def get_config(db: Session = Depends(get_db)) -> dict | None:
    config = _get_active_config(db)
    return _config_out(config) if config else None


@router.put("", response_model=AIProviderConfigOut)
def update_config(
    payload: AIProviderConfigUpdateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> dict:
    config = _get_active_config(db)
    if config is None and not payload.api_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chưa có cấu hình — cần nhập API key")

    is_new = config is None
    if is_new:
        config = AIProviderConfig(
            provider="openai",
            model=payload.model,
            embedding_model=payload.embedding_model,
            api_key_encrypted=encrypt_api_key(payload.api_key),
            temperature=payload.temperature,
            duplicate_similarity_threshold=payload.duplicate_similarity_threshold,
            is_active=True,
        )
        db.add(config)
    else:
        config.model = payload.model
        config.embedding_model = payload.embedding_model
        config.temperature = payload.temperature
        config.duplicate_similarity_threshold = payload.duplicate_similarity_threshold
        if payload.api_key:
            config.api_key_encrypted = encrypt_api_key(payload.api_key)
    config.updated_by_user_id = actor.id
    db.flush()

    record_audit_log(
        db,
        actor=actor,
        action="ai_config.created" if is_new else "ai_config.updated",
        target_type="ai_provider_config",
        target_id=config.id,
        target_label=f"{config.provider}/{config.model}",
        details={"model": payload.model, "embedding_model": payload.embedding_model},
    )
    db.commit()
    db.refresh(config)
    return _config_out(config)


@router.post("/test", response_model=TestConnectionResult)
def test_connection(payload: TestConnectionRequest) -> dict:
    try:
        client = openai.OpenAI(api_key=payload.api_key)
        client.models.list()
    except openai.AuthenticationError:
        return {"ok": False, "message": "API key không hợp lệ."}
    except openai.OpenAIError as exc:
        return {"ok": False, "message": f"Không kết nối được tới OpenAI: {type(exc).__name__}"}
    return {"ok": True, "message": "Kết nối thành công."}
