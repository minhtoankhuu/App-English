"""Test kiểm tra chất lượng câu trắc nghiệm VOCABULARY AND GRAMMAR
(app/services/mcq_check.py). Ca lấy từ đề sinh thử thật 07/08/2026."""

import pytest

from app.services.mcq_check import blank_count, check_multiple_choice

OPTS = [
    {"label": "A", "text": "contact", "is_correct": True},
    {"label": "B", "text": "contacts", "is_correct": False},
    {"label": "C", "text": "contacting", "is_correct": False},
    {"label": "D", "text": "contacted", "is_correct": False},
]


def _joined(ws):
    return " | ".join(ws)


@pytest.mark.parametrize(
    "text, expected",
    [("a ______ b", 1), ("a ______ b ______ c", 2), ("no blank", 0), ("dùng _______ 7 gạch", 1), (None, 0)],
)
def test_blank_count(text, expected):
    assert blank_count(text) == expected


def test_flags_two_blanks_in_dialogue():
    """Lỗi thật: model đặt chỗ trống ở CẢ lượt hỏi và lượt trả lời."""
    text = "Minh Khoa: How do you ______ with friends?\nBao Han: I keep in ______ online."
    assert "đúng 1 chỗ trống" in _joined(check_multiple_choice(text, OPTS))


def test_flags_missing_blank():
    assert "đúng 1 chỗ trống" in _joined(check_multiple_choice("What does 'in person' mean?", OPTS))


def test_flags_copied_prompt_example():
    """Lỗi thật: model chép nguyên câu ví dụ trong hướng dẫn vào đề của Unit khác."""
    assert "chép lại ví dụ mẫu" in _joined(
        check_multiple_choice("Solar energy is a ______ source of energy.", OPTS)
    )


def test_valid_question_has_no_warning():
    assert check_multiple_choice("Bao Han: I often keep in ______ through social media.", OPTS) == []
    assert check_multiple_choice("My friends and I often ______ on social media.", OPTS) == []


def test_flags_wrong_option_count_and_correct_count():
    assert "đúng 4 lựa chọn" in _joined(check_multiple_choice("a ______ b", OPTS[:3]))
    two_correct = [{**o, "is_correct": i < 2} for i, o in enumerate(OPTS)]
    assert "đúng 1 đáp án đúng" in _joined(check_multiple_choice("a ______ b", two_correct))


def test_flags_duplicate_options():
    dup = [{**o, "text": "contact"} for o in OPTS]
    assert "trùng nhau" in _joined(check_multiple_choice("a ______ b", dup))


def test_options_none_is_skipped():
    assert check_multiple_choice("a ______ b", None) == []
