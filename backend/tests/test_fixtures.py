from app.services import fixtures
from app.services.ai_provider import BlockSpec, GenerationContext, MockAIProvider

ALL_EXERCISE_TYPES = [
    "pronunciation",
    "stress",
    "multiple_choice",
    "matching",
    "gap_fill",
    "cloze_test",
    "reading_true_false",
    "sign_reading",
    "word_form",
    "sentence_rewrite",
]

UNIT3_GRADE7_CONTEXT = GenerationContext(grade_number=7, school_stage_code="secondary", exam_level_code="A2", unit_order_no=3)
OTHER_CONTEXT = GenerationContext(grade_number=7, school_stage_code="secondary", exam_level_code="A2", unit_order_no=5)


def test_golden_bank_covers_all_ten_exercise_types():
    assert set(fixtures.GOLDEN_UNIT3_QUESTIONS.keys()) == set(ALL_EXERCISE_TYPES)


def test_pool_prefers_golden_over_generic_for_unit3_grade7():
    provider = MockAIProvider()

    for code in ALL_EXERCISE_TYPES:
        block = BlockSpec(exercise_type_code=code, question_count=1, level_code="A2")
        pool = provider._pool(block, UNIT3_GRADE7_CONTEXT)
        golden_first = fixtures.GOLDEN_UNIT3_QUESTIONS[code][0]

        assert pool[0] == golden_first, f"dạng '{code}' phải ưu tiên câu vàng Unit 3"


def test_pool_falls_back_to_generic_outside_unit3_grade7():
    provider = MockAIProvider()

    for code in ALL_EXERCISE_TYPES:
        block = BlockSpec(exercise_type_code=code, question_count=1, level_code="A2")
        pool = provider._pool(block, OTHER_CONTEXT)
        golden_templates = fixtures.GOLDEN_UNIT3_QUESTIONS[code]

        assert all(t not in golden_templates for t in pool), (
            f"dạng '{code}' ngoài Unit 3 không được lẫn nội dung vàng"
        )
