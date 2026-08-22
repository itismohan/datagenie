"""Add governed discovery, classification, and certification records.

Revision ID: 20260821_04
Revises: 20260821_03
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260821_04"
down_revision = "20260821_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # These are shared named PostgreSQL types. Explicit manual creation is
    # required before the batch alteration, while create_type=False prevents
    # later create_table calls from attempting to create the same type again.
    glossary_status = postgresql.ENUM("PROPOSED", "APPROVED", "REJECTED", "DEPRECATED", name="glossarystatus", create_type=False)
    classification_type = postgresql.ENUM("EMAIL_ADDRESS", "PHONE_NUMBER", "GOVERNMENT_IDENTIFIER", "PAYMENT_DATA", "HEALTH_INFORMATION", name="classificationtype", create_type=False)
    review_status = postgresql.ENUM("PROPOSED", "APPROVED", "REJECTED", name="reviewstatus", create_type=False)
    discovery_event_type = postgresql.ENUM("SEARCH", "ASSET_VIEW", "CERTIFICATION_REQUEST", "USAGE_DECISION", name="discoveryeventtype", create_type=False)
    usage_decision_status = postgresql.ENUM("PENDING", "APPROVED", "REJECTED", name="usagedecisionstatus", create_type=False)
    suggestion_type = postgresql.ENUM("DESCRIPTION", "GLOSSARY_MAPPING", "OWNER", "QUALITY_RULE", name="suggestiontype", create_type=False)

    # `business_glossary_terms` already exists. PostgreSQL therefore will not
    # auto-create its enum while adding the status column in a batch operation.
    # Create every named enum explicitly before either altered or new tables use it.
    for enum_type in (
        glossary_status,
        classification_type,
        review_status,
        discovery_event_type,
        usage_decision_status,
        suggestion_type,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "governance_domains",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column("description", sa.Text()),
        sa.Column("business_owner", sa.String(length=255), index=True),
        sa.Column("data_steward", sa.String(length=255), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("assets") as batch_op:
        batch_op.add_column(sa.Column("domain_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("quality_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("quality_explainable_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key("fk_assets_domain_id", "governance_domains", ["domain_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_assets_domain_id", ["domain_id"])
        batch_op.create_index("ix_assets_quality_score", ["quality_score"])

    with op.batch_alter_table("business_glossary_terms") as batch_op:
        batch_op.add_column(sa.Column("domain_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("status", glossary_status, nullable=False, server_default="PROPOSED"))
        batch_op.add_column(sa.Column("proposed_by", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("reviewed_by", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("review_note", sa.Text(), nullable=True))
        batch_op.create_foreign_key("fk_glossary_domain_id", "governance_domains", ["domain_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_business_glossary_terms_domain_id", ["domain_id"])
        batch_op.create_index("ix_business_glossary_terms_status", ["status"])

    op.create_table(
        "glossary_asset_mappings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("term_id", sa.String(length=36), sa.ForeignKey("business_glossary_terms.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("column_name", sa.String(length=255), nullable=True),
        sa.Column("status", review_status, nullable=False, server_default="PROPOSED", index=True),
        sa.Column("proposed_by", sa.String(length=255), nullable=False),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("term_id", "asset_id", "column_name", name="uq_glossary_asset_column"),
    )
    op.create_table(
        "classification_findings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("column_name", sa.String(length=255), nullable=False),
        sa.Column("classification_type", classification_type, nullable=False, index=True),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", review_status, nullable=False, server_default="PROPOSED", index=True),
        sa.Column("detected_by", sa.String(length=255), nullable=False),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("asset_id", "column_name", "classification_type", name="uq_classification_asset_column_type"),
    )
    op.create_table(
        "certification_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("status", usage_decision_status, nullable=False, server_default="PENDING", index=True),
        sa.Column("decision_by", sa.String(length=255), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "discovery_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("actor_subject", sa.String(length=255), nullable=True, index=True),
        sa.Column("event_type", discovery_event_type, nullable=False, index=True),
        sa.Column("asset_id", sa.String(length=36), nullable=True, index=True),
        sa.Column("query_text", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "governance_suggestions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("asset_id", sa.String(length=36), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("suggestion_type", suggestion_type, nullable=False, index=True),
        sa.Column("proposed_value", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("generated_by", sa.String(length=255), nullable=False),
        sa.Column("status", review_status, nullable=False, server_default="PROPOSED", index=True),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table("governance_suggestions")
    op.drop_table("discovery_events")
    op.drop_table("certification_requests")
    op.drop_table("classification_findings")
    op.drop_table("glossary_asset_mappings")
    with op.batch_alter_table("business_glossary_terms") as batch_op:
        batch_op.drop_index("ix_business_glossary_terms_status")
        batch_op.drop_index("ix_business_glossary_terms_domain_id")
        batch_op.drop_constraint("fk_glossary_domain_id", type_="foreignkey")
        batch_op.drop_column("review_note")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("reviewed_by")
        batch_op.drop_column("proposed_by")
        batch_op.drop_column("status")
        batch_op.drop_column("domain_id")
    with op.batch_alter_table("assets") as batch_op:
        batch_op.drop_index("ix_assets_quality_score")
        batch_op.drop_index("ix_assets_domain_id")
        batch_op.drop_constraint("fk_assets_domain_id", type_="foreignkey")
        batch_op.drop_column("quality_explainable_at")
        batch_op.drop_column("quality_score")
        batch_op.drop_column("domain_id")
    op.drop_table("governance_domains")
    for enum_name in (
        "suggestiontype",
        "usagedecisionstatus",
        "discoveryeventtype",
        "reviewstatus",
        "classificationtype",
        "glossarystatus",
    ):
        postgresql.ENUM(name=enum_name, create_type=False).drop(bind, checkfirst=True)
