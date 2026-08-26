"""Kiểm tra chất lượng câu trắc nghiệm VOCABULARY AND GRAMMAR bằng code — trả CẢNH BÁO
(đúng nguyên tắc Validation Engine, PRD 11).

Sinh ra sau khi prompt v10 vẫn để lọt các lỗi lặp lại (đề sinh thử 07/08/2026):
- Câu hội thoại có HAI chỗ trống thay vì một (model đặt trống ở cả 2 lượt nói).
- Model chép nguyên câu ví dụ mẫu trong prompt ('Solar energy is a ______ source of
  energy.') vào đề của Unit chẳng liên quan.
- Câu đơn lọt vào dù phần này chỉ ra đề hội thoại (chốt 24/08/2026).
Bài học từ dạng phát âm: prompt-only không đủ tin cậy, phải chốt bằng kiểm tra xác định.
"""

import re

from app.services.docx_renderer import _speaker_prefix_cuts

BLANK_RE = re.compile(r"_{3,}")

# Câu ví dụ dùng trong prompts.py — model hay chép nguyên si thay vì tự đặt câu mới.
_PROMPT_EXAMPLE_FRAGMENTS = (
    "solar energy is a",
    "my brother often",
    "why does duc minh always join the school football club",
)


def blank_count(prompt_text: str | None) -> int:
    return len(BLANK_RE.findall(prompt_text or ""))


def is_two_turn_dialogue(prompt_text: str | None) -> bool:
    """Dùng đúng bộ nhận diện lượt thoại mà docx_renderer dùng để in đậm tên người nói —
    nếu ở đây nhận là hội thoại thì ra đề cũng chắc chắn in đúng định dạng."""
    cuts = _speaker_prefix_cuts(prompt_text or "")
    return cuts is not None and sum(1 for cut in cuts if cut) >= 2


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

    lowered = (prompt_text or "").lower()
    if any(fragment in lowered for fragment in _PROMPT_EXAMPLE_FRAGMENTS):
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
