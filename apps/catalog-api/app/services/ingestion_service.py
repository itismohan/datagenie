from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.connectors.base import DiscoveredAsset, DiscoveryResult, MetadataConnector
from app.connectors.postgresql import PostgreSQLConnector
from app.connectors.snowflake import SnowflakeConnector
from app.models.catalog import (
    Asset,
    AssetColumn,
    AssetMetadataVersion,
    ChangeSource,
    DataSource,
    IngestionJob,
    JobStatus,
    SourceStatus,
    SourceSyncState,
    SourceType,
    SyncMode,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_connector(source: DataSource) -> MetadataConnector:
    connectors: dict[SourceType, MetadataConnector] = {
        SourceType.POSTGRESQL: PostgreSQLConnector(),
        SourceType.SNOWFLAKE: SnowflakeConnector(),
    }
    try:
        return connectors[source.source_type]
    except KeyError as exc:
        raise ValueError(f"No connector is registered for source type {source.source_type.value}.") from exc


def _public_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _discovered_asset_fields(discovered: DiscoveredAsset) -> dict[str, Any]:
    return {
        "asset_type": discovered.asset_type,
        "qualified_name": discovered.qualified_name,
        "name": discovered.name,
        "database_name": discovered.database_name,
        "schema_name": discovered.schema_name,
        "technical_description": discovered.technical_description,
        "technical_metadata": discovered.technical_metadata,
        "row_count": discovered.row_count,
    }


def _column_snapshot(column: AssetColumn) -> dict[str, Any]:
    return {
        "name": column.name,
        "ordinal_position": column.ordinal_position,
        "data_type": column.data_type,
        "is_nullable": column.is_nullable,
        "default_value": column.default_value,
        "technical_description": column.technical_description,
    }


def _discovered_column_snapshot(column: Any) -> dict[str, Any]:
    return {
        "name": column.name,
        "ordinal_position": column.ordinal_position,
        "data_type": column.data_type,
        "is_nullable": column.is_nullable,
        "default_value": column.default_value,
        "technical_description": column.technical_description,
    }


def _sync_columns(asset: Asset, discovered: DiscoveredAsset) -> tuple[bool, dict[str, Any]]:
    existing_by_name = {column.name: column for column in asset.columns}
    incoming_by_name = {column.name: column for column in discovered.columns}
    changes: dict[str, Any] = {}

    for name, incoming in incoming_by_name.items():
        incoming_snapshot = _discovered_column_snapshot(incoming)
        existing = existing_by_name.get(name)
        if existing is None:
            asset.columns.append(AssetColumn(**incoming_snapshot))
            changes.setdefault("created", []).append(incoming_snapshot)
        elif _column_snapshot(existing) != incoming_snapshot:
            before = _column_snapshot(existing)
            for field, value in incoming_snapshot.items():
                setattr(existing, field, value)
            changes.setdefault("updated", []).append({"name": name, "before": before, "after": incoming_snapshot})

    for name, existing in existing_by_name.items():
        if name not in incoming_by_name:
            changes.setdefault("removed", []).append(_column_snapshot(existing))
            asset.columns.remove(existing)

    return bool(changes), changes


def synchronize_discovery(db: Session, source: DataSource, discovered_assets: list[DiscoveredAsset]) -> dict[str, int]:
    """Upsert technical metadata while never changing steward-curated fields."""
    existing_assets = list(
        db.scalars(
            select(Asset)
            .where(Asset.source_id == source.id)
            .options(selectinload(Asset.columns))
        ).unique()
    )
    existing_by_key = {(asset.asset_type, asset.qualified_name): asset for asset in existing_assets}
    stats = {"assets_discovered": len(discovered_assets), "assets_created": 0, "assets_updated": 0, "assets_unchanged": 0, "columns_discovered": 0}

    for discovered in discovered_assets:
        stats["columns_discovered"] += len(discovered.columns)
        key = (discovered.asset_type, discovered.qualified_name)
        existing = existing_by_key.get(key)
        fields = _discovered_asset_fields(discovered)
        if existing is None:
            asset = Asset(
                source_id=source.id,
                **fields,
                freshness_at=discovered.freshness_at or utc_now(),
                last_discovered_at=utc_now(),
            )
            for column in discovered.columns:
                asset.columns.append(AssetColumn(**_discovered_column_snapshot(column)))
            db.add(asset)
            db.flush()
            db.add(
                AssetMetadataVersion(
                    asset_id=asset.id,
                    change_source=ChangeSource.DISCOVERY,
                    actor=f"connector:{source.source_type.value}",
                    changed_fields={"created": {field: _public_value(value) for field, value in fields.items()}},
                )
            )
            stats["assets_created"] += 1
            continue

        technical_changes: dict[str, dict[str, Any]] = {}
        for field, incoming_value in fields.items():
            existing_value = getattr(existing, field)
            if existing_value != incoming_value:
                technical_changes[field] = {"before": _public_value(existing_value), "after": _public_value(incoming_value)}
                setattr(existing, field, incoming_value)
        column_changed, column_changes = _sync_columns(existing, discovered)
        existing.last_discovered_at = utc_now()
        existing.freshness_at = discovered.freshness_at or utc_now()

        if technical_changes or column_changed:
            existing.technical_version += 1
            if column_changes:
                technical_changes["columns"] = column_changes
            db.add(
                AssetMetadataVersion(
                    asset_id=existing.id,
                    change_source=ChangeSource.DISCOVERY,
                    actor=f"connector:{source.source_type.value}",
                    changed_fields=technical_changes,
                )
            )
            stats["assets_updated"] += 1
        else:
            stats["assets_unchanged"] += 1
    return stats


def _get_or_create_sync_state(db: Session, source_id: str) -> SourceSyncState:
    sync_state = db.get(SourceSyncState, source_id)
    if sync_state is None:
        sync_state = SourceSyncState(source_id=source_id, cursor={})
        db.add(sync_state)
        db.flush()
    return sync_state


def _apply_successful_discovery(
    db: Session, source: DataSource, job: IngestionJob, result: DiscoveryResult
) -> None:
    stats = synchronize_discovery(db, source, list(result.assets))
    stats.update(result.statistics)
    job.discovery_stats = stats
    job.effective_sync_mode = result.effective_sync_mode
    job.connector_strategy = result.strategy
    job.warnings = list(result.warnings)
    job.cursor_after = dict(result.next_cursor)

    sync_state = _get_or_create_sync_state(db, source.id)
    sync_state.cursor = dict(result.next_cursor)
    sync_state.last_successful_job_id = job.id
    sync_state.last_successful_at = utc_now()
    if result.effective_sync_mode == SyncMode.FULL:
        sync_state.last_full_sync_at = sync_state.last_successful_at
    else:
        sync_state.last_incremental_sync_at = sync_state.last_successful_at

    source.status = SourceStatus.ACTIVE
    source.last_synced_at = sync_state.last_successful_at
    job.status = JobStatus.SUCCEEDED
    job.completed_at = utc_now()


def run_ingestion_job(db: Session, job_id: str) -> IngestionJob:
    job = db.get(IngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion job not found.")
    if job.status == JobStatus.CANCELLED or job.cancel_requested:
        job.status = JobStatus.CANCELLED
        job.completed_at = utc_now()
        db.commit()
        db.refresh(job)
        return job

    source = db.get(DataSource, job.source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found for ingestion job.")

    sync_state = _get_or_create_sync_state(db, source.id)
    job.cursor_before = dict(sync_state.cursor)
    job.status = JobStatus.RUNNING
    job.attempt_count += 1
    job.started_at = utc_now()
    job.error_message = None
    job.warnings = []
    db.commit()

    try:
        connector = get_connector(source)
        connector.validate(source)
        result = connector.discover(source, job.requested_sync_mode, job.cursor_before)
        db.refresh(job)
        if job.cancel_requested:
            job.status = JobStatus.CANCELLED
            job.completed_at = utc_now()
            db.commit()
            db.refresh(job)
            return job

        _apply_successful_discovery(db, source, job, result)
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(IngestionJob, job_id)
        source = db.get(DataSource, source.id)
        if job:
            job.status = JobStatus.FAILED
            job.completed_at = utc_now()
            job.error_message = f"{type(exc).__name__}: {str(exc)[:500]}"
        if source:
            source.status = SourceStatus.ERROR
        db.commit()
    db.refresh(job)
    return job
