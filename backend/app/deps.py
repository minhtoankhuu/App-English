import uuid

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User, UserRole


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa đăng nhập")
    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập không hợp lệ")
    user = db.get(User, user_uuid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không hợp lệ")
    return user


def require_role(*roles: UserRole):
    def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không đủ quyền truy cập")
        return user

    return _check


require_admin = require_role(UserRole.ADMIN)
require_any_role = require_role(UserRole.ADMIN, UserRole.TEACHER)
