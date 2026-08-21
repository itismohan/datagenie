
from functools import lru_cache

from neo4j import GraphDatabase
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LineageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DATAGENIE_", extra="ignore")

    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr


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
