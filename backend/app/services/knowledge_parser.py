"""Parser thuần cho file bài học Global Success (.docx), không đụng DB.

Xem docs/superpowers/specs/2026-07-19-knowledge-base-global-success-design.md.
Không được raise exception vì cấu trúc một Unit lệch chuẩn — trường hợp xấu nhất
là chunk rơi vào DocumentChunkType.OTHER, không chặn import các file khác.
"""

import re
from pathlib import Path

from docx import Document
from docx.table import Table

from app.models.knowledge import DocumentChunkType
from app.services.docx_utils import ParsedChunk, iter_block_items, table_to_grid, table_to_text

# Global Success không đồng nhất định dạng mục từ vựng giữa các khối lớp/Unit:
# "word /IPA/ (pos): meaning" (đa số G6/G7), "word (pos) /IPA/ – meaning" (G8),
# và "word (pos): meaning" không có IPA (một số Unit G6).
_VOCAB_RE_IPA_FIRST = re.compile(r"^(?P<word>.+?)\s*/(?P<ipa>[^/]+)/\s*\((?P<pos>[^)]+)\)\s*:\s*(?P<meaning>.+)$")
_VOCAB_RE_POS_FIRST = re.compile(
    r"^(?P<word>.+?)\s*\((?P<pos>[^)]+)\)\s*/(?P<ipa>[^/]+)/\s*[:–-]\s*(?P<meaning>.+)$"
)
_VOCAB_RE_NO_IPA = re.compile(r"^(?P<word>.+)\((?P<pos>[^()]{1,15})\)\s*:\s*(?P<meaning>.+)$")
_PHRASE_RE = re.compile(r"^(?P<phrase>.+?):\s*(?P<meaning>.+)$")

_SECTION_KEYWORDS: list[tuple[str, DocumentChunkType]] = [
    ("VOCABULARY", DocumentChunkType.VOCABULARY),
    ("WORD FORM", DocumentChunkType.WORD_FORM),
    ("PREPOSITION", DocumentChunkType.PHRASE),
    ("PHRASE", DocumentChunkType.PHRASE),
    ("GRAMMAR", DocumentChunkType.GRAMMAR),
]

_HEADER_MAX_LEN = 60


def _classify_header(text: str) -> DocumentChunkType | None:
    upper = text.upper()
    for keyword, chunk_type in _SECTION_KEYWORDS:
        if keyword in upper:
            return chunk_type
    return None


def _is_header(text: str) -> bool:
    return bool(text) and len(text) < _HEADER_MAX_LEN and text == text.upper() and any(c.isalpha() for c in text)


def _parse_vocabulary(text: str) -> dict | None:
    for pattern in (_VOCAB_RE_IPA_FIRST, _VOCAB_RE_POS_FIRST):
        match = pattern.match(text)
        if match:
            return {
                "word": match.group("word").strip(),
                "ipa": match.group("ipa").strip(),
                "pos": match.group("pos").strip(),
                "meaning": match.group("meaning").strip(),
            }
    match = _VOCAB_RE_NO_IPA.match(text)
    if match:
        return {
            "word": match.group("word").strip(),
            "ipa": None,
            "pos": match.group("pos").strip(),
            "meaning": match.group("meaning").strip(),
        }
    return None


def _parse_phrase(text: str) -> dict | None:
    match = _PHRASE_RE.match(text)
    if not match:
        return None
    return {"phrase": match.group("phrase").strip(), "meaning": match.group("meaning").strip()}


def parse_lesson_docx(path: Path) -> list[ParsedChunk]:
    document = Document(str(path))
    chunks: list[ParsedChunk] = []
    current_section_title = ""
    current_type = DocumentChunkType.OTHER
    order_no = 0
    seen_title = False

    for item in iter_block_items(document):
        if isinstance(item, Table):
            if current_type == DocumentChunkType.GRAMMAR:
                raw_text = table_to_text(item)
                if raw_text:
                    order_no += 1
                    chunks.append(
                        ParsedChunk(
                            order_no,
                            DocumentChunkType.GRAMMAR,
                            current_section_title,
                            raw_text,
                            {"table": table_to_grid(item)},
                        )
                    )
            continue

        text = item.text.strip()
        if not text:
            continue
        if not seen_title:
            seen_title = True
            continue  # dòng tiêu đề Unit đầu tiên — Unit.title đã có sẵn trong DB

        if _is_header(text):
            current_section_title = text
            classified = _classify_header(text)
            if classified is not None:
                current_type = classified
            continue

        order_no += 1
        structured: dict | None = None
        if current_type == DocumentChunkType.VOCABULARY:
            structured = _parse_vocabulary(text)
        elif current_type in (DocumentChunkType.PHRASE, DocumentChunkType.GRAMMAR):
            structured = _parse_phrase(text)

        chunks.append(ParsedChunk(order_no, current_type, current_section_title, text, structured))

    return chunks
