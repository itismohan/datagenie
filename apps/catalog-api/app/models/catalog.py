import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def uuid_str() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class SourceType(str, Enum):
    POSTGRESQL = "postgresql"
    SNOWFLAKE = "snowflake"


class SyncMode(str, Enum):
    INCREMENTAL = "incremental"
    FULL = "full"


class SourceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssetType(str, Enum):
    DATABASE = "database"
    SCHEMA = "schema"
    TABLE = "table"
    VIEW = "view"


class LifecycleStatus(str, Enum):
    UNDER_REVIEW = "under_review"
    CERTIFIED = "certified"
    DEPRECATED = "deprecated"


class ChangeSource(str, Enum):
    DISCOVERY = "discovery"
    CURATION = "curation"


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    source_type: Mapped[SourceType] = mapped_column(SqlEnum(SourceType), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, default=5432, nullable=False)
    database_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    secret_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    include_schemas: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    connection_options: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[SourceStatus] = mapped_column(SqlEnum(SourceStatus), default=SourceStatus.ACTIVE, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    assets: Mapped[list["Asset"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    ingestion_jobs: Mapped[list["IngestionJob"]] = relationship(back_populates="source", cascade="all, delete-orphan")
    sync_state: Mapped["SourceSyncState | None"] = relationship(
        back_populates="source", cascade="all, delete-orphan", uselist=False
    )


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[JobStatus] = mapped_column(SqlEnum(JobStatus), default=JobStatus.QUEUED, index=True, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_of_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requested_sync_mode: Mapped[SyncMode] = mapped_column(
        SqlEnum(SyncMode), default=SyncMode.INCREMENTAL, nullable=False
    )
    effective_sync_mode: Mapped[SyncMode | None] = mapped_column(SqlEnum(SyncMode), nullable=True)
    cursor_before: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    cursor_after: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    connector_strategy: Mapped[str | None] = mapped_column(String(128), nullable=True)
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    discovery_stats: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    source: Mapped[DataSource] = relationship(back_populates="ingestion_jobs")


class SourceSyncState(Base):
    __tablename__ = "source_sync_states"

    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"), primary_key=True)
    cursor: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_successful_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_successful_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_full_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_incremental_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    source: Mapped[DataSource] = relationship(back_populates="sync_state")


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("source_id", "asset_type", "qualified_name", name="uq_assets_source_type_qualified_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id", ondelete="CASCADE"), index=True, nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(SqlEnum(AssetType), index=True, nullable=False)
    qualified_name: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    database_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    schema_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    technical_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    freshness_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    technical_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    classification: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        SqlEnum(LifecycleStatus), default=LifecycleStatus.UNDER_REVIEW, index=True, nullable=False
    )
    curated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    source: Mapped[DataSource] = relationship(back_populates="assets")
    columns: Mapped[list["AssetColumn"]] = relationship(back_populates="asset", cascade="all, delete-orphan")
    metadata_versions: Mapped[list["AssetMetadataVersion"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", order_by="AssetMetadataVersion.created_at.desc()"
    )


class AssetColumn(Base):
    __tablename__ = "asset_columns"
    __table_args__ = (UniqueConstraint("asset_id", "name", name="uq_asset_columns_asset_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ordinal_position: Mapped[int] = mapped_column(Integer, nullable=False)
    data_type: Mapped[str] = mapped_column(String(255), nullable=False)
    is_nullable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    default_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    asset: Mapped[Asset] = relationship(back_populates="columns")


class AssetMetadataVersion(Base):
    __tablename__ = "asset_metadata_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=False)
    change_source: Mapped[ChangeSource] = mapped_column(SqlEnum(ChangeSource), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_fields: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    asset: Mapped[Asset] = relationship(back_populates="metadata_versions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    actor_subject: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    actor_roles: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    action: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    request_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("principal_subject", "idempotency_key", "method", "path", name="uq_idempotency_principal_key_route"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    principal_subject: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class BusinessGlossaryTerm(Base):
    __tablename__ = "business_glossary_terms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
