from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PolicyOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ALLOW_WITH_OBLIGATIONS = "allow_with_obligations"
    REQUIRES_HUMAN_APPROVAL = "requires_human_approval"


class PolicyResource(BaseModel):
    resource_type: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    resource_id: str = Field(min_length=1, max_length=255)


class PolicyContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str | None = Field(default=None, min_length=1, max_length=255)
    request_id: str | None = Field(default=None, min_length=1, max_length=128)


class PolicyDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=3, max_length=128, pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
    resource: PolicyResource
    purpose: str | None = Field(default=None, max_length=500)
    context: PolicyContext = Field(default_factory=PolicyContext)

    @model_validator(mode="after")
    def normalize_purpose(self) -> "PolicyDecisionRequest":
        if self.purpose is not None:
            normalized = " ".join(self.purpose.split())
            self.purpose = normalized or None
        return self


class PolicyEvidenceReference(BaseModel):
    type: str = Field(min_length=1, max_length=100)
    reference: str = Field(min_length=1, max_length=512)


class PolicyDecisionRead(BaseModel):
    outcome: PolicyOutcome
    decision_version: str
    rule_ids: list[str]
    evidence: list[PolicyEvidenceReference]
    obligations: list[str]
    evaluated_at: datetime
    expires_at: datetime
    request_id: str
    resource_visible: bool


class PolicyDecisionContext(BaseModel):
    """Trusted internal context supplied by route adapters after request validation."""

    request_id: str = Field(min_length=1, max_length=128)
    workflow_id: str | None = Field(default=None, min_length=1, max_length=255)
    extras: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")
