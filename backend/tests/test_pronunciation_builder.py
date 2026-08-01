"""Test bộ dựng câu phát âm/trọng âm bằng code (app/services/pronunciation_builder.py).
Bảo chứng cốt lõi: MỌI câu dựng ra đều qua check_pronunciation_options (không lỗi)."""

import pytest

from app.services.pronunciation_builder import build_pronunciation_questions
from app.services.pronunciation_check import check_pronunciation_options


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


def test_prompt_text_matches_kind():
    assert "ending -s/-es" in build_pronunciation_questions("s", 1, seed=1)[0].prompt_text
    assert "ending -ed" in build_pronunciation_questions("ed", 1, seed=1)[0].prompt_text
    assert "underlined part" in build_pronunciation_questions("vowel", 1, seed=1)[0].prompt_text
    assert "stress pattern" in build_pronunciation_questions("stress", 1, seed=1)[0].prompt_text
