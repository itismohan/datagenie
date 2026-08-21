
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.policy import enforce_policy
from app.core.security import (
    ROLE_ANALYST,
    ROLE_DATA_OWNER,
    ROLE_DATA_STEWARD,
    ROLE_PLATFORM_ADMIN,
    ROLE_READ_ONLY,
    Principal,
    get_current_principal,
    require_roles,
)
from app.db.session import get_db
from app.models.catalog import Asset, DiscoveryEventType
from app.schemas.catalog import AssetCurationUpdate, AssetRead, AssetSearchResponse
from app.services.audit_service import record_audit_event
from app.services.catalog_service import get_asset_or_404, search_assets, update_asset_curation
from app.services.governance_service import record_discovery_event
from app.services.idempotency_service import IdempotencyContext, get_idempotency_context, replay_response, store_response

router = APIRouter()
asset_reader = require_roles(ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD, ROLE_DATA_OWNER, ROLE_ANALYST, ROLE_READ_ONLY)


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@router.get("/", response_model=AssetSearchResponse)
def list_assets(
    request: Request,
    q: str | None = Query(default=None, min_length=1, max_length=255),
    source_id: str | None = None,
    asset_type: str | None = None,
    lifecycle_status: str | None = None,
    owner: str | None = None,
    classification: str | None = None,
    tag: str | None = None,
    freshness_before: datetime | None = None,
    domain: str | None = None,
    business_term: str | None = None,
    quality_min: int | None = Query(default=None, ge=0, le=100),
    explainable_quality_only: bool = False,
    discovery_session_id: str | None = Query(default=None, min_length=1, max_length=128),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(asset_reader),
) -> AssetSearchResponse:
    items, total, facets, index_fresh_at = search_assets(
        db,
        q=q,
        source_id=source_id,
        asset_type=asset_type,
        lifecycle_status=lifecycle_status,
        owner=owner,
        classification=classification,
        tag=tag,
        freshness_before=freshness_before,
        domain=domain,
        business_term=business_term,
        quality_min=quality_min,
        explainable_quality_only=explainable_quality_only,
        limit=limit,
        offset=offset,
    )
    if discovery_session_id:
        record_discovery_event(
            db,
            discovery_session_id,
            principal.subject,
            DiscoveryEventType.SEARCH,
            None,
            q or business_term,
            {"result_count": total},
        )
    record_audit_event(
        db,
        principal=principal,
        action="asset.search",
        resource_type="asset",
        resource_id=None,
        outcome="success",
        request_id=request_id(request),
        metadata={"query_present": q is not None, "result_count": total},
    )
    db.commit()
    return AssetSearchResponse(items=items, total=total, facets=facets, index_fresh_at=index_fresh_at)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(
    asset_id: str,
    request: Request,
    discovery_session_id: str | None = Query(default=None, min_length=1, max_length=128),
    purpose: str | None = Query(default=None, min_length=3, max_length=500),
    db: Session = Depends(get_db),
    principal: Principal = Depends(asset_reader),
) -> Asset:
    asset = get_asset_or_404(db, asset_id)
    enforce_policy(
        db,
        principal,
        request,
        action="asset.read",
        resource_type="asset",
        resource_id=asset.id,
        purpose=purpose,
    )
    if discovery_session_id:
        record_discovery_event(
            db,
            discovery_session_id,
            principal.subject,
            DiscoveryEventType.ASSET_VIEW,
            asset.id,
            None,
            {},
        )
    record_audit_event(
        db,
        principal=principal,
        action="asset.read",
        resource_type="asset",
        resource_id=asset.id,
        outcome="success",
        request_id=request_id(request),
    )
    db.commit()
    return asset


@router.patch("/{asset_id}", response_model=AssetRead)
def curate_asset(
    asset_id: str,
    payload: AssetCurationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
    idempotency: IdempotencyContext | None = Depends(get_idempotency_context),
) -> Asset | Response:
    replay = replay_response(db, idempotency)
    if replay:
        return replay
    asset = get_asset_or_404(db, asset_id)
    enforce_policy(
        db,
        principal,
        request,
        action="asset.curate",
        resource_type="asset",
        resource_id=asset.id,
    )
    asset = update_asset_curation(db, asset, payload)
    record_audit_event(
        db,
        principal=principal,
        action="asset.curate",
        resource_type="asset",
        resource_id=asset.id,
        outcome="success",
        request_id=request_id(request),
        metadata={"updated_fields": sorted(payload.model_dump(exclude_unset=True, exclude={"actor"}).keys())},
    )
    body = AssetRead.model_validate(asset).model_dump(mode="json")
    store_response(db, idempotency, body, status.HTTP_200_OK)
    return asset
