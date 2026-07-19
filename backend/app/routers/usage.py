from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_any_role
from app.models.user import User
from app.schemas.usage import UsageStatusOut
from app.services.usage import get_usage_status

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/me", response_model=UsageStatusOut)
def my_usage(current_user: User = Depends(require_any_role), db: Session = Depends(get_db)) -> dict[str, object]:
    return get_usage_status(db, current_user).to_dict()
