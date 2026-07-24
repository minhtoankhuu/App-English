"""Test sanitizer chống nhân đôi ký tự đuôi phát âm — các ca lấy đúng từ dữ liệu thật
model sinh ra (dump từ DB, block PRONUNCIATION GS9/GS7)."""

import pytest

from app.services.text_markup import dedupe_pronunciation_suffix


@pytest.mark.parametrize(
    "raw, expected",
    [
        # -s bị nhân đôi (gốc đã có đuôi + bọc lại)
        ("cats<u>s</u>", "cat<u>s</u>"),
        ("dogs<u>s</u>", "dog<u>s</u>"),
        ("books<u>s</u>", "book<u>s</u>"),
        ("games<u>s</u>", "game<u>s</u>"),
        ("hikes<u>s</u>", "hike<u>s</u>"),
        ("bikes<u>s</u>", "bike<u>s</u>"),
        ("pens<u>s</u>", "pen<u>s</u>"),
        ("kittens<u>s</u>", "kitten<u>s</u>"),
        ("friends<u>s</u>", "friend<u>s</u>"),
        ("cousins<u>s</u>", "cousin<u>s</u>"),
        ("sisters<u>s</u>", "sister<u>s</u>"),
        # -es bị nhân đôi
        ("dresses<u>es</u>", "dress<u>es</u>"),
        ("houses<u>es</u>", "hous<u>es</u>"),
        # gốc kết thúc 'ss' → sửa luôn đuôi thành 'es' (classes/glasses)
        ("class<u>s</u>", "class<u>es</u>"),
        ("glass<u>s</u>", "glass<u>es</u>"),
        # -ed bị nhân đôi
        ("cooked<u>ed</u>", "cook<u>ed</u>"),
    ],
)
def test_fixes_doubled_suffix(raw, expected):
    assert dedupe_pronunciation_suffix(raw) == expected


@pytest.mark.parametrize(
    "correct",
    [
        # option đúng — không được đụng vào
        "star<u>s</u>",
        "wish<u>es</u>",
        "want<u>ed</u>",
        "play<u>ed</u>",
        "look<u>ed</u>",
        "decid<u>ed</u>",
        "marr<u>ied</u>",
        "miss<u>ed</u>",
        # gốc tự thân kết thúc 'ed' — needed/seeded đúng chính tả, KHÔNG cắt thành 'ne<u>ed</u>'
        "need<u>ed</u>",
        "seed<u>ed</u>",
        # dạng so sánh âm giữa từ (marker không ở cuối)
        "t<u>ea</u>m",
        "br<u>ea</u>d",
        "cl<u>ea</u>n",
        # dạng trọng âm (âm tiết ở cuối nhưng không phải đuôi lặp)
        "be<u>gin</u>",
        # không có markup
        "computer",
    ],
)
def test_keeps_correct_options_unchanged(correct):
    assert dedupe_pronunciation_suffix(correct) == correct


def test_no_markup_returns_input():
    assert dedupe_pronunciation_suffix("plain text") == "plain text"
