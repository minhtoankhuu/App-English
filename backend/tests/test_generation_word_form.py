"""Test Phần A word form gọi provider RIÊNG cho từng họ từ (5 câu/họ từ) và dọn hai lỗi
model hay mắc: tự thêm lựa chọn A/B/C/D, và thêm từ gốc trong ngoặc ở cuối câu.
Dùng provider giả — không cần DB hay OpenAI."""

import random
import re
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.services.ai_provider import BlockSpec, GenerationContext, QuestionDraft
from app.services.docx_renderer import split_bracket_root
from app.services.word_form_check import check_word_form, word_family_members
from app.services.generation import (
    _MAX_FAMILY_ATTEMPTS,
    _distinct_families,
    _pinned_family,
    _retrieval_query,
    _word_form_bracket_drafts,
    _shuffle_keeping_family_groups,
    word_form_questions_per_family,
    WORD_FORM_QUESTIONS_PER_FAMILY,
    _strip_word_form_extras,
    _unify_family_label,
    _word_form_family_drafts,
    word_form_family_count,
)

CTX = GenerationContext(grade_number=7, school_stage_code="thcs", exam_level_code="A2")
SPEC = BlockSpec(
    exercise_type_code="word_form",
    question_count=15,
    level_code="A2",
    prompt_override="Chỉ dùng kiểu (A) nhóm theo họ từ cho toàn bộ các câu.",
)


def _draft(prompt, family, options=None, answer_text=None):
    # Đáp án mặc định lấy TỪ CHÍNH họ từ mà câu khai: bộ kiểm đối chiếu hai chỗ này với
    # nhau, nên đặt chỗ giữ chỗ kiểu "x" là dựng ra câu mà thực tế sẽ bị loại.
    members = sorted(word_family_members(family))
    return QuestionDraft(
        prompt_text=prompt,
        answer_text=answer_text or (members[0] if members else "x"),
        explanation="e", target_knowledge=family,
        level_code="A2", source_ref="mock", options=options,
    )


UNIT_WORDS = ["collect", "benefit", "outdoor", "together", "creative"]


class FamilyProvider:
    """Trả 5 câu cùng 1 họ từ mỗi lần gọi, họ từ suy từ TỪ HẠT GIỐNG trong prompt_override."""

    def __init__(self, ignore_seed=False):
        self.calls = 0
        self.seen_overrides: list[str] = []
        self._ignore_seed = ignore_seed

    def _family_for(self, override: str) -> str:
        if self._ignore_seed:
            return "collect (v) → collection (n) → collector (n)"
        match = re.search(r"h\u1ecd t\u1eeb c\u1ee7a t\u1eeb '([a-z]+)'", override)
        stem = match.group(1) if match else "collect"
        return f"{stem} (v) → {stem}ion (n) → {stem}ive (adj)"

    def generate(self, spec, context):
        override = spec.prompt_override or ""
        self.calls += 1
        self.seen_overrides.append(override)
        family = self._family_for(override)
        return [_draft(f"Sentence {i} ______ here.", family) for i in range(spec.question_count)]

    def regenerate_one(self, spec, context, exclude_prompt=None, feedback=None):
        raise AssertionError("không cần sinh lại khi câu đã sạch")


def test_family_count_from_question_count():
    assert word_form_family_count(15) == 3
    assert word_form_family_count(5) == 1
    assert word_form_family_count(0) == 1  # không bao giờ ra 0 họ từ


def test_calls_provider_once_per_family():
    """Lỗi thật 24/08/2026: xin cả block trong 1 lần gọi -> 15 câu chung một họ từ."""
    provider = FamilyProvider()
    drafts = _word_form_family_drafts(provider, SPEC, CTX, UNIT_WORDS)

    assert provider.calls == 3
    assert len(drafts) == 3 * WORD_FORM_QUESTIONS_PER_FAMILY


def test_each_call_asks_for_five_questions_of_one_family():
    provider = FamilyProvider()
    _word_form_family_drafts(provider, SPEC, CTX, UNIT_WORDS)

    assert all("dùng CHUNG đúng MỘT họ từ" in o for o in provider.seen_overrides)


def test_pins_a_different_seed_word_each_call():
    """Chốt chặn chính: code chọn từ hạt giống khác nhau, không phó mặc model nghe lời."""
    provider = FamilyProvider()
    _word_form_family_drafts(provider, SPEC, CTX, UNIT_WORDS)

    seeds = [re.search(r"h\u1ecd t\u1eeb c\u1ee7a t\u1eeb '([a-z]+)'", o).group(1) for o in provider.seen_overrides]
    # Từ có đuôi phái sinh được thử trước (xem _rank_seed_words), còn lại giữ thứ tự.
    assert seeds == ["creative", "collect", "benefit"]
    assert len(set(seeds)) == len(seeds)


