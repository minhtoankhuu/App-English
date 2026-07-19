import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TeacherCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class TeacherUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=255)


class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
