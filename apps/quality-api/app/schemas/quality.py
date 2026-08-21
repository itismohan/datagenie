from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.quality import (
    BusinessCriticality,
    CertificationStatus,
    IncidentStatus,
    RuleSeverity,
    RuleType,
    RunStatus,
    RunTrigger,
)


class QualityRuleCreate(BaseModel):
    asset_id: str = Field(min_length=1, max_length=36)
    column_name: str | None = Field(default=None, max_length=255)
    name: str = Field(min_length=2, max_length=255)
    rule_type: RuleType
    severity: RuleSeverity = RuleSeverity.MEDIUM
    owner: str | None = Field(default=None, max_length=255)
    parameters: dict[str, Any] = Field(default_factory=dict)
    schedule_cron: str | None = Field(default=None, max_length=100)
    next_run_at: datetime | None = None


class QualityRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    severity: RuleSeverity | None = None
    owner: str | None = Field(default=None, max_length=255)
    parameters: dict[str, Any] | None = None
    enabled: bool | None = None
    schedule_cron: str | None = Field(default=None, max_length=100)
    next_run_at: datetime | None = None
    change_reason: str | None = Field(default=None, max_length=1000)


class QualityRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    column_name: str | None
    name: str
    rule_type: RuleType
    severity: RuleSeverity
    owner: str | None
    parameters: dict[str, Any]
    version: int
    enabled: bool
    schedule_cron: str | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class QualityRunCreate(BaseModel):
    profile_snapshot: dict[str, Any] = Field(default_factory=dict)
    trigger: RunTrigger = RunTrigger.MANUAL


class QualityRuleResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    rule_id: str
    rule_version: int
    rule_type: RuleType
    column_name: str | None
    evaluated: bool
    passed: bool
    score: int
    observed_value: dict[str, Any]
    expected_value: dict[str, Any]
    evidence: dict[str, Any]
    explanation: str
    evaluated_at: datetime


class QualityRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    status: RunStatus
    trigger: RunTrigger
    requested_by: str
    profile_snapshot: dict[str, Any]
    effective_rule_versions: dict[str, int]
    technical_score: int | None
    explainable: bool
    error_message: str | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    results: list[QualityRuleResultRead] = Field(default_factory=list)


class AssetQualityContextUpsert(BaseModel):
    business_criticality: BusinessCriticality = BusinessCriticality.MEDIUM
    certification_status: CertificationStatus = CertificationStatus.UNDER_REVIEW
    accountable_owner: str | None = Field(default=None, max_length=255)


class AssetQualityContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    business_criticality: BusinessCriticality
    certification_status: CertificationStatus
    accountable_owner: str | None
    latest_explainable_run_at: datetime | None
    latest_technical_score: int | None
    updated_at: datetime


class IncidentUpdate(BaseModel):
    status: IncidentStatus | None = None
    assignee: str | None = Field(default=None, max_length=255)


class IncidentCommentCreate(BaseModel):
    author: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=10000)


class IncidentCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    author: str
    body: str
    created_at: datetime


class QualityIncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    rule_id: str
    latest_result_id: str | None
    status: IncidentStatus
    severity: RuleSeverity
    assignee: str | None
    evidence: dict[str, Any]
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None
    comments: list[IncidentCommentRead] = Field(default_factory=list)


class CriticalCoverageMetric(BaseModel):
    critical_assets: int
    covered_assets: int
    percentage: float
    recency_hours: int
    exclusion_reasons: dict[str, int]


class AssetQualityProfileUpsert(BaseModel):
    snapshot: dict[str, Any] = Field(default_factory=dict)
    observed_at: datetime
    profiled_by: str = Field(min_length=1, max_length=255)


class AssetQualityProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    snapshot: dict[str, Any]
    observed_at: datetime
    profiled_by: str
    updated_at: datetime
