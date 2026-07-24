import random
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import require_teacher
from app.models.academic import Grade, ProficiencyLevel
from app.models.exam import (
    Exam,
    ExamBlock,
    ExamBlockPart,
    ExamGrammarSelection,
    ExamStatus,
    ExamVariant,
    Question,
    SourceType,
)
from app.models.exercise import ExerciseType
from app.models.user import User
from app.schemas.exam import (
    BlockCreateRequest,
    BlockOut,
    BlockPartCreateRequest,
    BlockPartReorderRequest,
    BlockPartUpdateRequest,
    BlockReorderRequest,
    BlockUpdateRequest,
    ExamCreateRequest,
    ExamDetailOut,
    ExamSummaryOut,
    ExamUpdateRequest,
    ExportConfigRequest,
    GrammarSelectionRequest,
    QuestionFlagsUpdateRequest,
    QuestionOut,
)
from app.schemas.exam_preview import ExamPreviewOut
from app.services.docx_renderer import render_exam_docx
from app.services.exam_preview import build_preview
from app.services.generation import embed_questions_for_bank, generate_block_questions, regenerate_question, shuffle_variant
from app.services.usage import UsageLimitExceeded, reserve_usage

router = APIRouter(prefix="/exams", tags=["exams"], dependencies=[Depends(require_teacher)])

BLOCK_LOAD_OPTIONS = (
    selectinload(Exam.blocks).selectinload(ExamBlock.exercise_type),
    selectinload(Exam.blocks).selectinload(ExamBlock.level_override),
    selectinload(Exam.blocks).selectinload(ExamBlock.questions).selectinload(Question.level),
    selectinload(Exam.blocks).selectinload(ExamBlock.parts),
)


def _validate_source_fields(payload) -> None:
    fields = {
        SourceType.GLOBAL_SUCCESS: "unit_id",
        SourceType.COMMON_KNOWLEDGE: "grammar_topic_id",
        SourceType.CAMBRIDGE: "cambridge_certificate_id",
    }
    required_field = fields[payload.source_type]
    if getattr(payload, required_field) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nguồn kiến thức '{payload.source_type.value}' cần trường '{required_field}'.",
        )
    for source_type, field_name in fields.items():
        if source_type != payload.source_type and getattr(payload, field_name) is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Trường '{field_name}' chỉ dùng khi nguồn kiến thức là '{source_type.value}'.",
            )


def _get_owned_exam(db: Session, exam_id: uuid.UUID, user: User) -> Exam:
    exam = db.scalar(select(Exam).options(*BLOCK_LOAD_OPTIONS).where(Exam.id == exam_id))
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đề")
    if exam.teacher_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền truy cập đề này")
    return exam


def _get_owned_block(exam: Exam, block_id: uuid.UUID) -> ExamBlock:
    block = next((b for b in exam.blocks if b.id == block_id), None)
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phần đề")
    return block


def _get_owned_question(block: ExamBlock, question_id: uuid.UUID) -> Question:
    question = next((q for q in block.questions if q.id == question_id), None)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy câu hỏi")
    return question


def _get_owned_part(block: ExamBlock, part_id: uuid.UUID) -> ExamBlockPart:
    part = next((p for p in block.parts if p.id == part_id), None)
    if part is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phần con")
    return part


def _sync_block_question_count(block: ExamBlock) -> None:
    """question_count của block = tổng question_count các phần con khi block có phần con
    (xem docs/superpowers/specs/2026-07-20-block-sub-parts-design.md)."""
    if block.parts:
        block.question_count = sum(p.question_count for p in block.parts)


def _exam_summary(exam: Exam) -> dict:
    total_questions = sum(len(b.questions) for b in exam.blocks)
    total_points = sum((b.points for b in exam.blocks), start=0)
    return {
        "id": exam.id,
        "title": exam.title,
        "status": exam.status,
        "grade_number": exam.grade.number,
        "level_code": exam.level.code,
        "total_questions": total_questions,
        "total_points": total_points,
        "export_mode": exam.export_mode,
        "variant_count": exam.variant_count,
        "updated_at": exam.updated_at,
    }


