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


def _scoped_base_query(unit_id: uuid.UUID | None, grammar_point_ids: list[uuid.UUID] | None) -> Select:
    stmt = select(KnowledgeChunk).join(KnowledgeChunk.document).where(KnowledgeDocument.is_published.is_(True))
    if unit_id is not None:
        return stmt.where(KnowledgeDocument.unit_id == unit_id)
    return stmt.where(KnowledgeDocument.grammar_point_id.in_(grammar_point_ids))


def hybrid_search(
    db: Session,
    embed_client: EmbeddingClient,
    *,
    query_text: str,
    unit_id: uuid.UUID | None = None,
    grammar_point_ids: list[uuid.UUID] | None = None,
    top_k: int = 8,
    candidate_k: int = 30,
) -> list[RetrievedChunk]:
    """Trả `[]` khi không có phạm vi nguồn nào (vd đề Cambridge — kho kiến thức
    hiện chỉ phủ Global Success + Kiến thức chung, xem app/import_knowledge.py).
    Caller (OpenAIProvider) phải xử lý tường minh, không coi là lỗi."""
    if unit_id is None and not grammar_point_ids:
        return []

    base = _scoped_base_query(unit_id, grammar_point_ids)

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
