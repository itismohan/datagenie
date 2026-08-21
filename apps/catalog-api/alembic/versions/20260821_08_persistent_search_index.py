"""Add a durable tenant-scoped catalog search index.

Revision ID: 20260821_08
Revises: 20260821_07
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_08"
down_revision = "20260821_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "search_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("document", sa.Text(), nullable=False),
        sa.Column("facets", sa.JSON(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "asset_id", name="uq_search_documents_tenant_asset"),
    )
    op.create_index("ix_search_documents_tenant_id", "search_documents", ["tenant_id"])
    op.create_index("ix_search_documents_asset_id", "search_documents", ["asset_id"])
    op.create_index("ix_search_documents_indexed_at", "search_documents", ["indexed_at"])

    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TABLE search_documents ENABLE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE search_documents FORCE ROW LEVEL SECURITY")
        op.execute(
            "CREATE POLICY tenant_isolation_search_documents ON search_documents "
            "USING (tenant_id = current_setting('app.tenant_id', true)) "
            "WITH CHECK (tenant_id = current_setting('app.tenant_id', true))"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS tenant_isolation_search_documents ON search_documents")
        op.execute("ALTER TABLE search_documents NO FORCE ROW LEVEL SECURITY")
        op.execute("ALTER TABLE search_documents DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_search_documents_indexed_at", table_name="search_documents")
    op.drop_index("ix_search_documents_asset_id", table_name="search_documents")
    op.drop_index("ix_search_documents_tenant_id", table_name="search_documents")
    op.drop_table("search_documents")
