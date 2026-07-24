"""Kiểm tra chất lượng lựa chọn dạng phát âm/trọng âm — trả CẢNH BÁO, không chặn cứng
(đúng nguyên tắc Validation Engine, PRD mục 11).

Sinh ra sau khi đề thật lộ 3 lỗi model lặp lại dù prompt đã dặn (báo cáo giáo viên
21/07/2026): bọc <u> lan cả từ ('g<u>ather</u>'), 4 lựa chọn gạch chân cụm chữ khác
nhau ('ather' vs 'other'), và bịa từ không có thật ('boring' → 'foring'/'woring'/
'soring'). Prompt-only không đủ tin cậy nên chốt bằng kiểm tra xác định ở đây.
"""

import re
from functools import lru_cache

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


def check_pronunciation_options(option_texts: list[str], *, check_cluster_shape: bool) -> list[str]:
    """`check_cluster_shape=True` cho dạng phát âm (cụm gạch chân phải ngắn và đồng
    nhất); dạng trọng âm bọc cả âm tiết nên chỉ kiểm tra gạch chân + từ có thật."""
    warnings: list[str] = []
    if not option_texts:
        return warnings

    clusters: list[str] = []
    missing: list[str] = []
    for text in option_texts:
        match = UNDERLINE_MARKUP_RE.search(text or "")
        if match is None:
            missing.append(visible_text(text or ""))
        else:
            clusters.append(match.group(1))

    if missing:
        warnings.append(f"Thiếu gạch chân <u> ở lựa chọn: {', '.join(missing)}.")

    if check_cluster_shape and clusters:
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
    for text in option_texts:
        word = visible_text(text or "").lower()
        if not _SINGLE_WORD_RE.match(word):
            continue
        if checker is None:
            checker = _spell_checker()
        if word not in checker:
            unknown.append(word)
    if unknown:
        warnings.append(
            f"Không phải từ tiếng Anh có thật: {', '.join(sorted(set(unknown)))} "
            "— kiểm tra lại chính tả/từ bịa."
        )

    return warnings
