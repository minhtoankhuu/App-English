"""Test lấy vốn từ đơn của Unit từ kho tri thức (app/services/unit_vocabulary.py)."""

from sqlalchemy import select

from app.models.academic import Grade, Unit
from app.models.knowledge import DocumentChunkType, KnowledgeChunk, KnowledgeDocument
from app.services.unit_vocabulary import _head_word, unit_vocabulary_words


def test_head_word_extracts_single_word_before_pos_or_ipa():
    assert _head_word("community (n) /kəˈmjuːnəti/ : cộng đồng") == "community"
    assert _head_word("purpose (n)") == "purpose"
    assert _head_word("career /kəˈrɪə(r)/ : nghề nghiệp") == "career"


def test_head_word_rejects_multiword_and_symbols():
    assert _head_word("heat wave (n) : đợt nóng") is None
    assert _head_word("check-up (n)") is None
    assert _head_word("") is None


def _unit3_grade7(db) -> Unit:
    return db.scalar(select(Unit).join(Grade).where(Grade.number == 7, Unit.order_no == 3))


def _add_chunk(db, doc, raw_text, chunk_type=DocumentChunkType.VOCABULARY, order_no=1):
    db.add(
        KnowledgeChunk(
            document_id=doc.id,
            order_no=order_no,
            chunk_type=chunk_type,
            section_title="VOCABULARY",
            raw_text=raw_text,
        )
    )
    db.flush()


def test_returns_empty_without_unit_id(seeded_db):
    assert unit_vocabulary_words(seeded_db, None) == []


def test_collects_vocabulary_words_of_unit(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = KnowledgeDocument(unit_id=unit.id, file_name="t.docx", checksum="x")
    seeded_db.add(doc)
    seeded_db.flush()
    _add_chunk(seeded_db, doc, "volunteer /ˌvɒlənˈtɪə(r)/ (n) : tình nguyện viên", order_no=1)
    _add_chunk(seeded_db, doc, "donate (v) : quyên góp", order_no=2)
    _add_chunk(seeded_db, doc, "heat wave (n) : đợt nóng", order_no=3)  # nhiều chữ -> bỏ
    _add_chunk(seeded_db, doc, "grammar note", chunk_type=DocumentChunkType.GRAMMAR, order_no=4)

    words = unit_vocabulary_words(seeded_db, unit.id)

    assert "volunteer" in words
    assert "donate" in words
    assert "heat" not in words and "wave" not in words
    assert "grammar" not in words  # chỉ lấy VOCABULARY/WORD_FORM


def test_deduplicates_words(seeded_db):
    unit = _unit3_grade7(seeded_db)
    doc = KnowledgeDocument(unit_id=unit.id, file_name="t2.docx", checksum="y")
    seeded_db.add(doc)
    seeded_db.flush()
    _add_chunk(seeded_db, doc, "donate (v) : quyên góp", order_no=1)
    _add_chunk(seeded_db, doc, "donate (v) : quyên góp lần 2", order_no=2)

    words = unit_vocabulary_words(seeded_db, unit.id)

    assert words.count("donate") == 1
