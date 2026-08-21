from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration sourced only from the DATAGENIE_ environment namespace."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DATAGENIE_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "DataGenie Catalog API"
    environment: Literal["development", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./datagenie_catalog.db"
    auth_enabled: bool = False
    auth_mode: Literal["hs256", "oidc"] = "hs256"
    auth_jwt_secret: SecretStr | None = None
    auth_jwt_algorithm: str = "HS256"
    auth_oidc_issuer: str | None = None
    auth_oidc_audience: str | None = None
    auth_oidc_jwks_url: str | None = None
    auth_oidc_role_claim: str = "roles"
    auth_tenant_claim: str = "tenant_id"
    mcp_gateway_service_identity_enabled: bool = False
    mcp_gateway_service_id: str = "mcp-gateway"
    mcp_gateway_service_shared_secret: SecretStr | None = None
    mcp_gateway_service_max_skew_seconds: int = 60
    tenant_isolation_enabled: bool = True
    tenant_default_id: str = "default"
    connector_redis_url: str | None = None
    connector_task_always_eager: bool = False
    connector_task_time_limit_seconds: int = 1_800
    connector_task_soft_time_limit_seconds: int = 1_740
    connector_max_retries: int = 3
    connector_retry_backoff_seconds: int = 30
    connector_lease_seconds: int = 1_860
    error_tracking_dsn: str | None = None
    error_tracking_traces_sample_rate: float = 0.1
    webhook_allowed_hosts: str = ""
    webhook_delivery_timeout_seconds: int = 10
    webhook_max_retries: int = 5
    idempotency_ttl_seconds: int = 86_400
    request_id_header: str = "X-Request-ID"
    rate_limit_enabled: bool = False
    rate_limit_redis_url: str | None = None
    rate_limit_requests: int = 300
    rate_limit_window_seconds: int = 60
    rate_limit_fail_open: bool = False
    log_level: str = "INFO"

    @model_validator(mode="after")
    def require_production_settings(self) -> "Settings":
        if self.environment in {"staging", "production"}:
            if self.database_url.startswith("sqlite"):
                raise ValueError("DATAGENIE_DATABASE_URL must use PostgreSQL outside development.")
            if not self.auth_enabled:
                raise ValueError("DATAGENIE_AUTH_ENABLED must be true outside development.")
            if self.auth_mode == "hs256" and (self.auth_jwt_secret is None or len(self.auth_jwt_secret.get_secret_value()) < 32):
                raise ValueError("DATAGENIE_AUTH_JWT_SECRET must contain at least 32 characters when HS256 is enabled outside development.")
            if self.auth_mode == "oidc" and not all([self.auth_oidc_issuer, self.auth_oidc_audience, self.auth_oidc_jwks_url]):
                raise ValueError("OIDC mode requires DATAGENIE_AUTH_OIDC_ISSUER, DATAGENIE_AUTH_OIDC_AUDIENCE, and DATAGENIE_AUTH_OIDC_JWKS_URL outside development.")
            if not self.rate_limit_enabled:
                raise ValueError("DATAGENIE_RATE_LIMIT_ENABLED must be true outside development.")
            if not self.rate_limit_redis_url:
                raise ValueError("DATAGENIE_RATE_LIMIT_REDIS_URL is required when rate limiting is enabled outside development.")
            if self.rate_limit_fail_open:
                raise ValueError("DATAGENIE_RATE_LIMIT_FAIL_OPEN must be false outside development.")
            if not self.tenant_isolation_enabled:
                raise ValueError("DATAGENIE_TENANT_ISOLATION_ENABLED must be true outside development.")
            if not self.connector_redis_url:
                raise ValueError("DATAGENIE_CONNECTOR_REDIS_URL is required outside development for durable connector execution.")
            if not self.error_tracking_dsn:
                raise ValueError("DATAGENIE_ERROR_TRACKING_DSN is required outside development.")
            if not self.webhook_allowed_hosts.strip():
                raise ValueError("DATAGENIE_WEBHOOK_ALLOWED_HOSTS is required outside development.")
            if self.mcp_gateway_service_identity_enabled and self.mcp_gateway_service_shared_secret is None:
                raise ValueError("DATAGENIE_MCP_GATEWAY_SERVICE_SHARED_SECRET is required when MCP service delegation is enabled.")
        if not self.tenant_default_id.strip():
            raise ValueError("DATAGENIE_TENANT_DEFAULT_ID must not be empty.")
        if not 0.0 <= self.error_tracking_traces_sample_rate <= 1.0:
            raise ValueError("DATAGENIE_ERROR_TRACKING_TRACES_SAMPLE_RATE must be between 0 and 1.")
        if self.connector_task_soft_time_limit_seconds >= self.connector_task_time_limit_seconds:
            raise ValueError("DATAGENIE_CONNECTOR_TASK_SOFT_TIME_LIMIT_SECONDS must be lower than the hard time limit.")
        if self.connector_max_retries < 0 or self.webhook_max_retries < 0:
            raise ValueError("Retry limits must be zero or greater.")
        if self.webhook_delivery_timeout_seconds < 1 or self.webhook_delivery_timeout_seconds > 60:
            raise ValueError("DATAGENIE_WEBHOOK_DELIVERY_TIMEOUT_SECONDS must be between 1 and 60.")
        if self.connector_retry_backoff_seconds < 1 or self.connector_lease_seconds < self.connector_task_time_limit_seconds:
            raise ValueError("Connector retry and lease settings are invalid.")
        if self.rate_limit_requests < 1:
            raise ValueError("DATAGENIE_RATE_LIMIT_REQUESTS must be at least 1.")
        if self.rate_limit_window_seconds < 1:
            raise ValueError("DATAGENIE_RATE_LIMIT_WINDOW_SECONDS must be at least 1.")
        if self.rate_limit_enabled and not self.rate_limit_redis_url:
            raise ValueError("DATAGENIE_RATE_LIMIT_REDIS_URL is required when rate limiting is enabled.")
        if self.mcp_gateway_service_max_skew_seconds < 1 or self.mcp_gateway_service_max_skew_seconds > 300:
            raise ValueError("DATAGENIE_MCP_GATEWAY_SERVICE_MAX_SKEW_SECONDS must be between 1 and 300.")
        return self

    def mcp_gateway_service_secret_value(self) -> str:
        if self.mcp_gateway_service_shared_secret is None:
            raise RuntimeError("MCP gateway service identity secret is not configured.")
        return self.mcp_gateway_service_shared_secret.get_secret_value()

    def jwt_secret_value(self) -> str:
        if self.auth_jwt_secret is None:
            raise RuntimeError("JWT authentication is enabled but DATAGENIE_AUTH_JWT_SECRET is not configured.")
        return self.auth_jwt_secret.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
