"""Test bố cục DOCX (thụt lề, đánh số, ẩn/hiện tiêu đề Phần con) bằng cách dựng
`Document` trực tiếp từ các đối tượng giả — không cần DB hay StreamingResponse.
Xem build_exam_document trong app/services/docx_renderer.py."""

from types import SimpleNamespace

from app.models.exam import ExportMode
from app.services.docx_renderer import PART_CONTENT_INDENT_CM, build_exam_document


def _opt(label, text, is_correct=False):
    return {"label": label, "text": text, "is_correct": is_correct}


def _question(part_id, prompt_text, options):
    return SimpleNamespace(
        id=f"q-{prompt_text[:4]}-{options[0]['text']}",
        part_id=part_id,
        prompt_text=prompt_text,
        passage_text=None,
        options=options,
        answer_text=options[0]["text"],
    )


def _exam(block):
    exam = SimpleNamespace(export_mode=ExportMode.PLAIN, title="Unit 1 Revision", blocks=[block])
    variant = SimpleNamespace(code="A", question_order={})
    return exam, variant


def _paragraph_by_text(doc, needle):
    for p in doc.paragraphs:
        if needle in p.text:
            return p
    raise AssertionError(f"Không tìm thấy đoạn chứa {needle!r}")


def _left_indent_cm(p):
    indent = p.paragraph_format.left_indent
    return 0.0 if indent is None else round(indent.cm, 3)


PRON_S = "Choose the word that has a different pronunciation of the ending -s/-es."
PRON_SOUND = "Choose the word that has a different sound in the underlined part."


def _pronunciation_block():
    part_s = SimpleNamespace(id="p1", order_no=1, title="Đuôi -s/-es", instruction=None)
    part_sound = SimpleNamespace(id="p2", order_no=2, title="Âm trong từ", instruction=None)
    questions = [
        _question("p1", PRON_S, [_opt("A", "dresses"), _opt("B", "kisses"), _opt("C", "houses"), _opt("D", "games")]),
        _question("p1", PRON_S, [_opt("A", "drinks"), _opt("B", "trains"), _opt("C", "hats"), _opt("D", "friends")]),
        _question("p2", PRON_SOUND, [_opt("A", "pean"), _opt("B", "cease"), _opt("C", "meat"), _opt("D", "dear")]),
        _question("p2", PRON_SOUND, [_opt("A", "friend"), _opt("B", "tried"), _opt("C", "diet"), _opt("D", "lie")]),
    ]
    return SimpleNamespace(
        id="b1",
        order_no=1,
        points=3,
        title="PRONUNCIATION",
        instruction=None,
        exercise_type=SimpleNamespace(code="pronunciation"),
        parts=[part_s, part_sound],
        questions=questions,
    )


def test_pronunciation_hides_part_headings():
    doc = build_exam_document(*_exam(_pronunciation_block()))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "Đuôi -s/-es" not in full_text
    assert "Âm trong từ" not in full_text
    assert "1. Đuôi" not in full_text


def test_pronunciation_labels_instruction_lines_with_letters():
    doc = build_exam_document(*_exam(_pronunciation_block()))
    # Câu dẫn mỗi phần con đánh nhãn chữ cái A/B/C (không phải số).
    assert _paragraph_by_text(doc, PRON_S).text.startswith("A.")
    assert _paragraph_by_text(doc, PRON_SOUND).text.startswith("B.")


def test_pronunciation_numbers_every_question_continuously():
    doc = build_exam_document(*_exam(_pronunciation_block()))
    # Mỗi câu (kể cả câu đầu mỗi phần) đều có số riêng, chạy liên tục 1..4.
    assert _paragraph_by_text(doc, "dresses").text.startswith("1.")
    assert _paragraph_by_text(doc, "drinks").text.startswith("2.")
    # Phần 2 nối tiếp số (3, 4), không đánh lại từ 1.
    assert _paragraph_by_text(doc, "pean").text.startswith("3.")
    assert _paragraph_by_text(doc, "tried").text.startswith("4.")


def test_pronunciation_indents_instruction_but_not_question_rows():
    doc = build_exam_document(*_exam(_pronunciation_block()))
    # Dòng hướng dẫn A/B/C thụt vào trong.
    assert _left_indent_cm(_paragraph_by_text(doc, PRON_S)) == round(PART_CONTENT_INDENT_CM, 3)
    # Hàng câu hỏi (số + lựa chọn A/B/C/D) nằm sát lề trái.
    assert _left_indent_cm(_paragraph_by_text(doc, "dresses")) == 0.0
    assert _left_indent_cm(_paragraph_by_text(doc, "drinks")) == 0.0


