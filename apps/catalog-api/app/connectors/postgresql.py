import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.connectors.base import ConnectorConfigurationError, DiscoveredAsset, DiscoveredColumn, DiscoveryResult
from app.models.catalog import AssetType, DataSource, SyncMode


class PostgreSQLConnector:
    """Discover PostgreSQL technical metadata through information_schema.

    The connector resolves an environment-backed reference such as
    ``env://DATAGENIE_SALES_PASSWORD``. The catalog database stores only this
    reference, never the password itself.
    """

    def capabilities(self) -> dict[str, bool]:
        return {
            "configuration_validation": True,
            "metadata_discovery": True,
            "column_discovery": True,
            "incremental_synchronization": True,
            "source_side_incremental_discovery": False,
            "content_fingerprint_incremental": True,
            "profiling": False,
            "cancellation": True,
            "retries": True,
        }

    def validate(self, source: DataSource) -> None:
        if not source.host or not source.database_name or not source.username:
            raise ConnectorConfigurationError("PostgreSQL host, database name, and username are required.")
        if not source.secret_ref.startswith("env://"):
            raise ConnectorConfigurationError(
                "This MVP supports environment-backed references only. Use secret_ref such as env://DATAGENIE_SOURCE_PASSWORD."
            )
        secret_name = source.secret_ref.removeprefix("env://")
        if not secret_name or not os.getenv(secret_name):
            raise ConnectorConfigurationError(f"Credential reference {source.secret_ref} is not available in the runtime environment.")

    def discover(
        self, source: DataSource, sync_mode: SyncMode, cursor: dict | None = None
    ) -> DiscoveryResult:
        self.validate(source)
        password = os.environ[source.secret_ref.removeprefix("env://")]
        now = datetime.now(timezone.utc)
        schemas = source.include_schemas or self._default_schemas(source, password)
        discovered: list[DiscoveredAsset] = [
            DiscoveredAsset(
                asset_type=AssetType.DATABASE,
                qualified_name=source.database_name,
                name=source.database_name,
                database_name=source.database_name,
                schema_name=None,
                technical_metadata={"engine": "postgresql"},
                freshness_at=now,
            )
        ]
        discovered.extend(
            DiscoveredAsset(
                asset_type=AssetType.SCHEMA,
                qualified_name=f"{source.database_name}.{schema}",
                name=schema,
                database_name=source.database_name,
                schema_name=schema,
                technical_metadata={"engine": "postgresql"},
                freshness_at=now,
            )
            for schema in schemas
        )

        columns_by_relation = self._discover_columns(source, password, schemas)
        relation_rows = self._discover_relations(source, password, schemas)
        for relation in relation_rows:
            schema_name = relation["schema_name"]
            relation_name = relation["relation_name"]
            relation_type = AssetType.TABLE if relation["relation_type"] == "BASE TABLE" else AssetType.VIEW
            qualified_name = f"{source.database_name}.{schema_name}.{relation_name}"
            discovered.append(
                DiscoveredAsset(
                    asset_type=relation_type,
                    qualified_name=qualified_name,
                    name=relation_name,
                    database_name=source.database_name,
                    schema_name=schema_name,
                    technical_metadata={"engine": "postgresql", "relation_type": relation["relation_type"]},
                    freshness_at=now,
                    columns=tuple(columns_by_relation[(schema_name, relation_name)]),
                )
            )
        return DiscoveryResult(
            assets=tuple(discovered),
            next_cursor={"catalog_observed_at": now.isoformat(), "strategy": "fingerprint_snapshot"},
            effective_sync_mode=sync_mode,
            strategy="postgresql_fingerprint_snapshot",
            warnings=(
                "PostgreSQL metadata is scanned as a snapshot because information_schema does not expose a portable DDL watermark; only changed catalog records are written.",
            )
            if sync_mode == SyncMode.INCREMENTAL
            else (),
            statistics={"relations_scanned": len(relation_rows), "schemas_scanned": len(schemas)},
        )

    def _connection_kwargs(self, source: DataSource, password: str) -> dict[str, Any]:
        return {
            "host": source.host,
            "port": source.port,
            "dbname": source.database_name,
            "user": source.username,
            "password": password,
            "connect_timeout": 10,
            "row_factory": dict_row,
        }

    def _default_schemas(self, source: DataSource, password: str) -> list[str]:
        query = """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
              AND schema_name NOT LIKE 'pg_toast%'
            ORDER BY schema_name
        """
        with psycopg.connect(**self._connection_kwargs(source, password)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                return [row["schema_name"] for row in cursor.fetchall()]

    def _discover_relations(self, source: DataSource, password: str, schemas: list[str]) -> list[dict[str, Any]]:
        query = """
            SELECT table_schema AS schema_name, table_name AS relation_name, table_type AS relation_type
            FROM information_schema.tables
            WHERE table_schema = ANY(%s)
              AND table_type IN ('BASE TABLE', 'VIEW')
            ORDER BY table_schema, table_name
        """
        with psycopg.connect(**self._connection_kwargs(source, password)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (schemas,))
                return list(cursor.fetchall())

    def _discover_columns(
        self, source: DataSource, password: str, schemas: list[str]
    ) -> dict[tuple[str, str], list[DiscoveredColumn]]:
        query = """
            SELECT table_schema AS schema_name, table_name AS relation_name, column_name,
                   ordinal_position, data_type, udt_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = ANY(%s)
            ORDER BY table_schema, table_name, ordinal_position
        """
        columns: dict[tuple[str, str], list[DiscoveredColumn]] = defaultdict(list)
        with psycopg.connect(**self._connection_kwargs(source, password)) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (schemas,))
                for row in cursor.fetchall():
                    rendered_data_type = row["data_type"]
                    if row["udt_name"] and row["udt_name"] != row["data_type"]:
                        rendered_data_type = f"{row['data_type']} ({row['udt_name']})"
                    columns[(row["schema_name"], row["relation_name"])].append(
                        DiscoveredColumn(
                            name=row["column_name"],
                            ordinal_position=row["ordinal_position"],
                            data_type=rendered_data_type,
                            is_nullable=row["is_nullable"] == "YES",
                            default_value=row["column_default"],
                        )
                    )
        return columns
