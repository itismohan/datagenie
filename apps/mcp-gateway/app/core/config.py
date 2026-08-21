from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """MCP gateway configuration sourced exclusively from DATAGENIE_* variables."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="DATAGENIE_", case_sensitive=False, extra="ignore")

    app_name: str = "DataGenie MCP Gateway"
    environment: Literal["development", "staging", "production"] = "development"
    mcp_protocol_versions: str = "2025-11-25,2026-07-28"
    mcp_endpoint_path: str = "/mcp"
    mcp_internal_beta_enabled: bool = False
    mcp_kill_switch_enabled: bool = False
    mcp_disabled_tools: str = ""
    mcp_allowed_tenants: str = "internal-beta"
    mcp_allowed_hosts: str = "datagenie-internal-host"
    mcp_allowed_origins: str = ""
    mcp_max_requests_per_minute: int = 60
    mcp_max_results: int = 50
    mcp_max_lineage_depth: int = 3
    mcp_max_lineage_nodes: int = 100
    mcp_tool_timeout_seconds: float = 5.0
    mcp_resource_base_url: str = "https://mcp.internal.example/mcp"

    auth_enabled: bool = True
    auth_mode: Literal["hs256", "oidc"] = "hs256"
    auth_jwt_secret: SecretStr | None = None
    auth_jwt_algorithm: str = "HS256"
    auth_oidc_issuer: str | None = None
    auth_oidc_audience: str | None = None
    auth_oidc_jwks_url: str | None = None
    auth_oidc_role_claim: str = "roles"
    auth_tenant_claim: str = "tenant_id"
    auth_scope_claim: str = "scope"
    mcp_required_audience: str = "datagenie-mcp"
    mcp_authorization_servers: str = "https://auth.internal.example"

    downstream_catalog_url: str = "http://catalog-api:8000"
    downstream_quality_url: str = "http://quality-api:8001"
    downstream_lineage_url: str = "http://lineage-api:8002"
    downstream_service_id: str = "mcp-gateway"
    downstream_service_shared_secret: SecretStr | None = None

    ledger_database_url: str = "sqlite:///./datagenie_mcp_gateway.db"
    request_id_header: str = "X-Request-ID"
    log_level: str = "INFO"

    @field_validator("mcp_max_requests_per_minute", "mcp_max_results", "mcp_max_lineage_depth", "mcp_max_lineage_nodes")
    @classmethod
    def positive_limits(cls, value: int) -> int:
        if value < 1:
            raise ValueError("MCP limits must be positive.")
        return value

    @model_validator(mode="after")
    def validate_secure_configuration(self) -> "Settings":
        if not self.mcp_endpoint_path.startswith("/"):
            raise ValueError("DATAGENIE_MCP_ENDPOINT_PATH must start with '/'.")
        if self.auth_enabled and self.auth_mode == "hs256" and self.auth_jwt_secret is None:
            raise ValueError("DATAGENIE_AUTH_JWT_SECRET is required when MCP HS256 authentication is enabled.")
        if self.auth_enabled and self.auth_mode == "oidc" and not all(
            [self.auth_oidc_issuer, self.auth_oidc_audience, self.auth_oidc_jwks_url]
        ):
            raise ValueError("OIDC MCP mode requires issuer, audience, and JWKS URL.")
        if self.environment in {"staging", "production"}:
            if not self.mcp_internal_beta_enabled:
                raise ValueError("Internal MCP beta must be explicitly enabled outside development.")
            if not self.downstream_service_shared_secret:
                raise ValueError("A downstream service identity secret is required outside development.")
            if not self.mcp_allowed_tenants.strip() or not self.mcp_allowed_hosts.strip():
                raise ValueError("Internal MCP beta requires allowed tenant and host lists.")
        return self

    def csv(self, value: str) -> frozenset[str]:
        return frozenset(item.strip() for item in value.split(",") if item.strip())

    @property
    def supported_protocol_versions(self) -> tuple[str, ...]:
        return tuple(item.strip() for item in self.mcp_protocol_versions.split(",") if item.strip())

    def jwt_secret_value(self) -> str:
        if self.auth_jwt_secret is None:
            raise RuntimeError("MCP gateway JWT secret is not configured.")
        return self.auth_jwt_secret.get_secret_value()

    def downstream_secret_value(self) -> str:
        if self.downstream_service_shared_secret is None:
            raise RuntimeError("MCP downstream service identity secret is not configured.")
        return self.downstream_service_shared_secret.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
