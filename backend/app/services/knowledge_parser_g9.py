"""Parser cho file từ vựng Global Success 9 (khác cấu trúc G6-G8).

G6-G8: mỗi Unit một file "GS{n} - UNIT {x} - LESSON.docx" (xem knowledge_parser.py).
G9: MỘT file "Vocabulary Global Success 9.docx" gộp cả 12 Unit — mỗi Unit là 1 đoạn
tiêu đề "UNIT n: TÊN" theo sau là MỘT bảng 4 cột chứa toàn bộ từ vựng của Unit đó:
  - hàng gộp (4 ô giống nhau) KHÔNG có ':'  -> tiêu đề mục (Getting started, A closer
    look 1...) — dùng làm section_title.
  - hàng gộp CÓ ':'  -> cụm từ/cấu trúc (PHRASE).
  - hàng thường [rỗng, từ (+ dạng, pos), IPA, nghĩa] -> mục từ vựng (VOCABULARY).

Trả về dict: unit_order_no -> list[ParsedChunk]. Các mục dùng chung sau UNIT 12
(PHRASAL VERBS, ngữ pháp) không gắn Unit cụ thể nên bỏ qua ở bước này.
"""

import re
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.models.knowledge import DocumentChunkType
from app.services.docx_utils import ParsedChunk

_UNIT_HEADING_RE = re.compile(r"^UNIT\s*(\d+)\s*:", re.IGNORECASE)


def _collapse(text: str) -> str:
    """Gộp mọi khoảng trắng/tab/xuống dòng thành 1 dấu cách."""
    return " ".join(text.split())


def _is_ipa(cell: str) -> bool:
    return "/" in cell


def parse_g9_unit_rows(rows: list[list[str]]) -> list[ParsedChunk]:
    """Logic thuần (list ô từng hàng) — tách khỏi việc đọc .docx để test được."""
    chunks: list[ParsedChunk] = []
    section = "Vocabulary"
    order = 0
    for cells in rows:
        stripped = [c.strip() for c in cells]
        nonempty = [c for c in stripped if c]
        if not nonempty:
            continue
        if len(set(nonempty)) == 1:
            # hàng gộp (mọi ô có nội dung giống nhau, kể cả khi gộp một phần): tiêu đề
            # mục (không ':') hoặc cụm từ/cấu trúc (có ':')
            text = nonempty[0]
            if ":" in text:
                order += 1
                chunks.append(ParsedChunk(order, DocumentChunkType.PHRASE, section, _collapse(text), None))
            else:
                section = text
            continue
        # hàng từ vựng: [rỗng, từ(+pos), IPA, nghĩa] (đôi khi lệch ô) -> lấy các ô có nội dung
        word = nonempty[0]
        meaning = nonempty[-1] if len(nonempty) > 1 else ""
        ipa = next((c for c in nonempty if _is_ipa(c)), "")
        raw = _collapse(f"{word} {ipa} : {meaning}") if ipa else _collapse(f"{word} : {meaning}")
        chunk_type = DocumentChunkType.VOCABULARY if ipa else DocumentChunkType.OTHER
        order += 1
        chunks.append(ParsedChunk(order, chunk_type, section, raw, None))
    return chunks


def parse_g9_vocabulary(path: Path) -> dict[int, list[ParsedChunk]]:
    document = Document(str(path))
    result: dict[int, list[ParsedChunk]] = {}
    current_unit: int | None = None
    for child in document.element.body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            match = _UNIT_HEADING_RE.match(Paragraph(child, document).text.strip())
            if match:
                current_unit = int(match.group(1))
        elif tag == "tbl" and current_unit is not None and current_unit not in result:
            # chỉ lấy bảng ĐẦU TIÊN ngay sau tiêu đề mỗi Unit
            rows = [[cell.text for cell in row.cells] for row in Table(child, document).rows]
            result[current_unit] = parse_g9_unit_rows(rows)
    return result
