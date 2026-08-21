from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.models.catalog import AssetType, DataSource, SyncMode


class ConnectorConfigurationError(ValueError):
    """Raised when a source cannot be safely executed."""


@dataclass(frozen=True)
class DiscoveredColumn:
    name: str
    ordinal_position: int
    data_type: str
    is_nullable: bool
    default_value: str | None = None
    technical_description: str | None = None


@dataclass(frozen=True)
class DiscoveredAsset:
    asset_type: AssetType
    qualified_name: str
    name: str
    database_name: str | None
    schema_name: str | None
    technical_description: str | None = None
    technical_metadata: dict = field(default_factory=dict)
    row_count: int | None = None
    freshness_at: datetime | None = None
    columns: tuple[DiscoveredColumn, ...] = ()


@dataclass(frozen=True)
class DiscoveryResult:
    """Normalized output of one connector discovery run."""

    assets: tuple[DiscoveredAsset, ...]
    next_cursor: dict = field(default_factory=dict)
    effective_sync_mode: SyncMode = SyncMode.FULL
    strategy: str = "full_snapshot"
    warnings: tuple[str, ...] = ()
    statistics: dict = field(default_factory=dict)


class MetadataConnector(Protocol):
    """Minimum interface every metadata connector must implement."""

    def validate(self, source: DataSource) -> None:
        """Validate configuration without exposing credentials in the catalog."""

    def discover(
        self, source: DataSource, sync_mode: SyncMode, cursor: dict | None = None
    ) -> DiscoveryResult:
        """Return normalized metadata plus a cursor safe to persist after success."""

    def capabilities(self) -> dict[str, bool]:
        """Advertise supported actions for future connector management UI."""
