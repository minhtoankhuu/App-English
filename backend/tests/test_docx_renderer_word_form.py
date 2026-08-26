"""Test bố cục WORD FORMATION theo format đề thật (yêu cầu chủ dự án 24/08/2026):
Phần A gom câu theo họ từ với dòng "❖ ...", Phần B đặt từ gốc trong ngoặc canh sát
lề phải. Không cần DB."""

from types import SimpleNamespace

import pytest
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.models.exam import ExportMode
from app.services.docx_renderer import (
    PART_CONTENT_INDENT_CM,
    USABLE_WIDTH_CM,
    WORD_FAMILY_BULLET,
    build_exam_document,
    normalize_bracket_root,
    split_bracket_root,
    word_family_label,
)

ADORE = "adore (v) → adorable (adj) → adorably (adv)"
ADDICT = "addicted (adj) → addict (n) → addiction (n)"


def _q(qid, part_id, prompt_text, target_knowledge):
    return SimpleNamespace(
        id=qid,
        part_id=part_id,
        prompt_text=prompt_text,
        passage_text=None,
        answer_text="x",
        target_knowledge=target_knowledge,
        options=None,
    )


def _block(parts, questions):
    return SimpleNamespace(
        id="b1",
        order_no=1,
        title="WORD FORMATION",
        instruction="Fill in the blanks with the correct form of the words",
        points=2,
        parts=parts,
        questions=questions,
        exercise_type=SimpleNamespace(code="word_form"),
    )


PART_A = SimpleNamespace(
    id="pa", order_no=1, title="Fill in the blanks with the correct form of the words", instruction=None
)
PART_B = SimpleNamespace(
    id="pb", order_no=2, title="Part B. Fill in the blanks with the correct form of the word in brackets.",
    instruction=None,
)

QUESTIONS = [
    _q("q1", "pa", "My little sister ______ her teddy bear before going to bed at night.", ADORE),
    _q("q2", "pa", "The puppies were extremely ______ and made everyone smile happily.", ADORE),
    _q("q3", "pa", "She looked at her birthday gift and smiled ______.", ADORE),
    _q("q4", "pa", "My cousin is ______ to watching TV and spends hours in front of the screen.", ADDICT),
    _q("q5", "pa", "Linh's brother is a video game ______ who plays every single afternoon.", ADDICT),
    _q("q6", "pb", "Many teenagers really ______ playing online games at night. (adorable)", "Word form"),
    _q("q7", "pb", "Ngan Khanh looked ______ when she saw her favorite singer. (adore)", "Word form"),
]


def _doc():
    exam = SimpleNamespace(
        export_mode=ExportMode.PLAIN,
        title="Unit 1 Revision",
        blocks=[_block([PART_A, PART_B], QUESTIONS)],
    )
    return build_exam_document(exam, SimpleNamespace(code="A", question_order={}))


def _texts(doc):
    return [p.text for p in doc.paragraphs]


def _para(doc, needle):
    return next(p for p in doc.paragraphs if needle in p.text)


# --- nhận diện họ từ ---------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("adore (v) → adorable (adj) → adorably (adv)", ADORE),
        ("adore (v) -> adorable (adj) -> adorably (adv)", ADORE),  # mũi tên ASCII
        ("adore(v)→adorable(adj)→adorably(adv)", "adore(v) → adorable(adj) → adorably(adv)"),
        # KHÔNG phải họ từ — mô tả kiến thức thông thường vẫn có mũi tên
        ("Word form: verb → noun (decide → decision)", None),
        ("Word form: adjective to noun", None),
        ("", None),
        (None, None),
    ],
)
def test_word_family_label(raw, expected):
    assert word_family_label(raw) == expected


@pytest.mark.parametrize(
    "raw, sentence, root",
    [
        ("Many teenagers really ______ playing games. (adorable)", "Many teenagers really ______ playing games.", "adorable"),
        ("Ngan Khanh looked ______ at the festival.(adore)", "Ngan Khanh looked ______ at the festival.", "adore"),
        ("No bracket at the end.", "No bracket at the end.", None),
        # ngoặc giữa câu không phải từ gốc
        ("She (finally) ______ the exam.", "She (finally) ______ the exam.", None),
    ],
)
def test_split_bracket_root(raw, sentence, root):
    assert split_bracket_root(raw) == (sentence, root)


# --- Phần A: gom theo họ từ --------------------------------------------------


def test_prints_family_heading_once_per_group():
    texts = _texts(_doc())
    assert texts.count(f"{WORD_FAMILY_BULLET} {ADORE}") == 1
    assert texts.count(f"{WORD_FAMILY_BULLET} {ADDICT}") == 1


def test_family_heading_is_bold_and_centered():
    doc = _doc()
    p = _para(doc, ADORE)
    assert p.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert all(r.font.bold for r in p.runs if r.text.strip())


