"""Test in đậm tên người nói trong câu trắc nghiệm dạng hội thoại (yêu cầu chủ dự án
24/08/2026). Không cần DB — dựng Document trực tiếp bằng build_exam_document."""

from types import SimpleNamespace

import pytest
from docx import Document

from app.models.exam import ExportMode
from app.services.docx_renderer import _speaker_prefix_cuts, _speaker_prefix_len, build_exam_document

NL = chr(10)
DIALOGUE = f"Khanh Ngoc: What do you like to do in your free time?{NL}Tu Anh: I ______ computer games after school."


def _question(prompt_text):
    return SimpleNamespace(
        id="q1",
        part_id=None,
        prompt_text=prompt_text,
        passage_text=None,
        answer_text="A. text",
        options=[
            {"label": lb, "text": t, "is_correct": i == 0}
            for i, (lb, t) in enumerate(zip("ABCD", ["text", "paper", "voice", "hand"]))
        ],
    )


def _doc(prompt_text):
    block = SimpleNamespace(
        id="b1",
        order_no=1,
        title="VOCABULARY AND GRAMMAR",
        instruction="Choose the best answer.",
        points=2,
        parts=[],
        questions=[_question(prompt_text)],
        exercise_type=SimpleNamespace(code="multiple_choice"),
    )
    exam = SimpleNamespace(export_mode=ExportMode.PLAIN, title="Unit 1 Revision", blocks=[block])
    variant = SimpleNamespace(code="A", question_order={})
    return build_exam_document(exam, variant)


def _prompt_paragraph(doc, needle):
    return next(p for p in doc.paragraphs if needle in p.text)


def _bold_texts(paragraph):
    return [r.text for r in paragraph.runs if r.font.bold]


# --- nhận diện tên người nói -------------------------------------------------


@pytest.mark.parametrize(
    "line, expected",
    [
        ("Khanh: How are you?", 6),  # "Khanh:"
        ("Ngoc: I'm fine.", 5),
        ("A: Where do you live?", 2),  # đề thật cũng dùng nhãn 1 chữ cái
        ("Khanh Ngoc: Hello.", 11),  # tên hai chữ
        ("Mrs. Lan: Good morning.", 9),  # có dấu chấm viết tắt
        ("Nguyễn Minh Anh: Xin chào.", 16),  # dấu tiếng Việt
        # KHÔNG phải lượt thoại
        ("Choose the word that has a different sound.", 0),  # không có dấu hai chấm
        ("solar energy is a ______ source.", 0),  # chữ thường
        ("This sentence is long enough that the part before the colon has many words: x", 0),
        ("2020: a difficult year", 0),  # số, không phải tên
    ],
)
def test_speaker_prefix_len(line, expected):
    assert _speaker_prefix_len(line) == expected


def test_single_line_prompt_is_not_a_dialogue():
    """Câu dẫn 1 dòng kiểu "Note: ..." không được coi là hội thoại — nếu không thì
    mọi câu đơn có dấu hai chấm đều bị in đậm oan."""
    assert _speaker_prefix_cuts("Note: choose the best answer.") is None


def test_needs_two_speaker_lines():
    text = f"Read the passage below:{NL}It was a sunny day."
    assert _speaker_prefix_cuts(text) is None


def test_detects_two_turn_dialogue():
    assert _speaker_prefix_cuts(DIALOGUE) == [11, 7]


# --- render ra DOCX ----------------------------------------------------------


def test_dialogue_speaker_names_are_bold():
    doc = _doc(DIALOGUE)
    p = _prompt_paragraph(doc, "What do you like")

    assert "Khanh Ngoc:" in _bold_texts(p)
    assert "Tu Anh:" in _bold_texts(p)


def test_dialogue_content_stays_normal_weight():
    doc = _doc(DIALOGUE)
    p = _prompt_paragraph(doc, "What do you like")

    normal = "".join(r.text for r in p.runs if not r.font.bold)
    assert "What do you like to do in your free time?" in normal
    assert "I ______ computer games after school." in normal


def test_dialogue_keeps_line_break_between_turns():
    doc = _doc(DIALOGUE)
    p = _prompt_paragraph(doc, "What do you like")

    xml = p._element.xml
    assert "<w:br/>" in xml or "<w:br />" in xml


def test_single_sentence_prompt_has_no_bold_besides_number():
    """Câu đơn (không hội thoại): chỉ số thứ tự in đậm, thân câu giữ nguyên."""
    doc = _doc("Solar energy is a ______ source of power.")
    p = _prompt_paragraph(doc, "Solar energy")

    assert _bold_texts(p) == ["1."]


def test_dialogue_turns_align_under_first_speaker():
    """Lượt thoại 2 phải thẳng cột với lượt 1, không tụt về dưới số thứ tự:
    thụt treo = độ rộng chừa cho "1." + tab dừng đúng cột đó."""
    from app.services.docx_renderer import NUMBER_GUTTER_CM

    doc = _doc(DIALOGUE)
    p = _prompt_paragraph(doc, "What do you like")
    pf = p.paragraph_format

    # So theo cm (EMU bị làm tròn khi ghi ra XML).
    assert round(pf.left_indent.cm, 2) == NUMBER_GUTTER_CM
    assert round(pf.first_line_indent.cm, 2) == -NUMBER_GUTTER_CM
    assert [round(t.position.cm, 2) for t in pf.tab_stops] == [NUMBER_GUTTER_CM]
    # Số thứ tự đứng riêng rồi tab sang cột tên người nói (không dùng dấu cách,
    # vì bề rộng dấu cách không khớp với thụt treo).
    assert "<w:tab/>" in p._element.xml


def test_single_sentence_prompt_keeps_flat_indent():
    """Câu đơn không cần thụt treo — giữ nguyên bố cục cũ."""
    doc = _doc("Gardening is a ______ hobby for many people.")
    p = _prompt_paragraph(doc, "Gardening")

    assert p.paragraph_format.left_indent is None or p.paragraph_format.left_indent == 0
    assert p.paragraph_format.first_line_indent is None
