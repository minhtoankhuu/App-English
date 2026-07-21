"""Dựng file DOCX từ đề đã duyệt, theo đúng thông số đã chốt với giáo viên
(Implementation Notes mục 2 / PRD mục 14). Không dùng trực tiếp văn bản thô của
LLM — dữ liệu đến từ Question đã qua Validation Engine và được giáo viên duyệt."""

import io
import re

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from fastapi.responses import StreamingResponse

from app.models.exam import Exam, ExamVariant, ExportMode

RED = RGBColor(0xC0, 0x00, 0x00)
FONT_NAME = "Times New Roman"
# LLM đánh dấu phần cần gạch chân bằng <u>...</u> trong text lựa chọn (dạng phát âm/
# trọng âm — PRD 7.3 yêu cầu gạch chân âm/trọng âm khác biệt trong đề in ra, xem
# app/services/prompts.py). Không dùng docx run.underline trực tiếp từ LLM vì output
# LLM là JSON text thuần, không phải OOXML.
_UNDERLINE_MARKUP_RE = re.compile(r"<u>(.*?)</u>")
PAGE_WIDTH_CM = 21.0
MARGIN_CM = 1.27
USABLE_WIDTH_CM = PAGE_WIDTH_CM - 2 * MARGIN_CM
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
LONG_OPTION_THRESHOLD = 24


def _set_font(run, size: float = 11.5, bold: bool = False, color: RGBColor | None = None) -> None:
    run.font.name = FONT_NAME
    run.font.size = Pt(size)
    run.font.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    r_fonts = rpr.find(qn("w:rFonts"))
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        rpr.append(r_fonts)
    r_fonts.set(qn("w:ascii"), FONT_NAME)
    r_fonts.set(qn("w:hAnsi"), FONT_NAME)


def _add_runs_with_underline(p, text: str, *, bold: bool = False, color: RGBColor | None = None) -> None:
    """Tách `text` theo marker `<u>...</u>` thành nhiều run — phần trong marker được
    `run.font.underline = True`, phần còn lại giữ nguyên. Không có marker thì y hệt
    hành vi cũ (1 run duy nhất)."""
    pos = 0
    for match in _UNDERLINE_MARKUP_RE.finditer(text):
        if match.start() > pos:
            run = p.add_run(text[pos : match.start()])
            _set_font(run, bold=bold, color=color)
        underline_run = p.add_run(match.group(1))
        _set_font(underline_run, bold=bold, color=color)
        underline_run.font.underline = True
        pos = match.end()
    if pos < len(text):
        run = p.add_run(text[pos:])
        _set_font(run, bold=bold, color=color)


def _new_paragraph(doc: Document, *, justify: bool = False, center: bool = False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = 1.15
    if justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def _visible_length(text: str) -> int:
    """Độ dài không tính marker <u></u> (14 ký tự không hiển thị) — tránh option ngắn
    có gạch chân bị tính nhầm là dài, kéo cả hàng xuống 2 lựa chọn/dòng."""
    return len(_UNDERLINE_MARKUP_RE.sub(r"\1", text))


def _render_options(doc: Document, options: list[dict], with_key: bool) -> None:
    max_len = max(_visible_length(opt["text"]) for opt in options)
    per_line = 2 if max_len > LONG_OPTION_THRESHOLD else 4
    step_cm = USABLE_WIDTH_CM / per_line

    for i in range(0, len(options), per_line):
        row = options[i : i + per_line]
        p = _new_paragraph(doc)
        for k in range(1, len(row)):
            p.paragraph_format.tab_stops.add_tab_stop(Cm(step_cm * k))
        for j, opt in enumerate(row):
            if j > 0:
                p.add_run().add_tab()
            highlight = with_key and bool(opt.get("is_correct"))
            label_run = p.add_run(f"{opt['label']}. ")
            _set_font(label_run, bold=True, color=RED if highlight else None)
            _add_runs_with_underline(p, opt["text"], bold=highlight, color=RED if highlight else None)


def render_exam_docx(exam: Exam, variant: ExamVariant) -> StreamingResponse:
    with_key = exam.export_mode == ExportMode.ANSWER_KEY

    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(PAGE_WIDTH_CM)
    section.page_height = Cm(29.7)
    section.top_margin = section.bottom_margin = Cm(MARGIN_CM)
    section.left_margin = section.right_margin = Cm(MARGIN_CM)

    student_line_p = _new_paragraph(doc)
    student_run = student_line_p.add_run("Full name: .......................................... Class: ..........")
    _set_font(student_run)

    _new_paragraph(doc)

    title_p = _new_paragraph(doc, center=True)
    title_run = title_p.add_run(f"{exam.title.upper()} — MÃ ĐỀ {variant.code}")
    _set_font(title_run, size=14, bold=True)

    ordered_blocks = sorted(exam.blocks, key=lambda b: b.order_no)
    question_no = 0
    for idx, block in enumerate(ordered_blocks):
        _new_paragraph(doc)  # dòng trống ngăn cách phần

        point_label = "point" if block.points == 1 else "points"
        heading_p = _new_paragraph(doc)
        heading_run = heading_p.add_run(
            f"{ROMAN[idx] if idx < len(ROMAN) else idx + 1}. {block.title.upper()} ({block.points} {point_label})"
        )
        _set_font(heading_run, bold=True)

        order = variant.question_order.get(str(block.id), [str(q.id) for q in block.questions])
        by_id = {str(q.id): q for q in block.questions}
        ordered_questions = [by_id[qid] for qid in order if qid in by_id]
        parts_by_id = {p.id: p for p in block.parts}

        current_part_id = None
        started = False
        for question in ordered_questions:
            if not started or question.part_id != current_part_id:
                started = True
                current_part_id = question.part_id
                part = parts_by_id.get(current_part_id) if current_part_id else None
                if part is not None:
                    part_heading_p = _new_paragraph(doc)
                    part_heading_run = part_heading_p.add_run(f"{part.order_no}. {part.title}")
                    _set_font(part_heading_run, bold=True)
                    if part.instruction:
                        part_instruction_p = _new_paragraph(doc)
                        part_instruction_run = part_instruction_p.add_run(part.instruction)
                        _set_font(part_instruction_run)

            question_no += 1

            if question.passage_text:
                passage_p = _new_paragraph(doc, justify=True)
                passage_run = passage_p.add_run(question.passage_text)
                _set_font(passage_run)

            prompt_p = _new_paragraph(doc)
            no_run = prompt_p.add_run(f"{question_no}. ")
            _set_font(no_run, bold=True)
            text_run = prompt_p.add_run(question.prompt_text)
            _set_font(text_run)

            if question.options:
                _render_options(doc, question.options, with_key)
            elif with_key:
                answer_p = _new_paragraph(doc)
                answer_run = answer_p.add_run(f"Đáp án: {question.answer_text}")
                _set_font(answer_run, bold=True, color=RED)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    suffix = "dap-an-do" if with_key else "hoc-sinh"
    filename = f"de-ma-{variant.code.lower()}-{suffix}.docx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
