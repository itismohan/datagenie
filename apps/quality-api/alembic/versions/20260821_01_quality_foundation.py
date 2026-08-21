"""Create durable trustworthy quality foundation tables.

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
    rule_type = sa.Enum("COMPLETENESS", "UNIQUENESS", "VALIDITY", "FRESHNESS", "REFERENTIAL_INTEGRITY", "DISTRIBUTION_ANOMALY", name="ruletype")
    severity = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="ruleseverity")
    run_status = sa.Enum("QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", name="runstatus")
    run_trigger = sa.Enum("MANUAL", "SCHEDULED", name="runtrigger")
    incident_status = sa.Enum("OPEN", "ACKNOWLEDGED", "RESOLVED", name="incidentstatus")
    criticality = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="businesscriticality")
    certification = sa.Enum("UNDER_REVIEW", "CERTIFIED", "DEPRECATED", name="certificationstatus")

    op.create_table(
        "quality_rules",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("asset_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("column_name", sa.String(length=255)),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("rule_type", rule_type, nullable=False, index=True),
        sa.Column("severity", severity, nullable=False),
        sa.Column("owner", sa.String(length=255), index=True),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("schedule_cron", sa.String(length=100)),
        sa.Column("next_run_at", sa.DateTime(timezone=True), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "quality_rule_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("rule_id", sa.String(length=36), sa.ForeignKey("quality_rules.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("changed_by", sa.String(length=255), nullable=False),
        sa.Column("change_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("rule_id", "version", name="uq_quality_rule_version"),
    )
    op.create_table(
        "quality_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("asset_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("status", run_status, nullable=False, index=True),
        sa.Column("trigger", run_trigger, nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("profile_snapshot", sa.JSON(), nullable=False),
        sa.Column("effective_rule_versions", sa.JSON(), nullable=False),
        sa.Column("technical_score", sa.Integer()),
        sa.Column("explainable", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "quality_rule_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("quality_runs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("rule_id", sa.String(length=36), sa.ForeignKey("quality_rules.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("rule_version", sa.Integer(), nullable=False),
        sa.Column("rule_type", rule_type, nullable=False),
        sa.Column("column_name", sa.String(length=255)),
        sa.Column("evaluated", sa.Boolean(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("observed_value", sa.JSON(), nullable=False),
        sa.Column("expected_value", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "rule_id", "rule_version", name="uq_quality_run_rule_version"),
    )
    op.create_table(
        "quality_incidents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("asset_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("rule_id", sa.String(length=36), sa.ForeignKey("quality_rules.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("latest_result_id", sa.String(length=36), sa.ForeignKey("quality_rule_results.id", ondelete="SET NULL")),
        sa.Column("status", incident_status, nullable=False, index=True),
        sa.Column("severity", severity, nullable=False),
        sa.Column("assignee", sa.String(length=255), index=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "quality_incident_comments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("incident_id", sa.String(length=36), sa.ForeignKey("quality_incidents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "asset_quality_profiles",
        sa.Column("asset_id", sa.String(length=36), primary_key=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("profiled_by", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "asset_quality_contexts",
        sa.Column("asset_id", sa.String(length=36), primary_key=True),
        sa.Column("business_criticality", criticality, nullable=False, index=True),
        sa.Column("certification_status", certification, nullable=False, index=True),
        sa.Column("accountable_owner", sa.String(length=255), index=True),
        sa.Column("latest_explainable_run_at", sa.DateTime(timezone=True)),
        sa.Column("latest_technical_score", sa.Integer()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("asset_quality_contexts")
    op.drop_table("asset_quality_profiles")
    op.drop_table("quality_incident_comments")
    op.drop_table("quality_incidents")
    op.drop_table("quality_rule_results")
    op.drop_table("quality_runs")
    op.drop_table("quality_rule_versions")
    op.drop_table("quality_rules")
