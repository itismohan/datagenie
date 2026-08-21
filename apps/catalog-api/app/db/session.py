
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _engine_options(database_url: str) -> dict:
    options: dict = {"future": True, "pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return options


engine: Engine = create_engine(
    get_settings().database_url,
    **_engine_options(get_settings().database_url),
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_schema() -> None:
    """Create tables for local development and tests.

    Production deployments should execute the Alembic migration before starting
    the application; this function keeps the repository immediately runnable.
    """
    from app.models.catalog import Base

    Base.metadata.create_all(bind=engine)
