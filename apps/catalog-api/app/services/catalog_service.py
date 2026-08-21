from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog import (
    Asset,
    AssetMetadataVersion,
    BusinessGlossaryTerm,
    GlossaryAssetMapping,
    GlossaryStatus,
    GovernanceDomain,
    ReviewStatus,
    ChangeSource,
    DataSource,
    IngestionJob,
    JobStatus,
    SourceSyncState,
    SourceType,
    SyncMode,
    SearchDocument,
    WebhookEventType,
)
from app.schemas.catalog import AssetCurationUpdate, SourceCreate
from app.services.operations_service import queue_webhook_deliveries
from app.services.search_index_service import facet_counts, index_asset, index_freshness
from app.workers.tasks import enqueue_webhook_delivery


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_source(db: Session, payload: SourceCreate) -> DataSource:
    existing = db.scalar(select(DataSource).where(DataSource.name == payload.name))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A data source with this name already exists.")

    source_data = payload.model_dump()
    if source_data["port"] is None:
        source_data["port"] = 443 if payload.source_type == SourceType.SNOWFLAKE else 5432
    source = DataSource(**source_data)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def get_source_or_404(db: Session, source_id: str) -> DataSource:
    source = db.get(DataSource, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")
    return source


def create_ingestion_job(
    db: Session, source: DataSource, sync_mode: SyncMode = SyncMode.INCREMENTAL
) -> IngestionJob:
    sync_state = db.get(SourceSyncState, source.id)
    job = IngestionJob(
        source_id=source.id,
        status=JobStatus.QUEUED,
        requested_sync_mode=sync_mode,
        cursor_before=dict(sync_state.cursor) if sync_state else {},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job_or_404(db: Session, job_id: str) -> IngestionJob:
    job = db.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found.")
    return job


def get_asset_or_404(db: Session, asset_id: str) -> Asset:
    statement = (
        select(Asset)
        .where(Asset.id == asset_id)
        .options(selectinload(Asset.columns), selectinload(Asset.metadata_versions))
    )
    asset = db.scalar(statement)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    return asset


def update_asset_curation(db: Session, asset: Asset, payload: AssetCurationUpdate) -> Asset:
    updates = payload.model_dump(exclude_unset=True, exclude={"actor"})
    changed_fields: dict[str, dict[str, object]] = {}
    for field, new_value in updates.items():
        old_value = getattr(asset, field)
        if old_value != new_value:
            changed_fields[field] = {"before": old_value.value if hasattr(old_value, "value") else old_value, "after": new_value.value if hasattr(new_value, "value") else new_value}
            setattr(asset, field, new_value)

    if changed_fields:
        asset.curated_at = utc_now()
        db.add(
            AssetMetadataVersion(
                asset_id=asset.id,
                change_source=ChangeSource.CURATION,
                actor=payload.actor,
                changed_fields=changed_fields,
            )
        )
        db.flush()
        index_asset(db, asset)
        deliveries = queue_webhook_deliveries(
            db,
            WebhookEventType.ASSET_UPDATED,
            {"asset_id": asset.id, "changed_fields": changed_fields, "updated_at": asset.updated_at.isoformat()},
        )
        db.commit()
        for delivery in deliveries:
            try:
                enqueue_webhook_delivery(delivery.id, asset.tenant_id)
            except Exception:
                # The durable pending outbox record remains available for an operator replay.
                pass
        db.refresh(asset)
    return get_asset_or_404(db, asset.id)


def search_assets(
    db: Session,
    *,
    q: str | None,
    source_id: str | None,
    asset_type: str | None,
    lifecycle_status: str | None,
    owner: str | None,
    classification: str | None,
    tag: str | None,
    freshness_before: datetime | None,
    domain: str | None = None,
    business_term: str | None = None,
    quality_min: int | None = None,
    explainable_quality_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Asset], int, dict[str, dict[str, int]], datetime | None]:
    filters = []
    q_normalized = q.strip().lower() if q else None
    indexed_document_ids: set[str] | None = None
    term_ids: set[str] = set()
    if business_term or q_normalized:
        term_pattern = f"%{(business_term or q_normalized).strip()}%"
        approved_term_ids = select(BusinessGlossaryTerm.id).where(
            BusinessGlossaryTerm.name.ilike(term_pattern),
            BusinessGlossaryTerm.status == GlossaryStatus.APPROVED,
        )
        term_ids = set(
            db.scalars(
                select(GlossaryAssetMapping.asset_id).where(
                    GlossaryAssetMapping.term_id.in_(approved_term_ids),
                    GlossaryAssetMapping.status == ReviewStatus.APPROVED,
                )
            )
        )
    if q_normalized:
        pattern = f"%{q_normalized}%"
        existing_documents = list(db.scalars(select(SearchDocument)))
        if existing_documents:
            indexed_document_ids = set(
                db.scalars(select(SearchDocument.asset_id).where(SearchDocument.document.ilike(pattern)))
            )
            filters.append(or_(Asset.id.in_(indexed_document_ids), Asset.id.in_(term_ids) if term_ids else False))
        else:
            filters.append(
                or_(
                    Asset.name.ilike(pattern),
                    Asset.qualified_name.ilike(pattern),
                    Asset.description.ilike(pattern),
                    Asset.technical_description.ilike(pattern),
                    Asset.id.in_(term_ids) if term_ids else False,
                )
            )
    elif business_term:
        filters.append(Asset.id.in_(term_ids) if term_ids else False)
    if source_id:
        filters.append(Asset.source_id == source_id)
    if asset_type:
        filters.append(Asset.asset_type == asset_type)
    if lifecycle_status:
        filters.append(Asset.lifecycle_status == lifecycle_status)
    if owner:
        filters.append(Asset.owner == owner)
    if classification:
        filters.append(Asset.classification.ilike(f"%{classification.strip()}%"))
    if domain:
        filters.append(Asset.domain.has(GovernanceDomain.name.ilike(f"%{domain.strip()}%")))
    if tag:
        # JSON containment differs between PostgreSQL and SQLite. Filtering in
        # memory preserves consistent behaviour across supported local stores.
        filters.append(Asset.tags.is_not(None))
    if freshness_before:
        filters.append(or_(Asset.freshness_at.is_(None), Asset.freshness_at < freshness_before))
    if quality_min is not None:
        filters.append(Asset.quality_score >= quality_min)
    if explainable_quality_only:
        filters.append(Asset.quality_explainable_at.is_not(None))

    base: Select = select(Asset).where(*filters)
    assets = list(
        db.scalars(
            base.options(selectinload(Asset.columns), selectinload(Asset.metadata_versions), selectinload(Asset.domain))
            .order_by(Asset.updated_at.desc(), Asset.name.asc())
        ).unique()
    )
    if tag:
        normalized = tag.strip().lower()
        assets = [asset for asset in assets if normalized in (asset.tags or [])]

    def rank(asset: Asset) -> int:
        score = 0
        if q_normalized:
            name = asset.name.lower()
            qualified_name = asset.qualified_name.lower()
            if name == q_normalized or qualified_name == q_normalized:
                score += 100
            elif name.startswith(q_normalized) or qualified_name.startswith(q_normalized):
                score += 70
            elif q_normalized in name or q_normalized in qualified_name:
                score += 45
            elif q_normalized in (asset.description or "").lower() or q_normalized in (asset.technical_description or "").lower():
                score += 20
            if asset.id in term_ids:
                score += 40
        if asset.lifecycle_status.value == "certified":
            score += 25
        if asset.description:
            score += 10
        if asset.owner:
            score += 10
        if asset.quality_score is not None and asset.quality_explainable_at is not None:
            score += 10 + min(asset.quality_score // 20, 5)
        updated_at = asset.updated_at
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        current_time = utc_now()
        if updated_at >= current_time.replace(hour=0, minute=0, second=0, microsecond=0):
            score += 8
        elif updated_at >= current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0):
            score += 4
        return score

    for asset in assets:
        setattr(asset, "discovery_score", rank(asset))
    assets.sort(key=lambda asset: (-getattr(asset, "discovery_score", 0), asset.name.lower()))
    total = len(assets)
    asset_ids = [asset.id for asset in assets]
    documents = list(db.scalars(select(SearchDocument).where(SearchDocument.asset_id.in_(asset_ids)))) if asset_ids else []
    return assets[offset : offset + limit], total, facet_counts(documents), index_freshness(documents)
