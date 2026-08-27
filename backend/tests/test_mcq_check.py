"""Test kiểm tra chất lượng câu trắc nghiệm VOCABULARY AND GRAMMAR
(app/services/mcq_check.py). Ca lấy từ đề sinh thử thật 07/08/2026."""

import pytest

from app.services.mcq_check import blank_count, check_multiple_choice, is_two_turn_dialogue

# Phần này chỉ ra đề hội thoại (chốt 24/08/2026) — câu mẫu hợp lệ dùng chung cho các ca dưới.
DIALOGUE = "Gia Linh: How do you keep in touch with your old friends?\nBao Han: I often keep in ______ through social media."

OPTS = [
    {"label": "A", "text": "contact", "is_correct": True, "why_wrong": None},
    {"label": "B", "text": "contacts", "is_correct": False, "why_wrong": "sai chia động từ"},
    {"label": "C", "text": "contacting", "is_correct": False, "why_wrong": "sai dạng V-ing"},
    {"label": "D", "text": "contacted", "is_correct": False, "why_wrong": "sai thì"},
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
    assert check_multiple_choice(DIALOGUE, OPTS) == []


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Gia Linh: What hobby does Nam have?%sBao Han: He likes ______ teddy bears." % chr(10), True),
        ("A: Do you have any hobbies?%sB: Yes, I would love ______ a dollhouse." % chr(10), True),
        # câu đơn — không còn được dùng ở phần này nữa
        ("My sister loves ______ in her free time.", False),
        ("Gardening is a popular ______ for many people.", False),
        # chỉ 1 lượt có tên -> chưa phải hội thoại 2 lượt
        ("Bao Han: I often keep in ______ through social media.", False),
        ("", False),
        (None, False),
    ],
)
def test_is_two_turn_dialogue(text, expected):
    assert is_two_turn_dialogue(text) is expected


def test_flags_single_sentence_question():
    """Đề thật 24/08/2026 còn lọt câu đơn ('My sister loves ______ in her free time.')
    xen giữa các câu hội thoại — phần này chỉ ra đề hội thoại."""
    warnings = _joined(check_multiple_choice("My sister loves ______ in her free time.", OPTS))
    assert "HỘI THOẠI 2 LƯỢT" in warnings


def test_flags_wrong_option_count_and_correct_count():
    assert "đúng 4 lựa chọn" in _joined(check_multiple_choice(DIALOGUE, OPTS[:3]))
    two_correct = [{**o, "is_correct": i < 2} for i, o in enumerate(OPTS)]
    assert "đúng 1 đáp án đúng" in _joined(check_multiple_choice(DIALOGUE, two_correct))


def test_flags_duplicate_options():
    dup = [{**o, "text": "contact"} for o in OPTS]
    assert "trùng nhau" in _joined(check_multiple_choice(DIALOGUE, dup))


def test_options_none_is_skipped():
    assert check_multiple_choice(DIALOGUE, None) == []


def test_flags_distractor_without_justification():
    """Không giải trình được vì sao phương án nhiễu sai -> nhiều khả năng nó CŨNG ĐÚNG."""
    no_reason = [dict(o, why_wrong=None) if not o["is_correct"] else o for o in OPTS]
    assert "Chưa nêu được vì sao" in _joined(check_multiple_choice(DIALOGUE, no_reason))

    # chỉ thiếu ở 1 phương án cũng phải báo, và nêu đúng nhãn
    partial = [dict(o, why_wrong=None) if o["label"] == "C" else o for o in OPTS]
    text = _joined(check_multiple_choice(DIALOGUE, partial))
    assert "phương án C" in text


def test_blank_why_wrong_on_correct_option_is_fine():
    """Đáp án đúng để why_wrong = null là hợp lệ, không được cảnh báo."""
    assert check_multiple_choice(DIALOGUE, OPTS) == []


# --- model nhét cả lượt trả lời vào lựa chọn (đề sinh thử 24/08/2026) --------

