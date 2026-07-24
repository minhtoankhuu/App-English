"""Tiện ích xử lý markup gạch chân `<u>...</u>` trong text lựa chọn phát âm/trọng âm.

`dedupe_pronunciation_suffix` sửa lỗi model hay mắc: dựng sẵn từ ĐÃ ĐỦ đuôi (vd
"cats", "dresses", "cooked") rồi bọc `<u>` lặp lại đuôi lần nữa → in ra bị nhân đôi
("catss", "dresseses", "cookeded"). Prompt đã dặn không được làm vậy (xem
app/services/prompts.py) nhưng model vẫn lỡ — đây là lớp chặn xác định, không phụ
thuộc vào việc model có nghe lời hay không.
"""

import re

UNDERLINE_MARKUP_RE = re.compile(r"<u>(.*?)</u>")

# Gốc từ TỰ THÂN kết thúc bằng "ed": "need<u>ed</u>" (needed) là ĐÚNG — không được
# cắt nhầm thành "ne<u>ed</u>". Danh sách nhỏ, đủ cho từ vựng THCS; thiếu từ nào thì
# tệ nhất là bỏ sót 1 ca hiếm, KHÔNG làm hỏng option đúng phổ biến.
_ED_BASE_STEMS = frozenset(
    {"need", "seed", "feed", "weed", "breed", "bleed", "speed", "exceed", "proceed", "succeed", "embed", "indeed"}
)


def dedupe_pronunciation_suffix(text: str) -> str:
    """Bỏ đuôi bị nhân đôi ngay trước marker `<u>`.

    Chỉ đụng khi marker nằm ở CUỐI chuỗi và phần trước nó kết thúc đúng bằng chuỗi
    trong marker (dấu hiệu chắc chắn của lỗi nhân đôi). Option đúng ('star<u>s</u>',
    'want<u>ed</u>', 'be<u>gin</u>') hoặc dạng so sánh âm giữa từ ('t<u>ea</u>m')
    không thỏa điều kiện nên giữ nguyên.
    """
    match = UNDERLINE_MARKUP_RE.search(text)
    if match is None:
        return text
    prefix, inner, tail = text[: match.start()], match.group(1), text[match.end() :]
    if tail or not inner:
        return text  # marker giữa từ (âm nguyên âm) hoặc rỗng — không phải lỗi đuôi

    low_prefix, low_inner = prefix.lower(), inner.lower()
    if not low_prefix.endswith(low_inner):
        return text  # 'star<u>s</u>', 'want<u>ed</u>' — đuôi không bị lặp

    if low_inner == "ed" and low_prefix in _ED_BASE_STEMS:
        return text  # 'need<u>ed</u>' đúng chính tả — giữ nguyên

    # 'class<u>s</u>'/'glass<u>s</u>': gốc kết thúc 'ss' đúng ra phải lấy đuôi 'es'
    # (classes/glasses) — vừa bỏ nhân đôi vừa sửa đuôi cho đúng chính tả.
    if low_inner == "s" and low_prefix.endswith("ss"):
        return f"{prefix}<u>es</u>"

    return f"{prefix[: -len(inner)]}<u>{inner}</u>"
