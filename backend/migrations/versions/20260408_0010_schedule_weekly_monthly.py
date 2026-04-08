"""rename recurring schedule type to weekly and add monthly support

Revision ID: 20260408_0010
Revises: 20260406_0009
Create Date: 2026-04-08 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_0010"
down_revision = "20260406_0009"
branch_labels = None
depends_on = None


OLD_TYPE_NAME = "scheduletype_old"
NEW_TYPE_NAME = "scheduletype"


def upgrade() -> None:
    op.add_column("schedules", sa.Column("days_of_month", sa.JSON(), nullable=True))

    op.execute(f"ALTER TYPE {NEW_TYPE_NAME} RENAME TO {OLD_TYPE_NAME}")
    op.execute("CREATE TYPE scheduletype AS ENUM ('one_time', 'weekly', 'monthly')")
    op.execute("ALTER TABLE schedules ALTER COLUMN type TYPE text USING type::text")
    op.execute("UPDATE schedules SET type = 'weekly' WHERE type = 'recurring'")
    op.execute("ALTER TABLE schedules ALTER COLUMN type TYPE scheduletype USING type::scheduletype")
    op.execute(f"DROP TYPE {OLD_TYPE_NAME}")


def downgrade() -> None:
    op.execute(f"ALTER TYPE {NEW_TYPE_NAME} RENAME TO {OLD_TYPE_NAME}")
    op.execute("CREATE TYPE scheduletype AS ENUM ('one_time', 'recurring')")
    op.execute("ALTER TABLE schedules ALTER COLUMN type TYPE text USING type::text")
    op.execute("UPDATE schedules SET type = 'recurring' WHERE type = 'weekly'")
    op.execute("DELETE FROM schedules WHERE type = 'monthly'")
    op.execute("ALTER TABLE schedules ALTER COLUMN type TYPE scheduletype USING type::scheduletype")
    op.execute(f"DROP TYPE {OLD_TYPE_NAME}")

    op.drop_column("schedules", "days_of_month")