ANSWER_TURN_AS_OPTIONS = [
    {"label": lb, "text": t, "is_correct": i == 0, "why_wrong": None if i == 0 else "x"}
    for i, (lb, t) in enumerate(zip("ABCD", [
        "We enjoy the show and ______ with friends.",
        "We enjoy the show and ______ gifts.",
        "We enjoy the show and ______ dance.",
        "We enjoy the show and ______ fireworks.",
    ]))
]
ONE_TURN = "Khanh Ngoc: What do we usually do at the firework festival?"


def test_flags_blank_left_inside_options():
    """Chỗ trống nằm trong lựa chọn -> không câu nào là đáp án thật."""
    assert "còn chứa chỗ trống" in _joined(check_multiple_choice(ONE_TURN, ANSWER_TURN_AS_OPTIONS))


def test_flags_options_sharing_a_long_prefix():
    assert "lặp chung" in _joined(check_multiple_choice(ONE_TURN, ANSWER_TURN_AS_OPTIONS))


def test_flags_options_that_are_full_sentences():
    assert "dài quá" in _joined(check_multiple_choice(ONE_TURN, ANSWER_TURN_AS_OPTIONS))


def test_short_options_sharing_a_word_are_fine():
    """Lựa chọn cùng dạng chia của một động từ vẫn hợp lệ, không được báo oan."""
    opts = [
        {"label": lb, "text": t, "is_correct": i == 0, "why_wrong": None if i == 0 else "x"}
        for i, (lb, t) in enumerate(zip("ABCD", ["take part in", "take care of", "take off", "take up"]))
    ]
    warnings = _joined(check_multiple_choice(DIALOGUE, opts))
    assert "lặp chung" not in warnings
    assert "dài quá" not in warnings


def _opts4(words, correct=0):
    return [
        {"label": lb, "text": t, "is_correct": i == correct, "why_wrong": None if i == correct else "x"}
        for i, (lb, t) in enumerate(zip("ABCD", words))
    ]


def test_options_repeating_a_noun_from_the_sentence_are_caught():
    """Đề sinh 27/08/2026: "I like to ______ old coins from different countries." với 4
    lựa chọn "collect coin / buy coins / sell coins / look coins" — điền vào thành "I
    like to collect coin old coins...". Bộ kiểm cũ chỉ dò phần lặp ở ĐẦU các lựa chọn
    nên không thấy phần lặp nằm ở đuôi."""
    prompt = (
        "Tu Anh: What hobby do you have?" + chr(10)
        + "Phuc Hung: I like to ______ old coins from different countries."
    )
    warnings = check_multiple_choice(prompt, _opts4(["collect coin", "buy coins", "sell coins", "look coins"]))

    assert any("nhắc lại từ đã có sẵn" in w for w in warnings)


def test_one_option_sharing_a_word_with_the_sentence_is_allowed():
    """Một lựa chọn trùng từ với câu dẫn có thể là bẫy cố ý — chỉ báo khi đa số cùng lặp."""
    prompt = (
        "Minh Khoa: What do you like to do in your free time?" + chr(10)
        + "Gia Linh: I enjoy ______ because it helps me relax and have fun."
    )
    warnings = check_multiple_choice(prompt, _opts4(["gardening", "cleaning", "studying", "relaxing"]))

    assert not any("nhắc lại từ đã có sẵn" in w for w in warnings)


def test_a_blank_in_the_first_turn_is_not_a_defect():
    """Đo 1.625 câu hội thoại của đề thật: 56% đặt chỗ trống ở lượt 1, 43% ở lượt 2."""
    prompt = (
        "Ngoc Bich: Do you enjoy ______ with your family?" + chr(10)
        + "Minh Hoang: Yes! We often go to the garden together."
    )

    assert check_multiple_choice(prompt, _opts4(["gardening", "watching TV", "doing chores", "playing games"])) == []
