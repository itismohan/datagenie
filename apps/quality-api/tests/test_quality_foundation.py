from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.quality import (
    AssetQualityContext,
    AssetQualityProfile,
    Base,
    BusinessCriticality,
    IncidentStatus,
    QualityRule,
    RuleSeverity,
    RuleType,
    RunTrigger,
)
from app.services.execution_service import dispatch_due_schedules, execute_quality_run
from app.services.quality_service import create_quality_run, critical_coverage, update_rule
from app.schemas.quality import QualityRuleUpdate


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def rule(asset_id: str, rule_type: RuleType, parameters: dict, severity: RuleSeverity = RuleSeverity.MEDIUM) -> QualityRule:
    return QualityRule(
        asset_id=asset_id,
        name=f"{rule_type.value} rule",
        rule_type=rule_type,
        severity=severity,
        parameters=parameters,
        owner="quality-owner@example.com",
    )


def complete_profile(now: datetime) -> dict:
    return {
        "row_count": 100,
        "null_count": 1,
        "distinct_count": 99,
        "invalid_count": 1,
        "latest_record_at": now.isoformat(),
        "orphan_count": 0,
        "related_asset_id": "customer-dimension",
        "current_value": 101,
        "baseline_mean": 100,
        "baseline_stddev": 2,
        "sample_rows": [{"order_id": 1, "customer_id": 42}],
    }


def test_six_rule_types_create_explainable_results_and_score() -> None:
    db = make_session()
    now = datetime.now(timezone.utc)
    asset_id = "asset-orders"
    rules = [
        rule(asset_id, RuleType.COMPLETENESS, {"minimum_ratio": 0.98}),
        rule(asset_id, RuleType.UNIQUENESS, {"minimum_ratio": 0.98}),
        rule(asset_id, RuleType.VALIDITY, {"minimum_ratio": 0.98}),
        rule(asset_id, RuleType.FRESHNESS, {"maximum_age_minutes": 60}),
        rule(asset_id, RuleType.REFERENTIAL_INTEGRITY, {"maximum_orphan_ratio": 0.01}),
        rule(asset_id, RuleType.DISTRIBUTION_ANOMALY, {"maximum_z_score": 2}),
    ]
    db.add_all(rules)
    db.commit()

    run = create_quality_run(db, asset_id, complete_profile(now), RunTrigger.MANUAL, "steward@example.com")
    completed = execute_quality_run(db, run.id)

    assert completed.status.value == "succeeded"
    assert completed.technical_score == 100
    assert completed.explainable is True
    assert len(completed.results) == 6
    assert all(result.evaluated and result.passed for result in completed.results)
    assert all(result.evidence["rule_definition"]["rule_type"] for result in completed.results)


def test_failed_high_severity_rule_creates_incident_and_unexplainable_run_is_not_authoritative() -> None:
    db = make_session()
    asset_id = "asset-customers"
    uniqueness_rule = rule(asset_id, RuleType.UNIQUENESS, {"minimum_ratio": 0.99}, RuleSeverity.HIGH)
    db.add(uniqueness_rule)
    db.commit()

    failure_run = create_quality_run(
        db,
        asset_id,
        {"row_count": 100, "distinct_count": 90, "sample_rows": [{"customer_id": "duplicate"}]},
        RunTrigger.MANUAL,
        "steward@example.com",
    )
    completed = execute_quality_run(db, failure_run.id)

    assert completed.technical_score == 0
    assert completed.explainable is True
    incident = db.query(__import__("app.models.quality", fromlist=["QualityIncident"]).QualityIncident).one()
    assert incident.status == IncidentStatus.OPEN
    assert incident.assignee == "quality-owner@example.com"
    assert incident.evidence["observed_value"]["ratio"] == 0.9

    absent_evidence_run = create_quality_run(db, asset_id, {}, RunTrigger.MANUAL, "steward@example.com")
    not_authoritative = execute_quality_run(db, absent_evidence_run.id)
    assert not_authoritative.technical_score is None
    assert not_authoritative.explainable is False
    assert not_authoritative.results[0].evaluated is False


def test_scheduled_run_uses_profile_and_critical_coverage_requires_owner_and_recent_explainable_run() -> None:
    db = make_session()
    now = datetime.now(timezone.utc)
    asset_id = "asset-critical-orders"
    scheduled_rule = rule(asset_id, RuleType.COMPLETENESS, {"minimum_ratio": 0.95})
    scheduled_rule.schedule_cron = "0 * * * *"
    scheduled_rule.next_run_at = now - timedelta(minutes=1)
    db.add(scheduled_rule)
    db.add(
        AssetQualityProfile(
            asset_id=asset_id,
            snapshot={"row_count": 100, "null_count": 0},
            observed_at=now,
            profiled_by="postgresql-profiler",
        )
    )
    db.add(
        AssetQualityContext(
            asset_id=asset_id,
            business_criticality=BusinessCriticality.CRITICAL,
            accountable_owner="data-owner@example.com",
        )
    )
    db.commit()

    scheduled = dispatch_due_schedules(db, now)
    assert len(scheduled) == 1
    completed = execute_quality_run(db, scheduled[0].id)
    assert completed.trigger == RunTrigger.SCHEDULED
    assert completed.explainable is True

    total, covered, reasons = critical_coverage(db, recency_hours=24)
    assert (total, covered) == (1, 1)
    assert reasons == {"missing_owner": 0, "no_explainable_run": 0, "stale_explainable_run": 0}
