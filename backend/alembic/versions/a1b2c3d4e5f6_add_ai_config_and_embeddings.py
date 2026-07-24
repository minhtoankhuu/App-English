"""add ai config, generation logs, and embedding columns

Revision ID: a1b2c3d4e5f6
Revises: fb9639cd5a3a
Create Date: 2026-07-21 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'fb9639cd5a3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1536  # OpenAI text-embedding-3-small


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Cột embedding trên knowledge_chunks + questions — viết tay, không autogenerate
    # (gotcha đã biết: SQLAlchemy không phản chiếu đúng ondelete=CASCADE hiện có trên
    # knowledge_chunks, autogenerate sẽ đề xuất xóa/tạo lại FK/index không liên quan,
    # xem c2e6a1f9d3b4_add_knowledge_base.py).
    op.add_column("knowledge_chunks", sa.Column("embedding", pgvector.sqlalchemy.Vector(EMBEDDING_DIM), nullable=True))
    op.add_column("knowledge_chunks", sa.Column("embedding_model", sa.String(length=64), nullable=True))
    op.add_column("knowledge_chunks", sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding ON knowledge_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.add_column("questions", sa.Column("embedding", pgvector.sqlalchemy.Vector(EMBEDDING_DIM), nullable=True))

    # Bảng mới hoàn toàn — an toàn để autogenerate-style, viết tay cho rõ ràng.
    op.create_table(
        "ai_provider_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=64), nullable=False),
        sa.Column("api_key_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("duplicate_similarity_threshold", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "generation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("exam_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("block_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False),
        sa.Column("question_count_requested", sa.Integer(), nullable=False),
        sa.Column("source_chunk_ids", postgresql.JSONB(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 6), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["block_id"], ["exam_blocks.id"], ondelete="SET NULL"),
    )


def downgrade() -> None:
    op.drop_table("generation_logs")
    op.drop_table("ai_provider_configs")
    op.drop_column("questions", "embedding")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding")
    op.drop_column("knowledge_chunks", "embedded_at")
    op.drop_column("knowledge_chunks", "embedding_model")
    op.drop_column("knowledge_chunks", "embedding")
    # Không drop extension "vector" — an toàn nếu có object khác phụ thuộc.
