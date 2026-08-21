from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.catalog import Asset, AssetColumn, AssetType, Base, DataSource, LifecycleStatus, SourceType
from app.services.catalog_service import search_assets
from app.services.search_index_service import reindex_assets


def make_db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_reindex_creates_persistent_documents_used_for_search_facets_and_freshness():
    db = make_db()
    source = DataSource(
        name="analytics-warehouse",
        source_type=SourceType.POSTGRESQL,
        host="warehouse.internal",
        database_name="analytics",
        username="catalog_reader",
        secret_ref="env://WAREHOUSE_PASSWORD",
    )
    asset = Asset(
        source=source,
        asset_type=AssetType.TABLE,
        qualified_name="analytics.finance.invoice_payments",
        name="invoice_payments",
        description="Certified finance payment records.",
        owner="finance-owner@example.com",
        tags=["finance", "payments"],
        classification="confidential",
        lifecycle_status=LifecycleStatus.CERTIFIED,
    )
    asset.columns = [AssetColumn(name="invoice_id", ordinal_position=1, data_type="uuid", is_nullable=False)]
    db.add(asset)
    db.commit()

    assert reindex_assets(db) == 1
    db.commit()

    items, total, facets, index_fresh_at = search_assets(
        db,
        q="invoice_id",
        source_id=None,
        asset_type=None,
        lifecycle_status=None,
        owner=None,
        classification=None,
        tag=None,
        freshness_before=None,
    )

    assert total == 1
    assert items[0].id == asset.id
    assert facets["lifecycle_status"] == {"certified": 1}
    assert facets["tag"] == {"finance": 1, "payments": 1}
    assert index_fresh_at is not None
