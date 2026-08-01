"""Kiểm tra chất lượng lựa chọn dạng phát âm/trọng âm — trả CẢNH BÁO, không chặn cứng
(đúng nguyên tắc Validation Engine, PRD mục 11).

Sinh ra sau khi đề thật lộ 3 lỗi model lặp lại dù prompt đã dặn (báo cáo giáo viên
21/07/2026): bọc <u> lan cả từ ('g<u>ather</u>'), 4 lựa chọn gạch chân cụm chữ khác
nhau ('ather' vs 'other'), và bịa từ không có thật ('boring' → 'foring'/'woring'/
'soring'). Prompt-only không đủ tin cậy nên chốt bằng kiểm tra xác định ở đây.
"""

import re
from collections import Counter
from functools import lru_cache

from app.services.pronunciation_sounds import SOUND_IPA, ending_sounds, stress_positions, vowel_sounds
from app.services.text_markup import UNDERLINE_MARKUP_RE

# Cụm gạch chân dạng phát âm là âm đang so sánh — dài hơn mức này nghĩa là model bọc
# lan cả từ. 4 ký tự đủ cho cụm dài nhất thường gặp ('ough' trong thought, 'eigh'
# trong neighbour); dạng trọng âm bọc cả âm tiết nên KHÔNG áp ngưỡng này.
MAX_PRONUNCIATION_CLUSTER_LEN = 4

# Kiểu (1) đuôi -s/-es và (2) đuôi -ed hợp lệ khi các lựa chọn bọc cụm KHÁC nhau
# ('look<u>s</u>' vs 'dress<u>es</u>', 'want<u>ed</u>' vs 'marr<u>ied</u>') nên bỏ qua
# ràng buộc "4 cụm phải giống hệt" — ràng buộc đó chỉ dành cho kiểu (3) âm trong từ.
_SUFFIX_CLUSTERS = frozenset({"s", "es", "d", "ed", "ied"})

# Chỉ kiểm tra từ điển với lựa chọn là MỘT từ đơn thuần chữ cái — cụm từ/câu, từ có
# gạch nối hay dấu nháy bỏ qua để không cảnh báo nhầm.
_SINGLE_WORD_RE = re.compile(r"^[a-z]+$")


@lru_cache(maxsize=1)
def _spell_checker():
    """Từ điển tiếng Anh offline (pyspellchecker) — nạp 1 lần, không gọi mạng."""
    from spellchecker import SpellChecker

    return SpellChecker()


def visible_text(text: str) -> str:
    """Chữ hiển thị sau khi bỏ marker <u>...</u>."""
    return UNDERLINE_MARKUP_RE.sub(r"\1", text).strip()


def _sound_pattern_warnings(option_texts: list[str], words: list[str]) -> list[str]:
    """Nhóm phát âm phải có ĐÚNG 1 từ khác 3 từ còn lại. Suy âm đuôi -s/-es, -ed từ
    chính tả; nếu không phải dạng đuôi thì thử suy nguyên âm giữa từ bằng từ điển IPA.
    Bỏ qua khi không suy chắc chắn được (xem pronunciation_sounds)."""
    result = ending_sounds(words)
    if result is None:
        result = vowel_sounds(option_texts)
    if result is None:
        return []
    sounds, label = result
    counts = Counter(sounds)
    if len(counts) == 2 and sorted(counts.values()) == [1, len(sounds) - 1]:
        return []
    detail = ", ".join(f"{word} {SOUND_IPA.get(sound, sound)}" for word, sound in zip(words, sounds))
    return [f"Nhóm {label} không đúng quy tắc 3 từ giống - 1 từ khác: {detail}."]


def _stress_pattern_warnings(words: list[str]) -> list[str]:
    """Nhóm trọng âm phải có ĐÚNG 1 từ trọng âm rơi vào âm tiết khác 3 từ còn lại. Bỏ
    qua khi không tra được vị trí trọng âm chắc chắn (xem pronunciation_sounds)."""
    result = stress_positions(words)
    if result is None:
        return []
    positions, label = result
    counts = Counter(positions)
    if len(counts) == 2 and sorted(counts.values()) == [1, len(positions) - 1]:
        return []
    detail = ", ".join(f"{word} (âm tiết {pos + 1})" for word, pos in zip(words, positions))
    return [f"Nhóm {label} không đúng quy tắc 3 từ giống - 1 từ khác: {detail}."]


def check_pronunciation_options(option_texts: list[str], *, is_pronunciation: bool) -> list[str]:
    """Kiểm tra chung cho gạch chân + từ đơn + từ có thật, cộng quy tắc 3 giống - 1 khác:
    `is_pronunciation=True` (dạng phát âm) so âm đuôi -s/-es, -ed hoặc nguyên âm giữa từ
    và ép cụm gạch chân ngắn/đồng nhất; `is_pronunciation=False` (dạng trọng âm) so vị
    trí âm tiết mang trọng âm. Ca không suy chắc chắn được thì bỏ qua, không báo nhầm."""
    warnings: list[str] = []
    if not option_texts:
        return warnings

    words = [visible_text(text or "") for text in option_texts]

    clusters: list[str] = []
    missing: list[str] = []
    for text, word in zip(option_texts, words):
        match = UNDERLINE_MARKUP_RE.search(text or "")
        if match is None:
            missing.append(word)
        else:
            clusters.append(match.group(1))

    if missing:
        warnings.append(f"Thiếu gạch chân <u> ở lựa chọn: {', '.join(missing)}.")

    # Lựa chọn BẮT BUỘC là từ đơn (prompt đã yêu cầu) — cụm từ/từ ghép có gạch nối vừa
    # phá quy tắc so sánh âm vừa không kiểm tra chính tả được. Đề thật 24/07/2026 lọt
    # "native languages", "southeast Asias", "black-and-whites".
    not_single = [word for word in words if word and not _SINGLE_WORD_RE.match(word.lower())]
    if not_single:
        warnings.append(
            f"Lựa chọn phải là 1 từ đơn: {', '.join(not_single)} "
            "— không dùng cụm từ hay từ ghép có gạch nối."
        )

    if is_pronunciation:
        warnings.extend(_sound_pattern_warnings(option_texts, words))
    else:
        warnings.extend(_stress_pattern_warnings(words))

    if is_pronunciation and clusters:
        too_long = sorted({c for c in clusters if len(c) > MAX_PRONUNCIATION_CLUSTER_LEN})
        if too_long:
            warnings.append(
                f"Phần gạch chân quá dài (bọc lan cả từ): {', '.join(too_long)} "
                "— chỉ nên bọc đúng âm đang so sánh."
            )
        lowered = {c.lower() for c in clusters}
        if len(clusters) > 1 and len(lowered) > 1 and not lowered <= _SUFFIX_CLUSTERS:
            warnings.append(
                f"Các lựa chọn gạch chân cụm chữ khác nhau ({', '.join(sorted(lowered))}) "
                "— dạng so sánh âm trong từ phải gạch chân cùng một cụm chữ cái."
            )

    checker = None
    unknown: list[str] = []
    for word in words:
        lowered = word.lower()
        if not _SINGLE_WORD_RE.match(lowered):
            continue
        if checker is None:
            checker = _spell_checker()
        if lowered not in checker:
            unknown.append(lowered)
    if unknown:
        warnings.append(
            f"Không phải từ tiếng Anh có thật: {', '.join(sorted(set(unknown)))} "
            "— kiểm tra lại chính tả/từ bịa."
        )

    return warnings
