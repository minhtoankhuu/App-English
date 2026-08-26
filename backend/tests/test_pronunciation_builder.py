"""Test bộ dựng câu phát âm/trọng âm bằng code (app/services/pronunciation_builder.py).
Bảo chứng cốt lõi: MỌI câu dựng ra đều qua check_pronunciation_options (không lỗi)."""

import pytest

from app.services.pronunciation_builder import build_pronunciation_questions, inflect_ed, inflect_s
from app.services.pronunciation_check import check_pronunciation_options
from app.services.pronunciation_sounds import stress_positions


def _is_pron(kind):
    return kind != "stress"


@pytest.mark.parametrize("kind", ["s", "ed", "vowel", "stress"])
def test_builds_requested_count(kind):
    qs = build_pronunciation_questions(kind, 5, seed=1)
    assert len(qs) == 5


@pytest.mark.parametrize("kind", ["s", "ed", "vowel", "stress"])
def test_every_built_question_passes_checker(kind):
    for q in build_pronunciation_questions(kind, 5, seed=7):
        texts = [o["text"] for o in q.options]
        assert check_pronunciation_options(texts, is_pronunciation=_is_pron(kind)) == [], texts


@pytest.mark.parametrize("kind", ["s", "ed", "vowel", "stress"])
def test_exactly_one_correct_and_answer_matches(kind):
    for q in build_pronunciation_questions(kind, 5, seed=3):
        correct = [o for o in q.options if o["is_correct"]]
        assert len(correct) == 1
        assert len(q.options) == 4
        assert q.answer_text.startswith(correct[0]["label"])


@pytest.mark.parametrize("kind", ["s", "ed", "vowel", "stress"])
def test_options_are_distinct_within_question(kind):
    for q in build_pronunciation_questions(kind, 5, seed=9):
        labels = [o["label"] for o in q.options]
        assert labels == ["A", "B", "C", "D"]
        words = [o["text"] for o in q.options]
        assert len(set(words)) == 4


def test_questions_do_not_repeat_option_sets():
    qs = build_pronunciation_questions("s", 5, seed=11)
    keys = {frozenset(o["text"] for o in q.options) for q in qs}
    assert len(keys) == len(qs)


def test_same_seed_is_reproducible():
    a = build_pronunciation_questions("ed", 4, seed=123)
    b = build_pronunciation_questions("ed", 4, seed=123)
    assert [[o["text"] for o in q.options] for q in a] == [[o["text"] for o in q.options] for q in b]


def test_unknown_kind_returns_empty():
    assert build_pronunciation_questions("banana", 5, seed=1) == []


UNIT_WORDS = [
    "tornado", "tremble", "flood", "damage", "destroy", "erupt", "collapse", "rescue",
    "warn", "shelter", "earthquake", "volcano", "drought", "storm", "victim", "evacuate",
    "supply", "battery", "layer", "ash",
]


@pytest.mark.parametrize(
    "word, expected",
    [
        ("book", ("book", "s")), ("watch", ("watch", "es")), ("box", ("box", "es")),
        ("city", ("citi", "es")), ("study", ("studi", "es")), ("save", ("save", "s")),
        ("day", ("day", "s")),
    ],
)
def test_inflect_s(word, expected):
    assert inflect_s(word) == expected


@pytest.mark.parametrize("word", ["books", "s", "", "zzqx"])
def test_inflect_s_rejects_uncertain(word):
    assert inflect_s(word) is None


@pytest.mark.parametrize(
    "word, expected",
    [("work", "worked"), ("stop", "stopped"), ("save", "saved"), ("study", "studied"), ("play", "played")],
)
def test_inflect_ed(word, expected):
    assert inflect_ed(word) == expected


@pytest.mark.parametrize("word", ["go", "be", "zzqx", "worked"])
def test_inflect_ed_rejects_irregular_or_unknown(word):
    """Động từ bất quy tắc (go -> goed) và từ lạ phải bị loại, không bịa."""
    assert inflect_ed(word) is None


@pytest.mark.parametrize("kind", ["s", "ed", "stress"])
def test_unit_words_are_preferred_when_sufficient(kind):
    """Có đủ vốn từ Unit thì lựa chọn phải lấy từ trong bài, không dùng bộ chuẩn."""
    qs = build_pronunciation_questions(kind, 3, seed=5, unit_words=UNIT_WORDS)
    assert qs
    for q in qs:
        for opt in q.options:
            plain = opt["text"].replace("<u>", "").replace("</u>", "").lower()
            assert any(plain.startswith(w[:4]) for w in UNIT_WORDS), plain


@pytest.mark.parametrize("kind", ["s", "ed", "stress"])
def test_falls_back_to_curated_when_unit_words_insufficient(kind):
    """Vốn từ Unit quá ít/không dùng được -> vẫn dựng đủ câu bằng bộ chuẩn."""
    qs = build_pronunciation_questions(kind, 3, seed=5, unit_words=["zzqx", "qqzz"])
    assert len(qs) == 3


@pytest.mark.parametrize("kind", ["s", "ed", "stress"])
def test_unit_word_questions_still_pass_checker(kind):
    for q in build_pronunciation_questions(kind, 5, seed=5, unit_words=UNIT_WORDS):
        texts = [o["text"] for o in q.options]
        assert check_pronunciation_options(texts, is_pronunciation=kind != "stress") == [], texts


def test_stress_excludes_single_syllable_unit_words():
    """'flood', 'drought', 'storm', 'ash', 'warn' 1 âm tiết -> không được vào bài trọng âm."""
    single = {"flood", "drought", "storm", "ash", "warn"}
    for q in build_pronunciation_questions("stress", 5, seed=5, unit_words=UNIT_WORDS):
        words = [o["text"].replace("<u>", "").replace("</u>", "").lower() for o in q.options]
        assert not (single & set(words)), words


def test_stress_options_carry_no_underline():
    """Gạch chân âm tiết trọng âm ở MỌI lựa chọn là lộ đáp án — học sinh chỉ cần so vị
    trí gạch chân. Đề thật để trần từ (báo cáo 26/08/2026)."""
    for q in build_pronunciation_questions("stress", 5, seed=5, unit_words=UNIT_WORDS):
        for opt in q.options:
            assert "<u>" not in opt["text"], opt["text"]


def test_prompt_text_matches_kind():
    assert "ending -s/-es" in build_pronunciation_questions("s", 1, seed=1)[0].prompt_text
    assert "ending -ed" in build_pronunciation_questions("ed", 1, seed=1)[0].prompt_text
    assert "underlined part" in build_pronunciation_questions("vowel", 1, seed=1)[0].prompt_text
    assert "stress pattern" in build_pronunciation_questions("stress", 1, seed=1)[0].prompt_text
