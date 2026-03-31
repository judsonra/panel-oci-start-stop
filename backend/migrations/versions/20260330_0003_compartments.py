"""add compartments table

Revision ID: 20260330_0003
Revises: 20260312_0002
Create Date: 2026-03-30 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260330_0003"
down_revision = "20260312_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compartments",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("ocid", sa.String(length=255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_compartments_ocid"), "compartments", ["ocid"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_compartments_ocid"), table_name="compartments")
    op.drop_table("compartments")
