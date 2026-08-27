"""Test cách chia phần con của mục PRONUNCIATION khi dựng câu bằng code
(app/services/generation._deterministic_pronunciation_drafts).

Đề thật ghép 3-4 phần vào cùng mục "I. PRONUNCIATION": một hoặc hai kiểu đuôi, một
kiểu so nguyên âm, rồi trọng âm. Mỗi phần con ghim kiểu của mình qua `prompt_override`
— hai điều kiện phải giữ là câu bốc ra đúng kiểu ĐÓ, và các phần con không lặp câu
của nhau (rổ câu đọc được của một Unit chỉ vài câu mỗi kiểu).
"""

import pytest

from app.services.ai_provider import AIGenerationError, BlockSpec, GenerationContext, QuestionDraft
from app.services.exam_pronunciation import line_kind, parse_option_line
from app.services.generation import (
    _answer_key_warnings,
    _answer_text_warnings,
    _duplicate_key,
    _duplicate_warning,
    _deterministic_pronunciation_drafts,
    _pronunciation_drafts,
    _retrieval_query,
    _sample_words,
)

TAB = chr(9)

S_LINES = [
    f"A. book<u>s</u>{TAB}B. cup<u>s</u>{TAB}C. dog<u>s</u>{TAB}D. map<u>s</u>",
    f"A. help<u>s</u>{TAB}B. live<u>s</u>{TAB}C. improve<u>s</u>{TAB}D. fold<u>s</u>",
]
ED_LINES = [
    f"A. work<u>ed</u>{TAB}B. want<u>ed</u>{TAB}C. wash<u>ed</u>{TAB}D. help<u>ed</u>",
    f"A. look<u>ed</u>{TAB}B. prepar<u>ed</u>{TAB}C. dress<u>ed</u>{TAB}D. watch<u>ed</u>",
]
VOWEL_LINES = [
    f"A. m<u>u</u>scle{TAB}B. s<u>u</u>gar{TAB}C. p<u>u</u>zzle{TAB}D. h<u>u</u>nting",
]
ALL_LINES = S_LINES + ED_LINES + VOWEL_LINES

PART_PROMPTS = {
    "s": "Chỉ dùng kiểu (1) đuôi -s/-es cho toàn bộ các câu.",
    "ed": "Chỉ dùng kiểu (2) đuôi -ed cho toàn bộ các câu.",
    "vowel": "Chỉ dùng kiểu (3) so sánh âm chung trong từ (không phải đuôi -s/-es hay -ed).",
}


def _spec(kind, count=2):
    return BlockSpec(
        exercise_type_code="pronunciation",
        question_count=count,
        level_code="A2",
        prompt_override=PART_PROMPTS[kind],
    )


def _kinds(drafts):
    return [line_kind([o["text"] for o in d.options]) for d in drafts]


def test_each_part_only_gets_lines_of_its_own_kind():
    for kind in ("s", "ed"):
        drafts = _deterministic_pronunciation_drafts(_spec(kind), [], ALL_LINES)
        assert _kinds(drafts) == [kind, kind], kind


def test_parts_of_one_block_do_not_repeat_each_other():
    """Cả khối dùng chung một set `used` — phần sau không được lấy lại nhóm 4 từ mà
    phần trước đã lấy."""
    used: set[frozenset[str]] = set()
    seen: list[frozenset[str]] = []
    for kind in ("s", "ed", "vowel"):
        drafts = _deterministic_pronunciation_drafts(_spec(kind, count=1), [], ALL_LINES, used)
        seen += [frozenset(o["text"] for o in d.options) for d in drafts]

    assert len(seen) == len(set(seen))
    assert set(seen) <= used


def test_a_part_reuses_nothing_from_the_used_set_it_is_given():
    used = {frozenset(parse_option_line(line)) for line in S_LINES}
    already = set(used)  # hàm có cập nhật `used`, phải chụp lại trước khi gọi
    drafts = _deterministic_pronunciation_drafts(_spec("s", count=2), [], S_LINES, used)

    # Rổ đề thật hết sạch -> rơi về bộ dựng viết tay, nhưng vẫn phải đúng kiểu đuôi -s/-es.
    assert _kinds(drafts) == ["s", "s"]
    assert all(frozenset(o["text"] for o in d.options) not in already for d in drafts)


def test_the_prompt_of_each_part_says_which_kind_it_is():
    prompts = {
        kind: _deterministic_pronunciation_drafts(_spec(kind, count=1), [], ALL_LINES)[0].prompt_text
        for kind in ("s", "ed", "vowel")
    }

    assert "-s/-es" in prompts["s"]
    assert "-ed" in prompts["ed"]
    assert len(set(prompts.values())) == 3


CTX = GenerationContext(grade_number=8, school_stage_code="thcs", exam_level_code="A2")


