"""Dựng câu phát âm/trọng âm từ ĐỀ THI THẬT đã nạp (chunk EXAM_ITEM).

Bộ dựng bằng code (`pronunciation_builder.py`) luôn đúng quy tắc 3 giống - 1 khác,
nhưng vốn từ là danh sách viết tay nên đề ra na ná nhau. Đề thật là nhóm 4 từ do giáo
viên soạn — bám sách, độ khó thật, đa dạng hơn hẳn.

Đề thật KHÔNG ghi đáp án, nên đáp án được suy bằng chính bộ phân tích âm dùng để kiểm
tra (`pronunciation_sounds`): 3 lựa chọn cùng một âm, 1 khác — cái khác là đáp án. Nhóm
nào không suy chắc chắn được thì BỎ, thà thiếu câu còn hơn ra đề sai đáp án.
"""

from __future__ import annotations

import random
import re

from app.services.ai_provider import QuestionDraft
from app.services.pronunciation_check import check_pronunciation_options, visible_text
from app.services.pronunciation_sounds import ending_sounds, stress_positions, vowel_sounds

# "A. puzzl<u>es</u>\tB. messag<u>es</u> ..." — tách theo nhãn A./B./C./D.
_OPTION_SPLIT_RE = re.compile(r"(?:^|[\s\t])([A-D])\s*[.)]\s*")
_LABELS = ("A", "B", "C", "D")

_PROMPTS = {
    "pronunciation": "Choose the word that has a different pronunciation of the underlined part.",
    "stress": "Choose the word that has a different stress pattern.",
}


def parse_option_line(text: str) -> list[str] | None:
    """Tách một dòng 4 lựa chọn của đề thật, giữ nguyên markup gạch chân.
    None nếu dòng không đủ 4 lựa chọn A/B/C/D."""
    parts = _OPTION_SPLIT_RE.split(text)
    if len(parts) < 9:  # [rác, 'A', text, 'B', text, 'C', text, 'D', text]
        return None
    labels = parts[1::2]
    values = [v.strip() for v in parts[2::2]]
    if list(labels) != list(_LABELS) or any(not v for v in values):
        return None
    return values


def odd_one_out(option_texts: list[str], *, is_pronunciation: bool) -> int | None:
    """Vị trí lựa chọn khác 3 cái còn lại, None nếu không suy chắc chắn được.

    Chấp nhận đúng thế 3-1: một giá trị xuất hiện 3 lần, một giá trị xuất hiện 1 lần.
    Thế 2-2 hoặc 4 khác nhau nghĩa là ta đọc sai âm (hoặc đề gõ sai) — bỏ qua.
    """
    words = [visible_text(t) for t in option_texts]
    if len(option_texts) != 4:
        return None

    if is_pronunciation:
        result = ending_sounds(words) or vowel_sounds(option_texts)
    else:
        result = stress_positions(words)
    if result is None:
        return None

    values = list(result[0])
    if len(values) != 4:
        return None
    unique = [v for v in set(values) if values.count(v) == 1]
    if len(unique) != 1 or values.count(unique[0]) != 1:
        return None
    majority = [v for v in set(values) if values.count(v) == 3]
    if not majority:
        return None
    return values.index(unique[0])


def build_from_exam_items(
    lines: list[str], *, is_pronunciation: bool, count: int, seed: int | None = None
) -> list[QuestionDraft]:
    """Tối đa `count` câu dựng từ các dòng lựa chọn của đề thật, không trùng nhau.

    Mỗi câu vẫn phải qua `check_pronunciation_options` như bộ dựng bằng code — đề thật
    cũng có thể gõ sai, và ta không có quyền tin tuyệt đối vào nguồn ngoài.
    """
    rng = random.Random(seed)
    pool = list(lines)
    rng.shuffle(pool)

    prompt = _PROMPTS["pronunciation" if is_pronunciation else "stress"]
    out: list[QuestionDraft] = []
    seen: set[frozenset[str]] = set()

    for line in pool:
        if len(out) >= count:
            break
        options_text = parse_option_line(line)
        if options_text is None:
            continue
        key = frozenset(options_text)
        if key in seen:
            continue
        odd = odd_one_out(options_text, is_pronunciation=is_pronunciation)
        if odd is None:
            continue
        if check_pronunciation_options(options_text, is_pronunciation=is_pronunciation):
            continue
        seen.add(key)
        options = [
            {"label": _LABELS[i], "text": text, "is_correct": i == odd}
            for i, text in enumerate(options_text)
        ]
        out.append(
            QuestionDraft(
                prompt_text=prompt,
                answer_text=f"{_LABELS[odd]}. {visible_text(options_text[odd])}",
                explanation=(
                    "Ba lựa chọn còn lại phát âm giống nhau, "
                    f"riêng {_LABELS[odd]} khác — lấy từ đề thi thật của Unit."
                ),
                target_knowledge="Phát âm" if is_pronunciation else "Trọng âm",
                level_code="A2",
                source_ref="Đề thi thật đã nạp (Knowledge_Base/Exams)",
                options=options,
            )
        )
    return out
