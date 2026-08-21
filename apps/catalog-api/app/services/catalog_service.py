from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog import (
    Asset,
    AssetMetadataVersion,
    ChangeSource,
    DataSource,
    IngestionJob,
    JobStatus,
    SourceSyncState,
    SourceType,
    SyncMode,
)
from app.schemas.catalog import AssetCurationUpdate, SourceCreate


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
        db.commit()
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
    limit: int,
    offset: int,
) -> tuple[list[Asset], int]:
    filters = []
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(or_(Asset.name.ilike(pattern), Asset.qualified_name.ilike(pattern), Asset.description.ilike(pattern), Asset.technical_description.ilike(pattern)))
    if source_id:
        filters.append(Asset.source_id == source_id)
    if asset_type:
        filters.append(Asset.asset_type == asset_type)
    if lifecycle_status:
        filters.append(Asset.lifecycle_status == lifecycle_status)
    if owner:
        filters.append(Asset.owner == owner)
    if classification:
        filters.append(Asset.classification == classification)
    if tag:
        # JSON containment differs between PostgreSQL and SQLite. Filtering in
        # memory preserves consistent MVP behaviour across both supported dev stores.
        filters.append(Asset.tags.is_not(None))
    if freshness_before:
        filters.append(or_(Asset.freshness_at.is_(None), Asset.freshness_at < freshness_before))

    base: Select = select(Asset).where(*filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    assets = list(
        db.scalars(
            base.options(selectinload(Asset.columns), selectinload(Asset.metadata_versions))
            .order_by(Asset.updated_at.desc(), Asset.name.asc())
            .offset(offset)
            .limit(limit)
        ).unique()
    )
    if tag:
        normalized = tag.strip().lower()
        assets = [asset for asset in assets if normalized in (asset.tags or [])]
        total = len(assets)
    return assets, total
