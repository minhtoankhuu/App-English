"""Quản trị kho kiến thức (PRD mục 6 / DEVELOPMENT_PLAN 1C): liệt kê, xuất bản/ẩn,
xóa và nhập tài liệu .docx qua UI thay vì chỉ chạy script `app.import_knowledge`.

Nhập tài liệu bài học Global Success (gắn Unit) tái dùng đúng `parse_lesson_docx`;
nhập tài liệu ngữ pháp Kiến thức chung (gắn GrammarPoint) dùng
`parse_grammar_reference_docx` — cả hai theo cùng logic idempotent theo checksum
SHA-256 như script CLI (xem docs/superpowers/specs/2026-07-20-admin-knowledge-base-design.md
và 2026-07-20-grammar-reference-knowledge-design.md).
"""

import hashlib
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import require_admin
from app.models.academic import Unit
from app.models.grammar import GrammarGroup, GrammarPoint
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.schemas.knowledge import (
    KnowledgeChunkAdminOut,
    KnowledgeDocumentAdminOut,
    KnowledgeDocumentUpdateRequest,
)
from app.services.grammar_parser import parse_grammar_reference_docx
from app.services.knowledge_parser import parse_lesson_docx

router = APIRouter(prefix="/admin/knowledge-documents", tags=["admin"], dependencies=[Depends(require_admin)])

DOC_LOAD_OPTIONS = (
    selectinload(KnowledgeDocument.chunks),
    selectinload(KnowledgeDocument.unit).selectinload(Unit.grade),
    selectinload(KnowledgeDocument.grammar_point).selectinload(GrammarPoint.group).selectinload(GrammarGroup.topic),
)


def _document_out(document: KnowledgeDocument) -> dict:
    return {
        "id": document.id,
        "file_name": document.file_name,
        "is_published": document.is_published,
        "chunk_count": len(document.chunks),
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "unit": (
            {
                "id": document.unit.id,
                "order_no": document.unit.order_no,
                "title": document.unit.title,
                "grade_number": document.unit.grade.number,
            }
            if document.unit
            else None
        ),
        "grammar_point": (
            {
                "id": document.grammar_point.id,
                "name": document.grammar_point.name,
                "group_name": document.grammar_point.group.name,
                "topic_name": document.grammar_point.group.topic.name,
            }
            if document.grammar_point
            else None
        ),
    }


def _get_document(db: Session, document_id: uuid.UUID) -> KnowledgeDocument:
    document = db.scalar(
        select(KnowledgeDocument).options(*DOC_LOAD_OPTIONS).where(KnowledgeDocument.id == document_id)
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu")
    return document


@router.get("", response_model=list[KnowledgeDocumentAdminOut])
def list_documents(db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(KnowledgeDocument).options(*DOC_LOAD_OPTIONS).order_by(KnowledgeDocument.created_at.desc())
    documents = db.scalars(stmt).unique().all()
    return [_document_out(d) for d in documents]


@router.post("", response_model=KnowledgeDocumentAdminOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    unit_id: uuid.UUID | None = Form(None),
    grammar_point_id: uuid.UUID | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    if (unit_id is None) == (grammar_point_id is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Chọn đúng một nguồn: Unit hoặc GrammarPoint"
        )
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chỉ nhận file .docx")

    if unit_id is not None:
        if db.get(Unit, unit_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unit không tồn tại")
        match_filter = (KnowledgeDocument.unit_id == unit_id,)
    else:
        if db.get(GrammarPoint, grammar_point_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="GrammarPoint không tồn tại")
        match_filter = (KnowledgeDocument.grammar_point_id == grammar_point_id,)

    content = await file.read()
    checksum = hashlib.sha256(content).hexdigest()

    existing = db.scalar(
        select(KnowledgeDocument)
        .options(*DOC_LOAD_OPTIONS)
        .where(*match_filter, KnowledgeDocument.file_name == file.filename)
    )
    if existing is not None and existing.checksum == checksum:
        return _document_out(existing)

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        parsed_chunks = (
            parse_lesson_docx(tmp_path) if unit_id is not None else parse_grammar_reference_docx(tmp_path)
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    if existing is not None:
        existing.checksum = checksum
        existing.chunks.clear()
        document = existing
    else:
        document = KnowledgeDocument(
            unit_id=unit_id, grammar_point_id=grammar_point_id, file_name=file.filename, checksum=checksum
        )
        db.add(document)

    for chunk in parsed_chunks:
        document.chunks.append(
            KnowledgeChunk(
                order_no=chunk.order_no,
                chunk_type=chunk.chunk_type,
                section_title=chunk.section_title,
                raw_text=chunk.raw_text,
                structured=chunk.structured,
            )
        )
    db.commit()
    return _document_out(_get_document(db, document.id))


@router.get("/{document_id}/chunks", response_model=list[KnowledgeChunkAdminOut])
def list_document_chunks(document_id: uuid.UUID, db: Session = Depends(get_db)) -> list[KnowledgeChunk]:
    document = _get_document(db, document_id)
    return sorted(document.chunks, key=lambda chunk: chunk.order_no)


@router.patch("/{document_id}", response_model=KnowledgeDocumentAdminOut)
def update_document(
    document_id: uuid.UUID, payload: KnowledgeDocumentUpdateRequest, db: Session = Depends(get_db)
) -> dict:
    document = _get_document(db, document_id)
    document.is_published = payload.is_published
    db.commit()
    return _document_out(_get_document(db, document_id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    document = _get_document(db, document_id)
    db.delete(document)
    db.commit()
