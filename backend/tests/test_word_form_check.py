"""Test bộ kiểm câu WORD FORMATION bằng code — nguồn feedback cho pipeline tự sinh lại."""

import pytest

from app.services.word_form_check import check_word_form, detect_word_form_kind

FAMILY = "adore (v) → adorable (adj) → adorably (adv)"


@pytest.mark.parametrize(
    "prompt_override, expected",
    [
        ("Chỉ dùng kiểu (A) nhóm theo họ từ cho toàn bộ các câu.", "family"),
        ("Chỉ dùng kiểu (B) từ gốc trong ngoặc ở cuối câu cho toàn bộ các câu.", "bracket"),
        # giáo viên tự nhập, không có mã kiểu
        ("gom các câu theo họ từ", "family"),
        ("đặt từ gốc trong ngoặc cuối câu", "bracket"),
        (None, None),
        ("", None),
    ],
)
def test_detect_kind(prompt_override, expected):
    assert detect_word_form_kind(prompt_override) == expected


def test_valid_family_question_has_no_warning():
    assert check_word_form(
        "My little sister ______ her teddy bear before going to bed at night.",
        "adores",
        FAMILY,
        kind="family",
    ) == []


def test_valid_bracket_question_has_no_warning():
    assert check_word_form(
        "Many teenagers really ______ playing online games at night. (adorable)",
        "adore",
        "Chuyển tính từ sang động từ",
        kind="bracket",
    ) == []


def test_family_kind_requires_word_family_target_knowledge():
    warnings = check_word_form("She smiled ______ at the gift.", "adorably", "Word form: adj → adv", kind="family")
    assert any("chuỗi họ từ" in w for w in warnings)


def test_family_kind_rejects_bracket_root():
    """Kiểu (A) đã in họ từ ở dòng ❖ — thêm từ gốc vào cuối câu là thừa và lộ đáp án."""
    warnings = check_word_form("She smiled ______ at the gift. (adore)", "adorably", FAMILY, kind="family")
    assert any("không đặt từ gốc trong ngoặc" in w for w in warnings)


def test_bracket_kind_requires_root():
    warnings = check_word_form("Many teenagers really ______ games.", "adore", "x", kind="bracket")
    assert any("kết thúc bằng từ gốc trong ngoặc" in w for w in warnings)


def test_bracket_root_must_differ_from_answer():
    """Bug thật hay gặp: model để (adore) rồi đáp án cũng là 'adore' — chép lại là xong."""
    warnings = check_word_form("Many teenagers really ______ games. (adore)", "adore", "x", kind="bracket")
    assert any("trùng hệt đáp án" in w for w in warnings)


def test_bracket_kind_rejects_word_family_target_knowledge():
    warnings = check_word_form("Many teenagers ______ games. (adorable)", "adore", FAMILY, kind="bracket")
    assert any("không viết thành chuỗi họ từ" in w for w in warnings)


@pytest.mark.parametrize("prompt, count", [
    ("No blank at all here.", 0),
    ("Two ______ blanks ______ here.", 2),
])
def test_blank_count(prompt, count):
    warnings = check_word_form(prompt, "adore", FAMILY, kind="family")
    assert any(f"đang có {count}" in w for w in warnings)


def test_answer_must_be_single_word():
    warnings = check_word_form("She is ______ about it.", "very adorable", FAMILY, kind="family")
    assert any("1 từ duy nhất" in w for w in warnings)


def test_rejects_underline_markup():
    warnings = check_word_form("She <u>smiled</u> ______ .", "adorably", FAMILY, kind="family")
    assert any("<u>" in w for w in warnings)


def test_unknown_kind_only_checks_shared_rules():
    """Không rõ kiểu (giáo viên tự nhập) — chỉ kiểm luật chung, không ép kiểu nào."""
    assert check_word_form("She smiled ______ at the gift.", "adorably", "mô tả tự do", kind=None) == []


def test_answer_outside_the_given_word_family_is_caught():
    """Kiểu (A) trước đây chỉ kiểm target_knowledge có đúng định dạng chuỗi họ từ, còn
    đáp án thì không ai đối chiếu — họ từ 'adore → adorable → adorably' mà đáp án
    'beautiful' vẫn lọt, nhìn đề không thấy gì bất thường."""
    family = "adore (v) → adorable (adj) → adorably (adv)"
    warnings = check_word_form("The puppy was very ______.", "beautiful", family, kind="family")

    assert any("không thuộc họ từ" in w for w in warnings)


def test_answer_inside_the_family_passes():
    family = "adore (v) → adorable (adj) → adorably (adv)"

    assert check_word_form("The puppy was very ______.", "adorable", family, kind="family") == []
    # Viết hoa đầu câu vẫn hợp lệ
    assert check_word_form("______ the puppy!", "Adore", family, kind="family") == []
