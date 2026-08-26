"""Tách đề thi thật (Knowledge_Base/Exams/) thành từng câu để làm CÂU MẪU cho RAG.

Khác với knowledge_parser.py (tách sách giáo khoa thành mục từ): ở đây mỗi chunk là
một câu hỏi hoàn chỉnh — câu dẫn + lựa chọn + lượt thoại, giữ nguyên như đề in ra —
vì thứ model cần bắt chước là CẢ CÂU chứ không phải từng từ.

Hàm thuần (nhận list[str], trả list[ExamItem]) nên test được không cần file .docx.
Xem docs: sách Global Success gần như không có câu ví dụ (GS7 Unit 1: 2/231 đoạn),
đây là nguồn câu mẫu thật duy nhất.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# "I. PRONUNCIATION", "III. WORD FORMATION"
_SECTION_RE = re.compile(r"^([IVXLC]+)\.\s+(.+)$")
# "1. A. puzzles ..." / "12. Minh Khoa: ..."
_NUMBERED_RE = re.compile(r"^\s*(\d+)\s*[.)]\s*(.*)$")
# Dòng lựa chọn: "A. for  B. about  C. on  D. with"
_OPTION_LINE_RE = re.compile(r"^\s*A\s*[.)]\s")
# Lượt thoại tiếp theo: "Bảo Hân: Because he's really crazy ..."
_SPEAKER_RE = re.compile(r"^\s*[^\W\d_][\w'\u00C0-\u1EF9.]*(?:\s+[\w'\u00C0-\u1EF9.]+){0,2}\s*:\s")
# Dòng họ từ của WORD FORMATION: "adore (v)  adorable (adj)  adorably (adv)"
_FAMILY_RE = re.compile(r"^[^()]*\([a-z]{1,4}\)(?:[^()]*\([a-z]{1,4}\))+\s*$", re.IGNORECASE)
_BLANK_RE = re.compile(r"_{3,}")

# Tiêu đề phần trong đề thật -> mã dạng bài của hệ thống. Dò theo từ khoá vì mỗi giáo
# viên đặt tên hơi khác ("SIGNS/ PICTURES" vs "PICTURE READING").
_SECTION_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("PRONUNCIATION", "pronunciation"),
    ("STRESS", "stress"),
    ("WORD FORMATION", "word_form"),
    ("WORD FORM", "word_form"),
    ("TRANSFORMATION", "sentence_rewrite"),
    ("REWRITE", "sentence_rewrite"),
    ("READING", "reading_true_false"),
    ("SIGN", "sign_reading"),
    ("PICTURE", "sign_reading"),
    ("VOCABULARY AND GRAMMAR", "multiple_choice"),
    ("GRAMMAR", "multiple_choice"),
)
# Một MỤC của đề thật hay chứa nhiều kiểu bài: đề GS8 Unit 1 đặt cả phát âm lẫn trọng
# âm trong "I. PRONUNCIATION", và đặt cloze test dưới "V. READING COMPREHENSION". Dòng câu
# lệnh giữa mục mới nói đúng đó là kiểu gì.
_INSTRUCTION_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("STRESS PATTERN", "stress"),
    ("FITS THE SPACE IN THE FOLLOWING PASSAGE", "cloze_test"),
    ("TRUE OR FALSE", "reading_true_false"),
    ("PRONOUNCED DIFFERENTLY", "pronunciation"),
)
# Dạng có bài đọc: dòng lựa chọn đứng một mình vô nghĩa khi tách khỏi đoạn văn.
_PASSAGE_TYPES = frozenset({"cloze_test", "reading_true_false"})
# Đoạn văn của bài đọc không đánh số và có thể không chứa chỗ trống (dạng True/False) —
# nhận ra nó bằng độ dài, vì câu lệnh và tiêu đề bài đọc luôn ngắn hơn nhiều.
_MIN_PASSAGE_CHARS = 80
# Câu ngắn hơn mức này là mảnh vụn (tiêu đề bảng, ghi chú), không dùng làm mẫu.
_MIN_ITEM_CHARS = 25


@dataclass(frozen=True)
class ExamItem:
    exercise_type_code: str
    text: str


def section_exercise_type(heading: str) -> str | None:
    upper = heading.upper()
    for keyword, code in _SECTION_KEYWORDS:
        if keyword in upper:
            return code
    return None


def instruction_exercise_type(line: str) -> str | None:
    """Kiểu bài suy từ dòng câu lệnh giữa mục, None nếu dòng đó không phải câu lệnh."""
    upper = line.upper()
    for keyword, code in _INSTRUCTION_KEYWORDS:
        if keyword in upper:
            return code
    return None


def normalize_family_line(line: str) -> str:
    """Khôi phục mũi tên giữa các từ trong họ từ. Word lưu mũi tên bằng ký tự symbol nên
    python-docx đọc ra khoảng trắng — mẫu phải đúng định dạng mình muốn model sinh ra."""
    members = [m.strip() for m in re.split(r"\)\s{2,}", line) if m.strip()]
    if len(members) < 2:
        return line
    return " → ".join(m if m.endswith(")") else f"{m})" for m in members)


def _is_continuation(line: str) -> bool:
    """Dòng thuộc về câu đang gom: dòng lựa chọn, hoặc lượt thoại thứ hai."""
    return bool(_OPTION_LINE_RE.match(line) or _SPEAKER_RE.match(line))


def parse_exam_items(lines: list[str]) -> list[ExamItem]:
    items: list[ExamItem] = []
    code: str | None = None
    family: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if code and buffer:
            text = "\n".join(buffer).strip()
            if len(text) >= _MIN_ITEM_CHARS:
                items.append(ExamItem(code, text))
        buffer = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        section = _SECTION_RE.match(line)
        if section:
            flush()
            code = section_exercise_type(section.group(2))
            family = None
            continue
        if code is None:
            continue

        if _FAMILY_RE.match(line) and not _BLANK_RE.search(line):
            # Dòng họ từ đứng riêng, gắn vào mọi câu của nhóm để mẫu còn ngữ cảnh.
            flush()
            family = normalize_family_line(line)
            continue

        refined = instruction_exercise_type(line)
        if refined and not _NUMBERED_RE.match(line):
            flush()
            code = refined
            family = None
            continue

        numbered = _NUMBERED_RE.match(line)
        if numbered:
            flush()
            # Dạng có bài đọc: "1. A. cinema  B. room ..." chỉ là dòng lựa chọn của một
            # chỗ trống trong đoạn văn — tách rời khỏi đoạn văn thì vô nghĩa.
            if code in _PASSAGE_TYPES and _OPTION_LINE_RE.match(numbered.group(2)):
                continue
            buffer = [f"{family}\n{numbered.group(2)}" if family else numbered.group(2)]
            continue

        if buffer and _is_continuation(line):
            buffer.append(line)
            continue

        if code in _PASSAGE_TYPES and _OPTION_LINE_RE.match(line):
            flush()
            continue

        if _BLANK_RE.search(line):
            # Câu tự đánh số bằng Word (WORD FORMATION) — không có "1." trong text.
            flush()
            buffer = [f"{family}\n{line}" if family else line]
            continue

        if code in _PASSAGE_TYPES and len(line) >= _MIN_PASSAGE_CHARS:
            flush()
            buffer = [line]
            continue

        # Câu lệnh, tiêu đề bài đọc, ghi chú — bỏ qua.
        flush()

    flush()
    return items
