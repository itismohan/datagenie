"""Add durable connector task execution and recovery state.

Revision ID: 20260821_07
Revises: 20260821_06
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_07"
down_revision = "20260821_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'DEAD_LETTER'")

    with op.batch_alter_table("ingestion_jobs") as batch_op:
        batch_op.add_column(sa.Column("task_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index("ix_ingestion_jobs_task_id", ["task_id"])
        batch_op.create_index("ix_ingestion_jobs_next_retry_at", ["next_retry_at"])
        batch_op.create_index("ix_ingestion_jobs_lease_expires_at", ["lease_expires_at"])


def downgrade() -> None:
    with op.batch_alter_table("ingestion_jobs") as batch_op:
        batch_op.drop_index("ix_ingestion_jobs_lease_expires_at")
        batch_op.drop_index("ix_ingestion_jobs_next_retry_at")
        batch_op.drop_index("ix_ingestion_jobs_task_id")
        batch_op.drop_column("lease_expires_at")
        batch_op.drop_column("next_retry_at")
        batch_op.drop_column("dead_lettered_at")
        batch_op.drop_column("task_id")
