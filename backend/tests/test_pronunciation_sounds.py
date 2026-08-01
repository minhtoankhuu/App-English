"""Test luật suy âm đuôi -s/-es và -ed từ chính tả (app/services/pronunciation_sounds.py)
và kiểm tra quy tắc "3 từ giống - 1 từ khác". Ca lấy từ đề thật ngày 24/07/2026."""

import pytest

from app.services.pronunciation_check import check_pronunciation_options
from app.services.pronunciation_sounds import ed_ending_sound, ending_sounds, s_ending_sound


@pytest.mark.parametrize(
    "word, expected",
    [
        # /ɪz/ sau âm xuýt
        ("voices", "iz"), ("languages", "iz"), ("watches", "iz"), ("boxes", "iz"),
        ("buses", "iz"), ("wishes", "iz"), ("classes", "iz"), ("dresses", "iz"),
        ("houses", "iz"), ("faces", "iz"),
        # /s/ sau phụ âm vô thanh (kể cả 'e' câm)
        ("types", "s"), ("separates", "s"), ("shoots", "s"), ("magics", "s"),
        ("books", "s"), ("cats", "s"), ("stops", "s"),
        # /z/ sau âm hữu thanh/nguyên âm
        ("twins", "z"), ("overalls", "z"), ("films", "z"), ("rings", "z"),
        ("endings", "z"), ("saves", "z"), ("destructions", "z"), ("dogs", "z"),
        ("toys", "z"), ("tries", "z"), ("goes", "z"),
    ],
)
def test_s_ending_sound(word, expected):
    assert s_ending_sound(word) == expected


@pytest.mark.parametrize(
    "word, expected",
    [
        # /ɪd/ sau /t/, /d/
        ("wanted", "id"), ("visited", "id"), ("decided", "id"), ("needed", "id"),
        ("directed", "id"), ("adapted", "id"), ("illustrated", "id"), ("destructed", "id"),
        # /t/ sau phụ âm vô thanh
        ("escaped", "t"), ("worked", "t"), ("talked", "t"), ("cooked", "t"),
        ("washed", "t"), ("watched", "t"), ("fixed", "t"), ("missed", "t"),
        ("jumped", "t"), ("stopped", "t"), ("danced", "t"),
        # /d/ sau âm hữu thanh/nguyên âm
        ("saved", "d"), ("loved", "d"), ("learned", "d"), ("played", "d"),
        ("tried", "d"), ("destroyed", "d"), ("cleaned", "d"), ("called", "d"),
    ],
)
def test_ed_ending_sound(word, expected):
    assert ed_ending_sound(word) == expected


@pytest.mark.parametrize("word", ["months", "paths", "laughs", "sighs"])
def test_s_ambiguous_spellings_return_none(word):
    """Chính tả nhập nhằng -> None để bên gọi bỏ qua, KHÔNG cảnh báo nhầm."""
    assert s_ending_sound(word) is None


@pytest.mark.parametrize("word", ["used", "promised", "closed", "based", "laughed", "sighed"])
def test_ed_ambiguous_spellings_return_none(word):
    assert ed_ending_sound(word) is None


def test_ending_sounds_returns_none_for_mixed_or_vowel_type():
    # dạng so sánh nguyên âm giữa từ — không suy đuôi được
    assert ending_sounds(["clean", "bread", "teach", "team"]) is None
    # trộn đuôi -s và -ed
    assert ending_sounds(["cats", "played", "dogs", "worked"]) is None
    # có cụm từ (không phải 1 từ đơn)
    assert ending_sounds(["native languages", "films", "magics", "voices"]) is None


def _pron(options):
    return check_pronunciation_options(options, is_pronunciation=True)


def _joined(warnings):
    return " | ".join(warnings)


@pytest.mark.parametrize(
    "options, description",
    [
        (["twin<u>s</u>", "type<u>s</u>", "separate<u>s</u>", "overall<u>s</u>"], "2-2 (/z/,/s/,/s/,/z/)"),
        (["sav<u>ed</u>", "lov<u>ed</u>", "want<u>ed</u>", "visit<u>ed</u>"], "2-2 (/d/,/d/,/ɪd/,/ɪd/)"),
        (["learn<u>ed</u>", "play<u>ed</u>", "work<u>ed</u>", "talk<u>ed</u>"], "2-2 (/d/,/d/,/t/,/t/)"),
        (["destroy<u>ed</u>", "direct<u>ed</u>", "escap<u>ed</u>", "decid<u>ed</u>"], "1-2-1"),
    ],
)
def test_flags_invalid_three_one_pattern_from_real_exam(options, description):
    text = _joined(_pron(options))
    assert "không đúng quy tắc 3 từ giống - 1 từ khác" in text, description


@pytest.mark.parametrize(
    "options",
    [
        # 3 từ /z/ + 1 từ /s/
        ["ring<u>s</u>", "ending<u>s</u>", "save<u>s</u>", "shoot<u>s</u>"],
        # 3 từ /ɪd/ + 1 từ /t/
        ["destruct<u>ed</u>", "illustrat<u>ed</u>", "adapt<u>ed</u>", "escap<u>ed</u>"],
        # 3 từ /s/ + 1 từ /z/
        ["book<u>s</u>", "cat<u>s</u>", "stop<u>s</u>", "dog<u>s</u>"],
    ],
)
def test_valid_three_one_pattern_has_no_sound_warning(options):
    assert "quy tắc 3 từ giống" not in _joined(_pron(options))


def test_vowel_comparison_type_is_not_sound_checked():
    """Dạng so sánh nguyên âm giữa từ không suy được âm -> không cảnh báo nhầm."""
    warnings = _pron(["cl<u>ea</u>n", "br<u>ea</u>d", "t<u>ea</u>ch", "t<u>ea</u>m"])
    assert warnings == []


def test_stress_type_skips_sound_pattern_check():
    """Dạng trọng âm không so đuôi — dù các từ cùng đuôi cũng không kiểm tra."""
    warnings = check_pronunciation_options(
        ["<u>cel</u>ebrates", "<u>dec</u>orates", "ex<u>hi</u>bits", "<u>har</u>vests"],
        is_pronunciation=False,
    )
    assert "quy tắc 3 từ giống" not in _joined(warnings)
