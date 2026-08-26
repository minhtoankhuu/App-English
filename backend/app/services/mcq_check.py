"""Kiểm tra chất lượng câu trắc nghiệm VOCABULARY AND GRAMMAR bằng code — trả CẢNH BÁO
(đúng nguyên tắc Validation Engine, PRD 11).

Sinh ra sau khi prompt v10 vẫn để lọt các lỗi lặp lại (đề sinh thử 07/08/2026):
- Câu hội thoại có HAI chỗ trống thay vì một (model đặt trống ở cả 2 lượt nói).
- Model chép nguyên câu ví dụ mẫu trong prompt ('Solar energy is a ______ source of
  energy.') vào đề của Unit chẳng liên quan.
- Câu đơn lọt vào dù phần này chỉ ra đề hội thoại (chốt 24/08/2026).
- Model nhét nguyên LƯỢT TRẢ LỜI vào 4 lựa chọn, mỗi lựa chọn là một câu đầy đủ còn
  chứa chỗ trống (đề thật 24/08/2026) — học sinh không có đáp án nào để chọn.
Bài học từ dạng phát âm: prompt-only không đủ tin cậy, phải chốt bằng kiểm tra xác định.
"""

import re

from app.services.docx_renderer import _speaker_prefix_cuts
from app.services.prompts import MULTIPLE_CHOICE_EXAMPLES

BLANK_RE = re.compile(r"_{3,}")

# Câu ví dụ dùng trong prompts.py — model hay chép nguyên si thay vì tự đặt câu mới.
# Câu ví dụ của các bản prompt cũ, vẫn chặn vì đề đã sinh trước đó còn lưu trong DB.
_LEGACY_EXAMPLE_FRAGMENTS = (
    "solar energy is a",
    "my brother often",
)
# Số từ tối thiểu để coi là chép mẫu — ngắn hơn thì dễ báo oan câu bình thường.
_MIN_COPIED_FRAGMENT_WORDS = 6


# Lựa chọn của đề thật là từ hoặc cụm ngắn ("play", "keep in touch with"), không phải câu.
_MAX_OPTION_WORDS = 6
_MAX_SHARED_OPTION_WORDS = 3


def _common_prefix_words(texts: list[str]) -> int:
    """Số từ đầu giống nhau ở MỌI lựa chọn."""
    if len(texts) < 2:
        return 0
    words = [t.split() for t in texts]
    shortest = min(len(w) for w in words)
    for i in range(shortest):
        if len({w[i] for w in words}) != 1:
            return i
    return shortest


def blank_count(prompt_text: str | None) -> int:
    return len(BLANK_RE.findall(prompt_text or ""))


def is_two_turn_dialogue(prompt_text: str | None) -> bool:
    """Dùng đúng bộ nhận diện lượt thoại mà docx_renderer dùng để in đậm tên người nói —
    nếu ở đây nhận là hội thoại thì ra đề cũng chắc chắn in đúng định dạng."""
    cuts = _speaker_prefix_cuts(prompt_text or "")
    return cuts is not None and sum(1 for cut in cuts if cut) >= 2


def _example_fragments() -> frozenset[str]:
    """Danh sách "cấm chép" suy thẳng từ kho câu mẫu trong prompts.py, nên thêm mẫu mới
    là tự động được bảo vệ — không phải nhớ cập nhật hai nơi.

    Lấy phần câu SAU tên người nói, bỏ chỗ trống và dấu câu, chỉ giữ đoạn đủ dài để
    không báo oan câu bình thường trùng vài từ thông dụng.
    """
    fragments: set[str] = set()
    for example in MULTIPLE_CHOICE_EXAMPLES:
        for line in example.split("\n"):
            _, sep, rest = line.partition(":")
            body = (rest if sep else line).strip().lower()
            body = " ".join(BLANK_RE.sub(" ", body).split())
            body = "".join(ch for ch in body if ch.isalnum() or ch.isspace())
            if len(body.split()) >= _MIN_COPIED_FRAGMENT_WORDS:
                fragments.add(" ".join(body.split()[:_MIN_COPIED_FRAGMENT_WORDS]))
    return frozenset(fragments)


