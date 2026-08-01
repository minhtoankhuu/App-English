"""Test tự động sinh lại câu phát âm/trọng âm bị lỗi trong pipeline
(app/services/generation._auto_fix_pronunciation_drafts) — dùng provider giả, không
cần DB hay gọi OpenAI thật."""

from app.services.ai_provider import AIGenerationError, BlockSpec, GenerationContext, QuestionDraft
from app.services.generation import _MAX_PRONUNCIATION_REGEN, _auto_fix_pronunciation_drafts


def _opts(words):
    return [{"label": lb, "text": t, "is_correct": i == 0} for i, (lb, t) in enumerate(zip("ABCD", words))]


def _draft(prompt, words):
    return QuestionDraft(
        prompt_text=prompt,
        answer_text=words[0],
        explanation="x",
        target_knowledge="pron",
        level_code="A2",
        source_ref="mock",
        options=_opts(words),
    )


# Câu lỗi: từ bịa (foring/woring/soring). Câu sạch: 3 /z/ + 1 /s/ (rings/endings/saves/shoots).
BAD = _draft("P", ["b<u>or</u>ing", "f<u>or</u>ing", "w<u>or</u>ing", "s<u>or</u>ing"])
CLEAN = _draft("P", ["ring<u>s</u>", "ending<u>s</u>", "save<u>s</u>", "shoot<u>s</u>"])
CTX = GenerationContext(grade_number=7, school_stage_code="thcs", exam_level_code="A2")
SPEC = BlockSpec(exercise_type_code="pronunciation", question_count=1, level_code="A2")


class FakeProvider:
    def __init__(self, replacements):
        self._replacements = list(replacements)
        self.calls = 0
        self.last_feedback = None

    def generate(self, spec, context):
        raise AssertionError("không nên gọi generate trong auto-fix")

    def regenerate_one(self, spec, context, exclude_prompt=None, feedback=None):
        self.calls += 1
        self.last_feedback = feedback
        return self._replacements.pop(0)


def test_replaces_bad_draft_with_clean_regeneration():
    provider = FakeProvider([CLEAN])
    result = _auto_fix_pronunciation_drafts(provider, SPEC, CTX, [BAD])

    assert result[0] is CLEAN
    assert provider.calls == 1
    assert provider.last_feedback  # cảnh báo được truyền làm feedback


def test_keeps_good_draft_without_regenerating():
    provider = FakeProvider([CLEAN])
    result = _auto_fix_pronunciation_drafts(provider, SPEC, CTX, [CLEAN])

    assert result[0] is CLEAN
    assert provider.calls == 0


def test_stops_after_max_attempts_and_keeps_best():
    # Luôn trả câu lỗi -> phải dừng sau _MAX_PRONUNCIATION_REGEN lần, không lặp vô hạn.
    provider = FakeProvider([BAD] * (_MAX_PRONUNCIATION_REGEN + 5))
    result = _auto_fix_pronunciation_drafts(provider, SPEC, CTX, [BAD])

    assert provider.calls == _MAX_PRONUNCIATION_REGEN
    assert result[0] is BAD


def test_ignores_non_pronunciation_types():
    provider = FakeProvider([CLEAN])
    spec = BlockSpec(exercise_type_code="multiple_choice", question_count=1, level_code="A2")
    result = _auto_fix_pronunciation_drafts(provider, spec, CTX, [BAD])

    assert result == [BAD]
    assert provider.calls == 0


def test_stops_gracefully_when_regeneration_errors():
    class FailingProvider:
        calls = 0

        def regenerate_one(self, spec, context, exclude_prompt=None, feedback=None):
            type(self).calls += 1
            raise AIGenerationError("OpenAI lỗi")

    provider = FailingProvider()
    result = _auto_fix_pronunciation_drafts(provider, SPEC, CTX, [BAD])

    assert result[0] is BAD  # giữ câu cũ, không vỡ pipeline
    assert provider.calls == 1
