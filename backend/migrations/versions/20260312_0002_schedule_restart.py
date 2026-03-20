"""add restart to schedule action enum

Revision ID: 20260312_0002
Revises: 20260310_0001
Create Date: 2026-03-12 12:40:00
"""

from alembic import op


revision = "20260312_0002"
down_revision = "20260310_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE scheduleaction ADD VALUE IF NOT EXISTS 'restart'")


def downgrade() -> None:
    # PostgreSQL enums do not support dropping a single value safely in-place.
    pass
