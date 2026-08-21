import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def uuid_str() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class RuleType(str, Enum):
    COMPLETENESS = "completeness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"
    FRESHNESS = "freshness"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    DISTRIBUTION_ANOMALY = "distribution_anomaly"


class RuleSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RunTrigger(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class IncidentStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class BusinessCriticality(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CertificationStatus(str, Enum):
    UNDER_REVIEW = "under_review"
    CERTIFIED = "certified"
    DEPRECATED = "deprecated"


class QualityRule(Base):
    __tablename__ = "quality_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    asset_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(SqlEnum(RuleType), index=True, nullable=False)
    severity: Mapped[RuleSeverity] = mapped_column(SqlEnum(RuleSeverity), default=RuleSeverity.MEDIUM, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    versions: Mapped[list["QualityRuleVersion"]] = relationship(back_populates="rule", cascade="all, delete-orphan")
    results: Mapped[list["QualityRuleResult"]] = relationship(back_populates="rule")


class QualityRuleVersion(Base):
    __tablename__ = "quality_rule_versions"
    __table_args__ = (UniqueConstraint("rule_id", "version", name="uq_quality_rule_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    rule_id: Mapped[str] = mapped_column(ForeignKey("quality_rules.id", ondelete="CASCADE"), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    changed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    rule: Mapped[QualityRule] = relationship(back_populates="versions")


class QualityRun(Base):
    __tablename__ = "quality_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    asset_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    status: Mapped[RunStatus] = mapped_column(SqlEnum(RunStatus), default=RunStatus.QUEUED, index=True, nullable=False)
    trigger: Mapped[RunTrigger] = mapped_column(SqlEnum(RunTrigger), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    effective_rule_versions: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    technical_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    explainable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    results: Mapped[list["QualityRuleResult"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class QualityRuleResult(Base):
    __tablename__ = "quality_rule_results"
    __table_args__ = (UniqueConstraint("run_id", "rule_id", "rule_version", name="uq_quality_run_rule_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    run_id: Mapped[str] = mapped_column(ForeignKey("quality_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(ForeignKey("quality_rules.id", ondelete="RESTRICT"), index=True, nullable=False)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(SqlEnum(RuleType), nullable=False)
    column_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evaluated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    expected_value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    run: Mapped[QualityRun] = relationship(back_populates="results")
    rule: Mapped[QualityRule] = relationship(back_populates="results")


class QualityIncident(Base):
    __tablename__ = "quality_incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    asset_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(ForeignKey("quality_rules.id", ondelete="RESTRICT"), index=True, nullable=False)
    latest_result_id: Mapped[str | None] = mapped_column(ForeignKey("quality_rule_results.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[IncidentStatus] = mapped_column(SqlEnum(IncidentStatus), default=IncidentStatus.OPEN, index=True, nullable=False)
    severity: Mapped[RuleSeverity] = mapped_column(SqlEnum(RuleSeverity), nullable=False)
    assignee: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    comments: Mapped[list["QualityIncidentComment"]] = relationship(back_populates="incident", cascade="all, delete-orphan")


class QualityIncidentComment(Base):
    __tablename__ = "quality_incident_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    incident_id: Mapped[str] = mapped_column(ForeignKey("quality_incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    incident: Mapped[QualityIncident] = relationship(back_populates="comments")


class AssetQualityProfile(Base):
    __tablename__ = "asset_quality_profiles"

    asset_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    profiled_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class AssetQualityContext(Base):
    __tablename__ = "asset_quality_contexts"

    asset_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_criticality: Mapped[BusinessCriticality] = mapped_column(
        SqlEnum(BusinessCriticality), default=BusinessCriticality.MEDIUM, index=True, nullable=False
    )
    certification_status: Mapped[CertificationStatus] = mapped_column(
        SqlEnum(CertificationStatus), default=CertificationStatus.UNDER_REVIEW, index=True, nullable=False
    )
    accountable_owner: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    latest_explainable_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_technical_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
