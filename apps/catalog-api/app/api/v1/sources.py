from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import ROLE_DATA_STEWARD, ROLE_PLATFORM_ADMIN, Principal, require_roles
from app.db.session import get_db
from app.models.catalog import DataSource, SourceSyncState
from app.schemas.catalog import IngestionJobRead, IngestionRequest, SourceCreate, SourceRead, SourceSyncStateRead
from app.services.audit_service import record_audit_event
from app.services.catalog_service import create_ingestion_job, create_source, get_source_or_404
from app.services.idempotency_service import IdempotencyContext, get_idempotency_context, replay_response, store_response
from app.services.ingestion_service import get_connector, run_ingestion_job

router = APIRouter()
source_operator = require_roles(ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD)


def request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@router.post("/", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
def register_source(
    payload: SourceCreate,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(source_operator),
    idempotency: IdempotencyContext | None = Depends(get_idempotency_context),
) -> DataSource | Response:
    """Register a source; credentials are referenced externally and never persisted here."""
    replay = replay_response(db, idempotency)
    if replay:
        return replay
    source = create_source(db, payload)
    record_audit_event(
        db,
        principal=principal,
        action="source.create",
        resource_type="data_source",
        resource_id=source.id,
        outcome="success",
        request_id=request_id(request),
        metadata={"source_type": source.source_type.value, "name": source.name},
    )
    body = SourceRead.model_validate(source).model_dump(mode="json")
    store_response(db, idempotency, body, status.HTTP_201_CREATED)
    return source


@router.get("/", response_model=list[SourceRead])
def list_sources(
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(source_operator),
) -> list[DataSource]:
    sources = list(db.scalars(select(DataSource).order_by(DataSource.created_at.desc())))
    record_audit_event(
        db,
        principal=principal,
        action="source.list",
        resource_type="data_source",
        resource_id=None,
        outcome="success",
        request_id=request_id(request),
        metadata={"result_count": len(sources)},
    )
    db.commit()
    return sources


@router.get("/{source_id}", response_model=SourceRead)
def get_source(
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(source_operator),
) -> DataSource:
    source = get_source_or_404(db, source_id)
    record_audit_event(
        db,
        principal=principal,
        action="source.read",
        resource_type="data_source",
        resource_id=source.id,
        outcome="success",
        request_id=request_id(request),
    )
    db.commit()
    return source


@router.get("/{source_id}/sync-state", response_model=SourceSyncStateRead)
def source_sync_state(
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(source_operator),
) -> SourceSyncStateRead | SourceSyncState:
    source = get_source_or_404(db, source_id)
    sync_state = db.get(SourceSyncState, source.id)
    record_audit_event(
        db,
        principal=principal,
        action="source.sync_state",
        resource_type="data_source",
        resource_id=source.id,
        outcome="success",
        request_id=request_id(request),
    )
    db.commit()
    if sync_state:
        return sync_state
    return SourceSyncStateRead(
        source_id=source.id,
        cursor={},
        last_successful_job_id=None,
        last_successful_at=None,
        last_full_sync_at=None,
        last_incremental_sync_at=None,
    )


@router.get("/{source_id}/capabilities")
def source_capabilities(
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(source_operator),
) -> dict[str, bool]:
    source = get_source_or_404(db, source_id)
    capabilities = get_connector(source).capabilities()
    record_audit_event(
        db,
        principal=principal,
        action="source.capabilities",
        resource_type="data_source",
        resource_id=source.id,
        outcome="success",
        request_id=request_id(request),
        metadata={"source_type": source.source_type.value},
    )
    db.commit()
    return capabilities


@router.post("/{source_id}/validate")
def validate_source(
    source_id: str, request: Request, db: Session = Depends(get_db), principal: Principal = Depends(source_operator)
) -> dict[str, str]:
    source = get_source_or_404(db, source_id)
    try:
        get_connector(source).validate(source)
    except ValueError as exc:
        record_audit_event(
            db,
            principal=principal,
            action="source.validate",
            resource_type="data_source",
            resource_id=source.id,
            outcome="failure",
            request_id=request_id(request),
            metadata={"reason": type(exc).__name__},
        )
        db.commit()
        return {"status": "invalid", "detail": str(exc)}
    record_audit_event(
        db,
        principal=principal,
        action="source.validate",
        resource_type="data_source",
        resource_id=source.id,
        outcome="success",
        request_id=request_id(request),
    )
    db.commit()
    return {"status": "valid"}


@router.post("/{source_id}/ingestion-jobs", response_model=IngestionJobRead, status_code=status.HTTP_201_CREATED)
def run_source_ingestion(
    source_id: str,
    request: Request,
    payload: IngestionRequest = IngestionRequest(),
    db: Session = Depends(get_db),
    principal: Principal = Depends(source_operator),
    idempotency: IdempotencyContext | None = Depends(get_idempotency_context),
) -> object:
    """Create and execute an ingestion job through the stable job resource contract."""
    replay = replay_response(db, idempotency)
    if replay:
        return replay
    source = get_source_or_404(db, source_id)
    job = create_ingestion_job(db, source, payload.sync_mode)
    job = run_ingestion_job(db, job.id)
    record_audit_event(
        db,
        principal=principal,
        action="ingestion_job.run",
        resource_type="ingestion_job",
        resource_id=job.id,
        outcome="success" if job.status.value == "succeeded" else "failure",
        request_id=request_id(request),
        metadata={
            "source_id": source.id,
            "job_status": job.status.value,
            "requested_sync_mode": job.requested_sync_mode.value,
            "effective_sync_mode": job.effective_sync_mode.value if job.effective_sync_mode else None,
            "strategy": job.connector_strategy,
        },
    )
    body = IngestionJobRead.model_validate(job).model_dump(mode="json")
    store_response(db, idempotency, body, status.HTTP_201_CREATED)
    return job
