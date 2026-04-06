"""add deskmanager catalogs

Revision ID: 20260406_0007
Revises: 20260405_0006
Create Date: 2026-04-06 00:00:00
"""

from alembic import op
import sqlalchemy as sa

from app.services.deskmanager_catalog import DESKMANAGER_CATEGORIES, DESKMANAGER_USERS


revision = "20260406_0007"
down_revision = "20260405_0006"
branch_labels = None
depends_on = None


deskmanager_users_table = sa.table(
    "deskmanager_users",
    sa.column("id", sa.String()),
    sa.column("name", sa.String()),
)

deskmanager_categories_table = sa.table(
    "deskmanager_categories",
    sa.column("id", sa.String()),
    sa.column("name", sa.String()),
)


def upgrade() -> None:
    op.create_table(
        "deskmanager_users",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_deskmanager_users"),
    )
    op.create_index("ix_deskmanager_users_name", "deskmanager_users", ["name"], unique=True)

    op.create_table(
        "deskmanager_categories",
        sa.Column("id", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_deskmanager_categories"),
    )
    op.create_index("ix_deskmanager_categories_name", "deskmanager_categories", ["name"], unique=True)

    op.bulk_insert(deskmanager_users_table, [{"id": item_id, "name": name} for item_id, name in DESKMANAGER_USERS])
    op.bulk_insert(deskmanager_categories_table, [{"id": item_id, "name": name} for item_id, name in DESKMANAGER_CATEGORIES])


def downgrade() -> None:
    op.drop_index("ix_deskmanager_categories_name", table_name="deskmanager_categories")
    op.drop_table("deskmanager_categories")
    op.drop_index("ix_deskmanager_users_name", table_name="deskmanager_users")
    op.drop_table("deskmanager_users")
