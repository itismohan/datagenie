from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.quality import (
    AssetQualityContext,
    AssetQualityProfile,
    CertificationStatus,
    IncidentStatus,
    QualityIncident,
    QualityIncidentComment,
    QualityRule,
    QualityRuleVersion,
    QualityRun,
    RuleSeverity,
    RuleType,
    RunStatus,
    RunTrigger,
)
from app.schemas.quality import (
    AssetQualityContextUpsert,
    IncidentCommentCreate,
    IncidentUpdate,
    QualityRuleCreate,
    QualityRuleUpdate,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _rule_definition(rule: QualityRule) -> dict[str, Any]:
    return {
        "name": rule.name,
        "asset_id": rule.asset_id,
        "column_name": rule.column_name,
        "rule_type": rule.rule_type.value,
        "severity": rule.severity.value,
        "owner": rule.owner,
        "parameters": rule.parameters,
        "enabled": rule.enabled,
        "schedule_cron": rule.schedule_cron,
    }


def validate_rule_parameters(rule_type: RuleType, parameters: dict[str, Any]) -> None:
    required: dict[RuleType, tuple[str, ...]] = {
        RuleType.COMPLETENESS: ("minimum_ratio",),
        RuleType.UNIQUENESS: ("minimum_ratio",),
        RuleType.VALIDITY: ("minimum_ratio",),
        RuleType.FRESHNESS: ("maximum_age_minutes",),
        RuleType.REFERENTIAL_INTEGRITY: ("maximum_orphan_ratio",),
        RuleType.DISTRIBUTION_ANOMALY: ("maximum_z_score",),
    }
    missing = [parameter for parameter in required[rule_type] if parameter not in parameters]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_rule_parameters", "message": f"Missing required parameters: {', '.join(missing)}."},
        )
    for key, value in parameters.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_rule_parameters", "message": f"Parameter {key} must be numeric."},
            )
    ratio_keys = {"minimum_ratio", "maximum_orphan_ratio"}
    for key in ratio_keys.intersection(parameters):
        if not 0 <= parameters[key] <= 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_rule_parameters", "message": f"Parameter {key} must be between 0 and 1."},
            )
    for key in {"maximum_age_minutes", "maximum_z_score"}.intersection(parameters):
        if parameters[key] < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_rule_parameters", "message": f"Parameter {key} must be non-negative."},
            )


def create_rule(db: Session, payload: QualityRuleCreate, actor: str) -> QualityRule:
    validate_rule_parameters(payload.rule_type, payload.parameters)
    rule = QualityRule(**payload.model_dump())
    db.add(rule)
    db.flush()
    db.add(
        QualityRuleVersion(
            rule_id=rule.id,
            version=rule.version,
            definition=_rule_definition(rule),
            changed_by=actor,
            change_reason="initial definition",
        )
    )
    db.commit()
    db.refresh(rule)
    return rule


