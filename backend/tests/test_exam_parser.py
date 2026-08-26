"""Test tách đề thi thật thành câu mẫu (app/services/exam_parser.py).

Ca lấy nguyên văn từ đề thật "8. GS. UNIT 1 REVISION EXERCISES.docx" chủ dự án gửi.
Hàm thuần nên không cần file .docx hay DB.
"""

import pytest

from app.services.exam_parser import (
    instruction_exercise_type,
    normalize_family_line,
    parse_exam_items,
    section_exercise_type,
)

TAB = chr(9)
NL = chr(10)


@pytest.mark.parametrize(
    "heading, expected",
    [
        ("PRONUNCIATION", "pronunciation"),
        ("VOCABULARY AND GRAMMAR", "multiple_choice"),
        ("WORD FORMATION", "word_form"),
        ("TRANSFORMATION PATTERNS", "sentence_rewrite"),
        ("READING COMPREHENSION", "reading_true_false"),
        ("SIGNS/ PICTURES", "sign_reading"),
        ("WORD ENTRY", None),  # dạng đề thật chưa có trong hệ thống
    ],
)
def test_section_exercise_type(heading, expected):
    assert section_exercise_type(heading) == expected


def test_instruction_line_refines_the_type_inside_a_section():
    """Đề thật đặt cả phát âm lẫn trọng âm trong "I. PRONUNCIATION"; chỉ dòng câu lệnh
    giữa mục mới phân biệt được."""
    assert instruction_exercise_type("Which word had a different stress pattern from that of the others?") == "stress"
    assert instruction_exercise_type("Which word has the underlined part pronounced differently?") == "pronunciation"
    assert instruction_exercise_type("1. A. crazy B. cruel") is None


def test_stress_questions_are_not_labelled_as_pronunciation():
    items = parse_exam_items([
        "I. PRONUNCIATION",
        "Which word has the underlined part pronounced differently from that of the others?",
        f"1. A. puzzles{TAB}B. messages{TAB}C. puddings{TAB}D. flowers",
        "Which word had a different stress pattern from that of the others?",
        f"1. A. crazy{TAB}B. cruel{TAB}C. leisure{TAB}D. resort",
    ])
    assert [i.exercise_type_code for i in items] == ["pronunciation", "stress"]


def test_dialogue_question_keeps_both_turns_and_options():
    items = parse_exam_items([
        "II. VOCABULARY AND GRAMMAR",
        "Prepositions and Phrases: Choose the word that best fits the space.",
        "1. Minh Khoa: Why does Duc Minh always join the school football club?",
        "    Bao Han: Because he's really crazy _______ sports and loves playing.",
        f"A. for {TAB}B. about{TAB}C. on {TAB}D. with",
    ])
    assert len(items) == 1
    assert items[0].exercise_type_code == "multiple_choice"
    assert items[0].text.count(NL) == 2
    assert items[0].text.startswith("Minh Khoa: Why does")
    assert items[0].text.endswith("D. with")


def test_word_form_family_line_is_attached_to_every_question_of_the_group():
    items = parse_exam_items([
        "III. WORD FORMATION",
        "Fill in the blanks with the correct form of the words",
        "adore (v)  adorable (adj)  adorably (adv)",
        "My little sister __________ her teddy bear before going to bed at night.",
        "The puppies were extremely __________ and made everyone smile happily.",
    ])
    assert len(items) == 2
    assert all(i.text.startswith("adore (v) → adorable (adj) → adorably (adv)") for i in items)


def test_family_line_arrows_are_restored():
    """Word lưu mũi tên bằng ký tự symbol nên python-docx đọc ra khoảng trắng; mẫu phải
    đúng định dạng mình muốn model sinh ra."""
    assert normalize_family_line("adore (v)  adorable (adj)  adorably (adv)") == (
        "adore (v) → adorable (adj) → adorably (adv)"
    )
    assert normalize_family_line("chỉ một mục (n)") == "chỉ một mục (n)"


def test_orphan_option_lines_of_a_cloze_are_dropped():
    """Dòng lựa chọn của cloze tách rời khỏi đoạn văn thì vô nghĩa làm mẫu."""
    items = parse_exam_items([
        "V. READING COMPREHENSION",
        "Choose the word (A, B, C or D) that best fits the space in the following passage.",
        "Many teenagers enjoy spending their free time with friends near the park every day.",
        f"1. {TAB}A. cinema{TAB}B. room{TAB}C. station{TAB}D. subject",
    ])
    assert [i.exercise_type_code for i in items] == ["cloze_test"]
    assert items[0].text.startswith("Many teenagers")


def test_lines_before_the_first_section_are_ignored():
    items = parse_exam_items(["UNIT 1 REVISION EXERCISES – GLOBAL SUCCESS 8", "Full name: ......"])
    assert items == []


def test_short_fragments_are_dropped():
    items = parse_exam_items(["I. PRONUNCIATION", "1. A. a", "2. abc"])
    assert items == []
