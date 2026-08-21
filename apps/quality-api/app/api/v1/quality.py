from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.quality import QualityIncident, QualityRule, QualityRun
from app.schemas.quality import (
    AssetQualityContextRead,
    AssetQualityContextUpsert,
    AssetQualityProfileRead,
    AssetQualityProfileUpsert,
    CriticalCoverageMetric,
    IncidentCommentCreate,
    IncidentCommentRead,
    IncidentUpdate,
    QualityIncidentRead,
    QualityRuleCreate,
    QualityRuleRead,
    QualityRuleUpdate,
    QualityRunCreate,
    QualityRunRead,
)
from app.services.quality_service import (
    add_incident_comment,
    create_quality_run,
    create_rule,
    critical_coverage,
    get_context,
    get_incident_or_404,
    get_profile_or_404,
    get_rule_or_404,
    get_run_or_404,
    list_incidents,
    list_rules,
    list_runs,
    update_incident,
    update_rule,
    upsert_context,
    upsert_profile,
)
from app.workers.tasks import run_quality_job

router = APIRouter()


def actor_header(x_quality_actor: str | None = Header(default=None)) -> str:
    return x_quality_actor or "quality-api"


def enqueue_run(run_id: str) -> None:
    """Leave a durable queued record if the broker is temporarily unavailable."""
    try:
        run_quality_job.delay(run_id)
    except Exception:
        return


@router.post("/rules", response_model=QualityRuleRead, status_code=status.HTTP_201_CREATED)
def create_quality_rule(
    payload: QualityRuleCreate, db: Session = Depends(get_db), actor: str = Depends(actor_header)
) -> QualityRule:
    return create_rule(db, payload, actor)


@router.get("/rules", response_model=list[QualityRuleRead])
def get_quality_rules(asset_id: str | None = None, db: Session = Depends(get_db)) -> list[QualityRule]:
    return list_rules(db, asset_id)


@router.patch("/rules/{rule_id}", response_model=QualityRuleRead)
def patch_quality_rule(
    rule_id: str,
    payload: QualityRuleUpdate,
    db: Session = Depends(get_db),
    actor: str = Depends(actor_header),
) -> QualityRule:
    return update_rule(db, get_rule_or_404(db, rule_id), payload, actor)


@router.put("/assets/{asset_id}/profile", response_model=AssetQualityProfileRead)
def put_quality_profile(
    asset_id: str, payload: AssetQualityProfileUpsert, db: Session = Depends(get_db)
):
    return upsert_profile(db, asset_id, payload.snapshot, payload.observed_at, payload.profiled_by)


@router.get("/assets/{asset_id}/profile", response_model=AssetQualityProfileRead)
def get_quality_profile(asset_id: str, db: Session = Depends(get_db)):
    return get_profile_or_404(db, asset_id)


@router.post("/assets/{asset_id}/runs", response_model=QualityRunRead, status_code=status.HTTP_202_ACCEPTED)
def trigger_quality_run(
    asset_id: str,
    payload: QualityRunCreate,
    response: Response,
    db: Session = Depends(get_db),
    actor: str = Depends(actor_header),
) -> QualityRun:
    run = create_quality_run(db, asset_id, payload.profile_snapshot, payload.trigger, actor)
    enqueue_run(run.id)
    response.headers["Location"] = f"/api/v1/quality/runs/{run.id}"
    return run


@router.get("/runs", response_model=list[QualityRunRead])
def get_quality_runs(asset_id: str | None = None, db: Session = Depends(get_db)) -> list[QualityRun]:
    return list_runs(db, asset_id)


@router.get("/runs/{run_id}", response_model=QualityRunRead)
def get_quality_run(run_id: str, db: Session = Depends(get_db)) -> QualityRun:
    return get_run_or_404(db, run_id)


@router.put("/assets/{asset_id}/context", response_model=AssetQualityContextRead)
def put_quality_context(
    asset_id: str, payload: AssetQualityContextUpsert, db: Session = Depends(get_db)
):
    return upsert_context(db, asset_id, payload)


@router.get("/assets/{asset_id}/context", response_model=AssetQualityContextRead)
def get_quality_context(asset_id: str, db: Session = Depends(get_db)):
    context = get_context(db, asset_id)
    db.commit()
    db.refresh(context)
    return context


@router.get("/incidents", response_model=list[QualityIncidentRead])
def get_quality_incidents(asset_id: str | None = None, db: Session = Depends(get_db)) -> list[QualityIncident]:
    return list_incidents(db, asset_id)


@router.get("/incidents/{incident_id}", response_model=QualityIncidentRead)
def get_quality_incident(incident_id: str, db: Session = Depends(get_db)) -> QualityIncident:
    return get_incident_or_404(db, incident_id)


@router.patch("/incidents/{incident_id}", response_model=QualityIncidentRead)
def patch_quality_incident(
    incident_id: str, payload: IncidentUpdate, db: Session = Depends(get_db)
) -> QualityIncident:
    return update_incident(db, get_incident_or_404(db, incident_id), payload)


@router.post("/incidents/{incident_id}/comments", response_model=IncidentCommentRead, status_code=status.HTTP_201_CREATED)
def create_incident_comment(
    incident_id: str, payload: IncidentCommentCreate, db: Session = Depends(get_db)
):
    return add_incident_comment(db, get_incident_or_404(db, incident_id), payload)


@router.get("/metrics/critical-coverage", response_model=CriticalCoverageMetric)
def critical_asset_coverage(
    recency_hours: int | None = Query(default=None, ge=1, le=8760), db: Session = Depends(get_db)
) -> CriticalCoverageMetric:
    configured_recency = recency_hours or get_settings().quality_recency_hours
    critical_assets, covered_assets, exclusions = critical_coverage(db, configured_recency)
    percentage = round((covered_assets / critical_assets) * 100, 2) if critical_assets else 0.0
    return CriticalCoverageMetric(
        critical_assets=critical_assets,
        covered_assets=covered_assets,
        percentage=percentage,
        recency_hours=configured_recency,
        exclusion_reasons=exclusions,
    )
