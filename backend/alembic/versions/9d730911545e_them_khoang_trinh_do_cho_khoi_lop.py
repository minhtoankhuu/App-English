"""them khoang trinh do cho khoi lop

Revision ID: 9d730911545e
Revises: c8f2d05e3a71

PRD 7.4 viết mức của THCS 8-9 là một DẢI "A2-B1", nhưng bảng grades chỉ lưu được
đúng một mức (suggested_level_id). Thêm min/max để giáo viên hạ mức cho lớp yếu
ngay trong khoảng của khối lớp, thay vì dropdown mở toang A1-C1 cho mọi lớp.
Nullable: khối lớp chưa cấu hình thì không giới hạn, giữ nguyên hành vi cũ.
"""

import sqlalchemy as sa
from alembic import op

revision = "9d730911545e"
down_revision = "c8f2d05e3a71"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("grades", sa.Column("min_level_id", sa.UUID(as_uuid=True), nullable=True))
    op.add_column("grades", sa.Column("max_level_id", sa.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_grades_min_level_id", "grades", "proficiency_levels", ["min_level_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_grades_max_level_id", "grades", "proficiency_levels", ["max_level_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_grades_max_level_id", "grades", type_="foreignkey")
    op.drop_constraint("fk_grades_min_level_id", "grades", type_="foreignkey")
    op.drop_column("grades", "max_level_id")
    op.drop_column("grades", "min_level_id")
