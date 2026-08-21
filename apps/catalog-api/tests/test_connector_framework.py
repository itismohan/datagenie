from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.connectors.base import DiscoveredAsset, DiscoveryResult
from app.connectors.snowflake import SnowflakeConnector
from app.models.catalog import AssetType, Base, DataSource, IngestionJob, SourceSyncState, SourceType, SyncMode
from app.services.ingestion_service import _apply_successful_discovery


class FakeCursor:
    def __init__(self):
        self.query = ""
        self.parameters = ()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, parameters=()):
        self.query = query
        self.parameters = parameters

    def fetchall(self):
        if "SCHEMATA" in self.query:
            return [{"SCHEMA_NAME": "ANALYTICS"}]
        if ".TABLES" in self.query:
            return [
                {
                    "schema_name": "ANALYTICS",
                    "relation_name": "ORDERS",
                    "relation_type": "BASE TABLE",
                    "last_altered": datetime(2026, 8, 21, 8, 30, tzinfo=timezone.utc),
                }
            ]
        if ".COLUMNS" in self.query:
            return [
                {
                    "schema_name": "ANALYTICS",
                    "relation_name": "ORDERS",
                    "column_name": "ORDER_ID",
                    "ordinal_position": 1,
                    "data_type": "NUMBER(38,0)",
                    "is_nullable": "NO",
                    "column_default": None,
                    "comment": "Stable order identifier",
                }
            ]
        return []


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def cursor(self, *_args):
        return FakeCursor()


class FakeSnowflakeModule:
    DictCursor = object()

    @staticmethod
    def connect(**_kwargs):
        return FakeConnection()


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_snowflake_connector_uses_last_altered_for_incremental_discovery(monkeypatch) -> None:
    from app.connectors import snowflake as snowflake_module

    monkeypatch.setenv("DATAGENIE_SNOWFLAKE_PASSWORD", "test-password")
    monkeypatch.setattr(snowflake_module, "snowflake_connector", FakeSnowflakeModule)
    source = DataSource(
        name="snowflake-finance",
        source_type=SourceType.SNOWFLAKE,
        host="xy12345.eu-west-1.aws",
        port=443,
        database_name="RAW",
        username="CATALOG_READER",
        secret_ref="env://DATAGENIE_SNOWFLAKE_PASSWORD",
        connection_options={"warehouse": "CATALOG_WH", "role": "CATALOG_ROLE"},
    )
    previous_watermark = datetime(2026, 8, 21, 8, 0, tzinfo=timezone.utc)

    result = SnowflakeConnector().discover(
        source,
        SyncMode.INCREMENTAL,
        {"last_successful_watermark": previous_watermark.isoformat()},
    )

    assert result.effective_sync_mode == SyncMode.INCREMENTAL
    assert result.strategy == "snowflake_last_altered"
    assert result.next_cursor["last_successful_watermark"] == "2026-08-21T08:30:00+00:00"
    table = next(asset for asset in result.assets if asset.asset_type == AssetType.TABLE)
    assert table.qualified_name == "RAW.ANALYTICS.ORDERS"
    assert table.columns[0].technical_description == "Stable order identifier"


def test_successful_incremental_sync_persists_cursor_and_job_history() -> None:
    db = make_session()
    source = DataSource(
        name="warehouse",
        source_type=SourceType.POSTGRESQL,
        host="db.internal",
        port=5432,
        database_name="analytics",
        username="reader",
        secret_ref="env://DATAGENIE_TEST_PASSWORD",
    )
    job = IngestionJob(
        source=source,
        requested_sync_mode=SyncMode.INCREMENTAL,
        cursor_before={"last_successful_watermark": "2026-08-20T00:00:00+00:00"},
    )
    db.add_all([source, job])
    db.commit()

    result = DiscoveryResult(
        assets=(
            DiscoveredAsset(
                asset_type=AssetType.TABLE,
                qualified_name="analytics.public.orders",
                name="orders",
                database_name="analytics",
                schema_name="public",
                technical_metadata={"engine": "postgresql"},
            ),
        ),
        next_cursor={"catalog_observed_at": "2026-08-21T10:00:00+00:00"},
        effective_sync_mode=SyncMode.INCREMENTAL,
        strategy="postgresql_fingerprint_snapshot",
        warnings=("fingerprint snapshot",),
        statistics={"relations_scanned": 1},
    )

    _apply_successful_discovery(db, source, job, result)
    db.commit()
    sync_state = db.get(SourceSyncState, source.id)

    assert job.status.value == "succeeded"
    assert job.effective_sync_mode == SyncMode.INCREMENTAL
    assert job.cursor_after == {"catalog_observed_at": "2026-08-21T10:00:00+00:00"}
    assert job.connector_strategy == "postgresql_fingerprint_snapshot"
    assert job.warnings == ["fingerprint snapshot"]
    assert sync_state.cursor == job.cursor_after
    assert sync_state.last_successful_job_id == job.id
    assert sync_state.last_incremental_sync_at is not None
    assert source.last_synced_at is not None