def get_rule_or_404(db: Session, rule_id: str) -> QualityRule:
    rule = db.get(QualityRule, rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quality rule not found.")
    return rule


def update_rule(db: Session, rule: QualityRule, payload: QualityRuleUpdate, actor: str) -> QualityRule:
    updates = payload.model_dump(exclude_unset=True, exclude={"change_reason"})
    if "parameters" in updates and updates["parameters"] is not None:
        validate_rule_parameters(rule.rule_type, updates["parameters"])
    changed = any(getattr(rule, field) != value for field, value in updates.items())
    if changed:
        for field, value in updates.items():
            setattr(rule, field, value)
        rule.version += 1
        db.add(
            QualityRuleVersion(
                rule_id=rule.id,
                version=rule.version,
                definition=_rule_definition(rule),
                changed_by=actor,
                change_reason=payload.change_reason,
            )
        )
        db.commit()
        db.refresh(rule)
    return rule


def list_rules(db: Session, asset_id: str | None = None) -> list[QualityRule]:
    statement = select(QualityRule)
    if asset_id:
        statement = statement.where(QualityRule.asset_id == asset_id)
    return list(db.scalars(statement.order_by(QualityRule.created_at.desc())))


def create_quality_run(
    db: Session, asset_id: str, profile_snapshot: dict[str, Any], trigger: RunTrigger, requested_by: str
) -> QualityRun:
    profile = db.get(AssetQualityProfile, asset_id)
    effective_snapshot = profile_snapshot or (dict(profile.snapshot) if profile else {})
    run = QualityRun(
        asset_id=asset_id,
        trigger=trigger,
        requested_by=requested_by,
        profile_snapshot=effective_snapshot,
        status=RunStatus.QUEUED,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_run_or_404(db: Session, run_id: str) -> QualityRun:
    run = db.scalar(select(QualityRun).where(QualityRun.id == run_id).options(selectinload(QualityRun.results)))
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quality run not found.")
    return run


def list_runs(db: Session, asset_id: str | None = None) -> list[QualityRun]:
    statement = select(QualityRun).options(selectinload(QualityRun.results))
    if asset_id:
        statement = statement.where(QualityRun.asset_id == asset_id)
    return list(db.scalars(statement.order_by(QualityRun.queued_at.desc())).unique())


def upsert_profile(
    db: Session, asset_id: str, snapshot: dict[str, Any], observed_at: datetime, profiled_by: str
) -> AssetQualityProfile:
    profile = db.get(AssetQualityProfile, asset_id)
    if profile is None:
        profile = AssetQualityProfile(
            asset_id=asset_id, snapshot=snapshot, observed_at=observed_at, profiled_by=profiled_by
        )
        db.add(profile)
    else:
        profile.snapshot = snapshot
        profile.observed_at = observed_at
        profile.profiled_by = profiled_by
    db.commit()
    db.refresh(profile)
    return profile


def get_profile_or_404(db: Session, asset_id: str) -> AssetQualityProfile:
    profile = db.get(AssetQualityProfile, asset_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quality profile not found for asset.")
    return profile


def get_or_create_context(db: Session, asset_id: str) -> AssetQualityContext:
    context = db.get(AssetQualityContext, asset_id)
    if context is None:
        context = AssetQualityContext(asset_id=asset_id)
        db.add(context)
        db.flush()
    return context


def upsert_context(db: Session, asset_id: str, payload: AssetQualityContextUpsert) -> AssetQualityContext:
    context = get_or_create_context(db, asset_id)
    for field, value in payload.model_dump().items():
        setattr(context, field, value)
    db.commit()
    db.refresh(context)
    return context


def get_context(db: Session, asset_id: str) -> AssetQualityContext:
    return get_or_create_context(db, asset_id)


def list_incidents(db: Session, asset_id: str | None = None) -> list[QualityIncident]:
    statement = select(QualityIncident).options(selectinload(QualityIncident.comments))
    if asset_id:
        statement = statement.where(QualityIncident.asset_id == asset_id)
    return list(db.scalars(statement.order_by(QualityIncident.last_seen_at.desc())).unique())


def get_incident_or_404(db: Session, incident_id: str) -> QualityIncident:
    incident = db.scalar(
        select(QualityIncident).where(QualityIncident.id == incident_id).options(selectinload(QualityIncident.comments))
    )
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quality incident not found.")
    return incident


def update_incident(db: Session, incident: QualityIncident, payload: IncidentUpdate) -> QualityIncident:
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(incident, field, value)
    if payload.status == IncidentStatus.RESOLVED:
        incident.resolved_at = utc_now()
    elif payload.status is not None:
        incident.resolved_at = None
    db.commit()
    db.refresh(incident)
    return incident


def add_incident_comment(db: Session, incident: QualityIncident, payload: IncidentCommentCreate) -> QualityIncidentComment:
    comment = QualityIncidentComment(incident_id=incident.id, author=payload.author, body=payload.body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def critical_coverage(db: Session, recency_hours: int) -> tuple[int, int, dict[str, int]]:
    contexts = list(db.scalars(select(AssetQualityContext).where(AssetQualityContext.business_criticality == "critical")))
    now = utc_now()
    covered = 0
    reasons = {"missing_owner": 0, "no_explainable_run": 0, "stale_explainable_run": 0}
    for context in contexts:
        if not context.accountable_owner:
            reasons["missing_owner"] += 1
            continue
        if not context.latest_explainable_run_at:
            reasons["no_explainable_run"] += 1
            continue
        latest_run_at = context.latest_explainable_run_at
        if latest_run_at.tzinfo is None:
            latest_run_at = latest_run_at.replace(tzinfo=timezone.utc)
        age_hours = (now - latest_run_at).total_seconds() / 3600
        if age_hours > recency_hours:
            reasons["stale_explainable_run"] += 1
            continue
        covered += 1
    return len(contexts), covered, reasons
