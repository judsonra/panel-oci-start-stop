"""add schedule target type and group support

Revision ID: 20260405_0006
Revises: 20260403_0005
Create Date: 2026-04-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260405_0006"
down_revision = "20260403_0005"
branch_labels = None
depends_on = None


schedule_target_type = sa.Enum("instance", "group", name="scheduletargettype")


def upgrade() -> None:
    schedule_target_type.create(op.get_bind(), checkfirst=True)
    with op.batch_alter_table("schedules") as batch_op:
        batch_op.add_column(sa.Column("target_type", schedule_target_type, nullable=False, server_default="instance"))
        batch_op.add_column(sa.Column("group_id", sa.String(), nullable=True))
        batch_op.create_index(batch_op.f("ix_schedules_group_id"), ["group_id"], unique=False)
        batch_op.alter_column("instance_id", existing_type=sa.String(), nullable=True)
        batch_op.create_foreign_key("fk_schedules_group_id_groups", "groups", ["group_id"], ["id"], ondelete="CASCADE")

    op.execute("UPDATE schedules SET target_type = 'instance' WHERE target_type IS NULL")

    with op.batch_alter_table("schedules") as batch_op:
        batch_op.alter_column("target_type", server_default=None)


def downgrade() -> None:
    with op.batch_alter_table("schedules") as batch_op:
        batch_op.drop_constraint("fk_schedules_group_id_groups", type_="foreignkey")
        batch_op.alter_column("instance_id", existing_type=sa.String(), nullable=False)
        batch_op.drop_index(batch_op.f("ix_schedules_group_id"))
        batch_op.drop_column("group_id")
        batch_op.drop_column("target_type")

    schedule_target_type.drop(op.get_bind(), checkfirst=True)
