"""Lấy vốn từ (từ đơn) của một Unit từ kho tri thức, để bộ dựng câu phát âm ưu tiên
dùng từ trong bài thay vì bộ từ chuẩn chung (xem pronunciation_builder).

Chỉ lấy TỪ ĐƠN thuần chữ cái: mục từ vựng trong sách hay kèm nhiều dạng/cụm
("encourage (v) encouragement (n)", "heat wave") — ta tách token đầu và bỏ cụm nhiều
chữ, vì bài phát âm bắt buộc lựa chọn là 1 từ đơn.
"""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import DocumentChunkType, KnowledgeChunk, KnowledgeDocument

_WORD_RE = re.compile(r"^[a-z]+$")
# Từ vựng đứng đầu raw_text, trước dấu '(' (pos), '/' (IPA) hoặc ':' (nghĩa).
_HEAD_RE = re.compile(r"^([^(/:]+)")


def _head_word(raw_text: str) -> str | None:
    match = _HEAD_RE.match(raw_text.strip())
    if not match:
        return None
    head = match.group(1).strip().lower()
    # "heat wave" -> nhiều chữ: bỏ (bài phát âm cần từ đơn)
    if not head or " " in head:
        return None
    return head if _WORD_RE.match(head) else None


def unit_vocabulary_words(db: Session, unit_id: uuid.UUID | None, limit: int = 400) -> list[str]:
    """Danh sách từ đơn (lowercase, không trùng) thuộc Unit. `[]` khi không có unit_id
    hoặc Unit chưa có tài liệu — caller tự dùng bộ từ chuẩn."""
    if unit_id is None:
        return []
    stmt = (
        select(KnowledgeChunk.raw_text)
        .join(KnowledgeChunk.document)
        .where(
            KnowledgeDocument.unit_id == unit_id,
            KnowledgeDocument.is_published.is_(True),
            KnowledgeChunk.chunk_type.in_([DocumentChunkType.VOCABULARY, DocumentChunkType.WORD_FORM]),
        )
        .limit(limit)
    )
    words: list[str] = []
    seen: set[str] = set()
    for (raw_text,) in db.execute(stmt):
        word = _head_word(raw_text or "")
        if word and word not in seen:
            seen.add(word)
            words.append(word)
    return words
