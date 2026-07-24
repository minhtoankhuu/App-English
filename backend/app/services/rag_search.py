"""Hybrid search cho RAG (Giai đoạn 1D) — kết hợp full-text (đã có, TSVECTOR) và
vector cosine similarity (pgvector), hợp nhất bằng Reciprocal Rank Fusion (RRF).

Quyết định chốt với chủ dự án (21/07/2026): dùng RRF làm cơ chế "rerank" chính,
không thêm bước LLM rerank riêng — OpenAI không có endpoint rerank như Cohere, và
corpus mỗi Unit/GrammarPoint chỉ vài chục-200 chunk nên RRF đủ tốt, rẻ hơn và
nhanh hơn một lời gọi LLM rerank thêm (xem
docs/superpowers/specs/2026-07-21-llm-rag-integration-design.md).
"""

import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.knowledge import DocumentChunkType, KnowledgeChunk, KnowledgeDocument

RRF_K = 60  # hằng số chuẩn phổ biến trong tài liệu RRF, không cần tune

_V = DocumentChunkType.VOCABULARY
_WF = DocumentChunkType.WORD_FORM
_PH = DocumentChunkType.PHRASE
_GR = DocumentChunkType.GRAMMAR

DEFAULT_TOP_K = 8

# Truy xuất theo dạng bài: mỗi dạng ưu tiên loại chunk phù hợp + số chunk đưa cho LLM
# khác nhau, thay vì cùng 1 rổ 8 chunk cho mọi dạng trong Unit (xem đánh giá 21/07/2026).
# Dạng nhiều từ vựng (phát âm/trọng âm/word form) cần nhiều chất liệu hơn để đủ đa dạng
# mà vẫn trong phạm vi bài; dạng đọc hiểu để chunk_types=None (lấy mọi loại) vì cần nội
# dung rộng. chunk nguồn rất ngắn (mỗi mục từ 1 chunk) nên top_k lớn vẫn ít token.
_RETRIEVAL_PROFILES: dict[str, tuple[tuple[DocumentChunkType, ...] | None, int]] = {
    "pronunciation": ((_V, _WF), 30),
    "stress": ((_V, _WF), 30),
    "word_form": ((_WF, _V), 24),
    "matching": ((_V, _PH), 20),
    "gap_fill": ((_V, _PH, _GR), 16),
    "cloze_test": ((_V, _PH, _GR), 16),
    "multiple_choice": ((_GR, _V, _PH), 16),
    "sentence_rewrite": ((_GR, _PH), 12),
    "sign_reading": ((_PH, _V), 12),
    "reading_true_false": (None, 12),
}


def retrieval_profile(exercise_type_code: str) -> tuple[list[DocumentChunkType] | None, int]:
    """(loại chunk ưu tiên, top_k) theo dạng bài; dạng lạ dùng mặc định (mọi loại, 8)."""
    chunk_types, top_k = _RETRIEVAL_PROFILES.get(exercise_type_code, (None, DEFAULT_TOP_K))
    return (list(chunk_types) if chunk_types else None, top_k)


class EmbeddingClient(Protocol):
    def embed_one(self, text: str) -> list[float]: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    raw_text: str
    section_title: str
    chunk_type: DocumentChunkType
    fused_score: float


def _scoped_base_query(
    unit_id: uuid.UUID | None,
    grammar_point_ids: list[uuid.UUID] | None,
    chunk_types: list[DocumentChunkType] | None = None,
) -> Select:
    stmt = select(KnowledgeChunk).join(KnowledgeChunk.document).where(KnowledgeDocument.is_published.is_(True))
    if unit_id is not None:
        stmt = stmt.where(KnowledgeDocument.unit_id == unit_id)
    else:
        stmt = stmt.where(KnowledgeDocument.grammar_point_id.in_(grammar_point_ids))
    if chunk_types:
        stmt = stmt.where(KnowledgeChunk.chunk_type.in_(chunk_types))
    return stmt


def hybrid_search(
    db: Session,
    embed_client: EmbeddingClient,
    *,
    query_text: str,
    unit_id: uuid.UUID | None = None,
    grammar_point_ids: list[uuid.UUID] | None = None,
    top_k: int = DEFAULT_TOP_K,
    candidate_k: int = 30,
    chunk_types: list[DocumentChunkType] | None = None,
) -> list[RetrievedChunk]:
    """Trả `[]` khi không có phạm vi nguồn nào (vd đề Cambridge — kho kiến thức
    hiện chỉ phủ Global Success + Kiến thức chung, xem app/import_knowledge.py).
    Caller (OpenAIProvider) phải xử lý tường minh, không coi là lỗi.

    `chunk_types` giới hạn theo loại chunk hợp với dạng bài (xem retrieval_profile).
    Nếu Unit không có loại đó (vd thiếu hẳn WORD_FORM) thì bỏ lọc để vẫn có chất liệu
    chung thay vì trả rỗng."""
    if unit_id is None and not grammar_point_ids:
        return []

    base = _scoped_base_query(unit_id, grammar_point_ids, chunk_types)
    if chunk_types and db.scalar(base.limit(1)) is None:
        base = _scoped_base_query(unit_id, grammar_point_ids)
    candidate_k = max(candidate_k, top_k)

    tsquery = func.plainto_tsquery("simple", query_text)
    fts_stmt = (
        base.where(KnowledgeChunk.search_vector.op("@@")(tsquery))
        .order_by(func.ts_rank(KnowledgeChunk.search_vector, tsquery).desc())
        .limit(candidate_k)
    )
    fts_chunks = list(db.scalars(fts_stmt))

    query_vector = embed_client.embed_one(query_text)
    vector_stmt = (
        base.where(KnowledgeChunk.embedding.isnot(None))
        .order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))
        .limit(candidate_k)
    )
    vector_chunks = list(db.scalars(vector_stmt))

    scores: dict[uuid.UUID, float] = {}
    chunk_by_id: dict[uuid.UUID, KnowledgeChunk] = {}
    for ranked_list in (fts_chunks, vector_chunks):
        for rank, chunk in enumerate(ranked_list, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (RRF_K + rank)
            chunk_by_id[chunk.id] = chunk

    if not scores:
        # Cả FTS lẫn vector đều rỗng — thường do query_text không khớp từ nào trong
        # chunk (plainto_tsquery AND toàn bộ từ, dễ trật với entry ngắn kiểu từ vựng)
        # hoặc chunk trong phạm vi chưa được embed (embed_knowledge.py chưa chạy).
        # Phạm vi (Unit/GrammarPoint) vẫn có thể có kiến thức thật — lấy tạm theo
        # order_no thay vì trả rỗng, để LLM luôn có ngữ cảnh khi phạm vi không trống.
        fallback_chunks = list(db.scalars(base.order_by(KnowledgeChunk.order_no).limit(top_k)))
        return [
            RetrievedChunk(
                chunk_id=chunk.id,
                raw_text=chunk.raw_text,
                section_title=chunk.section_title,
                chunk_type=chunk.chunk_type,
                fused_score=0.0,
            )
            for chunk in fallback_chunks
        ]

    ranked_ids = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    return [
        RetrievedChunk(
            chunk_id=chunk_id,
            raw_text=chunk_by_id[chunk_id].raw_text,
            section_title=chunk_by_id[chunk_id].section_title,
            chunk_type=chunk_by_id[chunk_id].chunk_type,
            fused_score=score,
        )
        for chunk_id, score in ranked_ids
    ]
