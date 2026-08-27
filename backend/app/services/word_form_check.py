"""Kiểm câu WORD FORMATION bằng code ngay khi sinh — cùng mô hình với mcq_check:
cảnh báo được dùng làm feedback để pipeline tự sinh lại câu lỗi (xem generation.py).

Hai kiểu có ràng buộc khác nhau nên phải biết đang sinh kiểu nào:
  (A) nhóm theo họ từ  -> target_knowledge PHẢI là chuỗi họ từ, câu KHÔNG có từ gốc trong ngoặc
  (B) từ gốc trong ngoặc -> câu PHẢI kết thúc bằng (từ gốc), và từ gốc phải khác đáp án
"""

from __future__ import annotations

import re

from app.services.docx_renderer import split_bracket_root, word_family_label

BLANK_RE = re.compile(r"_{3,}")
_FAMILY_MEMBER_WORD_RE = re.compile(r"([A-Za-z][A-Za-z'\-]*)\s*\(")


def word_family_members(family: str | None) -> set[str]:
    """Các từ trong một chuỗi họ từ, lowercase.
    'science (n) → scientist (n)' -> {'science', 'scientist'}."""
    return {m.group(1).lower() for m in _FAMILY_MEMBER_WORD_RE.finditer(family or "")}


def _in_family(answer: str, members: set[str]) -> bool:
    """Đáp án có thuộc họ từ không, CHẤP NHẬN dạng biến cách.

    Dòng ❖ liệt kê dạng gốc ('adore (v) → adorable (adj)'), còn câu hỏi bắt chia theo
    ngữ pháp: "My little sister ______ her teddy bear" đáp án đúng là 'adores'. So khớp
    tuyệt đối sẽ báo nhầm chính những câu đúng.
    """
    a = answer.lower()
    if a in members:
        return True
    for m in members:
        if a in {m + "s", m + "es", m + "d", m + "ed", m + "ing"}:
            return True
        if m.endswith("e") and a == m[:-1] + "ing":
            return True
        if m.endswith("y") and a in {m[:-1] + "ies", m[:-1] + "ied"}:
            return True
    return False


def detect_word_form_kind(prompt_override: str | None) -> str | None:
    """Suy kiểu word form từ prompt_override của Phần con (preset ở ExamBuilder ghi
    'kiểu (A)'/'kiểu (B)'). None = không rõ kiểu -> chỉ kiểm các luật chung."""
    text = (prompt_override or "").lower()
    for marker, kind in (("(b)", "bracket"), ("(a)", "family")):
        if marker in text:
            return kind
    if "trong ngoặc" in text:
        return "bracket"
    if "họ từ" in text:
        return "family"
    return None


def check_word_form(
    prompt_text: str,
    answer_text: str | None,
    target_knowledge: str | None,
    *,
    kind: str | None,
    options: list[dict] | None = None,
    allowed_family: str | None = None,
) -> list[str]:
    warnings: list[str] = []
    if options:
        # Đề thật 24/08/2026: model tự thêm "A. togetherness B. togetherly ..." dưới mỗi câu
        # — word form là bài ĐIỀN TỪ, không phải trắc nghiệm.
        warnings.append(f"Word form không có lựa chọn A/B/C/D, đang có {len(options)} lựa chọn.")
    sentence, root = split_bracket_root(prompt_text or "")
    family = word_family_label(target_knowledge)

    blanks = len(BLANK_RE.findall(sentence))
    if blanks != 1:
        warnings.append(f"Câu phải có đúng 1 chỗ trống ______, đang có {blanks}.")

    answer = (answer_text or "").strip()
    if not answer:
        warnings.append("Thiếu answer_text.")
    elif len(answer.split()) != 1:
        warnings.append(f"answer_text phải là 1 từ duy nhất, đang là '{answer}'.")

    if kind == "family":
        # Đáp án phải là MỘT TỪ TRONG chính họ từ đã giao. Trước đây chỉ kiểm
        # target_knowledge có đúng định dạng chuỗi họ từ hay không, còn đáp án thì
        # không ai đối chiếu — model trả họ từ 'adore → adorable → adorably' rồi đáp án
        # 'beautiful' vẫn lọt sạch, mà nhìn đề không thấy gì bất thường vì dòng ❖ và
        # câu hỏi đều hợp lệ.
        members = word_family_members(target_knowledge)
        if answer and members and not _in_family(answer, members):
            warnings.append(
                f"Đáp án '{answer}' không thuộc họ từ được giao ({target_knowledge})."
            )
        if family is None:
            warnings.append(
                "Kiểu (A): target_knowledge phải là chuỗi họ từ dạng "
                "'adore (v) → adorable (adj) → adorably (adv)', đang là "
                f"'{target_knowledge}'."
            )
        if root:
            warnings.append(f"Kiểu (A) không đặt từ gốc trong ngoặc ở cuối câu, đang có '({root})'.")
    elif kind == "bracket":
        if root is None:
            warnings.append("Kiểu (B): câu phải kết thúc bằng từ gốc trong ngoặc, vd '... games. (adorable)'.")
        elif answer and root.lower() == answer.lower():
            warnings.append(f"Từ gốc '({root})' trùng hệt đáp án — học sinh chỉ cần chép lại.")
        # Phần B ôn lại đúng các họ từ của Phần A — từ ngoài họ từ đó là lạc đề
        # (đề thật 24/08/2026: 7/15 câu dùng '(benefit)' chẳng dính dáng gì Phần A).
        members = word_family_members(allowed_family)
        if root and members and root.lower() not in members:
            warnings.append(
                f"Từ gốc '({root})' không thuộc họ từ được giao ({allowed_family})."
            )
        if family is not None:
            warnings.append("Kiểu (B): target_knowledge mô tả bằng lời, không viết thành chuỗi họ từ.")

    if "<u>" in (prompt_text or ""):
        warnings.append("Câu word form không dùng markup <u>...</u>.")
    return warnings
