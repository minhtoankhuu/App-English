"""them gia tri EXAM_ITEM vao enum knowledge_chunk_type

Revision ID: b7e1c94d2f30
Revises: a1b2c3d4e5f6
Create Date: 2026-08-26

Đề thi thật nạp từ Knowledge_Base/Exams/ được lưu thành chunk EXAM_ITEM — câu mẫu về
văn phong cho model, tách khỏi các loại chunk kiến thức (VOCABULARY/GRAMMAR/...).
"""

from alembic import op

revision = "b7e1c94d2f30"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE không chạy được trong transaction ở PostgreSQL < 12;
    # bản dùng ở đây là pg16 nên chạy thẳng được. IF NOT EXISTS cho phép chạy lại.
    op.execute("ALTER TYPE knowledge_chunk_type ADD VALUE IF NOT EXISTS 'EXAM_ITEM'")


def downgrade() -> None:
    # PostgreSQL không hỗ trợ xoá một giá trị khỏi enum. Gỡ bỏ phải dựng lại cả kiểu và
    # mọi cột dùng nó — không đáng cho một giá trị chỉ thêm vào, nên để no-op.
    pass
