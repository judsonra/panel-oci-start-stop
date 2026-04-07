"""add access control and audit tables

Revision ID: 20260406_0008
Revises: 20260406_0007
Create Date: 2026-04-06 01:00:00
"""

from alembic import op
import sqlalchemy as sa

from app.services.access_catalog import ACCESS_PERMISSION_CATALOG


revision = "20260406_0008"
down_revision = "20260406_0007"
branch_labels = None
depends_on = None


access_permissions_table = sa.table(
    "access_permissions",
    sa.column("id", sa.String()),
    sa.column("key", sa.String()),
    sa.column("label", sa.String()),
    sa.column("description", sa.String()),
)


def upgrade() -> None:
    op.create_table(
        "access_permissions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_permissions_key", "access_permissions", ["key"], unique=True)

    op.create_table(
        "access_groups",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_groups_name", "access_groups", ["name"], unique=True)

    op.create_table(
        "access_users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superadmin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_users_email", "access_users", ["email"], unique=True)

    op.create_table(
        "access_user_permissions",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("permission_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["access_permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["access_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "permission_id"),
    )
    op.create_table(
        "access_group_permissions",
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("permission_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["access_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["access_permissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "permission_id"),
    )
    op.create_table(
        "access_group_members",
        sa.Column("group_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["access_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["access_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("group_id", "user_id"),
    )

    op.create_table(
        "audit_access_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("auth_source", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("method", sa.String(length=12), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["access_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_access_logs_created_at", "audit_access_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_access_logs_email", "audit_access_logs", ["email"], unique=False)
    op.create_index("ix_audit_access_logs_event_type", "audit_access_logs", ["event_type"], unique=False)
    op.create_index("ix_audit_access_logs_path", "audit_access_logs", ["path"], unique=False)
    op.create_index("ix_audit_access_logs_user_id", "audit_access_logs", ["user_id"], unique=False)

    op.create_table(
        "audit_configuration_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("actor_user_id", sa.String(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("before_data", sa.JSON(), nullable=True),
        sa.Column("after_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["access_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_configuration_logs_actor_email", "audit_configuration_logs", ["actor_email"], unique=False)
    op.create_index("ix_audit_configuration_logs_actor_user_id", "audit_configuration_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_configuration_logs_created_at", "audit_configuration_logs", ["created_at"], unique=False)
    op.create_index("ix_audit_configuration_logs_entity_id", "audit_configuration_logs", ["entity_id"], unique=False)
    op.create_index("ix_audit_configuration_logs_entity_type", "audit_configuration_logs", ["entity_type"], unique=False)
    op.create_index("ix_audit_configuration_logs_event_type", "audit_configuration_logs", ["event_type"], unique=False)

    op.bulk_insert(
        access_permissions_table,
        [
            {"id": f"perm-{index:03d}", "key": key, "label": label, "description": description}
            for index, (key, label, description) in enumerate(ACCESS_PERMISSION_CATALOG, start=1)
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_configuration_logs_event_type", table_name="audit_configuration_logs")
    op.drop_index("ix_audit_configuration_logs_entity_type", table_name="audit_configuration_logs")
    op.drop_index("ix_audit_configuration_logs_entity_id", table_name="audit_configuration_logs")
    op.drop_index("ix_audit_configuration_logs_created_at", table_name="audit_configuration_logs")
    op.drop_index("ix_audit_configuration_logs_actor_user_id", table_name="audit_configuration_logs")
    op.drop_index("ix_audit_configuration_logs_actor_email", table_name="audit_configuration_logs")
    op.drop_table("audit_configuration_logs")
    op.drop_index("ix_audit_access_logs_user_id", table_name="audit_access_logs")
    op.drop_index("ix_audit_access_logs_path", table_name="audit_access_logs")
    op.drop_index("ix_audit_access_logs_event_type", table_name="audit_access_logs")
    op.drop_index("ix_audit_access_logs_email", table_name="audit_access_logs")
    op.drop_index("ix_audit_access_logs_created_at", table_name="audit_access_logs")
    op.drop_table("audit_access_logs")
    op.drop_table("access_group_members")
    op.drop_table("access_group_permissions")
    op.drop_table("access_user_permissions")
    op.drop_index("ix_access_users_email", table_name="access_users")
    op.drop_table("access_users")
    op.drop_index("ix_access_groups_name", table_name="access_groups")
    op.drop_table("access_groups")
    op.drop_index("ix_access_permissions_key", table_name="access_permissions")
    op.drop_table("access_permissions")
