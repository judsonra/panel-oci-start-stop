"""add instance proxy routing fields

Revision ID: 20260414_0012
Revises: 20260410_0011
Create Date: 2026-04-14 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260414_0012"
down_revision = "20260410_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("instances", sa.Column("app_url", sa.String(length=255), nullable=True))
    op.add_column("instances", sa.Column("environment", sa.String(length=10), nullable=True))
    op.add_column("instances", sa.Column("customer_name", sa.String(length=120), nullable=True))
    op.add_column("instances", sa.Column("domain", sa.String(length=120), nullable=True))
    op.add_column("instances", sa.Column("name_prefix", sa.String(length=30), nullable=True))

    op.create_index(op.f("ix_instances_app_url"), "instances", ["app_url"], unique=True)
    op.create_index(op.f("ix_instances_environment"), "instances", ["environment"], unique=False)
    op.create_index(op.f("ix_instances_customer_name"), "instances", ["customer_name"], unique=False)
    op.create_index(op.f("ix_instances_domain"), "instances", ["domain"], unique=False)
    op.create_index(op.f("ix_instances_name_prefix"), "instances", ["name_prefix"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_instances_name_prefix"), table_name="instances")
    op.drop_index(op.f("ix_instances_domain"), table_name="instances")
    op.drop_index(op.f("ix_instances_customer_name"), table_name="instances")
    op.drop_index(op.f("ix_instances_environment"), table_name="instances")
    op.drop_index(op.f("ix_instances_app_url"), table_name="instances")

    op.drop_column("instances", "name_prefix")
    op.drop_column("instances", "domain")
    op.drop_column("instances", "customer_name")
    op.drop_column("instances", "environment")
    op.drop_column("instances", "app_url")
