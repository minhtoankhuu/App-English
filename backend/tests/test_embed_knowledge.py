from sqlalchemy import select

from app.embed_knowledge import run_embedding
from app.models.academic import Grade, Unit
from app.models.ai_config import AIProviderConfig
from app.models.knowledge import EMBEDDING_DIM, DocumentChunkType, KnowledgeChunk, KnowledgeDocument
from app.services.crypto import encrypt_api_key


class FakeEmbeddingClient:
    def embed_one(self, text: str) -> list[float]:
        return [1.0] + [0.0] * (EMBEDDING_DIM - 1)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_one(t) for t in texts]


def _unit3_grade7(db) -> Unit:
    return db.scalar(select(Unit).join(Grade).where(Grade.number == 7, Unit.order_no == 3))


def _make_config(db, *, embedding_model: str = "text-embedding-3-small") -> AIProviderConfig:
    config = AIProviderConfig(
        provider="openai",
        model="gpt-4o-mini",
        embedding_model=embedding_model,
        api_key_encrypted=encrypt_api_key("sk-test"),
        is_active=True,
    )
    db.add(config)
    db.flush()
    return config


def _make_chunk(db, document, *, raw_text, embedding=None, embedding_model=None, order_no=1) -> KnowledgeChunk:
    chunk = KnowledgeChunk(
        document_id=document.id,
        order_no=order_no,
        chunk_type=DocumentChunkType.VOCABULARY,
        section_title="VOCABULARY",
        raw_text=raw_text,
        embedding=embedding,
        embedding_model=embedding_model,
    )
    db.add(chunk)
    db.flush()
    return chunk


def test_embeds_chunks_without_embedding(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = KnowledgeDocument(unit_id=unit.id, file_name="test.docx", checksum="x")
    seeded_db.add(doc)
    seeded_db.flush()
    chunk = _make_chunk(seeded_db, doc, raw_text="hello world")
    config = _make_config(seeded_db)

    stats = run_embedding(seeded_db, config, FakeEmbeddingClient())

    assert stats.total_pending == 1
    assert stats.embedded == 1
    seeded_db.refresh(chunk)
    assert chunk.embedding is not None
    assert chunk.embedding_model == "text-embedding-3-small"
    assert chunk.embedded_at is not None


def test_skips_chunks_already_embedded_with_current_model(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = KnowledgeDocument(unit_id=unit.id, file_name="test.docx", checksum="x")
    seeded_db.add(doc)
    seeded_db.flush()
    _make_chunk(
        seeded_db,
        doc,
        raw_text="already embedded",
        embedding=[1.0] * EMBEDDING_DIM,
        embedding_model="text-embedding-3-small",
    )
    config = _make_config(seeded_db)

    stats = run_embedding(seeded_db, config, FakeEmbeddingClient())

    assert stats.total_pending == 0
    assert stats.embedded == 0


def test_reembeds_chunks_with_outdated_model(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = KnowledgeDocument(unit_id=unit.id, file_name="test.docx", checksum="x")
    seeded_db.add(doc)
    seeded_db.flush()
    _make_chunk(
        seeded_db, doc, raw_text="old model", embedding=[0.5] * EMBEDDING_DIM, embedding_model="old-model-v1"
    )
    config = _make_config(seeded_db, embedding_model="text-embedding-3-small")

    stats = run_embedding(seeded_db, config, FakeEmbeddingClient())

    assert stats.total_pending == 1
    assert stats.embedded == 1


def test_force_reembeds_even_when_current(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = KnowledgeDocument(unit_id=unit.id, file_name="test.docx", checksum="x")
    seeded_db.add(doc)
    seeded_db.flush()
    _make_chunk(
        seeded_db,
        doc,
        raw_text="already embedded",
        embedding=[1.0] * EMBEDDING_DIM,
        embedding_model="text-embedding-3-small",
    )
    config = _make_config(seeded_db)

    stats = run_embedding(seeded_db, config, FakeEmbeddingClient(), force=True)

    assert stats.total_pending == 1
    assert stats.embedded == 1


def test_ignores_chunks_from_unpublished_documents(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = KnowledgeDocument(unit_id=unit.id, file_name="test.docx", checksum="x", is_published=False)
    seeded_db.add(doc)
    seeded_db.flush()
    _make_chunk(seeded_db, doc, raw_text="unpublished content")
    config = _make_config(seeded_db)

    stats = run_embedding(seeded_db, config, FakeEmbeddingClient())

    assert stats.total_pending == 0
