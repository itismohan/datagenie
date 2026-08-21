# Catalog MVP Implementation Guide

## Delivered capabilities

The catalog service now persists catalog data with SQLAlchemy and supports PostgreSQL sources, ingestion-job history, connector capabilities, safe credential references, normalized metadata discovery, asset search, and curation-safe stewardship updates.

The discovery process creates or updates database, schema, table, view, and column records from PostgreSQL's `information_schema`. Data stewards can independently set descriptions, tags, owners, classifications, and lifecycle status. A subsequent discovery run updates only technical fields and column structure; it does not replace steward-managed values.

## Run locally

```bash
cd apps/catalog-api
pip3 install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://catalog_user:catalog_password@localhost:5432/datagenie_catalog'
uvicorn app.main:app --reload
```

For a quick local evaluation, omit `DATABASE_URL`; the service uses `sqlite:///./datagenie_catalog.db`. PostgreSQL is required for production deployments.

Apply the `20260821_01` Alembic revision before production startup. The service also creates its schema on startup for local development and tests; production deployment should rely on the migration rather than the startup convenience path.

## Register and validate a source

The catalog does not accept or store raw passwords. Store a password in a deployment secret and expose it to the service as an environment variable. Register its reference with the `env://` convention.

```bash
export DATAGENIE_ORDERS_PASSWORD='replace-with-managed-secret-value'

curl -X POST http://localhost:8000/api/v1/sources/ \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "orders-warehouse",
    "source_type": "postgresql",
    "host": "warehouse.internal",
    "port": 5432,
    "database_name": "analytics",
    "username": "catalog_reader",
    "secret_ref": "env://DATAGENIE_ORDERS_PASSWORD",
    "include_schemas": ["public", "analytics"]
  }'
```

```bash
curl http://localhost:8000/api/v1/sources/SOURCE_ID/capabilities
curl -X POST http://localhost:8000/api/v1/sources/SOURCE_ID/validate
curl -X POST http://localhost:8000/api/v1/sources/SOURCE_ID/ingestion-jobs
```

The initial implementation runs the ingestion request synchronously while keeping job state in the database. This makes job execution observable now and provides the stable public resource contract needed to move execution to a queue worker later.

## Search and curate assets

```bash
curl 'http://localhost:8000/api/v1/assets/?q=orders&classification=internal&limit=25'

curl -X PATCH http://localhost:8000/api/v1/assets/ASSET_ID \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "Certified order facts for finance reporting.",
    "tags": ["finance", "orders"],
    "owner": "finance-data",
    "classification": "internal",
    "lifecycle_status": "certified",
    "actor": "steward@example.com"
  }'
```

All curation and discovery changes create `AssetMetadataVersion` records. The full OpenAPI specification is available at `/openapi.json` and interactive documentation at `/docs`.

## Validation performed

The repository includes a focused test suite at `apps/catalog-api/tests/test_catalog_workflow.py`. It confirms that discovery preserves steward-owned metadata, increments technical versioning when technical metadata changes, reconciles changed columns, writes metadata history, and omits credential references from public source responses.

```bash
cd apps/catalog-api
pytest -q
```

## Next production increment

The remaining gap is asynchronous execution and enterprise controls. The recommended next increment is to introduce a queue worker and managed secret-store adapter, then add authentication, authorization, connector-level audit events, scheduled runs, retry backoff, and dead-letter handling. These additions can reuse the delivered `DataSource`, `IngestionJob`, and connector contracts without breaking API clients.
