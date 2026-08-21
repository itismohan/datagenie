import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    import snowflake.connector as snowflake_connector
except ImportError:  # Keeps imports safe until dependencies are installed.
    snowflake_connector = None

from app.connectors.base import ConnectorConfigurationError, DiscoveredAsset, DiscoveredColumn, DiscoveryResult
from app.models.catalog import AssetType, DataSource, SyncMode


class SnowflakeConnector:
    """Discover Snowflake metadata through database-scoped INFORMATION_SCHEMA views."""

    WATERMARK_OVERLAP = timedelta(minutes=5)

    def capabilities(self) -> dict[str, bool]:
        return {
            "configuration_validation": True,
            "metadata_discovery": True,
            "column_discovery": True,
            "incremental_synchronization": True,
            "source_side_incremental_discovery": True,
            "content_fingerprint_incremental": True,
            "profiling": False,
            "cancellation": True,
            "retries": True,
        }

    def validate(self, source: DataSource) -> None:
        if not source.host or not source.database_name or not source.username:
            raise ConnectorConfigurationError("Snowflake account, database name, and username are required.")
        if not source.secret_ref.startswith("env://"):
            raise ConnectorConfigurationError(
                "Snowflake credentials must use an environment-backed secret reference such as env://DATAGENIE_SNOWFLAKE_PASSWORD."
            )
        secret_name = source.secret_ref.removeprefix("env://")
        if not secret_name or not os.getenv(secret_name):
            raise ConnectorConfigurationError(f"Credential reference {source.secret_ref} is not available in the runtime environment.")
        if snowflake_connector is None:
            raise ConnectorConfigurationError("snowflake-connector-python is not installed in the catalog runtime.")

    def discover(
        self, source: DataSource, sync_mode: SyncMode, cursor: dict | None = None
    ) -> DiscoveryResult:
        self.validate(source)
        password = os.environ[source.secret_ref.removeprefix("env://")]
        current_time = datetime.now(timezone.utc)
        prior_watermark = self._read_watermark(cursor or {})
        effective_mode = SyncMode.FULL if sync_mode == SyncMode.FULL or prior_watermark is None else SyncMode.INCREMENTAL
        cutoff = prior_watermark - self.WATERMARK_OVERLAP if effective_mode == SyncMode.INCREMENTAL else None

        with snowflake_connector.connect(**self._connection_kwargs(source, password)) as connection:
            schemas = source.include_schemas or self._discover_schemas(connection, source.database_name)
            relation_rows = self._discover_relations(connection, source.database_name, schemas, cutoff)
            relation_names = {(row["schema_name"], row["relation_name"]) for row in relation_rows}
            columns_by_relation = self._discover_columns(connection, source.database_name, schemas, relation_names)

        discovered: list[DiscoveredAsset] = [
            DiscoveredAsset(
                asset_type=AssetType.DATABASE,
                qualified_name=source.database_name,
                name=source.database_name,
                database_name=source.database_name,
                schema_name=None,
                technical_metadata={"engine": "snowflake", "account": source.host},
                freshness_at=current_time,
            )
        ]
        discovered.extend(
            DiscoveredAsset(
                asset_type=AssetType.SCHEMA,
                qualified_name=f"{source.database_name}.{schema}",
                name=schema,
                database_name=source.database_name,
                schema_name=schema,
                technical_metadata={"engine": "snowflake", "account": source.host},
                freshness_at=current_time,
            )
            for schema in schemas
        )

        latest_watermark = prior_watermark or current_time
        for relation in relation_rows:
            schema_name = relation["schema_name"]
            relation_name = relation["relation_name"]
            relation_type = AssetType.TABLE if relation["relation_type"] == "BASE TABLE" else AssetType.VIEW
            last_altered = self._as_utc(relation.get("last_altered"))
            if last_altered and last_altered > latest_watermark:
                latest_watermark = last_altered
            discovered.append(
                DiscoveredAsset(
                    asset_type=relation_type,
                    qualified_name=f"{source.database_name}.{schema_name}.{relation_name}",
                    name=relation_name,
                    database_name=source.database_name,
                    schema_name=schema_name,
                    technical_metadata={
                        "engine": "snowflake",
                        "relation_type": relation["relation_type"],
                        "last_altered": last_altered.isoformat() if last_altered else None,
                    },
                    freshness_at=current_time,
                    columns=tuple(columns_by_relation[(schema_name, relation_name)]),
                )
            )

        return DiscoveryResult(
            assets=tuple(discovered),
            next_cursor={
                "last_successful_watermark": latest_watermark.isoformat(),
                "overlap_seconds": int(self.WATERMARK_OVERLAP.total_seconds()),
                "strategy": "snowflake_last_altered",
            },
            effective_sync_mode=effective_mode,
            strategy="snowflake_last_altered",
            warnings=(
                "An overlap window is applied to the Snowflake LAST_ALTERED watermark; unchanged overlap results are deduplicated by catalog synchronization.",
            )
            if effective_mode == SyncMode.INCREMENTAL
            else (),
            statistics={
                "schemas_scanned": len(schemas),
                "relations_discovered": len(relation_rows),
                "incremental_cutoff": cutoff.isoformat() if cutoff else None,
            },
        )

    def _connection_kwargs(self, source: DataSource, password: str) -> dict[str, Any]:
        options = source.connection_options or {}
        connection_kwargs: dict[str, Any] = {
            "account": source.host,
            "user": source.username,
            "password": password,
            "database": source.database_name,
            "login_timeout": 15,
        }
        for key in ("warehouse", "role", "authenticator"):
            if options.get(key):
                connection_kwargs[key] = options[key]
        return connection_kwargs

    def _discover_schemas(self, connection: Any, database_name: str) -> list[str]:
        query = f"""
            SELECT SCHEMA_NAME
            FROM {self._quoted_identifier(database_name)}.INFORMATION_SCHEMA.SCHEMATA
            WHERE SCHEMA_NAME <> 'INFORMATION_SCHEMA'
            ORDER BY SCHEMA_NAME
        """
        with connection.cursor(snowflake_connector.DictCursor) as cursor:
            cursor.execute(query)
            return [row["SCHEMA_NAME"] for row in cursor.fetchall()]

    def _discover_relations(
        self, connection: Any, database_name: str, schemas: list[str], cutoff: datetime | None
    ) -> list[dict[str, Any]]:
        if not schemas:
            return []
        schema_placeholders = ", ".join(["%s"] * len(schemas))
        query = f"""
            SELECT TABLE_SCHEMA AS "schema_name", TABLE_NAME AS "relation_name", TABLE_TYPE AS "relation_type", LAST_ALTERED AS "last_altered"
            FROM {self._quoted_identifier(database_name)}.INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA IN ({schema_placeholders})
              AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
        """
        parameters: tuple[Any, ...] = tuple(schemas)
        if cutoff is not None:
            query += " AND LAST_ALTERED >= %s"
            parameters = (*parameters, cutoff)
        query += " ORDER BY TABLE_SCHEMA, TABLE_NAME"
        with connection.cursor(snowflake_connector.DictCursor) as cursor:
            cursor.execute(query, parameters)
            return list(cursor.fetchall())

    def _discover_columns(
        self,
        connection: Any,
        database_name: str,
        schemas: list[str],
        relation_names: set[tuple[str, str]],
    ) -> dict[tuple[str, str], list[DiscoveredColumn]]:
        columns: dict[tuple[str, str], list[DiscoveredColumn]] = defaultdict(list)
        if not relation_names:
            return columns
        schema_placeholders = ", ".join(["%s"] * len(schemas))
        query = f"""
            SELECT TABLE_SCHEMA AS "schema_name", TABLE_NAME AS "relation_name", COLUMN_NAME AS "column_name", ORDINAL_POSITION AS "ordinal_position",
                   DATA_TYPE AS "data_type", IS_NULLABLE AS "is_nullable", COLUMN_DEFAULT AS "column_default", COMMENT AS "comment"
            FROM {self._quoted_identifier(database_name)}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA IN ({schema_placeholders})
            ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
        """
        with connection.cursor(snowflake_connector.DictCursor) as cursor:
            cursor.execute(query, tuple(schemas))
            for row in cursor.fetchall():
                key = (row["schema_name"], row["relation_name"])
                if key not in relation_names:
                    continue
                columns[key].append(
                    DiscoveredColumn(
                        name=row["column_name"],
                        ordinal_position=row["ordinal_position"],
                        data_type=row["data_type"],
                        is_nullable=row["is_nullable"] == "YES",
                        default_value=row["column_default"],
                        technical_description=row["comment"],
                    )
                )
        return columns

    @staticmethod
    def _quoted_identifier(value: str) -> str:
        return '"' + value.replace('"', '""') + '"'

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _read_watermark(cursor: dict) -> datetime | None:
        raw_value = cursor.get("last_successful_watermark")
        if not isinstance(raw_value, str):
            return None
        try:
            parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
