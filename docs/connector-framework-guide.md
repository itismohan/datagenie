# DataGenie Connector Framework Guide

## Supported connectors

The Catalog API now supports PostgreSQL and Snowflake through one normalized discovery and job-execution interface. Both connectors validate externally stored credentials, discover databases, schemas, tables, views, and columns, and return the same catalog asset contract. Connector capabilities are available from `GET /api/v1/sources/{source_id}/capabilities`.

| Connector | Credential reference | Incremental behavior | Default port |
|---|---|---|---:|
| PostgreSQL | `env://DATAGENIE_POSTGRES_SOURCE_PASSWORD` | Re-reads metadata and applies only content changes to the catalog | 5432 |
| Snowflake | `env://DATAGENIE_SNOWFLAKE_SOURCE_PASSWORD` | Filters changed relations through the source `LAST_ALTERED` watermark, with a five-minute overlap window | 443 |

Snowflake discovery uses the official Python connector’s standard connection and cursor interface, and queries database-scoped `INFORMATION_SCHEMA` views for metadata. [1]

## Register a PostgreSQL source

```bash
export DATAGENIE_ORDERS_PASSWORD='stored-in-your-deployment-secret-provider'

curl -X POST http://localhost:8000/api/v1/sources/ \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Idempotency-Key: orders-source-001' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "orders-postgres",
    "source_type": "postgresql",
    "host": "orders.internal",
    "database_name": "orders",
    "username": "catalog_reader",
    "secret_ref": "env://DATAGENIE_ORDERS_PASSWORD",
    "include_schemas": ["public", "analytics"]
  }'
```

## Register a Snowflake source

The `host` field is the Snowflake account identifier, not an HTTPS URL. The `connection_options` field accepts non-secret connection settings; use it for a warehouse, role, and an approved connector authenticator. DataGenie never returns the credential reference in its public source response.

```bash
export DATAGENIE_SNOWFLAKE_PASSWORD='stored-in-your-deployment-secret-provider'

curl -X POST http://localhost:8000/api/v1/sources/ \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Idempotency-Key: finance-snowflake-001' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "finance-snowflake",
    "source_type": "snowflake",
    "host": "xy12345.eu-west-1.aws",
    "database_name": "RAW",
    "username": "CATALOG_READER",
    "secret_ref": "env://DATAGENIE_SNOWFLAKE_PASSWORD",
    "include_schemas": ["ANALYTICS"],
    "connection_options": {
      "warehouse": "CATALOG_WH",
      "role": "CATALOG_READER"
    }
  }'
```

The Snowflake service account needs permission to use the selected warehouse and role and to read the configured database’s metadata. Authentication, least privilege, and network policies remain Snowflake administration responsibilities.

## Run and inspect synchronization jobs

An incremental run is the default. On the first Snowflake run, DataGenie performs a full discovery because no prior source watermark exists. A subsequent Snowflake incremental run uses the stored `LAST_ALTERED` cursor. PostgreSQL reports its strategy as `postgresql_fingerprint_snapshot`, which means it scans metadata but does not rewrite unchanged catalog rows or technical versions.

```bash
# Default incremental run
curl -X POST http://localhost:8000/api/v1/sources/SOURCE_ID/ingestion-jobs \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{}'

# Explicit full scan
curl -X POST http://localhost:8000/api/v1/sources/SOURCE_ID/ingestion-jobs \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"sync_mode":"full"}'

# Current persisted source cursor and last successful job
curl -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  http://localhost:8000/api/v1/sources/SOURCE_ID/sync-state

# Job history with cursor boundaries, strategy, warnings, and outcome
curl -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  'http://localhost:8000/api/v1/ingestion-jobs?source_id=SOURCE_ID'
```

A successful job advances the source cursor only after catalog synchronization commits. Failed and cancelled jobs retain their original cursor boundary and do not advance the source state. The API supports a retry route for failed or cancelled jobs:

```bash
curl -X POST http://localhost:8000/api/v1/ingestion-jobs/JOB_ID/retry \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

## Operational behavior

| Situation | Result |
|---|---|
| Snowflake run with no prior cursor | Full discovery is executed and the first `LAST_ALTERED` watermark is stored |
| Snowflake incremental run | Relations changed since the watermark plus the five-minute overlap are discovered; duplicate overlap results reconcile without new versions when unchanged |
| PostgreSQL incremental run | A portable metadata snapshot is compared against the catalog; only changed relations and columns are written |
| Delta omits an existing asset | The asset is retained; missing asset deprecation requires an explicit full-reconciliation policy |
| Job fails or is cancelled | Job history records the outcome and error; source cursor remains unchanged |
| Job is retried | A new job stores `retry_of_job_id` and uses the last committed source cursor |

## Verification boundary

The implementation has unit coverage for Snowflake normalized discovery, Snowflake cursor advancement, PostgreSQL fingerprint-based state persistence, source cursor state, and migration application. It does not connect to a live Snowflake tenant in automated tests; before enabling a production source, run a least-privilege connectivity validation and an initial full discovery in staging.

## References

[1] [Snowflake Connector for Python — Snowflake Documentation](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector)
