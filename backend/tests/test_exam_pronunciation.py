"""Test dựng câu phát âm/trọng âm từ đề thi thật (app/services/exam_pronunciation.py).

Ca lấy nguyên văn từ các đề chủ dự án nạp vào Knowledge_Base/Exams/.
"""

import pytest

from app.services.exam_pronunciation import (
    build_from_exam_items,
    line_kind,
    odd_one_out,
    parse_option_line,
)

TAB = chr(9)

VOWEL_LINE = f"A. m<u>u</u>scle{TAB}B. s<u>u</u>gar{TAB}C. p<u>u</u>zzle{TAB}D. h<u>u</u>nting"
STRESS_LINE = f"A. relation{TAB}B. relative{TAB}C. dependence{TAB}D. description"
ENDING_LINE = f"A. book<u>s</u>{TAB}B. cup<u>s</u>{TAB}C. dog<u>s</u>{TAB}D. map<u>s</u>"
ED_LINE = f"A. work<u>ed</u>{TAB}B. want<u>ed</u>{TAB}C. wash<u>ed</u>{TAB}D. help<u>ed</u>"


def test_parse_option_line_keeps_underline_markup():
    assert parse_option_line(VOWEL_LINE) == [
        "m<u>u</u>scle", "s<u>u</u>gar", "p<u>u</u>zzle", "h<u>u</u>nting"
    ]


@pytest.mark.parametrize(
    "line",
    [
        "A. only  B. two",
        "Minh Khoa: a question with no options at all here.",
        f"A. one{TAB}B. two{TAB}C. three",
    ],
)
def test_parse_option_line_rejects_incomplete_lines(line):
    assert parse_option_line(line) is None


def test_odd_one_out_by_vowel_sound():
    assert odd_one_out(parse_option_line(VOWEL_LINE), is_pronunciation=True) == 1  # sugar


def test_odd_one_out_by_ending_sound():
    assert odd_one_out(parse_option_line(ENDING_LINE), is_pronunciation=True) == 2  # dogs /z/


def test_odd_one_out_by_stress_position():
    assert odd_one_out(parse_option_line(STRESS_LINE), is_pronunciation=False) == 1  # relative


def test_odd_one_out_gives_up_on_a_two_two_split():
    """Thế 2-2 nghĩa là ta đọc sai âm hoặc đề gõ sai — thà bỏ còn hơn ra đáp án bịa."""
    line = f"A. book<u>s</u>{TAB}B. cup<u>s</u>{TAB}C. dog<u>s</u>{TAB}D. pen<u>s</u>"
    assert odd_one_out(parse_option_line(line), is_pronunciation=True) is None


def test_odd_one_out_gives_up_when_a_word_is_unknown():
    line = f"A. laugh<u>s</u>{TAB}B. plough<u>s</u>{TAB}C. month<u>s</u>{TAB}D. bathe<u>s</u>"
    assert odd_one_out(parse_option_line(line), is_pronunciation=True) is None


def test_build_marks_the_odd_option_as_the_answer():
    drafts = build_from_exam_items([VOWEL_LINE], is_pronunciation=True, count=5, seed=1)

    assert len(drafts) == 1
    correct = [o for o in drafts[0].options if o["is_correct"]]
    assert [o["label"] for o in correct] == ["B"]
    assert drafts[0].answer_text == "B. sugar"


def test_build_stress_questions_carry_no_underline():
    drafts = build_from_exam_items([STRESS_LINE], is_pronunciation=False, count=5, seed=1)

    assert len(drafts) == 1
    assert all("<u>" not in o["text"] for o in drafts[0].options)


def test_build_skips_lines_it_cannot_resolve():
    unresolvable = f"A. laugh<u>s</u>{TAB}B. plough<u>s</u>{TAB}C. month<u>s</u>{TAB}D. bathe<u>s</u>"
    drafts = build_from_exam_items([unresolvable, VOWEL_LINE], is_pronunciation=True, count=5, seed=1)

    assert len(drafts) == 1


def test_build_does_not_repeat_the_same_group():
    drafts = build_from_exam_items([VOWEL_LINE, VOWEL_LINE], is_pronunciation=True, count=5, seed=1)
    assert len(drafts) == 1


def test_build_respects_the_requested_count():
    drafts = build_from_exam_items(
        [VOWEL_LINE, ENDING_LINE], is_pronunciation=True, count=1, seed=1
    )
    assert len(drafts) == 1


def test_build_returns_nothing_without_exam_items():
    assert build_from_exam_items([], is_pronunciation=True, count=5) == []


def test_line_kind_separates_the_three_pronunciation_shapes():
    assert line_kind(parse_option_line(ENDING_LINE)) == "s"
    assert line_kind(parse_option_line(ED_LINE)) == "ed"
    assert line_kind(parse_option_line(VOWEL_LINE)) == "vowel"


def test_build_only_takes_lines_of_the_requested_kind():
    """Phần con ghim kiểu nào chỉ được bốc câu kiểu đó — không lọc thì cả ba phần con
    lấy chung một rổ và ra đề trộn lẫn đuôi -s/-es với -ed với nguyên âm."""
    drafts = build_from_exam_items(
        [ENDING_LINE, ED_LINE, VOWEL_LINE], is_pronunciation=True, count=3, kind="ed"
    )

    assert len(drafts) == 1
    assert [o["text"] for o in drafts[0].options] == parse_option_line(ED_LINE)


def test_build_prompt_names_the_kind_of_the_part():
    by_kind = {
        k: build_from_exam_items([line], is_pronunciation=True, count=1, kind=k)[0].prompt_text
        for k, line in (("s", ENDING_LINE), ("ed", ED_LINE), ("vowel", VOWEL_LINE))
    }

    assert "-s/-es" in by_kind["s"]
    assert "-ed" in by_kind["ed"]
    assert "underlined part" in by_kind["vowel"]
    assert len(set(by_kind.values())) == 3


def test_build_skips_groups_already_used_by_an_earlier_part():
    """Rổ câu đọc được của một Unit chỉ vài câu mỗi kiểu, nên phần con sau phải biết
    phần con trước đã dùng nhóm nào."""
    used = {frozenset(parse_option_line(VOWEL_LINE))}
    drafts = build_from_exam_items(
        [VOWEL_LINE], is_pronunciation=True, count=1, kind="vowel", exclude=used
    )

    assert drafts == []


def test_build_does_not_mutate_the_exclude_set_it_was_given():
    used: set[frozenset[str]] = set()
    build_from_exam_items([VOWEL_LINE], is_pronunciation=True, count=1, exclude=used)

    assert used == set()
