from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogPage

router = APIRouter(prefix="/admin/audit-logs", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("", response_model=AuditLogPage)
def list_audit_logs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> AuditLogPage:
    total = db.scalar(select(func.count()).select_from(AuditLog)) or 0
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(offset).limit(limit)
    items = list(db.scalars(stmt))
    return AuditLogPage(items=items, total=total, limit=limit, offset=offset)
