"""phan con duoc phep khac dang bai voi khoi cha

Revision ID: c8f2d05e3a71
Revises: b7e1c94d2f30
Create Date: 2026-08-26

Đề thật gộp trọng âm thành một phần con của "I. PRONUNCIATION" (13/13 đề). Phát âm và
trọng âm là hai dạng bài khác nhau — khác bộ dựng, khác bộ kiểm, khác câu mẫu — nên
phần con phải ghi đè được dạng bài. NULL = dùng dạng bài của khối cha (mọi phần con
đang có đều như vậy, nên thay đổi này tương thích ngược).
"""

import sqlalchemy as sa
from alembic import op

revision = "c8f2d05e3a71"
down_revision = "b7e1c94d2f30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exam_block_parts",
        sa.Column("exercise_type_id", sa.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_exam_block_parts_exercise_type",
        "exam_block_parts",
        "exercise_types",
        ["exercise_type_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_exam_block_parts_exercise_type", "exam_block_parts", type_="foreignkey")
    op.drop_column("exam_block_parts", "exercise_type_id")