def test_later_calls_also_list_families_already_used():
    provider = FamilyProvider()
    _word_form_family_drafts(provider, SPEC, CTX, UNIT_WORDS)

    assert "ĐÃ RA" not in provider.seen_overrides[0]
    # Hạt giống đầu là "creative" (xem _rank_seed_words) -> lượt sau phải liệt kê họ đó.
    assert "creative" in provider.seen_overrides[1]


def test_groups_are_five_questions_each_with_distinct_families():
    provider = FamilyProvider()
    drafts = _word_form_family_drafts(provider, SPEC, CTX, UNIT_WORDS)

    families = [d.target_knowledge for d in drafts]
    groups = [families[i : i + WORD_FORM_QUESTIONS_PER_FAMILY]
              for i in range(0, len(families), WORD_FORM_QUESTIONS_PER_FAMILY)]
    for group in groups:
        assert len(set(group)) == 1, group
    # Đúng lỗi bạn báo: 3 nhóm phải là 3 họ từ KHÁC nhau, không dồn thành 15 câu một họ.
    assert len({g[0] for g in groups}) == 3


def test_retries_with_next_seed_when_model_repeats_a_family():
    """Model bướng, lần nào cũng trả 'collect' -> phải thử lại chứ không im lặng chấp nhận."""
    provider = FamilyProvider(ignore_seed=True)
    drafts = _word_form_family_drafts(provider, SPEC, CTX, UNIT_WORDS)

    # Họ từ 1 nhận ngay; họ từ 2 và 3 mỗi cái thử tối đa _MAX_FAMILY_ATTEMPTS lần.
    assert provider.calls == 1 + 2 * _MAX_FAMILY_ATTEMPTS
    # Thử hết lượt vẫn trùng -> BỎ. Trước đây batch trùng vẫn được nhận, nên đề sinh
    # 27/08/2026 ra cả mục WORD FORMATION chung một họ từ 'amaze'. Thà thiếu câu còn hơn.
    assert len(drafts) == WORD_FORM_QUESTIONS_PER_FAMILY
    assert len(_distinct_families(drafts)) == 1


def test_works_without_unit_vocabulary():
    """Unit chưa nạp tài liệu -> không có hạt giống, quay về cách dặn + thử lại."""
    provider = FamilyProvider()
    drafts = _word_form_family_drafts(provider, SPEC, CTX, [])

    assert len(drafts) == 3 * WORD_FORM_QUESTIONS_PER_FAMILY
    assert all("họ từ của từ" not in o for o in provider.seen_overrides)


def test_skips_seed_words_too_short_to_have_a_family():
    provider = FamilyProvider()
    _word_form_family_drafts(provider, SPEC, CTX, ["a", "go", "benefit", "outdoor", "creative"])

    seeds = [re.search(r"h\u1ecd t\u1eeb c\u1ee7a t\u1eeb '([a-z]+)'", o).group(1) for o in provider.seen_overrides]
    assert "a" not in seeds and "go" not in seeds
    assert seeds == ["creative", "benefit", "outdoor"]


def test_strips_multiple_choice_options():
    drafts = [_draft("A ______ b.", "use (v) → usage (n)", options=[{"label": "A", "text": "x"}])]
    _strip_word_form_extras(drafts, kind="family")
    assert drafts[0].options is None


def test_strips_bracket_root_in_family_kind():
    """Họ từ đã in ở dòng ❖ — "(together)" ở cuối câu là thừa và lộ đáp án."""
    drafts = [_draft("We usually have ______ with friends. (together)", "use (v) → usage (n)")]
    _strip_word_form_extras(drafts, kind="family")
    assert drafts[0].prompt_text == "We usually have ______ with friends."


def test_keeps_bracket_root_in_bracket_kind():
    drafts = [_draft("We usually have ______ with friends. (together)", "mô tả")]
    _strip_word_form_extras(drafts, kind="bracket")
    assert drafts[0].prompt_text.endswith("(together)")


