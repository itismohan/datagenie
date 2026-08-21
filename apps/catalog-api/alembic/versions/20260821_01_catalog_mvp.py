"""Create the Catalog MVP schema.

Revision ID: 20260821_01
Revises:
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    source_type = sa.Enum("POSTGRESQL", name="sourcetype")
    source_status = sa.Enum("ACTIVE", "PAUSED", "ERROR", name="sourcestatus")
    job_status = sa.Enum("QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", name="jobstatus")
    asset_type = sa.Enum("DATABASE", "SCHEMA", "TABLE", "VIEW", name="assettype")
    lifecycle_status = sa.Enum("UNDER_REVIEW", "CERTIFIED", "DEPRECATED", name="lifecyclestatus")
    change_source = sa.Enum("DISCOVERY", "CURATION", name="changesource")

    op.create_table(
        "data_sources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("database_name", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("secret_ref", sa.String(length=1024), nullable=False),
        sa.Column("include_schemas", sa.JSON(), nullable=False),
        sa.Column("status", source_status, nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_data_sources_name", "data_sources", ["name"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("retry_of_job_id", sa.String(length=36)),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False),
        sa.Column("discovery_stats", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ingestion_jobs_source_id", "ingestion_jobs", ["source_id"])
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])

    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", asset_type, nullable=False),
        sa.Column("qualified_name", sa.String(length=1024), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("database_name", sa.String(length=255)),
        sa.Column("schema_name", sa.String(length=255)),
        sa.Column("technical_description", sa.Text()),
        sa.Column("technical_metadata", sa.JSON(), nullable=False),
        sa.Column("row_count", sa.Integer()),
        sa.Column("last_discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("freshness_at", sa.DateTime(timezone=True)),
        sa.Column("technical_version", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("owner", sa.String(length=255)),
        sa.Column("classification", sa.String(length=100)),
        sa.Column("lifecycle_status", lifecycle_status, nullable=False),
        sa.Column("curated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "asset_type", "qualified_name", name="uq_assets_source_type_qualified_name"),
    )
    op.create_index("ix_assets_source_id", "assets", ["source_id"])
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])
    op.create_index("ix_assets_qualified_name", "assets", ["qualified_name"])
    op.create_index("ix_assets_name", "assets", ["name"])
    op.create_index("ix_assets_owner", "assets", ["owner"])
    op.create_index("ix_assets_classification", "assets", ["classification"])
    op.create_index("ix_assets_lifecycle_status", "assets", ["lifecycle_status"])

    op.create_table(
        "asset_columns",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("ordinal_position", sa.Integer(), nullable=False),
        sa.Column("data_type", sa.String(length=255), nullable=False),
        sa.Column("is_nullable", sa.Boolean(), nullable=False),
        sa.Column("default_value", sa.Text()),
        sa.Column("technical_description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("asset_id", "name", name="uq_asset_columns_asset_name"),
    )
    op.create_index("ix_asset_columns_asset_id", "asset_columns", ["asset_id"])

    op.create_table(
        "asset_metadata_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("change_source", change_source, nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_asset_metadata_versions_asset_id", "asset_metadata_versions", ["asset_id"])


def downgrade() -> None:
    op.drop_table("asset_metadata_versions")
    op.drop_table("asset_columns")
    op.drop_table("assets")
    op.drop_table("ingestion_jobs")
    op.drop_table("data_sources")