def _looks_copied(prompt_text: str | None) -> bool:
    lowered = " ".join(BLANK_RE.sub(" ", (prompt_text or "").lower()).split())
    lowered = " ".join("".join(ch for ch in lowered if ch.isalnum() or ch.isspace()).split())
    if any(fragment in lowered for fragment in _LEGACY_EXAMPLE_FRAGMENTS):
        return True
    return any(fragment in lowered for fragment in _example_fragments())


def check_multiple_choice(prompt_text: str | None, options: list[dict] | None) -> list[str]:
    warnings: list[str] = []

    if not is_two_turn_dialogue(prompt_text):
        warnings.append(
            "Phần VOCABULARY AND GRAMMAR chỉ ra đề dạng HỘI THOẠI 2 LƯỢT: mỗi lượt một dòng "
            "dạng 'Tên: câu nói', chỗ trống nằm ở lượt trả lời."
        )

    n_blanks = blank_count(prompt_text)
    if n_blanks != 1:
        warnings.append(
            f"Câu phải có đúng 1 chỗ trống '______' để điền (đang có {n_blanks}) "
            "— câu hội thoại chỉ đặt chỗ trống ở lượt trả lời."
        )

    if _looks_copied(prompt_text):
        warnings.append("Câu chép lại ví dụ mẫu trong hướng dẫn, không bám nội dung bài học.")

    if options is not None:
        if len(options) != 4:
            warnings.append(f"Phải có đúng 4 lựa chọn A/B/C/D (đang có {len(options)}).")
        n_correct = sum(1 for opt in options if opt.get("is_correct"))
        if n_correct != 1:
            warnings.append(f"Phải có đúng 1 đáp án đúng (đang có {n_correct}).")
        texts = [(opt.get("text") or "").strip().lower() for opt in options]
        if len(set(texts)) != len(texts):
            warnings.append("Các lựa chọn bị trùng nhau.")

        with_blank = [opt.get("label") or "?" for opt in options if blank_count(opt.get("text"))]
        if with_blank:
            warnings.append(
                f"Lựa chọn {', '.join(with_blank)} còn chứa chỗ trống — chỗ trống thuộc về lượt trả lời "
                "trong câu dẫn, lựa chọn chỉ là từ/cụm từ điền vào đó."
            )

        # 4 lựa chọn lặp chung một đoạn đầu dài = model đã nhét cả lượt trả lời vào lựa chọn.
        prefix = _common_prefix_words(texts)
        if prefix >= _MAX_SHARED_OPTION_WORDS:
            warnings.append(
                f"Cả 4 lựa chọn lặp chung {prefix} từ đầu — phần lặp đó thuộc về câu dẫn, "
                "lựa chọn chỉ giữ phần khác nhau."
            )

        too_long = [
            opt.get("label") or "?"
            for opt in options
            if len((opt.get("text") or "").split()) > _MAX_OPTION_WORDS
        ]
        if too_long:
            warnings.append(
                f"Lựa chọn {', '.join(too_long)} dài quá {_MAX_OPTION_WORDS} từ — lựa chọn là từ/cụm từ, "
                "không phải câu hoàn chỉnh."
            )

        # Model phải giải trình vì sao TỪNG phương án nhiễu sai ngay khi sinh (why_wrong).
        # Không giải trình được nghĩa là phương án đó có thể CŨNG ĐÚNG -> câu có nhiều đáp
        # án đúng, lỗi hay gặp nhất còn lại của dạng này.
        unjustified = [
            opt.get("label") or "?"
            for opt in options
            if not opt.get("is_correct") and not (opt.get("why_wrong") or "").strip()
        ]
        if unjustified:
            warnings.append(
                f"Chưa nêu được vì sao phương án {', '.join(unjustified)} sai "
                "— có thể các phương án này cũng đúng."
            )

    return warnings
