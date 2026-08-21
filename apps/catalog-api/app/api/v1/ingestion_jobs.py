from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import ROLE_DATA_STEWARD, ROLE_PLATFORM_ADMIN, Principal, require_roles
from app.db.session import get_db
from app.models.catalog import DataSource, IngestionJob, JobStatus
from app.schemas.catalog import IngestionJobRead
from app.services.audit_service import record_audit_event
from app.services.catalog_service import create_ingestion_job, get_job_or_404
from app.services.ingestion_service import run_ingestion_job

router = APIRouter()
job_operator = require_roles(ROLE_PLATFORM_ADMIN, ROLE_DATA_STEWARD)


@router.get("/", response_model=list[IngestionJobRead])
def list_ingestion_jobs(
    request: Request,
    source_id: str | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(job_operator),
) -> list[IngestionJob]:
    statement = select(IngestionJob)
    if source_id:
        statement = statement.where(IngestionJob.source_id == source_id)
    jobs = list(db.scalars(statement.order_by(IngestionJob.created_at.desc())))
    record_audit_event(
        db,
        principal=principal,
        action="ingestion_job.list",
        resource_type="ingestion_job",
        resource_id=None,
        outcome="success",
        request_id=getattr(request.state, "request_id", "unknown"),
        metadata={"source_id": source_id, "result_count": len(jobs)},
    )
    db.commit()
    return jobs


@router.get("/{job_id}", response_model=IngestionJobRead)
def get_ingestion_job(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(job_operator),
) -> IngestionJob:
    job = get_job_or_404(db, job_id)
    record_audit_event(
        db,
        principal=principal,
        action="ingestion_job.read",
        resource_type="ingestion_job",
        resource_id=job.id,
        outcome="success",
        request_id=getattr(request.state, "request_id", "unknown"),
        metadata={"source_id": job.source_id, "status": job.status.value},
    )
    db.commit()
    return job


@router.post("/{job_id}/retry", response_model=IngestionJobRead, status_code=status.HTTP_201_CREATED)
def retry_ingestion_job(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(job_operator),
) -> IngestionJob:
    prior_job = get_job_or_404(db, job_id)
    if prior_job.status not in {JobStatus.FAILED, JobStatus.CANCELLED}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "job_not_retryable", "message": "Only failed or cancelled ingestion jobs can be retried."},
        )
    source = db.get(DataSource, prior_job.source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found for ingestion job.")
    retry_job = create_ingestion_job(db, source, prior_job.requested_sync_mode)
    retry_job.retry_of_job_id = prior_job.id
    db.commit()
    retry_job = run_ingestion_job(db, retry_job.id)
    record_audit_event(
        db,
        principal=principal,
        action="ingestion_job.retry",
        resource_type="ingestion_job",
        resource_id=retry_job.id,
        outcome="success" if retry_job.status == JobStatus.SUCCEEDED else "failure",
        request_id=getattr(request.state, "request_id", "unknown"),
        metadata={"retry_of_job_id": prior_job.id, "source_id": source.id},
    )
    db.commit()
    return retry_job


@router.post("/{job_id}/cancel", response_model=IngestionJobRead)
def request_cancel(
    job_id: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(job_operator),
) -> IngestionJob:
    job = get_job_or_404(db, job_id)
    if job.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
        job.cancel_requested = True
        if job.status == JobStatus.QUEUED:
            job.status = JobStatus.CANCELLED
        record_audit_event(
            db,
            principal=principal,
            action="ingestion_job.cancel",
            resource_type="ingestion_job",
            resource_id=job.id,
            outcome="success",
            request_id=getattr(request.state, "request_id", "unknown"),
            metadata={"previous_status": job.status.value},
        )
        db.commit()
        db.refresh(job)
    return job
