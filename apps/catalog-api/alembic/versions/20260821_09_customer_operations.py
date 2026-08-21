"""Add retention, export support records, and webhook delivery outbox.

Revision ID: 20260821_09
Revises: 20260821_08
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_09"
down_revision = "20260821_08"
branch_labels = None
depends_on = None


def _enable_tenant_rls(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation_{table_name} ON {table_name} "
        "USING (tenant_id = current_setting('app.tenant_id', true)) "
        "WITH CHECK (tenant_id = current_setting('app.tenant_id', true))"
    )


def upgrade() -> None:
    retention_resource_type = sa.Enum("AUDIT_EVENT", "DISCOVERY_EVENT", "INGESTION_JOB", name="retentionresourcetype")
    webhook_event_type = sa.Enum("ASSET_UPDATED", "INGESTION_COMPLETED", "QUALITY_INCIDENT", name="webhookeventtype")
    webhook_delivery_status = sa.Enum("PENDING", "DELIVERED", "FAILED", "DEAD_LETTER", name="webhookdeliverystatus")

    op.create_table(
        "retention_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("resource_type", retention_resource_type, nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "resource_type", name="uq_retention_policies_tenant_resource"),
    )
    op.create_index("ix_retention_policies_tenant_id", "retention_policies", ["tenant_id"])

    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", webhook_event_type, nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("secret_ref", sa.String(length=1024), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_subscriptions_tenant_id", "webhook_subscriptions", ["tenant_id"])
    op.create_index("ix_webhook_subscriptions_event_type", "webhook_subscriptions", ["event_type"])

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("subscription_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", webhook_event_type, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", webhook_delivery_status, nullable=False, server_default="PENDING"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["webhook_subscriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_deliveries_tenant_id", "webhook_deliveries", ["tenant_id"])
    op.create_index("ix_webhook_deliveries_subscription_id", "webhook_deliveries", ["subscription_id"])
    op.create_index("ix_webhook_deliveries_event_type", "webhook_deliveries", ["event_type"])
    op.create_index("ix_webhook_deliveries_status", "webhook_deliveries", ["status"])

    if op.get_bind().dialect.name == "postgresql":
        for table_name in ("retention_policies", "webhook_subscriptions", "webhook_deliveries"):
            _enable_tenant_rls(table_name)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table_name in ("webhook_deliveries", "webhook_subscriptions", "retention_policies"):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table_name} ON {table_name}")
            op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")

    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_subscriptions")
    op.drop_table("retention_policies")
    if op.get_bind().dialect.name == "postgresql":
        sa.Enum(name="webhookdeliverystatus").drop(op.get_bind(), checkfirst=True)
        sa.Enum(name="webhookeventtype").drop(op.get_bind(), checkfirst=True)
        sa.Enum(name="retentionresourcetype").drop(op.get_bind(), checkfirst=True)
