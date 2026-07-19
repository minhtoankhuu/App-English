import uuid

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
