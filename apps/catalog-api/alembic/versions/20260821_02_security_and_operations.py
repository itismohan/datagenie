"""Add security and operational persistence.

Revision ID: 20260821_02
Revises: 20260821_01
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_02"
down_revision = "20260821_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "business_glossary_terms",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_business_glossary_terms_name", "business_glossary_terms", ["name"])
    op.create_index("ix_business_glossary_terms_owner", "business_glossary_terms", ["owner"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("actor_subject", sa.String(length=255)),
        sa.Column("actor_roles", sa.JSON(), nullable=False),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255)),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_actor_subject", "audit_events", ["actor_subject"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_resource_type", "audit_events", ["resource_type"])
    op.create_index("ix_audit_events_resource_id", "audit_events", ["resource_id"])
    op.create_index("ix_audit_events_outcome", "audit_events", ["outcome"])
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("principal_subject", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "principal_subject", "idempotency_key", "method", "path", name="uq_idempotency_principal_key_route"
        ),
    )
    op.create_index("ix_idempotency_records_principal_subject", "idempotency_records", ["principal_subject"])
    op.create_index("ix_idempotency_records_expires_at", "idempotency_records", ["expires_at"])


def downgrade() -> None:
    op.drop_table("idempotency_records")
    op.drop_table("audit_events")
    op.drop_table("business_glossary_terms")