def _draft(words):
    return QuestionDraft(
        prompt_text="Choose the word that has a different pronunciation of the ending -s/-es.",
        answer_text=f"D. {words[3]}",
        explanation="x",
        target_knowledge="Phát âm",
        level_code="A2",
        source_ref="ai",
        options=[
            {"label": lb, "text": t, "is_correct": i == 3}
            for i, (lb, t) in enumerate(zip("ABCD", words))
        ],
    )


# 3 /z/ + 1 /s/ — qua được bộ kiểm.
GOOD_AI = _draft(["ring<u>s</u>", "ending<u>s</u>", "save<u>s</u>", "shoot<u>s</u>"])
# 2-2, không có đáp án duy nhất — bộ kiểm bắt được.
BAD_AI = _draft(["twin<u>s</u>", "type<u>s</u>", "separate<u>s</u>", "overall<u>s</u>"])


class FakeProvider:
    """Trả sẵn danh sách cho generate; regenerate_one luôn trả lại chính câu hỏng để
    mô phỏng model không sửa được."""

    def __init__(self, drafts, *, error=False):
        self._drafts = list(drafts)
        self._error = error
        self.generate_calls = 0

    def generate(self, spec, context):
        self.generate_calls += 1
        if self._error:
            raise AIGenerationError("provider down")
        return list(self._drafts)

    def regenerate_one(self, spec, context, exclude_prompt=None, feedback=None):
        return BAD_AI


def test_ai_writes_the_questions_and_clean_ones_are_kept():
    """Đổi ngày 27/08/2026: mục phát âm phải GỌI AI, không còn bốc thẳng câu của đề thật."""
    provider = FakeProvider([GOOD_AI])
    used: set[frozenset[str]] = set()

    drafts = _pronunciation_drafts(provider, _spec("s", count=1), CTX, [], ALL_LINES, used)

    assert provider.generate_calls == 1
    assert drafts == [GOOD_AI]


def test_a_question_the_checker_rejects_is_replaced_not_shipped():
    """Sai quy tắc 3 giống - 1 khác là câu không có đáp án duy nhất — bỏ, bù bằng câu
    dựng được, chứ không gắn cảnh báo rồi vẫn in ra đề."""
    provider = FakeProvider([BAD_AI])
    used: set[frozenset[str]] = set()

    drafts = _pronunciation_drafts(provider, _spec("s", count=1), CTX, [], ALL_LINES, used)

    assert len(drafts) == 1
    assert drafts[0] is not BAD_AI
    assert _kinds(drafts) == ["s"]


def test_provider_failure_still_produces_a_full_part():
    provider = FakeProvider([], error=True)
    used: set[frozenset[str]] = set()

    drafts = _pronunciation_drafts(provider, _spec("s", count=2), CTX, [], ALL_LINES, used)

    assert len(drafts) == 2
    assert _kinds(drafts) == ["s", "s"]


def test_ai_questions_do_not_repeat_across_parts_either():
    provider = FakeProvider([GOOD_AI])
    used: set[frozenset[str]] = set()

    first = _pronunciation_drafts(provider, _spec("s", count=1), CTX, [], ALL_LINES, used)
    second = _pronunciation_drafts(provider, _spec("s", count=1), CTX, [], ALL_LINES, used)

    assert first == [GOOD_AI]
    assert second != [GOOD_AI]
    assert len(second) == 1


def test_retrieval_query_uses_unit_words_not_the_vietnamese_instruction():
    """Câu truy vấn RAG phải là từ khoá tiếng Anh của bài, không phải đoạn chỉ thị
    tiếng Việt ghim kiểu — gửi chỉ thị đi thì FTS trượt sạch và vector lệch hẳn."""
    words = ["volunteer", "collect", "donate", "charity", "community", "support", "fund"]
    query = _retrieval_query(CTX, " ".join(_sample_words(words)))

    assert "Chỉ dùng kiểu" not in query
    assert any(word in query for word in words)


def test_sample_words_keeps_the_query_short():
    words = [f"w{i}" for i in range(50)]

    assert len(_sample_words(words)) == 5
    assert len(_sample_words(["one", "two"])) == 2


# --- đối chiếu đáp án với âm đọc được ----------------------------------------

WRONG_KEY = _draft(["bird<u>s</u>", "friend<u>s</u>", "cat<u>s</u>", "dog<u>s</u>"])
UNREADABLE = _draft(["h<u>ea</u>vy", "s<u>ea</u>son", "pl<u>ea</u>se", "b<u>ea</u>r"])


def test_answer_marked_on_the_wrong_option_is_caught():
    """birds /z/, friends /z/, cats /s/, dogs /z/ — khác 3 cái còn lại là 'cats', nhưng
    đề sinh 27/08/2026 đánh đáp án vào 'dogs'. 4 từ đều hợp lệ nên bộ kiểm cũ (chỉ nhìn
    4 chuỗi lựa chọn) không thấy gì; học sinh chọn đúng vẫn bị chấm sai."""
    warnings = _answer_key_warnings(WRONG_KEY, is_pronunciation=True)

    assert warnings and "cat" in warnings[0]


