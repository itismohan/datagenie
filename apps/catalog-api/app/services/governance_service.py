import re
from datetime import datetime, timezone
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import (
    Asset,
    BusinessGlossaryTerm,
    CertificationRequest,
    ClassificationFinding,
    ClassificationType,
    DiscoveryEvent,
    DiscoveryEventType,
    GlossaryAssetMapping,
    GovernanceDomain,
    GovernanceSuggestion,
    LifecycleStatus,
    ReviewStatus,
    UsageDecisionStatus,
)
from app.schemas.governance import DomainCreate


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_asset_or_404(db: Session, asset_id: str) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catalog asset not found.")
    return asset


def create_domain(db: Session, payload: DomainCreate) -> GovernanceDomain:
    if db.scalar(select(GovernanceDomain).where(GovernanceDomain.name == payload.name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Governance domain already exists.")
    domain = GovernanceDomain(**payload.model_dump())
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


def list_domains(db: Session) -> list[GovernanceDomain]:
    return list(db.scalars(select(GovernanceDomain).order_by(GovernanceDomain.name.asc())))


def get_domain_or_404(db: Session, domain_id: str) -> GovernanceDomain:
    domain = db.get(GovernanceDomain, domain_id)
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Governance domain not found.")
    return domain


def create_glossary_term(
    db: Session, name: str, definition: str, owner: str | None, domain_id: str | None, proposed_by: str
) -> BusinessGlossaryTerm:
    if db.scalar(select(BusinessGlossaryTerm).where(BusinessGlossaryTerm.name == name)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A glossary term with this name already exists.")
    if domain_id:
        get_domain_or_404(db, domain_id)
    term = BusinessGlossaryTerm(
        name=name,
        definition=definition,
        owner=owner,
        domain_id=domain_id,
        proposed_by=proposed_by,
    )
    db.add(term)
    db.commit()
    db.refresh(term)
    return term


def get_term_or_404(db: Session, term_id: str) -> BusinessGlossaryTerm:
    term = db.get(BusinessGlossaryTerm, term_id)
    if term is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Glossary term not found.")
    return term


def review_term(db: Session, term: BusinessGlossaryTerm, review_status, review_note: str | None, reviewer: str) -> BusinessGlossaryTerm:
    term.status = review_status
    term.review_note = review_note
    term.reviewed_by = reviewer
    term.reviewed_at = utc_now()
    db.commit()
    db.refresh(term)
    return term


def create_mapping(db: Session, term: BusinessGlossaryTerm, asset_id: str, column_name: str | None, actor: str) -> GlossaryAssetMapping:
    get_asset_or_404(db, asset_id)
    existing = db.scalar(
        select(GlossaryAssetMapping).where(
            GlossaryAssetMapping.term_id == term.id,
            GlossaryAssetMapping.asset_id == asset_id,
            GlossaryAssetMapping.column_name == column_name,
        )
    )
    if existing:
        return existing
    mapping = GlossaryAssetMapping(term_id=term.id, asset_id=asset_id, column_name=column_name, proposed_by=actor)
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def review_mapping(db: Session, mapping: GlossaryAssetMapping, review_status: ReviewStatus, reviewer: str) -> GlossaryAssetMapping:
    mapping.status = review_status
    mapping.reviewed_by = reviewer
    mapping.reviewed_at = utc_now()
    db.commit()
    db.refresh(mapping)
    return mapping


CLASSIFICATION_RULES: tuple[tuple[ClassificationType, tuple[str, ...]], ...] = (
    (ClassificationType.EMAIL_ADDRESS, (r"(^|_)e?mail($|_)", r"email_address")),
    (ClassificationType.PHONE_NUMBER, (r"phone", r"mobile", r"telephone")),
    (ClassificationType.GOVERNMENT_IDENTIFIER, (r"ssn", r"social_security", r"national_id", r"passport", r"driver_licen[sc]e", r"tax_id")),
    (ClassificationType.PAYMENT_DATA, (r"card", r"pan", r"cvv", r"iban", r"bank_account", r"payment")),
    (ClassificationType.HEALTH_INFORMATION, (r"health", r"medical", r"diagnos", r"patient", r"clinical")),
)


def detect_classifications(db: Session, asset: Asset, actor: str) -> list[ClassificationFinding]:
    findings: list[ClassificationFinding] = []
    for column in asset.columns:
        normalized_name = column.name.lower()
        for classification_type, patterns in CLASSIFICATION_RULES:
            matched_pattern = next((pattern for pattern in patterns if re.search(pattern, normalized_name)), None)
            if matched_pattern is None:
                continue
            finding = db.scalar(
                select(ClassificationFinding).where(
                    ClassificationFinding.asset_id == asset.id,
                    ClassificationFinding.column_name == column.name,
                    ClassificationFinding.classification_type == classification_type,
                )
            )
            evidence = {
                "column_name": column.name,
                "data_type": column.data_type,
                "matched_pattern": matched_pattern,
                "detection_method": "column_name_and_type_heuristic",
            }
            if finding is None:
                finding = ClassificationFinding(
                    asset_id=asset.id,
                    column_name=column.name,
                    classification_type=classification_type,
                    confidence=85,
                    evidence=evidence,
                    detected_by=actor,
                )
                db.add(finding)
            else:
                finding.evidence = evidence
                finding.confidence = 85
            findings.append(finding)
    db.commit()
    for finding in findings:
        db.refresh(finding)
    return findings


def get_finding_or_404(db: Session, finding_id: str) -> ClassificationFinding:
    finding = db.get(ClassificationFinding, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classification finding not found.")
    return finding


def review_finding(db: Session, finding: ClassificationFinding, review_status: ReviewStatus, note: str | None, reviewer: str) -> ClassificationFinding:
    finding.status = review_status
    finding.reviewed_by = reviewer
    finding.reviewed_at = utc_now()
    finding.review_note = note
    if review_status == ReviewStatus.APPROVED:
        asset = get_asset_or_404(db, finding.asset_id)
        approved_types = list(
            db.scalars(
                select(ClassificationFinding.classification_type).where(
                    ClassificationFinding.asset_id == asset.id,
                    ClassificationFinding.status == ReviewStatus.APPROVED,
                )
            )
        )
        asset.classification = ",".join(sorted({item.value for item in approved_types + [finding.classification_type]}))
    db.commit()
    db.refresh(finding)
    return finding


def create_certification_request(db: Session, asset_id: str, actor: str, note: str | None) -> CertificationRequest:
    get_asset_or_404(db, asset_id)
    request = CertificationRequest(asset_id=asset_id, requested_by=actor, decision_note=note)
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def decide_certification_request(
    db: Session, request: CertificationRequest, decision: UsageDecisionStatus, note: str | None, actor: str
) -> CertificationRequest:
    if decision == UsageDecisionStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A certification decision must be approved or rejected.")
    request.status = decision
    request.decision_by = actor
    request.decision_note = note
    request.decided_at = utc_now()
    if decision == UsageDecisionStatus.APPROVED:
        asset = get_asset_or_404(db, request.asset_id)
        asset.lifecycle_status = LifecycleStatus.CERTIFIED
    db.commit()
    db.refresh(request)
    return request


def get_certification_request_or_404(db: Session, request_id: str) -> CertificationRequest:
    request = db.get(CertificationRequest, request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification request not found.")
    return request


def record_discovery_event(
    db: Session, session_id: str, actor: str | None, event_type, asset_id: str | None, query_text: str | None, metadata: dict
) -> DiscoveryEvent:
    event = DiscoveryEvent(
        session_id=session_id,
        actor_subject=actor,
        event_type=event_type,
        asset_id=asset_id,
        query_text=query_text,
        metadata_json=metadata,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def discovery_metric(db: Session) -> tuple[int, int, dict[str, int]]:
    sessions = list(db.scalars(select(DiscoveryEvent.session_id).where(DiscoveryEvent.event_type == DiscoveryEventType.SEARCH).distinct()))
    if not sessions:
        return 0, 0, {"asset_view": 0, "certification_request": 0, "usage_decision": 0}
    outcome_events = list(
        db.scalars(
            select(DiscoveryEvent).where(
                DiscoveryEvent.session_id.in_(sessions),
                DiscoveryEvent.event_type.in_(
                    [DiscoveryEventType.ASSET_VIEW, DiscoveryEventType.CERTIFICATION_REQUEST, DiscoveryEventType.USAGE_DECISION]
                ),
            )
        )
    )
    successful_sessions = {event.session_id for event in outcome_events}
    counts = {
        "asset_view": sum(event.event_type == DiscoveryEventType.ASSET_VIEW for event in outcome_events),
        "certification_request": sum(event.event_type == DiscoveryEventType.CERTIFICATION_REQUEST for event in outcome_events),
        "usage_decision": sum(event.event_type == DiscoveryEventType.USAGE_DECISION for event in outcome_events),
    }
    return len(sessions), len(successful_sessions), counts


def create_suggestion(db: Session, asset_id: str, suggestion_type, proposed_value: dict, evidence: dict, generated_by: str) -> GovernanceSuggestion:
    get_asset_or_404(db, asset_id)
    suggestion = GovernanceSuggestion(
        asset_id=asset_id,
        suggestion_type=suggestion_type,
        proposed_value=proposed_value,
        evidence=evidence,
        generated_by=generated_by,
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion


def get_suggestion_or_404(db: Session, suggestion_id: str) -> GovernanceSuggestion:
    suggestion = db.get(GovernanceSuggestion, suggestion_id)
    if suggestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Governance suggestion not found.")
    return suggestion


def review_suggestion(db: Session, suggestion: GovernanceSuggestion, review_status: ReviewStatus, note: str | None, reviewer: str) -> GovernanceSuggestion:
    suggestion.status = review_status
    suggestion.reviewed_by = reviewer
    suggestion.reviewed_at = utc_now()
    suggestion.review_note = note
    db.commit()
    db.refresh(suggestion)
    return suggestion
