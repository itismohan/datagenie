from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class QualitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATAGENIE_", case_sensitive=False, extra="ignore")

    environment: str = "development"
    quality_database_url: str = "sqlite:///./datagenie_quality.db"
    redis_url: str = "redis://localhost:6379/0"
    quality_task_always_eager: bool = False
    quality_recency_hours: int = 24
    mcp_gateway_service_identity_enabled: bool = False
    mcp_gateway_service_id: str = "mcp-gateway"
    mcp_gateway_service_shared_secret: SecretStr | None = None
    mcp_gateway_service_max_skew_seconds: int = 60

    def mcp_gateway_service_secret_value(self) -> str:
        if self.mcp_gateway_service_shared_secret is None:
            raise RuntimeError("MCP gateway service identity secret is not configured.")
        return self.mcp_gateway_service_shared_secret.get_secret_value()

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.strip().lower()


@lru_cache
def get_settings() -> QualitySettings:
    return QualitySettings()
