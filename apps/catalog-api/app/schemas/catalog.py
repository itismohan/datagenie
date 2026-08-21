from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.catalog import AssetType, ChangeSource, JobStatus, LifecycleStatus, SourceStatus, SourceType, SyncMode


class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    source_type: SourceType = SourceType.POSTGRESQL
    host: str = Field(min_length=1, max_length=255, description="PostgreSQL host or Snowflake account identifier.")
    port: int | None = Field(default=None, ge=1, le=65535)
    database_name: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=255)
    secret_ref: str = Field(
        min_length=3,
        max_length=1024,
        description="A reference to a credential held outside the catalog database; never submit raw passwords.",
    )
    include_schemas: list[str] = Field(default_factory=list)
    connection_options: dict[str, str] = Field(
        default_factory=dict,
        description="Non-secret connector options such as Snowflake warehouse, role, or authenticator.",
    )

    @field_validator("include_schemas")
    @classmethod
    def normalize_schemas(cls, value: list[str]) -> list[str]:
        return sorted({schema.strip() for schema in value if schema.strip()})


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    source_type: SourceType
    host: str
    port: int
    database_name: str
    username: str
    include_schemas: list[str]
    connection_options: dict[str, str]
    status: SourceStatus
    last_synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IngestionRequest(BaseModel):
    sync_mode: SyncMode = SyncMode.INCREMENTAL


class IngestionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    status: JobStatus
    attempt_count: int
    retry_of_job_id: str | None
    cancel_requested: bool
    requested_sync_mode: SyncMode
    effective_sync_mode: SyncMode | None
    cursor_before: dict[str, Any]
    cursor_after: dict[str, Any]
    connector_strategy: str | None
    warnings: list[str]
    discovery_stats: dict[str, Any]
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class AssetColumnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    ordinal_position: int
    data_type: str
    is_nullable: bool
    default_value: str | None
    technical_description: str | None


class AssetMetadataVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    change_source: ChangeSource
    actor: str
    changed_fields: dict[str, Any]
    created_at: datetime


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    asset_type: AssetType
    qualified_name: str
    name: str
    database_name: str | None
    schema_name: str | None
    technical_description: str | None
    technical_metadata: dict[str, Any]
    row_count: int | None
    last_discovered_at: datetime
    freshness_at: datetime | None
    technical_version: int
    description: str | None
    tags: list[str]
    owner: str | None
    classification: str | None
    domain_id: str | None
    quality_score: int | None
    quality_explainable_at: datetime | None
    lifecycle_status: LifecycleStatus
    discovery_score: int | None = None
    curated_at: datetime | None
    created_at: datetime
    updated_at: datetime
    columns: list[AssetColumnRead] = Field(default_factory=list)
    metadata_versions: list[AssetMetadataVersionRead] = Field(default_factory=list)


class AssetCurationUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=10000)
    tags: list[str] | None = Field(default=None, max_length=50)
    owner: str | None = Field(default=None, max_length=255)
    classification: str | None = Field(default=None, max_length=100)
    domain_id: str | None = None
    lifecycle_status: LifecycleStatus | None = None
    actor: str = Field(default="catalog-steward", min_length=1, max_length=255)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        return sorted({tag.strip().lower() for tag in value if tag.strip()})


class AssetSearchResponse(BaseModel):
    items: list[AssetRead]
    total: int


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_subject: str | None
    actor_roles: list[str]
    action: str
    resource_type: str
    resource_id: str | None
    outcome: str
    request_id: str
    metadata_json: dict[str, Any]
    created_at: datetime


class AuditEventSearchResponse(BaseModel):
    items: list[AuditEventRead]
    total: int


class SourceSyncStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: str
    cursor: dict[str, Any]
    last_successful_job_id: str | None
    last_successful_at: datetime | None
    last_full_sync_at: datetime | None
    last_incremental_sync_at: datetime | None
    updated_at: datetime | None = None
