"""Test kho câu mẫu chèn vào system prompt (prompts.example_block).

Sách Global Success gần như không có câu ví dụ (GS7 Unit 1: 2/231 đoạn), nên model
không có gì để bắt chước — kho này bù vào chỗ đó.
"""

import pytest

from app.services.mcq_check import _looks_copied, check_multiple_choice
from app.services.prompts import (
    MULTIPLE_CHOICE_EXAMPLES,
    WORD_FORM_BRACKET_EXAMPLES,
    WORD_FORM_FAMILY_EXAMPLES,
    _EXAMPLES_PER_CALL,
    build_system_prompt,
    example_block,
)

NL = chr(10)


def test_multiple_choice_prompt_carries_examples():
    text = build_system_prompt("multiple_choice", 5, "A2", example_offset=0)
    assert "CÂU MẪU" in text
    assert MULTIPLE_CHOICE_EXAMPLES[0] in text


def test_only_a_subset_is_sent_each_call():
    """Đưa hết thì prompt phình và model bị kéo về một khuôn duy nhất."""
    block = example_block("multiple_choice", offset=0)
    present = [e for e in MULTIPLE_CHOICE_EXAMPLES if e in block]
    assert len(present) == _EXAMPLES_PER_CALL < len(MULTIPLE_CHOICE_EXAMPLES)


def test_offset_rotates_through_the_whole_bank():
    seen: set[str] = set()
    for offset in range(len(MULTIPLE_CHOICE_EXAMPLES)):
        seen.update(e for e in MULTIPLE_CHOICE_EXAMPLES if e in example_block("multiple_choice", offset))
    assert seen == set(MULTIPLE_CHOICE_EXAMPLES)


def test_offset_wraps_around_the_end():
    block = example_block("multiple_choice", offset=len(MULTIPLE_CHOICE_EXAMPLES) - 1)
    assert MULTIPLE_CHOICE_EXAMPLES[-1] in block
    assert MULTIPLE_CHOICE_EXAMPLES[0] in block


def test_random_offset_is_not_always_the_same():
    blocks = {example_block("multiple_choice") for _ in range(30)}
    assert len(blocks) > 1


def test_word_form_bank_covers_both_kinds():
    seen = set()
    for offset in range(len(WORD_FORM_FAMILY_EXAMPLES) + len(WORD_FORM_BRACKET_EXAMPLES)):
        seen.add(example_block("word_form", offset))
    joined = " ".join(seen)
    assert WORD_FORM_FAMILY_EXAMPLES[0] in joined
    assert WORD_FORM_BRACKET_EXAMPLES[0] in joined


@pytest.mark.parametrize("code", ["stress", "pronunciation", "reading_true_false"])
def test_types_without_a_bank_get_no_example_block(code):
    assert example_block(code) == ""
    assert "CÂU MẪU" not in build_system_prompt(code, 5, "A2")


# --- bộ kiểm lấy danh sách cấm chép từ chính kho mẫu -------------------------


@pytest.mark.parametrize("example", MULTIPLE_CHOICE_EXAMPLES)
def test_every_bank_example_is_detected_if_copied(example):
    """Thêm mẫu mới là tự động được bảo vệ, không phải nhớ cập nhật hai nơi."""
    prompt = NL.join(line for line in example.split(NL) if not line.startswith("A. "))
    assert _looks_copied(prompt)


def test_copied_example_raises_a_warning():
    prompt = NL.join(MULTIPLE_CHOICE_EXAMPLES[1].split(NL)[:2])
    warnings = check_multiple_choice(prompt, None)
    assert any("chép lại ví dụ mẫu" in w for w in warnings)


def test_ordinary_question_is_not_flagged_as_copied():
    prompt = f"Gia Linh: What hobby does Nam have?{NL}Bao Han: He likes ______ teddy bears."
    assert not _looks_copied(prompt)
    assert check_multiple_choice(prompt, None) == []


def test_old_prompt_examples_still_flagged():
    """Đề sinh bằng prompt cũ vẫn còn trong DB."""
    assert _looks_copied("Solar energy is a ______ source of energy.")


# --- câu mẫu từ đề thật được ưu tiên hơn kho viết tay ------------------------


def test_real_exam_examples_replace_the_handwritten_bank():
    """Câu mẫu của đúng Unit bám sát chủ đề và độ khó của bài đang ra đề."""
    real = ["Thanh Tai: Some teenagers are addicted ______ fast food.\nHai Nam: Yes.\nA. to  B. in"]
    text = build_system_prompt("multiple_choice", 5, "A2", example_offset=0, examples=real)

    assert real[0] in text
    assert not any(e in text for e in MULTIPLE_CHOICE_EXAMPLES)


def test_falls_back_to_the_bank_when_the_unit_has_no_real_exam():
    """Unit chưa nạp đề thật không được bỏ trắng phần câu mẫu."""
    text = build_system_prompt("multiple_choice", 5, "A2", example_offset=0, examples=[])
    assert MULTIPLE_CHOICE_EXAMPLES[0] in text
