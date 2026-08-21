# Catalog MVP Contract

## Scope

This increment implements the durable core of the Catalog MVP. It supports registering a PostgreSQL source, recording ingestion jobs, synchronizing discovered databases, schemas, tables, views, and columns, searching assets, and applying steward-curated metadata without later discovery overwriting it.

## Domain model

| Entity | Purpose | Stable identity |
|---|---|---|
| `DataSource` | A registered data platform connection and its operational state. Credentials are represented only by an external secret reference. | UUID `id` |
| `IngestionJob` | An auditable request to discover metadata from a source. Captures status, timing, attempt count, error, and discovery statistics. | UUID `id` |
| `Asset` | A discovered database, schema, table, or view. Contains harvested technical metadata and steward-curated fields. | UUID `id`; natural identity is `source_id + asset_type + qualified_name` |
| `AssetColumn` | A column discovered beneath a table or view. | UUID `id`; natural identity is `asset_id + name` |
| `AssetMetadataVersion` | A before/after audit record for curator updates and discovery changes. | UUID `id` |

`Asset` deliberately separates fields owned by discovery (`qualified_name`, database/schema location, technical description, data type metadata, discovery timestamps) from fields owned by data stewards (`description`, tags, owner, classification, lifecycle status). Harvesting updates only discovered fields. Curated fields change only through the catalog API.

## Initial API surface

| Route | Responsibility |
|---|---|
| `POST /api/v1/sources` | Register a PostgreSQL source using a secret reference rather than a raw password. |
| `GET /api/v1/sources` / `GET /api/v1/sources/{id}` | List or inspect sources and their most recent synchronization state. |
| `POST /api/v1/sources/{id}/ingestion-jobs` | Create and execute a discovery job. The service is structured for a later worker queue; this increment executes in-process. |
| `GET /api/v1/ingestion-jobs` / `GET /api/v1/ingestion-jobs/{id}` | Inspect job history, status, statistics, and errors. |
| `GET /api/v1/assets` | Search and filter assets by text, source, type, lifecycle status, owner, classification, tag, or freshness. |
| `GET /api/v1/assets/{id}` | Inspect technical and curated metadata, columns, and recent version history. |
| `PATCH /api/v1/assets/{id}` | Update curated metadata without allowing a steward to corrupt harvested identity fields. |

## Operational contract

The PostgreSQL connector validates a source configuration before a job begins, reads catalog metadata from `information_schema`, normalizes the results into a connector-independent discovery contract, and reports failures on the job rather than losing them in a request log. The synchronization service is idempotent for an unchanged discovery snapshot and increments `technical_version` only when harvested technical metadata changes.

This MVP intentionally omits background workers, secret-store integration, authentication, row-level preview, profiling execution, and distributed retry scheduling. The model includes `attempt_count`, `retry_of_job_id`, `cancel_requested`, and `secret_ref` so those production capabilities can be added without breaking the resource contract.
