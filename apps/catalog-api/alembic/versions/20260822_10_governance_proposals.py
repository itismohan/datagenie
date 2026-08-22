"""Add proposal-only governance workflows.

Revision ID: 20260822_10
Revises: 20260821_09
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260822_10"
down_revision = "20260821_09"
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
    proposal_type = sa.Enum(
        "ASSET_CURATION", "CERTIFICATION_REVIEW_REQUEST", "QUALITY_CHECK_SCHEDULE", name="governanceproposaltype"
    )
    proposal_status = sa.Enum(
        "PENDING_REVIEW", "APPROVED", "REJECTED", "CANCELLED", "EXPIRED", "EXECUTED", "BLOCKED", name="governanceproposalstatus"
    )
    quality_schedule_status = sa.Enum("PENDING", "READY", "CANCELLED", name="qualityschedulerequeststatus")

    op.create_table(
        "governance_proposals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("proposal_type", proposal_type, nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("proposal_text", sa.Text(), nullable=False),
        sa.Column("change_diff", sa.JSON(), nullable=False),
        sa.Column("source_evidence", sa.JSON(), nullable=False),
        sa.Column("impact", sa.JSON(), nullable=False),
        sa.Column("source_channel", sa.String(length=64), nullable=False),
        sa.Column("initiating_subject", sa.String(length=255), nullable=False),
        sa.Column("initiating_agent_id", sa.String(length=255), nullable=True),
        sa.Column("initiating_model_id", sa.String(length=255), nullable=True),
        sa.Column("initiating_host_id", sa.String(length=255), nullable=True),
        sa.Column("source_request_id", sa.String(length=128), nullable=False),
        sa.Column("policy_snapshot", sa.JSON(), nullable=False),
        sa.Column("version_preconditions", sa.JSON(), nullable=False),
        sa.Column("proposal_hash", sa.String(length=64), nullable=False),
        sa.Column("status", proposal_status, nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.String(length=255), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.String(length=255), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("approval_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confirmation_nonce_digest", sa.String(length=64), nullable=True),
        sa.Column("confirmation_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("executed_by", sa.String(length=255), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_outcome", sa.String(length=32), nullable=True),
        sa.Column("blocked_reason", sa.String(length=255), nullable=True),
        sa.Column("audit_event_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_governance_proposals_tenant_id", "governance_proposals", ["tenant_id"])
    op.create_index("ix_governance_proposals_proposal_type", "governance_proposals", ["proposal_type"])
    op.create_index("ix_governance_proposals_resource_type", "governance_proposals", ["resource_type"])
    op.create_index("ix_governance_proposals_resource_id", "governance_proposals", ["resource_id"])
    op.create_index("ix_governance_proposals_initiating_subject", "governance_proposals", ["initiating_subject"])
    op.create_index("ix_governance_proposals_source_request_id", "governance_proposals", ["source_request_id"])
    op.create_index("ix_governance_proposals_proposal_hash", "governance_proposals", ["proposal_hash"])
    op.create_index("ix_governance_proposals_status", "governance_proposals", ["status"])
    op.create_index("ix_governance_proposals_expires_at", "governance_proposals", ["expires_at"])
    op.create_index("ix_governance_proposals_tenant_status_created", "governance_proposals", ["tenant_id", "status", "created_at"])
    op.create_index("ix_governance_proposals_tenant_resource", "governance_proposals", ["tenant_id", "resource_type", "resource_id"])

    op.create_table(
        "quality_check_schedule_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("schedule", sa.JSON(), nullable=False),
        sa.Column("status", quality_schedule_status, nullable=False, server_default="PENDING"),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["proposal_id"], ["governance_proposals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id"),
    )
    op.create_index("ix_quality_check_schedule_requests_tenant_id", "quality_check_schedule_requests", ["tenant_id"])
    op.create_index("ix_quality_check_schedule_requests_proposal_id", "quality_check_schedule_requests", ["proposal_id"])
    op.create_index("ix_quality_check_schedule_requests_asset_id", "quality_check_schedule_requests", ["asset_id"])
    op.create_index("ix_quality_check_schedule_requests_status", "quality_check_schedule_requests", ["status"])
    op.create_index("ix_quality_schedule_requests_tenant_status", "quality_check_schedule_requests", ["tenant_id", "status"])

    if op.get_bind().dialect.name == "postgresql":
        _enable_tenant_rls("governance_proposals")
        _enable_tenant_rls("quality_check_schedule_requests")


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table_name in ("quality_check_schedule_requests", "governance_proposals"):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table_name} ON {table_name}")
            op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")
    op.drop_table("quality_check_schedule_requests")
    op.drop_table("governance_proposals")
    if op.get_bind().dialect.name == "postgresql":
        sa.Enum(name="qualityschedulerequeststatus").drop(op.get_bind(), checkfirst=True)
        sa.Enum(name="governanceproposalstatus").drop(op.get_bind(), checkfirst=True)
        sa.Enum(name="governanceproposaltype").drop(op.get_bind(), checkfirst=True)
