import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import require_any_role
from app.models.academic import Unit
from app.models.knowledge import DocumentChunkType, KnowledgeChunk, KnowledgeDocument
from app.schemas.knowledge import KnowledgeChunkOut

router = APIRouter(prefix="/knowledge", tags=["knowledge"], dependencies=[Depends(require_any_role)])


@router.get("/search", response_model=list[KnowledgeChunkOut])
def search_knowledge(
    unit_id: uuid.UUID | None = None,
    grade_id: uuid.UUID | None = None,
    chunk_type: DocumentChunkType | None = None,
    q: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[KnowledgeChunk]:
    stmt = (
        select(KnowledgeChunk)
        .join(KnowledgeChunk.document)
        .options(selectinload(KnowledgeChunk.document))
        .where(KnowledgeDocument.is_published.is_(True))
    )

    if unit_id is not None:
        stmt = stmt.where(KnowledgeDocument.unit_id == unit_id)
    if grade_id is not None:
        stmt = stmt.join(Unit, Unit.id == KnowledgeDocument.unit_id).where(Unit.grade_id == grade_id)
    if chunk_type is not None:
        stmt = stmt.where(KnowledgeChunk.chunk_type == chunk_type)

    if q:
        tsquery = func.plainto_tsquery("simple", q)
        stmt = stmt.where(KnowledgeChunk.search_vector.op("@@")(tsquery))
        stmt = stmt.order_by(func.ts_rank(KnowledgeChunk.search_vector, tsquery).desc())
    else:
        stmt = stmt.order_by(KnowledgeDocument.unit_id, KnowledgeChunk.order_no)

    stmt = stmt.limit(limit)
    return list(db.scalars(stmt))
