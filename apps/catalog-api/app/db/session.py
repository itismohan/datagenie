
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker, with_loader_criteria

from app.core.config import get_settings
from app.core.tenant import get_current_tenant_id


def _engine_options(database_url: str) -> dict:
    options: dict = {"future": True, "pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return options


engine: Engine = create_engine(
    get_settings().database_url,
    **_engine_options(get_settings().database_url),
)


class TenantSession(Session):
    def get(self, entity, ident, options=None, populate_existing=False, with_for_update=None, identity_token=None, execution_options=None, bind_arguments=None):
        """Never satisfy a tenant-scoped lookup from an object cached under another tenant context."""
        from app.models.catalog import TenantScoped

        if isinstance(entity, type) and issubclass(entity, TenantScoped):
            populate_existing = True
        return super().get(
            entity,
            ident,
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )


SessionLocal = sessionmaker(bind=engine, class_=TenantSession, autocommit=False, autoflush=False, expire_on_commit=False)


def session_tenant_id(session: Session) -> str:
    settings = get_settings()
    return str(session.info.get("tenant_id") or get_current_tenant_id(settings.tenant_default_id))


@event.listens_for(Session, "do_orm_execute")
def apply_tenant_scope(orm_execute_state) -> None:
    """Apply tenant predicates to every ORM select unless an explicit maintenance bypass is used."""
    settings = get_settings()
    if not settings.tenant_isolation_enabled or not orm_execute_state.is_select:
        return
    if orm_execute_state.execution_options.get("include_all_tenants"):
        return
    from app.models.catalog import TenantScoped

    tenant_id = session_tenant_id(orm_execute_state.session)
    orm_execute_state.statement = orm_execute_state.statement.options(
        with_loader_criteria(TenantScoped, lambda entity: entity.tenant_id == tenant_id, include_aliases=True)
    )


@event.listens_for(Session, "before_flush")
def assign_tenant_scope(session: Session, _flush_context, _instances) -> None:
    """Overwrite caller-provided tenant IDs so writes cannot cross the active boundary."""
    settings = get_settings()
    if not settings.tenant_isolation_enabled:
        return
    from app.models.catalog import TenantScoped

    tenant_id = session_tenant_id(session)
    for entity in session.new:
        if isinstance(entity, TenantScoped):
            entity.tenant_id = tenant_id


@event.listens_for(Session, "after_begin")
def set_postgresql_tenant_context(session: Session, _transaction, connection) -> None:
    """Bind PostgreSQL row-level-security policies to the validated tenant claim."""
    settings = get_settings()
    if settings.tenant_isolation_enabled and connection.dialect.name == "postgresql":
        tenant_id = session_tenant_id(session)
        connection.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})


def get_db(request: Request) -> Generator[Session, None, None]:
    db = SessionLocal()
    request.state.db = db
    try:
        yield db
    finally:
        if getattr(request.state, "db", None) is db:
            delattr(request.state, "db")
        db.close()


def create_schema() -> None:
    """Create tables for local development and tests.

    Production deployments should execute the Alembic migration before starting
    the application; this function keeps the repository immediately runnable.
    """
    from app.models.catalog import Base

    Base.metadata.create_all(bind=engine)
