from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.quality import (
    AssetQualityContext,
    AssetQualityProfile,
    IncidentStatus,
    QualityIncident,
    QualityRule,
    QualityRuleResult,
    QualityRun,
    RuleSeverity,
    RunStatus,
    RunTrigger,
)
from app.services.quality_service import _rule_definition, get_or_create_context
from app.services.rule_engine import evaluate_rule


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


SEVERITY_WEIGHT = {
    RuleSeverity.LOW: 1,
    RuleSeverity.MEDIUM: 2,
    RuleSeverity.HIGH: 3,
    RuleSeverity.CRITICAL: 4,
}


def _upsert_incident(db: Session, run: QualityRun, rule: QualityRule, result: QualityRuleResult) -> None:
    if rule.severity not in {RuleSeverity.HIGH, RuleSeverity.CRITICAL} or result.passed or not result.evaluated:
        return
    incident = db.scalar(
        select(QualityIncident).where(
            QualityIncident.asset_id == run.asset_id,
            QualityIncident.rule_id == rule.id,
            QualityIncident.status != IncidentStatus.RESOLVED,
        )
    )
    evidence = {
        "run_id": run.id,
        "result_id": result.id,
        "rule_version": result.rule_version,
        "observed_value": result.observed_value,
        "expected_value": result.expected_value,
        "evidence": result.evidence,
        "explanation": result.explanation,
    }
    if incident is None:
        db.add(
            QualityIncident(
                asset_id=run.asset_id,
                rule_id=rule.id,
                latest_result_id=result.id,
                severity=rule.severity,
                assignee=rule.owner,
                evidence=evidence,
            )
        )
    else:
        incident.latest_result_id = result.id
        incident.severity = rule.severity
        incident.evidence = evidence
        incident.last_seen_at = utc_now()


def execute_quality_run(db: Session, run_id: str) -> QualityRun:
    run = db.get(QualityRun, run_id)
    if run is None:
        raise ValueError("Quality run not found.")
    if run.status in {RunStatus.SUCCEEDED, RunStatus.CANCELLED}:
        return run

    run.status = RunStatus.RUNNING
    run.started_at = utc_now()
    run.error_message = None
    db.commit()

    try:
        rules = list(
            db.scalars(
                select(QualityRule).where(QualityRule.asset_id == run.asset_id, QualityRule.enabled.is_(True))
            )
        )
        effective_versions: dict[str, int] = {}
        evaluated_results: list[tuple[QualityRule, QualityRuleResult]] = []
        all_results: list[QualityRuleResult] = []

        for rule in rules:
            effective_versions[rule.id] = rule.version
            evaluation = evaluate_rule(rule, run.profile_snapshot)
            result = QualityRuleResult(
                run_id=run.id,
                rule_id=rule.id,
                rule_version=rule.version,
                rule_type=rule.rule_type,
                column_name=rule.column_name,
                evaluated=evaluation.evaluated,
                passed=evaluation.passed,
                score=evaluation.score,
                observed_value=evaluation.observed_value,
                expected_value=evaluation.expected_value,
                evidence={**evaluation.evidence, "rule_definition": _rule_definition(rule)},
                explanation=evaluation.explanation,
            )
            db.add(result)
            db.flush()
            all_results.append(result)
            if result.evaluated:
                evaluated_results.append((rule, result))
            _upsert_incident(db, run, rule, result)

        run.effective_rule_versions = effective_versions
        if evaluated_results:
            weighted_total = sum(SEVERITY_WEIGHT[rule.severity] * result.score for rule, result in evaluated_results)
            weight_sum = sum(SEVERITY_WEIGHT[rule.severity] for rule, _result in evaluated_results)
            run.technical_score = round(weighted_total / weight_sum)
        else:
            run.technical_score = None
        run.explainable = bool(all_results) and len(evaluated_results) == len(all_results) and all(
            bool(result.evidence) for result in all_results
        )
        run.status = RunStatus.SUCCEEDED
        run.completed_at = utc_now()

        context = get_or_create_context(db, run.asset_id)
        if run.explainable:
            context.latest_explainable_run_at = run.completed_at
            context.latest_technical_score = run.technical_score
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(QualityRun, run_id)
        if run:
            run.status = RunStatus.FAILED
            run.error_message = f"{type(exc).__name__}: {str(exc)[:500]}"
            run.completed_at = utc_now()
            db.commit()
        raise
    db.refresh(run)
    return run


def dispatch_due_schedules(db: Session, now: datetime | None = None) -> list[QualityRun]:
    """Create scheduled runs. A source profiler can later populate the run snapshot before worker execution."""
    now = now or utc_now()
    due_rules = list(
        db.scalars(
            select(QualityRule).where(
                QualityRule.enabled.is_(True),
                QualityRule.schedule_cron.is_not(None),
                QualityRule.next_run_at.is_not(None),
                QualityRule.next_run_at <= now,
            )
        )
    )
    runs: list[QualityRun] = []
    for rule in due_rules:
        profile = db.get(AssetQualityProfile, rule.asset_id)
        run = QualityRun(
            asset_id=rule.asset_id,
            trigger=RunTrigger.SCHEDULED,
            requested_by="quality-scheduler",
            profile_snapshot=dict(profile.snapshot) if profile else {"scheduled_at": now.isoformat(), "profile_provider": "missing"},
        )
        db.add(run)
        rule.next_run_at = now + timedelta(days=1)
        runs.append(run)
    db.commit()
    for run in runs:
        db.refresh(run)
    return runs
