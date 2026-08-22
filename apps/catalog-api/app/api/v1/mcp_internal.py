from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.security import Principal, get_mcp_delegated_principal
from app.db.session import get_db
from app.models.catalog import GovernanceDomain
from app.schemas.proposals import GovernanceProposalCreate, ProposalCreated, ProposalRead
from app.schemas.catalog import AssetRead
from app.schemas.policy import PolicyContext, PolicyResource
from app.services.catalog_service import get_asset_or_404, search_assets
from app.services.policy_service import evaluate_access
from app.services.proposal_service import create_proposal

router = APIRouter()


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _policy_packet(db: Session, principal: Principal, request: Request, asset_id: str, purpose: str) -> dict:
    decision = evaluate_access(
        db,
        subject=principal,
        tenant=principal.tenant_id,
        action="asset.read",
        resource=PolicyResource(resource_type="asset", resource_id=asset_id),
        purpose=purpose,
        context=PolicyContext(request_id=_request_id(request), workflow_id="mcp-gateway"),
    )
    db.commit()
    return decision.to_read().model_dump(mode="json")


def _asset_packet(db: Session, principal: Principal, request: Request, asset, purpose: str) -> dict:
    policy = _policy_packet(db, principal, request, asset.id, purpose)
    if policy["outcome"] in {"deny", "requires_human_approval"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "mcp_forbidden", "message": "The shared policy does not permit this asset response."},
        )
    return {"asset": AssetRead.model_validate(asset).model_dump(mode="json"), "policy": policy}


@router.get("/assets")
def mcp_search_assets(
    request: Request,
    q: str | None = Query(default=None, max_length=255),
    business_term: str | None = Query(default=None, max_length=255),
    owner: str | None = Query(default=None, max_length=255),
    domain: str | None = Query(default=None, max_length=255),
    tag: str | None = Query(default=None, max_length=128),
    classification: str | None = Query(default=None, max_length=128),
    quality_min: int | None = Query(default=None, ge=0, le=100),
    purpose: str = Query(min_length=3, max_length=500),
    limit: int = Query(default=25, ge=1, le=50),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_mcp_delegated_principal),
) -> dict:
    assets, total, facets, index_fresh_at = search_assets(
        db,
        q=q,
        source_id=None,
        asset_type=None,
        lifecycle_status=None,
        owner=owner,
        classification=classification,
        tag=tag,
        freshness_before=None,
        domain=domain,
        business_term=business_term,
        quality_min=quality_min,
        limit=limit,
    )
    visible = []
    for asset in assets:
        try:
            visible.append(_asset_packet(db, principal, request, asset, purpose))
        except HTTPException:
            continue
    return {
        "items": visible,
        "total": total,
        "visible_total": len(visible),
        "facets": facets,
        "index_fresh_at": index_fresh_at.isoformat() if index_fresh_at else None,
    }


@router.get("/assets/{asset_id}")
def mcp_get_asset_context(
    asset_id: str,
    request: Request,
    purpose: str = Query(min_length=3, max_length=500),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_mcp_delegated_principal),
) -> dict:
    return _asset_packet(db, principal, request, get_asset_or_404(db, asset_id), purpose)


@router.get("/domains/{domain_id}")
def mcp_get_domain(
    domain_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_mcp_delegated_principal),
) -> dict:
    domain = db.get(GovernanceDomain, domain_id)
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "Domain not found."})
    return {
        "id": domain.id,
        "name": domain.name,
        "description": domain.description,
        "owner": domain.owner,
        "steward": domain.steward,
        "tenant_id": principal.tenant_id,
    }


@router.post("/proposals", response_model=ProposalCreated, status_code=status.HTTP_201_CREATED)
def mcp_create_governance_proposal(
    payload: GovernanceProposalCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_mcp_delegated_principal),
) -> dict:
    if payload.source.channel != "mcp":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "mcp_proposal_source_invalid", "message": "The private MCP proposal endpoint requires source.channel=mcp."},
        )
    proposal = create_proposal(
        db,
        principal,
        payload,
        request_id=_request_id(request),
        host_id=getattr(request.state, "mcp_host_id", None),
    )
    return ProposalCreated(
        **ProposalRead.model_validate(proposal).model_dump(mode="json"),
        inbox_uri=f"/api/v1/governance/inbox?proposal_id={proposal.id}",
    )
