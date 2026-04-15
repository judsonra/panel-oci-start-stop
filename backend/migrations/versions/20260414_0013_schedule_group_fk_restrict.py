"""change schedules group foreign key to restrict

Revision ID: 20260414_0013
Revises: 20260414_0012
Create Date: 2026-04-14 00:00:01
"""

from alembic import op


revision = "20260414_0013"
down_revision = "20260414_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("schedules") as batch_op:
        batch_op.drop_constraint("fk_schedules_group_id_groups", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_schedules_group_id_groups",
            "groups",
            ["group_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    with op.batch_alter_table("schedules") as batch_op:
        batch_op.drop_constraint("fk_schedules_group_id_groups", type_="foreignkey")
        batch_op.create_foreign_key(
            "fk_schedules_group_id_groups",
            "groups",
            ["group_id"],
            ["id"],
            ondelete="CASCADE",
        )