def test_pronunciation_instruction_printed_once_per_part():
    doc = build_exam_document(*_exam(_pronunciation_block()))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert full_text.count(PRON_S) == 1
    assert full_text.count(PRON_SOUND) == 1


STRESS_PROMPT = "Which word has a different stress pattern?"


def _stress_block():
    """Khối STRESS không có phần con nhưng các câu dùng chung 1 câu dẫn."""
    questions = [
        _question(None, STRESS_PROMPT, [_opt(label, word) for label, word in zip("ABCD", words)])
        for words in (
            ["celebrate", "decorate", "exhibition", "international"],
            ["thanksgiving", "entertain", "competition", "celebration"],
            ["festival", "carnival", "feast", "celebration"],
        )
    ]
    return SimpleNamespace(
        id="b-stress",
        order_no=1,
        points=1,
        title="STRESS",
        instruction=None,
        exercise_type=SimpleNamespace(code="stress"),
        parts=[],
        questions=questions,
    )


def test_stress_prints_instruction_alone_and_numbers_every_question():
    """Bug: số thứ tự bị gộp lên dòng câu dẫn nên hàng lựa chọn đầu tiên mất số
    (ảnh giáo viên 21/07/2026 — khối II. STRESS)."""
    doc = build_exam_document(*_exam(_stress_block()))
    # Câu dẫn đứng riêng, KHÔNG mang số thứ tự.
    instruction_p = _paragraph_by_text(doc, STRESS_PROMPT)
    assert instruction_p.text.strip() == STRESS_PROMPT
    assert not instruction_p.text.strip().startswith("1.")
    # Mọi câu đều có số riêng, kể cả câu đầu nhóm.
    assert _paragraph_by_text(doc, "celebrate").text.startswith("1.")
    assert _paragraph_by_text(doc, "thanksgiving").text.startswith("2.")
    assert _paragraph_by_text(doc, "carnival").text.startswith("3.")


def test_unique_prompt_questions_keep_number_on_prompt_line():
    """Trắc nghiệm thường (mỗi câu 1 câu dẫn riêng) vẫn giữ 'số + câu dẫn cùng dòng',
    không bị đổi sang kiểu dòng hướng dẫn riêng."""
    questions = [
        _question(None, "We ______ books last month.", [_opt("A", "donate"), _opt("B", "donated")]),
        _question(None, "She ______ to school every day.", [_opt("A", "walk"), _opt("B", "walks")]),
    ]
    block = SimpleNamespace(
        id="b-mc",
        order_no=1,
        points=2,
        title="MULTIPLE CHOICE",
        instruction=None,
        exercise_type=SimpleNamespace(code="multiple_choice"),
        parts=[],
        questions=questions,
    )
    doc = build_exam_document(*_exam(block))
    assert _paragraph_by_text(doc, "We ______ books").text.startswith("1.")
    assert _paragraph_by_text(doc, "She ______ to school").text.startswith("2.")


def test_non_pronunciation_parts_keep_headings_and_restart_numbering():
    """Dạng có phần con là nội dung đề thật (vd SENTENCE TRANSFORMATION): vẫn hiện
    tiêu đề phần con và đánh số lại từ 1 mỗi phần — không bị ảnh hưởng bởi thay đổi
    dành riêng cho Pronunciation."""
    part_a = SimpleNamespace(id="pa", order_no=1, title="So sánh kép", instruction=None)
    part_b = SimpleNamespace(id="pb", order_no=2, title="Cụm động từ", instruction="Rewrite using phrasal verbs.")
    questions = [
        _question("pa", "Prompt A1", [_opt("A", "x1"), _opt("B", "y1")]),
        _question("pb", "Prompt B1", [_opt("A", "x2"), _opt("B", "y2")]),
    ]
    block = SimpleNamespace(
        id="b1",
        order_no=1,
        points=3,
        title="SENTENCE TRANSFORMATION",
        instruction=None,
        exercise_type=SimpleNamespace(code="sentence_rewrite"),
        parts=[part_a, part_b],
        questions=questions,
    )
    doc = build_exam_document(*_exam(block))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    assert "1. So sánh kép" in full_text
    assert "2. Cụm động từ" in full_text
    assert "Rewrite using phrasal verbs." in full_text
    # Mỗi phần đánh số lại từ 1: câu dẫn hai phần đều bắt đầu bằng "1.".
    assert _paragraph_by_text(doc, "Prompt A1").text.startswith("1.")
    assert _paragraph_by_text(doc, "Prompt B1").text.startswith("1.")
    # Phần con hiện tiêu đề thì lựa chọn cũng thụt theo câu dẫn.
    assert _left_indent_cm(_paragraph_by_text(doc, "x1")) == round(PART_CONTENT_INDENT_CM, 3)
