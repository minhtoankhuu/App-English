"""Test parser từ vựng Global Success 9 (app/services/knowledge_parser_g9.py)."""

from app.models.knowledge import DocumentChunkType
from app.services.knowledge_parser_g9 import parse_g9_unit_rows


def test_section_header_row_sets_section_not_chunk():
    rows = [
        ["Getting started", "Getting started", "Getting started", "Getting started"],
        ["", "community (n)", "/kəˈmjuːnəti/", "cộng đồng"],
    ]
    chunks = parse_g9_unit_rows(rows)
    assert len(chunks) == 1
    assert chunks[0].chunk_type == DocumentChunkType.VOCABULARY
    assert chunks[0].section_title == "Getting started"
    assert chunks[0].raw_text == "community (n) /kəˈmjuːnəti/ : cộng đồng"


def test_vocabulary_row_combines_word_ipa_meaning():
    rows = [["", "purpose (n)", "/ˈpɜːpəs/", "mục đích"]]
    chunk = parse_g9_unit_rows(rows)[0]
    assert chunk.chunk_type == DocumentChunkType.VOCABULARY
    assert chunk.raw_text == "purpose (n) /ˈpɜːpəs/ : mục đích"


def test_merged_row_with_colon_is_phrase():
    rows = [
        ["Essential phrases", "Essential phrases", "Essential phrases", "Essential phrases"],
        ["by the way : nhân tiện", "by the way : nhân tiện", "", ""],
    ]
    chunks = parse_g9_unit_rows(rows)
    assert len(chunks) == 1
    assert chunks[0].chunk_type == DocumentChunkType.PHRASE
    assert chunks[0].raw_text == "by the way : nhân tiện"
    assert chunks[0].section_title == "Essential phrases"


def test_row_without_ipa_is_other():
    rows = [["", "some grammar note without transcription", "", "ghi chú"]]
    chunk = parse_g9_unit_rows(rows)[0]
    assert chunk.chunk_type == DocumentChunkType.OTHER


def test_empty_rows_skipped_and_order_increments():
    rows = [
        ["", "", "", ""],
        ["", "ash (n)", "/æʃ/", "tro"],
        ["", "layer (n)", "/ˈleɪə(r)/", "lớp"],
    ]
    chunks = parse_g9_unit_rows(rows)
    assert [c.order_no for c in chunks] == [1, 2]
    assert all(c.chunk_type == DocumentChunkType.VOCABULARY for c in chunks)


def test_multi_form_word_cell_kept_in_raw_text():
    rows = [["", "encourage (v) encouragement (n)", "/ɪnˈkʌrɪdʒ/ /ɪnˈkʌrɪdʒmənt/", "khuyến khích; sự khuyến khích"]]
    chunk = parse_g9_unit_rows(rows)[0]
    assert "encourage" in chunk.raw_text and "encouragement" in chunk.raw_text
    assert "/ɪnˈkʌrɪdʒ/" in chunk.raw_text