def test_unifies_family_label_when_majority_agrees():
    """Model hay ghi chuỗi lệch nhau chút -> renderer tách thành nhiều dòng ❖."""
    good = "use (v) → useful (adj) → usage (n)"
    drafts = [_draft("s ______ .", good) for _ in range(3)]
    drafts += [_draft("s ______ .", "use (v) → usage (n)"), _draft("s ______ .", "lệch hẳn")]

    _unify_family_label(drafts)

    assert {d.target_knowledge for d in drafts} == {good}


def test_keeps_labels_when_no_majority():
    """Không đủ đồng thuận thì để nguyên — gán bừa sẽ giấu mất lỗi thật."""
    drafts = [
        _draft("s ______ .", "use (v) → usage (n)"),
        _draft("s ______ .", "share (v) → sharing (n)"),
        _draft("s ______ .", "collect (v) → collection (n)"),
        _draft("s ______ .", "belong (v) → belonging (n)"),
        _draft("s ______ .", "adore (v) → adorable (adj)"),
    ]
    _unify_family_label(drafts)

    assert len({d.target_knowledge for d in drafts}) == 5


# --- số câu mỗi họ từ do giáo viên đặt ---------------------------------------


@pytest.mark.parametrize(
    "prompt_override, expected",
    [
        (None, 5),
        ("Chỉ dùng kiểu (A) nhóm theo họ từ cho toàn bộ các câu.", 5),  # mặc định
        ("Chỉ dùng kiểu (A) nhóm theo họ từ. Mỗi họ từ 7 câu.", 7),
        ("mỗi họ từ 6 câu", 6),
        ("MỖI HỌ TỪ 5 CÂU", 5),
        ("Mỗi họ từ 99 câu.", 10),  # kẹp trần, không để đề phình ra vô hạn
        ("Mỗi họ từ 1 câu.", 3),  # kẹp sàn — 1 câu thì không còn là "họ từ"
    ],
)
def test_questions_per_family_from_prompt_override(prompt_override, expected):
    assert word_form_questions_per_family(prompt_override) == expected


def test_family_count_uses_configured_per_family():
    assert word_form_family_count(21, 7) == 3
    assert word_form_family_count(18, 6) == 3
    assert word_form_family_count(15, 5) == 3


def test_generates_configured_number_of_questions_per_family():
    provider = FamilyProvider()
    spec = replace(
        SPEC,
        question_count=21,
        prompt_override="Chỉ dùng kiểu (A) nhóm theo họ từ cho toàn bộ các câu. Mỗi họ từ 7 câu.",
    )

    drafts = _word_form_family_drafts(provider, spec, CTX, UNIT_WORDS)

    assert provider.calls == 3
    assert len(drafts) == 21
    assert all("Cả 7 câu lần này" in o for o in provider.seen_overrides)


# --- đảo câu không được xé nhóm họ từ ----------------------------------------


def _q(qid, family):
    return SimpleNamespace(id=qid, target_knowledge=family, order_no=int(qid))


FAM_A = "energy (n) → energetic (adj) → energetically (adv)"
FAM_B = "cause (v) → cause (n) → causing (adj)"
FAM_C = "Japanese (adj) → Japanese (n)"


def _grouped_questions():
    questions = []
    for i, family in enumerate([FAM_A] * 5 + [FAM_B] * 5 + [FAM_C] * 5):
        questions.append(_q(str(i + 1), family))
    return questions


def test_shuffle_keeps_family_groups_contiguous():
    """Bug thật 24/08/2026: đảo thẳng cả phần khiến "❖ energy" in ra 4 lần xen kẽ."""
    questions = _grouped_questions()
    by_id = {q.id: q.target_knowledge for q in questions}

    for seed in range(20):
        ids = _shuffle_keeping_family_groups(questions, random.Random(seed))
        families = [by_id[i] for i in ids]
        # Mỗi họ từ chỉ được xuất hiện thành ĐÚNG MỘT khối liền nhau
        blocks = [f for j, f in enumerate(families) if j == 0 or families[j - 1] != f]
        assert len(blocks) == len(set(blocks)) == 3, (seed, families)


def test_shuffle_reorders_questions_inside_a_family():
    """Ý bạn đặt ra: câu trong một họ từ phải random, không chạy theo thứ tự v → n → adj."""
    questions = _grouped_questions()
    orders = {tuple(_shuffle_keeping_family_groups(questions, random.Random(s))) for s in range(20)}
    assert len(orders) > 1  # không phải lúc nào cũng ra một thứ tự

    original = [q.id for q in questions]
    assert any(list(o) != original for o in orders)


