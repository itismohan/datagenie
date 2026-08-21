from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.mcp_security import McpActor, require_mcp_gateway_actor
from app.schemas.lineage import (
    ImpactAnalysisRead,
    ImpactRequest,
    LineageEventCreate,
    LineageGraphRead,
    QualityIncidentImpactRequest,
    SchemaChangeImpactRequest,
)
from app.services.lineage_service import downstream_impact, get_lineage, ingest_lineage_event

router = APIRouter()


@router.post("/events", status_code=status.HTTP_201_CREATED)
def ingest_event(payload: LineageEventCreate) -> dict:
    return ingest_lineage_event(payload)


@router.get("/internal/mcp/{asset_id}", response_model=LineageGraphRead, include_in_schema=False)
def fetch_mcp_lineage(
    asset_id: str,
    request: Request,
    direction: str = Query(default="both", pattern="^(upstream|downstream|both)$"),
    max_depth: int = Query(default=3, ge=1, le=3),
    _actor: McpActor = Depends(require_mcp_gateway_actor),
) -> dict:
    return get_lineage(asset_id, direction=direction, max_depth=max_depth)


@router.get("/{asset_id}", response_model=LineageGraphRead)
def fetch_lineage(
    asset_id: str,
    direction: str = Query(default="both", pattern="^(upstream|downstream|both)$"),
    max_depth: int = Query(default=5, ge=1, le=12),
) -> dict:
    return get_lineage(asset_id, direction=direction, max_depth=max_depth)


@router.post("/impact", response_model=ImpactAnalysisRead)
def generic_impact(payload: ImpactRequest) -> dict:
    return downstream_impact(payload.asset_id, payload.max_depth, impact_type="generic")


@router.post("/impact/quality-incidents", response_model=ImpactAnalysisRead)
def quality_incident_impact(payload: QualityIncidentImpactRequest) -> dict:
    return downstream_impact(
        payload.asset_id,
        payload.max_depth,
        impact_type="quality_incident",
        event_reference=payload.incident_id,
        metadata={"severity": payload.severity, "evidence": payload.evidence},
    )


@router.post("/impact/schema-changes", response_model=ImpactAnalysisRead)
def schema_change_impact(payload: SchemaChangeImpactRequest) -> dict:
    return downstream_impact(
        payload.asset_id,
        payload.max_depth,
        impact_type="schema_change",
        event_reference=payload.change_id,
        metadata={"change_summary": payload.change_summary, "changed_columns": payload.changed_columns},
    )
