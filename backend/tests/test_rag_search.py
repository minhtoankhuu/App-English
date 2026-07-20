from sqlalchemy import select

from app.models.academic import Grade, Unit
from app.models.grammar import GrammarPoint
from app.models.knowledge import EMBEDDING_DIM, DocumentChunkType, KnowledgeChunk, KnowledgeDocument
from app.services.rag_search import hybrid_search


class FakeEmbeddingClient:
    """Trả vector cố định theo nội dung truy vấn — không gọi OpenAI thật trong test."""

    def __init__(self, vectors: dict[str, list[float]]):
        self._vectors = vectors

    def embed_one(self, text: str) -> list[float]:
        return self._vectors.get(text, [0.0] * EMBEDDING_DIM)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_one(t) for t in texts]


def _vector(first_dim: float) -> list[float]:
    return [first_dim] + [0.0] * (EMBEDDING_DIM - 1)


def _unit3_grade7(db) -> Unit:
    return db.scalar(select(Unit).join(Grade).where(Grade.number == 7, Unit.order_no == 3))


def _make_document(db, *, unit_id=None, grammar_point_id=None, file_name="test.docx") -> KnowledgeDocument:
    doc = KnowledgeDocument(unit_id=unit_id, grammar_point_id=grammar_point_id, file_name=file_name, checksum="x")
    db.add(doc)
    db.flush()
    return doc


def _make_chunk(db, document, *, raw_text, embedding=None, chunk_type=DocumentChunkType.VOCABULARY, order_no=1):
    chunk = KnowledgeChunk(
        document_id=document.id,
        order_no=order_no,
        chunk_type=chunk_type,
        section_title="VOCABULARY",
        raw_text=raw_text,
        embedding=embedding,
    )
    db.add(chunk)
    db.flush()
    return chunk


def test_returns_empty_when_no_scope_given(seeded_db):
    client = FakeEmbeddingClient({})
    result = hybrid_search(seeded_db, client, query_text="anything")
    assert result == []


def test_finds_chunk_by_full_text_match(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = _make_document(seeded_db, unit_id=unit.id)
    _make_chunk(seeded_db, doc, raw_text="volunteer /vɑːlənˈtɪr/ (n): tình nguyện viên")
    _make_chunk(seeded_db, doc, raw_text="unrelated word entry", order_no=2)
    seeded_db.flush()

    client = FakeEmbeddingClient({})
    result = hybrid_search(seeded_db, client, query_text="volunteer", unit_id=unit.id)

    assert len(result) >= 1
    assert any("volunteer" in r.raw_text for r in result)


def test_finds_chunk_by_vector_similarity_even_without_text_overlap(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = _make_document(seeded_db, unit_id=unit.id)
    close_chunk = _make_chunk(seeded_db, doc, raw_text="xyz zzz qqq", embedding=_vector(1.0))
    _make_chunk(seeded_db, doc, raw_text="completely different filler text", embedding=_vector(-1.0), order_no=2)
    seeded_db.flush()

    client = FakeEmbeddingClient({"query about xyz": _vector(1.0)})
    result = hybrid_search(seeded_db, client, query_text="query about xyz", unit_id=unit.id)

    assert result[0].chunk_id == close_chunk.id


def test_rrf_fusion_ranks_chunk_matching_both_signals_first(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = _make_document(seeded_db, unit_id=unit.id)
    both = _make_chunk(seeded_db, doc, raw_text="unique keyword alpha", embedding=_vector(1.0), order_no=1)
    only_text = _make_chunk(seeded_db, doc, raw_text="unique keyword beta", embedding=_vector(-1.0), order_no=2)
    only_vector = _make_chunk(seeded_db, doc, raw_text="totally unrelated gamma", embedding=_vector(1.0), order_no=3)
    seeded_db.flush()

    client = FakeEmbeddingClient({"unique keyword": _vector(1.0)})
    result = hybrid_search(seeded_db, client, query_text="unique keyword", unit_id=unit.id)

    result_ids = [r.chunk_id for r in result]
    assert result_ids[0] == both.id
    assert only_text.id in result_ids
    assert only_vector.id in result_ids


def test_excludes_unpublished_documents(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = _make_document(seeded_db, unit_id=unit.id, file_name="unpublished.docx")
    doc.is_published = False
    _make_chunk(seeded_db, doc, raw_text="secret unpublished vocabulary entry")
    seeded_db.flush()

    client = FakeEmbeddingClient({})
    result = hybrid_search(seeded_db, client, query_text="secret unpublished", unit_id=unit.id)
    assert result == []


def test_scopes_by_grammar_point_ids(seeded_db):
    point = seeded_db.scalar(select(GrammarPoint).where(GrammarPoint.name == "Present Simple"))
    other_point = seeded_db.scalar(select(GrammarPoint).where(GrammarPoint.name != "Present Simple"))
    doc_in_scope = _make_document(seeded_db, grammar_point_id=point.id, file_name="in-scope.docx")
    doc_out_of_scope = _make_document(seeded_db, grammar_point_id=other_point.id, file_name="out-of-scope.docx")
    _make_chunk(seeded_db, doc_in_scope, raw_text="present simple usage rule")
    _make_chunk(seeded_db, doc_out_of_scope, raw_text="present simple usage rule", order_no=1)
    seeded_db.flush()

    client = FakeEmbeddingClient({})
    result = hybrid_search(seeded_db, client, query_text="present simple usage", grammar_point_ids=[point.id])

    assert all(r.chunk_id in {c.id for c in doc_in_scope.chunks} for r in result)
