from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.connectors.base import DiscoveredAsset, DiscoveredColumn
from app.models.catalog import Asset, AssetMetadataVersion, AssetType, Base, DataSource, SourceType
from app.services.catalog_service import update_asset_curation
from app.schemas.catalog import AssetCurationUpdate, SourceRead
from app.services.ingestion_service import synchronize_discovery


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_discovery_preserves_curated_metadata_and_versions_technical_changes() -> None:
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
    db.add(source)
    db.commit()

    initial = DiscoveredAsset(
        asset_type=AssetType.TABLE,
        qualified_name="analytics.public.orders",
        name="orders",
        database_name="analytics",
        schema_name="public",
        technical_metadata={"engine": "postgresql", "relation_type": "BASE TABLE"},
        freshness_at=datetime.now(timezone.utc),
        columns=(
            DiscoveredColumn("id", 1, "integer", False),
            DiscoveredColumn("amount", 2, "numeric", False),
        ),
    )
    stats = synchronize_discovery(db, source, [initial])
    db.commit()
    assert stats["assets_created"] == 1

    asset = db.scalar(select(Asset).where(Asset.qualified_name == "analytics.public.orders"))
    assert asset is not None
    update_asset_curation(
        db,
        asset,
        AssetCurationUpdate(
            description="Certified order facts.",
            tags=["Finance", "Orders"],
            owner="finance-data",
            classification="internal",
            lifecycle_status="certified",
            actor="steward@example.com",
        ),
    )

    refreshed = DiscoveredAsset(
        asset_type=AssetType.TABLE,
        qualified_name="analytics.public.orders",
        name="orders",
        database_name="analytics",
        schema_name="public",
        technical_metadata={"engine": "postgresql", "relation_type": "BASE TABLE", "has_primary_key": True},
        freshness_at=datetime.now(timezone.utc),
        columns=(
            DiscoveredColumn("id", 1, "integer", False),
            DiscoveredColumn("total_amount", 2, "numeric", False),
        ),
    )
    stats = synchronize_discovery(db, source, [refreshed])
    db.commit()

    asset = db.scalar(select(Asset).where(Asset.id == asset.id))
    assert asset.description == "Certified order facts."
    assert asset.tags == ["finance", "orders"]
    assert asset.owner == "finance-data"
    assert asset.classification == "internal"
    assert asset.lifecycle_status.value == "certified"
    assert asset.technical_version == 2
    assert asset.technical_metadata["has_primary_key"] is True
    assert {column.name for column in asset.columns} == {"id", "total_amount"}
    assert stats["assets_updated"] == 1
    versions = list(db.scalars(select(AssetMetadataVersion).where(AssetMetadataVersion.asset_id == asset.id)))
    assert len(versions) == 3


def test_source_read_schema_excludes_secret_reference() -> None:
    source = DataSource(
        name="local-test-source",
        source_type=SourceType.POSTGRESQL,
        host="localhost",
        port=5432,
        database_name="analytics",
        username="catalog_reader",
        secret_ref="env://DATAGENIE_TEST_PASSWORD",
    )
    db = make_session()
    db.add(source)
    db.commit()
    public_source = SourceRead.model_validate(source).model_dump()
    assert "secret_ref" not in public_source
