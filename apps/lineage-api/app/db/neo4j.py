
from functools import lru_cache

from neo4j import GraphDatabase
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LineageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DATAGENIE_", extra="ignore")

    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr
    mcp_gateway_service_identity_enabled: bool = False
    mcp_gateway_service_id: str = "mcp-gateway"
    mcp_gateway_service_shared_secret: SecretStr | None = None
    mcp_gateway_service_max_skew_seconds: int = 60

    def mcp_gateway_service_secret_value(self) -> str:
        if self.mcp_gateway_service_shared_secret is None:
            raise RuntimeError("MCP gateway service identity secret is not configured.")
        return self.mcp_gateway_service_shared_secret.get_secret_value()


@lru_cache
def get_settings() -> LineageSettings:
    return LineageSettings()


@lru_cache
def get_driver():
    settings = get_settings()
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password.get_secret_value()),
    )


def get_session():
    return get_driver().session()
