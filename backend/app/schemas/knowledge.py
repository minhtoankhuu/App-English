import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.knowledge import DocumentChunkType


class KnowledgeDocumentRefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unit_id: uuid.UUID
    file_name: str


class KnowledgeChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_type: DocumentChunkType
    section_title: str
    raw_text: str
    structured: dict | None
    document: KnowledgeDocumentRefOut


class KnowledgeUnitRefOut(BaseModel):
    id: uuid.UUID
    order_no: int
    title: str
    grade_number: int


class KnowledgeDocumentAdminOut(BaseModel):
    id: uuid.UUID
    file_name: str
    is_published: bool
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    unit: KnowledgeUnitRefOut


class KnowledgeDocumentUpdateRequest(BaseModel):
    is_published: bool


class KnowledgeChunkAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_no: int
    chunk_type: DocumentChunkType
    section_title: str
    raw_text: str
    structured: dict | None