def test_shuffle_keeps_every_question_exactly_once():
    questions = _grouped_questions()
    ids = _shuffle_keeping_family_groups(questions, random.Random(7))
    assert sorted(ids, key=int) == [q.id for q in questions]


def test_questions_without_family_shuffle_freely():
    """Dạng bài khác (target_knowledge không phải họ từ) giữ nguyên hành vi đảo tự do."""
    questions = [_q(str(i), "Th\u00ec hi\u1ec7n t\u1ea1i \u0111\u01a1n") for i in range(1, 9)]
    orders = {tuple(_shuffle_keeping_family_groups(questions, random.Random(s))) for s in range(20)}
    assert len(orders) > 5


# --- Phần B ôn lại đúng các họ từ của Phần A ---------------------------------

FAMILIES = [
    "science (n) → scientist (n) → scientific (adj)",
    "benefit (n) → beneficial (adj) → beneficially (adv)",
    "fit (adj) → fitness (n) → fitly (adv)",
]
BRACKET_SPEC = BlockSpec(
    exercise_type_code="word_form",
    question_count=15,
    level_code="A2",
    prompt_override="Chỉ dùng kiểu (B) từ gốc trong ngoặc ở cuối câu cho toàn bộ các câu.",
)


class BracketProvider:
    def __init__(self):
        self.calls = 0
        self.seen: list[tuple[str, int]] = []

    def generate(self, spec, context):
        self.calls += 1
        self.seen.append((spec.prompt_override or "", spec.question_count))
        family = _pinned_family(spec.prompt_override) or "?"
        root = family.split(" (")[0]
        return [
            _draft(f"Sentence {i} ______ here. ({root})", "Chuyển từ loại")
            for i in range(spec.question_count)
        ]

    def regenerate_one(self, spec, context, exclude_prompt=None, feedback=None):
        raise AssertionError("câu đã sạch, không cần sinh lại")


def test_bracket_part_calls_once_per_family_from_part_a():
    """Đề thật 24/08/2026: xin cả block một lần -> 7/15 câu cùng '(benefit)'."""
    provider = BracketProvider()
    drafts = _word_form_bracket_drafts(provider, BRACKET_SPEC, CTX, FAMILIES)

    assert provider.calls == 3
    assert len(drafts) == 15


def test_bracket_roots_spread_across_part_a_families():
    provider = BracketProvider()
    drafts = _word_form_bracket_drafts(provider, BRACKET_SPEC, CTX, FAMILIES)

    roots = [split_bracket_root(d.prompt_text)[1] for d in drafts]
    assert set(roots) == {"science", "benefit", "fit"}
    # Trải đều, không dồn hết vào một từ như đề thật
    assert max(roots.count(r) for r in set(roots)) <= 5


def test_bracket_pins_each_family_and_can_be_read_back():
    provider = BracketProvider()
    _word_form_bracket_drafts(provider, BRACKET_SPEC, CTX, FAMILIES)

    pinned = [_pinned_family(override) for override, _ in provider.seen]
    assert pinned == FAMILIES
    assert all("KHÁC TỪ LOẠI" in override for override, _ in provider.seen)


def test_bracket_never_returns_more_than_requested():
    """Chia đều làm tròn lên (15/4 -> 4/họ từ) không được làm dư câu."""
    provider = BracketProvider()
    drafts = _word_form_bracket_drafts(provider, BRACKET_SPEC, CTX, FAMILIES + ["use (v) → usage (n)"])

    assert len(drafts) == 15


def test_distinct_families_keeps_first_seen_order():
    drafts = [_draft("s ______ .", f) for f in [FAMILIES[1], FAMILIES[0], FAMILIES[1], "mô tả tự do"]]
    assert _distinct_families(drafts) == [FAMILIES[1], FAMILIES[0]]


def test_bracket_check_rejects_root_outside_the_assigned_family():
    warnings = check_word_form(
        "He works very ______. (benefit)", "hard", "mô tả", kind="bracket", allowed_family=FAMILIES[0]
    )
    assert any("không thuộc họ từ được giao" in w for w in warnings)


def test_bracket_check_accepts_another_form_of_the_same_family():
    """Ví dụ bạn đưa: 'I want to become a ______ (science).' -> scientist."""
    assert check_word_form(
        "I want to become a ______. (science)", "scientist", "mô tả", kind="bracket",
        allowed_family=FAMILIES[0],
    ) == []


def test_word_family_members():
    assert word_family_members(FAMILIES[0]) == {"science", "scientist", "scientific"}
    assert word_family_members(None) == set()


