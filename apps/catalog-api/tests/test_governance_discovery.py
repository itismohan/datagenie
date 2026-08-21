from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.catalog import (
    Asset,
    AssetColumn,
    AssetType,
    Base,
    DataSource,
    DiscoveryEventType,
    LifecycleStatus,
    ReviewStatus,
    SourceType,
    SuggestionType,
    UsageDecisionStatus,
)
from app.schemas.governance import DomainCreate
from app.services.catalog_service import search_assets
from app.services.governance_service import (
    create_certification_request,
    create_domain,
    create_glossary_term,
    create_mapping,
    create_suggestion,
    decide_certification_request,
    detect_classifications,
    discovery_metric,
    record_discovery_event,
    review_finding,
    review_mapping,
    review_suggestion,
    review_term,
)


def make_db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def seed_asset(db: Session) -> Asset:
    source = DataSource(
        name="warehouse",
        source_type=SourceType.POSTGRESQL,
        host="warehouse.local",
        database_name="analytics",
        username="metadata-reader",
        secret_ref="env://WAREHOUSE_PASSWORD",
    )
    asset = Asset(
        source=source,
        asset_type=AssetType.TABLE,
        qualified_name="analytics.finance.payments",
        name="payments",
        description="Approved payment operations for finance reporting.",
        owner="finance-owner@example.com",
        tags=["finance", "revenue"],
        lifecycle_status=LifecycleStatus.CERTIFIED,
        quality_score=98,
        quality_explainable_at=datetime.now(timezone.utc),
    )
    asset.columns = [
        AssetColumn(name="customer_email", ordinal_position=1, data_type="varchar", is_nullable=False),
        AssetColumn(name="card_number", ordinal_position=2, data_type="varchar", is_nullable=True),
    ]
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def test_governance_workflows_are_reviewable_and_search_uses_approved_business_context():
    db = make_db()
    asset = seed_asset(db)
    domain = create_domain(db, DomainCreate(name="Finance", business_owner="finance-lead@example.com", data_steward="steward@example.com"))
    asset.domain_id = domain.id
    db.commit()

    term = create_glossary_term(db, "Revenue", "Recognized payment revenue for finance reporting.", "finance-owner@example.com", domain.id, "analyst@example.com")
    term = review_term(db, term, ReviewStatus.APPROVED, "Definition approved.", "steward@example.com")
    mapping = create_mapping(db, term, asset.id, None, "analyst@example.com")
    review_mapping(db, mapping, ReviewStatus.APPROVED, "steward@example.com")

    items, total, facets, index_fresh_at = search_assets(
        db,
        q="revenue",
        source_id=None,
        asset_type=None,
        lifecycle_status=None,
        owner=None,
        classification=None,
        tag=None,
        freshness_before=None,
        business_term=None,
        domain="finance",
        quality_min=90,
        explainable_quality_only=True,
    )
    assert total == 1
    assert items[0].id == asset.id
    assert items[0].discovery_score >= 90
    assert isinstance(facets, dict)
    assert index_fresh_at is None

    findings = detect_classifications(db, asset, "deterministic-classifier")
    assert {finding.classification_type.value for finding in findings} == {"email_address", "payment_data"}
    approved = review_finding(db, findings[0], ReviewStatus.APPROVED, "Confirmed by data steward.", "steward@example.com")
    assert approved.status == ReviewStatus.APPROVED
    assert "email_address" in db.get(Asset, asset.id).classification

    certification = create_certification_request(db, asset.id, "analyst@example.com", "Please certify for monthly reporting.")
    decided = decide_certification_request(db, certification, UsageDecisionStatus.APPROVED, "Evidence reviewed.", "steward@example.com")
    assert decided.status == UsageDecisionStatus.APPROVED
    assert db.get(Asset, asset.id).lifecycle_status == LifecycleStatus.CERTIFIED

    suggestion = create_suggestion(
        db,
        asset.id,
        SuggestionType.LINEAGE_SUMMARY,
        {"summary": "Payments derives into the critical Revenue dashboard."},
        {"edge_provenance": "dbt-manifest", "source": "lineage graph"},
        "governance-assistant",
    )
    reviewed_suggestion = review_suggestion(db, suggestion, ReviewStatus.APPROVED, "Use as steward-reviewed draft.", "steward@example.com")
    assert reviewed_suggestion.status == ReviewStatus.APPROVED
    assert reviewed_suggestion.suggestion_type == SuggestionType.LINEAGE_SUMMARY


def test_discovery_success_metric_requires_search_then_outcome():
    db = make_db()
    asset = seed_asset(db)
    record_discovery_event(db, "session-success", "analyst@example.com", DiscoveryEventType.SEARCH, None, "payments", {})
    record_discovery_event(db, "session-success", "analyst@example.com", DiscoveryEventType.ASSET_VIEW, asset.id, None, {})
    record_discovery_event(db, "session-incomplete", "analyst@example.com", DiscoveryEventType.SEARCH, None, "customers", {})
    sessions, successful, outcomes = discovery_metric(db)
    assert (sessions, successful) == (2, 1)
    assert outcomes["asset_view"] == 1
