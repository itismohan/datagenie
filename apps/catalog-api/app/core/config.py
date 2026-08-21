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
    idempotency_ttl_seconds: int = 86_400
    request_id_header: str = "X-Request-ID"
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
        return self

    def jwt_secret_value(self) -> str:
        if self.auth_jwt_secret is None:
            raise RuntimeError("JWT authentication is enabled but DATAGENIE_AUTH_JWT_SECRET is not configured.")
        return self.auth_jwt_secret.get_secret_value()


@lru_cache
def get_settings() -> Settings:
    return Settings()