def test_strip_moves_inline_bracket_before_checking():
    """Ngoặc giữa câu che mất lỗi "từ gốc trùng đáp án": bộ kiểm chỉ đọc ngoặc ở cuối câu,
    nên câu "The ______ (form) of the artwork..." với đáp án 'form' lọt qua (đề thật 24/08/2026)."""
    draft = _draft("The ______ (form) of the artwork was very unique.", "mô tả")
    draft.answer_text = "form"

    _strip_word_form_extras([draft], kind="bracket")

    assert draft.prompt_text == "The ______ of the artwork was very unique. (form)"
    warnings = check_word_form(draft.prompt_text, draft.answer_text, draft.target_knowledge, kind="bracket")
    assert any("trùng hệt đáp án" in w for w in warnings)


def test_strip_removes_inline_bracket_in_family_kind():
    draft = _draft("Many plants need water to ______ (grow) every day.", "grow (v) → growth (n)")
    _strip_word_form_extras([draft], kind="family")

    assert draft.prompt_text == "Many plants need water to ______ every day."

# --- câu truy vấn RAG tách khỏi chỉ thị cho model ---------------------------

CTX_UNIT = GenerationContext(
    grade_number=7, school_stage_code="thcs", exam_level_code="A2", unit_title="Healthy Living"
)


def test_retrieval_query_is_english_keywords_plus_unit():
    assert _retrieval_query(CTX_UNIT, "collect") == "collect Healthy Living"


def test_retrieval_query_skips_empty_terms():
    assert _retrieval_query(CTX_UNIT, None, "", "grow") == "grow Healthy Living"


def test_retrieval_query_never_empty():
    """OpenAI embeddings từ chối chuỗi rỗng."""
    bare = GenerationContext(grade_number=7, school_stage_code="thcs", exam_level_code="A2")
    assert _retrieval_query(bare, None).strip()


def test_family_call_queries_by_seed_word_not_the_vietnamese_instruction():
    """Trước đây cả đoạn "Cả 5 câu lần này dùng CHUNG đúng MỘT họ từ... BẮT BUỘC lấy họ
    từ của từ 'collect'..." trở thành câu truy vấn RAG: plainto_tsquery (AND toàn bộ từ)
    trượt sạch, vector search lệch hẳn."""

    class CaptureProvider(FamilyProvider):
        def __init__(self):
            super().__init__()
            self.queries: list[str | None] = []

        def generate(self, spec, context):
            self.queries.append(spec.retrieval_query)
            return super().generate(spec, context)

    provider = CaptureProvider()
    _word_form_family_drafts(provider, replace(SPEC, question_count=10), CTX_UNIT, UNIT_WORDS)

    assert provider.queries == ["creative Healthy Living", "collect Healthy Living"]
    # Chỉ thị vẫn đầy đủ cho model, chỉ là không dùng làm truy vấn nữa
    assert all("dùng CHUNG đúng MỘT họ từ" in o for o in provider.seen_overrides)


def test_bracket_call_queries_by_family_words():
    class CaptureProvider(BracketProvider):
        def __init__(self):
            super().__init__()
            self.queries: list[str | None] = []

        def generate(self, spec, context):
            self.queries.append(spec.retrieval_query)
            return super().generate(spec, context)

    provider = CaptureProvider()
    _word_form_bracket_drafts(provider, replace(BRACKET_SPEC, question_count=3), CTX_UNIT, FAMILIES[:1])

    assert provider.queries == ["science scientific scientist Healthy Living"]


# --- bù cho đủ số câu khi model trả thiếu ------------------------------------


class ShortProvider:
    """Trả đúng những câu được giao sẵn, ghi lại mỗi lần bị hỏi xin bao nhiêu câu."""

    def __init__(self, extra):
        self._extra = list(extra)
        self.asked: list[int] = []

    def generate(self, spec, context):
        self.asked.append(spec.question_count)
        return self._extra

    def regenerate_one(self, spec, context, exclude_prompt=None, feedback=None):
        raise AssertionError("không cần sinh lại khi câu đã sạch")


