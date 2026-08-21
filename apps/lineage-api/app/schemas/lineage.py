from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


RelationshipType = Literal["FLOWS_TO", "DERIVES_FROM", "CONSUMES", "COLUMN_FLOWS_TO"]


class LineageNodeInput(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    node_type: Literal["asset", "column", "dashboard", "report"] = "asset"
    display_name: str | None = Field(default=None, max_length=1024)
    owner: str | None = Field(default=None, max_length=255)
    domain: str | None = Field(default=None, max_length=255)
    business_criticality: str | None = Field(default=None, max_length=32)


class LineageEventCreate(BaseModel):
    event_id: str = Field(min_length=1, max_length=255)
    source: LineageNodeInput
    target: LineageNodeInput
    relationship_type: RelationshipType
    source_provenance: str = Field(min_length=1, max_length=255)
    confidence: int = Field(ge=0, le=100)
    observed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageEdgeRead(BaseModel):
    event_id: str
    source_id: str
    target_id: str
    relationship_type: str
    source_provenance: str
    confidence: int
    observed_at: datetime | str
    created_at: datetime | str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineageNodeRead(BaseModel):
    id: str
    node_type: str | None = None
    display_name: str | None = None
    owner: str | None = None
    domain: str | None = None
    business_criticality: str | None = None


class LineageGraphRead(BaseModel):
    focal_asset_id: str
    direction: Literal["upstream", "downstream", "both"]
    nodes: list[LineageNodeRead]
    edges: list[LineageEdgeRead]


class ImpactRequest(BaseModel):
    asset_id: str
    max_depth: int = Field(default=5, ge=1, le=12)


class QualityIncidentImpactRequest(ImpactRequest):
    incident_id: str = Field(min_length=1, max_length=255)
    severity: str = Field(min_length=1, max_length=32)
    evidence: dict[str, Any] = Field(default_factory=dict)


class SchemaChangeImpactRequest(ImpactRequest):
    change_id: str = Field(min_length=1, max_length=255)
    change_summary: str = Field(min_length=1, max_length=10000)
    changed_columns: list[str] = Field(default_factory=list, max_length=500)


class ImpactedConsumerRead(BaseModel):
    asset_id: str
    node_type: str | None = None
    display_name: str | None = None
    owner: str | None = None
    domain: str | None = None
    business_criticality: str | None = None
    minimum_confidence: int | None = None
    distance: int


class ImpactAnalysisRead(BaseModel):
    impact_type: Literal["quality_incident", "schema_change", "generic"]
    asset_id: str
    event_reference: str | None = None
    consumers: list[ImpactedConsumerRead]
