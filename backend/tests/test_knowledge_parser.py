from pathlib import Path

from app.models.knowledge import DocumentChunkType
from app.services.knowledge_parser import parse_lesson_docx

KB_ROOT = Path(__file__).resolve().parents[2] / "Knowledge_Base" / "Global Success"


def test_parses_golden_reference_unit3_grade7():
    chunks = parse_lesson_docx(KB_ROOT / "G7" / "GS7 - UNIT 3 - LESSON.docx")

    types_present = {c.chunk_type for c in chunks}
    assert types_present == {
        DocumentChunkType.VOCABULARY,
        DocumentChunkType.WORD_FORM,
        DocumentChunkType.PHRASE,
        DocumentChunkType.GRAMMAR,
    }

    volunteer = next(
        c for c in chunks if c.chunk_type == DocumentChunkType.VOCABULARY and c.structured and c.structured["word"] == "volunteer"
    )
    assert volunteer.structured == {
        "word": "volunteer",
        "ipa": "ˌvɑːlənˈtɪr",
        "pos": "n, v",
        "meaning": "tình nguyện viên; tình nguyện",
    }

    grammar_table_chunks = [c for c in chunks if c.chunk_type == DocumentChunkType.GRAMMAR and "Simple Past Tense" in c.raw_text]
    assert grammar_table_chunks, "bảng ngữ pháp (Simple Past Tense) phải được trích từ table"

    order_nos = [c.order_no for c in chunks]
    assert order_nos == sorted(order_nos)
    assert len(order_nos) == len(set(order_nos))


def _all_lesson_files() -> list[Path]:
    return sorted(f for grade in ("G6", "G7", "G8") for f in (KB_ROOT / grade).glob("*.docx"))


def test_vocabulary_match_rate_across_all_units_is_high():
    all_files = _all_lesson_files()
    assert len(all_files) == 36

    total_vocab = 0
    total_matched = 0
    for file_path in all_files:
        chunks = parse_lesson_docx(file_path)
        vocab_chunks = [c for c in chunks if c.chunk_type == DocumentChunkType.VOCABULARY]
        total_vocab += len(vocab_chunks)
        total_matched += sum(1 for c in vocab_chunks if c.structured is not None)

    assert total_vocab > 2000
    assert total_matched / total_vocab > 0.9


def test_parser_never_raises_on_any_unit_file():
    for file_path in _all_lesson_files():
        chunks = parse_lesson_docx(file_path)
        assert len(chunks) > 0
        assert all(c.raw_text.strip() for c in chunks)