def test_short_block_is_topped_up_to_the_requested_count():
    """Prompt đã ghi "PHẢI có đúng N phần tử" mà model vẫn trả thiếu (đề sinh
    27/08/2026: xin 15 câu, gpt-4o-mini trả 13). Trước đây chỗ này chỉ CẮT phần thừa,
    không bù phần thiếu — đề ngắn đi mà không màn hình nào báo."""
    from app.services.generation import _top_up_drafts

    spec = BlockSpec(exercise_type_code="reading_true_false", question_count=5, level_code="A2")
    first = [_draft(f"Cau {i} ______ .", "use (v) → usage (n)") for i in range(3)]
    later = [_draft(f"Bu them {i} ______ .", "use (v) → usage (n)") for i in range(2)]
    provider = ShortProvider(later)

    drafts = _top_up_drafts(provider, spec, CTX, list(first))

    assert len(drafts) == 5
    assert provider.asked == [2]  # chỉ xin đúng phần còn thiếu


def test_a_block_already_full_does_not_call_the_provider_again():
    from app.services.generation import _top_up_drafts

    spec = BlockSpec(exercise_type_code="reading_true_false", question_count=3, level_code="A2")
    first = [_draft(f"Cau {i} ______ .", "use (v) → usage (n)") for i in range(3)]
    provider = ShortProvider([])

    assert len(_top_up_drafts(provider, spec, CTX, list(first))) == 3
    assert provider.asked == []


# --- chọn hạt giống và chặn trùng họ từ --------------------------------------


def test_words_that_can_form_a_family_are_tried_first():
    """Vốn từ của Unit phần lớn là danh từ/tính từ cụt (đo G7 Unit 1: chỉ 35/106 từ có
    dấu hiệu phái sinh). Lấy hạt giống theo đúng thứ tự danh sách thì 2 trong 4 từ đầu
    là 'cardboard', 'club' — không dựng nổi họ từ, model bèn quay về một họ nó thích."""
    from app.services.generation import _rank_seed_words

    ranked = _rank_seed_words(["cardboard", "club", "amazing", "creativity", "glue"])

    assert ranked[:2] == ["amazing", "creativity"]
    # Từ cụt không bị loại, chỉ đẩy xuống cuối — Unit nghèo từ phái sinh vẫn cần hạt giống
    assert set(ranked) == {"cardboard", "club", "amazing", "creativity", "glue"}


class OneFamilyProvider:
    """Lần nào cũng trả đúng một họ từ, bất kể hạt giống được ghim là gì."""

    def __init__(self, family):
        self._family = family
        self.calls = 0

    def generate(self, spec, context):
        self.calls += 1
        return [_draft(f"Cau {self.calls}-{i} ______ .", self._family) for i in range(spec.question_count)]

    def regenerate_one(self, spec, context, exclude_prompt=None, feedback=None):
        raise AssertionError("không cần sinh lại khi câu đã sạch")


def test_a_family_already_used_is_dropped_instead_of_shipped_twice():
    """Đề sinh 27/08/2026: cả 10 câu Phần A đều là họ 'amaze' (in ra thành 4 dòng ❖ chỉ
    vì nhãn ghi khác nhau đôi chút), rồi Phần B ôn lại đúng họ đó nên 10/10 câu đều
    '(amaze)'. Hết lượt thử mà vẫn trùng thì thà thiếu câu."""
    provider = OneFamilyProvider("amaze (v) → amazing (adj) → amazingly (adv)")
    spec = BlockSpec(
        exercise_type_code="word_form", question_count=10, level_code="A2",
        prompt_override="Chỉ dùng kiểu (A) nhóm theo họ từ cho toàn bộ các câu. Mỗi họ từ 5 câu.",
    )

    drafts = _word_form_family_drafts(provider, spec, CTX, UNIT_WORDS)

    assert len(_distinct_families(drafts)) == 1
    assert len(drafts) == 5  # chỉ nhận họ từ đầu tiên, không dồn 10 câu vào một họ


def test_machine_warnings_ride_along_with_the_question():
    """Cảnh báo của bộ kiểm bằng code phải ĐI THEO câu ra đề, không chỉ dùng làm điều
    kiện sinh lại. Đề sinh 27/08/2026 có 2 câu Phần A đáp án nằm ngoài họ từ được giao
    (sinh lại 2 lần vẫn hỏng nên câu vẫn ra đề) mà trang Duyệt hiện warnings rỗng."""
    from app.services.generation import _machine_warnings

    spec = BlockSpec(
        exercise_type_code="word_form", question_count=5, level_code="A2",
        prompt_override="Chỉ dùng kiểu (A) nhóm theo họ từ cho toàn bộ các câu.",
    )
    lac = _draft(
        "This movie is based on an ______ story.",
        "actually (adv) → actual (adj) → actively (adv)",
        answer_text="activities",
    )

    warnings = _machine_warnings(lac, spec)

    assert any("không thuộc họ từ" in w for w in warnings)
