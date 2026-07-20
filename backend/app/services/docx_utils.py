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


def _row_to_lines(cells: list[str]) -> list[str]:
    """Một số bảng gộp nhiều mục song song vào 1 ô (ví dụ ô "Positive" chứa cả 5 dòng
    good/bad/far/many-much/little, ô "Comparative" chứa 5 dòng tương ứng) — nếu ghép
    thẳng bằng " | " sẽ lẫn cả cột với nhau, đọc sai cặp (LLM cũng hiểu sai y như
    người đọc). Khi mọi ô trong hàng có cùng số dòng con, ghép theo đúng vị trí dòng
    ("good → better → the best") thay vì gộp cả cột. Ngược lại (số dòng lệch nhau,
    trường hợp thường gặp nhất — mỗi ô chỉ có 1 dòng) giữ nguyên cách ghép " | " cũ."""
    split_cells = [cell.split("\n") for cell in cells]
    max_lines = max((len(c) for c in split_cells), default=0)
    if max_lines <= 1:
        return [" | ".join(cell.strip() for cell in cells)]

    lines = []
    for i in range(max_lines):
        parts = [split_cells[j][i].strip() if i < len(split_cells[j]) else "" for j in range(len(cells))]
        if any(parts):
            lines.append(" → ".join(p for p in parts if p))
    return lines


def table_to_text(table: Table) -> str:
    lines = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        if any(cells):
            lines.extend(_row_to_lines(cells))
    return "\n".join(lines)


def table_to_grid(table: Table) -> list[list[str]]:
    """Giữ đúng cấu trúc hàng/cột thật của bảng — dùng để hiển thị lại đúng bảng thay
    vì chuỗi đã dồn dấu "|" (một số tài liệu gộp nhiều dòng vào 1 ô, `table_to_text`
    làm mất ranh giới hàng/cột khi hiển thị, xem docs/superpowers/specs/2026-07-20-grammar-reference-knowledge-design.md)."""
    return [[cell.text.strip() for cell in row.cells] for row in table.rows]