def _exam_detail(exam: Exam) -> dict:
    return {
        "id": exam.id,
        "title": exam.title,
        "status": exam.status,
        "source_type": exam.source_type,
        "grade_id": exam.grade_id,
        "level": exam.level,
        "unit_id": exam.unit_id,
        "grammar_topic_id": exam.grammar_topic_id,
        "cambridge_certificate_id": exam.cambridge_certificate_id,
        "extra_prompt": exam.extra_prompt,
        "export_mode": exam.export_mode,
        "variant_count": exam.variant_count,
        "grammar_point_ids": [s.grammar_point_id for s in exam.grammar_selections],
        "blocks": exam.blocks,
    }


@router.post("", response_model=ExamDetailOut, status_code=status.HTTP_201_CREATED)
def create_exam(
    payload: ExamCreateRequest, current_user: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> dict:
    _validate_source_fields(payload)
    if db.get(Grade, payload.grade_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Khối lớp không tồn tại")
    if db.get(ProficiencyLevel, payload.level_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Trình độ không tồn tại")

    exam = Exam(
        teacher_id=current_user.id,
        title=payload.title,
        grade_id=payload.grade_id,
        level_id=payload.level_id,
        source_type=payload.source_type,
        unit_id=payload.unit_id,
        grammar_topic_id=payload.grammar_topic_id,
        cambridge_certificate_id=payload.cambridge_certificate_id,
        extra_prompt=payload.extra_prompt,
    )
    db.add(exam)
    db.commit()
    return _exam_detail(_get_owned_exam(db, exam.id, current_user))


@router.get("", response_model=list[ExamSummaryOut])
def list_exams(current_user: User = Depends(require_teacher), db: Session = Depends(get_db)) -> list[dict]:
    stmt = (
        select(Exam)
        .options(*BLOCK_LOAD_OPTIONS, selectinload(Exam.grade), selectinload(Exam.level))
        .where(Exam.teacher_id == current_user.id)
        .order_by(Exam.updated_at.desc())
    )
    exams = db.scalars(stmt).all()
    return [_exam_summary(e) for e in exams]


@router.get("/{exam_id}/preview", response_model=ExamPreviewOut)
def get_exam_preview(
    exam_id: uuid.UUID, current_user: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> dict[str, object]:
    exam = _get_owned_exam(db, exam_id, current_user)
    return {"exam_id": exam.id, "title": exam.title, **build_preview(exam)}


@router.get("/{exam_id}", response_model=ExamDetailOut)
def get_exam(
    exam_id: uuid.UUID, current_user: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> dict:
    exam = _get_owned_exam(db, exam_id, current_user)
    return _exam_detail(exam)


@router.patch("/{exam_id}", response_model=ExamDetailOut)
def update_exam(
    exam_id: uuid.UUID,
    payload: ExamUpdateRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    exam = _get_owned_exam(db, exam_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    source_related_fields = {"source_type", "unit_id", "grammar_topic_id", "cambridge_certificate_id"}
    if source_related_fields & data.keys():
        merged = ExamCreateRequest(
            title=exam.title,
            grade_id=data.get("grade_id", exam.grade_id),
            level_id=data.get("level_id", exam.level_id),
            source_type=data.get("source_type", exam.source_type),
            unit_id=data.get("unit_id", exam.unit_id),
            grammar_topic_id=data.get("grammar_topic_id", exam.grammar_topic_id),
            cambridge_certificate_id=data.get("cambridge_certificate_id", exam.cambridge_certificate_id),
        )
        _validate_source_fields(merged)
    for field_name, value in data.items():
        setattr(exam, field_name, value)
    db.commit()
    return _exam_detail(_get_owned_exam(db, exam_id, current_user))


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: uuid.UUID, current_user: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> None:
    exam = _get_owned_exam(db, exam_id, current_user)
    db.delete(exam)
    db.commit()


@router.put("/{exam_id}/grammar-selection", response_model=ExamDetailOut)
def set_grammar_selection(
    exam_id: uuid.UUID,
    payload: GrammarSelectionRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    exam = _get_owned_exam(db, exam_id, current_user)
    db.query(ExamGrammarSelection).filter(ExamGrammarSelection.exam_id == exam.id).delete()
    for point_id in payload.grammar_point_ids:
        db.add(ExamGrammarSelection(exam_id=exam.id, grammar_point_id=point_id))
    db.commit()
    return _exam_detail(_get_owned_exam(db, exam_id, current_user))


@router.post("/{exam_id}/blocks", response_model=BlockOut, status_code=status.HTTP_201_CREATED)
def add_block(
    exam_id: uuid.UUID,
    payload: BlockCreateRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> ExamBlock:
    exam = _get_owned_exam(db, exam_id, current_user)
    if db.get(ExerciseType, payload.exercise_type_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dạng bài không tồn tại")
    next_order = (max((b.order_no for b in exam.blocks), default=0)) + 1
    block = ExamBlock(exam_id=exam.id, order_no=next_order, **payload.model_dump())
    db.add(block)
    db.commit()
    db.refresh(block)
    return _get_owned_block(_get_owned_exam(db, exam_id, current_user), block.id)


@router.patch("/{exam_id}/blocks/{block_id}", response_model=BlockOut)
def update_block(
    exam_id: uuid.UUID,
    block_id: uuid.UUID,
    payload: BlockUpdateRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> ExamBlock:
    exam = _get_owned_exam(db, exam_id, current_user)
    block = _get_owned_block(exam, block_id)
    data = payload.model_dump(exclude_unset=True)
    if block.parts:
        # question_count là tổng tự động của các phần con — sửa qua endpoint phần con,
        # không cho ghi đè trực tiếp để tránh hai nguồn sự thật (xem spec phần con).
        data.pop("question_count", None)
    for field_name, value in data.items():
        setattr(block, field_name, value)
    db.commit()
    return _get_owned_block(_get_owned_exam(db, exam_id, current_user), block_id)


@router.delete("/{exam_id}/blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_block(
    exam_id: uuid.UUID,
    block_id: uuid.UUID,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> None:
    exam = _get_owned_exam(db, exam_id, current_user)
    block = _get_owned_block(exam, block_id)
    db.delete(block)
    db.commit()


@router.post("/{exam_id}/blocks/reorder", response_model=ExamDetailOut)
def reorder_blocks(
    exam_id: uuid.UUID,
    payload: BlockReorderRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    exam = _get_owned_exam(db, exam_id, current_user)
    blocks_by_id = {b.id: b for b in exam.blocks}
    if set(payload.block_ids) != set(blocks_by_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Danh sách block không khớp đề")
    # 2 lượt để tránh vi phạm unique constraint (exam_id, order_no) giữa chừng
    for i, block_id in enumerate(payload.block_ids):
        blocks_by_id[block_id].order_no = -(i + 1)
    db.flush()
    for i, block_id in enumerate(payload.block_ids):
        blocks_by_id[block_id].order_no = i + 1
    db.commit()
    return _exam_detail(_get_owned_exam(db, exam_id, current_user))


@router.post("/{exam_id}/blocks/{block_id}/parts", response_model=BlockOut, status_code=status.HTTP_201_CREATED)
def add_block_part(
    exam_id: uuid.UUID,
    block_id: uuid.UUID,
    payload: BlockPartCreateRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> ExamBlock:
    exam = _get_owned_exam(db, exam_id, current_user)
    block = _get_owned_block(exam, block_id)
    next_order = (max((p.order_no for p in block.parts), default=0)) + 1
    part = ExamBlockPart(block_id=block.id, order_no=next_order, **payload.model_dump())
    db.add(part)
    db.flush()
    db.refresh(block, attribute_names=["parts"])
    _sync_block_question_count(block)
    db.commit()
    return _get_owned_block(_get_owned_exam(db, exam_id, current_user), block_id)


@router.patch("/{exam_id}/blocks/{block_id}/parts/{part_id}", response_model=BlockOut)
def update_block_part(
    exam_id: uuid.UUID,
    block_id: uuid.UUID,
    part_id: uuid.UUID,
    payload: BlockPartUpdateRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> ExamBlock:
    exam = _get_owned_exam(db, exam_id, current_user)
    block = _get_owned_block(exam, block_id)
    part = _get_owned_part(block, part_id)
    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(part, field_name, value)
    _sync_block_question_count(block)
    db.commit()
    return _get_owned_block(_get_owned_exam(db, exam_id, current_user), block_id)


@router.delete("/{exam_id}/blocks/{block_id}/parts/{part_id}", response_model=BlockOut)
def delete_block_part(
    exam_id: uuid.UUID,
    block_id: uuid.UUID,
    part_id: uuid.UUID,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> ExamBlock:
    exam = _get_owned_exam(db, exam_id, current_user)
    block = _get_owned_block(exam, block_id)
    part = _get_owned_part(block, part_id)
    block.parts.remove(part)
    _sync_block_question_count(block)
    db.commit()
    return _get_owned_block(_get_owned_exam(db, exam_id, current_user), block_id)


@router.post("/{exam_id}/blocks/{block_id}/parts/reorder", response_model=BlockOut)
def reorder_block_parts(
    exam_id: uuid.UUID,
    block_id: uuid.UUID,
    payload: BlockPartReorderRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> ExamBlock:
    exam = _get_owned_exam(db, exam_id, current_user)
    block = _get_owned_block(exam, block_id)
    parts_by_id = {p.id: p for p in block.parts}
    if set(payload.part_ids) != set(parts_by_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Danh sách phần con không khớp block")
    # 2 lượt để tránh vi phạm unique constraint (block_id, order_no) giữa chừng
    for i, part_id in enumerate(payload.part_ids):
        parts_by_id[part_id].order_no = -(i + 1)
    db.flush()
    for i, part_id in enumerate(payload.part_ids):
        parts_by_id[part_id].order_no = i + 1
    db.commit()
    return _get_owned_block(_get_owned_exam(db, exam_id, current_user), block_id)


@router.post("/{exam_id}/generate", response_model=ExamDetailOut)
def generate_exam(
    exam_id: uuid.UUID, current_user: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> dict:
    exam = _get_owned_exam(db, exam_id, current_user)
    if not exam.blocks:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Đề chưa có phần nào để sinh câu hỏi")
    try:
        reserve_usage(db, current_user, len(exam.blocks))
        for block in exam.blocks:
            generate_block_questions(db, exam, block)
        db.commit()
    except UsageLimitExceeded as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.status.to_error_detail()) from exc
    except Exception:
        db.rollback()
        raise
    return _exam_detail(_get_owned_exam(db, exam_id, current_user))


@router.patch("/{exam_id}/questions/{question_id}", response_model=QuestionOut)
def update_question_flags(
    exam_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: QuestionFlagsUpdateRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> Question:
    """Đặt tường minh is_approved/is_locked (không dùng toggle) — an toàn khi client
    gọi lại do mất mạng hoặc double-click, không âm thầm đảo trạng thái ngược lại."""
    exam = _get_owned_exam(db, exam_id, current_user)
    question = None
    for block in exam.blocks:
        question = next((q for q in block.questions if q.id == question_id), None)
        if question:
            break
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy câu hỏi")
    data = payload.model_dump(exclude_unset=True)
    for field_name, value in data.items():
        setattr(question, field_name, value)
    db.commit()
    db.refresh(question)
    return question


@router.post("/{exam_id}/questions/{question_id}/regenerate", response_model=QuestionOut)
def regenerate(
    exam_id: uuid.UUID,
    question_id: uuid.UUID,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> Question:
    exam = _get_owned_exam(db, exam_id, current_user)
    owning_block = None
    question = None
    for block in exam.blocks:
        question = next((q for q in block.questions if q.id == question_id), None)
        if question:
            owning_block = block
            break
    if question is None or owning_block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy câu hỏi")
    if question.is_locked:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Câu đã khóa — không sinh lại được")
    if question.is_approved:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bỏ duyệt trước khi sinh lại")
    try:
        reserve_usage(db, current_user, 1)
        regenerate_question(db, exam, owning_block, question)
        db.commit()
    except UsageLimitExceeded as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.status.to_error_detail()) from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(question)
    return question


def _finalize_review(db: Session, exam: Exam, all_questions: list[Question]) -> None:
    embed_questions_for_bank(db, all_questions)
    for q in all_questions:
        q.is_in_bank = True
    exam.status = ExamStatus.REVIEWED


@router.post("/{exam_id}/complete-review", response_model=ExamDetailOut)
def complete_review(
    exam_id: uuid.UUID, current_user: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> dict:
    exam = _get_owned_exam(db, exam_id, current_user)
    all_questions = [q for b in exam.blocks for q in b.questions]
    if not all_questions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Đề chưa có câu hỏi nào")
    if not all(q.is_approved for q in all_questions):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Còn câu chưa được duyệt")
    _finalize_review(db, exam, all_questions)
    db.commit()
    return _exam_detail(_get_owned_exam(db, exam_id, current_user))


@router.post("/{exam_id}/approve-all", response_model=ExamDetailOut)
def approve_all_questions(
    exam_id: uuid.UUID, current_user: User = Depends(require_teacher), db: Session = Depends(get_db)
) -> dict:
    """Duyệt toàn bộ câu hỏi của đề trong 1 lần bấm (thay vì duyệt từng câu ở trang
    Duyệt câu) rồi hoàn tất kiểm duyệt luôn — dùng khi giáo viên đã xem qua bản xem
    trước A4 và thấy nội dung ổn, không cần duyệt từng câu."""
    exam = _get_owned_exam(db, exam_id, current_user)
    all_questions = [q for b in exam.blocks for q in b.questions]
    if not all_questions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Đề chưa có câu hỏi nào")
    for q in all_questions:
        q.is_approved = True
    _finalize_review(db, exam, all_questions)
    db.commit()
    return _exam_detail(_get_owned_exam(db, exam_id, current_user))


@router.post("/{exam_id}/export-config", response_model=ExamDetailOut)
def save_export_config(
    exam_id: uuid.UUID,
    payload: ExportConfigRequest,
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    exam = _get_owned_exam(db, exam_id, current_user)
    if exam.status == ExamStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Đề chưa được kiểm duyệt xong")

    db.query(ExamVariant).filter(ExamVariant.exam_id == exam.id).delete()
    codes = ["A", "B", "C", "D"][: payload.variant_count]
    for code in codes:
        seed = random.randint(1, 2**31 - 1)
        db.add(ExamVariant(exam_id=exam.id, code=code, seed=seed, question_order=shuffle_variant(exam, seed)))

    exam.export_mode = payload.export_mode
    exam.variant_count = payload.variant_count
    exam.status = ExamStatus.READY
    db.commit()
    return _exam_detail(_get_owned_exam(db, exam_id, current_user))


@router.get("/{exam_id}/export.docx")
def export_docx(
    exam_id: uuid.UUID,
    variant: str = "A",
    current_user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
):
    exam = _get_owned_exam(db, exam_id, current_user)
    if exam.status != ExamStatus.READY or exam.export_mode is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Đề chưa lưu cấu hình xuất")
    exam_variant = db.scalar(
        select(ExamVariant).where(ExamVariant.exam_id == exam.id, ExamVariant.code == variant.upper())
    )
    if exam_variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mã đề")
    return render_exam_docx(exam, exam_variant)
