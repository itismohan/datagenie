from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import ROLE_DATA_STEWARD, ROLE_PLATFORM_ADMIN, Principal, require_roles
from app.db.session import get_db
from app.models.catalog import Asset, SearchDocument
from app.services.audit_service import record_audit_event
from app.services.search_index_service import reindex_assets


router = APIRouter()
index_operator = require_roles(ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD)


@router.get("/status")
def index_status(
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(index_operator),
) -> dict[str, object]:
    document_count = db.scalar(select(func.count()).select_from(SearchDocument)) or 0
    stale_document_count = db.scalar(
        select(func.count())
        .select_from(SearchDocument)
        .join(Asset, Asset.id == SearchDocument.asset_id)
        .where(SearchDocument.source_updated_at < Asset.updated_at)
    ) or 0
    oldest_indexed_at = db.scalar(select(func.min(SearchDocument.indexed_at)))
    record_audit_event(
        db,
        principal=principal,
        action="search_index.status",
        resource_type="search_index",
        resource_id=None,
        outcome="success",
        request_id=getattr(request.state, "request_id", "unknown"),
        metadata={"document_count": document_count, "stale_document_count": stale_document_count},
    )
    db.commit()
    return {
        "document_count": document_count,
        "stale_document_count": stale_document_count,
        "oldest_indexed_at": oldest_indexed_at,
        "fresh": stale_document_count == 0,
    }


@router.post("/reindex", status_code=status.HTTP_202_ACCEPTED)
def reindex_current_tenant(
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(index_operator),
) -> dict[str, int]:
    """Rebuild only the active tenant's index; invoke during controlled maintenance windows."""
    count = reindex_assets(db)
    record_audit_event(
        db,
        principal=principal,
        action="search_index.reindex",
        resource_type="search_index",
        resource_id=None,
        outcome="success",
        request_id=getattr(request.state, "request_id", "unknown"),
        metadata={"indexed_asset_count": count},
    )
    db.commit()
    return {"indexed_asset_count": count}
