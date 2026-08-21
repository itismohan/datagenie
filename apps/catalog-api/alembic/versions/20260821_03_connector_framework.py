"""Add Snowflake and incremental connector framework state.

Revision ID: 20260821_03
Revises: 20260821_02
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_03"
down_revision = "20260821_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS 'SNOWFLAKE'")

    sync_mode = sa.Enum("INCREMENTAL", "FULL", name="syncmode")
    sync_mode.create(bind, checkfirst=True)

    with op.batch_alter_table("data_sources") as batch_op:
        batch_op.add_column(
            sa.Column("connection_options", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
        )

    with op.batch_alter_table("ingestion_jobs") as batch_op:
        batch_op.add_column(
            sa.Column("requested_sync_mode", sync_mode, nullable=False, server_default="INCREMENTAL")
        )
        batch_op.add_column(sa.Column("effective_sync_mode", sync_mode, nullable=True))
        batch_op.add_column(sa.Column("cursor_before", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("cursor_after", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column("connector_strategy", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    op.create_table(
        "source_sync_states",
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("data_sources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("cursor", sa.JSON(), nullable=False),
        sa.Column("last_successful_job_id", sa.String(length=36)),
        sa.Column("last_successful_at", sa.DateTime(timezone=True)),
        sa.Column("last_full_sync_at", sa.DateTime(timezone=True)),
        sa.Column("last_incremental_sync_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("source_sync_states")
    with op.batch_alter_table("ingestion_jobs") as batch_op:
        batch_op.drop_column("warnings")
        batch_op.drop_column("connector_strategy")
        batch_op.drop_column("cursor_after")
        batch_op.drop_column("cursor_before")
        batch_op.drop_column("effective_sync_mode")
        batch_op.drop_column("requested_sync_mode")
    with op.batch_alter_table("data_sources") as batch_op:
        batch_op.drop_column("connection_options")
