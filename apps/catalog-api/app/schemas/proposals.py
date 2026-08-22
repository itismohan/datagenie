from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.catalog import GovernanceProposalStatus, GovernanceProposalType, QualityScheduleRequestStatus


class ProposalResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_type: Literal["asset"]
    resource_id: str = Field(min_length=1, max_length=255)


class ProposalSourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Literal["api", "mcp"] = "api"
    agent_id: str | None = Field(default=None, max_length=255)
    model_id: str | None = Field(default=None, max_length=255)


class GovernanceProposalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_type: GovernanceProposalType
    title: str = Field(min_length=5, max_length=255)
    proposal_text: str = Field(min_length=10, max_length=10_000)
    resource: ProposalResource
    purpose: str = Field(min_length=3, max_length=500)
    diff: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    impact: dict[str, Any] = Field(default_factory=dict)
    version_preconditions: dict[str, Any] = Field(default_factory=dict)
    source: ProposalSourceInput = Field(default_factory=ProposalSourceInput)
    expires_in_seconds: int = Field(default=86_400, ge=300, le=604_800)


class ProposalReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_note: str = Field(min_length=3, max_length=5_000)


class ProposalExecution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_hash: str = Field(min_length=64, max_length=64)
    confirmation_nonce: str = Field(min_length=32, max_length=255)


class ProposalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    proposal_type: GovernanceProposalType
    resource_type: str
    resource_id: str
    title: str
    proposal_text: str
    change_diff: dict[str, Any]
    source_evidence: list[dict[str, Any]]
    impact: dict[str, Any]
    source_channel: str
    initiating_subject: str
    initiating_agent_id: str | None
    initiating_model_id: str | None
    initiating_host_id: str | None
    source_request_id: str
    policy_snapshot: dict[str, Any]
    version_preconditions: dict[str, Any]
    proposal_hash: str
    status: GovernanceProposalStatus
    expires_at: datetime
    approved_by: str | None
    approved_at: datetime | None
    rejected_by: str | None
    rejected_at: datetime | None
    cancelled_by: str | None
    cancelled_at: datetime | None
    review_note: str | None
    approval_version: int
    confirmation_expires_at: datetime | None
    execution_attempts: int
    executed_by: str | None
    executed_at: datetime | None
    execution_outcome: str | None
    blocked_reason: str | None
    audit_event_id: str | None
    created_at: datetime
    updated_at: datetime


class ProposalCreated(ProposalRead):
    inbox_uri: str


class ProposalApproval(ProposalRead):
    confirmation_nonce: str


class ProposalExecutionRead(ProposalRead):
    execution_result: dict[str, Any] = Field(default_factory=dict)


class QualityScheduleRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    proposal_id: str
    asset_id: str
    requested_by: str
    schedule: dict[str, Any]
    status: QualityScheduleRequestStatus
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime
