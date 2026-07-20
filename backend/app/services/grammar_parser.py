"""Parser thuần cho tài liệu ngữ pháp tổng hợp (Kiến thức chung — 1 GrammarPoint,
ví dụ toàn bộ nội dung về "The Simple Present"), không đụng DB.

Xem docs/superpowers/specs/2026-07-20-grammar-reference-knowledge-design.md.
Khác `knowledge_parser.parse_lesson_docx` (dành cho bài học Global Success theo
Unit, nhận diện tiêu đề bằng viết HOA toàn bộ): tài liệu ngữ pháp tiếng Việt
thường dùng tiêu đề in đậm chứ không viết hoa (vd "Cách dùng:"), nên parser này
nhận diện tiêu đề bằng định dạng in đậm của cả đoạn văn, có thêm heuristic dòng
đánh số ("1. ...") làm tín hiệu phụ. Toàn bộ nội dung đều là DocumentChunkType.GRAMMAR
— không cần phân loại VOCABULARY/WORD_FORM/PHRASE như tài liệu Global Success.

Không được raise exception vì cấu trúc tài liệu lệch chuẩn — trường hợp xấu nhất
là chunk không có section_title, nhưng vẫn được lưu đầy đủ (không mất dữ liệu).
"""

import re
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.models.knowledge import DocumentChunkType
from app.services.docx_utils import ParsedChunk, iter_block_items, table_to_text

_HEADER_MAX_LEN = 120
_NUMBERED_HEADING_RE = re.compile(r"^\d+\.\s+\S")


def _is_bold_paragraph(paragraph: Paragraph) -> bool:
    runs = [r for r in paragraph.runs if r.text.strip()]
    if not runs:
        return False
    return all(r.bold for r in runs)


def _is_header(paragraph: Paragraph, text: str) -> bool:
    if not text or len(text) > _HEADER_MAX_LEN:
        return False
    if _is_bold_paragraph(paragraph):
        return True
    return bool(_NUMBERED_HEADING_RE.match(text))


def parse_grammar_reference_docx(path: Path) -> list[ParsedChunk]:
    document = Document(str(path))
    chunks: list[ParsedChunk] = []
    current_section_title = ""
    order_no = 0

    for item in iter_block_items(document):
        if isinstance(item, Table):
            raw_text = table_to_text(item)
            if raw_text:
                order_no += 1
                chunks.append(ParsedChunk(order_no, DocumentChunkType.GRAMMAR, current_section_title, raw_text, None))
            continue

        text = item.text.strip()
        if not text:
            continue

        if _is_header(item, text):
            current_section_title = text
            continue

        order_no += 1
        chunks.append(ParsedChunk(order_no, DocumentChunkType.GRAMMAR, current_section_title, text, None))

    return chunks
