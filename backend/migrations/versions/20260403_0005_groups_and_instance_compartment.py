"""add groups and instance compartment relation

Revision ID: 20260403_0005
Revises: 20260402_0004
Create Date: 2026-04-03 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260403_0005"
down_revision = "20260402_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("instances", sa.Column("compartment_id", sa.String(), nullable=True))
    op.create_index(op.f("ix_instances_compartment_id"), "instances", ["compartment_id"], unique=False)
    op.create_foreign_key(
        "fk_instances_compartment_id_compartments",
        "instances",
        "compartments",
        ["compartment_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "groups",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_groups_normalized_name"), "groups", ["normalized_name"], unique=True)

    op.create_table(
        "group_instances",
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("instance_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "instance_id"),
    )


def downgrade() -> None:
    op.drop_table("group_instances")
    op.drop_index(op.f("ix_groups_normalized_name"), table_name="groups")
    op.drop_table("groups")
    op.drop_constraint("fk_instances_compartment_id_compartments", "instances", type_="foreignkey")
    op.drop_index(op.f("ix_instances_compartment_id"), table_name="instances")
    op.drop_column("instances", "compartment_id")
