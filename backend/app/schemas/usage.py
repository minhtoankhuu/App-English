from datetime import date, datetime

from pydantic import BaseModel


class UsageStatusOut(BaseModel):
    limit: int
    used: int
    remaining: int
    usage_date: date
    reset_at: datetime
    is_unlimited: bool
