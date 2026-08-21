"""Add lineage and metadata-gap governance suggestion types.

Revision ID: 20260821_05
Revises: 20260821_04
Create Date: 2026-08-21
"""

from alembic import op


revision = "20260821_05"
down_revision = "20260821_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Extend the PostgreSQL enum; SQLite stores these values as strings."""
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE suggestiontype ADD VALUE IF NOT EXISTS 'LINEAGE_SUMMARY'")
        op.execute("ALTER TYPE suggestiontype ADD VALUE IF NOT EXISTS 'METADATA_GAP'")


def downgrade() -> None:
    """PostgreSQL enum values are intentionally retained to avoid unsafe rewrites."""
