"""Kiểm tra chất lượng câu trắc nghiệm VOCABULARY AND GRAMMAR bằng code — trả CẢNH BÁO
(đúng nguyên tắc Validation Engine, PRD 11).

Sinh ra sau khi prompt v10 vẫn để lọt các lỗi lặp lại (đề sinh thử 07/08/2026):
- Câu hội thoại có HAI chỗ trống thay vì một (model đặt trống ở cả 2 lượt nói).
- Model chép nguyên câu ví dụ mẫu trong prompt ('Solar energy is a ______ source of
  energy.') vào đề của Unit chẳng liên quan.
Bài học từ dạng phát âm: prompt-only không đủ tin cậy, phải chốt bằng kiểm tra xác định.
"""

import re

BLANK_RE = re.compile(r"_{3,}")

# Câu ví dụ dùng trong prompts.py — model hay chép nguyên si thay vì tự đặt câu mới.
_PROMPT_EXAMPLE_FRAGMENTS = (
    "solar energy is a",
    "my brother often",
    "why does duc minh always join the school football club",
)


def blank_count(prompt_text: str | None) -> int:
    return len(BLANK_RE.findall(prompt_text or ""))


def check_multiple_choice(prompt_text: str | None, options: list[dict] | None) -> list[str]:
    warnings: list[str] = []

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
