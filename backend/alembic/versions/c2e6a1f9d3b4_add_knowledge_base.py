"""add knowledge base

Revision ID: c2e6a1f9d3b4
Revises: d4f61c2a9b07
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2e6a1f9d3b4"
down_revision: str | None = "d4f61c2a9b07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

knowledge_chunk_type = postgresql.ENUM(
    "vocabulary", "word_form", "phrase", "grammar", "other", name="knowledge_chunk_type"
)


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("unit_id", "file_name", name="uq_knowledge_document_unit_file"),
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("chunk_type", knowledge_chunk_type, nullable=False),
        sa.Column("section_title", sa.String(length=255), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("structured", postgresql.JSONB(), nullable=True),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('simple', raw_text)", persisted=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"], unique=False)
    op.create_index(
        "ix_knowledge_chunks_search_vector", "knowledge_chunks", ["search_vector"], unique=False, postgresql_using="gin"
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_search_vector", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    knowledge_chunk_type.drop(op.get_bind())
    op.drop_table("knowledge_documents")
