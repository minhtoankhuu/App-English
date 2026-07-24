"""Embed toàn bộ KnowledgeChunk đã xuất bản vào cột `embedding` (Giai đoạn 1D — RAG).

Gọi OpenAI thật, TỐN TIỀN THẬT (nhỏ — xem ước tính chi phí in ra trước khi chạy).
Không tự động chạy trong migration/CI/Docker — chạy tay: `python -m app.embed_knowledge`.

Idempotent/resumable: mặc định chỉ embed chunk chưa có embedding hoặc có
`embedding_model` khác model đang cấu hình (đổi model → tự động embed lại đúng
những chunk cần), trừ khi `--force`. Commit theo batch nên crash giữa chừng
không mất tiến trình đã làm — chạy lại sẽ tiếp tục đúng chỗ dở dang.
"""

import argparse
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
import tiktoken
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.ai_config import AIProviderConfig
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.crypto import decrypt_api_key
from app.services.openai_embedding import OpenAIEmbeddingClient
from app.services.rag_search import EmbeddingClient

# Giá công bố OpenAI (USD/1 triệu token) tại thời điểm viết — chỉ để ước tính sơ bộ
# trước khi chạy thật, không phải nguồn giá chính thức (có thể đổi theo thời gian).
_PRICE_PER_1M_TOKENS = {"text-embedding-3-small": 0.02, "text-embedding-3-large": 0.13}

# tiktoken.get_encoding tự tải file BPE (~1.7MB) từ blob Azure lúc gọi lần đầu trong
# tiến trình nếu chưa có trong cache cục bộ — runner CI ephemeral (không cache giữa
# các lần chạy nếu không cấu hình riêng) nên thỉnh thoảng gặp lỗi mạng thoáng qua
# (503 "server is busy") dù không liên quan gì logic ứng dụng (đã gặp thật, CI đỏ
# dù test dùng FakeEmbeddingClient không gọi OpenAI). Thử lại như các lệnh gọi mạng
# khác trong codebase (xem OpenAIProvider._call_openai) thay vì để cả suite fail.
_ENCODING_LOAD_ATTEMPTS = 3


def _load_cl100k_encoding() -> tiktoken.Encoding:
    last_error: requests.exceptions.RequestException | None = None
    for attempt in range(_ENCODING_LOAD_ATTEMPTS):
        try:
            return tiktoken.get_encoding("cl100k_base")
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < _ENCODING_LOAD_ATTEMPTS - 1:
                time.sleep(1)
    raise RuntimeError(
        f"Tải file mã hoá tiktoken (cl100k_base) thất bại sau {_ENCODING_LOAD_ATTEMPTS} lần thử: {last_error}"
    ) from last_error


@dataclass
class EmbeddingStats:
    total_pending: int = 0
    embedded: int = 0
    estimated_tokens: int = 0


def _pending_chunks_query(embedding_model: str, force: bool):
    stmt = select(KnowledgeChunk).join(KnowledgeChunk.document).where(KnowledgeDocument.is_published.is_(True))
    if not force:
        stmt = stmt.where(or_(KnowledgeChunk.embedding.is_(None), KnowledgeChunk.embedding_model != embedding_model))
    return stmt


def estimate_tokens(chunks: list[KnowledgeChunk]) -> int:
    encoding = _load_cl100k_encoding()
    return sum(len(encoding.encode(c.raw_text)) for c in chunks)


def run_embedding(
    db: Session,
    config: AIProviderConfig,
    embed_client: EmbeddingClient,
    *,
    force: bool = False,
    batch_size: int = 100,
) -> EmbeddingStats:
    """Logic thuần, tách khỏi `main()` để test được với DB test + fake embedding
    client (không gọi OpenAI thật trong test)."""
    chunks = list(db.scalars(_pending_chunks_query(config.embedding_model, force)))
    stats = EmbeddingStats(total_pending=len(chunks), estimated_tokens=estimate_tokens(chunks))

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vectors = embed_client.embed_batch([c.raw_text for c in batch])
        now = datetime.now(timezone.utc)
        for chunk, vector in zip(batch, vectors):
            chunk.embedding = vector
            chunk.embedding_model = config.embedding_model
            chunk.embedded_at = now
        db.commit()
        stats.embedded += len(batch)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="Embed lại toàn bộ chunk kể cả đã có embedding hiện hành."
    )
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        config = db.scalar(select(AIProviderConfig).where(AIProviderConfig.is_active.is_(True)))
        if config is None:
            print("Chưa cấu hình AI (Admin > Cấu hình AI) — không thể embed.")
            return

        pending = list(db.scalars(_pending_chunks_query(config.embedding_model, args.force)))
        if not pending:
            print("Không có chunk nào cần embed.")
            return

        total_tokens = estimate_tokens(pending)
        price = _PRICE_PER_1M_TOKENS.get(config.embedding_model, 0.0)
        estimated_cost = total_tokens / 1_000_000 * price
        print(
            f"Sẽ embed {len(pending)} chunk (~{total_tokens} token, model {config.embedding_model}), "
            f"ước tính chi phí ~${estimated_cost:.4f} USD. Lệnh này gọi OpenAI thật."
        )

        client = OpenAIEmbeddingClient(decrypt_api_key(config.api_key_encrypted), config.embedding_model)
        stats = run_embedding(db, config, client, force=args.force, batch_size=args.batch_size)
        print(f"Đã embed {stats.embedded}/{stats.total_pending}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
