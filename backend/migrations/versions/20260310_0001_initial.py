"""initial schema

Revision ID: 20260310_0001
Revises:
Create Date: 2026-03-10 00:00:01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260310_0001"
down_revision = None
branch_labels = None
depends_on = None


execution_source = postgresql.ENUM("manual", "schedule", name="executionsource", create_type=False)
execution_status = postgresql.ENUM("pending", "success", "failed", name="executionstatus", create_type=False)
schedule_type = postgresql.ENUM("one_time", "recurring", name="scheduletype", create_type=False)
schedule_action = postgresql.ENUM("start", "stop", name="scheduleaction", create_type=False)


def upgrade() -> None:
    execution_source.create(op.get_bind(), checkfirst=True)
    execution_status.create(op.get_bind(), checkfirst=True)
    schedule_type.create(op.get_bind(), checkfirst=True)
    schedule_action.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "instances",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("ocid", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_known_state", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_instances_ocid"), "instances", ["ocid"], unique=True)

    op.create_table(
        "schedules",
        sa.Column("instance_id", sa.String(), nullable=False),
        sa.Column("type", schedule_type, nullable=False),
        sa.Column("action", schedule_action, nullable=False),
        sa.Column("run_at_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("days_of_week", sa.JSON(), nullable=True),
        sa.Column("time_utc", sa.String(length=5), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedules_instance_id"), "schedules", ["instance_id"], unique=False)

    op.create_table(
        "execution_logs",
        sa.Column("instance_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("source", execution_source, nullable=False),
        sa.Column("status", execution_status, nullable=False),
        sa.Column("stdout_summary", sa.Text(), nullable=True),
        sa.Column("stderr_summary", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_execution_logs_instance_id"), "execution_logs", ["instance_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_execution_logs_instance_id"), table_name="execution_logs")
    op.drop_table("execution_logs")
    op.drop_index(op.f("ix_schedules_instance_id"), table_name="schedules")
    op.drop_table("schedules")
    op.drop_index(op.f("ix_instances_ocid"), table_name="instances")
    op.drop_table("instances")
    schedule_action.drop(op.get_bind(), checkfirst=True)
    schedule_type.drop(op.get_bind(), checkfirst=True)
    execution_status.drop(op.get_bind(), checkfirst=True)
    execution_source.drop(op.get_bind(), checkfirst=True)
