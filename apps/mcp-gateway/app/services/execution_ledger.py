from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.config import get_settings
from app.schemas import LedgerRecord


class Base(DeclarativeBase):
    pass


class AgentExecution(Base):
    __tablename__ = "mcp_agent_executions"

    invocation_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    host_id: Mapped[str] = mapped_column(String(255), nullable=False)
    operation_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    operation_name: Mapped[str] = mapped_column(String(128), nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_outcome: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LedgerUnavailable(RuntimeError):
    pass


class ExecutionLedger:
    def __init__(self, database_url: str | None = None) -> None:
        url = database_url or get_settings().ledger_database_url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, future=True, connect_args=connect_args)
        self.sessions = sessionmaker(bind=self.engine, class_=Session, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def record(self, record: LedgerRecord) -> None:
        try:
            with self.sessions.begin() as session:
                session.add(
                    AgentExecution(
                        invocation_id=record.invocation_id,
                        request_id=record.request_id,
                        tenant_id=record.tenant_id,
                        actor_subject=record.actor_subject,
                        host_id=record.host_id,
                        operation_kind=record.operation_kind,
                        operation_name=record.operation_name,
                        input_digest=record.input_digest,
                        policy_outcome=record.policy_outcome,
                        outcome=record.outcome,
                        result_count=record.result_count,
                        result_bytes=record.result_bytes,
                        duration_ms=record.duration_ms,
                        error_code=record.error_code,
                        created_at=record.created_at,
                    )
                )
        except Exception as exc:
            raise LedgerUnavailable("MCP agent execution evidence could not be persisted.") from exc


def make_ledger_record(
    *,
    request_id: str,
    tenant_id: str,
    actor_subject: str,
    host_id: str,
    operation_kind: str,
    operation_name: str,
    input_digest: str,
    policy_outcome: str | None,
    outcome: str,
    result_count: int = 0,
    result_bytes: int = 0,
    duration_ms: float = 0.0,
    error_code: str | None = None,
) -> LedgerRecord:
    return LedgerRecord(
        invocation_id=str(uuid4()),
        request_id=request_id,
        tenant_id=tenant_id,
        actor_subject=actor_subject,
        host_id=host_id,
        operation_kind=operation_kind,  # type: ignore[arg-type]
        operation_name=operation_name,
        input_digest=input_digest,
        policy_outcome=policy_outcome,
        outcome=outcome,  # type: ignore[arg-type]
        result_count=result_count,
        result_bytes=result_bytes,
        duration_ms=duration_ms,
        error_code=error_code,
        created_at=datetime.now(timezone.utc),
    )