def test_answer_marked_on_the_odd_one_passes():
    good = _draft(["ring<u>s</u>", "ending<u>s</u>", "save<u>s</u>", "shoot<u>s</u>"])

    assert _answer_key_warnings(good, is_pronunciation=True) == []


def test_group_the_machine_cannot_read_is_rejected():
    """Không đọc được nghĩa là không bảo đảm được. Đề sinh 27/08/2026 lọt
    'heavy/season/please/bear' (thật ra 2-2) đúng vì `vowel_sounds` trả None rồi bộ kiểm
    im lặng cho qua."""
    assert _answer_key_warnings(UNREADABLE, is_pronunciation=True)


def test_a_wrong_answer_key_keeps_the_draft_out_of_the_exam():
    provider = FakeProvider([WRONG_KEY])
    used: set[frozenset[str]] = set()

    drafts = _pronunciation_drafts(provider, _spec("s", count=1), CTX, [], ALL_LINES, used)

    assert len(drafts) == 1
    assert drafts[0] is not WRONG_KEY


# --- so trùng theo bộ lựa chọn, không theo câu dẫn ---------------------------


def test_two_pronunciation_questions_sharing_a_prompt_are_not_duplicates():
    """Cả phần con dùng chung đúng một câu dẫn, nên so theo câu dẫn thì từ câu thứ 2 trở
    đi câu nào cũng bị báo trùng dù 4 từ khác hẳn — mỗi câu đốt thêm 2 lượt gọi API mà
    bản thay thế cũng mang đúng câu dẫn đó nên không bao giờ được nhận."""
    spec = _spec("s")
    first = _draft(["car<u>s</u>", "bike<u>s</u>", "train<u>s</u>", "toy<u>s</u>"])
    second = _draft(["start<u>s</u>", "run<u>s</u>", "enjoy<u>s</u>", "begin<u>s</u>"])
    seen = {_duplicate_key(first, spec)}

    assert first.prompt_text == second.prompt_text
    assert _duplicate_warning(second, seen, spec) == []


def test_the_same_four_words_twice_is_still_a_duplicate():
    spec = _spec("s")
    draft = _draft(["car<u>s</u>", "bike<u>s</u>", "train<u>s</u>", "toy<u>s</u>"])
    seen = {_duplicate_key(draft, spec)}

    assert _duplicate_warning(draft, seen, spec)


def test_other_exercise_types_still_compare_by_prompt():
    """Dạng trắc nghiệm mỗi câu một câu dẫn riêng — vẫn so theo câu dẫn như cũ."""
    spec = BlockSpec(exercise_type_code="multiple_choice", question_count=5, level_code="A2")
    draft = _draft(["a", "b", "c", "d"])

    assert _duplicate_warning(draft, {_duplicate_key(draft, spec)}, spec)


# --- answer_text phải khớp lựa chọn đánh is_correct --------------------------


def _with_answer(words, answer_text, correct_index):
    return QuestionDraft(
        prompt_text="p", answer_text=answer_text, explanation="", target_knowledge="",
        level_code="A2", source_ref="ai",
        options=[
            {"label": lb, "text": t, "is_correct": i == correct_index}
            for i, (lb, t) in enumerate(zip("ABCD", words))
        ],
    )


WORDS = ["car<u>s</u>", "bike<u>s</u>", "train<u>s</u>", "toy<u>s</u>"]


def test_answer_text_pointing_at_another_option_is_caught():
    """Trang Duyệt in answer_text, bản đáp án DOCX tô đậm lựa chọn is_correct — hai
    trường model điền độc lập. Lệch nhau thì giáo viên duyệt một đáp án còn học sinh
    nhận một đáp án khác, mà không màn hình nào nhìn ra."""
    warnings = _answer_text_warnings(_with_answer(WORDS, "D. toys", 1))

    assert warnings and "bikes" in warnings[0]


def test_answer_text_matching_an_option_that_does_not_exist_is_caught():
    assert _answer_text_warnings(_with_answer(WORDS, "elephants", 1))


def test_answer_text_missing_on_a_multiple_choice_question_is_caught():
    assert _answer_text_warnings(_with_answer(WORDS, "", 1))


@pytest.mark.parametrize("answer", ["B. bikes", "bikes", "B", "b) bikes"])
def test_the_usual_ways_of_writing_the_answer_all_pass(answer):
    """Model ghi 'B. bikes', 'bikes' hay 'B' đều hợp lệ — không được báo nhầm."""
    assert _answer_text_warnings(_with_answer(WORDS, answer, 1)) == []


def test_question_without_options_is_not_checked():
    """Word form / viết lại câu in thẳng answer_text, không có lựa chọn để đối chiếu."""
    draft = QuestionDraft(
        prompt_text="p", answer_text="collection", explanation="", target_knowledge="",
        level_code="A2", source_ref="ai", options=None,
    )

    assert _answer_text_warnings(draft) == []
