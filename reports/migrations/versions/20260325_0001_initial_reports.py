"""initial reports cache tables

Revision ID: 20260325_0001
Revises:
Create Date: 2026-03-25 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260325_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_periods",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("sync_status", sa.String(length=32), nullable=False),
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year", "month", name="uq_report_period_year_month"),
    )
    op.create_table(
        "report_cost_entries",
        sa.Column("period_id", sa.String(), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("compartment_id", sa.String(length=255), nullable=True),
        sa.Column("compartment_name", sa.String(length=255), nullable=True),
        sa.Column("service", sa.String(length=255), nullable=True),
        sa.Column("sku_name", sa.String(length=255), nullable=True),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("resource_name", sa.String(length=255), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("amount", sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["period_id"], ["report_periods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_report_cost_entries_compartment_id"), "report_cost_entries", ["compartment_id"], unique=False)
    op.create_index(op.f("ix_report_cost_entries_period_id"), "report_cost_entries", ["period_id"], unique=False)
    op.create_index(op.f("ix_report_cost_entries_usage_date"), "report_cost_entries", ["usage_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_cost_entries_usage_date"), table_name="report_cost_entries")
    op.drop_index(op.f("ix_report_cost_entries_period_id"), table_name="report_cost_entries")
    op.drop_index(op.f("ix_report_cost_entries_compartment_id"), table_name="report_cost_entries")
    op.drop_table("report_cost_entries")
    op.drop_table("report_periods")