def test_family_heading_precedes_its_questions():
    texts = _texts(_doc())
    assert texts.index(f"{WORD_FAMILY_BULLET} {ADORE}") < texts.index(
        "1. My little sister ______ her teddy bear before going to bed at night."
    )
    assert texts.index("3. She looked at her birthday gift and smiled ______.") < texts.index(
        f"{WORD_FAMILY_BULLET} {ADDICT}"
    )


def test_numbering_runs_continuously_across_families():
    """Đổi họ từ KHÔNG đánh số lại — đề thật đánh 1..18 xuyên các nhóm."""
    texts = _texts(_doc())
    assert any(t.startswith("4. My cousin is") for t in texts)
    assert any(t.startswith("5. Linh's brother") for t in texts)


def test_part_b_restarts_numbering():
    """Part B là Phần con riêng nên đánh số lại từ 1."""
    texts = _texts(_doc())
    assert any(t.startswith("1. Many teenagers really") for t in texts)
    assert any(t.startswith("2. Ngan Khanh looked") for t in texts)


# --- Phần B: từ gốc trong ngoặc ----------------------------------------------


def test_bracket_root_is_bold_and_right_aligned():
    doc = _doc()
    p = _para(doc, "Many teenagers really")

    bold = [r.text for r in p.runs if r.font.bold]
    assert "(adorable)" in bold
    right_tabs = [t for t in p.paragraph_format.tab_stops if round(t.position.cm, 2) == round(USABLE_WIDTH_CM, 2)]
    assert right_tabs, "phải có tab canh phải ở mép lề phải"
    assert "<w:tab/>" in p._element.xml


def test_bracket_root_removed_from_sentence():
    """Từ gốc chuyển sang cột phải — không được lặp lại trong thân câu."""
    doc = _doc()
    p = _para(doc, "Many teenagers really")
    sentence = "".join(r.text for r in p.runs if not r.font.bold)
    assert "(adorable)" not in sentence
    assert sentence.strip().endswith("playing online games at night.")


def test_part_a_questions_have_no_bracket_column():
    doc = _doc()
    p = _para(doc, "My little sister")
    assert list(p.paragraph_format.tab_stops) == []


# --- tiêu đề Phần con --------------------------------------------------------


def test_part_heading_has_no_order_number():
    """Tiêu đề Phần con của word form CHÍNH LÀ câu lệnh ("Part B. Fill in...") —
    thêm "2." vào trước sẽ thành "2. Part B. ..." rất tối nghĩa."""
    texts = _texts(_doc())
    assert PART_B.title in texts
    assert f"2. {PART_B.title}" not in texts


def test_part_heading_indented_but_questions_at_margin():
    doc = _doc()
    heading = _para(doc, "Part B.")
    question = _para(doc, "Many teenagers really")

    assert round(heading.paragraph_format.left_indent.cm, 2) == PART_CONTENT_INDENT_CM
    assert question.paragraph_format.left_indent is None or question.paragraph_format.left_indent == 0


# --- từ gốc bị đặt giữa câu (đề thật 24/08/2026) -----------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # model đặt ngoặc ngay sau chỗ trống thay vì cuối câu
        ("The teacher explained the ______ (formally) of the lesson plan.",
         "The teacher explained the ______ of the lesson plan. (formally)"),
        ("He spoke very ______ (form) during the presentation.",
         "He spoke very ______ during the presentation. (form)"),
        # đã ở cuối câu -> giữ nguyên
        ("To show ______ in difficult situations. (maturity)",
         "To show ______ in difficult situations. (maturity)"),
        # không có ngoặc -> giữ nguyên
        ("No bracket here at all.", "No bracket here at all."),
        # nhiều ngoặc -> lấy cái cuối cùng làm từ gốc
        ("She (finally) ______ the exam (succeed) last week.",
         "She (finally) ______ the exam last week. (succeed)"),
    ],
)
def test_normalize_bracket_root(raw, expected):
    assert normalize_bracket_root(raw) == expected


def test_render_moves_inline_bracket_to_the_right_margin():
    """Đề cũ đã lưu sai vị trí vẫn in đúng khi tải lại, không cần sinh lại."""
    from app.services.docx_renderer import USABLE_WIDTH_CM

    exam = SimpleNamespace(
        export_mode=ExportMode.PLAIN, title="Unit 1 Revision",
        blocks=[_block([PART_B], [
            _q("q1", "pb", "The teacher explained the ______ (formally) of the lesson plan.", "Chuyển từ loại"),
        ])],
    )
    doc = build_exam_document(exam, SimpleNamespace(code="A", question_order={}))
    p = _para(doc, "The teacher explained")

    assert "(formally)" in [r.text for r in p.runs if r.font.bold]
    normal = "".join(r.text for r in p.runs if not r.font.bold)
    assert "(formally)" not in normal
    assert normal.strip().endswith("of the lesson plan.")
    assert [round(t.position.cm, 2) for t in p.paragraph_format.tab_stops] == [round(USABLE_WIDTH_CM, 2)]
