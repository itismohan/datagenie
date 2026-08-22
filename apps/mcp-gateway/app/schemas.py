from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class JsonRpcRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jsonrpc: Literal["2.0"]
    id: str | int | None = None
    method: str = Field(min_length=1, max_length=128)
    params: dict[str, Any] = Field(default_factory=dict)


class JsonRpcError(BaseModel):
    code: int
    message: str
    data: dict[str, Any] | None = None


class JsonRpcResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None
    result: dict[str, Any] | None = None
    error: JsonRpcError | None = None


class Principal(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    tenant_id: str = Field(min_length=1, max_length=128)
    roles: frozenset[str] = Field(default_factory=frozenset)
    scopes: frozenset[str] = Field(default_factory=frozenset)
    host_id: str = Field(min_length=1, max_length=255)
    issuer: str | None = None


class PolicyEvidence(BaseModel):
    type: str
    reference: str


class PolicyPacket(BaseModel):
    outcome: Literal["allow", "deny", "allow_with_obligations", "requires_human_approval"]
    rule_ids: list[str] = Field(default_factory=list)
    evidence: list[PolicyEvidence] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)
    expires_at: datetime
    decision_version: str


class Provenance(BaseModel):
    source: str
    source_request_id: str | None = None
    retrieved_at: datetime


class StructuredResult(BaseModel):
    tool_version: str = "0.1.0"
    request_id: str
    tenant_bound: Literal[True] = True
    generated_at: datetime
    timestamp: datetime
    provenance: list[Provenance]
    evidence: list[PolicyEvidence]
    policy: PolicyPacket | None = None
    obligations: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    redactions: list[str] = Field(default_factory=list)
    truncated: bool = False
    data: dict[str, Any]


class LedgerRecord(BaseModel):
    invocation_id: str
    request_id: str
    tenant_id: str
    actor_subject: str
    host_id: str
    operation_kind: Literal["tool", "resource", "prompt", "protocol"]
    operation_name: str
    input_digest: str
    policy_outcome: str | None = None
    outcome: Literal["allowed", "denied", "error"]
    result_count: int = 0
    result_bytes: int = 0
    duration_ms: float = 0.0
    error_code: str | None = None
    created_at: datetime


class ToolCall(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ResourceRead(BaseModel):
    uri: str = Field(min_length=1, max_length=2048)


class PromptGet(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    arguments: dict[str, Any] = Field(default_factory=dict)


class SearchArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str | None = Field(default=None, max_length=255)
    business_term: str | None = Field(default=None, max_length=255)
    owner: str | None = Field(default=None, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    tag: str | None = Field(default=None, max_length=128)
    classification: str | None = Field(default=None, max_length=128)
    quality_min: float | None = Field(default=None, ge=0, le=100)
    certification_status: str | None = Field(default=None, max_length=64)
    source: str | None = Field(default=None, max_length=255)
    purpose: str = Field(min_length=3, max_length=500)
    limit: int = Field(default=25, ge=1, le=50)


class AssetArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1, max_length=64)
    purpose: str = Field(min_length=3, max_length=500)
    include: list[Literal["columns", "glossary", "governance", "quality"]] = Field(default_factory=list, max_length=4)


class QualityArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1, max_length=64)
    purpose: str = Field(min_length=3, max_length=500)
    history_limit: int = Field(default=5, ge=1, le=10)


class LineageArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1, max_length=64)
    purpose: str = Field(min_length=3, max_length=500)
    direction: Literal["upstream", "downstream", "both"] = "both"
    depth: int = Field(default=2, ge=1, le=3)


class ProposalArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_type: Literal["asset_curation", "certification_review_request", "quality_check_schedule"]
    asset_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=5, max_length=255)
    proposal_text: str = Field(min_length=10, max_length=10_000)
    purpose: str = Field(min_length=3, max_length=500)
    diff: dict[str, Any] = Field(default_factory=dict)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    impact: dict[str, Any] = Field(default_factory=dict)
    technical_version: int = Field(ge=1)
    agent_id: str | None = Field(default=None, max_length=255)
    model_id: str | None = Field(default=None, max_length=255)
    expires_in_seconds: int = Field(default=86_400, ge=300, le=604_800)


class CertificationReviewArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1, max_length=64)
    purpose: str = Field(min_length=3, max_length=500)
    note: str | None = Field(default=None, max_length=5_000)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    technical_version: int = Field(ge=1)
    agent_id: str | None = Field(default=None, max_length=255)
    model_id: str | None = Field(default=None, max_length=255)


class QualityScheduleArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1, max_length=64)
    purpose: str = Field(min_length=3, max_length=500)
    frequency: Literal["daily", "weekly", "manual"]
    rule_types: list[Literal["completeness", "uniqueness", "validity", "freshness", "referential_integrity", "distribution_anomaly"]] = Field(default_factory=list, max_length=6)
    evidence: list[dict[str, Any]] = Field(default_factory=list, max_length=50)
    technical_version: int = Field(ge=1)
    agent_id: str | None = Field(default=None, max_length=255)
    model_id: str | None = Field(default=None, max_length=255)
