from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.tenant import tenant_context
from app.db.session import TenantSession
from app.models.catalog import Base, DataSource, SourceType


def make_db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return TenantSession(bind=engine)


def source(name: str, tenant_id: str | None = None) -> DataSource:
    return DataSource(
        name=name,
        source_type=SourceType.POSTGRESQL,
        host="warehouse.internal",
        database_name="analytics",
        username="catalog_reader",
        secret_ref="env://WAREHOUSE_PASSWORD",
        tenant_id=tenant_id,
    )


def test_tenant_context_filters_reads_and_prevents_forged_write_scope():
    db = make_db()
    with tenant_context("tenant-finance"):
        finance_source = source("finance-warehouse", tenant_id="tenant-forged")
        db.add(finance_source)
        db.commit()
        assert finance_source.tenant_id == "tenant-finance"

    with tenant_context("tenant-sales"):
        sales_source = source("sales-warehouse")
        db.add(sales_source)
        db.commit()
        assert sales_source.tenant_id == "tenant-sales"
        assert [item.name for item in db.scalars(select(DataSource)).all()] == ["sales-warehouse"]
        assert db.get(DataSource, finance_source.id) is None

    with tenant_context("tenant-finance"):
        assert [item.name for item in db.scalars(select(DataSource)).all()] == ["finance-warehouse"]
        assert db.get(DataSource, sales_source.id) is None


def test_maintenance_query_requires_an_explicit_all_tenants_bypass():
    db = make_db()
    with tenant_context("tenant-one"):
        db.add(source("one"))
        db.commit()
    with tenant_context("tenant-two"):
        db.add(source("two"))
        db.commit()
        scoped_names = [item.name for item in db.scalars(select(DataSource)).all()]
        all_names = [item.name for item in db.scalars(select(DataSource).execution_options(include_all_tenants=True)).all()]

    assert scoped_names == ["two"]
    assert set(all_names) == {"one", "two"}


def test_staging_tokens_require_a_tenant_claim():
    from datetime import datetime, timedelta, timezone

    import jwt
    import pytest
    from fastapi import HTTPException

    from app.core.config import Settings
    from app.core.security import _decode_principal

    secret = "test-jwt-secret-that-is-longer-than-thirty-two-characters"
    settings = Settings(
        environment="staging",
        database_url="postgresql+psycopg://catalog:password@db.example/datagenie",
        auth_enabled=True,
        auth_jwt_secret=secret,
        rate_limit_enabled=True,
        rate_limit_redis_url="redis://redis.example:6379/1",
        connector_redis_url="redis://redis.example:6379/2",
        error_tracking_dsn="https://public@example.invalid/1",
        webhook_allowed_hosts="hooks.example.invalid",
    )
    missing_tenant = jwt.encode(
        {"sub": "analyst@example.com", "roles": ["analyst"], "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException, match="tenant_id"):
        _decode_principal(missing_tenant, settings)

    accepted = jwt.encode(
        {"sub": "analyst@example.com", "tenant_id": "tenant-finance", "roles": ["analyst"], "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        secret,
        algorithm="HS256",
    )
    assert _decode_principal(accepted, settings).tenant_id == "tenant-finance"
