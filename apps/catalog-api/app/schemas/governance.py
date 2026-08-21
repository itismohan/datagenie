from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.catalog import (
    ClassificationType,
    DiscoveryEventType,
    GlossaryStatus,
    ReviewStatus,
    SuggestionType,
    UsageDecisionStatus,
)


class DomainCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    business_owner: str | None = Field(default=None, max_length=255)
    data_steward: str | None = Field(default=None, max_length=255)


class DomainRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    business_owner: str | None
    data_steward: str | None
    created_at: datetime
    updated_at: datetime


class GlossaryTermCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    definition: str = Field(min_length=10, max_length=10000)
    owner: str | None = Field(default=None, max_length=255)
    domain_id: str | None = None


class GlossaryTermReview(BaseModel):
    status: GlossaryStatus
    review_note: str | None = Field(default=None, max_length=5000)


class GlossaryTermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    definition: str
    owner: str | None
    domain_id: str | None
    status: GlossaryStatus
    proposed_by: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime


class GlossaryAssetMappingCreate(BaseModel):
    asset_id: str
    column_name: str | None = Field(default=None, max_length=255)


class GlossaryAssetMappingReview(BaseModel):
    status: ReviewStatus


class GlossaryAssetMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    term_id: str
    asset_id: str
    column_name: str | None
    status: ReviewStatus
    proposed_by: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime


class ClassificationFindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    column_name: str
    classification_type: ClassificationType
    confidence: int
    evidence: dict[str, Any]
    status: ReviewStatus
    detected_by: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime


class ClassificationReview(BaseModel):
    status: ReviewStatus
    review_note: str | None = Field(default=None, max_length=5000)


class CertificationRequestCreate(BaseModel):
    note: str | None = Field(default=None, max_length=5000)


class CertificationRequestDecision(BaseModel):
    status: UsageDecisionStatus
    decision_note: str | None = Field(default=None, max_length=5000)


class CertificationRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    requested_by: str
    status: UsageDecisionStatus
    decision_by: str | None
    decision_note: str | None
    requested_at: datetime
    decided_at: datetime | None


class DiscoveryEventCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    event_type: DiscoveryEventType
    asset_id: str | None = None
    query_text: str | None = Field(default=None, max_length=255)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class DiscoveryMetricRead(BaseModel):
    sessions: int
    successful_sessions: int
    percentage: float
    successful_by_outcome: dict[str, int]


class GovernanceSuggestionCreate(BaseModel):
    asset_id: str
    suggestion_type: SuggestionType
    proposed_value: dict[str, Any]
    evidence: dict[str, Any]
    generated_by: str = Field(default="deterministic-governance-assistant", max_length=255)


class GovernanceSuggestionReview(BaseModel):
    status: ReviewStatus
    review_note: str | None = Field(default=None, max_length=5000)


class GovernanceSuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    asset_id: str
    suggestion_type: SuggestionType
    proposed_value: dict[str, Any]
    evidence: dict[str, Any]
    generated_by: str
    status: ReviewStatus
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime


class AssetQualityEvidenceUpdate(BaseModel):
    technical_score: int = Field(ge=0, le=100)
    explainable_at: datetime
    quality_run_id: str = Field(min_length=1, max_length=255)
