from collections import Counter
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Asset, SearchDocument, utc_now


def _facet_payload(asset: Asset) -> dict[str, object]:
    return {
        "asset_type": asset.asset_type.value,
        "lifecycle_status": asset.lifecycle_status.value,
        "owner": asset.owner,
        "classification": asset.classification,
        "domain_id": asset.domain_id,
        "tags": list(asset.tags or []),
        "quality_bucket": "explainable" if asset.quality_explainable_at else "unexplained",
    }


def _document_text(asset: Asset) -> str:
    values = [
        asset.name,
        asset.qualified_name,
        asset.description or "",
        asset.technical_description or "",
        asset.owner or "",
        asset.classification or "",
        " ".join(asset.tags or []),
        " ".join(column.name for column in asset.columns),
    ]
    return " ".join(values).lower()


def index_asset(db: Session, asset: Asset) -> SearchDocument:
    """Upsert a tenant-scoped document in the same transaction as metadata changes."""
    document = db.scalar(select(SearchDocument).where(SearchDocument.asset_id == asset.id))
    if document is None:
        document = SearchDocument(asset_id=asset.id, document="", facets={}, source_updated_at=asset.updated_at)
        db.add(document)
    document.document = _document_text(asset)
    document.facets = _facet_payload(asset)
    document.source_updated_at = asset.updated_at
    document.indexed_at = utc_now()
    return document


def reindex_assets(db: Session) -> int:
    assets = list(db.scalars(select(Asset)))
    for asset in assets:
        index_asset(db, asset)
    db.flush()
    return len(assets)


def facet_counts(documents: list[SearchDocument]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = {
        "asset_type": Counter(),
        "lifecycle_status": Counter(),
        "owner": Counter(),
        "classification": Counter(),
        "domain_id": Counter(),
        "tag": Counter(),
        "quality_bucket": Counter(),
    }
    for document in documents:
        facets = document.facets or {}
        for key in ("asset_type", "lifecycle_status", "owner", "classification", "domain_id", "quality_bucket"):
            value = facets.get(key)
            if value:
                counts[key][str(value)] += 1
        for tag in facets.get("tags", []):
            counts["tag"][str(tag)] += 1
    return {key: dict(sorted(values.items())) for key, values in counts.items()}


def index_freshness(documents: list[SearchDocument]) -> datetime | None:
    if not documents:
        return None
    return min(document.indexed_at for document in documents)
