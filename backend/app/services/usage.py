from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.usage import DailyUsage
from app.models.user import User, UserRole

BANGKOK_TIMEZONE = ZoneInfo("Asia/Bangkok")


@dataclass(frozen=True)
class UsageStatus:
    limit: int
    used: int
    remaining: int
    usage_date: date
    reset_at: datetime
    is_unlimited: bool

    def to_error_detail(self) -> dict[str, object]:
        return {
            "message": "Đã vượt hạn mức sinh đề hôm nay",
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "reset_at": self.reset_at.isoformat(),
        }

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class UsageLimitExceeded(Exception):
    def __init__(self, status: UsageStatus):
        super().__init__("Daily generation limit exceeded")
        self.status = status


def _bangkok_now(now: datetime | None) -> datetime:
    return (now or datetime.now(BANGKOK_TIMEZONE)).astimezone(BANGKOK_TIMEZONE)


def _status(used: int, now: datetime | None, *, is_unlimited: bool = False) -> UsageStatus:
    current = _bangkok_now(now)
    limit = get_settings().daily_generation_limit
    next_day = current.date() + timedelta(days=1)
    return UsageStatus(
        limit=limit,
        used=used,
        remaining=max(limit - used, 0),
        usage_date=current.date(),
        reset_at=datetime.combine(next_day, time.min, tzinfo=BANGKOK_TIMEZONE),
        is_unlimited=is_unlimited,
    )


def get_usage_status(db: Session, user: User, now: datetime | None = None) -> UsageStatus:
    if user.role == UserRole.ADMIN:
        return _status(0, now, is_unlimited=True)
    current = _bangkok_now(now)
    row = db.scalar(
        select(DailyUsage).where(
            DailyUsage.user_id == user.id,
            DailyUsage.usage_date == current.date(),
        )
    )
    return _status(row.used_count if row else 0, current)


def reserve_usage(db: Session, user: User, amount: int, now: datetime | None = None) -> UsageStatus:
    if amount <= 0:
        raise ValueError("amount must be positive")
    if user.role == UserRole.ADMIN:
        return _status(0, now, is_unlimited=True)

    current = _bangkok_now(now)
    db.execute(
        insert(DailyUsage)
        .values(user_id=user.id, usage_date=current.date(), used_count=0)
        .on_conflict_do_nothing(index_elements=[DailyUsage.user_id, DailyUsage.usage_date])
    )
    row = db.scalar(
        select(DailyUsage)
        .where(DailyUsage.user_id == user.id, DailyUsage.usage_date == current.date())
        .with_for_update()
    )
    if row is None:
        raise RuntimeError("Không thể khởi tạo bộ đếm sử dụng")
    current_status = _status(row.used_count, current)
    if row.used_count + amount > current_status.limit:
        raise UsageLimitExceeded(current_status)
    row.used_count += amount
    db.flush()
    return _status(row.used_count, current)
