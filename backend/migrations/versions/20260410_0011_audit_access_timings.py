"""add timing fields to audit access logs

Revision ID: 20260410_0011
Revises: 20260408_0010
Create Date: 2026-04-10 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_0011"
down_revision = "20260408_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_access_logs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("audit_access_logs", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("audit_access_logs", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.create_index("ix_audit_access_logs_started_at", "audit_access_logs", ["started_at"], unique=False)
    op.create_index("ix_audit_access_logs_duration_ms", "audit_access_logs", ["duration_ms"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_access_logs_duration_ms", table_name="audit_access_logs")
    op.drop_index("ix_audit_access_logs_started_at", table_name="audit_access_logs")
    op.drop_column("audit_access_logs", "duration_ms")
    op.drop_column("audit_access_logs", "finished_at")
    op.drop_column("audit_access_logs", "started_at")
