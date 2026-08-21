"""Add tenant isolation keys and PostgreSQL row-level-security policies.

Revision ID: 20260821_06
Revises: 20260821_05
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_06"
down_revision = "20260821_05"
branch_labels = None
depends_on = None


TENANT_TABLES = (
    "data_sources",
    "ingestion_jobs",
    "source_sync_states",
    "assets",
    "asset_columns",
    "asset_metadata_versions",
    "audit_events",
    "idempotency_records",
    "governance_domains",
    "business_glossary_terms",
    "glossary_asset_mappings",
    "classification_findings",
    "certification_requests",
    "discovery_events",
    "governance_suggestions",
)
LEGACY_TENANT_ID = "default"


def upgrade() -> None:
    bind = op.get_bind()
    for table_name in TENANT_TABLES:
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("tenant_id", sa.String(length=255), nullable=True))
        op.execute(sa.text(f"UPDATE {table_name} SET tenant_id = :tenant_id WHERE tenant_id IS NULL").bindparams(tenant_id=LEGACY_TENANT_ID))
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.alter_column("tenant_id", existing_type=sa.String(length=255), nullable=False)
            batch_op.create_index(f"ix_{table_name}_tenant_id", ["tenant_id"])

    if bind.dialect.name == "postgresql":
        for table_name in TENANT_TABLES:
            policy_name = f"tenant_isolation_{table_name}"
            op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
            op.execute(
                f"CREATE POLICY {policy_name} ON {table_name} "
                "USING (tenant_id = current_setting('app.tenant_id', true)) "
                "WITH CHECK (tenant_id = current_setting('app.tenant_id', true))"
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table_name in TENANT_TABLES:
            policy_name = f"tenant_isolation_{table_name}"
            op.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name}")
            op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")

    for table_name in reversed(TENANT_TABLES):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_tenant_id")
            batch_op.drop_column("tenant_id")
