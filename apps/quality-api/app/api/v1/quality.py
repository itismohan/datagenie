from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.mcp_security import McpActor, require_mcp_gateway_actor

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


@router.get("/internal/mcp/assets/{asset_id}/evidence", include_in_schema=False)
def mcp_quality_evidence(
    asset_id: str,
    history_limit: int = Query(default=5, ge=1, le=10),
    db: Session = Depends(get_db),
    _actor: McpActor = Depends(require_mcp_gateway_actor),
) -> dict:
    runs = list(
        db.scalars(
            select(QualityRun)
            .where(QualityRun.asset_id == asset_id)
            .options(selectinload(QualityRun.results))
            .order_by(QualityRun.completed_at.desc(), QualityRun.queued_at.desc())
            .limit(history_limit)
        ).unique()
    )
    incidents = list(
        db.scalars(
            select(QualityIncident)
            .where(QualityIncident.asset_id == asset_id)
            .order_by(QualityIncident.last_seen_at.desc())
            .limit(history_limit)
        )
    )
    latest = runs[0] if runs else None
    now = datetime.now(timezone.utc)
    if latest is None:
        state = "missing"
    elif latest.status.value == "failed":
        state = "failed"
    elif not latest.explainable or latest.completed_at is None:
        state = "unexplained"
    else:
        completed = latest.completed_at if latest.completed_at.tzinfo else latest.completed_at.replace(tzinfo=timezone.utc)
        state = "stale" if (now - completed).total_seconds() > get_settings().quality_recency_hours * 3600 else "current"
    return {
        "asset_id": asset_id,
        "state": state,
        "latest_technical_score": latest.technical_score if latest else None,
        "latest_explainable_at": latest.completed_at.isoformat() if latest and latest.explainable and latest.completed_at else None,
        "runs": [
            {
                "id": run.id,
                "status": run.status.value,
                "trigger": run.trigger.value,
                "technical_score": run.technical_score,
                "explainable": run.explainable,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "effective_rule_versions": run.effective_rule_versions,
                "results": [
                    {
                        "rule_id": result.rule_id,
                        "rule_version": result.rule_version,
                        "rule_type": result.rule_type.value,
                        "column_name": result.column_name,
                        "evaluated": result.evaluated,
                        "passed": result.passed,
                        "score": result.score,
                        "expected_value": result.expected_value,
                        "evaluated_at": result.evaluated_at.isoformat(),
                    }
                    for result in run.results
                ],
            }
            for run in runs
        ],
        "incidents": [
            {
                "id": incident.id,
                "status": incident.status.value,
                "severity": incident.severity.value,
                "first_seen_at": incident.first_seen_at.isoformat(),
                "last_seen_at": incident.last_seen_at.isoformat(),
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
            }
            for incident in incidents
        ],
        "evidence": [{"type": "quality_run", "reference": f"quality:asset:{asset_id}"}],
    }


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
