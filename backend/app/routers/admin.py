"""Admin quản lý tài khoản giáo viên (PRD 5.1). Chỉ thao tác trên tài khoản vai trò
teacher — không phải bảng quản trị người dùng chung; không xóa cứng tài khoản,
chỉ đổi is_active (PRD 12: dữ liệu có lịch sử ưu tiên xóa mềm/ngừng sử dụng)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_admin
from app.models.user import User, UserRole
from app.schemas.admin import TeacherCreateRequest, TeacherOut, TeacherUpdateRequest
from app.security import hash_password
from app.services.audit import record_audit_log

router = APIRouter(prefix="/admin/teachers", tags=["admin"], dependencies=[Depends(require_admin)])


def _get_teacher(db: Session, teacher_id: uuid.UUID) -> User:
    teacher = db.scalar(select(User).where(User.id == teacher_id, User.role == UserRole.TEACHER))
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giáo viên")
    return teacher


@router.get("", response_model=list[TeacherOut])
def list_teachers(db: Session = Depends(get_db)) -> list[User]:
    stmt = select(User).where(User.role == UserRole.TEACHER).order_by(User.created_at)
    return list(db.scalars(stmt))


@router.post("", response_model=TeacherOut, status_code=status.HTTP_201_CREATED)
def create_teacher(
    payload: TeacherCreateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> User:
    teacher = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.TEACHER,
        is_active=True,
    )
    db.add(teacher)
    try:
        db.flush()
        record_audit_log(db, actor=actor, action="teacher.created", target=teacher)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email đã được sử dụng")
    db.refresh(teacher)
    return teacher


@router.patch("/{teacher_id}", response_model=TeacherOut)
def update_teacher(
    teacher_id: uuid.UUID,
    payload: TeacherUpdateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
) -> User:
    teacher = _get_teacher(db, teacher_id)
    old_full_name = teacher.full_name
    was_active = teacher.is_active
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    if password:
        teacher.password_hash = hash_password(password)
    for field_name, value in data.items():
        setattr(teacher, field_name, value)
    if "full_name" in data and data["full_name"] != old_full_name:
        record_audit_log(
            db,
            actor=actor,
            action="teacher.updated",
            target=teacher,
            details={"changed_fields": ["full_name"]},
        )
    if "is_active" in data and data["is_active"] != was_active:
        record_audit_log(
            db,
            actor=actor,
            action="teacher.activated" if data["is_active"] else "teacher.deactivated",
            target=teacher,
        )
    if password:
        record_audit_log(db, actor=actor, action="teacher.password_reset", target=teacher)
    db.commit()
    db.refresh(teacher)
    return teacher
