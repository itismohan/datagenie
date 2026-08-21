# PostgreSQL and Snowflake Connector Framework Contract

## Connector-independent discovery

Each connector implements a single normalized discovery interface. It validates a `DataSource`, declares capabilities, receives a requested sync mode plus the last successful source cursor, and returns a `DiscoveryResult`. The result contains normalized assets and columns, the cursor safe to persist after a successful run, the effective sync mode, strategy metadata, and non-fatal warnings.

| Concept | Contract |
|---|---|
| `DataSource` | Stores shared identity fields plus non-secret `connection_options`; credentials remain a `secret_ref` only |
| `DiscoveryResult` | Contains discovered assets, sync cursor, effective mode, connector statistics, and warnings |
| `sync_mode` | `incremental` by default; callers can request `full` explicitly |
| `SourceSyncState` | One durable state record per source with cursor, last successful job, and last successful full or incremental sync times |
| `IngestionJob` | Immutable operational history of requested/effective mode, cursor boundaries, connector statistics, and outcome |

## Source configuration

PostgreSQL uses `host`, `port`, `database_name`, `username`, `secret_ref`, and optional `include_schemas`. Snowflake uses the same shared fields with `host` interpreted as the account identifier and `connection_options` for non-secret values such as `warehouse`, `role`, and optional `authenticator`. `database_name` remains the catalog database for both platforms.

Only `env://NAME` secret references are accepted in this increment. PostgreSQL resolves the named value as a password. Snowflake resolves it as a password unless `connection_options.authenticator` describes a supported external authentication mechanism. Raw passwords, private keys, tokens, and connection strings are not saved in DataGenie.

## Incremental behavior

| Connector | Incremental strategy | Reliability behavior |
|---|---|---|
| PostgreSQL | Full metadata read with content-fingerprint synchronization | PostgreSQL does not expose a portable, universal DDL-change timestamp through `information_schema`; therefore the connector reads the catalog snapshot but writes only changed metadata, columns, and versions |
| Snowflake | Source-side filtering by object `LAST_ALTERED` after the stored cursor | A full scan is used on the first run or when explicitly requested. Changed relations are then expanded to their current column metadata. A safety overlap window is recorded to avoid boundary loss. |

Incremental runs never delete a catalog asset merely because it is absent from a delta. Deletion or deprecation needs a dedicated full-reconciliation policy, preventing a transient incomplete delta or source permission change from erasing a catalog record. Changed columns on a discovered relation are reconciled because their current relation metadata is authoritative.

## Job history and cursor updates

A job transitions from `queued` to `running`, then to `succeeded`, `failed`, or `cancelled`. It records the requested and effective sync mode, cursor before and after, connector strategy, discovered counts, errors, retry relationship, cancellation request, and timestamps. A source cursor advances only after the synchronization transaction succeeds. Failed or cancelled jobs preserve the previous cursor and remain visible in job history.

## Backward compatibility

Existing `POST /api/v1/sources/{id}/ingestion-jobs` requests continue to work. They default to `incremental`; existing PostgreSQL sources transparently use fingerprint-based incremental sync. Clients can submit `{"sync_mode": "full"}` to force a full connector scan. The source capability endpoint advertises whether a connector supports source-side incremental discovery or fingerprint-based incremental synchronization.
