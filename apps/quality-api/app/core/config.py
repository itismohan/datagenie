from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class QualitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATAGENIE_", case_sensitive=False, extra="ignore")

    environment: str = "development"
    quality_database_url: str = "sqlite:///./datagenie_quality.db"
    redis_url: str = "redis://localhost:6379/0"
    quality_task_always_eager: bool = False
    quality_recency_hours: int = 24

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.strip().lower()


@lru_cache
def get_settings() -> QualitySettings:
    return QualitySettings()
