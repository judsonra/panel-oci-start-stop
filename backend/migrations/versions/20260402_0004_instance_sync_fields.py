"""add synced OCI instance fields

Revision ID: 20260402_0004
Revises: 20260330_0003
Create Date: 2026-04-02 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260402_0004"
down_revision = "20260330_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("instances", sa.Column("vcpu", sa.Float(), nullable=True))
    op.add_column("instances", sa.Column("memory_gbs", sa.Float(), nullable=True))
    op.add_column("instances", sa.Column("vnic_id", sa.String(length=255), nullable=True))
    op.add_column("instances", sa.Column("public_ip", sa.String(length=64), nullable=True))
    op.add_column("instances", sa.Column("private_ip", sa.String(length=64), nullable=True))
    op.add_column("instances", sa.Column("oci_created_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("instances", "oci_created_at")
    op.drop_column("instances", "private_ip")
    op.drop_column("instances", "public_ip")
    op.drop_column("instances", "vnic_id")
    op.drop_column("instances", "memory_gbs")
    op.drop_column("instances", "vcpu")
