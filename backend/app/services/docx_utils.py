"""Helper duyệt file .docx dùng chung cho các parser kho kiến thức
(`knowledge_parser.py` cho bài học Global Success, `grammar_parser.py` cho
tài liệu ngữ pháp Kiến thức chung)."""

from dataclasses import dataclass

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.models.knowledge import DocumentChunkType


@dataclass
class ParsedChunk:
    order_no: int
    chunk_type: DocumentChunkType
    section_title: str
    raw_text: str
    structured: dict | None


def iter_block_items(document: Document):
    """Duyệt paragraph và table theo đúng thứ tự xuất hiện trong body (python-docx tách
    riêng .paragraphs/.tables nên phải tự duyệt XML để giữ thứ tự thật)."""
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def table_to_text(table: Table) -> str:
    lines = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        if any(cells):
            lines.append(" | ".join(cells))
    return "\n".join(lines)
