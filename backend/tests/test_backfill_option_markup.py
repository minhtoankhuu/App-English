"""Test logic làm sạch nhân đôi đuôi trong option đã lưu (app/backfill_option_markup)."""

from app.backfill_option_markup import _fixed_options


def test_fixes_doubled_suffix_options():
    options = [
        {"label": "A", "text": "cats<u>s</u>", "is_correct": False},
        {"label": "B", "text": "dogs<u>s</u>", "is_correct": True},
    ]
    fixed, changed = _fixed_options(options)
    assert changed is True
    assert fixed[0]["text"] == "cat<u>s</u>"
    assert fixed[1]["text"] == "dog<u>s</u>"
    # giữ nguyên các trường khác
    assert fixed[1]["is_correct"] is True


def test_leaves_correct_options_untouched():
    options = [
        {"label": "A", "text": "star<u>s</u>", "is_correct": False},
        {"label": "B", "text": "want<u>ed</u>", "is_correct": True},
    ]
    fixed, changed = _fixed_options(options)
    assert changed is False
    assert fixed == options


def test_handles_none_and_empty():
    assert _fixed_options(None) == (None, False)
    assert _fixed_options([]) == ([], False)


def test_options_without_text_key_are_safe():
    options = [{"label": "A"}]
    fixed, changed = _fixed_options(options)
    assert changed is False
    assert fixed == options
